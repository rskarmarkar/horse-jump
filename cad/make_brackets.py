"""
Corner brackets (L + diagonal brace) for stiffening plywood joints.
    small:  50 x 50 mm legs
    long:  150 x 50 mm legs
Run:  python make_brackets.py      (needs trimesh + manifold3d)

PRINT: lay it on its big flat side (the L/triangle shape flat on the bed).
       No supports needed. 4 walls / 30–40% infill makes them very stiff.
"""
import os
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

T = 4.0          # leg + brace thickness
HOLE = 3.4       # M3 bolt or small wood screw
FILLET = 8.0     # solid fill in the inside corner

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
os.makedirs(OUT, exist_ok=True)


def union(*m):
    return trimesh.boolean.union(list(m), engine="manifold")


def bracket(leg_a, leg_b, width, brace_a, brace_b, holes_a, holes_b):
    """leg_a lies along X, leg_b along Y, both `width` deep in Z.
    brace runs from (brace_a, T) on leg_a to (T, brace_b) on leg_b."""
    a = box([leg_a, T, width]); a.apply_translation([leg_a / 2, T / 2, width / 2])
    b = box([T, leg_b, width]); b.apply_translation([T / 2, leg_b / 2, width / 2])

    p1 = np.array([brace_a, T / 2]); p2 = np.array([T / 2, brace_b])
    d = p2 - p1
    length = np.linalg.norm(d) + 2 * T
    s = box([length, T, width])
    s.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(d[1], d[0]), [0, 0, 1]))
    mid = (p1 + p2) / 2
    s.apply_translation([mid[0], mid[1], width / 2])

    f = box([FILLET * 1.414, FILLET * 1.414, width])          # 45° square → corner fillet
    f.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 4, [0, 0, 1]))
    f.apply_translation([T, T, width / 2])

    body = union(a, b, s, f)
    keep = box([leg_a, leg_b, width]); keep.apply_translation([leg_a / 2, leg_b / 2, width / 2])
    body = trimesh.boolean.intersection([body, keep], engine="manifold")

    cuts = []
    for x in holes_a:   # through leg_a (along Y)
        c = cylinder(radius=HOLE / 2, height=T * 4, sections=48)
        c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        c.apply_translation([x, T / 2, width / 2]); cuts.append(c)
    for y in holes_b:   # through leg_b (along X)
        c = cylinder(radius=HOLE / 2, height=T * 4, sections=48)
        c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
        c.apply_translation([T / 2, y, width / 2]); cuts.append(c)
    if not cuts:
        return body
    return trimesh.boolean.difference([body, union(*cuts) if len(cuts) > 1 else cuts[0]],
                                      engine="manifold")


def save(mesh, name):
    mesh.export(os.path.join(OUT, name))
    s = mesh.bounds[1] - mesh.bounds[0]
    print(f"{name:26s} {s[0]:6.1f} x {s[1]:6.1f} x {s[2]:5.1f} mm  watertight={mesh.is_watertight}")


if __name__ == "__main__":
    save(bracket(50, 50, 15, brace_a=34, brace_b=34,
                 holes_a=[18, 44], holes_b=[18, 44]), "bracket_50x50.stl")
    save(bracket(50, 50, 15, brace_a=34, brace_b=34,
                 holes_a=[], holes_b=[]), "bracket_50x50_15mm_noholes.stl")
    save(bracket(30, 30, 5, brace_a=21, brace_b=21,
                 holes_a=[], holes_b=[]), "bracket_30x30_5mm_noholes.stl")
    save(bracket(150, 50, 20, brace_a=130, brace_b=42,
                 holes_a=[25, 75, 144], holes_b=[16, 30]), "bracket_150x50.stl")
