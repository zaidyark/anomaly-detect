"""General utility helpers."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def ensure_directory(path: str | Path) -> Path:
    """Create a directory if it does not exist."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def dataframe_to_json(frame: pd.DataFrame) -> str:
    """Serialize a dataframe to a JSON string."""
    return frame.to_json(orient="records", date_format="iso")


def json_to_dataframe(data: str) -> pd.DataFrame:
    """Deserialize a dataframe from JSON records."""
    if not data:
        return pd.DataFrame()
    return pd.read_json(StringIO(data), orient="records")


def dump_json(payload: dict[str, Any]) -> str:
    """Dump a JSON payload with stable formatting."""
    return json.dumps(payload, indent=2, sort_keys=True, default=str)
