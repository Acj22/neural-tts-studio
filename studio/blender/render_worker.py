"""Trabajador de renderizado headless para Blender 5.3+ (Fase 3.1).

1. Parsea la especificación JSON de la escena.
2. Construye el modelo procedural especializado y aplica la animación de la fase.
3. Control de calidad previo (componentes requeridos, conexiones mecánicas).
4. Cámara por plan del Director Visual Especializado con encuadre automático (sin cortes).
5. Renderiza la secuencia PNG con EEVEE y escribe status.json con el informe de QC.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import bpy
except ImportError:
    bpy = None

from studio.blender.models_library.combustion_engine import create_combustion_engine_3d
from studio.blender.models_library.automatic_transmission import (
    create_automatic_transmission_3d,
    build_transmission_keyframes,
)
from studio.blender.models_library.refrigerator_cycle import (
    create_refrigerator_cycle_3d,
    build_refrigerator_keyframes,
)
from studio.blender.models_library.printer_3d_fdm import (
    create_printer_3d_3d,
    build_printer_3d_keyframes,
)
from studio.blender.animation_controller import build_4_stroke_cycle_keyframes
from studio.blender.camera_director import setup_studio_lighting, setup_camera_for_shot
from studio.blender.camera_plans import apply_camera_plan
from studio.blender.model_qc import check_required, check_connections
from studio.blender.render_profiles import get_render_profile


def clean_blender_scene() -> None:
    if bpy is None:
        return
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)


def run_blender_render(spec: dict) -> None:
    if bpy is None:
        raise RuntimeError("No se puede ejecutar fuera de Blender.")

    clean_blender_scene()

    profile_key = spec.get("render_profile", "production")
    profile = get_render_profile(profile_key)
    output_dir = Path(spec["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    single_frame = bool(spec.get("single_frame_only", False))

    width = int(spec.get("width") or profile.get("width", 1080))
    height = int(spec.get("height") or profile.get("height", 1920))
    fps = int(profile.get("fps") or spec.get("fps", 24))
    duration_sec = float(spec.get("duration_sec", 4.0))
    composition_type = spec.get("composition_type", "hero_view")
    cycle_phase = spec.get("cycle_phase", "full_cycle")
    camera_plan = spec.get("camera_plan")

    is_vertical = height > width
    total_frames = 1 if single_frame else max(10, int(round(duration_sec * fps)))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = int(profile.get("resolution_scale", 100))
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames

    if hasattr(scene, "eevee"):
        samples_val = int(profile.get("samples", 16))
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = max(samples_val, int(spec.get("min_samples", 2)))
        if hasattr(scene.eevee, "use_shadows"):
            scene.eevee.use_shadows = True
        is_fast_preview = profile_key in ("test", "draft") or samples_val <= 8
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = not is_fast_preview
        if hasattr(scene.eevee, "use_fast_gi"):
            scene.eevee.use_fast_gi = True

    setup_studio_lighting()

    model_type = spec.get("model_type", "combustion_engine")
    highlight_comp = spec.get("highlight_component")
    data = {}
    qc: dict = {"model_type": model_type, "phase": cycle_phase}

    if model_type == "automatic_transmission":
        data = create_automatic_transmission_3d(center_z=2.0)
        build_transmission_keyframes(trans_data=data, start_frame=1, end_frame=total_frames,
                                     scene_phase=cycle_phase, highlight_component=highlight_comp)
    elif model_type == "refrigerator_cycle":
        data = create_refrigerator_cycle_3d(center_z=2.2)
        build_refrigerator_keyframes(fridge_data=data, start_frame=1, end_frame=total_frames,
                                     scene_phase=cycle_phase, highlight_component=highlight_comp)
    elif model_type == "printer_3d_fdm":
        data = create_printer_3d_3d(center_z=2.0)
        build_printer_3d_keyframes(printer_data=data, start_frame=1, end_frame=total_frames,
                                   scene_phase=cycle_phase, highlight_component=highlight_comp)
    else:
        data = create_combustion_engine_3d(crank_radius=1.0, rod_length=3.6, cylinder_radius=1.30,
                                           piston_height=1.45, crank_center_z=0.0)
        build_4_stroke_cycle_keyframes(engine_data=data, start_frame=1, end_frame=total_frames,
                                       cycle_phase=cycle_phase, highlight_component=highlight_comp)

    # QC previo (se evalúa en el fotograma 1 ensamblado antes de posibles despieces axiales)
    qc["components"] = check_required(model_type, data)
    qc["connections"] = check_connections(data, frame=1) if data.get("connections") else {"checks": [], "ok": True}

    # Cámara
    if camera_plan:
        qc["camera"] = apply_camera_plan(camera_plan, data, width, height, 1, total_frames)
    else:
        setup_camera_for_shot(shot_type=composition_type, is_vertical=is_vertical, start_frame=1, end_frame=total_frames)
        qc["camera"] = {"shot": composition_type, "note": "cámara heredada (sin plan)"}

    scene.frame_set(1)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_dir / "frame_")

    print(f"[BLENDER_WORKER] Renderizando {total_frames} fotogramas a {width}x{height} ({profile_key}) fase={cycle_phase}")
    if single_frame:
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)

    (output_dir / "status.json").write_text(
        json.dumps({"success": True, "total_frames": total_frames, "width": width, "height": height, "fps": fps,
                    "render_profile": profile_key, "composition_type": composition_type,
                    "cycle_phase": cycle_phase, "qc": qc}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"[BLENDER_WORKER] Completado: {output_dir}")


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        idx = argv.index("--") + 1
        if idx < len(argv):
            spec_file = Path(argv[idx])
            if spec_file.is_file():
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_data = json.load(f)
                run_blender_render(spec_data)
                sys.exit(0)
    print("Error: Se requiere una ruta a un archivo de especificación JSON tras '--'.")
    sys.exit(1)
