"""Render the animation with explicit Cycles GPU setup (prefs are not stored in .blend)."""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
opts = {}
for a in argv:
    if '=' in a:
        k, v = a.split('=', 1)
        opts[k] = v

BLEND = opts.get('blend', 'D:/code/vibe/antiscald/scenes/two_clip_demo.blend')
OUT = opts.get('out', 'D:/code/vibe/antiscald/video/frames/f_')
START = int(opts.get('start', 1))
END = int(opts.get('end', 516))
RES = opts.get('res', '1280x720')
SAMPLES = int(opts.get('samples', 32))

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
rx, ry = [int(x) for x in RES.split('x')]
scene.render.resolution_x, scene.render.resolution_y = rx, ry
scene.render.resolution_percentage = 100
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.03
scene.cycles.max_bounces = 6
scene.cycles.transmission_bounces = 0
scene.render.use_motion_blur = False
scene.render.threads_mode = 'AUTO'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 15
scene.render.filepath = OUT
scene.render.use_file_extension = True

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'HIP'
prefs.refresh_devices()
gpu = False
for d in prefs.devices:
    d.use = 'Radeon RX 9070 XT' in d.name
    if d.use:
        gpu = True
scene.cycles.device = 'GPU' if gpu else 'CPU'
print('[anim] device:', 'GPU' if gpu else 'CPU', 'samples', SAMPLES,
      'res', RES, 'frames', START, END)

# render frames one by one, skipping existing
for f in range(START, END + 1):
    path = f'{OUT}{f:04d}.png'
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        continue
    scene.frame_set(f)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('[anim] frame', f, flush=True)
print('[anim] done')
