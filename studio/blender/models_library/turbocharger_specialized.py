"""Lógica especializada del modelo 3D de Turbocompresor Automotriz de Alta Fidelidad.
Refactorizado según directrices maestras de producción vertical 9:16:
1. Framerate mínimo 24 fps, Motion Blur activo, rotación continua sin tiempos muertos.
2. Zonas seguras estrictas 9:16 (u: 10%-90%, v: >=28%), clamping y líneas directrices cortas.
3. Cámara con constraint TRACK_TO y target animado, vista explosiva real y compuerta wastegate articulada.
4. Modificadores Bevel + Weighted Normal, detalles mecánicos y splines 3D emisivas de flujo continuo.
5. Iluminación tri-punto con contraste de temperatura (Warm Rim Inconel vs Cool Rim Billet) y EEVEE Next denoise.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError:
    bpy = None
    Matrix = None
    Vector = None

from studio.blender.educational_vertical_framework import (
    AdaptiveLabelsEngine,
    Educational916FrameworkConfig,
    create_adaptive_3d_label,
)
from studio.blender.materials import get_or_create_material, hex_to_rgba
from studio.blender.models_library import _common as C


# ==============================================================================
# 1. TIMELINE CUES NARRATIVOS (14 ESCENAS DINÁMICAS · 131.7s TOTAL)
# ==============================================================================

TURBO_TIMELINE_CUES = [
    {
        "id": "st01_hero_orbit",
        "name": "1. Gancho: Multiplicador de Potencia",
        "time_range": (0.5, 10.88),
        "frame_range": (13, 261),
        "camera_start": {"az": 26.0, "el": 16.0, "dist": 4.6, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "camera_end":   {"az": 36.0, "el": 18.0, "dist": 4.3, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "active_labels": [],
        "target": (0.0, 0.0, 1.25),
    },
    {
        "id": "st02_exploded_view",
        "name": "2. Despiece Axial: Dos Mundos Opuestos",
        "time_range": (10.88, 20.15),
        "frame_range": (262, 483),
        "camera_start": {"az": 22.0, "el": 22.0, "dist": 4.6, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "camera_end":   {"az": 28.0, "el": 20.0, "dist": 4.3, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "active_labels": ["overview_turbine", "overview_chra", "overview_compressor"],
        "target": (0.0, 0.0, 1.25),
    },
    {
        "id": "st03_inconel_macro",
        "name": "3. Lado Caliente: Turbina Inconel a 950°C",
        "time_range": (20.15, 29.74),
        "frame_range": (484, 713),
        "camera_start": {"az": 40.0, "el": 18.0, "dist": 3.7, "tx": 0.32, "ty": -0.05, "tz": 1.25, "lens": 42.0},
        "camera_end":   {"az": 46.0, "el": 20.0, "dist": 3.4, "tx": 0.32, "ty": -0.05, "tz": 1.25, "lens": 42.0},
        "active_labels": ["close_turbine"],
        "target": (0.32, -0.05, 1.25),
    },
    {
        "id": "st04_exhaust_flange",
        "name": "4. Voluta Espiral y Flujo de Gases",
        "time_range": (29.74, 38.6),
        "frame_range": (714, 926),
        "camera_start": {"az": 54.0, "el": 16.0, "dist": 3.8, "tx": 0.30, "ty": 0.15, "tz": 1.20, "lens": 42.0},
        "camera_end":   {"az": 60.0, "el": 14.0, "dist": 3.5, "tx": 0.30, "ty": 0.15, "tz": 1.20, "lens": 42.0},
        "active_labels": [],
        "target": (0.30, 0.15, 1.20),
    },
    {
        "id": "st05_chra_cutaway",
        "name": "5. Cartucho Central CHRA: 150,000 RPM",
        "time_range": (38.6, 47.69),
        "frame_range": (927, 1144),
        "camera_start": {"az": 18.0, "el": 20.0, "dist": 3.6, "tx": 0.0, "ty": -0.08, "tz": 1.25, "lens": 42.0},
        "camera_end":   {"az": 24.0, "el": 22.0, "dist": 3.3, "tx": 0.0, "ty": -0.08, "tz": 1.25, "lens": 42.0},
        "active_labels": ["close_chra"],
        "target": (0.0, -0.08, 1.25),
    },
    {
        "id": "st06_oil_lubrication",
        "name": "6. Lubricación y Película Hidrodinámica",
        "time_range": (47.69, 57.25),
        "frame_range": (1145, 1373),
        "camera_start": {"az": 14.0, "el": 26.0, "dist": 3.5, "tx": 0.0, "ty": -0.04, "tz": 1.26, "lens": 42.0},
        "camera_end":   {"az": 20.0, "el": 28.0, "dist": 3.2, "tx": 0.0, "ty": -0.04, "tz": 1.26, "lens": 42.0},
        "active_labels": [],
        "target": (0.0, -0.04, 1.26),
    },
    {
        "id": "st07_billet_compressor",
        "name": "7. Lado Frío: Compresor Billet CNC",
        "time_range": (57.25, 66.43),
        "frame_range": (1374, 1594),
        "camera_start": {"az": -36.0, "el": 18.0, "dist": 3.7, "tx": -0.32, "ty": -0.05, "tz": 1.25, "lens": 42.0},
        "camera_end":   {"az": -42.0, "el": 20.0, "dist": 3.4, "tx": -0.32, "ty": -0.05, "tz": 1.25, "lens": 42.0},
        "active_labels": ["close_compressor"],
        "target": (-0.32, -0.05, 1.25),
    },
    {
        "id": "st08_intake_horn",
        "name": "8. Admisión Masiva de Aire Fresco",
        "time_range": (66.43, 75.05),
        "frame_range": (1595, 1801),
        "camera_start": {"az": -58.0, "el": 16.0, "dist": 3.8, "tx": -0.45, "ty": 0.0, "tz": 1.25, "lens": 42.0},
        "camera_end":   {"az": -64.0, "el": 14.0, "dist": 3.5, "tx": -0.45, "ty": 0.0, "tz": 1.25, "lens": 42.0},
        "active_labels": ["overview_intake"],
        "target": (-0.45, 0.0, 1.25),
    },
    {
        "id": "st09_boost_discharge",
        "name": "9. Difusor e Impulsión de Boost",
        "time_range": (75.05, 84.01),
        "frame_range": (1802, 2016),
        "camera_start": {"az": -24.0, "el": 14.0, "dist": 3.8, "tx": -0.30, "ty": 0.30, "tz": 1.35, "lens": 42.0},
        "camera_end":   {"az": -30.0, "el": 16.0, "dist": 3.5, "tx": -0.30, "ty": 0.30, "tz": 1.35, "lens": 42.0},
        "active_labels": [],
        "target": (-0.30, 0.30, 1.35),
    },
    {
        "id": "st10_wastegate_actuator",
        "name": "10. Control de Presión: Actuador Wastegate",
        "time_range": (84.01, 93.12),
        "frame_range": (2017, 2234),
        "camera_start": {"az": 32.0, "el": 20.0, "dist": 3.6, "tx": 0.22, "ty": 0.22, "tz": 1.38, "lens": 42.0},
        "camera_end":   {"az": 38.0, "el": 22.0, "dist": 3.3, "tx": 0.22, "ty": 0.22, "tz": 1.38, "lens": 42.0},
        "active_labels": ["close_wastegate"],
        "target": (0.22, 0.22, 1.38),
    },
    {
        "id": "st11_wastegate_bypass",
        "name": "11. Apertura de Compuerta y Bypass",
        "time_range": (93.12, 102.71),
        "frame_range": (2235, 2464),
        "camera_start": {"az": 38.0, "el": 18.0, "dist": 3.6, "tx": 0.26, "ty": 0.16, "tz": 1.30, "lens": 42.0},
        "camera_end":   {"az": 44.0, "el": 20.0, "dist": 3.3, "tx": 0.26, "ty": 0.16, "tz": 1.30, "lens": 42.0},
        "active_labels": [],
        "target": (0.26, 0.16, 1.30),
    },
    {
        "id": "st12_thermal_gradient",
        "name": "12. Gradiente Térmico: 950°C vs 40°C",
        "time_range": (102.71, 112.08),
        "frame_range": (2465, 2689),
        "camera_start": {"az": 2.0,  "el": 48.0, "dist": 4.2, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "camera_end":   {"az": -4.0, "el": 45.0, "dist": 3.9, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "active_labels": [],
        "target": (0.0, 0.0, 1.25),
    },
    {
        "id": "st13_high_speed_orbit",
        "name": "13. Régimen Continuo a Plena Carga",
        "time_range": (112.08, 121.42),
        "frame_range": (2690, 2914),
        "camera_start": {"az": 20.0, "el": 18.0, "dist": 4.4, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "camera_end":   {"az": 65.0, "el": 16.0, "dist": 4.1, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "active_labels": [],
        "target": (0.0, 0.0, 1.25),
    },
    {
        "id": "st14_hero_climax",
        "name": "14. Cierre Heroico: Máximo Boost",
        "time_range": (121.42, 130.72),
        "frame_range": (2915, 3137),
        "camera_start": {"az": 65.0, "el": 16.0, "dist": 4.2, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "camera_end":   {"az": 105.0, "el": 14.0, "dist": 3.9, "tx": 0.0, "ty": 0.0, "tz": 1.25, "lens": 44.0},
        "active_labels": [],
        "target": (0.0, 0.0, 1.25),
    },
]


# ==============================================================================
# 2. GENERADORES GEOMÉTRICOS DE ALTA FIDELIDAD Y ACABADO INDUSTRIAL
# ==============================================================================

def apply_engineering_finish(obj: Any, bevel_width: float = 0.015, segments: int = 2) -> None:
    """Aplica biseles duros y Weighted Normals para eliminar aspecto blando o primitivo."""
    if bpy is None or obj is None or obj.type != "MESH":
        return
    try:
        # Modificador Bevel
        bev = obj.modifiers.new("Eng_Bevel", "BEVEL")
        bev.width = bevel_width
        bev.segments = segments
        bev.limit_method = "ANGLE"
        bev.angle_limit = math.radians(35.0)
        bev.harden_normals = True

        # Modificador Weighted Normal
        wn = obj.modifiers.new("Eng_WeightedNormal", "WEIGHTED_NORMAL")
        wn.keep_sharp = True

        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(45.0)
    except Exception:
        pass


def create_clean_cutaway_casing_mesh(
    name: str,
    r_inner: float,
    r_outer_start: float,
    r_outer_end: float,
    x_back: float,
    x_front: float,
    center: Tuple[float, float, float],
    theta_start_deg: float = 220.0,
    theta_end_deg: float = 480.0,
    mat: Any = None,
    steps: int = 36,
) -> Any:
    """Genera una carcasa seccionada profesional CAD sin superposiciones ni tubos abiertos."""
    cx, cy, cz = center
    verts = []
    faces = []

    theta_start = math.radians(theta_start_deg)
    theta_end = math.radians(theta_end_deg)

    slices = []
    for s in range(steps + 1):
        t = s / steps
        theta = theta_start + t * (theta_end - theta_start)
        r_out = r_outer_start + t * (r_outer_end - r_outer_start)
        r_in = r_inner

        c_th = math.cos(theta)
        s_th = math.sin(theta)

        y_in = cy + r_in * c_th
        z_in = cz + r_in * s_th
        y_out = cy + r_out * c_th
        z_out = cz + r_out * s_th

        idx = len(verts)
        verts.append((x_back, y_in, z_in))     # 0: inner back
        verts.append((x_front, y_in, z_in))    # 1: inner front
        verts.append((x_front, y_out, z_out))  # 2: outer front
        verts.append((x_back, y_out, z_out))   # 3: outer back
        slices.append((idx, idx + 1, idx + 2, idx + 3))

    for s in range(steps):
        s0 = slices[s]
        s1 = slices[s + 1]
        faces.append((s0[0], s0[1], s1[1], s1[0]))
        faces.append((s0[1], s0[2], s1[2], s1[1]))
        faces.append((s0[2], s0[3], s1[3], s1[2]))
        faces.append((s0[3], s0[0], s1[0], s1[3]))

    # Tapas planas estancas en cortes de sección
    first_s = slices[0]
    last_s = slices[-1]
    faces.append((first_s[0], first_s[3], first_s[2], first_s[1]))
    faces.append((last_s[0], last_s[1], last_s[2], last_s[3]))

    obj = C.mesh_object(name, verts, faces, mat=mat, flat=False)
    apply_engineering_finish(obj, bevel_width=0.012, segments=2)
    return obj


def create_curved_blade_mesh(
    name: str,
    r_inner: float,
    r_outer: float,
    length: float,
    angle: float,
    twist_deg: float,
    mat: Any,
    is_splitter: bool = False,
) -> Any:
    """Genera una pala/álabe aerodinámico con curvatura 3D."""
    verts = []
    faces = []
    slices = 8
    rad_steps = 4
    x_offset = 0.04 if is_splitter else -length * 0.38

    for s in range(slices):
        t_x = s / (slices - 1)
        px = x_offset + t_x * length
        theta = angle + math.radians(twist_deg) * (t_x ** 1.3)

        for r_step in range(rad_steps):
            t_r = r_step / (rad_steps - 1)
            r_curr = r_inner + (r_outer - r_inner) * (0.35 + 0.65 * (t_x ** 0.8)) * (0.2 + 0.8 * t_r)
            py = r_curr * math.cos(theta)
            pz = r_curr * math.sin(theta)
            verts.append((px, py, pz))

    for s in range(slices - 1):
        for r_step in range(rad_steps - 1):
            i0 = s * rad_steps + r_step
            i1 = i0 + 1
            i2 = (s + 1) * rad_steps + r_step + 1
            i3 = i2 - 1
            faces.append((i0, i1, i2, i3))

    obj = C.mesh_object(name, verts, faces, mat=mat, flat=False)
    apply_engineering_finish(obj, bevel_width=0.005, segments=1)
    return obj


def create_flow_curve_spline(
    name: str,
    path_points: List[Tuple[float, float, float]],
    bevel_radius: float,
    mat: Any,
) -> Any:
    """Crea una spline 3D curva Bézier suave para la visualización de flujos continuos."""
    curve = bpy.data.curves.new(f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel_radius
    curve.bevel_resolution = 4
    curve.use_fill_caps = True

    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(path_points) - 1)

    for i, pt in enumerate(path_points):
        bp = spline.bezier_points[i]
        bp.co = pt
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    obj = bpy.data.objects.new(name, curve)
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ==============================================================================
# 3. CONSTRUCTOR DEL MODELO COMPLETO DE ALTA FIDELIDAD
# ==============================================================================

def build_specialized_turbocharger_model(center_z: float = 1.25) -> Dict[str, Any]:
    """Construye un turbocompresor automotriz de fidelidad profesional cinematográfica."""
    if bpy is None:
        return {"status": "mock"}

    data: Dict[str, Any] = {
        "groups": {},
        "anchors_3d": {},
        "moving_parts": {},
    }

    def grp(name: str, *objs):
        data["groups"].setdefault(name, []).extend(objs)

    # 1. Materiales PBR Especializados
    m_turb_iron = get_or_create_material("Mat_TurbIron_Pro", hex_to_rgba("#1C1E22"), roughness=0.55, metallic=0.82)
    m_inconel = get_or_create_material(
        "Mat_Inconel_Pro", hex_to_rgba("#C2410C"), roughness=0.25, metallic=0.90,
        emission_color=hex_to_rgba("#EA580C"), emission_strength=0.45
    )
    m_comp_alum = get_or_create_material("Mat_CompAlum_Pro", hex_to_rgba("#E2E8F0"), roughness=0.18, metallic=0.94)
    m_billet = get_or_create_material("Mat_BilletWheel_Pro", hex_to_rgba("#F8FAFC"), roughness=0.08, metallic=0.98)
    m_chra = get_or_create_material("Mat_CHRA_Pro", hex_to_rgba("#27272A"), roughness=0.35, metallic=0.85)
    m_gold = get_or_create_material("Mat_Brass_Pro", hex_to_rgba("#D97706"), roughness=0.20, metallic=0.92)
    m_steel = get_or_create_material("Mat_Steel_Pro", hex_to_rgba("#CBD5E1"), roughness=0.10, metallic=0.96)
    m_oil_film = get_or_create_material(
        "Mat_Oil_Film_Pro", hex_to_rgba("#F59E0B"), roughness=0.10, metallic=0.20,
        emission_color=hex_to_rgba("#FBBF24"), emission_strength=2.2
    )
    m_floor = get_or_create_material("Mat_StudioPedestal_Dark", hex_to_rgba("#090D16"), roughness=0.30, metallic=0.50)

    # Materiales emisivos de flujo termodinámico
    m_flow_hot = get_or_create_material(
        "Mat_FlowHot_Emissive", hex_to_rgba("#FF3B00"), roughness=0.15,
        emission_color=hex_to_rgba("#FF6A00"), emission_strength=3.8
    )
    m_flow_cold = get_or_create_material(
        "Mat_FlowCold_Emissive", hex_to_rgba("#00E5FF"), roughness=0.15,
        emission_color=hex_to_rgba("#38BDF8"), emission_strength=3.5
    )

    cz = center_z

    # =========================================================================
    # A. ILUMINACIÓN TRI-PUNTO CON CONTRASTE DE TEMPERATURA APUNTADA AL CENTRO
    # =========================================================================
    target_pt = Vector((0.0, 0.0, cz))

    # 1. Key Light Frontal Neutral
    key_l = bpy.data.lights.new("Studio_Key_Light", type="AREA")
    key_l.energy = 320.0
    key_l.size = 2.4
    key_l.color = (1.0, 0.98, 0.94)
    key_obj = bpy.data.objects.new("Studio_Key_Light", key_l)
    key_obj.location = (2.2, -3.5, cz + 2.4)
    key_obj.rotation_euler = (target_pt - Vector(key_obj.location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(key_obj)

    # 2. Rim Light Cálida (Lado Turbina X > 0)
    rim_l = bpy.data.lights.new("Studio_Rim_Turbine", type="AREA")
    rim_l.energy = 380.0
    rim_l.size = 1.8
    rim_l.color = (1.0, 0.42, 0.12)  # Ámbar cálido 950°C
    rim_obj = bpy.data.objects.new("Studio_Rim_Turbine", rim_l)
    rim_obj.location = (2.8, 2.4, cz + 1.8)
    rim_obj.rotation_euler = (target_pt - Vector(rim_obj.location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(rim_obj)

    # 3. Rim Light Fría (Lado Compresor X < 0)
    fill_l = bpy.data.lights.new("Studio_Fill_Compressor", type="AREA")
    fill_l.energy = 340.0
    fill_l.size = 2.0
    fill_l.color = (0.20, 0.70, 1.0)  # Cian frío 40°C
    fill_obj = bpy.data.objects.new("Studio_Fill_Compressor", fill_l)
    fill_obj.location = (-2.8, -2.5, cz + 1.5)
    fill_obj.rotation_euler = (target_pt - Vector(fill_obj.location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(fill_obj)

    # =========================================================================
    # B. CUERPO CENTRAL CHRA Y LUBRICACIÓN (VENTANA DE CORTE SECCIONAL REAL)
    # =========================================================================
    # Carcasa central CHRA con corte frontal (125° a 235° abierto) para revelar interior
    chra_body = create_clean_cutaway_casing_mesh(
        "CHRA_Waist",
        r_inner=0.13,
        r_outer_start=0.26,
        r_outer_end=0.26,
        x_back=-0.17,
        x_front=0.17,
        center=(0, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_chra,
    )

    chra_flange_comp = create_clean_cutaway_casing_mesh(
        "CHRA_Flange_Comp",
        r_inner=0.18,
        r_outer_start=0.36,
        r_outer_end=0.36,
        x_back=-0.20,
        x_front=-0.17,
        center=(0, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_chra,
    )
    chra_flange_turb = create_clean_cutaway_casing_mesh(
        "CHRA_Flange_Turb",
        r_inner=0.18,
        r_outer_start=0.35,
        r_outer_end=0.35,
        x_back=0.17,
        x_front=0.20,
        center=(0, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_chra,
    )

    oil_feed_fitting = C.cylinder("Oil_Feed_AN_Fitting", 0.042, 0.15, (0, 0, cz + 0.32), axis="Z", mat=m_gold, verts=6)
    oil_drain_pipe = C.cylinder("Oil_Drain_Pipe", 0.045, 0.14, (0, 0, cz - 0.30), axis="Z", mat=m_chra, verts=18)

    # Cojinetes de bronce y película de lubricación interna plenamente visibles en corte
    bearing_l = C.cylinder("CHRA_Bearing_Comp", 0.075, 0.08, (-0.08, 0, cz), axis="X", mat=m_gold, verts=20)
    bearing_r = C.cylinder("CHRA_Bearing_Turb", 0.075, 0.08, (0.08, 0, cz), axis="X", mat=m_gold, verts=20)
    oil_film = C.cylinder("CHRA_Oil_Film", 0.065, 0.32, (0, 0, cz), axis="X", mat=m_oil_film, verts=20)

    # Pernos de fijación perimetrales en CHRA (solo en sector existente de la brida)
    chra_bolts = []
    for b_idx in range(6):
        b_ang = b_idx * (2.0 * math.pi / 6)
        b_deg = math.degrees(b_ang)
        if 115.0 <= b_deg <= 245.0:
            continue  # No colocar pernos flotantes en el área de corte abierta
        bx = -0.19
        by = 0.33 * math.cos(b_ang)
        bz = cz + 0.33 * math.sin(b_ang)
        bolt = C.cylinder(f"CHRA_Bolt_{b_idx}", 0.014, 0.035, (bx, by, bz), axis="X", mat=m_steel, verts=6)
        chra_bolts.append(bolt)

    grp("chra", chra_body, chra_flange_comp, chra_flange_turb, oil_feed_fitting, oil_drain_pipe, bearing_l, bearing_r, oil_film, *chra_bolts)
    data["anchors_3d"]["chra"] = Vector((0.0, -0.13, cz))

    # =========================================================================
    # C. EJE ROTOR COAXIAL Y ÁLABES AERODINÁMICOS GIRATORIOS
    # =========================================================================
    rotor_master = C.empty("Rotor_Master_Shaft", (0.0, 0.0, cz))

    shaft = C.cylinder("Rotor_Shaft", 0.045, 1.10, (0, 0, 0), axis="X", mat=m_steel, verts=20)
    shaft.parent = rotor_master
    shaft.matrix_parent_inverse = Matrix.Identity(4)
    shaft.location = (0, 0, 0)
    apply_engineering_finish(shaft, bevel_width=0.005, segments=1)

    # 1. Rueda de Turbina Inconel (Lado Caliente: X > 0)
    turb_hub = C.cylinder("Turbine_Hub", 0.28, 0.26, (0, 0, 0), axis="X", mat=m_inconel, verts=28, r2=0.13)
    turb_hub.parent = rotor_master
    turb_hub.matrix_parent_inverse = Matrix.Identity(4)
    turb_hub.location = (0.32, 0, 0)
    apply_engineering_finish(turb_hub, bevel_width=0.008, segments=2)

    turb_blades = []
    num_turb = 11
    for i in range(num_turb):
        ang = 2.0 * math.pi * i / num_turb
        b = create_curved_blade_mesh(
            f"Turb_Blade_{i}", r_inner=0.18, r_outer=0.27, length=0.18,
            angle=ang, twist_deg=-30.0, mat=m_inconel, is_splitter=False
        )
        b.parent = rotor_master
        b.matrix_parent_inverse = Matrix.Identity(4)
        b.location = (0.32, 0, 0)
        turb_blades.append(b)

    # 2. Rueda del Compresor Billet (Lado Frío: X < 0)
    comp_hub = C.cylinder("Compressor_Hub", 0.30, 0.28, (0, 0, 0), axis="X", mat=m_billet, verts=28, r2=0.11)
    comp_hub.parent = rotor_master
    comp_hub.matrix_parent_inverse = Matrix.Identity(4)
    comp_hub.location = (-0.32, 0, 0)
    apply_engineering_finish(comp_hub, bevel_width=0.008, segments=2)

    comp_nut = C.cylinder("Compressor_NoseNut", 0.08, 0.06, (0, 0, 0), axis="X", mat=m_steel, verts=6)
    comp_nut.parent = rotor_master
    comp_nut.matrix_parent_inverse = Matrix.Identity(4)
    comp_nut.location = (-0.46, 0, 0)

    comp_blades = []
    num_comp = 6
    for i in range(num_comp):
        ang_m = 2.0 * math.pi * i / num_comp
        bm = create_curved_blade_mesh(
            f"Comp_MainBlade_{i}", r_inner=0.20, r_outer=0.33, length=0.25,
            angle=ang_m, twist_deg=28.0, mat=m_billet, is_splitter=False
        )
        bm.parent = rotor_master
        bm.matrix_parent_inverse = Matrix.Identity(4)
        bm.location = (-0.32, 0, 0)
        comp_blades.append(bm)

        ang_s = ang_m + math.pi / num_comp
        bs = create_curved_blade_mesh(
            f"Comp_SplitBlade_{i}", r_inner=0.18, r_outer=0.30, length=0.17,
            angle=ang_s, twist_deg=22.0, mat=m_billet, is_splitter=True
        )
        bs.parent = rotor_master
        bs.matrix_parent_inverse = Matrix.Identity(4)
        bs.location = (-0.32, 0, 0)
        comp_blades.append(bs)

    grp("rotor", shaft, turb_hub, *turb_blades, comp_hub, comp_nut, *comp_blades)
    data["moving_parts"]["rotor"] = rotor_master

    # =========================================================================
    # D. CARCASAS EN ESPIRAL AUTÉNTICAS (VOLUTAS CON DETALLES MECÁNICOS)
    # =========================================================================
    # Caracol de turbina (Hierro fundido con corte seccional limpio)
    turb_volute = create_clean_cutaway_casing_mesh(
        "Turbine_Volute",
        r_inner=0.31,
        r_outer_start=0.39,
        r_outer_end=0.56,
        x_back=0.19,
        x_front=0.46,
        center=(0.35, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_turb_iron,
    )
    turb_inlet = C.box("Turbine_Inlet_Flange", (0.18, 0.26, 0.32), (0.35, 0.52, cz - 0.10), mat=m_turb_iron, bev=0.015)
    apply_engineering_finish(turb_inlet, bevel_width=0.014, segments=2)

    # 4 Pernos mecanizados en la brida de escape T3/T4
    flange_bolts = []
    f_corners = [
        (0.35 - 0.06, 0.52 - 0.10, cz - 0.10),
        (0.35 + 0.06, 0.52 - 0.10, cz - 0.10),
        (0.35 - 0.06, 0.52 + 0.10, cz - 0.10),
        (0.35 + 0.06, 0.52 + 0.10, cz - 0.10),
    ]
    for fb_i, (fx, fy, fz) in enumerate(f_corners):
        fb = C.cylinder(f"Turbine_Flange_Bolt_{fb_i}", 0.016, 0.04, (fx, fy, fz), axis="Z", mat=m_steel, verts=6)
        flange_bolts.append(fb)

    # Salida de escape con corte seccional que no bloquea la rueda de Inconel
    turb_outlet = create_clean_cutaway_casing_mesh(
        "Turbine_Exhaust_Outlet",
        r_inner=0.20,
        r_outer_start=0.28,
        r_outer_end=0.28,
        x_back=0.46,
        x_front=0.58,
        center=(0.35, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_turb_iron,
    )

    grp("turbine_housing", turb_volute, turb_inlet, turb_outlet, *flange_bolts)
    data["anchors_3d"]["turbine"] = Vector((0.45, -0.10, cz + 0.05))

    # Caracol de compresor (Aluminio maquinado CNC con corte seccional)
    comp_volute = create_clean_cutaway_casing_mesh(
        "Compressor_Volute",
        r_inner=0.35,
        r_outer_start=0.41,
        r_outer_end=0.60,
        x_back=-0.19,
        x_front=-0.46,
        center=(-0.35, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_comp_alum,
    )
    comp_intake = create_clean_cutaway_casing_mesh(
        "Compressor_Intake_Bell",
        r_inner=0.21,
        r_outer_start=0.30,
        r_outer_end=0.30,
        x_back=-0.46,
        x_front=-0.58,
        center=(-0.35, 0, cz),
        theta_start_deg=235.0,
        theta_end_deg=485.0,
        mat=m_comp_alum,
    )

    comp_boost_pipe = C.cylinder("Compressor_Discharge_Pipe", 0.15, 0.30, (-0.35, 0.55, cz + 0.25), axis="Y", mat=m_comp_alum, verts=24)
    apply_engineering_finish(comp_boost_pipe, bevel_width=0.012, segments=2)

    grp("compressor_housing", comp_volute, comp_intake, comp_boost_pipe)
    data["anchors_3d"]["compressor"] = Vector((-0.45, -0.10, cz + 0.05))
    data["anchors_3d"]["intake"] = Vector((-0.68, 0.0, cz - 0.05))

    # =========================================================================
    # E. VÁLVULA WASTEGATE Y COMPUERTA ARTICULADA
    # =========================================================================
    wg_canister = C.cylinder("WG_Canister", 0.13, 0.22, (0.24, 0.34, cz + 0.40), axis="Z", mat=m_gold, verts=24)
    apply_engineering_finish(wg_canister, bevel_width=0.012, segments=2)

    wg_rod = C.cylinder("WG_Rod", 0.015, 0.38, (0.32, 0.28, cz + 0.20), axis="Z", mat=m_steel, verts=14)
    wg_bracket = C.box("WG_Mount_Bracket", (0.03, 0.15, 0.12), (0.20, 0.28, cz + 0.40), mat=m_turb_iron)

    # Brazo articulado y disco de compuerta flapper de alivio
    wg_hinge_arm = C.cylinder("WG_Hinge_Arm", 0.016, 0.14, (0.32, 0.28, cz + 0.02), axis="Y", mat=m_steel, verts=12)
    wg_flapper_disc = C.cylinder("WG_Flapper_Disc", 0.09, 0.025, (0.32, 0.34, cz + 0.02), axis="X", mat=m_steel, verts=24)
    apply_engineering_finish(wg_flapper_disc, bevel_width=0.005, segments=1)

    grp("wastegate", wg_canister, wg_rod, wg_bracket, wg_hinge_arm, wg_flapper_disc)
    data["anchors_3d"]["wastegate"] = Vector((0.24, 0.34, cz + 0.44))

    # =========================================================================
    # F. FLUJOS PROCEDURALES EN CURVAS 3D BÉZIER (SPLINES EMISIVAS)
    # =========================================================================
    # 1. Flujo de escape caliente (950°C, espiral y salida axial)
    exhaust_path_pts = [
        (0.35, 0.75, cz - 0.10),
        (0.35, 0.50, cz - 0.10),
        (0.40, 0.25, cz + 0.20),
        (0.45, -0.10, cz + 0.15),
        (0.50, 0.0, cz),
        (0.85, 0.0, cz),
    ]
    flow_exhaust = create_flow_curve_spline("Flow_Exhaust_Path", exhaust_path_pts, bevel_radius=0.038, mat=m_flow_hot)

    # 2. Flujo de admisión fresco (40°C, entrada axial y salida boost)
    intake_path_pts = [
        (-0.95, 0.0, cz),
        (-0.65, 0.0, cz),
        (-0.45, 0.0, cz),
        (-0.35, 0.20, cz + 0.10),
        (-0.35, 0.50, cz + 0.25),
        (-0.35, 0.85, cz + 0.25),
    ]
    flow_intake = create_flow_curve_spline("Flow_Intake_Path", intake_path_pts, bevel_radius=0.038, mat=m_flow_cold)

    grp("flows", flow_exhaust, flow_intake)

    # Compatibilidad bidireccional
    data["subsystems"] = data["groups"]
    return data


# ==============================================================================
# 4. GENERADOR DE ETIQUETAS ADAPTATIVAS 3D (HUD ZONAS SEGURAS 9:16)
# ==============================================================================

def generate_turbo_adaptive_labels(
    turbo_data: Dict[str, Any],
    cam_pos: Vector,
    cam_target: Vector,
    config: Educational916FrameworkConfig,
) -> Dict[str, Tuple[Any, Any]]:
    """Crea el conjunto de etiquetas HUD dinámicas en zonas seguras estrictas."""
    if bpy is None:
        return {}

    anchors_3d = turbo_data.get("anchors_3d", {})
    lbl_collection = bpy.data.collections.get("Turbo_Adaptive_Labels_9_16")
    if not lbl_collection:
        lbl_collection = bpy.data.collections.new("Turbo_Adaptive_Labels_9_16")
        bpy.context.scene.collection.children.link(lbl_collection)

    created_labels: Dict[str, Tuple[Any, Any]] = {}
    cam_o = bpy.context.scene.camera or bpy.data.objects.get("Director_Camera_Obj")

    # 1. Overview Cues (Presentación de componentes en Stage 2)
    cue_st2 = next((c for c in TURBO_TIMELINE_CUES if c["id"] == "st02_exploded_view"), TURBO_TIMELINE_CUES[0])
    c_cfg2 = cue_st2.get("camera_start") or cue_st2.get("camera")
    az_st2 = math.radians(c_cfg2["az"])
    el_st2 = math.radians(c_cfg2["el"])
    c_tgt_st2 = Vector((c_cfg2["tx"], c_cfg2["ty"], c_cfg2["tz"]))
    d_st2 = Vector((math.sin(az_st2) * math.cos(el_st2), -math.cos(az_st2) * math.cos(el_st2), math.sin(el_st2)))
    c_pos_st2 = c_tgt_st2 + d_st2 * c_cfg2["dist"]

    if cam_o:
        cam_o.location = c_pos_st2
        cam_o.rotation_euler = (c_tgt_st2 - c_pos_st2).to_track_quat("-Z", "Y").to_euler()
        cam_o.data.lens = c_cfg2["lens"]
        bpy.context.view_layer.update()

    # Coordenadas calibradas estrictamente en zona segura (u in [0.15, 0.85], v in [0.32, 0.84])
    overview_specs = {
        "wastegate":  ("VÁLVULA WASTEGATE", 0.78, 0.82),
        "turbine":    ("TURBINA INCONEL",   0.78, 0.52),
        "chra":       ("CARTUCHO CHRA",     0.18, 0.82),
        "compressor": ("COMPRESOR BILLET",  0.18, 0.52),
        "intake":     ("ENTRADA DE AIRE",   0.18, 0.32),
    }

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

    # 2. Close-up Specs por Etapa Individual (Calibrados con distancias holgadas y encuadres limpios)
    close_specs = [
        ("close_turbine",    "turbine",    "TURBINA INCONEL (950°C)", 0.74, 0.76, 40.0, 18.0, 3.7, 0.32, -0.05, 1.25, 42.0),
        ("close_chra",       "chra",       "EJE Y LUBRICACIÓN CHRA",  0.22, 0.78, 18.0, 20.0, 3.6, 0.0,  -0.08, 1.25, 42.0),
        ("close_compressor", "compressor", "COMPRESOR DE BILLET",    0.22, 0.76, -36.0, 18.0, 3.7, -0.32, -0.05, 1.25, 42.0),
        ("close_wastegate",  "wastegate",  "COMPUERTA WASTEGATE",     0.74, 0.80, 32.0, 20.0, 3.6, 0.22, 0.22, 1.38, 42.0),
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
# 5. COREOGRAFÍA CINEMÁTICA, TRACK TO Y ANIMACIÓN CONTINUA
# ==============================================================================

def animate_turbo_vertical_showcase(
    turbo_data: Dict[str, Any],
    camera_obj: Any,
    config: Educational916FrameworkConfig,
    labels_dict: Optional[Dict[str, Tuple[Any, Any]]] = None,
) -> Dict[str, Any]:
    """Aplica la coreografía cinemática con apuntado dinámico TRACK_TO y fluidez 100%."""
    if bpy is None or not camera_obj:
        return {"status": "mock"}

    fps = config.timeline.fps
    total_frames = config.timeline.total_frames
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames

    # Configuración técnica de Render EEVEE Next con Motion Blur
    scene.render.fps = fps
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.5
    scene.render.motion_blur_position = 'CENTER'

    cam_data = camera_obj.data
    cam_data.sensor_fit = config.camera.sensor_fit
    cam_data.sensor_width = config.camera.sensor_width_mm

    # 1. Target Dinámico con constraint TRACK_TO (Encuadre perfecto)
    track_target = bpy.data.objects.get("Director_Track_Target")
    if not track_target:
        track_target = bpy.data.objects.new("Director_Track_Target", None)
        track_target.empty_display_size = 0.1
        track_target.empty_display_type = "PLAIN_AXES"
        scene.collection.objects.link(track_target)

    # Asignar o reutilizar constraint TRACK_TO en la cámara
    tt_constraint = next((c for c in camera_obj.constraints if c.type == "TRACK_TO"), None)
    if not tt_constraint:
        tt_constraint = camera_obj.constraints.new(type="TRACK_TO")
        tt_constraint.name = "Dynamic_Piece_Tracker"
        tt_constraint.target = track_target
        tt_constraint.track_axis = "TRACK_NEGATIVE_Z"
        tt_constraint.up_axis = "UP_Y"

    track_target.animation_data_create()
    camera_obj.animation_data_create()
    cam_data.animation_data_create()

    # 2. Keyframes de cámara y target por etapa (Multi-Toma Dinámica sin pausas muertas)
    for cue in TURBO_TIMELINE_CUES:
        f_start, f_end = cue["frame_range"]
        cam_start = cue.get("camera_start") or cue.get("camera")
        cam_end = cue.get("camera_end") or cam_start
        tgt_coord = cue.get("target", (0.0, 0.0, 1.25))

        # Target de apuntado dinámico en f_start y f_end
        track_target.location = Vector(tgt_coord)
        track_target.keyframe_insert(data_path="location", frame=f_start)
        track_target.keyframe_insert(data_path="location", frame=f_end)

        # Posición de inicio en f_start
        az_s = math.radians(cam_start["az"])
        el_s = math.radians(cam_start["el"])
        dist_s = cam_start["dist"]
        tgt_s = Vector((cam_start["tx"], cam_start["ty"], cam_start["tz"]))
        d_vec_s = Vector((math.sin(az_s) * math.cos(el_s), -math.cos(az_s) * math.cos(el_s), math.sin(el_s)))
        pos_s = tgt_s + d_vec_s * dist_s

        camera_obj.location = pos_s
        cam_data.lens = cam_start["lens"]
        camera_obj.keyframe_insert(data_path="location", frame=f_start)
        cam_data.keyframe_insert(data_path="lens", frame=f_start)

        # Paneo continuo en f_end (garantiza movimiento continuo sin pausas > 2s)
        az_e = math.radians(cam_end["az"])
        el_e = math.radians(cam_end["el"])
        dist_e = cam_end["dist"]
        tgt_e = Vector((cam_end["tx"], cam_end["ty"], cam_end["tz"]))
        d_vec_e = Vector((math.sin(az_e) * math.cos(el_e), -math.cos(az_e) * math.cos(el_e), math.sin(el_e)))
        pos_e = tgt_e + d_vec_e * dist_e

        camera_obj.location = pos_e
        cam_data.lens = cam_end["lens"]
        camera_obj.keyframe_insert(data_path="location", frame=f_end)
        cam_data.keyframe_insert(data_path="lens", frame=f_end)

    # 3. Vista Explosiva Real (Exploded View) en Stage 2
    cue_exp = next((c for c in TURBO_TIMELINE_CUES if c["id"] == "st02_exploded_view"), None)
    if cue_exp:
        f_s, f_e = cue_exp["frame_range"]
        f_open = f_s + 35
        f_close = max(f_open + 1, f_e - 35)

        subsystems = turbo_data.get("subsystems", {}) or turbo_data.get("groups", {})
        turb_objs = subsystems.get("turbine_housing", [])
        comp_objs = subsystems.get("compressor_housing", [])
        wg_objs = subsystems.get("wastegate", [])

        # Despiece lateral Carcasa de Turbina (+X)
        for o in turb_objs:
            o.animation_data_create()
            ox = o.location.x
            o.keyframe_insert(data_path="location", index=0, frame=1)
            o.keyframe_insert(data_path="location", index=0, frame=f_s)
            o.location.x = ox + 0.42
            o.keyframe_insert(data_path="location", index=0, frame=f_open)
            o.keyframe_insert(data_path="location", index=0, frame=f_close)
            o.location.x = ox
            o.keyframe_insert(data_path="location", index=0, frame=f_e)

        # Despiece lateral Carcasa de Compresor (-X)
        for o in comp_objs:
            o.animation_data_create()
            ox = o.location.x
            o.keyframe_insert(data_path="location", index=0, frame=1)
            o.keyframe_insert(data_path="location", index=0, frame=f_s)
            o.location.x = ox - 0.42
            o.keyframe_insert(data_path="location", index=0, frame=f_open)
            o.keyframe_insert(data_path="location", index=0, frame=f_close)
            o.location.x = ox
            o.keyframe_insert(data_path="location", index=0, frame=f_e)

        # Despiece radial Wastegate (+Y, +Z)
        for o in wg_objs:
            o.animation_data_create()
            oy = o.location.y
            oz = o.location.z
            o.keyframe_insert(data_path="location", index=1, frame=1)
            o.keyframe_insert(data_path="location", index=2, frame=1)
            o.keyframe_insert(data_path="location", index=1, frame=f_s)
            o.keyframe_insert(data_path="location", index=2, frame=f_s)
            o.location.y = oy + 0.18
            o.location.z = oz + 0.15
            o.keyframe_insert(data_path="location", index=1, frame=f_open)
            o.keyframe_insert(data_path="location", index=2, frame=f_open)
            o.keyframe_insert(data_path="location", index=1, frame=f_close)
            o.keyframe_insert(data_path="location", index=2, frame=f_close)
            o.location.y = oy
            o.location.z = oz
            o.keyframe_insert(data_path="location", index=1, frame=f_e)
            o.keyframe_insert(data_path="location", index=2, frame=f_e)

    # 4. Actuación Real de la Válvula Wastegate (Vástago y Compuerta Flapper en Stage 10-11)
    cue_wg = next((c for c in TURBO_TIMELINE_CUES if c["id"] == "st11_wastegate_bypass"), None)
    if cue_wg:
        f_s, f_e = cue_wg["frame_range"]
        subsystems = turbo_data.get("subsystems", {}) or turbo_data.get("groups", {})
        wg_objs = subsystems.get("wastegate", [])
        for o in wg_objs:
            if "Rod" in o.name:
                o.animation_data_create()
                orig_z = o.location.z
                o.keyframe_insert(data_path="location", index=2, frame=1)
                o.keyframe_insert(data_path="location", index=2, frame=f_s)
                o.location.z = orig_z + 0.05
                o.keyframe_insert(data_path="location", index=2, frame=f_s + 20)
                o.keyframe_insert(data_path="location", index=2, frame=f_e - 20)
                o.location.z = orig_z
                o.keyframe_insert(data_path="location", index=2, frame=f_e)
            elif "Flapper" in o.name or "Hinge" in o.name:
                o.animation_data_create()
                o.rotation_euler = (0, 0, 0)
                o.keyframe_insert(data_path="rotation_euler", index=1, frame=1)
                o.keyframe_insert(data_path="rotation_euler", index=1, frame=f_s)
                o.rotation_euler = (0, math.radians(35.0), 0)
                o.keyframe_insert(data_path="rotation_euler", index=1, frame=f_s + 20)
                o.keyframe_insert(data_path="rotation_euler", index=1, frame=f_e - 20)
                o.rotation_euler = (0, 0, 0)
                o.keyframe_insert(data_path="rotation_euler", index=1, frame=f_e)

    # 5. Giro Ultrarrápido Continuo del Rotor Coaxial (150,000 RPM simuladas con Motion Blur)
    rotor = turbo_data.get("moving_parts", {}).get("rotor")
    if rotor:
        rotor.animation_data_create()
        rotor.rotation_euler = (0, 0, 0)
        rotor.keyframe_insert(data_path="rotation_euler", index=0, frame=1)
        # 300 vueltas completas sobre la línea de tiempo
        rotor.rotation_euler = (math.radians(360.0 * 300.0), 0, 0)
        rotor.keyframe_insert(data_path="rotation_euler", index=0, frame=total_frames)

        # Forzar interpolación lineal para giro continuo uniforme
        act = rotor.animation_data.action if rotor.animation_data else None
        if act:
            fcs = getattr(act, "fcurves", None)
            if not fcs and hasattr(act, "layers"):
                fcs = []
                for layer in act.layers:
                    for strip in layer.strips:
                        for cb in getattr(strip, "channel_bags", []):
                            fcs.extend(getattr(cb, "fcurves", []))
            if fcs:
                for fc in fcs:
                    if getattr(fc, "data_path", "") == "rotation_euler":
                        for kp in getattr(fc, "keyframe_points", []):
                            kp.interpolation = "LINEAR"

    # 6. Sincronización Estricta de Visibilidad de Etiquetas HUD
    if labels_dict:
        for lbl_name, (txt_o, line_o) in labels_dict.items():
            dot_o = txt_o.get("dot_obj") if txt_o else None
            badge_o = txt_o.get("badge_obj") if txt_o else None
            objs_to_anim = [o for o in (txt_o, line_o, dot_o, badge_o) if o is not None]

            for o in objs_to_anim:
                o.animation_data_create()
                for cue in TURBO_TIMELINE_CUES:
                    f_start, f_end = cue["frame_range"]
                    is_active = lbl_name in cue["active_labels"]
                    val = not is_active

                    o.hide_viewport = val
                    o.hide_render = val
                    o.keyframe_insert(data_path="hide_viewport", frame=f_start)
                    o.keyframe_insert(data_path="hide_render", frame=f_start)
                    o.keyframe_insert(data_path="hide_viewport", frame=f_end)
                    o.keyframe_insert(data_path="hide_render", frame=f_end)

    return {
        "status": "animated",
        "total_frames": total_frames,
        "duration_sec": config.timeline.target_duration_sec,
        "stages_count": len(TURBO_TIMELINE_CUES),
    }
