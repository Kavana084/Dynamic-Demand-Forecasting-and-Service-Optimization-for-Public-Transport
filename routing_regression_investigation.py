"""
routing_regression_investigation.py
====================================
Instrument the routing pipeline for:
  Source: 21454 (Ambedkar Institute of Technology)
  Dest:   21517 (Goraguntepalya)

Covers:
 1. Graph membership check
 2. Direct route search trace
 3. Dijkstra trace with geographic-pruning audit
 4. _build_route_response trace (transfer counting)
 5. Route-revisit / backtrack detection
"""

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

import networkx as nx
from collections import deque
from app.database.connection import SessionLocal
from app.services.routing_service import (
    build_transit_graph,
    _find_direct_route,
    _transfer_aware_dijkstra,
    _build_route_response,
    _count_transfers,
    haversine,
    MAX_TRANSFERS,
)

SOURCE = "21454"
DEST   = "21517"

REPORT_LINES = []

def log(msg=""):
    REPORT_LINES.append(msg)
    print(msg)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Build graph
# ─────────────────────────────────────────────────────────────────────────────

db = SessionLocal()
log("=" * 70)
log("STEP 1 — Build transit graph")
log("=" * 70)
G = build_transit_graph(db)
log(f"  nodes={G.number_of_nodes()}  edges={G.number_of_edges()}")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Node membership
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 2 — Node membership check")
log("=" * 70)
src_in = G.has_node(SOURCE)
dst_in = G.has_node(DEST)
log(f"  source {SOURCE} in graph: {src_in}")
log(f"  dest   {DEST} in graph:   {dst_in}")
if src_in:
    log(f"  source name: {G.nodes[SOURCE].get('name')}")
if dst_in:
    log(f"  dest name:   {G.nodes[DEST].get('name')}")
log(f"  source out-edges: {G.out_degree(SOURCE) if src_in else 'N/A'}")
log(f"  dest   in-edges:  {G.in_degree(DEST) if dst_in else 'N/A'}")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Direct route search (manual trace)
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 3 — Manual direct-route search trace")
log("=" * 70)

source_routes = {}
for nbr in G.successors(SOURCE):
    for ek, ed in G[SOURCE][nbr].items():
        r   = ed.get("route_id")
        seq = ed.get("stop_sequence", 0)
        if r and (r not in source_routes or seq < source_routes[r]):
            source_routes[r] = seq

dest_routes = {}
for pred in G.predecessors(DEST):
    for ek, ed in G[pred][DEST].items():
        r   = ed.get("route_id")
        seq = ed.get("stop_sequence", 0)
        if r and (r not in dest_routes or seq > dest_routes[r]):
            dest_routes[r] = seq

shared = set(source_routes) & set(dest_routes)
log(f"  source_routes count: {len(source_routes)}")
log(f"  dest_routes count:   {len(dest_routes)}")
log(f"  shared_routes count: {len(shared)}")
log()

if not shared:
    log("  *** NO SHARED ROUTES — direct route impossible ***")
else:
    log(f"  Shared route IDs: {sorted(shared)}")
    for rid in sorted(shared):
        src_seq = source_routes[rid]
        dst_seq = dest_routes[rid]
        direction_ok = src_seq < dst_seq
        log(f"    route={rid}  src_seq={src_seq}  dst_seq={dst_seq}  "
            f"direction={'OK' if direction_ok else 'BACKWARD — SKIPPED'}")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Geographic pruning audit — does the destination lie in a pruned direction?
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 4 — Geographic pruning audit")
log("=" * 70)
src_lat = G.nodes.get(SOURCE, {}).get("lat")
src_lon = G.nodes.get(SOURCE, {}).get("lon")
dst_lat = G.nodes.get(DEST, {}).get("lat")
dst_lon = G.nodes.get(DEST, {}).get("lon")
log(f"  source coords: ({src_lat}, {src_lon})")
log(f"  dest   coords: ({dst_lat}, {dst_lon})")
if src_lat and dst_lat:
    direct_km = haversine(src_lat, src_lon, dst_lat, dst_lon)
    log(f"  straight-line distance: {direct_km:.2f} km")
log()

# For every shared route, check how many intermediate transfer points are pruned
if shared:
    log("  Checking whether geographic pruning blocks valid 1-transfer paths...")
    # pick a well-connected intermediate hub
    for sample_route in sorted(shared)[:3]:
        log(f"  [Sample route {sample_route}]")
        # walk forward from source on this route
        stops_on_route = [SOURCE]
        q = deque([(SOURCE, source_routes[sample_route])])
        visited = {SOURCE}
        while q:
            node, prev_seq = q.popleft()
            for nbr in G.successors(node):
                for ek, ed in G[node][nbr].items():
                    if ed.get("route_id") == sample_route:
                        seq = ed.get("stop_sequence", 0)
                        if seq > prev_seq and nbr not in visited:
                            visited.add(nbr)
                            stops_on_route.append(nbr)
                            q.append((nbr, seq))
                            break
        log(f"    stops forward from source on this route: {len(stops_on_route)}")
        log(f"    destination found on route: {DEST in stops_on_route}")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Run _find_direct_route (official function)
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 5 — _find_direct_route() result")
log("=" * 70)
direct_result = _find_direct_route(G, SOURCE, DEST, log_result=True)
if direct_result:
    path, rid = direct_result
    log(f"  DIRECT ROUTE FOUND: route={rid}  stops={len(path)}")
else:
    log("  DIRECT ROUTE: None found")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Run _transfer_aware_dijkstra (official function)
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 6 — _transfer_aware_dijkstra() result")
log("=" * 70)
dijkstra_path = _transfer_aware_dijkstra(G, SOURCE, DEST)
if dijkstra_path:
    log(f"  PATH FOUND: length={len(dijkstra_path)}")
    log(f"  Path stop IDs: {dijkstra_path}")
    log(f"  Path stop names:")
    for i, sid in enumerate(dijkstra_path):
        sname = G.nodes.get(sid, {}).get("name", "?")
        log(f"    [{i:02d}] {sname} ({sid})")
    transfer_count_raw = _count_transfers(dijkstra_path, G)
    log(f"  _count_transfers() = {transfer_count_raw}")
    log(f"  MAX_TRANSFERS      = {MAX_TRANSFERS}")
else:
    log("  DIJKSTRA: No path found (returned None)")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Simulate _build_route_response transfer counting
# ─────────────────────────────────────────────────────────────────────────────

if dijkstra_path:
    log("=" * 70)
    log("STEP 7 — Simulate leg-walk transfer counting (_build_route_response)")
    log("=" * 70)

    from app.services.routing_service import _best_edge

    current_route = None
    leg_transfers = []

    def pick_edge(u, v, current):
        e = _best_edge(G, u, v, current_route=current)
        return e.get("route_id", "UNKNOWN")

    # First stop: set initial route
    if len(dijkstra_path) > 1:
        current_route = pick_edge(dijkstra_path[0], dijkstra_path[1], None)
        log(f"  Initial route at stop 0: {current_route}")

    for i in range(1, len(dijkstra_path)):
        node = dijkstra_path[i]
        is_last = (i == len(dijkstra_path) - 1)
        if i > 0:
            edge_route = pick_edge(dijkstra_path[i-1], dijkstra_path[i], current_route)
            is_transfer = (current_route is not None and edge_route != current_route and not is_last)
            if is_transfer:
                sname = G.nodes.get(node, {}).get("name", "?")
                leg_transfers.append((i, node, sname, current_route, edge_route))
                log(f"  TRANSFER at [{i:02d}] {sname}: {current_route} -> {edge_route}")
            current_route = edge_route

    log(f"  Total leg-walk transfers: {len(leg_transfers)}")
    log(f"  MAX_TRANSFERS: {MAX_TRANSFERS}")
    if len(leg_transfers) > MAX_TRANSFERS:
        log(f"  *** REJECTION POINT: num_transfers={len(leg_transfers)} > MAX_TRANSFERS={MAX_TRANSFERS} ***")
        log(f"  *** This is the line that causes the 404 in _build_route_response ***")
    else:
        log(f"  Transfer count within limit — route would pass.")
    log()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Route revisit detection (backtrack audit)
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 8 — Route revisit / backtrack detection")
log("=" * 70)

def detect_revisits(path, G):
    seen_ids = {}
    seen_names = {}
    revisit_ids = []
    revisit_names = []
    for i, sid in enumerate(path):
        name = G.nodes.get(sid, {}).get("name", sid)
        if sid in seen_ids:
            revisit_ids.append((i, sid, name, seen_ids[sid]))
        else:
            seen_ids[sid] = i
        if name in seen_names:
            revisit_names.append((i, sid, name, seen_names[name]))
        else:
            seen_names[name] = i
    return revisit_ids, revisit_names

if dijkstra_path:
    rid_revisits, rname_revisits = detect_revisits(dijkstra_path, G)
    log(f"  Stop-ID revisits: {len(rid_revisits)}")
    for item in rid_revisits:
        log(f"    stop_id={item[1]} name={item[2]} first_at={item[3]} revisited_at={item[0]}")
    log(f"  Stop-name revisits: {len(rname_revisits)}")
    for item in rname_revisits[:20]:
        log(f"    name={item[2]} first_at={item[3]} revisited_at={item[0]}")
else:
    log("  (no path to audit)")
log()


# ─────────────────────────────────────────────────────────────────────────────
# 9. NetworkX path check (baseline)
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 70)
log("STEP 9 — NetworkX baseline shortest_path")
log("=" * 70)
try:
    nx_path = nx.shortest_path(G, source=SOURCE, target=DEST, weight="distance_km")
    log(f"  NetworkX path found: {len(nx_path)} stops")
    nx_tc = _count_transfers(nx_path, G)
    log(f"  _count_transfers (nx path): {nx_tc}")
    rid_r, rname_r = detect_revisits(nx_path, G)
    log(f"  Stop-ID revisits in NX path: {len(rid_r)}")
    log(f"  Stop-name revisits in NX path: {len(rname_r)}")
except nx.NetworkXNoPath:
    log("  NetworkX: No path between these stops (graph is truly disconnected here)")
except Exception as ex:
    log(f"  NetworkX error: {ex}")
log()


# ─────────────────────────────────────────────────────────────────────────────
# Write report
# ─────────────────────────────────────────────────────────────────────────────

db.close()
print("\n" + "=" * 70)
print("Investigation complete. See routing_regression_report.md for full report.")
