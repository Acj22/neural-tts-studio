"""Modelo 3D procedural del Ciclo de Refrigeración y Refrigerador para Blender 5.3+ (Fase 3).

Orientación frontal directa hacia la cámara (Y < 0):
- Gabinete en corte transversal frontal exponiendo el interior.
- Congelador superior con fondo de escarcha y serpentín evaporador (absorbe calor).
- Compartimento inferior de alimentos con estantes de cristal.
- Nicho inferior con compresor hermético ("bocha negra") y base.
- Serpentín de condensador en lateral/espalda con disipación térmica y tubo capilar.
- Animación cinemática y termodinámica sincronizada para 6 escenas educativas.
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


def create_refrigerator_cycle_3d(center_z: float = 2.2) -> dict[str, Any]:
    """Construye proceduralmente el gabinete y circuito termodinámico de un refrigerador."""
    if bpy is None:
        return {}

    mats = setup_engine_materials()
    data: dict[str, Any] = {"components": {}}

    # 1. Gabinete Exterior e Interior seccionado (Corte frontal para ver el interior)
    # Pared trasera y laterales del refrigerador (Blanco perla)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.25, center_z),
        scale=(2.0, 1.2, 3.8),
    )
    cabinet = bpy.context.active_object
    cabinet.name = "Fridge_Cabinet"
    cabinet.data.materials.append(mats.get("white_cabinet"))
    _smooth(cabinet)
    _apply_bevel(cabinet, width=0.03)

    # Cavidad Congelador Superior (Freezer) con fondo azul escarcha
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -0.05, center_z + 1.1),
        scale=(1.75, 0.95, 1.15),
    )
    freezer_box = bpy.context.active_object
    freezer_box.name = "Fridge_Freezer_Box"
    freezer_box.data.materials.append(mats.get("frost_blue"))
    _smooth(freezer_box)

    # Cavidad Compartimento Fresco Inferior
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -0.05, center_z - 0.45),
        scale=(1.75, 0.95, 1.55),
    )
    fridge_box = bpy.context.active_object
    fridge_box.name = "Fridge_Fresh_Box"
    fridge_box.data.materials.append(mats.get("studio_floor"))
    _smooth(fridge_box)

    # Estantes de cristal en compartimento fresco
    shelves = []
    for s_idx in range(2):
        sz = (center_z - 0.75) + s_idx * 0.58
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, -0.05, sz),
            scale=(1.65, 0.85, 0.04),
        )
        sh = bpy.context.active_object
        sh.name = f"Fridge_Glass_Shelf_{s_idx+1}"
        sh.data.materials.append(mats.get("cutaway_rim"))
        _smooth(sh)
        shelves.append(sh)

    # 2. Compresor Hermético ("La bocha negra" en el nicho inferior frontal-izquierdo)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.42,
        depth=0.68,
        vertices=32,
        location=(-0.48, -0.15, center_z - 1.45),
        rotation=(0, 0, 0),
    )
    compressor = bpy.context.active_object
    compressor.name = "Fridge_Compressor"
    compressor.data.materials.append(mats.get("compressor_black"))
    _smooth(compressor)
    _apply_bevel(compressor, width=0.04)

    # Tapa superior abovedada del compresor
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.42,
        location=(-0.48, -0.15, center_z - 1.12),
        scale=(1.0, 1.0, 0.50),
    )
    comp_cap = bpy.context.active_object
    comp_cap.name = "Fridge_Compressor_Cap"
    comp_cap.data.materials.append(mats.get("compressor_black"))
    _smooth(comp_cap)

    # 3. Serpentín del Condensador (Tuberías disipadoras de cobre visibles en el lateral derecho)
    cond_coils = []
    for c_idx in range(5):
        cz = (center_z - 0.9) + c_idx * 0.45
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.042,
            depth=1.10,
            vertices=16,
            location=(1.15, 0.15, cz),
            rotation=(math.radians(90), 0, 0),
        )
        coil = bpy.context.active_object
        coil.name = f"Condenser_Tube_{c_idx+1}"
        coil_mat = mats.get("heat_red") if c_idx < 2 else mats.get("copper_coil")
        coil.data.materials.append(coil_mat)
        _smooth(coil)
        cond_coils.append(coil)

    # Ondas Térmicas Disipadas (Calor saliendo hacia la derecha)
    bpy.ops.mesh.primitive_plane_add(
        size=1.0,
        location=(1.45, 0.15, center_z),
        scale=(0.1, 1.2, 2.2),
        rotation=(0, 0, 0),
    )
    heat_waves = bpy.context.active_object
    heat_waves.name = "Condenser_Heat_Waves"
    heat_waves.data.materials.append(mats.get("heat_red"))
    _smooth(heat_waves)

    # 4. Filtro Deshidratador y Tubo Capilar de Expansión
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.075,
        depth=0.35,
        vertices=20,
        location=(0.45, -0.15, center_z - 1.35),
        rotation=(0, 0, 0),
    )
    dryer_filter = bpy.context.active_object
    dryer_filter.name = "Fridge_Dryer_Filter"
    dryer_filter.data.materials.append(mats.get("brass_gold"))
    _smooth(dryer_filter)

    # Tubo capilar en espiral subiendo hacia el evaporador
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.018,
        depth=2.2,
        vertices=12,
        location=(0.85, -0.05, center_z - 0.1),
        rotation=(0, 0, 0),
    )
    capillary_tube = bpy.context.active_object
    capillary_tube.name = "Fridge_Capillary_Tube"
    capillary_tube.data.materials.append(mats.get("frost_blue"))
    _smooth(capillary_tube)

    # 5. Serpentín del Evaporador (Dentro del congelador, absorbe calor)
    evap_coils = []
    for e_idx in range(3):
        ez = (center_z + 0.85) + e_idx * 0.25
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.038,
            depth=1.35,
            vertices=16,
            location=(0.0, -0.05, ez),
            rotation=(0, math.radians(90), 0),
        )
        evap = bpy.context.active_object
        evap.name = f"Evaporator_Tube_{e_idx+1}"
        evap.data.materials.append(mats.get("frost_blue"))
        _smooth(evap)
        evap_coils.append(evap)

    # Línea de retorno de baja presión hacia el compresor
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.045,
        depth=2.3,
        vertices=16,
        location=(-0.65, 0.0, center_z - 0.25),
        rotation=(0, 0, 0),
    )
    suction_line = bpy.context.active_object
    suction_line.name = "Fridge_Suction_Line"
    suction_line.data.materials.append(mats.get("intake_flow"))
    _smooth(suction_line)

    data["components"] = {
        "cabinet": cabinet,
        "freezer_box": freezer_box,
        "fridge_box": fridge_box,
        "shelves": shelves,
        "compressor": compressor,
        "comp_cap": comp_cap,
        "condenser_coils": cond_coils,
        "heat_waves": heat_waves,
        "dryer_filter": dryer_filter,
        "capillary_tube": capillary_tube,
        "evaporator_coils": evap_coils,
        "suction_line": suction_line,
    }
    return data


def build_refrigerator_keyframes(
    fridge_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    scene_phase: str = "overview",
    highlight_component: str | None = None,
) -> None:
    """Aplica animación termodinámica y de despiece según la fase del guion educativo."""
    if bpy is None:
        return

    comps = fridge_data.get("components", {})
    compressor = comps.get("compressor")
    comp_cap = comps.get("comp_cap")
    heat_waves = comps.get("heat_waves")
    evap_coils = comps.get("evaporator_coils", [])
    cabinet = comps.get("cabinet")

    total_frames = max(10, end_frame - start_frame)

    if "exploded" in scene_phase or "components" in scene_phase:
        if cabinet:
            cabinet.keyframe_insert("location", frame=start_frame)
            cabinet.location.y += 0.9
            cabinet.keyframe_insert("location", frame=end_frame)
        if heat_waves:
            heat_waves.keyframe_insert("location", frame=start_frame)
            heat_waves.location.x += 0.4
            heat_waves.keyframe_insert("location", frame=end_frame)

    elif "compressor" in scene_phase:
        if compressor and comp_cap:
            for obj in (compressor, comp_cap):
                base_z = obj.location.z
                for step in range(0, total_frames, 4):
                    f = start_frame + step
                    dz = 0.014 if (step // 4) % 2 == 0 else -0.014
                    obj.location.z = base_z + dz
                    obj.keyframe_insert("location", frame=f)
                obj.location.z = base_z
                obj.keyframe_insert("location", frame=end_frame)

    elif "condenser" in scene_phase:
        if heat_waves:
            heat_waves.scale = (0.1, 1.0, 1.8)
            heat_waves.keyframe_insert("scale", frame=start_frame)
            heat_waves.scale = (0.2, 1.4, 2.3)
            heat_waves.keyframe_insert("scale", frame=start_frame + total_frames // 2)
            heat_waves.scale = (0.1, 1.0, 1.8)
            heat_waves.keyframe_insert("scale", frame=end_frame)

    elif "expansion" in scene_phase or "evaporator" in scene_phase:
        for idx, coil in enumerate(evap_coils):
            coil.scale = (1.0, 1.0, 1.0)
            coil.keyframe_insert("scale", frame=start_frame)
            coil.scale = (1.15, 1.15, 1.15)
            coil.keyframe_insert("scale", frame=start_frame + (idx + 1) * 15)
            coil.scale = (1.0, 1.0, 1.0)
            coil.keyframe_insert("scale", frame=end_frame)

    else:
        if heat_waves:
            heat_waves.scale = (0.1, 1.1, 2.0)
            heat_waves.keyframe_insert("scale", frame=start_frame)
            heat_waves.scale = (0.16, 1.3, 2.15)
            heat_waves.keyframe_insert("scale", frame=start_frame + total_frames // 2)
            heat_waves.scale = (0.1, 1.1, 2.0)
            heat_waves.keyframe_insert("scale", frame=end_frame)
