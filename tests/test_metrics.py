from __future__ import annotations

import pandas as pd

from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_graph_statistics, compute_node_metrics


def test_metrics_include_expected_columns():
    frame = load_network_data(
        pd.DataFrame(
            [
                {"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:00", "protocol": "tcp"},
                {"source": "B", "destination": "C", "timestamp": "2025-01-01 00:01:00", "protocol": "udp"},
                {"source": "C", "destination": "A", "timestamp": "2025-01-01 00:02:00", "protocol": "icmp"},
            ]
        )
    )
    graph = build_graph(frame).graph
    metrics = compute_node_metrics(graph, frame)
    stats = compute_graph_statistics(graph)

    assert {"node", "degree", "pagerank", "clustering_coefficient", "community_id"}.issubset(metrics.columns)
    assert stats.nodes == 3
    assert stats.edges == 3
    assert stats.density > 0
    assert metrics["community_id"].notna().all()

