"""Convert an IoT-23 labeled Zeek conn.log into this project's CSV format.

The IoT-23 dataset (Stratosphere Lab, CTU) contains real malware traffic
captured from infected IoT devices, with every flow labeled Benign/Malicious
plus a detailed attack-type label. This script converts a scenario's
``conn.log.labeled`` file into the ``source,destination,timestamp,protocol``
format the dashboard loads, sampling down to a graph small enough for
interactive rendering while preserving the infected device's traffic pattern
and every benign flow. Infected devices are detected from the flow labels and
written to a ``.truth.json`` sidecar, which the dashboard picks up to show the
Detector Evaluation panel.

Usage:
    python scripts/convert_iot23.py <conn.log.labeled> [output.csv] [scenario-name]

Recommended capture — scenario 3-1 (horizontal port scan, 1 infected device, 24 MB):
    https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/IndividualScenarios/CTU-IoT-Malware-Capture-3-1/bro/conn.log.labeled
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

MAX_FLOWS_PER_BOT = 150
MAX_BENIGN_FLOWS = 700
NODE_BUDGET = 320
SEED = 42

# Zeek's conn.log.labeled writes tunnel_parents/label/detailed-label as one
# whitespace-separated group instead of proper tab fields in IoT-23 exports.
_FIELDS = (
    "ts", "uid", "src", "sport", "dst", "dport", "proto", "service",
    "duration", "orig_bytes", "resp_bytes", "conn_state", "local_orig",
    "local_resp", "missed_bytes", "history", "orig_pkts", "orig_ip_bytes",
    "resp_pkts", "resp_ip_bytes", "tail",
)


def _read_conn_log(path: Path) -> pd.DataFrame:
    rows = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(_FIELDS):
                continue
            record = dict(zip(_FIELDS, parts))
            tail = re.split(r"\s+", record["tail"].strip())
            record["label"] = tail[1] if len(tail) > 1 else ""
            rows.append(record)
    return pd.DataFrame(rows)


def convert(conn_log_path: Path, output_path: Path, scenario_name: str) -> pd.DataFrame:
    flows = _read_conn_log(conn_log_path).dropna(subset=["src", "dst", "ts"])
    flows = flows[flows["src"].ne("") & flows["dst"].ne("")]

    # The infected device(s) are the sources of Malicious-labeled flows.
    bot_ips = sorted(flows.loc[flows["label"] == "Malicious", "src"].unique())
    if not bot_ips:
        raise SystemExit("No Malicious flows found — is this a labeled IoT-23 conn.log?")

    malicious = flows[flows["label"] == "Malicious"]
    benign = flows[flows["label"] == "Benign"]

    per_bot = []
    for bot in bot_ips:
        bot_flows = malicious[(malicious["src"] == bot) | (malicious["dst"] == bot)]
        if len(bot_flows) > MAX_FLOWS_PER_BOT:
            bot_flows = bot_flows.sample(MAX_FLOWS_PER_BOT, random_state=SEED)
        per_bot.append(bot_flows.reset_index(drop=True))

    # Interleave round-robin so the node budget is shared fairly across bots.
    interleaved = (
        pd.concat(per_bot, keys=range(len(per_bot)))
        .reset_index(level=0, names="bot_index")
        .sort_index()
        .drop(columns="bot_index")
    )
    benign_sample = benign.sample(min(MAX_BENIGN_FLOWS, len(benign)), random_state=SEED)

    # Priority order: malicious traffic first so the infection's fan-out
    # survives the node budget, then benign traffic.
    candidate = pd.concat([interleaved, benign_sample])

    # Enforce the node budget greedily so the graph stays renderable.
    nodes: set[str] = set(bot_ips)
    kept_rows = []
    for row in candidate.itertuples(index=False):
        endpoints = {str(row.src), str(row.dst)}
        new_nodes = endpoints - nodes
        if len(nodes) + len(new_nodes) > NODE_BUDGET:
            continue
        nodes.update(new_nodes)
        kept_rows.append(row)

    kept = pd.DataFrame(kept_rows)
    result = pd.DataFrame(
        {
            "source": kept["src"].astype(str),
            "destination": kept["dst"].astype(str),
            "timestamp": kept["ts"].astype(float).map(
                lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
            ),
            "protocol": kept["proto"].astype(str).str.upper(),
        }
    ).sort_values("timestamp").reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    truth_path = output_path.with_suffix("").with_suffix(".truth.json")
    truth_path.write_text(
        json.dumps(
            {
                "name": scenario_name,
                "description": (
                    "Real IoT malware traffic from the IoT-23 dataset (Stratosphere Lab, CTU), "
                    f"sampled from {conn_log_path.name}. Infected IoT devices are labeled in "
                    "the original capture; every benign flow sampled is genuine device traffic."
                ),
                "true_anomalies": list(bot_ips),
            },
            indent=2,
        )
    )
    return result


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    conn_log_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/iot23_scenario3.csv")
    scenario_name = sys.argv[3] if len(sys.argv) > 3 else "IoT-23 Real Botnet (Port Scan)"
    result = convert(conn_log_path, output_path, scenario_name)
    hosts = set(result["source"]) | set(result["destination"])
    truth = json.loads(output_path.with_suffix("").with_suffix(".truth.json").read_text())
    print(f"Wrote {len(result)} flows, {len(hosts)} hosts -> {output_path}")
    print(f"Infected devices ({len(truth['true_anomalies'])}): {truth['true_anomalies']}")


if __name__ == "__main__":
    main()
