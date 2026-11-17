"""Director de Cámaras e Iluminación de Estudio en Blender 5.3 (Fase 6).

Crea tomas cinematográficas con encuadre inteligente adaptado a:
- Vertical 9:16 (1080 × 1920) para TikTok, Reels y Shorts.
- Horizontal 16:9 (1920 × 1080) para YouTube y monitores.

Soporta 8 tipos de tomas:
- hero_view: Vista general 3/4 de impacto.
- isometric_view: Perspectiva técnica isométrica limpia.
- close_up_view: Acercamiento macro a culata, bujía y válvulas.
- cutaway_view: Enfoque directo a través del corte del cilindro.
- exploded_view: Vista elevada para despiece axial sin solapamientos.
- turntable_orbit: Recorrido orbital 360° suave alrededor del motor.
- piston_track: Enfoque dinámico siguiendo la carrera del pistón.
- crank_track: Acercamiento al cigüeñal y volante de inercia.
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

    # 1. Key Light (Luz principal suave con radio amplio para sombras difusas)
    bpy.ops.object.light_add(type="AREA", radius=3.5, location=(4.5, 6.0, 5.5))
    key_light = bpy.context.active_object
    key_light.name = "Light_Key"
    key_light.data.energy = 650.0
    key_light.data.color = (1.0, 0.96, 0.92)  # Blanco cálido suave
    key_light.rotation_euler = (math.radians(35), math.radians(25), math.radians(-35))

    # 2. Fill Light (Luz de relleno suave azulada)
    bpy.ops.object.light_add(type="AREA", radius=4.5, location=(-5.0, 3.5, 4.0))
    fill_light = bpy.context.active_object
    fill_light.name = "Light_Fill"
    fill_light.data.energy = 280.0
    fill_light.data.color = (0.78, 0.88, 1.0)  # Cian/celeste suave
    fill_light.rotation_euler = (math.radians(20), math.radians(-40), math.radians(45))

    # 3. Rim / Backlight (Luz de contra para recortar siluetas con filo nítido)
    bpy.ops.object.light_add(type="AREA", radius=2.5, location=(0.0, 7.5, -4.5))
    rim_light = bpy.context.active_object
    rim_light.name = "Light_Rim"
    rim_light.data.energy = 450.0
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

    # Ajuste de encuadre vertical vs horizontal
    # En vertical 9:16 alejamos la cámara ligeramente en Z o reducimos focal para abarcar la altura del motor (6.5 unidades)
    dist_mult = 1.35 if is_vertical else 1.0

    cam_target = bpy.data.objects.new("Camera_Target", None)
    cam_target.location = (0.0, 3.2, 0.0)  # Centro visual del motor
    bpy.context.scene.collection.objects.link(cam_target)

    # Añadir constraint Track-To para que la cámara siempre encuadre el motor suavemente
    track = cam_obj.constraints.new(type="TRACK_TO")
    track.target = cam_target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    total_frames = max(10, end_frame - start_frame)

    if shot_type in ("hero_view", "hero_intro"):
        cam_data.lens = 55
        start_loc = (3.5 * dist_mult, 4.2, 6.8 * dist_mult)
        end_loc = (2.8 * dist_mult, 3.8, 6.2 * dist_mult)

    elif shot_type == "isometric_view":
        cam_data.lens = 75
        start_loc = (5.5 * dist_mult, 5.0, 5.5 * dist_mult)
        end_loc = (5.8 * dist_mult, 5.2, 5.2 * dist_mult)

    elif shot_type in ("close_up_view", "cylinder_macro"):
        cam_data.lens = 85
        cam_target.location = (0.0, 4.8, 0.0)  # Foco en cámara de combustión
        start_loc = (1.8 * dist_mult, 5.2, 3.8 * dist_mult)
        end_loc = (1.4 * dist_mult, 5.0, 3.4 * dist_mult)

    elif shot_type == "cutaway_view":
        cam_data.lens = 65
        cam_target.location = (0.0, 3.4, 0.0)
        start_loc = (1.2 * dist_mult, 3.4, 5.8 * dist_mult)
        end_loc = (0.8 * dist_mult, 3.4, 5.4 * dist_mult)

    elif shot_type == "exploded_view":
        cam_data.lens = 50
        cam_target.location = (0.0, 3.6, 0.0)
        # Vista elevada y amplia para que el pistón elevado y cigüeñal descendido entren sin corte
        start_loc = (4.8 * dist_mult, 6.5, 7.8 * dist_mult)
        end_loc = (4.0 * dist_mult, 6.2, 7.4 * dist_mult)

    elif shot_type == "crank_track":
        cam_data.lens = 70
        cam_target.location = (0.0, 0.2, 0.0)  # Foco en cigüeñal
        start_loc = (2.8 * dist_mult, 1.2, 4.5 * dist_mult)
        end_loc = (2.2 * dist_mult, 0.9, 4.2 * dist_mult)

    elif shot_type in ("turntable_orbit", "full_cycle"):
        cam_data.lens = 60
        # Órbita circular suave alrededor del motor
        radius = 7.0 * dist_mult
        y_height = 3.8
        for f in range(start_frame, end_frame + 1, 5):
            pct = (f - start_frame) / float(total_frames)
            ang = math.radians(35) + pct * math.radians(70)
            cx = radius * math.sin(ang)
            cz = radius * math.cos(ang)
            cam_obj.location = (cx, y_height, cz)
            cam_obj.keyframe_insert(data_path="location", frame=f)
        return cam_obj

    else:  # default process_view
        cam_data.lens = 60
        start_loc = (2.2 * dist_mult, 3.6, 6.2 * dist_mult)
        end_loc = (1.8 * dist_mult, 3.5, 5.8 * dist_mult)

    # Animar desplazamiento de cámara (dolly in / pan suave)
    cam_obj.location = start_loc
    cam_obj.keyframe_insert(data_path="location", frame=start_frame)

    cam_obj.location = end_loc
    cam_obj.keyframe_insert(data_path="location", frame=end_frame)

    return cam_obj
