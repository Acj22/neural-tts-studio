"""Lógica especializada del modelo de Refrigerador (Ciclo Termodinámico Cerrado).

DESACOPLADO DEL FRAMEWORK BASE:
- Utiliza las clases `SafeZone916Config`, `Camera916Config`, `EeveeLightingConfig`,
  `LabelStyleConfig`, `AdaptiveLabelsEngine` y `create_adaptive_3d_label` de
  `studio.blender.educational_vertical_framework`.
- Define exclusivamente la geometría física, los anclajes de componentes y la
  cinemática del ciclo de refrigeración para videos verticales de 90-110 s.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None
    Vector = None

from studio.blender.educational_vertical_framework import (
    AdaptiveLabelsEngine,
    Educational916FrameworkConfig,
    create_adaptive_3d_label,
)
from studio.blender.materials import get_or_create_material, hex_to_rgba, setup_engine_materials
from studio.blender.models_library import _common as C


# ==============================================================================
# GEOMETRÍA DEL REFRIGERADOR Y CIRCUITO TERMODINÁMICO
# ==============================================================================

def build_specialized_refrigerator_model(
    center_z: float = 2.2,
) -> Dict[str, Any]:
    """Construye el modelo físico del refrigerador en corte con circuito completo."""
    if bpy is None:
        return {}

    mats = setup_engine_materials()
    Z0 = center_z - 2.15
    Z = lambda z: Z0 + z

    data: Dict[str, Any] = {
        "groups": {},
        "components": {},
        "anchors_3d": {},
        "meta": {"center_z": center_z},
    }
    G = data["groups"]

    def grp(name: str, *objs: Any) -> None:
        for o in objs:
            if o is None:
                continue
            G.setdefault(name, []).append(o)
            o["comp_group"] = name

    # Materiales PBR especializados
    m_white = mats.get("white_cabinet") or get_or_create_material("Mat_WhiteCabinet", hex_to_rgba("#F8FAFC"), roughness=0.35)
    m_foam = get_or_create_material("Mat_FoamInsulation", hex_to_rgba("#F5D66B"), roughness=0.9)
    m_liner = get_or_create_material("Mat_FridgeLiner", hex_to_rgba("#CBD5E1"), roughness=0.5)
    m_glass = get_or_create_material("Mat_GlassShelf", hex_to_rgba("#9ED8F0"), roughness=0.15, metallic=0.0, alpha=0.55)
    m_frost = mats.get("frost_blue") or get_or_create_material("Mat_FrostBlue", hex_to_rgba("#7DD3FC"), roughness=0.25, metallic=0.1)
    m_copper = get_or_create_material("Mat_CopperBright", hex_to_rgba("#C25E2E"), roughness=0.22, metallic=0.92)
    m_cast_iron = get_or_create_material("Mat_CastIronDark", hex_to_rgba("#22272E"), roughness=0.55, metallic=0.75)

    # 1. Gabinete en corte frontal de 3 capas
    zb, zt = Z(0.68), Z(4.15)

    def layered(name, axis, lo, hi, other_a, other_b, other_c, other_d, layers=(0.22, 0.56, 0.22), flip=False):
        t = hi - lo
        cuts = [lo, lo + t * layers[0], lo + t * (layers[0] + layers[1]), hi]
        mlist = [m_white, m_foam, m_liner] if not flip else [m_liner, m_foam, m_white]
        out = []
        for i in range(3):
            a, b = cuts[i], cuts[i + 1]
            if axis == "x":
                size = (b - a, other_b - other_a, other_d - other_c)
                ctr = ((a + b) / 2, (other_a + other_b) / 2, (other_c + other_d) / 2)
            elif axis == "y":
                size = (other_b - other_a, b - a, other_d - other_c)
                ctr = ((other_a + other_b) / 2, (a + b) / 2, (other_c + other_d) / 2)
            else:
                size = (other_b - other_a, other_d - other_c, b - a)
                ctr = ((other_a + other_b) / 2, (other_c + other_d) / 2, (a + b) / 2)
            o = C.box(f"{name}_L{i+1}", size, ctr, mlist[i])
            out.append(o)
        grp("cabinet", *out)
        return out

    layered("Wall_Left", "x", -1.0, -0.82, -0.6, 0.6, zb, zt)
    layered("Wall_Right", "x", 0.82, 1.0, -0.6, 0.6, zb, zt, flip=True)
    layered("Wall_Back", "y", 0.42, 0.6, -1.0, 1.0, zb, zt, flip=True)
    layered("Wall_Top", "z", Z(3.97), zt, -1.0, 1.0, -0.6, 0.6, flip=True)
    layered("Wall_Bottom", "z", zb, Z(0.86), -1.0, 1.0, -0.6, 0.6)
    layered("Partition", "z", Z(2.75), Z(2.9), -0.82, 0.82, -0.6, 0.42, layers=(0.25, 0.5, 0.25))

    # Plinto / Compartimento de máquinas inferior
    plinth_floor = C.box("Plinth_Floor", (2.2, 1.3, 0.08), (0.0, 0.0, Z(0.04)), m_liner, bev=0.01)
    plinth_back = C.box("Plinth_Back", (2.2, 0.08, 0.68), (0.0, 0.66, Z(0.34)), m_white)
    plinth_left = C.box("Plinth_Left", (0.08, 1.3, 0.68), (-1.1, 0.0, Z(0.34)), m_white)
    grp("cabinet", plinth_floor, plinth_back, plinth_left)

    # 2. Compresor Hermético con corte visual
    comp_root = C.empty("Compressor_Root", (0.35, 0.05, Z(0.35)))
    shell = C.cylinder("Compressor_Shell", 0.28, 0.38, (0, 0, 0), "Z", m_cast_iron, 32, parent=comp_root)
    cap_top = C.cylinder("Compressor_Cap_Top", 0.27, 0.08, (0, 0, 0.21), "Z", m_cast_iron, 32, parent=comp_root, r2=0.18)
    cap_bot = C.cylinder("Compressor_Cap_Bot", 0.27, 0.08, (0, 0, -0.21), "Z", m_cast_iron, 32, parent=comp_root, r2=0.27)
    rotor_root = C.empty("Comp_Rotor_Root", (0, 0, 0), parent=comp_root)
    crank = C.cylinder("Comp_CrankPin", 0.035, 0.18, (0.06, 0, 0), "Z", m_copper, 16, parent=rotor_root)
    piston = C.cylinder("Comp_Piston", 0.065, 0.12, (0, 0, -0.17), "X", mats.get("piston_rings", m_copper), 16, parent=comp_root)
    grp("compressor", shell, cap_top, cap_bot, crank, piston)

    data["anchors_3d"]["compressor"] = Vector((0.35, -0.25, Z(0.35)))

    # 3. Serpentín del Condensador (panel exterior de 8 pasadas)
    cond_x0, cond_x1 = 1.25, 2.05
    cond_ztop, cond_zbot = Z(3.85), Z(1.20)
    cond_rows = 8

    def _serpentine_pts(x0: float, x1: float, z_top: float, z_bot: float, rows: int, y: float, start_left: bool) -> List[Tuple[float, float, float]]:
        pts = []
        zs = [z_top + (z_bot - z_top) * i / (rows - 1) for i in range(rows)]
        left = start_left
        for z_val in zs:
            a, b = (x0, x1) if left else (x1, x0)
            pts.append((a, y, z_val))
            pts.append((b, y, z_val))
            left = not left
        return pts

    cond_pts = _serpentine_pts(cond_x0, cond_x1, cond_ztop, cond_zbot, cond_rows, 0.0, True)
    poly_cond = C.rounded_polyline([Vector(p) for p in cond_pts], 0.045)
    tube_cond = C.tube_from_path("Pipe_condenser", poly_cond, 0.022, mats.get("heat_red", m_copper))
    grp("condenser", tube_cond)

    data["anchors_3d"]["condenser"] = Vector((2.08, 0.0, Z(2.65)))

    # 4. Filtro Deshidratador
    dryer = C.cylinder("Filter_Dryer", 0.045, 0.22, (1.20, 0.0, Z(0.85)), "Z", m_copper, 20)
    grp("dryer", dryer)
    data["anchors_3d"]["dryer"] = Vector((1.20, -0.15, Z(0.85)))

    # 5. Tubo Capilar (Espiral de cobre compacta de alta resistencia)
    cap_path = C.helix_path((0.95, -0.05, Z(0.82)), "Z", 0.45, 0.042, turns=7.5, pts_per_turn=12)
    tube_capillary = C.tube_from_path("Pipe_capillary", cap_path, 0.010, m_copper)
    grp("capillary", tube_capillary)
    data["anchors_3d"]["capillary"] = Vector((0.95, -0.20, Z(0.95)))

    # 6. Evaporador (Serpentín en el congelador interior)
    evap_pts = _serpentine_pts(-0.72, 0.72, Z(3.85), Z(3.05), 5, 0.35, True)
    poly_evap = C.rounded_polyline([Vector(p) for p in evap_pts], 0.04)
    tube_evap = C.tube_from_path("Pipe_evaporator", poly_evap, 0.022, m_frost)
    grp("evaporator", tube_evap)
    data["anchors_3d"]["evaporator"] = Vector((0.0, 0.20, Z(3.50)))

    # Tuberías de interconexión (Descarga y Succión)
    p_disc = C.rounded_polyline([Vector((0.35, 0.05, Z(0.55))), Vector((0.35, 0.05, Z(0.70))), Vector((1.25, 0.0, Z(0.70))), Vector(cond_pts[0])], 0.04)
    tube_disc = C.tube_from_path("Pipe_discharge", p_disc, 0.018, mats.get("manifold_pipes", m_cast_iron))

    p_suct = C.rounded_polyline([Vector(evap_pts[-1]), Vector((-0.75, 0.35, Z(1.10))), Vector((-0.75, 0.0, Z(0.40))), Vector((0.15, 0.05, Z(0.40)))], 0.05)
    tube_suct = C.tube_from_path("Pipe_suction", p_suct, 0.024, mats.get("frost_blue", m_frost))
    grp("compressor", tube_disc, tube_suct)

    # 7. Flechas térmicas (Disipación en condensador y absorción en congelador)
    arrows_hot = []
    mat_arrow_hot = C.emissive_material("Mat_ArrowHot", (1.0, 0.35, 0.12), 3.5)
    for i in range(4):
        a = C.make_arrow(f"HeatOut_{i+1}", 0.38, 0.018, mat_arrow_hot)
        a.location = (cond_x1 + 0.12, 0.0, Z(1.45 + i * 0.70))
        arrows_hot.append(a)
        grp("heat_arrows", a)

    arrows_cold = []
    mat_arrow_cold = C.emissive_material("Mat_ArrowCold", (0.35, 0.75, 1.0), 3.5)
    for i in range(3):
        a = C.make_arrow(f"HeatIn_{i+1}", 0.34, 0.016, mat_arrow_cold)
        a.rotation_euler = (0, 0, math.pi / 2)
        a.location = (-0.45 + 0.45 * i, -0.40, Z(3.35))
        arrows_cold.append(a)
        grp("heat_arrows", a)

    # Estantes de vidrio y alimentos estilizados
    shelf1 = C.box("Glass_Shelf_1", (1.62, 0.95, 0.035), (0, -0.08, Z(1.50)), m_glass)
    shelf2 = C.box("Glass_Shelf_2", (1.62, 0.95, 0.035), (0, -0.08, Z(2.15)), m_glass)
    grp("cabinet", shelf1, shelf2)

    # Guardar referencias
    data["compressor_parts"] = {
        "root": comp_root, "rotor_root": rotor_root, "piston": piston,
        "base_loc": comp_root.location.copy(), "piston_base_x": 0.0,
    }
    data["arrows_hot"] = arrows_hot
    data["arrows_cold"] = arrows_cold

    return data


# ==============================================================================
# SISTEMA DE ETIQUETAS ADAPTATIVAS CONFIGURABLES PARA EL REFRIGERADOR
# ==============================================================================

def generate_refrigerator_adaptive_labels(
    refrigerator_data: Dict[str, Any],
    cam_pos: Vector,
    cam_target: Vector,
    config: Educational916FrameworkConfig,
    active_labels_keys: Optional[List[str]] = None,
) -> Dict[str, Tuple[Any, Any]]:
    """Genera las etiquetas adaptativas del refrigerador proyectándolas en pantalla 2D,
    ajustándolas a las zonas seguras (safe zones) y eliminando solapamientos."""
    anchors_3d = refrigerator_data.get("anchors_3d", {})
    engine = AdaptiveLabelsEngine(config.safe_zones, config.labels)

    lbl_collection = bpy.data.collections.get("Adaptive_Labels_9_16")
    if not lbl_collection:
        lbl_collection = bpy.data.collections.new("Adaptive_Labels_9_16")
        bpy.context.scene.collection.children.link(lbl_collection)

    created_labels: Dict[str, Tuple[Any, Any]] = {}

    # --------------------------------------------------------------------------
    # 1. CONJUNTO MAESTRO DE ARQUITECTURA (Vista General · Stage 2, Frames 337-720)
    # --------------------------------------------------------------------------
    cam_o = bpy.context.scene.camera if bpy is not None else None
    if cam_o:
        cam_o.location = cam_pos
        cam_o.rotation_euler = (cam_target - cam_pos).to_track_quat("-Z", "Y").to_euler()
        cam_o.data.lens = config.camera.lens_mm
        bpy.context.view_layer.update()

    label_specs_overview = {
        "compressor": ("COMPRESOR", "left"),
        "condenser": ("CONDENSADOR", "right"),
        "dryer": ("FILTRO SECADOR", "right"),
        "capillary": ("TUBO CAPILAR", "left"),
        "evaporator": ("EVAPORADOR", "left"),
    }

    anchors_2d = {}
    for key, (txt, side) in label_specs_overview.items():
        if key in anchors_3d:
            u, v, _ = engine.project_3d_to_screen_uv(
                anchors_3d[key], cam_pos, cam_target,
                config.camera.lens_mm, config.render_width, config.render_height,
                cam_obj=cam_o, scene=bpy.context.scene if bpy else None,
            )
            anchors_2d[key] = (u, v, side)

    solved_overview = engine.solve_label_positions_2d(anchors_2d)

    for key, (target_u, target_v) in solved_overview.items():
        text_content, _ = label_specs_overview[key]
        anchor_pt = anchors_3d[key]
        txt_obj, line_obj = create_adaptive_3d_label(
            name=f"overview_{key}",
            text=text_content,
            anchor_3d=anchor_pt,
            target_screen_u=target_u,
            target_screen_v=target_v,
            cam_pos=cam_pos,
            cam_target=cam_target,
            config=config,
            collection=lbl_collection,
        )
        created_labels[f"overview_{key}"] = (txt_obj, line_obj)

    # --------------------------------------------------------------------------
    # 2. CONJUNTOS DE PRIMER PLANO / MACRO POR ETAPA (Stages 3 a 6)
    # --------------------------------------------------------------------------
    close_stage_configs = [
        # (stage_name, comp_key, label_text, target_u, target_v, cam_az_deg, cam_el_deg, cam_dist, target_z, lens_mm)
        ("compressor", "compressor", "COMPRESOR", 0.35, 0.68, 22.0, 12.0, 4.8, 0.50, 56.0),
        ("condenser", "condenser", "CONDENSADOR", 0.70, 0.62, 30.0, 12.0, 6.2, 2.65, 56.0),
        ("capillary", "capillary", "TUBO CAPILAR", 0.36, 0.68, 16.0, 10.0, 3.8, 0.95, 58.0),
        ("dryer", "dryer", "FILTRO SECADOR", 0.70, 0.56, 16.0, 10.0, 3.8, 0.95, 58.0),
        ("evaporator", "evaporator", "EVAPORADOR", 0.36, 0.70, 10.0, 12.0, 5.4, 3.40, 54.0),
    ]

    for st_name, c_key, txt, tu, tv, az_d, el_d, dist_val, tz_val, lens_val in close_stage_configs:
        az = math.radians(az_d)
        el = math.radians(el_d)
        c_target = Vector((0.0, 0.0, tz_val))
        d_vec = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        c_pos = c_target + d_vec * dist_val

        if cam_o:
            cam_o.location = c_pos
            cam_o.rotation_euler = (c_target - c_pos).to_track_quat("-Z", "Y").to_euler()
            cam_o.data.lens = lens_val
            bpy.context.view_layer.update()

        anchor_pt = anchors_3d[c_key]
        txt_obj, line_obj = create_adaptive_3d_label(
            name=f"close_{c_key}",
            text=txt,
            anchor_3d=anchor_pt,
            target_screen_u=tu,
            target_screen_v=tv,
            cam_pos=c_pos,
            cam_target=c_target,
            config=config,
            collection=lbl_collection,
        )
        created_labels[f"close_{c_key}"] = (txt_obj, line_obj)

    return created_labels


# ==============================================================================
# ANIMACIÓN Y RETENCIÓN MULTI-FASE (~1:30–1:50 min / 90–110s)
# ==============================================================================

def animate_refrigerator_vertical_showcase(
    refrigerator_data: Dict[str, Any],
    camera_obj: Any,
    config: Educational916FrameworkConfig,
    labels_dict: Optional[Dict[str, Tuple[Any, Any]]] = None,
) -> Dict[str, Any]:
    """Aplica la coreografía de movimientos de cámara cinemáticos suaves,
    pulsos de componentes, flechas térmicas y etiquetas para sostener la retención
    durante todo el video de 105 segundos (2520 frames a 24fps)."""
    if bpy is None or not camera_obj:
        return {"status": "mock"}

    fps = config.timeline.fps
    total_frames = config.timeline.total_frames
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames

    cam_data = camera_obj.data
    cam_data.lens = config.camera.lens_mm
    cam_data.sensor_fit = config.camera.sensor_fit

    # Fases de cámara continuas calibradas para proporción áurea 9:16 sin desbordamiento
    keyframes_timeline = [
        # Frame 1 (0.0s): Hero View panorámico inicial (encuadre completo dentro de safe zone)
        {"frame": 1, "az": 14.0, "el": 9.5, "dist": 11.2, "tz": 2.25, "lens": 54.0},
        # Frame 336 (14.0s): Fin de gancho, rotación continua y respiración
        {"frame": 336, "az": 22.0, "el": 11.0, "dist": 11.0, "tz": 2.25, "lens": 54.0},
        # Frame 720 (30.0s): Mapeo de arquitectura global, leve dolly in
        {"frame": 720, "az": 18.0, "el": 11.0, "dist": 10.8, "tz": 2.20, "lens": 54.0},
        # Frame 1152 (48.0s): Enfoque dinámico en Compresor inferior (plinto)
        {"frame": 1152, "az": 22.0, "el": 12.0, "dist": 4.8, "tz": 0.50, "lens": 56.0},
        # Frame 1584 (66.0s): Travelling vertical al Condensador disipador
        {"frame": 1584, "az": 30.0, "el": 12.0, "dist": 6.2, "tz": 2.65, "lens": 56.0},
        # Frame 1968 (82.0s): Macro Dolly al Tubo Capilar (expansión criogénica)
        {"frame": 1968, "az": 16.0, "el": 10.0, "dist": 3.8, "tz": 0.95, "lens": 58.0},
        # Frame 2352 (98.0s): Paneo interior al Evaporador y alimentos
        {"frame": 2352, "az": 10.0, "el": 12.0, "dist": 5.4, "tz": 3.40, "lens": 54.0},
        # Frame 2640 (110.0s): Regreso suave a plano general continuo con ciclo completo
        {"frame": 2640, "az": 18.0, "el": 10.0, "dist": 11.2, "tz": 2.25, "lens": 54.0},
    ]

    # Interpolar y registrar keyframes de cámara con aceleración suave
    for kf in keyframes_timeline:
        fr = kf["frame"]
        az = math.radians(kf["az"])
        el = math.radians(kf["el"])
        dist = kf["dist"]
        target = Vector((0.0, 0.0, kf["tz"]))

        d_vec = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        pos = target + d_vec * dist

        camera_obj.location = pos
        camera_obj.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        cam_data.lens = kf["lens"]

        camera_obj.keyframe_insert(data_path="location", frame=fr)
        camera_obj.keyframe_insert(data_path="rotation_euler", frame=fr)
        cam_data.keyframe_insert(data_path="lens", frame=fr)

    # Suavizar curvas F-Curves con interpolación Bezier (compatible con Blender 4.x y 5.x)
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
    except Exception:
        pass

    if camera_obj.animation_data and camera_obj.animation_data.action:
        act = camera_obj.animation_data.action
        fcurves_list = []
        if hasattr(act, "fcurves"):
            fcurves_list.extend(act.fcurves)
        elif hasattr(act, "layers"):
            for layer in getattr(act, "layers", []):
                for strip in getattr(layer, "strips", []):
                    for bag in getattr(strip, "channelbags", []):
                        fcurves_list.extend(getattr(bag, "fcurves", []))
        for fc in fcurves_list:
            for kp in getattr(fc, "keyframe_points", []):
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    # Animación mecánica continua del compresor (pistón oscilando a 1.2 rev/s)
    cp = refrigerator_data.get("compressor_parts")
    if cp:
        rr = cp["rotor_root"]
        piston = cp["piston"]
        base_x = cp["piston_base_x"]
        rev_speed = 1.2
        for fr in range(1, total_frames + 1, 6):  # Keyframes cada 6 frames
            t = fr / fps
            ang = 2 * math.pi * rev_speed * t
            rr.rotation_euler = (0, 0, ang)
            rr.keyframe_insert(data_path="rotation_euler", frame=fr)
            piston.location = (base_x + 0.065 * math.cos(ang), 0, -0.17)
            piston.keyframe_insert(data_path="location", frame=fr)

    # Animación continua de flechas térmicas (pulsos de calor cada 1.5s)
    arrows_hot = refrigerator_data.get("arrows_hot", [])
    loop_fr = int(fps * 1.5)
    for i, a in enumerate(arrows_hot):
        base_pos = a.location.copy()
        for fr in range(1, total_frames + 1, 8):
            phase = (((fr / loop_fr) + i * 0.22) % 1.0)
            a.location = (base_pos.x + phase * 0.45, base_pos.y, base_pos.z)
            scale_fac = 0.6 + 0.6 * math.sin(phase * math.pi)
            a.scale = (scale_fac, 1.0, 1.0)
            a.keyframe_insert(data_path="location", frame=fr)
            a.keyframe_insert(data_path="scale", frame=fr)

    # Sincronización de visibilidad de etiquetas adaptativas por etapa narrativa
    if labels_dict:
        stage_visibility = {
            "overview_compressor": [(350, 720)],
            "overview_condenser":  [(420, 720)],
            "overview_dryer":      [(630, 720)],
            "overview_capillary":  [(490, 720)],
            "overview_evaporator": [(560, 720)],
            "close_compressor":    [(721, 1152)],
            "close_condenser":     [(1153, 1584)],
            "close_capillary":     [(1585, 1968)],
            "close_dryer":         [(1585, 1968)],
            "close_evaporator":    [(1969, 2352)],
        }
        for l_name, (txt_obj, line_obj) in labels_dict.items():
            objs = [txt_obj, line_obj]
            dot = bpy.data.objects.get(f"Dot_{l_name}")
            if dot:
                objs.append(dot)
            windows = stage_visibility.get(l_name, [(350, 720)])
            for o in objs:
                if not o:
                    continue
                # Inicia oculto en la introducción
                o.hide_render = True
                o.hide_viewport = True
                o.keyframe_insert(data_path="hide_render", frame=1)
                o.keyframe_insert(data_path="hide_viewport", frame=1)
                for w_start, w_end in windows:
                    o.hide_render = False
                    o.hide_viewport = False
                    o.keyframe_insert(data_path="hide_render", frame=w_start)
                    o.keyframe_insert(data_path="hide_viewport", frame=w_start)
                    o.hide_render = True
                    o.hide_viewport = True
                    o.keyframe_insert(data_path="hide_render", frame=w_end + 1)
                    o.keyframe_insert(data_path="hide_viewport", frame=w_end + 1)

    return {
        "status": "animated",
        "total_frames": total_frames,
        "duration_sec": total_frames / fps,
        "keyframes_count": len(keyframes_timeline),
    }
