"""Render high quality still frames for the design sheet / delivery."""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opts = {}
for a in argv:
    if '=' in a:
        k, v = a.split('=', 1)
        opts[k] = v

bpy.ops.wm.open_mainfile(filepath='D:/code/vibe/antiscald/scenes/two_clip_demo.blend')
scene = bpy.context.scene
for m in list(scene.timeline_markers):
    scene.timeline_markers.remove(m)
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'HIP'
prefs.refresh_devices()
for dev in prefs.devices:
    dev.use = 'Radeon RX 9070 XT' in dev.name
scene.cycles.device = 'GPU'
scene.cycles.samples = int(opts.get('samples', 128))
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 0
scene.render.use_motion_blur = False
scene.view_settings.exposure = -1.1
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 10

OUT = 'D:/code/vibe/antiscald/design'
os.makedirs(OUT, exist_ok=True)

jobs = [
    (160, 'CamMacro', 'joint_macro.png', 1600, 1000),
    (120, 'CamClose', 'joint_separated.png', 1600, 1000),
    (320, 'CamHero', 'hero_lift.png', 1600, 900),
    (108, 'CamWide', 'assembled_table.png', 1600, 900),
]
for (fr, cam, name, rx, ry) in jobs:
    scene.frame_set(fr)
    scene.camera = bpy.data.objects[cam]
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print('[stills] wrote', scene.render.filepath)
print('[stills] done')
