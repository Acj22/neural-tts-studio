"""Modelo 3D procedural de Impresora 3D FDM para Blender 5.3+ (Fase 3).

Incluye:
- Chasis rígido de aluminio V-Slot negro con pórtico vertical y varillas roscadas.
- Carrete superior de filamento PLA naranja con tubo guía PTFE.
- Cama de impresión caliente texturizada en PEI dorado.
- Cabezal extrusor directo con bloque disipador, bloque térmico y boquilla de latón dorado.
- Pieza geométrica en proceso de impresión creciendo capa por capa.
- Hilo de filamento fundido depositado en la punta de la boquilla.
- Animación cinemática sincronizada para 6 escenas educativas.
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


def create_printer_3d_3d(center_z: float = 2.0) -> dict[str, Any]:
    """Construye proceduralmente la estructura mecánica y cinemática de una impresora 3D FDM."""
    if bpy is None:
        return {}

    mats = setup_engine_materials()
    data: dict[str, Any] = {"components": {}}

    # 1. Chasis y Pórtico V-Slot (Aluminio negro anodizado)
    # Base inferior en H
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, center_z - 1.6),
        scale=(2.6, 2.6, 0.25),
    )
    base_frame = bpy.context.active_object
    base_frame.name = "Printer_Base_Frame"
    base_frame.data.materials.append(mats.get("vslot_black"))
    _smooth(base_frame)
    _apply_bevel(base_frame, width=0.03)

    # Columnas verticales del eje Z (Izquierda y Derecha)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(-1.15, 0.0, center_z + 0.35),
        scale=(0.25, 0.25, 3.6),
    )
    column_left = bpy.context.active_object
    column_left.name = "Printer_Column_Left"
    column_left.data.materials.append(mats.get("vslot_black"))
    _smooth(column_left)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(1.15, 0.0, center_z + 0.35),
        scale=(0.25, 0.25, 3.6),
    )
    column_right = bpy.context.active_object
    column_right.name = "Printer_Column_Right"
    column_right.data.materials.append(mats.get("vslot_black"))
    _smooth(column_right)

    # Travesaño superior
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, center_z + 2.1),
        scale=(2.6, 0.25, 0.25),
    )
    top_bar = bpy.context.active_object
    top_bar.name = "Printer_Top_Bar"
    top_bar.data.materials.append(mats.get("vslot_black"))
    _smooth(top_bar)

    # Varilla roscada de precisión del eje Z
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.045,
        depth=3.4,
        vertices=16,
        location=(-0.95, 0.0, center_z + 0.35),
    )
    leadscrew_z = bpy.context.active_object
    leadscrew_z.name = "Printer_Leadscrew_Z"
    leadscrew_z.data.materials.append(mats.get("cutaway_rim"))
    _smooth(leadscrew_z)

    # 2. Cama Caliente de Impresión (Heated Bed)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, center_z - 1.25),
        scale=(1.8, 1.8, 0.08),
    )
    bed = bpy.context.active_object
    bed.name = "Printer_Heated_Bed"
    bed.data.materials.append(mats.get("pei_bed"))
    _smooth(bed)
    _apply_bevel(bed, width=0.015)

    # 3. Carrete de Filamento (Filament Spool) en el travesaño superior
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.65,
        depth=0.45,
        vertices=32,
        location=(0.65, 0.0, center_z + 2.75),
        rotation=(0, math.radians(90), 0),
    )
    spool = bpy.context.active_object
    spool.name = "Printer_Filament_Spool"
    spool.data.materials.append(mats.get("filament_orange"))
    _smooth(spool)
    _apply_bevel(spool, width=0.03)

    # Soporte del carrete
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.65, 0.0, center_z + 2.3),
        scale=(0.15, 0.15, 0.5),
    )
    spool_holder = bpy.context.active_object
    spool_holder.name = "Printer_Spool_Holder"
    spool_holder.data.materials.append(mats.get("vslot_black"))
    _smooth(spool_holder)

    # 4. Puente Móvil del Eje X y Cabezal Extrusor (Print Head & Hotend)
    # Puente horizontal que sube/baja en Z
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, center_z - 0.25),
        scale=(2.4, 0.20, 0.20),
    )
    x_gantry = bpy.context.active_object
    x_gantry.name = "Printer_X_Gantry"
    x_gantry.data.materials.append(mats.get("vslot_black"))
    _smooth(x_gantry)

    # Carro extrusor móvil en X
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, center_z - 0.25),
        scale=(0.55, 0.55, 0.55),
    )
    extruder_carriage = bpy.context.active_object
    extruder_carriage.name = "Printer_Extruder_Carriage"
    extruder_carriage.data.materials.append(mats.get("engine_block"))
    _smooth(extruder_carriage)
    _apply_bevel(extruder_carriage, width=0.02)

    # Bloque disipador térmico con aletas
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.16,
        depth=0.35,
        vertices=24,
        location=(0.0, -0.22, center_z - 0.55),
    )
    heatsink = bpy.context.active_object
    heatsink.name = "Printer_Heatsink"
    heatsink.data.materials.append(mats.get("cylinder_liner"))
    _smooth(heatsink)

    # Bloque calefactor (Heatblock)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -0.22, center_z - 0.82),
        scale=(0.28, 0.35, 0.20),
    )
    heatblock = bpy.context.active_object
    heatblock.name = "Printer_Heatblock"
    heatblock.data.materials.append(mats.get("connecting_rod"))
    _smooth(heatblock)

    # Boquilla de Latón Dorado (Brass Nozzle)
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.12,
        radius2=0.025,
        depth=0.22,
        vertices=24,
        location=(0.0, -0.22, center_z - 1.02),
        rotation=(math.radians(180), 0, 0),
    )
    nozzle = bpy.context.active_object
    nozzle.name = "Printer_Nozzle"
    nozzle.data.materials.append(mats.get("brass_gold"))
    _smooth(nozzle)
    _apply_bevel(nozzle, width=0.01)

    # Hilo de filamento extruido fundido brillante en la punta
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.028,
        depth=0.15,
        vertices=12,
        location=(0.0, -0.22, center_z - 1.14),
    )
    extrusion_line = bpy.context.active_object
    extrusion_line.name = "Printer_Extrusion_Line"
    extrusion_line.data.materials.append(mats.get("extrusion_glow"))
    _smooth(extrusion_line)

    # 5. Pieza Impresa en Proceso sobre la Cama (Part in Progress)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.42,
        depth=0.38,
        vertices=32,
        location=(0.0, -0.22, center_z - 1.15),
    )
    printed_part = bpy.context.active_object
    printed_part.name = "Printer_Printed_Part"
    printed_part.data.materials.append(mats.get("filament_orange"))
    _smooth(printed_part)
    _apply_bevel(printed_part, width=0.02)

    data["components"] = {
        "base_frame": base_frame,
        "columns": [column_left, column_right],
        "top_bar": top_bar,
        "leadscrew_z": leadscrew_z,
        "bed": bed,
        "spool": spool,
        "spool_holder": spool_holder,
        "x_gantry": x_gantry,
        "carriage": extruder_carriage,
        "heatsink": heatsink,
        "heatblock": heatblock,
        "nozzle": nozzle,
        "extrusion_line": extrusion_line,
        "printed_part": printed_part,
    }
    return data


def build_printer_3d_keyframes(
    printer_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    scene_phase: str = "overview",
    highlight_component: str | None = None,
) -> None:
    """Aplica animación cinemática y de deposición según la fase del guion educativo."""
    if bpy is None:
        return

    comps = printer_data.get("components", {})
    carriage = comps.get("carriage")
    heatsink = comps.get("heatsink")
    heatblock = comps.get("heatblock")
    nozzle = comps.get("nozzle")
    ext_line = comps.get("extrusion_line")
    x_gantry = comps.get("x_gantry")
    bed = comps.get("bed")
    spool = comps.get("spool")
    part = comps.get("printed_part")

    total_frames = max(10, end_frame - start_frame)
    head_group = [carriage, heatsink, heatblock, nozzle, ext_line]

    # Modo A: Despiece axial de subsistemas
    if "exploded" in scene_phase or "components" in scene_phase:
        # Elevar gantry y cabezal
        if x_gantry:
            x_gantry.keyframe_insert("location", frame=start_frame)
            x_gantry.location.z += 0.8
            x_gantry.keyframe_insert("location", frame=end_frame)
        for obj in head_group:
            if obj:
                obj.keyframe_insert("location", frame=start_frame)
                obj.location.z += 0.8
                obj.keyframe_insert("location", frame=end_frame)
        # Desplazar cama hacia el frente
        if bed:
            bed.keyframe_insert("location", frame=start_frame)
            bed.location.y -= 0.6
            bed.keyframe_insert("location", frame=end_frame)

    # Modo B: Enfoque en Hotend y Boquilla térmica
    elif "hotend" in scene_phase or "extrusion" in scene_phase:
        # Micro movimiento en perímetro circular
        r_path = 0.22
        for step in range(0, total_frames, 5):
            f = start_frame + step
            theta = (step / float(total_frames)) * 4.0 * math.pi
            dx = r_path * math.cos(theta)
            dy = r_path * math.sin(theta)
            for obj in head_group:
                if obj:
                    obj.location.x = dx
                    obj.keyframe_insert("location", frame=f)
        if ext_line:
            ext_line.scale = (1.0, 1.0, 1.0)
            ext_line.keyframe_insert("scale", frame=start_frame)
            ext_line.scale = (1.3, 1.3, 1.3)
            ext_line.keyframe_insert("scale", frame=start_frame + total_frames // 2)
            ext_line.scale = (1.0, 1.0, 1.0)
            ext_line.keyframe_insert("scale", frame=end_frame)

    # Modo C: Demostración cinemática de los tres ejes (X, Y, Z)
    elif "axis_motion" in scene_phase or "movement" in scene_phase:
        # El cabezal barre en X (-0.6 a +0.6)
        for obj in head_group:
            if obj:
                obj.keyframe_insert("location", frame=start_frame)
                obj.location.x = -0.55
                obj.keyframe_insert("location", frame=start_frame + total_frames // 2)
                obj.location.x = 0.55
                obj.keyframe_insert("location", frame=end_frame)
        # La cama barre en Y (-0.4 a +0.4)
        if bed:
            bed.keyframe_insert("location", frame=start_frame)
            bed.location.y = 0.35
            bed.keyframe_insert("location", frame=start_frame + total_frames // 2)
            bed.location.y = -0.35
            bed.keyframe_insert("location", frame=end_frame)

    # Modo D: Construcción Capa por Capa (La pieza crece en Z)
    elif "layer_by_layer" in scene_phase or "layers" in scene_phase:
        if part:
            part.scale = (1.0, 1.0, 0.4)
            part.keyframe_insert("scale", frame=start_frame)
            part.scale = (1.0, 1.0, 1.25)
            part.keyframe_insert("scale", frame=end_frame)
        # El cabezal sube coordinadamente
        for obj in head_group:
            if obj:
                obj.keyframe_insert("location", frame=start_frame)
                obj.location.z += 0.28
                obj.keyframe_insert("location", frame=end_frame)
        if x_gantry:
            x_gantry.keyframe_insert("location", frame=start_frame)
            x_gantry.location.z += 0.28
            x_gantry.keyframe_insert("location", frame=end_frame)

    # Modo E: Marcha continua armónica (Overview / Conclusión)
    else:
        # Movimiento de impresión continuo
        r_path = 0.25
        for step in range(0, total_frames, 6):
            f = start_frame + step
            theta = (step / float(total_frames)) * 6.0 * math.pi
            dx = r_path * math.cos(theta)
            for obj in head_group:
                if obj:
                    obj.location.x = dx
                    obj.keyframe_insert("location", frame=f)
        if spool:
            revs = total_frames / 30.0
            spool.rotation_euler = (0, 0, 0)
            spool.keyframe_insert("rotation_euler", frame=start_frame)
            spool.rotation_euler = (revs * 2 * math.pi, 0, 0)
            spool.keyframe_insert("rotation_euler", frame=end_frame)
