"""
Pulleys with the axle printed as ONE piece (pulley + spacer collar + stub).
The whole part spins; the stub turns inside a hole in the back panel.

  idler_pulley_axle_5mm  : stub fits the EXISTING 5.3 mm idler hole (+ glue-on cap)
  idler_pulley_axle_8mm  : stronger stub — drill the idler hole out to 8.5 mm
  drive_pulley_axle_DD   : drive pulley (DD 0.3 fit) + stub that rests in a 9 mm hole
                           drilled in the back panel at the drive pulley center.
                           Steadies the pulley so it can't wobble on the short motor shaft.
PRINT: flange down, collar/stub pointing up. No supports. 4 walls, 40%+ infill.
Run:  python make_pulley_axles.py
"""
import os
import trimesh
import make_parts as mp

GAP_TO_PANEL = 19.5   # pulley back flange -> back panel front face (belt region starts 20 mm out)
PANEL = 3.0
CAP_T = 3.0

OUT = mp.OUT


def collar_and_stub(z0, collar_d, stub_d, stub_len):
    collar = mp.cyl(collar_d, GAP_TO_PANEL, z0)
    stub = mp.cyl(stub_d, stub_len + 0.01, z0 + GAP_TO_PANEL - 0.01)
    return [collar, stub]


def idler_with_axle(stub_d):
    body, h = mp.pulley_body(0)
    stub_len = PANEL + 0.5 + CAP_T                 # through the panel + room for the cap
    return mp.union(body, *collar_and_stub(h - 0.01, max(10.0, stub_d + 4), stub_d, stub_len))


def drive_with_axle():
    body, h = mp.pulley_body(mp.GRIP_RIBS)
    body = mp.union(body, *collar_and_stub(h - 0.01, 12.0, 8.0, PANEL + 1.5))
    return mp.diff(body, mp.d_bore("DD", h))      # DD hole only through the pulley, axle stays solid


def cap(stub_d):
    c = mp.cyl(stub_d + 7, CAP_T, 0)
    return mp.diff(c, mp.cyl(stub_d + 0.2, CAP_T + 2, -1))


if __name__ == "__main__":
    mp.save(idler_with_axle(5.0), "idler_pulley_axle_5mm.stl")
    mp.save(cap(5.0), "idler_axle_cap_5mm.stl")
    mp.save(idler_with_axle(8.0), "idler_pulley_axle_8mm.stl")
    mp.save(cap(8.0), "idler_axle_cap_8mm.stl")
    mp.save(drive_with_axle(), "drive_pulley_axle_DD.stl")
