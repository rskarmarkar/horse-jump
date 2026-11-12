"""
Printed axles that replace the long M5 (idler) and M4 (horse) bolts.

Each axle = thin shaft | thick spacer collar | thin shaft, plus 2 glue-on end caps.
They print LYING DOWN (flat side on the bed) so the layers run along the rod —
that makes them much stronger than printing upright.

  idler_axle:  back shaft through the panel -> 19.5 mm collar -> pulley shaft
  horse_axle:  back shaft through arm + slot -> 50 mm collar -> horse shaft
Run:  python make_axles.py
"""
import os
import numpy as np
import trimesh
from trimesh.creation import cylinder, box

FLAT = 0.6        # how much is shaved off the bottom so it sits flat on the bed
CAP_T = 3.0
CAP_D = 11.0
GLUE_GAP = 0.2    # cap hole is this much bigger than the shaft (superglue it)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")


def union(*m):
    return trimesh.boolean.union(list(m), engine="manifold")


def seg(d, length, x0):
    c = cylinder(radius=d / 2, height=length, sections=64)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    c.apply_translation([x0 + length / 2, 0, 0])
    return c


def axle(shaft_d, collar_d, back_len, collar_len, front_len):
    parts = [seg(shaft_d, back_len + 0.01, 0),
             seg(collar_d, collar_len, back_len),
             seg(shaft_d, front_len + 0.01, back_len + collar_len - 0.01)]
    body = union(*parts)
    total = back_len + collar_len + front_len
    floor = -shaft_d / 2 + FLAT                      # flat at the bottom of the thin shaft
    keep = box([total + 2, 40, 40]); keep.apply_translation([total / 2, 0, floor + 20])
    body = trimesh.boolean.intersection([body, keep], engine="manifold")
    body.apply_translation([0, 0, -floor])
    return body


def caps(shaft_d, n=2):
    out = []
    for i in range(n):
        c = cylinder(radius=CAP_D / 2, height=CAP_T, sections=64)
        h = cylinder(radius=(shaft_d + GLUE_GAP) / 2, height=CAP_T + 2, sections=48)
        c = trimesh.boolean.difference([c, h], engine="manifold")
        c.apply_translation([i * (CAP_D + 4), 0, CAP_T / 2])
        out.append(c)
    return union(*out)


def crank_link(offset, arm_gap, t):
    """Flat plate (print it lying flat, peg up). Hole A takes the axle's back stub
    (glue). Peg B, `offset` away, goes back through the servo arm hole (glue + cap).
    The thick part of the peg fills the rest of the gap so the arm sits snug."""
    w = 9.0
    plate = box([offset + w, w, t]); plate.apply_translation([offset / 2, 0, t / 2])
    ends = [cylinder(radius=w / 2, height=t, sections=48) for _ in range(2)]
    ends[0].apply_translation([0, 0, t / 2]); ends[1].apply_translation([offset, 0, t / 2])
    spacer_len = arm_gap - 0.5 - t                      # remaining gap between link and arm
    thick = cylinder(radius=3.5, height=spacer_len, sections=48)
    thick.apply_translation([offset, 0, t + spacer_len / 2])
    pin_len = 3 + 0.5 + CAP_T                           # through the arm + cap
    pin = cylinder(radius=2.0, height=pin_len + 0.01, sections=48)
    pin.apply_translation([offset, 0, t + spacer_len + pin_len / 2 - 0.01])
    body = union(plate, *ends, thick, pin)
    hole = cylinder(radius=(4.0 + GLUE_GAP) / 2, height=t + 2, sections=48)
    hole.apply_translation([0, 0, t / 2])
    return trimesh.boolean.difference([body, hole], engine="manifold")


def save(mesh, name):
    mesh.export(os.path.join(OUT, name))
    s = mesh.bounds[1] - mesh.bounds[0]
    print(f"{name:24s} {s[0]:6.1f} x {s[1]:5.1f} x {s[2]:5.1f} mm  watertight={mesh.is_watertight}")


if __name__ == "__main__":
    # idler: 5.0 shaft fits the 5.3 panel hole and 5.5 pulley bore
    #   back = 3 panel + 3 cap ; collar = gap panel->pulley ; front = 32 pulley + 0.5 play + 3 cap
    save(axle(5.0, 10.0, back_len=6.0, collar_len=19.5, front_len=35.5), "idler_axle.stl")
    save(caps(5.0), "idler_axle_caps_x2.stl")
    # horse: 4.0 shaft fits the 4.3 holes and the 5 mm slot
    #   The servo-arm hole sits OFFSET (~10 mm) from the slot and ~10 mm behind the panel,
    #   so the axle gets a separate "crank link" behind the panel:
    #     main axle: back stub (3 panel + 0.5 + 4 link plate) | 50 collar | 6 horse + 3 cap
    #     crank link: plate with a hole for the stub, OFFSET away a peg that goes back into the arm
    ARM_GAP, OFFSET, LINK_T = 10.0, 10.0, 4.0
    save(axle(4.0, 9.0, back_len=3 + 0.5 + LINK_T + 10, collar_len=50.0, front_len=9.0), "horse_axle.stl")
    save(caps(4.0), "horse_axle_caps_x2.stl")
    save(crank_link(OFFSET, ARM_GAP, LINK_T), "horse_axle_crank_link.stl")
    save(crank_link(15.0, ARM_GAP, LINK_T), "horse_axle_crank_link_15mm.stl")
