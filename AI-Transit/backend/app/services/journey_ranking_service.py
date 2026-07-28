from typing import List, Dict, Any
from app.logger import app_logger

class JourneyRankingService:
    def __init__(self):
        self.MAX_TRANSFERS = 2
        self.MAX_WALK_DISTANCE = 800

    def rank_and_filter(self, itineraries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters out invalid OTP itineraries and ranks them according to the formula:
        score = travel_time + (transfers * 15) + (walking_distance * 0.01)

        Validation enforced:
        - No more than MAX_TRANSFERS transfers
        - Walking distance <= MAX_WALK_DISTANCE
        - Destination-termination: journey must end at the destination stop
        - No repeated stop IDs across transit legs (loop detection)
        """
        valid_itineraries = []

        for itinerary in itineraries:
            transfers = itinerary.get("transfers", 0)
            walk_distance = itinerary.get("walkDistance", 0)
            travel_time = itinerary.get("duration", 0) / 60.0  # seconds to minutes
            
            if transfers > self.MAX_TRANSFERS:
                continue
                
            if walk_distance > self.MAX_WALK_DISTANCE:
                continue

            legs = itinerary.get("legs", [])
            seen_stops: set = set()
            loop_detected = False
            dest_overrun = False  # stops exist after the declared destination

            # Collect the declared destination from the last transit leg
            declared_dest_id = None
            for leg in reversed(legs):
                if leg.get("mode") != "WALK":
                    declared_dest_id = leg.get("to", {}).get("stopId")
                    break

            for leg_idx, leg in enumerate(legs):
                # We only care about transit legs for stop repetition
                if leg.get("mode") == "WALK":
                    continue
                    
                from_stop = leg.get("from", {}).get("stopId")
                to_stop = leg.get("to", {}).get("stopId")
                
                if from_stop:
                    if from_stop in seen_stops:
                        loop_detected = True
                        app_logger.warning(
                            f"[JourneyRanking] Loop detected: stop {from_stop} "
                            f"revisited in leg {leg_idx}"
                        )
                        break
                    seen_stops.add(from_stop)

                # Check intermediate stops for loops and destination overrun
                for intermediate in leg.get("intermediateStops", []):
                    stop_id = intermediate.get("stopId")
                    if stop_id:
                        if stop_id in seen_stops:
                            loop_detected = True
                            app_logger.warning(
                                f"[JourneyRanking] Loop detected at intermediate "
                                f"stop {stop_id} in leg {leg_idx}"
                            )
                            break
                        # Destination-termination: if destination appears as
                        # intermediate, the journey should have stopped there
                        if declared_dest_id and stop_id == declared_dest_id:
                            dest_overrun = True
                            app_logger.warning(
                                f"[JourneyRanking] Destination overrun: stop "
                                f"{stop_id} appears as intermediate before journey end"
                            )
                            break
                        seen_stops.add(stop_id)
                        
                if loop_detected or dest_overrun:
                    break
                    
                if to_stop:
                    if to_stop in seen_stops:
                        loop_detected = True
                        app_logger.warning(
                            f"[JourneyRanking] Loop detected: to_stop {to_stop} "
                            f"revisited in leg {leg_idx}"
                        )
                        break
                    seen_stops.add(to_stop)

            if loop_detected or dest_overrun:
                continue
                
            # Score calculation
            score = travel_time + (transfers * 15) + (walk_distance * 0.01)
            itinerary["_quality_score"] = score
            valid_itineraries.append(itinerary)

        # Sort by best score (lowest)
        valid_itineraries.sort(key=lambda x: x["_quality_score"])
        return valid_itineraries

journey_ranking_service = JourneyRankingService()

