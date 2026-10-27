"""Quick quality/speed test: load saved blend, override engine/settings, render still."""
import sys
import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
opts = {}
for a in argv:
    if '=' in a:
        k, v = a.split('=', 1)
        opts[k] = v

bpy.ops.wm.open_mainfile(filepath=opts.get('blend', 'D:/code/vibe/antiscald/scenes/two_clip_demo.blend'))
scene = bpy.context.scene
for m in list(scene.timeline_markers):
    scene.timeline_markers.remove(m)

frame = int(opts.get('frame', 132))
engine = opts.get('engine', 'EEVEE')
res = opts.get('res', '1280x720')
rx, ry = [int(x) for x in res.split('x')]
scene.render.resolution_x, scene.render.resolution_y = rx, ry
scene.render.resolution_percentage = 100

if engine == 'EEVEE':
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    ee = scene.eevee
    ee.taa_render_samples = int(opts.get('samples', 64))
    for attr, val in (('use_raytracing', True), ('use_shadows', True),
                      ('use_shadow_jitter', True), ('shadow_jitter_overblur', 10.0),
                      ('use_fast_gi', True)):
        try:
            setattr(ee, attr, val)
        except Exception as e:
            print('eevee attr', attr, e)
    try:
        ee.ray_tracing_options.resolution_scale = '1'
        ee.ray_tracing_options.trace_max_roughness = 0.5
    except Exception as e:
        print('rt opts', e)
    try:
        ee.use_gtao = True
    except Exception:
        pass
else:
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = int(opts.get('samples', 24))
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = float(opts.get('adaptive', 0.03))
    scene.cycles.max_bounces = int(opts.get('bounces', 6))
    scene.cycles.transmission_bounces = 0
    scene.render.use_motion_blur = opts.get('mblur', '0') == '1'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'HIP'
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = 'Radeon RX 9070 XT' in d.name
    scene.cycles.device = 'GPU'

# camera by markers (re-add logic): choose explicit cam if given
cam = opts.get('cam', '')
if cam:
    scene.camera = bpy.data.objects[cam]
else:
    # emulate marker: pick camera from original markers by name/frames
    best = None
    for name, fr in [('CamWide', 1), ('CamClose', 126), ('CamHero', 174),
                     ('CamClose2', 421), ('CamWide', 466)]:
        if frame >= fr:
            best = name
    scene.camera = bpy.data.objects[best or 'CamWide']

scene.frame_set(frame)
scene.render.filepath = opts.get('out', 'D:/code/vibe/antiscald/tests/quick.png')
scene.view_settings.exposure = float(opts.get('exposure', -1.1))
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print('[quick] wrote', scene.render.filepath)
