"""Application layout."""

from __future__ import annotations

from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

from dashboard.components import evaluation_section, right_panel, sidebar_controls, stat_card


def build_layout() -> dbc.Container:
    """Construct the overall dashboard layout."""
    return dbc.Container(
        fluid=True,
        className="app-shell py-3 px-3 px-xl-4",
        children=[
            dcc.Store(id="network-store"),
            dcc.Store(id="metrics-store"),
            dcc.Store(id="anomalies-store"),
            dcc.Store(id="selected-node-store"),
            dcc.Store(id="filtered-node-store"),
            dcc.Store(id="ground-truth-store"),
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Security Operations Center", className="title-mark"),
                                            html.H2("Graph-Based Network Anomaly Detection", className="mb-1"),
                                            html.Div(
                                                "Interactive graph analytics for detecting suspicious hosts, bridges, and unusual communication patterns.",
                                                className="text-secondary",
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Div("● LIVE", className="live-badge"),
                                            html.Div(id="last-scan-label", children="AWAITING FIRST SCAN"),
                                        ],
                                        className="banner-status",
                                    ),
                                ],
                                className="d-flex align-items-center justify-content-between",
                            )
                        ),
                        className="top-banner mb-3",
                    )
                )
            ),
            dbc.Row(
                [
                    dbc.Col(stat_card("Nodes", "stat-nodes", "bi-diagram-3"), md=2, className="stat-col"),
                    dbc.Col(stat_card("Edges", "stat-edges", "bi-link-45deg"), md=2, className="stat-col"),
                    dbc.Col(stat_card("Average Degree", "stat-avg-degree", "bi-graph-up"), md=2, className="stat-col"),
                    dbc.Col(stat_card("Detected Anomalies", "stat-anomalies", "bi-shield-exclamation", critical=True), md=3, className="stat-col"),
                    dbc.Col(stat_card("Density", "stat-density", "bi-braces"), md=3, className="stat-col"),
                ],
                className="g-3 mb-3",
            ),
            html.Div(
                [
                    html.Div(sidebar_controls(), className="sidebar-col"),
                    dbc.Card(
                        [
                            html.Div(
                                [
                                    html.Span("Network Graph", className="section-label"),
                                    html.Div(
                                        [
                                            html.Span("Normal", className="legend-dot legend-dot--normal"),
                                            html.Span("Suspicious", className="legend-dot legend-dot--warning"),
                                            html.Span("Anomaly", className="legend-dot legend-dot--anomaly"),
                                            html.Span("Bridge edge", className="legend-dot legend-dot--bridge"),
                                            html.Span("New edge", className="legend-dot legend-dot--new"),
                                            html.Button(
                                                "FIT",
                                                id="fit-view-btn",
                                                className="graph-expand-btn graph-expand-btn--fit",
                                                title="Fit the whole graph in view",
                                            ),
                                            html.Button(
                                                "⛶",
                                                id="graph-fullscreen-btn",
                                                className="graph-expand-btn",
                                                title="Toggle fullscreen",
                                            ),
                                        ],
                                        className="graph-legend",
                                    ),
                                ],
                                className="graph-card-header",
                            ),
                            dcc.Loading(
                                cyto.Cytoscape(
                                    id="network-graph",
                                    className="cy-container",
                                    style={"width": "100%", "height": "100%"},
                                    responsive=True,
                                    elements=[],
                                    stylesheet=[],
                                    layout={
                                        "name": "fcose",
                                        "animate": True,
                                        "fit": True,
                                        "padding": 40,
                                        "randomize": False,
                                        "seed": 42,
                                    },
                                    minZoom=0.03,
                                    maxZoom=3.5,
                                    zoom=1,
                                    pan={"x": 0, "y": 0},
                                ),
                                type="circle",
                            ),
                        ],
                        id="graph-card",
                        className="glass-card graph-card",
                    ),
                    right_panel(),
                ],
                id="workspace-grid",
                className="workspace-grid",
            ),
            html.Div("Analytics", className="section-label mb-2"),
            dbc.Row(
                dbc.Col(
                    html.Div(
                        [
                            dbc.Card(
                                dbc.CardBody(dcc.Graph(id="degree-distribution", config={"displayModeBar": False, "responsive": True}, style={"height": "100%", "width": "100%"})),
                                className="glass-card",
                            ),
                            dbc.Card(
                                dbc.CardBody(dcc.Graph(id="centrality-distribution", config={"displayModeBar": False, "responsive": True}, style={"height": "100%", "width": "100%"})),
                                className="glass-card",
                            ),
                            dbc.Card(
                                dbc.CardBody(dcc.Graph(id="anomaly-histogram", config={"displayModeBar": False, "responsive": True}, style={"height": "100%", "width": "100%"})),
                                className="glass-card",
                            ),
                            dbc.Card(
                                dbc.CardBody(dcc.Graph(id="top-degree-chart", config={"displayModeBar": False, "responsive": True}, style={"height": "100%", "width": "100%"})),
                                className="glass-card",
                            ),
                            dbc.Card(
                                dbc.CardBody(dcc.Graph(id="protocol-distribution", config={"displayModeBar": False, "responsive": True}, style={"height": "100%", "width": "100%"})),
                                className="glass-card",
                            ),
                        ],
                        className="chart-grid",
                    ),
                    width=12,
                ),
                className="mb-3",
            ),
            evaluation_section(),
            html.Div("Anomalous Nodes", className="section-label mb-2"),
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dash_table.DataTable(
                                    id="anomaly-table",
                                    page_size=10,
                                    sort_action="native",
                                    row_selectable="single",
                                    markdown_options={"html": True},
                                    style_table={"overflowX": "auto"},
                                    style_header={
                                        "backgroundColor": "#0c141f",
                                        "color": "#56718c",
                                        "fontWeight": "500",
                                        "fontSize": "12px",
                                        "border": "none",
                                        "borderBottom": "1px solid rgba(94, 234, 212, 0.12)",
                                        "padding": "12px 16px",
                                        "textAlign": "right",
                                    },
                                    style_cell={
                                        "backgroundColor": "#0c141f",
                                        "color": "#dfe8f2",
                                        "border": "none",
                                        "padding": "13px 16px",
                                        "fontFamily": "'IBM Plex Mono', monospace",
                                        "fontSize": "12px",
                                        "whiteSpace": "normal",
                                        "height": "auto",
                                        "textAlign": "right",
                                    },
                                    style_cell_conditional=[
                                        {"if": {"column_id": "node"}, "textAlign": "left"},
                                    ],
                                    style_header_conditional=[
                                        {"if": {"column_id": "node"}, "textAlign": "left"},
                                    ],
                                ),
                            ]
                        ),
                        className="glass-card table-shell",
                    ),
                    className="mb-3",
                )
            ),
        ],
    )
