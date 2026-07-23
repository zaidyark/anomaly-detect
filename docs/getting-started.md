# Getting Started

## Prerequisites

- Python 3.11+ (developed on 3.13)
- Optionally Docker + Docker Compose
- `requirements.txt` installs a CPU-only PyTorch build for the Lightweight
  GNN detector (via `--extra-index-url`, ~200 MB download) — no GPU or CUDA
  needed, and no PyTorch Geometric or compiled graph-library extensions

## Quick start

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

## All make targets

Run `make help` (or `make.bat help`) to list them:

| Target | Does |
|---|---|
| `venv` | Create the virtual environment only |
| `install` | Create `.venv` and install dependencies |
| `run` | Start the dashboard at http://127.0.0.1:8050 |
| `test` / `test-verbose` | Run the pytest suite |
| `convert-ctu13` | Convert a CTU-13 capture — see [Datasets](datasets.md) |
| `docker` / `docker-down` | Docker Compose up / down |
| `clean` | Remove the venv, caches, and build artifacts |

The venv lives in `.venv/`; the make targets always use it, so you never need to
activate it manually.

## Manual setup (without make)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

If you run `python app.py` directly, activate the venv first. Running with a
global interpreter works only if it happens to have all dependencies installed,
and version drift between the two causes confusing behavior (e.g., warnings or
errors pointing at `~/.pyenv/...` paths instead of `.venv/`).

## Docker

```bash
make docker        # docker compose up --build
make docker-down
```

## Next steps

- [User Guide](user-guide.md) — a tour of the dashboard and a suggested demo flow
- [Architecture](architecture.md) — if you're here to change the code
