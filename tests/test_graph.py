from __future__ import annotations

import pandas as pd

from src.graph_builder import build_graph
from src.loader import load_network_data


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

