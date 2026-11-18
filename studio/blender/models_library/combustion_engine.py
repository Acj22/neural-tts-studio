"""Modelo 3D Procedural de Motor de Cuatro Tiempos en Blender 5.3 (Fase 2.1 - Corrección y Perfeccionamiento).

Mejoras de la Fase 2.1:
- Proporciones revisadas: bloque más ancho y culata más gruesa, componentes bien diferenciados.
- Corte cutaway mejorado: solo la mitad frontal del bloque es removida para mantener estructura visible.
- Pistón con falda más larga y anillos bien espaciados, visibles en la vista de corte.
- Biela con cuerpo en sección I claramente visible y casquillos de bronce prominentes.
- Cigüeñal con muñequilla decentemente descentrada y contrapesos en sector circular.
- Válvulas con platillo plano (disco) claramente visible desde arriba y desde el frente.
- Separación de colores mejorada: pistón crema, biela grafito oscuro, cigüeñal azul vivo.
- Conductos de admisión/escape bien orientados (Z-arriba, 40° naturales desde culata).
- crank_center_z = 0.0 → cigüeñal en centro del cárter, todo el motor crece hacia +Z.
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


def _smooth(obj):
    """Aplica shading suave a la malla activa sin provocar errores en headless."""
    try:
        if obj and hasattr(obj, "data") and hasattr(obj.data, "polygons"):
            for poly in obj.data.polygons:
                poly.use_smooth = True
    except Exception:
        pass
    return obj


def create_combustion_engine_3d(
    crank_radius: float = 1.0,
    rod_length: float = 3.6,
    cylinder_radius: float = 1.30,
    piston_height: float = 1.40,
    crank_center_z: float = 0.0,
) -> dict[str, Any]:
    """Crea proceduralmente todos los componentes mecánicos con proporciones revisadas.

    Sistema de coordenadas (Fase 2.1):
      - Z es el eje vertical del cilindro (arriba = positivo).
      - Y es la profundidad (vista frontal: Y negativo = hacia el observador).
      - X es la horizontal del cigüeñal.
      - El cigüeñal rota alrededor del eje Y (eje de profundidad).
      - Crank_center_z = 0.0  → cigüeñal en el centro del cárter.
      - PMS del pistón ≈ crank_center_z + rod_length + crank_radius.
    """
    if bpy is None:
        raise RuntimeError("Este módulo debe ejecutarse dentro del entorno de Blender.")

    mats = setup_engine_materials()
    collection = bpy.data.collections.new("Engine_3D_v21")
    bpy.context.scene.collection.children.link(collection)

    def add(obj):
        """Agrega objeto a la colección del motor y aplica smooth shading."""
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
        if obj.name not in collection.objects:
            collection.objects.link(obj)
        _smooth(obj)
        return obj

    # =========================================================================
    # DIMENSIONES GLOBALES COHERENTES
    # =========================================================================
    cr = cylinder_radius            # radio interior del cilindro
    block_r = cr + 0.52             # radio exterior del bloque
    pms_z = crank_center_z + crank_radius + rod_length      # punto muerto superior del pistón
    block_top = pms_z + piston_height + 0.4                 # tope del cilindro (sobre PMS + culata)
    block_bottom = crank_center_z - 1.1                     # base del cárter
    block_height = block_top - block_bottom
    block_center_z = (block_top + block_bottom) / 2.0
    head_z = pms_z + piston_height * 0.5 + 0.3             # base inferior de la culata

    # =========================================================================
    # 1. BLOQUE EXTERIOR DEL MOTOR (Carcasa sólida tipo fundición con aletas)
    # =========================================================================
    block_w = cr * 3.4
    block_d = cr * 2.0
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, block_center_z),
    )
    block = bpy.context.active_object
    block.name = "Engine_Block"
    block.scale = (block_w, block_d, block_height)
    block.data.materials.append(mats["engine_block"])
    add(block)

    # Aletas de disipación / nervios de refuerzo
    fin_z_start = block_bottom + 0.8
    fin_z_end = block_top - 0.6
    for i in range(5):
        pct = i / 4.0
        z_fin_world = fin_z_start + pct * (fin_z_end - fin_z_start)
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, 0.0, z_fin_world),
        )
        fin = bpy.context.active_object
        fin.scale = (block_w + 0.35, block_d + 0.22, 0.13)
        fin.data.materials.append(mats["engine_block"])
        mod_uf = block.modifiers.new(f"UnionFin_{i}", type="BOOLEAN")
        mod_uf.object = fin
        mod_uf.operation = "UNION"
        bpy.context.view_layer.objects.active = block
        bpy.ops.object.modifier_apply(modifier=f"UnionFin_{i}")
        bpy.data.objects.remove(fin, do_unlink=True)

    # Vaciado interior del cilindro (Bore hueco)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr + 0.12,
        depth=block_height * 0.70,
        location=(0.0, 0.0, block_center_z + 0.8),
        vertices=48,
    )
    bore = bpy.context.active_object
    mod_bore = block.modifiers.new(name="Bore_Block", type="BOOLEAN")
    mod_bore.object = bore
    mod_bore.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = block
    bpy.ops.object.modifier_apply(modifier="Bore_Block")
    bpy.data.objects.remove(bore, do_unlink=True)

    # Cavidad inferior del cárter para giro del cigüeñal
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, crank_center_z + 0.35),
    )
    crank_cav = bpy.context.active_object
    crank_cav.scale = (cr * 2.6, block_d * 1.1, 3.4)
    mod_cc = block.modifiers.new(name="CrankCavity", type="BOOLEAN")
    mod_cc.object = crank_cav
    mod_cc.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = block
    bpy.ops.object.modifier_apply(modifier="CrankCavity")
    bpy.data.objects.remove(crank_cav, do_unlink=True)

    # Corte cutaway frontal (revela todo el mecanismo mecánico interior)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -block_d * 0.5, block_center_z),
    )
    cutter = bpy.context.active_object
    cutter.name = "Cutaway_Cutter"
    cutter.scale = (block_w * 1.3, block_d, block_height * 1.15)
    mod_b = block.modifiers.new(name="Cutaway_Block", type="BOOLEAN")
    mod_b.object = cutter
    mod_b.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = block
    bpy.ops.object.modifier_apply(modifier="Cutaway_Block")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # =========================================================================
    # 2. CAMISA INTERIOR DEL CILINDRO (Acero cromado satinado con corte frontal)
    # =========================================================================
    liner_height = rod_length + crank_radius + piston_height + 0.3
    liner_center_z = crank_center_z + liner_height / 2.0 + 0.15

    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr + 0.10,
        depth=liner_height,
        location=(0.0, 0.0, liner_center_z),
        vertices=48,
    )
    liner = bpy.context.active_object
    liner.name = "Cylinder_Liner"
    liner.data.materials.append(mats["cylinder_liner"])
    add(liner)

    # Vaciado de la camisa para que sea un tubo hueco
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr,
        depth=liner_height + 0.2,
        location=(0.0, 0.0, liner_center_z),
        vertices=48,
    )
    bore_l = bpy.context.active_object
    mod_bl = liner.modifiers.new(name="Bore_Liner", type="BOOLEAN")
    mod_bl.object = bore_l
    mod_bl.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = liner
    bpy.ops.object.modifier_apply(modifier="Bore_Liner")
    bpy.data.objects.remove(bore_l, do_unlink=True)

    # Corte de la mitad frontal de la camisa
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -(cr * 0.6 + 0.5), liner_center_z),
    )
    cutter_l = bpy.context.active_object
    cutter_l.scale = (cr * 2.8, cr * 1.6, liner_height * 1.1)
    mod_l = liner.modifiers.new(name="Cutaway_Liner", type="BOOLEAN")
    mod_l.object = cutter_l
    mod_l.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = liner
    bpy.ops.object.modifier_apply(modifier="Cutaway_Liner")
    bpy.data.objects.remove(cutter_l, do_unlink=True)

    # =========================================================================
    # 3. CULATA Y CONDUCTOS DE ADMISIÓN / ESCAPE
    # =========================================================================
    head_root = bpy.data.objects.new("Cylinder_Head_Root", None)
    head_root.empty_display_type = "PLAIN_AXES"
    head_root.location = (0.0, 0.0, head_z)
    bpy.context.scene.collection.objects.link(head_root)
    add(head_root)

    # Conducto de admisión izquierdo, 40° hacia arriba-izquierda
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.28,
        depth=1.3,
        location=(-0.75, 0.0, 0.55),
        vertices=24,
    )
    port_in = bpy.context.active_object
    port_in.name = "Intake_Port_Duct"
    port_in.rotation_euler = (0.0, math.radians(40), 0.0)
    port_in.parent = head_root
    port_in.data.materials.append(mats["valve_intake"])
    add(port_in)

    # Conducto de escape derecho, 40° hacia arriba-derecha
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.28,
        depth=1.3,
        location=(0.75, 0.0, 0.55),
        vertices=24,
    )
    port_ex = bpy.context.active_object
    port_ex.name = "Exhaust_Port_Duct"
    port_ex.rotation_euler = (0.0, math.radians(-40), 0.0)
    port_ex.parent = head_root
    port_ex.data.materials.append(mats["valve_exhaust"])
    add(port_ex)

    # =========================================================================
    # 5. PISTÓN AUTOMOTRIZ DE ALTA FIDELIDAD (ANILLOS, BULÓN FRONTAL, FALDA ARQUEADA)
    # =========================================================================
    piston_root = bpy.data.objects.new("Piston_Root", None)
    piston_root.empty_display_type = "ARROWS"
    piston_root.empty_display_size = 0.4
    piston_root.location = (0.0, 0.0, pms_z)
    bpy.context.scene.collection.objects.link(piston_root)
    add(piston_root)

    # Cuerpo del pistón: corona + falda con holgura exacta
    piston_rad = cr - 0.035
    bpy.ops.mesh.primitive_cylinder_add(
        radius=piston_rad,
        depth=piston_height,
        location=(0.0, 0.0, 0.0),
        vertices=48,
    )
    piston_body = bpy.context.active_object
    piston_body.name = "Piston_Body"
    piston_body.parent = piston_root
    piston_body.data.materials.append(mats["piston"])
    add(piston_body)

    # Recortes arqueados de la falda a los lados (-X y +X) para darle la silueta de pistón real
    for sx in [-cr * 0.88, cr * 0.88]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=cr * 0.54,
            depth=piston_height * 0.78,
            location=(sx, 0.0, -piston_height * 0.28),
            vertices=36,
        )
        cut_sk = bpy.context.active_object
        cut_sk.parent = piston_root
        msk = piston_body.modifiers.new("SkirtArch", type="BOOLEAN")
        msk.object = cut_sk
        msk.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = piston_body
        bpy.ops.object.modifier_apply(modifier="SkirtArch")
        bpy.data.objects.remove(cut_sk, do_unlink=True)

    # Rebaje interior en la cavidad de la falda
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr - 0.26,
        depth=piston_height * 0.65,
        location=(0.0, 0.0, -piston_height * 0.20),
        vertices=36,
    )
    skirt_cut = bpy.context.active_object
    skirt_cut.parent = piston_root
    mod_p = piston_body.modifiers.new(name="Piston_Cavity", type="BOOLEAN")
    mod_p.object = skirt_cut
    mod_p.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = piston_body
    bpy.ops.object.modifier_apply(modifier="Piston_Cavity")
    bpy.data.objects.remove(skirt_cut, do_unlink=True)

    # Orificio del bulón pasante visible en el frente
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.28,
        depth=cr * 2.0,
        location=(0.0, 0.0, 0.0),
        vertices=36,
    )
    ph = bpy.context.active_object
    ph.parent = piston_root
    ph.rotation_euler = (math.pi / 2, 0, 0)
    mph = piston_body.modifiers.new("PinHole", type="BOOLEAN")
    mph.object = ph
    mph.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = piston_body
    bpy.ops.object.modifier_apply(modifier="PinHole")
    bpy.data.objects.remove(ph, do_unlink=True)

    # Bulón de acero templado insertado en el orificio
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.25,
        depth=cr * 1.90,
        location=(0.0, 0.0, 0.0),
        vertices=36,
    )
    wrist_pin = bpy.context.active_object
    wrist_pin.name = "Piston_Wrist_Pin"
    wrist_pin.rotation_euler = (math.pi / 2, 0, 0)
    wrist_pin.parent = piston_root
    wrist_pin.data.materials.append(mats["wrist_pin"])
    add(wrist_pin)

    # 3 aros de compresión y aceite bien definidos
    ring_z_positions = [
        piston_height * 0.40,
        piston_height * 0.26,
        piston_height * 0.12,
    ]
    for idx, z_ring in enumerate(ring_z_positions):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=cr - 0.030,
            minor_radius=0.032,
            location=(0.0, 0.0, z_ring),
            major_segments=48,
            minor_segments=12,
        )
        ring = bpy.context.active_object
        ring.name = f"Piston_Ring_{idx+1}"
        ring.parent = piston_root
        ring.data.materials.append(mats["piston_rings"])
        add(ring)

    # =========================================================================
    # 6. BIELA FORJADA CON VIGA 'I', CASQUILLOS DE BRONCE Y PERNOS
    # =========================================================================
    crank_pin_z = crank_center_z + crank_radius

    rod_root = bpy.data.objects.new("Connecting_Rod_Root", None)
    rod_root.empty_display_type = "PLAIN_AXES"
    rod_root.location = (0.0, 0.0, crank_pin_z)
    bpy.context.scene.collection.objects.link(rod_root)
    add(rod_root)

    # Vástago principal de la biela
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, rod_length * 0.5),
    )
    rod_body = bpy.context.active_object
    rod_body.name = "Rod_IBeam_Body"
    rod_body.scale = (0.35, 0.24, rod_length * 0.74)
    rod_body.parent = rod_root
    rod_body.data.materials.append(mats["connecting_rod"])
    add(rod_body)

    # Canal en I forjado por ambos lados
    for r_y in [-0.09, 0.09]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, r_y, rod_length * 0.5),
        )
        rec = bpy.context.active_object
        rec.name = f"Rod_Recess_{'F' if r_y < 0 else 'B'}"
        rec.scale = (0.20, 0.10, rod_length * 0.66)
        rec.parent = rod_root
        rec.data.materials.append(mats["rod_recess"])
        add(rec)

    # Small end (pie de biela, abraza el bulón)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.40,
        depth=0.42,
        location=(0.0, 0.0, rod_length),
        vertices=36,
    )
    small_end = bpy.context.active_object
    small_end.name = "Rod_Small_End"
    small_end.rotation_euler = (math.pi / 2, 0, 0)
    small_end.parent = rod_root
    small_end.data.materials.append(mats["connecting_rod"])
    add(small_end)

    # Casquillo de bronce en pie de biela
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.27,
        depth=0.44,
        location=(0.0, 0.0, rod_length),
        vertices=36,
    )
    small_bushing = bpy.context.active_object
    small_bushing.name = "Rod_Small_Bushing"
    small_bushing.rotation_euler = (math.pi / 2, 0, 0)
    small_bushing.parent = rod_root
    small_bushing.data.materials.append(mats["rod_bearings"])
    add(small_bushing)

    # Big end (cabeza de biela, abraza la muñequilla)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.56,
        depth=0.48,
        location=(0.0, 0.0, 0.0),
        vertices=36,
    )
    big_end = bpy.context.active_object
    big_end.name = "Rod_Big_End"
    big_end.rotation_euler = (math.pi / 2, 0, 0)
    big_end.parent = rod_root
    big_end.data.materials.append(mats["connecting_rod"])
    add(big_end)

    # Casquillo de bronce de bancada en cabeza
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.34,
        depth=0.50,
        location=(0.0, 0.0, 0.0),
        vertices=36,
    )
    big_bearing = bpy.context.active_object
    big_bearing.name = "Rod_Big_Bearing"
    big_bearing.rotation_euler = (math.pi / 2, 0, 0)
    big_bearing.parent = rod_root
    big_bearing.data.materials.append(mats["rod_bearings"])
    add(big_bearing)

    # Tornillos de sombrerete hexagonales
    for x_bolt in [-0.36, 0.36]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.08,
            depth=0.62,
            location=(x_bolt, 0.0, -0.22),
            vertices=6,
        )
        bolt = bpy.context.active_object
        bolt.name = f"Rod_Bolt_{'L' if x_bolt < 0 else 'R'}"
        bolt.parent = rod_root
        bolt.data.materials.append(mats["rod_bolts"])
        add(bolt)

    # =========================================================================
    # 7. CIGÜEÑAL (EJE, MUÑEQUILLA, BRAZOS, CONTRAPESOS, VOLANTE)
    # =========================================================================
    crank_root = bpy.data.objects.new("Crankshaft_Root", None)
    crank_root.empty_display_type = "SINGLE_ARROW"
    crank_root.location = (0.0, 0.0, crank_center_z)
    bpy.context.scene.collection.objects.link(crank_root)
    add(crank_root)

    # Eje principal (en Y)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.34,
        depth=2.6,
        location=(0.0, 0.0, 0.0),
        vertices=32,
    )
    main_journal = bpy.context.active_object
    main_journal.name = "Crank_Main_Journal"
    main_journal.rotation_euler = (math.pi / 2, 0, 0)
    main_journal.parent = crank_root
    main_journal.data.materials.append(mats["crankshaft"])
    add(main_journal)

    # Muñequilla excéntrica (a crank_radius en +Z relativo)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.22,
        depth=0.48,
        location=(0.0, 0.0, crank_radius),
        vertices=32,
    )
    crank_pin_obj = bpy.context.active_object
    crank_pin_obj.name = "Crank_Pin"
    crank_pin_obj.rotation_euler = (math.pi / 2, 0, 0)
    crank_pin_obj.parent = crank_root
    crank_pin_obj.data.materials.append(mats["crankshaft"])
    add(crank_pin_obj)

    # Brazos del cigüeñal (frontal y trasero)
    for y_arm in [-0.28, 0.28]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, y_arm, crank_radius * 0.5),
        )
        arm = bpy.context.active_object
        arm.name = f"Crank_Arm_{'Front' if y_arm < 0 else 'Back'}"
        arm.scale = (0.24, 0.12, crank_radius * 0.95)
        arm.parent = crank_root
        arm.data.materials.append(mats["crankshaft"])
        add(arm)

    # Contrapesos semicirculares / en forma de cuña (estrictamente en Z <= 0, opuestos a la muñequilla)
    for y_cw in [-0.28, 0.28]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=1.05,
            depth=0.18,
            location=(0.0, y_cw, 0.0),
            vertices=32,
        )
        cw = bpy.context.active_object
        cw.name = f"Counterweight_{'F' if y_cw < 0 else 'B'}"
        cw.rotation_euler = (math.pi / 2, 0, 0)

        # Cortar la mitad superior (Z > 0) para que sea un verdadero contrapeso de media luna
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, y_cw, 0.65),
        )
        cw_cutter = bpy.context.active_object
        cw_cutter.scale = (2.5, 0.5, 1.3)
        mod_cw = cw.modifiers.new(name="Cut_CW", type="BOOLEAN")
        mod_cw.object = cw_cutter
        mod_cw.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = cw
        bpy.ops.object.modifier_apply(modifier="Cut_CW")
        bpy.data.objects.remove(cw_cutter, do_unlink=True)

        cw.parent = crank_root
        cw.data.materials.append(mats["counterweights"])
        add(cw)

    # Volante de inercia
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.70,
        depth=0.30,
        location=(0.0, 1.15, 0.0),
        vertices=48,
    )
    flywheel = bpy.context.active_object
    flywheel.name = "Engine_Flywheel"
    flywheel.rotation_euler = (math.pi / 2, 0, 0)
    flywheel.parent = crank_root
    flywheel.data.materials.append(mats["flywheel"])
    add(flywheel)

    # =========================================================================
    # 8. VÁLVULAS (PLATILLO PLANO + VÁSTAGO + RESORTE + RETAINER)
    # =========================================================================
    valves = {}
    valve_defs = [
        ("intake",  -0.58, mats["valve_intake"]),
        ("exhaust",  0.58, mats["valve_exhaust"]),
    ]

    for v_type, x_pos, v_mat in valve_defs:
        v_root = bpy.data.objects.new(f"Valve_{v_type.capitalize()}_Root", None)
        v_root.empty_display_type = "PLAIN_AXES"
        v_root.location = (x_pos, 0.0, head_z + 0.06)
        bpy.context.scene.collection.objects.link(v_root)
        add(v_root)

        # Platillo de válvula (disco plano claramente visible)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.42,
            depth=0.11,
            location=(0.0, 0.0, 0.0),
            vertices=28,
        )
        v_head = bpy.context.active_object
        v_head.name = f"Valve_{v_type}_Head"
        v_head.parent = v_root
        v_head.data.materials.append(v_mat)
        add(v_head)

        # Vástago vertical hacia arriba
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.08,
            depth=1.55,
            location=(0.0, 0.0, 0.775),
            vertices=16,
        )
        v_stem = bpy.context.active_object
        v_stem.name = f"Valve_{v_type}_Stem"
        v_stem.parent = v_root
        v_stem.data.materials.append(mats["wrist_pin"])
        add(v_stem)

        # Resorte helicoidal (cilindro)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.23,
            depth=0.85,
            location=(0.0, 0.0, 0.70),
            vertices=24,
        )
        v_spring = bpy.context.active_object
        v_spring.name = f"Valve_{v_type}_Spring"
        v_spring.parent = v_root
        v_spring.data.materials.append(mats["valve_spring"])
        add(v_spring)

        # Platillo de retención superior
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.27,
            depth=0.09,
            location=(0.0, 0.0, 1.14),
            vertices=24,
        )
        v_ret = bpy.context.active_object
        v_ret.name = f"Valve_{v_type}_Retainer"
        v_ret.parent = v_root
        v_ret.data.materials.append(mats["rod_bolts"])
        add(v_ret)

        valves[v_type] = v_root

    # =========================================================================
    # 9. BUJÍA CENTRAL
    # =========================================================================
    spark_root = bpy.data.objects.new("Spark_Plug_Root", None)
    spark_root.location = (0.0, 0.0, head_z + 0.06)
    bpy.context.scene.collection.objects.link(spark_root)
    add(spark_root)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.21,
        depth=1.20,
        location=(0.0, 0.0, 0.60),
        vertices=20,
    )
    ceramic = bpy.context.active_object
    ceramic.name = "Spark_Ceramic_Body"
    ceramic.parent = spark_root
    ceramic.data.materials.append(mats["spark_ceramic"])
    add(ceramic)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.29,
        depth=0.42,
        location=(0.0, 0.0, 0.08),
        vertices=6,
    )
    hex_nut = bpy.context.active_object
    hex_nut.name = "Spark_Hex_Nut"
    hex_nut.parent = spark_root
    hex_nut.data.materials.append(mats["spark_metal"])
    add(hex_nut)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.055,
        depth=0.38,
        location=(0.0, 0.0, -0.19),
        vertices=12,
    )
    electrode = bpy.context.active_object
    electrode.name = "Spark_Electrode"
    electrode.parent = spark_root
    electrode.data.materials.append(mats["spark_metal"])
    add(electrode)

    # =========================================================================
    # 10. EFECTOS VISUALES (Chispa, Llama, Flujos)
    # =========================================================================
    combustion_z = head_z - 0.2

    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=0.18,
        subdivisions=2,
        location=(0.0, 0.0, combustion_z),
    )
    spark_arc = bpy.context.active_object
    spark_arc.name = "FX_Electric_Spark"
    spark_arc.data.materials.append(mats["electric_spark"])
    spark_arc.scale = (0.001, 0.001, 0.001)
    add(spark_arc)

    # Llama de combustión hiperrealista multicapa
    flame_root = bpy.data.objects.new("FX_Combustion_Flame", None)
    flame_root.location = (0.0, 0.0, combustion_z - 0.25)
    flame_root.scale = (0.001, 0.001, 0.001)
    bpy.context.scene.collection.objects.link(flame_root)
    add(flame_root)

    # Capa exterior: corona roja con picos estilizados
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr * 0.95,
        depth=0.18,
        location=(0.0, -0.05, 0.0),
        vertices=18,
    )
    f_out = bpy.context.active_object
    f_out.name = "Flame_Spikes_Outer"
    f_out.rotation_euler = (math.pi / 2, 0, 0)
    f_out.parent = flame_root
    f_out.data.materials.append(mats["flame_combustion"])
    add(f_out)
    if hasattr(f_out.data, "polygons"):
        for p in f_out.data.polygons:
            p.use_smooth = False

    # Capa interior: núcleo blanco incandescente de altísima emisión
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr * 0.52,
        depth=0.24,
        location=(0.0, -0.08, 0.0),
        vertices=12,
    )
    f_core = bpy.context.active_object
    f_core.name = "Flame_Core_Incandescent"
    f_core.rotation_euler = (math.pi / 2, math.radians(15), 0)
    f_core.parent = flame_root
    f_core.data.materials.append(mats.get("flame_core", mats["flame_combustion"]))
    add(f_core)
    if hasattr(f_core.data, "polygons"):
        for p in f_core.data.polygons:
            p.use_smooth = False

    combustion_flame = flame_root

    intake_flow_z = head_z + 0.55
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.36,
        radius2=0.06,
        depth=0.85,
        location=(-0.65, 0.0, intake_flow_z),
        vertices=20,
    )
    fx_intake = bpy.context.active_object
    fx_intake.name = "FX_Intake_Flow"
    fx_intake.rotation_euler = (0.0, math.radians(-28), 0.0)
    fx_intake.data.materials.append(mats["intake_flow"])
    fx_intake.scale = (0.001, 0.001, 0.001)
    add(fx_intake)

    bpy.ops.mesh.primitive_cone_add(
        radius1=0.06,
        radius2=0.36,
        depth=0.85,
        location=(0.65, 0.0, intake_flow_z),
        vertices=20,
    )
    fx_exhaust = bpy.context.active_object
    fx_exhaust.name = "FX_Exhaust_Flow"
    fx_exhaust.rotation_euler = (0.0, math.radians(28), 0.0)
    fx_exhaust.data.materials.append(mats["exhaust_flow"])
    fx_exhaust.scale = (0.001, 0.001, 0.001)
    add(fx_exhaust)

    # Volumen de mezcla en compresión (cilindro semi-transparente que muestra la mezcla comprimiéndose)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr * 0.90,
        depth=0.70,
        location=(0.0, 0.0, combustion_z - 0.25),
        vertices=24,
    )
    fx_compression = bpy.context.active_object
    fx_compression.name = "FX_Compression_Gas"
    fx_compression.data.materials.append(mats["compression_gas"])
    fx_compression.scale = (0.001, 0.001, 0.001)
    add(fx_compression)

    # =========================================================================
    # 11. SUELO DE ESTUDIO
    # =========================================================================
    bpy.ops.mesh.primitive_plane_add(
        size=50.0,
        location=(0.0, 0.0, block_bottom - 0.08),
    )
    floor = bpy.context.active_object
    floor.name = "Studio_Floor"
    floor.data.materials.append(mats["studio_floor"])
    add(floor)

    return {
        "piston_root": piston_root,
        "rod_root": rod_root,
        "crank_root": crank_root,
        "valve_intake": valves["intake"],
        "valve_exhaust": valves["exhaust"],
        "spark_root": spark_root,
        "cylinder_head": head_root,
        "fx_spark": spark_arc,
        "fx_flame": combustion_flame,
        "fx_intake": fx_intake,
        "fx_exhaust": fx_exhaust,
        "fx_compression": fx_compression,
        "block": block,
        "crank_radius": crank_radius,
        "rod_length": rod_length,
        "crank_center_z": crank_center_z,
        # Valores derivados para cámara y animación
        "head_z": head_z,
        "pms_z": pms_z,
        "block_top": block_top,
        "block_bottom": block_bottom,
        "block_center_z": block_center_z,
        "cylinder_radius": cr,
    }
