from __future__ import annotations

import pandas as pd
import pytest

from src.loader import load_network_data


def test_missing_required_column_raises():
    frame = pd.DataFrame([{"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:00"}])
    with pytest.raises(ValueError, match="Missing required columns"):
        load_network_data(frame)


def test_rows_with_invalid_timestamp_are_dropped():
    frame = pd.DataFrame(
        [
            {"source": "A", "destination": "B", "timestamp": "2025-01-01 00:00:00", "protocol": "tcp"},
            {"source": "C", "destination": "D", "timestamp": "not-a-date", "protocol": "udp"},
        ]
    )
    loaded = load_network_data(frame)
    assert len(loaded) == 1
    assert loaded.iloc[0]["source"] == "A"


def test_all_invalid_rows_raises():
    frame = pd.DataFrame(
        [{"source": "A", "destination": "B", "timestamp": "not-a-date", "protocol": "tcp"}]
    )
    with pytest.raises(ValueError, match="No valid network rows"):
        load_network_data(frame)
