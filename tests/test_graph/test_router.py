import pytest

from src.graph.router import build_router_graph, route_by_phase


def test_route_by_phase():
    assert route_by_phase({"phase": "discovery"}) == "discovery_subgraph"
    assert route_by_phase({"phase": "poc"}) == "poc_subgraph"
    assert route_by_phase({"phase": "proposal"}) == "proposal_subgraph"
    assert route_by_phase({"phase": "followup"}) == "followup_subgraph"
    assert route_by_phase({"phase": "closed_won"}) == "discovery_subgraph"  # fallback
    assert route_by_phase({}) == "discovery_subgraph"  # missing phase


def test_graph_compiles():
    graph = build_router_graph()
    compiled = graph.compile()
    assert compiled is not None
