"""Trabajador de renderizado headless para Blender 5.3+ (Fase 4 y 5).

Se ejecuta dentro del intérprete de Blender (-b) para:
1. Parsear la especificación de escena (JSON).
2. Construir la escena procedural (modelo 3D, luces, materiales maqueta).
3. Configurar animación cinemática y cámara inteligente.
4. Renderizar la secuencia de fotogramas PNG optimizada con EEVEE Next.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# Agregar directorio raíz al sys.path para importar módulos de studio
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import bpy
except ImportError:
    bpy = None

from studio.blender.materials import setup_engine_materials
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
from studio.blender.render_profiles import get_render_profile


def clean_blender_scene() -> None:
    """Elimina todos los objetos, mallas, cámaras y luces por defecto."""
    if bpy is None:
        return
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam, do_unlink=True)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)


def run_blender_render(spec: dict) -> None:
    """Construye y renderiza la escena 3D según la especificación."""
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

    is_vertical = height > width
    total_frames = 1 if single_frame else max(10, int(round(duration_sec * fps)))

    # 1. Configurar Motor de Render y Parámetros
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = int(profile.get("resolution_scale", 100))
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames

    # EEVEE Next sampling, trazado de rayos y sombras suaves
    if hasattr(scene, "eevee"):
        samples_val = int(profile.get("samples", 16))
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples_val
        if hasattr(scene.eevee, "use_shadows"):
            scene.eevee.use_shadows = True
        # En perfiles rápidos de preview desactivamos trazado pesado de rayos para acelerar x10 en Iris Xe
        is_fast_preview = profile_key in ("test", "draft") or samples_val <= 8
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = not is_fast_preview
        if hasattr(scene.eevee, "use_fast_gi"):
            scene.eevee.use_fast_gi = True

    # 2. Iluminación de Estudio y Fondo
    setup_studio_lighting()

    # 3. Construcción del Modelo 3D según el tema especificado (Fase 3 Multi-Modelo)
    model_type = spec.get("model_type", "combustion_engine")
    highlight_comp = spec.get("highlight_component")

    if model_type == "automatic_transmission":
        trans_data = create_automatic_transmission_3d(center_z=2.0)
        build_transmission_keyframes(
            trans_data=trans_data,
            start_frame=1,
            end_frame=total_frames,
            scene_phase=cycle_phase,
            highlight_component=highlight_comp,
        )
    elif model_type == "refrigerator_cycle":
        fridge_data = create_refrigerator_cycle_3d(center_z=2.2)
        build_refrigerator_keyframes(
            fridge_data=fridge_data,
            start_frame=1,
            end_frame=total_frames,
            scene_phase=cycle_phase,
            highlight_component=highlight_comp,
        )
    elif model_type == "printer_3d_fdm":
        printer_data = create_printer_3d_3d(center_z=2.0)
        build_printer_3d_keyframes(
            printer_data=printer_data,
            start_frame=1,
            end_frame=total_frames,
            scene_phase=cycle_phase,
            highlight_component=highlight_comp,
        )
    else:
        # Default: Motor de 4 Tiempos (Fase 2.1 & 2.3)
        engine_data = create_combustion_engine_3d(
            crank_radius=1.0,
            rod_length=3.6,
            cylinder_radius=1.30,
            piston_height=1.40,
            crank_center_z=0.0,
        )
        build_4_stroke_cycle_keyframes(
            engine_data=engine_data,
            start_frame=1,
            end_frame=total_frames,
            cycle_phase=cycle_phase,
            highlight_component=highlight_comp,
        )

    # 5. Cámara Cinemática Inteligente
    setup_camera_for_shot(
        shot_type=composition_type,
        is_vertical=is_vertical,
        start_frame=1,
        end_frame=total_frames,
    )

    # 6. Renderizado
    scene.render.image_settings.file_format = "PNG"
    render_prefix = str(output_dir / "frame_")
    scene.render.filepath = render_prefix

    print(f"[BLENDER_WORKER] Iniciando renderizado de {total_frames} fotogramas a {width}x{height} (Perfil: {profile_key})...")
    if single_frame:
        scene.frame_set(1)
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)

    status_file = output_dir / "status.json"
    status_file.write_text(
        json.dumps(
            {
                "success": True,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "fps": fps,
                "render_profile": profile_key,
                "composition_type": composition_type,
                "cycle_phase": cycle_phase,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[BLENDER_WORKER] Renderizado completado con éxito en: {output_dir}")


if __name__ == "__main__":
    # Leer archivo de especificación pasado tras el argumento '--'
    argv = sys.argv
    if "--" in argv:
        spec_arg_idx = argv.index("--") + 1
        if spec_arg_idx < len(argv):
            spec_file = Path(argv[spec_arg_idx])
            if spec_file.is_file():
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_data = json.load(f)
                run_blender_render(spec_data)
                sys.exit(0)
    print("Error: Se requiere una ruta a un archivo de especificación JSON tras '--'.")
    sys.exit(1)
