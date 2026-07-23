# Detection & Evaluation

How nodes become features, features become anomaly scores, and scores get
measured against ground truth. For the algorithm *intuitions* (why Isolation
Forest works, what betweenness means), see `PROJECT_GUIDE.md` at the repo root.

## Feature contract

`src/metrics.py::compute_node_metrics()` returns one row per node. The numeric
feature subset used by the ML models is defined in
`src/preprocessing.py::DEFAULT_FEATURE_COLUMNS`:

```
degree, degree_centrality, betweenness_centrality, closeness_centrality,
eigenvector_centrality, pagerank, clustering_coefficient, component_size,
unique_neighbours, new_neighbour_ratio
```

plus identifier/context columns (`node`, `community_id`, `is_bridge`,
`component_id`). `select_feature_frame()` picks the numeric subset and
`scale_features()` standardizes it (mean 0 / std 1) before the sklearn models —
without scaling, large-range features like degree would dominate the distance
math.

The temporal feature (`new_neighbour_ratio`) splits the capture timeline into
an early 75% and late 25%, and measures what fraction of each node's contacts
are new in the late window — the scanning / lateral-movement signature.

## Detector contract

Every algorithm receives the same feature frame and must return it plus:

| Column | Meaning |
|---|---|
| `anomaly_score` | float in [0, 1], min-max normalized (`_normalize_scores`) |
| `anomaly_label` | 0/1 after applying the user threshold to the score |
| `reason_flagged` | human-readable explanation; `"Within expected behavior"` when unflagged |

`detect_anomalies()` (in `src/anomaly_detection.py`) dispatches on the
`algorithm` string, re-applies the threshold uniformly, and sorts flagged-first.

## The six detectors

| Key | Method | Notes |
|---|---|---|
| `rule_based` | Hand-written statistical rules (mean + 1.5σ on degree/betweenness, new-neighbour ratio, isolated bridges) | Fully explainable; `reason_flagged` names the exact rule(s) |
| `isolation_forest` | `sklearn.ensemble.IsolationForest`, 200 trees | Good general-purpose default |
| `local_outlier_factor` | `sklearn.neighbors.LocalOutlierFactor`, 35 neighbors | Local-density based; its duplicate-values warning is expected on real captures (many identical quiet hosts) and suppressed |
| `one_class_svm` | `sklearn.svm.OneClassSVM`, RBF kernel | Tight boundary around "normal"; tends to over-flag |
| `consensus` | Runs all four above; score = mean, flagged on ≥ 2 votes | `reason_flagged` lists which detectors voted; adds a `detector_votes` column |
| `lightweight_gnn` | Hand-rolled 2-layer GCN autoencoder, plain PyTorch (no PyTorch Geometric); scores by feature-reconstruction error | Unsupervised, small by design (224 params, <1 KB); needs the graph, not just features — see [Lightweight GNN](lightweight-gnn.md) |

## Evaluation

When ground truth exists (demo scenario or converted real dataset),
`src/evaluation.py` scores detections:

- `evaluate_detection(result, truth)` → TP, FP, FN, precision, recall, F1
- `compare_algorithms(metrics, truth, threshold, graph=None)` → one row per
  detector, all run on **identical features** so the comparison is fair.
  Pass `graph` to include `lightweight_gnn` — it is silently skipped without one.

Precision = TP / (TP+FP) (low = alert fatigue). Recall = TP / (TP+FN)
(low = missed intrusions). F1 = harmonic mean of both.

### Reference results

Measured at the default threshold 0.65 (regenerate with the code in
`tests/test_evaluation.py` or by loading the scenario in the app):

- **Synthetic scanner**: Rule-Based and LOF reach F1 = 1.0.
- **Synthetic botnet**: hardest case; most detectors improve markedly at
  threshold ≈ 0.5 (the point of the live threshold slider).
- **CTU-13 scenario 9 (real, 10 bots)**: Consensus F1 ≈ 0.87 with recall 1.0;
  Isolation Forest and One-Class SVM similar; Rule-Based catches 6/10 with
  precision 1.0 — precise but blind to patterns its rules don't encode.
- **IoT-23 scenario 3-1 (real, port scan)**: Lightweight GNN ties the best
  classical detectors at F1 = 0.667. On CTU-13 it fails at the default
  threshold for a documented, reproducible reason — see
  [Lightweight GNN](lightweight-gnn.md#measured-results).

### Known limitations

Purely topological features cannot see **volume-based** attacks: CTU-13
scenario 11's DDoS bots send thousands of flows to a *single* target — degree 1
on a who-talks-to-whom graph. Flow-volume features (weighted degree, per-edge
flow counts) are the documented future-work fix.

Unsupervised structural/statistical detectors — the rule-based detector and
the Lightweight GNN alike — can mistake a legitimate, busy server for the real
threat, because both score "how unusual is this node's structural position,"
not "is this node malicious." Both hit this on CTU-13 scenario 9 independently;
see each detector's own writeup for the specifics.

## Determinism

Everything random is seeded (`random_state=42`, Louvain `seed=42`, scenario
generators use `random.Random(seed)`), so results are reproducible
run-to-run. Keep it that way — the tests rely on it.
