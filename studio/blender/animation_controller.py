"""Controlador cinemático y de animación para Blender 5.3 (Fase 2 - Perfeccionamiento).

Calcula las relaciones físicas exactas en orientación vertical (Z es UP):
- Posición del pistón: z(θ) = z_pin + sqrt(l^2 - r^2*sin(θ)^2)
- Giro de biela: φ(θ) = arcsin((r/l)*sin(θ)) alrededor del eje Y
- Rotación del cigüeñal: sincronizada concéntricamente alrededor de Y
- Los 4 tiempos mecánicos rigurosos:
  1. Admisión (0° -> 180°): Válvula admisión abierta, escape cerrada, pistón baja, flujo azul.
  2. Compresión (180° -> 360°): Ambas válvulas cerradas, pistón sube a PMS.
  3. Expansión (360° -> 540°): Chispa eléctrica a 350°, explosión estilizada, pistón baja empujado por gases.
  4. Escape (540° -> 720°): Válvula escape abierta, admisión cerrada, pistón sube expulsando gases.
- Sincronización continua de bucle sin saltos (seamless loop a 720°).
- Despiece cinemático axial suave (Exploded View) sin deformaciones ni piezas desalineadas.
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
    l: float = 3.5,
    crank_center_z: float = 0.4,
) -> tuple[float, float, float, float]:
    """Calcula matemáticamente la cinemática exacta del mecanismo biela-manivela.
    Retorna:
    - z_piston: Altura vertical del bulón/pistón
    - phi_rod: Ángulo de inclinación de la biela (en radianes, alrededor de Y)
    - x_pin: Posición X de la muñequilla
    - z_pin: Posición Z de la muñequilla
    """
    sin_t = math.sin(theta_rad)
    cos_t = math.cos(theta_rad)

    x_pin = r * sin_t
    z_pin = crank_center_z + (r * cos_t)

    # Inclinación angular de la biela en el plano X-Z
    sin_phi = (r / l) * sin_t
    sin_phi = max(-1.0, min(1.0, sin_phi))
    phi_rod = math.asin(sin_phi)

    # Recorrido vertical del pistón (altura del centro del bulón)
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
    """Inserta keyframes cinemáticos exactos en el fotograma indicado."""
    if bpy is None:
        return

    r = float(engine_data["crank_radius"])
    l = float(engine_data["rod_length"])
    crank_center_z = float(engine_data.get("crank_center_z", 0.4))

    z_piston, phi_rod, x_pin, z_pin = calculate_piston_kinematics(
        theta_rad=theta_rad,
        r=r,
        l=l,
        crank_center_z=crank_center_z,
    )

    # 1. Cigüeñal: Giro continuo alrededor del eje Y
    crank = engine_data["crank_root"]
    crank.rotation_euler = (0.0, -theta_rad, 0.0)
    crank.location = (0.0, 0.0, crank_center_z - (2.5 * exploded_factor))
    crank.keyframe_insert(data_path="rotation_euler", frame=frame)
    crank.keyframe_insert(data_path="location", frame=frame)

    # 2. Biela: Cabeza anclada exactamente en la muñequilla (X_pin, 0, Z_pin)
    # y rotación angular phi_rod para que su pie coincida con el bulón
    rod = engine_data["rod_root"]
    rod.location = (x_pin, 0.0, z_pin - (1.2 * exploded_factor))
    rod.rotation_euler = (0.0, -phi_rod, 0.0)
    rod.keyframe_insert(data_path="location", frame=frame)
    rod.keyframe_insert(data_path="rotation_euler", frame=frame)

    # 3. Pistón: Desplazamiento vertical puro a lo largo del eje Z
    piston = engine_data["piston_root"]
    piston.location = (0.0, 0.0, z_piston + (1.2 * exploded_factor))
    piston.keyframe_insert(data_path="location", frame=frame)

    # 4. Válvula de Admisión (Cian): Apertura descendente en tiempo 1
    v_in = engine_data["valve_intake"]
    v_in.location = (-0.58, 0.0, 5.6 - (intake_lift * 0.42) + (2.5 * exploded_factor))
    v_in.keyframe_insert(data_path="location", frame=frame)

    # 5. Válvula de Escape (Naranja): Apertura descendente en tiempo 4
    v_ex = engine_data["valve_exhaust"]
    v_ex.location = (0.58, 0.0, 5.6 - (exhaust_lift * 0.42) + (2.5 * exploded_factor))
    v_ex.keyframe_insert(data_path="location", frame=frame)

    # 6. Bujía: Se eleva suavemente en despiece axial
    spark = engine_data["spark_root"]
    spark.location = (0.0, 0.0, 6.2 + (3.4 * exploded_factor))
    spark.keyframe_insert(data_path="location", frame=frame)

    # 7. Culata: Se eleva en despiece axial
    if "cylinder_head" in engine_data:
        c_head = engine_data["cylinder_head"]
        c_head.location = (0.0, 0.0, 6.1 + (2.2 * exploded_factor))
        c_head.keyframe_insert(data_path="location", frame=frame)

    # 8. Efectos Volumétricos de Chispa Eléctrica
    fx_sp = engine_data["fx_spark"]
    sp_sc = 1.0 if spark_on else 0.001
    fx_sp.scale = (sp_sc, sp_sc, sp_sc)
    fx_sp.keyframe_insert(data_path="scale", frame=frame)

    # 9. Frente de Llama de Combustión
    fx_fl = engine_data["fx_flame"]
    fl_sc = max(0.001, flame_scale)
    fx_fl.scale = (fl_sc, fl_sc, fl_sc)
    fx_fl.keyframe_insert(data_path="scale", frame=frame)

    # 10. Indicadores de Flujo de Gas (Punto 6)
    if "fx_intake" in engine_data:
        fx_in = engine_data["fx_intake"]
        in_sc = max(0.001, intake_flow)
        fx_in.scale = (in_sc, in_sc, in_sc)
        fx_in.keyframe_insert(data_path="scale", frame=frame)

    if "fx_exhaust" in engine_data:
        fx_ex = engine_data["fx_exhaust"]
        ex_sc = max(0.001, exhaust_flow)
        fx_ex.scale = (ex_sc, ex_sc, ex_sc)
        fx_ex.keyframe_insert(data_path="scale", frame=frame)


def build_4_stroke_cycle_keyframes(
    engine_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    cycle_phase: str = "full_cycle",
) -> None:
    """Genera la secuencia completa de animación según la fase o los 4 tiempos continuos."""
    total_frames = max(10, end_frame - start_frame)

    # Definir el rango angular en radianes (720° = 4*pi para ciclo completo)
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
    else:  # full_cycle o régimen continuo (2 vueltas completas = 720°)
        theta_start, theta_end = 0.0, 4 * math.pi

    for f in range(start_frame, end_frame + 1):
        progress = (f - start_frame) / float(total_frames)

        # Factor de despiece axial (apertura progresiva y cierre suave)
        if cycle_phase == "exploded_view":
            if progress < 0.40:
                exploded_factor = progress / 0.40
            elif progress < 0.70:
                exploded_factor = 1.0
            else:
                exploded_factor = max(0.0, 1.0 - ((progress - 0.70) / 0.30))
        else:
            exploded_factor = 0.0

        current_theta = theta_start + (progress * (theta_end - theta_start))

        # Ciclo relativo normalizado a 0° - 720° (4 Tiempos exactos)
        cycle_angle_deg = math.degrees(current_theta) % 720.0

        intake_lift = 0.0
        exhaust_lift = 0.0
        spark_on = False
        flame_scale = 0.0
        intake_flow = 0.0
        exhaust_flow = 0.0

        # =====================================================================
        # 1. TIEMPO 1: ADMISIÓN (0° a 180°)
        # - Válvula admisión desciende (abierta)
        # - Válvula escape cerrada
        # - Pistón desciende succionando mezcla (flujo azul)
        # =====================================================================
        if 8.0 <= cycle_angle_deg <= 172.0:
            phi_rad = math.radians((cycle_angle_deg - 8.0) / 164.0 * 180.0)
            intake_lift = math.sin(phi_rad)
            intake_flow = intake_lift

        # =====================================================================
        # 2. TIEMPO 2: COMPRESIÓN (180° a 360°)
        # - Ambas válvulas herméticamente cerradas (lift = 0)
        # - Pistón asciende comprimiendo la mezcla hacia PMS
        # =====================================================================

        # =====================================================================
        # IGNICIÓN POR CHISPA (345° a 368° justo antes de PMS)
        # =====================================================================
        if 346.0 <= cycle_angle_deg <= 368.0:
            spark_on = True

        # =====================================================================
        # 3. TIEMPO 3: COMBUSTIÓN / EXPANSIÓN (360° a 540°)
        # - Ambas válvulas cerradas
        # - Frente de llama en expansión que empuja el pistón hacia abajo con fuerza
        # =====================================================================
        if 360.0 <= cycle_angle_deg <= 530.0:
            flame_progress = (cycle_angle_deg - 360.0) / 170.0
            if flame_progress < 0.22:
                flame_scale = flame_progress / 0.22
            else:
                flame_scale = max(0.0, 1.0 - ((flame_progress - 0.22) / 0.78))

        # =====================================================================
        # 4. TIEMPO 4: ESCAPE (540° a 720°)
        # - Válvula escape desciende (abierta)
        # - Válvula admisión cerrada
        # - Pistón asciende barriendo los gases quemados hacia el escape (flujo naranja)
        # =====================================================================
        if 548.0 <= cycle_angle_deg <= 712.0:
            phi_rad = math.radians((cycle_angle_deg - 548.0) / 164.0 * 180.0)
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
