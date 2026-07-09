"""Feature preprocessing for anomaly models."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
from sklearn.preprocessing import StandardScaler


DEFAULT_FEATURE_COLUMNS = (
    "degree",
    "degree_centrality",
    "betweenness_centrality",
    "closeness_centrality",
    "eigenvector_centrality",
    "pagerank",
    "clustering_coefficient",
    "component_size",
    "unique_neighbours",
    "new_neighbour_ratio",
)


def select_feature_frame(frame: pd.DataFrame, columns: Iterable[str] = DEFAULT_FEATURE_COLUMNS) -> pd.DataFrame:
    """Select and safely fill the numeric feature matrix."""
    available = [column for column in columns if column in frame.columns]
    if not available:
        raise ValueError("No usable feature columns were found.")
    features = frame.loc[:, available].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return features


def scale_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a standard scaled feature matrix as a dataframe."""
    scaler = StandardScaler()
    scaled = scaler.fit_transform(frame.values)
    return pd.DataFrame(scaled, columns=frame.columns, index=frame.index)

