import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='D:/code/vibe/antiscald/print/print_parts.blend')
sc = bpy.context.scene
for o in bpy.data.objects:
    o.scale = (0.001, 0.001, 0.001)
cam = bpy.data.cameras.new('C'); co = bpy.data.objects.new('C', cam)
sc.collection.objects.link(co); sc.camera = co
co.location = Vector((0.07, -0.66, 0.40))
target = Vector((0.0, 0.0, 0.09))
co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
cam.lens = 50; cam.clip_start = 0.01
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'RANDOM'
sc.display.shading.show_shadows = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 860
sc.render.filepath = 'D:/code/vibe/antiscald/tests/print_preview.png'
bpy.ops.render.render(write_still=True)
print('[prev] done')
