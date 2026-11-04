# research/ — TwinTrust-AP inside the live demo

This folder connects the live-drive demo to the project's own algorithms. It holds three things:

1. **The algorithm source,** unchanged. `aegis_ai/` is a copy of Vaishnavi's Python code from the Aegis-V2X repository: branch `feature/vaishnavi-ai-architect-ml-designer`, commit `add0a07` ("feat(phase5): integrate gdca authority into tahs", 2026-09-20). That repository is the source of truth; this copy is read-only reference. Copied files:
   - `ai/trust_estimator/`: Calibrated Twin Trust Estimator, `T = σ((0.20q − 0.35e − 0.25u − 0.20a)/τ)`, τ = 0.8.
   - `ai/criticality/`: Context-Aware Criticality Estimator. A weighted sum of 5 features (0.25, 0.25, 0.15, 0.20, 0.15).
   - `ai/twintrust_ap/gdca.py`: GDCA authority, `A = exp(−½z²)`.
   - `ai/twintrust_ap/tahs.py`: TAHS horizon, `H = Hmin + (Hmax − Hmin)·σ(βT − γC + δA)`.
   - `ai/twintrust_ap/fsdp.py` and `policy.py`: the FSDP contract. 9 states, 6 actions; no policy table yet.
   - `configs/model.yaml`, `digital_twin/state.py` and `ai/utils/`: needed for the imports.
2. **The JavaScript port and its tests.**
   - `port/twintrust_core.js` is embedded in `../index.html`.
   - `tests/` checks the port against the Python originals.
3. **The pipeline** that produced the calibration and the FSDP table from recorded demo runs, and the results it produced.

## What is new here (and what is not)

| Item | Status |
|---|---|
| Trust, criticality, GDCA, TAHS formulas | **Unchanged.** Ported exactly. |
| TAHS parameters | Changed for the demo only: β = 3, γ = 5, δ = 2. `configs/model.yaml` has β = γ = δ = 1, which can only reach horizons 3–8. The new values make 1–10 reachable, and the neutral point (0.5, 0.5, 0.5) still gives H = 5. The formula is unchanged. |
| Calibration (a, b) | **New.** Fitted here; the original code had no fitted calibration. |
| FSDP policy table | **New.** Generated here; it was the open Phase 5 blocker in `fsdp.py`. |
| Evidence (e, u, a, q, criticality features) | **New.** Computed live from the demo's twin vs LiDAR. The scales (3 m error, 1 s age, 300 ms latency, 20 m/s, 20 road users) are design choices. |

Everything below comes from the **browser simulation in this repository**, not from CARLA, Sionna RT or real vehicles.

## Tests

```bash
pip install pyyaml
python3 -I tests/gen_vectors.py aegis_ai vectors.json              # calls her Python functions on 2,000 random cases each
node tests/test_parity.cjs "$PWD/port/twintrust_core.js" "$PWD/vectors.json"
python3 tests/check_embedded.py                                     # the copy inside index.html is the tested port
```

Last run (2026-11-04):

- All cases match: trust, criticality, GDCA and spread 2,000 each (spread checks 4,000 windows), and TAHS 2,000 cases.
- Maximum absolute error 1.1 × 10⁻¹⁶. TAHS horizon mismatches: 0.
- The embedded copy is identical to the tested port.

## Pipeline

`pipeline/collect.py` runs the demo headless with Playwright, seeded so every run is reproducible.

- **Conditions:** 8 conditions × 150 s: normal, normal_fast, packet loss, +300 ms latency, LiDAR degradation, spoofing, loss + latency, slow dense traffic.
- **Driving:** a simple autopilot drives (it brakes when TTC < 2.5 s).
- **Recorded per cycle (10 Hz):** state, action, T, C, A, H, the evidence and the cost terms of J.

```bash
pip install playwright && playwright install chromium
python3 pipeline/collect.py explore.jsonl explore results/calibration.json        # random FSDP actions (exploration data)
SEED_OFF=500009 python3 pipeline/collect.py explore_b.jsonl explore results/calibration.json   # second batch, other seeds
python3 pipeline/calibrate_trust.py explore.jsonl calibration.json
python3 pipeline/generate_fsdp_policy.py explore_all.jsonl fsdp_policy.json   # cond names must differ per batch
python3 pipeline/collect.py eval_tt.jsonl twintrust
python3 pipeline/collect.py eval_fx.jsonl fixed
python3 pipeline/summarize_eval.py eval_tt.jsonl eval_fx.jsonl eval_summary.json
```

Recorded `.jsonl` files (about 7 MB each) are not committed; the seeds reproduce them.

### 1. Calibration — `results/calibration.json`

- **Method:** Platt scaling, `T_cal = σ(a·raw + b)`, where raw is her unchanged trust score. Her uncalibrated estimator is the special case a = 1/τ, b = 0.
- **Target:** the probability that a twin object is within 1 m of where the ego's LiDAR sees it on the next cycle.
- **Data:** fitted on 8,000 cycles and tested on 3,992 held-out cycles.

| | ECE (5 bands) | NLL |
|---|---:|---:|
| Uncalibrated (a = 1.25, b = 0) | 0.1288 | 0.6925 |
| Calibrated (a = 3.303, b = 0.660) | **0.0419** | **0.6478** |

Calibrated T ranges over about 0.22–0.72 on the test data. It does not reach 1, because in this simulation the twin is right only about 60–70% of the time even in good conditions.

### 2. FSDP policy table — `results/fsdp_policy.json`

- **Data:** 24,000 cycles with uniformly random actions.
- **Cost of an action:** the mean J over 10 cycles starting with the action's own cycle. J = 0.25L + 0.20E + 0.20O + 0.20F − 0.15R, from `configs/model.yaml`.
- **Choice per state:** the action with the lowest cost, if every action has at least 40 samples. Otherwise the cell uses the design rule from the algorithm design document.

| Trust ＼ Criticality | Low | Medium | High |
|---|---|---|---|
| **High** | beam_switch (z = 0.88) | reduce_horizon (z = 1.15) | predict *(design rule, no data)* |
| **Medium** | beam_switch (z = 0.22) | beam_switch (z = 0.88) | reduce_horizon (z = 1.32) |
| **Low** | synchronize *(design rule, 34 samples)* | beam_switch (z = 0.46) | reduce_horizon (z = 0.13) |

z is the gap to the runner-up action in standard errors. **None of the data-chosen cells is statistically separated from its runner-up** (all z < 2), so this table is provisional.

### 3. TwinTrust-AP vs fixed policy — `results/eval_summary.json`

- **Fixed baseline:** horizon 5, an edge synchronisation every 1 s, prediction always on.
- **Seeds:** the same per condition for both modes. Traffic diverges once actions differ, so these are two runs of the same scenario, not a cycle-by-cycle pairing.
- **Confidence intervals:** block bootstrap over 10 s blocks.

| Condition | J TwinTrust-AP | J fixed | ΔJ [95% CI] | Twin correct TT / fixed | Edge syncs/s TT / fixed |
|---|---:|---:|---|---:|---:|
| normal | −0.015 | 0.074 | −0.089 [−0.103, −0.076] | 59% / 63% | 0.0 / 44.1 |
| normal_fast | −0.014 | 0.066 | −0.079 [−0.091, −0.068] | 56% / 62% | 0.0 / 43.2 |
| loss | 0.104 | 0.184 | −0.080 [−0.089, −0.072] | 42% / 62% | 0.0 / 49.0 |
| latency | 0.076 | 0.163 | −0.087 [−0.099, −0.075] | 54% / 73% | 0.0 / 41.0 |
| lidar_degraded | 0.084 | 0.148 | −0.064 [−0.076, −0.052] | 9% / 9% | 6.7 / 39.1 |
| spoof | −0.002 | 0.076 | −0.078 [−0.089, −0.068] | 55% / 62% | 0.0 / 44.5 |
| loss_latency | 0.178 | 0.238 | −0.060 [−0.070, −0.051] | 40% / 66% | 0.0 / 47.6 |
| slow_dense | −0.019 | 0.078 | −0.097 [−0.108, −0.086] | 55% / 57% | 0.0 / 47.9 |
| **Overall** | **0.049** | **0.128** | **−0.079 [−0.096, −0.063]** | **46% / 57%** | **0.8 / 44.6** |

**How to read this (important):**

- TwinTrust-AP has a lower J in every condition. Almost all of the difference comes from the energy and sync-overhead terms (E 0.057 vs 0.343, O 0.002 vs 0.100), because the learned table almost never synchronises.
- It pays for this with a **less accurate twin.** Twin correctness is 46% vs 57% overall, and about 41% vs 64% under packet loss.
- The policy is doing what J asks. With R weighted at 0.15 against 0.20 + 0.20 for energy and overhead, J rates "sync less, accept a worse twin" as better.
- **A reviewer would rightly say this result shows the effect of the objective's weights, not that trust-driven control keeps the twin more accurate.** Before the result can support the paper's claims, two things are needed:
  1. **Vaishnavi decides the objective.** Options: re-weight J, add a constraint such as "twin correctness ≥ the fixed policy's", or use a Pareto comparison.
  2. **Regenerate the table and evaluate again** with the new objective.
- "Twin correct" uses LiDAR as the reference. Under LiDAR degradation (σ = 2.2 m) the reference itself is too noisy for a 1 m threshold, so that row says little about the twin.

Not yet experimentally verified beyond these simulated runs. No CARLA, Sionna RT or hardware results are claimed.
