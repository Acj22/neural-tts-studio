import bpy, sys, math
from mathutils import Vector
sys.path.insert(0, r"C:\Users\angel.cruz\.gemini\antigravity\scratch\neural-tts-studio")

from studio.blender.educational_vertical_framework import (
    Educational916FrameworkConfig,
    setup_educational_scene_base,
)
from studio.blender.models_library.turbocharger_specialized import (
    build_specialized_turbocharger_model,
)

cfg = Educational916FrameworkConfig()
cfg.render_width = 720
cfg.render_height = 1280

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
    for item in list(coll):
        coll.remove(item, do_unlink=True)

scene_info = setup_educational_scene_base(cfg)
cam_obj = scene_info["camera"]

model_data = build_specialized_turbocharger_model(center_z=1.25)

# Cámara de Stage 3 (lado caliente / turbina donde se tomó la foto del usuario)
az = math.radians(50.0)
el = math.radians(18.0)
dist = 2.7
tgt = Vector((0.35, -0.05, 1.25))
d_vec = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
pos = tgt + d_vec * dist
cam_obj.location = pos
cam_obj.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
cam_obj.data.lens = 48.0

scene = bpy.context.scene
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 720
scene.render.resolution_y = 1280
scene.render.filepath = r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a\preview_turbo_stage3_clean_cutaway.png"

bpy.ops.render.render(write_still=True)
print("TEST RENDER FINISHED SUCCESSFULLY")
