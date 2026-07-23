"""Detector evaluation against ground-truth anomaly labels."""

from __future__ import annotations

from typing import Iterable

import networkx as nx
import pandas as pd

from src.anomaly_detection import SUPPORTED_ALGORITHMS, detect_anomalies


ALGORITHM_LABELS = {
    "rule_based": "Rule-Based",
    "isolation_forest": "Isolation Forest",
    "local_outlier_factor": "Local Outlier Factor",
    "one_class_svm": "One-Class SVM",
    "consensus": "Consensus",
    "lightweight_gnn": "Lightweight GNN",
}


def evaluate_detection(result_frame: pd.DataFrame, true_anomalies: Iterable[str]) -> dict[str, float]:
    """Score one detection result against the known injected anomalies."""
    truth = {str(node) for node in true_anomalies}
    if result_frame.empty:
        flagged: set[str] = set()
    else:
        flagged = {
            str(node)
            for node in result_frame.loc[result_frame["anomaly_label"] == 1, "node"]
        }

    true_positives = len(flagged & truth)
    false_positives = len(flagged - truth)
    false_negatives = len(truth - flagged)

    precision = true_positives / len(flagged) if flagged else 0.0
    recall = true_positives / len(truth) if truth else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def compare_algorithms(
    metrics: pd.DataFrame,
    true_anomalies: Iterable[str],
    threshold: float = 0.65,
    algorithms: Iterable[str] = SUPPORTED_ALGORITHMS,
    graph: nx.Graph | None = None,
) -> pd.DataFrame:
    """Run every detector on the same features and score each against ground truth.

    ``graph`` is required for ``"lightweight_gnn"``, which is silently skipped
    when no graph is supplied (it cannot run on features alone).
    """
    truth = list(true_anomalies)
    records: list[dict] = []
    for algorithm in algorithms:
        if algorithm == "lightweight_gnn" and graph is None:
            continue
        result = detect_anomalies(metrics, algorithm=algorithm, threshold=threshold, graph=graph).frame
        scores = evaluate_detection(result, truth)
        records.append(
            {
                "algorithm": ALGORITHM_LABELS.get(algorithm, algorithm),
                "flagged": int(result["anomaly_label"].sum()) if not result.empty else 0,
                **scores,
            }
        )
    return pd.DataFrame.from_records(records)
