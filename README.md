# Graph-Based Anomaly Detection in Computer Networks

A lightweight SOC-style dashboard for detecting anomalous devices in computer network traffic using graph analytics and machine learning.

## Features

- Load CSV network data
- Build directed or undirected graphs
- Compute graph metrics and network statistics
- Detect anomalous nodes with multiple algorithms, plus a consensus (majority-vote) mode
- Built-in attack scenarios with ground-truth labels (scanner, exfiltration hub, rogue bridge, botnet)
- Evaluate every detector with precision / recall / F1 against the injected ground truth
- Explore the network visually with Dash Cytoscape, including bridge and newly-appeared edge highlighting
- Filter traffic to a time window and watch the graph evolve
- Inspect suspicious nodes and neighboring devices
- Export results as CSV, JSON, or PNG

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running locally

```bash
python app.py
```

Open the dashboard at `http://127.0.0.1:8050`.

## Docker

```bash
docker compose up --build
```

## Project Structure

```text
graph-anomaly-detection/
    app.py
    requirements.txt
    README.md
    Dockerfile
    docker-compose.yml
    assets/
    data/
    src/
    dashboard/
    tests/
```

## Dataset Format

The application expects CSV files with the following columns:

```text
source,destination,timestamp,protocol
```

Example:

```csv
PC1,Server1,2025-01-01 10:00:00,TCP
PC1,Router,2025-01-01 10:00:10,TCP
PC2,PC4,2025-01-01 10:00:30,UDP
```

## Algorithms

- Rule-Based
- Isolation Forest
- Local Outlier Factor
- One-Class SVM
- Consensus (all four detectors vote; a node is flagged when at least two agree)

## Demo Scenarios & Evaluation

The sidebar's **Demo scenario** dropdown generates synthetic office traffic with one
known attack injected into the last quarter of the capture window:

| Scenario | Injected behaviour | Dominant signal |
|---|---|---|
| Network Scanner | One workstation sweeps nearly every device | Degree spike, new-neighbour ratio |
| Data Exfiltration Hub | Many machines funnel data into a staging host | Sudden high-degree hub |
| Rogue Bridge Device | Unauthorized AP links an IoT segment to the LAN | Bridge edge, low clustering |
| Botnet Beaconing | Infected machines beacon to a C2 server and mesh | New clique spanning departments |
| CTU-13 Real Botnet (Neris) | **Real** labeled botnet capture, 10 infected hosts | Spam/scan fan-out from infected machines |

Because the anomalous devices are known (injected by construction, or labeled in the
original capture), the dashboard shows a **Detector Evaluation** panel with precision,
recall, and F1 for every algorithm on the same features — try moving the threshold
slider and watching the trade-off.

### Real-data evaluation (CTU-13)

`data/ctu13_scenario9.csv` is a 600-host slice of scenario 9 of the CTU-13 dataset
(Garcia et al., 2014) — real traffic from the CTU University network with 10 hosts
infected by the Neris botnet, labeled flow-by-flow in the original capture. The slice
is produced reproducibly by `scripts/convert_ctu13.py`, which preserves every
labeled-normal flow and each bot's fan-out signature. Headline result at the default
threshold: **consensus voting catches all 10 bots with F1 = 0.83**, while the
rule-based detector transfers poorly to real traffic (it flags the legitimate
high-degree servers instead) — a useful demonstration that learned models generalize
where hand-written rules do not.

To regenerate (or convert a different scenario), download a labeled `.binetflow`
capture from the [CTU-13 dataset](https://www.stratosphereips.org/datasets-ctu13) and run:

```bash
python scripts/convert_ctu13.py capture20110817.binetflow data/ctu13_scenario9.csv "CTU-13 Real Botnet (Neris)"
```

Any converted dataset dropped into `data/` with its `.truth.json` sidecar appears
automatically in the Demo scenario dropdown.

## Screenshots

Add dashboard screenshots here once deployed or captured locally.

## Future Work

- Flow-volume features (weighted degree, per-edge flow counts) — CTU-13 scenario 11
  showed that DDoS bots hammering a single target are invisible to purely topological
  features (degree 1 on a who-talks-to-whom graph); volume features would catch them
- Session-aware timeline playback (beyond the current time-window filter)
- Deeper community detection views
- Shortest path investigation workflow
- Multi-tenant incident bookmarking
- Authentication and persistence

