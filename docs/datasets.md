# Datasets

The CSV format, what ships in `data/`, and how to convert real captures.

## CSV format

The loader (`src/loader.py`) requires exactly these columns:

```csv
source,destination,timestamp,protocol
PC1,Server1,2025-01-01 10:00:00,TCP
PC1,Router,2025-01-01 10:00:10,TCP
PC2,PC4,2025-01-01 10:00:30,UDP
```

Cleaning applied on load: timestamps parsed (unparseable rows dropped),
whitespace stripped, protocols uppercased, literal `"nan"` endpoints removed,
exact duplicate rows dropped. An upload producing more than 750 nodes is
rejected to keep rendering and metric computation interactive.

Repeated contacts between the same pair become **one weighted edge** in the
graph (`weight` = number of flows), with the timestamps and protocols kept as
edge attributes.

## What ships in `data/`

| File | Contents |
|---|---|
| `sample_network.csv` | Small hand-written office network — the default on startup |
| `ctu13_scenario9.csv` | 320-host slice of real CTU-13 botnet traffic (see below) |
| `ctu13_scenario9.truth.json` | Ground-truth sidecar: the 10 labeled infected hosts |

## Synthetic scenarios

Generated in code (`src/scenarios.py`), not stored as files. Each builds a
seeded baseline office network (3 departments, switches, router, servers) and
injects one attack into the last quarter of the time window. See the
[User Guide](user-guide.md) for the list and their ground-truth nodes, and
[Extending](extending.md) to add one.

## File-backed (real) datasets

Any pair of files in `data/`:

```
data/<name>.csv          # dashboard CSV format
data/<name>.truth.json   # {"name": "...", "description": "...", "true_anomalies": ["ip1", ...]}
```

is auto-discovered by `src/scenarios.py::_file_backed_scenarios` and appears in
the Demo scenario dropdown, with the evaluation panel scoring against its
`true_anomalies`.

## Converting CTU-13 captures

The [CTU-13 dataset](https://www.stratosphereips.org/datasets-ctu13)
(Garcia et al., 2014) contains 13 real botnet captures from the CTU University
network, with every flow labeled Background / Normal / Botnet. Download a
labeled `.binetflow` file (scenario 9 = directory `CTU-Malware-Capture-Botnet-50`,
~273 MB) and convert it:

```bash
make convert-ctu13 CAPTURE=capture20110817.binetflow OUT=data/my_slice.csv NAME="My Scenario"
# Windows: make.bat convert-ctu13 capture20110817.binetflow data\my_slice.csv "My Scenario"
```

What `scripts/convert_ctu13.py` does:

- Detects infected hosts from the flow labels (`From-Botnet` sources) — no hardcoding.
- Samples up to `MAX_FLOWS_PER_BOT` (120) flows per bot, **interleaved
  round-robin** so every bot keeps its fan-out signature under the node budget.
- Keeps labeled-normal flows, then internal (`147.32.*`) background traffic.
- Enforces `NODE_BUDGET` (320) greedily: a flow is kept only if its endpoints fit
  the budget; flows between already-included nodes are always kept, so edge
  weights stay realistic.
- Writes the CSV plus the `.truth.json` sidecar.

Tuning knobs are the constants at the top of the script. The node budget trades
fidelity for renderability — record the budget you used if you quote results.

### Choosing a scenario

Bots whose behaviour is *topological* (scanning, spam fan-out — e.g., Neris in
scenarios 1, 2, 9) suit this tool. Scenario 11's DDoS bots send thousands of
flows to a single target — degree 1 on the graph — and are invisible to the
current features (see the known limitation in
[Detection & Evaluation](detection-and-evaluation.md)).
