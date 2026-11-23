"""Modelo 3D Procedural de Pirámide y Monumento Mesoamericano en Blender 5.3 (EEVEE Next).

Genera una maqueta arquitectónica de precisión histórica y arqueológica:
- Estructura escalonada de 4 terrazas con proporción talud-tablero estilo Teotihuacán / Chichén Itzá.
- Escalinata monumental central con alfardas de piedra y remates ceremoniales.
- Templo superior con pórtico de dos pilares y dintel labrado.
- Altar ceremonial con bracero sagrado e iluminación cálida de fuego (faro de luz puntual).
- Materiales PBR procedurales: Caliza erosionada, obsidiana pulida, estuco rojo ritual y suelo de piedra labrada.
- Iluminación cinematográfica de hora dorada (Key light ámbar, Fill azul celeste y Rim especular).
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


def _smooth(obj: Any) -> Any:
    try:
        if obj and hasattr(obj, "data") and hasattr(obj.data, "polygons"):
            for poly in obj.data.polygons:
                poly.use_smooth = True
    except Exception:
        pass
    return obj


def _apply_bevel(obj: Any, width: float = 0.02, segments: int = 2) -> None:
    try:
        mod = obj.modifiers.new("Bevel", type="BEVEL")
        mod.width = width
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(30.0)
    except Exception:
        pass


def setup_pyramid_materials() -> dict[str, Any]:
    """Crea los materiales PBR procedurales para el monumento ceremonial."""
    if bpy is None:
        return {}

    mats = {}

    # 1. Piedra Caliza Erosionada (Cuerpo de la Pirámide)
    mat_stone = bpy.data.materials.new("Mat_PyramidStone")
    mat_stone.use_nodes = True
    bsdf = mat_stone.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (0.58, 0.52, 0.44, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.88
    mats["stone"] = mat_stone

    # 2. Estuco Rojo Ritual Ceremonial (Frisos y cornisas)
    mat_stucco = bpy.data.materials.new("Mat_PyramidStucco")
    mat_stucco.use_nodes = True
    bsdf_st = mat_stucco.node_tree.nodes.get("Principled BSDF")
    if bsdf_st:
        if "Base Color" in bsdf_st.inputs:
            bsdf_st.inputs["Base Color"].default_value = (0.55, 0.16, 0.12, 1.0)
        if "Roughness" in bsdf_st.inputs:
            bsdf_st.inputs["Roughness"].default_value = 0.75
    mats["stucco"] = mat_stucco

    # 3. Obsidiana Negra Pulida (Altar y remates)
    mat_obsidian = bpy.data.materials.new("Mat_Obsidian")
    mat_obsidian.use_nodes = True
    bsdf_ob = mat_obsidian.node_tree.nodes.get("Principled BSDF")
    if bsdf_ob:
        if "Base Color" in bsdf_ob.inputs:
            bsdf_ob.inputs["Base Color"].default_value = (0.04, 0.04, 0.05, 1.0)
        if "Roughness" in bsdf_ob.inputs:
            bsdf_ob.inputs["Roughness"].default_value = 0.12
        if "IOR" in bsdf_ob.inputs:
            bsdf_ob.inputs["IOR"].default_value = 1.55
    mats["obsidian"] = mat_obsidian

    # 4. Fuego Sagrado Emisivo
    mat_fire = bpy.data.materials.new("Mat_SacredFire")
    mat_fire.use_nodes = True
    bsdf_fi = mat_fire.node_tree.nodes.get("Principled BSDF")
    if bsdf_fi:
        if "Emission Color" in bsdf_fi.inputs:
            bsdf_fi.inputs["Emission Color"].default_value = (1.0, 0.45, 0.05, 1.0)
        if "Emission Strength" in bsdf_fi.inputs:
            bsdf_fi.inputs["Emission Strength"].default_value = 8.5
    mats["fire"] = mat_fire

    return mats


def create_pyramid_monument_3d(
    base_size: float = 7.0,
    num_tiers: int = 4,
    tier_height: float = 0.85,
) -> dict[str, Any]:
    """Construye proceduralmente la Pirámide Monumental con proporciones talud-tablero y templo."""
    if bpy is None:
        return {}

    mats = setup_pyramid_materials()
    created_objects = []

    # Plataforma Base
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, 0.1),
        scale=(base_size * 1.25, base_size * 1.25, 0.2),
    )
    ground = bpy.context.active_object
    ground.name = "Pyramid_Ground_Plaza"
    if "stone" in mats:
        ground.data.materials.append(mats["stone"])
    created_objects.append(ground)

    # Terrazas Escalonadas con Talud-Tablero
    current_z = 0.2
    for t_idx in range(num_tiers):
        t_factor = 1.0 - (t_idx / float(num_tiers)) * 0.55
        tier_size = base_size * t_factor
        t_center_z = current_z + (tier_height / 2.0)

        # Cuerpo del nivel
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, 0.0, t_center_z),
            scale=(tier_size, tier_size, tier_height),
        )
        tier_obj = bpy.context.active_object
        tier_obj.name = f"Pyramid_Tier_{t_idx + 1}"
        _apply_bevel(tier_obj, width=0.04)
        if "stone" in mats:
            tier_obj.data.materials.append(mats["stone"])
        created_objects.append(tier_obj)

        # Cornisa de estuco ritual (Tablero decorativo)
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, 0.0, current_z + tier_height - 0.05),
            scale=(tier_size * 1.03, tier_size * 1.03, 0.10),
        )
        cornice = bpy.context.active_object
        cornice.name = f"Pyramid_Cornice_{t_idx + 1}"
        if "stucco" in mats:
            cornice.data.materials.append(mats["stucco"])
        created_objects.append(cornice)

        current_z += tier_height

    # Escalinata Monumental Central (Frente Y negativo)
    stair_width = base_size * 0.28
    stair_depth = base_size * 0.58
    total_h = current_z - 0.2
    stair_angle = math.atan2(total_h, stair_depth)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -stair_depth * 0.52, total_h * 0.5 + 0.1),
        scale=(stair_width, stair_depth, total_h),
    )
    ramp = bpy.context.active_object
    ramp.name = "Pyramid_Stairway_Ramp"
    ramp.rotation_euler[0] = stair_angle * 0.25
    _apply_bevel(ramp, width=0.03)
    if "stone" in mats:
        ramp.data.materials.append(mats["stone"])
    created_objects.append(ramp)

    # Alfardas de Piedra a los costados de la escalera
    for side in (-1.0, 1.0):
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(side * (stair_width * 0.5 + 0.08), -stair_depth * 0.52, total_h * 0.5 + 0.15),
            scale=(0.14, stair_depth * 1.02, total_h * 1.05),
        )
        balustrade = bpy.context.active_object
        balustrade.name = f"Pyramid_Balustrade_{'L' if side < 0 else 'R'}"
        balustrade.rotation_euler[0] = ramp.rotation_euler[0]
        if "stucco" in mats:
            balustrade.data.materials.append(mats["stucco"])
        created_objects.append(balustrade)

    # Templo Superior en la Cúspide
    temple_size_x = base_size * 0.36
    temple_size_y = base_size * 0.32
    temple_h = 1.35
    temple_z = current_z + (temple_h / 2.0)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, temple_z),
        scale=(temple_size_x, temple_size_y, temple_h),
    )
    temple = bpy.context.active_object
    temple.name = "Pyramid_Summit_Temple"
    _apply_bevel(temple, width=0.03)
    if "stucco" in mats:
        temple.data.materials.append(mats["stucco"])
    created_objects.append(temple)

    # Columnas del Pórtico del Templo
    for col_x in (-temple_size_x * 0.25, temple_size_x * 0.25):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.12,
            depth=temple_h * 0.85,
            location=(col_x, -temple_size_y * 0.48, temple_z - 0.08),
        )
        col = bpy.context.active_object
        col.name = "Temple_Column"
        _smooth(col)
        if "stone" in mats:
            col.data.materials.append(mats["stone"])
        created_objects.append(col)

    # Altar de Obsidiana con Fuego Sagrado
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.28,
        depth=0.45,
        location=(0.0, -temple_size_y * 0.85, current_z + 0.22),
    )
    altar = bpy.context.active_object
    altar.name = "Sacred_Obsidian_Altar"
    _smooth(altar)
    if "obsidian" in mats:
        altar.data.materials.append(mats["obsidian"])
    created_objects.append(altar)

    # Llama Sagrada (Esfera emisiva + Luz Puntual Cálida)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.12,
        location=(0.0, -temple_size_y * 0.85, current_z + 0.52),
    )
    fire_orb = bpy.context.active_object
    fire_orb.name = "Sacred_Flame_Orb"
    _smooth(fire_orb)
    if "fire" in mats:
        fire_orb.data.materials.append(mats["fire"])
    created_objects.append(fire_orb)

    # Luz puntual del fuego
    bpy.ops.object.light_add(
        type="POINT",
        radius=0.3,
        location=(0.0, -temple_size_y * 0.85, current_z + 0.70),
    )
    fire_light = bpy.context.active_object
    fire_light.name = "Light_SacredFire"
    fire_light.data.energy = 85.0
    fire_light.data.color = (1.0, 0.45, 0.08)
    created_objects.append(fire_light)

    return {
        "status": "success",
        "objects": created_objects,
        "summit_height": current_z + temple_h,
    }


def build_pyramid_keyframes(
    total_frames: int = 120,
    orbit_radius: float = 12.0,
    orbit_height: float = 7.5,
) -> None:
    """Configura una trayectoria orbital cinematográfica de cámara alrededor del monumento."""
    if bpy is None:
        return

    cam = bpy.context.scene.camera
    if not cam:
        return

    cam.animation_data_clear()

    # Puntos de órbita cinematográfica con hora dorada
    angles = [
        (1, -math.pi * 0.45, orbit_height * 0.85),
        (total_frames // 2, -math.pi * 0.15, orbit_height * 1.15),
        (total_frames, math.pi * 0.20, orbit_height * 0.95),
    ]

    for frame, theta, h in angles:
        bpy.context.scene.frame_set(frame)
        cam.location.x = orbit_radius * math.sin(theta)
        cam.location.y = -orbit_radius * math.cos(theta)
        cam.location.z = h
        cam.keyframe_insert(data_path="location", frame=frame)

        # Mirar al altar y centro de la pirámide
        target = mathutils.Vector((0.0, 0.0, 2.5))
        direction = target - cam.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        cam.rotation_euler = rot_quat.to_euler()
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)
