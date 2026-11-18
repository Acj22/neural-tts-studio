"""Modelo 3D Procedural de Motor de Cuatro Tiempos en Blender 5.3 (Fase 2.1 - Alto Realismo CAD).

Mejoras de Fidelidad Mecánica y Visual (Estilo Coverfox / Precision Engineering):
- Bloque monolítico de fundición grafito con cara de corte en acero mecanizado nítido.
- Resortes de válvula helicoidales 3D reales de alambre de acero con deformación física de compresión.
- Bujía con aislador cerámico corrugado, tuerca hexagonal de apriete y electrodo de masa en escuadra ('L').
- Pistón automotriz con bisel perimétrico, muescas de válvulas en corona, falda arqueada y 3 aros de compresión.
- Biela forjada en viga 'I' con sombrerete de cabeza partido y pernos hexagonales de bancada.
- Cigüeñal con muñequilla rectificada a espejo y contrapesos lobulares aerodinámicos.
- Cárter inferior (Oil Pan) estampado en base del motor.
- Llama de combustión explosiva multicapa (Coverfox starburst explosion) con luz puntual interna dinámica.
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
    """Aplica shading suave a la malla activa asegurando normales limpias."""
    try:
        if obj and hasattr(obj, "data") and hasattr(obj.data, "polygons"):
            for poly in obj.data.polygons:
                poly.use_smooth = True
    except Exception:
        pass
    return obj


def _apply_bevel(obj: Any, width: float = 0.02, segments: int = 2, angle_deg: float = 35.0) -> None:
    """Aplica un modificador de bisel para generar brillos especulares en aristas mecanizadas."""
    try:
        mod = obj.modifiers.new("Bevel_Highlight", type="BEVEL")
        mod.width = width
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(angle_deg)
    except Exception:
        pass


def _create_helical_spring(
    name: str,
    radius: float = 0.22,
    wire_radius: float = 0.032,
    height: float = 0.85,
    num_turns: float = 6.0,
    pts_per_turn: int = 16,
    mat: Any = None,
) -> Any:
    """Crea proceduralmente un resorte helicoidal 3D de alta precisión mediante curva poligonal."""
    curve_data = bpy.data.curves.new(f"{name}_Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.bevel_depth = wire_radius
    curve_data.bevel_resolution = 4

    spline = curve_data.splines.new("POLY")
    total_pts = int(num_turns * pts_per_turn)
    spline.points.add(total_pts - 1)

    for i in range(total_pts):
        frac = i / float(total_pts - 1)
        theta = frac * num_turns * 2.0 * math.pi
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        z = frac * height
        spline.points[i].co = (x, y, z, 1.0)

    spring_obj = bpy.data.objects.new(name, curve_data)
    if mat:
        spring_obj.data.materials.append(mat)
    return spring_obj


def _create_starburst_flame_layer(
    name: str,
    outer_r: float,
    inner_r: float,
    depth: float,
    n_spikes: int,
    mat: Any,
) -> Any:
    """Genera una malla 3D de explosión estelar dentada (Coverfox Starburst Explosion)."""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)

    verts = []
    faces = []

    # Generar caras frontales y traseras con grosor 3D
    half_d = depth * 0.5
    for y_val in [-half_d, half_d]:
        verts.append((0.0, y_val, 0.0))  # Vértice central
        for i in range(n_spikes * 2):
            angle = (i / (n_spikes * 2)) * 2 * math.pi
            # Alternar entre punta de llama y valle
            r = outer_r if (i % 2 == 1) else inner_r
            # Aplanar suavemente la parte superior para adaptarse a la culata
            x_coord = r * math.cos(angle)
            z_coord = r * math.sin(angle) * 0.85
            verts.append((x_coord, y_val, z_coord))

    # Construir abanicos y faldón lateral
    offset_back = 1 + n_spikes * 2
    for i in range(n_spikes * 2):
        next_i = (i + 1) % (n_spikes * 2)
        # Cara frontal
        faces.append((0, 1 + i, 1 + next_i))
        # Cara trasera
        faces.append((offset_back, offset_back + 1 + next_i, offset_back + 1 + i))
        # Faldón perimetral
        faces.append((1 + i, offset_back + 1 + i, offset_back + 1 + next_i, 1 + next_i))

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    if mat:
        obj.data.materials.append(mat)
    # Sombrado plano para aristas afiladas de cómic técnico
    if hasattr(mesh, "polygons"):
        for p in mesh.polygons:
            p.use_smooth = False

    return obj


def create_combustion_engine_3d(
    crank_radius: float = 1.0,
    rod_length: float = 3.6,
    cylinder_radius: float = 1.30,
    piston_height: float = 1.40,
    crank_center_z: float = 0.0,
) -> dict[str, Any]:
    """Crea proceduralmente todos los componentes mecánicos con grado de realismo CAD y estética Coverfox."""
    if bpy is None:
        raise RuntimeError("Este módulo debe ejecutarse dentro del entorno de Blender.")

    mats = setup_engine_materials()
    col_name = "Engine_3D_v21"
    collection = bpy.data.collections.get(col_name)
    if not collection:
        collection = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(collection)

    def add(obj: Any) -> Any:
        """Agrega objeto a la colección del motor y aplica smooth shading si corresponde."""
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
        if obj.name not in collection.objects:
            collection.objects.link(obj)
        if obj.type == "MESH":
            _smooth(obj)
        return obj

    # =========================================================================
    # DIMENSIONES GLOBALES COHERENTES
    # =========================================================================
    cr = cylinder_radius
    pms_z = crank_center_z + crank_radius + rod_length
    block_top = pms_z + piston_height + 0.45
    block_bottom = crank_center_z - 1.15
    block_height = block_top - block_bottom
    block_center_z = (block_top + block_bottom) / 2.0
    head_z = pms_z + piston_height * 0.5 + 0.35

    # =========================================================================
    # 1. BLOQUE EXTERIOR DEL MOTOR Y CÁRTER (Fundición oscura con aletas)
    # =========================================================================
    block_w = cr * 3.4
    block_d = cr * 2.05

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, block_center_z),
    )
    block = bpy.context.active_object
    block.name = "Engine_Block"
    block.scale = (block_w, block_d, block_height)
    block.data.materials.append(mats["engine_block"])
    block.data.materials.append(mats["cutaway_rim"])  # Slot 1 para corte seccionado
    add(block)

    # Aletas de refrigeración laterales
    fin_z_start = block_bottom + 0.85
    fin_z_end = block_top - 0.65
    for i in range(5):
        pct = i / 4.0
        z_fin_world = fin_z_start + pct * (fin_z_end - fin_z_start)
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, 0.0, z_fin_world),
        )
        fin = bpy.context.active_object
        fin.scale = (block_w + 0.38, block_d + 0.22, 0.13)
        fin.data.materials.append(mats["engine_block"])
        mod_uf = block.modifiers.new(f"UnionFin_{i}", type="BOOLEAN")
        mod_uf.object = fin
        mod_uf.operation = "UNION"
        bpy.context.view_layer.objects.active = block
        bpy.ops.object.modifier_apply(modifier=f"UnionFin_{i}")
        bpy.data.objects.remove(fin, do_unlink=True)

    # Vaciado interior del cilindro (Bore)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr + 0.12,
        depth=block_height * 0.72,
        location=(0.0, 0.0, block_center_z + 0.85),
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
    crank_cav.scale = (cr * 2.65, block_d * 1.1, 3.4)
    mod_cc = block.modifiers.new(name="CrankCavity", type="BOOLEAN")
    mod_cc.object = crank_cav
    mod_cc.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = block
    bpy.ops.object.modifier_apply(modifier="CrankCavity")
    bpy.data.objects.remove(crank_cav, do_unlink=True)

    # Bandeja del cárter inferior (Oil Pan)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, block_bottom - 0.25),
    )
    oil_pan = bpy.context.active_object
    oil_pan.name = "Engine_Oil_Pan"
    oil_pan.scale = (block_w * 0.88, block_d * 0.88, 0.45)
    oil_pan.data.materials.append(mats["oil_pan"])
    add(oil_pan)
    _apply_bevel(oil_pan, width=0.03, segments=2)

    # Tapón de drenaje de aceite
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.10,
        depth=0.15,
        location=(0.0, -block_d * 0.42, block_bottom - 0.35),
        vertices=6,
    )
    drain_plug = bpy.context.active_object
    drain_plug.name = "Oil_Drain_Plug"
    drain_plug.rotation_euler = (math.pi / 2, 0, 0)
    drain_plug.parent = oil_pan
    drain_plug.data.materials.append(mats["rod_bolts"])
    add(drain_plug)

    # Corte cutaway frontal (la mitad frontal del bloque se retira)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -block_d * 0.5, block_center_z),
    )
    cutter = bpy.context.active_object
    cutter.name = "Cutaway_Cutter"
    cutter.scale = (block_w * 1.35, block_d, block_height * 1.15)
    cutter.data.materials.append(mats["cutaway_rim"])  # Transfiere material de corte a las caras
    mod_b = block.modifiers.new(name="Cutaway_Block", type="BOOLEAN")
    mod_b.object = cutter
    mod_b.operation = "DIFFERENCE"
    mod_b.material_mode = "TRANSFER" if hasattr(mod_b, "material_mode") else "INDEX"
    bpy.context.view_layer.objects.active = block
    bpy.ops.object.modifier_apply(modifier="Cutaway_Block")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # =========================================================================
    # 2. CAMISA INTERIOR DEL CILINDRO (Acero satinado con bisel de corte)
    # =========================================================================
    liner_height = rod_length + crank_radius + piston_height + 0.35
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

    # Vaciado interior de la camisa
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

    # Conducto de admisión izquierdo (40° hacia arriba)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.29,
        depth=1.35,
        location=(-0.75, 0.0, 0.55),
        vertices=24,
    )
    port_in = bpy.context.active_object
    port_in.name = "Intake_Port_Duct"
    port_in.rotation_euler = (0.0, math.radians(40), 0.0)
    port_in.parent = head_root
    port_in.data.materials.append(mats.get("manifold_pipes", mats["valve_intake"]))
    add(port_in)
    _apply_bevel(port_in, width=0.015, segments=2)

    # Conducto de escape derecho (40° hacia arriba)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.29,
        depth=1.35,
        location=(0.75, 0.0, 0.55),
        vertices=24,
    )
    port_ex = bpy.context.active_object
    port_ex.name = "Exhaust_Port_Duct"
    port_ex.rotation_euler = (0.0, math.radians(-40), 0.0)
    port_ex.parent = head_root
    port_ex.data.materials.append(mats.get("manifold_pipes", mats["valve_exhaust"]))
    add(port_ex)
    _apply_bevel(port_ex, width=0.015, segments=2)

    # =========================================================================
    # 4. PISTÓN AUTOMOTRIZ DE ALTA FIDELIDAD (MUESCAS, ANILLOS, BULÓN FRONTAL)
    # =========================================================================
    piston_root = bpy.data.objects.new("Piston_Root", None)
    piston_root.empty_display_type = "ARROWS"
    piston_root.empty_display_size = 0.4
    piston_root.location = (0.0, 0.0, pms_z)
    bpy.context.scene.collection.objects.link(piston_root)
    add(piston_root)

    # Cuerpo cilíndrico del pistón
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

    # Muescas circulares en corona para válvulas (Valve Relief Pockets)
    for vx, v_rot in [(-0.55, 15), (0.55, -15)]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.40,
            depth=0.15,
            location=(vx, 0.0, piston_height * 0.5),
            vertices=28,
        )
        pocket = bpy.context.active_object
        pocket.parent = piston_root
        mp = piston_body.modifiers.new("ValvePocket", type="BOOLEAN")
        mp.object = pocket
        mp.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = piston_body
        bpy.ops.object.modifier_apply(modifier="ValvePocket")
        bpy.data.objects.remove(pocket, do_unlink=True)

    # Recortes arqueados de la falda a los lados (-X y +X)
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

    # Vaciado interior de la falda
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

    # Orificio pasante del bulón en el centro
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

    _apply_bevel(piston_body, width=0.012, segments=2)

    # Bulón cilíndrico de acero templado insertado en el orificio
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
    _apply_bevel(wrist_pin, width=0.015, segments=2)

    # 3 aros de compresión y aceite independientes
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
    # 5. BIELA FORJADA EN VIGA 'I', CASQUILLOS DE BRONCE Y PERNOS
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
    _apply_bevel(rod_body, width=0.018, segments=2)

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
    _apply_bevel(small_end, width=0.015, segments=2)

    # Casquillo de bronce de fricción en pie
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

    # Big end (cabeza de biela con sombrerete partido)
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
    _apply_bevel(big_end, width=0.018, segments=2)

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

    # Tornillos de sombrerete hexagonales con arandelas
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
    # 6. CIGÜEÑAL (EJE, MUÑEQUILLA, CONTRAPESOS AERODINÁMICOS, VOLANTE)
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

    # Muñequilla excéntrica rectificada a espejo
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

    # Brazos del cigüeñal (web arms)
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
        _apply_bevel(arm, width=0.015, segments=2)

    # Contrapesos lobulares aerodinámicos (en Z <= 0, opuestos a la muñequilla)
    for y_cw in [-0.28, 0.28]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=1.05,
            depth=0.18,
            location=(0.0, y_cw, 0.0),
            vertices=36,
        )
        cw = bpy.context.active_object
        cw.name = f"Counterweight_{'F' if y_cw < 0 else 'B'}"
        cw.rotation_euler = (math.pi / 2, 0, 0)

        # Cortar la mitad superior para media luna
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
        _apply_bevel(cw, width=0.02, segments=2)

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
    _apply_bevel(flywheel, width=0.025, segments=2)

    # =========================================================================
    # 7. VÁLVULAS CON RESORTES HELICOIDALES 3D REALES
    # =========================================================================
    valves = {}
    springs = {}
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

        # Platillo de válvula con bisel de asiento a 45°
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.42,
            depth=0.11,
            location=(0.0, 0.0, 0.0),
            vertices=32,
        )
        v_head = bpy.context.active_object
        v_head.name = f"Valve_{v_type}_Head"
        v_head.parent = v_root
        v_head.data.materials.append(v_mat)
        add(v_head)
        _apply_bevel(v_head, width=0.015, segments=2)

        # Vástago vertical pulido hacia arriba
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

        # Platillo retenedor superior
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.27,
            depth=0.09,
            location=(0.0, 0.0, 1.14),
            vertices=24,
        )
        v_ret = bpy.context.active_object
        v_ret.name = f"Valve_{v_type}_Retainer"
        v_ret.parent = v_root
        v_ret.data.materials.append(mats["valve_retainer"])
        add(v_ret)
        _apply_bevel(v_ret, width=0.012, segments=2)

        # RESORTE HELICOIDAL 3D REAL (Espirales de alambre de acero)
        # Nace en la culata y abraza el vástago hasta el retenedor
        spring = _create_helical_spring(
            name=f"Valve_{v_type}_Spring",
            radius=0.22,
            wire_radius=0.032,
            height=0.82,
            num_turns=6.0,
            pts_per_turn=16,
            mat=mats["valve_spring"],
        )
        spring.location = (x_pos, 0.0, head_z + 0.32)
        add(spring)
        springs[v_type] = spring

        valves[v_type] = v_root

    # =========================================================================
    # 8. BUJÍA DE ALTA PRECISIÓN (AISLADOR CORRUGADO, HEXÁGONO Y ELECTRODOS)
    # =========================================================================
    spark_root = bpy.data.objects.new("Spark_Plug_Root", None)
    spark_root.location = (0.0, 0.0, head_z + 0.06)
    bpy.context.scene.collection.objects.link(spark_root)
    add(spark_root)

    # Cuerpo cerámico principal
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.20,
        depth=1.25,
        location=(0.0, 0.0, 0.65),
        vertices=24,
    )
    ceramic = bpy.context.active_object
    ceramic.name = "Spark_Ceramic_Body"
    ceramic.parent = spark_root
    ceramic.data.materials.append(mats["spark_ceramic"])
    add(ceramic)

    # 3 Anillos corrugados dieléctricos en la porcelana
    for i_rib in range(3):
        z_rib = 0.85 + i_rib * 0.14
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.21,
            minor_radius=0.025,
            location=(0.0, 0.0, z_rib),
            major_segments=24,
            minor_segments=8,
        )
        rib = bpy.context.active_object
        rib.name = f"Spark_Rib_{i_rib+1}"
        rib.parent = spark_root
        rib.data.materials.append(mats["spark_ceramic"])
        add(rib)

    # Tuerca hexagonal de apriete
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.30,
        depth=0.38,
        location=(0.0, 0.0, 0.12),
        vertices=6,
    )
    hex_nut = bpy.context.active_object
    hex_nut.name = "Spark_Hex_Nut"
    hex_nut.parent = spark_root
    hex_nut.data.materials.append(mats["spark_metal"])
    add(hex_nut)
    _apply_bevel(hex_nut, width=0.015, segments=2)

    # Arandela / Junta de estanqueidad de cobre
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.29,
        depth=0.06,
        location=(0.0, 0.0, -0.06),
        vertices=24,
    )
    washer = bpy.context.active_object
    washer.name = "Spark_Copper_Washer"
    washer.parent = spark_root
    washer.data.materials.append(mats["spark_copper"])
    add(washer)

    # Electrodo central
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.05,
        depth=0.35,
        location=(0.0, 0.0, -0.22),
        vertices=12,
    )
    electrode = bpy.context.active_object
    electrode.name = "Spark_Electrode_Center"
    electrode.parent = spark_root
    electrode.data.materials.append(mats["spark_metal"])
    add(electrode)

    # Electrodo de masa en escuadra ('L' Ground Strap)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.035,
        depth=0.24,
        location=(0.14, 0.0, -0.22),
        vertices=10,
    )
    ground_leg = bpy.context.active_object
    ground_leg.name = "Spark_Ground_Leg"
    ground_leg.parent = spark_root
    ground_leg.data.materials.append(mats["spark_metal"])
    add(ground_leg)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.035,
        depth=0.15,
        location=(0.07, 0.0, -0.34),
        vertices=10,
    )
    ground_tip = bpy.context.active_object
    ground_tip.name = "Spark_Ground_Tip"
    ground_tip.rotation_euler = (0, math.pi / 2, 0)
    ground_tip.parent = spark_root
    ground_tip.data.materials.append(mats["spark_metal"])
    add(ground_tip)

    # =========================================================================
    # 9. EFECTOS VISUALES Y LLAMA COVERFOX DE ALTO IMPACTO
    # =========================================================================
    combustion_z = head_z - 0.22

    # Chispa eléctrica en el entrehierro
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=0.16,
        subdivisions=2,
        location=(0.0, 0.0, combustion_z + 0.02),
    )
    spark_arc = bpy.context.active_object
    spark_arc.name = "FX_Electric_Spark"
    spark_arc.data.materials.append(mats["electric_spark"])
    spark_arc.scale = (0.001, 0.001, 0.001)
    add(spark_arc)

    # Llama de combustión explosiva estelar (Coverfox Starburst Explosion)
    flame_root = bpy.data.objects.new("FX_Combustion_Flame", None)
    flame_root.location = (0.0, 0.0, combustion_z - 0.15)
    flame_root.scale = (0.001, 0.001, 0.001)
    bpy.context.scene.collection.objects.link(flame_root)
    add(flame_root)

    # Capa 1: Llamas exteriores carmesí profundo (spikes largos)
    flame_outer = _create_starburst_flame_layer(
        name="Flame_Starburst_Outer",
        outer_r=cr * 0.98,
        inner_r=cr * 0.55,
        depth=0.18,
        n_spikes=14,
        mat=mats["flame_outer"],
    )
    flame_outer.parent = flame_root
    add(flame_outer)

    # Capa 2: Explosión intermedia naranja ardiente
    flame_mid = _create_starburst_flame_layer(
        name="Flame_Starburst_Mid",
        outer_r=cr * 0.75,
        inner_r=cr * 0.40,
        depth=0.22,
        n_spikes=12,
        mat=mats["flame_mid"],
    )
    flame_mid.parent = flame_root
    flame_mid.rotation_euler = (0, 0, math.radians(15))
    add(flame_mid)

    # Capa 3: Núcleo blanco incandescente de altísima radiación
    flame_core = _create_starburst_flame_layer(
        name="Flame_Starburst_Core",
        outer_r=cr * 0.45,
        inner_r=cr * 0.25,
        depth=0.26,
        n_spikes=8,
        mat=mats["flame_core"],
    )
    flame_core.parent = flame_root
    flame_core.rotation_euler = (0, 0, math.radians(30))
    add(flame_core)

    # Luz puntual dinámica interior de combustión (ilumina el cilindro y el pistón al estallar)
    bpy.ops.object.light_add(
        type="POINT",
        radius=0.35,
        location=(0.0, 0.0, combustion_z - 0.10),
    )
    light_combustion = bpy.context.active_object
    light_combustion.name = "Light_Combustion_Dynamic"
    light_combustion.data.color = (1.0, 0.45, 0.08)
    light_combustion.data.energy = 0.0  # Apagada por defecto
    collection.objects.link(light_combustion)
    if light_combustion.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(light_combustion)

    # Flujo de admisión aerodinámico (cian)
    intake_flow_z = head_z + 0.55
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.36,
        radius2=0.06,
        depth=0.90,
        location=(-0.65, 0.0, intake_flow_z),
        vertices=20,
    )
    fx_intake = bpy.context.active_object
    fx_intake.name = "FX_Intake_Flow"
    fx_intake.rotation_euler = (0.0, math.radians(-28), 0.0)
    fx_intake.data.materials.append(mats["intake_flow"])
    fx_intake.scale = (0.001, 0.001, 0.001)
    add(fx_intake)

    # Flujo de escape aerodinámico (naranja)
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.06,
        radius2=0.36,
        depth=0.90,
        location=(0.65, 0.0, intake_flow_z),
        vertices=20,
    )
    fx_exhaust = bpy.context.active_object
    fx_exhaust.name = "FX_Exhaust_Flow"
    fx_exhaust.rotation_euler = (0.0, math.radians(28), 0.0)
    fx_exhaust.data.materials.append(mats["exhaust_flow"])
    fx_exhaust.scale = (0.001, 0.001, 0.001)
    add(fx_exhaust)

    # Volumen de mezcla comprimida
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
    # 10. SUELO DE ESTUDIO TÉCNICO
    # =========================================================================
    bpy.ops.mesh.primitive_plane_add(
        size=50.0,
        location=(0.0, 0.0, block_bottom - 0.50),
    )
    floor = bpy.context.active_object
    floor.name = "Studio_Floor"
    floor.data.materials.append(mats["studio_floor"])
    add(floor)

    return {
        "engine_block": block,
        "cylinder_liner": liner,
        "cylinder_head": head_root,
        "piston_root": piston_root,
        "piston_body": piston_body,
        "rod_root": rod_root,
        "crank_root": crank_root,
        "valve_intake": valves["intake"],
        "valve_exhaust": valves["exhaust"],
        "spring_intake": springs["intake"],
        "spring_exhaust": springs["exhaust"],
        "spark_root": spark_root,
        "fx_spark": spark_arc,
        "fx_flame": flame_root,
        "light_combustion": light_combustion,
        "fx_intake": fx_intake,
        "fx_exhaust": fx_exhaust,
        "fx_compression": fx_compression,
        "crank_radius": crank_radius,
        "rod_length": rod_length,
        "crank_center_z": crank_center_z,
        "head_z": head_z,
    }
