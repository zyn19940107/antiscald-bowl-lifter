"""Generate 3D-printable STL parts of the V2 clip pair (print prototype version).

Design (printable, FDM/SLS):
  clip_A_body   : half ring + two eye loops (孔) + boss with vertical socket slot
  clip_B_body   : half ring + two drop pins (插销) + boss with vertical socket slot
  riser_handle  : gooseneck riser + fish handle, one flat part with a slot tab
  fit_gauge     : eye hole + pin for a 5-minute fit check
All parts are designed to be printed flat (no supports).

Run:
  blender -b --factory-startup --python scripts/make_print_parts.py
"""
import math
import os
import sys

import bpy
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

OUT = 'D:/code/vibe/antiscald/print'
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- print design (mm)
R_RING = 64.0          # ring centreline radius
R_J = 72.5             # joint radius at the tips
SEC_W = 7.0            # ring section, radial width
SEC_H = 6.0            # ring section, height (print z)
END_T = 8.0            # end feature thickness (print z)
EYE_RO, EYE_RI = 13.0, 5.25    # eye loop outer/inner radius (hole Ø10.5)
PIN_R, PIN_H = 4.5, 16.0       # drop pin radius / height above the pad
PAD_W, PAD_D = 26.0, 20.0      # end pad size
BOSS_X, BOSS_Y, BOSS_H = 32.0, 26.0, 14.0
SLOT_W, SLOT_L, SLOT_D = 5.5, 17.0, 10.0
RISER_W, RISER_T = 12.0, 9.0
FISH_L, FISH_W, FISH_T = 105.0, 32.0, 9.0
RISER = [(73.5, 12.0), (78.0, 20.0), (82.0, 30.0), (86.5, 44.0), (91.0, 62.0),
         (94.5, 80.0), (98.5, 99.0), (103.5, 116.0), (110.5, 130.0), (120.0, 140.0),
         (131.2, 146.5)]
BETA = math.radians(33.0)


# ---------------------------------------------------------------- mesh helpers
def make_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box(cx, cy, cz, sx, sy, sz):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


def cylinder(cx, cy, z0, z1, r, n=40):
    v, f = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((cx + r * math.cos(a), cy + r * math.sin(a), z0))
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((cx + r * math.cos(a), cy + r * math.sin(a), z1))
    for k in range(n):
        k2 = (k + 1) % n
        f.append((k, k2, n + k2, n + k))
    f.append(tuple(range(n - 1, -1, -1)))
    f.append(tuple(range(n, 2 * n)))
    return v, f


def washer(cx, cy, z0, z1, r_out, r_in, n=48):
    v, f = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a), z0))
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((cx + r_in * math.cos(a), cy + r_in * math.sin(a), z0))
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a), z1))
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((cx + r_in * math.cos(a), cy + r_in * math.sin(a), z1))
    O0, I0, O1, I1 = 0, n, 2 * n, 3 * n
    for k in range(n):
        k2 = (k + 1) % n
        f.append((O0 + k, O0 + k2, I0 + k2, I0 + k))
        f.append((O1 + k, I1 + k, I1 + k2, O1 + k2))
        f.append((O0 + k, O1 + k, O1 + k2, O0 + k2))
        f.append((I0 + k, I0 + k2, I1 + k2, I1 + k))
    return v, f


class Part:
    def __init__(self):
        self.v, self.f = [], []

    def add(self, vf):
        v, f = vf
        b = len(self.v)
        self.v.extend(v)
        self.f.extend([tuple(b + i for i in face) for face in f])

    def obj(self, name):
        return make_obj(name, self.v, self.f)

    def volume(self):
        vol = 0.0
        v = np.array(self.v, float)
        for face in self.f:
            for i in range(1, len(face) - 1):
                a, b, c = v[face[0]], v[face[i]], v[face[i + 1]]
                vol += np.dot(a, np.cross(b, c)) / 6.0
        return abs(vol) / 1000.0   # cm^3


def ring_path(kind, radius=R_RING, n=220):
    a0, a1 = (math.radians(98.0), math.radians(262.0)) if kind == 'eye' else \
             (math.radians(-82.0), math.radians(82.0))
    u = np.linspace(0, 1, n)
    ang = a0 + (a1 - a0) * u
    f = np.clip(np.exp(-((u / 0.075) ** 2)) + np.exp(-(((1 - u) / 0.075) ** 2)), 0, 1)
    r = radius + (R_J - radius) * f
    return np.stack([r * np.cos(ang), r * np.sin(ang)], axis=1)


def sweep_rect_xy(path, half_w, z0, h):
    """Sweep a rectangle (half_w in-plane, h in z) along an XY polyline."""
    P = np.asarray(path, float)
    n = len(P)
    v, f = [], []
    for i in range(n):
        t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        t /= (np.linalg.norm(t) or 1)
        N = np.array([-t[1], t[0]])
        for sw in (-half_w, half_w):
            p = P[i] + N * sw
            v.append((p[0], p[1], z0))
            v.append((p[0], p[1], z0 + h))
    for i in range(n - 1):
        a, b = 4 * i, 4 * (i + 1)
        f.append((a, a + 1, b + 1, b))          # inner wall
        f.append((a + 2, b + 2, b + 3, a + 3))  # outer wall
        f.append((a + 1, a + 3, b + 3, b + 1))  # top
        f.append((a, b, b + 2, a + 2))          # bottom
    f.append((0, 1, 3, 2))
    e = 4 * (n - 1)
    f.append((e, e + 2, e + 3, e + 1))
    return v, f


def extrude_poly(pts, z0, h):
    """Extrude a closed 2D polygon (list of (x,y)) from z0 to z0+h (needs CCW)."""
    n = len(pts)
    v = [(x, y, z0) for (x, y) in pts] + [(x, y, z0 + h) for (x, y) in pts]
    f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        f.append((i, j, n + j, n + i))
    return v, f


def chaikin(pts, it=2):
    P = [np.array(p, float) for p in pts]
    for _ in range(it):
        out = [P[0]]
        for i in range(len(P) - 1):
            out.append(0.75 * P[i] + 0.25 * P[i + 1])
            out.append(0.25 * P[i] + 0.75 * P[i + 1])
        out.append(P[-1])
        P = out
    return P


def strip_sweep_rz(path_rz, half_w, half_t, y=0.0):
    """Sweep a rectangle along a polyline in the XZ plane: width in-plane, thickness in Y."""
    P = np.array([(p[0], p[1]) for p in chaikin(path_rz, 2)], float)
    n = len(P)
    v, f = [], []
    for i in range(n):
        t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        t /= (np.linalg.norm(t) or 1)
        N = np.array([-t[1], t[0]])   # in-plane normal
        for sw in (-half_w, half_w):
            for sy in (-half_t, half_t):
                p = P[i] + N * sw
                v.append((p[0], y + sy, p[1]))
    for i in range(n - 1):
        a, b = 4 * i, 4 * (i + 1)
        f.append((a, a + 1, b + 1, b))
        f.append((a + 2, b + 2, b + 3, a + 3))
        f.append((a + 1, a + 3, b + 3, b + 1))
        f.append((a, b, b + 2, a + 2))
    f.append((0, 1, 3, 2))
    e = 4 * (n - 1)
    f.append((e, e + 2, e + 3, e + 1))
    return v, f


# ---------------------------------------------------------------- clip bodies
def tip_points(kind):
    p = ring_path(kind)
    return p[0], p[-1]


def build_clip_body(kind):
    part = Part()
    path = ring_path(kind)
    part.add(sweep_rect_xy(path, SEC_W / 2, 0.0, SEC_H))
    tipA, tipB = path[0], path[-1]
    z0 = 0.0 if kind == 'eye' else 4.0      # A: lower lap pad, B: upper lap pad
    for tip, ey in ((tipA, R_J if tipA[1] > 0 else -R_J),
                    (tipB, R_J if tipB[1] > 0 else -R_J)):
        J = np.array([0.0, ey])
        mid = (tip + J) / 2
        part.add(box(mid[0], mid[1], 4.0, 18, 13, 8.0))
        part.add(washer(J[0], J[1], z0, z0 + 4.0, 12.0, 2.15))
        # stiffening web from the pad to the ring
        part.add(box(mid[0] * 0.55, mid[1] * 0.55, 4.0, 20, 10, 8.0))
    # closed-end boss + vertical slot (U shape, open at the top)
    side = -1 if kind == 'eye' else 1
    bx = side * (R_RING + 7.0)
    half_gap = SLOT_W / 2
    part.add(box(bx, half_gap + (BOSS_Y / 2 - half_gap) / 2, BOSS_H / 2, BOSS_X, BOSS_Y / 2 - half_gap, BOSS_H))
    part.add(box(bx, -half_gap - (BOSS_Y / 2 - half_gap) / 2, BOSS_H / 2, BOSS_X, BOSS_Y / 2 - half_gap, BOSS_H))
    part.add(box(bx, 0.0, 2.0, BOSS_X, SLOT_W, 4.0))
    for yy in (-1, 1):
        part.add(box(side * (R_RING + 4.0), yy * 9.0, 5.0, 14.0, 5.0, 10.0))
    return part


# ---------------------------------------------------------------- riser + handle
def build_riser_handle(side=1):
    part = Part()
    path = [(73.5, 1.0)] + [(p[0], p[1]) for p in RISER]
    part.add(strip_sweep_rz(path, RISER_W / 2, RISER_T / 2))
    part.add(box(73.5, 0.0, 6.5, 14.0, RISER_T, 11.0))
    bx, bz = RISER[-1]
    ax = np.array([math.cos(BETA), math.sin(BETA)])
    pe = np.array([-ax[1], ax[0]])
    stations = [(0.0, 0.34), (10.0, 0.64), (22.0, 0.86), (34.0, 0.96), (48.0, 0.97),
                (62.0, 0.92), (76.0, 0.80), (88.0, 0.64), (97.0, 0.44),
                (103.0, 0.24), (FISH_L, 0.06)]
    top, bot = [], []
    for (u, fr) in stations:
        c = np.array([bx, bz]) + u * ax
        hw = 0.5 * FISH_W * fr
        top.append(c + hw * pe)
        bot.append(c - hw * pe)
    tip = np.array([bx, bz]) + (FISH_L + 1.0) * ax
    outline = top + [tip] + list(reversed(bot))
    outline = [tuple(p) for p in chaikin(outline, 2)]
    part.add(extrude_poly(outline, 0.0, FISH_T))
    part.add(box(bx - ax[0] * 7, 0.0, bz - ax[1] * 7, 20, RISER_T, 20))
    if side < 0:
        v = [(-x, y, z) for (x, y, z) in part.v]
        f = [tuple(reversed(face)) for face in part.f]
        part = Part()
        part.v, part.f = v, f
    return part


# ---------------------------------------------------------------- fit gauge
def build_gauge():
    part = Part()
    part.add(washer(-13.0, 0.0, 0.0, 4.0, 12.0, 2.15))
    part.add(box(-13.0, 0.0, 4.0, 18, 13, 8.0))
    part.add(washer(13.0, 0.0, 4.0, 8.0, 12.0, 2.15))
    return part


# ---------------------------------------------------------------- export
def fix_normals(ob):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def export_stl(ob, name):
    fix_normals(ob)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(OUT, name)
    ok = False
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
        ok = True
    except Exception:
        pass
    if not ok:
        try:
            bpy.ops.export_mesh.stl(filepath=path, use_selection=True)
            ok = True
        except Exception as e:
            print('[print] export failed', name, e)
    print('[print]', name, 'OK' if ok else 'FAIL', flush=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = []
    A = build_clip_body('eye')
    parts.append((A, 'clip_A_body.stl'))
    B = build_clip_body('hook')
    parts.append((B, 'clip_B_body.stl'))
    parts.append((build_riser_handle(+1), 'riser_handle_B.stl'))
    parts.append((build_riser_handle(-1), 'riser_handle_A.stl'))
    G = build_gauge()
    parts.append((G, 'fit_gauge.stl'))
    for part, name in parts:
        ob = part.obj(name.replace('.stl', ''))
        ob.name = name.replace('.stl', '')
        try:
            vol = part.volume()
        except Exception:
            vol = 0.0
        print('[print] %-18s volume %6.1f cm3  ~PETG %5.1f g  ~PA12 %5.1f g'
              % (name, vol, vol * 1.27, vol * 1.01), flush=True)
        export_stl(ob, name)
    # save a preview scene
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'print_parts.blend'))
    print('[print] done', flush=True)


if __name__ == '__main__':
    main()
