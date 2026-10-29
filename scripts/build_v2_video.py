"""V2 video: taking a bowl out of a pot with the raised-handle clip pair.

Builds the pot scene (cut-away pot), raised-handle clips with an animated
elastic U-ring flex shape key, animates the whole operation and saves the blend.

Run:
  blender -b --factory-startup --python scripts/build_v2_video.py -- [--test]
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import build_scene as bs
import scene_common as sc

ROOT = 'D:/code/vibe/antiscald'
BLEND_OUT = os.path.join(ROOT, 'scenes', 'two_clip_v2_demo.blend')
FRAME_END = 500
FPS = 24

# pot
POT_R = 0.140          # inner radius
POT_DEPTH = 0.140
POT_WALL = 0.0025
POT_CUT = math.radians(100.0)   # opening facing -y

# ring elastic flex
FLEX_DR = 0.030        # max radial expansion of the wire centreline (m)
BOWL_RIM_Z = 0.0828
CONTACT_Z = bs.CONTACT_Z
RING_Z0 = bs.RING_Z0
B_HOVER = bs.B_HOVER
Z_LIFT = 0.160
TARGET_X = 0.300

# animation frames
F_TITLE = 30
F_A0, F_A1 = 34, 116
F_B0, F_B1 = 120, 198
F_ENG0, F_ENG1 = 202, 228
F_HOLD1 = 240
F_TAKE0, F_TAKE1 = 240, 258
F_LIFT0, F_LIFT1 = 262, 312
F_CARRY0, F_CARRY1 = 312, 372
F_SET0, F_SET1 = 372, 396
F_RELAX0, F_RELAX1 = 396, 410
F_UNH0, F_UNH1 = 410, 428
F_WD0, F_WD1 = 428, 460
F_END = FRAME_END


# ------------------------------------------------------------------ pot
def pot_profile():
    ri, d, w = POT_R, POT_DEPTH, POT_WALL
    return [(0.0, 0.0), (ri * 0.94, 0.0), (ri - 0.004, 0.004), (ri, 0.011),
            (ri, d - 0.004), (ri + 0.0004, d), (ri + w + 0.0008, d + 0.0016),
            (ri + w + 0.0008, d - 0.0016), (ri + w, d - 0.007), (ri + w, 0.007),
            (ri + 0.003, -0.0015), (ri * 0.9, -0.004), (0.0, -0.004)]


def build_pot():
    prof = pot_profile()
    n_th = 150
    a0 = -math.pi / 2 + POT_CUT / 2
    a1 = a0 + 2 * math.pi - POT_CUT
    verts, faces = [], []
    n_p = len(prof)
    for i in range(n_th + 1):
        a = a0 + (a1 - a0) * i / n_th
        ca, sa = math.cos(a), math.sin(a)
        for (r, z) in prof:
            verts.append((r * ca, r * sa, z))
    for i in range(n_th):
        for j in range(n_p - 1):
            a = i * n_p + j
            b = i * n_p + j + 1
            c = (i + 1) * n_p + j + 1
            d = (i + 1) * n_p + j
            faces.append((a, b, c, d))
    # cut caps
    for i in (0, n_th):
        ring = [Vector(verts[i * n_p + j]) for j in range(n_p)]
        tris = tessellate_polygon([ring])
        for t in tris:
            faces.append(tuple(i * n_p + int(k) for k in t))
    me = bpy.data.meshes.new('PotV2')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    ob = bpy.data.objects.new('PotV2', me)
    bpy.context.scene.collection.objects.link(ob)
    mat = sc.principled('PotSteelV2', base=(0.52, 0.535, 0.55, 1), metallic=1.0,
                        roughness=0.30)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


# ------------------------------------------------------------------ flex shape key
def bowl_radius_at(z):
    pts = np.array(bs.BOWL_OUTER)          # (r, z)
    if z <= pts[0, 1]:
        return float(pts[0, 0])
    if z >= pts[-1, 1]:
        return float(pts[-1, 0])
    return float(np.interp(z, pts[:, 1], pts[:, 0]))


def flex_dr(z_ring):
    """Radial expansion needed for the ring at height z_ring above the bowl base."""
    if z_ring >= BOWL_RIM_Z:
        r = 0.0868
    else:
        r = bowl_radius_at(z_ring)
    return max(0.0, r + 0.0012 - (bs.R_IN - bs.WIRE_R))


def add_flex_key(obj):
    me = obj.data
    obj.shape_key_add(name='Basis', from_mix=False)
    kb = obj.shape_key_add(name='Flex', from_mix=False)
    for i, v in enumerate(me.vertices):
        x, y, z = v.co
        if z > 0.05:
            kb.data[i].co = (x - FLEX_DR, y, z)
            continue
        r = math.hypot(x, y)
        if r < 0.03:
            kb.data[i].co = (x - FLEX_DR, y, z)
        else:
            kb.data[i].co = (x + x / r * FLEX_DR, y + y / r * FLEX_DR, z)
    return kb


# ------------------------------------------------------------------ pose
def seg(f, f0, f1):
    if f1 <= f0:
        return 1.0 if f >= f1 else 0.0
    return min(1.0, max(0.0, (f - f0) / (f1 - f0)))


def pose_at(f):
    def ez(f0, f1):
        return sc.ease_in_out(seg(f, f0, f1))

    bowl = np.zeros(3)
    A = np.array([0.0, 0.0, 0.44])
    B = np.array([0.0, 0.0, 0.44])
    rotB = np.identity(3)
    rotA = np.identity(3)
    if f <= F_A0:
        A[2] = 0.44
        B[2] = 0.44
    elif f <= F_A1:
        u = ez(F_A0, F_A1)
        A[2] = sc.lerp(0.44, RING_Z0, u)
        B[2] = 0.44
    elif f <= F_B0:
        A[2] = RING_Z0
        B[2] = 0.44
    elif f <= F_B1:
        u = ez(F_B0, F_B1)
        A[2] = RING_Z0
        B[2] = sc.lerp(0.44, RING_Z0 + B_HOVER, u)
    elif f <= F_ENG0:
        A[2] = RING_Z0
        B[2] = RING_Z0 + B_HOVER
    elif f <= F_ENG1:
        u = ez(F_ENG0, F_ENG1)
        A[2] = RING_Z0
        B[2] = sc.lerp(RING_Z0 + B_HOVER, RING_Z0, u)
    elif f <= F_HOLD1:
        A[2] = B[2] = RING_Z0
    elif f <= F_TAKE1:
        u = ez(F_TAKE0, F_TAKE1)
        A[2] = B[2] = sc.lerp(RING_Z0, CONTACT_Z, u)
    elif f <= F_LIFT1:
        u = ez(F_LIFT0 + 4, F_LIFT1)
        bowl[2] = sc.lerp(0.0, Z_LIFT, u)
        A[2] = B[2] = bowl[2] + CONTACT_Z
    elif f <= F_CARRY0:
        bowl[2] = Z_LIFT
        A[2] = B[2] = Z_LIFT + CONTACT_Z
    elif f <= F_CARRY1:
        u = ez(F_CARRY0, F_CARRY1)
        bowl[0] = sc.lerp(0.0, TARGET_X, u)
        bowl[2] = Z_LIFT + 0.002 * math.sin(math.pi * u)
        yaw = 0.020 * math.sin(math.pi * u)
        tilt = -0.010 * math.sin(math.pi * u)
        rotA = np.array(Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'Y'))
        rotB = rotA.copy()
        A[:] = bowl + np.array([0.0, 0.0, CONTACT_Z])
        B[:] = A.copy()
    elif f <= F_SET1:
        u = ez(F_SET0, F_SET1)
        bowl[0] = TARGET_X
        bowl[2] = sc.lerp(Z_LIFT, 0.0, u)
        A[0] = B[0] = TARGET_X
        A[2] = B[2] = bowl[2] + CONTACT_Z
    elif f <= F_RELAX1:
        u = ez(F_RELAX0, F_RELAX1)
        bowl[0] = TARGET_X
        A[0] = B[0] = TARGET_X
        A[2] = B[2] = sc.lerp(CONTACT_Z, RING_Z0, u)
    elif f <= F_UNH0:
        bowl[0] = TARGET_X
        A[0] = B[0] = TARGET_X
        A[2] = B[2] = RING_Z0
    elif f <= F_UNH1:
        u = ez(F_UNH0, F_UNH1)
        bowl[0] = TARGET_X
        A[0] = B[0] = TARGET_X
        A[2] = RING_Z0
        B[2] = RING_Z0 + 0.012 * u
    elif f <= F_WD1:
        u = ez(F_UNH1, F_WD1)
        bowl[0] = TARGET_X
        A[0] = sc.lerp(TARGET_X, TARGET_X - 0.115, u)
        B[0] = sc.lerp(TARGET_X, TARGET_X + 0.115, u)
        A[2] = RING_Z0 + 0.020 * u
        B[2] = RING_Z0 + 0.012 + 0.020 * u
    else:
        bowl[0] = TARGET_X
        A[0] = TARGET_X - 0.115
        B[0] = TARGET_X + 0.115
        A[2] = RING_Z0 + 0.020
        B[2] = RING_Z0 + 0.032
    # elastic flex for each ring (depends on ring height above the bowl base)
    drA = flex_dr(A[2] - bowl[2])
    drB = flex_dr(B[2] - bowl[2])
    flexA = min(1.0, drA / FLEX_DR)
    flexB = min(1.0, drB / FLEX_DR)
    return dict(bowl_loc=Vector(bowl), bowl_rot=_euler(rotA),
                A_loc=Vector(A), A_rot=_euler(rotA),
                B_loc=Vector(B), B_rot=_euler(rotB),
                flexA=flexA, flexB=flexB)


def _euler(R):
    if np.allclose(R, np.identity(3)):
        return (0.0, 0.0, 0.0)
    m = Matrix([list(r) for r in R])
    return tuple(m.to_euler())


# ------------------------------------------------------------------ cameras / lights
def build_cameras():
    sc_ = bpy.context.scene
    c1 = sc.add_camera('CamPotWide', (-0.46, -0.80, 0.60), (0.0, 0.005, 0.16),
                       lens=38.0, fstop=5.0)
    c2 = sc.add_camera('CamPotClose', (-0.105, -0.415, 0.165), (-0.004, -0.058, 0.040),
                       lens=66.0, fstop=7.1)
    c5 = sc.add_camera('CamSnap', (-0.30, -0.44, 0.30), (-0.03, 0.00, 0.13),
                       lens=50.0, fstop=6.3)
    c3 = sc.add_camera('CamLift', (0.52, -0.88, 0.44), (0.14, 0.01, 0.20),
                       lens=40.0, fstop=5.0)
    c4 = sc.add_camera('CamPotEnd', (0.46, -0.74, 0.30), (0.255, 0.01, 0.085),
                       lens=46.0, fstop=5.0)
    return c1, c2, c3, c4, c5


def add_lights():
    sc.add_area_light('PotKey', (0.25, -0.55, 0.85), (0.0, 0.0, 0.10), 70.0, 0.5,
                      color=(1.0, 0.96, 0.90), shape='RECTANGLE')
    sc.add_area_light('PotFill', (-0.55, -0.30, 0.50), (0.0, 0.0, 0.15), 22.0, 0.6,
                      color=(0.86, 0.90, 1.0))
    sc.add_area_light('PotTop', (0.0, 0.02, 0.62), (0.0, 0.0, 0.02), 40.0, 0.30,
                      color=(1.0, 0.97, 0.92), shape='DISK')
    sc.add_area_light('PotLowFill', (-0.45, -0.58, 0.08), (0.0, 0.0, 0.06), 20.0, 0.5,
                      color=(1.0, 0.95, 0.88))


def configure_render():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.max_bounces = 6
    scene.cycles.transmission_bounces = 0
    scene.render.use_motion_blur = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -1.1
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 15
    try:
        w = bpy.data.worlds[0]
        w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25
    except Exception:
        pass
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_END


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    bs.RAISED_HANDLE = True
    bs.reset_scene()
    bs.make_materials()
    bs.make_table_and_wall()
    bowl = bs.build_bowl()
    tongA = bs.build_tong('eye')
    tongB = bs.build_tong('hook')
    pot = build_pot()
    kbA = add_flex_key(tongA)
    kbB = add_flex_key(tongB)
    bs.build_cameras_and_lights()
    cams = build_cameras()
    add_lights()
    configure_render()
    # timeline markers: camera cuts
    for m in list(bpy.context.scene.timeline_markers):
        bpy.context.scene.timeline_markers.remove(m)
    for (f, cam) in ((1, cams[0]), (84, cams[4]), (118, cams[0]), (164, cams[4]),
                     (196, cams[1]), (236, cams[2]), (F_SET0, cams[3])):
        mk = bpy.context.scene.timeline_markers.new('cam', frame=f)
        mk.camera = cam
    bpy.context.scene.camera = cams[0]
    # animate
    for f in range(1, FRAME_END + 1):
        p = pose_at(f)
        bowl.location = p['bowl_loc']
        bowl.rotation_euler = p['bowl_rot']
        bowl.keyframe_insert('location', frame=f)
        bowl.keyframe_insert('rotation_euler', frame=f)
        for ob, lk, rk, fk in ((tongA, 'A_loc', 'A_rot', 'flexA'),
                               (tongB, 'B_loc', 'B_rot', 'flexB')):
            ob.location = p[lk]
            ob.rotation_euler = p[rk]
            ob.keyframe_insert('location', frame=f)
            ob.keyframe_insert('rotation_euler', frame=f)
            kb = ob.data.shape_keys.key_blocks['Flex']
            kb.value = p[fk]
            kb.keyframe_insert('value', frame=f)
    for ob in (bowl, tongA, tongB):
        if ob.animation_data and ob.animation_data.action:
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
    if tongA.data.shape_keys and tongA.data.shape_keys.animation_data:
        for fc in tongA.data.shape_keys.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    if tongB.data.shape_keys and tongB.data.shape_keys.animation_data:
        for fc in tongB.data.shape_keys.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print('[v2v] saved', BLEND_OUT, flush=True)

    if '--test' in argv:
        scene = bpy.context.scene
        scene.render.resolution_percentage = 60
        scene.cycles.samples = 16
        for f in (1, 96, 215, 290, 440):
            scene.frame_set(f)
            scene.render.filepath = os.path.join(ROOT, 'tests', f'v2v_test_{f:04d}.png')
            bpy.ops.render.render(write_still=True)
            print('[v2v] test frame', f, flush=True)


if __name__ == '__main__':
    main()
