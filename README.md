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

Because the anomalous devices are known by construction, the dashboard shows a
**Detector Evaluation** panel with precision, recall, and F1 for every algorithm on
the same features — try moving the threshold slider and watching the trade-off.

## Screenshots

Add dashboard screenshots here once deployed or captured locally.

## Future Work

- Session-aware timeline playback (beyond the current time-window filter)
- Deeper community detection views
- Shortest path investigation workflow
- Evaluation on real public datasets (e.g., CTU-13, UNSW-NB15 flow samples)
- Multi-tenant incident bookmarking
- Authentication and persistence

