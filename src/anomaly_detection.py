"""Anomaly detection algorithms for graph features."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import OneClassSVM

from src.preprocessing import scale_features, select_feature_frame


BASE_ALGORITHMS = ("rule_based", "isolation_forest", "local_outlier_factor", "one_class_svm")
SUPPORTED_ALGORITHMS = BASE_ALGORITHMS + ("consensus",)

ALGORITHM_DISPLAY_NAMES = {
    "rule_based": "Rule-Based",
    "isolation_forest": "Isolation Forest",
    "local_outlier_factor": "LOF",
    "one_class_svm": "One-Class SVM",
}


@dataclass(frozen=True)
class DetectionResult:
    """Tabular anomaly result."""

    frame: pd.DataFrame
    algorithm: str


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    scaler = MinMaxScaler()
    reshaped = scores.reshape(-1, 1)
    return scaler.fit_transform(reshaped).ravel()


def _build_reason_row(row: pd.Series, thresholds: dict[str, float]) -> str:
    reasons: list[str] = []
    if row["degree"] >= thresholds["degree"]:
        reasons.append("Very high degree")
    if row["betweenness_centrality"] >= thresholds["betweenness"]:
        reasons.append("Very high betweenness")
    if row["new_neighbour_ratio"] >= thresholds["new_neighbours"]:
        reasons.append("Too many new neighbours")
    if row["is_bridge"] == 1 and row["clustering_coefficient"] <= thresholds["bridge_clustering"]:
        reasons.append("Isolated bridge")
    return "; ".join(reasons) if reasons else "Model score above threshold"


def _rule_based_detection(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    thresholds = {
        "degree": float(frame["degree"].mean() + 1.5 * frame["degree"].std(ddof=0)),
        "betweenness": float(frame["betweenness_centrality"].mean() + 1.5 * frame["betweenness_centrality"].std(ddof=0)),
        "new_neighbours": float(frame["new_neighbour_ratio"].mean() + frame["new_neighbour_ratio"].std(ddof=0)),
        "bridge_clustering": float(frame["clustering_coefficient"].median()),
    }
    if np.isnan(thresholds["degree"]):
        thresholds["degree"] = 0.0
    if np.isnan(thresholds["betweenness"]):
        thresholds["betweenness"] = 0.0
    if np.isnan(thresholds["new_neighbours"]):
        thresholds["new_neighbours"] = 0.0
    if np.isnan(thresholds["bridge_clustering"]):
        thresholds["bridge_clustering"] = 1.0

    score = (
        0.35 * _normalize_scores(frame["degree"].to_numpy())
        + 0.35 * _normalize_scores(frame["betweenness_centrality"].to_numpy())
        + 0.15 * _normalize_scores(frame["new_neighbour_ratio"].to_numpy())
        + 0.15 * _normalize_scores(frame["is_bridge"].to_numpy().astype(float))
    )
    frame["anomaly_score"] = score
    frame["anomaly_label"] = (score >= 0.65).astype(int)
    frame["reason_flagged"] = frame.apply(lambda row: _build_reason_row(row, thresholds), axis=1)
    return frame


def _model_detection(features: pd.DataFrame, algorithm: str) -> pd.DataFrame:
    model_frame = select_feature_frame(features)
    scaled = scale_features(model_frame)
    if algorithm == "isolation_forest":
        model = IsolationForest(n_estimators=200, contamination=0.15, random_state=42)
        model.fit(scaled)
        raw_scores = -model.score_samples(scaled)
        labels = (model.predict(scaled) == -1).astype(int)
    elif algorithm == "local_outlier_factor":
        n_neighbors = min(20, max(2, len(scaled) - 1))
        model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=0.15)
        labels = (model.fit_predict(scaled) == -1).astype(int)
        raw_scores = -model.negative_outlier_factor_
    elif algorithm == "one_class_svm":
        model = OneClassSVM(kernel="rbf", nu=0.15, gamma="scale")
        model.fit(scaled)
        labels = (model.predict(scaled) == -1).astype(int)
        raw_scores = -model.decision_function(scaled)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    normalized = _normalize_scores(np.asarray(raw_scores, dtype=float))
    result = features.copy()
    result["anomaly_score"] = normalized
    result["anomaly_label"] = labels.astype(int)
    result["reason_flagged"] = np.where(
        result["anomaly_label"].astype(bool),
        f"{algorithm.replace('_', ' ').title()} flagged node",
        "Within expected behavior",
    )
    return result


def _consensus_detection(features: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Run every base detector and combine them by majority vote.

    A node's consensus score is the mean of the per-detector scores, and it is
    flagged when at least half of the detectors flag it — high-confidence
    anomalies are the ones several independent methods agree on.
    """
    votes = pd.Series(0, index=features.index, dtype=int)
    score_sum = pd.Series(0.0, index=features.index, dtype=float)
    flagged_by: dict[str, list[str]] = {str(node): [] for node in features["node"]}

    for algorithm in BASE_ALGORITHMS:
        result = detect_anomalies(features, algorithm=algorithm, threshold=threshold).frame
        indexed = result.set_index("node")
        aligned = indexed.reindex(features["node"].astype(str))
        labels = aligned["anomaly_label"].fillna(0).astype(int).to_numpy()
        votes += labels
        score_sum += aligned["anomaly_score"].fillna(0.0).to_numpy()
        for node, label in zip(features["node"].astype(str), labels):
            if label:
                flagged_by[node].append(ALGORITHM_DISPLAY_NAMES[algorithm])

    frame = features.copy()
    required_votes = max(2, len(BASE_ALGORITHMS) // 2)
    frame["anomaly_score"] = score_sum / len(BASE_ALGORITHMS)
    frame["detector_votes"] = votes.to_numpy()
    frame["anomaly_label"] = (frame["detector_votes"] >= required_votes).astype(int)
    frame["reason_flagged"] = [
        (
            f"Flagged by {len(flagged_by[node])} of {len(BASE_ALGORITHMS)} detectors: "
            + ", ".join(flagged_by[node])
        )
        if flagged_by[node] and votes_count >= required_votes
        else "Within expected behavior"
        for node, votes_count in zip(frame["node"].astype(str), frame["detector_votes"])
    ]
    return frame


def detect_anomalies(
    features: pd.DataFrame,
    algorithm: str = "rule_based",
    threshold: float = 0.65,
) -> DetectionResult:
    """Run anomaly detection on graph features."""
    if features.empty:
        frame = features.copy()
        frame["anomaly_score"] = pd.Series(dtype=float)
        frame["anomaly_label"] = pd.Series(dtype=int)
        frame["reason_flagged"] = pd.Series(dtype=str)
        return DetectionResult(frame=frame, algorithm=algorithm)

    if algorithm == "consensus":
        result = _consensus_detection(features, threshold=threshold)
    elif algorithm == "rule_based":
        result = _rule_based_detection(features)
        result["anomaly_label"] = (result["anomaly_score"] >= threshold).astype(int)
        result.loc[result["anomaly_label"] == 0, "reason_flagged"] = "Within expected behavior"
    elif algorithm in {"isolation_forest", "local_outlier_factor", "one_class_svm"}:
        result = _model_detection(features, algorithm)
        if threshold is not None:
            result["anomaly_label"] = (result["anomaly_score"] >= threshold).astype(int)
            result.loc[result["anomaly_label"] == 0, "reason_flagged"] = "Within expected behavior"
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    ordered = result.sort_values(["anomaly_label", "anomaly_score"], ascending=[False, False]).reset_index(drop=True)
    return DetectionResult(frame=ordered, algorithm=algorithm)

