# User Guide

A tour of the dashboard, top to bottom, plus a suggested demo flow.

## Loading data

Three ways, in the sidebar:

1. **Default sample** — `data/sample_network.csv` loads automatically on startup.
2. **Upload CSV** — drag-and-drop or browse. Requires the columns
   `source,destination,timestamp,protocol` (see [Datasets](datasets.md)); files
   producing more than 750 nodes are rejected to keep rendering interactive.
   Uploading while a demo scenario is active switches back to the upload.
3. **Demo scenario** — generates labeled attack traffic (or loads a converted
   real capture) with known anomalous nodes; this is what activates the
   Detector Evaluation panel. Scenario descriptions appear under the dropdown.

## Sidebar controls

| Control | Effect |
|---|---|
| Directed graph | Rebuild as a directed graph (who *initiated* each connection matters) |
| Algorithm selector | Rule-Based, Isolation Forest, Local Outlier Factor, One-Class SVM, Consensus (all four vote; flagged on ≥2 votes), or Lightweight GNN (a small GCN autoencoder — see [Lightweight GNN](lightweight-gnn.md)) |
| Threshold | Score cutoff for flagging. Lower = more sensitive. Graph colors, table, KPIs, and evaluation all update live |
| Time window (% of capture) | Keep only traffic inside the selected slice of the capture and re-run everything — slide to see the network before/after an attack begins |
| Color nodes by | Anomaly severity (red/amber/blue) or community membership |
| Graph layout | Fcose (physics-based, default), breadth-first, circle, concentric, grid |
| Search node | Select a device by name |
| Export format + Export Results | CSV / JSON of the anomaly table, or PNG of the graph |

## The network graph

- **Node color** follows the detection result: red = flagged at the current
  threshold, amber = unflagged but scoring close to it, blue = normal.
- **Node size** scales with degree.
- **Dashed amber edges** are bridges (removing them splits the network).
- **Dotted teal edges** are new — the first-ever contact between that pair of
  devices happened in the last quarter of the capture (a scanning /
  lateral-movement signature).
- On graphs over 150 nodes the view switches to compact mode: smaller nodes,
  labels only on flagged or selected nodes.
- **FIT** button: re-fit the whole graph in view. **⛶** button: fullscreen
  (click again to exit). Mouse wheel zooms, drag pans, click a node to inspect it.

## The Selected Node panel

Click a node (or a table row, or use search) to see its full metric breakdown,
its neighbours, its anomaly score, and *why* it was flagged. When a scenario
with ground truth is active, the panel also shows whether the node really is an
injected/labeled anomaly — so you can check the detector's answer.

## Detector Evaluation panel

Appears only when ground truth exists (a demo scenario or converted real
dataset is loaded). It runs **all six detectors on identical features** and
scores each against the known anomalous nodes. When the graph is available, a
**resource profile** for the Lightweight GNN also appears below the table —
its parameter count, model size, and inference latency, assessed against a
Raspberry Pi Zero 2 W's RAM budget (see
[Lightweight GNN](lightweight-gnn.md) for what that estimate does and doesn't cover):

- **True Positives** — flagged nodes that really are attackers
- **False Positives** — innocent devices wrongly flagged (false alarms)
- **Missed** — attackers that slipped through
- **Precision** — of everything flagged, how much was real?
- **Recall** — of the real attacks, how many were caught?
- **F1** — harmonic mean of the two

It re-computes when you move the threshold slider, which makes the
precision/recall trade-off visible live.

## What to look for in each scenario

| Scenario | Ground-truth anomalies | Visual signature |
|---|---|---|
| Network Scanner | `ENG-PC3` | One workstation fanning out to almost every device; many dotted teal edges |
| Data Exfiltration Hub | `STAGING-01` | An unfamiliar hub receiving from ~14 machines, with a link to `EXT-198.51.100.7` |
| Rogue Bridge Device | `ROGUE-AP` | Sole connector between the `IOT-CAM*` cluster and the LAN; dashed amber bridge edges |
| Botnet Beaconing | `C2-SERVER` + `HR-PC2`, `ENG-PC5`, `ENG-PC7`, `FIN-PC3`, `FIN-PC5` | Cross-department mesh beaconing to the C2 node; hard at threshold 0.65, try ~0.5 |
| CTU-13 Real Botnet (Neris) | 10 real infected IPs (`147.32.84.165`, `.191–.193`, `.204–.209`) | Real capture; consensus catches all 10 (F1 ≈ 0.87 at the default threshold). Lightweight GNN misses at default threshold — a real, documented finding, see [Lightweight GNN](lightweight-gnn.md#measured-results) |
| IoT-23 Real Botnet (Port Scan) | Real infected IoT device(s), e.g. `192.168.2.5` | Real IoT malware capture; a massive fan-out hub. Lightweight GNN ties the best classical detectors here (F1 ≈ 0.667) |

Nodes *involved* in an attack but not compromised (e.g., the external IP, the
IoT cameras) are intentionally not part of the ground truth.

## Suggested demo flow (~2 minutes)

1. Select the **Network Scanner** scenario — point at the red fan-out node.
2. Show the **evaluation table**: Rule-Based and LOF at F1 = 1.0.
3. Drag the **threshold** down and up — graph, table, and metrics move together.
4. Switch algorithm to **Consensus** — click the red node, read "Flagged by N of
   4 detectors" and the ground-truth badge.
5. Load **CTU-13 Real Botnet** — real traffic, all 10 bots caught; contrast the
   rule-based detector's misses with the ML models.
6. Slide the **time window** to 0–75% — the attack vanishes; back to 100% — it returns.
