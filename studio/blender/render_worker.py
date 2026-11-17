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

    width = int(spec.get("width", 1080))
    height = int(spec.get("height", 1920))
    fps = int(spec.get("fps", 30))
    duration_sec = float(spec.get("duration_sec", 4.0))
    composition_type = spec.get("composition_type", "hero_view")
    cycle_phase = spec.get("cycle_phase", "full_cycle")
    profile_key = spec.get("render_profile", "standard")
    profile = get_render_profile(profile_key)
    output_dir = Path(spec["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    single_frame = bool(spec.get("single_frame_only", False))

    is_vertical = height > width
    total_frames = 1 if single_frame else max(10, int(round(duration_sec * fps)))

    # 1. Configurar Motor de Render y Parámetros
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = int(profile["resolution_scale"])
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames

    # EEVEE Next sampling
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = int(profile["samples"])

    # 2. Iluminación de Estudio y Fondo
    setup_studio_lighting()

    # 3. Construcción del Modelo 3D (Motor de 4 Tiempos)
    engine_data = create_combustion_engine_3d(
        crank_radius=1.0,
        rod_length=3.5,
        cylinder_radius=1.35,
        piston_height=1.25,
    )

    # 4. Cinemática de Animación
    build_4_stroke_cycle_keyframes(
        engine_data=engine_data,
        start_frame=1,
        end_frame=total_frames,
        cycle_phase=cycle_phase,
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
