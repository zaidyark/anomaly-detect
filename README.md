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
make install        # Linux / macOS
make.bat install    # Windows
```

Or manually:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running locally

```bash
make run            # or make.bat run, or: python app.py
```

Open the dashboard at `http://127.0.0.1:8050`.

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

- [Getting Started](docs/getting-started.md) — install, run, make targets
- [User Guide](docs/user-guide.md) — dashboard tour, scenario ground truth, demo flow
- [Architecture](docs/architecture.md) — code structure, data flow, callback map
- [Detection & Evaluation](docs/detection-and-evaluation.md) — features, detectors, measured results
- [Datasets](docs/datasets.md) — CSV format, CTU-13 conversion
- [Extending](docs/extending.md) — add detectors, scenarios, metrics, charts
- [Testing](docs/testing.md) and [Troubleshooting](docs/troubleshooting.md)

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
- Lightweight GNN — a hand-rolled 2-layer GCN autoencoder in plain PyTorch (no
  PyTorch Geometric), 224 parameters / <1 KB, scored by feature-reconstruction
  error. See [docs/lightweight-gnn.md](docs/lightweight-gnn.md) for the
  architecture, its resource profile (assessed against a Raspberry Pi Zero 2 W's
  RAM budget), and an honest account of where it does and doesn't beat the
  classical detectors on real traffic.

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
| IoT-23 Real Botnet (Port Scan) | **Real** labeled IoT malware capture | Horizontal port scan from an infected IoT device |

Because the anomalous devices are known (injected by construction, or labeled in the
original capture), the dashboard shows a **Detector Evaluation** panel with precision,
recall, and F1 for every algorithm on the same features — try moving the threshold
slider and watching the trade-off.

### Real-data evaluation (CTU-13)

`data/ctu13_scenario9.csv` is a 320-host slice of scenario 9 of the CTU-13 dataset
(Garcia et al., 2014) — real traffic from the CTU University network with 10 hosts
infected by the Neris botnet, labeled flow-by-flow in the original capture. The slice
is produced reproducibly by `scripts/convert_ctu13.py`, which preserves each bot's
fan-out signature alongside labeled-normal and background traffic. Headline results at
the default threshold: **consensus voting catches all 10 bots with F1 = 0.87**
(Isolation Forest and One-Class SVM match it individually), while the rule-based
detector finds only 6 of 10 — precise but blind to the bots whose behaviour its rules
don't encode, a useful demonstration of why the ML models and ensemble voting exist.

To regenerate (or convert a different scenario), download a labeled `.binetflow`
capture from the [CTU-13 dataset](https://www.stratosphereips.org/datasets-ctu13) and run:

```bash
python scripts/convert_ctu13.py capture20110817.binetflow data/ctu13_scenario9.csv "CTU-13 Real Botnet (Neris)"
```

Any converted dataset dropped into `data/` with its `.truth.json` sidecar appears
automatically in the Demo scenario dropdown.

### Real-data evaluation (IoT-23)

`data/iot23_scenario3.csv` is a 320-host slice of a real IoT-23 capture
(Stratosphere Lab, CTU) — a genuinely infected IoT device running a horizontal
port scan, labeled flow-by-flow in the original capture. Produced by
`scripts/convert_iot23.py`. The **Lightweight GNN** detector was built and
evaluated specifically against this dataset — see
[docs/lightweight-gnn.md](docs/lightweight-gnn.md) for its architecture,
measured results (ties the best classical detectors here, F1 ≈ 0.667), and an
explicit account of how this differs from a full compressed-GNN-on-physical-hardware
brief.

```bash
python scripts/convert_iot23.py conn.log.labeled data/iot23_scenario3.csv "IoT-23 Real Botnet (Port Scan)"
```

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

