from src.graph.discovery import build_discovery_subgraph
from src.graph.followup import build_followup_subgraph
from src.graph.poc import build_poc_subgraph
from src.graph.proposal import build_proposal_subgraph


def test_discovery_subgraph_compiles():
    sg = build_discovery_subgraph()
    compiled = sg.compile()
    assert compiled is not None


def test_poc_subgraph_compiles():
    sg = build_poc_subgraph()
    compiled = sg.compile()
    assert compiled is not None


def test_proposal_subgraph_compiles():
    sg = build_proposal_subgraph()
    compiled = sg.compile()
    assert compiled is not None


def test_followup_subgraph_compiles():
    sg = build_followup_subgraph()
    compiled = sg.compile()
    assert compiled is not None
