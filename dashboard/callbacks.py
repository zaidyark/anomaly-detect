"""Dash callbacks for the anomaly dashboard."""

from __future__ import annotations

import base64
from io import BytesIO
from io import StringIO
from pathlib import Path

import pandas as pd
from dash import Input, Output, State, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate

from src.anomaly_detection import detect_anomalies
from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_graph_statistics, compute_node_metrics
from src.utils import dataframe_to_json
from src.visualization import (
    create_anomaly_histogram,
    create_centrality_distribution,
    create_cytoscape_elements,
    create_cytoscape_stylesheet,
    create_degree_distribution,
    create_protocol_distribution,
    create_top_degree_chart,
    export_network_png,
)


def _default_dataset_path() -> Path:
    return Path("data/sample_network.csv")


def _read_json_frame(payload: str | None) -> pd.DataFrame:
    """Read a dataframe stored as a JSON string in Dash state."""
    if not payload:
        return pd.DataFrame()
    return pd.read_json(StringIO(payload), orient="records")


def _build_payload(source: str | Path | pd.DataFrame, directed: bool) -> dict:
    network = load_network_data(source)
    build_result = build_graph(network, directed=directed)
    metrics = compute_node_metrics(build_result.graph, build_result.edge_frame)
    stats = compute_graph_statistics(build_result.graph)
    return {
        "edges": dataframe_to_json(build_result.edge_frame),
        "metrics": dataframe_to_json(metrics),
        "statistics": {
            "nodes": stats.nodes,
            "edges": stats.edges,
            "average_degree": stats.average_degree,
            "density": stats.density,
            "connected_components": stats.connected_components,
        },
        "directed": directed,
    }


def _load_default_payload(directed: bool) -> dict | None:
    path = _default_dataset_path()
    if not path.exists():
        return None
    return _build_payload(path, directed)


def register_callbacks(app) -> None:
    """Register all dashboard callbacks."""

    @app.callback(
        Output("network-store", "data"),
        Output("metrics-store", "data"),
        Output("stat-nodes", "children"),
        Output("stat-edges", "children"),
        Output("stat-avg-degree", "children"),
        Output("stat-density", "children"),
        Output("upload-error", "children"),
        Output("upload-error", "is_open"),
        Input("run-detection", "n_clicks"),
        Input("upload-data", "contents"),
        Input("directed-toggle", "value"),
        State("upload-data", "filename"),
        State("algorithm-select", "value"),
        State("threshold-slider", "value"),
        prevent_initial_call=False,
    )
    def load_or_run(n_clicks, contents, directed, filename, algorithm, threshold):
        triggered = callback_context.triggered_id
        directed = bool(directed)
        if contents and filename and filename.lower().endswith(".csv"):
            try:
                content_type, content_string = contents.split(",", 1)
                decoded = base64.b64decode(content_string)
                frame = pd.read_csv(BytesIO(decoded))
                payload = _build_payload(frame, directed=directed)
            except (ValueError, pd.errors.ParserError) as exc:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    f"Could not load '{filename}': {exc}",
                    True,
                )
        elif triggered == "upload-data" and contents:
            raise PreventUpdate
        else:
            payload = _load_default_payload(directed)

        if payload is None:
            raise PreventUpdate

        stats = payload["statistics"]
        return (
            payload,
            payload["metrics"],
            f"{stats['nodes']}",
            f"{stats['edges']}",
            f"{stats['average_degree']:.2f}",
            f"{stats['density']:.3f}",
            "",
            False,
        )

    @app.callback(
        Output("anomalies-store", "data"),
        Output("stat-anomalies", "children"),
        Input("run-detection", "n_clicks"),
        Input("metrics-store", "data"),
        Input("algorithm-select", "value"),
        Input("threshold-slider", "value"),
        prevent_initial_call=False,
    )
    def run_detection(n_clicks, metrics_json, algorithm, threshold):
        if not metrics_json:
            raise PreventUpdate

        metrics = _read_json_frame(metrics_json)
        detection = detect_anomalies(metrics, algorithm=algorithm, threshold=threshold).frame
        return detection.to_json(orient="records", date_format="iso"), str(int(detection["anomaly_label"].sum()))

    @app.callback(
        Output("network-graph", "elements"),
        Output("network-graph", "stylesheet"),
        Output("network-graph", "layout"),
        Output("degree-distribution", "figure"),
        Output("centrality-distribution", "figure"),
        Output("anomaly-histogram", "figure"),
        Output("top-degree-chart", "figure"),
        Output("protocol-distribution", "figure"),
        Output("anomaly-table", "data"),
        Output("anomaly-table", "columns"),
        Input("network-store", "data"),
        Input("metrics-store", "data"),
        Input("anomalies-store", "data"),
        Input("layout-select", "value"),
        Input("selected-node-store", "data"),
        Input("color-mode-select", "value"),
    )
    def refresh_visuals(network_payload, metrics_json, anomalies_json, layout_name, selected_node, color_mode):
        if not network_payload or not metrics_json or not anomalies_json:
            raise PreventUpdate

        edges = _read_json_frame(network_payload["edges"])
        metrics = _read_json_frame(metrics_json)
        anomalies = _read_json_frame(anomalies_json)
        build_result = build_graph(edges, directed=bool(network_payload.get("directed", False)))
        highlighted = anomalies.query("anomaly_label == 1")["node"].tolist()
        if selected_node:
            highlighted.append(str(selected_node))
        elements = create_cytoscape_elements(build_result.graph, metrics, anomalies, highlighted_nodes=highlighted)
        stylesheet = create_cytoscape_stylesheet(color_mode=color_mode or "anomaly")
        layout = {"name": layout_name, "animate": True, "fit": True, "padding": 40, "randomize": False}
        degree_fig = create_degree_distribution(metrics)
        centrality_fig = create_centrality_distribution(metrics)
        anomaly_subset = anomalies.query("anomaly_label == 1") if not anomalies.empty else anomalies
        anomaly_fig = create_anomaly_histogram(anomaly_subset)
        top_fig = create_top_degree_chart(metrics)
        proto_fig = create_protocol_distribution(edges)
        table_frame = anomaly_subset.copy()
        columns = [
            {"name": column.replace("_", " ").title(), "id": column}
            for column in table_frame.columns
        ]
        return (
            elements,
            stylesheet,
            layout,
            degree_fig,
            centrality_fig,
            anomaly_fig,
            top_fig,
            proto_fig,
            table_frame.to_dict("records"),
            columns,
        )

    @app.callback(
        Output("selected-node-store", "data"),
        Input("network-graph", "tapNodeData"),
        Input("anomaly-table", "selected_rows"),
        Input("node-search", "value"),
        State("anomaly-table", "data"),
        prevent_initial_call=True,
    )
    def update_selected_node(node_data, selected_rows, search_value, table_data):
        triggered = callback_context.triggered_id
        if triggered == "network-graph" and node_data:
            return node_data["id"]
        if triggered == "anomaly-table" and selected_rows and table_data:
            return table_data[selected_rows[0]]["node"]
        if triggered == "node-search" and search_value:
            return str(search_value).strip()
        raise PreventUpdate

    @app.callback(
        Output("selected-node-name", "children"),
        Output("selected-node-details", "children"),
        Input("selected-node-store", "data"),
        Input("metrics-store", "data"),
        Input("anomalies-store", "data"),
        Input("network-store", "data"),
    )
    def update_node_panel(selected_node, metrics_json, anomalies_json, network_payload):
        if not selected_node or not metrics_json or not anomalies_json:
            return "No node selected", "Click a node or select a table row."

        metrics = _read_json_frame(metrics_json)
        anomalies = _read_json_frame(anomalies_json)
        edges = _read_json_frame(network_payload["edges"]) if network_payload else pd.DataFrame()
        metric_row = metrics.loc[metrics["node"] == selected_node]
        anomaly_row = anomalies.loc[anomalies["node"] == selected_node]
        if metric_row.empty:
            return selected_node, "Node not present in the current graph."

        row = metric_row.iloc[0]
        anomaly = anomaly_row.iloc[0] if not anomaly_row.empty else None
        neighbour_values: set[str] = set()
        if not edges.empty:
            mask = (edges["source"].astype(str) == str(selected_node)) | (edges["destination"].astype(str) == str(selected_node))
            matched = edges.loc[mask, ["source", "destination"]]
            for edge_row in matched.itertuples(index=False):
                if str(edge_row.source) != str(selected_node):
                    neighbour_values.add(str(edge_row.source))
                if str(edge_row.destination) != str(selected_node):
                    neighbour_values.add(str(edge_row.destination))
        neighbours = ", ".join(sorted(neighbour_values)) if neighbour_values else "None"
        details = [
            html.Div(f"Device Name: {row['node']}"),
            html.Div(f"Degree: {int(row['degree'])}"),
            html.Div(f"Degree Centrality: {row['degree_centrality']:.4f}"),
            html.Div(f"Betweenness Centrality: {row['betweenness_centrality']:.4f}"),
            html.Div(f"Eigenvector Centrality: {row['eigenvector_centrality']:.4f}"),
            html.Div(f"PageRank: {row['pagerank']:.4f}"),
            html.Div(f"Community: {int(row['community_id'])}"),
            html.Div(f"Neighbours: {neighbours}"),
            html.Div(f"Anomaly Score: {float(anomaly['anomaly_score']):.4f}" if anomaly is not None else "Anomaly Score: 0.0000"),
            html.Div(f"Reason Flagged: {anomaly['reason_flagged']}" if anomaly is not None else "Reason Flagged: None"),
        ]
        return row["node"], details

    @app.callback(
        Output("download-results", "data"),
        Input("export-results", "n_clicks"),
        State("export-format", "value"),
        State("network-store", "data"),
        State("metrics-store", "data"),
        State("anomalies-store", "data"),
        prevent_initial_call=True,
    )
    def export_results(n_clicks, export_format, network_payload, metrics_json, anomalies_json):
        if not n_clicks or not network_payload:
            raise PreventUpdate

        edges = _read_json_frame(network_payload["edges"])
        metrics = _read_json_frame(metrics_json)
        anomalies = _read_json_frame(anomalies_json)

        if export_format == "csv":
            return dcc.send_data_frame(anomalies.to_csv, "anomalies.csv", index=False)
        if export_format == "json":
            payload = anomalies.to_json(orient="records", indent=2)
            return dcc.send_bytes(lambda buffer: buffer.write(payload.encode("utf-8")), "anomalies.json")
        if export_format == "png":
            graph = build_graph(edges, directed=bool(network_payload.get("directed", False))).graph
            png_bytes = export_network_png(graph, metrics, anomalies, highlighted_nodes=anomalies.query("anomaly_label == 1")["node"].tolist())
            return dcc.send_bytes(lambda buffer: buffer.write(png_bytes), "network.png")
        raise PreventUpdate
