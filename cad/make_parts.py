"""
Generates the 3D-printed parts for HORSE JUMP as STL files (all units mm).

Edit the numbers in PARAMETERS, then re-run:
    python make_parts.py
Needs:  pip install trimesh manifold3d numpy
"""
import os
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

# ---------------- PARAMETERS ----------------
DRUM_D       = 50.0   # pulley diameter where the belt rides
FACE_W       = 28.0   # pulley width (belt is ~25 mm)
FLANGE_D     = 58.0   # rim diameter that keeps the belt on
FLANGE_T     = 2.0
GRIP_RIBS    = 24     # small ridges on the drive pulley so the belt doesn't slip

# Motor shaft (measure yours with calipers!)
SHAFT_D      = 5.5    # round part of the shaft
DD_FLATS     = 3.7    # "double-D" (TT yellow motors): distance across the two flats
D_FLAT       = 4.6    # single "D" shaft: distance from flat to far side (for 5.5 shaft)
FIT          = 0.3    # extra clearance (0.2 was slightly tight on the DD shaft)

IDLER_BORE   = 5.5    # M5 bolt (use 6.8 for a 1/4" dowel)

FENCE_W      = 24.0   # across the belt
FENCE_H      = 30.0
FENCE_BASE_D = 6.0    # along the belt — keep small so the belt can bend around pulleys
POST         = 4.0

HOLDER_HOLE  = 5.3    # 5 mm LED / 5 mm LDR
TUBE_LEN     = 15.0   # light shield tube
SCREW_HOLE   = 3.4    # M3 or small wood screws
# --------------------------------------------

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
os.makedirs(OUT, exist_ok=True)
SEG = 96


def cyl(d, h, z0=0.0, seg=SEG):
    c = cylinder(radius=d / 2, height=h, sections=seg)
    c.apply_translation([0, 0, z0 + h / 2])
    return c


def at(mesh, x=0, y=0, z=0):
    mesh.apply_translation([x, y, z])
    return mesh


def union(*m):
    return trimesh.boolean.union(list(m), engine="manifold")


def diff(a, *b):
    return trimesh.boolean.difference([a, *b], engine="manifold")


def pulley_body(ribs=0):
    total = FACE_W + 2 * FLANGE_T
    parts = [
        cyl(FLANGE_D, FLANGE_T, 0),
        cyl(DRUM_D, FACE_W, FLANGE_T),
        cyl(FLANGE_D, FLANGE_T, FLANGE_T + FACE_W),
    ]
    for i in range(ribs):
        a = 2 * np.pi * i / ribs
        r = box([1.6, 1.6, FACE_W])
        r.apply_transform(trimesh.transformations.rotation_matrix(a + np.pi / 4, [0, 0, 1]))
        at(r, (DRUM_D / 2) * np.cos(a), (DRUM_D / 2) * np.sin(a), FLANGE_T + FACE_W / 2)
        parts.append(r)
    return union(*parts), total


def d_bore(kind, h):
    """Cutting tool for the motor shaft hole."""
    d = SHAFT_D + FIT
    hole = cyl(d, h + 2, -1)
    if kind == "round":
        return hole
    if kind == "DD":
        keep = box([DD_FLATS + FIT, d + 2, h + 2])
        return trimesh.boolean.intersection([hole, at(keep, 0, 0, h / 2)], engine="manifold")
    if kind == "D":
        w = D_FLAT + FIT
        keep = box([w, d + 2, h + 2])
        at(keep, -d / 2 + w / 2, 0, h / 2)
        return trimesh.boolean.intersection([hole, keep], engine="manifold")
    raise ValueError(kind)


def drive_pulley(kind):
    body, h = pulley_body(GRIP_RIBS)
    return diff(body, d_bore(kind, h))


def idler_pulley():
    body, h = pulley_body(0)
    return diff(body, cyl(IDLER_BORE, h + 2, -1))


def fence():
    base = at(box([FENCE_W, FENCE_BASE_D, 1.6]), 0, 0, 0.8)
    xs = FENCE_W / 2 - POST / 2
    p1 = at(box([POST, POST, FENCE_H]), -xs, 0, FENCE_H / 2)
    p2 = at(box([POST, POST, FENCE_H]), xs, 0, FENCE_H / 2)
    r1 = at(box([FENCE_W, 2.5, 3]), 0, 0, FENCE_H - 1.5)
    r2 = at(box([FENCE_W, 2.5, 3]), 0, 0, FENCE_H * 0.5)
    return union(base, p1, p2, r1, r2)


def beam_holder():
    """Screws flat to a wall; tube points across the belt. Print flange-down."""
    flange = at(box([32, 20, 3]), 0, 0, 1.5)
    tube = cyl(11, TUBE_LEN, 3)
    body = union(flange, tube)
    cuts = [cyl(HOLDER_HOLE, TUBE_LEN + 10, -1),
            at(cyl(SCREW_HOLE, 10, -1, 32), -11.5, 0, 0),
            at(cyl(SCREW_HOLE, 10, -1, 32), 11.5, 0, 0)]
    return diff(body, *cuts)


def shaft_test():
    """Three tiny rings to find which bore fits your motor (print in ~5 min).
    Notches on the outside: 1 = round, 2 = DD, 3 = D."""
    rings = []
    for i, kind in enumerate(["round", "DD", "D"]):
        r = diff(cyl(14, 6, 0), d_bore(kind, 6))
        for n in range(i + 1):
            a = np.pi / 2 + (n - i / 2) * 0.45
            notch = at(box([2, 2, 8]), 7 * np.cos(a), 7 * np.sin(a), 3)
            r = diff(r, notch)
        rings.append(at(r, (i - 1) * 18, 0, 0))
    return union(*rings)


def save(mesh, name):
    path = os.path.join(OUT, name)
    mesh.export(path)
    b = mesh.bounds
    size = b[1] - b[0]
    print(f"{name:28s} {size[0]:6.1f} x {size[1]:6.1f} x {size[2]:6.1f} mm"
          f"   watertight={mesh.is_watertight}")
    return mesh


if __name__ == "__main__":
    save(drive_pulley("DD"), "drive_pulley_DD_shaft.stl")
    save(drive_pulley("D"), "drive_pulley_D_shaft.stl")
    save(drive_pulley("round"), "drive_pulley_round_shaft.stl")
    save(idler_pulley(), "idler_pulley_M5.stl")
    save(fence(), "fence.stl")
    f = fence()
    save(union(*[at(f.copy(), 0, i * 12, 0) for i in range(4)]), "fences_x4.stl")
    save(beam_holder(), "beam_holder.stl")
    save(shaft_test(), "shaft_test_rings.stl")


# ---- idler with taller banks (flanges) so the belt can't ride off ----
TALL_FLANGE_D = 68.0   # 9 mm tall banks above the drum (was 58 → 4 mm)
TALL_FLANGE_T = 2.0    # keep total width 32 so it still fits the printed idler axle


def idler_pulley_tall():
    global FLANGE_D, FLANGE_T
    old = FLANGE_D, FLANGE_T
    FLANGE_D, FLANGE_T = TALL_FLANGE_D, TALL_FLANGE_T
    try:
        return idler_pulley()
    finally:
        FLANGE_D, FLANGE_T = old


if __name__ == "__main__":
    save(idler_pulley_tall(), "idler_pulley_tall_banks.stl")
