"""
HORSE LINKAGE — the servo no longer sits at the arm's pivot.

    servo -> short CRANK -> LINK -> long ROCKER ARM (turns on its own fixed pin) -> horse axle in the slot

Parts (all mm):
  linkage_bracket.stl   plugs into the OLD servo cutout of the laser-cut servo mount (pivot pin sits
                        exactly where the old servo shaft was) and reaches past the plate edge to
                        hold the NEW servo.
  rocker_arm.stl        pivot hole -> link pin at 62 -> horse-axle hole at 120.5 (10 mm longer than
                        the old 110 arm; the hole is 2 mm long so it follows the slot)
  link.stl              50 mm between holes
  servo_crank.stl       screws/glues on top of the SG90's own horn; pin at 24 mm
  linkage_caps.stl      1 big cap (pivot) + 3 small caps (pins)
  horse_axle_for_linkage.stl + horse_axle_spacer_linkage.stl   straight axle (no crank link needed)

Coordinates below: x, z = the same "front view" mm as the laser files; h = distance in front of the
BACK face of the servo-mount plate (plate is h 0..3, back panel's rear face is at h = 23).
Run:  python make_linkage.py
"""
import math, os
import numpy as np
import trimesh
from trimesh.creation import box, cylinder
from make_axles import axle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# ---------- where things are ----------
SLOT_C, SLOT_R = (94.0, 177.0), 110.0     # slot arc in the back panel
P = (83.0, 177.0)        # arm pivot = where the old servo shaft actually was (10–11 mm short of design)
ARM_L = 120.5            # pivot -> horse axle
ARM_PIN = 62.0           # pivot -> link pin
LINK_L = 50.0
CRANK_R = 24.0
S = (169.0, 124.5)       # new servo shaft
REST_SLOT_DEG, UP_SLOT_DEG = -15.0, 10.0   # horse positions along the slot (same as before)

T = 4.0                  # arm / link / crank thickness
BR_T = 4.0               # bracket plate thickness
ARM_H = 8.0              # arm + crank underside height (h); link rides on top of both
PIN_D, PIN_HOLE = 4.0, 4.4
PIVOT_D, PIVOT_HOLE = 7.0, 7.3


def B(x0, x1, y0, y1, z0, z1):
    b = box([x1 - x0, y1 - y0, z1 - z0]); b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return b


def C(d, x, y, z0, z1, seg=48):
    c = cylinder(radius=d / 2, height=z1 - z0, sections=seg); c.apply_translation([x, y, (z0 + z1) / 2]); return c


def U(*m):
    return trimesh.boolean.union(list(m), engine="manifold")


def D(a, *b):
    return trimesh.boolean.difference([a, U(*b) if len(b) > 1 else b[0]], engine="manifold")


def bar(length, width, t, z0=0.0):
    """Rounded-end bar from (0,0) to (length,0)."""
    return U(B(0, length, -width / 2, width / 2, z0, z0 + t),
             C(width, 0, 0, z0, z0 + t), C(width, length, 0, z0, z0 + t))


# ---------- kinematics ----------
def arm_angle_for_slot(deg):
    a = math.radians(deg)
    x, z = SLOT_C[0] + SLOT_R * math.cos(a), SLOT_C[1] + SLOT_R * math.sin(a)
    return math.atan2(z - P[1], x - P[0])


def crank_angle(theta):
    """Crank direction (rad, front view) that puts the link on the arm pin for arm angle theta."""
    ax, az = P[0] + ARM_PIN * math.cos(theta), P[1] + ARM_PIN * math.sin(theta)
    dx, dz = ax - S[0], az - S[1]
    d = math.hypot(dx, dz)
    base = math.atan2(dz, dx)
    off = math.acos((CRANK_R ** 2 + d ** 2 - LINK_L ** 2) / (2 * CRANK_R * d))
    return base + off        # the branch with the crank pin BELOW the arm pin


def report():
    tr, tu = arm_angle_for_slot(REST_SLOT_DEG), arm_angle_for_slot(UP_SLOT_DEG)
    cr, cu = crank_angle(tr), crank_angle(tu)
    cm = crank_angle((tr + tu) / 2)
    print(f"arm angle   rest {math.degrees(tr):6.1f}°   up {math.degrees(tu):6.1f}°   (swing {math.degrees(tu - tr):.1f}°)")
    print(f"crank angle rest {math.degrees(cr):6.1f}°   up {math.degrees(cu):6.1f}°   (swing {math.degrees(cr - cu):.1f}°)   mid {math.degrees(cm):.1f}°")
    print(f"servo.write with the crank put on at 90 = mid:  REST {90 + math.degrees(cr - cm):.0f}   UP {90 - math.degrees(cm - cu):.0f}")
    worst = 9
    for i in range(41):                     # axle vs slot centre line over the stroke
        th = tr + (tu - tr) * i / 40
        x, z = P[0] + ARM_L * math.cos(th), P[1] + ARM_L * math.sin(th)
        worst = min(worst, 1.0 - abs(math.hypot(x - SLOT_C[0], z - SLOT_C[1]) - SLOT_R))
    print(f"axle stays within the 2 mm-long arm hole: spare {worst:.2f} mm")
    print(f"servo torque needed = {CRANK_R / ARM_PIN * ARM_L / 110:.2f} x what the old direct-drive arm needed")


# ---------- parts ----------
def bracket():
    """Modelled in (x, z, h). Plate h -BR_T..0 lies on the BACK of the wooden servo mount."""
    plate = U(B(68, 182, 164, 190, -BR_T, 0),          # beam: over the old cutout, out past the plate edge (x=123.5)
              B(156, 182, 96, 190, -BR_T, 0))          # tab that holds the new servo
    key = B(77.1, 99.9, 170.7, 183.3, -0.01, 3.0)       # fills the old 23.2 x 13 servo cutout
    boss = C(11.5, P[0], P[1], -0.01, ARM_H - 0.3)       # arm rests on this shoulder
    pin = C(PIVOT_D, P[0], P[1], ARM_H - 0.31, ARM_H + T + 0.5 + 3.0)
    body = U(plate, key, boss, pin)
    sx, sz = S[0], S[1] - 5.5                            # servo body centre (shaft is 5.5 off centre)
    cuts = [B(sx - 6.4, sx + 6.4, sz - 11.6, sz + 11.6, -BR_T - 1, 1),      # SG90 body 12.8 x 23.2
            C(1.8, sx, sz - 13.75, -BR_T - 1, 1), C(1.8, sx, sz + 13.75, -BR_T - 1, 1),   # servo ear screws
            C(2.4, 88.5 - 13.75, 177, -BR_T - 1, 1), C(2.4, 88.5 + 13.75, 177, -BR_T - 1, 1),  # into the old ear holes
            B(sx + 6.3, sx + 9.5, sz - 11.6, sz - 6.6, -BR_T - 1, 1)]       # wire notch
    m = D(body, *cuts)
    m.apply_translation([-68, -96, BR_T])               # sit on the bed
    return m


def rocker_arm():
    body = bar(ARM_L + 1.0, 15, T)
    pin = C(PIN_D, ARM_PIN, 0, T - 0.01, T + 0.5 + T + 0.5 + 2.5)
    slot = U(B(ARM_L - 1, ARM_L + 1, -PIN_HOLE / 2, PIN_HOLE / 2, -1, T + 1),
             C(PIN_HOLE, ARM_L - 1, 0, -1, T + 1), C(PIN_HOLE, ARM_L + 1, 0, -1, T + 1))
    return D(U(body, pin), C(PIVOT_HOLE, 0, 0, -1, T + 1), slot)


def link():
    return D(bar(LINK_L, 10, T), C(PIN_HOLE, 0, 0, -1, T + 1), C(PIN_HOLE, LINK_L, 0, -1, T + 1))


def servo_crank():
    body = bar(CRANK_R, 12, T)
    pin = C(PIN_D, CRANK_R, 0, T - 0.01, T + 0.5 + T + 0.5 + 2.5)
    cuts = [C(6.0, 0, 0, -1, T + 1)] + [C(1.5, r, 0, -1, T + 1, 24) for r in (9, 14)]
    return D(U(body, pin), *cuts)


def caps():
    big = D(C(12, 0, 0, 0, 3), C(PIVOT_D + 0.2, 0, 0, -1, 4))
    small = [D(C(9, 16 + i * 12, 0, 0, 2.5), C(PIN_D + 0.2, 16 + i * 12, 0, -1, 4)) for i in range(3)]
    return U(big, *small)


def spacer(length):
    return D(C(9, 0, 0, 0, length), C(PIN_HOLE, 0, 0, -1, length + 1))


def save(mesh, name):
    mesh.export(os.path.join(OUT, name))
    s = mesh.bounds[1] - mesh.bounds[0]
    print(f"{name:32s} {s[0]:6.1f} x {s[1]:5.1f} x {s[2]:5.1f} mm  watertight={mesh.is_watertight}")


if __name__ == "__main__":
    report()
    save(bracket(), "linkage_bracket.stl")
    save(rocker_arm(), "rocker_arm.stl")
    save(link(), "link.stl")
    save(servo_crank(), "servo_crank.stl")
    save(caps(), "linkage_caps.stl")
    gap = 23.0 - (ARM_H + T)                              # arm top -> back panel rear face
    save(axle(4.0, 9.0, back_len=3 + gap + T + 0.5 + 3, collar_len=50.0, front_len=9.0), "horse_axle_for_linkage.stl")
    save(spacer(gap - 0.5), "horse_axle_spacer_linkage.stl")
