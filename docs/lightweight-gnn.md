# Lightweight GNN Detector

A hand-rolled Graph Convolutional Network (GCN) autoencoder, added as a sixth
detector alongside the classical algorithms in
[Detection & Evaluation](detection-and-evaluation.md). This page covers why it
exists, how it works, what it measured, and — importantly — what it does
**not** claim.

## Why this exists

This detector is a scoped adaptation of a separate, more ambitious brief
("Lightweight Graph Neural Network-Based Anomaly Detection for
Resource-Constrained IoT Network Traffic") that called for a compressed GNN
empirically benchmarked on physical constrained hardware (Raspberry Pi Zero
2 W / ARM Cortex-M), trained on the IoT-23/IoTID20 datasets. Building that
exactly would require PyTorch Geometric, physical hardware, and novel
graph-compression research the source material's own literature review
admits is still an open problem. This adaptation keeps everything that is
genuinely buildable and honestly re-scopes the rest — see
[Deviations from the original brief](#deviations-from-the-original-brief).

## Architecture

`src/gnn.py::LightweightGCN` — a 2-layer graph-convolutional encoder/decoder
(a graph autoencoder), implemented in **plain CPU-only PyTorch, no PyTorch
Geometric**. A GCN layer is one matrix expression:

```
H' = activation(Â @ H @ W)
```

where `Â` is the symmetrically-normalized adjacency matrix with self-loops
(`D^-1/2 (A + I) D^-1/2`). That's the entire graph-specific logic — no
sampling, no attention, no compiled graph-batching library.

```
Encoder: features (10-dim) → GCN → hidden (8) → GCN → bottleneck (4)
Decoder: bottleneck (4)    → GCN → hidden (8) → GCN → reconstructed features (10-dim)
```

**224 parameters, 0.88 KB as float32** — small enough to state exactly, which
is the point: this model is lightweight *by architectural choice*, not via
pruning, quantization, or knowledge distillation. Those techniques are
explicitly out of scope (see below), and the model doesn't need them to be
small.

## Training: unsupervised, by design

The network is trained only to reconstruct each node's own feature vector
from its graph neighbourhood — no labels are used. Nodes whose structural
position or features are unusual are harder for their neighbourhood to
reconstruct, so **reconstruction error becomes the anomaly score**.

This matters for the evaluation to be meaningful: the detector never sees the
ground-truth labels it is later scored against (`tests/test_gnn.py` asserts
this at the function-signature level), keeping its contract identical to the
classical detectors — same `anomaly_score` / `anomaly_label` / `reason_flagged`
columns as every other algorithm in `detect_anomalies()`.

Unlike the classical detectors, the GNN also needs the graph's adjacency
structure, not just the feature table — `detect_anomalies()` and
`compare_algorithms()` both take an optional `graph` parameter for this reason
(see [Architecture](architecture.md) for the full callback wiring).

## Resource profile: analytical, not physical

`src/gnn.py::resource_profile()` reports:

- **Parameter count** and **model size in KB** (float32, uncompressed)
- **Inference latency per node**, timed on this development machine
- Whether that footprint **fits within a stated target device's RAM budget** —
  the Raspberry Pi Zero 2 W (512 MB RAM, quad-core ARM Cortex-A53 @ 1 GHz),
  the smallest device class named in the original brief

This is displayed in the dashboard whenever a scenario with ground truth is
active. Measured numbers on both real scenarios: **224 parameters, 0.88 KB,
~0.0004 ms/node** — comfortably inside a 512 MB budget by any reasonable
estimate.

**This is an estimate on ordinary development hardware, not a measurement on
physical constrained hardware.** No Raspberry Pi or microcontroller is
involved. This is the single biggest scope reduction from the original
brief, stated here explicitly rather than left implicit.

## Measured results

At the default threshold (0.65), scored with `compare_algorithms(..., graph=graph)`:

| Scenario | Ground truth | Lightweight GNN | Best classical detector |
|---|---|---|---|
| IoT-23 (real, port scan) | 2 devices | **F1 = 0.667** (caught the dominant scanner, missed a low-degree secondary flag) | Rule-Based / LOF / One-Class SVM / Consensus, all F1 = 0.667 |
| CTU-13 (real, 10 bots) | 10 devices | **F1 = 0** at default threshold | Consensus, F1 = 0.87 |

The GNN is competitive on IoT-23 — tied for best. **On CTU-13 it fails at the
default threshold, and this is worth understanding rather than hiding:**
inspecting the raw (pre-threshold) reconstruction error shows all 10 real
bots ranked in the top 10 of 320 nodes by score — the signal is genuinely
there. But one legitimate high-traffic server produces an even larger
reconstruction error than any bot, and because scores are min-max normalized
(0–1, matching every other detector's contract), that single outlier compresses
every other node's score toward zero, keeping the real bots under the 0.65 cutoff.

This is the same failure mode already documented for the rule-based detector
on CTU-13 in [Detection & Evaluation](detection-and-evaluation.md): a
detector built on structural/statistical signal alone can mistake a busy,
legitimate server for the real threat. It is an honest, reproducible finding
about unsupervised graph-structural anomaly detection on real infrastructure
traffic — not a bug to be tuned away. (Rank-based and log-scaled
normalization were tried during development and did shift the trade-off, but
each helped one scenario while hurting the other under the dashboard's single
shared threshold slider — a deliberately simple, honest scoring scheme was
kept over a tuned one.)

## Deviations from the original brief

Stated plainly, so nothing here is discovered rather than disclosed:

| Original requirement | What this delivers | Gap |
|---|---|---|
| PyTorch Geometric, GCN/GAT/GraphSAGE | Hand-rolled GCN in plain PyTorch | Narrower architecture space explored; no attention or sampling variants |
| Pruning + quantization + knowledge distillation | Small-by-design architecture (224 params) | No compression *technique* is executed — the brief's own literature review calls graph-specific compression an open research problem, so this is scoped out, not solved |
| Physical benchmarking on Raspberry Pi Zero 2 W / ARM Cortex-M | Analytical estimate on dev hardware, compared to the same device's spec sheet | No physical device touched; this is estimation, not measurement |
| Comparison against "full-scale GNN baselines" | Comparison against classical ML baselines only (already built) | A larger GCN/GAT as a second baseline was not built |
| IoT-23 / IoTID20 datasets | IoT-23 scenario 3-1 (real, labeled, verified) | Satisfied — this is not a deviation |
| Deployment guidelines "based on empirical results" | Guidelines would be based on analytical estimates | Weaker evidentiary basis than physical measurement |

If presenting this work under that title, state these scope reductions in the
report's own "Scope and Delimitations" section — see the conversation history
in this repo for the reasoning behind each one.

## Extending

Follows the same contract as every other detector — see
[Extending](extending.md#add-a-detection-algorithm). The one addition: any
detector needing the graph (not just features) should accept it as an
optional `graph` parameter and be threaded through `detect_anomalies()` /
`compare_algorithms()` the same way `lightweight_gnn` is.
