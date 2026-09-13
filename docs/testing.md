# Testing

## Running

```bash
make test                                        # quiet
make test-verbose                                # full output
.venv/bin/pytest tests/test_detector.py -k consensus   # one test
```

Windows: `make.bat test` / `make.bat test-verbose`.

## Running the detector evaluation (CLI)

`pytest` checks evaluation *arithmetic* against toy data; it does not print
real detector accuracy. For that, run every detector against every
scenario/dataset directly from the command line:

```bash
make evaluate                                          # every scenario, threshold 0.65
make evaluate ARGS="--scenario ctu13_scenario9"        # one dataset
make evaluate ARGS="--threshold 0.5 0.65 0.8"          # threshold sweep
make evaluate ARGS="--no-gnn"                          # skip GNN training (faster)
make evaluate ARGS="--output results.md"               # also write a Markdown report
```

Or directly: `.venv/bin/python scripts/run_evaluation.py --list` to see
available scenario keys, `--help` for all options. Windows: `make.bat
evaluate <args>` or `.venv\Scripts\python.exe scripts\run_evaluation.py`.

This is the same pipeline the dashboard uses
(`load_network_data` → `build_graph` → `compute_node_metrics` →
`compare_algorithms`), so its numbers match what the "Detector Evaluation"
panel shows for the same scenario and threshold — it just doesn't need a
browser, which makes it the source for the results tables in Chapter Four.

## Suite layout

One test file per `src/` module:

| File | Covers |
|---|---|
| `test_loader.py` | Validation errors, cleaning, dedup |
| `test_graph.py` | Graph construction, edge weights, edge cases (empty / single node) |
| `test_metrics.py` | Metric computation and expected columns |
| `test_detector.py` | Rule-based scoring; consensus voting flags an obvious attacker with ≥2 votes |
| `test_scenarios.py` | Every scenario passes loader validation, contains its ground-truth nodes, is deterministic; file-backed datasets load (skipped if none present) |
| `test_evaluation.py` | Precision/recall/F1 arithmetic; `compare_algorithms` covers every detector |
| `test_visualization.py` | Cytoscape element/class generation (including the labels-follow-threshold regression), stylesheet modes |

## Principles

- Test `src/` modules directly with small hand-built DataFrames and graphs — no
  Dash, no browser, no bundled datasets (except the deliberately-conditional
  file-backed scenario test).
- Anything involving randomness must be seeded; scenario generation asserts
  determinism explicitly.
- When you fix a bug, add the regression test in the same commit — see
  `test_node_severity_follows_detection_labels_at_low_threshold` for the
  pattern (graph coloring once ignored the threshold; the test pins the fix).

## Manual smoke pass

Callbacks have no automated tests — verify them by running the app. A full
pass takes about a minute:

1. Load a demo scenario → KPIs, graph, charts, and table populate.
2. Drag the threshold down/up → graph recolors **in sync with** the table.
3. Switch algorithm to Consensus → click a red node → reason shows detector votes.
4. Evaluation panel visible with sensible precision/recall.
5. FIT and ⛶ fullscreen buttons behave; layouts switch without breaking fit.
6. Time-window slider to 0–75% → scenario anomaly disappears.
7. Upload a CSV (switches out of the scenario); upload garbage → friendly error.
8. Export CSV, JSON, and PNG.
