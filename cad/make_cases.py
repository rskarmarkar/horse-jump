"""
Open-top trays for the electronics on the rear ledge (all mm).
    arduino_case.stl     Uno R3 (68.6 x 53.3): 4 screw posts, USB + power-jack openings, wire notches
    l298n_case.stl       L298N module (43 x 43): 4 screw posts, big notches for the screw terminals + pins
    breadboard_case.stl  half breadboard 82 x 55: snug pocket, wire notches on every wall
Every tray has 2 ear tabs with 3.4 mm holes to screw/bolt it to the base (or just hot-glue it).
PRINT: open side up, no supports. 3 walls, 20% infill.
Run:  python make_cases.py
"""
import os
import trimesh
from trimesh.creation import box, cylinder

WALL, FLOOR = 2.0, 2.0
FIT = 0.6            # gap around each board
POST_D, POST_HOLE = 6.0, 2.8   # 2.8 = M3 self-tapping / small wood screw
EAR_HOLE = 3.4

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")


def B(x0, x1, y0, y1, z0, z1):
    b = box([x1 - x0, y1 - y0, z1 - z0]); b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def C(d, x, y, z0, z1, seg=40):
    c = cylinder(radius=d / 2, height=z1 - z0, sections=seg); c.apply_translation([x, y, (z0 + z1) / 2])
    return c


def U(*m):
    return trimesh.boolean.union(list(m), engine="manifold")


def D(a, *b):
    return trimesh.boolean.difference([a, U(*b) if len(b) > 1 else b[0]], engine="manifold")


def tray(in_x, in_y, wall_h, posts=(), post_h=0.0, ears=True):
    """Tray whose INSIDE runs from (0,0) to (in_x,in_y); floor top at z=FLOOR."""
    outer = B(-WALL, in_x + WALL, -WALL, in_y + WALL, 0, FLOOR + wall_h)
    body = D(outer, B(0, in_x, 0, in_y, FLOOR, FLOOR + wall_h + 1))
    parts = [body]
    for (x, y) in posts:
        parts.append(C(POST_D, x, y, FLOOR - 0.01, FLOOR + post_h))
    if ears:
        for x in (-WALL - 10, in_x + WALL):
            parts.append(B(x, x + 10, in_y / 2 - 7, in_y / 2 + 7, 0, 3))
    body = U(*parts)
    cuts = [C(POST_HOLE, x, y, FLOOR, FLOOR + post_h + 1) for (x, y) in posts]
    if ears:
        cuts += [C(EAR_HOLE, -WALL - 5, in_y / 2, -1, 4), C(EAR_HOLE, in_x + WALL + 5, in_y / 2, -1, 4)]
    return D(body, *cuts) if cuts else body


def notch_x(x_center, width, y_wall, z_bottom, top):
    """Slot through a wall that runs along X (front/back wall at y = y_wall)."""
    return B(x_center - width / 2, x_center + width / 2, y_wall - 3, y_wall + 3, z_bottom, top + 1)


def notch_y(y_center, width, x_wall, z_bottom, top):
    return B(x_wall - 3, x_wall + 3, y_center - width / 2, y_center + width / 2, z_bottom, top + 1)


def arduino_case():
    # Uno R3 holes (board origin = lower-left, USB + power jack on the x=0 edge)
    holes = [(13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56)]
    off = FIT / 2
    post_h = 4.0
    in_x, in_y = 68.6 + FIT, 53.3 + FIT
    wall_h = 12.0
    top = FLOOR + wall_h
    pcb = FLOOR + post_h                       # bottom of the board
    t = tray(in_x, in_y, wall_h, [(x + off, y + off) for x, y in holes], post_h)
    cuts = [
        notch_y(37.7 + off, 14.0, -WALL / 2, pcb + 0.5, top),   # USB-B
        notch_y(7.6 + off, 11.0, -WALL / 2, pcb + 0.5, top),    # power jack
        notch_x(in_x * 0.30, 10.0, in_y + WALL / 2, pcb + 3, top),   # wire notches over the headers
        notch_x(in_x * 0.65, 10.0, in_y + WALL / 2, pcb + 3, top),
        notch_x(in_x * 0.45, 10.0, -WALL / 2, pcb + 3, top),
        notch_y(in_y / 2, 12.0, in_x + WALL / 2, pcb + 3, top),
    ]
    return D(t, *cuts)


def l298n_case():
    side, inset = 43.0, 3.0                    # check your board: holes ~3 mm in from each corner
    off = FIT / 2
    post_h = 4.0
    in_xy = side + FIT
    wall_h = 9.0
    top = FLOOR + wall_h
    pcb = FLOOR + post_h
    posts = [(inset + off, inset + off), (side - inset + off, inset + off),
             (inset + off, side - inset + off), (side - inset + off, side - inset + off)]
    t = tray(in_xy, in_xy, wall_h, posts, post_h)
    cuts = [
        notch_y(in_xy / 2, 20.0, -WALL / 2, pcb, top),          # motor A terminals
        notch_y(in_xy / 2, 20.0, in_xy + WALL / 2, pcb, top),   # motor B terminals
        notch_x(in_xy / 2, 30.0, -WALL / 2, pcb, top),          # power terminals + ENA/IN pins
        notch_x(in_xy / 2, 14.0, in_xy + WALL / 2, pcb + 1, top),
    ]
    return D(t, *cuts)


def breadboard_case(bx=82.0, by=55.0):
    in_x, in_y = bx + FIT, by + FIT
    wall_h = 8.0                               # breadboard is ~9.5 tall: walls stop below the top
    top = FLOOR + wall_h
    t = tray(in_x, in_y, wall_h)
    cuts = []
    for fx in (0.2, 0.5, 0.8):                 # 3 notches on each long wall
        cuts.append(notch_x(in_x * fx, 8.0, -WALL / 2, FLOOR + 3, top))
        cuts.append(notch_x(in_x * fx, 8.0, in_y + WALL / 2, FLOOR + 3, top))
    for fy in (0.3, 0.7):                      # 2 on each short wall (beside the ear tab)
        cuts.append(notch_y(in_y * fy, 8.0, -WALL / 2, FLOOR + 3, top))
        cuts.append(notch_y(in_y * fy, 8.0, in_x + WALL / 2, FLOOR + 3, top))
    return D(t, *cuts)


def save(mesh, name):
    mesh.export(os.path.join(OUT, name))
    s = mesh.bounds[1] - mesh.bounds[0]
    print(f"{name:22s} {s[0]:6.1f} x {s[1]:5.1f} x {s[2]:5.1f} mm  watertight={mesh.is_watertight}")


if __name__ == "__main__":
    save(arduino_case(), "arduino_case.stl")
    save(l298n_case(), "l298n_case.stl")
    save(breadboard_case(), "breadboard_case.stl")
