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


NODE_NORMAL = "#3b82f6"
NODE_WARNING = "#fbbf24"
NODE_ANOMALY = "#f43f5e"

COMMUNITY_PALETTE = (
    "#3b82f6", "#2dd4bf", "#fbbf24", "#f43f5e", "#c792ea",
    "#f78c6c", "#82aaff", "#c3e88d", "#f07178", "#89ddff",
)


def _node_score_lookup(anomalies: pd.DataFrame | None) -> dict[str, float]:
    if anomalies is None or anomalies.empty:
        return {}
    return {str(row.node): float(row.anomaly_score) for row in anomalies.itertuples(index=False)}


def _node_label_lookup(anomalies: pd.DataFrame | None) -> dict[str, int]:
    if anomalies is None or anomalies.empty or "anomaly_label" not in anomalies.columns:
        return {}
    return {str(row.node): int(row.anomaly_label) for row in anomalies.itertuples(index=False)}


def _severity_class(score: float, label: int, threshold: float) -> str:
    """Severity follows the detection result: flagged nodes are anomalies,
    unflagged nodes close to the threshold are warnings."""
    if label == 1:
        return "anomaly"
    if score >= threshold * 0.7:
        return "warning"
    return "normal"


def _node_color(score: float, label: int, threshold: float, selected: bool = False) -> str:
    if selected:
        return "#7dd3fc"
    severity = _severity_class(score, label, threshold)
    if severity == "anomaly":
        return NODE_ANOMALY
    if severity == "warning":
        return NODE_WARNING
    return NODE_NORMAL


def _edge_key(source: str, destination: str) -> tuple[str, str]:
    return tuple(sorted((str(source), str(destination))))


def _new_edge_keys(edge_frame: pd.DataFrame | None) -> set[tuple[str, str]]:
    """Edges whose first communication happens in the last quarter of the window.

    Brand-new connections between devices that never talked before are a
    classic sign of scanning or lateral movement, so they get their own visual
    treatment on the graph.
    """
    if edge_frame is None or edge_frame.empty or "timestamp" not in edge_frame.columns:
        return set()
    frame = edge_frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp"])
    if frame.empty:
        return set()
    start = frame["timestamp"].min()
    span = frame["timestamp"].max() - start
    if span.total_seconds() <= 0:
        return set()
    cutoff = start + span * 0.75
    first_seen: dict[tuple[str, str], pd.Timestamp] = {}
    for row in frame.itertuples(index=False):
        key = _edge_key(row.source, row.destination)
        if key not in first_seen or row.timestamp < first_seen[key]:
            first_seen[key] = row.timestamp
    return {key for key, seen in first_seen.items() if seen > cutoff}


def create_cytoscape_elements(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
    highlighted_nodes: Iterable[str] | None = None,
    edge_frame: pd.DataFrame | None = None,
    threshold: float = 0.65,
) -> list[dict]:
    """Create Dash Cytoscape elements from graph state."""
    score_lookup = _node_score_lookup(anomalies)
    label_lookup = _node_label_lookup(anomalies)
    metrics_lookup = metrics.set_index("node").to_dict(orient="index") if not metrics.empty else {}
    highlighted = {str(node) for node in (highlighted_nodes or [])}
    elements: list[dict] = []

    for node in graph.nodes:
        node_name = str(node)
        metric_row = metrics_lookup.get(node_name, {})
        score = float(score_lookup.get(node_name, 0.0))
        label = int(label_lookup.get(node_name, 0))
        community_id = int(metric_row.get("community_id", 0))
        classes: list[str] = [_severity_class(score, label, threshold)]
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

    undirected = graph.to_undirected() if graph.is_directed() else graph
    bridge_keys = {_edge_key(*edge) for edge in nx.bridges(undirected)}
    new_keys = _new_edge_keys(edge_frame)
    for source, destination, attrs in graph.edges(data=True):
        key = _edge_key(source, destination)
        edge_classes: list[str] = []
        if key in new_keys:
            edge_classes.append("new-edge")
        if key in bridge_keys:
            edge_classes.append("bridge-edge")
        elements.append(
            {
                "data": {
                    "source": str(source),
                    "target": str(destination),
                    "weight": int(attrs.get("weight", 1)),
                },
                "classes": " ".join(edge_classes),
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
                "background-color": NODE_NORMAL,
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
                "style": {"background-color": NODE_WARNING, "border-color": NODE_WARNING},
            }
        )
        stylesheet.append(
            {
                "selector": "node.anomaly",
                "style": {"background-color": NODE_ANOMALY, "border-color": NODE_ANOMALY},
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
    stylesheet.append(
        {
            "selector": "edge.new-edge",
            "style": {
                "line-style": "dotted",
                "line-color": "rgba(45, 212, 191, 0.85)",
                "target-arrow-color": "rgba(45, 212, 191, 0.85)",
                "opacity": 0.95,
            },
        }
    )
    stylesheet.append(
        {
            "selector": "edge.bridge-edge",
            "style": {
                "line-style": "dashed",
                "line-color": "rgba(251, 191, 36, 0.85)",
                "target-arrow-color": "rgba(251, 191, 36, 0.85)",
                "opacity": 0.95,
            },
        }
    )
    return stylesheet


def create_network_figure(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
    highlighted_nodes: Iterable[str] | None = None,
    threshold: float = 0.65,
) -> go.Figure:
    """Create a Plotly network figure for export."""
    highlighted = {str(node) for node in (highlighted_nodes or [])}
    score_lookup = _node_score_lookup(anomalies)
    label_lookup = _node_label_lookup(anomalies)
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
        node_color.append(
            _node_color(score, int(label_lookup.get(node_name, 0)), threshold, selected=node_name in highlighted)
        )
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


CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color="#56718c", size=10),
    title_font=dict(family="IBM Plex Sans, sans-serif", color="#dfe8f2", size=14),
    margin=dict(l=35, r=15, t=40, b=30),
    xaxis=dict(gridcolor="#1c2a3a", zerolinecolor="#1c2a3a"),
    yaxis=dict(gridcolor="#1c2a3a", zerolinecolor="#1c2a3a"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9.5, color="#8296ac")),
)


def create_degree_distribution(metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=metrics["degree"], nbinsx=12, marker_color=NODE_NORMAL, opacity=0.9))
    fig.update_layout(title="Degree Distribution", **CHART_LAYOUT)
    return fig


def create_centrality_distribution(metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for column, color in [
        ("betweenness_centrality", "#f472a0"),
        ("pagerank", "#d4b96a"),
        ("degree_centrality", NODE_NORMAL),
    ]:
        fig.add_trace(go.Histogram(x=metrics[column], name=column.replace("_", " ").title(), opacity=0.75, marker_color=color))
    fig.update_layout(title="Centrality Distribution", barmode="overlay", **CHART_LAYOUT)
    return fig


def create_anomaly_histogram(anomalies: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=anomalies["anomaly_score"], nbinsx=14, marker_color=NODE_ANOMALY, opacity=0.85))
    fig.update_layout(title="Anomaly Score Histogram", **CHART_LAYOUT)
    return fig


def create_top_degree_chart(metrics: pd.DataFrame, limit: int = 20) -> go.Figure:
    top = metrics.nlargest(limit, "degree").sort_values("degree", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=top["degree"],
            y=top["node"],
            orientation="h",
            marker_color="#2dd4bf",
        )
    )
    fig.update_layout(title="Top 20 Highest Degree Nodes", **CHART_LAYOUT)
    return fig


def create_protocol_distribution(edge_frame: pd.DataFrame) -> go.Figure:
    counts = Counter(edge_frame["protocol"].astype(str))
    palette = {"TCP": "#6366f1", "UDP": "#f97316", "ICMP": "#34d399"}
    colors = [palette.get(label, "#82aaff") for label in counts]
    fig = go.Figure(
        go.Pie(
            labels=list(counts.keys()),
            values=list(counts.values()),
            hole=0.55,
            marker=dict(colors=colors),
            textinfo="none",
        )
    )
    fig.update_layout(title="Protocol Distribution", **CHART_LAYOUT)
    return fig


def create_evaluation_chart(evaluation: pd.DataFrame) -> go.Figure:
    """Grouped bars of precision / recall / F1 per detection algorithm."""
    fig = go.Figure()
    if not evaluation.empty:
        for column, color in [
            ("precision", NODE_NORMAL),
            ("recall", "#2dd4bf"),
            ("f1", "#d4b96a"),
        ]:
            fig.add_trace(
                go.Bar(
                    x=evaluation["algorithm"],
                    y=evaluation[column],
                    name=column.title() if column != "f1" else "F1",
                    marker_color=color,
                )
            )
    layout = {**CHART_LAYOUT, "yaxis": dict(gridcolor="#1c2a3a", zerolinecolor="#1c2a3a", range=[0, 1.05])}
    fig.update_layout(title="Detector Performance vs Ground Truth", barmode="group", **layout)
    return fig


def export_network_png(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
    highlighted_nodes: Iterable[str] | None = None,
    threshold: float = 0.65,
) -> bytes:
    """Export the current network visual state as PNG bytes."""
    figure = create_network_figure(graph, metrics, anomalies, highlighted_nodes, threshold=threshold)
    return figure.to_image(format="png", engine="kaleido")
