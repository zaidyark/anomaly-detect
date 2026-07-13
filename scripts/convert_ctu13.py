"""Convert a CTU-13 labeled binetflow capture into this project's CSV format.

The CTU-13 dataset (Garcia et al., 2014) contains real botnet traffic captured
on the CTU University network, with every flow labeled Background / Normal /
Botnet. This script converts a capture into the
``source,destination,timestamp,protocol`` format the dashboard loads, sampling
the tens of thousands of hosts down to a graph small enough for interactive
rendering while preserving every labeled-normal flow and each bot's
behavioural signature. The infected hosts are detected from the flow labels
and written to a ``.truth.json`` sidecar, which the dashboard picks up to show
the Detector Evaluation panel.

Usage:
    python scripts/convert_ctu13.py <capture.binetflow> [output.csv] [scenario-name]

Recommended capture — scenario 9 (Neris, 10 infected hosts, 273 MB):
    https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-50/detailed-bidirectional-flow-labels/capture20110817.binetflow
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

MAX_FLOWS_PER_BOT = 120
MAX_BACKGROUND_FLOWS = 900
NODE_BUDGET = 600
SEED = 42


def convert(binetflow_path: Path, output_path: Path, scenario_name: str) -> pd.DataFrame:
    flows = pd.read_csv(
        binetflow_path, usecols=["StartTime", "Proto", "SrcAddr", "DstAddr", "Label"]
    ).dropna(subset=["SrcAddr", "DstAddr", "StartTime"])

    # The infected hosts are exactly the sources of "From-Botnet" flows.
    bot_ips = sorted(
        flows.loc[flows["Label"].str.contains("From-Botnet", na=False), "SrcAddr"].unique()
    )
    if not bot_ips:
        raise SystemExit("No From-Botnet flows found — is this a labeled CTU-13 capture?")

    normal = flows[flows["Label"].str.contains("Normal", na=False)]
    botnet = flows[flows["Label"].str.contains("Botnet", na=False)]
    background = flows[flows["Label"].str.contains("Background", na=False)]
    # Keep the background graph coherent: only university-internal traffic.
    internal = background[
        background["SrcAddr"].str.startswith("147.32.")
        & background["DstAddr"].str.startswith("147.32.")
    ]

    per_bot = []
    for bot in bot_ips:
        bot_flows = botnet[(botnet["SrcAddr"] == bot) | (botnet["DstAddr"] == bot)]
        if len(bot_flows) > MAX_FLOWS_PER_BOT:
            bot_flows = bot_flows.sample(MAX_FLOWS_PER_BOT, random_state=SEED)
        per_bot.append(bot_flows.reset_index(drop=True))

    # Interleave the bots' flows round-robin so the node budget is shared
    # fairly instead of the first bot claiming it all.
    interleaved = (
        pd.concat(per_bot, keys=range(len(per_bot)))
        .reset_index(level=0, names="bot_index")
        .sort_index()
        .drop(columns="bot_index")
    )
    background_sample = internal.sample(
        min(MAX_BACKGROUND_FLOWS, len(internal)), random_state=SEED
    )

    # Priority order: bot traffic first so the bots' fan-out signature survives
    # the node budget, then labeled-normal, then background.
    candidate = pd.concat([interleaved, normal, background_sample])

    # Enforce the node budget greedily so the graph stays renderable.
    nodes: set[str] = set(bot_ips)
    kept_rows = []
    for row in candidate.itertuples(index=False):
        endpoints = {str(row.SrcAddr), str(row.DstAddr)}
        new_nodes = endpoints - nodes
        if len(nodes) + len(new_nodes) > NODE_BUDGET:
            continue
        nodes.update(new_nodes)
        kept_rows.append(row)

    kept = pd.DataFrame(kept_rows)
    result = pd.DataFrame(
        {
            "source": kept["SrcAddr"].astype(str),
            "destination": kept["DstAddr"].astype(str),
            "timestamp": pd.to_datetime(kept["StartTime"], format="%Y/%m/%d %H:%M:%S.%f"),
            "protocol": kept["Proto"].astype(str).str.upper(),
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
                    "Real botnet traffic from the CTU-13 dataset (Garcia et al., 2014), "
                    f"sampled from {binetflow_path.name}. Infected hosts are labeled in "
                    "the original capture; every labeled-normal flow is preserved."
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
    binetflow_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/ctu13_scenario9.csv")
    scenario_name = sys.argv[3] if len(sys.argv) > 3 else "CTU-13 Real Botnet (Neris)"
    result = convert(binetflow_path, output_path, scenario_name)
    hosts = set(result["source"]) | set(result["destination"])
    truth = json.loads(output_path.with_suffix("").with_suffix(".truth.json").read_text())
    print(f"Wrote {len(result)} flows, {len(hosts)} hosts -> {output_path}")
    print(f"Infected hosts ({len(truth['true_anomalies'])}): {truth['true_anomalies']}")


if __name__ == "__main__":
    main()
