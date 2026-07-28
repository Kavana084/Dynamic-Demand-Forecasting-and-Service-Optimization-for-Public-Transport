"""
RAPTOR (Round-based Public Transit Optimized Router) Service
===========================================================

Replaces the Dijkstra + NetworkX-fallback pipeline with RAPTOR algorithm.
Key benefits:
  1. Bounded by construction: runs at most (MAX_TRANSFERS + 1) rounds
  2. Scans routes/trips directly instead of relaxing millions of edges
  3. Transfer count is a first-class dimension (round index k)
  4. Millisecond responses for city-scale networks
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import heapq
import bisect
from sqlalchemy.orm import Session
from app.database.models import GTFSStop, GTFSTrip, GTFSStopTime, Route
from app.logger import app_logger
import time
import math

INF = float("inf")

# --- Walking-transfer generation (distance-based, since GTFS has no transfers.txt) ---
WALK_TRANSFER_RADIUS_M = 300      # max walking distance to treat two stops as transferable
WALK_SPEED_MPS = 1.2              # conservative walking pace (~4.3 km/h) to account for real streets vs straight-line distance
MIN_TRANSFER_SEC = 60             # minimum buffer even for very close stops (crossing a street, finding the platform, etc.)
EARTH_RADIUS_M = 6371000.0



# ---------------------------------------------------------------------------
# Data model matching RAPTOR requirements
# ---------------------------------------------------------------------------

@dataclass
class Trip:
    """One scheduled run of a route (e.g. Bus 500D, 08:15 departure)."""
    trip_id: str
    # arrival/departure time (seconds since midnight) at each stop index
    arrivals: List[int]
    departures: List[int]


@dataclass
class RaptorRoute:
    """A route = an ordered sequence of stops + a set of trips on it."""
    route_id: str
    stops: List[str]                  # stop_ids in travel order
    stop_indices: Dict[str, int]     # stop_id -> index in stops list (precomputed)
    trips: List[Trip]                 # sorted by departure time at stops[0]


@dataclass
class TransferEdge:
    """A walking/interchange transfer between two nearby stops."""
    to_stop: str
    duration_sec: int


@dataclass
class TransitData:
    routes: Dict[str, RaptorRoute] = field(default_factory=dict)
    routes_by_stop: Dict[str, List[str]] = field(default_factory=dict)
    transfers: Dict[str, List[TransferEdge]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Data loading from database
# ---------------------------------------------------------------------------

def _parse_time_to_seconds(time_str: str) -> int:
    """Convert GTFS time string (HH:MM:SS) to seconds since midnight."""
    if not time_str:
        return 0
    try:
        parts = time_str.split(':')
        if len(parts) >= 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 3600 + minutes * 60
        else:
            return int(parts[0]) * 3600
    except (ValueError, IndexError):
        return 0


def check_repeated_stop_names(db: Session) -> Dict[str, List[str]]:
    """
    Check for repeated stop names within routes.
    
    Returns: Dict mapping route_id to list of repeated stop names found.
    Empty dict if no issues found.
    """
    app_logger.info("Checking for repeated stop names within routes...")
    
    # Get all routes
    routes = db.query(Route).all()
    
    repeated_by_route = {}
    
    for route in routes:
        # Get all stop times for this route's trips
        stop_times = db.query(
            GTFSStopTime.stop_id,
            GTFSStop.stop_name
        ).join(
            GTFSStop, GTFSStopTime.stop_id == GTFSStop.stop_id
        ).join(
            GTFSTrip, GTFSStopTime.trip_id == GTFSTrip.trip_id
        ).filter(
            GTFSTrip.route_id == route.route_id
        ).order_by(
            GTFSStopTime.stop_sequence
        ).all()
        
        # Check for repeated stop names
        stop_names = [st.stop_name for st in stop_times]
        seen = set()
        repeated = set()
        
        for name in stop_names:
            if name in seen:
                repeated.add(name)
            seen.add(name)
        
        if repeated:
            repeated_by_route[route.route_id] = list(repeated)
            app_logger.warning(
                f"Route {route.route_id} has repeated stop names: {repeated}"
            )
    
    if repeated_by_route:
        app_logger.error(
            f"Found {len(repeated_by_route)} routes with repeated stop names. "
            f"These should be split into separate route/pattern objects for RAPTOR."
        )
    else:
        app_logger.info("No repeated stop names found in routes.")
    
    return repeated_by_route


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_walk_transfers(
    stops: List[Tuple[str, float, float]],
    radius_m: float = WALK_TRANSFER_RADIUS_M,
    walk_speed_mps: float = WALK_SPEED_MPS,
) -> Dict[str, List["TransferEdge"]]:
    """
    Generate walking transfer edges between distinct stops that are within
    `radius_m` of each other, using a lat/lon grid to avoid an O(n^2) scan.

    There is no transfers.txt in this dataset, so this is the substitute:
    any two stops close enough to walk between become transfer-eligible,
    letting RAPTOR chain routes that don't share a literal stop_id.
    """
    t0 = time.time()

    # Cell size in degrees latitude for the requested radius (~111.32 km / degree).
    cell_deg = max(radius_m / 111320.0, 1e-6)

    # Bucket stops into a grid. Longitude cells are sized the same in degrees;
    # since we re-verify with a real haversine distance below, a slightly
    # too-generous longitude bucket (near the poles) only costs a few extra
    # comparisons, it can't cause a missed or incorrect transfer.
    grid: Dict[Tuple[int, int], List[Tuple[str, float, float]]] = {}
    valid_stops = [(sid, lat, lon) for sid, lat, lon in stops if lat is not None and lon is not None]

    for sid, lat, lon in valid_stops:
        cell = (int(lat // cell_deg), int(lon // cell_deg))
        grid.setdefault(cell, []).append((sid, lat, lon))

    transfers: Dict[str, List[TransferEdge]] = {}
    seen_pairs = set()

    for sid, lat, lon in valid_stops:
        cell_x, cell_y = int(lat // cell_deg), int(lon // cell_deg)
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                candidates.extend(grid.get((cell_x + dx, cell_y + dy), []))

        for other_id, other_lat, other_lon in candidates:
            if other_id == sid:
                continue
            pair = (sid, other_id) if sid < other_id else (other_id, sid)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            dist_m = _haversine_m(lat, lon, other_lat, other_lon)
            if dist_m <= radius_m:
                duration_sec = max(MIN_TRANSFER_SEC, int(dist_m / walk_speed_mps))
                transfers.setdefault(sid, []).append(TransferEdge(to_stop=other_id, duration_sec=duration_sec))
                transfers.setdefault(other_id, []).append(TransferEdge(to_stop=sid, duration_sec=duration_sec))

    elapsed = time.time() - t0
    n_edges = sum(len(v) for v in transfers.values())
    app_logger.info(
        f"Generated {n_edges} walking transfer edges across {len(transfers)} stops "
        f"(radius={radius_m:.0f}m) in {elapsed:.2f}s"
    )
    return transfers


def load_data(db: Session) -> TransitData:
    """
    Build TransitData from the database schema.
    
    Schema used:
    - Route: route_id, route_short_name, route_long_name
    - GTFSTrip: trip_id, route_id, service_id, trip_headsign
    - GTFSStopTime: trip_id, stop_id, arrival_time, departure_time, stop_sequence
    - GTFSStop: stop_id, stop_name, stop_lat, stop_lon
    
    IMPORTANT: Routes are split by actual stop pattern. If a route has trips with
    different stop sequences (branches, short-turns, express variants), each distinct
    pattern becomes a separate RaptorRoute entry with a pattern-specific ID.
    """
    app_logger.info("Loading transit data for RAPTOR...")
    t0 = time.time()
    
    data = TransitData()
    
    # Load all routes
    routes = db.query(Route).all()
    app_logger.info(f"Loaded {len(routes)} routes from database")
    
    # Bulk load all stop times to avoid N+1 queries
    all_stop_times = db.query(
        GTFSStopTime.trip_id,
        GTFSStopTime.stop_id,
        GTFSStopTime.arrival_time,
        GTFSStopTime.departure_time,
        GTFSStopTime.stop_sequence
    ).order_by(GTFSStopTime.trip_id, GTFSStopTime.stop_sequence).all()
    
    # Group stop times by trip_id
    stop_times_by_trip = {}
    for st in all_stop_times:
        if st.trip_id not in stop_times_by_trip:
            stop_times_by_trip[st.trip_id] = []
        stop_times_by_trip[st.trip_id].append(st)
    
    # Load all trips
    all_trips = db.query(GTFSTrip).all()
    trips_by_route = {}
    for trip in all_trips:
        if trip.route_id not in trips_by_route:
            trips_by_route[trip.route_id] = []
        trips_by_route[trip.route_id].append(trip)
    
    app_logger.info(f"Loaded {len(all_trips)} trips and {len(all_stop_times)} stop times")
    
    # Process each route, grouping trips by stop pattern
    pattern_route_count = 0
    for route in routes:
        trips = trips_by_route.get(route.route_id, [])
        if not trips:
            continue
        
        # Group trips by their actual stop pattern (ordered tuple of stop_ids)
        patterns = {}
        for trip in trips:
            trip_st = stop_times_by_trip.get(trip.trip_id, [])
            if not trip_st:
                continue
            
            # Create pattern key as ordered tuple of stop_ids
            pattern = tuple(st.stop_id for st in trip_st)
            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(trip)
        
        # Create a RaptorRoute for each distinct pattern
        for pattern, pattern_trips in patterns.items():
            stops = list(pattern)
            stop_indices = {stop_id: idx for idx, stop_id in enumerate(stops)}
            
            # Build trip objects with arrival/departure times
            trip_objects = []
            for trip in pattern_trips:
                trip_st = stop_times_by_trip.get(trip.trip_id, [])
                arrivals = [_parse_time_to_seconds(st.arrival_time) for st in trip_st]
                departures = [_parse_time_to_seconds(st.departure_time) for st in trip_st]
                
                # Validate that trip times match the pattern length
                if len(arrivals) != len(stops) or len(departures) != len(stops):
                    app_logger.warning(
                        f"Trip {trip.trip_id} has mismatched time arrays: "
                        f"stops={len(stops)}, arrivals={len(arrivals)}, departures={len(departures)}"
                    )
                    continue
                
                trip_objects.append(Trip(
                    trip_id=trip.trip_id,
                    arrivals=arrivals,
                    departures=departures
                ))
            
            # Sort trips by departure time at first stop
            trip_objects.sort(key=lambda t: t.departures[0] if t.departures else 0)
            
            # Create pattern-specific route ID
            if len(patterns) == 1:
                pattern_route_id = route.route_id
            else:
                import hashlib
                pattern_hash = hashlib.md5(str(pattern).encode()).hexdigest()[:8]
                pattern_route_id = f"{route.route_id}::{pattern_hash}"
            
            # Create RaptorRoute object
            data.routes[pattern_route_id] = RaptorRoute(
                route_id=pattern_route_id,
                stops=stops,
                stop_indices=stop_indices,
                trips=trip_objects
            )
            
            pattern_route_count += 1
            
            # Build routes_by_stop index
            for stop_id in stops:
                if stop_id not in data.routes_by_stop:
                    data.routes_by_stop[stop_id] = []
                data.routes_by_stop[stop_id].append(pattern_route_id)
    
    # Generate walking transfers from stop proximity (no transfers.txt in this dataset).
    # Any two distinct stops within WALK_TRANSFER_RADIUS_M become transfer-eligible,
    # so RAPTOR can chain routes that don't share a literal stop_id.
    all_stops = db.query(GTFSStop.stop_id, GTFSStop.stop_lat, GTFSStop.stop_lon).all()
    data.transfers = build_walk_transfers(
        [(s.stop_id, s.stop_lat, s.stop_lon) for s in all_stops]
    )
    
    elapsed = time.time() - t0
    app_logger.info(
        f"TransitData loaded: {len(routes)} base routes -> {pattern_route_count} pattern routes, "
        f"{sum(len(r.trips) for r in data.routes.values())} trips, "
        f"loaded in {elapsed:.2f}s"
    )
    
    return data


# Global cache for TransitData
_transit_data_cache: Optional[TransitData] = None
_transit_data_lock = None


def get_transit_data(db: Session, force_reload: bool = False) -> TransitData:
    """
    Get cached TransitData or load it fresh.
    
    NOTE: The process-global cache should be invalidated automatically after a GTFS
    reload/sync operation. Call get_transit_data(db, force_reload=True) after any
    data update to ensure the cache reflects the latest GTFS data.
    """
    global _transit_data_cache, _transit_data_lock
    
    if _transit_data_lock is None:
        import threading
        _transit_data_lock = threading.Lock()
    
    if not force_reload and _transit_data_cache is not None:
        return _transit_data_cache
    
    with _transit_data_lock:
        if not force_reload and _transit_data_cache is not None:
            return _transit_data_cache
        
        _transit_data_cache = load_data(db)
        return _transit_data_cache


# ---------------------------------------------------------------------------
# Startup warmup
# ---------------------------------------------------------------------------

def warm_raptor_cache(db: Session) -> Dict[str, Any]:
    """
    Preload TransitData (routes, patterns, trips, walk-transfers) into the
    process-global cache at startup.

    Unlike the old Dijkstra-based warmup — which precomputed and cached
    individual hub-to-hub *paths* because each Dijkstra call could take
    seconds — RAPTOR answers a live query in well under a second (see
    plan_trip_raptor benchmarks: ~60-200ms on this dataset), so there is
    no need to precompute per-pair results. The only expensive, worth-
    -caching step is the one-time load of the transit graph itself.
    """
    t0 = time.time()
    data = get_transit_data(db, force_reload=False)
    elapsed = time.time() - t0
    stats = {
        "pattern_routes": len(data.routes),
        "stops_with_routes": len(data.routes_by_stop),
        "stops_with_transfers": len(data.transfers),
        "elapsed_sec": round(elapsed, 2),
    }
    app_logger.info("raptor cache warmup completed", extra={"extra_data": stats})
    return stats


def start_raptor_warmup() -> bool:
    """Load RAPTOR's TransitData in a background thread so the first live
    request doesn't pay the ~10s load cost. Safe to call once per process."""
    global _raptor_warmup_started
    if _raptor_warmup_started:
        return False
    _raptor_warmup_started = True

    import threading

    def _run():
        from app.database.connection import SessionLocal
        db = SessionLocal()
        try:
            warm_raptor_cache(db)
        except Exception as e:
            app_logger.warning(f"RAPTOR warmup failed: {e}", exc_info=True)
        finally:
            db.close()

    threading.Thread(target=_run, name="raptor-cache-warmup", daemon=True).start()
    app_logger.info("RAPTOR warmup thread started.")
    return True


_raptor_warmup_started = False

@dataclass
class Leg:
    """One leg of the resulting journey, for reconstruction/display."""
    kind: str            # "ride" or "walk"
    route_id: Optional[str]
    from_stop: str
    to_stop: str
    depart_sec: Optional[int]
    arrive_sec: int


def _earliest_trip_after(route: Route, stop_idx: int, not_before: int) -> Optional[Trip]:
    """
    Binary search for earliest trip departing at or after not_before.
    
    Trips are pre-sorted by departure time at stop index 0, but we need
    to find the earliest trip that departs at stop_idx >= not_before.
    """
    # Extract departure times at this stop index
    departures = [trip.departures[stop_idx] for trip in route.trips]
    
    # Binary search for the first departure >= not_before
    idx = bisect.bisect_left(departures, not_before)
    
    if idx < len(route.trips):
        return route.trips[idx]
    return None


def raptor(
    data: TransitData,
    source: str,
    target: str,
    start_time_sec: int,
    max_transfers: int = 3,
    max_rounds_time_budget_ms: Optional[int] = None,
) -> Optional[Tuple[int, List[Leg]]]:
    """
    Earliest-arrival RAPTOR bounded to `max_transfers` transfers.
    
    Returns (arrival_time_sec, journey_legs) for the best journey found
    within the transfer budget, or None if no such journey exists.
    """
    t0 = time.monotonic()

    n_rounds = max_transfers + 1  # round 0 = no transfers, ..., round k = k transfers

    # earliest known arrival time at each stop, per round
    tau: List[Dict[str, int]] = [dict() for _ in range(n_rounds + 1)]
    tau_best: Dict[str, int] = {}  # best arrival at stop across all rounds so far

    # for journey reconstruction: parent[k][stop] = (Leg)
    parent: List[Dict[str, Leg]] = [dict() for _ in range(n_rounds + 1)]

    tau[0][source] = start_time_sec
    tau_best[source] = start_time_sec

    marked_stops = {source}

    for k in range(1, n_rounds + 1):
        if max_rounds_time_budget_ms is not None:
            elapsed = (time.monotonic() - t0) * 1000
            if elapsed > max_rounds_time_budget_ms:
                app_logger.warning(
                    f"RAPTOR time budget {max_rounds_time_budget_ms}ms exceeded - "
                    f"this indicates structural issues with route data"
                )
                break  # fail fast — return best found so far, or None

        # --- Stage 1: gather routes that pass through any marked stop ---
        Q: Dict[str, int] = {}
        for stop in marked_stops:
            for route_id in data.routes_by_stop.get(stop, []):
                route = data.routes[route_id]
                # Use precomputed stop index instead of .index()
                stop_idx = route.stop_indices.get(stop)
                if stop_idx is None:
                    continue
                if route_id not in Q or stop_idx < Q[route_id]:
                    Q[route_id] = stop_idx

        marked_stops = set()

        # --- Stage 2: traverse each candidate route once, scanning forward ---
        for route_id, board_idx in Q.items():
            route = data.routes[route_id]
            current_trip: Optional[Trip] = None
            board_stop: Optional[str] = None
            board_time: Optional[int] = None

            for idx in range(board_idx, len(route.stops)):
                stop = route.stops[idx]

                if current_trip is not None:
                    arr = current_trip.arrivals[idx]
                    if arr < tau_best.get(stop, INF) and arr < tau_best.get(target, INF):
                        tau[k][stop] = arr
                        tau_best[stop] = arr
                        parent[k][stop] = Leg(
                            kind="ride",
                            route_id=route_id,
                            from_stop=board_stop,
                            to_stop=stop,
                            depart_sec=board_time,
                            arrive_sec=arr,
                        )
                        marked_stops.add(stop)

                # Can we catch an earlier/better trip at this stop from round k-1?
                prev_arrival = tau[k - 1].get(stop, INF)
                if current_trip is None or prev_arrival <= (
                    current_trip.departures[idx] if idx < len(route.stops) else INF
                ):
                    candidate_trip = _earliest_trip_after(route, idx, prev_arrival)
                    if candidate_trip is not None and (
                        current_trip is None
                        or candidate_trip.departures[idx] < current_trip.departures[idx]
                    ):
                        current_trip = candidate_trip
                        board_stop = stop
                        board_time = candidate_trip.departures[idx]

        # --- Stage 3: foot transfers from stops improved this round ---
        for stop in list(marked_stops):
            arrival = tau[k].get(stop)
            if arrival is None:
                continue
            for edge in data.transfers.get(stop, []):
                new_arr = arrival + edge.duration_sec
                if new_arr < tau_best.get(edge.to_stop, INF):
                    tau[k][edge.to_stop] = new_arr
                    tau_best[edge.to_stop] = new_arr
                    parent[k][edge.to_stop] = Leg(
                        kind="walk",
                        route_id=None,
                        from_stop=stop,
                        to_stop=edge.to_stop,
                        depart_sec=arrival,
                        arrive_sec=new_arr,
                    )
                    marked_stops.add(edge.to_stop)

        if not marked_stops:
            break  # nothing new improved -> converged early

    if target not in tau_best:
        return None  # correctly and quickly: no journey within max_transfers

    # reconstruct journey by walking backward through the best round found
    best_k = min(
        (k for k in range(n_rounds + 1) if tau[k].get(target) == tau_best[target]),
        default=None,
    )
    legs: List[Leg] = []
    stop = target
    k = best_k
    while stop != source and k is not None and k >= 0:
        leg = parent[k].get(stop)
        if leg is None:
            break
        legs.append(leg)
        stop = leg.from_stop
        # Only decrement k for ride legs - walk legs are in the same round as the ride that fed them
        if leg.kind == "ride":
            k -= 1
    legs.reverse()

    return tau_best[target], legs


def plan_trip_raptor(
    db: Session,
    source_id: str,
    target_id: str,
    start_time_sec: int,
    max_transfers: int = 3
) -> Dict[str, Any]:
    """
    Drop-in replacement for current plan_trip() path using RAPTOR.
    
    Returns dict matching current API contract:
    - On success: {"status_code": 200, "arrival_time_sec": ..., "legs": [...]}
    - On failure: {"status_code": 404, "detail": "No viable route found..."}
    """
    data = get_transit_data(db)
    
    result = raptor(
        data, source_id, target_id, start_time_sec,
        max_transfers=max_transfers,
        max_rounds_time_budget_ms=2000,  # hard safety net
    )
    
    if result is None:
        return {
            "status_code": 404,
            "detail": f"No viable route found with {max_transfers} or fewer transfers.",
        }
    
    arrival_time, legs = result
    return {
        "status_code": 200,
        "arrival_time_sec": arrival_time,
        "transfer_count": sum(1 for l in legs if l.kind == "ride") - 1,
        "legs": [
            {
                "kind": l.kind,
                "route_id": l.route_id,
                "from": l.from_stop,
                "to": l.to_stop,
                "depart": l.depart_sec,
                "arrive": l.arrive_sec,
            }
            for l in legs
        ],
    }