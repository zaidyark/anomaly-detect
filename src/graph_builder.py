"""Graph construction utilities."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd


@dataclass(frozen=True)
class GraphBuildResult:
    """Container for graph construction output."""

    graph: nx.Graph
    edge_frame: pd.DataFrame


def build_graph(
    frame: pd.DataFrame,
    directed: bool = False,
) -> GraphBuildResult:
    """Build a NetworkX graph from a cleaned network dataframe."""
    graph: nx.Graph = nx.DiGraph() if directed else nx.Graph()
    edge_frame = frame.copy()

    for row in edge_frame.itertuples(index=False):
        source = str(row.source)
        destination = str(row.destination)
        timestamp = row.timestamp.to_pydatetime() if hasattr(row.timestamp, "to_pydatetime") else row.timestamp
        protocol = str(row.protocol)

        graph.add_node(source)
        graph.add_node(destination)

        if graph.has_edge(source, destination):
            graph[source][destination]["weight"] = graph[source][destination].get("weight", 1) + 1
            graph[source][destination]["timestamps"].append(timestamp)
            graph[source][destination]["protocols"].append(protocol)
        else:
            graph.add_edge(
                source,
                destination,
                weight=1,
                timestamps=[timestamp],
                protocols=[protocol],
            )

    for node in graph.nodes:
        if node not in graph:
            graph.add_node(node)

    return GraphBuildResult(graph=graph, edge_frame=edge_frame)

