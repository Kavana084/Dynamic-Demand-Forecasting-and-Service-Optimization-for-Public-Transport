import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database.models import ForecastHistory, DemandHistory, RouteScope, OptimizationResult, Route
from datetime import timedelta

logger = logging.getLogger(__name__)

def _normalize_scope(value: str | None, all_label: str) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v or v == all_label:
        return None
    return v

def _apply_route_scope_filter(db: Session, query, route_id_column, region: str | None, depot: str | None):
    region_v = _normalize_scope(region, "All Regions")
    depot_v = _normalize_scope(depot, "All Depots")
    if not region_v and not depot_v:
        return query

    route_ids_q = db.query(RouteScope.route_id)
    if region_v:
        route_ids_q = route_ids_q.filter(RouteScope.region == region_v)
    if depot_v:
        route_ids_q = route_ids_q.filter(RouteScope.depot == depot_v)

    return query.filter(route_id_column.in_(route_ids_q.subquery()))

class AnalyticsService:
    @staticmethod
    def get_dashboard_summary(db: Session, *, start=None, end=None, region: str | None = None, depot: str | None = None):
        """
        Returns the 4 summary KPI cards shown in Demand Analytics Dashboard:
        - Forecast Records       → always all-time total
        - Active Routes          → always all-time total
        - Total Predicted Passengers → always all-time total
        - Forecast Generated     → most recent timestamp (date-scoped)

        The date window (start/end) is intentionally NOT applied to the three
        top stat cards so they always reflect the complete dataset.  Charts and
        other analytics below the cards are date-scoped separately.
        """
        logger.info("Fetching dashboard summary KPIs...")

        # 1. Forecast Records — ALL TIME (no date filter)
        fh_all_q = db.query(ForecastHistory)
        fh_all_q = _apply_route_scope_filter(db, fh_all_q, ForecastHistory.route_id, region, depot)
        forecast_records = fh_all_q.count()

        # 2. Total Predicted Passengers — ALL TIME (no date filter)
        total_pax = fh_all_q.with_entities(func.sum(ForecastHistory.predicted_passengers)).scalar() or 0

        # 3. Active Routes — ALL TIME (no date filter)
        active_routes_q = db.query(func.count(func.distinct(ForecastHistory.route_id)))
        active_routes_q = _apply_route_scope_filter(db, active_routes_q, ForecastHistory.route_id, region, depot)
        active_routes = active_routes_q.scalar() or 0

        # 4. Peak Demand Route — date-scoped (used in charts/tables, not the 3 cards)
        peak_q = db.query(
            ForecastHistory.route_id,
            Route.route_short_name,
            func.sum(ForecastHistory.predicted_passengers).label('total_pax')
        ).join(Route, Route.route_id == ForecastHistory.route_id)
        if start and end:
            peak_q = peak_q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
        peak_q = _apply_route_scope_filter(db, peak_q, ForecastHistory.route_id, region, depot)
        peak_row = peak_q.group_by(ForecastHistory.route_id, Route.route_short_name).order_by(desc('total_pax')).first()
        peak_demand_route = peak_row.route_short_name if peak_row and peak_row.route_short_name else (peak_row.route_id if peak_row else None)

        # 5. Average Occupancy — date-scoped
        occ_q = db.query(func.avg(DemandHistory.occupancy_percent))
        if start and end:
            occ_q = occ_q.filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
        occ_q = _apply_route_scope_filter(db, occ_q, DemandHistory.route_id, region, depot)
        avg_occ = occ_q.scalar()
        average_occupancy = round(float(avg_occ), 1) if avg_occ is not None else 0.0

        # 6. Last Forecast Generated Time — all-time most recent
        last_gen = db.query(func.max(ForecastHistory.generated_at)).scalar()

        return {
            "forecast_records": forecast_records,
            "active_routes": active_routes,
            "total_predicted_passengers": int(total_pax),
            "peak_demand_route": peak_demand_route,
            "average_occupancy": average_occupancy,
            "last_forecast_time": last_gen.isoformat() if last_gen else None
        }


    @staticmethod
    def get_demand_distribution(db: Session, *, start=None, end=None, region: str | None = None, depot: str | None = None):
        """Predicted passengers by route"""
        q = db.query(
            ForecastHistory.route_id,
            Route.route_short_name,
            func.sum(ForecastHistory.predicted_passengers).label('predicted_passengers')
        ).join(Route, Route.route_id == ForecastHistory.route_id)
        if start and end:
            q = q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
        q = _apply_route_scope_filter(db, q, ForecastHistory.route_id, region, depot)
        results = q.group_by(ForecastHistory.route_id, Route.route_short_name).order_by(desc('predicted_passengers')).all()

        return [
            {
                "route_id": r.route_id,
                "route_short_name": r.route_short_name or r.route_id,
                "predicted_passengers": int(r.predicted_passengers or 0)
            } for r in results
        ]

    @staticmethod
    def get_peak_hour_analysis(db: Session, *, start=None, end=None, region: str | None = None, depot: str | None = None):
        """Passenger demand by hour of the day"""
        dialect = getattr(getattr(db, "bind", None), "dialect", None)
        dialect_name = getattr(dialect, "name", "")
        if dialect_name == "sqlite":
            hour_expr = func.strftime("%H", ForecastHistory.target_timestamp)
        else:
            hour_expr = func.extract("hour", ForecastHistory.target_timestamp)

        q = db.query(
            hour_expr.label("hour"),
            func.sum(ForecastHistory.predicted_passengers).label("predicted_passengers")
        )
        if start and end:
            q = q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
        q = _apply_route_scope_filter(db, q, ForecastHistory.route_id, region, depot)
        results = q.group_by("hour").order_by("hour").all()

        return [
            {
                "hour": f"{int(r.hour):02d}:00" if r.hour is not None else "00:00",
                "predicted_passengers": int(r.predicted_passengers or 0)
            } for r in results if r.hour is not None
        ]

    @staticmethod
    def get_route_ranking(db: Session, *, start=None, end=None, region: str | None = None, depot: str | None = None):
        """
        Table of routes with predicted demand, allocated buses, utilization, 
        occupancy, crowd level, demand trend, and last updated time.
        """
        # 1. Predicted Demand (Current Window) - Latest only
        q_pred = db.query(
            ForecastHistory.route_id,
            Route.route_short_name,
            ForecastHistory.predicted_passengers,
            ForecastHistory.generated_at
        ).join(Route, Route.route_id == ForecastHistory.route_id)
        if start and end:
            q_pred = q_pred.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
        q_pred = _apply_route_scope_filter(db, q_pred, ForecastHistory.route_id, region, depot)
        q_pred = q_pred.order_by(ForecastHistory.generated_at.desc())
        all_pred_rows = q_pred.all()
        pred_dict = {}
        for r in all_pred_rows:
            if r.route_id not in pred_dict:
                pred_dict[r.route_id] = type('Row', (), {'route_id': r.route_id, 'route_short_name': r.route_short_name, 'total_pred': r.predicted_passengers, 'last_updated': r.generated_at})
        pred_rows = list(pred_dict.values())

        # 2. Predicted Demand (Previous Window) for Trend
        trend_map = {}
        if start and end:
            duration = end - start
            prev_start = start - duration
            prev_end = start
            q_prev = db.query(
                ForecastHistory.route_id,
                func.sum(ForecastHistory.predicted_passengers).label('total_pred')
            ).filter(ForecastHistory.target_timestamp >= prev_start, ForecastHistory.target_timestamp < prev_end)
            q_prev = _apply_route_scope_filter(db, q_prev, ForecastHistory.route_id, region, depot)
            prev_rows = q_prev.group_by(ForecastHistory.route_id).all()
            for r in prev_rows:
                trend_map[r.route_id] = r.total_pred

        # 3. Allocated Buses, Utilization, Recommendation from OptimizationResult
        q_opt = db.query(OptimizationResult)
        if start and end:
            q_opt = q_opt.filter(OptimizationResult.timestamp >= start, OptimizationResult.timestamp < end)
        q_opt = _apply_route_scope_filter(db, q_opt, OptimizationResult.route_id, region, depot)
        opt_rows = q_opt.order_by(OptimizationResult.timestamp.desc()).all()
        opt_map = {}
        for r in opt_rows:
            if r.route_id not in opt_map:
                opt_map[r.route_id] = {
                    "allocated_buses": r.allocated_buses or 0,
                    "utilization": r.utilization or 0.0,
                    "unserved_demand": r.unserved_demand or 0,
                    "recommended_frequency": r.recommended_frequency or "",
                }

        # 4. Average Occupancy from DemandHistory
        q_occ = db.query(
            DemandHistory.route_id,
            func.avg(DemandHistory.occupancy_percent).label('avg_occ')
        )
        if start and end:
            q_occ = q_occ.filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
        q_occ = _apply_route_scope_filter(db, q_occ, DemandHistory.route_id, region, depot)
        occ_rows = q_occ.group_by(DemandHistory.route_id).all()
        occ_map = {r.route_id: (r.avg_occ or 0.0) for r in occ_rows}

        results = []
        for row in pred_rows:
            route_id = row.route_id
            curr_pred = float(row.total_pred or 0)
            prev_pred = float(trend_map.get(route_id, 0))
            
            trend = "▬ Stable"
            if prev_pred > 0:
                change = (curr_pred - prev_pred) / prev_pred
                if change > 0.05:
                    trend = "▲ Increasing"
                elif change < -0.05:
                    trend = "▼ Decreasing"

            opt_data = opt_map.get(route_id, {
                "allocated_buses": 0, "utilization": 0.0,
                "unserved_demand": 0, "recommended_frequency": ""
            })
            alloc_buses = opt_data["allocated_buses"]
            # utilization is stored as a percentage (0-100) by the MILP engine
            util_pct = float(opt_data["utilization"])
            unserved_demand = opt_data["unserved_demand"]
            recommended_frequency = opt_data["recommended_frequency"]

            if util_pct > 85.0:
                alloc_status = "Under Allocated"
            elif util_pct < 60.0 and alloc_buses > 0:
                alloc_status = "Over Allocated"
            elif alloc_buses == 0:
                alloc_status = "Unallocated"
            else:
                alloc_status = "Optimal"

            occ = float(occ_map.get(route_id, 0.0))
            if occ < 40:
                crowd_level = "🟢 Low"
            elif occ < 70:
                crowd_level = "🟡 Moderate"
            elif occ < 90:
                crowd_level = "🟠 Busy"
            else:
                crowd_level = "🔴 Crowded"

            results.append({
                "route_id": route_id,
                "route_short_name": row.route_short_name or route_id,
                "predicted_demand": int(curr_pred),
                "allocated_buses": alloc_buses,
                "utilization": round(util_pct, 1),  # already a percentage
                "occupancy": round(occ, 1),
                "crowd_level": crowd_level,
                "demand_trend": trend,
                "allocation_status": alloc_status,
                "unserved_demand": unserved_demand,
                "recommended_frequency": recommended_frequency,
                "last_updated": row.last_updated.isoformat() if row.last_updated else None
            })

        return results

    @staticmethod
    def get_demand_heatmap(db: Session, *, start, end, region: str | None = None, depot: str | None = None, top_routes: int = 8):
        """
        Returns heatmap matrix backed by DemandHistory aggregation (no frontend synthesis).

        Output:
          { rows: [route_id...], cols: ["00".."23"], values: {route:{hour:sum}}, max: int }
        """
        if not start or not end:
            return {"rows": [], "cols": [], "values": {}, "max": 0}

        dialect = getattr(getattr(db, "bind", None), "dialect", None)
        dialect_name = getattr(dialect, "name", "")
        if dialect_name == "sqlite":
            hour_expr = func.strftime("%H", DemandHistory.timestamp)
        else:
            hour_expr = func.extract("hour", DemandHistory.timestamp)

        base = db.query(
            DemandHistory.route_id.label("route_id"),
            hour_expr.label("hour"),
            func.sum(DemandHistory.passenger_count).label("pax"),
        ).filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
        base = _apply_route_scope_filter(db, base, DemandHistory.route_id, region, depot)

        # Determine top routes by total pax in the window
        totals = (
            db.query(DemandHistory.route_id, func.sum(DemandHistory.passenger_count).label("pax"))
            .filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
        )
        totals = _apply_route_scope_filter(db, totals, DemandHistory.route_id, region, depot)
        top = (
            totals.group_by(DemandHistory.route_id)
            .order_by(desc("pax"))
            .limit(top_routes)
            .all()
        )
        route_ids = [r.route_id for r in top if r.route_id]
        if not route_ids:
            return {"rows": [], "cols": [], "values": {}, "max": 0}

        rows = (
            base.filter(DemandHistory.route_id.in_(route_ids))
            .group_by(DemandHistory.route_id, "hour")
            .all()
        )

        cols = [str(i).zfill(2) for i in range(24)]

        values = {rid: {h: None for h in cols} for rid in route_ids}
        max_v = 0
        for r in rows:
            h = str(r.hour).zfill(2)
            pax = int(r.pax or 0)
            values[r.route_id][h] = pax
            max_v = max(max_v, pax)

        return {"rows": route_ids, "cols": cols, "values": values, "max": max_v}
