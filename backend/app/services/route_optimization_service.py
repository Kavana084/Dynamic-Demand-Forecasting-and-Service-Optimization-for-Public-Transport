import math
import logging
from typing import List, Dict, Any, Optional

import networkx as nx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Traffic-congestion weight multipliers applied to each edge
# ---------------------------------------------------------------------------
TRAFFIC_MULT  = {"Low": 1.0, "Medium": 1.2, "High": 1.5, "Heavy": 2.0}
WEATHER_MULT  = {"Clear": 1.0, "Cloudy": 1.05, "Rainy": 1.2, "Storm": 1.5}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two GPS coordinates."""
    R = 6371.0
    try:
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except Exception:
        return 0.5  # safe default 500 m


class RouteOptimizationService:
    """
    Builds a lightweight in-memory graph from a route_path payload and
    finds the optimal loop-free path between the first and last stops.
    """

    # ------------------------------------------------------------------
    # Graph Construction
    # ------------------------------------------------------------------
    def _build_graph(
        self,
        route_path: List[Dict[str, Any]],
        traffic:    str = "Medium",
        weather:    str = "Clear",
    ) -> nx.DiGraph:
        G = nx.DiGraph()

        traffic_w = TRAFFIC_MULT.get(traffic, 1.2)
        weather_w = WEATHER_MULT.get(weather, 1.0)

        for stop in route_path:
            sid = stop.get("stop_id")
            if sid:
                G.add_node(
                    sid,
                    name=stop.get("stop_name", sid),
                    lat=stop.get("lat"),
                    lon=stop.get("lon"),
                )

        for i in range(len(route_path) - 1):
            u = route_path[i]
            v = route_path[i + 1]
            uid, vid = u.get("stop_id"), v.get("stop_id")
            if not uid or not vid or uid == vid:
                continue

            dist_km = _haversine(
                u.get("lat", 0), u.get("lon", 0),
                v.get("lat", 0), v.get("lon", 0),
            )
            # Weighted cost: distance × traffic × weather
            weight = dist_km * traffic_w * weather_w
            G.add_edge(uid, vid, weight=max(0.01, weight), distance_km=dist_km)

        return G

    # ------------------------------------------------------------------
    # Shortest Loop-Free Path
    # ------------------------------------------------------------------
    def _shortest_loop_free_path(
        self,
        G: nx.DiGraph,
        source: str,
        target: str,
    ) -> Optional[List[str]]:
        """
        Run Dijkstra and validate the result is free of repeated nodes.
        Falls back to the original ordered node sequence if no valid path found.
        """
        try:
            path = nx.shortest_path(G, source=source, target=target, weight="weight")
            if len(path) == len(set(path)):        # no cycles
                return path
            # Cycle found — remove repeated nodes deterministically
            seen:       set            = set()
            clean_path: List[str]      = []
            for node in path:
                if node not in seen:
                    seen.add(node)
                    clean_path.append(node)
            return clean_path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    # ------------------------------------------------------------------
    # Route Efficiency Score
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_efficiency(
        original_len: int,
        optimized_len: int,
        traffic: str,
        weather: str,
        transfers: int = 0,
    ) -> int:
        """
        Score reflects how much we improved vs the raw path.
        Base 100 → deduct for congestion, weather, and excess stops.
        """
        score = 100

        # Penalise unused stops in optimized path
        if original_len > 0:
            ratio = optimized_len / original_len
            score -= int(max(0, ratio - 1.0) * 30)   # penalise detours heavily
            if ratio > 1.5:
                score -= 15 # extra penalty for long detours/loops

        # Traffic penalty
        traffic_penalty = {"Low": 0, "Medium": 5, "High": 15, "Heavy": 25}
        score -= traffic_penalty.get(traffic, 5)

        # Weather penalty
        weather_penalty = {"Clear": 0, "Cloudy": 3, "Rainy": 8, "Storm": 18}
        score -= weather_penalty.get(weather, 0)
        
        # Transfers penalty
        if transfers > 0:
            score -= (transfers * 15) # heavy penalty for excessive transfers

        return max(0, min(100, score))

    # ------------------------------------------------------------------
    # Public Interface
    # ------------------------------------------------------------------
    def optimize(
        self,
        route_path: List[Dict[str, Any]],
        traffic:    str = "Medium",
        weather:    str = "Clear",
        transfers:  int = 0,
    ) -> dict:
        """
        Parameters
        ----------
        route_path : List of stop dicts with keys stop_id, stop_name, lat, lon.
        traffic    : "Low" | "Medium" | "High" | "Heavy"
        weather    : "Clear" | "Cloudy" | "Rainy" | "Storm"

        Returns
        -------
        {
            "optimized_route"  : [{"stop_id": ..., "stop_name": ..., "lat": ..., "lon": ...}],
            "route_efficiency" : int   # 0-100
        }
        """
        if not route_path or len(route_path) < 2:
            return {
                "optimized_route"  : route_path or [],
                "route_efficiency" : 70,
            }

        try:
            G      = self._build_graph(route_path, traffic, weather)
            source = route_path[0].get("stop_id")
            target = route_path[-1].get("stop_id")

            if not source or not target or source not in G or target not in G:
                raise ValueError("Source or target stop not in graph")

            path = self._shortest_loop_free_path(G, source, target)

            if path:
                optimized_route = [
                    {
                        "stop_id"  : n,
                        "stop_name": G.nodes[n].get("name", n),
                        "lat"      : G.nodes[n].get("lat"),
                        "lon"      : G.nodes[n].get("lon"),
                    }
                    for n in path
                    if n in G.nodes
                ]
            else:
                # Fallback: return original path deduplicated
                logger.warning("No path found — returning deduplicated original route")
                seen: set = set()
                optimized_route = []
                for stop in route_path:
                    sid = stop.get("stop_id")
                    if sid and sid not in seen:
                        seen.add(sid)
                        optimized_route.append(stop)

            efficiency = self._compute_efficiency(
                len(route_path), len(optimized_route), traffic, weather, transfers
            )

            return {
                "optimized_route"  : optimized_route,
                "route_efficiency" : efficiency,
            }

        except Exception as exc:
            logger.error(f"Route optimization error: {exc}")
            return {
                "optimized_route"  : route_path,
                "route_efficiency" : 65,
            }


# Module-level singleton
route_optimization_service = RouteOptimizationService()
