"""AI VIDEO STUDIO — Inspector Visual Multi-Ángulo (Inspirado en la función 'look' de mcp-for-blender).

Genera rápidamente una hoja de contacto (Contact Sheet 2x2) que audita simultáneamente:
1. Perspectiva 3/4 (Hero View)
2. Vista Frontal (Front Elevation)
3. Vista Superior (Top Down)
4. Vista Lateral (Side Profile)

Permite auditar proporciones, simetría, colisiones y calidad geométrica en menos de un segundo
antes de autorizar la producción del video completo.
"""

from __future__ import annotations

import json
import logging
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.blender.blender_gateway import detect_blender_executable

logger = logging.getLogger("studio.inspector")


INSPECTOR_BLENDER_SCRIPT = """
import sys
from pathlib import Path

repo_root = r"{repo_root}"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import bpy
from mathutils import Vector
from studio.blender.educational_vertical_framework import (
    Educational916FrameworkConfig,
    setup_educational_scene_base,
)

model_type = "{model_type}"
output_dir = Path(r"{output_dir}")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Limpiar escena
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
    for item in list(coll):
        coll.remove(item, do_unlink=True)

cfg = Educational916FrameworkConfig()
cfg.render_width = {tile_w}
cfg.render_height = {tile_h}

scene_info = setup_educational_scene_base(cfg)
cam_obj = scene_info["camera"]

# 2. Cargar modelo según tipo
if model_type in ("turbocharger", "turbo", "turbocompresor"):
    from studio.blender.models_library.turbocharger_specialized import build_specialized_turbocharger_model
    model_data = build_specialized_turbocharger_model(center_z=1.25)
    cz = 1.25
    dist_base = 3.8
elif model_type == "refrigerator_cycle":
    from studio.blender.models_library.refrigerator_pipeline_specialized import build_specialized_refrigerator_model
    model_data = build_specialized_refrigerator_model()
    cz = 1.95
    dist_base = 6.2
else:
    from studio.blender.models_library.combustion_engine import create_combustion_engine_3d
    model_data = create_combustion_engine_3d()
    cz = 1.4
    dist_base = 4.2

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE" if hasattr(scene.render, "engine") else "BLENDER_EEVEE_NEXT"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = {tile_w}
scene.render.resolution_y = {tile_h}
if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 4

cam_data = cam_obj.data
cam_data.lens = 50.0

# 3. Definir los 4 ángulos de inspección técnica
angles = [
    ("angle_1_hero",      Vector((dist_base * 0.7, -dist_base * 0.8, cz + 1.2)), Vector((0, 0, cz))),
    ("angle_2_front",     Vector((0.0, -dist_base, cz)),                         Vector((0, 0, cz))),
    ("angle_3_top",       Vector((0.0, -0.01, cz + dist_base)),                  Vector((0, 0, cz))),
    ("angle_4_side",      Vector((dist_base, 0.0, cz)),                          Vector((0, 0, cz))),
]

for name, pos, tgt in angles:
    cam_obj.location = pos
    cam_obj.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.render.filepath = str((output_dir / f"{{name}}.png").resolve())
    bpy.ops.render.render(write_still=True)

print("INSPECTION TILES GENERATED")
"""


def generate_multi_angle_inspection(
    model_type: str = "turbocharger",
    output_dir: Optional[Path] = None,
    tile_size: int = 600,
) -> Path:
    """Ejecuta Blender para renderizar 4 vistas y las combina en una hoja de contacto 2x2."""
    if output_dir is None:
        output_dir = _repo_root / "projects" / f"inspection_{model_type}"
    output_dir.mkdir(parents=True, exist_ok=True)

    exe = detect_blender_executable()
    if not exe:
        raise RuntimeError("Blender no encontrado para inspección.")

    # Generar script de render de 4 vistas
    blend_script = output_dir / "_run_inspection.py"
    code = INSPECTOR_BLENDER_SCRIPT.format(
        repo_root=str(_repo_root),
        model_type=model_type,
        output_dir=str(output_dir),
        tile_w=tile_size,
        tile_h=tile_size,
    )
    blend_script.write_text(code, encoding="utf-8")

    cmd = [str(exe), "-b", "--python", str(blend_script.resolve())]
    subprocess.run(cmd, check=True, capture_output=True)

    # Coser la cuadrícula 2x2 con Pillow
    tiles = {
        "Hero Perspective (3/4)": output_dir / "angle_1_hero.png",
        "Front Elevation": output_dir / "angle_2_front.png",
        "Top Plan View": output_dir / "angle_3_top.png",
        "Side Profile": output_dir / "angle_4_side.png",
    }

    border = 16
    header_h = 36
    cell_w = tile_size
    cell_h = tile_size + header_h
    total_w = border * 3 + cell_w * 2
    total_h = border * 3 + cell_h * 2 + 50  # 50px para el título principal

    contact_sheet = Image.new("RGBA", (total_w, total_h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(contact_sheet)

    # Título principal
    title_text = f"AI VIDEO STUDIO — INSPECCIÓN MULTI-ÁNGULO: {model_type.upper()}"
    draw.text((border, 16), title_text, fill=(241, 245, 249, 255))

    positions = [
        (border, 50 + border),
        (border * 2 + cell_w, 50 + border),
        (border, 50 + border * 2 + cell_h),
        (border * 2 + cell_w, 50 + border * 2 + cell_h),
    ]

    for (label, path), (x, y) in zip(tiles.items(), positions):
        # Fondo de la celda
        draw.rectangle([x, y, x + cell_w, y + cell_h], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255), width=2)
        # Etiqueta
        draw.text((x + 12, y + 8), f"▶ {label}", fill=(56, 189, 248, 255))
        # Imagen
        if path.exists():
            with Image.open(path) as img:
                img_resized = img.resize((cell_w - 4, tile_size - 4))
                contact_sheet.paste(img_resized, (x + 2, y + header_h + 2))

    out_contact_path = output_dir / f"multi_angle_inspection_{model_type}.png"
    contact_sheet.save(out_contact_path, "PNG")
    print(f"[OK] Hoja de inspección multi-ángulo guardada: {out_contact_path}")
    return out_contact_path


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "turbocharger"
    p = generate_multi_angle_inspection(t)
    print("FINISHED:", p)
