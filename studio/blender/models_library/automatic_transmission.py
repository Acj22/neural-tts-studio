"""Modelo 3D procedural de Transmisión Automática para Blender 5.3+ (Fase 3).

Orientación longitudinal en eje X para encuadre frontal cinematográfico:
- Extremo izquierdo (X < 0): Convertidor de par hidráulico seccionado (impulsor, turbina, estátor y fluido ATF).
- Zona central (X ≈ 0.2): Tren epicicloidal (engranaje solar dorado, 3 planetas engranados, carrier y corona azul).
- Zona derecha (X > 0): Paquete de embragues multidisco y eje de salida estriado.
- Mitad frontal cortada a 180° para exponer la cinemática interior a la cámara.
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

from studio.blender.materials import setup_engine_materials


def _smooth(obj: Any) -> Any:
    try:
        if obj and hasattr(obj, "data") and hasattr(obj.data, "polygons"):
            for poly in obj.data.polygons:
                poly.use_smooth = True
    except Exception:
        pass
    return obj


def _apply_bevel(obj: Any, width: float = 0.02, segments: int = 1) -> None:
    try:
        mod = obj.modifiers.new("Bevel_Mod", type="BEVEL")
        mod.width = width
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(35.0)
    except Exception:
        pass


def create_automatic_transmission_3d(center_z: float = 2.0) -> dict[str, Any]:
    """Construye proceduralmente el conjunto mecánico de la transmisión a lo largo del eje X."""
    if bpy is None:
        return {}

    mats = setup_engine_materials()
    data: dict[str, Any] = {"components": {}}

    # 1. Carcasa de Transmisión en Corte Transversal (Cubre posterior e inferior)
    # Campana del convertidor (Bellhousing) en la mitad posterior
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.65,
        depth=1.1,
        vertices=36,
        location=(-1.2, 0.25, center_z),
        rotation=(0, math.radians(90), 0),
    )
    bell_case = bpy.context.active_object
    bell_case.name = "Trans_Bellhousing_Case"
    bell_case.data.materials.append(mats.get("engine_block"))
    _smooth(bell_case)
    _apply_bevel(bell_case, width=0.03)

    # Cuerpo principal de la caja (Main Case)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.25,
        depth=2.4,
        vertices=36,
        location=(0.6, 0.25, center_z),
        rotation=(0, math.radians(90), 0),
    )
    main_case = bpy.context.active_object
    main_case.name = "Trans_Main_Case"
    main_case.data.materials.append(mats.get("engine_block"))
    _smooth(main_case)
    _apply_bevel(main_case, width=0.03)

    # Cárter de aceite inferior (Oil pan)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.1, 0.0, center_z - 1.35),
        scale=(3.4, 1.8, 0.25),
    )
    oil_pan = bpy.context.active_object
    oil_pan.name = "Trans_Oil_Pan"
    oil_pan.data.materials.append(mats.get("oil_pan"))
    _smooth(oil_pan)
    _apply_bevel(oil_pan, width=0.02)

    # 2. Convertidor de Par Hidráulico (Torque Converter) en X = -1.2
    # Carcasa toroidal exterior
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.25,
        minor_radius=0.35,
        major_segments=36,
        minor_segments=20,
        location=(-1.2, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    conv_housing = bpy.context.active_object
    conv_housing.name = "Converter_Housing"
    conv_housing.data.materials.append(mats.get("manifold_pipes"))
    _smooth(conv_housing)

    # Impulsor / Bomba (conectado al motor por la izquierda)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.12,
        depth=0.22,
        vertices=32,
        location=(-1.4, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    impeller = bpy.context.active_object
    impeller.name = "Converter_Impeller"
    impeller.data.materials.append(mats.get("piston"))  # Cobre/bronce para álabes de bomba
    _smooth(impeller)
    _apply_bevel(impeller, width=0.02)

    # Turbina (conectada al eje de entrada hacia la derecha)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.08,
        depth=0.22,
        vertices=32,
        location=(-1.0, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    turbine = bpy.context.active_object
    turbine.name = "Converter_Turbine"
    turbine.data.materials.append(mats.get("cutaway_rim"))  # Acero brillante satinado
    _smooth(turbine)
    _apply_bevel(turbine, width=0.02)

    # Fluido ATF Hidráulico (anillo rojo rubí translúcido entre álabes)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.88,
        minor_radius=0.15,
        location=(-1.2, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    atf_fluid = bpy.context.active_object
    atf_fluid.name = "Converter_ATF_Fluid"
    atf_fluid.data.materials.append(mats.get("fluid_atf"))
    _smooth(atf_fluid)

    # 3. Tren de Engranajes Epicicloidal / Planetario (Planetary Gear Set) en X = 0.35
    # Engranaje Solar Central (Sun Gear)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.45,
        depth=0.75,
        vertices=24,
        location=(0.35, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    sun_gear = bpy.context.active_object
    sun_gear.name = "Planetary_Sun_Gear"
    sun_gear.data.materials.append(mats.get("brass_gold"))  # Latón dorado
    _smooth(sun_gear)
    _apply_bevel(sun_gear, width=0.025)

    # 3 Engranajes Satélites / Planetas (Planet Pinions) en órbita en plano Y-Z
    orbit_radius = 0.82
    planet_objs: list[Any] = []
    for p_idx in range(3):
        angle = p_idx * (2.0 * math.pi / 3.0)
        py = orbit_radius * math.cos(angle)
        pz = center_z + orbit_radius * math.sin(angle)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.34,
            depth=0.68,
            vertices=20,
            location=(0.35, py, pz),
            rotation=(0, math.radians(90), 0),
        )
        planet = bpy.context.active_object
        planet.name = f"Planetary_Pinion_{p_idx+1}"
        planet.data.materials.append(mats.get("cylinder_liner"))  # Acero rectificado pulido
        _smooth(planet)
        _apply_bevel(planet, width=0.02)
        planet_objs.append(planet)

    # Porta-satélites (Planet Carrier)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.05,
        depth=0.14,
        vertices=32,
        location=(0.75, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    carrier = bpy.context.active_object
    carrier.name = "Planetary_Carrier"
    carrier.data.materials.append(mats.get("connecting_rod"))
    _smooth(carrier)
    _apply_bevel(carrier, width=0.02)

    # Corona Exterior Dentada (Ring Gear / Annulus) en corte superior/frontal
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.28,
        depth=0.72,
        vertices=36,
        location=(0.35, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    ring_gear = bpy.context.active_object
    ring_gear.name = "Planetary_Ring_Gear"
    ring_gear.data.materials.append(mats.get("ring_gear_blue"))  # Azul anodizado
    _smooth(ring_gear)
    _apply_bevel(ring_gear, width=0.03)

    # 4. Paquete de Embragues Multidisco (Clutch Pack) en X ≈ 1.2
    clutch_discs: list[Any] = []
    for c_idx in range(5):
        cx = 1.05 + c_idx * 0.12
        bpy.ops.mesh.primitive_cylinder_add(
            radius=1.18,
            depth=0.04,
            vertices=32,
            location=(cx, 0.0, center_z),
            rotation=(0, math.radians(90), 0),
        )
        cdisc = bpy.context.active_object
        cdisc.name = f"Clutch_Disc_{c_idx+1}"
        mat_c = mats.get("clutch_plate") if c_idx % 2 == 0 else mats.get("cutaway_rim")
        cdisc.data.materials.append(mat_c)
        _smooth(cdisc)
        clutch_discs.append(cdisc)

    # Eje de salida estriado (Output Shaft) extendiéndose a la derecha
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.26,
        depth=2.2,
        vertices=24,
        location=(1.5, 0.0, center_z),
        rotation=(0, math.radians(90), 0),
    )
    output_shaft = bpy.context.active_object
    output_shaft.name = "Transmission_Output_Shaft"
    output_shaft.data.materials.append(mats.get("crankshaft"))
    _smooth(output_shaft)
    _apply_bevel(output_shaft, width=0.02)

    data["components"] = {
        "bell_case": bell_case,
        "main_case": main_case,
        "oil_pan": oil_pan,
        "conv_housing": conv_housing,
        "impeller": impeller,
        "turbine": turbine,
        "atf_fluid": atf_fluid,
        "sun_gear": sun_gear,
        "planets": planet_objs,
        "carrier": carrier,
        "ring_gear": ring_gear,
        "clutch_discs": clutch_discs,
        "output_shaft": output_shaft,
    }
    return data


def build_transmission_keyframes(
    trans_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    scene_phase: str = "overview",
    highlight_component: str | None = None,
) -> None:
    """Aplica animación cinemática sincronizada con el eje longitudinal X."""
    if bpy is None:
        return

    comps = trans_data.get("components", {})
    sun = comps.get("sun_gear")
    planets = comps.get("planets", [])
    carrier = comps.get("carrier")
    ring = comps.get("ring_gear")
    impeller = comps.get("impeller")
    turbine = comps.get("turbine")
    atf = comps.get("atf_fluid")
    output_shaft = comps.get("output_shaft")

    total_frames = max(10, end_frame - start_frame)

    # Modo A: Despiece axial en X (Exploded View)
    if "exploded" in scene_phase or "components" in scene_phase:
        for obj, offset_x in [(comps.get("conv_housing"), -1.0), (impeller, -1.4), (turbine, -0.7), (atf, -1.0)]:
            if obj:
                x_base = obj.location.x
                obj.keyframe_insert("location", frame=start_frame)
                obj.location.x = x_base + offset_x
                obj.keyframe_insert("location", frame=end_frame)

        if sun:
            sun.keyframe_insert("location", frame=start_frame)
            sun.location.z += 0.4
            sun.keyframe_insert("location", frame=end_frame)
        if ring:
            ring.keyframe_insert("location", frame=start_frame)
            ring.location.z -= 0.5
            ring.keyframe_insert("location", frame=end_frame)
        if output_shaft:
            output_shaft.keyframe_insert("location", frame=start_frame)
            output_shaft.location.x += 0.8
            output_shaft.keyframe_insert("location", frame=end_frame)

    # Modo B: Demostración de Convertidor de Par
    elif "torque_converter" in scene_phase or "converter" in scene_phase:
        revs_impeller = total_frames / 18.0
        revs_turbine = total_frames / 24.0
        if impeller:
            impeller.rotation_euler = (0, math.radians(90), 0)
            impeller.keyframe_insert("rotation_euler", frame=start_frame)
            impeller.rotation_euler = (revs_impeller * 2 * math.pi, math.radians(90), 0)
            impeller.keyframe_insert("rotation_euler", frame=end_frame)
        if turbine:
            turbine.rotation_euler = (0, math.radians(90), 0)
            turbine.keyframe_insert("rotation_euler", frame=start_frame)
            turbine.rotation_euler = (revs_turbine * 2 * math.pi, math.radians(90), 0)
            turbine.keyframe_insert("rotation_euler", frame=end_frame)
        if atf:
            atf.scale = (1.0, 1.0, 1.0)
            atf.keyframe_insert("scale", frame=start_frame)
            atf.scale = (1.08, 1.08, 1.08)
            atf.keyframe_insert("scale", frame=start_frame + total_frames // 2)
            atf.scale = (1.0, 1.0, 1.0)
            atf.keyframe_insert("scale", frame=end_frame)

    # Modo C: Demostración del Tren Planetario (Reducción de velocidad / 1ª Marcha)
    elif "planetary" in scene_phase or "gear" in scene_phase:
        revs_sun = total_frames / 15.0
        revs_carrier = revs_sun / 2.8
        if sun:
            sun.rotation_euler = (0, math.radians(90), 0)
            sun.keyframe_insert("rotation_euler", frame=start_frame)
            sun.rotation_euler = (revs_sun * 2 * math.pi, math.radians(90), 0)
            sun.keyframe_insert("rotation_euler", frame=end_frame)
        if carrier:
            carrier.rotation_euler = (0, math.radians(90), 0)
            carrier.keyframe_insert("rotation_euler", frame=start_frame)
            carrier.rotation_euler = (revs_carrier * 2 * math.pi, math.radians(90), 0)
            carrier.keyframe_insert("rotation_euler", frame=end_frame)

        center_z = sun.location.z if sun else 2.0
        orbit_r = 0.82
        for p_idx, p_obj in enumerate(planets):
            init_ang = p_idx * (2.0 * math.pi / 3.0)
            p_obj.keyframe_insert("location", frame=start_frame)
            final_ang = init_ang + (revs_carrier * 2 * math.pi)
            p_obj.location.y = orbit_r * math.cos(final_ang)
            p_obj.location.z = center_z + orbit_r * math.sin(final_ang)
            p_obj.keyframe_insert("location", frame=end_frame)

    # Modo D: Embragues Hidráulicos comprimiendo
    elif "clutch" in scene_phase:
        clutches = comps.get("clutch_discs", [])
        for c_idx, c_obj in enumerate(clutches):
            c_obj.keyframe_insert("location", frame=start_frame)
            c_obj.location.x -= 0.03 * (c_idx + 1)
            c_obj.keyframe_insert("location", frame=end_frame)
        if output_shaft:
            revs_out = total_frames / 20.0
            output_shaft.rotation_euler = (0, math.radians(90), 0)
            output_shaft.keyframe_insert("rotation_euler", frame=start_frame)
            output_shaft.rotation_euler = (revs_out * 2 * math.pi, math.radians(90), 0)
            output_shaft.keyframe_insert("rotation_euler", frame=end_frame)

    # Modo E: Marcha continua armónica (Overview / Conclusión)
    else:
        revs = total_frames / 24.0
        if sun:
            sun.rotation_euler = (0, math.radians(90), 0)
            sun.keyframe_insert("rotation_euler", frame=start_frame)
            sun.rotation_euler = (revs * 2.5 * 2 * math.pi, math.radians(90), 0)
            sun.keyframe_insert("rotation_euler", frame=end_frame)
        if carrier:
            carrier.rotation_euler = (0, math.radians(90), 0)
            carrier.keyframe_insert("rotation_euler", frame=start_frame)
            carrier.rotation_euler = (revs * 2 * math.pi, math.radians(90), 0)
            carrier.keyframe_insert("rotation_euler", frame=end_frame)
        if impeller:
            impeller.rotation_euler = (0, math.radians(90), 0)
            impeller.keyframe_insert("rotation_euler", frame=start_frame)
            impeller.rotation_euler = (revs * 3.0 * 2 * math.pi, math.radians(90), 0)
            impeller.keyframe_insert("rotation_euler", frame=end_frame)
        if output_shaft:
            output_shaft.rotation_euler = (0, math.radians(90), 0)
            output_shaft.keyframe_insert("rotation_euler", frame=start_frame)
            output_shaft.rotation_euler = (revs * 2 * math.pi, math.radians(90), 0)
            output_shaft.keyframe_insert("rotation_euler", frame=end_frame)
