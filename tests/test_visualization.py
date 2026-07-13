from __future__ import annotations

import pandas as pd

from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_node_metrics
from src.visualization import create_cytoscape_elements, create_cytoscape_stylesheet


def _sample_graph():
    frame = load_network_data(
        pd.DataFrame(
            [
                {"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:00", "protocol": "tcp"},
                {"source": "B", "destination": "C", "timestamp": "2025-01-01 00:01:00", "protocol": "udp"},
            ]
        )
    )
    build_result = build_graph(frame, directed=False)
    metrics = compute_node_metrics(build_result.graph, build_result.edge_frame)
    return build_result.graph, metrics


def test_cytoscape_elements_include_nodes_and_edges():
    graph, metrics = _sample_graph()
    elements = create_cytoscape_elements(graph, metrics)

    node_elements = [el for el in elements if "id" in el["data"]]
    edge_elements = [el for el in elements if "source" in el["data"]]

    assert len(node_elements) == 3
    assert len(edge_elements) == 2
    assert all("community-" in el["classes"] for el in node_elements)


def test_highlighted_node_gets_selected_class():
    graph, metrics = _sample_graph()
    elements = create_cytoscape_elements(graph, metrics, highlighted_nodes=["A"])
    node_a = next(el for el in elements if el["data"].get("id") == "A")

    assert "selected" in node_a["classes"]


def test_node_severity_follows_detection_labels_at_low_threshold():
    graph, metrics = _sample_graph()
    anomalies = pd.DataFrame(
        [
            {"node": "A", "anomaly_score": 0.3, "anomaly_label": 1},
            {"node": "B", "anomaly_score": 0.16, "anomaly_label": 0},
            {"node": "C", "anomaly_score": 0.05, "anomaly_label": 0},
        ]
    )
    elements = create_cytoscape_elements(graph, metrics, anomalies, threshold=0.2)
    classes = {el["data"]["id"]: el["classes"] for el in elements if "id" in el["data"]}

    assert "anomaly" in classes["A"]  # flagged, even though its raw score is low
    assert "warning" in classes["B"]  # unflagged but close to the threshold
    assert "normal" in classes["C"]


def test_stylesheet_modes_produce_different_rules():
    anomaly_stylesheet = create_cytoscape_stylesheet(color_mode="anomaly")
    community_stylesheet = create_cytoscape_stylesheet(color_mode="community")

    anomaly_selectors = {rule["selector"] for rule in anomaly_stylesheet}
    community_selectors = {rule["selector"] for rule in community_stylesheet}

    assert "node.anomaly" in anomaly_selectors
    assert "node.community-0" in community_selectors
    assert "node.anomaly" not in community_selectors
