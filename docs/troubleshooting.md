# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Address already in use` on start | Another instance is on port 8050: `fuser -k 8050/tcp` (Linux/WSL) or find it with `netstat -ano \| findstr 8050` (Windows), then restart |
| Graph shows only edges / must pan to find nodes | Old build — fixed by the zoom-floor change (`minZoom: 0.03`) and the FIT button; restart the app |
| Table flags nodes but the graph doesn't recolor | Old build — node severity now follows `anomaly_label`; restart the app |
| sklearn `Duplicate values` warning from LOF | Expected on real captures (many quiet hosts share identical feature rows); it's suppressed in `_model_detection`. If it reappears, sklearn changed the message string the filter matches |
| Upload rejected | Not a `.csv`, missing required columns, more than 750 nodes, or no valid rows after cleaning — the alert text says which |
| Evaluation panel missing | It only appears when ground truth exists: select a demo scenario, or add a dataset with a `.truth.json` sidecar (see [Datasets](datasets.md)) |
| CTU-13 scenario loads slowly | Normal — 320 nodes of betweenness/community computation takes a few seconds; the spinner covers it |
| PNG export fails | `kaleido` missing or broken in the active environment — `make install` and run via `make run` |
| Changes don't appear in the browser | You're running a different interpreter/checkout than you edited (check for `~/.pyenv/...` vs `.venv/...` in tracebacks), or the server needs a restart; hard-refresh with Ctrl+Shift+R |
| Warnings/tracebacks reference `~/.pyenv/...` paths | You launched with a global Python instead of the project venv — use `make run`, or activate `.venv` first |
| `make` not found on Windows | Use `make.bat` — same targets, plain batch, no install needed |
