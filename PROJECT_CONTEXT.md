# PROJECT_CONTEXT — Aegis-V2X

Read this first. It replaces re-analysing the whole project. Last updated: 2026-11-06.

## Title (project and paper)
**Aegis-V2X: A Calibrated Trust-Driven Autonomic Framework for Joint Prediction, Synchronization and Beam Adaptation in Digital Twin-Assisted 6G V2X Networks**
B.Tech project, Hindustan University, target IEEE PerCom 2027. Team: Vaishnavi (research lead), Haridharani, Logapriya, Khushi. Logapriya completed the minimal project covering all roles. The old 7-phase plan (CARLA, Sionna RT dataset, PointPillars, V2X-ViT, Jetson) was dropped for a minimal project.

## Status
Minimal project COMPLETE and verified. Both repos hold the same final version.

| Repo (local folder) | Role | Latest |
|---|---|---|
| `C:\Users\logap\aegis-v2x-live-drive` = github.com/Logapriya05/aegis-v2x-live-drive | Final project: live demo page + evaluation pipeline + results | 6141846 |
| `C:\Users\logap\Aegis-V2X` = fork Logapriya05/Aegis-V2X of upstream bossygirl-1818/Aegis-V2X | Team repo: Python reference (`ai/twintrust_ap/`), GRU, configs, tests, CI. Branch `latest-main` = upstream main 1894ec8 (PR #8). Checked-out branch `feature/logapriya-software-engineering` is OLD (25 Aug) and has uncommitted files (`backend/app/services/carla_ingestion.py`, its test, a docs file, Makefile) — do not discard them without asking | 1894ec8 |

PRs to upstream: #3 #4 #5 #6 #7 #8 merged; #1 (Phase 3 backend) closed, not merged.

## Architecture (demo, `index.html`, one self-contained page, three.js r128, GitHub Pages)
10 Hz TwinTrust-AP loop: V2X messages + LiDAR → evidence (twin error vs LiDAR, info age, loss, links) → Platt-calibrated trust T = σ(a·raw + b), a = 4.398645468120582, b = 1.1421320450667993 (ECE 0.162 → 0.031) → criticality C, GDCA authority → FSDP table b1 (low trust → synchronize, medium → beam_switch, high → increase_horizon) + TAHS horizon (1–10 × 0.1 s) → actions.
- **Age bridging** (`TTAP_CFG.AGE_FLOOR`): prediction always on, horizon ≥ mean information age.
- **Twin-aided beam tracking** (`TTAP_CFG.DT_BEAM`): beams steered to the twin's predicted vehicle positions between sweeps.
- **Twin predictor:** GRU (Vaishnavi's `GRUPredictor`, hidden 32, 6 horizons in one pass), weights embedded as `GRU_W`; JS port = PyTorch within 5e-6 m.
- **Channel:** 3GPP TR 37.885 V2V urban mmWave (LOS/NLOSv/NLOS, vehicle blockage, correlated shadowing), TR 38.901 beam pattern, link budget → PER. Bands 15/30/100 GHz (`CH.FC`).
- **Cost:** J = 0.25 L + 0.20 E + 0.20 O + 0.20 F − 0.15 R (lower is better). GRU prediction cost charged at H = 5.
- **UI:** drive controls, digital twin view, Trust Score (name fixed — do not rename), fault buttons, TwinTrust-AP tab, policy switch (TwinTrust-AP / fixed / age-of-information 0.5 s), band switch, Resource use, Recorded results, Trust calibration cards. Khushi's name stays in the city.
- **Monitoring (demo) tab** (added 2026-11-06): a Grafana-styled mock dashboard tab in `index.html` — 6 stat cards, 6 time-series charts (seeded random walk, own canvas renderer `monChart`), vehicle telemetry table, network health, active connections, recent events, a time-range selector (5m/15m/1h) and refresh/auto-refresh controls. Entirely self-contained demo data (`const MON=...`) — never reads the real simulation, backend, Prometheus or `research/results/`; the tab button and an in-panel banner both say "demo". Playwright-verified: renders, no console errors, all controls work, no horizontal overflow at 400px.
- **Headless:** `window.__aegis`, `fastForward`; `research/pipeline/collect.py` (Playwright) runs modes explore / twintrust / fixed / aoi; env SEED_OFF, AOI_THR, PRED, FC_GHZ, AGE_FLOOR, DT_BEAM, THREE_DIR.
- **Python reference:** `ai/twintrust_ap/` in the team repo (evidence, GDCA, TAHS, FSDP, `twin_adaptation.py`). `research/tests/check_embedded.py` checks the embedded JS core equals the tested port.
- **Live Grafana dashboard (optional, opt-in):** the demo pushes each 10 Hz TwinTrust-AP cycle (`ttap.T/C/H/action`) to the team repo's already-built Phase 3 FastAPI backend via `POST /api/v1/telemetry/live` (new, no DB write — just updates the existing Prometheus metrics in `backend/app/core/metrics.py`). Off by default so the public demo never needs a backend; enable with `?telemetry=1` on the demo URL (`&telemetryUrl=...` to override the default `http://localhost:8000`). Bring up the whole stack from the team repo root: `docker compose --profile backend --profile monitoring up --build` → Prometheus http://localhost:9090, Grafana http://localhost:3000 (admin/aegis, "Aegis-V2X Backend Overview" dashboard pre-provisioned). Backend `.env`/`config.py` CORS already allows `localhost:5500`, `localhost:5173/8000`, and the GitHub Pages origin. See `backend/README.md` "Live demo -> Grafana" in the team repo.

## Final results (3 seed sets × 8 conditions × 150 s; `research/README.md` section 10)
| Band | J TT / fixed / AoI | Syncs/s TT / fixed / AoI | Vehicle twin correct TT / fixed / AoI |
|---|---|---|---|
| 15 GHz | 0.055 / 0.132 / 0.139 | 16.0 / 44.4 / 113.7 | 89.0 / 87.5 / 89.0% |
| 30 GHz | 0.056 / 0.139 / 0.142 | 17.9 / 44.5 / 116.0 | 88.2 / 85.8 / 88.5% |
| 100 GHz | 0.101 / 0.145 / 0.147 | 28.4 / 44.7 / 119.3 | 88.4 / 82.3 / 86.4% |
Ablation 30 GHz: age bridging +7.8 points twin accuracy, beam tracking +1.1. Calibration ECE 0.04–0.05 on final runs.

## Rules and decisions
- Never fabricate results; anything not run = "not yet experimentally verified". Runs are statistically repeatable, not bit-identical.
- Claims allowed: lower J and fewer syncs without lower twin accuracy; evaluated across 6G candidate bands (15–100 GHz) with digital-twin-aided beam tracking; browser simulation with a 3GPP statistical channel. NOT: ray-traced/measured channel, THz, ISAC, CARLA, real vehicles, Jetson timing.
- Do not push directly to bossygirl-1818/Aegis-V2X: push to the fork Logapriya05/Aegis-V2X and open a PR.
- Never type or accept passwords or tokens. Do not modify, rename or delete existing files without the user's permission.
- The user (Logapriya) is a beginner: explain steps simply.

## Pending (in this order)
1. ~~Grafana live dashboard~~ — code done and pushed 2026-11-06 (team repo `feature/logapriya-software-engineering` @ commits 42bca32/3f55838 on the fork; live-drive `main` @ 6af7c0f). **Verification is partial, not full end-to-end**: with the real backend running locally (uvicorn + Postgres, no Docker available on this machine), `POST /api/v1/telemetry/live` was confirmed live to update `/metrics` correctly — that half is genuinely verified. Prometheus actually scraping and Grafana actually rendering the dashboard were **not** verified: Docker isn't installed here, and a Docker-free fallback (downloading the portable Prometheus/Grafana Windows binaries) was blocked by this sandbox's permission classifier before the binaries could be run. Needs the user to either install Docker and run `docker compose --profile backend --profile monitoring up --build` themselves, or grant permission to run locally-downloaded binaries in this environment.
2. Minimal Sionna RT check: BLOCKED 2026-11-06, see `research/sionna_rt_check/README.md`. `sionna.rt` 2.2.0 installs fine (no TensorFlow needed in this version) but hard-requires a CUDA/Metal/LLVM-JIT Dr.Jit backend with no CPU scalar fallback; this machine has no GPU and no system LLVM-C.dll. `run_v2i_check.py` (box buildings + ground, one RSU + one vehicle receiver, 30 GHz, PathSolver + RadioMapSolver) is written and ready but untested against real sionna.rt classes. Needs either a CUDA GPU machine, a Linux box with LLVM, or a system LLVM install (+`DRJIT_LIBLLVM_PATH`) before this can proceed — user decision. Then: ray-traced radio maps for fixed RSUs (V2I) at 30 GHz + Sionna-vs-3GPP comparison for sampled V2V pairs; re-run eval at 30 GHz.
3. ONNX export of GRU + decision loop, timing on Jetson Orin if Khushi has one. GRU half BLOCKED 2026-11-06, see team repo `ai/gru/README_onnx_export.md`: `requirements/ai.txt`'s pins (torch 2.5.1, onnx 1.17.0, onnxruntime 1.20.0, numpy 1.26.4) predate Python 3.13 wheel support and this machine has no C/C++ compiler to build from source. Export script + comparison test are written (`ai/gru/export_onnx.py`, `tests/unit/test_gru_onnx_export.py`, using the real trained weights extracted from `GRU_W`) but never run. Needs a Python 3.11/3.12 environment or a maintainer decision to bump the pins. Decision loop (FSDP/TAHS) export not started.
4. IEEE PerCom paper + college project report (templates not yet provided). Report doc: Claude Doc "Aegis-V2X Live Drive — Project Report".
