"""
routing_service.py — Transfer-Aware Transit Routing Engine
===========================================================
Key improvements over previous version:
  1. TRANSFER_PENALTY additive cost on every route-switch edge
  2. Direct-route fast path (try single-route before composite)
  3. MAX_TRANSFERS = 3 enforcement post-pathfinding
  4. Destination-as-transfer bug fixed
  5. Dynamic route efficiency formula (no hardcoded values)
"""

import copy
import math
import threading
import time
import networkx as nx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.database.models import GTFSStop, GTFSTrip, GTFSStopTime
from app.logger import app_logger
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import OrderedDict, defaultdict, deque


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

TRANSFER_PENALTY  = 15.0   # Increased penalty for route switches (was 8.0)
MAX_TRANSFERS     = 3      # Paths with more switches are rejected
AVG_STOP_DIST_KM  = 1.0   # Fallback distance when coordinates are missing
BACKTRACK_PENALTY = 50.0   # Heavy penalty for backward traversal
MAX_ROUTE_LENGTH  = 50     # Maximum stops in a route (prevents excessive sequences)

# Optimization layer is disabled for production routing consistency
USE_BEST_EDGE_INDEX = False

# ─────────────────────────────────────────────────────────────────────────────
# Custom exception
# ─────────────────────────────────────────────────────────────────────────────

class RoutingValidationError(Exception):
    """Raised when a generated path contains repeated stop_ids."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Haversine distance
# ─────────────────────────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    try:
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Graph cache
# ─────────────────────────────────────────────────────────────────────────────

transit_graph_cache: Optional[nx.MultiDiGraph] = None
route_cache: "OrderedDict[Tuple[str, str, int], Dict[str, Any]]" = OrderedDict()
ROUTE_CACHE_TTL_SECONDS = 600
ROUTE_CACHE_MAX_SIZE = 1000
route_cache_hits = 0
route_cache_misses = 0
route_cache_evictions = 0
HUB_STOPS: List[str] = [
    "29506",  # Ananda Rao Circle / Majestic corridor
    "22890",  # 18th Main Jayanagara / BTM-side example
    "20940",  # KR Market
    "21172",  # Shivajinagara Bus Station
]
HUB_STOP_SET: Set[str] = set(HUB_STOPS)
hub_cache: Dict[Tuple[str, str], List[str]] = {}
COMMON_FREQUENT_ROUTES: List[Tuple[str, str]] = [
    ("29506", "22950"),
    ("22950", "29506"),
    ("29506", "22890"),
    ("22890", "29506"),
    ("21630", "22896"),
    ("22896", "21630"),
    ("29506", "20940"),
    ("20940", "29506"),
    ("29506", "21172"),
    ("21172", "29506"),
    ("22890", "20940"),
    ("20940", "22890"),
    ("22890", "21172"),
    ("21172", "22890"),
    ("20940", "21172"),
    ("21172", "20940"),
    ("21630", "29506"),
    ("29506", "21630"),
    ("22950", "20940"),
    ("22950", "21172"),
]
ROUTE_WARMUP_BUS_CAPACITY = 60
_routing_warmup_started = False


def invalidate_transit_graph_cache() -> None:
    """Force a fresh graph rebuild on the next request."""
    global transit_graph_cache, route_cache, hub_cache, _routing_warmup_started
    transit_graph_cache = None
    route_cache = OrderedDict()
    hub_cache = {}
    _routing_warmup_started = False
    app_logger.info("Transit graph cache invalidated.")


def _get_route_cache_key(source_id: str, destination_id: str, bus_capacity: int) -> Tuple[str, str, int]:
    return (str(source_id), str(destination_id), int(bus_capacity))


def _is_hub_stop(stop_id: str) -> bool:
    return str(stop_id) in HUB_STOP_SET


def _get_hub_cache_key(source_id: str, destination_id: str) -> Tuple[str, str]:
    return (str(source_id), str(destination_id))


def _get_cached_hub_path(
    G: nx.MultiDiGraph,
    source_id: str,
    destination_id: str,
) -> Optional[List[str]]:
    cache_key = _get_hub_cache_key(source_id, destination_id)
    cached_path = hub_cache.get(cache_key)
    if not cached_path or len(cached_path) < 2:
        return None
    if cached_path[0] != str(source_id) or cached_path[-1] != str(destination_id):
        hub_cache.pop(cache_key, None)
        return None
    for i in range(len(cached_path) - 1):
        if not G.has_edge(cached_path[i], cached_path[i + 1]):
            hub_cache.pop(cache_key, None)
            return None
    return list(cached_path)


def _prune_expired_route_cache() -> None:
    expired_keys: List[Tuple[str, str, int]] = []
    now = time.time()
    for cache_key, entry in route_cache.items():
        timestamp = entry.get("timestamp", 0.0)
        if (now - timestamp) > ROUTE_CACHE_TTL_SECONDS:
            expired_keys.append(cache_key)

    for cache_key in expired_keys:
        route_cache.pop(cache_key, None)


def _get_route_cache_stats() -> Dict[str, Any]:
    total_requests = route_cache_hits + route_cache_misses
    hit_ratio = (route_cache_hits / total_requests) if total_requests > 0 else 0.0
    return {
        "cache_size": len(route_cache),
        "cache_hit_ratio": round(hit_ratio, 4),
        "eviction_count": route_cache_evictions,
    }


def _get_cached_route(
    source_id: str,
    destination_id: str,
    bus_capacity: int,
) -> Optional[Dict[str, Any]]:
    if transit_graph_cache is None or not isinstance(transit_graph_cache, nx.MultiDiGraph):
        return None

    _prune_expired_route_cache()
    cache_key = _get_route_cache_key(source_id, destination_id, bus_capacity)
    entry = route_cache.get(cache_key)
    if not entry:
        return None

    response = entry.get("response")
    if not isinstance(response, dict):
        route_cache.pop(cache_key, None)
        return None

    route_cache.move_to_end(cache_key)
    return copy.deepcopy(response)


def _store_cached_route(
    source_id: str,
    destination_id: str,
    bus_capacity: int,
    response: Dict[str, Any],
) -> None:
    global route_cache_evictions
    _prune_expired_route_cache()
    cache_key = _get_route_cache_key(source_id, destination_id, bus_capacity)
    if cache_key in route_cache:
        route_cache.pop(cache_key, None)

    while len(route_cache) >= ROUTE_CACHE_MAX_SIZE:
        route_cache.popitem(last=False)
        route_cache_evictions += 1

    route_cache[cache_key] = {
        "timestamp": time.time(),
        "response": copy.deepcopy(response),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────

def _best_edge(G: nx.MultiDiGraph, u: str, v: str, current_route: Optional[str] = None) -> Dict[str, Any]:
    """
    For a MultiDiGraph edge pair return the edge with the smallest distance_km,
    or the edge matching current_route if provided.
    """
    edges = G.get_edge_data(u, v)
    if not edges:
        return {}

    # If called with a plain DiGraph-like mapping (attributes dict), just return it.
    if isinstance(edges, dict) and "distance_km" in edges:
        return edges  # type: ignore[return-value]

    if current_route:
        for data in edges.values():
            if data.get("route_id") == current_route:
                return data

    # MultiDiGraph returns {edge_key: attr_dict}
    return min(
        edges.values(),
        key=lambda e: e.get("distance_km", float("inf")),
    )


def build_best_edge_index(G: nx.MultiDiGraph) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Scan all edges once and store the best edge per (u, v) pair.

    The "best" edge is defined as the one with the smallest distance_km.
    This helper is retained only for optional offline benchmarking/tests and is
    not part of production routing.
    """
    best_edge_index: Dict[Tuple[str, str], Dict[str, Any]] = {}

    # MultiDiGraph supports (u, v, key, data) iteration; data is the edge-attr dict.
    for u, v, k, data in G.edges(keys=True, data=True):
        pair = (str(u), str(v))
        prev = best_edge_index.get(pair)
        if prev is None or data.get("distance_km", float("inf")) < prev.get("distance_km", float("inf")):
            best_edge_index[pair] = data

    return best_edge_index


def _canonicalize_stop_id(db: Session, stop_name: str) -> str:
    """
    For stops with identical names, select the stop_id with highest occurrence count in gtfs_stop_times.
    
    Args:
        db: Database session
        stop_name: Stop name to canonicalize
        
    Returns:
        The stop_id with highest occurrence count
    """
    from sqlalchemy import func
    
    # Query all stop_ids with this name and their occurrence counts in stop_times
    stop_counts = db.query(
        GTFSStop.stop_id,
        func.count(GTFSStopTime.stop_id).label("occurrence_count")
    ).join(
        GTFSStopTime, GTFSStop.stop_id == GTFSStopTime.stop_id
    ).filter(
        GTFSStop.stop_name == stop_name
    ).group_by(
        GTFSStop.stop_id
    ).all()
    
    if not stop_counts:
        return None
    
    # Sort by occurrence count descending and return the first
    stop_counts.sort(key=lambda x: x[1], reverse=True)
    
    # Log canonicalization decision
    if len(stop_counts) > 1:
        candidates = [{"stop_id": s[0], "count": s[1]} for s in stop_counts]
        app_logger.info(
            "STOP_CANONICALIZATION",
            extra={
                "extra_data": {
                    "stop_name": stop_name,
                    "candidates": candidates,
                    "selected_stop_id": stop_counts[0][0],
                    "selected_count": stop_counts[0][1]
                }
            }
        )
    
    return stop_counts[0][0]


_graph_lock = threading.Lock()

def build_transit_graph(db: Session) -> nx.MultiDiGraph:
    """

    Node key  : str(stop_id)
    Edge attrs: route_id (str), distance_km (float), weight (float), stop_sequence (int)

    Edge weight = distance_km + TRANSFER_PENALTY when route switches.
    Transfer detection is done during pathfinding (not at graph build time)
    because a single edge carries one route_id; the switch cost is applied
    by the modified Dijkstra wrapper that tracks current_route.

    Self-loop and consecutive-duplicate elimination preserved.
    stop_sequence is now stored to enable directional route constraints.
    """
    global transit_graph_cache
    if transit_graph_cache is not None:
        return transit_graph_cache

    with _graph_lock:
        if transit_graph_cache is not None:
            return transit_graph_cache

    # MultiDiGraph is required to preserve parallel edges between the same two stops.
    # In GTFS, multiple routes can serve the same stop-to-stop hop; collapsing to a
    # simple DiGraph discards route alternatives and inflates transfer counts.
    G = nx.MultiDiGraph()

    # 1. Nodes
    stops = db.query(GTFSStop).all()
    for s in stops:
        G.add_node(str(s.stop_id),
                   name=s.stop_name,
                   lat=s.stop_lat,
                   lon=s.stop_lon)

    # 2. Trip → route_id lookup
    trips = db.query(GTFSTrip.trip_id, GTFSTrip.route_id).all()
    trip_route_map: Dict[str, str] = {t.trip_id: t.route_id for t in trips}

    # 3. Collect stop-times per trip
    stop_times_raw = db.query(
        GTFSStopTime.trip_id,
        GTFSStopTime.stop_id,
        GTFSStopTime.stop_sequence
    ).all()

    trips_stops: Dict[str, list] = defaultdict(list)
    for row in stop_times_raw:
        trips_stops[row.trip_id].append((row.stop_sequence, str(row.stop_id)))

    # 4. Add directed edges with stop_sequence
    stats = {"added": 0, "self_loop": 0, "no_coords": 0, "duplicate": 0}
    dist_cache = {}
    added_edges = set()

    for trip_id, stops_list in trips_stops.items():
        stops_list.sort(key=lambda x: x[0])

        # Remove consecutive duplicates within a trip
        deduped: list = []
        for seq, sid in stops_list:
            if not deduped or deduped[-1][1] != sid:
                deduped.append((seq, sid))

        r_id = trip_route_map.get(trip_id, "UNKNOWN")

        for i in range(len(deduped) - 1):
            curr_seq, curr_stop = deduped[i]
            nxt_seq, nxt_stop  = deduped[i + 1]

            if curr_stop == nxt_stop:
                stats["self_loop"] += 1
                continue

            n1 = G.nodes.get(curr_stop, {})
            n2 = G.nodes.get(nxt_stop, {})
            lat1, lon1 = n1.get("lat"), n1.get("lon")
            lat2, lon2 = n2.get("lat"), n2.get("lon")

            if None in (lat1, lon1, lat2, lon2):
                stats["no_coords"] += 1
                continue

            pair = (curr_stop, nxt_stop)
            if pair in dist_cache:
                distance_km = dist_cache[pair]
            else:
                distance_km = max(0.01, haversine(lat1, lon1, lat2, lon2))
                dist_cache[pair] = distance_km

            # Dedup key: one edge per (stop pair, route) — NOT one per trip.
            # Two trips on the same route between the same two stops carry
            # identical route_id/distance and are indistinguishable for
            # routing purposes. Without this, a route with N trips/day
            # inserted N parallel MultiDiGraph edges for every hop, which
            # multiplied edges_explored during Dijkstra by ~N (up to ~350x
            # on this dataset's busiest routes) with zero pathfinding benefit.
            edge_key = (curr_stop, nxt_stop, r_id)
            if edge_key in added_edges:
                stats["duplicate"] += 1
                continue
            added_edges.add(edge_key)

            # Base weight is distance only; transfer penalty applied during search
            # Store stop_sequence to enable directional constraints
            G.add_edge(
                curr_stop,
                nxt_stop,
                route_id=r_id,
                distance_km=distance_km,
                weight=distance_km,
                stop_sequence=curr_seq,  # Store sequence for backward traversal detection
            )
            stats["added"] += 1

    if USE_BEST_EDGE_INDEX:
        try:
            best_edge_index = build_best_edge_index(G)
            app_logger.info(
                "best_edge_index benchmark",
                extra={
                    "extra_data": {
                        "pairs_indexed": len(best_edge_index),
                        "optimization_layer_enabled": True,
                        "production_routing_affected": False,
                    }
                },
            )
        except Exception as e:
            app_logger.warning(f"best_edge_index benchmark failed (ignored): {e}")

    transit_graph_cache = G
    app_logger.info(
        "build_transit_graph completed",
        extra={
            "extra_data": {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "multidigraph_active": isinstance(G, nx.MultiDiGraph),
                "routing_mode": "deterministic",
                "added": stats["added"],
                "self_loop": stats["self_loop"],
                "no_coords": stats["no_coords"],
                "duplicate": stats["duplicate"],
            }
        },
    )
    return G


# ─────────────────────────────────────────────────────────────────────────────
# Graph diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def get_graph_diagnostics(db: Session) -> Dict[str, Any]:
    """Return a full diagnostic report of the transit graph."""
    G = build_transit_graph(db)

    self_loops = list(nx.selfloop_edges(G))
    disconnected = [n for n in G.nodes() if G.degree(n) == 0]
    sccs = list(nx.strongly_connected_components(G))
    cycle_sccs = [s for s in sccs if len(s) > 1]
    nodes_in_cycles: List[str] = []
    for scc in cycle_sccs:
        nodes_in_cycles.extend(list(scc))

    name_to_ids: Dict[str, List[str]] = {}
    for node_id, data in G.nodes(data=True):
        name = data.get("name") or ""
        name_to_ids.setdefault(name, []).append(node_id)
    duplicate_names = {n: ids for n, ids in name_to_ids.items() if len(ids) > 1}

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "self_loop_count": len(self_loops),
        "self_loop_sample": [(a, b) for a, b in self_loops[:20]],
        "disconnected_node_count": len(disconnected),
        "scc_count": len(sccs),
        "sccs_with_cycles": len(cycle_sccs),
        "nodes_in_cycles_count": len(nodes_in_cycles),
        "nodes_in_cycles_sample": nodes_in_cycles[:30],
        "duplicate_stop_name_count": len(duplicate_names),
        "duplicate_stop_names_sample": dict(list(duplicate_names.items())[:20]),
    }


def get_graph_statistics(db: Session) -> Dict[str, Any]:
    """
    Return profiling statistics about the transit graph for the performance audit.

    Collects:
    - Total nodes and edges (MultiDiGraph — includes all parallel edges)
    - Unique (stop_A, stop_B) pair count
    - Unique (stop_A, stop_B, route_id) triple count
    - Parallelism distribution: max / mean parallel edges per stop pair
    - Top-10 routes by edge count
    - Parallelism factor (total_edges / unique_pairs)

    These numbers explain why N stops → M >> N^2 edges.
    """
    G = build_transit_graph(db)

    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    # Accumulate per (u, v) pair stats
    pair_edge_counts: Dict[Tuple[str, str], int]    = defaultdict(int)
    pair_routes:      Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    route_edge_counts: Dict[str, int]                 = defaultdict(int)

    for u, v, data in G.edges(data=True):
        pair = (u, v)
        r    = data.get("route_id", "UNKNOWN")
        pair_edge_counts[pair] += 1
        pair_routes[pair].add(r)
        route_edge_counts[r]  += 1

    unique_pairs         = len(pair_edge_counts)
    unique_route_triples = sum(len(routes) for routes in pair_routes.values())

    counts       = list(pair_edge_counts.values())
    max_parallel = max(counts, default=0)
    mean_parallel = round(sum(counts) / len(counts), 2) if counts else 0.0
    pairs_with_multi = sum(1 for c in counts if c > 1)
    parallelism_factor = round(total_edges / unique_pairs, 2) if unique_pairs else 0.0

    top_routes = sorted(route_edge_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    app_logger.info(
        "graph_statistics",
        extra={
            "extra_data": {
                "total_nodes":          total_nodes,
                "total_edges":          total_edges,
                "unique_stop_pairs":    unique_pairs,
                "unique_route_triples": unique_route_triples,
                "max_parallel_edges":   max_parallel,
                "mean_parallel_edges":  mean_parallel,
                "parallelism_factor":   parallelism_factor,
            }
        },
    )

    return {
        "total_nodes":                total_nodes,
        "total_edges":                total_edges,
        "unique_stop_pairs":          unique_pairs,
        "unique_route_triples":       unique_route_triples,
        "max_parallel_edges_per_pair": max_parallel,
        "mean_parallel_edges_per_pair": mean_parallel,
        "pairs_with_multiple_edges":  pairs_with_multi,
        "parallelism_factor":         parallelism_factor,
        "top_10_routes_by_edge_count": [
            {"route_id": r, "edge_count": c} for r, c in top_routes
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Path validation
# ─────────────────────────────────────────────────────────────────────────────

def detect_repeated_stop_ids(path: List[str]) -> List[str]:
    """Return stop IDs that appear more than once in the path."""
    seen = set()
    dups = set()
    for s in path:
        if s in seen:
            dups.add(s)
        seen.add(s)
    return list(dups)

def detect_repeated_edges(path: List[str]) -> List[Tuple[str, str]]:
    """Return directed edges (u, v) that are traversed more than once."""
    if len(path) < 2:
        return []
    edges = [(path[i], path[i+1]) for i in range(len(path) - 1)]
    seen = set()
    dups = set()
    for e in edges:
        if e in seen:
            dups.add(e)
        seen.add(e)
    return list(dups)

def detect_backtracking(path: List[str]) -> List[Tuple[str, str, str]]:
    """Return segments where the path goes A -> B -> A."""
    if len(path) < 3:
        return []
    backtracks = []
    for i in range(len(path) - 2):
        if path[i] == path[i+2]:
            backtracks.append((path[i], path[i+1], path[i+2]))
    return backtracks

def detect_cycles(path: List[str]) -> List[List[str]]:
    """Return subpaths that form a cycle A -> ... -> A."""
    cycles = []
    seen = {}
    for i, s in enumerate(path):
        if s in seen:
            # Cycle from seen[s] to i
            cycles.append(path[seen[s]:i+1])
        seen[s] = i
    return cycles

def detect_repeated_corridors(path: List[str]) -> List[str]:
    """Return stops that are visited, left, and then visited again (essentially same as repeated stops)."""
    return detect_repeated_stop_ids(path)


def validate_route(path: List[str], G: nx.MultiDiGraph, max_length: int = 150) -> None:
    """
    Comprehensive route validation with multiple checks:
    1. No duplicate stop_ids
    2. No excessive length
    3. Geographic monotonic progression
    4. No backtracking
    5. Valid endpoints
    """
    if len(path) > max_length:
        raise RoutingValidationError(
            f"Route exceeds maximum allowed length of {max_length} stops."
        )

    if len(path) != len(set(path)):
        seen: set = set()
        dups: List[str] = []
        for s in path:
            if s in seen:
                dups.append(s)
            seen.add(s)
        raise RoutingValidationError(
            f"Route contains repeated stop IDs: {dups}"
        )
    
    # Check for geographic monotonic progression
    if len(path) >= 3:
        dest_node = G.nodes.get(path[-1], {})
        dest_lat = dest_node.get("lat")
        dest_lon = dest_node.get("lon")
        
        if dest_lat is not None and dest_lon is not None:
            prev_dist_to_dest = None
            for i in range(len(path) - 1):
                curr_node = G.nodes.get(path[i], {})
                curr_lat = curr_node.get("lat")
                curr_lon = curr_node.get("lon")
                
                if curr_lat is not None and curr_lon is not None:
                    curr_dist = haversine(curr_lat, curr_lon, dest_lat, dest_lon)
                    
                    if prev_dist_to_dest is not None:
                        # Allow small tolerance for route curvature
                        if curr_dist > prev_dist_to_dest + 2.0:  # 2km tolerance
                            app_logger.warning(
                                f"Non-monotonic progression detected at stop {i}: "
                                f"distance to destination increased from {prev_dist_to_dest:.2f}km "
                                f"to {curr_dist:.2f}km"
                            )
                    
                    prev_dist_to_dest = curr_dist
    
    # Check for backtracking within same route
    current_route = None
    route_sequence = {}
    for i in range(len(path) - 1):
        edge = _best_edge(G, path[i], path[i + 1])
        route_id = edge.get("route_id")
        stop_seq = edge.get("stop_sequence", 0)
        
        if route_id == current_route:
            prev_seq = route_sequence.get(route_id, 0)
            if stop_seq <= prev_seq:
                app_logger.warning(
                    f"Backward traversal detected on route {route_id}: "
                    f"stop sequence {prev_seq} -> {stop_seq}"
                )
        
        route_sequence[route_id] = stop_seq
        current_route = route_id
        
    seen_names: set = set()
    dup_names: List[str] = []
    for s in path:
        name = G.nodes.get(s, {}).get("name") or s
        if name in seen_names:
            dup_names.append(name)
        seen_names.add(name)
        
    if dup_names:
        app_logger.warning(f"Repeated stop names detected: {list(set(dup_names))}")


def _simplify_route_path(
    path: List[str],
    G: nx.MultiDiGraph,
    source_id: str,
    destination_id: str,
) -> List[str]:
    # TEMPORARILY DISABLED for Phase 4 routing fix
    return path


def _deduplicate_by_name(path: List[str], G: nx.DiGraph) -> List[str]:
    """
    Log duplicate names but DO NOT truncate the path.
    Truncating the path destroys routing correctness if the destination is cut off.
    """
    seen_names: set = set()
    for node_id in path:
        name = G.nodes[node_id].get("name") or node_id
        if name in seen_names:
            app_logger.warning(
                f"Name dedup warning: duplicate name '{name}' found in path "
                f"(stop_id={node_id})"
            )
        seen_names.add(name)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Transfer-aware Dijkstra
# ─────────────────────────────────────────────────────────────────────────────

def _count_transfers(path: List[str], G: nx.MultiDiGraph) -> int:
    """
    Count how many times the route_id changes along a path.
    
    A transfer occurs when there's NO common route_id between consecutive edges.
    This is important for direct routes where multiple parallel edges exist.
    """
    if len(path) < 2:
        return 0
    transfers = 0
    
    # Collect all route_ids for each edge
    all_edge_routes = []
    for i in range(len(path) - 1):
        route_ids = set()
        for edge_key, edge_data in G[path[i]][path[i + 1]].items():
            r = edge_data.get("route_id")
            if r:
                route_ids.add(r)
        all_edge_routes.append(route_ids)
    
    # Count transfers where consecutive edges have NO common route
    for i in range(len(all_edge_routes) - 1):
        current_routes = all_edge_routes[i]
        next_routes = all_edge_routes[i + 1]
        
        # Check if there's any common route between consecutive edges
        if current_routes and next_routes:
            common = current_routes & next_routes
            if not common:
                # No common route - this is a transfer
                transfers += 1
    
    return transfers


def _compute_best_path(
    G: nx.MultiDiGraph,
    source_id: str,
    destination_id: str,
    *,
    traffic: str = "Medium",
    weather: str = "Clear",
    log_strategy: bool = True,
) -> Tuple[List[str], Optional[str]]:
    """
    Enhanced path computation with direct route priority.

    Priority order:
    1. Direct route (0 transfers) - ALWAYS preferred and returned immediately
    2. Transfer-aware Dijkstra (minimal transfers)
    3. NetworkX fallback (last resort)

    Direct routes are returned immediately without considering other candidates.

    Returns:
        Tuple of (path, route_id) where route_id is the single route for direct routes,
        or None for transfer routes.
    """
    source_name = G.nodes.get(source_id, {}).get("name", source_id)
    dest_name = G.nodes.get(destination_id, {}).get("name", destination_id)

    app_logger.info(
        f"[Path Computation] {source_name} ({source_id}) → {dest_name} ({destination_id})"
    )

    # Priority 1: Direct route — return immediately if found
    try:
        direct_result = _find_direct_route(G, source_id, destination_id, log_result=log_strategy)
        if direct_result:
            direct_path, direct_route_id = direct_result
            if len(direct_path) >= 2:
                app_logger.info(
                    f"[PRIORITY] Direct route found - returning immediately "
                    f"(stops={len(direct_path)}, transfers=0, route_id={direct_route_id})"
                )
                return (direct_path, direct_route_id)
    except Exception as e:
        if log_strategy:
            app_logger.warning(f"Direct-route search failed: {e}")

    # Priority 2: Transfer-aware Dijkstra (only if no direct route)
    # nx.has_path() pre-check removed: it runs a full BFS across all edges before
    # Dijkstra even starts. On a 1.4 M-edge graph this alone consumed seconds.
    # Dijkstra's natural return of None is the correct failure signal.
    try:
        dijkstra_path, dijkstra_route = _transfer_aware_dijkstra(G, source_id, destination_id)
        if dijkstra_path and len(dijkstra_path) >= 2:
            return (dijkstra_path, dijkstra_route)
    except Exception as e:
        if log_strategy:
            app_logger.warning("dijkstra_search_failed: queue empty before target reached")
    
    # Priority 3: NetworkX fallback (last resort — Dijkstra found no path)
    try:
        nx_path = nx.shortest_path(G, source=source_id, target=destination_id, weight="distance_km")
        if nx_path and len(nx_path) >= 2:
            app_logger.info(
                f"[Path Computation] NetworkX fallback succeeded | stops={len(nx_path)}"
            )
            return (nx_path, None)
    except Exception as e:
        if log_strategy:
            app_logger.warning(f"NetworkX search failed: {e}")

    raise HTTPException(status_code=404, detail="No route found between these stops.")


def _transfer_aware_dijkstra(
    G: nx.MultiDiGraph,
    source: str,
    target: str,
    *,
    max_explored: int = 35_000,
    max_transfers: int = MAX_TRANSFERS,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Parent-pointer Dijkstra — transfer-aware with full search instrumentation.

    Key improvements over the path-in-heap version:
    1. Parent-pointer map replaces the growing path list in every heap entry.
       Previously: O(depth) list copy on every heap push (the primary hang cause).
       Now: zero copying — path reconstructed in O(path_length) once at target.
    2. Transfer count tracked explicitly in heap state for O(1) budget pruning.
       Branches exceeding max_transfers are pruned before exploring further edges.
    3. Hard limits: max_explored_nodes aborts runaway searches early.
    4. Full structured search instrumentation logged at completion.
    5. visited_stops frozenset kept per-branch for correct state isolation.
    6. route_seq dict (max ~3 entries) retained for backward-traversal detection.

    Heap state: (cost, node, curr_route, transfer_count, route_seq, visited_stops_frozenset)
    Parent map: (node, arriving_route) -> (parent_node, parent_arriving_route) | None
    """
    import heapq
    import itertools

    MAX_HEAP_SIZE = 50_000  # tight cap — safe with deduplicated graph

    target_node = G.nodes.get(target, {})
    target_lat = target_node.get("lat")
    target_lon = target_node.get("lon")

    # Parent map keyed by (node_id, arriving_route_id).
    # Value: (parent_node_id, parent_arriving_route_id) or None for the source.
    parent: Dict[Tuple[str, str], Optional[Tuple[str, str]]] = {
        (source, ""): None
    }

    # Per-state best cost: (node, route_id) -> lowest cost seen
    best_cost: Dict[Tuple[str, str], Tuple[int, float]] = {}
    # Finalized states — once a (node, route) state is popped and expanded once,
    # any later, staler heap entries for the same state are skipped instead of
    # being re-expanded. Without this, the same node's edges get re-processed
    # once per stale heap entry, which is what causes edges_explored to blow far
    # past the graph's actual edge count.
    closed: set = set()
    tiebreaker = itertools.count()

    # Heap: (transfer_count, priority, cost, tiebreaker, node, curr_route, route_seq, visited_stops_frozenset)
    initial_visited: frozenset = frozenset([source])
    heap: List[Tuple] = [
        (0.0, 0.0, next(tiebreaker), 0, source, None, {}, initial_visited)
    ]

    # ── Instrumentation counters ──────────────────────────────────────────────
    nodes_explored:      int = 0
    edges_explored:      int = 0
    peak_heap_size:      int = 0
    max_depth_reached:   int = 0
    transfers_considered: int = 0
    depth_map: Dict[str, int] = {source: 0}
    t_start = time.time()

    while heap:
        peak_heap_size = max(peak_heap_size, len(heap))

        if len(heap) > MAX_HEAP_SIZE:
            app_logger.warning(
                f"[Dijkstra] Heap cap {MAX_HEAP_SIZE} hit — aborting "
                f"(source={source}, target={target}, explored={nodes_explored})"
            )
            break

        priority, cost, _, transfer_count, node, curr_route, route_seq, visited_stops = heapq.heappop(heap)

        # ── Stale entry check ──────────────────────────────────────────────────
        # This same (node, route) state may have been pushed multiple times as
        # progressively cheaper paths were discovered. The first (cheapest) pop
        # finalizes the state; any later pops for the same state are leftovers
        # from earlier, more expensive pushes and must be skipped, not
        # re-expanded — otherwise every stale entry re-walks all of that node's
        # outgoing edges again.
        state_key_now = (node, curr_route or "")
        if state_key_now in closed:
            continue
        closed.add(state_key_now)

        nodes_explored += 1

        if nodes_explored > max_explored:
            app_logger.warning(
                f"[Dijkstra] Node limit {max_explored} hit — aborting "
                f"(source={source}, target={target})"
            )
            break

        # ── Target reached: reconstruct path via parent pointers ──────────────
        if node == target:
            path: List[str] = []
            state: Optional[Tuple[str, str]] = (target, curr_route or "")
            while state is not None:
                path.append(state[0])
                state = parent.get(state)
            path.reverse()

            elapsed_ms = round((time.time() - t_start) * 1000, 2)
            app_logger.info(
                "dijkstra_search_complete",
                extra={
                    "extra_data": {
                        "result": "found",
                        "source": source,
                        "target": target,
                        "path_length": len(path),
                        "transfer_count": transfer_count,
                        "nodes_explored": nodes_explored,
                        "edges_explored": edges_explored,
                        "peak_heap_size": peak_heap_size,
                        "max_depth_reached": max_depth_reached,
                        "transfers_considered": transfers_considered,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return (path, curr_route if transfer_count == 0 else None)

        curr_depth = depth_map.get(node, 0)
        max_depth_reached = max(max_depth_reached, curr_depth)

        # Prune branches that already blew the transfer budget
        if transfer_count > max_transfers:
            continue

        curr_node_data = G.nodes.get(node, {})
        curr_lat = curr_node_data.get("lat")
        curr_lon = curr_node_data.get("lon")

        for nbr, edge_dict in G[node].items():
            # Branch-local visited check: never revisit within this branch's path
            if nbr in visited_stops:
                continue

            for edge_key, edge_data in edge_dict.items():
                edges_explored += 1
                edge_route = edge_data.get("route_id")
                dist_km    = edge_data.get("distance_km", AVG_STOP_DIST_KM)
                stop_seq   = edge_data.get("stop_sequence", 0)

                # ── Backward traversal detection ──────────────────────────────
                is_backward = False
                if curr_route and edge_route == curr_route:
                    prev_seq = route_seq.get(curr_route, 0)
                    if stop_seq <= prev_seq:
                        is_backward = True
                        app_logger.debug(
                            f"Backward: {node} seq={prev_seq} -> "
                            f"{nbr} seq={stop_seq} route={curr_route}"
                        )

                # ── Transfer detection & budget check ─────────────────────────
                is_transfer = (
                    curr_route is not None
                    and edge_route is not None
                    and edge_route != curr_route
                )

                penalty = 0.0
                new_transfer_count = transfer_count

                if is_transfer:
                    transfers_considered += 1
                    new_transfer_count = transfer_count + 1
                    if new_transfer_count > max_transfers:
                        continue  # Hard transfer budget — prune this branch
                    penalty = TRANSFER_PENALTY
                    # Geographic progress check: reject transfers moving away from target
                    if target_lat is not None and target_lon is not None:
                        nbr_node = G.nodes.get(nbr, {})
                        nbr_lat = nbr_node.get("lat")
                        nbr_lon = nbr_node.get("lon")
                        if (
                            curr_lat is not None and curr_lon is not None
                            and nbr_lat is not None and nbr_lon is not None
                        ):
                            curr_dist = haversine(curr_lat, curr_lon, target_lat, target_lon)
                            new_dist  = haversine(nbr_lat,  nbr_lon,  target_lat, target_lon)
                            if new_dist >= curr_dist + 0.5:
                                app_logger.debug(
                                    f"Transfer pruned: no geographic progress "
                                    f"(curr={curr_dist:.2f}km, new={new_dist:.2f}km)"
                                )
                                continue
                elif is_backward:
                    penalty = BACKTRACK_PENALTY

                new_cost = cost + dist_km + penalty

                # ── Cost-based state pruning ──────────────────────────────────
                state_key = (nbr, edge_route or "")
                state_cost = new_cost
                if state_key in best_cost and best_cost[state_key] <= state_cost:
                    continue
                best_cost[state_key] = state_cost

                # ── Update parent pointer ─────────────────────────────────────
                parent[state_key] = (node, curr_route or "")

                new_route_seq    = route_seq.copy()
                new_route_seq[edge_route or ""] = stop_seq

                new_visited      = visited_stops | frozenset([nbr])
                depth_map[nbr]   = curr_depth + 1

                h = 0.0
                if target_lat is not None and target_lon is not None:
                    nbr_node = G.nodes.get(nbr, {})
                    nbr_lat = nbr_node.get("lat")
                    nbr_lon = nbr_node.get("lon")
                    if nbr_lat is not None and nbr_lon is not None:
                        h = haversine(nbr_lat, nbr_lon, target_lat, target_lon)

                priority = new_cost + h

                heapq.heappush(
                    heap,
                    (priority, new_cost, next(tiebreaker), new_transfer_count, nbr, edge_route,
                     new_route_seq, new_visited),
                )

    # ── No path found ─────────────────────────────────────────────────────────
    elapsed_ms = round((time.time() - t_start) * 1000, 2)
    app_logger.info(
        "dijkstra_search_complete",
        extra={
            "extra_data": {
                "result": "not_found",
                "source": source,
                "target": target,
                "nodes_explored": nodes_explored,
                "edges_explored": edges_explored,
                "peak_heap_size": peak_heap_size,
                "max_depth_reached": max_depth_reached,
                "transfers_considered": transfers_considered,
                "elapsed_ms": elapsed_ms,
            }
        },
    )
    return (None, None)  # no path found


# ─────────────────────────────────────────────────────────────────────────────
# Direct-route fast path
# ─────────────────────────────────────────────────────────────────────────────

def _find_direct_route(
    G: nx.MultiDiGraph,
    source_id: str,
    dest_id: str,
    *,
    log_result: bool = True,
) -> Optional[Tuple[List[str], str]]:
    """
    Enhanced direct route finder with strict segment extraction.
    
    Strategy:
    1. Find all routes containing both source and destination
    2. Verify source appears BEFORE destination (direction validation)
    3. For each valid route, extract the segment from source to destination
    4. Return the shortest segment
    
    This ensures we only return the traveled stops, not the entire route.
    Traversal is terminated immediately when destination is reached.
    
    Returns:
        Tuple of (path, route_id) or None if no direct route found
    """
    source_name = G.nodes.get(source_id, {}).get("name", source_id)
    dest_name = G.nodes.get(dest_id, {}).get("name", dest_id)
    
    app_logger.info(
        f"[Direct Route Search] {source_name} ({source_id}) -> {dest_name} ({dest_id})"
    )

    # -- Root-cause tracing: verify stop IDs exist in graph -------------------
    if not G.has_node(source_id):
        app_logger.warning(f"  [ROOT-CAUSE] source_id={source_id} NOT FOUND in graph")
        return None
    if not G.has_node(dest_id):
        app_logger.warning(f"  [ROOT-CAUSE] dest_id={dest_id} NOT FOUND in graph")
        return None

    # -- Collect routes passing through source --------------------------------
    source_routes: Set[str] = set()
    source_route_seqs: Dict[str, int] = {}  # route_id -> stop_sequence at source
    for nbr in G.successors(source_id):
        for edge_key, edge_data in G[source_id][nbr].items():
            r = edge_data.get("route_id")
            seq = edge_data.get("stop_sequence", 0)
            if r:
                source_routes.add(r)
                if r not in source_route_seqs or seq < source_route_seqs[r]:
                    source_route_seqs[r] = seq

    # -- Collect routes passing through destination ---------------------------
    dest_routes: Set[str] = set()
    dest_route_seqs: Dict[str, int] = {}  # route_id -> stop_sequence at dest
    for pred in G.predecessors(dest_id):
        for edge_key, edge_data in G[pred][dest_id].items():
            r = edge_data.get("route_id")
            seq = edge_data.get("stop_sequence", 0)
            if r:
                dest_routes.add(r)
                if r not in dest_route_seqs or seq > dest_route_seqs[r]:
                    dest_route_seqs[r] = seq

    shared_routes = source_routes & dest_routes
    
    app_logger.info(f"  Source routes: {len(source_routes)}")
    app_logger.info(f"  Destination routes: {len(dest_routes)}")
    app_logger.info(f"  Shared routes: {len(shared_routes)}")
    
    if not shared_routes:
        app_logger.info("  No direct route found")
        return None

    best_path: Optional[List[str]] = None
    best_len = float("inf")
    best_route_id = None

    for route_id in sorted(shared_routes):
        src_seq = source_route_seqs.get(route_id, -1)
        dst_seq = dest_route_seqs.get(route_id, -1)

        # -- Direction validation: source must appear before destination -------
        if src_seq >= dst_seq:
            app_logger.info(
                f"  [DIRECTION] Route {route_id} SKIPPED: "
                f"source_seq={src_seq} >= dest_seq={dst_seq} (backward traversal)"
            )
            continue

        app_logger.info(
            f"  [INDEX] Route {route_id}: "
            f"source_index={src_seq}, destination_index={dst_seq}"
        )

        result = _extract_route_segment(G, source_id, dest_id, route_id)
        
        if result:
            segment, segment_route_id = result
            app_logger.info(
                f"  [STOPS] Route {route_id}: returned {len(segment)} stop(s)"
            )
            if len(segment) < best_len:
                best_len = len(segment)
                best_path = segment
                best_route_id = segment_route_id

    if best_path and log_result:
        app_logger.info(
            f"Direct route found | {source_id} -> {dest_id} | "
            f"route_id={best_route_id} | stops={len(best_path)}"
        )
        app_logger.info("  Segment details:")
        for i, stop_id in enumerate(best_path):
            stop_name = G.nodes.get(stop_id, {}).get("name", "Unknown")
            is_dest_marker = " <-- DESTINATION" if stop_id == dest_id else ""
            app_logger.info(f"    [{i}] {stop_name} ({stop_id}){is_dest_marker}")
    
    if best_path and best_route_id:
        return (best_path, best_route_id)
    return None


def _extract_route_segment(
    G: nx.MultiDiGraph,
    source_id: str,
    dest_id: str,
    route_id: str,
) -> Optional[Tuple[List[str], str]]:
    """
    Extract the segment from source to destination on a specific route.
    
    This function ensures we only return the traveled stops, not the entire route.
    It enforces directional constraints (no backward traversal).
    
    Returns:
        Tuple of (path, route_id) or None if no path found
    """
    # Route tracing with direction validation and destination-termination
    queue = deque([([source_id], -1)]) # (path, last_sequence)
    best_path: Optional[List[str]] = None
    best_len = float("inf")
    
    while queue:
        path, prev_seq = queue.popleft()
        node = path[-1]
        
        # 1. Stop-ID verification & Destination-termination logic
        # (Replaces blanket duplicate-stop rejection)
        if node == dest_id:
            if len(path) < best_len:
                best_len = len(path)
                best_path = path
            break  # Stop traversal immediately after destination is reached
        
        # Only follow edges on the specified route with direction validation
        for nbr in G.successors(node):
            valid_edge = False
            next_seq = -1
            
            for edge_key, edge_data in G[node][nbr].items():
                if edge_data.get("route_id") == route_id:
                    seq = edge_data.get("stop_sequence", 0)
                    # 2. Direction validation (ensure strictly increasing sequence)
                    if prev_seq == -1 or seq > prev_seq:
                        valid_edge = True
                        next_seq = seq
                        break
            
            if valid_edge:
                queue.append((path + [nbr], next_seq))
    
    if best_path:
        return (best_path, route_id)
    return None


def _infer_best_starting_route(
    G: nx.MultiDiGraph,
    path: List[str],
    lookahead: int = 5,
) -> Optional[str]:
    """
    Find the route that can run the longest consecutive streak from position 0.

    Used to initialise current_route in _build_route_response when direct_route_id
    is None (Dijkstra / NetworkX paths).  Without this, _best_edge picks an
    arbitrary parallel edge at stop 0, which causes phantom transfers for every
    subsequent stop that lacks that route.
    """
    if len(path) < 2:
        return None

    # Candidates: all routes on the very first edge
    first_routes: Set[str] = set()
    if G.has_edge(path[0], path[1]):
        for _, ed in G[path[0]][path[1]].items():
            r = ed.get("route_id")
            if r:
                first_routes.add(r)

    if not first_routes:
        return None

    # Score each candidate by consecutive-edge coverage from position 0
    best_route: Optional[str] = None
    best_score: int = -1

    for candidate in first_routes:
        score = 0
        for i in range(min(lookahead, len(path) - 1)):
            found = False
            if G.has_edge(path[i], path[i + 1]):
                for _, ed in G[path[i]][path[i + 1]].items():
                    if ed.get("route_id") == candidate:
                        found = True
                        score += 1
                        break
            if not found:
                break  # Stop at first gap — continuity matters
        if score > best_score:
            best_score = score
            best_route = candidate

    app_logger.debug(
        f"_infer_best_starting_route: path[0]={path[0]} → chose route={best_route} "
        f"(score={best_score}/{min(lookahead, len(path)-1)} candidates={len(first_routes)})"
    )
    return best_route


def _build_route_response(
    G: nx.MultiDiGraph,
    best_path: List[str],
    source_id: str,
    traffic: str = "Medium",
    weather: str = "Clear",
    *,
    log_response: bool = True,
    direct_route_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enhanced route response builder with comprehensive debug logging.
    
    Args:
        direct_route_id: If provided, this route_id will be used for all edges
                        to ensure direct routes remain single-route.
    """
    app_logger.info(
        "route_builder_start",
        extra={
            "extra_data": {
                "source_id": source_id,
                "path_length": len(best_path) if best_path else 0,
                "unique_stops": len(set(best_path)) if best_path else 0,
                "direct_route_id": direct_route_id,
            }
        },
    )

    source_name    = G.nodes.get(source_id, {}).get("name", source_id)
    destination_id = best_path[-1] if best_path else source_id
    dest_name      = G.nodes.get(destination_id, {}).get("name", destination_id)

    try:
        validate_route(best_path, G)
    except RoutingValidationError as ve:
        app_logger.error(f"FINAL VALIDATION FAILED: {ve}")
        raise HTTPException(
            status_code=500,
            detail=f"Routing engine could not produce a cycle-free path: {ve}"
        )
    
    # Apply route simplification layer
    simplified_path = _simplify_route_path(best_path, G, source_id, destination_id)
    
    # Use simplified path for further processing
    best_path = simplified_path

    # _count_transfers is kept for audit comparison only; num_transfers will be
    # overridden by len(transfers) after the leg-walk (single authoritative source).
    num_transfers = _count_transfers(best_path, G)

    if num_transfers > MAX_TRANSFERS:
        app_logger.warning(f"Transfer limit exceeded ({num_transfers}) - early check")

    # Check for missing nodes BEFORE accessing G.nodes
    missing_nodes = [node_id for node_id in best_path if node_id not in G.nodes]
    if missing_nodes:
        app_logger.error(
            "STOP_TRACE_5_MISSING_NODES_IN_BEST_PATH",
            extra={
                "extra_data": {
                    "stage": "route_response_builder",
                    "missing_nodes": missing_nodes,
                    "best_path": best_path,
                }
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Path contains nodes not in graph: {missing_nodes}"
        )

    dest_name    = G.nodes[best_path[-1]].get("name", "")
    stop_names   = [G.nodes[n].get("name", "Unknown") for n in best_path]
    source_name  = G.nodes[source_id].get("name", "Unknown")

    route_legs:    List[Dict] = []
    detailed_path: List[Dict] = []
    transfers:     List[Dict] = []
    current_route: Optional[str] = None

    for i, node_id in enumerate(best_path):
        if node_id not in G.nodes:
            app_logger.error(
                "STOP_TRACE_6_NODE_ACCESS_ERROR",
                extra={
                    "extra_data": {
                        "stage": "route_response_builder",
                        "node_id": node_id,
                        "index": i,
                        "best_path": best_path,
                    }
                }
            )
            raise HTTPException(
                status_code=500,
                detail=f"Node {node_id} not in graph at index {i}"
            )
        node_data = G.nodes[node_id]
        is_last   = (i == len(best_path) - 1)

        if i > 0:
            if direct_route_id:
                # For direct routes, use the provided route_id for all edges
                edge_route = direct_route_id
            else:
                prev_edge   = _best_edge(G, best_path[i - 1], node_id, current_route=current_route)
                edge_route  = prev_edge.get("route_id", "UNKNOWN")
            is_transfer = (current_route is not None and
                           edge_route != current_route and
                           not is_last)
            if is_transfer:
                transfers.append({
                    "stop_name":  node_data.get("name", "Unknown"),
                    "from_route": current_route,
                    "to_route":   edge_route,
                })
            current_route = edge_route
        else:
            is_transfer = False
            if len(best_path) > 1:
                if direct_route_id:
                    # For direct routes, use the provided route_id
                    current_route = direct_route_id
                else:
                    # Infer the dominant starting route to avoid phantom transfers.
                    # _best_edge without current_route picks an arbitrary parallel
                    # edge; _infer_best_starting_route picks the one with the
                    # longest consecutive run from position 0.
                    inferred = _infer_best_starting_route(G, best_path)
                    if inferred:
                        current_route = inferred
                    else:
                        first_edge    = _best_edge(G, best_path[0], best_path[1])
                        current_route = first_edge.get("route_id", "UNKNOWN")
                    app_logger.debug(
                        f"leg-walk initial route: {current_route} "
                        f"(inferred={inferred is not None})"
                    )

        if i < len(best_path) - 1:
            if direct_route_id:
                # For direct routes, use the provided route_id
                display_rid = direct_route_id
            else:
                ahead_edge  = _best_edge(G, node_id, best_path[i + 1], current_route=current_route)
                display_rid = ahead_edge.get("route_id", current_route or "UNKNOWN")
        else:
            display_rid = current_route or "UNKNOWN"

        if not route_legs or route_legs[-1].get("route_id") != current_route:
            route_legs.append({
                "route_id":   current_route,
                "start_stop": node_data.get("name", "Unknown"),
            })

        detailed_path.append({
            "stop_id":    node_id,
            "stop_name":  node_data.get("name", "Unknown"),
            "lat":        node_data.get("lat"),
            "lon":        node_data.get("lon"),
            "route_id":   display_rid,
            "is_transfer": is_transfer,
        })

    # Leg-walk is the single authoritative transfer count.
    # _count_transfers() above uses _best_edge (picks the cheapest parallel edge)
    # which can return a different route_id than what _best_edge(current_route=…)
    # picks in the leg-walk below, causing the two counts to diverge.
    # The leg-walk is always used for the transfers list displayed to the user,
    # so len(transfers) is the only consistent source.
    num_transfers = len(transfers)
    
    if num_transfers > MAX_TRANSFERS:
        app_logger.warning(f"Route rejected: transfer limit exceeded ({num_transfers} > {MAX_TRANSFERS})")
        raise HTTPException(
            status_code=404,
            detail=f"No viable route found with {MAX_TRANSFERS} or fewer transfers."
        )

    try:
        total_distance_km = sum(
            _best_edge(G, best_path[i], best_path[i + 1]).get("distance_km", 0.0)
            for i in range(len(best_path) - 1)
        ) if len(best_path) > 1 else 0.0
    except Exception:
        total_distance_km = 0.0

    valid_path: List[Dict] = [
        s for s in detailed_path
        if s["lat"] is not None and s["lon"] is not None
    ]

    route_efficiency = compute_route_efficiency(
        path=best_path,
        G=G,
        transfers=num_transfers,
        traffic=traffic,
        weather=weather,
    )
    validated = validate_route_integrity(best_path, G)
    integrity_score = _compute_route_integrity_score(best_path, G)

    is_multi_hop     = len(route_legs) > 1
    primary_route_id = ("COMPOSITE_ROUTE" if is_multi_hop
                        else (route_legs[0]["route_id"] if route_legs else "UNKNOWN"))
    ml_route_id      = route_legs[0]["route_id"] if route_legs else "UNKNOWN"

    if log_response:
        app_logger.info(
            "route response ready",
            extra={
                "extra_data": {
                    "source_name": source_name,
                    "dest_name": dest_name,
                    "path_length": len(best_path),
                    "distance_km": round(total_distance_km, 1),
                    "transfer_count": num_transfers,
                    "validation_status": bool(validated),
                    "route_integrity_score": integrity_score,
                    "routing_mode": "deterministic",
                }
            },
        )
        
    # ── Loop detection validation ─────────────────────────────────────────
    # Audit the final path for stop-name revisits and corridor backtracking.
    # This is logged but does NOT reject the route — it provides diagnostic
    # data for ongoing quality improvement.
    seen_stop_names: Dict[str, int] = {}
    revisited_names: List[str] = []
    for idx, sid in enumerate(best_path):
        sname = G.nodes.get(sid, {}).get("name", sid)
        if sname in seen_stop_names:
            revisited_names.append(sname)
        else:
            seen_stop_names[sname] = idx

    # Corridor backtrack: detect A→B→…→B pattern (same stop_id, not name)
    corridor_revisits: List[Dict] = []
    seen_stop_ids: Dict[str, int] = {}
    for idx, sid in enumerate(best_path):
        if sid in seen_stop_ids:
            corridor_revisits.append({
                "stop_id": sid,
                "stop_name": G.nodes.get(sid, {}).get("name", sid),
                "first_index": seen_stop_ids[sid],
                "revisit_index": idx,
            })
        else:
            seen_stop_ids[sid] = idx

    if revisited_names or corridor_revisits:
        app_logger.warning(
            "route_loop_detection",
            extra={
                "extra_data": {
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "path_length": len(best_path),
                    "revisited_stop_names": list(set(revisited_names)),
                    "revisited_name_count": len(revisited_names),
                    "corridor_revisits": corridor_revisits,
                    "corridor_revisit_count": len(corridor_revisits),
                }
            },
        )

    # ── Strict Path-Quality Diagnostics (Non-blocking) ────────────────────
    repeated_stop_ids = detect_repeated_stop_ids(best_path)
    repeated_edges = detect_repeated_edges(best_path)
    backtracks = detect_backtracking(best_path)
    cycles = detect_cycles(best_path)

    if repeated_stop_ids or repeated_edges or backtracks or cycles:
        app_logger.error(
            "route_quality_failure",
            extra={
                "extra_data": {
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "path_length": len(best_path),
                    "unique_stops": len(set(best_path)),
                    "repeated_stop_ids_count": len(repeated_stop_ids),
                    "repeated_stop_ids": repeated_stop_ids,
                    "repeated_edges_count": len(repeated_edges),
                    "repeated_edges": repeated_edges,
                    "backtracking_count": len(backtracks),
                    "backtracks": backtracks,
                    "cycle_count": len(cycles),
                    "cycles": cycles,
                    "primary_route_id": primary_route_id,
                }
            },
        )

    route_ids = [leg.get("route_id") for leg in route_legs if leg.get("route_id")]
    route_ids = list(dict.fromkeys(route_ids))
    
    # ETA calculation audit
    travel_time_min = (total_distance_km / 20.0) * 60.0
    waiting_time_min = 5.0
    transfer_time_min = num_transfers * 7.0
    delay_adj_min = 0.0
    if traffic == "High": delay_adj_min += 5.0
    elif traffic == "Heavy": delay_adj_min += 15.0
    if weather == "Rainy": delay_adj_min += 3.0
    elif weather == "Storm": delay_adj_min += 10.0
    
    eta_min = int(travel_time_min + waiting_time_min + transfer_time_min + delay_adj_min)


    return {
        "route_id":          primary_route_id,
        "ml_route_id":       ml_route_id,
        "source_name":       source_name,
        "dest_name":         dest_name,
        "stops":             stop_names,
        "route_legs":        route_legs,
        "route_path":        valid_path,
        "total_distance_km": round(total_distance_km),
        "transfers":         transfers,
        "num_transfers":     num_transfers,
        "route_efficiency":  route_efficiency,
        "path":              valid_path,
        "distance_km":       round(total_distance_km),
        "route_ids":         route_ids,
        "eta_min":           eta_min,
        "debug": {
            "graph_type": "MultiDiGraph",
            "edge_mode": "best_edge_only",
            "validated": bool(validated),
        },
    }


def precompute_hub_routes(db: Session) -> Dict[str, int]:
    G = build_transit_graph(db)
    valid_hubs = [hub_id for hub_id in HUB_STOPS if G.has_node(hub_id)]
    computed = 0
    skipped = 0

    for source_id in valid_hubs:
        for destination_id in valid_hubs:
            if source_id == destination_id:
                continue
            cache_key = _get_hub_cache_key(source_id, destination_id)
            if cache_key in hub_cache:
                skipped += 1
                continue
            try:
                best_path = _compute_best_path(
                    G,
                    source_id,
                    destination_id,
                    log_strategy=False,
                )
            except HTTPException:
                skipped += 1
                continue
            except Exception as e:
                skipped += 1
                app_logger.warning(
                    f"Hub precompute skipped for {source_id}->{destination_id}: {e}"
                )
                continue

            if best_path and len(best_path[0]) >= 2:
                hub_cache[cache_key] = list(best_path[0])
                computed += 1
            else:
                skipped += 1

    app_logger.info(
        "hub route precompute completed",
        extra={
            "extra_data": {
                "configured_hubs": len(HUB_STOPS),
                "valid_hubs": len(valid_hubs),
                "computed_pairs": computed,
                "skipped_pairs": skipped,
            }
        },
    )
    return {
        "configured_hubs": len(HUB_STOPS),
        "valid_hubs": len(valid_hubs),
        "computed_pairs": computed,
        "skipped_pairs": skipped,
    }


def warm_common_route_cache(
    db: Session,
    bus_capacity: int = ROUTE_WARMUP_BUS_CAPACITY,
) -> Dict[str, int]:
    G = build_transit_graph(db)
    warmed = 0
    skipped = 0

    for source_id, destination_id in COMMON_FREQUENT_ROUTES[:20]:
        if source_id == destination_id:
            skipped += 1
            continue
        if not G.has_node(source_id) or not G.has_node(destination_id):
            skipped += 1
            continue
        cache_key = _get_route_cache_key(source_id, destination_id, bus_capacity)
        if cache_key in route_cache:
            skipped += 1
            continue

        best_path = None
        if _is_hub_stop(source_id) and _is_hub_stop(destination_id):
            best_path = _get_cached_hub_path(G, source_id, destination_id)

        if best_path is None:
            try:
                best_path, best_route_id = _compute_best_path(
                    G,
                    source_id,
                    destination_id,
                    log_strategy=False,
                )
            except HTTPException:
                skipped += 1
                continue
            except Exception as e:
                skipped += 1
                app_logger.warning(
                    f"Common route warmup skipped for {source_id}->{destination_id}: {e}"
                )
                continue

        response = _build_route_response(
            G,
            best_path,
            source_id,
            traffic="Medium",
            weather="Clear",
            log_response=False,
            direct_route_id=best_route_id,
        )
        _store_cached_route(source_id, destination_id, bus_capacity, response)
        warmed += 1

    app_logger.info(
        "common route cache warmup completed",
        extra={
            "extra_data": {
                "configured_routes": min(len(COMMON_FREQUENT_ROUTES), 20),
                "warmed_routes": warmed,
                "skipped_routes": skipped,
            }
        },
    )
    return {
        "configured_routes": min(len(COMMON_FREQUENT_ROUTES), 20),
        "warmed_routes": warmed,
        "skipped_routes": skipped,
    }


def _run_startup_routing_warmup() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        precompute_hub_routes(db)
        warm_common_route_cache(db)
    except Exception as e:
        app_logger.warning(f"Startup routing warmup failed: {e}", exc_info=True)
    finally:
        db.close()


def start_routing_warmup() -> bool:
    global _routing_warmup_started
    if _routing_warmup_started:
        return False

    _routing_warmup_started = True
    threading.Thread(
        target=_run_startup_routing_warmup,
        name="routing-cache-warmup",
        daemon=True,
    ).start()
    app_logger.info("Routing warmup thread started.")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Route efficiency — dynamic formula (no hardcoded values)
# ─────────────────────────────────────────────────────────────────────────────

def compute_route_efficiency(
    path: List[str],
    G: nx.MultiDiGraph,
    transfers: int,
    traffic: str = "Medium",
    weather: str = "Clear",
    return_components: bool = False,
) -> Any:
    """
    Dynamic efficiency score.  100 is perfect; penalties subtracted.
    """
    score = 100
    
    travel_time_cost = 0
    transfer_cost = transfers * 15
    loop_penalty = 0
    detour_penalty = 0
    occupancy_cost = 0
    demand_cost = 0

    score -= transfer_cost

    unique_stops = len(set(path))
    loop_count   = len(path) - unique_stops
    loop_penalty = loop_count * 10
    score       -= loop_penalty

    if len(path) >= 2:
        src_data  = G.nodes.get(path[0], {})
        dst_data  = G.nodes.get(path[-1], {})
        lat_s, lon_s = src_data.get("lat"), src_data.get("lon")
        lat_d, lon_d = dst_data.get("lat"), dst_data.get("lon")

        if all(v is not None for v in (lat_s, lon_s, lat_d, lon_d)):
            straight_km = haversine(lat_s, lon_s, lat_d, lon_d)
            actual_km = 0.0
            current_route = None
            for i in range(len(path) - 1):
                if i == 0:
                    edge_data = _best_edge(G, path[i], path[i + 1])
                else:
                    edge_data = _best_edge(G, path[i], path[i + 1], current_route=current_route)
                current_route = edge_data.get("route_id")
                actual_km += edge_data.get("distance_km", AVG_STOP_DIST_KM)

            travel_time_cost = int(actual_km * 2)
            
            soft_transfer_penalty = min(transfers * 0.2, 2.0)
            actual_km += soft_transfer_penalty

            if straight_km > 0:
                detour_ratio = actual_km / straight_km
                excess       = max(0.0, detour_ratio - 1.3)
                detour_penalty = min(25, int(excess * 30))
                score -= detour_penalty

    traffic_cost = {
        "Low": 0, "Medium": 5, "High": 12, "Heavy": 20
    }.get(traffic, 5)
    score -= traffic_cost

    weather_cost = {
        "Clear": 0, "Cloudy": 3, "Rainy": 8, "Storm": 18
    }.get(weather, 0)
    score -= weather_cost
    
    final_cost = max(0, min(100, score))
    
    components = {
        "travel_time_cost": travel_time_cost,
        "transfer_cost": transfer_cost,
        "occupancy_cost": occupancy_cost,
        "demand_cost": demand_cost,
        "traffic_cost": traffic_cost,
        "weather_cost": weather_cost,
        "loop_penalty": loop_penalty,
        "detour_penalty": detour_penalty,
        "final_cost": final_cost
    }
    
    if return_components:
        return final_cost, components
        
    return final_cost


def _compute_route_integrity_score(path: List[str], G: nx.MultiDiGraph) -> int:
    """
    Read-only integrity score based on valid path segments.
    """
    if len(path) < 2:
        return 100

    valid_segments = 0
    total_segments = len(path) - 1
    for i in range(total_segments):
        u = str(path[i])
        v = str(path[i + 1])
        if not G.has_edge(u, v):
            continue
        edge = _best_edge(G, u, v)
        route_id = edge.get("route_id")
        distance_km = edge.get("distance_km")
        try:
            distance_ok = float(distance_km) > 0 and math.isfinite(float(distance_km))
        except Exception:
            distance_ok = False
        if route_id and route_id != "UNKNOWN" and distance_ok:
            valid_segments += 1

    return int(round((valid_segments / total_segments) * 100)) if total_segments else 100


# ─────────────────────────────────────────────────────────────────────────────
# Alternative routes generation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_path_with_strategy(
    G: nx.MultiDiGraph,
    source_id: str,
    destination_id: str,
    strategy: str = "fastest",
    traffic: str = "Medium",
    weather: str = "Clear",
) -> Optional[Tuple[List[str], Optional[str]]]:
    """
    Compute a path using a specific optimization strategy.
    
    Strategies:
    - fastest: Minimum travel time (default behavior)
    - least_transfers: Minimum number of transfers
    - shortest_distance: Minimum total distance
    - least_walking: Minimum walking distance (approximated by fewer stops)
    
    Returns:
        Tuple of (path, route_id) or None if no path found
    """
    import heapq
    
    # Adjust transfer penalty based on strategy
    global TRANSFER_PENALTY
    original_transfer_penalty = TRANSFER_PENALTY
    
    if strategy == "least_transfers":
        TRANSFER_PENALTY = 50.0  # Heavy penalty for transfers
    elif strategy == "shortest_distance":
        TRANSFER_PENALTY = 5.0   # Lower penalty to allow more transfers for shorter distance
    elif strategy == "least_walking":
        TRANSFER_PENALTY = 10.0  # Moderate penalty
    else:  # fastest
        TRANSFER_PENALTY = 15.0  # Default
    
    try:
        path, route_id = _compute_best_path(G, source_id, destination_id, traffic=traffic, weather=weather, log_strategy=False)
        return (path, route_id)
    except HTTPException:
        return None
    finally:
        TRANSFER_PENALTY = original_transfer_penalty


def generate_alternative_routes(
    db: Session,
    source_id: str,
    destination_id: str,
    bus_capacity: int = 60,
    traffic: str = "Medium",
    weather: str = "Clear",
) -> List[Dict[str, Any]]:
    """
    Generate up to 4 unique alternative routes using different optimization strategies.
    
    Strategies:
    1. Fastest - minimum travel time
    2. Least Crowded - lowest predicted occupancy (uses ML prediction)
    3. Fewest Transfers - minimum transfers
    4. Shortest Walking Distance - minimum walking distance
    
    Returns:
        List of alternative route dictionaries with strategy, route_id, eta, distance, etc.
    """
    G = build_transit_graph(db)

    # Fast pre-check: is there even a direct/shared route between these stops?
    # _find_direct_route's shared-route check (source_routes & dest_routes) is
    # cheap -- a single pass over each stop's immediate route edges. But when
    # it comes up empty, _compute_best_path falls through to the transfer-aware
    # Dijkstra fallback, which explores millions of edges on this dataset's
    # route density and can take 20-60+ seconds. Each of the 4 strategies below
    # independently re-runs that same expensive fallback, so a single
    # no-shared-route pair could burn several minutes of CPU per call to this
    # function -- and since callers often wrap this in a timeout (see
    # navigation.py's ALTERNATIVES_TIMEOUT_SEC), that CPU keeps burning in an
    # orphaned background thread even after the caller gives up waiting,
    # degrading unrelated concurrent work via GIL contention.
    #
    # Alternates are a "nice to have" layered on top of the primary
    # RAPTOR-resolved route, so when there's no direct route, skip the
    # expensive multi-transfer search across all 4 strategies rather than
    # paying that cost (up to) 4 times for a result we can already predict.
    if _find_direct_route(G, source_id, destination_id, log_result=True) is None:
        app_logger.info(
            f"generate_alternative_routes: no direct/shared route for "
            f"{source_id}->{destination_id}; skipping expensive multi-transfer "
            f"search for all strategies (alternates are optional)"
        )
        return []

    strategies = [
        ("fastest", "⚡ Fastest"),
        ("least_transfers", "🔄 Fewest Transfers"),
        ("shortest_distance", "📏 Shortest Distance"),
        ("least_walking", "🚶 Short Walk"),
    ]
    
    alternative_routes = []
    seen_routes = set()  # Track unique route signatures to avoid duplicates
    
    for strategy_key, strategy_label in strategies:
        try:
            path, route_id = _compute_path_with_strategy(
                G, source_id, destination_id, strategy=strategy_key, traffic=traffic, weather=weather
            )
            
            if not path or len(path) < 2:
                continue
            
            # Build route response for this alternative
            route_response = _build_route_response(
                G, path, source_id, traffic=traffic, weather=weather, log_response=False, direct_route_id=route_id
            )
            
            # Create a unique signature for this route (based on path and route_ids)
            route_signature = (tuple(path), tuple(route_response.get("route_ids", [])))
            
            if route_signature in seen_routes:
                continue  # Skip duplicate routes
            
            seen_routes.add(route_signature)
            
            # Calculate walking distance (approximate by number of stops)
            walking_distance_m = len(path) * 100  # Approximate 100m per stop
            
            # Determine occupancy level (will be updated with ML prediction later)
            occupancy_level = "Medium"
            
            alternative_route = {
                "strategy": strategy_label,
                "strategy_key": strategy_key,
                "route_id": route_response.get("route_id", ""),
                "route_name": route_response.get("route_id", ""),
                "eta": route_response.get("eta_min", 0),
                "distance": route_response.get("total_distance_km", 0),
                "walking_distance": walking_distance_m,
                "transfers": route_response.get("num_transfers", 0),
                "occupancy": occupancy_level,
                "journey": route_response,
            }
            
            alternative_routes.append(alternative_route)
            
            # Stop if we have enough alternatives
            if len(alternative_routes) >= 4:
                break
                
        except Exception as e:
            app_logger.warning(f"Failed to generate alternative route for strategy {strategy_key}: {e}")
            continue
    
    return alternative_routes


# ─────────────────────────────────────────────────────────────────────────────
# Core routing — public entry point
# ─────────────────────────────────────────────────────────────────────────────

def resolve_route_dynamic(
    db: Session,
    source_id: str,
    destination_id: str,
    bus_capacity: int = 60,
    traffic: str = "Medium",
    weather: str  = "Clear",
) -> Dict[str, Any]:
    """
    Find the best loop-free path from source_id to destination_id.

    Strategy (in priority order):
      1. Direct-route fast path (single route_id, no transfers)
      2. Transfer-aware Dijkstra (TRANSFER_PENALTY on route switches)
      3. NetworkX simple-path fallback if step 2 fails

    Post-processing:
      - Validate: no repeated stops
      - Name-dedup: truncate at repeated display name
      - MAX_TRANSFERS enforcement: reject paths with > MAX_TRANSFERS switches
      - Fix destination-transfer bug: destination never in transfers list
      - Compute dynamic route efficiency
    """
    app_logger.info(
        "ROUTING_TRACE",
        extra={
            "extra_data": {
                "function": "resolve_route_dynamic",
                "source_id": str(source_id),
                "destination_id": str(destination_id),
                "bus_capacity": bus_capacity,
                "traffic": traffic,
                "weather": weather,
            }
        }
    )

    global route_cache_hits, route_cache_misses
    request_started = time.time()

    source_id      = str(source_id)
    destination_id = str(destination_id)
    bus_capacity   = int(bus_capacity or 60)

    cached_response = _get_cached_route(source_id, destination_id, bus_capacity)
    app_logger.info(
        "ROUTING_TRACE",
        extra={
            "extra_data": {
                "function": "_get_cached_route",
                "source_id": source_id,
                "destination_id": destination_id,
                "cache_hit": cached_response is not None,
            }
        }
    )
    if cached_response is not None:
        route_cache_hits += 1
        routing_time_ms = round((time.time() - request_started) * 1000, 2)
        cache_stats = _get_route_cache_stats()
        app_logger.info(
            "route_metrics",
            extra={
                "extra_data": {
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "bus_capacity": bus_capacity,
                    "cache_hit": True,
                    "cache_miss": False,
                    "routing_time_ms": routing_time_ms,
                    "transfer_count": len(cached_response.get("transfers", []) or []),
                    "route_length": len(cached_response.get("path", []) or []),
                    "cache_size": cache_stats["cache_size"],
                    "cache_hit_ratio": cache_stats["cache_hit_ratio"],
                    "eviction_count": cache_stats["eviction_count"],
                    "hub_route_used": False,
                    "hub_cache_hit": False,
                }
            },
        )
        return cached_response

    route_cache_misses += 1

    G = build_transit_graph(db)
    app_logger.info(
        "routing_graph_ready",
        extra={
            "extra_data": {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "source_id": source_id,
                "destination_id": destination_id,
            }
        },
    )

    if source_id not in G:
        raise HTTPException(status_code=404,
                            detail=f"Source stop '{source_id}' not found in transit network.")
    if destination_id not in G:
        return {
            "success": False,
            "message": "Destination stop not present in routing graph"
        }
    if source_id == destination_id:
        raise HTTPException(status_code=400,
                            detail="Source and destination must be different stops.")

    hub_route_used = False
    hub_cache_hit = False

    best_path = None
    best_route_id: Optional[str] = None
    if _is_hub_stop(source_id) and _is_hub_stop(destination_id):
        best_path = _get_cached_hub_path(G, source_id, destination_id)
        if best_path is not None:
            hub_route_used = True
            hub_cache_hit  = True
            # Recover route_id for hub paths so _build_route_response can use
            # direct_route_id and avoid phantom-transfer mis-attribution.
            if len(best_path) >= 2:
                try:
                    direct_result = _find_direct_route(
                        G, source_id, destination_id, log_result=False
                    )
                    if direct_result:
                        best_route_id = direct_result[1]
                        app_logger.debug(
                            f"Hub-cache path: recovered direct route_id={best_route_id}"
                        )
                except Exception:
                    pass  # Leave best_route_id as None; leg-walk will infer it

    if best_path is None:
        best_path, best_route_id = _compute_best_path(
            G, source_id, destination_id, traffic=traffic, weather=weather,
        )

    if not best_path:
        raise HTTPException(status_code=404, detail="No route found")
        
    if best_path[-1] != destination_id:
        app_logger.error(f"INVALID ROUTE: expected destination={destination_id}, actual={best_path[-1]}")
        return {
            "success": False,
            "message": "Computed route does not reach requested destination"
        }

    response = _build_route_response(
        G,
        best_path,
        source_id,
        traffic=traffic,
        weather=weather,
        log_response=True,
        direct_route_id=best_route_id,
    )

    _store_cached_route(source_id, destination_id, bus_capacity, response)

    routing_time_ms = round((time.time() - request_started) * 1000, 2)
    cache_stats = _get_route_cache_stats()
    app_logger.info(
        "route_metrics",
        extra={
            "extra_data": {
                "source_id": source_id,
                "destination_id": destination_id,
                "bus_capacity": bus_capacity,
                "cache_hit": False,
                "cache_miss": True,
                "routing_time_ms": routing_time_ms,
                "transfer_count": response.get("num_transfers", 0),
                "route_length": len(response.get("path", []) or []),
                "cache_size": cache_stats["cache_size"],
                "cache_hit_ratio": cache_stats["cache_hit_ratio"],
                "eviction_count": cache_stats["eviction_count"],
                "hub_route_used": hub_route_used,
                "hub_cache_hit": hub_cache_hit,
            }
        },
    )

    return response


def validate_route_integrity(path: List[str], G: nx.MultiDiGraph) -> bool:
    """
    READ-ONLY integrity checks for routing output.

    - verify every edge exists in MultiDiGraph
    - verify route_id exists
    - verify distance_km is valid

    Logs warnings only; does NOT mutate graph/path or alter routing decisions.
    """
    if not path or len(path) < 2:
        return True

    ok = True
    for i in range(len(path) - 1):
        u = str(path[i])
        v = str(path[i + 1])
        if not G.has_edge(u, v):
            app_logger.warning(f"Route integrity: missing edge {u} -> {v}")
            ok = False
            continue

        e = _best_edge(G, u, v)
        rid = e.get("route_id")
        dist = e.get("distance_km")

        if not rid or rid == "UNKNOWN":
            app_logger.warning(f"Route integrity: missing/unknown route_id for edge {u} -> {v}")
            ok = False

        try:
            dist_val = float(dist)
            if not (dist_val > 0 and math.isfinite(dist_val)):
                raise ValueError("non-positive or non-finite")
        except Exception:
            app_logger.warning(f"Route integrity: invalid distance_km for edge {u} -> {v} | distance_km={dist}")
            ok = False

    return ok