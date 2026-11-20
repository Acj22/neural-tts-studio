import sys
from pathlib import Path
repo_root = r"C:\Users\angel.cruz\.gemini\antigravity\scratch\neural-tts-studio"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import bpy
from mathutils import Vector
from studio.blender.educational_vertical_framework import (
    Educational916FrameworkConfig,
    setup_educational_scene_base,
)
from studio.blender.models_library.turbocharger_specialized import (
    build_specialized_turbocharger_model,
    generate_turbo_adaptive_labels,
    animate_turbo_vertical_showcase,
)

cfg = Educational916FrameworkConfig()
cfg.render_width = 720
cfg.render_height = 1280

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
    for item in list(coll):
        coll.remove(item, do_unlink=True)

scene_info = setup_educational_scene_base(cfg)
cam_obj = scene_info["camera"]

model_data = build_specialized_turbocharger_model(center_z=1.25)
cam_pos = Vector((2.4, -4.0, 2.3))
cam_target = Vector((0.0, 0.0, 1.25))
cam_obj.location = cam_pos
cam_obj.rotation_euler = (cam_target - cam_pos).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

labels_dict = generate_turbo_adaptive_labels(model_data, cam_pos, cam_target, cfg)
animate_turbo_vertical_showcase(model_data, cam_obj, cfg, labels_dict=labels_dict)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE" if hasattr(scene.render, "engine") else "BLENDER_EEVEE_NEXT"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 720
scene.render.resolution_y = 1280

if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 6

# Renderizar cuadro de Stage 2 (frame 500)
scene.frame_set(500)
scene.render.filepath = r"C:\Users\angel.cruz\.gemini\antigravity\scratch\neural-tts-studio\projects\showcase_turbocharger_vertical_9_16\preview_st2_fixed.png"
bpy.ops.render.render(write_still=True)

# Renderizar cuadro de Stage 6 (frame 2000)
scene.frame_set(2000)
scene.render.filepath = r"C:\Users\angel.cruz\.gemini\antigravity\scratch\neural-tts-studio\projects\showcase_turbocharger_vertical_9_16\preview_st6_fixed.png"
bpy.ops.render.render(write_still=True)
print("Preview renders completed successfully!")
