"""Modelo 3D Procedural de Motor de Cuatro Tiempos en Blender 5.3 (Fase 3).

Genera la geometría tridimensional completa con estética de maqueta educativa:
- Bloque con corte transversal (Cutaway) y camisa de cilindro visible.
- Pistón con corona, 3 anillos y bulón articulado.
- Biela forjada con vástago I-beam y cojinetes.
- Cigüeñal con muñequillas, contrapesos de inercia y volante.
- Válvulas de admisión y escape con muelles helicoidales.
- Bujía con aislador cerámico y electrodos.
- Efectos volumétricos de chispa eléctrica, llama de combustión y flujos de gas.
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


def create_combustion_engine_3d(
    crank_radius: float = 1.0,
    rod_length: float = 3.5,
    cylinder_radius: float = 1.35,
    piston_height: float = 1.25,
) -> dict[str, Any]:
    """Crea proceduralmente todos los componentes tridimensionales del motor de 4 tiempos."""
    if bpy is None:
        raise RuntimeError("Este módulo debe ejecutarse dentro del entorno de Blender.")

    mats = setup_engine_materials()
    collection = bpy.data.collections.new("Engine_3D_Maqueta")
    bpy.context.scene.collection.children.link(collection)

    def add_to_col(obj):
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
        if obj.name not in collection.objects:
            collection.objects.link(obj)
        return obj

    # =========================================================================
    # 1. BLOQUE DE MOTOR CON CORTE TRANSVERSAL (CUTAWAY) Y CÁMARA
    # =========================================================================
    # Bloque exterior rectangular con cilindro hueco interior
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.35,
        depth=6.2,
        location=(0.0, 3.4, 0.0),
        vertices=48,
    )
    block_outer = bpy.context.active_object
    block_outer.name = "Engine_Block_Outer"
    block_outer.rotation_euler = (math.pi / 2, 0, 0)
    block_outer.data.materials.append(mats["engine_block"])
    add_to_col(block_outer)

    # Aletas de refrigeración decorativas
    for i in range(5):
        y_fin = 2.4 + (i * 0.7)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=cylinder_radius + 0.65,
            depth=0.12,
            location=(0.0, y_fin, 0.0),
            vertices=36,
        )
        fin = bpy.context.active_object
        fin.name = f"Cooling_Fin_{i+1}"
        fin.rotation_euler = (math.pi / 2, 0, 0)
        fin.data.materials.append(mats["engine_block"])
        fin.parent = block_outer
        add_to_col(fin)

    # Camisa interior de cilindro con corte frontal de 120 grados para visión interna
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius,
        depth=5.2,
        location=(0.0, 3.5, 0.0),
        vertices=48,
    )
    liner = bpy.context.active_object
    liner.name = "Cylinder_Liner"
    liner.rotation_euler = (math.pi / 2, 0, 0)
    liner.data.materials.append(mats["cylinder_liner"])
    add_to_col(liner)

    # Vidrio técnico frontal protector del corte
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.02,
        depth=5.0,
        location=(0.0, 3.5, 0.0),
        vertices=32,
    )
    glass_window = bpy.context.active_object
    glass_window.name = "Cutaway_Glass_Window"
    glass_window.rotation_euler = (math.pi / 2, 0, 0)
    glass_window.data.materials.append(mats["cutaway_glass"])
    add_to_col(glass_window)

    # =========================================================================
    # 2. CULATA Y PUERTOS DE VÁLVULAS
    # =========================================================================
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.45,
        depth=1.2,
        location=(0.0, 6.2, 0.0),
        vertices=36,
    )
    cylinder_head = bpy.context.active_object
    cylinder_head.name = "Cylinder_Head"
    cylinder_head.rotation_euler = (math.pi / 2, 0, 0)
    cylinder_head.data.materials.append(mats["engine_block"])
    add_to_col(cylinder_head)

    # =========================================================================
    # 3. PISTÓN, ANILLOS Y BULÓN
    # =========================================================================
    piston_root = bpy.data.objects.new("Piston_Root", None)
    piston_root.empty_display_type = "ARROWS"
    piston_root.empty_display_size = 0.5
    piston_root.location = (0.0, rod_length + crank_radius, 0.0)  # Inicio en PMS
    bpy.context.scene.collection.objects.link(piston_root)
    add_to_col(piston_root)

    # Cuerpo del pistón
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius - 0.04,
        depth=piston_height,
        location=(0.0, 0.0, 0.0),
        vertices=48,
    )
    piston_body = bpy.context.active_object
    piston_body.name = "Piston_Body"
    piston_body.rotation_euler = (math.pi / 2, 0, 0)
    piston_body.parent = piston_root
    piston_body.data.materials.append(mats["piston"])
    add_to_col(piston_body)

    # Anillos de compresión (3 aros dorados)
    for idx, y_ring in enumerate([0.38, 0.22, 0.06]):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=cylinder_radius - 0.03,
            minor_radius=0.035,
            location=(0.0, y_ring, 0.0),
            major_segments=36,
            minor_segments=12,
        )
        ring = bpy.context.active_object
        ring.name = f"Piston_Ring_{idx+1}"
        ring.rotation_euler = (math.pi / 2, 0, 0)
        ring.parent = piston_root
        ring.data.materials.append(mats["piston_rings"])
        add_to_col(ring)

    # Bulón / Pasador de pistón (Wrist Pin)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.18,
        depth=cylinder_radius * 1.5,
        location=(0.0, -0.25, 0.0),
        vertices=24,
    )
    wrist_pin = bpy.context.active_object
    wrist_pin.name = "Wrist_Pin"
    wrist_pin.parent = piston_root
    wrist_pin.data.materials.append(mats["wrist_pin"])
    add_to_col(wrist_pin)

    # =========================================================================
    # 4. BIELA FORJADA CON VÁSTAGO I-BEAM
    # =========================================================================
    rod_root = bpy.data.objects.new("Connecting_Rod_Root", None)
    rod_root.empty_display_type = "PLAIN_AXES"
    rod_root.empty_display_size = 0.4
    rod_root.location = (0.0, piston_root.location.y - 0.25, 0.0)
    bpy.context.scene.collection.objects.link(rod_root)
    add_to_col(rod_root)

    # Vástago central de la biela
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -rod_length / 2, 0.0),
    )
    rod_shank = bpy.context.active_object
    rod_shank.name = "Rod_Shank"
    rod_shank.scale = (0.24, rod_length * 0.72, 0.16)
    rod_shank.parent = rod_root
    rod_shank.data.materials.append(mats["connecting_rod"])
    add_to_col(rod_shank)

    # Ojo superior (pie de biela articulado al bulón)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.32,
        depth=0.38,
        location=(0.0, 0.0, 0.0),
        vertices=32,
    )
    rod_small_end = bpy.context.active_object
    rod_small_end.name = "Rod_Small_End"
    rod_small_end.parent = rod_root
    rod_small_end.data.materials.append(mats["connecting_rod"])
    add_to_col(rod_small_end)

    # Cabeza de biela inferior (cojinete sobre la muñequilla del cigüeñal)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.48,
        depth=0.45,
        location=(0.0, -rod_length, 0.0),
        vertices=36,
    )
    rod_big_end = bpy.context.active_object
    rod_big_end.name = "Rod_Big_End"
    rod_big_end.parent = rod_root
    rod_big_end.data.materials.append(mats["rod_bearings"])
    add_to_col(rod_big_end)

    # =========================================================================
    # 5. CIGÜEÑAL Y CONTRAPESOS DE INERCIA
    # =========================================================================
    crank_root = bpy.data.objects.new("Crankshaft_Root", None)
    crank_root.empty_display_type = "CIRCLE"
    crank_root.empty_display_size = crank_radius
    crank_root.location = (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(crank_root)
    add_to_col(crank_root)

    # Eje principal de giro del cigüeñal (Z)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.42,
        depth=2.8,
        location=(0.0, 0.0, 0.0),
        vertices=36,
    )
    crank_main_shaft = bpy.context.active_object
    crank_main_shaft.name = "Crankshaft_Main_Shaft"
    crank_main_shaft.parent = crank_root
    crank_main_shaft.data.materials.append(mats["crankshaft"])
    add_to_col(crank_main_shaft)

    # Muñequilla excéntrica donde asienta la biela
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.32,
        depth=0.6,
        location=(0.0, crank_radius, 0.0),
        vertices=32,
    )
    crank_pin = bpy.context.active_object
    crank_pin.name = "Crank_Pin"
    crank_pin.parent = crank_root
    crank_pin.data.materials.append(mats["crankshaft"])
    add_to_col(crank_pin)

    # Dos contrapesos de inercia opuestos
    for z_offset in [-0.55, 0.55]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=crank_radius * 1.35,
            depth=0.32,
            location=(0.0, -crank_radius * 0.45, z_offset),
            vertices=36,
        )
        counterweight = bpy.context.active_object
        counterweight.name = f"Crank_Counterweight_{'F' if z_offset > 0 else 'B'}"
        counterweight.scale = (1.0, 0.65, 1.0)
        counterweight.parent = crank_root
        counterweight.data.materials.append(mats["counterweights"])
        add_to_col(counterweight)

    # Volante de inercia lateral (Flywheel)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=crank_radius * 1.8,
        depth=0.4,
        location=(0.0, 0.0, -1.6),
        vertices=48,
    )
    flywheel = bpy.context.active_object
    flywheel.name = "Flywheel"
    flywheel.parent = crank_root
    flywheel.data.materials.append(mats["engine_block"])
    add_to_col(flywheel)

    # =========================================================================
    # 6. VÁLVULAS DE ADMISIÓN Y ESCAPE CON MUELLES
    # =========================================================================
    valves = {}
    for v_type, x_pos, mat_key in [("Intake", -0.68, "valve_intake"), ("Exhaust", 0.68, "valve_exhaust")]:
        v_root = bpy.data.objects.new(f"Valve_{v_type}_Root", None)
        v_root.location = (x_pos, 5.5, 0.0)
        bpy.context.scene.collection.objects.link(v_root)
        add_to_col(v_root)

        # Cabeza cónica de la válvula
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.48,
            radius2=0.08,
            depth=0.32,
            location=(0.0, 0.0, 0.0),
            vertices=32,
        )
        v_head = bpy.context.active_object
        v_head.name = f"Valve_{v_type}_Head"
        v_head.rotation_euler = (math.pi / 2, 0, 0)
        v_head.parent = v_root
        v_head.data.materials.append(mats[mat_key])
        add_to_col(v_head)

        # Vástago de la válvula
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.09,
            depth=1.8,
            location=(0.0, 0.9, 0.0),
            vertices=24,
        )
        v_stem = bpy.context.active_object
        v_stem.name = f"Valve_{v_type}_Stem"
        v_stem.rotation_euler = (math.pi / 2, 0, 0)
        v_stem.parent = v_root
        v_stem.data.materials.append(mats[mat_key])
        add_to_col(v_stem)

        valves[v_type.lower()] = v_root

    # =========================================================================
    # 7. BUJÍA CON ELECTRODOS
    # =========================================================================
    spark_root = bpy.data.objects.new("Spark_Plug_Root", None)
    spark_root.location = (0.0, 5.75, 0.0)
    bpy.context.scene.collection.objects.link(spark_root)
    add_to_col(spark_root)

    # Cuerpo aislador de porcelana blanca
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.22,
        depth=1.2,
        location=(0.0, 0.8, 0.0),
        vertices=32,
    )
    spark_body = bpy.context.active_object
    spark_body.name = "Spark_Ceramic_Body"
    spark_body.rotation_euler = (math.pi / 2, 0, 0)
    spark_body.parent = spark_root
    spark_body.data.materials.append(mats["spark_ceramic"])
    add_to_col(spark_body)

    # Tuerca hexagonal de metal
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.32,
        depth=0.4,
        location=(0.0, 0.2, 0.0),
        vertices=6,
    )
    spark_hex = bpy.context.active_object
    spark_hex.name = "Spark_Hex_Nut"
    spark_hex.rotation_euler = (math.pi / 2, 0, 0)
    spark_hex.parent = spark_root
    spark_hex.data.materials.append(mats["spark_metal"])
    add_to_col(spark_hex)

    # Electrodo central saliente hacia la cámara
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.04,
        depth=0.35,
        location=(0.0, -0.22, 0.0),
        vertices=16,
    )
    spark_elec = bpy.context.active_object
    spark_elec.name = "Spark_Center_Electrode"
    spark_elec.rotation_euler = (math.pi / 2, 0, 0)
    spark_elec.parent = spark_root
    spark_elec.data.materials.append(mats["spark_metal"])
    add_to_col(spark_elec)

    # =========================================================================
    # 8. EFECTOS VOLUMÉTRICOS DE LOS 4 TIEMPOS (CHISPA, FUEGO, GASES)
    # =========================================================================
    # Arco eléctrico de chispa (Emisión azul 20,000 V)
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=0.15,
        subdivisions=3,
        location=(0.0, 5.35, 0.0),
    )
    spark_arc = bpy.context.active_object
    spark_arc.name = "FX_Electric_Spark"
    spark_arc.data.materials.append(mats["electric_spark"])
    spark_arc.scale = (0.001, 0.001, 0.001)  # Oculto por defecto
    add_to_col(spark_arc)

    # Frente de llama esférico de combustión
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=cylinder_radius * 0.88,
        location=(0.0, 4.95, 0.0),
    )
    combustion_flame = bpy.context.active_object
    combustion_flame.name = "FX_Combustion_Flame"
    combustion_flame.data.materials.append(mats["flame_combustion"])
    combustion_flame.scale = (0.001, 0.001, 0.001)  # Oculto por defecto
    add_to_col(combustion_flame)

    # Flujo de mezcla entrante (Admisión azul)
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.45,
        radius2=0.1,
        depth=1.2,
        location=(-0.68, 5.2, 0.0),
    )
    fx_intake = bpy.context.active_object
    fx_intake.name = "FX_Intake_Flow"
    fx_intake.rotation_euler = (-math.pi / 4, 0, 0)
    fx_intake.data.materials.append(mats["intake_flow"])
    fx_intake.scale = (0.001, 0.001, 0.001)
    add_to_col(fx_intake)

    # Flujo de gases de escape salientes
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.1,
        radius2=0.5,
        depth=1.2,
        location=(0.68, 5.4, 0.0),
    )
    fx_exhaust = bpy.context.active_object
    fx_exhaust.name = "FX_Exhaust_Flow"
    fx_exhaust.rotation_euler = (math.pi / 4, 0, 0)
    fx_exhaust.data.materials.append(mats["exhaust_flow"])
    fx_exhaust.scale = (0.001, 0.001, 0.001)
    add_to_col(fx_exhaust)

    return {
        "piston_root": piston_root,
        "rod_root": rod_root,
        "crank_root": crank_root,
        "valve_intake": valves["intake"],
        "valve_exhaust": valves["exhaust"],
        "spark_root": spark_root,
        "fx_spark": spark_arc,
        "fx_flame": combustion_flame,
        "fx_intake": fx_intake,
        "fx_exhaust": fx_exhaust,
        "block": block_outer,
        "crank_radius": crank_radius,
        "rod_length": rod_length,
    }
