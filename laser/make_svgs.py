"""
Laser-cut parts for HORSE JUMP. Pure Python, no installs needed:
    python3 make_svgs.py
Writes one SVG per part into ./svg  (units = mm, RED = cut, BLUE = engrave/score).

COORDINATES (everything measured in mm)
  x = left → right, looking at the FRONT of the box  (0 … 400)
  y = back → front  (0 = front face of the back panel; + toward the viewer)
  z = up, from the TOP surface of the base

  Back panel ........ y -T … 0, stands in base slots
  Belt + pulleys .... y 20 … 52  (pulley centers at z = 65, x = 45 and 355)
  Horse ............. y ≈ 55 (in front of the belt, so its legs never hit fences)
  Motor plate ....... y 53 … 56 at the LEFT pulley; motor face-mounts on its front
  Sensor post ....... y 75 … 78 at x = 200 (LDR side of the light beam)
  Servo mount ....... y -26 … -23, behind the back panel (servo shaft points forward)
  Front lip ......... y 143 … 146
"""
import math, os

# ---------------- PARAMETERS ----------------
T        = 3.0     # plywood thickness (use 3.175 for 1/8", 6.0 for 1/4")
SLOT_FIT = 0.2     # extra slot width so tabs slide in (raise if too tight)
W        = 400.0   # box width
BACK_H   = 260.0   # back panel height above the base
LIP_H    = 85.0    # front lip height
LEDGE    = 90.0    # base depth behind the back panel (servo + Arduino live here)
FRONT    = 143.0   # distance from back panel to front lip
EDGE     = 8.0     # base sticks out this far past the front lip

AXLE_Z   = 65.0    # pulley center height
PULLEY_X = (45.0, 355.0)  # (drive/motor, idler)

PIVOT    = (94.0, 177.0)  # servo shaft position (x, z) — raised so the hind hooves rest on the belt
ARM_R    = 110.0          # servo arm length, pivot → horse bolt
REST_DEG = -15.0          # arm angle with horse down
UP_DEG   = 10.0           # arm angle with horse up (25° swing)
SLOT_DEG = (-22.0, 22.0)  # arc slot range (gives tuning room)
SLOT_W   = 5.0            # M4 bolt

BEAM_Z   = 105.0   # height of the LED→LDR light beam
HORSE_X  = 200.0   # beam/horse center
# --------------------------------------------

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "svg")
os.makedirs(OUT, exist_ok=True)
CUT = 'fill="none" stroke="#ff0000" stroke-width="0.1"'
ENG = 'fill="none" stroke="#0000ff" stroke-width="0.1"'
TXT = 'fill="#0000ff" font-family="Helvetica" font-size="5"'


def pin_at(deg):
    a = math.radians(deg)
    return PIVOT[0] + ARM_R * math.cos(a), PIVOT[1] + ARM_R * math.sin(a)


class Part:
    """Shapes are given in world-ish coords (x right, z up) relative to the
    part's own bottom-left corner; converted to SVG (y down) on save."""

    def __init__(self, name, w, h, below=0.0, note=""):
        self.name, self.w, self.h, self.below, self.note = name, w, h, below, note
        self.items = []

    def Y(self, z):
        return self.h - z

    def outline(self, pts):
        self.items.append(("poly", pts, CUT))

    def hole(self, x, z, d):
        self.items.append(("circle", (x, z, d / 2), CUT))

    def rect(self, x0, z0, x1, z1, style=CUT):
        self.items.append(("poly", [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], style))

    def arc_slot(self, cx, cz, r, a0, a1, w):
        self.items.append(("arcslot", (cx, cz, r, a0, a1, w), CUT))

    def label(self, x, z, s):
        self.items.append(("text", (x, z, s), TXT))

    def svg_items(self):
        out = []
        for kind, d, style in self.items:
            if kind == "poly":
                p = " ".join(f"{x:.3f},{self.Y(z):.3f}" for x, z in d)
                out.append(f'<polygon points="{p}" {style}/>')
            elif kind == "circle":
                x, z, r = d
                out.append(f'<circle cx="{x:.3f}" cy="{self.Y(z):.3f}" r="{r:.3f}" {style}/>')
            elif kind == "text":
                x, z, s = d
                out.append(f'<text x="{x:.2f}" y="{self.Y(z):.2f}" {style}>{s}</text>')
            elif kind == "arcslot":
                cx, cz, r, a0, a1, w = d
                ro, ri, h = r + w / 2, r - w / 2, w / 2
                A0, A1 = math.radians(a0), math.radians(a1)
                P = lambda rr, a: (cx + rr * math.cos(a), self.Y(cz + rr * math.sin(a)))
                big = 1 if (a1 - a0) > 180 else 0
                s = (f"M {P(ro, A0)[0]:.3f} {P(ro, A0)[1]:.3f} "
                     f"A {ro} {ro} 0 {big} 0 {P(ro, A1)[0]:.3f} {P(ro, A1)[1]:.3f} "
                     f"A {h} {h} 0 0 0 {P(ri, A1)[0]:.3f} {P(ri, A1)[1]:.3f} "
                     f"A {ri} {ri} 0 {big} 1 {P(ri, A0)[0]:.3f} {P(ri, A0)[1]:.3f} "
                     f"A {h} {h} 0 0 0 {P(ro, A0)[0]:.3f} {P(ro, A0)[1]:.3f} Z")
                out.append(f'<path d="{s}" {style}/>')
        return out

    def save(self):
        m = 2.0  # margin
        vb_y = -m
        total_h = self.h + self.below + 2 * m
        body = "\n  ".join(self.svg_items())
        svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
               f'<!-- {self.name}: {self.note}  RED=cut BLUE=engrave -->\n'
               f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'width="{self.w + 2*m:.2f}mm" height="{total_h:.2f}mm" '
               f'viewBox="{-m} {vb_y} {self.w + 2*m:.2f} {total_h:.2f}">\n  {body}\n</svg>\n')
        with open(os.path.join(OUT, self.name + ".svg"), "w") as f:
            f.write(svg)
        print(f"{self.name + '.svg':24s} {self.w:6.1f} x {self.h + self.below:6.1f} mm  {self.note}")


def tabbed_bottom(w, h, tabs, tab_w=20.0):
    """Rectangle w x h with tabs of depth T hanging below z=0 at x centers `tabs`."""
    pts = [(0, h), (0, 0)]
    for cx in sorted(tabs):
        pts += [(cx - tab_w / 2, 0), (cx - tab_w / 2, -T), (cx + tab_w / 2, -T), (cx + tab_w / 2, 0)]
    pts += [(w, 0), (w, h)]
    return pts


# ---------------- parts ----------------
BACK_TABS = (60.0, 200.0, 340.0)


def back_panel():
    p = Part("back_panel", W, BACK_H, T, "1x  front view; tabs go into base")
    p.outline(tabbed_bottom(W, BACK_H, BACK_TABS))
    # arc slot for the horse bolt
    p.arc_slot(*PIVOT, ARM_R, *SLOT_DEG, SLOT_W)
    # idler pulley axle (M5)
    p.hole(PULLEY_X[1], AXLE_Z, 5.3)
    # LED beam holder: 2 pilot holes + hole for LED legs
    p.hole(HORSE_X - 11.5, BEAM_Z, 2.5)
    p.hole(HORSE_X + 11.5, BEAM_Z, 2.5)
    p.hole(HORSE_X, BEAM_Z, 6.0)
    # indicator LEDs (5 mm): red, red, green
    p.hole(30, 235, 5.0)
    p.hole(W - 30, 235, 5.0)
    p.hole(W - 80, 235, 5.0)
    # wire pass-throughs (motor, LDR)
    p.hole(100, 15, 12)
    p.hole(240, 15, 12)
    p.label(5, 5, "FRONT FACE")
    return p


def base():
    D = LEDGE + T + FRONT + T + EDGE  # total depth
    p = Part("base", W, D, 0, "1x  top view, back edge at top")
    p.outline([(0, 0), (W, 0), (W, D), (0, D)])
    # convert world y (back→front) to this part's vertical coord (front at bottom)
    v = lambda y: D - (y + LEDGE + T)

    def slot(xc, y0, w, name):
        p.rect(xc - (w + SLOT_FIT) / 2, v(y0 + T) - SLOT_FIT / 2,
               xc + (w + SLOT_FIT) / 2, v(y0) + SLOT_FIT / 2)
        p.label(xc + w / 2 + 2, v(y0 + T) - 0.5, name)

    for x in BACK_TABS:
        slot(x, -T, 20, "back")
    for x in BACK_TABS:
        slot(x, FRONT, 20, "lip")
    slot(PULLEY_X[0], 53, 30, "motor")
    slot(HORSE_X, 75, 20, "sensor")
    slot(SERVO_PLATE_X + 35, -26, 30, "servo")
    return p


def front_lip():
    p = Part("front_lip", W, LIP_H, T, "1x  start button hole in the middle")
    p.outline(tabbed_bottom(W, LIP_H, BACK_TABS))
    p.rect(W / 2 - 3.25, 45 - 3.25, W / 2 + 3.25, 45 + 3.25)  # 6x6 tactile button
    p.label(W / 2 - 8, 35, "START")
    return p


def motor_plate():
    w, h = 60.0, 100.0
    p = Part("motor_plate", w, h, T, "1x  motor face-mounts on the FRONT side")
    p.outline(tabbed_bottom(w, h, [w / 2], 30))
    cx = w / 2
    p.hole(cx, AXLE_Z, 12)                       # shaft + gearbox boss
    for a in (0, 90, 180, 270):                  # radial slots: fit most screw patterns
        r = math.radians(a)
        x0, z0 = cx + 8 * math.cos(r), AXLE_Z + 8 * math.sin(r)
        x1, z1 = cx + 17 * math.cos(r), AXLE_Z + 17 * math.sin(r)
        nx, nz = -math.sin(r) * 1.6, math.cos(r) * 1.6
        p.outline([(x0 + nx, z0 + nz), (x1 + nx, z1 + nz), (x1 - nx, z1 - nz), (x0 - nx, z0 - nz)])
    for z in (AXLE_Z - 26, AXLE_Z + 26):         # zip-tie slots as a backup
        p.rect(cx - 16, z - 2, cx - 11, z + 2)
        p.rect(cx + 11, z - 2, cx + 16, z + 2)
    return p


def sensor_post():
    w, h = 40.0, 125.0
    p = Part("sensor_post", w, h, T, "1x  LDR holder screws to the BACK side")
    p.outline(tabbed_bottom(w, h, [w / 2]))
    p.hole(w / 2 - 11.5, BEAM_Z, 2.5)
    p.hole(w / 2 + 11.5, BEAM_Z, 2.5)
    p.hole(w / 2, BEAM_Z, 6.0)
    return p


# SG90 micro servo: body 22.8 x 12.6, ear holes 27.5 apart, shaft 5.5 mm off body center
SERVO_BODY = (23.2, 13.0)
SERVO_PLATE_X = PIVOT[0] - 5.5 - 35.0   # plate left edge (plate is 70 wide)


def servo_mount():
    w, h = 70.0, PIVOT[1] + 35.0
    p = Part("servo_mount", w, h, T, "1x  stands behind back panel; servo ears screw to its BACK")
    p.outline(tabbed_bottom(w, h, [w / 2], 30))
    bx = PIVOT[0] - 5.5 - SERVO_PLATE_X       # body center (shaft sits toward the horse side)
    bw, bh = SERVO_BODY
    p.rect(bx - bw / 2, PIVOT[1] - bh / 2, bx + bw / 2, PIVOT[1] + bh / 2)
    p.hole(bx - 13.75, PIVOT[1], 2.0)
    p.hole(bx + 13.75, PIVOT[1], 2.0)
    p.rect(w / 2 - 6, 10, w / 2 + 6, 22)      # wire hole
    return p


def servo_arm():
    L, wd = ARM_R, 14.0
    p = Part("servo_arm", L + wd, wd, 0, "cut 2 (1 spare)  glue/screw the servo horn on")
    r = wd / 2
    pts = []
    for i in range(0, 181, 10):                # left round end
        a = math.radians(90 + i)
        pts.append((r + r * math.cos(a), r + r * math.sin(a)))
    for i in range(0, 181, 10):                # right round end
        a = math.radians(-90 + i)
        pts.append((r + L + r * math.cos(a), r + r * math.sin(a)))
    p.outline(pts)
    p.hole(r, r, 6.0)                          # screwdriver access to horn screw
    for d in (9, 14, 19):
        p.hole(r + d, r, 1.5)                  # horn screw pilots (drill to suit)
    p.hole(r + L, r, 4.3)                      # M4 horse bolt
    return p


# Horse silhouette mid-jump: neck stretched forward, front legs tucked, hind legs
# reaching back to push off, tail streaming. Traced on a 1436x1060 sketch grid,
# then scaled to mm with the bolt hole at the middle of the body.
_HORSE_SKETCH = [
    (300, 495), (240, 502), (175, 540), (115, 600), (75, 670), (55, 745),          # tail top edge
    (95, 715), (140, 660), (190, 610), (250, 570), (292, 560),                      # tail underside
    (290, 620), (270, 700), (245, 790), (220, 860), (195, 925), (178, 965),         # hind leg, back edge
    (205, 975), (232, 955),                                                         # hind hoof
    (250, 900), (280, 830), (320, 740), (360, 670), (400, 630),                     # hind leg, front edge
    (470, 605), (560, 592), (650, 585), (700, 588),                                 # belly
    (770, 605), (835, 612), (790, 632), (735, 648), (728, 668), (762, 678),         # tucked front leg
    (830, 656), (880, 632), (905, 597), (900, 565), (875, 540),                     # cannon, knee
    (855, 510), (850, 470), (880, 420), (940, 388),                                 # chest, neck front
    (975, 430), (1000, 470), (1030, 495), (1058, 480), (1062, 450),                 # jaw, muzzle
    (1052, 395), (1040, 335), (1042, 300), (1052, 268), (1028, 282), (1003, 290),   # face, ear
    (985, 290), (940, 282), (880, 288), (820, 300), (765, 330),                     # mane
    (700, 348), (600, 368), (500, 392), (420, 425), (350, 460),                     # back, croup
]
_S, _O = 0.175, (600, 470)          # mm per sketch unit, body-center origin
_LEG = 0.6                          # shorten legs below the belly so hooves land on the belt


def _catmull(pts, n=5):
    out = []
    for i in range(len(pts)):
        p0, p1, p2, p3 = (pts[(i + k) % len(pts)] for k in (-1, 0, 1, 2))
        for s in range(n):
            u = s / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * u
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u * u
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u ** 3) for j in (0, 1)))
    return out


def _horse_pts():
    pts = []
    for px, py in _HORSE_SKETCH:
        x, z = (px - _O[0]) * _S, (_O[1] - py) * _S
        if z < -20:
            z = -20 + (z + 20) * _LEG
        pts.append((x, z))
    return _catmull(pts)


HORSE = _horse_pts()
HORSE_EYE = ((1012 - _O[0]) * _S, (_O[1] - 360) * _S)


def horse():
    xs = [x for x, _ in HORSE]
    zs = [z for _, z in HORSE]
    ox, oz = -min(xs) + 1, -min(zs) + 1
    p = Part("horse", max(xs) - min(xs) + 2, max(zs) - min(zs) + 2, 0,
             "1x (cut 2 and glue for a stiffer 6 mm horse)")
    p.outline([(x + ox, z + oz) for x, z in HORSE])
    p.hole(ox, oz, 4.3)                        # M4 bolt to the servo arm
    p.hole(ox + HORSE_EYE[0], oz + HORSE_EYE[1], 2.5)  # eye
    return p


def side_panel():
    D = LEDGE + T + FRONT + T + EDGE
    H = T + BACK_H
    back_face = LEDGE + T                      # where the back panel's front face is
    p = Part("side_panel", D, H, 0, "cut 2  glue/screw to the outside of the box")
    lip_back = back_face + FRONT + T
    p.outline([(0, 0), (D, 0), (D, T), (lip_back, T), (lip_back, T + LIP_H), (back_face + 20, H), (0, H)])
    p.rect(25, T + 10, 45, T + 24)             # USB / battery cable hole (rear area)
    return p


if __name__ == "__main__":
    print(f"pin rest {pin_at(REST_DEG)}  pin up {pin_at(UP_DEG)}")
    for f in (back_panel, base, front_lip, side_panel, motor_plate, sensor_post,
              servo_mount, servo_arm, horse):
        f().save()
