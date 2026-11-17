"""Modelo 3D Procedural de Motor de Cuatro Tiempos en Blender 5.3 (Fase 2 - Perfeccionamiento).

Estética de Maqueta Educativa Estilizada (Stylized Technical Model):
- Proporciones mecánicas coherentes y reconocibles de ingeniería.
- Bloque con corte transversal limpio (Cutaway) y bordes biselados.
- Pistón detallado con falda, 3 anillos y bulón articulado.
- Biela forjada con sección I-beam, casquillos de bronce, sombrerete y tornillos.
- Cigüeñal con contrapesos biselados, muñequilla concéntrica y volante de inercia.
- Válvulas con platillo cónico, vástagos guiados y resortes helicoidales.
- Bujía con cuerpo cerámico estriado y electrodos.
- Conductos de admisión y escape con indicadores de flujo y chispa/llama de combustión.
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
    crank_center_z: float = 0.4,
) -> dict[str, Any]:
    """Crea proceduralmente todos los componentes mecánicos con proporciones exactas."""
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
        # Suavizado de normales estilizado para maqueta sin polígonos facetados
        if hasattr(obj, "data") and hasattr(obj.data, "shade_smooth"):
            try:
                obj.data.shade_smooth()
            except Exception:
                pass
        return obj

    # =========================================================================
    # 1. BLOQUE DE MOTOR CON CORTE TRANSVERSAL TÉCNICO (CUTAWAY)
    # =========================================================================
    # Bloque exterior vertical (Z es UP)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.40,
        depth=5.6,
        location=(0.0, 0.0, 3.4),
        vertices=48,
    )
    block_outer = bpy.context.active_object
    block_outer.name = "Engine_Block_Outer"
    block_outer.data.materials.append(mats["engine_block"])
    add_to_col(block_outer)

    # Aletas de refrigeración envolventes
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

    # Cortador booleano frontal (Cutter que remueve Y < 0.15 para vista interna abierta)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -1.8, 3.4))
    cutter = bpy.context.active_object
    cutter.name = "Cutaway_Cutter"
    cutter.scale = (5.2, 3.6, 6.6)

    mod_b = block_outer.modifiers.new(name="Cutaway_Block", type="BOOLEAN")
    mod_b.object = cutter
    mod_b.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = block_outer
    bpy.ops.object.modifier_apply(modifier="Cutaway_Block")

    for fin_obj in cooling_fins:
        mod_f = fin_obj.modifiers.new(name="Cutaway_Fin", type="BOOLEAN")
        mod_f.object = cutter
        mod_f.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = fin_obj
        bpy.ops.object.modifier_apply(modifier="Cutaway_Fin")

    bpy.data.objects.remove(cutter, do_unlink=True)

    # Camisa interior del cilindro (acero satinado con corte frontal)
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
    cutter_l = bpy.context.active_object
    cutter_l.scale = (5.2, 3.6, 6.0)
    mod_l = liner.modifiers.new(name="Cutaway_Liner", type="BOOLEAN")
    mod_l.object = cutter_l
    mod_l.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = liner
    bpy.ops.object.modifier_apply(modifier="Cutaway_Liner")
    bpy.data.objects.remove(cutter_l, do_unlink=True)

    # Bancada inferior del cárter (soporte para cigüeñal en Z=0.4)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.5, 0.4),
    )
    crankcase_back = bpy.context.active_object
    crankcase_back.name = "Crankcase_Housing"
    crankcase_back.scale = (3.2, 1.2, 1.8)
    crankcase_back.data.materials.append(mats["engine_block"])
    add_to_col(crankcase_back)

    # =========================================================================
    # 2. CULATA, CÁMARA Y CONDUCTOS DE ADMISIÓN / ESCAPE
    # =========================================================================
    cylinder_head = bpy.data.objects.new("Cylinder_Head_Root", None)
    cylinder_head.location = (0.0, 0.0, 6.1)
    bpy.context.scene.collection.objects.link(cylinder_head)
    add_to_col(cylinder_head)

    # Bloque de culata
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius + 0.45,
        depth=0.9,
        location=(0.0, 0.0, 0.0),
        vertices=36,
    )
    c_head_mesh = bpy.context.active_object
    c_head_mesh.name = "Cylinder_Head_Mesh"
    c_head_mesh.parent = cylinder_head
    c_head_mesh.data.materials.append(mats["engine_block"])
    add_to_col(c_head_mesh)

    # Conducto de admisión (curvado hacia la izquierda)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.38,
        depth=1.1,
        location=(-1.1, 0.0, -0.1),
        vertices=24,
    )
    port_in = bpy.context.active_object
    port_in.name = "Intake_Port_Duct"
    port_in.rotation_euler = (0.0, math.radians(45), 0.0)
    port_in.parent = cylinder_head
    port_in.data.materials.append(mats["cutaway_rim"])
    add_to_col(port_in)

    # Conducto de escape (curvado hacia la derecha)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.38,
        depth=1.1,
        location=(1.1, 0.0, -0.1),
        vertices=24,
    )
    port_ex = bpy.context.active_object
    port_ex.name = "Exhaust_Port_Duct"
    port_ex.rotation_euler = (0.0, math.radians(-45), 0.0)
    port_ex.parent = cylinder_head
    port_ex.data.materials.append(mats["cutaway_rim"])
    add_to_col(port_ex)

    # =========================================================================
    # 3. PISTÓN DETALLADO (ALUMINIO SATINADO, 3 ANILLOS Y BULÓN)
    # =========================================================================
    piston_root = bpy.data.objects.new("Piston_Root", None)
    piston_root.empty_display_type = "ARROWS"
    piston_root.empty_display_size = 0.5
    # En PMS inicial: crank_center_z + crank_radius + rod_length
    initial_piston_z = crank_center_z + crank_radius + rod_length
    piston_root.location = (0.0, 0.0, initial_piston_z)
    bpy.context.scene.collection.objects.link(piston_root)
    add_to_col(piston_root)

    # Corona y falda del pistón
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

    # Rebaje interior de la falda para alivianar y alojar la biela
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cylinder_radius - 0.22,
        depth=piston_height * 0.75,
        location=(0.0, 0.0, -0.22),
        vertices=32,
    )
    skirt_cut = bpy.context.active_object
    mod_p = piston_body.modifiers.new(name="Piston_Cavity", type="BOOLEAN")
    mod_p.object = skirt_cut
    mod_p.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = piston_body
    bpy.ops.object.modifier_apply(modifier="Piston_Cavity")
    bpy.data.objects.remove(skirt_cut, do_unlink=True)

    # 3 Anillos de compresión dorados
    for idx, z_ring in enumerate([0.38, 0.20, 0.02]):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=cylinder_radius - 0.03,
            minor_radius=0.032,
            location=(0.0, 0.0, z_ring),
            major_segments=36,
            minor_segments=12,
        )
        ring = bpy.context.active_object
        ring.name = f"Piston_Ring_{idx+1}"
        ring.parent = piston_root
        ring.data.materials.append(mats["piston_rings"])
        add_to_col(ring)

    # Bulón del pistón (Wrist Pin horizontal a lo largo del eje Y en Z=0.0)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.18,
        depth=cylinder_radius * 1.5,
        location=(0.0, 0.0, 0.0),
        vertices=24,
    )
    wrist_pin = bpy.context.active_object
    wrist_pin.name = "Piston_Wrist_Pin"
    wrist_pin.rotation_euler = (math.pi / 2, 0, 0)
    wrist_pin.parent = piston_root
    wrist_pin.data.materials.append(mats["wrist_pin"])
    add_to_col(wrist_pin)

    # =========================================================================
    # 4. BIELA FORJADA I-BEAM (CON SOMBRERETE Y TORNILLOS)
    # =========================================================================
    rod_root = bpy.data.objects.new("Connecting_Rod_Root", None)
    rod_root.empty_display_type = "PLAIN_AXES"
    # El origen de la biela se ancla en la muñequilla (Big End)
    rod_root.location = (0.0, 0.0, crank_center_z + crank_radius)
    bpy.context.scene.collection.objects.link(rod_root)
    add_to_col(rod_root)

    # Cuerpo principal en perfil I-beam
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, rod_length / 2),
    )
    rod_body = bpy.context.active_object
    rod_body.name = "Rod_IBeam_Body"
    rod_body.scale = (0.34, 0.24, rod_length * 0.82)
    rod_body.parent = rod_root
    rod_body.data.materials.append(mats["connecting_rod"])
    add_to_col(rod_body)

    # Pie de biela superior (Small End) con buje de bronce acoplado al bulón
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.28,
        depth=0.36,
        location=(0.0, 0.0, rod_length),
        vertices=24,
    )
    small_end = bpy.context.active_object
    small_end.name = "Rod_Small_End"
    small_end.rotation_euler = (math.pi / 2, 0, 0)
    small_end.parent = rod_root
    small_end.data.materials.append(mats["rod_bearings"])
    add_to_col(small_end)

    # Cabeza de biela inferior (Big End) que rodea concéntricamente la muñequilla
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.38,
        depth=0.40,
        location=(0.0, 0.0, 0.0),
        vertices=32,
    )
    big_end = bpy.context.active_object
    big_end.name = "Rod_Big_End"
    big_end.rotation_euler = (math.pi / 2, 0, 0)
    big_end.parent = rod_root
    big_end.data.materials.append(mats["rod_bearings"])
    add_to_col(big_end)

    # Sombrerete inferior de biela (Rod Cap) con tornillos de fijación
    for x_bolt in [-0.26, 0.26]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.06,
            depth=0.48,
            location=(x_bolt, 0.0, -0.12),
            vertices=12,
        )
        bolt = bpy.context.active_object
        bolt.name = f"Rod_Bolt_{'L' if x_bolt < 0 else 'R'}"
        bolt.parent = rod_root
        bolt.data.materials.append(mats["rod_bolts"])
        add_to_col(bolt)

    # =========================================================================
    # 5. CIGÜEÑAL CON CONTRAPESOS BISELADOS Y VOLANTE DE INERCIA
    # =========================================================================
    crank_root = bpy.data.objects.new("Crankshaft_Root", None)
    crank_root.empty_display_type = "SINGLE_ARROW"
    crank_root.location = (0.0, 0.0, crank_center_z)
    bpy.context.scene.collection.objects.link(crank_root)
    add_to_col(crank_root)

    # Eje principal de giro (Main Journal alineado a lo largo del eje Y)
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

    # Muñequilla descentrada (Crank Pin exactamente a distancia crank_radius en +Z relativo)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.24,
        depth=0.46,
        location=(0.0, 0.0, crank_radius),
        vertices=32,
    )
    crank_pin = bpy.context.active_object
    crank_pin.name = "Crank_Pin_Offset"
    crank_pin.rotation_euler = (math.pi / 2, 0, 0)
    crank_pin.parent = crank_root
    crank_pin.data.materials.append(mats["crankshaft"])
    add_to_col(crank_pin)

    # Contrapeso frontal con chaflán biselado en forma de sector
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.25,
        depth=0.22,
        location=(0.0, -0.22, -0.32),
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
        radius=1.25,
        depth=0.22,
        location=(0.0, 0.22, -0.32),
        vertices=36,
    )
    c_weight_b = bpy.context.active_object
    c_weight_b.name = "Crank_Counterweight_B"
    c_weight_b.rotation_euler = (math.pi / 2, 0, 0)
    c_weight_b.parent = crank_root
    c_weight_b.data.materials.append(mats["counterweights"])
    add_to_col(c_weight_b)

    # Volante de inercia trasero (Flywheel) con escala de calado
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.65,
        depth=0.26,
        location=(0.0, 0.95, 0.0),
        vertices=48,
    )
    flywheel = bpy.context.active_object
    flywheel.name = "Engine_Flywheel"
    flywheel.rotation_euler = (math.pi / 2, 0, 0)
    flywheel.parent = crank_root
    flywheel.data.materials.append(mats["flywheel"])
    add_to_col(flywheel)

    # =========================================================================
    # 6. VÁLVULAS CON PLATILLO CÓNICO, GUÍAS Y RESORTES HELICOIDALES
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

        # Platillo cónico sellante de la válvula
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.48,
            radius2=0.10,
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
            depth=1.35,
            location=(0.0, 0.0, 0.68),
            vertices=16,
        )
        v_stem = bpy.context.active_object
        v_stem.name = f"Valve_{v_type}_Stem"
        v_stem.parent = v_root
        v_stem.data.materials.append(mats["wrist_pin"])
        add_to_col(v_stem)

        # Muelle helicoidal estilizado (espiral cilíndrica)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.22,
            depth=0.72,
            location=(0.0, 0.0, 0.68),
            vertices=24,
        )
        v_spring = bpy.context.active_object
        v_spring.name = f"Valve_{v_type}_Spring"
        v_spring.parent = v_root
        v_spring.data.materials.append(mats["valve_spring"])
        add_to_col(v_spring)

        # Platillo de retención superior del muelle
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.26,
            depth=0.08,
            location=(0.0, 0.0, 1.05),
            vertices=24,
        )
        v_retainer = bpy.context.active_object
        v_retainer.name = f"Valve_{v_type}_Retainer"
        v_retainer.parent = v_root
        v_retainer.data.materials.append(mats["rod_bolts"])
        add_to_col(v_retainer)

        valves[v_type] = v_root

    # =========================================================================
    # 7. BUJÍA CENTRAL DETALLADA (Z = 6.2)
    # =========================================================================
    spark_root = bpy.data.objects.new("Spark_Plug_Root", None)
    spark_root.location = (0.0, 0.0, 6.2)
    bpy.context.scene.collection.objects.link(spark_root)
    add_to_col(spark_root)

    # Aislador cerámico blanco puro estriado
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

    # Tuerca hexagonal de montaje en acero
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

    # Electrodo central y de masa
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.05,
        depth=0.45,
        location=(0.0, 0.0, -0.42),
        vertices=12,
    )
    electrode = bpy.context.active_object
    electrode.name = "Spark_Electrode"
    electrode.parent = spark_root
    electrode.data.materials.append(mats["spark_metal"])
    add_to_col(electrode)

    # =========================================================================
    # 8. EFECTOS VOLUMÉTRICOS DE CHISPA, LLAMA Y FLUJOS DE GAS (Punto 6)
    # =========================================================================
    # Chispa eléctrica (emisión cian 25V)
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
        radius=cylinder_radius * 0.90,
        location=(0.0, 0.0, 5.05),
    )
    combustion_flame = bpy.context.active_object
    combustion_flame.name = "FX_Combustion_Flame"
    combustion_flame.data.materials.append(mats["flame_combustion"])
    combustion_flame.scale = (0.001, 0.001, 0.001)
    add_to_col(combustion_flame)

    # Indicador de flujo de mezcla fresca (Admisión cian)
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.42,
        radius2=0.08,
        depth=1.1,
        location=(-0.65, 0.0, 5.3),
    )
    fx_intake = bpy.context.active_object
    fx_intake.name = "FX_Intake_Flow"
    fx_intake.rotation_euler = (0.0, math.radians(-35), 0.0)
    fx_intake.data.materials.append(mats["intake_flow"])
    fx_intake.scale = (0.001, 0.001, 0.001)
    add_to_col(fx_intake)

    # Indicador de flujo de gases quemados (Escape naranja)
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.08,
        radius2=0.42,
        depth=1.1,
        location=(0.65, 0.0, 5.3),
    )
    fx_exhaust = bpy.context.active_object
    fx_exhaust.name = "FX_Exhaust_Flow"
    fx_exhaust.rotation_euler = (0.0, math.radians(35), 0.0)
    fx_exhaust.data.materials.append(mats["exhaust_flow"])
    fx_exhaust.scale = (0.001, 0.001, 0.001)
    add_to_col(fx_exhaust)

    # Suelo de estudio de maqueta suave
    bpy.ops.mesh.primitive_plane_add(
        size=45.0,
        location=(0.0, 0.0, -0.65),
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
        "fx_intake": fx_intake,
        "fx_exhaust": fx_exhaust,
        "block": block_outer,
        "crank_radius": crank_radius,
        "rod_length": rod_length,
        "crank_center_z": crank_center_z,
    }
