import datetime
import logging
import re
from sqlalchemy import func
from app.database.connection import SessionLocal
from app.database.models import JourneyHistory, DemandHistory, Route
from app.cache import app_cache

logger = logging.getLogger(__name__)

class DemandAggregationService:
    def __init__(self):
        pass

    @staticmethod
    def _extract_route_ids(route_summary, valid_route_ids):
        """
        Journey history stores a display summary such as "6943 -> 8116 -> 1672".
        DemandHistory.route_id is a foreign key, so aggregate each valid route ID
        instead of inserting the whole path string.
        """
        if not route_summary:
            return []

        tokens = re.findall(r"[A-Za-z0-9-]+", str(route_summary))
        seen = set()
        route_ids = []
        for token in tokens:
            if token in valid_route_ids and token not in seen:
                route_ids.append(token)
                seen.add(token)
        return route_ids

    def run_aggregation(self):
        """
        Aggregates JourneyHistory into DemandHistory by route and hour.
        Uses a watermark (last processed JourneyHistory ID) to avoid duplicates.
        """
        db = SessionLocal()
        try:
            # Get the last processed ID from cache (or database max)
            last_processed_id = app_cache.get("last_aggregated_journey_id") or 0

            # Find all new journeys since last_processed_id
            new_journeys = db.query(JourneyHistory).filter(JourneyHistory.id > last_processed_id).all()
            
            if not new_journeys:
                logger.info("DemandAggregation: No new journeys to aggregate.")
                return

            # Group by route_id and the hour of the search
            # We'll use the current weather/traffic from cache for the aggregation record
            weather = app_cache.get('weather') or 'Clear, 28.0°C'
            traffic = app_cache.get('traffic') or 'Medium'
            
            aggregations = {}
            max_id = last_processed_id
            valid_route_ids = {r[0] for r in db.query(Route.route_id).all()}

            for j in new_journeys:
                if j.id > max_id:
                    max_id = j.id
                
                # If the journey resulted in a route
                if j.route_summary:
                    route_ids = self._extract_route_ids(j.route_summary, valid_route_ids)
                    if not route_ids:
                        logger.warning(
                            "DemandAggregation: skipped journey %s because route_summary has no valid route IDs: %s",
                            j.id,
                            j.route_summary,
                        )
                        continue

                    # simplify timestamp to hour
                    hour_timestamp = j.created_at.replace(minute=0, second=0, microsecond=0)
                    for route_id in route_ids:
                        key = (route_id, hour_timestamp)
                        if key not in aggregations:
                            aggregations[key] = 0
                        aggregations[key] += 1 # 1 search = 1 passenger intent

            # Insert into DemandHistory
            records_added = 0
            for (route_id, hour_ts), count in aggregations.items():
                # Estimate occupancy based on a default 60 capacity bus
                occupancy = min(100.0, (count / 60.0) * 100.0)
                
                # Check if we already have an entry for this route/hour to update, or insert new
                existing = db.query(DemandHistory).filter(
                    DemandHistory.route_id == route_id,
                    DemandHistory.timestamp == hour_ts
                ).first()

                if existing:
                    existing.passenger_count += count
                    existing.occupancy_percent = min(100.0, (existing.passenger_count / 60.0) * 100.0)
                else:
                    new_record = DemandHistory(
                        route_id=route_id,
                        passenger_count=count,
                        occupancy_percent=occupancy,
                        weather=weather.split(',')[0].strip(), # "Clear"
                        traffic=traffic,
                        timestamp=hour_ts
                    )
                    db.add(new_record)
                records_added += 1

            db.commit()
            app_cache.set("last_aggregated_journey_id", max_id, ttl_seconds=0) # 0 = infinite in some cache impls, or just long
            logger.info(f"DemandAggregation: Processed up to ID {max_id}. Added/Updated {records_added} hourly route records.")

        except Exception as e:
            import traceback
            logger.error(f"DemandAggregation failed: {e}\n{traceback.format_exc()}")
            db.rollback()
            raise e
        finally:
            db.close()

demand_aggregation_service = DemandAggregationService()
