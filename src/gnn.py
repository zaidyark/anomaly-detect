"""A lightweight Graph Convolutional Network (GCN) autoencoder detector.

Deliberately hand-rolled instead of built on PyTorch Geometric: a GCN layer is
one matrix expression (``Â X W``), so a 2-layer encoder/decoder needs no
graph-specific library, no compiled extensions, and no GPU — just plain
CPU-only PyTorch. This keeps the whole model inspectable and installable
anywhere (including, eventually, an IoT edge device).

Anomaly scoring is unsupervised: the network is trained only to reconstruct
each node's own feature vector from its graph neighbourhood (a graph
autoencoder). Nodes whose structural position or features are unusual are
harder to reconstruct from their neighbours, so reconstruction error becomes
the anomaly score — no labels are used during training, keeping this
detector's contract identical to the classical detectors in
``anomaly_detection.py`` (it never sees the ground truth it is evaluated
against).

"Lightweight" here means small by architectural choice, not by post-hoc
compression (pruning/quantization/distillation): a handful of hidden units
and a few hundred parameters, so the model is inherently small enough to
state its exact footprint. See ``resource_profile()`` for the analytical
size/latency assessment used in place of physical hardware benchmarking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import networkx as nx
import numpy as np
import pandas as pd
import torch
from torch import nn

from src.preprocessing import scale_features, select_feature_frame

HIDDEN_DIM = 8
BOTTLENECK_DIM = 4
EPOCHS = 150
LEARNING_RATE = 0.05
SEED = 42


class LightweightGCN(nn.Module):
    """A 2-layer graph-convolutional encoder/decoder, feature-reconstruction autoencoder.

    Forward pass per layer: ``H' = activation(Â @ H @ W)`` where ``Â`` is the
    symmetrically-normalized adjacency with self-loops. No sampling, no
    attention, no learned graph structure — the simplest GCN formulation that
    still lets each node's representation depend on its neighbours.
    """

    def __init__(self, in_dim: int) -> None:
        super().__init__()
        self.encoder1 = nn.Linear(in_dim, HIDDEN_DIM, bias=False)
        self.encoder2 = nn.Linear(HIDDEN_DIM, BOTTLENECK_DIM, bias=False)
        self.decoder1 = nn.Linear(BOTTLENECK_DIM, HIDDEN_DIM, bias=False)
        self.decoder2 = nn.Linear(HIDDEN_DIM, in_dim, bias=False)

    def forward(self, adjacency: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        h = torch.relu(adjacency @ self.encoder1(features))
        z = adjacency @ self.encoder2(h)
        h = torch.relu(adjacency @ self.decoder1(z))
        reconstructed = adjacency @ self.decoder2(h)
        return reconstructed


def _normalized_adjacency(graph: nx.Graph, node_order: list[str]) -> torch.Tensor:
    """Symmetric normalization with self-loops: D^-1/2 (A + I) D^-1/2."""
    undirected = graph.to_undirected() if graph.is_directed() else graph
    adjacency = nx.to_numpy_array(undirected, nodelist=node_order, weight=None)
    adjacency = adjacency + np.eye(len(node_order))
    degree = adjacency.sum(axis=1)
    degree_inv_sqrt = np.zeros_like(degree)
    nonzero = degree > 0
    degree_inv_sqrt[nonzero] = np.power(degree[nonzero], -0.5)
    normalized = degree_inv_sqrt[:, None] * adjacency * degree_inv_sqrt[None, :]
    return torch.tensor(normalized, dtype=torch.float32)


def _train(model: LightweightGCN, adjacency: torch.Tensor, features: torch.Tensor) -> np.ndarray:
    torch.manual_seed(SEED)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    model.train()
    for _ in range(EPOCHS):
        optimizer.zero_grad()
        reconstructed = model(adjacency, features)
        loss = torch.mean((reconstructed - features) ** 2)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        reconstructed = model(adjacency, features)
        per_node_error = torch.mean((reconstructed - features) ** 2, dim=1)
    return per_node_error.numpy().astype(np.float64)


def _fit_and_score(features: pd.DataFrame, graph: nx.Graph) -> tuple[LightweightGCN, torch.Tensor, torch.Tensor, np.ndarray]:
    node_order = features["node"].astype(str).tolist()
    model_frame = select_feature_frame(features)
    scaled = scale_features(model_frame)

    adjacency = _normalized_adjacency(graph, node_order)
    feature_tensor = torch.tensor(scaled.to_numpy(), dtype=torch.float32)

    # Seed before constructing the model: nn.Linear draws its initial weights
    # from the global RNG at construction time, so seeding only inside
    # _train() (after the model already exists) does not make results
    # reproducible across process runs.
    torch.manual_seed(SEED)
    model = LightweightGCN(in_dim=feature_tensor.shape[1])
    raw_scores = _train(model, adjacency, feature_tensor)
    return model, adjacency, feature_tensor, raw_scores


def _scored_frame(features: pd.DataFrame, raw_scores: np.ndarray) -> pd.DataFrame:
    from src.anomaly_detection import _normalize_scores  # local import avoids a cycle

    result = features.copy()
    result["anomaly_score"] = _normalize_scores(raw_scores)
    result["anomaly_label"] = 0
    result["reason_flagged"] = "Within expected behavior"
    return result


def gcn_autoencoder_detection(features: pd.DataFrame, graph: nx.Graph) -> pd.DataFrame:
    """Score each node by GCN feature-reconstruction error (unsupervised)."""
    _model, _adjacency, _features, raw_scores = _fit_and_score(features, graph)
    return _scored_frame(features, raw_scores)


@dataclass(frozen=True)
class ResourceProfile:
    """Analytical resource-footprint assessment for an edge deployment target.

    Measured on this machine, not on physical constrained hardware — see
    docs/lightweight-gnn.md for why, and what that limitation means.
    """

    parameter_count: int
    model_size_kb: float
    inference_ms_per_node: float
    graph_nodes: int
    target_device: str
    target_ram_mb: int
    fits_target_ram: bool


# Raspberry Pi Zero 2 W: quad-core ARM Cortex-A53 @ 1 GHz, 512 MB RAM —
# the document's own named target for the smallest class of edge hardware.
TARGET_DEVICE = "Raspberry Pi Zero 2 W"
TARGET_RAM_MB = 512


def resource_profile(model: LightweightGCN, adjacency: torch.Tensor, features: torch.Tensor) -> ResourceProfile:
    """Estimate the model's footprint against a stated target device profile.

    This is an analytical estimate on ordinary development hardware, not a
    physical measurement on the target device (no Raspberry Pi or
    microcontroller is used) — an explicit, documented scope limitation.
    """
    parameter_count = sum(p.numel() for p in model.parameters())
    model_size_kb = parameter_count * 4 / 1024  # float32 weights, no compression applied

    model.eval()
    with torch.no_grad():
        start = time.perf_counter()
        repeats = 20
        for _ in range(repeats):
            model(adjacency, features)
        elapsed = time.perf_counter() - start
    inference_ms_per_node = (elapsed / repeats) * 1000 / max(1, features.shape[0])

    # The model's own weights plus one graph's worth of float32 activations
    # are the dominant runtime memory cost at this scale; both are trivial
    # next to a 512 MB budget.
    activation_estimate_kb = features.numel() * 4 / 1024
    fits = (model_size_kb + activation_estimate_kb) < (TARGET_RAM_MB * 1024 * 0.1)

    return ResourceProfile(
        parameter_count=parameter_count,
        model_size_kb=model_size_kb,
        inference_ms_per_node=inference_ms_per_node,
        graph_nodes=features.shape[0],
        target_device=TARGET_DEVICE,
        target_ram_mb=TARGET_RAM_MB,
        fits_target_ram=bool(fits),
    )


def gcn_autoencoder_with_profile(features: pd.DataFrame, graph: nx.Graph) -> tuple[pd.DataFrame, ResourceProfile]:
    """Train the detector once and return both its scores and its resource profile."""
    model, adjacency, feature_tensor, raw_scores = _fit_and_score(features, graph)
    profile = resource_profile(model, adjacency, feature_tensor)
    return _scored_frame(features, raw_scores), profile
