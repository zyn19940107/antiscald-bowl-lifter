"""Build the raised-handle (v2) variant and render stills (clip pair, pot scene, detail,
flat-vs-raised elevation comparison).

Run:
  blender -b --factory-startup --python scripts/build_v2.py -- [--flat]
"""
import math
import os
import sys

import bpy
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import build_scene as bs
import scene_common as sc

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RAISED = '--flat' not in argv
ONLY = ''
for a in argv:
    if a.startswith('only='):
        ONLY = a.split('=', 1)[1]

bs.RAISED_HANDLE = RAISED
OUT = 'D:/code/vibe/antiscald/design'
os.makedirs(OUT, exist_ok=True)


def build_pot():
    prof = [
        (0.000, 0.0000), (0.1180, 0.0000), (0.1235, 0.0035), (0.1250, 0.0120),
        (0.1250, 0.1355), (0.1255, 0.1400), (0.1280, 0.1418), (0.1282, 0.1385),
        (0.1276, 0.0070), (0.1240, 0.0005), (0.1100, -0.0040), (0.000, -0.0040),
    ]
    v, f, _ = sc.lathe_data(prof, 128, lambda i: 0)
    me = bpy.data.meshes.new('Pot')
    me.from_pydata([tuple(x) for x in v], [], f)
    me.validate()
    ob = bpy.data.objects.new('Pot', me)
    bpy.context.scene.collection.objects.link(ob)
    mat = sc.principled('PotSteel', base=(0.55, 0.56, 0.58, 1), metallic=1.0,
                        roughness=0.28)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def configure(samples=80, res=(1600, 1000)):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'HIP'
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = 'Radeon RX 9070 XT' in d.name
    scene.cycles.device = 'GPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.max_bounces = 6
    scene.cycles.transmission_bounces = 0
    scene.render.use_motion_blur = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -1.1
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 10
    for m in list(scene.timeline_markers):
        scene.timeline_markers.remove(m)


def cam(name, loc, target, lens=50.0, fstop=5.6):
    c = sc.add_camera(name, loc, target, lens=lens, fstop=fstop)
    return c


def render(camera, path, res=(1600, 1000), samples=80):
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.cycles.samples = samples
    scene.render.filepath = path
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print('[v2] wrote', path, flush=True)


def main():
    bs.reset_scene()
    bs.make_materials()
    bs.make_table_and_wall()
    bowl = bs.build_bowl()
    tongA = bs.build_tong('eye')
    tongB = bs.build_tong('hook')
    pot = build_pot()
    pot.hide_render = True

    p = bs.pose_at(150)
    bowl.location = p['bowl_loc']
    bowl.rotation_euler = p['bowl_rot']
    tongA.location = p['A_loc']
    tongA.rotation_euler = p['A_rot']
    tongB.location = p['B_loc']
    tongB.rotation_euler = p['B_rot']
    bs.build_cameras_and_lights()
    configure()

    if 'save' in ONLY or '--save' in argv:
        out = 'D:/code/vibe/antiscald/scenes/two_clip_v2.blend'
        bpy.ops.wm.save_as_mainfile(filepath=out)
        print('[v2] saved', out, flush=True)

    if ONLY == 'save':
        print('[v2] done save')
        return

    if not ONLY or 'pair' in ONLY:
        c = cam('V2Pair', (0.36, -0.64, 0.36), (0.0, 0.01, 0.13), lens=50.0, fstop=5.0)
        render(c, os.path.join(OUT, 'v2_clip_pair.png'), (1600, 1000), 96)

    if not ONLY or 'elev' in ONLY:
        c = cam('V2Elev', (0.02, -0.98, 0.115), (0.0, 0.0, 0.105), lens=55.0, fstop=6.3)
        name = 'compare_raised.png' if RAISED else 'compare_flat.png'
        render(c, os.path.join(OUT, name), (1600, 900), 80)

    if RAISED and (not ONLY or 'pot' in ONLY):
        pot.hide_render = False
        c = cam('V2Pot', (0.40, -0.52, 0.52), (0.0, 0.015, 0.115), lens=45.0, fstop=6.3)
        render(c, os.path.join(OUT, 'v2_pot_scene.png'), (1600, 1100), 96)
        c2 = cam('V2PotLow', (0.34, -0.62, 0.28), (0.0, 0.01, 0.15), lens=55.0, fstop=5.6)
        render(c2, os.path.join(OUT, 'v2_pot_scene_low.png'), (1600, 1000), 96)
        pot.hide_render = True

    if RAISED and (not ONLY or 'detail' in ONLY):
        c = cam('V2Detail', (-0.34, -0.36, 0.26), (-0.13, 0.0, 0.115), lens=70.0, fstop=6.3)
        render(c, os.path.join(OUT, 'v2_handle_detail.png'), (1600, 1000), 96)
    print('[v2] done', 'raised' if RAISED else 'flat')


if __name__ == '__main__':
    main()
