# Architecture

Code structure, data flow, and the Dash state/callback graph.

## Project layout

```
app.py                  Entry point: creates the Dash app, loads layout, registers callbacks
src/                    Pure-Python analytics core (no Dash imports — unit-testable)
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
scripts/convert_ctu13.py  Real-dataset converter (see docs/datasets.md)
tests/                  Pytest suite, one file per src module
```

**Dependency rule:** `src/` must never import from `dashboard/`. `dashboard/`
imports freely from `src/`. This keeps the analytics core testable without a
browser and reusable outside Dash.

## Data flow

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
`dcc.Store` components — the server holds no per-session state, which is why
callbacks always rebuild the graph from the stored edge list.

## Stores

Defined in `dashboard/layout.py`:

| Store | Contents |
|---|---|
| `network-store` | `{edges: <json records>, metrics: <json>, statistics: {...}, directed: bool}` |
| `metrics-store` | Node metrics table (JSON records) — duplicated out of network-store so detection can depend on it alone |
| `anomalies-store` | Detection result: metrics + `anomaly_score`, `anomaly_label`, `reason_flagged` (+ `detector_votes` for consensus) |
| `ground-truth-store` | List of known-anomalous node names; non-empty only when a scenario is active. Gates the evaluation panel |
| `selected-node-store` | Name of the currently selected node |

## Callback graph

All in `dashboard/callbacks.py`:

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

### Callback conventions

- Every callback that reads a store parses it with `_read_json_frame()` — never
  `pd.read_json` directly (it wraps the StringIO handling).
- Raise `PreventUpdate` for "nothing to do"; return `no_update` per-output when
  only some outputs should change.
- User-facing failures (bad CSV, empty time window, oversized upload) are
  `ValueError`s raised inside the build helpers and caught once in `load_or_run`,
  which surfaces them in the `upload-error` alert.

## Performance notes

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

## Conventions

- Python: type hints on public functions, `from __future__ import annotations`,
  dataclasses for structured returns (`DetectionResult`, `ScenarioResult`,
  `GraphStatistics`), module docstrings.
- `src/` stays Dash-free (dependency rule above).
- IDs: kebab-case for Dash component ids (`anomaly-table`), snake_case for
  Python. CSS class names follow BEM-ish modifiers (`graph-card--fullscreen`).
- Colors and chart styling live in `src/visualization.py` (`NODE_*`,
  `COMMUNITY_PALETTE`, `CHART_LAYOUT`) and `assets/style.css` — don't inline
  new hex values elsewhere.
- Commit style: imperative summary line explaining the *why*, body listing the
  what (see `git log`).
