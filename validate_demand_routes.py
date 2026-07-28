"""
validate_demand_routes.py
=========================
Phase 2 Validation: Demand Prediction Audit

Tests up to min(100, all_routes) origin-destination pairs through the
backend demand prediction service.

For each route captures:
  - route_id
  - predicted_demand (at peak and off-peak hours)
  - occupancy_percent  (from demand_history DB)
  - peak_status
  - demand_confidence  (from forecast_history DB — note: /api/predict_demand drops this)
  - weather
  - traffic

Generates:
  - Statistics (min, max, avg, stddev, unique count)
  - Suspicious clustering detection
  - Peak vs off-peak differential check
  - Weather/traffic sensitivity check

Output: demand_validation_report.md
"""

import os
import sys
import math
import statistics
import datetime
from collections import defaultdict, Counter

# Ensure backend importable
_base = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_base, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "transit_admin_secret")
MAX_ROUTES = 100
REPORT_PATH = os.path.join(os.path.dirname(__file__), "demand_validation_report.md")

# Hour configurations
PEAK_HOURS     = [8, 17]   # morning peak, evening peak
OFF_PEAK_HOURS = [13, 22]  # midday, late night

# Condition matrix for sensitivity testing
WEATHER_CONDITIONS = ["Clear", "Cloudy", "Rainy", "Storm"]
TRAFFIC_LEVELS     = ["Low", "Medium", "High", "Heavy"]

# Suspicion threshold: if stddev of demand across all routes is < this, flag it
SUSPICION_STDDEV_THRESHOLD = 5.0
# Clustering threshold: if > this % of demand values are identical, flag it
CLUSTERING_PERCENT_THRESHOLD = 40.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def try_import_requests():
    try:
        import requests
        return requests
    except ImportError:
        return None

def call_predict_api(requests_lib, route_id, hour, weather, traffic):
    """Call /api/predict_demand. Returns predicted_demand int or None on error."""
    try:
        r = requests_lib.post(
            f"{BACKEND_URL}/api/predict_demand",
            json={"route_id": route_id, "hour": hour, "weather": weather, "traffic": traffic},
            headers={"X-Admin-Token": ADMIN_TOKEN},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("predicted_demand"), data.get("cached", False)
    except Exception as e:
        pass
    return None, None

_sa_session_cache = None
_sa_dh_cache = {}    # route_id -> {occupancy_percent, weather, traffic}
_sa_fh_cache = {}    # route_id -> confidence_score

def _get_sa_data():
    """Load demand_history and forecast_history into memory caches."""
    global _sa_dh_cache, _sa_fh_cache
    if _sa_dh_cache or _sa_fh_cache:
        return  # already loaded
    try:
        from app.database.connection import SessionLocal
        from app.database.models import DemandHistory, ForecastHistory
        db = SessionLocal()
        # Load DemandHistory — latest per route
        dh_rows = db.query(DemandHistory).order_by(DemandHistory.timestamp.desc()).limit(5000).all()
        for r in dh_rows:
            if r.route_id not in _sa_dh_cache:
                _sa_dh_cache[r.route_id] = {
                    "occupancy_percent": r.occupancy_percent,
                    "weather":           r.weather,
                    "traffic":           r.traffic,
                }
        # Load ForecastHistory — latest per route
        fh_rows = db.query(ForecastHistory).order_by(ForecastHistory.generated_at.desc()).limit(5000).all()
        for r in fh_rows:
            if r.route_id not in _sa_fh_cache:
                _sa_fh_cache[r.route_id] = r.confidence_score
        db.close()
        print(f"  [DB] Loaded {len(_sa_dh_cache)} demand history and {len(_sa_fh_cache)} forecast history records.")
    except Exception as e:
        print(f"  [DB] SQLAlchemy load failed: {e}")

def get_routes_from_db():
    """Read route IDs from Supabase via backend SQLAlchemy."""
    try:
        from app.database.connection import SessionLocal
        from app.database.models import Route
        db = SessionLocal()
        rows = db.query(Route.route_id).limit(MAX_ROUTES).all()
        db.close()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        print(f"  [DB] Routes query failed: {e}")
        return []

def get_demand_history_from_db(route_id):
    """Fetch occupancy_percent, weather, traffic from demand_history for a route."""
    _get_sa_data()
    return _sa_dh_cache.get(str(route_id), {})

def get_forecast_confidence_from_db(route_id):
    """Fetch latest confidence_score from forecast_history for a route."""
    _get_sa_data()
    return _sa_fh_cache.get(str(route_id))

    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT confidence_score FROM forecast_history WHERE route_id=? ORDER BY generated_at DESC LIMIT 1",
                    (route_id,)
                )
                row = cur.fetchone()
                conn.close()
                if row:
                    return row[0]
            except Exception:
                pass
    return None

# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------

def run_demand_audit():
    requests_lib = try_import_requests()
    api_available = False

    if requests_lib:
        try:
            r = requests_lib.get(f"{BACKEND_URL}/api/routes?skip=0&limit={MAX_ROUTES}", timeout=8)
            if r.status_code == 200:
                api_available = True
                routes_data = r.json()
                route_ids = [row.get("route_id") or row.get("id") for row in routes_data if row.get("route_id") or row.get("id")]
                route_ids = [str(r) for r in route_ids if r][:MAX_ROUTES]
            else:
                route_ids = get_routes_from_db()
        except Exception:
            route_ids = get_routes_from_db()
    else:
        route_ids = get_routes_from_db()

    if not route_ids:
        print("ERROR: No routes found. Cannot run demand audit.")
        sys.exit(1)

    print(f"[Demand Audit] Found {len(route_ids)} routes. API available: {api_available}")

    # ── Per-route data collection ────────────────────────────────────────────
    results = []
    peak_demands    = []  # demand at peak hours
    offpeak_demands = []  # demand at off-peak hours
    all_demands     = []  # all demand values (for statistics)

    sensitivity_data = defaultdict(dict)  # route_id -> {condition_key: demand}

    for idx, route_id in enumerate(route_ids):
        print(f"  [{idx+1}/{len(route_ids)}] Route: {route_id}")

        # Demand at peak hour (hour=8, Clear, Medium)
        peak_d, peak_cached = call_predict_api(requests_lib, route_id, 8, "Clear", "Medium") if api_available else (None, None)
        # Demand at off-peak (hour=14, Clear, Medium)
        offpeak_d, _ = call_predict_api(requests_lib, route_id, 14, "Clear", "Medium") if api_available else (None, None)

        # Sensitivity: Rainy vs Clear (hour=8, Medium traffic)
        rainy_d, _ = call_predict_api(requests_lib, route_id, 8, "Rainy", "Medium") if api_available else (None, None)
        # Sensitivity: Heavy traffic vs Low (hour=8, Clear)
        heavy_d, _ = call_predict_api(requests_lib, route_id, 8, "Clear", "Heavy") if api_available else (None, None)
        low_d, _   = call_predict_api(requests_lib, route_id, 8, "Clear", "Low") if api_available else (None, None)

        # DB lookups
        dh = get_demand_history_from_db(route_id)
        confidence = get_forecast_confidence_from_db(route_id)

        row = {
            "route_id":          route_id,
            "peak_demand":        peak_d,
            "offpeak_demand":     offpeak_d,
            "rainy_demand":       rainy_d,
            "heavy_traffic_demand": heavy_d,
            "low_traffic_demand": low_d,
            "occupancy_percent":  dh.get("occupancy_percent"),
            "weather_db":         dh.get("weather", "N/A"),
            "traffic_db":         dh.get("traffic", "N/A"),
            "demand_confidence":  confidence,
            "peak_status":        "peak" if peak_d is not None else "unknown",
            "peak_cached":        peak_cached,
        }
        results.append(row)

        if peak_d is not None:
            peak_demands.append(peak_d)
            all_demands.append(peak_d)
        if offpeak_d is not None:
            offpeak_demands.append(offpeak_d)
            all_demands.append(offpeak_d)

        sensitivity_data[route_id]["clear_medium"]  = peak_d
        sensitivity_data[route_id]["rainy_medium"]  = rainy_d
        sensitivity_data[route_id]["clear_heavy"]   = heavy_d
        sensitivity_data[route_id]["clear_low"]     = low_d

    # ── Statistics ───────────────────────────────────────────────────────────
    valid_peak = [d for d in peak_demands if d is not None]
    valid_offpeak = [d for d in offpeak_demands if d is not None]
    valid_all = [d for d in all_demands if d is not None]

    def stats(vals):
        if not vals:
            return {"min": None, "max": None, "avg": None, "stddev": None, "count": 0, "unique": 0}
        return {
            "min":    min(vals),
            "max":    max(vals),
            "avg":    round(statistics.mean(vals), 2),
            "stddev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0,
            "count":  len(vals),
            "unique": len(set(vals)),
        }

    peak_stats    = stats(valid_peak)
    offpeak_stats = stats(valid_offpeak)
    all_stats     = stats(valid_all)

    # ── Suspicious clustering detection ──────────────────────────────────────
    value_freq = Counter(valid_peak)
    most_common_val, most_common_count = value_freq.most_common(1)[0] if value_freq else (None, 0)
    cluster_pct = (most_common_count / len(valid_peak) * 100) if valid_peak else 0

    suspicious_clustering = cluster_pct >= CLUSTERING_PERCENT_THRESHOLD or (
        peak_stats["stddev"] is not None and peak_stats["stddev"] < SUSPICION_STDDEV_THRESHOLD
    )

    # ── Peak vs off-peak check ────────────────────────────────────────────────
    peak_gt_offpeak_count = 0
    comparable_routes = 0
    for row in results:
        if row["peak_demand"] is not None and row["offpeak_demand"] is not None:
            comparable_routes += 1
            if row["peak_demand"] > row["offpeak_demand"]:
                peak_gt_offpeak_count += 1

    peak_check_pass = (peak_gt_offpeak_count / comparable_routes >= 0.70) if comparable_routes > 0 else None

    # ── Sensitivity check ────────────────────────────────────────────────────
    weather_sensitive_count = 0
    traffic_sensitive_count = 0
    sensitivity_total = 0

    for route_id, conds in sensitivity_data.items():
        clear = conds.get("clear_medium")
        rainy = conds.get("rainy_medium")
        heavy = conds.get("clear_heavy")
        low   = conds.get("clear_low")

        if clear is not None and rainy is not None:
            sensitivity_total += 1
            if rainy != clear:
                weather_sensitive_count += 1

        if heavy is not None and low is not None:
            if heavy != low:
                traffic_sensitive_count += 1

    # ── Build report ─────────────────────────────────────────────────────────
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = []

    lines.append("# Demand Prediction Validation Report")
    lines.append(f"\n**Generated**: {now_str}")
    lines.append(f"**Backend**: {BACKEND_URL} (API available: {api_available})")
    lines.append(f"**Routes tested**: {len(results)}")
    lines.append(f"**Conditions tested per route**: peak(h=8), off-peak(h=14), rainy, heavy-traffic, low-traffic\n")

    lines.append("---\n")

    # Summary statistics
    lines.append("## 1. Statistics Summary\n")
    lines.append("### Peak Hour Demands (hour=8, Clear, Medium traffic)")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Minimum | {peak_stats['min']} |")
    lines.append(f"| Maximum | {peak_stats['max']} |")
    lines.append(f"| Average | {peak_stats['avg']} |")
    lines.append(f"| Std Dev | {peak_stats['stddev']} |")
    lines.append(f"| Count   | {peak_stats['count']} |")
    lines.append(f"| Unique values | {peak_stats['unique']} |")

    lines.append("\n### Off-Peak Hour Demands (hour=14, Clear, Medium traffic)")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Minimum | {offpeak_stats['min']} |")
    lines.append(f"| Maximum | {offpeak_stats['max']} |")
    lines.append(f"| Average | {offpeak_stats['avg']} |")
    lines.append(f"| Std Dev | {offpeak_stats['stddev']} |")
    lines.append(f"| Count   | {offpeak_stats['count']} |")
    lines.append(f"| Unique values | {offpeak_stats['unique']} |")

    lines.append("\n### All Demand Values (combined)")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Minimum | {all_stats['min']} |")
    lines.append(f"| Maximum | {all_stats['max']} |")
    lines.append(f"| Average | {all_stats['avg']} |")
    lines.append(f"| Std Dev | {all_stats['stddev']} |")
    lines.append(f"| Count   | {all_stats['count']} |")
    lines.append(f"| Unique values | {all_stats['unique']} |")
    lines.append("")

    # Frequency distribution
    lines.append("### Demand Value Frequency Distribution (Peak Hour)")
    lines.append("| Demand Value | Route Count | % of Routes |")
    lines.append("|---|---|---|")
    for val, cnt in sorted(value_freq.items(), key=lambda x: -x[1])[:20]:
        pct = cnt / len(valid_peak) * 100 if valid_peak else 0
        lines.append(f"| {val} | {cnt} | {pct:.1f}% |")
    lines.append("")

    # Clustering flag
    lines.append("---\n")
    lines.append("## 2. Suspicious Clustering Detection\n")
    status_emoji = "🔴 FLAGGED" if suspicious_clustering else "✅ PASS"
    lines.append(f"**Status**: {status_emoji}\n")
    lines.append(f"- Most common peak demand value: **{most_common_val}** (appears {most_common_count} times = {cluster_pct:.1f}% of routes)")
    lines.append(f"- Standard deviation of peak demands: **{peak_stats['stddev']}**")
    lines.append(f"- Clustering threshold: >{CLUSTERING_PERCENT_THRESHOLD}% identical values OR stddev < {SUSPICION_STDDEV_THRESHOLD}")
    if suspicious_clustering:
        lines.append("\n> ⚠️ **Issue**: Many unrelated routes produce nearly identical demand values.")
        lines.append("> This suggests the model may be defaulting to constant outputs for certain feature combinations,")
        lines.append("> or that historical feature defaults (e.g., `historical_route_average=25.0`) are dominating the prediction.")
    lines.append("")

    # Peak vs off-peak
    lines.append("---\n")
    lines.append("## 3. Peak Hour vs Off-Peak Hour Validation\n")
    if peak_check_pass is None:
        lines.append("**Status**: ⚠️ INSUFFICIENT DATA (no comparable route pairs)\n")
    elif peak_check_pass:
        lines.append("**Status**: ✅ PASS\n")
    else:
        lines.append("**Status**: 🔴 FAIL\n")
    lines.append(f"- Comparable routes (both peak + off-peak available): {comparable_routes}")
    lines.append(f"- Routes where peak > off-peak: {peak_gt_offpeak_count} ({peak_gt_offpeak_count/comparable_routes*100:.1f}% if applicable)")
    lines.append(f"- Threshold: ≥70% of routes must show peak > off-peak")
    if not peak_check_pass and comparable_routes > 0:
        lines.append("\n> ⚠️ **Issue**: Fewer than 70% of routes show higher demand at peak hours vs off-peak.")
        lines.append("> This indicates the `peak_hour_flag` feature may not be influencing the CatBoost model correctly.")
    lines.append("")

    # Sensitivity
    lines.append("---\n")
    lines.append("## 4. Weather & Traffic Sensitivity Validation\n")
    weather_pct = (weather_sensitive_count / sensitivity_total * 100) if sensitivity_total > 0 else 0
    traffic_pct = (traffic_sensitive_count / sensitivity_total * 100) if sensitivity_total > 0 else 0

    weather_emoji = "✅ PASS" if weather_pct >= 50 else "🔴 FAIL"
    traffic_emoji = "✅ PASS" if traffic_pct >= 50 else "🔴 FAIL"

    lines.append(f"### Weather Sensitivity (Clear vs Rainy, same route/hour/traffic)")
    lines.append(f"**Status**: {weather_emoji}")
    lines.append(f"- Routes where Rainy ≠ Clear demand: {weather_sensitive_count}/{sensitivity_total} ({weather_pct:.1f}%)")
    lines.append("")
    lines.append(f"### Traffic Sensitivity (Low vs Heavy, same route/hour/weather)")
    lines.append(f"**Status**: {traffic_emoji}")
    lines.append(f"- Routes where Heavy ≠ Low demand: {traffic_sensitive_count}/{sensitivity_total} ({traffic_pct:.1f}%)")
    lines.append("")

    if weather_pct < 50:
        lines.append("> ⚠️ **Issue**: Most routes produce the same demand regardless of weather.")
        lines.append("> The `weather_condition` feature may be underweighted in the CatBoost model, or")
        lines.append("> the current API path (/api/predict_demand) maps weather into features with insufficient")
        lines.append("> differentiation (see `service.py:_construct_features_from_inputs`).")
        lines.append("")
    if traffic_pct < 50:
        lines.append("> ⚠️ **Issue**: Most routes produce the same demand regardless of traffic level.")
        lines.append("> The `traffic_level` / `congestion_index` features may not be effective in the model.")
        lines.append("")

    # Per-route table
    lines.append("---\n")
    lines.append("## 5. Per-Route Detail Table\n")
    lines.append("| Route ID | Peak Demand (h=8) | Off-Peak (h=14) | Rainy (h=8) | Heavy Traffic | DB Occupancy% | DB Confidence | Peak>OffPeak |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in results:
        peak     = row["peak_demand"]   or "N/A"
        offpeak  = row["offpeak_demand"] or "N/A"
        rainy    = row["rainy_demand"]   or "N/A"
        heavy    = row["heavy_traffic_demand"] or "N/A"
        occ      = f"{row['occupancy_percent']:.1f}%" if row["occupancy_percent"] else "N/A"
        conf     = f"{row['demand_confidence']:.3f}" if row["demand_confidence"] else "N/A"
        pk_gt    = ""
        if row["peak_demand"] is not None and row["offpeak_demand"] is not None:
            pk_gt = "✅" if row["peak_demand"] > row["offpeak_demand"] else "❌"
        lines.append(f"| {row['route_id']} | {peak} | {offpeak} | {rainy} | {heavy} | {occ} | {conf} | {pk_gt} |")
    lines.append("")

    # Findings summary
    lines.append("---\n")
    lines.append("## 6. Key Findings\n")

    findings = []
    if suspicious_clustering:
        findings.append(f"🔴 **Demand clustering detected**: {cluster_pct:.1f}% of routes return demand={most_common_val}. "
                        f"Stddev={peak_stats['stddev']}. Model may be outputting near-constant values for the default feature set.")

    if not peak_check_pass and comparable_routes > 0:
        findings.append(f"🔴 **Peak/off-peak not differentiated**: Only {peak_gt_offpeak_count}/{comparable_routes} routes "
                        f"show peak > off-peak. The `peak_hour_flag` feature is not driving meaningful demand increase.")

    if weather_pct < 50:
        findings.append(f"🔴 **Weather insensitivity**: Only {weather_sensitive_count}/{sensitivity_total} routes respond to weather change. "
                        f"Demand is largely weather-invariant under current feature construction.")

    if traffic_pct < 50:
        findings.append(f"🔴 **Traffic insensitivity**: Only {traffic_sensitive_count}/{sensitivity_total} routes respond to traffic change.")

    # API confidence stripping
    findings.append("⚠️ **Confidence stripped at API boundary**: `/api/predict_demand` returns only `predicted_demand`. "
                    "The CatBoost model's `confidence_score` is computed internally but never forwarded to callers. "
                    "Frontend (`PredictDemand.jsx:42`) hardcodes `confidence: 85` as fallback.")

    findings.append("⚠️ **Dual demand paths**: `/api/predict_demand` uses `PredictionService.predict_demand()` with hardcoded "
                    "default features (`day_of_week='Monday'`, `month=1`, `temperature=28`). "
                    "The Fleet Optimization engine reads `ForecastHistory` DB records instead. "
                    "These two paths diverge and may produce different demand values for the same route.")

    if findings:
        for f in findings:
            lines.append(f"- {f}\n")
    else:
        lines.append("✅ No critical findings detected.\n")

    # Write report
    report_text = "\n".join(lines)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n[Demand Audit] Report written to: {REPORT_PATH}")
    print(f"  Routes tested: {len(results)}")
    print(f"  Clustering detected: {suspicious_clustering}")
    print(f"  Peak check pass: {peak_check_pass}")
    print(f"  Weather sensitivity: {weather_pct:.1f}%")
    print(f"  Traffic sensitivity: {traffic_pct:.1f}%")
    return len(findings)


if __name__ == "__main__":
    issues = run_demand_audit()
    sys.exit(0 if issues == 0 else 1)
