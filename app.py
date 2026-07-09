"""Application entry point."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

from dashboard.callbacks import register_callbacks
from dashboard.layout import build_layout


cyto.load_extra_layouts()

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
    ],
    suppress_callback_exceptions=True,
    title="Graph-Based Network Anomaly Detection",
)
server = app.server
app.layout = build_layout()
register_callbacks(app)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

