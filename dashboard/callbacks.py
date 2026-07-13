"""Dash callbacks for the anomaly dashboard."""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from io import StringIO
from pathlib import Path

import pandas as pd
from dash import Input, Output, State, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate

from src.anomaly_detection import detect_anomalies
from src.evaluation import compare_algorithms
from src.graph_builder import build_graph
from src.loader import load_network_data
from src.metrics import compute_graph_statistics, compute_node_metrics
from src.scenarios import generate_scenario, list_scenarios
from src.utils import dataframe_to_json
from src.visualization import (
    NODE_ANOMALY,
    create_anomaly_histogram,
    create_centrality_distribution,
    create_cytoscape_elements,
    create_cytoscape_stylesheet,
    create_degree_distribution,
    create_evaluation_chart,
    create_protocol_distribution,
    create_top_degree_chart,
    export_network_png,
)


MAX_UPLOAD_NODES = 750


def _default_dataset_path() -> Path:
    return Path("data/sample_network.csv")


def _read_json_frame(payload: str | None) -> pd.DataFrame:
    """Read a dataframe stored as a JSON string in Dash state."""
    if not payload:
        return pd.DataFrame()
    return pd.read_json(StringIO(payload), orient="records")


def _apply_time_window(frame: pd.DataFrame, time_range: list[float] | None) -> pd.DataFrame:
    """Keep only traffic inside the selected percentage window of the capture."""
    if not time_range:
        return frame
    start_pct, end_pct = time_range
    if start_pct <= 0 and end_pct >= 100:
        return frame
    start_time = frame["timestamp"].min()
    span = frame["timestamp"].max() - start_time
    lower = start_time + span * (start_pct / 100)
    upper = start_time + span * (end_pct / 100)
    filtered = frame[(frame["timestamp"] >= lower) & (frame["timestamp"] <= upper)]
    if filtered.empty:
        raise ValueError("No traffic falls inside the selected time window.")
    return filtered.reset_index(drop=True)


def _build_payload(
    source: str | Path | pd.DataFrame,
    directed: bool,
    time_range: list[float] | None = None,
) -> dict:
    network = load_network_data(source)
    network = _apply_time_window(network, time_range)
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


def _load_default_payload(directed: bool, time_range: list[float] | None = None) -> dict | None:
    path = _default_dataset_path()
    if not path.exists():
        return None
    return _build_payload(path, directed, time_range)


def _upload_payload(
    contents: str | None,
    filename: str | None,
    directed: bool,
    time_range: list[float] | None,
) -> dict:
    if not contents or not filename or not filename.lower().endswith(".csv"):
        raise ValueError("Please upload a .csv file with source, destination, timestamp, protocol columns.")
    content_type, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)
    frame = pd.read_csv(BytesIO(decoded))
    payload = _build_payload(frame, directed=directed, time_range=time_range)
    if payload["statistics"]["nodes"] > MAX_UPLOAD_NODES:
        raise ValueError(
            f"'{filename}' has {payload['statistics']['nodes']} devices, "
            f"which exceeds the {MAX_UPLOAD_NODES}-node limit for interactive "
            "rendering. Use a smaller dataset."
        )
    return payload


def register_callbacks(app) -> None:
    """Register all dashboard callbacks."""

    app.clientside_callback(
        """
        function(n_clicks, current_class) {
            if (!n_clicks) { return window.dash_clientside.no_update; }
            const base = (current_class || "").replace("sidebar-collapsed", "").trim();
            const isCollapsed = (current_class || "").indexOf("sidebar-collapsed") !== -1;
            return isCollapsed ? base : (base + " sidebar-collapsed").trim();
        }
        """,
        Output("workspace-grid", "className"),
        Input("sidebar-collapse-btn", "n_clicks"),
        State("workspace-grid", "className"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        """
        function(n_clicks, current_class) {
            if (!n_clicks) { return window.dash_clientside.no_update; }
            const base = (current_class || "").replace("graph-card--fullscreen", "").trim();
            const isFullscreen = (current_class || "").indexOf("graph-card--fullscreen") !== -1;
            setTimeout(function() { window.dispatchEvent(new Event("resize")); }, 200);
            return isFullscreen ? base : (base + " graph-card--fullscreen").trim();
        }
        """,
        Output("graph-card", "className"),
        Input("graph-fullscreen-btn", "n_clicks"),
        State("graph-card", "className"),
        prevent_initial_call=True,
    )

    @app.callback(
        Output("scenario-select", "value"),
        Input("upload-data", "contents"),
        State("scenario-select", "value"),
        prevent_initial_call=True,
    )
    def reset_scenario_on_upload(contents, scenario):
        """Uploading a CSV takes over from any active demo scenario."""
        if not contents or scenario == "none":
            raise PreventUpdate
        return "none"

    @app.callback(
        Output("scenario-description", "children"),
        Input("scenario-select", "value"),
    )
    def show_scenario_description(scenario):
        for entry in list_scenarios():
            if entry["key"] == scenario:
                return entry["description"]
        return ""

    @app.callback(
        Output("network-store", "data"),
        Output("metrics-store", "data"),
        Output("ground-truth-store", "data"),
        Output("stat-nodes", "children"),
        Output("stat-edges", "children"),
        Output("stat-avg-degree", "children"),
        Output("stat-density", "children"),
        Output("upload-error", "children"),
        Output("upload-error", "is_open"),
        Input("run-detection", "n_clicks"),
        Input("upload-data", "contents"),
        Input("directed-toggle", "value"),
        Input("scenario-select", "value"),
        Input("time-range-slider", "value"),
        State("upload-data", "filename"),
        State("algorithm-select", "value"),
        State("threshold-slider", "value"),
        prevent_initial_call=False,
    )
    def load_or_run(n_clicks, contents, directed, scenario, time_range, filename, algorithm, threshold):
        triggered = callback_context.triggered_id
        directed = bool(directed)
        scenario_active = bool(scenario) and scenario != "none"
        ground_truth: list[str] = []
        try:
            if triggered == "upload-data":
                if scenario_active:
                    # reset_scenario_on_upload will flip the dropdown to "none",
                    # which re-triggers this callback on the upload path.
                    raise PreventUpdate
                payload = _upload_payload(contents, filename, directed, time_range)
            elif scenario_active:
                result = generate_scenario(scenario)
                payload = _build_payload(result.frame, directed=directed, time_range=time_range)
                ground_truth = list(result.true_anomalies)
            elif contents and filename and filename.lower().endswith(".csv"):
                payload = _upload_payload(contents, filename, directed, time_range)
            else:
                payload = _load_default_payload(directed, time_range)
        except (ValueError, pd.errors.ParserError) as exc:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                f"Could not load data: {exc}",
                True,
            )

        if payload is None:
            raise PreventUpdate

        stats = payload["statistics"]
        return (
            payload,
            payload["metrics"],
            ground_truth,
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
        Output("last-scan-label", "children"),
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
        last_scan = f"LAST SCAN {datetime.now():%H:%M:%S}"
        return (
            detection.to_json(orient="records", date_format="iso"),
            str(int(detection["anomaly_label"].sum())),
            last_scan,
        )

    @app.callback(
        Output("network-graph", "layout"),
        Input("network-store", "data"),
        Input("layout-select", "value"),
        Input("fit-view-btn", "n_clicks"),
    )
    def refresh_layout(network_payload, layout_name, fit_clicks):
        if not network_payload:
            raise PreventUpdate
        return {
            "name": layout_name,
            "animate": True,
            "fit": True,
            "padding": 40,
            "randomize": False,
            "seed": 42,
            # Unknown keys are ignored by Cytoscape but make the dict differ
            # per click, so pressing FIT re-runs the layout and re-fits.
            "fitCount": int(fit_clicks or 0),
        }

    @app.callback(
        Output("network-graph", "elements"),
        Output("network-graph", "stylesheet"),
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
        Input("selected-node-store", "data"),
        Input("color-mode-select", "value"),
        State("threshold-slider", "value"),
    )
    def refresh_visuals(network_payload, metrics_json, anomalies_json, selected_node, color_mode, threshold):
        if not network_payload or not metrics_json or not anomalies_json:
            raise PreventUpdate

        edges = _read_json_frame(network_payload["edges"])
        metrics = _read_json_frame(metrics_json)
        anomalies = _read_json_frame(anomalies_json)
        build_result = build_graph(edges, directed=bool(network_payload.get("directed", False)))
        highlighted = anomalies.query("anomaly_label == 1")["node"].tolist()
        if selected_node:
            highlighted.append(str(selected_node))
        elements = create_cytoscape_elements(
            build_result.graph,
            metrics,
            anomalies,
            highlighted_nodes=highlighted,
            edge_frame=edges,
            threshold=float(threshold) if threshold is not None else 0.65,
        )
        stylesheet = create_cytoscape_stylesheet(
            color_mode=color_mode or "anomaly",
            compact=len(metrics) > 150,
            max_degree=int(metrics["degree"].max()) if not metrics.empty else 20,
        )
        degree_fig = create_degree_distribution(metrics)
        centrality_fig = create_centrality_distribution(metrics)
        anomaly_subset = anomalies.query("anomaly_label == 1") if not anomalies.empty else anomalies
        anomaly_fig = create_anomaly_histogram(anomaly_subset)
        top_fig = create_top_degree_chart(metrics)
        proto_fig = create_protocol_distribution(edges)
        table_frame = anomaly_subset.copy()
        if not table_frame.empty:
            table_frame["node"] = table_frame["node"].map(
                lambda name: (
                    '<span style="display:inline-flex;align-items:center;gap:8px;'
                    f'color:{NODE_ANOMALY};font-weight:600;">'
                    f'<span style="width:8px;height:8px;border-radius:50%;'
                    f'background:{NODE_ANOMALY};display:inline-block;"></span>{name}</span>'
                )
            )
            table_frame["is_bridge"] = table_frame["is_bridge"].map(lambda value: "Yes" if value else "No")
        columns = [
            {"name": column.replace("_", " ").title(), "id": column}
            | ({"presentation": "markdown"} if column == "node" else {})
            for column in table_frame.columns
        ]
        return (
            elements,
            stylesheet,
            degree_fig,
            centrality_fig,
            anomaly_fig,
            top_fig,
            proto_fig,
            table_frame.to_dict("records"),
            columns,
        )

    @app.callback(
        Output("evaluation-section", "style"),
        Output("evaluation-summary", "children"),
        Output("evaluation-table", "data"),
        Output("evaluation-table", "columns"),
        Output("evaluation-chart", "figure"),
        Input("metrics-store", "data"),
        Input("ground-truth-store", "data"),
        Input("threshold-slider", "value"),
    )
    def update_evaluation(metrics_json, ground_truth, threshold):
        if not ground_truth or not metrics_json:
            return {"display": "none"}, "", [], [], no_update

        metrics = _read_json_frame(metrics_json)
        evaluation = compare_algorithms(metrics, ground_truth, threshold=threshold)
        figure = create_evaluation_chart(evaluation)
        display = evaluation.copy()
        for column in ("precision", "recall", "f1"):
            display[column] = display[column].round(3)
        column_names = {
            "algorithm": "Algorithm",
            "flagged": "Flagged",
            "true_positives": "True Positives",
            "false_positives": "False Positives",
            "false_negatives": "Missed",
            "precision": "Precision",
            "recall": "Recall",
            "f1": "F1 Score",
        }
        columns = [{"name": column_names.get(column, column), "id": column} for column in display.columns]
        summary = (
            f"This scenario injected {len(ground_truth)} anomalous device(s) into normal traffic: "
            f"{', '.join(ground_truth)}. Every detector ran on identical features at threshold "
            f"{float(threshold):.2f}, scored against that ground truth."
        )
        return {}, summary, display.to_dict("records"), columns, figure

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
        Input("ground-truth-store", "data"),
    )
    def update_node_panel(selected_node, metrics_json, anomalies_json, network_payload, ground_truth):
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
        if ground_truth:
            is_injected = str(selected_node) in {str(node) for node in ground_truth}
            details.append(
                html.Div(
                    f"Ground Truth: {'Injected anomaly' if is_injected else 'Normal (by construction)'}",
                    style={"color": NODE_ANOMALY, "fontWeight": "600"} if is_injected else None,
                )
            )
        return row["node"], details

    @app.callback(
        Output("download-results", "data"),
        Input("export-results", "n_clicks"),
        State("export-format", "value"),
        State("network-store", "data"),
        State("metrics-store", "data"),
        State("anomalies-store", "data"),
        State("threshold-slider", "value"),
        prevent_initial_call=True,
    )
    def export_results(n_clicks, export_format, network_payload, metrics_json, anomalies_json, threshold):
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
            png_bytes = export_network_png(
                graph,
                metrics,
                anomalies,
                highlighted_nodes=anomalies.query("anomaly_label == 1")["node"].tolist(),
                threshold=float(threshold) if threshold is not None else 0.65,
            )
            return dcc.send_bytes(lambda buffer: buffer.write(png_bytes), "network.png")
        raise PreventUpdate
