"""Data loading and validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

REQUIRED_COLUMNS = ("source", "destination", "timestamp", "protocol")


def load_network_data(data: str | Path | pd.DataFrame | IO[str]) -> pd.DataFrame:
    """Load a network dataset from disk, a file-like object, or a dataframe."""
    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    else:
        frame = pd.read_csv(data)

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    frame = frame.loc[:, REQUIRED_COLUMNS].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["source", "destination", "timestamp"])
    frame["source"] = frame["source"].astype(str).str.strip()
    frame["destination"] = frame["destination"].astype(str).str.strip()
    frame["protocol"] = frame["protocol"].astype(str).str.strip().str.upper()
    frame = frame[frame["source"].ne("") & frame["destination"].ne("")]
    frame = frame[~frame["source"].str.lower().eq("nan") & ~frame["destination"].str.lower().eq("nan")]
    frame = frame.drop_duplicates().reset_index(drop=True)

    if frame.empty:
        raise ValueError("No valid network rows were found in the dataset.")

    return frame
