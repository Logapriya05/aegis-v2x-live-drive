"""Generates plain Wavefront .obj meshes for a minimal demo city tile:
one ground plane and a handful of box buildings, so the RT check does not
depend on any bundled Sionna scene asset. Run once before run_v2i_check.py.
"""

from __future__ import annotations

import os

MESH_DIR = os.path.join(os.path.dirname(__file__), "meshes")


def _write_obj(path: str, vertices: list[tuple[float, float, float]], faces: list[tuple[int, int, int]]) -> None:
    with open(path, "w") as f:
        for x, y, z in vertices:
            f.write(f"v {x} {y} {z}\n")
        for a, b, c in faces:
            f.write(f"f {a} {b} {c}\n")  # 1-indexed, per the .obj format


def write_box(path: str, center: tuple[float, float, float], size: tuple[float, float, float]) -> None:
    """A closed box mesh (12 triangles), `size` = (dx, dy, dz) full extents."""
    cx, cy, cz = center
    dx, dy, dz = (s / 2 for s in size)
    v = [
        (cx - dx, cy - dy, cz - dz), (cx + dx, cy - dy, cz - dz),
        (cx + dx, cy + dy, cz - dz), (cx - dx, cy + dy, cz - dz),
        (cx - dx, cy - dy, cz + dz), (cx + dx, cy - dy, cz + dz),
        (cx + dx, cy + dy, cz + dz), (cx - dx, cy + dy, cz + dz),
    ]
    faces = [
        (1, 2, 3), (1, 3, 4),  # bottom
        (5, 7, 6), (5, 8, 7),  # top
        (1, 5, 6), (1, 6, 2),  # sides
        (2, 6, 7), (2, 7, 3),
        (3, 7, 8), (3, 8, 4),
        (4, 8, 5), (4, 5, 1),
    ]
    _write_obj(path, v, faces)


def write_ground(path: str, size: tuple[float, float] = (120.0, 120.0)) -> None:
    """A flat ground plane (2 triangles) centred at the origin, z=0."""
    dx, dy = size[0] / 2, size[1] / 2
    v = [(-dx, -dy, 0.0), (dx, -dy, 0.0), (dx, dy, 0.0), (-dx, dy, 0.0)]
    faces = [(1, 2, 3), (1, 3, 4)]
    _write_obj(path, v, faces)


# Demo tile: a street-canyon-ish crossing with 4 buildings at the corners,
# each set back from the two roads (matching the live demo's own "buildings
# stand > 11 m from every road centreline" convention, see index.html TTAP_CFG
# comments) so there is a clear road LoS channel through the middle.
BUILDINGS = [
    {"name": "bldg-ne", "center": (25.0, 25.0, 9.0), "size": (30.0, 30.0, 18.0)},
    {"name": "bldg-nw", "center": (-25.0, 25.0, 9.0), "size": (30.0, 30.0, 18.0)},
    {"name": "bldg-se", "center": (25.0, -25.0, 9.0), "size": (30.0, 30.0, 18.0)},
    {"name": "bldg-sw", "center": (-25.0, -25.0, 9.0), "size": (30.0, 30.0, 18.0)},
]


def generate_all() -> list[dict]:
    os.makedirs(MESH_DIR, exist_ok=True)
    ground_path = os.path.join(MESH_DIR, "ground.obj")
    write_ground(ground_path)
    objects = [{"name": "ground", "fname": ground_path, "kind": "ground"}]
    for b in BUILDINGS:
        path = os.path.join(MESH_DIR, f"{b['name']}.obj")
        write_box(path, b["center"], b["size"])
        objects.append({"name": b["name"], "fname": path, "kind": "building"})
    return objects


if __name__ == "__main__":
    objs = generate_all()
    print(f"Wrote {len(objs)} meshes to {MESH_DIR}")
