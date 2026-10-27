"""Build the two-clip (eye + hook) bowl lifter demo scene and animation.

Run:
  blender -b --factory-startup --python scripts/build_scene.py
  blender -b --factory-startup --python scripts/build_scene.py -- --test-frame 220 --samples 24 --res 960x540 --out test.png
"""
import argparse
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import scene_common as sc

TAU = 2.0 * math.pi
FPS = 24
FRAME_END = 516

# ------------------------------------------------------------------ dimensions
WIRE_R = 0.0016            # wire radius (3.2 mm wire)
R_IN = 0.0625              # inner wire centreline radius (ring, working state)
R_OUT = 0.0675             # outer wire centreline radius
R_J = 0.0725               # radial position of the joints (eye / hook)
EYE_MAJOR = 0.0072         # eye loop centreline radius
EYE_LOOP_R = 0.0022        # forged eye loop wire radius
CONTACT_Z = 0.0454         # ring-plane height above bowl base when wedged
RING_Z0 = 0.030            # initial approach height of ring plane
B_HOVER = 0.0095           # hook clip rides this much higher during approach
CROOK_TIP_Z = -0.0028      # hook tip below ring plane after engagement
X_HOME = 0.30              # tongs start this far out
Z_RELEASE = 0.012          # ring plane height after setting bowl down
TARGET_X, TARGET_Y = 0.155, 0.055
Z_LIFT = 0.095

# Bowl outer profile (r, z).  Starts at bottom pole, goes out and up to rim,
# then comes back down the inside to the inner-floor pole.
BOWL_OUTER = [
    (0.0000, 0.0000), (0.0130, 0.0000), (0.0235, 0.0000), (0.0298, 0.0006),
    (0.0345, 0.0022), (0.0390, 0.0052), (0.0432, 0.0095), (0.0472, 0.0148),
    (0.0512, 0.0208), (0.0545, 0.0270), (0.0570, 0.0330), (0.0585, 0.0380),
    (0.0600, 0.0420), (0.0612, 0.0455), (0.0630, 0.0495), (0.0655, 0.0535),
    (0.0687, 0.0575), (0.0725, 0.0615), (0.0766, 0.0655), (0.0806, 0.0695),
    (0.0841, 0.0735), (0.0861, 0.0770), (0.0868, 0.0795), (0.0863, 0.0812),
    (0.0846, 0.0824),          # rim outer top, curling in
    (0.0830, 0.0828),          # rim top edge
    (0.0808, 0.0820),          # inner top edge
]
BOWL_INNER = [
    (0.0794, 0.0808), (0.0772, 0.0786), (0.0740, 0.0748), (0.0705, 0.0708),
    (0.0668, 0.0666), (0.0632, 0.0628), (0.0595, 0.0588), (0.0558, 0.0548),
    (0.0522, 0.0508), (0.0488, 0.0468), (0.0452, 0.0428), (0.0418, 0.0388),
    (0.0385, 0.0348), (0.0350, 0.0308), (0.0315, 0.0268), (0.0278, 0.0228),
    (0.0240, 0.0188), (0.0198, 0.0150), (0.0150, 0.0118), (0.0090, 0.0092),
    (0.0040, 0.0078), (0.0000, 0.0074),
]

MAT = {}

# ---------------------------------------------------------------- handle style
# False: original flat fish handle (in ring plane)
# True : raised gooseneck handle (grip well above the U-ring, for use inside a pot)
RAISED_HANDLE = False

# riser tube centreline (rho, z) in the handle's radial-vertical plane
RISER_PTS = [
    (0.0735, 0.0016), (0.0805, 0.0125), (0.0875, 0.0245), (0.0930, 0.0340),
    (0.0952, 0.0520), (0.0968, 0.0720), (0.0992, 0.0930), (0.1038, 0.1120),
    (0.1108, 0.1270), (0.1202, 0.1370), (0.1312, 0.1438),
]
RISER_TUBE_R = 0.0030      # dia 6 mm tube
HANDLE_BETA = math.radians(33.0)   # handle axis above horizontal
FERRULE_R = 0.0050
FERRULE_HALF = 0.0110


# ------------------------------------------------------------------ materials
def make_materials():
    MAT['steel'] = sc.principled('Steel', base=(0.72, 0.73, 0.75, 1), metallic=1.0,
                                 roughness=0.15, coat=0.0)
    MAT['steel'].node_tree.nodes["Principled BSDF"].inputs["Anisotropic"].default_value = 0.25
    MAT['plastic'] = sc.principled('PlasticWhite', base=(0.72, 0.71, 0.665, 1),
                                   roughness=0.34, coat=0.30, coat_rough=0.14)
    sc.add_scale_bump(MAT['plastic'], scale=230.0, strength=0.38)
    MAT['dark'] = sc.principled('Dark', base=(0.015, 0.015, 0.017, 1), roughness=0.28)
    MAT['yellow'] = sc.principled('CeramicYellow', base=(0.74, 0.33, 0.008, 1),
                                  roughness=0.12, coat=0.28, coat_rough=0.08)
    MAT['white'] = sc.principled('CeramicWhite', base=(0.67, 0.66, 0.60, 1),
                                 roughness=0.11, coat=0.28, coat_rough=0.08)
    MAT['wood'] = sc.wood_material('WoodTable', light=(0.30, 0.175, 0.065, 1),
                                   dark=(0.085, 0.041, 0.012, 1), grain_scale=60.0,
                                   roughness=0.36)
    MAT['wall'] = sc.principled('WallDark', base=(0.085, 0.055, 0.033, 1),
                                roughness=0.9)
    MAT['wood2'] = sc.wood_material('WoodBoard', light=(0.28, 0.17, 0.075, 1),
                                    dark=(0.15, 0.08, 0.03, 1), grain_scale=40.0,
                                    roughness=0.6)
    MAT['jar'] = sc.principled('Stoneware', base=(0.055, 0.048, 0.042, 1),
                               roughness=0.42, coat=0.1)


# ------------------------------------------------------------------ helpers
def ring_wire_path(kind, radius, n=220):
    """Approach arc + outward flare so tips end exactly at the joint points."""
    if kind == 'eye':       # left half, from front joint (phi=262) to back (98)
        a0, a1 = math.radians(262.0), math.radians(98.0)
    else:                   # right half, from front (phi=-82) to back (+82)
        a0, a1 = math.radians(-82.0), math.radians(82.0)
    u = np.linspace(0.0, 1.0, n)
    ang = a0 + (a1 - a0) * u
    s = np.clip(u / 0.11, 0.0, 1.0)
    s2 = np.clip((1.0 - u) / 0.11, 0.0, 1.0)
    flare = np.exp(-(s ** 2) * 3.0) * (1.0 - 0.0) + np.exp(-(s2 ** 2) * 3.0)
    # blend factor: 1 at ends, 0 in middle
    f = np.clip(np.exp(-((u / 0.075) ** 2)) + np.exp(-(((1 - u) / 0.075) ** 2)), 0, 1)
    r = radius + (R_J - radius) * f
    return np.stack([r * np.cos(ang), r * np.sin(ang), np.zeros_like(r)], axis=1)


def eye_geometry(ey):
    """Formed eye at the end of the clip: stem + 360 deg loop (welded back)."""
    E = np.array([0.0, ey, 0.0])
    sign = 1.0 if ey > 0 else -1.0
    Rj = abs(ey)
    start = E + np.array([0.0, sign * EYE_MAJOR, 0.0])
    J = np.array([-0.01009, sign * 0.07180, 0.0])
    stem = np.array([
        J,
        np.array([-0.0080, sign * 0.0745, 0.0]),
        np.array([-0.0050, sign * 0.0775, 0.0]),
        np.array([-0.0022, sign * 0.0794, 0.0]),
        start,
    ])
    stem = sc.catmull_rom(stem, n_per_seg=12)
    a_start = math.atan2(start[1] - E[1], start[0] - E[0])
    adir = 1.0 if ey < 0 else -1.0
    a = np.linspace(a_start, a_start + adir * TAU, 100)
    loop = np.stack([E[0] + EYE_MAJOR * np.cos(a), E[1] + EYE_MAJOR * np.sin(a),
                     np.zeros_like(a)], axis=1)
    return [(stem, WIRE_R), (loop, EYE_LOOP_R)]


def crook_path(ey):
    """Hook wire: rises from the clip tip, arcs over the eye rim and its tip
    drops down through the eye hole (releasable when unloaded)."""
    E = np.array([0.0, ey, 0.0])
    Rj = abs(ey)
    J = np.array([0.01009, -Rj * 0.99027 if ey < 0 else Rj * 0.99027, 0.0])
    d = J - E
    d = d / np.linalg.norm(d)
    profile = [
        (0.01011, 0.0000), (0.01120, 0.0022), (0.01240, 0.0050),
        (0.01340, 0.0080), (0.01380, 0.0102), (0.01350, 0.0118),
        (0.01250, 0.0127), (0.01100, 0.0128), (0.00960, 0.0118),
        (0.00860, 0.0100), (0.00800, 0.0076), (0.00770, 0.0054),
        (0.00750, 0.0039), (0.00660, 0.00385), (0.00580, 0.00365),
        (0.00500, 0.00315), (0.00440, 0.00235), (0.00390, 0.00135),
        (0.00342, 0.00022), (0.00320, -0.00130), (0.00280, -0.00260),
        (0.00220, -0.00340), (0.00160, -0.00375), (0.00100, -0.00370),
    ]
    pts = np.array([[E[0] + u * d[0], E[1] + u * d[1], z] for (u, z) in profile])
    pts = sc.catmull_rom(pts, n_per_seg=10)
    return [(pts, WIRE_R)]


def _add_transformed(mb, sub, origin, ax, ay, az):
    """Map sub-builder local (u,y,z) -> origin + u*ax + y*ay + z*az."""
    v = np.array(sub.verts)
    v = origin[None, :] + v[:, 0:1] * ax[None, :] + v[:, 1:2] * ay[None, :] + v[:, 2:3] * az[None, :]
    base = len(mb.verts)
    mb.verts.extend([tuple(map(float, p)) for p in v])
    for f, m, sm in zip(sub.faces, sub.mats, sub.smooth):
        mb.faces.append(tuple(base + i for i in f))
        mb.mats.append(m)
        mb.smooth.append(sm)


def _fish_handle_local(sub, mat_plastic, mat_dark):
    """Fish handle built along +u (0..0.105), width y, thickness z, centred at z=0."""
    stations = [
        (0.0000, 0.0115, 0.0060), (0.0033, 0.0218, 0.0104), (0.0070, 0.0288, 0.0134),
        (0.0125, 0.0312, 0.0148), (0.0190, 0.0298, 0.0150), (0.0260, 0.0312, 0.0156),
        (0.0355, 0.0322, 0.0160), (0.0465, 0.0318, 0.0159), (0.0580, 0.0302, 0.0153),
        (0.0690, 0.0278, 0.0144), (0.0790, 0.0248, 0.0132), (0.0875, 0.0212, 0.0116),
        (0.0945, 0.0172, 0.0096), (0.1000, 0.0122, 0.0070), (0.1035, 0.0068, 0.0040),
        (0.1053, 0.0026, 0.0015),
    ]
    n_sec = 24
    verts = []
    for (u, w, t) in stations:
        for k in range(n_sec):
            a = TAU * k / n_sec
            verts.append((u, 0.5 * w * math.cos(a), 0.5 * t * math.sin(a)))
    verts = np.array(verts)
    n = len(verts)
    verts = np.vstack([verts, np.array([(stations[0][0], 0.0, 0.0),
                                        (stations[-1][0], 0.0, 0.0)])])
    c0, c1 = n, n + 1
    faces = []
    ns = len(stations)
    for i in range(ns - 1):
        for k in range(n_sec):
            a = i * n_sec + k
            b = i * n_sec + (k + 1) % n_sec
            c = (i + 1) * n_sec + (k + 1) % n_sec
            d = (i + 1) * n_sec + k
            faces.append((a, b, c, d))
    for k in range(n_sec):
        b = (k + 1) % n_sec
        faces.append((c0, b, k))
        base = (ns - 1) * n_sec
        faces.append((c1, base + k, base + b))
    sub.add_raw(verts, faces, mat_plastic)

    # eyes (domes on both flat sides near the head)
    for zsign in (1.0, -1.0):
        eu, ez = 0.0885, zsign * 0.00505
        prof = []
        for j in range(9):
            aa = math.pi * j / 8.0
            prof.append((0.0031 * math.sin(aa), -0.0031 * math.cos(aa) * 0.40))
        verts2, faces2, _ = sc.lathe_data(prof, 16, lambda i: 0)
        verts2 = np.array(verts2)
        vv = np.stack([eu + verts2[:, 2], verts2[:, 0], ez + verts2[:, 1]], axis=1)
        sub.add_raw(vv, faces2, mat_dark)
    # mouth grooves
    for zsign in (1.0, -1.0):
        mz = zsign * 0.0028
        mv = np.array([(0.0995, -0.0045, mz), (0.1035, -0.0010, mz + zsign * 0.0012),
                       (0.1035, 0.0018, mz + zsign * 0.0006)])
        sub.add_raw(mv, [(0, 1, 2), (2, 1, 0)], mat_dark, smooth=False)


def bracket_and_handle(mb, side, mat_steel, mat_plastic, mat_dark):
    """V bracket + riser + fish handle at the closed end. side=-1 (left) / +1 (right)."""
    base_a = math.pi if side < 0 else 0.0
    apex = np.array([side * 0.0735, 0.0, 0.0016])

    def pt(radius, ang_off):
        a = base_a + ang_off * (-1 if side < 0 else 1)
        return np.array([radius * math.cos(a), radius * math.sin(a), 0.0])

    anchors = [pt(R_IN, math.radians(8.5)), pt(R_OUT, math.radians(-8.5))]
    for anc in anchors:
        path = sc.catmull_rom([apex, (apex + anc) / 2 + np.array([0, 0, -0.0015]), anc],
                              n_per_seg=10)
        mb.add_tube(path, WIRE_R, mat_steel)

    if not RAISED_HANDLE:
        # ---------------- original flat handle (kept for reference)
        tail = np.array([side * 0.0845, 0.0, 0.0045])
        stem = sc.catmull_rom([apex, (apex + tail) / 2 + np.array([0, 0, 0.0012]), tail],
                              n_per_seg=10)
        mb.add_tube(stem, WIRE_R, mat_steel)
        fer0 = np.array([side * 0.0800, 0.0, 0.0045])
        fer1 = np.array([side * 0.0880, 0.0, 0.0045])
        mb.add_tube(np.array([fer0, fer1]), 0.0046, mat_steel, sides=16)
        sub = sc.MeshBuilder()
        _fish_handle_local(sub, mat_plastic, mat_dark)
        # local u along side*x, z offset by 0.0045, y unchanged
        ax = np.array([side, 0.0, 0.0])
        ay = np.array([0.0, 1.0, 0.0])
        az = np.array([0.0, 0.0, 1.0])
        _add_transformed(mb, sub, np.array([side * 0.0835, 0.0, 0.0045]), ax, ay, az)
        return

    # ---------------- raised gooseneck handle
    riser = np.array([[side * rho, 0.0, z] for (rho, z) in RISER_PTS])
    riser = sc.catmull_rom(riser, n_per_seg=10)
    mb.add_tube(riser, RISER_TUBE_R, mat_steel, sides=20)
    # weld collar at the bracket
    mb.add_tube(np.array([np.array([side * 0.0735, 0, 0.0016]),
                          np.array([side * 0.0760, 0, 0.0060])]), 0.0042, mat_steel, sides=16)

    top = np.array([side * RISER_PTS[-1][0], 0.0, RISER_PTS[-1][1]])
    ax = np.array([side * math.cos(HANDLE_BETA), 0.0, math.sin(HANDLE_BETA)])
    ay = np.array([0.0, 1.0, 0.0])
    az = np.cross(ax, ay)  # flat faces of the fish
    # ferrule along handle axis
    mb.add_tube(np.array([top - ax * FERRULE_HALF, top + ax * FERRULE_HALF]),
                FERRULE_R, mat_steel, sides=20)
    sub = sc.MeshBuilder()
    _fish_handle_local(sub, mat_plastic, mat_dark)
    _add_transformed(mb, sub, top + ax * 0.0040, ax, ay, az)


def build_tong(kind):
    """kind 'eye' -> left clip with two eyes; 'hook' -> right clip with two hooks."""
    mb = sc.MeshBuilder()
    m_steel, m_plastic, m_dark = 0, 1, 2
    side = -1 if kind == 'eye' else 1
    for rad in (R_IN, R_OUT):
        path = ring_wire_path(kind, rad)
        mb.add_tube(path, WIRE_R, m_steel, sides=18)
    for ey in (-R_J, R_J):
        tubes = eye_geometry(ey) if kind == 'eye' else crook_path(ey)
        for p, r in tubes:
            mb.add_tube(p, r, m_steel, sides=18)
    bracket_and_handle(mb, side, m_steel, m_plastic, m_dark)
    mats = [MAT['steel'], MAT['plastic'], MAT['dark']]
    return mb.build_object('Clip_' + kind, mats)


def build_bowl():
    outer = list(BOWL_OUTER)
    inner = list(BOWL_INNER)
    profile = outer + inner
    n_outer = len(outer)
    th0, th1 = math.radians(45.0), math.radians(200.0)

    def mod_fn(r, z, th):
        if z < 0.050:
            return r
        amp = 0.030 * sc.smoothstep((z - 0.050) / 0.028)
        return r * (1.0 + amp * math.cos(12.0 * th))

    def mat_of_seg(i):
        return 0 if i <= n_outer - 1 else 1

    verts, faces, mats = sc.lathe_data(profile, 384, mat_of_seg, mod_fn)
    mesh = bpy.data.meshes.new('Bowl')
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.validate()
    obj = bpy.data.objects.new('Bowl', mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(MAT['yellow'])
    mesh.materials.append(MAT['white'])
    for poly, mi in zip(mesh.polygons, mats):
        poly.use_smooth = True
        poly.material_index = mi
    return obj


def make_table_and_wall():
    verts = [(-1.6, -1.4, -0.06), (1.8, -1.4, -0.06), (1.8, 1.9, -0.06), (-1.6, 1.9, -0.06),
             (-1.6, -1.4, 0.0), (1.8, -1.4, 0.0), (1.8, 1.9, 0.0), (-1.6, 1.9, 0.0)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh = bpy.data.meshes.new('Table')
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new('Table', mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(MAT['wood'])
    for p in mesh.polygons:
        p.use_smooth = False
    w = [(-2.0, 1.35, 0.0), (2.2, 1.35, 0.0), (2.2, 1.35, 1.6), (-2.0, 1.35, 1.6)]
    wf = [(0, 1, 2, 3)]
    wmesh = bpy.data.meshes.new('Wall')
    wmesh.from_pydata(w, [], wf)
    wmesh.validate()
    wobj = bpy.data.objects.new('Wall', wmesh)
    bpy.context.scene.collection.objects.link(wobj)
    wmesh.materials.append(MAT['wall'])

    # ---------------- background props (out of focus, for depth)
    def add_box(name, size, loc, rotz, mat):
        sx, sy, sz = size
        v = [(-sx/2,-sy/2,-sz/2),(sx/2,-sy/2,-sz/2),(sx/2,sy/2,-sz/2),(-sx/2,sy/2,-sz/2),
             (-sx/2,-sy/2,sz/2),(sx/2,-sy/2,sz/2),(sx/2,sy/2,sz/2),(-sx/2,sy/2,sz/2)]
        f = [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
        me = bpy.data.meshes.new(name)
        me.from_pydata(v, [], f); me.validate()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (0, 0, rotz)
        me.materials.append(mat)
        for p_ in me.polygons:
            p_.use_smooth = False
        return ob

    add_box('Board', (0.50, 0.30, 0.018), (-0.34, 0.42, 0.009), math.radians(28), MAT['wood2'])
    jar_prof = [(0.0,0.0),(0.040,0.0),(0.044,0.004),(0.046,0.030),(0.047,0.060),
                (0.044,0.078),(0.040,0.082),(0.042,0.088),(0.040,0.092),(0.0,0.092)]
    jv, jf, _ = sc.lathe_data(jar_prof, 40, lambda i: 0)
    jme = bpy.data.meshes.new('Jar')
    jme.from_pydata([tuple(x) for x in jv], [], jf); jme.validate()
    job = bpy.data.objects.new('Jar', jme)
    bpy.context.scene.collection.objects.link(job)
    job.location = (0.37, 0.32, 0.0)
    jme.materials.append(MAT['jar'])
    for p_ in jme.polygons:
        p_.use_smooth = True


# ------------------------------------------------------------------ animation
# phase boundaries (frames @ 24 fps)
F_SETTLE = 34
F_APPROACH = 101
F_HOLD_A = 128
F_BDESC = 149
F_HOLD_B = 173
F_SEAT = 217
F_LIFT = 269
F_CARRY = 341
F_SETDOWN = 382
F_RELAX = 411
F_HOLD_C = 428
F_BLIFT = 445
F_HOLD_D = 457
F_WITHDRAW = 500


def pose_at(frame):
    """Return dict of transforms for every animated object at 1-based frame."""
    f = float(frame)

    def seg(f0, f1):
        if f1 <= f0:
            return 1.0 if f >= f1 else 0.0
        return min(1.0, max(0.0, (f - f0) / (f1 - f0)))

    # state
    A = np.array([-X_HOME, 0.0, RING_Z0])
    B = np.array([X_HOME, 0.0, RING_Z0 + B_HOVER])
    bowl_base = np.array([0.0, 0.0, 0.0])
    R = np.identity(3)
    locked = False

    if f <= F_SETTLE:
        pass
    elif f <= F_APPROACH:
        u = sc.ease_in_out(seg(F_SETTLE, F_APPROACH))
        A[0] = sc.lerp(-X_HOME, 0.0, u)
        B[0] = sc.lerp(X_HOME, 0.0, u)
    elif f <= F_HOLD_A:
        A[0] = B[0] = 0.0
    elif f <= F_BDESC:
        A[0] = B[0] = 0.0
        u = sc.ease_in_out(seg(F_HOLD_A, F_BDESC))
        B[2] = sc.lerp(RING_Z0 + B_HOVER, RING_Z0, u)
    elif f <= F_HOLD_B:
        A[0] = B[0] = 0.0
        B[2] = RING_Z0
    elif f <= F_SEAT:
        A[0] = B[0] = 0.0
        u = sc.ease_in_out(seg(F_HOLD_B, F_SEAT))
        A[2] = B[2] = sc.lerp(RING_Z0, CONTACT_Z, u)
    elif f <= F_LIFT:
        u = sc.ease_in_out(seg(F_SEAT, F_LIFT))
        z = sc.lerp(CONTACT_Z, CONTACT_Z + Z_LIFT, u)
        A[:] = (0.0, 0.0, z)
        B[:] = (0.0, 0.0, z)
        bowl_base = np.array([0.0, 0.0, z - CONTACT_Z])
        locked = True
    elif f <= F_CARRY:
        u = seg(F_LIFT, F_CARRY)
        ue = sc.ease_in_out(u)
        C = np.array([sc.lerp(0.0, TARGET_X, ue), sc.lerp(0.0, TARGET_Y, ue),
                      CONTACT_Z + Z_LIFT + 0.0025 * math.sin(math.pi * u)])
        yaw = 0.030 * math.sin(math.pi * u)
        tilt = -0.012 * math.sin(math.pi * u)
        R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'Y')
        R = np.array(R)
        A = C.copy()
        B = C.copy()
        bowl_base = C + R @ np.array([0.0, 0.0, -CONTACT_Z])
        locked = True
    elif f <= F_SETDOWN:
        ue = sc.ease_in_out(seg(F_CARRY, F_SETDOWN))
        z = sc.lerp(CONTACT_Z + Z_LIFT, CONTACT_Z, ue)
        C = np.array([TARGET_X, TARGET_Y, z])
        A = C.copy()
        B = C.copy()
        bowl_base = C + np.array([0.0, 0.0, -CONTACT_Z])
        locked = True
    elif f <= F_RELAX:
        u = sc.ease_in_out(seg(F_SETDOWN, F_RELAX))
        z = sc.lerp(CONTACT_Z, Z_RELEASE, u)
        A = np.array([TARGET_X, TARGET_Y, z])
        B = np.array([TARGET_X, TARGET_Y, z])
        bowl_base = np.array([TARGET_X, TARGET_Y, 0.0])
    elif f <= F_HOLD_C:
        A = np.array([TARGET_X, TARGET_Y, Z_RELEASE])
        B = A.copy()
        bowl_base = np.array([TARGET_X, TARGET_Y, 0.0])
    elif f <= F_BLIFT:
        A = np.array([TARGET_X, TARGET_Y, Z_RELEASE])
        u = sc.ease_in_out(seg(F_HOLD_C, F_BLIFT))
        B = np.array([TARGET_X, TARGET_Y, sc.lerp(Z_RELEASE, Z_RELEASE + 0.012, u)])
        bowl_base = np.array([TARGET_X, TARGET_Y, 0.0])
    elif f <= F_HOLD_D:
        A = np.array([TARGET_X, TARGET_Y, Z_RELEASE])
        B = np.array([TARGET_X, TARGET_Y, Z_RELEASE + 0.012])
        bowl_base = np.array([TARGET_X, TARGET_Y, 0.0])
    elif f <= F_WITHDRAW:
        uB = sc.ease_in_out(seg(F_HOLD_D, F_WITHDRAW - 8))
        uA = sc.ease_in_out(seg(F_HOLD_D + 6, F_WITHDRAW))
        B = np.array([sc.lerp(TARGET_X, 0.85, uB),
                      sc.lerp(TARGET_Y, TARGET_Y + 0.04, uB),
                      sc.lerp(Z_RELEASE + 0.012, 0.125, uB)])
        A = np.array([sc.lerp(TARGET_X, -0.62, uA),
                      sc.lerp(TARGET_Y, TARGET_Y - 0.02, uA),
                      sc.lerp(Z_RELEASE, 0.125, uA)])
        bowl_base = np.array([TARGET_X, TARGET_Y, 0.0])
    else:
        A = np.array([-0.62, TARGET_Y - 0.02, 0.125])
        B = np.array([0.85, TARGET_Y + 0.04, 0.125])
        bowl_base = np.array([TARGET_X, TARGET_Y, 0.0])

    if locked:
        bowl_rot = R
    else:
        bowl_rot = np.identity(3)
    return {
        'bowl_loc': bowl_base,
        'bowl_rot': Matrix(bowl_rot).to_euler(),
        'A_loc': A, 'A_rot': Matrix(R if locked else np.identity(3)).to_euler(),
        'B_loc': B, 'B_rot': Matrix(R if locked else np.identity(3)).to_euler(),
        'locked': locked,
    }


def animate(objs):
    bowl, tongA, tongB = objs
    for f in range(1, FRAME_END + 1):
        p = pose_at(f)
        bowl.location = p['bowl_loc']
        bowl.rotation_euler = p['bowl_rot']
        bowl.keyframe_insert('location', frame=f)
        bowl.keyframe_insert('rotation_euler', frame=f)
        tongA.location = p['A_loc']
        tongA.rotation_euler = p['A_rot']
        tongA.keyframe_insert('location', frame=f)
        tongA.keyframe_insert('rotation_euler', frame=f)
        tongB.location = p['B_loc']
        tongB.rotation_euler = p['B_rot']
        tongB.keyframe_insert('location', frame=f)
        tongB.keyframe_insert('rotation_euler', frame=f)
    # linear interpolation (dense keys)
    for ob in objs:
        if ob.animation_data and ob.animation_data.action:
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'


# ------------------------------------------------------------------ scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_cameras_and_lights():
    sc_ = bpy.context.scene
    cam_wide = sc.add_camera('CamWide', (0.03, -0.84, 0.315), (0.03, 0.03, 0.093),
                             lens=44.0, fstop=4.5)
    cam_close = sc.add_camera('CamClose', (-0.078, -0.220, 0.138), (0.010, -0.0705, 0.039),
                              lens=88.0, fstop=7.1)
    cam_hero = sc.add_camera('CamHero', (-0.44, -0.62, 0.33), (0.055, 0.02, 0.062),
                             lens=50.0, fstop=4.5)
    cam_close2 = sc.add_camera('CamClose2', (0.104, -0.196, 0.098), (0.164, -0.017, 0.022),
                               lens=88.0, fstop=7.1)
    cam_macro = sc.add_camera('CamMacro', (-0.085, -0.190, 0.108), (0.0, -0.0695, 0.034),
                              lens=85.0, fstop=8.0)
    cam_handle = sc.add_camera('CamHandle', (-0.365, -0.185, 0.085), (-0.395, 0.0, 0.036),
                               lens=90.0, fstop=8.0)
    def key_cam(cam_obj, keys):
        import mathutils
        for (fr, loc, tgt) in keys:
            cam_obj.location = loc
            sc.look_at(cam_obj, tgt)
            cam_obj.keyframe_insert('location', frame=fr)
            cam_obj.keyframe_insert('rotation_euler', frame=fr)
            cam_obj.data.dof.focus_distance = (mathutils.Vector(tgt) - mathutils.Vector(loc)).length
            cam_obj.data.dof.keyframe_insert('focus_distance', frame=fr)

    key_cam(cam_hero, [
        (174, (-0.44, -0.62, 0.33), (0.055, 0.020, 0.062)),
        (300, (-0.36, -0.54, 0.40), (0.125, 0.045, 0.112)),
        (420, (-0.30, -0.47, 0.44), (0.175, 0.058, 0.112)),
    ])
    key_cam(cam_wide, [
        (1, (0.030, -0.840, 0.315), (0.030, 0.030, 0.093)),
        (516, (0.018, -0.812, 0.303), (0.030, 0.030, 0.091)),
    ])
    sc_ = bpy.context.scene
    sc_.camera = cam_wide
    marks = [(1, cam_wide), (126, cam_close), (174, cam_hero), (421, cam_close2),
             (466, cam_wide)]
    for fr, cam in marks:
        m = sc_.timeline_markers.new(cam.name, frame=fr)
        m.camera = cam

    sc.add_area_light('Key', (-0.52, -0.40, 0.82), (0.02, 0.0, 0.05), 120.0, 0.45,
                      color=(1.0, 0.92, 0.82), shape='RECTANGLE')
    sc.add_area_light('Fill', (0.80, -0.30, 0.45), (0.05, 0.0, 0.05), 9.0, 1.0,
                      color=(0.82, 0.90, 1.0))
    sc.add_area_light('Rim', (0.20, 0.60, 0.55), (0.05, 0.0, 0.07), 45.0, 0.35,
                      color=(1.0, 0.86, 0.68))
    # world
    world = bpy.data.worlds.new('World')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.16, 0.14, 0.12, 1.0)
    bg.inputs['Strength'].default_value = 0.10
    bpy.context.scene.world = world


def configure_render(samples=64, res=(1280, 720), use_gpu=True):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.use_motion_blur = False
    scene.render.motion_blur_shutter = 0.25
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.max_bounces = 6
    scene.cycles.transmission_bounces = 0
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 15
    scene.render.filepath = 'D:/code/vibe/antiscald/video/frames/f_'
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Punchy'
    except Exception:
        pass
    scene.view_settings.exposure = 0.0
    if use_gpu:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type = 'HIP'
            prefs.refresh_devices()
            gpu_found = False
            for d in prefs.devices:
                d.use = ('Radeon RX 9070 XT' in d.name)
                if d.use:
                    gpu_found = True
            if gpu_found:
                scene.cycles.device = 'GPU'
                print('[render] using HIP GPU')
            else:
                scene.cycles.device = 'CPU'
        except Exception as e:
            print('[render] GPU setup failed, CPU:', e)
            scene.cycles.device = 'CPU'
    else:
        scene.cycles.device = 'CPU'
    scene.render.threads_mode = 'AUTO'


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--test-frame', type=int, default=0)
    ap.add_argument('--frames', type=str, default='')
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--res', type=str, default='1280x720')
    ap.add_argument('--out', type=str, default='test.png')
    ap.add_argument('--outdir', type=str, default='D:/code/vibe/antiscald/tests')
    ap.add_argument('--exposure', type=float, default=0.0)
    ap.add_argument('--cam', type=str, default='')
    ap.add_argument('--sheet', action='store_true')
    ap.add_argument('--cpu', action='store_true')
    ap.add_argument('--blend', type=str,
                    default='D:/code/vibe/antiscald/scenes/two_clip_demo.blend')
    args = ap.parse_args(argv)

    reset_scene()
    make_materials()
    make_table_and_wall()
    bowl = build_bowl()
    tongA = build_tong('eye')
    tongB = build_tong('hook')
    animate([bowl, tongA, tongB])
    build_cameras_and_lights()
    res = tuple(int(x) for x in args.res.lower().split('x'))
    configure_render(samples=args.samples, res=res, use_gpu=not args.cpu)
    scene = bpy.context.scene
    scene.view_settings.exposure = args.exposure
    scene.frame_set(1)

    def camera_for_frame(f):
        best = None
        for m in sorted(scene.timeline_markers, key=lambda m: m.frame):
            if m.frame <= f:
                best = m.camera
        return best or scene.camera

    if (args.frames or args.test_frame) and not args.sheet:
        # camera markers would override the manual camera during still renders
        for m in list(scene.timeline_markers):
            scene.timeline_markers.remove(m)
    if args.sheet:
        os.makedirs(args.outdir, exist_ok=True)
        scene.render.use_motion_blur = False
        sheet_frames = list(range(17, FRAME_END, 22))
        for fr in sheet_frames:
            scene.frame_set(fr)
            scene.camera = camera_for_frame(fr)
            scene.render.filepath = os.path.join(args.outdir, f'sheet_{fr:04d}.png')
            bpy.ops.render.render(write_still=True)
        print('[render] sheet done', len(sheet_frames))
        return
    if args.frames:
        os.makedirs(args.outdir, exist_ok=True)
        for fr in [int(x) for x in args.frames.split(',')]:
            scene.frame_set(fr)
            scene.camera = bpy.data.objects[args.cam] if args.cam else camera_for_frame(fr)
            scene.render.filepath = os.path.join(args.outdir, f'test_f{fr:04d}.png')
            print('[cam]', fr, scene.camera.name)
            bpy.ops.render.render(write_still=True)
            print('[render] wrote', scene.render.filepath)
    elif args.test_frame:
        scene.frame_set(args.test_frame)
        scene.camera = bpy.data.objects[args.cam] if args.cam else camera_for_frame(args.test_frame)
        scene.render.filepath = args.out
        bpy.ops.render.render(write_still=True)
        print('[render] wrote', args.out)
    else:
        os.makedirs(os.path.dirname(args.blend), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=args.blend)
        print('[scene] saved', args.blend)


if __name__ == '__main__':
    main()
