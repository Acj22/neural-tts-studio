"""Controlador cinemático y de animación para Blender 5.3 (Fase 5).

Calcula las relaciones físicas exactas en orientación vertical (Z es UP):
- Posición del pistón: z(θ) = z_pin + sqrt(l^2 - r^2*sin(θ)^2)
- Giro de biela: φ(θ) = arcsin((r/l)*sin(θ)) alrededor del eje Y
- Rotación del cigüeñal: alrededor del eje Y
- Apertura de válvulas de admisión (0° -> 180°) y escape (540° -> 720°)
- Salto de chispa (~350°) e ignición/expansión (360° -> 540°)
- Animación de despiece cinemático axial (Exploded View) en el eje Z
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


def calculate_piston_kinematics(theta_rad: float, r: float = 1.0, l: float = 3.5, crank_center_z: float = 0.4) -> tuple[float, float, float, float]:
    """Calcula matemáticamente la posición y ángulo exactos del conjunto biela-manivela.
    Retorna:
    - z_piston: Altura vertical del bulón/pistón
    - phi_rod: Ángulo de inclinación de la biela en radianes (alrededor de Y)
    - x_crank_pin: Posición X de la muñequilla
    - z_crank_pin: Posición Z de la muñequilla
    """
    sin_t = math.sin(theta_rad)
    cos_t = math.cos(theta_rad)

    x_pin = r * sin_t
    z_pin = crank_center_z + (r * cos_t)

    # Inclinación angular de la biela
    sin_phi = (r / l) * sin_t
    sin_phi = max(-1.0, min(1.0, sin_phi))
    phi_rod = math.asin(sin_phi)

    # Recorrido vertical del pistón
    z_piston = z_pin + math.sqrt(max(0.0001, (l * l) - (r * r * sin_t * sin_t)))

    return z_piston, phi_rod, x_pin, z_pin


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
    exploded_factor: float = 0.0,
) -> None:
    """Inserta keyframes cinemáticos coherentes en el fotograma indicado."""
    if bpy is None:
        return

    r = float(engine_data["crank_radius"])
    l = float(engine_data["rod_length"])

    z_piston, phi_rod, x_pin, z_pin = calculate_piston_kinematics(theta_rad, r, l)

    # 1. Rotación del Cigüeñal (alrededor del eje Y)
    crank = engine_data["crank_root"]
    crank.rotation_euler = (0.0, -theta_rad, 0.0)
    crank.location = (0.0, 0.0, 0.4 - (2.5 * exploded_factor))
    crank.keyframe_insert(data_path="rotation_euler", frame=frame)
    crank.keyframe_insert(data_path="location", frame=frame)

    # 2. Desplazamiento Vertical del Pistón
    piston = engine_data["piston_root"]
    piston.location = (0.0, 0.0, z_piston + (1.2 * exploded_factor))
    piston.keyframe_insert(data_path="location", frame=frame)

    # 3. Posición y Rotación de la Biela (articulada en la muñequilla)
    rod = engine_data["rod_root"]
    rod.location = (x_pin, 0.0, z_pin)
    rod.rotation_euler = (0.0, -phi_rod, 0.0)
    rod.keyframe_insert(data_path="location", frame=frame)
    rod.keyframe_insert(data_path="rotation_euler", frame=frame)

    # 4. Válvula de Admisión
    v_in = engine_data["valve_intake"]
    v_in.location = (-0.58, 0.0, 5.6 - (intake_lift * 0.42) + (2.5 * exploded_factor))
    v_in.keyframe_insert(data_path="location", frame=frame)

    # 5. Válvula de Escape
    v_ex = engine_data["valve_exhaust"]
    v_ex.location = (0.58, 0.0, 5.6 - (exhaust_lift * 0.42) + (2.5 * exploded_factor))
    v_ex.keyframe_insert(data_path="location", frame=frame)

    # 6. Bujía (se eleva en despiece)
    spark = engine_data["spark_root"]
    spark.location = (0.0, 0.0, 6.2 + (3.2 * exploded_factor))
    spark.keyframe_insert(data_path="location", frame=frame)

    # Culata (se eleva en despiece)
    if "cylinder_head" in engine_data:
        c_head = engine_data["cylinder_head"]
        c_head.location = (0.0, 0.0, 6.15 + (2.2 * exploded_factor))
        c_head.keyframe_insert(data_path="location", frame=frame)

    # 7. Chispa Eléctrica
    fx_sp = engine_data["fx_spark"]
    sp_sc = 1.0 if spark_on else 0.001
    fx_sp.scale = (sp_sc, sp_sc, sp_sc)
    fx_sp.keyframe_insert(data_path="scale", frame=frame)

    # 8. Llama de Combustión
    fx_fl = engine_data["fx_flame"]
    fl_sc = max(0.001, flame_scale)
    fx_fl.scale = (fl_sc, fl_sc, fl_sc)
    fx_fl.keyframe_insert(data_path="scale", frame=frame)


def build_4_stroke_cycle_keyframes(
    engine_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    cycle_phase: str = "full_cycle",
) -> None:
    """Genera la secuencia completa de animación según la fase o los 4 tiempos continuos."""
    total_frames = max(10, end_frame - start_frame)

    if cycle_phase == "intake":
        theta_start, theta_end = 0.0, math.pi
    elif cycle_phase == "compression":
        theta_start, theta_end = math.pi, 2 * math.pi
    elif cycle_phase == "combustion":
        theta_start, theta_end = 2 * math.pi, 3 * math.pi
    elif cycle_phase == "exhaust":
        theta_start, theta_end = 3 * math.pi, 4 * math.pi
    elif cycle_phase == "hero_intro":
        theta_start, theta_end = 0.0, 2 * math.pi
    elif cycle_phase == "exploded_view":
        theta_start, theta_end = 0.0, math.pi
    else:  # full_cycle o régimen continuo (2 vueltas = 720°)
        theta_start, theta_end = 0.0, 4 * math.pi

    for f in range(start_frame, end_frame + 1):
        progress = (f - start_frame) / float(total_frames)

        # Factor de despiece axial suave
        if cycle_phase == "exploded_view":
            # Abre en el primer 45%, sostiene 25%, cierra en el último 30%
            if progress < 0.45:
                exploded_factor = progress / 0.45
            elif progress < 0.70:
                exploded_factor = 1.0
            else:
                exploded_factor = max(0.0, 1.0 - ((progress - 0.70) / 0.30))
        else:
            exploded_factor = 0.0

        current_theta = theta_start + (progress * (theta_end - theta_start))

        # Ciclo relativo de 0° a 720° (4 Tiempos)
        cycle_angle_deg = math.degrees(current_theta) % 720.0

        intake_lift = 0.0
        exhaust_lift = 0.0
        spark_on = False
        flame_scale = 0.0
        intake_flow = 0.0
        exhaust_flow = 0.0

        # TIEMPO 1: ADMISIÓN (0° a 180°)
        if 5.0 <= cycle_angle_deg <= 175.0:
            phi_rad = math.radians((cycle_angle_deg - 5.0) / 170.0 * 180.0)
            intake_lift = math.sin(phi_rad)
            intake_flow = intake_lift

        # TIEMPO 2: COMPRESIÓN (180° a 360°) - Válvulas herméticamente selladas

        # IGNICIÓN Y CHISPA (345° a 368°)
        if 345.0 <= cycle_angle_deg <= 368.0:
            spark_on = True

        # TIEMPO 3: COMBUSTIÓN / EXPANSIÓN (360° a 540°)
        if 360.0 <= cycle_angle_deg <= 530.0:
            flame_progress = (cycle_angle_deg - 360.0) / 170.0
            if flame_progress < 0.25:
                flame_scale = flame_progress / 0.25
            else:
                flame_scale = max(0.0, 1.0 - ((flame_progress - 0.25) / 0.75))

        # TIEMPO 4: ESCAPE (540° a 720°)
        if 545.0 <= cycle_angle_deg <= 715.0:
            phi_rad = math.radians((cycle_angle_deg - 545.0) / 170.0 * 180.0)
            exhaust_lift = math.sin(phi_rad)
            exhaust_flow = exhaust_lift

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
            exploded_factor=exploded_factor,
        )
