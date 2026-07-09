"""Graph and chart visualisation helpers."""

from __future__ import annotations

from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Iterable

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


COMMUNITY_PALETTE = (
    "#3da9fc", "#00d4a6", "#ffd166", "#ff5c7a", "#c792ea",
    "#f78c6c", "#82aaff", "#c3e88d", "#f07178", "#89ddff",
)


def _node_score_lookup(anomalies: pd.DataFrame | None) -> dict[str, float]:
    if anomalies is None or anomalies.empty:
        return {}
    return {str(row.node): float(row.anomaly_score) for row in anomalies.itertuples(index=False)}


def _node_color(score: float, selected: bool = False) -> str:
    if selected:
        return "#7dd3fc"
    if score >= 0.75:
        return "#ff5c7a"
    if score >= 0.45:
        return "#ffd166"
    return "#3da9fc"


def create_cytoscape_elements(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
    highlighted_nodes: Iterable[str] | None = None,
) -> list[dict]:
    """Create Dash Cytoscape elements from graph state."""
    score_lookup = _node_score_lookup(anomalies)
    metrics_lookup = metrics.set_index("node").to_dict(orient="index") if not metrics.empty else {}
    highlighted = {str(node) for node in (highlighted_nodes or [])}
    elements: list[dict] = []

    for node in graph.nodes:
        node_name = str(node)
        metric_row = metrics_lookup.get(node_name, {})
        score = float(score_lookup.get(node_name, 0.0))
        community_id = int(metric_row.get("community_id", 0))
        classes: list[str] = []
        if score >= 0.75:
            classes.append("anomaly")
        elif score >= 0.45:
            classes.append("warning")
        else:
            classes.append("normal")
        classes.append(f"community-{community_id % len(COMMUNITY_PALETTE)}")
        if node_name in highlighted:
            classes.append("selected")
        elements.append(
            {
                "data": {
                    "id": node_name,
                    "label": node_name,
                    "degree": int(metric_row.get("degree", graph.degree(node))),
                    "centrality": round(float(metric_row.get("degree_centrality", 0.0)), 4),
                    "pagerank": round(float(metric_row.get("pagerank", 0.0)), 4),
                    "score": round(score, 4),
                    "component": int(metric_row.get("component_id", 0)),
                    "community": community_id,
                    "reason": str(metric_row.get("reason_flagged", "")),
                },
                "classes": " ".join(classes),
            }
        )

    for source, destination, attrs in graph.edges(data=True):
        elements.append(
            {
                "data": {
                    "source": str(source),
                    "target": str(destination),
                    "weight": int(attrs.get("weight", 1)),
                }
            }
        )
    return elements


def create_cytoscape_stylesheet(color_mode: str = "anomaly") -> list[dict]:
    """Create the Cytoscape stylesheet for the graph canvas.

    ``color_mode`` is either ``"anomaly"`` (color by anomaly severity) or
    ``"community"`` (color by detected community membership).
    """
    stylesheet: list[dict] = [
        {
            "selector": "node",
            "style": {
                "background-color": "#3da9fc",
                "label": "data(label)",
                "color": "#e5eef9",
                "font-size": "11px",
                "text-outline-width": 2,
                "text-outline-color": "#07111f",
                "width": "mapData(degree, 0, 20, 18, 64)",
                "height": "mapData(degree, 0, 20, 18, 64)",
                "border-width": 1.5,
                "border-color": "#9cccf5",
            },
        },
    ]

    if color_mode == "community":
        for index, color in enumerate(COMMUNITY_PALETTE):
            stylesheet.append(
                {
                    "selector": f"node.community-{index}",
                    "style": {"background-color": color, "border-color": color},
                }
            )
    else:
        stylesheet.append(
            {
                "selector": "node.warning",
                "style": {"background-color": "#ffd166", "border-color": "#f4b942"},
            }
        )
        stylesheet.append(
            {
                "selector": "node.anomaly",
                "style": {"background-color": "#ff5c7a", "border-color": "#ff91a4"},
            }
        )

    stylesheet.append(
        {
            "selector": "node.selected",
            "style": {
                "border-width": 4,
                "border-color": "#7dd3fc",
                "shadow-blur": 10,
                "shadow-color": "#7dd3fc",
                "shadow-opacity": 0.5,
            },
        }
    )
    stylesheet.append(
        {
            "selector": "edge",
            "style": {
                "width": "mapData(weight, 1, 6, 1, 6)",
                "line-color": "rgba(120, 145, 180, 0.38)",
                "target-arrow-color": "rgba(120, 145, 180, 0.38)",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "opacity": 0.8,
            },
        }
    )
    return stylesheet


def create_network_figure(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
    highlighted_nodes: Iterable[str] | None = None,
) -> go.Figure:
    """Create a Plotly network figure for export."""
    highlighted = {str(node) for node in (highlighted_nodes or [])}
    score_lookup = _node_score_lookup(anomalies)
    pos = nx.spring_layout(graph, seed=42, k=None)

    edge_x: list[float] = []
    edge_y: list[float] = []
    for source, destination in graph.edges():
        x0, y0 = pos[source]
        x1, y1 = pos[destination]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    node_x: list[float] = []
    node_y: list[float] = []
    node_text: list[str] = []
    node_color: list[str] = []
    node_size: list[float] = []
    metrics_lookup = metrics.set_index("node").to_dict(orient="index") if not metrics.empty else {}

    for node in graph.nodes:
        node_name = str(node)
        x, y = pos[node]
        metric_row = metrics_lookup.get(node_name, {})
        score = float(score_lookup.get(node_name, 0.0))
        degree = int(metric_row.get("degree", graph.degree(node)))
        node_x.append(x)
        node_y.append(y)
        node_text.append(
            f"{node_name}<br>Degree: {degree}<br>Score: {score:.3f}<br>Pagerank: {float(metric_row.get('pagerank', 0.0)):.3f}"
        )
        node_color.append(_node_color(score, selected=node_name in highlighted))
        node_size.append(16 + degree * 3)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color="rgba(120, 145, 180, 0.28)"),
            hoverinfo="none",
            name="Connections",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=[str(node) for node in graph.nodes],
            textposition="top center",
            hovertext=node_text,
            hoverinfo="text",
            marker=dict(color=node_color, size=node_size, line=dict(width=1.2, color="#e5eef9")),
            name="Devices",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def create_degree_distribution(metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=metrics["degree"], nbinsx=12, marker_color="#3da9fc", opacity=0.85))
    fig.update_layout(template="plotly_dark", title="Degree Distribution", margin=dict(l=25, r=15, t=45, b=25))
    return fig


def create_centrality_distribution(metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for column, color in [
        ("betweenness_centrality", "#ff5c7a"),
        ("pagerank", "#ffd166"),
        ("degree_centrality", "#3da9fc"),
    ]:
        fig.add_trace(go.Histogram(x=metrics[column], name=column.replace("_", " ").title(), opacity=0.65, marker_color=color))
    fig.update_layout(template="plotly_dark", barmode="overlay", title="Centrality Distribution", margin=dict(l=25, r=15, t=45, b=25))
    return fig


def create_anomaly_histogram(anomalies: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=anomalies["anomaly_score"], nbinsx=14, marker_color="#ff5c7a", opacity=0.88))
    fig.update_layout(template="plotly_dark", title="Anomaly Score Histogram", margin=dict(l=25, r=15, t=45, b=25))
    return fig


def create_top_degree_chart(metrics: pd.DataFrame, limit: int = 20) -> go.Figure:
    top = metrics.nlargest(limit, "degree").sort_values("degree", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=top["degree"],
            y=top["node"],
            orientation="h",
            marker_color="#00d4a6",
        )
    )
    fig.update_layout(template="plotly_dark", title="Top 20 Highest Degree Nodes", margin=dict(l=25, r=15, t=45, b=25))
    return fig


def create_protocol_distribution(edge_frame: pd.DataFrame) -> go.Figure:
    counts = Counter(edge_frame["protocol"].astype(str))
    fig = go.Figure(go.Pie(labels=list(counts.keys()), values=list(counts.values()), hole=0.42))
    fig.update_layout(template="plotly_dark", title="Protocol Distribution", margin=dict(l=25, r=15, t=45, b=25))
    return fig


def export_network_png(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
    highlighted_nodes: Iterable[str] | None = None,
) -> bytes:
    """Export the current network visual state as PNG bytes."""
    figure = create_network_figure(graph, metrics, anomalies, highlighted_nodes)
    return figure.to_image(format="png", engine="kaleido")
