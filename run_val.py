"""
Route Planner Bug Fix — Validation Script (with timeout guard)
Runs only the primary + feasible journey tests.
"""
import sys, os, signal, threading
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv()
from app.database.connection import SessionLocal
from app.services.routing_service import (
    build_transit_graph, _find_direct_route,
    _extract_route_segment, resolve_route_dynamic
)
from collections import deque

BUS_SPEED_KMH = 20.0

def pre_fix_bfs_count(G, source_id, dest_id, route_id):
    """Simulate old BFS (used 'continue' at dest instead of 'break')."""
    queue = deque([[source_id]])
    visited = set()
    all_paths = []
    limit = 0
    while queue and limit < 50000:
        limit += 1
        path = queue.popleft()
        node = path[-1]
        if node == dest_id:
            all_paths.append(path)
            continue   # OLD: kept going after destination
        if node in visited:
            continue
        visited.add(node)
        for nbr in G.successors(node):
            if nbr in path:
                continue
            if any(d.get('route_id') == route_id for d in G[node][nbr].values()):
                queue.append(path + [nbr])
    return max((len(p) for p in all_paths), default=0)


def compute_tt(route_path, G):
    ids = [s['stop_id'] for s in route_path]
    total_km = 0.0
    for i in range(len(ids)-1):
        u, v = ids[i], ids[i+1]
        if G.has_node(u) and G.has_node(v) and G.has_edge(u, v):
            total_km += min(d.get('distance_km', 0.5) for d in G[u][v].values())
        else:
            total_km += 0.5
    return round((total_km / BUS_SPEED_KMH) * 60, 2)


def get_seqs(G, source_id, dest_id, route_id):
    src_vals = [d.get('stop_sequence', 0) for nbr in G.successors(source_id)
                for d in G[source_id][nbr].values() if d.get('route_id') == route_id]
    dst_vals = [d.get('stop_sequence', 0) for pred in G.predecessors(dest_id)
                for d in G[pred][dest_id].values() if d.get('route_id') == route_id]
    return (min(src_vals) if src_vals else -1), (max(dst_vals) if dst_vals else -1)


def run_test_with_timeout(db, G, label, src, dst, timeout=30):
    """Run a single test with a wall-clock timeout."""
    result_box = {}
    error_box  = {}

    def worker():
        try:
            r = resolve_route_dynamic(db, src, dst, bus_capacity=60,
                                      traffic='Medium', weather='Clear')
            result_box['result'] = r
        except Exception as e:
            error_box['err'] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        return None, f'TIMEOUT after {timeout}s'
    if 'err' in error_box:
        return None, str(error_box['err'])
    return result_box.get('result'), None


def run_test(db, G, label, src, dst):
    print(f"\n{'='*70}")
    print(f"  TEST: {label}")
    src_name = G.nodes.get(src, {}).get('name', src)
    dst_name = G.nodes.get(dst, {}).get('name', dst)
    print(f"  Source: {src_name} ({src})")
    print(f"  Dest  : {dst_name} ({dst})")
    print(f"{'='*70}")

    route_result, err = run_test_with_timeout(db, G, label, src, dst, timeout=45)
    if err:
        print(f"  ERROR/TIMEOUT: {err}")
        return {
            'label': label, 'src': src, 'dst': dst,
            'src_idx': '?', 'dst_idx': '?',
            'before': '?', 'after': '?',
            'tt_before': '?', 'tt_after': '?',
            'passed': False, 'note': err
        }

    rp   = route_result.get('route_path', [])
    ids  = [s['stop_id'] for s in rp]

    direct = _find_direct_route(G, src, dst, log_result=False)
    rid    = direct[1] if direct else None

    src_idx, dst_idx = get_seqs(G, src, dst, rid) if rid else (-1, -1)
    before   = pre_fix_bfs_count(G, src, dst, rid) if rid else len(ids)
    after    = len(ids)
    tt_after  = compute_tt(rp, G)
    tt_before = round(tt_after * (before / after), 2) if after else tt_after

    dest_pos_in_path = ids.index(dst) if dst in ids else -1
    dest_last  = (ids[-1] == dst) if ids else False
    stops_after = ids[dest_pos_in_path + 1:] if dest_pos_in_path >= 0 else ['DEST_NOT_FOUND']
    no_after   = len(stops_after) == 0
    no_loops   = len(ids) == len(set(ids))
    passed     = dest_last and no_after and no_loops

    print(f"  route_id        : {rid}")
    print(f"  source_index    : {src_idx}")
    print(f"  dest_index      : {dst_idx}")
    print(f"  stops BEFORE fix: {before}")
    print(f"  stops AFTER  fix: {after}")
    print(f"  travel BEFORE   : {tt_before} min")
    print(f"  travel AFTER    : {tt_after} min")
    print(f"  dest is last    : {dest_last}")
    print(f"  no stops after  : {no_after}  (stops after dest: {stops_after})")
    print(f"  no loops        : {no_loops}")
    print(f"  VERDICT         : {'PASS' if passed else 'FAIL'}")

    print(f"\n  Stop sequence ({after} stops):")
    for i, s in enumerate(rp):
        marker = ' <-- DESTINATION' if s['stop_id'] == dst else ''
        unexp  = ' !!UNEXPECTED'    if (dest_pos_in_path >= 0 and i > dest_pos_in_path) else ''
        print(f"    [{i:2d}] {s['stop_id']:<8} {s['stop_name']:<40}{marker}{unexp}")

    return {
        'label': label, 'src': src, 'dst': dst,
        'src_idx': src_idx, 'dst_idx': dst_idx,
        'before': before, 'after': after,
        'tt_before': tt_before, 'tt_after': tt_after,
        'passed': passed, 'note': ''
    }


# ── Main ──────────────────────────────────────────────────────────────────────
print('Building transit graph...')
db = SessionLocal()
G  = build_transit_graph(db)
print(f'Graph ready: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n')

print('Stop-ID verification:')
for sid, sname in [('21454','Ambedkar Inst of Tech'),('21517','Goraguntepalya'),('21630','BHEL')]:
    n = G.nodes.get(sid, {})
    print(f'  stop {sid}: found={G.has_node(sid)}, db_name={n.get("name","NOT FOUND")}')

tests = [
    ('21454->21517 Ambedkar->Goraguntepalya [PRIMARY]',  '21454', '21517'),
    ('21630->21454 BHEL->Ambedkar',                      '21630', '21454'),
    ('21630->21517 BHEL->Goraguntepalya [LONGER]',       '21630', '21517'),
    ('21517->21454 Goraguntepalya->Ambedkar [REVERSE]',  '21517', '21454'),
]

rows = []
for label, src, dst in tests:
    rows.append(run_test(db, G, label, src, dst))

db.close()

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n\n{'='*80}")
print('VALIDATION SUMMARY REPORT')
print(f"{'='*80}")
print(f"  {'Test':<44} {'src_i':>5} {'dst_i':>5} {'bef':>5} {'aft':>5} {'TT_bef':>7} {'TT_aft':>7} {'Result':>6}")
print(f"  {'-'*44} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*7} {'-'*7} {'-'*6}")
for r in rows:
    note = f" ({r['note']})" if r.get('note') else ''
    print(
        f"  {r['label'][:44]:<44} "
        f"{str(r['src_idx']):>5} "
        f"{str(r['dst_idx']):>5} "
        f"{str(r['before']):>5} "
        f"{str(r['after']):>5} "
        f"{str(r['tt_before']):>7} "
        f"{str(r['tt_after']):>7} "
        f"{'PASS' if r['passed'] else 'FAIL':>6}{note}"
    )

passed = sum(1 for r in rows if r['passed'])
print(f"\n  Overall: {passed}/{len(rows)} tests passed")
print(f"{'='*80}")
