from __future__ import annotations

import networkx as nx
import pandas as pd

from src.gnn import gcn_autoencoder_detection, gcn_autoencoder_with_profile


def _cluster_graph_with_outlier() -> tuple[nx.Graph, pd.DataFrame]:
    """A tight cluster of similar nodes plus one structurally distinct hub."""
    graph = nx.Graph()
    cluster = [f"N{i}" for i in range(12)]
    graph.add_nodes_from(cluster)
    for i in range(len(cluster)):
        for j in range(i + 1, min(i + 3, len(cluster))):
            graph.add_edge(cluster[i], cluster[j])

    outlier = "HUB"
    graph.add_node(outlier)
    for node in cluster:
        graph.add_edge(outlier, node)

    records = []
    for node in graph.nodes:
        degree = graph.degree(node)
        records.append(
            {
                "node": node,
                "degree": degree,
                "degree_centrality": degree / (graph.number_of_nodes() - 1),
                "betweenness_centrality": 0.8 if node == outlier else 0.01,
                "closeness_centrality": 0.5,
                "eigenvector_centrality": 0.3,
                "pagerank": 0.2 if node == outlier else 0.05,
                "clustering_coefficient": 0.1 if node == outlier else 0.6,
                "component_size": graph.number_of_nodes(),
                "unique_neighbours": degree,
                "new_neighbour_ratio": 0.0,
            }
        )
    return graph, pd.DataFrame.from_records(records)


def test_gcn_autoencoder_returns_detector_contract_columns():
    graph, features = _cluster_graph_with_outlier()
    result = gcn_autoencoder_detection(features, graph)

    assert "anomaly_score" in result.columns
    assert "anomaly_label" in result.columns
    assert "reason_flagged" in result.columns
    assert result["anomaly_score"].between(0, 1).all()
    assert (result["anomaly_label"] == 0).all()  # thresholding happens in detect_anomalies


def test_gcn_autoencoder_never_sees_labels():
    """The detector contract requires unsupervised training — no ground truth as input."""
    import inspect

    signature = inspect.signature(gcn_autoencoder_detection)
    assert "true_anomalies" not in signature.parameters
    assert "labels" not in signature.parameters


def test_resource_profile_reports_a_tiny_model():
    graph, features = _cluster_graph_with_outlier()
    _result, profile = gcn_autoencoder_with_profile(features, graph)

    assert profile.parameter_count > 0
    assert profile.model_size_kb < 50  # a genuinely lightweight model
    assert profile.inference_ms_per_node > 0
    assert profile.target_device == "Raspberry Pi Zero 2 W"
    assert profile.fits_target_ram is True
