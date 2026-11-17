"""Director de Cámaras e Iluminación de Estudio en Blender 5.3 (Fase 6).

Crea tomas cinematográficas con encuadre inteligente en orientación vertical Z-up adaptado a:
- Vertical 9:16 (1080 × 1920) para TikTok, Reels y Shorts.
- Horizontal 16:9 (1920 × 1080) para YouTube y monitores.

Soporta 8 tipos de tomas:
- hero_view: Vista general 3/4 de impacto.
- isometric_view: Perspectiva técnica isométrica limpia.
- close_up_view: Acercamiento macro a culata, bujía y válvulas.
- cutaway_view: Enfoque frontal directo a través del corte del cilindro.
- exploded_view: Vista elevada para despiece axial sin solapamientos.
- turntable_orbit: Recorrido orbital 360° suave alrededor del motor.
- crank_track: Acercamiento al cigüeñal y biela.
- process_view: Vista del ciclo de 4 tiempos.
"""

from __future__ import annotations

import math
from typing import Any

try:
    import bpy
    import mathutils
except ImportError:
    bpy = None
    mathutils = None


def setup_studio_lighting() -> dict[str, Any]:
    """Crea un esquema de iluminación de 3 puntos estilo maqueta suave."""
    if bpy is None:
        return {}

    lights_col = bpy.data.collections.new("Studio_Lighting")
    bpy.context.scene.collection.children.link(lights_col)

    # 1. Key Light (Luz principal suave con radio amplio para sombras difusas desde el frente-derecha)
    bpy.ops.object.light_add(type="AREA", radius=4.5, location=(6.0, -8.5, 7.5))
    key_light = bpy.context.active_object
    key_light.name = "Light_Key"
    key_light.data.energy = 850.0
    key_light.data.color = (1.0, 0.97, 0.94)  # Blanco cálido suave

    # 2. Fill Light (Luz de relleno suave azulada desde el frente-izquierda)
    bpy.ops.object.light_add(type="AREA", radius=5.5, location=(-6.5, -6.5, 5.5))
    fill_light = bpy.context.active_object
    fill_light.name = "Light_Fill"
    fill_light.data.energy = 420.0
    fill_light.data.color = (0.75, 0.88, 1.0)  # Cian/celeste suave

    # 3. Rim / Backlight (Luz de contra trasera para recortar siluetas con filo nítido)
    bpy.ops.object.light_add(type="AREA", radius=3.5, location=(0.0, 6.5, 5.5))
    rim_light = bpy.context.active_object
    rim_light.name = "Light_Rim"
    rim_light.data.energy = 550.0
    rim_light.data.color = (0.55, 0.85, 1.0)  # Halo tecnológico

    # 4. Color de Mundo Ambiental (Studio Void)
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("StudioWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.043, 0.067, 0.125, 1.0)  # #0B1120
        bg_node.inputs["Strength"].default_value = 0.85

    return {
        "key": key_light,
        "fill": fill_light,
        "rim": rim_light,
    }


def setup_camera_for_shot(
    shot_type: str = "hero_view",
    is_vertical: bool = True,
    start_frame: int = 1,
    end_frame: int = 120,
) -> Any:
    """Configura la cámara activa, su distancia focal y su movimiento cinemático."""
    if bpy is None:
        return None

    cam_data = bpy.data.cameras.new("Director_Camera")
    cam_obj = bpy.data.objects.new("Director_Camera_Obj", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # En vertical 9:16 aumentamos la distancia y abrimos lente para que toda la altura (bujía a cigüeñal) entre completa
    dist_mult = 1.25 if is_vertical else 1.0
    total_frames = max(10, end_frame - start_frame)

    if shot_type in ("hero_view", "hero_intro"):
        cam_data.lens = 38
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        start_loc = mathutils.Vector((2.8 * dist_mult, -11.2 * dist_mult, 4.0))
        end_loc = mathutils.Vector((2.2 * dist_mult, -10.4 * dist_mult, 3.6))

    elif shot_type == "isometric_view":
        cam_data.lens = 55
        target_loc = mathutils.Vector((0.0, 0.0, 3.2))
        start_loc = mathutils.Vector((5.5 * dist_mult, -8.5 * dist_mult, 6.0))
        end_loc = mathutils.Vector((5.0 * dist_mult, -8.0 * dist_mult, 5.6))

    elif shot_type in ("close_up_view", "cylinder_macro"):
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 4.8))  # Foco en cámara de combustión
        start_loc = mathutils.Vector((1.6 * dist_mult, -5.8 * dist_mult, 5.0))
        end_loc = mathutils.Vector((1.2 * dist_mult, -5.2 * dist_mult, 4.9))

    elif shot_type == "cutaway_view":
        cam_data.lens = 48
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        start_loc = mathutils.Vector((0.4 * dist_mult, -8.8 * dist_mult, 3.4))
        end_loc = mathutils.Vector((0.2 * dist_mult, -8.2 * dist_mult, 3.3))

    elif shot_type == "exploded_view":
        cam_data.lens = 38
        target_loc = mathutils.Vector((0.0, 0.0, 3.6))
        # Vista elevada y amplia para que el pistón elevado y cigüeñal descendido entren sin corte
        start_loc = mathutils.Vector((3.8 * dist_mult, -13.5 * dist_mult, 4.6))
        end_loc = mathutils.Vector((3.0 * dist_mult, -12.5 * dist_mult, 4.2))

    elif shot_type == "crank_track":
        cam_data.lens = 55
        target_loc = mathutils.Vector((0.0, 0.0, 0.8))  # Foco en cigüeñal y biela
        start_loc = mathutils.Vector((2.2 * dist_mult, -6.6 * dist_mult, 1.2))
        end_loc = mathutils.Vector((1.8 * dist_mult, -6.0 * dist_mult, 1.0))

    elif shot_type in ("turntable_orbit", "full_cycle"):
        cam_data.lens = 45
        target_loc = mathutils.Vector((0.0, 0.0, 3.4))
        radius = 9.5 * dist_mult
        z_height = 3.8
        for f in range(start_frame, end_frame + 1, max(1, total_frames // 24)):
            pct = (f - start_frame) / float(total_frames)
            ang = -math.pi / 2 + (pct * math.radians(70) - math.radians(35))
            cx = radius * math.cos(ang)
            cy = radius * math.sin(ang)
            cpos = mathutils.Vector((cx, cy, z_height))
            cam_obj.location = cpos
            direction = target_loc - cpos
            cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
            cam_obj.keyframe_insert(data_path="location", frame=f)
            cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)
        return cam_obj

    else:  # default process_view
        cam_data.lens = 45
        target_loc = mathutils.Vector((0.0, 0.0, 3.4))
        start_loc = mathutils.Vector((2.4 * dist_mult, -9.5 * dist_mult, 3.8))
        end_loc = mathutils.Vector((1.8 * dist_mult, -8.6 * dist_mult, 3.4))

    # Animar desplazamiento de cámara con orientación exacta calculada matemáticamente
    cam_obj.location = start_loc
    cam_obj.rotation_euler = (target_loc - start_loc).to_track_quat("-Z", "Y").to_euler()
    cam_obj.keyframe_insert(data_path="location", frame=start_frame)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    cam_obj.location = end_loc
    cam_obj.rotation_euler = (target_loc - end_loc).to_track_quat("-Z", "Y").to_euler()
    cam_obj.keyframe_insert(data_path="location", frame=end_frame)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    return cam_obj
