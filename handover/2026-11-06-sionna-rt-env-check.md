```text
AEGIS-V2X HANDOVER REPORT
Task: Establish the minimal Sionna RT 30 GHz environment and generate one test radio map
Status: BLOCKED
What was done:
- Confirmed the pip install (sionna 2.2.0, sionna-rt 2.2.0, mitsuba 3.9.1, drjit 1.5.0, torch 2.15.0 CPU) completed with exit code 0 in the isolated venv
- Wrote research/sionna_rt_check/run_v2i_check.py: empty scene via load_scene(None), 4 box buildings + ground from make_meshes.py as SceneObjects via scene.edit(add=...), scene.frequency=30e9, one fixed RSU Transmitter + one vehicle Receiver, PathSolver then RadioMapSolver -- API confirmed against current nvlabs.github.io/sionna/rt docs
- Ran it: fails inside `import sionna.rt` itself, before any scene/mesh code executes -- captured verbatim in research/sionna_rt_check/run_output.txt
- Root cause confirmed by reading the installed package: sionna.rt 2.2.0 hard-requires a CUDA, Metal, or LLVM-JIT Dr.Jit backend (no scalar/CPU fallback). This machine has no GPU (no nvidia-smi) and no system LLVM-C.dll anywhere (searched Program Files/ProgramData, no Rust toolchain, no llvmlite) -- confirmed via mitsuba.variants() and a filesystem search
- Added research/sionna_rt_check/README.md documenting the exact blocker, reproduction steps, and the 3 ways to unblock it (install system LLVM + DRJIT_LIBLLVM_PATH, use a CUDA GPU machine, or use Linux) -- none attempted, since all are outside this isolated-venv/folder scope
Files changed: research/sionna_rt_check/{README.md, make_meshes.py, run_v2i_check.py, .gitignore, run_output.txt} (all new); research/sionna_rt_check/.venv/ and meshes/*.obj and out/ are gitignored. Nothing outside research/sionna_rt_check/ was touched this task.
Tests/checks: .venv/Scripts/python.exe run_v2i_check.py -> ImportError at `import sionna.rt` (LLVM-C.dll not found), captured in run_output.txt. make_meshes.py -> 5 .obj files written successfully (verified independently of Sionna).
Results/numbers: none -- no radio map, path gain, or LoS result exists. research/README.md's existing "no Sionna RT" claims are unchanged.
Git: not committed (also still pending from the two prior tasks on this repo)
Problems / open questions:
- Unblocking needs either a system LLVM install (admin-level, outside this folder) or a CUDA-capable GPU machine -- a real decision for the user, not something to do unprompted
- run_v2i_check.py's sionna.rt calls are written against the docs but not yet exercised against the real classes, since import fails first -- treat it as the ready-to-run next step once a backend is available, not as verified-working code
Next suggested task: user decision -- either (a) provide/point to a CUDA GPU or a Linux box with LLVM to unblock and finish this check, or (b) skip Sionna RT for now and move to ONNX export of GRU + decision loop (pending item 3)
```
