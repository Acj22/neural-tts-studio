"""Controlador cinemático y de animación para Blender 5.3 (Fase 2.1 - Corrección y Perfeccionamiento).

Cinemática del mecanismo biela-manivela (Z es el eje vertical del cilindro):
  - crank_center_z = 0.0  → cigüeñal en el origen del cárter.
  - theta = 0° → muñequilla en PMS (Z máximo). Pistón en punto muerto superior.
  - theta = 180° → pistón en PMI (punto muerto inferior).
  - Eje de rotación del cigüeñal: Y (profundidad).
  - x_pin = r·sin(θ)  (desplazamiento lateral de la muñequilla)
  - z_pin = crank_center_z + r·cos(θ)  (altura de la muñequilla)
  - z_piston = z_pin + √(l² − r²·sin²(θ))  (altura del bulón / pistón)
  - phi_rod = arcsin((r/l)·sin(θ))  (inclinación de la biela)

Válvulas:
  - Admisión abierta: 10° → 170° (tiempo 1)
  - Escape abierto: 540° → 700° (tiempo 4)
  - Superposición: 700° → 720° / 0° → 10° (breve)
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


def calculate_piston_kinematics(
    theta_rad: float,
    r: float = 1.0,
    l: float = 3.6,
    crank_center_z: float = 0.0,
) -> tuple[float, float, float, float]:
    """Calcula la cinemática exacta del mecanismo biela-manivela en Blender.

    Coordenadas en Blender (rotación del cigüeñal alrededor de Y con Euler (0, -theta, 0)):
      - La muñequilla parte en (0, 0, r) relativo al centro del cigüeñal.
      - Al rotar (0, -theta, 0):
          pin_x = -r * sin(theta)
          pin_z = crank_center_z + r * cos(theta)
      - El bulón del pistón desliza estrictamente en la vertical X = 0:
          z_piston = pin_z + sqrt(l^2 - pin_x^2)
      - La biela nace con su cabeza en (pin_x, 0, pin_z) y crece en +Z local hacia el bulón.
      - El ángulo de rotación de la biela alrededor de Y para coincidir exactamente con el bulón es:
          phi_rod = asin(-pin_x / l)

    Returns:
        z_piston: Altura vertical del centro del bulón del pistón.
        phi_rod:  Ángulo de inclinación de la biela (rad, alrededor del eje Y).
        x_pin:    Posición X de la muñequilla.
        z_pin:    Posición Z de la muñequilla.
    """
    sin_t = math.sin(theta_rad)
    cos_t = math.cos(theta_rad)

    # Posición exacta de la muñequilla en el espacio 3D de Blender
    x_pin = -r * sin_t
    z_pin = crank_center_z + (r * cos_t)

    # Inclinación exacta de la biela: el pie (0, z_piston) coincide con el bulón con DIFF=0
    sin_phi = -x_pin / l
    sin_phi = max(-1.0, min(1.0, sin_phi))
    phi_rod = math.asin(sin_phi)

    # Altura del centro del bulón del pistón
    z_piston = z_pin + math.sqrt(max(1e-6, l * l - x_pin * x_pin))

    return z_piston, phi_rod, x_pin, z_pin


def _valve_lift_profile(deg: float, open_deg: float, close_deg: float, max_lift: float = 0.46) -> float:
    """Perfil de alzada de válvula suavizado con seno (rampa de apertura y cierre).

    Args:
        deg:       Ángulo actual del cigüeñal en grados (0–720).
        open_deg:  Ángulo de inicio de apertura.
        close_deg: Ángulo de cierre (open_deg < close_deg).
        max_lift:  Desplazamiento máximo en unidades Blender.
    Returns:
        Alzada en unidades Blender (0.0 = cerrada, max_lift = máxima apertura).
    """
    if open_deg <= deg <= close_deg:
        span = close_deg - open_deg
        norm = (deg - open_deg) / span  # 0→1
        return max_lift * math.sin(math.pi * norm)
    return 0.0


def apply_engine_pose_at_frame(
    engine_data: dict[str, Any],
    frame: int,
    theta_rad: float,
    intake_lift: float = 0.0,
    exhaust_lift: float = 0.0,
    spark_on: bool = False,
    flame_scale: float = 0.0,
    intake_flow: float = 0.0,
    exhaust_flow: float = 0.0,
    compression_gas: float = 0.0,
    exploded_factor: float = 0.0,
) -> None:
    """Inserta keyframes cinemáticos exactos en el fotograma indicado."""
    if bpy is None:
        return

    r = float(engine_data["crank_radius"])
    l = float(engine_data["rod_length"])
    crank_center_z = float(engine_data.get("crank_center_z", 0.0))
    head_z = float(engine_data.get("head_z", crank_center_z + r + l + 2.0))

    z_piston, phi_rod, x_pin, z_pin = calculate_piston_kinematics(
        theta_rad=theta_rad,
        r=r,
        l=l,
        crank_center_z=crank_center_z,
    )

    # -------------------------------------------------------------------
    # 1. CIGÜEÑAL — Rotación continua alrededor del eje Y
    # -------------------------------------------------------------------
    crank = engine_data["crank_root"]
    crank.rotation_euler = (0.0, -theta_rad, 0.0)
    crank.location = (0.0, 0.0, crank_center_z - 2.6 * exploded_factor)
    crank.keyframe_insert(data_path="rotation_euler", frame=frame)
    crank.keyframe_insert(data_path="location", frame=frame)

    # -------------------------------------------------------------------
    # 2. BIELA — Cabeza en la muñequilla, pie en el bulón
    # La biela nace con su origen en la muñequilla (x_pin, 0, z_pin).
    # El cuerpo crece en +Z local hacia el pistón con ángulo phi_rod.
    # -------------------------------------------------------------------
    rod = engine_data["rod_root"]
    rod.location = (x_pin, 0.0, z_pin - 1.4 * exploded_factor)
    rod.rotation_euler = (0.0, phi_rod, 0.0)
    rod.keyframe_insert(data_path="location", frame=frame)
    rod.keyframe_insert(data_path="rotation_euler", frame=frame)

    # -------------------------------------------------------------------
    # 3. PISTÓN — Desplazamiento vertical puro en Z
    # -------------------------------------------------------------------
    piston = engine_data["piston_root"]
    piston.location = (0.0, 0.0, z_piston + 1.4 * exploded_factor)
    piston.keyframe_insert(data_path="location", frame=frame)

    # -------------------------------------------------------------------
    # 4. VÁLVULA DE ADMISIÓN Y RESORTE — Desplaza a 16° y comprime muelle
    # -------------------------------------------------------------------
    v_in = engine_data["valve_intake"]
    theta_v = math.radians(16.0)
    intake_base_z = head_z + 0.15
    v_in.location = (
        -0.65 + intake_lift * math.sin(theta_v),
        0.0,
        intake_base_z - intake_lift * math.cos(theta_v) + 2.6 * exploded_factor,
    )
    v_in.keyframe_insert(data_path="location", frame=frame)

    if "spring_intake" in engine_data:
        s_in = engine_data["spring_intake"]
        # El resorte se comprime físicamente a lo largo de su eje local Z cuando la válvula abre
        s_in_comp = max(0.40, (0.88 - intake_lift) / 0.88)
        s_in.scale = (1.0, 1.0, s_in_comp)
        s_in.keyframe_insert(data_path="scale", frame=frame)

    # -------------------------------------------------------------------
    # 5. VÁLVULA DE ESCAPE Y RESORTE — Desplaza a 16° y comprime muelle
    # -------------------------------------------------------------------
    v_ex = engine_data["valve_exhaust"]
    v_ex.location = (
        0.65 - exhaust_lift * math.sin(theta_v),
        0.0,
        intake_base_z - exhaust_lift * math.cos(theta_v) + 2.6 * exploded_factor,
    )
    v_ex.keyframe_insert(data_path="location", frame=frame)

    if "spring_exhaust" in engine_data:
        s_ex = engine_data["spring_exhaust"]
        s_ex_comp = max(0.40, (0.88 - exhaust_lift) / 0.88)
        s_ex.scale = (1.0, 1.0, s_ex_comp)
        s_ex.keyframe_insert(data_path="scale", frame=frame)

    # -------------------------------------------------------------------
    # 6. BUJÍA — Sube en despiece axial
    # -------------------------------------------------------------------
    spark = engine_data["spark_root"]
    spark.location = (0.0, 0.0, intake_base_z + 3.6 * exploded_factor)
    spark.keyframe_insert(data_path="location", frame=frame)

    # -------------------------------------------------------------------
    # 7. CULATA — Sube en despiece axial
    # -------------------------------------------------------------------
    if "cylinder_head" in engine_data:
        c_head = engine_data["cylinder_head"]
        c_head.location = (0.0, 0.0, head_z + 2.4 * exploded_factor)
        c_head.keyframe_insert(data_path="location", frame=frame)

    # -------------------------------------------------------------------
    # 8. EFECTOS VISUALES Y LUZ DE COMBUSTIÓN
    # -------------------------------------------------------------------
    # Chispa
    fx_sp = engine_data["fx_spark"]
    sp_sc = 1.0 if spark_on else 0.001
    fx_sp.scale = (sp_sc, sp_sc, sp_sc)
    fx_sp.keyframe_insert(data_path="scale", frame=frame)

    # Llama de combustión
    fx_fl = engine_data["fx_flame"]
    fl_sc = max(0.001, flame_scale)
    fx_fl.scale = (fl_sc, fl_sc, fl_sc)
    fx_fl.keyframe_insert(data_path="scale", frame=frame)

    # Luz puntual dinámica interior de combustión
    if "light_combustion" in engine_data:
        l_comb = engine_data["light_combustion"]
        l_comb.data.energy = 280.0 * flame_scale
        l_comb.data.keyframe_insert(data_path="energy", frame=frame)

    # Flujo de admisión (cian)
    if "fx_intake" in engine_data:
        fx_in = engine_data["fx_intake"]
        in_sc = max(0.001, intake_flow)
        fx_in.scale = (in_sc, in_sc, in_sc)
        fx_in.keyframe_insert(data_path="scale", frame=frame)

    # Flujo de escape (naranja)
    if "fx_exhaust" in engine_data:
        fx_ex = engine_data["fx_exhaust"]
        ex_sc = max(0.001, exhaust_flow)
        fx_ex.scale = (ex_sc, ex_sc, ex_sc)
        fx_ex.keyframe_insert(data_path="scale", frame=frame)

    # Volumen de compresión de la mezcla
    if "fx_compression" in engine_data:
        fx_cmp = engine_data["fx_compression"]
        cmp_sc = max(0.001, compression_gas)
        fx_cmp.scale = (cmp_sc, cmp_sc, cmp_sc)
        fx_cmp.keyframe_insert(data_path="scale", frame=frame)


def build_4_stroke_cycle_keyframes(
    engine_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    cycle_phase: str = "full_cycle",
    highlight_component: str | None = None,
) -> None:
    """Genera la secuencia completa de animación según la fase del ciclo de 4 tiempos.

    Fases disponibles:
      full_cycle    — ciclo completo 720° (2 vueltas de cigüeñal).
      hero_intro    — 360° con pistón y cigüeñal en movimiento continuo.
      intake        — 0°–180° (1er tiempo: admisión).
      compression   — 180°–360° (2° tiempo: compresión).
      combustion    — 360°–540° (3er tiempo: expansión/combustión).
      exhaust       — 540°–720° (4° tiempo: escape).
      exploded_view — despiece axial progresivo.
      assembly_shot — ensamblaje inverso sincronizado (despiece a cerrado).
    """
    total_frames = max(10, end_frame - start_frame)

    # Rango angular
    phase_ranges = {
        "intake":        (0.0, math.pi),
        "compression":   (math.pi, 2 * math.pi),
        "combustion":    (2 * math.pi, 3 * math.pi),
        "exhaust":       (3 * math.pi, 4 * math.pi),
        "hero_intro":    (0.0, 2 * math.pi),
        "exploded_view": (0.0, math.pi),
        "assembly_shot": (0.0, 2 * math.pi),
    }
    theta_start, theta_end = phase_ranges.get(cycle_phase, (0.0, 4 * math.pi))

    # Pulso de resaltado (Highlight) en el material del componente mencionado
    if highlight_component and bpy is not None:
        target_mat_names = []
        if highlight_component == "piston":
            target_mat_names = ["Mat_Piston"]
        elif highlight_component == "connecting_rod":
            target_mat_names = ["Mat_ConnectingRod"]
        elif highlight_component == "crankshaft":
            target_mat_names = ["Mat_Crankshaft"]
        elif highlight_component == "valves":
            target_mat_names = ["Mat_ValveIntake", "Mat_ValveExhaust"]

        for m_name in target_mat_names:
            if m_name in bpy.data.materials:
                h_mat = bpy.data.materials[m_name]
                if h_mat.node_tree:
                    bsdf = h_mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf and "Emission Strength" in bsdf.inputs:
                        f_start = start_frame + int(total_frames * 0.10)
                        f_peak = start_frame + int(total_frames * 0.35)
                        f_end = start_frame + int(total_frames * 0.65)
                        bsdf.inputs["Emission Color"].default_value = (1.0, 0.82, 0.35, 1.0)
                        bsdf.inputs["Emission Strength"].default_value = 0.0
                        bsdf.inputs["Emission Strength"].keyframe_insert(data_path="default_value", frame=start_frame)
                        bsdf.inputs["Emission Strength"].keyframe_insert(data_path="default_value", frame=f_start)
                        bsdf.inputs["Emission Strength"].default_value = 1.8
                        bsdf.inputs["Emission Strength"].keyframe_insert(data_path="default_value", frame=f_peak)
                        bsdf.inputs["Emission Strength"].default_value = 0.0
                        bsdf.inputs["Emission Strength"].keyframe_insert(data_path="default_value", frame=f_end)

    for f in range(start_frame, end_frame + 1):
        progress = (f - start_frame) / float(total_frames)
        current_theta = theta_start + progress * (theta_end - theta_start)
        cycle_angle_deg = math.degrees(current_theta) % 720.0

        # --- Factor de despiece y ensamblaje ---
        if cycle_phase == "exploded_view":
            if progress < 0.35:
                exploded_factor = progress / 0.35
            elif progress < 0.68:
                exploded_factor = 1.0
            else:
                exploded_factor = max(0.0, 1.0 - (progress - 0.68) / 0.32)
        elif cycle_phase == "assembly_shot":
            if progress < 0.15:
                exploded_factor = 1.0
            elif progress < 0.75:
                t = (progress - 0.15) / 0.60
                s = t * t * (3.0 - 2.0 * t)  # Transición cúbica suave hermite
                exploded_factor = max(0.0, 1.0 - s)
            else:
                exploded_factor = 0.0
        else:
            exploded_factor = 0.0

        # --- Inicializar efectos ---
        intake_lift = 0.0
        exhaust_lift = 0.0
        spark_on = False
        flame_scale = 0.0
        intake_flow = 0.0
        exhaust_flow = 0.0
        compression_gas = 0.0

        # =================================================================
        # T1 — ADMISIÓN (0° → 180°): válvula admisión abierta, pistón baja
        # =================================================================
        intake_lift = _valve_lift_profile(cycle_angle_deg, 10.0, 170.0)
        if 10.0 <= cycle_angle_deg <= 170.0:
            # Flujo proporcional a la alzada de válvula
            intake_flow = intake_lift / 0.46

        # =================================================================
        # T2 — COMPRESIÓN (180° → 360°): todo cerrado, pistón sube
        # La mezcla se comprime visualmente aumentando en intensidad
        # =================================================================
        if 180.0 <= cycle_angle_deg <= 360.0:
            c_prog = (cycle_angle_deg - 180.0) / 180.0
            compression_gas = 0.4 + 0.6 * c_prog

        # =================================================================
        # IGNICIÓN (346° → 368°): chispa justo antes del PMS
        # =================================================================
        if 346.0 <= cycle_angle_deg <= 368.0:
            spark_on = True

        # =================================================================
        # T3 — COMBUSTIÓN/EXPANSIÓN (360° → 540°): llama, pistón baja
        # =================================================================
        if 360.0 <= cycle_angle_deg <= 530.0:
            fp = (cycle_angle_deg - 360.0) / 170.0
            # Llama crece rápido y luego se apaga
            if fp < 0.20:
                flame_scale = fp / 0.20
            else:
                flame_scale = max(0.0, 1.0 - (fp - 0.20) / 0.80)

        # =================================================================
        # T4 — ESCAPE (540° → 720°): válvula escape abierta, pistón sube
        # =================================================================
        exhaust_lift = _valve_lift_profile(cycle_angle_deg, 540.0, 700.0)
        if 540.0 <= cycle_angle_deg <= 700.0:
            exhaust_flow = exhaust_lift / 0.46

        apply_engine_pose_at_frame(
            engine_data=engine_data,
            frame=f,
            theta_rad=current_theta,
            intake_lift=intake_lift,
            exhaust_lift=exhaust_lift,
            spark_on=spark_on,
            flame_scale=flame_scale,
            intake_flow=intake_flow,
            exhaust_flow=exhaust_flow,
            compression_gas=compression_gas,
            exploded_factor=exploded_factor,
        )
