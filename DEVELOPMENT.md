# Developer Documentation

Technical reference for working on this codebase: setup, architecture, the Dash
callback graph, module reference, extension recipes, and troubleshooting.
For the *concepts* (what betweenness centrality means, how Isolation Forest works),
see `PROJECT_GUIDE.md`; for a user-facing overview, see `README.md`.

---

## 1. Setup

### Prerequisites

- Python 3.11+ (developed on 3.13)
- Optionally Docker + Docker Compose

### Quick start

Linux / macOS:

```bash
make install   # create .venv and install dependencies
make run       # start the dashboard at http://127.0.0.1:8050
make test      # run the test suite
```

Windows:

```bat
make.bat install
make.bat run
make.bat test
```

Run `make help` (or `make.bat help`) for all targets. The venv lives in `.venv/`;
`make run`/`make test` always use it, so you never need to activate it manually.
If you run `python app.py` directly instead, activate the venv first
(`source .venv/bin/activate` or `.venv\Scripts\activate`) — running with a global
interpreter works only if it happens to have all dependencies, and version drift
between the two causes confusing behavior.

### Docker

```bash
make docker        # docker compose up --build
make docker-down
```

---

## 2. Project layout

```
app.py                  Entry point: creates the Dash app, loads layout, registers callbacks
src/                    Pure-Python analytics core (no Dash imports — everything here is unit-testable)
  loader.py             CSV validation boundary
  graph_builder.py      DataFrame -> NetworkX graph
  metrics.py            Per-node metrics + graph-level statistics
  preprocessing.py      Feature selection & scaling for the ML models
  anomaly_detection.py  The 5 detectors (rule-based, 3 sklearn models, consensus)
  scenarios.py          Synthetic attack generators + file-backed real datasets
  evaluation.py         Precision/recall/F1 scoring against ground truth
  visualization.py      Cytoscape elements/stylesheets + Plotly figures
  utils.py              JSON (de)serialization helpers for Dash stores
dashboard/              Dash-specific code
  layout.py             Page structure (stores, banner, KPI row, workspace, charts, tables)
  components.py         Reusable component builders (sidebar, stat cards, evaluation panel)
  callbacks.py          All interactivity — the only place callbacks are registered
assets/style.css        All styling (Dash serves assets/ automatically)
data/                   Bundled datasets (sample CSV, converted CTU-13 slice + .truth.json)
scripts/convert_ctu13.py  Real-dataset converter (see §7)
tests/                  Pytest suite, one file per src module
```

**Dependency rule:** `src/` must never import from `dashboard/`. `dashboard/`
imports freely from `src/`. This keeps the analytics core testable without a
browser and reusable outside Dash.

---

## 3. Architecture & data flow

One request cycle, from CSV to pixels:

```
CSV / generated frame
      │  load_network_data()          validates columns, parses timestamps, dedupes
      ▼
src/loader.py
      │  build_graph()                nx.Graph or nx.DiGraph; repeated contacts
      ▼                               aggregate into one weighted edge
src/graph_builder.py
      │  compute_node_metrics()       degree, centralities, clustering, communities,
      ▼                               bridges, new-neighbour ratio (early-75%/late-25% split)
src/metrics.py
      │  detect_anomalies()           per-node anomaly_score (0-1), anomaly_label,
      ▼                               reason_flagged; consensus mode runs all 4 and votes
src/anomaly_detection.py
      │  create_cytoscape_elements()  nodes classed normal/warning/anomaly; edges classed
      ▼  create_*() figures           bridge-edge / new-edge; 5 Plotly charts
src/visualization.py
      │
      ▼
dashboard/callbacks.py                orchestrates the above inside Dash callbacks
```

All intermediate state is serialized to JSON strings and kept in browser-side
`dcc.Store` components (see next section) — the server holds no per-session state,
which is why callbacks always rebuild the graph from the stored edge list.

---

## 4. Dash state & callback graph

### Stores (defined in `dashboard/layout.py`)

| Store | Contents |
|---|---|
| `network-store` | `{edges: <json records>, metrics: <json>, statistics: {...}, directed: bool}` |
| `metrics-store` | Node metrics table (JSON records) — duplicated out of network-store so detection can depend on it alone |
| `anomalies-store` | Detection result table: metrics + `anomaly_score`, `anomaly_label`, `reason_flagged` (+ `detector_votes` for consensus) |
| `ground-truth-store` | List of known-anomalous node names; non-empty only when a scenario is active. Gates the evaluation panel |
| `selected-node-store` | Name of the currently selected node |

### Callbacks (all in `dashboard/callbacks.py`)

```
load_or_run          IN:  run-detection click, upload contents, directed-toggle,
                          scenario-select, time-range-slider
                     OUT: network-store, metrics-store, ground-truth-store,
                          4 KPI cards, upload-error
                     Data source precedence: upload trigger > active scenario >
                     previously uploaded file > bundled sample dataset.

run_detection        IN:  metrics-store, algorithm-select, threshold-slider
                     OUT: anomalies-store, anomaly KPI, last-scan label

refresh_layout       IN:  network-store, layout-select, fit-view-btn
                     OUT: network-graph.layout
                     Kept separate from refresh_visuals so recoloring/selection
                     never re-runs the physics layout (prevents visual jumping).
                     The FIT button varies a dummy key in the layout dict to
                     force Cytoscape to re-run + refit the same layout.

refresh_visuals      IN:  network-store, metrics-store, anomalies-store,
                          selected-node-store, color-mode-select (State: threshold)
                     OUT: graph elements + stylesheet, 5 chart figures,
                          anomaly table data/columns
                     Severity classes come from anomaly_label (not raw score),
                     so the graph always matches the table. Stylesheet switches
                     to compact mode above 150 nodes (smaller nodes, labels only
                     on flagged/selected).

update_evaluation    IN:  metrics-store, ground-truth-store, threshold-slider
                     OUT: evaluation section visibility, summary, table, chart
                     Runs compare_algorithms() (all 5 detectors) when ground
                     truth exists; hidden otherwise.

update_selected_node IN:  graph tap, table row selection, search box
                     OUT: selected-node-store

update_node_panel    IN:  selected-node-store + all data stores
                     OUT: right-hand node inspection panel (metrics, neighbours,
                          score, reason, ground-truth badge)

reset_scenario_on_upload   Uploading a CSV flips scenario-select back to "none";
                           load_or_run defers to this on upload-while-scenario-active
                           (raises PreventUpdate and lets the reset re-trigger it).

export_results       CSV / JSON of anomalies, or PNG via kaleido.

clientside           Sidebar collapse toggle; graph fullscreen toggle (adds
                     .graph-card--fullscreen and dispatches a window resize so
                     Cytoscape refits).
```

**Callback conventions**

- Every callback that reads a store parses it with `_read_json_frame()` — never
  `pd.read_json` directly (it wraps the StringIO handling).
- Raise `PreventUpdate` for "nothing to do"; return `no_update` per-output when
  only some outputs should change.
- User-facing failures (bad CSV, empty time window, oversized upload) are
  `ValueError`s raised inside the build helpers and caught once in `load_or_run`,
  which surfaces them in the `upload-error` alert.

---

## 5. The detection pipeline

### Feature contract

`compute_node_metrics()` returns one row per node with the columns listed in
`src/preprocessing.py::DEFAULT_FEATURE_COLUMNS` (plus identifiers like `node`,
`community_id`, `is_bridge`). Detectors receive this exact frame; `select_feature_frame()`
picks the numeric feature subset and `scale_features()` standardizes it
(mean 0 / std 1) before the sklearn models.

### Detector contract

Every algorithm — including any new one — must return the input frame plus:

| Column | Meaning |
|---|---|
| `anomaly_score` | float in [0, 1], min-max normalized (`_normalize_scores`) |
| `anomaly_label` | 0/1 after applying the user threshold to the score |
| `reason_flagged` | human-readable explanation, `"Within expected behavior"` when unflagged |

`detect_anomalies()` dispatches on the `algorithm` string, re-applies the
threshold uniformly, and sorts flagged-first. Consensus (`_consensus_detection`)
runs the four base detectors, averages scores, and flags on ≥2 votes.

### Determinism

Everything that involves randomness is seeded (`random_state=42`, `seed=42`,
Louvain `seed=42`, scenario generators use `random.Random(seed)`), so results
are reproducible run-to-run. Keep it that way — the tests rely on it.

---

## 6. Extension recipes

### Add a detection algorithm

1. Implement it in `src/anomaly_detection.py` following the detector contract
   above (see `_model_detection` for the sklearn pattern).
2. Register the dispatch branch in `detect_anomalies()` and add the key to
   `BASE_ALGORITHMS` (if it should participate in consensus voting) and
   `ALGORITHM_DISPLAY_NAMES`.
3. Add the dropdown option in `dashboard/components.py::sidebar_controls`.
4. Add a label in `src/evaluation.py::ALGORITHM_LABELS` so the evaluation
   table names it properly. It is picked up automatically by `compare_algorithms`.
5. Test it in `tests/test_detector.py` (use `_synthetic_feature_frame` for an
   obvious attacker the detector must flag).

### Add a synthetic scenario

1. In `src/scenarios.py`, write an injector `def _my_attack(rng, rows, departments) -> tuple[str, ...]`
   that appends traffic rows (use `_row()`, keep attack traffic after
   `ATTACK_START_MINUTE` so temporal features see it) and returns the
   ground-truth node names.
2. Register it in `_SCENARIOS` with a key, display name, and description.
   The sidebar dropdown, description text, and evaluation panel pick it up
   automatically. `tests/test_scenarios.py` parametrizes over `list_scenarios()`,
   so the loader-validation test covers it with no changes.

### Add a real dataset

Convert it to `source,destination,timestamp,protocol` CSV and write a sidecar
`data/<name>.truth.json`:

```json
{"name": "Display Name", "description": "...", "true_anomalies": ["ip1", "ip2"]}
```

Any `data/*.csv` + `.truth.json` pair is auto-discovered by
`src/scenarios.py::_file_backed_scenarios` and appears in the dropdown. For
CTU-13 captures, `scripts/convert_ctu13.py` does all of this (see §7).

### Add a node metric / feature

1. Compute it in `src/metrics.py::compute_node_metrics` and add it to each record.
2. Add the column name to `DEFAULT_FEATURE_COLUMNS` in `src/preprocessing.py`
   if the ML models should use it.
3. Optionally surface it in the node panel (`update_node_panel`) and rule-based
   reasons (`_build_reason_row`).

### Add a chart

1. Write `create_my_chart(frame) -> go.Figure` in `src/visualization.py`; spread
   `CHART_LAYOUT` into `update_layout` for consistent styling.
2. Add a `dcc.Graph(id=...)` card to the chart grid in `dashboard/layout.py`.
3. Add the `Output` and figure construction to `refresh_visuals`.

---

## 7. The CTU-13 converter

`scripts/convert_ctu13.py` turns a labeled CTU-13 `.binetflow` capture into a
dashboard-ready dataset:

- Detects infected hosts from flow labels (`From-Botnet` sources) — no hardcoding.
- Samples up to `MAX_FLOWS_PER_BOT` flows per bot, **interleaved round-robin**
  so every bot keeps its fan-out signature under the node budget.
- Keeps labeled-normal flows, then internal (`147.32.*`) background traffic.
- Enforces `NODE_BUDGET` (320) greedily: a flow is kept only if its endpoints
  fit the budget; flows between already-included nodes are always kept, so
  edge weights stay realistic.
- Writes the CSV plus the `.truth.json` sidecar.

```bash
make convert-ctu13 CAPTURE=capture20110817.binetflow OUT=data/my_slice.csv NAME="My Scenario"
```

Captures: https://www.stratosphereips.org/datasets-ctu13 (scenario 9 = directory
`CTU-Malware-Capture-Botnet-50`, ~273 MB). Tuning knobs are the constants at the
top of the script. Note the node budget trades fidelity for renderability —
document the budget you used if you quote results.

Known limitation worth remembering: scenario 11's DDoS bots send thousands of
flows to a *single* target (degree 1 topologically) and are invisible to the
current features. See "flow-volume features" in the README's Future Work.

---

## 8. Testing

```bash
make test            # quiet
make test-verbose
.venv/bin/pytest tests/test_detector.py -k consensus   # one test
```

Layout of the suite:

| File | Covers |
|---|---|
| `test_loader.py` | Validation errors, cleaning, dedup |
| `test_graph.py` | Graph construction, weights, edge cases (empty/single node) |
| `test_metrics.py` | Metric computation and expected columns |
| `test_detector.py` | Rule-based scoring; consensus voting on an obvious attacker |
| `test_scenarios.py` | Every scenario passes loader validation, contains its ground truth, deterministic; file-backed datasets load |
| `test_evaluation.py` | Precision/recall/F1 arithmetic; `compare_algorithms` covers all detectors |
| `test_visualization.py` | Element/class generation (incl. label-follows-threshold regression), stylesheets |

Principles: test `src/` modules directly with small hand-built frames (no Dash,
no browser); anything with randomness must be seeded; when you fix a bug, add
the regression test in the same commit (see
`test_node_severity_follows_detection_labels_at_low_threshold` for the pattern).

Callbacks have no automated tests — verify them by running the app. A quick
manual smoke pass: load a scenario → threshold slider down/up (graph recolors in
sync with the table) → switch algorithm to Consensus → click a red node → FIT →
fullscreen → export CSV.

---

## 9. Performance notes

- `betweenness_centrality` is O(V·E) and dominates metric computation; ~600
  nodes is comfortably interactive, thousands is not. `MAX_UPLOAD_NODES` (750,
  in `dashboard/callbacks.py`) guards uploads for rendering *and* compute reasons.
- The graph is rebuilt from the stored edge list on every visual refresh —
  cheap at these sizes, and stateless-server-friendly. Don't cache NetworkX
  objects server-side without rethinking multi-session behavior.
- Compact rendering kicks in above 150 nodes (`refresh_visuals`); node sizing
  scales to the graph's actual max degree.
- `minZoom` is 0.03 so `fit` can always show the whole graph; the FIT button
  re-runs the layout if the user gets lost.

---

## 10. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Address already in use` on start | Another instance is on 8050: `fuser -k 8050/tcp` (Linux) or find it with `netstat -ano \| findstr 8050` (Windows) |
| Graph shows only edges / must pan to find nodes | You're on an old build — the zoom floor fix (`minZoom: 0.03`) and FIT button address this; restart the app |
| Table flags nodes but graph doesn't recolor | Same — severity now follows `anomaly_label`; restart the app |
| sklearn `Duplicate values` warning from LOF | Expected on real captures (many identical quiet hosts); suppressed in `_model_detection` — if you see it, the suppression filter's message string no longer matches |
| Upload rejected | Not a `.csv`, missing required columns, >750 nodes, or no valid rows after cleaning — the alert text says which |
| Evaluation panel missing | It only appears when ground truth exists (scenario selected, or file-backed dataset with `.truth.json`) |
| PNG export fails | `kaleido` missing or broken in the env — `pip install -r requirements.txt` into `.venv` and run via `make run` |
| Changes don't appear in the browser | You edited while running a non-debug server, or you're running a different checkout/interpreter — check the process and hard-refresh (Ctrl+Shift+R) |

---

## 11. Conventions

- Python: type hints on public functions, `from __future__ import annotations`,
  dataclasses for structured returns (`DetectionResult`, `ScenarioResult`,
  `GraphStatistics`), module docstrings.
- `src/` stays Dash-free (import rule from §2).
- IDs: kebab-case for Dash component ids (`anomaly-table`), snake_case for
  Python. CSS class names follow BEM-ish modifiers (`graph-card--fullscreen`).
- Colors and chart styling live in `src/visualization.py` (`NODE_*`,
  `COMMUNITY_PALETTE`, `CHART_LAYOUT`) and `assets/style.css` — don't inline
  new hex values elsewhere.
- Commit style: imperative summary line explaining the *why*, body listing the
  what (see `git log`).
