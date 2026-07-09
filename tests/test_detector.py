from __future__ import annotations

import pandas as pd

from src.anomaly_detection import detect_anomalies


def test_rule_based_detector_returns_scores_and_labels():
    frame = pd.DataFrame(
        [
            {
                "node": "A",
                "degree": 30,
                "degree_centrality": 0.7,
                "betweenness_centrality": 0.8,
                "closeness_centrality": 0.3,
                "eigenvector_centrality": 0.2,
                "pagerank": 0.25,
                "clustering_coefficient": 0.05,
                "component_id": 1,
                "component_size": 4,
                "unique_neighbours": 10,
                "new_neighbour_ratio": 0.9,
                "is_bridge": 1,
            },
            {
                "node": "B",
                "degree": 2,
                "degree_centrality": 0.1,
                "betweenness_centrality": 0.01,
                "closeness_centrality": 0.2,
                "eigenvector_centrality": 0.05,
                "pagerank": 0.05,
                "clustering_coefficient": 0.4,
                "component_id": 1,
                "component_size": 4,
                "unique_neighbours": 2,
                "new_neighbour_ratio": 0.0,
                "is_bridge": 0,
            },
        ]
    )
    result = detect_anomalies(frame, algorithm="rule_based", threshold=0.5).frame

    assert "anomaly_score" in result.columns
    assert "anomaly_label" in result.columns
    assert result.loc[result["node"] == "A", "anomaly_label"].iloc[0] == 1
    assert result.loc[result["node"] == "A", "reason_flagged"].iloc[0]

