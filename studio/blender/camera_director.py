"""Director de Cámaras e Iluminación de Estudio en Blender 5.3 (Fase 2 - Perfeccionamiento).

Estética de Maqueta Educativa Estilizada:
- Iluminación de estudio de 3 puntos + luz de rebote ambiental en fondo claro.
- Sombras suaves y separación nítida de siluetas.
- 9 tomas reutilizables (Hero, Isométrica, Primer Plano, Lateral, Superior, Corte, Despiece, Seguimiento y Órbita).
- Encuadre inteligente con márgenes de seguridad para formato vertical 9:16 y horizontal 16:9.
- Orientación matemática estricta calculada por cuaterniones (to_track_quat) para renderizado headless.
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
    """Crea una iluminación de estudio profesional de 4 fuentes en entorno de maqueta clara."""
    if bpy is None:
        return {}

    lights_col = bpy.data.collections.new("Studio_Lighting")
    bpy.context.scene.collection.children.link(lights_col)

    # 1. Key Light (Luz Principal Cálida Difusa - Frente Derecha con radio amplio para sombras de maqueta sedosas)
    bpy.ops.object.light_add(type="AREA", radius=6.5, location=(5.5, -8.0, 7.5))
    key_light = bpy.context.active_object
    key_light.name = "Light_Key_Studio"
    key_light.data.energy = 850.0
    key_light.data.color = (1.0, 0.98, 0.95)  # Blanco cálido suave

    # 2. Fill Light (Luz de Relleno Suave - Frente Izquierda para aclarar sombras)
    bpy.ops.object.light_add(type="AREA", radius=5.5, location=(-6.5, -6.5, 5.5))
    fill_light = bpy.context.active_object
    fill_light.name = "Light_Fill_Studio"
    fill_light.data.energy = 380.0
    fill_light.data.color = (0.92, 0.95, 1.0)  # Cielo fresco suave

    # 3. Rim Light (Luz de Contorno Trasera Elevada para recortar bordes con nitidez)
    bpy.ops.object.light_add(type="AREA", radius=3.5, location=(0.0, 6.5, 6.0))
    rim_light = bpy.context.active_object
    rim_light.name = "Light_Rim_Studio"
    rim_light.data.energy = 480.0
    rim_light.data.color = (1.0, 1.0, 1.0)

    # 4. Bounce Light (Luz de Rebote Inferior para iluminar cárter y cigüeñal sin oscuridad profunda)
    bpy.ops.object.light_add(type="AREA", radius=4.0, location=(0.0, -4.5, -1.8))
    bounce_light = bpy.context.active_object
    bounce_light.name = "Light_Bounce_Studio"
    bounce_light.data.energy = 220.0
    bounce_light.data.color = (0.95, 0.94, 0.92)  # Rebote cálido de mesa

    # 5. Entorno Mundial Claro de Estudio (Fondo Beige/Gris Claro Neutro - Punto 2 y 3)
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("StudioWorld_Light")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        # Fondo gris claro neutro suave (#E8ECEF / #F1F5F9)
        bg_node.inputs["Color"].default_value = (0.88, 0.89, 0.91, 1.0)
        bg_node.inputs["Strength"].default_value = 0.95

    return {
        "key": key_light,
        "fill": fill_light,
        "rim": rim_light,
        "bounce": bounce_light,
    }


def setup_camera_for_shot(
    shot_type: str = "hero_view",
    is_vertical: bool = True,
    start_frame: int = 1,
    end_frame: int = 120,
) -> Any:
    """Configura la cámara con encuadre de estudio, distancias de seguridad y tomas reutilizables."""
    if bpy is None:
        return None

    cam_data = bpy.data.cameras.new("Director_Camera")
    cam_obj = bpy.data.objects.new("Director_Camera_Obj", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Margen de encuadre en 9:16 vertical (dist_mult = 1.25 para abarcar la altura completa)
    dist_mult = 1.25 if is_vertical else 1.0
    total_frames = max(10, end_frame - start_frame)

    # =========================================================================
    # CATÁLOGO DE TOMAS CINEMÁTICAS REUTILIZABLES (Punto 4)
    # =========================================================================

    # 1. HERO VIEW (Vista General 3/4 de Estudio)
    if shot_type in ("hero_view", "hero_intro"):
        cam_data.lens = 38
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        start_loc = mathutils.Vector((2.8 * dist_mult, -11.2 * dist_mult, 4.0))
        end_loc = mathutils.Vector((2.2 * dist_mult, -10.4 * dist_mult, 3.6))

    # 2. ISOMETRIC VIEW (Perspectiva Isométrica Técnica Limpia a 45°)
    elif shot_type == "isometric_view":
        cam_data.lens = 52
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        start_loc = mathutils.Vector((6.5 * dist_mult, -10.5 * dist_mult, 6.2))
        end_loc = mathutils.Vector((6.0 * dist_mult, -9.8 * dist_mult, 5.8))

    # 3. CLOSE-UP VIEW (Primer Plano a Cámara de Combustión, Válvulas y Bujía)
    elif shot_type in ("close_up_view", "cylinder_macro"):
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 4.8))
        start_loc = mathutils.Vector((1.4 * dist_mult, -6.0 * dist_mult, 5.0))
        end_loc = mathutils.Vector((1.0 * dist_mult, -5.4 * dist_mult, 4.8))

    # 4. SIDE VIEW (Vista Lateral Perfil del Mecanismo)
    elif shot_type == "side_view":
        cam_data.lens = 42
        target_loc = mathutils.Vector((0.0, 0.0, 3.2))
        start_loc = mathutils.Vector((11.5 * dist_mult, 0.0, 3.4))
        end_loc = mathutils.Vector((10.8 * dist_mult, 0.0, 3.2))

    # 5. TOP VIEW (Vista Superior de Culata, Balancines y Válvulas)
    elif shot_type == "top_view":
        cam_data.lens = 45
        target_loc = mathutils.Vector((0.0, 0.0, 5.4))
        start_loc = mathutils.Vector((0.1, -1.8, 12.5 * dist_mult))
        end_loc = mathutils.Vector((0.1, -1.5, 11.8 * dist_mult))

    # 6. CUTAWAY VIEW (Corte Transversal Técnico Frontal Directo)
    elif shot_type == "cutaway_view":
        cam_data.lens = 40
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        start_loc = mathutils.Vector((0.3 * dist_mult, -10.2 * dist_mult, 3.5))
        end_loc = mathutils.Vector((0.1 * dist_mult, -9.6 * dist_mult, 3.3))

    # 7. EXPLODED VIEW (Despiece Axial Amplio sin Solapamientos)
    elif shot_type == "exploded_view":
        cam_data.lens = 34
        target_loc = mathutils.Vector((0.0, 0.0, 3.4))
        start_loc = mathutils.Vector((3.8 * dist_mult, -14.2 * dist_mult, 4.4))
        end_loc = mathutils.Vector((3.0 * dist_mult, -13.2 * dist_mult, 4.0))

    # 8. COMPONENT TRACK (Seguimiento Cinemático de Pistón y Muñequilla)
    elif shot_type in ("component_track", "crank_track"):
        cam_data.lens = 52
        target_loc = mathutils.Vector((0.0, 0.0, 1.2))
        start_loc = mathutils.Vector((2.2 * dist_mult, -7.2 * dist_mult, 1.6))
        end_loc = mathutils.Vector((1.8 * dist_mult, -6.6 * dist_mult, 1.4))

    # 9. TURNTABLE ORBIT (Recorrido Orbital Suave 360° Alrededor del Motor)
    elif shot_type in ("turntable_orbit", "full_cycle"):
        cam_data.lens = 42
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        radius = 10.2 * dist_mult
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
        cam_data.lens = 40
        target_loc = mathutils.Vector((0.0, 0.0, 3.3))
        start_loc = mathutils.Vector((2.4 * dist_mult, -10.2 * dist_mult, 3.8))
        end_loc = mathutils.Vector((1.8 * dist_mult, -9.4 * dist_mult, 3.4))

    # Animar desplazamiento de cámara con orientación calculada matemáticamente en cada extremo
    cam_obj.location = start_loc
    cam_obj.rotation_euler = (target_loc - start_loc).to_track_quat("-Z", "Y").to_euler()
    cam_obj.keyframe_insert(data_path="location", frame=start_frame)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    cam_obj.location = end_loc
    cam_obj.rotation_euler = (target_loc - end_loc).to_track_quat("-Z", "Y").to_euler()
    cam_obj.keyframe_insert(data_path="location", frame=end_frame)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    return cam_obj
