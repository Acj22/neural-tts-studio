"""Lógica especializada del modelo de Refrigerador (Ciclo Termodinámico Cerrado).
Diseñado para videos educativos verticales en formato 9:16 (TikTok, Reels, Shorts).

ESTRUCTURA MODULAR:
1. Parámetros y Cues de Cámara/Etiquetas por rango de tiempo (Timeline Cues).
2. Construcción Geométrica del Refrigerador Icónico y Circuito Cerrado.
3. Motor de Etiquetas Adaptativas 3D (Zonas Seguras y Anti-Colisión).
4. Coreografía de Animación y Retención Visual (Interpolación Bézier y Pulsos).
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
# 1. TIMELINE CUES NARRATIVOS (SINCRONIZACIÓN EXACTA SEGUNDO A SEGUNDO)
# ==============================================================================

REFRIGERATOR_TIMELINE_CUES = [
    {
        "id": "st1_hook",
        "name": "1. Gancho y extracción de calor",
        "time_range": (0.0, 19.5),
        "frame_range": (1, 468),
        "camera": {"az": 22.0, "el": 10.0, "dist": 9.6, "tx": 0.0, "ty": 0.0, "tz": 1.95, "lens": 54.0},
        "active_labels": [],  # Ninguna etiqueta al inicio para mantener plano limpio
        "description": "Plano general completo del refrigerador en corte 3/4. Reconocible de inmediato.",
    },
    {
        "id": "st2_architecture",
        "name": "2. Presentación de los 5 componentes",
        "time_range": (19.5, 30.5),
        "frame_range": (469, 732),
        "camera": {"az": 22.0, "el": 10.0, "dist": 9.6, "tx": 0.0, "ty": 0.0, "tz": 1.95, "lens": 54.0},
        "active_labels": [
            "overview_compressor",
            "overview_condenser",
            "overview_dryer",
            "overview_capillary",
            "overview_evaporator",
        ],
        "description": "Aparición ordenada de los 5 componentes en columnas laterales seguras.",
    },
    {
        "id": "st3_compressor",
        "name": "3. Compresor hermético",
        "time_range": (30.5, 47.5),
        "frame_range": (733, 1140),
        "camera": {"az": 18.0, "el": 12.0, "dist": 3.2, "tx": 0.0, "ty": 0.05, "tz": 0.38, "lens": 56.0},
        "active_labels": ["close_compressor"],  # ÚNICAMENTE compresor
        "description": "Acercamiento a la base, animación de bombeo mecánico y compresión.",
    },
    {
        "id": "st4_condenser",
        "name": "4. Condensador trasero",
        "time_range": (47.5, 65.5),
        "frame_range": (1141, 1572),
        "camera": {"az": 148.0, "el": 12.0, "dist": 4.6, "tx": 0.0, "ty": 0.68, "tz": 2.35, "lens": 54.0},
        "active_labels": ["close_condenser"],  # ÚNICAMENTE condensador
        "description": "Reencuadre a la rejilla trasera, disipación de calor al ambiente exterior.",
    },
    {
        "id": "st5_expansion",
        "name": "5. Filtro secador y tubo capilar",
        "time_range": (65.5, 81.5),
        "frame_range": (1573, 1956),
        # Encuadre frontal limpio directo al filtro y capilar sin interferencia de paredes laterales
        "camera": {"az": 16.0, "el": 12.0, "dist": 2.2, "tx": 0.55, "ty": 0.28, "tz": 0.95, "lens": 54.0},
        "active_labels": ["close_capillary", "close_dryer"],  # Separadas sin cruzarse ni tocar bordes
        "description": "Filtro deshidratador a la derecha y capilar a la izquierda, caída de presión.",
    },
    {
        "id": "st6_evaporator",
        "name": "6. Evaporador interior",
        "time_range": (81.5, 96.5),
        "frame_range": (1957, 2316),
        "camera": {"az": 16.0, "el": 14.0, "dist": 3.4, "tx": 0.0, "ty": 0.25, "tz": 3.20, "lens": 54.0},
        "active_labels": ["close_evaporator"],  # ÚNICAMENTE evaporador
        "description": "Interior del congelador, serpentín gélido y absorción de calor de los alimentos.",
    },
    {
        "id": "st7_closure",
        "name": "7. Retorno y cierre del ciclo",
        "time_range": (96.5, 105.0),
        "frame_range": (2317, 2520),
        "camera": {"az": 22.0, "el": 10.0, "dist": 9.6, "tx": 0.0, "ty": 0.0, "tz": 1.95, "lens": 54.0},
        "active_labels": [],  # Cierre limpio sin etiquetas que obstruyan la animación
        "description": "Pull-back al plano general mostrando el ciclo termodinámico continuo.",
    },
]


# ==============================================================================
# 2. CONSTRUCCIÓN GEOMÉTRICA DEL REFRIGERADOR ICÓNICO Y CIRCUITO CERRADO
# ==============================================================================

def build_specialized_refrigerator_model(
    center_z: float = 1.95,
) -> Dict[str, Any]:
    """Construye un refrigerador doméstico vertical 9:16 icónico y reconocible:
    - Gabinete de 2 puertas con división congelador/conservador y tiradores.
    - Condensador en la rejilla trasera integrado dentro del perfil vertical.
    - Estantes de vidrio con alimentos para referenciar escala y uso real.
    - Materiales PBR optimizados para eliminar grano/ruido en EEVEE."""
    if bpy is None:
        return {}

    mats = setup_engine_materials()

    Z = lambda z: z + (center_z - 1.95)

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

    # Materiales PBR limpios con rugosidad calibrada anti-ruido
    m_white = get_or_create_material("Mat_WhiteGlossCabinet", hex_to_rgba("#F8FAFC"), roughness=0.22, metallic=0.04)
    m_dark_metal = get_or_create_material("Mat_DarkMetal", hex_to_rgba("#1E293B"), roughness=0.32, metallic=0.75)
    m_foam = get_or_create_material("Mat_FoamInsulation", hex_to_rgba("#EAB308"), roughness=0.55)
    m_liner = get_or_create_material("Mat_FridgeLiner", hex_to_rgba("#E2E8F0"), roughness=0.28)
    m_glass = get_or_create_material("Mat_GlassShelf", hex_to_rgba("#BAE6FD"), roughness=0.10, metallic=0.0, alpha=0.55)
    m_frost = get_or_create_material("Mat_FrostBlue", hex_to_rgba("#38BDF8"), roughness=0.22, metallic=0.1)
    m_copper = get_or_create_material("Mat_CopperBright", hex_to_rgba("#C25E2E"), roughness=0.18, metallic=0.92)
    m_cast_iron = get_or_create_material("Mat_CastIronDark", hex_to_rgba("#0F172A"), roughness=0.40, metallic=0.82)
    m_cond_black = get_or_create_material("Mat_CondenserBlack", hex_to_rgba("#18181B"), roughness=0.32, metallic=0.88)

    # Dimensiones verticales compactas (proporción áurea para 9:16)
    # Ancho total: 1.6 m (X: [-0.80, 0.80]), Fondo: 1.2 m (Y: [-0.55, 0.65]), Alto: 3.8 m
    zb, zt = Z(0.68), Z(3.80)
    z_freeze_div = Z(2.55)

    # 1. Gabinete exterior con silueta reconocible (corte frontal 3/4)
    # Pared lateral izquierda (en corte para mostrar el aislamiento de 3 capas)
    w_left = C.box("Wall_Left_Outer", (0.10, 1.15, zt - zb), (-0.75, 0.05, (zb + zt) / 2), m_white, bev=0.015)
    w_left_ins = C.box("Wall_Left_Foam", (0.08, 1.10, zt - zb - 0.05), (-0.66, 0.05, (zb + zt) / 2), m_foam)
    w_left_in = C.box("Wall_Left_Liner", (0.04, 1.05, zt - zb - 0.10), (-0.60, 0.05, (zb + zt) / 2), m_liner)
    grp("cabinet", w_left, w_left_ins, w_left_in)

    # Pared lateral derecha (blanca con acabado limpio)
    w_right = C.box("Wall_Right", (0.12, 1.15, zt - zb), (0.76, 0.05, (zb + zt) / 2), m_white, bev=0.015)
    grp("cabinet", w_right)

    # Techo y piso del gabinete
    w_top = C.box("Wall_Top", (1.64, 1.15, 0.12), (0.0, 0.05, zt + 0.06), m_white, bev=0.015)
    w_bot = C.box("Wall_Bottom", (1.64, 1.15, 0.10), (0.0, 0.05, zb - 0.05), m_white, bev=0.015)
    grp("cabinet", w_top, w_bot)

    # Pared trasera que separa el interior del condensador exterior
    w_back = C.box("Wall_Back", (1.60, 0.10, zt - zb), (0.0, 0.60, (zb + zt) / 2), m_white)
    grp("cabinet", w_back)

    # División horizontal entre Congelador y Conservador
    freezer_div = C.box("Freezer_Divider", (1.40, 0.95, 0.12), (0.0, 0.05, z_freeze_div), m_white, bev=0.01)
    grp("cabinet", freezer_div)

    # Elementos de identidad de refrigerador:
    # Tiradores dobles cromados en la puerta
    handle_top = C.cylinder("Handle_Freezer", 0.022, 0.45, (0.76, -0.56, Z(3.15)), "Z", m_dark_metal, 16)
    handle_bot = C.cylinder("Handle_Fridge", 0.022, 0.70, (0.76, -0.56, Z(1.75)), "Z", m_dark_metal, 16)
    hinge_top = C.cylinder("Hinge_Top", 0.035, 0.06, (0.74, -0.52, zt + 0.06), "Z", m_dark_metal, 16)
    hinge_mid = C.cylinder("Hinge_Mid", 0.035, 0.06, (0.74, -0.52, z_freeze_div), "Z", m_dark_metal, 16)
    feet_l = C.cylinder("Foot_Left", 0.045, 0.08, (-0.68, -0.45, Z(0.04)), "Z", m_dark_metal, 16)
    feet_r = C.cylinder("Foot_Right", 0.045, 0.08, (0.68, -0.45, Z(0.04)), "Z", m_dark_metal, 16)
    grp("cabinet", handle_top, handle_bot, hinge_top, hinge_mid, feet_l, feet_r)

    # Estantes interiores y alimentos
    shelf1 = C.box("Shelf_1", (1.30, 0.85, 0.025), (0.0, 0.05, Z(1.95)), m_glass)
    shelf2 = C.box("Shelf_2", (1.30, 0.85, 0.025), (0.0, 0.05, Z(1.35)), m_glass)
    crisper = C.box("Crisper_Drawer", (1.30, 0.85, 0.45), (0.0, 0.05, Z(0.92)), m_glass, bev=0.01)
    grp("cabinet", shelf1, shelf2, crisper)

    bottle1 = C.cylinder("Bottle_1", 0.06, 0.32, (-0.40, -0.15, Z(1.53)), "Z", m_frost, 16)
    bottle2 = C.cylinder("Bottle_2", 0.05, 0.28, (-0.25, -0.15, Z(1.51)), "Z", m_copper, 16)
    fruit1 = C.sphere("Fruit_1", 0.09, (0.30, 0.0, Z(1.44)), get_or_create_material("Mat_Orange", hex_to_rgba("#EA580C"), roughness=0.4))
    grp("cabinet", bottle1, bottle2, fruit1)

    # Plinto / Compartimento de máquinas inferior
    plinth_floor = C.box("Plinth_Floor", (1.64, 1.15, 0.08), (0.0, 0.05, Z(0.04)), m_liner, bev=0.01)
    plinth_back = C.box("Plinth_Back", (1.60, 0.08, 0.60), (0.0, 0.60, Z(0.34)), m_white)
    grp("cabinet", plinth_floor, plinth_back)

    # 2. Compresor Hermético (montado en la base plinth)
    comp_root = C.empty("Compressor_Root", (0.0, 0.05, Z(0.35)))
    shell = C.cylinder("Compressor_Shell", 0.26, 0.36, (0, 0, 0), "Z", m_cast_iron, 32, parent=comp_root)
    cap_top = C.cylinder("Compressor_Cap_Top", 0.25, 0.08, (0, 0, 0.20), "Z", m_cast_iron, 32, parent=comp_root, r2=0.17)
    cap_bot = C.cylinder("Compressor_Cap_Bot", 0.25, 0.08, (0, 0, -0.20), "Z", m_cast_iron, 32, parent=comp_root, r2=0.25)
    rotor_root = C.empty("Comp_Rotor_Root", (0, 0, 0), parent=comp_root)
    crank = C.cylinder("Comp_CrankPin", 0.035, 0.16, (0.06, 0, 0), "Z", m_copper, 16, parent=rotor_root)
    piston = C.cylinder("Comp_Piston", 0.065, 0.12, (0, 0, -0.15), "X", m_copper, 16, parent=comp_root)
    grp("compressor", shell, cap_top, cap_bot, crank, piston)

    data["compressor_parts"] = {
        "rotor_root": rotor_root,
        "piston": piston,
        "piston_base_x": 0.0,
    }
    # Anclaje exacto en la cúpula superior del compresor
    data["anchors_3d"]["compressor"] = Vector((0.0, 0.05, Z(0.53)))

    # 3. Serpentín del Condensador (Rejilla montada en la parte trasera exterior)
    cond_x0, cond_x1 = -0.62, 0.62
    cond_ztop, cond_zbot = Z(3.55), Z(1.10)
    cond_rows = 10
    cond_y = 0.68

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

    cond_pts = _serpentine_pts(cond_x0, cond_x1, cond_ztop, cond_zbot, cond_rows, cond_y, True)
    poly_cond = C.rounded_polyline([Vector(p) for p in cond_pts], 0.045)
    tube_cond = C.tube_from_path("Pipe_condenser", poly_cond, 0.018, m_cond_black)

    support_l = C.cylinder("Cond_Support_L", 0.012, cond_ztop - cond_zbot + 0.20, (-0.35, cond_y - 0.01, (cond_ztop + cond_zbot) / 2), "Z", m_dark_metal, 12)
    support_r = C.cylinder("Cond_Support_R", 0.012, cond_ztop - cond_zbot + 0.20, (0.35, cond_y - 0.01, (cond_ztop + cond_zbot) / 2), "Z", m_dark_metal, 12)
    grp("condenser", tube_cond, support_l, support_r)

    # Anclaje exacto sobre la tubería del condensador trasero
    data["anchors_3d"]["condenser"] = Vector((0.35, cond_y, Z(2.45)))

    # 4. Filtro Deshidratador y Tubo Capilar (Ubicados en la base lateral)
    dryer = C.cylinder("Filter_Dryer", 0.042, 0.24, (0.65, 0.45, Z(0.85)), "Z", m_copper, 20)
    grp("dryer", dryer)
    # Anclaje exacto en el extremo superior de cobre del filtro secador
    data["anchors_3d"]["dryer"] = Vector((0.65, 0.45, Z(0.97)))

    cap_path = C.helix_path((0.65, 0.15, Z(0.82)), "Z", 0.42, 0.038, turns=8.0, pts_per_turn=12)
    tube_capillary = C.tube_from_path("Pipe_capillary", cap_path, 0.009, m_copper)
    grp("capillary", tube_capillary)
    # Anclaje exacto en la espiral de cobre del tubo capilar
    data["anchors_3d"]["capillary"] = Vector((0.65, 0.15, Z(0.92)))

    # 5. Evaporador (Serpentín gélido en el congelador interior)
    evap_pts = _serpentine_pts(-0.55, 0.55, Z(3.60), Z(2.80), 6, 0.25, True)
    poly_evap = C.rounded_polyline([Vector(p) for p in evap_pts], 0.04)
    tube_evap = C.tube_from_path("Pipe_evaporator", poly_evap, 0.020, m_frost)
    frost_panel = C.box("Frost_Panel", (1.20, 0.04, 0.95), (0.0, 0.42, Z(3.20)), m_frost, bev=0.01)
    grp("evaporator", tube_evap, frost_panel)
    # Anclaje exacto en el serpentín frontal del evaporador
    data["anchors_3d"]["evaporator"] = Vector((0.0, 0.23, Z(3.20)))

    # 6. Tuberías del Circuito Cerrado
    p_disc = C.rounded_polyline([
        Vector((0.0, 0.25, Z(0.48))),
        Vector((0.0, cond_y, Z(0.48))),
        Vector((cond_x0, cond_y, Z(0.65))),
        Vector(cond_pts[0])
    ], 0.04)
    tube_disc = C.tube_from_path("Pipe_discharge", p_disc, 0.016, m_copper)

    p_to_dryer = C.rounded_polyline([
        Vector(cond_pts[-1]),
        Vector((0.65, cond_y, Z(1.05))),
        Vector((0.65, 0.45, Z(0.98)))
    ], 0.03)
    tube_to_dryer = C.tube_from_path("Pipe_to_dryer", p_to_dryer, 0.014, m_copper)

    p_cap_to_evap = C.rounded_polyline([
        Vector((0.65, 0.15, Z(1.24))),
        Vector((0.65, 0.35, Z(1.40))),
        Vector((0.65, 0.35, Z(2.70))),
        Vector(evap_pts[0])
    ], 0.04)
    tube_cap_to_evap = C.tube_from_path("Pipe_cap_to_evap", p_cap_to_evap, 0.011, m_copper)

    p_suct = C.rounded_polyline([
        Vector(evap_pts[-1]),
        Vector((-0.65, 0.35, Z(2.70))),
        Vector((-0.65, 0.15, Z(0.45))),
        Vector((-0.18, 0.05, Z(0.45)))
    ], 0.05)
    tube_suct = C.tube_from_path("Pipe_suction", p_suct, 0.022, m_frost)

    grp("compressor", tube_disc, tube_to_dryer, tube_cap_to_evap, tube_suct)

    # 7. Flechas térmicas volumétricas
    arrows_hot = []
    mat_arrow_hot = C.emissive_material("Mat_ArrowHot", (1.0, 0.32, 0.08), 3.8)
    for i in range(4):
        a = C.make_arrow(f"HeatOut_{i+1}", 0.36, 0.018, mat_arrow_hot)
        a.location = (0.0 + (i - 1.5) * 0.30, cond_y + 0.10, Z(1.60 + i * 0.50))
        a.rotation_euler = (0, 0, math.radians(90))
        arrows_hot.append(a)
        grp("heat_arrows", a)

    arrows_cold = []
    mat_arrow_cold = C.emissive_material("Mat_ArrowCold", (0.25, 0.75, 1.0), 3.8)
    for i in range(3):
        a = C.make_arrow(f"HeatIn_{i+1}", 0.30, 0.016, mat_arrow_cold)
        a.location = (-0.35 + i * 0.35, -0.15, Z(3.10))
        a.rotation_euler = (0, 0, math.radians(0))
        arrows_cold.append(a)
        grp("cold_arrows", a)

    data["arrows_hot"] = arrows_hot
    data["arrows_cold"] = arrows_cold
    return data


# ==============================================================================
# 3. GENERACIÓN DE ETIQUETAS ADAPTATIVAS (OVERVIEW Y MACRO)
# ==============================================================================

def generate_refrigerator_adaptive_labels(
    refrigerator_data: Dict[str, Any],
    cam_pos: Vector,
    cam_target: Vector,
    config: Educational916FrameworkConfig,
) -> Dict[str, Tuple[Any, Any]]:
    """Genera las etiquetas 3D billboard adaptativas para el refrigerador:
    - Conjunto Overview (para la presentación de los 5 componentes en 00:20-00:30).
    - Conjunto Macro especializado por etapa (para cada zoom de componente)."""
    anchors_3d = refrigerator_data.get("anchors_3d", {})
    engine = AdaptiveLabelsEngine(config.safe_zones, config.labels)

    lbl_collection = bpy.data.collections.get("Adaptive_Labels_9_16")
    if not lbl_collection:
        lbl_collection = bpy.data.collections.new("Adaptive_Labels_9_16")
        bpy.context.scene.collection.children.link(lbl_collection)

    created_labels: Dict[str, Tuple[Any, Any]] = {}

    cam_o = bpy.context.scene.camera or bpy.data.objects.get("Director_Camera_Obj") or bpy.data.objects.get("Camera_916")
    if cam_o:
        cam_o.location = cam_pos
        cam_o.rotation_euler = (cam_target - cam_pos).to_track_quat("-Z", "Y").to_euler()
        cam_o.data.lens = config.camera.lens_mm
        bpy.context.view_layer.update()

    # 1. Conjunto Overview (5 componentes ordenados en 2 columnas laterales seguras)
    overview_specs = {
        "condenser":  ("CONDENSADOR", 0.74, 0.68),
        "dryer":      ("FILTRO SECADOR", 0.74, 0.48),
        "compressor": ("COMPRESOR", 0.74, 0.28),
        "evaporator": ("EVAPORADOR", 0.26, 0.70),
        "capillary":  ("TUBO CAPILAR", 0.26, 0.38),
    }

    # Evaluar cámara para Stage 2 (Overview)
    az_st2 = math.radians(22.0)
    el_st2 = math.radians(10.0)
    c_tgt_st2 = Vector((0.0, 0.0, 1.95))
    d_st2 = Vector((math.sin(az_st2) * math.cos(el_st2), -math.cos(az_st2) * math.cos(el_st2), math.sin(el_st2)))
    c_pos_st2 = c_tgt_st2 + d_st2 * 9.6

    if cam_o:
        cam_o.location = c_pos_st2
        cam_o.rotation_euler = (c_tgt_st2 - c_pos_st2).to_track_quat("-Z", "Y").to_euler()
        cam_o.data.lens = 54.0
        bpy.context.view_layer.update()

    for key, (txt_content, tu, tv) in overview_specs.items():
        if key in anchors_3d:
            anchor_pt = anchors_3d[key]
            txt_obj, line_obj = create_adaptive_3d_label(
                name=f"overview_{key}",
                text=txt_content,
                anchor_3d=anchor_pt,
                target_screen_u=tu,
                target_screen_v=tv,
                cam_pos=c_pos_st2,
                cam_target=c_tgt_st2,
                config=config,
                collection=lbl_collection,
                cam_obj=cam_o,
            )
            created_labels[f"overview_{key}"] = (txt_obj, line_obj)

    # 2. Conjunto Macro por Etapa Individual (con encuadres de cámara dedicados)
    cond_y = 0.68
    close_specs = [
        # (etiqueta_key, comp_key, texto, target_u, target_v, az_deg, el_deg, dist, tx, ty, tz, lens)
        ("close_compressor", "compressor", "COMPRESOR", 0.30, 0.72, 18.0, 12.0, 3.2, 0.0, 0.05, 0.38, 56.0),
        ("close_condenser",  "condenser",  "CONDENSADOR", 0.72, 0.72, 148.0, 12.0, 4.6, 0.0, cond_y, 2.35, 54.0),
        ("close_capillary",  "capillary",  "TUBO CAPILAR", 0.28, 0.36, 16.0, 12.0, 2.2, 0.55, 0.28, 0.95, 54.0),
        ("close_dryer",      "dryer",      "FILTRO SECADOR", 0.72, 0.70, 16.0, 12.0, 2.2, 0.55, 0.28, 0.95, 54.0),
        ("close_evaporator", "evaporator", "EVAPORADOR", 0.30, 0.74, 16.0, 14.0, 3.4, 0.0, 0.25, 3.20, 54.0),
    ]

    for lbl_id, comp_k, txt_str, tu, tv, az_d, el_d, dist_val, tx_val, ty_val, tz_val, lens_val in close_specs:
        az = math.radians(az_d)
        el = math.radians(el_d)
        c_target = Vector((tx_val, ty_val, tz_val))
        d_vec = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        c_pos = c_target + d_vec * dist_val

        if cam_o:
            cam_o.location = c_pos
            cam_o.rotation_euler = (c_target - c_pos).to_track_quat("-Z", "Y").to_euler()
            cam_o.data.lens = lens_val
            bpy.context.view_layer.update()

        anchor_pt = anchors_3d[comp_k]
        txt_obj, line_obj = create_adaptive_3d_label(
            name=lbl_id,
            text=txt_str,
            anchor_3d=anchor_pt,
            target_screen_u=tu,
            target_screen_v=tv,
            cam_pos=c_pos,
            cam_target=c_target,
            config=config,
            collection=lbl_collection,
            cam_obj=cam_o,
        )
        created_labels[lbl_id] = (txt_obj, line_obj)

    return created_labels


# ==============================================================================
# 4. ANIMACIÓN Y SINCRONIZACIÓN DE LÍNEA DE TIEMPO
# ==============================================================================

def animate_refrigerator_vertical_showcase(
    refrigerator_data: Dict[str, Any],
    camera_obj: Any,
    config: Educational916FrameworkConfig,
    labels_dict: Optional[Dict[str, Tuple[Any, Any]]] = None,
) -> Dict[str, Any]:
    """Aplica la coreografía cinemática con sincronización estricta de la narración."""
    if bpy is None or not camera_obj:
        return {"status": "mock"}

    fps = config.timeline.fps
    total_frames = config.timeline.total_frames
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames

    cam_data = camera_obj.data
    cam_data.sensor_fit = config.camera.sensor_fit

    # 1. Configuración de keyframes cinemáticos por cue narrativo
    cues = REFRIGERATOR_TIMELINE_CUES

    for cue in cues:
        f_start, f_end = cue["frame_range"]
        cam_info = cue["camera"]
        az = math.radians(cam_info["az"])
        el = math.radians(cam_info["el"])
        dist = cam_info["dist"]
        tx = cam_info.get("tx", 0.0)
        ty = cam_info.get("ty", 0.0)
        tz = cam_info.get("tz", 1.95)
        lens = cam_info["lens"]

        target = Vector((tx, ty, tz))
        d_vec = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        pos = target + d_vec * dist

        camera_obj.location = pos
        camera_obj.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        cam_data.lens = lens

        for sub_fr in (f_start, f_end):
            camera_obj.keyframe_insert(data_path="location", frame=sub_fr)
            camera_obj.keyframe_insert(data_path="rotation_euler", frame=sub_fr)
            cam_data.keyframe_insert(data_path="lens", frame=sub_fr)

    # 2. Interpolación limpia por etapa (sin saltos anómalos de F-Curves)
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
                kp.interpolation = "CONSTANT"

    # 3. Animación mecánica continua del compresor
    cp = refrigerator_data.get("compressor_parts")
    if cp:
        rr = cp["rotor_root"]
        piston = cp["piston"]
        base_x = cp["piston_base_x"]
        rev_speed = 1.25
        for fr in range(1, total_frames + 1, 6):
            t = fr / fps
            ang = 2 * math.pi * rev_speed * t
            rr.rotation_euler = (0, 0, ang)
            rr.keyframe_insert(data_path="rotation_euler", frame=fr)
            piston.location = (base_x + 0.065 * math.cos(ang), 0, -0.15)
            piston.keyframe_insert(data_path="location", frame=fr)

    # 4. Animación continua de flechas térmicas (pulsos rítmicos cada 1.5s)
    arrows_hot = refrigerator_data.get("arrows_hot", [])
    loop_fr = int(fps * 1.5)
    for i, a in enumerate(arrows_hot):
        base_pos = a.location.copy()
        for fr in range(1, total_frames + 1, 8):
            phase = (((fr / loop_fr) + i * 0.25) % 1.0)
            a.location = (base_pos.x, base_pos.y + phase * 0.40, base_pos.z)
            scale_fac = 0.5 + 0.7 * math.sin(phase * math.pi)
            a.scale = (scale_fac, scale_fac, scale_fac)
            a.keyframe_insert(data_path="location", frame=fr)
            a.keyframe_insert(data_path="scale", frame=fr)

    # 5. Sincronización estricta de visibilidad de etiquetas según los cues de la narración
    if labels_dict:
        # Construir mapa de visibilidad por etiqueta basado exactamente en REFRIGERATOR_TIMELINE_CUES
        visibility_windows: Dict[str, List[Tuple[int, int]]] = {k: [] for k in labels_dict.keys()}
        for cue in cues:
            f_s, f_e = cue["frame_range"]
            for l_key in cue["active_labels"]:
                if l_key in visibility_windows:
                    visibility_windows[l_key].append((f_s, f_e))

        for l_name, (txt_obj, line_obj) in labels_dict.items():
            objs = [txt_obj, line_obj]
            dot = bpy.data.objects.get(f"Dot_{l_name}")
            if dot:
                objs.append(dot)
            badge = bpy.data.objects.get(f"Badge_{l_name}")
            if badge:
                objs.append(badge)

            windows = visibility_windows.get(l_name, [])
            for o in objs:
                if not o:
                    continue
                # Inicia oculto por defecto
                o.hide_render = True
                o.hide_viewport = True
                o.keyframe_insert(data_path="hide_render", frame=1)
                o.keyframe_insert(data_path="hide_viewport", frame=1)

                for w_start, w_end in windows:
                    o.hide_render = False
                    o.hide_viewport = False
                    o.keyframe_insert(data_path="hide_render", frame=w_start)
                    o.keyframe_insert(data_path="hide_viewport", frame=w_start)
                    o.keyframe_insert(data_path="hide_render", frame=w_end)
                    o.keyframe_insert(data_path="hide_viewport", frame=w_end)

                    if w_end < total_frames:
                        o.hide_render = True
                        o.hide_viewport = True
                        o.keyframe_insert(data_path="hide_render", frame=w_end + 1)
                        o.keyframe_insert(data_path="hide_viewport", frame=w_end + 1)

            # Forzar interpolación CONSTANT en visibilidad
            for o in objs:
                if not o or not o.animation_data or not o.animation_data.action:
                    continue
                act = o.animation_data.action
                fcs = []
                if hasattr(act, "fcurves"):
                    fcs.extend(act.fcurves)
                elif hasattr(act, "layers"):
                    for layer in getattr(act, "layers", []):
                        for strip in getattr(layer, "strips", []):
                            for bag in getattr(strip, "channelbags", []):
                                fcs.extend(getattr(bag, "fcurves", []))
                for fc in fcs:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"

    return {
        "status": "animated",
        "total_frames": total_frames,
        "duration_sec": total_frames / fps,
        "cues_count": len(cues),
    }
