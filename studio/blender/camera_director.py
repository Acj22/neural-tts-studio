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
    """Crea una iluminación de estudio profesional de 4 fuentes en entorno de maqueta clara con Freestyle."""
    if bpy is None:
        return {}

    scene = bpy.context.scene

    # Configuración Freestyle (desactivada por defecto para máxima velocidad de render en Iris Xe)
    scene.render.use_freestyle = False

    lights_col = bpy.data.collections.new("Studio_Lighting")
    bpy.context.scene.collection.children.link(lights_col)

    # 0. Telón de fondo Slate Blue Elegante (Inspirado en Referencia CAD 2.3)
    mat_bg = bpy.data.materials.get("Mat_StudioBackdrop")
    if not mat_bg:
        mat_bg = bpy.data.materials.new("Mat_StudioBackdrop")
        b_bg = mat_bg.node_tree.nodes.get("Principled BSDF")
        if b_bg:
            b_bg.inputs["Base Color"].default_value = (0.145, 0.21, 0.27, 1.0)  # Slate Blue #253545
            b_bg.inputs["Emission Color"].default_value = (0.145, 0.21, 0.27, 1.0)
            b_bg.inputs["Emission Strength"].default_value = 0.90

    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0, 12.0, 3.0))
    bg_plane = bpy.context.active_object
    bg_plane.name = "Studio_Backdrop_Plane"
    bg_plane.rotation_euler = (math.radians(90), 0, 0)
    bg_plane.data.materials.append(mat_bg)
    lights_col.objects.link(bg_plane)
    if bg_plane.name in scene.collection.objects:
        scene.collection.objects.unlink(bg_plane)

    # 1. Key Light (Luz Principal Cálida Difusa con sombras definidas)
    bpy.ops.object.light_add(type="AREA", radius=5.0, location=(6.0, -10.0, 8.0))
    key_light = bpy.context.active_object
    key_light.name = "Light_Key_Studio"
    key_light.data.energy = 650.0
    key_light.data.color = (1.0, 0.98, 0.95)
    lights_col.objects.link(key_light)
    if key_light.name in scene.collection.objects:
        scene.collection.objects.unlink(key_light)

    # 2. Fill Light (Luz de Relleno Suave)
    bpy.ops.object.light_add(type="AREA", radius=6.0, location=(-6.0, -8.0, 5.0))
    fill_light = bpy.context.active_object
    fill_light.name = "Light_Fill_Studio"
    fill_light.data.energy = 300.0
    fill_light.data.color = (0.88, 0.93, 1.0)
    lights_col.objects.link(fill_light)
    if fill_light.name in scene.collection.objects:
        scene.collection.objects.unlink(fill_light)

    # 3. Rim Light (Luz de Contorno Trasera para recortar aristas metálicas)
    bpy.ops.object.light_add(type="AREA", radius=4.0, location=(0.0, 7.0, 7.0))
    rim_light = bpy.context.active_object
    rim_light.name = "Light_Rim_Studio"
    rim_light.data.energy = 450.0
    rim_light.data.color = (1.0, 1.0, 1.0)
    lights_col.objects.link(rim_light)
    if rim_light.name in scene.collection.objects:
        scene.collection.objects.unlink(rim_light)

    # 4. Front Fill (Luz Frontal Suave de Detalle)
    bpy.ops.object.light_add(type="AREA", radius=3.5, location=(0.0, -8.0, 2.0))
    front_light = bpy.context.active_object
    front_light.name = "Light_Front_Studio"
    front_light.data.energy = 200.0
    front_light.data.color = (1.0, 0.97, 0.93)
    lights_col.objects.link(front_light)
    if front_light.name in scene.collection.objects:
        scene.collection.objects.unlink(front_light)

    # 5. Top Downlight (Luz Cenital de Alta Definición para Válvulas y Bujía)
    bpy.ops.object.light_add(type="AREA", radius=3.0, location=(0.0, -1.5, 9.5))
    top_light = bpy.context.active_object
    top_light.name = "Light_Top_Studio"
    top_light.data.energy = 300.0
    top_light.data.color = (1.0, 0.98, 0.96)
    lights_col.objects.link(top_light)
    if top_light.name in scene.collection.objects:
        scene.collection.objects.unlink(top_light)

    # 6. Entorno Suave Slate Blue
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("StudioWorld_Light")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.145, 0.21, 0.27, 1.0)
        bg_node.inputs["Strength"].default_value = 0.50

    return {
        "key": key_light,
        "fill": fill_light,
        "rim": rim_light,
        "front": front_light,
        "top": top_light,
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

    # ── Coordenadas de referencia Fase 2.1 ──────────────────────────────────
    # crank_center_z = 0.0  → cigüeñal en el origen del cárter
    # crank_radius   = 1.0  → muñequilla oscila Z -1.0 … +1.0
    # rod_length     = 3.6  → pms_z = 4.6
    # piston_height  = 1.40 → tope pistón PMS ≈ 5.3
    # head_z         ≈ 5.6  → culata y válvulas
    # block_top      ≈ 5.7  → límite superior del bloque
    # block_bottom   = -1.1
    # block_center_z ≈ 2.3  ← CENTRO GEOMÉTRICO DEL MOTOR
    # ────────────────────────────────────────────────────────────────────────

    # Margen de encuadre en 9:16 vertical — ligeramente reducido para acercar más
    dist_mult = 1.10 if is_vertical else 1.0
    total_frames = max(10, end_frame - start_frame)

    # =========================================================================
    # CATÁLOGO DE TOMAS CINEMÁTICAS — Fase 2.3 (10 Plantillas Cinematográficas)
    # =========================================================================

    # 1. HERO SHOT (Plantilla A: Presentación 3/4 general equilibrada - CAD 65mm)
    if shot_type in ("hero_shot", "hero_view", "hero_intro"):
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 2.7))
        start_loc = mathutils.Vector((2.6 * dist_mult, -19.2 * dist_mult, 3.6))
        end_loc   = mathutils.Vector((2.2 * dist_mult, -18.2 * dist_mult, 3.3))

    # 2. ISOMETRIC SHOT (Plantilla B: Perspectiva Isométrica Técnica 3D a 45°)
    elif shot_type in ("isometric_shot", "isometric_view"):
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 2.7))
        start_loc = mathutils.Vector((6.2 * dist_mult, -16.5 * dist_mult, 5.2))
        end_loc   = mathutils.Vector((5.8 * dist_mult, -15.5 * dist_mult, 4.8))

    # 3. CLOSE-UP: PISTÓN (Plantilla C1: Macro al pistón de cobre y aros)
    elif shot_type in ("close_up_piston", "piston_macro"):
        cam_data.lens = 68
        target_loc = mathutils.Vector((0.0, 0.0, 3.8))
        start_loc = mathutils.Vector((1.2 * dist_mult, -13.0 * dist_mult, 4.2))
        end_loc   = mathutils.Vector((0.9 * dist_mult, -12.0 * dist_mult, 3.9))

    # 4. CLOSE-UP: CIGÜEÑAL (Plantilla C2: Macro a muñequilla y contrapesos)
    elif shot_type in ("close_up_crank", "crank_macro"):
        cam_data.lens = 62
        target_loc = mathutils.Vector((0.0, 0.0, 0.5))
        start_loc = mathutils.Vector((1.5 * dist_mult, -12.0 * dist_mult, 1.2))
        end_loc   = mathutils.Vector((1.2 * dist_mult, -11.0 * dist_mult, 0.9))

    # 5. CLOSE-UP: VÁLVULAS & CÁMARA (Plantilla C3: Cámara de combustión, bujía y estallido)
    elif shot_type in ("close_up_chamber", "close_up_view", "close_up"):
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 4.3))
        start_loc = mathutils.Vector((1.1 * dist_mult, -12.5 * dist_mult, 4.6))
        end_loc   = mathutils.Vector((0.8 * dist_mult, -11.5 * dist_mult, 4.3))

    # 6. TRACKING SHOT (Plantilla D: Seguimiento de biela y pistón en movimiento oscilante)
    elif shot_type in ("tracking_shot", "tracking_rod", "component_track", "crank_track"):
        cam_data.lens = 52
        target_loc = mathutils.Vector((0.0, 0.0, 1.8))
        start_loc = mathutils.Vector((1.8 * dist_mult, -10.5 * dist_mult, 2.2))
        end_loc   = mathutils.Vector((1.4 * dist_mult, -9.5 * dist_mult, 1.8))

    # 7. ORBIT SHOT (Plantilla E: Recorrido orbital dinámico suave)
    elif shot_type in ("orbit_shot", "turntable_orbit"):
        cam_data.lens = 42
        target_loc = mathutils.Vector((0.0, 0.0, 2.4))
        radius = 9.2 * dist_mult
        z_height = 3.6
        for f in range(start_frame, end_frame + 1, max(1, total_frames // 24)):
            pct = (f - start_frame) / float(total_frames)
            ang = -math.pi / 2 + (pct * math.radians(72) - math.radians(36))
            cx = radius * math.cos(ang)
            cy = radius * math.sin(ang)
            cpos = mathutils.Vector((cx, cy, z_height))
            cam_obj.location = cpos
            direction = target_loc - cpos
            cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
            cam_obj.keyframe_insert(data_path="location", frame=f)
            cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)
        return cam_obj

    # 8. CUTAWAY SHOT (Plantilla F: Corte transversal frontal para flujos y ciclos)
    elif shot_type in ("cutaway_shot", "cutaway_view"):
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 2.7))
        start_loc = mathutils.Vector((0.15 * dist_mult, -18.8 * dist_mult, 3.1))
        end_loc   = mathutils.Vector((0.08 * dist_mult, -17.8 * dist_mult, 2.8))

    # 9. EXPLODED VIEW (Plantilla G: Despiece axial amplio de todos los componentes)
    elif shot_type == "exploded_view":
        cam_data.lens = 55
        target_loc = mathutils.Vector((0.0, 0.0, 3.2))
        start_loc = mathutils.Vector((3.0 * dist_mult, -21.0 * dist_mult, 4.2))
        end_loc   = mathutils.Vector((2.4 * dist_mult, -19.5 * dist_mult, 3.8))

    # 10. ASSEMBLY SHOT (Plantilla H: Ensamblaje inverso donde los componentes se unen)
    elif shot_type in ("assembly_shot", "assembly_view"):
        cam_data.lens = 58
        target_loc = mathutils.Vector((0.0, 0.0, 2.8))
        start_loc = mathutils.Vector((2.8 * dist_mult, -20.5 * dist_mult, 4.0))
        end_loc   = mathutils.Vector((2.2 * dist_mult, -18.2 * dist_mult, 3.4))

    # 11. TOP VIEW (Plantilla I: Vista superior elevada a 50° de culata, válvulas y muelles)
    elif shot_type in ("top_view", "valve_top_view", "valves_view"):
        cam_data.lens = 48
        target_loc = mathutils.Vector((0.0, 0.0, 5.0))
        start_loc = mathutils.Vector((1.8 * dist_mult, -8.0 * dist_mult, 7.5))
        end_loc   = mathutils.Vector((1.4 * dist_mult, -7.2 * dist_mult, 6.9))

    # 12. SIDE VIEW (Plantilla J: Vista lateral técnica)
    elif shot_type in ("side_view", "side_cutaway"):
        cam_data.lens = 58
        target_loc = mathutils.Vector((0.0, 0.0, 2.6))
        start_loc = mathutils.Vector((16.5 * dist_mult, 0.0, 3.0))
        end_loc   = mathutils.Vector((15.5 * dist_mult, 0.0, 2.7))

    else:  # default process_view — vista equilibrada CAD
        cam_data.lens = 65
        target_loc = mathutils.Vector((0.0, 0.0, 2.7))
        start_loc = mathutils.Vector((2.6 * dist_mult, -19.2 * dist_mult, 3.6))
        end_loc   = mathutils.Vector((2.2 * dist_mult, -18.2 * dist_mult, 3.3))

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
