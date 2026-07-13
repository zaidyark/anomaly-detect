from __future__ import annotations

import pytest

from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_node_metrics
from src.scenarios import generate_scenario, list_scenarios


def test_list_scenarios_exposes_metadata():
    scenarios = list_scenarios()
    assert len(scenarios) >= 4
    for entry in scenarios:
        assert entry["key"]
        assert entry["name"]
        assert entry["description"]


@pytest.mark.parametrize("key", [entry["key"] for entry in list_scenarios()])
def test_generated_scenarios_pass_loader_validation(key):
    result = generate_scenario(key)
    frame = load_network_data(result.frame)
    assert not frame.empty
    assert result.true_anomalies

    graph = build_graph(frame).graph
    node_names = {str(node) for node in graph.nodes}
    for anomalous_node in result.true_anomalies:
        assert anomalous_node in node_names


def test_generation_is_deterministic():
    first = generate_scenario("scanner", seed=7)
    second = generate_scenario("scanner", seed=7)
    assert first.frame.equals(second.frame)
    assert first.true_anomalies == second.true_anomalies


def test_unknown_scenario_raises():
    with pytest.raises(ValueError):
        generate_scenario("does-not-exist")


def test_scanner_dominates_degree_metrics():
    result = generate_scenario("scanner")
    frame = load_network_data(result.frame)
    build_result = build_graph(frame)
    metrics = compute_node_metrics(build_result.graph, build_result.edge_frame)
    top_degree_node = metrics.sort_values("degree", ascending=False).iloc[0]["node"]
    scanner = result.true_anomalies[0]
    top_new_ratio = metrics.sort_values("new_neighbour_ratio", ascending=False).head(5)["node"].tolist()
    assert top_degree_node == scanner or scanner in top_new_ratio
