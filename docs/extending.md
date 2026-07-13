# Extending

Step-by-step recipes for the common extension points. Read
[Architecture](architecture.md) first for the contracts these rely on.

## Add a detection algorithm

1. Implement it in `src/anomaly_detection.py` following the detector contract
   (`anomaly_score` in [0,1], `anomaly_label`, `reason_flagged` — see
   [Detection & Evaluation](detection-and-evaluation.md)). For sklearn-style
   models, follow the pattern in `_model_detection`.
2. Register the dispatch branch in `detect_anomalies()`; add the key to
   `BASE_ALGORITHMS` if it should participate in consensus voting, and to
   `ALGORITHM_DISPLAY_NAMES`.
3. Add the dropdown option in `dashboard/components.py::sidebar_controls`.
4. Add a label in `src/evaluation.py::ALGORITHM_LABELS`; `compare_algorithms`
   picks it up automatically, so it appears in the evaluation panel.
5. Test it in `tests/test_detector.py` — use `_synthetic_feature_frame()` to
   build a frame with an obvious attacker the detector must flag.

## Add a synthetic scenario

1. In `src/scenarios.py`, write an injector:

   ```python
   def _my_attack(rng: random.Random, rows: list[dict], departments: dict[str, list[str]]) -> tuple[str, ...]:
       # append traffic with _row(source, destination, minute, protocol);
       # keep attack traffic after ATTACK_START_MINUTE so temporal features see it
       return ("ATTACKER-NODE",)   # the ground-truth anomalous nodes
   ```

2. Register it in `_SCENARIOS` with a key, display name, and description.

The sidebar dropdown, description text, and evaluation panel pick it up
automatically. `tests/test_scenarios.py` parametrizes over `list_scenarios()`,
so loader validation covers the new scenario with no test changes.

## Add a real dataset

Convert it to the dashboard CSV format and drop it in `data/` with a
`.truth.json` sidecar — see [Datasets](datasets.md). Nothing else to wire up.

## Add a node metric / feature

1. Compute it in `src/metrics.py::compute_node_metrics` and add it to each
   node's record.
2. Add the column name to `DEFAULT_FEATURE_COLUMNS` in `src/preprocessing.py`
   if the ML models should use it as input.
3. Optionally surface it in the node panel
   (`dashboard/callbacks.py::update_node_panel`) and in the rule-based reasons
   (`src/anomaly_detection.py::_build_reason_row`).
4. Extend `tests/test_metrics.py` to assert the column exists and is sane.

## Add a chart

1. Write `create_my_chart(frame) -> go.Figure` in `src/visualization.py`;
   spread `CHART_LAYOUT` into `update_layout(...)` for consistent styling.
2. Add a `dcc.Graph(id=...)` card to the chart grid in `dashboard/layout.py`.
3. Add the `Output` and the figure construction to
   `dashboard/callbacks.py::refresh_visuals`.

## Add a sidebar control

1. Add the component in `dashboard/components.py::sidebar_controls` with a
   kebab-case id.
2. Wire it as an `Input`/`State` into the relevant callback in
   `dashboard/callbacks.py`. If it changes *which data is loaded*, it belongs in
   `load_or_run`; if it changes *detection*, `run_detection`; if it changes
   *appearance only*, `refresh_visuals` (keep it out of `refresh_layout` unless
   it genuinely requires re-running the physics layout).
