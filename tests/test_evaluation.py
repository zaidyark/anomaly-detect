from __future__ import annotations

import pandas as pd

from src.anomaly_detection import SUPPORTED_ALGORITHMS
from src.evaluation import compare_algorithms, evaluate_detection
from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_node_metrics
from src.scenarios import generate_scenario


def _result_frame(flagged: dict[str, int]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"node": node, "anomaly_label": label, "anomaly_score": float(label)} for node, label in flagged.items()]
    )


def test_perfect_detection_scores_one():
    result = _result_frame({"A": 1, "B": 0, "C": 0})
    scores = evaluate_detection(result, ["A"])
    assert scores["precision"] == 1.0
    assert scores["recall"] == 1.0
    assert scores["f1"] == 1.0


def test_partial_detection_scores_between_zero_and_one():
    result = _result_frame({"A": 1, "B": 1, "C": 0, "D": 0})
    scores = evaluate_detection(result, ["A", "C"])
    assert scores["true_positives"] == 1
    assert scores["false_positives"] == 1
    assert scores["false_negatives"] == 1
    assert scores["precision"] == 0.5
    assert scores["recall"] == 0.5


def test_no_flags_yields_zero_scores():
    result = _result_frame({"A": 0, "B": 0})
    scores = evaluate_detection(result, ["A"])
    assert scores["precision"] == 0.0
    assert scores["recall"] == 0.0
    assert scores["f1"] == 0.0


def test_compare_algorithms_covers_every_detector():
    scenario = generate_scenario("scanner")
    frame = load_network_data(scenario.frame)
    build_result = build_graph(frame)
    metrics = compute_node_metrics(build_result.graph, build_result.edge_frame)

    evaluation = compare_algorithms(metrics, scenario.true_anomalies, threshold=0.65)

    assert len(evaluation) == len(SUPPORTED_ALGORITHMS)
    for column in ("algorithm", "precision", "recall", "f1", "flagged"):
        assert column in evaluation.columns
    assert evaluation["recall"].max() > 0
