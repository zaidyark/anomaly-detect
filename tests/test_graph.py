from __future__ import annotations

import pandas as pd

from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_graph_statistics, compute_node_metrics


def test_graph_construction_creates_expected_nodes_and_edges():
    frame = load_network_data(
        pd.DataFrame(
            [
                {"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:00", "protocol": "tcp"},
                {"source": "B", "destination": "C", "timestamp": "2025-01-01 00:01:00", "protocol": "udp"},
            ]
        )
    )

    result = build_graph(frame, directed=False)
    assert result.graph.number_of_nodes() == 3
    assert result.graph.number_of_edges() == 2
    assert result.graph.has_edge("A", "B")


def test_repeated_edges_are_aggregated_with_weight():
    frame = load_network_data(
        pd.DataFrame(
            [
                {"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:00", "protocol": "tcp"},
                {"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:10", "protocol": "tcp"},
            ]
        )
    )

    result = build_graph(frame, directed=False)
    assert result.graph.number_of_edges() == 1
    assert result.graph["A"]["B"]["weight"] == 2


def test_single_node_graph_metrics_do_not_error():
    frame = load_network_data(
        pd.DataFrame(
            [{"source": "A", "destination": "A", "timestamp": "2025-01-01 00:00:00", "protocol": "tcp"}]
        )
    )

    graph = build_graph(frame, directed=False).graph
    metrics = compute_node_metrics(graph, frame)
    stats = compute_graph_statistics(graph)

    assert stats.nodes == 1
    assert len(metrics) == 1


def test_empty_graph_metrics_returns_empty_frame_with_expected_columns():
    import networkx as nx

    empty_graph = nx.Graph()
    metrics = compute_node_metrics(empty_graph)
    stats = compute_graph_statistics(empty_graph)

    assert metrics.empty
    assert "community_id" in metrics.columns
    assert stats.nodes == 0
    assert stats.density == 0.0

