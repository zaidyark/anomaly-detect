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


def _synthetic_feature_frame(size: int = 12) -> pd.DataFrame:
    rows = []
    for index in range(size):
        rows.append(
            {
                "node": f"PC{index}",
                "degree": 2 + index % 3,
                "degree_centrality": 0.1,
                "betweenness_centrality": 0.02,
                "closeness_centrality": 0.2,
                "eigenvector_centrality": 0.05,
                "pagerank": 0.05,
                "clustering_coefficient": 0.4,
                "component_id": 1,
                "component_size": size + 1,
                "unique_neighbours": 2,
                "new_neighbour_ratio": 0.0,
                "is_bridge": 0,
            }
        )
    rows.append(
        {
            "node": "ATTACKER",
            "degree": 40,
            "degree_centrality": 0.9,
            "betweenness_centrality": 0.85,
            "closeness_centrality": 0.6,
            "eigenvector_centrality": 0.5,
            "pagerank": 0.4,
            "clustering_coefficient": 0.01,
            "component_id": 1,
            "component_size": size + 1,
            "unique_neighbours": 30,
            "new_neighbour_ratio": 0.95,
            "is_bridge": 1,
        }
    )
    return pd.DataFrame(rows)


def test_consensus_detector_combines_votes():
    frame = _synthetic_feature_frame()
    result = detect_anomalies(frame, algorithm="consensus", threshold=0.6).frame

    assert "detector_votes" in result.columns
    attacker = result.loc[result["node"] == "ATTACKER"].iloc[0]
    assert attacker["anomaly_label"] == 1
    assert attacker["detector_votes"] >= 2
    assert "detectors" in attacker["reason_flagged"]
    assert result["anomaly_score"].between(0, 1).all()


