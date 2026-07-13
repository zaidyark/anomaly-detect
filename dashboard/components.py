"""Reusable dashboard components."""

from __future__ import annotations

from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc

from src.scenarios import list_scenarios


def stat_card(title: str, value_id: str, icon: str, critical: bool = False) -> dbc.Card:
    """Create a compact statistics card."""
    icon_color = "#f43f5e" if critical else "#4b6178"
    className = "glass-card h-100" + (" stat-card--critical" if critical else "")
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Div(title, className="card-title"),
                        html.I(className=f"bi {icon}", style={"fontSize": "1.05rem", "color": icon_color}),
                    ],
                    className="d-flex justify-content-between align-items-center mb-2",
                ),
                html.Div(id=value_id, className="metric-value"),
            ],
            className="stat-card-body",
        ),
        className=className,
    )


def sidebar_controls() -> dbc.Card:
    """Build the sidebar controls panel."""
    return dbc.Card(
        [
            html.Div(
                [
                    html.Span("Controls", className="section-label"),
                    html.Button("«", id="sidebar-collapse-btn", className="sidebar-collapse-btn"),
                ],
                className="section-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Upload CSV", className="control-label"),
                            dcc.Upload(
                                id="upload-data",
                                children=html.Div(["Drag and drop or ", html.A("browse")]),
                                style={"cursor": "pointer"},
                                multiple=False,
                            ),
                            dbc.Alert(
                                id="upload-error",
                                color="danger",
                                is_open=False,
                                className="py-2 small mb-0 mt-2",
                            ),
                        ]
                    ),
                html.Div(
                    [
                        html.Div("Demo scenario", className="control-label"),
                        dcc.Dropdown(
                            id="scenario-select",
                            className="dash-dropdown",
                            options=[
                                {"label": "None (sample / uploaded data)", "value": "none"},
                            ]
                            + [
                                {"label": scenario["name"], "value": scenario["key"]}
                                for scenario in list_scenarios()
                            ],
                            value="none",
                            clearable=False,
                        ),
                        html.Div(id="scenario-description", className="scenario-description"),
                    ]
                ),
                dbc.Switch(
                    id="directed-toggle",
                    label="Directed graph",
                    value=False,
                    className="mb-0",
                ),
                html.Div(
                    [
                        html.Div("Algorithm selector", className="control-label"),
                        dcc.Dropdown(
                            id="algorithm-select",
                            className="dash-dropdown",
                            options=[
                                {"label": "Rule-Based", "value": "rule_based"},
                                {"label": "Isolation Forest", "value": "isolation_forest"},
                                {"label": "Local Outlier Factor", "value": "local_outlier_factor"},
                                {"label": "One-Class SVM", "value": "one_class_svm"},
                                {"label": "Consensus (all detectors vote)", "value": "consensus"},
                            ],
                            value="rule_based",
                            clearable=False,
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div("Threshold", className="control-label"),
                        dcc.Slider(
                            id="threshold-slider",
                            min=0.1,
                            max=0.95,
                            step=0.05,
                            value=0.65,
                            marks=None,
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div("Time window (% of capture)", className="control-label"),
                        dcc.RangeSlider(
                            id="time-range-slider",
                            min=0,
                            max=100,
                            step=5,
                            value=[0, 100],
                            marks={0: "0%", 50: "50%", 100: "100%"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div("Color nodes by", className="control-label"),
                        dcc.Dropdown(
                            id="color-mode-select",
                            className="dash-dropdown",
                            options=[
                                {"label": "Anomaly Severity", "value": "anomaly"},
                                {"label": "Community", "value": "community"},
                            ],
                            value="anomaly",
                            clearable=False,
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div("Graph layout", className="control-label"),
                        dcc.Dropdown(
                            id="layout-select",
                            className="dash-dropdown",
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
                    ]
                ),
                html.Div(
                    [
                        html.Div("Search node", className="control-label"),
                        dcc.Input(id="node-search", type="text", placeholder="Type device name", className="form-control"),
                    ]
                ),
                html.Div(
                    [
                        html.Div("Export format", className="control-label"),
                        dcc.Dropdown(
                            id="export-format",
                            className="dash-dropdown",
                            options=[
                                {"label": "CSV", "value": "csv"},
                                {"label": "JSON", "value": "json"},
                                {"label": "PNG Screenshot", "value": "png"},
                            ],
                            value="csv",
                            clearable=False,
                        ),
                    ]
                ),
                    dbc.Button("Run Detection", id="run-detection", color="primary", className="w-100 mb-0"),
                    dbc.Button("Export Results", id="export-results", color="secondary", outline=True, className="w-100"),
                    dcc.Download(id="download-results"),
                ],
                className="sidebar-collapsible",
            ),
        ],
        className="sidebar-panel",
    )


TABLE_STYLE_HEADER = {
    "backgroundColor": "#0c141f",
    "color": "#56718c",
    "fontWeight": "500",
    "fontSize": "12px",
    "border": "none",
    "borderBottom": "1px solid rgba(94, 234, 212, 0.12)",
    "padding": "12px 16px",
    "textAlign": "right",
}

TABLE_STYLE_CELL = {
    "backgroundColor": "#0c141f",
    "color": "#dfe8f2",
    "border": "none",
    "padding": "13px 16px",
    "fontFamily": "'IBM Plex Mono', monospace",
    "fontSize": "12px",
    "whiteSpace": "normal",
    "height": "auto",
    "textAlign": "right",
}


def evaluation_section() -> html.Div:
    """Detector evaluation panel, shown only when a demo scenario is active."""
    return html.Div(
        id="evaluation-section",
        style={"display": "none"},
        children=[
            html.Div("Detector Evaluation", className="section-label mb-2"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div(
                                        id="evaluation-summary",
                                        className="text-secondary mb-3",
                                        style={"fontSize": "13px"},
                                    ),
                                    dash_table.DataTable(
                                        id="evaluation-table",
                                        sort_action="native",
                                        style_table={"overflowX": "auto"},
                                        style_header=TABLE_STYLE_HEADER,
                                        style_cell=TABLE_STYLE_CELL,
                                        style_cell_conditional=[
                                            {"if": {"column_id": "algorithm"}, "textAlign": "left"},
                                        ],
                                        style_header_conditional=[
                                            {"if": {"column_id": "algorithm"}, "textAlign": "left"},
                                        ],
                                    ),
                                ]
                            ),
                            className="glass-card table-shell h-100",
                        ),
                        md=6,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                dcc.Graph(
                                    id="evaluation-chart",
                                    config={"displayModeBar": False, "responsive": True},
                                    style={"height": "100%", "width": "100%"},
                                )
                            ),
                            className="glass-card h-100",
                        ),
                        md=6,
                        className="mb-3",
                    ),
                ],
                className="g-3",
            ),
        ],
    )


def right_panel() -> dbc.Card:
    """Build the selected-node inspection panel."""
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div("Selected Node", className="panel-title"),
                html.Div(id="selected-node-name"),
                html.Div(id="selected-node-details"),
            ]
        ),
        className="panel-shell right-panel",
    )

