import os
import sys
from collections import OrderedDict

import networkx as nx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import routing_service as rs


def _build_test_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.add_node("H1", name="Hub One", lat=12.0, lon=77.0)
    graph.add_node("M1", name="Mid One", lat=12.1, lon=77.1)
    graph.add_node("M2", name="Mid Two", lat=12.2, lon=77.2)
    graph.add_node("H2", name="Hub Two", lat=12.3, lon=77.3)

    graph.add_edge("H1", "M1", route_id="R1", distance_km=1.0, weight=1.0)
    graph.add_edge("M1", "H2", route_id="R1", distance_km=1.2, weight=1.2)
    graph.add_edge("H1", "M2", route_id="R2", distance_km=1.5, weight=1.5)
    graph.add_edge("M2", "H2", route_id="R2", distance_km=1.4, weight=1.4)
    graph.add_edge("H2", "M1", route_id="R3", distance_km=1.1, weight=1.1)
    graph.add_edge("M1", "H1", route_id="R3", distance_km=1.0, weight=1.0)
    return graph


@pytest.fixture(autouse=True)
def reset_routing_globals(monkeypatch):
    monkeypatch.setattr(rs, "transit_graph_cache", None)
    monkeypatch.setattr(rs, "route_cache", OrderedDict())
    monkeypatch.setattr(rs, "hub_cache", {})
    monkeypatch.setattr(rs, "route_cache_hits", 0)
    monkeypatch.setattr(rs, "route_cache_misses", 0)
    monkeypatch.setattr(rs, "route_cache_evictions", 0)
    monkeypatch.setattr(rs, "HUB_STOPS", ["H1", "H2"])
    monkeypatch.setattr(rs, "HUB_STOP_SET", {"H1", "H2"})


def test_resolve_route_uses_hub_cache_for_hub_pairs(monkeypatch):
    graph = _build_test_graph()
    monkeypatch.setattr(rs, "build_transit_graph", lambda db: graph)
    monkeypatch.setattr(rs, "_get_cached_route", lambda *args, **kwargs: None)
    monkeypatch.setattr(rs, "hub_cache", {("H1", "H2"): ["H1", "M1", "H2"]})

    def fail_if_called(*args, **kwargs):
        raise AssertionError("normal path computation should not run for a hub cache hit")

    monkeypatch.setattr(rs, "_compute_best_path", fail_if_called)

    response = rs.resolve_route_dynamic(db=None, source_id="H1", destination_id="H2")

    assert [stop["stop_id"] for stop in response["path"]] == ["H1", "M1", "H2"]
    assert ("H1", "H2", 60) in rs.route_cache


def test_resolve_route_falls_back_to_normal_path_when_hub_cache_misses(monkeypatch):
    graph = _build_test_graph()
    monkeypatch.setattr(rs, "build_transit_graph", lambda db: graph)
    monkeypatch.setattr(rs, "_get_cached_route", lambda *args, **kwargs: None)
    monkeypatch.setattr(rs, "hub_cache", {})

    calls = {"count": 0}

    def fake_compute_best_path(G, source_id, destination_id, log_strategy=True):
        calls["count"] += 1
        assert source_id == "H1"
        assert destination_id == "H2"
        return ["H1", "M2", "H2"]

    monkeypatch.setattr(rs, "_compute_best_path", fake_compute_best_path)

    response = rs.resolve_route_dynamic(db=None, source_id="H1", destination_id="H2")

    assert calls["count"] == 1
    assert [stop["stop_id"] for stop in response["path"]] == ["H1", "M2", "H2"]


def test_warm_common_route_cache_only_warms_configured_routes(monkeypatch):
    graph = _build_test_graph()
    monkeypatch.setattr(rs, "build_transit_graph", lambda db: graph)
    monkeypatch.setattr(
        rs,
        "COMMON_FREQUENT_ROUTES",
        [("H1", "H2"), ("H2", "H1"), ("UNKNOWN", "H2")],
    )
    monkeypatch.setattr(rs, "hub_cache", {("H1", "H2"): ["H1", "M1", "H2"]})

    calls = {"count": 0}

    def fake_compute_best_path(G, source_id, destination_id, log_strategy=True):
        calls["count"] += 1
        return ["H2", "M1", "H1"]

    monkeypatch.setattr(rs, "_compute_best_path", fake_compute_best_path)

    stats = rs.warm_common_route_cache(db=None, bus_capacity=60)

    assert stats["warmed_routes"] == 2
    assert stats["skipped_routes"] == 1
    assert calls["count"] == 1
    assert ("H1", "H2", 60) in rs.route_cache
    assert ("H2", "H1", 60) in rs.route_cache
