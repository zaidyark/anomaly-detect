"""Reusable dashboard components."""

from __future__ import annotations

from dash import dcc, html
import dash_bootstrap_components as dbc


def stat_card(title: str, value_id: str, icon: str) -> dbc.Card:
    """Create a compact statistics card."""
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Div(title, className="card-title"),
                        html.I(className=f"bi {icon}", style={"fontSize": "1.2rem", "color": "#3da9fc"}),
                    ],
                    className="d-flex justify-content-between align-items-center mb-2",
                ),
                html.Div(id=value_id, className="metric-value"),
            ]
        ),
        className="glass-card h-100",
    )


def sidebar_controls() -> dbc.Card:
    """Build the sidebar controls panel."""
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div("Controls", className="section-header"),
                html.Div("Upload CSV", className="control-label"),
                dcc.Upload(
                    id="upload-data",
                    children=html.Div(["Drag and drop or ", html.A("browse")]),
                    className="p-3 mb-3 rounded border border-secondary",
                    style={"cursor": "pointer"},
                    multiple=False,
                ),
                dbc.Alert(
                    id="upload-error",
                    color="danger",
                    is_open=False,
                    className="mb-3 py-2 small",
                ),
                dbc.Switch(
                    id="directed-toggle",
                    label="Directed graph",
                    value=False,
                    className="mb-3",
                ),
                html.Div("Algorithm selector", className="control-label"),
                dcc.Dropdown(
                    id="algorithm-select",
                    className="dash-dropdown mb-3",
                    options=[
                        {"label": "Rule-Based", "value": "rule_based"},
                        {"label": "Isolation Forest", "value": "isolation_forest"},
                        {"label": "Local Outlier Factor", "value": "local_outlier_factor"},
                        {"label": "One-Class SVM", "value": "one_class_svm"},
                    ],
                    value="rule_based",
                    clearable=False,
                ),
                html.Div("Threshold", className="control-label"),
                dcc.Slider(
                    id="threshold-slider",
                    min=0.1,
                    max=0.95,
                    step=0.05,
                    value=0.65,
                    marks={0.2: "0.2", 0.4: "0.4", 0.6: "0.6", 0.8: "0.8"},
                    tooltip={"placement": "bottom", "always_visible": False},
                ),
                html.Div("Color nodes by", className="control-label"),
                dcc.Dropdown(
                    id="color-mode-select",
                    className="dash-dropdown mb-3",
                    options=[
                        {"label": "Anomaly Severity", "value": "anomaly"},
                        {"label": "Community", "value": "community"},
                    ],
                    value="anomaly",
                    clearable=False,
                ),
                html.Div("Graph layout", className="control-label mt-3"),
                dcc.Dropdown(
                    id="layout-select",
                    className="dash-dropdown mb-3",
                    options=[
                        {"label": "Fcose (Stable)", "value": "fcose"},
                        {"label": "Breadth First", "value": "breadthfirst"},
                        {"label": "Circle", "value": "circle"},
                        {"label": "Concentric", "value": "concentric"},
                        {"label": "Grid", "value": "grid"},
                    ],
                    value="fcose",
                    clearable=False,
                ),
                html.Div("Search node", className="control-label"),
                dcc.Input(id="node-search", type="text", placeholder="Type device name", className="form-control mb-3"),
                html.Div("Export format", className="control-label"),
                dcc.Dropdown(
                    id="export-format",
                    className="dash-dropdown mb-3",
                    options=[
                        {"label": "CSV", "value": "csv"},
                        {"label": "JSON", "value": "json"},
                        {"label": "PNG Screenshot", "value": "png"},
                    ],
                    value="csv",
                    clearable=False,
                ),
                dbc.Button("Run Detection", id="run-detection", color="primary", className="w-100 mb-2"),
                dbc.Button("Export Results", id="export-results", color="secondary", outline=True, className="w-100"),
                dcc.Download(id="download-results"),
            ]
        ),
        className="sidebar-panel",
    )


def right_panel() -> dbc.Card:
    """Build the selected-node inspection panel."""
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div("Selected Node", className="section-header"),
                html.Div(id="selected-node-name", className="h4"),
                html.Div(id="selected-node-details", className="small"),
            ]
        ),
        className="panel-shell right-panel h-100",
    )

