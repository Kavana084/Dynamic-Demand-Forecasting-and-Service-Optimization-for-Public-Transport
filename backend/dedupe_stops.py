"""
Deduplicate near-duplicate stops in gtfs_stops and remap all foreign-key
references (gtfs_stop_times, route_plan_logs, journey_history) to a single
canonical stop_id per real-world location.

SAFE TO RE-RUN: if there are no more duplicate clusters, it will do nothing.
Always backs up the DB before touching it.
"""

import sqlite3
import shutil
import datetime
from math import radians, sin, cos, sqrt, atan2

DB_PATH = "transit_ai.db"
DIST_THRESHOLD_M = 150  # stops within this distance + same name = same real stop


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def backup_db(path):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.backup_{ts}"
    shutil.copy2(path, backup_path)
    print(f"[backup] Copied {path} -> {backup_path}")
    return backup_path


def main():
    backup_db(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ---- 1. Load all stops ----
    cur.execute("SELECT stop_id, stop_name, stop_lat, stop_lon FROM gtfs_stops")
    stops = cur.fetchall()
    print(f"[load] {len(stops)} stops loaded")

    # Group by normalized name
    from collections import defaultdict
    by_name = defaultdict(list)
    for stop_id, name, lat, lon in stops:
        key = (name or "").strip().lower()
        by_name[key].append((stop_id, lat, lon))

    # ---- 2. Get reference counts per stop_id from gtfs_stop_times ----
    cur.execute("SELECT stop_id, COUNT(*) FROM gtfs_stop_times GROUP BY stop_id")
    ref_counts = dict(cur.fetchall())

    # ---- 3. Build clusters within each name group ----
    clusters = []
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        n = len(group)
        visited = set()
        for i in range(n):
            if i in visited:
                continue
            cluster = [i]
            for j in range(i + 1, n):
                if j in visited:
                    continue
                d = haversine_m(group[i][1], group[i][2], group[j][1], group[j][2])
                if d < DIST_THRESHOLD_M:
                    cluster.append(j)
                    visited.add(j)
            if len(cluster) > 1:
                visited.add(i)
                clusters.append([group[k][0] for k in cluster])  # list of stop_ids

    print(f"[cluster] {len(clusters)} duplicate clusters found "
          f"({sum(len(c) for c in clusters)} stops involved)")

    # ---- 4. Pick canonical stop_id per cluster ----
    id_map = {}  # old_stop_id -> canonical_stop_id
    for cluster in clusters:
        # sort by (ref_count desc, stop_id asc) -> canonical is first
        ranked = sorted(cluster, key=lambda sid: (-ref_counts.get(sid, 0), sid))
        canonical = ranked[0]
        for sid in ranked[1:]:
            id_map[sid] = canonical

    print(f"[map] {len(id_map)} stop_ids will be merged into canonical IDs")

    if not id_map:
        print("[done] No duplicates to merge. Nothing changed.")
        conn.close()
        return

    # ---- 5. Create temp mapping table ----
    cur.execute("DROP TABLE IF EXISTS _stop_id_map")
    cur.execute("CREATE TEMP TABLE _stop_id_map (old_id INTEGER PRIMARY KEY, new_id INTEGER)")
    cur.executemany("INSERT INTO _stop_id_map (old_id, new_id) VALUES (?, ?)", list(id_map.items()))

    # Helpful index for the big table, if not already present
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gtfs_stop_times_stop_id ON gtfs_stop_times(stop_id)")

    # ---- 6. Remap references ----
    def remap(table, column):
        cur.execute(f"""
            UPDATE {table}
            SET {column} = (SELECT new_id FROM _stop_id_map WHERE old_id = {table}.{column})
            WHERE {column} IN (SELECT old_id FROM _stop_id_map)
        """)
        print(f"[remap] {table}.{column}: {cur.rowcount} rows updated")

    remap("gtfs_stop_times", "stop_id")
    remap("route_plan_logs", "source_stop_id")
    remap("route_plan_logs", "destination_stop_id")
    remap("journey_history", "source_stop_id")
    remap("journey_history", "destination_stop_id")

    # ---- 7. Delete orphaned duplicate stop rows ----
    cur.execute("""
        DELETE FROM gtfs_stops
        WHERE stop_id IN (SELECT old_id FROM _stop_id_map)
    """)
    print(f"[cleanup] {cur.rowcount} duplicate rows deleted from gtfs_stops")

    cur.execute("DROP TABLE _stop_id_map")

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM gtfs_stops")
    print(f"[done] gtfs_stops now has {cur.fetchone()[0]} rows (was {len(stops)})")

    conn.close()


if __name__ == "__main__":
    main()