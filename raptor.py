"""
RAPTOR (Round-based Public Transit Optimized Router)
=====================================================

Purpose-built replacement for the Dijkstra + NetworkX-fallback pipeline
seen in the transit_system logs. Key differences from the current setup:

  1. Bounded by construction: it runs at most (MAX_TRANSFERS + 1) rounds,
     so it can never explore a 7-transfer path when the limit is 3 -- it
     simply won't find one, and it won't burn 450s finding out.
  2. Scans routes/trips directly instead of relaxing millions of edges,
     so per-round cost is proportional to (routes touched x stops per
     route), not (edges explored).
  3. Transfer count is a first-class dimension (the round index k),
     not a post-hoc check on a path that was already fully computed.

This is a clean, from-scratch reference implementation (the classic
Delling/Pyrga/Werneck RAPTOR, simplified). It is NOT wired to your
database -- you need to fill in `load_data()` (or equivalent) to build
the Route/Trip objects from your existing schema (routes, stops,
GTFS-style trips, etc).

Complexity: O(rounds x (routes_serving_marked_stops + transfers)),
which in practice is milliseconds for city-scale networks, versus the
edges_explored in the millions your logs show for plain Dijkstra.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import heapq

INF = float("inf")


# ---------------------------------------------------------------------------
# Data model — adapt these to your actual schema (route table, trip table,
# stop_times, transfers table, etc). The fields below are the minimum
# RAPTOR needs.
# ---------------------------------------------------------------------------

@dataclass
class Trip:
    """One scheduled run of a route (e.g. Bus 500D, 08:15 departure)."""
    trip_id: str
    # arrival/departure time (seconds since midnight) at each stop index
    # along the route's stop sequence. Same length as Route.stops.
    arrivals: List[int]
    departures: List[int]


@dataclass
class Route:
    """A route = an ordered sequence of stops + a set of trips on it.

    IMPORTANT: stops must be in a single consistent physical order.
    If a real-world route branches or loops, split it into separate
    Route objects per pattern (this is standard GTFS practice and is
    also almost certainly why your log showed 'Repeated stop names
    detected' -- a route/path was allowed to revisit stops).
    """
    route_id: str
    stops: List[str]                  # stop_ids in travel order
    trips: List[Trip]                 # sorted by departure time at stops[0]


@dataclass
class TransferEdge:
    """A walking/interchange transfer between two nearby stops."""
    to_stop: str
    duration_sec: int


@dataclass
class TransitData:
    routes: Dict[str, Route] = field(default_factory=dict)
    # stop_id -> list of route_ids serving that stop
    routes_by_stop: Dict[str, List[str]] = field(default_factory=dict)
    # stop_id -> list of TransferEdge (walking interchanges)
    transfers: Dict[str, List[TransferEdge]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# RAPTOR core
# ---------------------------------------------------------------------------

@dataclass
class Leg:
    """One leg of the resulting journey, for reconstruction/display."""
    kind: str            # "ride" or "walk"
    route_id: Optional[str]
    from_stop: str
    to_stop: str
    depart_sec: Optional[int]
    arrive_sec: int


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

    This intentionally mirrors your API contract: if nothing is found
    within max_transfers, it returns None fast (milliseconds), the same
    semantic your current code produces after 458 seconds.
    """
    import time
    t0 = time.monotonic()

    n_rounds = max_transfers + 1  # round 0 = no transfers, ..., round k = k transfers

    # earliest known arrival time at each stop, per round
    # tau[k][stop] = earliest arrival at `stop` using <= k trips (i.e. k-1 transfers)
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
                break  # fail fast — return best found so far, or None

        # --- Stage 1: gather routes that pass through any marked stop ---
        # Q[route_id] = earliest stop index on that route we need to board from
        Q: Dict[str, int] = {}
        for stop in marked_stops:
            for route_id in data.routes_by_stop.get(stop, []):
                route = data.routes[route_id]
                stop_idx = route.stops.index(stop)  # precompute this in real impl
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
            break  # nothing new improved -> converged early, no need to keep going

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
        k -= 1
    legs.reverse()

    return tau_best[target], legs


def _earliest_trip_after(route: Route, stop_idx: int, not_before: int) -> Optional[Trip]:
    """
    Binary-search-friendly: trips should be pre-sorted by departure time
    at each stop. Returns the earliest trip departing `stop_idx` at or
    after `not_before`. Replace with a real binary search once trips are
    sorted in your data layer -- linear scan here for clarity only.
    """
    best = None
    for trip in route.trips:
        dep = trip.departures[stop_idx]
        if dep >= not_before:
            if best is None or dep < best.departures[stop_idx]:
                best = trip
    return best


# ---------------------------------------------------------------------------
# Example usage / integration sketch
# ---------------------------------------------------------------------------

def plan_trip_raptor(data: TransitData, source_id: str, target_id: str,
                      start_time_sec: int, max_transfers: int = 3):
    """
    Drop-in replacement for your current plan_trip() path.
    Mirrors the 404 semantics your API already returns, but fast.
    """
    result = raptor(
        data, source_id, target_id, start_time_sec,
        max_transfers=max_transfers,
        max_rounds_time_budget_ms=2000,  # hard safety net, should never trigger
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
