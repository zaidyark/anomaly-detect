"""Application layout."""

from __future__ import annotations

from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

from dashboard.components import right_panel, sidebar_controls, stat_card


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
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Security Operations Center", className="title-mark"),
                                html.H2("Graph-Based Network Anomaly Detection", className="mb-1"),
                                html.Div(
                                    "Interactive graph analytics for detecting suspicious hosts, bridges, and unusual communication patterns.",
                                    className="text-secondary",
                                ),
                            ]
                        ),
                        className="top-banner mb-3",
                    )
                )
            ),
            dbc.Row(
                [
                    dbc.Col(stat_card("Nodes", "stat-nodes", "bi-diagram-3"), md=2),
                    dbc.Col(stat_card("Edges", "stat-edges", "bi-link-45deg"), md=2),
                    dbc.Col(stat_card("Average Degree", "stat-avg-degree", "bi-graph-up"), md=2),
                    dbc.Col(stat_card("Detected Anomalies", "stat-anomalies", "bi-shield-exclamation"), md=3),
                    dbc.Col(stat_card("Density", "stat-density", "bi-braces"), md=3),
                ],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(sidebar_controls(), lg=3, className="mb-3"),
                    dbc.Col(
                        [
                            dbc.Card(
                                dbc.CardBody(
                                    dcc.Loading(
                                        cyto.Cytoscape(
                                            id="network-graph",
                                            className="cy-container",
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
                                            minZoom=0.35,
                                            maxZoom=3.5,
                                            zoom=1,
                                            pan={"x": 0, "y": 0},
                                        ),
                                        type="circle",
                                    )
                                ),
                                className="glass-card mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(dcc.Graph(id="degree-distribution", config={"displayModeBar": False})),
                                            className="glass-card mb-3",
                                        ),
                                        md=6,
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(dcc.Graph(id="centrality-distribution", config={"displayModeBar": False})),
                                            className="glass-card mb-3",
                                        ),
                                        md=6,
                                    ),
                                ],
                                className="g-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(dcc.Graph(id="anomaly-histogram", config={"displayModeBar": False})),
                                            className="glass-card mb-3",
                                        ),
                                        md=4,
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(dcc.Graph(id="top-degree-chart", config={"displayModeBar": False})),
                                            className="glass-card mb-3",
                                        ),
                                        md=4,
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(dcc.Graph(id="protocol-distribution", config={"displayModeBar": False})),
                                            className="glass-card mb-3",
                                        ),
                                        md=4,
                                    ),
                                ],
                                className="g-3",
                            ),
                        ],
                        lg=6,
                    ),
                    dbc.Col(right_panel(), lg=3, className="mb-3"),
                ],
                className="g-3",
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Anomalous Nodes", className="section-header"),
                                dash_table.DataTable(
                                    id="anomaly-table",
                                    page_size=10,
                                    sort_action="native",
                                    filter_action="native",
                                    row_selectable="single",
                                    style_table={"overflowX": "auto"},
                                    style_header={
                                        "backgroundColor": "#102238",
                                        "color": "#e5eef9",
                                        "fontWeight": "600",
                                        "border": "1px solid #20344f",
                                    },
                                    style_cell={
                                        "backgroundColor": "#0d1b2a",
                                        "color": "#e5eef9",
                                        "border": "1px solid #20344f",
                                        "padding": "10px",
                                        "fontFamily": "Inter, sans-serif",
                                        "whiteSpace": "normal",
                                        "height": "auto",
                                    },
                                    style_data_conditional=[
                                        {
                                            "if": {"row_index": "odd"},
                                            "backgroundColor": "#102238",
                                        }
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
