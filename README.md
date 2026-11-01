# Aegis-V2X Live Drive

A playable, browser-based demonstration of the **Aegis-V2X** project (B.Tech research project, Hindustan University, targeting IEEE PerCom 2027). You drive an ego vehicle through an endless city. Beside the road view, a live **digital twin** is rebuilt only from V2X messages and LiDAR. The page also shows a **Trust Score**, lane monitoring, collision prediction and V2X communication in real time.

It is a single self-contained page (`index.html`) with no build step and no backend.

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

## What is shown

- **Physical layer:** the simulated world, including traffic, pedestrians, signals and the Hindustan University district.
- **Digital twin:** the same camera view, but other road users are placed only from received V2X messages (V2V, V2I, V2P, V2E) and the ego's LiDAR, with real latency, packet loss and noise.
- **Trust Score (0–100):** how safe the vehicle is right now. Five hazards are combined: collision risk (time-to-collision), a pedestrian ahead, a red light needing hard braking, close following, and lane status:

  `Trust Score = 5 + 95 × (1 − r_coll)(1 − r_ped)(1 − r_signal)(1 − r_headway)(1 − r_lane)`

  - It is 100 with no danger and about 5 in extreme danger.
  - It is 0 only at an actual collision, then recovers over about 10 s.
  - The full definition is in the comment above `updateTrustScores` in `index.html`.
- **Lane monitor:** GREEN / YELLOW / RED for every vehicle, based on road geometry, position, heading and lane-change state.
- **V2X message trust:** a per-sender reliability value (checked against LiDAR), shown in the V2X tab.

## Limitations (please read before presenting)

- Everything is simulated in the browser. It is not connected to CARLA, SUMO, Sionna RT or the project backend.
- The Trust Score is a **demonstration heuristic** built on the simulator's own safety metrics. It is not the GDCA research formula and is not calibrated on real data; the weights are design choices.
- Weather changes visuals and the reported road friction only. Vehicle dynamics do not change with weather.
- Collision risk is evaluated only while the ego is moving. Being hit from behind while stationary is not modelled.

## Team

Vaishnavi (Research Lead), Haridharani (Simulation & Scenarios), Logapriya (Software Engineering), Khushi (Edge AI & Deployment).
