# Aegis-V2X Live Drive

**Aegis-V2X: A Calibrated Trust-Driven Autonomic Framework for Joint Prediction, Synchronization and Beam Adaptation in Digital Twin-Assisted 6G V2X Networks**

Live demo: https://logapriya05.github.io/aegis-v2x-live-drive/

A playable, browser-based demonstration of the **Aegis-V2X** project (B.Tech research project, Hindustan University, targeting IEEE PerCom 2027). You drive an ego vehicle through an endless city. Beside the road view, a live **digital twin** is rebuilt only from V2X messages and LiDAR. The page also shows a **Trust Score**, lane monitoring, collision prediction and V2X communication in real time.

It is a single self-contained page (`index.html`) with no build step and no backend. The `research/` folder holds the algorithm source, the tests and the scripts that produced the calibration and the FSDP table.

## Run it

- **Online:** enable GitHub Pages for this repository (Settings → Pages → Deploy from branch → `main` / root) and open the URL GitHub shows.
- **Locally:** open `index.html` in a recent desktop browser (Chrome, Edge or Firefox). A GPU is recommended because the page draws two 3D views.

## Controls

| Key | Action |
|---|---|
| W / S or ↑ / ↓ | Accelerate / brake, then reverse |
| A / D or ← / → | Steer (turn at any junction to enter a different district) |
| Space | Handbrake |
| P | Pause / resume |
| C | Camera |
| T | Time of day |
| Y | Weather (sunny, rainy, snowfall, autumn, cherry blossom, foggy) |
| M | Engine sound |
| N | Alert sounds |
| H | Show or hide controls |
| 1–5 | Faults: spoof a vehicle, 60% packet loss, LiDAR degradation, +300 ms latency, erratic driver |
| 0 | Clear all faults |

On phones and tablets, on-screen GAS / BRK / ◀ ▶ buttons appear. A Split / Road / Twin switcher appears in portrait mode.

Live: https://logapriya05.github.io/aegis-v2x-live-drive/

## What is shown

- **Physical layer:** the simulated world, including traffic, pedestrians, signals and the Hindustan University district.
- **Digital twin:** the same camera view, but other road users are placed only from received V2X messages (V2V, V2I, V2P, V2E) and the ego's LiDAR, with real latency, packet loss and noise.
- **TwinTrust-AP (new tab):** the project's own algorithms run live at 10 Hz, using evidence the demo produces as you drive:
  - **Calibrated Twin Trust Estimator:** compares each twin object with where the ego's LiDAR sees it, then computes `T = σ(a·raw + b)` with `raw = 0.20q − 0.35e − 0.25u − 0.20a` (e prediction error, u error spread, a information age, q link quality). The Platt parameters a and b were fitted on recorded cycles.
  - **Criticality C:** the weighted sum of closing speed, blocked links, information age, channel loss and traffic density.
  - **GDCA authority A = exp(−½z²)**, from per-object residuals against their robust spread.
  - **TAHS:** sets the prediction horizon H from T, C and A.
  - **GRU twin predictor:** each V2X vehicle's position is predicted from its last 8 messages by a trained GRU (Vaishnavi's `GRUPredictor` architecture), up to the horizon H.
  - **3GPP mmWave V2V channel:** TR 37.885 path loss, vehicle and building blockage and shadowing, with the TR 38.901 beam pattern; misaligned beams lose gain until the next beam sweep.
  - **FSDP:** a 3 × 3 table (trust bin × criticality bin) that picks one of six actions: synchronize, predict, beam switch, reduce horizon, increase horizon, maintain state.
  - **Joint beam adaptation:** in the same cycle, the beam is switched when buildings block at least 5% of V2V links, so prediction, synchronisation and beam are decided together.
  - **Baselines:** a switch selects TwinTrust-AP, the fixed policy (horizon 5, edge sync every 1 s) or the age-of-information baseline (sync when the mean information age exceeds 0.5 s), so the resource use and twin accuracy can be compared live.
  - **mmWave band:** a second switch sets the V2V carrier to 15, 30 or 100 GHz (6G candidate bands).
  - **Recorded results:** a card shows J, syncs per second and twin correctness for the three policies in each band (3 seed sets), including the accuracy cost of TwinTrust-AP.
- **Trust Score (0–100):** how much the vehicle can trust its situation right now. Six hazards are combined: collision risk (time-to-collision), a pedestrian ahead, a red light needing hard braking, close following, lane status and **low twin trust**. The twin term is `r_twin = 0.6 × clamp((0.6 − T)/0.6, 0, 1)`, so a reliable twin (T ≥ 0.6) costs nothing:

  `Trust Score = 5 + 95 × (1 − r_coll)(1 − r_ped)(1 − r_signal)(1 − r_headway)(1 − r_lane)(1 − r_twin)`

  - It is 100 with no danger, and about 5 in extreme danger.
  - It is 0 only at an actual collision, then recovers over about 10 s.
  - "Driving safety" in the card is the same score without the twin term.
  - The full definition is in the comment above `updateTrustScores` in `index.html`.
- **Lane monitor:** GREEN / YELLOW / RED for every vehicle, based on road geometry, position, heading and lane-change state.
- **V2X message trust:** a per-sender reliability value (checked against LiDAR), shown in the V2X tab.

## Limitations (please read before presenting)

- Everything is simulated in the browser. It is not connected to CARLA, SUMO, Sionna RT or the project backend.
- The TwinTrust-AP formulas are Vaishnavi's Python code (copied unchanged into `research/aegis_ai/`), ported to JavaScript and checked case by case (`research/tests/`). The evidence that feeds them, the calibration and the FSDP table come from **this simulated city**, not from CARLA or real vehicles.
- The FSDP table was chosen as the lowest-cost table that keeps the twin as accurate as the fixed policy. No candidate met that in every condition; the closest one was chosen.
- Final configuration (see `research/README.md` section 10): 3GPP TR 37.885 mmWave V2V channel with the TR 38.901 beam pattern, a trained GRU twin predictor (Vaishnavi's `GRUPredictor`), age bridging (prediction stays on, horizon at least the information age) and twin-aided beam tracking.
- Against a fixed policy and an age-of-information baseline (Kaul et al. 2012; Sun et al. 2017), over 3 seed sets in each 6G candidate band (15 / 30 / 100 GHz), TwinTrust-AP has the lowest J (−58% / −60% / −30% against the fixed policy) and the fewest synchronisations (−64% / −60% / −36%). Its twin is as accurate as the age-of-information baseline, which syncs 4–7 times as often, and more accurate than the fixed policy. The table and calibration were chosen at 30 GHz and not re-tuned. Seeded runs are statistically repeatable, not bit-identical.
- The channel is a 3GPP statistical mmWave model on the simulated geometry, not a ray-traced (Sionna RT) or measured channel. See `research/README.md`.
- The weights of the Trust Score's hazard terms and the evidence scales (3 m error, 1 s age, 300 ms latency) are design choices, not fitted values.
- Weather changes visuals and the reported road friction only. Vehicle dynamics do not change with weather.
- Collision risk is evaluated only while the ego is moving. Being hit from behind while stationary is not modelled.

## Team

Vaishnavi (Research Lead), Haridharani (Simulation & Scenarios), Logapriya (Software Engineering), Khushi (Edge AI & Deployment).
