# Project Guide: Graph-Based Network Anomaly Detection

This document explains **everything** about this project: the concepts, the terminology, the algorithms, and how each file in the codebase works. Read it top to bottom before you present or defend this project — by the end you should be able to answer "why did you do it this way?" for every part of it.

---

## 1. What problem does this project solve?

Computer networks generate constant traffic: laptops talking to servers, servers talking to routers, and so on. Most of this traffic is normal. But sometimes a device behaves strangely — it suddenly talks to way more devices than usual, or it becomes a single point that everything routes through, or it starts making brand-new connections it's never made before. These patterns can indicate:

- A compromised device (malware scanning the network, a botnet node)
- A misconfigured device (a router with a bad routing table)
- An unusual but legitimate event (a backup server suddenly talking to everything at once)

The goal of this project is: **turn raw network traffic logs into a graph, describe the "shape" of normal behavior mathematically, and flag devices whose behavior looks statistically unusual.**

---

## 2. Core concept: representing a network as a graph

A **graph** (in the computer-science/math sense, not a chart) is just:

- **Nodes** (also called vertices) — the "things." Here, each node is a device (`PC1`, `Server1`, `Router`, ...).
- **Edges** — the "connections" between things. Here, an edge exists between two devices if they communicated at least once.

Example, from `data/sample_network.csv`:

```
PC1,Server1,2025-01-01 10:00:00,TCP
PC1,Router,2025-01-01 10:00:10,TCP
```

This says: `PC1` talked to `Server1`, and `PC1` talked to `Router`. As a graph, that's 3 nodes (`PC1`, `Server1`, `Router`) and 2 edges (`PC1`—`Server1`, `PC1`—`Router`).

### Directed vs. undirected graphs

- **Undirected**: an edge just means "these two talked," with no notion of who started it. `PC1`–`Server1` is the same as `Server1`–`PC1`.
- **Directed**: an edge has a direction — `PC1 → Server1` means PC1 initiated the connection to Server1, and that's tracked separately from `Server1 → PC1`.

This project supports both (toggle in the sidebar: "Directed graph"). Undirected is simpler and usually fine for "who talks to whom" analysis; directed matters more if the *direction* of communication is meaningful (e.g., who is scanning whom).

### Edge weight

If `PC1` and `Server1` talk multiple times, we don't create multiple edges — we increase the **weight** of the single edge between them (`weight=2`, `weight=3`, ...). Weight represents "how much" two nodes interacted.

### Why NetworkX?

The code uses a Python library called **NetworkX** (`import networkx as nx`) to represent and analyze graphs. It gives us ready-made, well-tested implementations of all the graph algorithms below (centrality measures, community detection, bridge detection, etc.), so we don't have to implement graph theory from scratch.

---

## 3. Terminology glossary (read this before the metrics section)

| Term | Meaning |
|---|---|
| **Node / Vertex** | A single device in the network. |
| **Edge** | A connection between two devices. |
| **Degree** | The number of edges touching a node (how many distinct devices it talks to). |
| **Centrality** | A family of measures that answer "how important/central is this node?", computed in different ways (see below). |
| **Path** | A sequence of edges connecting one node to another (possibly through intermediate nodes). |
| **Shortest path** | The path between two nodes using the fewest edges (or lowest total weight). |
| **Connected component** | A group of nodes that can all reach each other via some path, but cannot reach nodes outside the group. A graph can have multiple disconnected "islands." |
| **Bridge** | An edge that, if removed, would split its connected component into two separate pieces. Bridges are structurally important — and often unusual. |
| **Community** | A cluster of nodes that talk to each other much more than they talk to nodes outside the cluster (like an informal "department" in an organization). |
| **Feature** | A numeric column describing a node (degree, centrality, etc.) — the inputs fed into the anomaly detection algorithms. |
| **Outlier / Anomaly** | A data point (node) whose feature values are unusual compared to the rest of the dataset. |
| **Threshold** | The cutoff score above which a node is labeled "anomalous" rather than "normal." |
| **Model / Estimator** | A machine learning algorithm object that has learned patterns from the data (e.g., an `IsolationForest` instance). |
| **Feature scaling / normalization** | Transforming numeric columns so they're on comparable ranges (e.g., 0–1 or mean 0/std 1), so no single feature dominates just because its raw numbers are bigger. |

---

## 4. The metrics, explained one by one

All computed in `src/metrics.py`, function `compute_node_metrics()`. For every node in the graph, we calculate:

### Degree
> How many other devices does this node talk to directly?

The simplest and most intuitive metric. `nx.degree()` in the code. A device with degree 20 talks to 20 others; a device with degree 1 talks to only one.

### Degree Centrality
> Degree, but normalized to a 0–1 scale (degree ÷ (number of nodes − 1)).

This lets you compare "how connected" a node is *relative to the size of the network*, rather than in raw counts. Useful when comparing graphs of different sizes.

### Betweenness Centrality
> How often does this node sit on the shortest path between two other nodes?

Computed by looking at every pair of nodes in the graph, finding the shortest path between them, and counting how often each node appears "in between." A node with high betweenness is a **broker** — traffic between other parts of the network routes through it. Routers and core servers naturally have high betweenness (that's expected/normal). A random laptop with unexpectedly high betweenness is suspicious — why is *its* traffic in the middle of everything?

### Closeness Centrality
> On average, how many hops away is this node from every other node?

A node with high closeness can "reach" the rest of the network quickly. Computed as the inverse of the average shortest-path distance to all other nodes.

### Eigenvector Centrality
> Like degree, but connections to *important* nodes count more than connections to unimportant ones.

Being connected to one popular, highly-connected node is worth more than being connected to ten isolated ones. This is computed iteratively: each node's "importance" is based on the importance of its neighbors, which is based on *their* neighbors, and so on until the numbers stabilize.

### PageRank
> The same family of idea as eigenvector centrality — literally the algorithm Google originally used to rank web pages, applied here to devices instead of web pages. A node's rank depends on how many (and how important) other nodes point to it.

### Clustering Coefficient
> Do this node's neighbors also know each other?

If `A` talks to `B` and `C`, and `B` also talks to `C`, that's a "closed triangle" — high clustering. If `B` and `C` never talk to each other despite both talking to `A`, that's low clustering, meaning `A` acts as a bridge between two otherwise-separate groups.

### Component ID / Component Size
> Which disconnected "island" of the graph does this node belong to, and how big is that island?

Most real networks are one big connected component, but isolated devices or misconfigurations can create separate islands.

### Is Bridge
> Is the edge connecting this node a bridge (i.e., removing it would split the graph)?

Computed with `nx.bridges()`. Bridges combined with low clustering often indicate a node that's an isolated connector — structurally unusual.

### Unique Neighbours / New Neighbour Ratio
> Out of all the devices this node has ever talked to, what fraction are *new* contacts made only recently (in the later part of the time window) versus contacts it already had?

The code splits the timeline into an "early" 75% and a "late" 25% (see `compute_node_metrics`), then compares each node's neighbor set in each period. A node whose neighbor list is mostly *new* in the recent period is behaving differently than its historical pattern — a classic sign of scanning behavior or a compromised device reaching out to new targets.

### Community
> Which cluster of "mostly-talk-to-each-other" nodes does this node belong to?

Computed with the **Louvain algorithm** (`nx.community.louvain_communities`), which tries to partition the graph into groups that maximize internal connections while minimizing connections between groups. This has nothing to do with anomaly detection directly — it's used for visualization ("Color nodes by → Community") to help you see the natural structure of the network.

---

## 5. The anomaly detection algorithms, explained one by one

All in `src/anomaly_detection.py`. Every algorithm receives the same feature table (the metrics above) and outputs, per node: an **anomaly score** (0–1) and an **anomaly label** (0 = normal, 1 = flagged).

### Rule-Based

The simplest, most explainable method — literally hand-written statistical rules:

1. Compute the average (mean) and spread (standard deviation) of degree and betweenness across all nodes.
2. A node is flagged as having "very high degree" if its degree is more than **1.5 standard deviations above the mean**. (This is a standard statistics trick: values far from the mean, measured in units of standard deviation, are considered outliers. 1.5–3 standard deviations is a common threshold band.)
3. Same idea for betweenness.
4. Also flags nodes with a high "new neighbour ratio" (talking to lots of new devices recently) and nodes that are isolated bridges (bridge edge + low clustering).
5. Combines these into a weighted score: 35% degree + 35% betweenness + 15% new-neighbour-ratio + 15% is-bridge.
6. If the final score crosses the threshold (default 0.65), the node is flagged, and the specific rule(s) that triggered it are recorded in **"Reason Flagged"** — this is what makes rule-based detection *explainable*: you always know exactly why a node was flagged.

**Why it matters:** unlike the ML models below, you can show this logic to a non-technical stakeholder and they'll understand it immediately. The tradeoff is it can only catch the specific patterns you thought to encode as rules.

### Isolation Forest

A machine learning model (`sklearn.ensemble.IsolationForest`). The core idea:

> Outliers are easier to "isolate" than normal points.

Imagine repeatedly picking a random feature and a random split value, and cutting the data in half at that split. If a point is normal (surrounded by lots of similar points), it takes many random cuts before it ends up alone in its own little region. If a point is an outlier (far from everything else), it gets isolated in just a few cuts, because there's nothing else nearby to keep splitting apart from it.

The model builds many random "trees" of these cuts and measures, on average, how many cuts it took to isolate each node. Nodes isolated in **fewer** cuts get **higher** anomaly scores.

**Why it matters:** doesn't require any hand-written rules or assumptions about what "normal" looks like — it learns the shape of normal behavior directly from the data's structure.

### Local Outlier Factor (LOF)

Another ML model (`sklearn.neighbors.LocalOutlierFactor`). The key difference from Isolation Forest: LOF looks at **local density** rather than global position.

> A node is anomalous if it's much less "dense" (has much sparser neighbors) than the nodes immediately around it.

For each node, LOF compares its local neighborhood density to the density of its neighbors' neighborhoods. If a node sits in a much sparser region than its neighbors do, it's flagged — even if, globally, it's not "far away" in absolute terms. This is useful when your data has multiple different "normal" clusters with different densities (e.g., a cluster of chatty servers and a cluster of quiet laptops) — LOF can catch an outlier *within* the quiet-laptop cluster that a global method might miss.

### One-Class SVM

A third ML model (`sklearn.svm.OneClassSVM`). The idea:

> Learn the tightest possible boundary that wraps around the "normal" data, then flag anything falling outside that boundary.

It projects the data into a higher-dimensional space (using a mathematical trick called a "kernel," here the RBF/Gaussian kernel) where it can draw a smooth boundary around the bulk of normal points. Anything landing outside that learned boundary — even slightly — is flagged as an outlier.

### Consensus (ensemble voting)

The fifth option runs **all four detectors** on the same features and combines them:

- Each node's consensus **score** is the average of the four per-detector scores.
- Each node is **flagged** only when at least 2 of the 4 detectors flag it (majority-style voting).
- The "Reason Flagged" column records exactly which detectors voted (e.g., "Flagged by 3 of 4 detectors: Rule-Based, Isolation Forest, LOF").

**Why it matters:** individual detectors make different mistakes. One-Class SVM tends to over-flag; the rule-based detector only catches what its rules encode. When several *independent* methods agree on the same node, that's much stronger evidence than any single method — the same reason a SOC analyst trusts an alert more when multiple tools raise it. This is a simple form of **ensemble learning**.

### Why 3 different ML models instead of just 1?

Each makes different assumptions and catches different kinds of anomalies:
- **Isolation Forest** — good general-purpose default, fast, handles high-dimensional data well.
- **LOF** — best when "normal" isn't one single blob but several different-density clusters.
- **One-Class SVM** — good when you want a smooth, well-defined boundary and have a moderate amount of data (it's slower on large datasets).

Letting the user switch between them (and compare results) is part of the "Compare detection algorithms" feature mentioned in the README.

### Feature scaling (why it's needed)

Before feeding features into Isolation Forest / LOF / One-Class SVM, the code standardizes them (`src/preprocessing.py`, `scale_features()`) using `StandardScaler`, which transforms every column to have mean 0 and standard deviation 1. **Why:** degree might range 0–20 while clustering coefficient ranges 0–1. Without scaling, degree's bigger raw numbers would dominate the "distance" calculations these models rely on, making the smaller-range features irrelevant even if they're actually more informative.

---

## 5b. Proving the detectors work: scenarios & evaluation

The hardest question about any anomaly detector is *"how do you know it's right?"* On real traffic you usually don't — nobody labels which devices were actually compromised. This project answers it with **synthetic scenarios with ground truth**.

### Attack scenarios (`src/scenarios.py`)

`generate_scenario()` builds a realistic baseline office network (3 departments behind switches, a core router, shared servers, random-but-seeded normal chatter), then injects **one known attack** into the last quarter of the time window:

| Key | Scenario | What is injected | Why detectors should catch it |
|---|---|---|---|
| `scanner` | Network Scanner | One workstation contacts nearly every device once | Degree spike + very high new-neighbour ratio |
| `exfiltration` | Data Exfiltration Hub | 14 machines funnel data into a staging host, which uploads to an external IP | Sudden high-degree hub that didn't exist before |
| `rogue_bridge` | Rogue Bridge Device | An unauthorized AP becomes the only link between an IoT segment and the LAN | Bridge edge + low clustering + high betweenness |
| `botnet` | Botnet Beaconing | Infected workstations beacon to a C2 server, mesh together, and probe laterally | New cross-department clique + new neighbours |

Because *we* injected the anomaly, we know exactly which nodes are bad — that's the **ground truth**. Everything is generated with a fixed random seed, so scenarios are reproducible.

### Evaluation metrics (`src/evaluation.py`)

With ground truth available, we can score each detector with the standard classification metrics:

- **True positive (TP)** — flagged node that really is the injected attacker.
- **False positive (FP)** — flagged node that is actually normal (a false alarm).
- **False negative (FN)** — injected attacker the detector missed.
- **Precision** = TP / (TP + FP) — *of everything flagged, how much was real?* Low precision = alert fatigue.
- **Recall** = TP / (TP + FN) — *of the real attacks, how many did we catch?* Low recall = missed intrusions.
- **F1 score** — the harmonic mean of precision and recall; a single number balancing both.

`compare_algorithms()` runs **every detector on the identical feature table** and scores each one, so the comparison is fair. The dashboard shows this as the "Detector Evaluation" table and chart whenever a demo scenario is active.

**Key talking point:** the detectors genuinely differ per scenario. For example, One-Class SVM catches the botnet best (high recall) but flags many innocent machines everywhere (low precision), while the rule-based detector is precise on the scanner but blind to patterns its rules don't encode. Moving the threshold slider makes the precision/recall trade-off visible live. This is exactly why the consensus mode exists.

### Edge-level highlighting

Node scores aren't the only signal — the graph view also highlights suspicious **edges**:

- **Bridge edges** (dashed amber) — removing them would split the network; computed with `nx.bridges()`.
- **New edges** (dotted teal) — device pairs whose *first ever* communication happened in the last quarter of the capture window (classic lateral-movement/scanning signature).

### Time window filter

The "Time window" range slider keeps only traffic inside the selected percentage of the capture, then rebuilds the graph and re-runs detection. Sliding it forward shows the network *before* and *after* an attack begins — with a demo scenario, restrict the window to the first 75% and the anomaly disappears, because the attack traffic only exists in the final quarter.

---

## 6. Codebase walkthrough

### `src/loader.py` — Loading & validating input data
`load_network_data()` takes a CSV path, file object, or DataFrame and:
- Confirms the required columns exist (`source`, `destination`, `timestamp`, `protocol`) — raises a clear error if not.
- Parses timestamps, drops rows with unparseable/missing dates.
- Cleans up whitespace, standardizes protocol names to uppercase, removes literal "nan" strings.
- Deduplicates identical rows.
- Raises an error if nothing valid is left.

This is the **data validation boundary** of the app — everything downstream can assume clean, well-typed data.

### `src/graph_builder.py` — Building the graph
`build_graph()` takes the cleaned DataFrame and constructs a NetworkX graph (`nx.Graph` or `nx.DiGraph`), aggregating repeated edges into a single weighted edge with a list of timestamps and protocols.

### `src/metrics.py` — Computing per-node statistics
`compute_node_metrics()` — computes every metric described in section 4 above, returns one row per node.
`compute_graph_statistics()` — computes graph-wide summary stats (total nodes/edges, average degree, density, number of connected components) — these are the 5 KPI cards at the top of the dashboard.

### `src/preprocessing.py` — Preparing features for ML
`select_feature_frame()` — picks out the numeric columns used as ML input, safely handling missing/non-numeric values.
`scale_features()` — standardizes those columns (see section 5).

### `src/anomaly_detection.py` — Running the detection algorithms
`detect_anomalies()` — the main entry point; dispatches to rule-based, one of the 3 ML models, or consensus voting based on the `algorithm` argument, applies the score threshold, and returns a sorted result (most anomalous first).
`_consensus_detection()` — runs all four base detectors and combines them by majority vote (see section 5).

### `src/scenarios.py` — Synthetic attack scenarios
`generate_scenario()` — builds seeded, reproducible office-network traffic and injects one labelled attack (scanner / exfiltration / rogue bridge / botnet). Returns the traffic rows **and** the ground-truth anomalous node names.
`list_scenarios()` — scenario metadata used to build the sidebar dropdown.

### `src/evaluation.py` — Scoring detectors against ground truth
`evaluate_detection()` — computes TP/FP/FN, precision, recall, and F1 for one detection result.
`compare_algorithms()` — runs every supported detector on the same features and evaluates each, producing the comparison table shown in the "Detector Evaluation" panel.

### `src/visualization.py` — Building the charts and graph visuals
- `create_cytoscape_elements()` / `create_cytoscape_stylesheet()` — build the interactive network graph you see in the dashboard (using Dash Cytoscape), including node coloring by anomaly severity or community.
- `create_degree_distribution()`, `create_centrality_distribution()`, `create_anomaly_histogram()`, `create_top_degree_chart()`, `create_protocol_distribution()` — the 5 analytics charts, built with Plotly.
- `create_network_figure()` / `export_network_png()` — a static (non-interactive) version of the graph used for PNG export, laid out using NetworkX's `spring_layout` (a physics-simulation-style layout where connected nodes pull together and unconnected ones push apart).

### `src/utils.py` — Small helpers
JSON (de)serialization helpers used to pass data between Dash callbacks (Dash stores data as JSON strings in browser-side "stores").

### `dashboard/layout.py` — The page structure
Defines the visual layout: header banner, KPI cards, the 3-column workspace (controls sidebar / network graph / selected-node panel), the analytics chart grid, and the anomalous-nodes table. Pure structure — no logic.

### `dashboard/components.py` — Reusable UI pieces
Builds the sidebar controls (upload, algorithm dropdown, threshold slider, etc.), the KPI stat cards, and the selected-node panel, as functions that return Dash component trees.

### `dashboard/callbacks.py` — The app's logic/interactivity
This is where "clicking things causes stuff to happen." Key callbacks:
- **`load_or_run`** — loads the default sample dataset or a user-uploaded CSV, builds the graph, computes metrics, and updates the KPI cards. Handles upload errors (bad CSV, too many nodes) gracefully.
- **`run_detection`** — runs the selected anomaly detection algorithm whenever the algorithm, threshold, or data changes.
- **`refresh_layout`** — recomputes the graph's visual layout only when the graph or the chosen layout algorithm changes (kept separate so re-layout doesn't happen every time you just change a color or select a node — that would make the graph visually "jump" for no reason).
- **`refresh_visuals`** — redraws the network graph coloring, the 5 charts, and the data table whenever relevant data changes.
- **`update_selected_node`** / **`update_node_panel`** — handle clicking a node (on the graph or in the table, or searching by name) and display its full metric breakdown.
- **`export_results`** — handles the CSV / JSON / PNG export buttons.

### `tests/` — Automated tests
Each test file checks one module in isolation with small, hand-crafted example graphs (not the full sample CSV) so failures are easy to diagnose:
- `test_loader.py` — validates error handling for bad/missing data.
- `test_graph.py` — validates graph construction, edge weighting, and edge cases (single-node, empty graphs).
- `test_metrics.py` — validates that metrics are computed and include expected columns.
- `test_detector.py` — validates the rule-based detector produces sensible scores/labels, and that consensus voting flags an obvious attacker with multiple detector votes.
- `test_scenarios.py` — validates every scenario passes loader validation, contains its ground-truth nodes, and is deterministic for a fixed seed.
- `test_evaluation.py` — validates precision/recall/F1 arithmetic and that `compare_algorithms` covers every detector.
- `test_visualization.py` — validates the graph visualization elements and stylesheets.

---

## 7. How data flows through the whole app (end to end)

```
CSV file
   │
   ▼
src/loader.py           → validates & cleans the raw rows
   │
   ▼
src/graph_builder.py     → builds a NetworkX graph (nodes + weighted edges)
   │
   ▼
src/metrics.py           → computes per-node metrics (degree, centralities, community, ...)
   │
   ▼
src/preprocessing.py     → selects & scales the numeric features for ML models
   │
   ▼
src/anomaly_detection.py → scores & labels each node (rule-based / Isolation Forest / LOF / One-Class SVM)
   │
   ▼
src/visualization.py     → turns the graph + metrics + anomaly scores into charts and a colored network view
   │
   ▼
dashboard/*.py            → renders it all in the browser and wires up interactivity
```

---

## 8. Anticipated questions & how to answer them

**Q: Why use a graph instead of just analyzing each device's traffic volume independently?**
A: Because a lot of anomalies are *structural* — they're about a device's *position* in the network (is it a bridge? does it sit between everything?), not just how much traffic it sends. That kind of pattern is invisible if you look at devices one at a time; you need the relationships (the graph) to see it.

**Q: Why 4 algorithms instead of just 1?**
A: They make different assumptions and catch different kinds of anomalies (see section 5). Offering a choice — and letting the user compare — makes the tool more robust and more transparent about its own limitations.

**Q: How do you know a flagged node is actually a real problem, and not a false positive?**
A: Two answers. On real data: this project detects *statistical* anomalies — a starting point for investigation, not a verdict; a human analyst should still look at flagged nodes (which is why the dashboard shows the "Reason Flagged," the node's full metrics, and its neighbors). On synthetic data: we *measured* it — the demo scenarios inject attacks with known ground truth, and the Detector Evaluation panel reports each algorithm's precision, recall, and F1 against that truth.

**Q: How did you evaluate your detectors?**
A: Two ways. First, with injected-anomaly scenarios (section 5b): we generate realistic baseline traffic, inject a known attack (scanner, exfiltration hub, rogue bridge, or botnet), run every detector on identical features, and score them with precision/recall/F1. Second, on **real data**: a 320-host slice of CTU-13 scenario 9 (real university traffic with 10 hosts infected by the Neris botnet, labeled flow-by-flow by the dataset authors). At the default threshold, consensus voting catches all 10 real bots with F1 = 0.87.

**Q: What did the real data teach you that the synthetic data didn't?**
A: Two things. (1) The rule-based detector, which was perfect on the synthetic scanner, catches only 6 of the 10 real bots — everything it flags is correct (precision 1.0), but it is blind to the bots whose behaviour its rules don't encode, while the ML models catch all 10. Hand-written rules encode assumptions that only partially transfer to real traffic. (2) We first tried CTU-13 scenario 11, whose bots run DDoS attacks: thousands of flows, but all to a *single* target — degree 1 on a who-talks-to-whom graph, completely invisible to our topological features. That's a real blind spot, documented in Future Work: volume-based features (weighted degree) would be needed to catch it. Finding a limitation through real-data testing is exactly what evaluation is for.

**Q: What would you improve with more time?**
A: See the README's "Future Work" section — session-aware timeline playback, deeper community-detection views, shortest-path investigation workflows, multi-tenant incident bookmarking, authentication/persistence.
