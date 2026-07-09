"""Graph metrics and derived network statistics."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GraphStatistics:
    """Summary statistics for the full graph."""

    nodes: int
    edges: int
    average_degree: float
    density: float
    connected_components: int


def _component_map(graph: nx.Graph) -> dict[str, int]:
    if graph.is_directed():
        components = list(nx.weakly_connected_components(graph))
    else:
        components = list(nx.connected_components(graph))
    mapping: dict[str, int] = {}
    for index, component in enumerate(components, start=1):
        for node in component:
            mapping[str(node)] = index
    return mapping


def _community_map(graph: nx.Graph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    undirected = graph.to_undirected() if graph.is_directed() else graph
    try:
        communities = nx.community.louvain_communities(undirected, seed=42)
    except Exception:
        communities = [{node} for node in undirected.nodes]
    mapping: dict[str, int] = {}
    for index, community in enumerate(communities):
        for node in community:
            mapping[str(node)] = index
    return mapping


def _safe_eigenvector_centrality(graph: nx.Graph) -> dict[str, float]:
    try:
        if graph.number_of_nodes() == 0:
            return {}
        if graph.is_directed():
            return nx.eigenvector_centrality_numpy(graph.reverse(copy=True))
        return nx.eigenvector_centrality_numpy(graph)
    except Exception:
        return {str(node): 0.0 for node in graph.nodes}


def compute_graph_statistics(graph: nx.Graph) -> GraphStatistics:
    """Compute graph-level statistics."""
    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()
    average_degree = float(sum(dict(graph.degree()).values()) / nodes) if nodes else 0.0
    density = float(nx.density(graph)) if nodes > 1 else 0.0
    if graph.is_directed():
        components = nx.number_weakly_connected_components(graph)
    else:
        components = nx.number_connected_components(graph)
    return GraphStatistics(
        nodes=nodes,
        edges=edges,
        average_degree=average_degree,
        density=density,
        connected_components=components,
    )


def compute_node_metrics(graph: nx.Graph, edge_frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute node-level metrics and derived anomaly features."""
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(
            columns=[
                "node",
                "degree",
                "degree_centrality",
                "betweenness_centrality",
                "closeness_centrality",
                "eigenvector_centrality",
                "pagerank",
                "clustering_coefficient",
                "component_id",
                "component_size",
                "unique_neighbours",
                "new_neighbour_ratio",
                "is_bridge",
                "community_id",
            ]
        )

    degree = dict(graph.degree())
    degree_centrality = nx.degree_centrality(graph)
    if graph.number_of_nodes() > 1:
        betweenness = nx.betweenness_centrality(graph, normalized=True)
        closeness = nx.closeness_centrality(graph)
        pagerank = nx.pagerank(graph)
    else:
        betweenness = {node: 0.0 for node in graph.nodes}
        closeness = {node: 0.0 for node in graph.nodes}
        pagerank = {node: 1.0 for node in graph.nodes}

    if graph.is_directed():
        clustering = nx.clustering(graph.to_undirected())
    else:
        clustering = nx.clustering(graph)
    eigenvector = _safe_eigenvector_centrality(graph)
    component_map = _component_map(graph)
    component_sizes = Counter(component_map.values())
    community_map = _community_map(graph)
    bridge_nodes: set[str] = set()
    if not graph.is_directed():
        bridge_nodes = {str(node) for edge in nx.bridges(graph) for node in edge}

    unique_neighbour_counts: dict[str, int] = {}
    new_neighbour_ratio: dict[str, float] = {}
    if edge_frame is not None and not edge_frame.empty:
        ordered = edge_frame.sort_values("timestamp")
        split_index = max(1, int(len(ordered) * 0.75))
        early_edges = ordered.iloc[:split_index]
        late_edges = ordered.iloc[split_index:]
        early_neighbours: dict[str, set[str]] = defaultdict(set)
        late_neighbours: dict[str, set[str]] = defaultdict(set)
        for row in early_edges.itertuples(index=False):
            early_neighbours[str(row.source)].add(str(row.destination))
            early_neighbours[str(row.destination)].add(str(row.source))
        for row in late_edges.itertuples(index=False):
            late_neighbours[str(row.source)].add(str(row.destination))
            late_neighbours[str(row.destination)].add(str(row.source))
        for node in graph.nodes:
            node_name = str(node)
            early = early_neighbours.get(node_name, set())
            late = late_neighbours.get(node_name, set())
            total = len(early | late)
            unique_neighbour_counts[node_name] = total
            new_neighbour_ratio[node_name] = float(len(late - early) / total) if total else 0.0
    else:
        for node in graph.nodes:
            neighbours = set(graph.neighbors(node))
            unique_neighbour_counts[str(node)] = len(neighbours)
            new_neighbour_ratio[str(node)] = 0.0

    records: list[dict[str, Any]] = []
    for node in graph.nodes:
        node_name = str(node)
        records.append(
            {
                "node": node_name,
                "degree": int(degree.get(node, 0)),
                "degree_centrality": float(degree_centrality.get(node, 0.0)),
                "betweenness_centrality": float(betweenness.get(node, 0.0)),
                "closeness_centrality": float(closeness.get(node, 0.0)),
                "eigenvector_centrality": float(eigenvector.get(node, 0.0)),
                "pagerank": float(pagerank.get(node, 0.0)),
                "clustering_coefficient": float(clustering.get(node, 0.0)),
                "component_id": int(component_map.get(node_name, 0)),
                "component_size": int(component_sizes.get(component_map.get(node_name, 0), 0)),
                "unique_neighbours": int(unique_neighbour_counts.get(node_name, 0)),
                "new_neighbour_ratio": float(new_neighbour_ratio.get(node_name, 0.0)),
                "is_bridge": int(node_name in bridge_nodes),
                "community_id": int(community_map.get(node_name, 0)),
            }
        )

    frame = pd.DataFrame.from_records(records).sort_values(
        by=["degree", "betweenness_centrality", "pagerank"], ascending=False
    )
    frame["degree_rank"] = frame["degree"].rank(method="dense", ascending=False).astype(int)
    return frame.reset_index(drop=True)

