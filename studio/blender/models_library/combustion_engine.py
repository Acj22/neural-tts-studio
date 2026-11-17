"""Modelo 3D Procedural de Motor de Cuatro Tiempos en Blender 5.3 (Fase 3).

Genera la maqueta tridimensional orientada verticalmente (Z es UP):
- Bloque con CORTE TRANSVERSAL REAL (Cutaway) que expone el interior.
- Aletas de refrigeración estilizadas con corte visible.
- Camisa de cilindro pulida con vista en sección.
- Pistón con 3 anillos dorados, bulón y falda hueca.
- Biela forjada articulada conectando muñequilla a pistón.
- Cigüeñal con muñón descentrado, contrapesos y volante de inercia.
- Válvulas de admisión (cian) y escape (naranja) con muelles helicoidales.
- Bujía con aislador cerámico y electrodo central.
- Efectos volumétricos de chispa 20kV, flama de ignición y flujos de gas.
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
    # 1. BLOQUE DE MOTOR CON CORTE FRONTAL (CUTAWAY REAL)
    # =========================================================================
    # Cilindro vertical exterior del bloque
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.38,
        depth=5.8,
        location=(0.0, 0.0, 3.4),
        vertices=48,
    )
    block_outer = bpy.context.active_object
    block_outer.name = "Engine_Block_Outer"
    block_outer.data.materials.append(mats["engine_block"])
    add_to_col(block_outer)

    # Aletas de refrigeración decorativas
    cooling_fins = []
    for i in range(5):
        z_fin = 1.9 + (i * 0.72)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=cylinder_radius + 0.72,
            depth=0.10,
            location=(0.0, 0.0, z_fin),
            vertices=36,
        )
        fin = bpy.context.active_object
        fin.name = f"Cooling_Fin_{i+1}"
        fin.data.materials.append(mats["engine_block"])
        fin.parent = block_outer
        cooling_fins.append(fin)
        add_to_col(fin)

    # Cortador booleano (Cutter) para remover la mitad frontal (Y < 0.15)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -1.8, 3.4))
    cutter = bpy.context.active_object
    cutter.name = "Cutaway_Cutter"
    cutter.scale = (5.0, 3.6, 6.8)

    # Aplicar corte al bloque principal
    mod_b = block_outer.modifiers.new(name="Cutaway_Block", type="BOOLEAN")
    mod_b.object = cutter
    mod_b.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = block_outer
    bpy.ops.object.modifier_apply(modifier="Cutaway_Block")

    # Aplicar corte a cada aleta
    for fin_obj in cooling_fins:
        mod_f = fin_obj.modifiers.new(name="Cutaway_Fin", type="BOOLEAN")
        mod_f.object = cutter
        mod_f.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = fin_obj
        bpy.ops.object.modifier_apply(modifier="Cutaway_Fin")

    # Eliminar cutter temporal
    bpy.data.objects.remove(cutter, do_unlink=True)

    # Camisa interior de cilindro con corte frontal para visualización limpia
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius,
        depth=5.2,
        location=(0.0, 0.0, 3.5),
        vertices=48,
    )
    liner = bpy.context.active_object
    liner.name = "Cylinder_Liner"
    liner.data.materials.append(mats["cylinder_liner"])
    add_to_col(liner)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -1.8, 3.5))
    cutter_liner = bpy.context.active_object
    cutter_liner.scale = (5.0, 3.6, 6.0)
    mod_l = liner.modifiers.new(name="Cutaway_Liner", type="BOOLEAN")
    mod_l.object = cutter_liner
    mod_l.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = liner
    bpy.ops.object.modifier_apply(modifier="Cutaway_Liner")
    bpy.data.objects.remove(cutter_liner, do_unlink=True)

    # =========================================================================
    # 2. CULATA Y TAPA SUPERIOR
    # =========================================================================
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.45,
        depth=0.9,
        location=(0.0, 0.0, 6.15),
        vertices=36,
    )
    cylinder_head = bpy.context.active_object
    cylinder_head.name = "Cylinder_Head"
    cylinder_head.data.materials.append(mats["engine_block"])
    add_to_col(cylinder_head)

    # =========================================================================
    # 3. PISTÓN, ANILLOS Y BULÓN ARTICULADO
    # =========================================================================
    piston_root = bpy.data.objects.new("Piston_Root", None)
    piston_root.empty_display_type = "ARROWS"
    piston_root.empty_display_size = 0.5
    piston_root.location = (0.0, 0.0, rod_length + crank_radius + 0.4)
    bpy.context.scene.collection.objects.link(piston_root)
    add_to_col(piston_root)

    # Cuerpo del pistón (cilindro plateado brillante)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius - 0.04,
        depth=piston_height,
        location=(0.0, 0.0, 0.0),
        vertices=48,
    )
    piston_body = bpy.context.active_object
    piston_body.name = "Piston_Body"
    piston_body.parent = piston_root
    piston_body.data.materials.append(mats["piston"])
    add_to_col(piston_body)

    # 3 Anillos de compresión dorados
    for idx, z_ring in enumerate([0.38, 0.20, 0.02]):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=cylinder_radius - 0.03,
            minor_radius=0.035,
            location=(0.0, 0.0, z_ring),
            major_segments=36,
            minor_segments=12,
        )
        ring = bpy.context.active_object
        ring.name = f"Piston_Ring_{idx+1}"
        ring.parent = piston_root
        ring.data.materials.append(mats["piston_rings"])
        add_to_col(ring)

    # Bulón del pistón (Wrist Pin horizontal a lo largo del eje Y)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.18,
        depth=cylinder_radius * 1.5,
        location=(0.0, 0.0, -0.25),
        vertices=24,
    )
    wrist_pin = bpy.context.active_object
    wrist_pin.name = "Piston_Wrist_Pin"
    wrist_pin.rotation_euler = (math.pi / 2, 0, 0)
    wrist_pin.parent = piston_root
    wrist_pin.data.materials.append(mats["wrist_pin"])
    add_to_col(wrist_pin)

    # =========================================================================
    # 4. BIELA FORJADA CON VÁSTAGO I-BEAM
    # =========================================================================
    rod_root = bpy.data.objects.new("Connecting_Rod_Root", None)
    rod_root.empty_display_type = "PLAIN_AXES"
    rod_root.location = (0.0, 0.0, 0.4 + crank_radius)
    bpy.context.scene.collection.objects.link(rod_root)
    add_to_col(rod_root)

    # Cuerpo principal de la biela
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, rod_length / 2),
    )
    rod_body = bpy.context.active_object
    rod_body.name = "Rod_IBeam_Body"
    rod_body.scale = (0.32, 0.28, rod_length * 0.85)
    rod_body.parent = rod_root
    rod_body.data.materials.append(mats["connecting_rod"])
    add_to_col(rod_body)

    # Cabeza de biela inferior (Big End cojinete)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.38,
        depth=0.36,
        location=(0.0, 0.0, 0.0),
        vertices=32,
    )
    big_end = bpy.context.active_object
    big_end.name = "Rod_Big_End"
    big_end.rotation_euler = (math.pi / 2, 0, 0)
    big_end.parent = rod_root
    big_end.data.materials.append(mats["rod_bearings"])
    add_to_col(big_end)

    # Pie de biela superior (Small End)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.28,
        depth=0.32,
        location=(0.0, 0.0, rod_length),
        vertices=24,
    )
    small_end = bpy.context.active_object
    small_end.name = "Rod_Small_End"
    small_end.rotation_euler = (math.pi / 2, 0, 0)
    small_end.parent = rod_root
    small_end.data.materials.append(mats["rod_bearings"])
    add_to_col(small_end)

    # =========================================================================
    # 5. CIGÜEÑAL Y CONTRAPESOS ROTATIVOS (Giro alrededor del eje Y en Z=0.4)
    # =========================================================================
    crank_root = bpy.data.objects.new("Crankshaft_Root", None)
    crank_root.empty_display_type = "SINGLE_ARROW"
    crank_root.location = (0.0, 0.0, 0.4)
    bpy.context.scene.collection.objects.link(crank_root)
    add_to_col(crank_root)

    # Eje principal de bancada
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.32,
        depth=2.2,
        location=(0.0, 0.0, 0.0),
        vertices=32,
    )
    main_journal = bpy.context.active_object
    main_journal.name = "Crank_Main_Journal"
    main_journal.rotation_euler = (math.pi / 2, 0, 0)
    main_journal.parent = crank_root
    main_journal.data.materials.append(mats["crankshaft"])
    add_to_col(main_journal)

    # Muñequilla descentrada (Crank Pin a distancia crank_radius en +Z)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.24,
        depth=0.48,
        location=(0.0, 0.0, crank_radius),
        vertices=32,
    )
    crank_pin = bpy.context.active_object
    crank_pin.name = "Crank_Pin_Offset"
    crank_pin.rotation_euler = (math.pi / 2, 0, 0)
    crank_pin.parent = crank_root
    crank_pin.data.materials.append(mats["crankshaft"])
    add_to_col(crank_pin)

    # Contrapeso frontal
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.2,
        depth=0.22,
        location=(0.0, -0.22, -0.3),
        vertices=36,
    )
    c_weight_f = bpy.context.active_object
    c_weight_f.name = "Crank_Counterweight_F"
    c_weight_f.rotation_euler = (math.pi / 2, 0, 0)
    c_weight_f.parent = crank_root
    c_weight_f.data.materials.append(mats["counterweights"])
    add_to_col(c_weight_f)

    # Contrapeso trasero
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.2,
        depth=0.22,
        location=(0.0, 0.22, -0.3),
        vertices=36,
    )
    c_weight_b = bpy.context.active_object
    c_weight_b.name = "Crank_Counterweight_B"
    c_weight_b.rotation_euler = (math.pi / 2, 0, 0)
    c_weight_b.parent = crank_root
    c_weight_b.data.materials.append(mats["counterweights"])
    add_to_col(c_weight_b)

    # Volante de inercia trasero
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.65,
        depth=0.28,
        location=(0.0, 0.95, 0.0),
        vertices=48,
    )
    flywheel = bpy.context.active_object
    flywheel.name = "Engine_Flywheel"
    flywheel.rotation_euler = (math.pi / 2, 0, 0)
    flywheel.parent = crank_root
    flywheel.data.materials.append(mats["counterweights"])
    add_to_col(flywheel)

    # =========================================================================
    # 6. VÁLVULAS DE ADMISIÓN Y ESCAPE (Cian y Naranja con Resortes)
    # =========================================================================
    valves = {}
    valve_configs = [
        ("intake", -0.58, mats["valve_intake"]),
        ("exhaust", 0.58, mats["valve_exhaust"]),
    ]

    for v_type, x_pos, v_mat in valve_configs:
        v_root = bpy.data.objects.new(f"Valve_{v_type.capitalize()}_Root", None)
        v_root.location = (x_pos, 0.0, 5.6)
        bpy.context.scene.collection.objects.link(v_root)
        add_to_col(v_root)

        # Cabeza cónica de la válvula
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.48,
            radius2=0.08,
            depth=0.22,
            location=(0.0, 0.0, 0.0),
            vertices=32,
        )
        v_head = bpy.context.active_object
        v_head.name = f"Valve_{v_type}_Head"
        v_head.parent = v_root
        v_head.data.materials.append(v_mat)
        add_to_col(v_head)

        # Vástago de la válvula
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.08,
            depth=1.3,
            location=(0.0, 0.0, 0.65),
            vertices=16,
        )
        v_stem = bpy.context.active_object
        v_stem.name = f"Valve_{v_type}_Stem"
        v_stem.parent = v_root
        v_stem.data.materials.append(mats["wrist_pin"])
        add_to_col(v_stem)

        # Muelle helicoidal
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.22,
            depth=0.75,
            location=(0.0, 0.0, 0.65),
            vertices=24,
        )
        v_spring = bpy.context.active_object
        v_spring.name = f"Valve_{v_type}_Spring"
        v_spring.parent = v_root
        v_spring.data.materials.append(mats["valve_spring"])
        add_to_col(v_spring)

        valves[v_type] = v_root

    # =========================================================================
    # 7. BUJÍA CENTRAL CON ELECTRODO (Z = 6.4)
    # =========================================================================
    spark_root = bpy.data.objects.new("Spark_Plug_Root", None)
    spark_root.location = (0.0, 0.0, 6.2)
    bpy.context.scene.collection.objects.link(spark_root)
    add_to_col(spark_root)

    # Aislador cerámico blanco
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.26,
        depth=1.3,
        location=(0.0, 0.0, 0.65),
        vertices=24,
    )
    ceramic = bpy.context.active_object
    ceramic.name = "Spark_Ceramic_Body"
    ceramic.parent = spark_root
    ceramic.data.materials.append(mats["spark_ceramic"])
    add_to_col(ceramic)

    # Tuerca hexagonal y rosca
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.34,
        depth=0.45,
        location=(0.0, 0.0, 0.1),
        vertices=6,
    )
    hex_nut = bpy.context.active_object
    hex_nut.name = "Spark_Hex_Nut"
    hex_nut.parent = spark_root
    hex_nut.data.materials.append(mats["spark_metal"])
    add_to_col(hex_nut)

    # Electrodo central proyectado a la cámara (Z = 5.3)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.06,
        depth=0.4,
        location=(0.0, 0.0, -0.4),
        vertices=12,
    )
    electrode = bpy.context.active_object
    electrode.name = "Spark_Electrode"
    electrode.parent = spark_root
    electrode.data.materials.append(mats["spark_metal"])
    add_to_col(electrode)

    # =========================================================================
    # 8. EFECTOS VOLUMÉTRICOS DE CHISPA Y LLAMA DE COMBUSTIÓN
    # =========================================================================
    # Chispa eléctrica
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=0.22,
        subdivisions=3,
        location=(0.0, 0.0, 5.35),
    )
    spark_arc = bpy.context.active_object
    spark_arc.name = "FX_Electric_Spark"
    spark_arc.data.materials.append(mats["electric_spark"])
    spark_arc.scale = (0.001, 0.001, 0.001)
    add_to_col(spark_arc)

    # Frente de llama esférico de combustión
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=cylinder_radius * 0.92,
        location=(0.0, 0.0, 5.1),
    )
    combustion_flame = bpy.context.active_object
    combustion_flame.name = "FX_Combustion_Flame"
    combustion_flame.data.materials.append(mats["flame_combustion"])
    combustion_flame.scale = (0.001, 0.001, 0.001)
    add_to_col(combustion_flame)

    # Suelo infinito de estudio
    bpy.ops.mesh.primitive_plane_add(
        size=40.0,
        location=(0.0, 0.0, -0.7),
    )
    floor = bpy.context.active_object
    floor.name = "Studio_Floor"
    floor.data.materials.append(mats["studio_floor"])
    add_to_col(floor)

    return {
        "piston_root": piston_root,
        "rod_root": rod_root,
        "crank_root": crank_root,
        "valve_intake": valves["intake"],
        "valve_exhaust": valves["exhaust"],
        "spark_root": spark_root,
        "cylinder_head": cylinder_head,
        "fx_spark": spark_arc,
        "fx_flame": combustion_flame,
        "block": block_outer,
        "crank_radius": crank_radius,
        "rod_length": rod_length,
    }
