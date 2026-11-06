"""Minimal Sionna RT V2I check: one fixed RSU + one receiver on a simple
box-building street-canyon tile at 30 GHz, a PathSolver LoS/path result,
and a small RadioMapSolver map.

Run from this folder's isolated venv (see README.md):
    .venv/Scripts/python.exe run_v2i_check.py

Known blocker on this machine (documented in README.md): sionna.rt needs a
CUDA, Metal, or LLVM-JIT Dr.Jit backend. There is no GPU here and no
system LLVM-C.dll, so `import sionna.rt` itself fails before any of the
code below runs -- see README.md "Blocker" section for the exact
traceback and how to fix it elsewhere.
"""

from __future__ import annotations

import os

from make_meshes import generate_all

MESH_OBJECTS = generate_all()


def main() -> None:
    import mitsuba as mi
    import sionna.rt as rt

    scene = rt.load_scene(None)  # empty scene, built entirely from our own meshes
    scene.frequency = 30e9  # 30 GHz, matches the project's stated mmWave band

    concrete = rt.ITURadioMaterial("concrete-material", "concrete", thickness=0.2)
    objects = []
    for obj in MESH_OBJECTS:
        so = rt.SceneObject(fname=obj["fname"], name=obj["name"], radio_material=concrete)
        objects.append(so)
    scene.edit(add=objects)

    # One fixed RSU (6 m lamp-post height) and one V2I receiver (1.5 m, vehicle
    # height) on the road that crosses between the four corner buildings.
    scene.tx_array = rt.PlanarArray(
        num_rows=1, num_cols=1, vertical_spacing=0.5, horizontal_spacing=0.5,
        pattern="tr38901", polarization="V",
    )
    scene.rx_array = rt.PlanarArray(
        num_rows=1, num_cols=1, vertical_spacing=0.5, horizontal_spacing=0.5,
        pattern="iso", polarization="V",
    )

    rsu = rt.Transmitter(name="rsu", position=mi.Point3f(0.0, -40.0, 6.0))
    scene.add(rsu)
    vehicle = rt.Receiver(name="vehicle", position=mi.Point3f(0.0, 10.0, 1.5))
    scene.add(vehicle)
    rsu.look_at(vehicle)

    print("Running PathSolver ...")
    path_solver = rt.PathSolver()
    paths = path_solver(scene, max_depth=3, los=True, specular_reflection=True)
    print("PathSolver result:", paths)

    print("Running RadioMapSolver ...")
    rm_solver = rt.RadioMapSolver()
    radio_map = rm_solver(scene, cell_size=(2.0, 2.0), samples_per_tx=1_000_000)
    print("RadioMap path_gain shape:", radio_map.path_gain.shape)

    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)
    import numpy as np
    np.save(os.path.join(out_dir, "path_gain.npy"), np.array(radio_map.path_gain))
    print(f"Saved {out_dir}/path_gain.npy")


if __name__ == "__main__":
    main()
