# Graph-Based Anomaly Detection in Computer Networks

A lightweight SOC-style dashboard for detecting anomalous devices in computer network traffic using graph analytics and machine learning.

## Features

- Load CSV network data
- Build directed or undirected graphs
- Compute graph metrics and network statistics
- Detect anomalous nodes with multiple algorithms
- Explore the network visually with Dash Cytoscape
- Inspect suspicious nodes and neighboring devices
- Compare detection algorithms
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

## Screenshots

Add dashboard screenshots here once deployed or captured locally.

## Future Work

- Session-aware timeline playback
- Deeper community detection views
- Shortest path investigation workflow
- Multi-tenant incident bookmarking
- Authentication and persistence

