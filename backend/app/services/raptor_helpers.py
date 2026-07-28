"""
raptor_helpers.py — Shared RAPTOR result conversion
=====================================================
Extracted from app/api_routes.py so that every endpoint using RAPTOR routing
(/api/plan_trip, /api/navigation/plan, and any future callers) converts RAPTOR
output identically. Previously this logic existed only inside api_routes.py,
which meant /api/navigation/plan (used by the AI Assistant's plan_trip tool)
had no access to it and fell back to calling the legacy Dijkstra engine
(resolve_route_dynamic) directly instead — the cause of multi-minute timeouts
on multi-transfer trips. See routing_service._transfer_aware_dijkstra for
that engine's documented scaling limits.

Both api_routes.py and app/api/navigation.py should import from here.
"""

import math
from typing import Dict, List, Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models import GTFSStop


def _base_route_id(pattern_route_id: Optional[str]) -> Optional[str]:
    """
    RAPTOR splits routes by stop pattern and tags non-primary patterns with a
    synthetic suffix, e.g. "1000::a1b2c3d4". Nothing outside raptor_service
    (routes table, fare_service, ML encoders, live bus tracking, optimization
    results) knows about that suffix — they all key on the plain GTFS route_id.
    Strip it here, at the boundary, so the synthetic ID never leaks downstream.
    """
    if not pattern_route_id:
        return pattern_route_id
    return pattern_route_id.split("::", 1)[0]


def convert_raptor_to_route_info(raptor_result: dict, db: Session) -> dict:
    """
    Convert RAPTOR output to the existing route_info format expected by the rest
    of the pipeline (both /api/plan_trip and /api/navigation/plan consume this).

    RAPTOR returns: {status_code, arrival_time_sec, transfer_count, legs}
    We need to convert to: {route_id, stops, route_path, transfers, total_distance_km, etc.}
    """
    from app.services.raptor_service import get_transit_data  # local import avoids circulars

    if raptor_result.get("status_code") == 404:
        raise HTTPException(status_code=404, detail=raptor_result.get("detail"))

    legs = raptor_result.get("legs", [])
    arrival_time_sec = raptor_result.get("arrival_time_sec", 0)

    # Extract stops from legs. For "ride" legs, expand from the board/alight
    # endpoints out to the FULL physical stop sequence the bus actually
    # passes through (using the same pattern data RAPTOR already has
    # cached), so the map can draw the real route shape instead of a
    # straight line between two far-apart points. Walk legs have no
    # intermediate physical stops, so they stay as 2 points.
    transit_data = get_transit_data(db)  # process-global cache — cheap to call again

    stops: List[str] = []  # ordered stop_ids, may include consecutive duplicates at leg joins
    route_ids = []  # ordered, de-duplicated (not a set — leg order matters for fare/display)

    def _append_stop(stop_id):
        # avoid duplicating the shared boundary stop between consecutive legs
        if not stops or stops[-1] != stop_id:
            stops.append(stop_id)

    for leg in legs:
        base_id = _base_route_id(leg.get("route_id"))
        if base_id and base_id not in route_ids:
            route_ids.append(base_id)

        if leg.get("kind") == "ride":
            route = transit_data.routes.get(leg.get("route_id"))
            from_idx = route.stop_indices.get(leg.get("from")) if route else None
            to_idx = route.stop_indices.get(leg.get("to")) if route else None
            if route and from_idx is not None and to_idx is not None:
                # full physical stop sequence for this ride, endpoints included
                for stop_id in route.stops[from_idx:to_idx + 1]:
                    _append_stop(stop_id)
            else:
                # fallback: pattern lookup failed, just use board/alight
                _append_stop(leg.get("from"))
                _append_stop(leg.get("to"))
        else:
            # walk leg: no intermediate physical stops
            _append_stop(leg.get("from"))
            _append_stop(leg.get("to"))

    # Build route_path with coordinates. Bulk-fetch all stops in one query
    # instead of one query per stop_id.
    route_path = []
    transfer_stop_ids = set()
    current_route = None
    for leg in legs:
        if leg.get("kind") == "ride":
            r_id = _base_route_id(leg.get("route_id"))
            if current_route and current_route != r_id:
                transfer_stop_ids.add(leg.get("from"))
            current_route = r_id

    if stops:
        unique_ids = list(dict.fromkeys(stops))
        stop_rows = {
            s.stop_id: s
            for s in db.query(GTFSStop).filter(GTFSStop.stop_id.in_(unique_ids)).all()
        }
        last_idx = len(stops) - 1
        for i, stop_id in enumerate(stops):
            stop = stop_rows.get(stop_id)
            if not stop:
                continue
            if i == 0:
                stop_type = "start"
            elif i == last_idx:
                stop_type = "destination"
            elif stop_id in transfer_stop_ids:
                stop_type = "transfer"
            else:
                stop_type = "stop"
            route_path.append({
                "stop_id": stop_id,
                "stop_name": stop.stop_name,
                "lat": stop.stop_lat,
                "lon": stop.stop_lon,
                "type": stop_type,
                "is_transfer": stop_type == "transfer",
            })

    # Calculate total distance using haversine
    total_distance_km = 0.0
    for i in range(len(route_path) - 1):
        lat1, lon1 = route_path[i]["lat"], route_path[i]["lon"]
        lat2, lon2 = route_path[i + 1]["lat"], route_path[i + 1]["lon"]
        if lat1 and lon1 and lat2 and lon2:
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
                 * math.sin(dlon / 2) ** 2)
            total_distance_km += R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    total_distance_km = round(total_distance_km)

    # Build transfers list. stop_name must be the actual stop name (not the
    # stop_id) since the frontend matches transfer markers by name against
    # route_path entries.
    stop_name_by_id = {p["stop_id"]: p["stop_name"] for p in route_path}
    transfers = []
    current_route = None
    for leg in legs:
        if leg.get("kind") == "ride":
            route_id = _base_route_id(leg.get("route_id"))
            if current_route and current_route != route_id:
                from_stop_id = leg.get("from")
                transfers.append({
                    "stop_id": from_stop_id,
                    "stop_name": stop_name_by_id.get(from_stop_id, from_stop_id),
                    "from_route": current_route,
                    "to_route": route_id
                })
            current_route = route_id

    # Build route_legs for display
    route_legs = []
    current_route = None
    for leg in legs:
        if leg.get("kind") == "ride":
            route_id = _base_route_id(leg.get("route_id"))
            if current_route != route_id:
                route_legs.append({
                    "route_id": route_id,
                    "start_stop": leg.get("from"),
                })
                current_route = route_id

    return {
        "route_id": route_ids[0] if route_ids else "unknown",
        "route_ids": route_ids,
        "stops": stops,
        "route_path": route_path,
        "transfers": transfers,
        "route_legs": route_legs,
        "total_distance_km": total_distance_km,
        "total_stops_on_route": len(stops),
        "ml_route_id": route_ids[0] if route_ids else "unknown",
    }