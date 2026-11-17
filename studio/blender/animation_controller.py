"""Controlador cinemático y de animación para Blender 5.3 (Fase 5).

Calcula las relaciones físicas exactas:
- Posición del pistón: y(θ) = r*cos(θ) + sqrt(l^2 - r^2*sin(θ)^2)
- Giro de biela: φ(θ) = arcsin((r/l)*sin(θ))
- Apertura de válvulas de admisión (0° -> 180°) y escape (540° -> 720°)
- Salto de chispa (~350°) e ignición/expansión (360° -> 540°)
- Animación de despiece cinemático (Exploded View) sin deformaciones
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


def calculate_piston_kinematics(theta_rad: float, r: float = 1.0, l: float = 3.5) -> tuple[float, float, float, float]:
    """Calcula matemáticamente la posición y ángulo exactos del conjunto biela-manivela.
    Retorna:
    - y_piston: Altura vertical del bulón/pistón
    - phi_rod: Ángulo de inclinación de la biela en radianes
    - x_crank_pin: Posición X de la muñequilla
    - y_crank_pin: Posición Y de la muñequilla
    """
    sin_t = math.sin(theta_rad)
    cos_t = math.cos(theta_rad)

    x_pin = r * sin_t
    y_pin = r * cos_t

    # Inclinación angular de la biela
    sin_phi = (r / l) * sin_t
    sin_phi = max(-1.0, min(1.0, sin_phi))
    phi_rod = math.asin(sin_phi)

    # Recorrido vertical del pistón
    y_piston = y_pin + math.sqrt(max(0.0001, (l * l) - (r * r * sin_t * sin_t)))

    return y_piston, phi_rod, x_pin, y_pin


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

    y_piston, phi_rod, x_pin, y_pin = calculate_piston_kinematics(theta_rad, r, l)

    # 1. Rotación del Cigüeñal (alrededor del eje Z)
    crank = engine_data["crank_root"]
    crank.rotation_euler = (0.0, 0.0, -theta_rad)
    crank.location = (0.0, -2.5 * exploded_factor, 0.0)
    crank.keyframe_insert(data_path="rotation_euler", frame=frame)
    crank.keyframe_insert(data_path="location", frame=frame)

    # 2. Desplazamiento Vertical del Pistón
    piston = engine_data["piston_root"]
    piston.location = (0.0, y_piston + (1.2 * exploded_factor), 0.0)
    piston.keyframe_insert(data_path="location", frame=frame)

    # 3. Posición y Rotación de la Biela
    rod = engine_data["rod_root"]
    rod.location = (0.0, y_piston - 0.25, 0.0)
    rod.rotation_euler = (0.0, 0.0, phi_rod)
    rod.keyframe_insert(data_path="location", frame=frame)
    rod.keyframe_insert(data_path="rotation_euler", frame=frame)

    # 4. Válvula de Admisión
    v_in = engine_data["valve_intake"]
    # Lift desciende hacia la cámara
    v_in.location.y = 5.5 - (intake_lift * 0.42) + (2.5 * exploded_factor)
    v_in.keyframe_insert(data_path="location", frame=frame)

    # 5. Válvula de Escape
    v_ex = engine_data["valve_exhaust"]
    v_ex.location.y = 5.5 - (exhaust_lift * 0.42) + (2.5 * exploded_factor)
    v_ex.keyframe_insert(data_path="location", frame=frame)

    # 6. Bujía (se eleva en despiece)
    spark = engine_data["spark_root"]
    spark.location.y = 5.75 + (3.2 * exploded_factor)
    spark.keyframe_insert(data_path="location", frame=frame)

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

    # 9. Flujo de Admisión
    fx_in = engine_data["fx_intake"]
    in_sc = max(0.001, intake_flow)
    fx_in.scale = (in_sc, in_sc, in_sc)
    fx_in.keyframe_insert(data_path="scale", frame=frame)

    # 10. Flujo de Escape
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
    """Genera la secuencia completa de animación según la fase o los 4 tiempos continuos.
    Fases soportadas:
    - 'hero_intro': Giro suave inicial mostrando la máquina
    - 'intake': 0° -> 180° (Válvula admisión abierta, pistón baja, flujo azul)
    - 'compression': 180° -> 360° (Válvulas cerradas, pistón sube, gas concentrado)
    - 'combustion': 350° -> 540° (Salto de chispa, explosión de llama, empuje potente)
    - 'exhaust': 540° -> 720° (Válvula escape abierta, pistón sube barriendo gas)
    - 'exploded_view': Despiece axial donde las piezas se separan suavemente
    - 'full_cycle': Los 720 grados (2 vueltas de cigüeñal) sincronizados
    """
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
        # En despiece el cigüeñal gira lentamente mientras las partes se expanden
        theta_start, theta_end = 0.0, math.pi
    else:  # full_cycle
        theta_start, theta_end = 0.0, 4 * math.pi  # 720 grados = 1 ciclo completo de 4 tiempos

    step_count = max(8, int(total_frames / 2.5))
    for i in range(step_count + 1):
        progress = i / float(step_count)
        cur_frame = int(start_frame + progress * total_frames)
        cur_theta = theta_start + progress * (theta_end - theta_start)

        # Determinar posición en el ciclo de 720 grados (0 a 4pi)
        mod_theta = cur_theta % (4 * math.pi)
        deg = math.degrees(mod_theta)

        # Admisión (0° -> 180°)
        if 5.0 <= deg <= 175.0:
            intake_lift = math.sin(math.radians(deg))
            intake_flow = 1.0
        else:
            intake_lift = 0.0
            intake_flow = 0.0

        # Compresión (180° -> 360°)
        # Ambas válvulas selladas

        # Chispa e Ignición (345° -> 365°)
        spark_on = (345.0 <= deg <= 365.0)

        # Expansión / Llama (360° -> 530°)
        if 360.0 <= deg <= 530.0:
            flame_progress = (deg - 360.0) / 170.0
            # Pico de llama rápido y decaimiento
            if flame_progress < 0.25:
                flame_scale = flame_progress / 0.25
            else:
                flame_scale = max(0.0, 1.0 - (flame_progress - 0.25) / 0.75)
        else:
            flame_scale = 0.0

        # Escape (540° -> 715°)
        if 545.0 <= deg <= 715.0:
            exhaust_deg = deg - 540.0
            exhaust_lift = math.sin(math.radians(exhaust_deg))
            exhaust_flow = 1.0
        else:
            exhaust_lift = 0.0
            exhaust_flow = 0.0

        # Factor de despiece si es la toma de exploded_view
        if cycle_phase == "exploded_view":
            # Abre suavemente en la primera mitad y se mantiene
            exp_factor = min(1.0, progress * 1.8)
        else:
            exp_factor = 0.0

        apply_engine_pose_at_frame(
            engine_data=engine_data,
            frame=cur_frame,
            theta_rad=cur_theta,
            intake_lift=intake_lift,
            exhaust_lift=exhaust_lift,
            spark_on=spark_on,
            flame_scale=flame_scale,
            intake_flow=intake_flow,
            exhaust_flow=exhaust_flow,
            exploded_factor=exp_factor,
        )
