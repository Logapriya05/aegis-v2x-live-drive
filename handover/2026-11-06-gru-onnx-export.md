```text
AEGIS-V2X HANDOVER REPORT
Task: Start ONNX export validation for the trained GRU twin predictor only
Status: BLOCKED
What was done:
- Found the real GRU twin predictor exists only on upstream latest-main (ai/gru/model.py, ai/gru/train_twin_predictor.py) -- missing on feature/logapriya-software-engineering, which only had the abstract ai/gru/base.py stub
- Materialized ai/gru/model.py verbatim from latest-main (new file, not previously on this branch) and added the missing perception.gru_twin profile to configs/model.yaml (verbatim from latest-main; nothing else in that file touched)
- Extracted the real trained weights (GRU_W, embedded in the live-drive repo's index.html) verbatim into ai/gru/trained_weights/twin_gru_weights.json -- no retraining, shapes verified against the gru_twin profile (hidden 32, input_dim 5, 6 horizons)
- Wrote ai/gru/export_onnx.py: loads those exact weights into a real GRUPredictor, wraps train_twin_predictor.py's forward_all computation, exports via torch.onnx.export at opset 17
- Wrote tests/unit/test_gru_onnx_export.py: deterministic fixed-seed input, compares ONNX Runtime vs PyTorch, tolerance 5e-6 m (the exact bar research/tests/check_embedded.py already uses for JS-vs-PyTorch port parity in the live-drive repo, not an invented number) -- raw-tensor tolerance 5e-7 after /10 m scaling
- Tried installing requirements/ai.txt (torch==2.5.1, onnx==1.17.0, onnxruntime==1.20.0, numpy==1.26.4 via base.txt) in an isolated .venv at the repo root (gitignored): blocked -- documented below
Files changed: ai/gru/{model.py, export_onnx.py, README_onnx_export.md, trained_weights/twin_gru_weights.json} (all new); tests/unit/test_gru_onnx_export.py (new); configs/model.yaml (added perception.gru_twin only). Nothing in index.html, TwinTrust-AP decision logic, evaluation results, Grafana/backend files, or the Sionna RT check was touched.
Tests/checks: pip download --no-deps torch==2.5.1 -> no distribution for any platform (earliest compatible torch release is 2.6.0); pip install --dry-run -r requirements/ai.txt -> numpy==1.26.4 and onnx==1.17.0 have no Python-3.13 wheel and fail building from source (no C/C++ compiler on this machine: cl/gcc/clang all "file not found"). export_onnx.py and the test pass `python -m py_compile` but were never run (import torch fails immediately).
Results/numbers: none -- no ONNX model, no max-abs-diff, no pass/fail exists yet
Git: not committed (also still pending from the two prior tasks on this repo)
Problems / open questions:
- requirements/ai.txt's pins predate Python 3.13 wheel support across the board; not re-pinned here since it's a shared file ("owner: Vaishnavi") and the task said not to change unrelated dependencies -- needs either a Python 3.11/3.12 environment or a maintainer decision to bump the pins
- export_onnx.py / the test are believed correct against the documented forward_all computation but are completely unverified -- treat as ready-to-run, not working
Next suggested task: user decision -- either (a) provide a Python 3.11/3.12 environment (or approve bumping requirements/ai.txt's pins) to actually run the export+comparison, or (b) move to the IEEE PerCom paper + project report (pending item 4)
```
