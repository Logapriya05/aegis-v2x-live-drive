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
| FSDP policy table | **New.** Chosen here by a constrained closed-loop search; it was the open Phase 5 blocker in `fsdp.py`. |
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

`pipeline/collect.py` runs the demo headless with Playwright. The conditions come from `scenarios.json` (the scenario catalogue). Math.random is seeded per condition, but runs are **not bit-identical**: the page's 2.5 s load warm-up runs in real time, so the machine's speed changes how many random numbers are used before the seeded run starts. Repeating a seed set gives statistically similar, not identical, results (for example J 0.1278 vs 0.1284 for the fixed policy on the same seeds).

- **Conditions:** 8 conditions × 150 s: normal, normal_fast, packet loss, +300 ms latency, LiDAR degradation, spoofing, loss + latency, slow dense traffic.
- **Driving:** a simple autopilot drives (it brakes when TTC < 2.5 s).
- **Recorded per cycle (10 Hz):** state, action, T, C, A, H, the evidence and the cost terms of J.

```bash
pip install playwright && playwright install chromium
python3 pipeline/collect.py explore.jsonl explore results/calibration.json        # random FSDP actions (exploration data)
SEED_OFF=500009 python3 pipeline/collect.py explore_b.jsonl explore results/calibration.json   # second batch, other seeds
python3 pipeline/calibrate_trust.py explore.jsonl calibration.json
python3 pipeline/generate_fsdp_policy.py explore_all.jsonl fsdp_policy_j_only.json   # J-only table; cond names must differ per batch
SEED_OFF=777 python3 pipeline/collect.py s_fixed.jsonl fixed - - 90                 # selection seeds
SEED_OFF=777 python3 pipeline/collect.py s_c9.jsonl twintrust - c9.json 90         # one run per candidate table
python3 pipeline/select_policy.py s_fixed.jsonl s_c*.jsonl                          # constrained selection
python3 pipeline/collect.py eval_tt.jsonl twintrust - results/fsdp_policy.json
python3 pipeline/collect.py eval_fx.jsonl fixed
python3 pipeline/summarize_eval.py eval_tt.jsonl eval_fx.jsonl eval_summary.json
# age-of-information baseline: threshold search on the selection seeds, then repeated runs (section 6)
for th in 0.2 0.35 0.5 0.8; do SEED_OFF=777 AOI_THR=$th python3 pipeline/collect.py s_aoi$th.jsonl aoi - - 90; done
for so in 0 2000 4000; do
  SEED_OFF=$so python3 pipeline/collect.py ev${so}_fixed.jsonl fixed
  SEED_OFF=$so python3 pipeline/collect.py ev${so}_b1.jsonl twintrust - results/fsdp_policy.json
  SEED_OFF=$so AOI_THR=0.8 python3 pipeline/collect.py ev${so}_aoi.jsonl aoi
  SEED_OFF=$so AOI_THR=0.2 python3 pipeline/collect.py ev${so}_aoi02.jsonl aoi
done
python3 pipeline/summarize_repeated.py eval_repeated.json ev0 ev2000 ev4000
# section 8: GRU training tracks (own seeds), then the same exploration / calibration / selection / repeated runs
python3 pipeline/collect_tracks.py tracks.jsonl 240 6
python -m ai.gru.train_twin_predictor tracks.jsonl gru_twin.json      # in bossygirl-1818/Aegis-V2X
MODES=tt,fixed,aoi,aoi02,ttctrv,fixedctrv python3 pipeline/summarize_repeated.py eval_final.json ev0 ev2000 ev4000
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

### 2. FSDP policy table (first version, c9) — `results/fsdp_policy_c9.json`

**Objective, decided 2026-11-04:** minimise J = 0.25L + 0.20E + 0.20O + 0.20F − 0.15R (`configs/model.yaml`), but only among tables whose twin correctness R is at least the fixed policy's, overall and in every condition (tolerance 0.01).

**Why this objective.** A first table chose actions by J alone (`results/fsdp_policy_j_only.json`, from 24,000 random-action cycles).

- It lowered J in every test condition (ΔJ −0.079, 95% CI [−0.096, −0.063]) by almost never synchronising.
- But its twin was correct less often: 46% vs 57% (`results/eval_summary_j_only.json`).
- That shows the effect of J's weights, not a better twin, so the accuracy rule was added.

**How the table was chosen** (`pipeline/select_policy.py`, results in `results/policy_search.json`):

- Random-action data can't show the rule, because one action's effect on accuracy depends on the actions after it.
- So whole candidate tables were run in the simulation as policies.
- Selection used separate seeds (`SEED_OFF=777`, 90 s per condition). The chosen table was then evaluated once on the original evaluation seeds.

| Candidate | Rule | J | Twin correct | Syncs/s |
|---|---|---:|---:|---:|
| Fixed policy | horizon 5, sync every 1 s | 0.137 | 0.534 | 45.2 |
| c0 | J only | 0.046 | 0.464 | 2.2 |
| c1 | c0 + sync when trust is low | 0.083 | 0.472 | 48.0 |
| c5 | predict everywhere | 0.065 | 0.468 | 0.0 |
| c6 | increase horizon everywhere | 0.094 | 0.493 | 0.0 |
| c7 | sync when trust is low, else predict | 0.105 | 0.500 | 57.0 |
| c8 | sync when trust is low; else increase horizon if criticality ≥ medium, predict otherwise | 0.137 | 0.527 | 45.8 |
| **c9** | **sync when trust is low, else increase horizon** | **0.124** | **0.530** | **34.6** |
| c10 | c9 + sync at medium trust / high criticality | 0.142 | 0.522 | 55.2 |

**No candidate met the rule.** Every one was below the fixed policy in at least one condition.

What made the difference, seen in the runs:

- **Prediction horizon.** Under packet loss and latency, information is 0.6–0.9 s old and trust is low. TAHS then picks short horizons (1–2 steps, 0.1–0.2 s), so the twin cannot bridge the delay. The fixed policy always predicts 0.5 s ahead.
- **Prediction is switched off.** The table's "synchronize" and "beam switch" actions turn prediction off.
- **Trust that stays high.** In c9's weak conditions, calibrated trust stays high while the twin gets worse, so the table never asks for a sync. The trust estimator does not detect those degradations.

**Decision (2026-11-04):** use c9, the closest, and report the conditions where it misses the rule.

### 3. c9 vs fixed policy on the evaluation seeds — `results/eval_summary_c9.json`

- **Seeds:** the same per condition for both modes, 150 s per condition. Traffic diverges once actions differ, so these are two runs of the same scenario, not a cycle-by-cycle pairing.
- **Confidence intervals:** block bootstrap over 10 s blocks.

| Condition | J c9 | J fixed | ΔJ [95% CI] | Twin correct c9 / fixed | Syncs/s c9 / fixed |
|---|---:|---:|---|---:|---:|
| normal | 0.031 | 0.074 | −0.043 [−0.061, −0.027] | 59% / 63% | 0.0 / 44.1 |
| normal_fast | 0.001 | 0.066 | −0.064 [−0.081, −0.048] | 70% / 62% | 0.0 / 43.2 |
| loss | 0.199 | 0.184 | +0.015 [−0.004, 0.030] | 65% / 62% | 31.6 / 49.0 |
| latency | 0.196 | 0.163 | +0.033 [−0.006, 0.073] | 66% / 73% | 62.8 / 41.0 |
| lidar_degraded | 0.200 | 0.148 | +0.052 [0.038, 0.067] | 11% / 9% | 102.3 / 39.1 |
| spoof | 0.020 | 0.076 | −0.056 [−0.067, −0.043] | 60% / 62% | 0.0 / 44.5 |
| loss_latency | 0.326 | 0.238 | +0.088 [0.076, 0.100] | 65% / 66% | 198.1 / 47.6 |
| slow_dense | 0.005 | 0.078 | −0.073 [−0.086, −0.062] | 64% / 57% | 0.0 / 47.9 |
| **Overall** | **0.122** | **0.128** | **−0.006 [−0.030, 0.018]** | **57.5% / 56.6%** | **49.3 / 44.6** |

**How to read this:**

- **Accuracy:** c9 keeps the twin about as accurate as the fixed policy overall (57.5% vs 56.6%).
- **Cost:** J is not significantly different overall.
- **Synchronisation moves rather than shrinks.**
  - With good links (normal, spoof, slow dense) c9 does not synchronise at all, and has lower J with similar or better accuracy.
  - With degraded links it synchronises much more, up to 198 per second under loss + latency, and has higher J.
  - That is the trust-driven behaviour the design intends, but **total** synchronisation is not lower (49 vs 45 per second).
- **The accuracy rule per condition is still not met.** On these seeds c9 is less accurate under latency (−7 points), in normal driving (−4) and under spoofing (−2).
- **The weak conditions change with the seeds.** On the selection seeds they were spoofing and slow dense traffic; here they are latency and normal driving. So per-condition differences of a few points are within run-to-run variation at 90–150 s per condition. Longer or repeated runs are needed before reporting any per-condition claim.
- **Reference noise:** "Twin correct" uses LiDAR as the reference. Under LiDAR degradation (σ = 2.2 m) the reference itself is too noisy for a 1 m threshold, so that row says little about the twin.

### 4. c9 + joint beam adaptation (superseded by section 5) — `results/eval_summary_joint_beam.json`

The demo ships c9 together with **joint beam adaptation**: in the same cycle as the table's action, the beam is switched (alternate path / relay, held 2 s) whenever at least 5% of V2V links are blocked by buildings. Prediction horizon, synchronisation and beam are therefore decided together in every cycle.

**The beam model is abstract.** A switch cuts the extra loss on blocked links from 30% to 6%. It is not ray-traced and has no mmWave/THz beam physics.

Evaluation seeds, 150 s per condition, against the same fixed-policy runs:

| Condition | J joint | J fixed | ΔJ [95% CI] | Twin correct joint / fixed | Syncs/s joint / fixed |
|---|---:|---:|---|---:|---:|
| normal | 0.024 | 0.074 | −0.050 [−0.063, −0.038] | 57.3% / 62.7% | 0.0 / 44.1 |
| normal_fast | 0.005 | 0.066 | −0.061 [−0.074, −0.048] | 60.2% / 62.0% | 0.0 / 43.2 |
| loss | 0.187 | 0.184 | +0.003 [−0.020, 0.024] | 51.8% / 61.9% | 22.0 / 49.0 |
| latency | 0.203 | 0.163 | +0.040 [−0.004, 0.078] | 70.3% / 72.7% | 55.8 / 41.0 |
| lidar_degraded | 0.172 | 0.148 | +0.023 [0.013, 0.035] | 8.1% / 8.6% | 54.5 / 39.1 |
| spoof | −0.011 | 0.076 | −0.087 [−0.104, −0.068] | 61.5% / 62.4% | 0.0 / 44.5 |
| loss_latency | 0.304 | 0.238 | +0.066 [0.056, 0.077] | 65.5% / 65.6% | 163.5 / 47.6 |
| slow_dense | 0.008 | 0.078 | −0.070 [−0.083, −0.059] | 54.9% / 56.8% | 0.0 / 47.9 |
| **Overall** | **0.111** | **0.128** | **−0.017 [−0.040, 0.006]** | **53.7% / 56.6%** | **37.0 / 44.5** |

**How to read this:**

- **Fewer synchronisations:** 17% fewer edge synchronisations than the fixed policy (37.0 vs 44.5 per second).
- **Cost:** lower J overall, but the difference is not statistically significant.
- **Accuracy:** about 3 points lower twin correctness (53.7% vs 56.6%), mostly under packet loss (51.8% vs 61.9%). So the accuracy constraint is not met.
- **Beam switching:** in this city layout at least 5% of links are almost always blocked, so the beam was switched every 2 s (0.49 per second) in every condition. In practice it acted like an always-on relay rather than a condition-dependent choice. A finer beam model (per-link beams, ray-traced blockage) is needed for beam adaptation to show condition-specific behaviour.
- **Beam failures:** 0.

**What a fair claim from this simulation would be:** trust-driven control can match the fixed policy's twin accuracy while moving synchronisation to where the link is degraded. It does **not**, in this setup, reduce total resource use under the accuracy rule.

**What would strengthen it:**
- Trust evidence that reacts to spoofing and dense traffic, for example GDCA authority or V2X consistency.
- A TAHS horizon that does not shrink when information is stale.
- Longer, repeated evaluation runs.

Not yet experimentally verified beyond these simulated runs. No CARLA, Sionna RT or hardware results are claimed.


### 5. Final configuration: mmWave beam model + table b1 — `results/eval_summary.json`

**Beam model (added 2026-11-06).** The earlier blockage/relay model made beam switching nearly useless, so a simple mmWave model was added for V2V links. The values are design choices for an FR2 link, not measured:

- **Alignment.** Each link keeps the bearing its beam was last aligned to. As vehicles move, the bearing drifts.
- **Loss.** Beyond half the 12° beamwidth, packet loss rises by up to 70%.
- **Degraded links.** Misaligned links count as degraded in the criticality blockage feature.
- **Beam switch.** It re-sweeps every link, with a 20 ms outage.
- **Fixed policy.** It sweeps every 1 s, together with its sync.
- **Joint beam switch.** The automatic switch from section 4 (`JOINT_BEAM`) stays on.

**Selection** (`results/policy_search_beam.json`, selection seeds, 90 s per condition):

| Candidate | Rule | J | Twin correct | Syncs/s |
|---|---|---:|---:|---:|
| Fixed policy | horizon 5, sync + beam sweep every 1 s | 0.130 | 0.546 | 47.2 |
| c9 | sync when trust is low, else increase horizon | 0.198 | 0.500 | 85.4 |
| b1 | sync when trust is low, beam switch when medium, increase horizon when high | 0.092 | 0.505 | 40.9 |
| b2 | as b1, beam switch only at medium trust with criticality ≥ medium | 0.099 | 0.496 | 45.4 |
| b3 | sync when trust is low, beam switch at high criticality or medium/medium | 0.095 | 0.497 | 42.7 |

- **Without beam switching (c9):** misaligned links pile up, trust drops, and the table floods synchronisation.
- **With beam switching (b1–b3):** J is about 30% below the fixed policy's, but twin correctness is 4–5 points lower. **No candidate met the accuracy rule.**
- **Choice:** b1 had the lowest J and the highest accuracy of the beam-aware tables.

**b1 vs fixed policy, evaluation seeds** (150 s per condition):

| Condition | J b1 | J fixed | ΔJ [95% CI] | Twin correct b1 / fixed | Syncs/s b1 / fixed |
|---|---:|---:|---|---:|---:|
| normal | 0.027 | 0.070 | -0.043 [-0.053, -0.033] | 53.9% / 60.6% | 0.0 / 47.1 |
| normal_fast | -0.005 | 0.068 | -0.073 [-0.084, -0.062] | 59.9% / 64.5% | 0.0 / 42.7 |
| loss | 0.117 | 0.183 | -0.066 [-0.076, -0.057] | 51.4% / 57.4% | 34.2 / 52.5 |
| latency | 0.174 | 0.168 | +0.007 [-0.011, +0.026] | 63.1% / 65.3% | 89.4 / 43.0 |
| lidar_degraded | 0.133 | 0.148 | -0.015 [-0.029, -0.000] | 7.4% / 7.1% | 58.4 / 39.8 |
| spoof | 0.024 | 0.069 | -0.045 [-0.061, -0.030] | 55.4% / 61.5% | 0.0 / 47.1 |
| loss_latency | 0.243 | 0.250 | -0.007 [-0.019, +0.008] | 61.0% / 59.2% | 207.5 / 46.6 |
| slow_dense | 0.009 | 0.070 | -0.061 [-0.070, -0.052] | 57.7% / 61.9% | 0.0 / 48.0 |
| **Overall** | **0.090** | **0.128** | **-0.038 [-0.057, -0.018]** | **51.2% / 54.7%** | **48.7 / 45.8** |

**How to read this:**

- **Cost:** J is 30% lower overall and the difference is significant. It comes from fresher information (L 0.40 vs 0.49) and less energy (E 0.23 vs 0.33).
- **Accuracy:** the twin is correct 3.5 points less often (51.2% vs 54.7%), so the accuracy rule is **not** met.
- **Synchronisation:** about the same in total (48.7 vs 45.8 per second). It is moved to degraded links: none with good links, up to 207 per second under loss + latency.
- **What can be claimed:** in this simulation, joint trust-driven control of prediction horizon, synchronisation and beam lowers the J objective by 30% at a cost of about 3.5 points of twin accuracy.

Not yet experimentally verified beyond these simulated runs. No CARLA, Sionna RT or hardware results are claimed.

### 6. Literature baseline and repeated runs (2026-11-06, superseded by section 8) — `results/eval_repeated.json`

**Baseline: age-of-information (AoI) threshold updates.** The twin is synchronised (with a beam sweep, like the fixed policy) whenever the mean age of its V2X information exceeds a threshold; horizon 5, prediction always on. Threshold policies are the standard way to keep information fresh in the AoI literature:

- Kaul, Yates, Gruteser, "Real-time status: How often should one update?", IEEE INFOCOM 2012 (the AoI metric).
- Sun, Uysal-Biyikoglu, Yates, Koksal, Shroff, "Update or Wait: How to Keep Your Data Fresh", IEEE Trans. Inf. Theory, 2017 (threshold-type update policies).

This is our implementation of the threshold idea in this simulation, not the authors' code. Demo mode `aoi` (headless only), `TTAP_CFG.AOI`.

**Threshold choice** (`results/aoi_threshold_search.json`, selection seeds, 90 s per condition):

| Policy | J | Twin correct | Syncs/s |
|---|---:|---:|---:|
| Fixed policy | 0.131 | 54.6% | 47.2 |
| b1 | 0.092 | 50.5% | 40.9 |
| AoI 0.8 s | 0.138 | 52.4% | 45.6 |
| AoI 0.5 s | 0.147 | 58.0% | 108.1 |
| AoI 0.35 s | 0.174 | 62.1% | 177.5 |
| AoI 0.2 s | 0.234 | 68.4% | 301.4 |

- **Main baseline: 0.8 s.** It has the lowest J of the AoI thresholds and about the same sync budget as the fixed policy.
- **High-accuracy reference: 0.2 s.** It is the only threshold that meets the accuracy rule, at about 6 times the synchronisation.

**Repeated runs.** Three new seed sets (`SEED_OFF` 0, 2000, 4000), 8 conditions × 150 s each, all four policies. The 95% CIs use Student's t over the 3 seed sets (2 degrees of freedom), so they are wide.

| Policy | J | Twin correct | Syncs/s | Beam sweeps/s |
|---|---:|---:|---:|---:|
| **TwinTrust-AP (b1)** | **0.092** | 52.5% | 49.5 | 4.72 |
| Fixed (H 5, sync + sweep every 1 s) | 0.129 | 56.6% | 44.8 | 1.00 |
| AoI threshold 0.8 s | 0.136 | 56.5% | 48.2 | 1.07 |
| AoI threshold 0.2 s | 0.215 | 69.1% | 274.1 | 6.14 |

| Difference (b1 − other) | ΔJ [95% CI] | Δ twin correct [95% CI] | Δ syncs/s [95% CI] |
|---|---|---|---|
| vs fixed | −0.036 [−0.047, −0.026] | −4.1 points [−8.8, +0.7] | +4.7 [+2.1, +7.4] |
| vs AoI 0.8 s | −0.044 [−0.065, −0.023] | −4.0 points [−7.0, −0.9] | +1.3 [−2.6, +5.2] |
| vs AoI 0.2 s | −0.123 [−0.133, −0.113] | −16.7 points [−21.1, −12.3] | −225 [−240, −209] |

**Per condition** (mean over the 3 sets, no interval):

| Condition | J b1 | J fixed | J AoI 0.8 | Correct b1 | Correct fixed | Correct AoI 0.8 |
|---|---:|---:|---:|---:|---:|---:|
| normal | 0.012 | 0.071 | 0.078 | 58.9% | 61.2% | 58.7% |
| normal_fast | 0.018 | 0.072 | 0.085 | 56.6% | 63.8% | 56.6% |
| loss | 0.106 | 0.166 | 0.151 | 57.6% | 67.5% | 70.3% |
| latency | 0.193 | 0.179 | 0.223 | 55.4% | 65.3% | 67.0% |
| lidar_degraded | 0.133 | 0.153 | 0.148 | 8.4% | 8.5% | 8.2% |
| spoof | 0.020 | 0.084 | 0.086 | 56.0% | 59.7% | 53.9% |
| loss_latency | 0.252 | 0.243 | 0.256 | 61.9% | 62.9% | 74.5% |
| slow_dense | 0.006 | 0.061 | 0.062 | 65.1% | 63.6% | 62.6% |

**How to read this:**

- **J.** TwinTrust-AP has the lowest J against both baselines on every seed set, and the intervals exclude 0.
- **Accuracy.** Twin correctness is about 4 points lower than the fixed policy (the interval includes 0) and than AoI 0.8 s (the interval excludes 0). The accuracy rule is still not met.
- **What the AoI baseline adds.** At the same sync budget, the age threshold does not do better than syncing every second (J 0.136 vs 0.129). Information age alone does not tell the twin where to sync. To reach high accuracy, the age threshold needs about 6 times the synchronisation.
- **Where b1 loses.** Under latency and loss + latency, b1's J is not lower and its accuracy is clearly lower. This is the known short-horizon-under-delay limitation.
- **Low LiDAR accuracy.** Correctness is about 8% for every policy under LiDAR degradation, because the "correct" test (within 1 m of the LiDAR position) fails with 2.2 m LiDAR noise. It measures the reference sensor, not the twin.

Simulation only. Not yet experimentally verified on CARLA, Sionna RT or hardware.

### 7. Decision time on a CPU — `results/decision_timing_cpu.json`

`evaluation/benchmark_twintrust_ap.py` (in `bossygirl-1818/Aegis-V2X`) times one decision cycle of the Python code: evidence → calibrated trust → criticality → TAHS → FSDP.

- **Setup:** 20,000 cycles with seeded random inputs, on a 2-vCPU Intel Xeon 2.1 GHz cloud VM with Python 3.13.
- **Latency:** mean 13.2 µs, median 11.2 µs, p99 32.7 µs, max 172 µs. This is far inside the 100 ms budget of the 10 Hz loop.
- **Memory:** peak traced Python allocation of 8.5 KiB over 1,000 cycles.
- **Scope:** decision logic only. It excludes perception and the digital-twin update, and it was not measured on a Jetson Orin (future work). Re-run it on the target machine before quoting it for that machine.

### 8. Final configuration: 3GPP mmWave channel + GRU twin predictor (2026-11-06) — `results/eval_final.json`

Three changes, then the whole pipeline (calibration, selection, repeated runs) was run again. **These are the numbers to report; sections 5–6 are superseded.**

**1. 3GPP mmWave V2V channel** (replaces the distance/blockage heuristic for V2V links; `v2vChannel` in `index.html`):

- **Path loss:** 3GPP TR 37.885 V2V urban, as implemented in ns-3 `ThreeGppV2vUrbanPropagationLossModel`.
  - LOS and NLOSv: 38.77 + 16.7 log10 d + 18.2 log10 fc.
  - NLOS: 36.85 + 30 log10 d + 18.9 log10 fc.
- **Vehicle blockage (NLOSv):** lognormal extra loss, mean 5 dB (car) or 9 dB (bus/truck) + max(0, 15 log10 d − 41) dB.
- **Shadowing:** 3 dB (LOS, NLOSv) or 4 dB (NLOS), correlated over 10 m.
- **Link state:** from the simulated geometry.
  - NLOS if a building cuts the line of sight.
  - NLOSv if a vehicle is within 1.2 m of it.
  - Otherwise LOS.
- **Beam gain:** 3GPP TR 38.901 element pattern −min(12 (θ/12°)², 30 dB), θ = drift since the last beam sweep.
- **Link budget** (design choices, not measured): 30 GHz, 23 dBm, 10 dBi per side, 400 MHz, noise figure 9 dB, packet error 1/(1 + e^((SNR − 3 dB)/0.8)).
- **Beam switch:** for 2 s, NLOS links use a reflected path (LOS path loss + 10 dB).
- **Effect** (measured on one run): NLOS links lose about 95% of packets (median SNR −7 dB), LOS links almost none (median 26 dB).

**2. GRU twin motion predictor** (`GRU_W` and `gruForward` in `index.html`; `TTAP_CFG.PRED`):

- **Model:** Vaishnavi's `GRUPredictor` architecture (`ai/gru/model.py`), profile `perception.gru_twin` (hidden 32, 1 layer).
- **Training:** by `ai/gru/train_twin_predictor.py` on 6 × 240 s of tracks from `pipeline/collect_tracks.py`, recorded with their own seeds.
- **Inputs and outputs:** the last 8 received messages of a vehicle → displacement at horizons 1, 2, 3, 5, 8, 10 × 0.1 s.
- **Port check:** the JavaScript forward pass matches PyTorch to 5 × 10⁻⁶ m.
- **Design note:** all six horizons are predicted in one pass. `GRUPredictor` adds the horizon embedding before a linear head, so on its own the embedding only shifts the output by a constant per horizon. Trained that way, the errors at horizons 1 and 10 were 2–3 times the dead-reckoning error.
- **Offline test** (`results/gru_offline_eval.json`, held-out run, 20% message loss, 0.4 m position noise):

  | Horizon | GRU mean error | CTRV (dead reckoning) | GRU within 1 m | CTRV within 1 m |
  |---|---:|---:|---:|---:|
  | 0.1 s | 0.19 m | 0.50 m | 100.0% | 95.4% |
  | 0.5 s | 0.21 m | 0.55 m | 99.4% | 93.0% |
  | 1.0 s | 0.37 m | 0.83 m | 96.2% | 77.2% |

**3. Twin correctness measured on the twin's estimate.**

- **Before:** "twin correct" (the calibration target and R in J) was measured on the drawn twin object. That object is smoothed for display and evaluated one 0.05 s step late, about 0.5–1 m of artificial error at 10 m/s.
- **Now:** it is measured on the twin's position estimate at the same instant (`twinEstimate`).
- **Size of the change, on one seeded run (fixed policy):** vehicle twin correctness went from 61% (drawn object) to 99.1% (GRU estimate), against 95.6% for the CTRV estimate.
- **Also recorded:** vehicle-only correctness (`correctV2V`) and error (`meanErrV2V`), because R also includes pedestrians, whose V2X position noise is 2 m.

**Re-fitted calibration** (`results/calibration.json`): a = 4.399, b = 1.142; held-out ECE 0.162 → 0.031.

**Selection** (`results/policy_search_3gpp_gru.json`, selection seeds, 90 s per condition):

| Policy | J | Twin correct (all) | Syncs/s |
|---|---:|---:|---:|
| Fixed | 0.142 | 60.7% | 46.7 |
| b1 | 0.081 | 54.6% | 23.9 |
| b2 | 0.085 | 54.4% | 26.8 |
| b3 | 0.077 | 54.3% | 14.5 |
| c9 | 0.196 | 59.0% | 68.4 |
| AoI 0.2 s | 0.222 | 74.7% | 293.8 |
| AoI 0.35 s | 0.176 | 69.9% | 195.4 |
| AoI 0.5 s | 0.144 | 68.4% | 120.8 |
| AoI 0.8 s | 0.159 | 61.5% | 64.9 |

- **Table:** no trust-driven table meets the accuracy rule, so **b1 is kept** (b1–b3 are within run-to-run noise of each other).
- **AoI baseline:** the threshold with the lowest J, **0.5 s**, is the main AoI baseline. It also meets the accuracy rule.

**Repeated runs** (3 seed sets × 8 conditions × 150 s; 95% CIs by Student's t over the sets):

| Policy (GRU predictor) | J | Vehicle twin correct | Vehicle error | Syncs/s | Energy E | Info age L | Overhead O |
|---|---:|---:|---:|---:|---:|---:|---:|
| **TwinTrust-AP (b1)** | **0.083** | 78.6% | 0.83 m | **30.6** | **0.249** | 0.418 | **0.068** |
| Fixed (H 5, sync + sweep every 1 s) | 0.139 | 85.8% | 0.68 m | 44.5 | 0.372 | 0.558 | 0.100 |
| AoI threshold 0.5 s | 0.142 | 88.5% | 0.58 m | 116.0 | 0.456 | 0.405 | 0.257 |
| AoI threshold 0.2 s | 0.209 | 88.7% | 0.58 m | 278.9 | 0.658 | 0.262 | 0.623 |

| TwinTrust-AP − other | ΔJ | Δ vehicle twin correct | Δ syncs/s | Δ energy E |
|---|---|---|---|---|
| vs fixed | −0.055 [−0.076, −0.034] | −7.2 points [−8.4, −5.9] | −13.9 [−27.6, −0.1] | −0.122 [−0.147, −0.098] |
| vs AoI 0.5 s | −0.058 [−0.081, −0.036] | −9.8 points [−13.9, −5.8] | −85.4 [−98.3, −72.4] | −0.206 [−0.226, −0.187] |

**GRU vs dead reckoning, in the loop** (same seeds; `PRED=ctrv`):

| Policy | Vehicle twin correct GRU / CTRV | Vehicle error GRU / CTRV | Δ error [95% CI] |
|---|---:|---:|---|
| TwinTrust-AP | 78.6% / 77.0% | 0.83 / 0.92 m | −0.085 m [−0.168, −0.003] |
| Fixed | 85.8% / 83.8% | 0.68 / 0.78 m | −0.097 m [−0.261, +0.067] |

**How to read this:**

- **Cost.** TwinTrust-AP lowers J by 40% against the fixed policy and by 41% against the AoI baseline. Both intervals exclude 0.
- **Resources.** It sends 31% fewer synchronisations than the fixed policy (30.6 vs 44.5 per second; the interval just excludes 0) and 74% fewer than AoI 0.5 s. Modelled energy is 33% lower than fixed and 45% lower than AoI 0.5 s. Information age is 25% lower than fixed and about equal to AoI 0.5 s. It sweeps beams more often (4.1 vs 1.0 per second).
- **Accuracy.** The twin is correct 7 points less often than with the fixed policy and 10 points less than AoI 0.5 s. **The accuracy rule is not met.** This is the price of the lower cost.
- **GRU.** Offline it cuts the prediction error by 55–62%. In the loop the vehicle error falls by about 0.09 m for both policies; that interval excludes 0 only for TwinTrust-AP. The correctness gain (+1.6 and +2.0 points) is within noise. In the loop the error is dominated by information that arrives late or not at all (NLOS links, latency, the horizon cap), not by the predictor.
- **Where TwinTrust-AP loses.** Under latency and loss + latency its accuracy drops most (61% vs 70% and 62% vs 76% overall). This is the known short-horizon-under-delay limitation.
- **Low LiDAR accuracy.** Correctness is about 8% for every policy under LiDAR degradation, because the reference sensor's 2.2 m noise fails the 1 m test.

Simulation only. 3GPP channel models, not a ray-traced (Sionna RT) or measured channel. Not yet experimentally verified beyond these runs.

