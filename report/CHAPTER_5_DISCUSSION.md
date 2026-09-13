# CHAPTER FIVE
## DISCUSSION, CONCLUSION AND RECOMMENDATIONS

This chapter interprets the results reported in Chapter Four, judges them against the five objectives set out in Section 1.4, situates the system relative to the literature reviewed in Chapter Two, and closes with the project's contributions and recommendations for future work. Where a claim in this chapter rests on a number, it points back to the specific table in Chapter Four that produced it.

---

### 5.1 Summary of Findings

Six detectors — a rule-based statistical detector, three classical machine-learning models (Isolation Forest, Local Outlier Factor, One-Class SVM), a four-way consensus ensemble, and the Lightweight GCN autoencoder — were run on identical graph features across four synthetic attack scenarios and two real, independently-labelled datasets (CTU-13 scenario 9 and IoT-23 scenario 3-1), and scored with precision, recall, and F1 against ground truth (Tables 4.6–4.12). Four findings stand out:

1. **No single detector wins everywhere.** The rule-based detector reaches a perfect F1 = 1.000 on the Network Scanner scenario, the exact pattern (degree + betweenness spike) it was written to catch, but F1 = 0.000 on the Rogue Bridge scenario, a pattern its bridge rule did not correctly isolate (Table 4.8).
2. **Consensus voting is the most consistently strong detector on real traffic.** On CTU-13, consensus reaches F1 = 0.870 with recall 1.0 — tied with Isolation Forest and One-Class SVM, all three ahead of the rule-based detector's F1 = 0.750 (Table 4.10).
3. **The Lightweight GNN is competitive on the dataset it was built for, and fails cleanly, explainably on the other.** On IoT-23 it ties the best classical detectors at F1 = 0.667 (Table 4.11); on CTU-13 it scores F1 = 0.000 at the default threshold (Table 4.10) for a specific, root-caused reason (Section 5.2), not an unexplained failure.
4. **The model is genuinely small.** 224 parameters, 0.88 KB, sub-millisecond-per-node inference latency on every dataset tested (Table 4.14) — comfortably inside the Raspberry Pi Zero 2 W's 512 MB RAM budget by three orders of magnitude, albeit measured on development hardware rather than the physical device (Section 5.3, objective 4).

All 33 automated tests pass (Table 4.5), and every number above is reproducible on demand with `make evaluate` (Section 4.9) — a capability that did not exist before this phase of the project and is itself one of its contributions (Section 5.8).

---

### 5.2 Interpretation of Results

**Why the rule-based detector is either the best or the worst detector, and nothing in between.** Its score is a fixed weighted sum of four statistics (degree, betweenness, new-neighbour ratio, is-bridge; Section 4.7.2) that encode exactly one hypothesis about what an attack looks like. When a scenario matches that hypothesis (Network Scanner: a real degree/betweenness spike), it wins outright. When it does not (Rogue Bridge: the isolated-bridge rule flagged a different structurally-unusual node instead of the true rogue access point), it has no fallback signal to catch the miss — the detector's biggest strength, full explainability of *why* it flagged a node, is inseparable from this same rigidity.

**Why consensus outperforms every individual detector on real traffic without ever "knowing more" than they do.** Consensus adds no new signal; it only requires two of four independent detectors to agree (Section 4.7.3). On CTU-13, this makes it immune to any single detector's idiosyncratic mistakes while still capturing every bot that at least two of Isolation Forest, One-Class SVM, LOF, or the rule-based detector independently flag — which is why it exactly matches the two strongest individual detectors (F1 = 0.870) rather than being dragged down by the weakest (LOF, F1 = 0.533).

**Why the Lightweight GNN fails on CTU-13 in a way that is diagnosable, not mysterious.** As documented in `docs/lightweight-gnn.md` and reproduced during this evaluation, inspecting the model's *raw*, pre-threshold reconstruction error shows all 10 real bots ranked in the top 10 of 320 nodes by score — the reconstruction-error signal genuinely separates bots from normal hosts. The failure is introduced downstream, by score normalisation: one legitimate, high-traffic server produces an even larger reconstruction error than any bot (it is likely itself a modest structural outlier — a busy server, not a botnet client), and because every detector in this system reports its score min-max normalised into [0, 1] for a consistent contract, that single outlier compresses every other node's score toward zero, pulling the true bots back under the 0.65 threshold even though their *relative* ranking was correct. This is the same class of mistake the rule-based detector makes on the same dataset for a related reason (Section 4.11): a detector built purely on structural/statistical unusualness can mistake a legitimate, busy server for the real threat, because "structurally unusual" and "malicious" are correlated, not identical, and real infrastructure traffic contains legitimately unusual hosts that synthetic scenarios do not.

**Why IoT-23 is where the Lightweight GNN succeeds.** With only 2 ground-truth devices and no single overwhelming legitimate outlier of the kind found in CTU-13's 320-host university network, the normalisation step that hurt CTU-13 does not compress the signal away here — the GNN's ranking and its threshold-crossing agree, producing the same F1 = 0.667 the best classical detectors reach independently.

---

### 5.3 Achievement of Objectives

Table 5.1 assesses each objective from Section 1.4 against the evidence produced in Chapter Four.

#### Table 5.1 — Objectives vs. evidence

| # | Objective (Section 1.4) | Evidence | Verdict |
|---|---|---|---|
| 1 | Represent IoT-23 traffic as a graph with node-level structural and temporal features | `src/graph_builder.py`, `src/metrics.py` (Section 4.7.1); the full feature set is computed and used for every detector in Tables 4.6–4.12 | **Achieved** |
| 2 | Develop a lightweight, edge-deployable GNN with an explicitly stated, minimal parameter count; identify compression techniques for future work | `LightweightGCN`, 224 parameters (Section 4.7.4, Table 4.14); compression techniques identified, not implemented, exactly as the objective's own wording scopes it | **Achieved as scoped** |
| 3 | Evaluate detection performance (P/R/F1) against real, ground-truth labelled traffic covering both botnet and port-scan behaviour, compared against classical baselines | Tables 4.10 (CTU-13, botnet) and 4.11 (IoT-23, port scan), both run against all four classical baselines on identical features | **Achieved** |
| 4 | Assess resource efficiency (parameters, size, latency) against the Raspberry Pi Zero 2 W's published RAM specification | Table 4.14; explicitly an analytical estimate on development hardware, never on the physical device | **Achieved analytically; physical measurement not attempted** |
| 5 | Propose deployment guidelines from the results obtained, and identify physical hardware validation as the next stage | Guidelines drafted in Section 5.9, grounded in Tables 4.10–4.14; physical validation is named here, as the objective itself anticipated, as future work rather than a delivered result | **Achieved within the objective's own stated limit** |

Four of five objectives are fully met by the evidence in Chapter Four; the fifth is met to exactly the extent its own wording asked for — a resource assessment and a set of guidelines *derived from* analytical results, with physical validation explicitly deferred. No objective was silently dropped or reinterpreted after the fact.

---

### 5.4 Comparison with Existing Systems

Section 2.6 identified five gaps in the literature this project set out to address: (1) evaluation confined to high-performance computing environments, (2) an absence of resource-efficiency reporting alongside accuracy, (3) immature, graph-unaware model compression, (4) no standardised graph-construction protocol, and (5) a gap between regulatory logging requirements and constrained-hardware feasibility. Table 5.2 compares this system's approach against the classes of system described in Sections 2.2 and 2.4.

#### Table 5.2 — This system vs. existing approaches

| Dimension | Typical existing approach (Chapter Two) | This system |
|---|---|---|
| Detection basis | Signature-based (Snort/Suricata, Section 2.2.1): blind to zero-day/novel attacks | Unsupervised structural/statistical anomaly detection (Sections 3.5, 4.7): the CTU-13 bots and IoT-23 scanner are caught without any attack-specific signature |
| Processing location | Cloud-centric platforms (Section 2.2.2): bandwidth cost, latency, centralised privacy risk | Entirely local (Section 3.3.3): no traffic, upload, or result leaves the machine |
| Reported metric | Villegas-Ch et al. (2025): GCN/GAT/GraphSAGE report >98% **accuracy** on IoT-23/IoTID20 | This system reports **precision/recall/F1** (Tables 4.6–4.12), the metric appropriate under the severe class imbalance real intrusion datasets have — on a 320-node graph with 2–10 true anomalies, a trivial "flag nothing" classifier already scores >96% raw accuracy, making accuracy alone an unreliable basis for comparison across studies that do not also report F1 |
| Resource-efficiency reporting | Largely absent (Section 2.5.2's documented gap) | Reported directly and reproducibly for every dataset (Table 4.14): parameter count, model size, per-node latency, explicit pass/fail against a named device's RAM budget |
| Path to smallness | Pruning / quantization / knowledge distillation (Zhou et al., 2024; Section 2.3.4) applied to an otherwise large model | Architectural minimalism (Section 3.5.4): the model is small by design, so no compression step is needed to reach 224 parameters |
| Graph construction | Ad hoc per study (Section 2.5.4's documented gap: no standard for what counts as a node or edge) | One fixed, documented convention (`source, destination, timestamp, protocol` → weighted graph, Section 4.7.1) applied identically to four synthetic scenarios and two real datasets from different capture tools (Argus, Zeek) |

This comparison is deliberately not a claim of outright superiority: the >98% accuracy figures in Villegas-Ch et al. (2025) were not reproduced or independently checked here, and this system was not tested against GAT or GraphSAGE baselines (an explicitly named deviation, `docs/lightweight-gnn.md`). The claim is narrower and evidenced directly by Chapter Four: this system closes gaps (2) and, partially, (4) from Section 2.6 in a way that is reproducible on demand (Section 4.9), which most of the reviewed literature, by its own account, does not do.

---

### 5.5 Advantages of the New System

- **Multi-detector, identical-features comparability.** Every detector — classical and GNN alike — runs on the same feature table (Section 4.7), so Table 4.12's comparisons are not confounded by different preprocessing, unlike comparing figures across separate papers each with their own pipeline.
- **Evidence from real, independently-labelled traffic, not only synthetic data.** CTU-13 and IoT-23's ground truth was assigned by the datasets' original researchers (Section 3.6.1), so Tables 4.10–4.11 are not a demonstration tuned to succeed on this project's own synthetic test data.
- **Explainability where it matters.** The rule-based detector and the consensus ensemble both produce a human-readable `reason_flagged` (Figures 4.3–4.4) — a SOC analyst is told *why* a device was flagged, not only that it was, which the GNN's reconstruction-error score alone cannot provide.
- **A small, inspectable, dependency-light GNN.** No PyTorch Geometric, no compiled graph-batching extension — `src/gnn.py` is under 200 lines and installs anywhere plain PyTorch does (Section 4.7.4).
- **Full reproducibility.** Every stochastic component is seeded (Section 3.1, `docs/detection-and-evaluation.md`), and `scripts/run_evaluation.py` (Section 4.9) turns every number in Chapter Four into a one-command, byte-for-byte reproducible artefact rather than a screenshot of a dashboard session.
- **A working automated test suite.** 33 tests (Table 4.5) exercise input validation, every detector, scenario determinism, and the specific guarantee that the GNN's training function cannot access ground truth (`TC-08`) — a level of automated verification not evidenced in most of the literature reviewed in Chapter Two.

---

### 5.6 Challenges Encountered

- **Sampling a 320-device graph from tens-of-thousands-of-host real captures without losing the attack signature.** `scripts/convert_ctu13.py` had to interleave each bot's own flows round-robin (rather than simply truncating) so that every infected host's behavioural signature survived the node budget alongside labelled-normal and background traffic (Section 3.6.2).
- **A detector's blind spot only became visible on real data.** CTU-13 scenario 11's DDoS bots send thousands of flows to a single target — degree 1 on a who-talks-to-whom graph, invisible to every purely topological feature this system computes. This was discovered only by testing against real traffic, not anticipated from the synthetic scenarios, and is documented as a known limitation (README, "Future Work") rather than hidden.
- **Diagnosing, not just observing, the GNN's CTU-13 failure.** It would have been easy to report "F1 = 0" and move on; establishing that the raw reconstruction-error ranking was actually correct, and that min-max normalisation against one outlier server was the specific mechanism destroying it (Section 5.2), took inspecting pre-threshold scores directly rather than trusting the final metric alone.
- **Tooling that should have existed did not.** Prior to this evaluation, detection accuracy could only be read off a running dashboard by hand or inferred from unit-test arithmetic on toy data — not reproducible, not scriptable, and not suitable for producing the tables in this chapter. Building `scripts/run_evaluation.py` was a precondition for writing this chapter honestly.
- **No access to the target physical hardware.** Objective 4's Raspberry Pi Zero 2 W was never available to this project (Section 1.6, Scope and Delimitations); the resource profile in Table 4.14 is consequently an estimate, not a measurement, and is reported as such rather than implied to be more than it is.
- **Reproducibility under randomness.** Louvain community detection, all three classical ML models, the synthetic scenario generator, and the GCN's own weight initialisation and training are each independently stochastic; making Tables 4.6–4.12 exactly reproducible required seeding every one of them individually (`random_state=42` throughout) and verifying determinism with a dedicated test (`TC-10`).

---

### 5.7 Implications of the Study

**For security operations practice.** The finding that consensus voting matches the best individual classical detector on real botnet traffic (Section 5.2) without any deep-learning component suggests that a simple, cheap ensemble of already-available detectors is a practical, low-cost way to raise confidence in an alert before a more expensive model is justified — relevant to teams without the resources to operate a GNN pipeline.

**For IoT security policy.** Consistent with the policy contribution identified in Section 1.5, the CTU-13 and IoT-23 results are indicative evidence that unsupervised, structure-based detection can identify botnet activity on infrastructure traffic without requiring a pre-existing attack signature — relevant to regulatory frameworks such as the EU Cyber Resilience Act that call for baseline anomaly-detection capability on connected devices without prescribing a specific technique.

**For GNN security research (Sections 2.5.1–2.5.2).** This project's resource-profile methodology (Section 4.10, Table 4.14) is a concrete, if modest, answer to the literature's documented habit of reporting accuracy without resource cost: every result in Chapter Four is paired with a parameter count, a model size, and a latency figure, computed the same way every time. The CTU-13 finding also carries a transferable methodological caution for that same research community: an anomaly score that is only ever validated on curated benchmark traffic can look correct while carrying a normalisation assumption (here, global min-max scaling) that silently breaks in the presence of a single extreme legitimate outlier — a failure mode worth checking for explicitly on any real deployment target, not just this one.

---

### 5.8 Contribution of the Project

1. **A reproducible, identical-features benchmarking pipeline** for comparing detectors on graph-structured network traffic — usable beyond this project as a harness for testing additional detectors under the same controlled conditions (Section 3.1.1).
2. **A working, minimally-parameterised (224-parameter) GCN autoencoder detector**, implemented without PyTorch Geometric, contributed as an inspectable, dependency-light reference implementation (`src/gnn.py`).
3. **A specific, root-caused account of a real detection failure mode** — the CTU-13 min-max-normalisation result (Section 5.2) — reported as a finding in its own right rather than omitted, contributing an honest data point to a literature that Section 2.5.2 already flags as thin on real-world resource and failure-mode reporting.
4. **A command-line detection-accuracy evaluation tool** (`scripts/run_evaluation.py`, Section 4.9), which converts every table in Chapter Four from a manually-observed dashboard reading into a one-command, scriptable, reproducible artefact — a methodological contribution usable by anyone extending this codebase.
5. **A 33-test automated verification suite plus a documented manual test protocol** (Section 4.8), providing a template for testing anomaly-detection software specifically, where "runs without crashing" and "detects correctly" are different claims requiring different kinds of tests.

---

### 5.9 Recommendations for Future Work

1. **Physical hardware validation.** Run the trained Lightweight GCN on an actual Raspberry Pi Zero 2 W (or a comparable ARM Cortex-M microcontroller) to replace Table 4.14's analytical estimate with a measured latency, memory footprint, and power draw — the single most important next step, and the one both Objective 4/5 and Section 1.6 already name as this project's explicit boundary.
2. **Flow-volume features.** Add weighted-degree and per-edge flow-count features so volume-based attacks (CTU-13 scenario 11's single-target DDoS, Section 5.6) become visible to detectors that currently see only topology.
3. **A normalisation scheme robust to extreme legitimate outliers.** Informed directly by Section 5.2's diagnosis, evaluate rank-based or per-cohort score normalisation for the GNN (and the rule-based detector) so that one unusually busy legitimate host cannot compress the scores of genuinely malicious nodes below threshold.
4. **Model compression as a complementary path.** Apply pruning, quantization, or knowledge distillation (Section 2.3.4) on top of the current architecture, and compare the result against this project's architecture-driven minimalism, directly addressing the compression techniques Objective 2 named but deferred.
5. **Broader GNN architecture exploration.** Add Graph Attention Network and GraphSAGE baselines (Sections 2.4.8–2.4.9) alongside the current GCN, following through on the comparison this project's own scope document (`docs/lightweight-gnn.md`) named as not yet built.
6. **Contribute the graph-construction convention as a candidate standard.** Publish the `source, destination, timestamp, protocol` → weighted-graph convention and the `.truth.json` ground-truth sidecar format (Section 4.4) as a proposal toward the standardised graph-construction protocol Section 2.5.4 identifies as missing from the field.
7. **Dashboard and analysis features identified during development** (README, "Future Work"): session-aware timeline playback beyond the current time-window filter, deeper community-detection views, a shortest-path investigation workflow, multi-tenant incident bookmarking, and authentication/persistence for multi-user deployment.

---

### 5.10 Conclusion

This project set out to build and evaluate a lightweight, graph-based anomaly detection system for IoT network traffic, centred on a minimally-parameterised GCN autoencoder. Chapter Four's results show a system that meets four of its five objectives directly and the fifth to exactly the extent it was scoped to: real, independently-labelled traffic was represented as graphs and detected against with measured precision/recall/F1 (Tables 4.10–4.11), a 224-parameter GNN was built and shown analytically to fit comfortably inside a named constrained device's memory budget (Table 4.14), and every one of these results is reproducible on demand rather than asserted (Section 4.9). The system also produced an honest negative result — the GNN's failure on CTU-13 — and, unlike a simple pass/fail report, this project traced that failure to a specific, fixable mechanism (Section 5.2), which is itself evidence that the evaluation methodology in Section 3.7.2 did what it was designed to do: surface what actually works, and what does not, rather than only what was hoped for. The recommendations in Section 5.9, beginning with physical hardware validation, define the direct path from this project's analytical evidence to a deployable one.
