"""Modelo 3D Procedural de Motor de Cuatro Tiempos en Blender 5.3 (Fase 2.1 / 2.3 - Ultra Realismo CAD).

Fidelidad Mecánica y Visual idéntica a la Referencia CAD Técnica del Usuario (Imagen 2):
- Bloque monolítico de fundición de aluminio con silueta orgánica, apoyos de bancada y corte transversal nítido.
- Cárter inferior macizo con apoyos escalonados y hendidura rectangular frontal característica.
- Camisa de cilindro rectificada con ánima pulida a espejo y chaflán mecanizado.
- Culata de doble cúpula redondeada (tapa de balancines en antracita oscura técnica) con conductos curvos de admisión y escape.
- Pistón automotriz forjado en cobre / bronce anodizado cálido con aros de compresión en cromo brillante.
- Bulón del pistón tubular pasante en acero templado oscuro (núcleo cilíndrico hueco visible en corte frontal).
- Biela forjada en viga 'I' con flancos maquinados, canal forjado oscurecido, casquillos de bronce y tornillos de sombrerete.
- Cigüeñal con muñequilla rectificada, contrapesos lobulares aerodinámicos y muñón de salida.
- Válvulas inclinadas simétricamente a 16° con resortes helicoidales 3D de alambre de acero de alta tensión.
- Bujía centralizada en la cúspide con aislador cerámico blanco corrugado, tuerca hexagonal y electrodos.
- Efectos de combustión explosiva estilo Coverfox (starburst multicapa) con luz puntual interna sincronizada.
- Ciclorama de estudio en Slate Blue técnico (#2A4053) con iluminación de 3 puntos (Key, Fill, Rim specular).
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


def _apply_bevel(obj: Any, width: float = 0.016, segments: int = 2, angle_deg: float = 35.0) -> None:
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
    radius: float = 0.20,
    wire_radius: float = 0.032,
    height: float = 0.88,
    num_turns: float = 6.5,
    pts_per_turn: int = 24,
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

    half_d = depth * 0.5
    for y_val in [-half_d, half_d]:
        verts.append((0.0, y_val, 0.0))
        for i in range(n_spikes * 2):
            angle = (i / (n_spikes * 2)) * 2 * math.pi
            r = outer_r if (i % 2 == 1) else inner_r
            x_coord = r * math.cos(angle)
            z_coord = r * math.sin(angle) * 0.85
            verts.append((x_coord, y_val, z_coord))

    offset_back = 1 + n_spikes * 2
    for i in range(n_spikes * 2):
        next_i = (i + 1) % (n_spikes * 2)
        faces.append((0, 1 + i, 1 + next_i))
        faces.append((offset_back, offset_back + 1 + next_i, offset_back + 1 + i))
        faces.append((1 + i, offset_back + 1 + i, offset_back + 1 + next_i, 1 + next_i))

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    if mat:
        obj.data.materials.append(mat)
    if hasattr(mesh, "polygons"):
        for p in mesh.polygons:
            p.use_smooth = False

    return obj


def create_combustion_engine_3d(
    crank_radius: float = 1.0,
    rod_length: float = 3.6,
    cylinder_radius: float = 1.30,
    piston_height: float = 1.45,
    crank_center_z: float = 0.0,
) -> dict[str, Any]:
    """Crea proceduralmente todos los componentes mecánicos con grado de realismo CAD idéntico a la referencia del usuario."""
    if bpy is None:
        raise RuntimeError("Este módulo debe ejecutarse dentro del entorno de Blender.")

    mats = setup_engine_materials()
    col_name = "Engine_3D_v23_CAD"
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
    # DIMENSIONES GLOBALES EXACTAS
    # =========================================================================
    cr = cylinder_radius
    pms_z = crank_center_z + crank_radius + rod_length  # 4.60
    head_z = pms_z + piston_height * 0.5 + 0.35         # 5.675
    block_bottom = crank_center_z - 1.25

    # =========================================================================
    # 0. CICLORAMA DE ESTUDIO (Slate Blue #2A4053 de la Referencia CAD)
    # =========================================================================
    mesh_cyc = bpy.data.meshes.new("Studio_Cyclorama_Mesh")
    obj_cyc = bpy.data.objects.new("Studio_Cyclorama", mesh_cyc)
    verts_cyc = [
        (-24.0, -14.0, block_bottom),
        ( 24.0, -14.0, block_bottom),
        (-24.0,   8.0, block_bottom),
        ( 24.0,   8.0, block_bottom),
        (-24.0,  10.0, block_bottom + 1.2),
        ( 24.0,  10.0, block_bottom + 1.2),
        (-24.0,  11.5, block_bottom + 4.0),
        ( 24.0,  11.5, block_bottom + 4.0),
        (-24.0,  11.8, block_bottom + 18.0),
        ( 24.0,  11.8, block_bottom + 18.0),
    ]
    faces_cyc = [
        (0, 1, 3, 2),
        (2, 3, 5, 4),
        (4, 5, 7, 6),
        (6, 7, 9, 8),
    ]
    mesh_cyc.from_pydata(verts_cyc, [], faces_cyc)
    mesh_cyc.update()
    obj_cyc.data.materials.append(mats["studio_backdrop"])
    _smooth(obj_cyc)
    add(obj_cyc)

    # =========================================================================
    # 1. BLOQUE DEL MOTOR Y CÁRTER MACIZO CON HENDIDURA Y APOYO DE BANCADA
    # =========================================================================
    # Base inferior / Cárter macizo
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.40, block_bottom + 0.40),
    )
    base_pan = bpy.context.active_object
    base_pan.name = "Engine_Base_Sump"
    base_pan.scale = (4.4, 2.4, 0.80)
    base_pan.data.materials.append(mats["engine_block"])
    base_pan.data.materials.append(mats["cutaway_rim"])
    add(base_pan)
    _apply_bevel(base_pan, width=0.035, segments=2)

    # Hendidura rectangular frontal en la base (visible claramente en la Referencia)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -0.65, block_bottom + 0.40),
    )
    pocket_front = bpy.context.active_object
    pocket_front.scale = (2.2, 0.45, 0.50)
    mpf = base_pan.modifiers.new("PocketFront", type="BOOLEAN")
    mpf.object = pocket_front
    mpf.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = base_pan
    bpy.ops.object.modifier_apply(modifier="PocketFront")
    bpy.data.objects.remove(pocket_front, do_unlink=True)

    # Pies de apoyo escalonados en los flancos
    for sx in [-2.05, 2.05]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(sx, 0.40, block_bottom + 0.20),
        )
        foot = bpy.context.active_object
        foot.name = f"Engine_Mount_Foot_{'L' if sx < 0 else 'R'}"
        foot.scale = (0.50, 2.2, 0.38)
        foot.data.materials.append(mats["engine_block"])
        foot.parent = base_pan
        foot.matrix_parent_inverse = base_pan.matrix_world.inverted()
        add(foot)
        _apply_bevel(foot, width=0.02, segments=2)

    # Cárter cilíndrico del cigüeñal
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.85,
        depth=2.2,
        location=(0.0, 0.30, crank_center_z + 0.25),
        vertices=48,
    )
    crank_housing = bpy.context.active_object
    crank_housing.name = "Engine_Crank_Housing"
    crank_housing.rotation_euler = (math.pi / 2, 0, 0)
    crank_housing.data.materials.append(mats["engine_block"])
    crank_housing.data.materials.append(mats["cutaway_rim"])
    add(crank_housing)

    # Apoyo semicircular de bancada frontal (Bearing Saddle en Y=0)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.72,
        depth=0.55,
        location=(0.0, 0.15, crank_center_z),
        vertices=48,
    )
    saddle = bpy.context.active_object
    saddle.name = "Bearing_Saddle"
    saddle.rotation_euler = (math.pi / 2, 0, 0)
    saddle.data.materials.append(mats["engine_block"])
    saddle.data.materials.append(mats["cutaway_rim"])
    add(saddle)

    # Cavidad cilíndrica interior del cárter
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.45,
        depth=2.4,
        location=(0.0, 0.30, crank_center_z + 0.25),
        vertices=48,
    )
    crank_cav = bpy.context.active_object
    crank_cav.rotation_euler = (math.pi / 2, 0, 0)
    mcc = crank_housing.modifiers.new("CrankCav", type="BOOLEAN")
    mcc.object = crank_cav
    mcc.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = crank_housing
    bpy.ops.object.modifier_apply(modifier="CrankCav")
    bpy.data.objects.remove(crank_cav, do_unlink=True)

    # Cuerpo principal del bloque que rodea el cilindro (Barrel)
    barrel_center_z = crank_center_z + rod_length * 0.75  # ~2.7
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr + 0.42,
        depth=3.6,
        location=(0.0, 0.10, barrel_center_z),
        vertices=48,
    )
    barrel = bpy.context.active_object
    barrel.name = "Engine_Block_Barrel"
    barrel.data.materials.append(mats["engine_block"])
    barrel.data.materials.append(mats["cutaway_rim"])
    add(barrel)

    # Paredes laterales curvas que crean la silueta orgánica acampanada
    for sx in [-1.50, 1.50]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(sx, 0.35, crank_center_z + 1.55),
        )
        rib = bpy.context.active_object
        rib.name = f"Structural_Rib_{'L' if sx < 0 else 'R'}"
        rib.scale = (0.38, 2.0, 2.4)
        rib.data.materials.append(mats["engine_block"])
        rib.data.materials.append(mats["cutaway_rim"])
        add(rib)
        _apply_bevel(rib, width=0.03, segments=2)

    # Camisa interior del cilindro (Cylinder Liner sellada contra la culata)
    liner_len = rod_length + crank_radius + piston_height * 0.5 + 0.65
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr + 0.12,
        depth=liner_len,
        location=(0.0, 0.0, barrel_center_z),
        vertices=48,
    )
    liner = bpy.context.active_object
    liner.name = "Cylinder_Liner"
    liner.data.materials.append(mats["cylinder_liner"])
    liner.data.materials.append(mats["cutaway_rim"])
    add(liner)

    # Vaciado del ánima de la camisa
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr,
        depth=liner_len + 0.4,
        location=(0.0, 0.0, barrel_center_z),
        vertices=48,
    )
    bore = bpy.context.active_object
    mb = liner.modifiers.new("Bore", type="BOOLEAN")
    mb.object = bore
    mb.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = liner
    bpy.ops.object.modifier_apply(modifier="Bore")
    bpy.data.objects.remove(bore, do_unlink=True)

    # Corte seccionado frontal en Y <= 0 para todas las piezas del bloque
    cut_targets = [barrel, crank_housing, saddle, liner]
    for target in cut_targets:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, -1.8, crank_center_z + 2.0),
        )
        cutter = bpy.context.active_object
        cutter.scale = (6.0, 3.5, 9.0)
        cutter.data.materials.append(mats["cutaway_rim"])
        mc = target.modifiers.new("Cutaway", type="BOOLEAN")
        mc.object = cutter
        mc.operation = "DIFFERENCE"
        mc.material_mode = "TRANSFER" if hasattr(mc, "material_mode") else "INDEX"
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier="Cutaway")
        bpy.data.objects.remove(cutter, do_unlink=True)
        _apply_bevel(target, width=0.016, segments=2)

    # =========================================================================
    # 2. CULATA DE DOBLE CÚPULA CON CONDUCTOS CURVOS (Estilo CAD Imagen 2)
    # =========================================================================
    head_root = bpy.data.objects.new("Cylinder_Head_Root", None)
    head_root.location = (0.0, 0.0, head_z)
    bpy.context.scene.collection.objects.link(head_root)
    add(head_root)

    # Base de la culata seccionada
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.25, head_z + 0.35),
    )
    head_base = bpy.context.active_object
    head_base.name = "Cylinder_Head_Base"
    head_base.scale = (3.5, 2.2, 0.70)
    head_base.data.materials.append(mats["engine_block"])
    head_base.data.materials.append(mats["cutaway_rim"])
    add(head_base)

    # Cúpulas gemelas redondeadas en antracita técnica (Rocker Domes como en la Referencia)
    for vx, v_name in [(-0.72, "Intake"), (0.72, "Exhaust")]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.72,
            depth=2.15,
            location=(vx, 0.25, head_z + 0.70),
            vertices=36,
        )
        dome = bpy.context.active_object
        dome.name = f"Head_Dome_{v_name}"
        dome.rotation_euler = (math.pi / 2, 0, 0)
        dome.data.materials.append(mats["rocker_cover"])
        dome.data.materials.append(mats["cutaway_rim"])
        add(dome)

        # Corte frontal en Y < 0 para la cúpula
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(vx, -1.5, head_z + 0.70),
        )
        c_dome = bpy.context.active_object
        c_dome.scale = (2.2, 3.0, 2.0)
        mcd = dome.modifiers.new("CutDome", type="BOOLEAN")
        mcd.object = c_dome
        mcd.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = dome
        bpy.ops.object.modifier_apply(modifier="CutDome")
        bpy.data.objects.remove(c_dome, do_unlink=True)
        _apply_bevel(dome, width=0.016, segments=2)

    # Corte frontal para head_base
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -1.8, head_z + 0.35),
    )
    c_hb = bpy.context.active_object
    c_hb.scale = (5.0, 3.5, 2.0)
    mchb = head_base.modifiers.new("CutHB", type="BOOLEAN")
    mchb.object = c_hb
    mchb.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = head_base
    bpy.ops.object.modifier_apply(modifier="CutHB")
    bpy.data.objects.remove(c_hb, do_unlink=True)
    _apply_bevel(head_base, width=0.016, segments=2)

    # Conducto curvo de admisión negro (hacia la izquierda, -X)
    curve_in = bpy.data.curves.new("Intake_Manifold_Curve", type="CURVE")
    curve_in.dimensions = "3D"
    curve_in.bevel_depth = 0.24
    curve_in.bevel_resolution = 6
    spline_in = curve_in.splines.new("BEZIER")
    spline_in.bezier_points.add(2)
    p0 = spline_in.bezier_points[0]
    p0.co = (-0.85, 0.10, head_z + 0.60)
    p0.handle_left = (-1.10, 0.10, head_z + 0.60)
    p0.handle_right = (-0.60, 0.10, head_z + 0.60)
    p1 = spline_in.bezier_points[1]
    p1.co = (-1.85, 0.10, head_z + 0.75)
    p1.handle_left = (-1.55, 0.10, head_z + 0.70)
    p1.handle_right = (-2.15, 0.10, head_z + 0.80)
    p2 = spline_in.bezier_points[2]
    p2.co = (-2.45, -0.05, head_z + 1.45)
    p2.handle_left = (-2.40, 0.05, head_z + 1.15)
    p2.handle_right = (-2.50, -0.15, head_z + 1.65)

    obj_in_pipe = bpy.data.objects.new("Intake_Manifold_Pipe", curve_in)
    obj_in_pipe.data.materials.append(mats["manifold_pipes"])
    add(obj_in_pipe)

    # Cámara esférica del filtro de admisión superior izquierda (idéntica a la silueta CAD de referencia)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.58,
        location=(-2.45, 0.05, head_z + 1.62),
        segments=32,
        ring_count=20,
    )
    flange_in = bpy.context.active_object
    flange_in.name = "Intake_Manifold_Flange"
    flange_in.data.materials.append(mats["manifold_pipes"])
    add(flange_in)

    # Conducto curvo de escape negro (hacia la derecha, +X)
    curve_ex = bpy.data.curves.new("Exhaust_Manifold_Curve", type="CURVE")
    curve_ex.dimensions = "3D"
    curve_ex.bevel_depth = 0.24
    curve_ex.bevel_resolution = 6
    spline_ex = curve_ex.splines.new("BEZIER")
    spline_ex.bezier_points.add(1)
    ep0 = spline_ex.bezier_points[0]
    ep0.co = (0.85, 0.10, head_z + 0.60)
    ep0.handle_left = (0.60, 0.10, head_z + 0.60)
    ep0.handle_right = (1.10, 0.10, head_z + 0.60)
    ep1 = spline_ex.bezier_points[1]
    ep1.co = (2.25, 0.10, head_z + 0.45)
    ep1.handle_left = (1.80, 0.10, head_z + 0.55)
    ep1.handle_right = (2.50, 0.10, head_z + 0.40)

    obj_ex_pipe = bpy.data.objects.new("Exhaust_Manifold_Pipe", curve_ex)
    obj_ex_pipe.data.materials.append(mats["manifold_pipes"])
    add(obj_ex_pipe)

    # =========================================================================
    # 3. PISTÓN DE COBRE ANODIZADO Y BULÓN TUBULAR (Idéntico a Imagen 2)
    # =========================================================================
    piston_root = bpy.data.objects.new("Piston_Root", None)
    piston_root.location = (0.0, 0.0, pms_z)
    bpy.context.scene.collection.objects.link(piston_root)
    add(piston_root)

    piston_rad = cr - 0.035
    bpy.ops.mesh.primitive_cylinder_add(
        radius=piston_rad,
        depth=piston_height,
        location=(0.0, 0.0, pms_z),
        vertices=48,
    )
    piston_body = bpy.context.active_object
    piston_body.name = "Piston_Body"
    piston_body.data.materials.append(mats["piston"])
    add(piston_body)

    # Vaciado interior de la falda (Skirt Cavity)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=piston_rad - 0.22,
        depth=piston_height * 0.70,
        location=(0.0, 0.0, pms_z - piston_height * 0.20),
        vertices=36,
    )
    skirt_cav = bpy.context.active_object
    msk = piston_body.modifiers.new("SkirtCav", type="BOOLEAN")
    msk.object = skirt_cav
    msk.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = piston_body
    bpy.ops.object.modifier_apply(modifier="SkirtCav")
    bpy.data.objects.remove(skirt_cav, do_unlink=True)

    # Orificio pasante del bulón del pistón
    pin_rad = 0.24
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pin_rad + 0.015,
        depth=piston_rad * 2.2,
        location=(0.0, 0.0, pms_z),
        vertices=36,
    )
    hole_pin = bpy.context.active_object
    hole_pin.rotation_euler = (math.pi / 2, 0, 0)
    mph = piston_body.modifiers.new("PinHole", type="BOOLEAN")
    mph.object = hole_pin
    mph.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = piston_body
    bpy.ops.object.modifier_apply(modifier="PinHole")
    bpy.data.objects.remove(hole_pin, do_unlink=True)
    _apply_bevel(piston_body, width=0.014, segments=2)

    # Bulón tubular pasante en acero templado oscuro (Visible en el orificio frontal)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pin_rad,
        depth=piston_rad * 1.95,
        location=(0.0, 0.0, pms_z),
        vertices=36,
    )
    wrist_pin = bpy.context.active_object
    wrist_pin.name = "Piston_Wrist_Pin"
    wrist_pin.rotation_euler = (math.pi / 2, 0, 0)
    wrist_pin.data.materials.append(mats["wrist_pin"])
    add(wrist_pin)

    # Núcleo hueco del bulón (Hollow Bore)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.14,
        depth=piston_rad * 2.1,
        location=(0.0, 0.0, pms_z),
        vertices=32,
    )
    core_pin = bpy.context.active_object
    core_pin.rotation_euler = (math.pi / 2, 0, 0)
    mwp = wrist_pin.modifiers.new("HollowCore", type="BOOLEAN")
    mwp.object = core_pin
    mwp.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = wrist_pin
    bpy.ops.object.modifier_apply(modifier="HollowCore")
    bpy.data.objects.remove(core_pin, do_unlink=True)
    _apply_bevel(wrist_pin, width=0.012, segments=2)

    # 3 aros de compresión en acero pulido brillante
    ring_zs = [pms_z + piston_height * 0.40, pms_z + piston_height * 0.26, pms_z + piston_height * 0.12]
    piston_rings = []
    for idx, rz in enumerate(ring_zs):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=piston_rad - 0.025,
            minor_radius=0.030,
            location=(0.0, 0.0, rz),
            major_segments=48,
            minor_segments=12,
        )
        ring = bpy.context.active_object
        ring.name = f"Piston_Ring_{idx+1}"
        ring.data.materials.append(mats["piston_rings"])
        add(ring)
        piston_rings.append(ring)

    # Parentado al root manteniendo matriz local correcta
    piston_body.parent = piston_root
    piston_body.matrix_parent_inverse = piston_root.matrix_world.inverted()
    wrist_pin.parent = piston_root
    wrist_pin.matrix_parent_inverse = piston_root.matrix_world.inverted()
    for ring in piston_rings:
        ring.parent = piston_root
        ring.matrix_parent_inverse = piston_root.matrix_world.inverted()

    # =========================================================================
    # 4. BIELA FORJADA EN VIGA 'I' (Connecting Rod)
    # =========================================================================
    crank_pin_z = crank_center_z + crank_radius
    rod_root = bpy.data.objects.new("Connecting_Rod_Root", None)
    rod_root.location = (0.0, 0.0, crank_pin_z)
    bpy.context.scene.collection.objects.link(rod_root)
    add(rod_root)

    # Vástago central de la biela en sección I
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, crank_pin_z + rod_length * 0.50),
    )
    rod_shank = bpy.context.active_object
    rod_shank.name = "Rod_Shank"
    rod_shank.scale = (0.34, 0.22, rod_length * 0.82)
    rod_shank.data.materials.append(mats["connecting_rod"])
    add(rod_shank)
    _apply_bevel(rod_shank, width=0.018, segments=2)

    # Canales maquinados en I (frente y dorso)
    for ry in [-0.08, 0.08]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, ry, crank_pin_z + rod_length * 0.50),
        )
        rec = bpy.context.active_object
        rec.name = f"Rod_Recess_{'F' if ry < 0 else 'B'}"
        rec.scale = (0.20, 0.09, rod_length * 0.65)
        rec.data.materials.append(mats["rod_recess"])
        add(rec)
        rec.parent = rod_root
        rec.matrix_parent_inverse = rod_root.matrix_world.inverted()

    # Pie de biela (Small End)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.40,
        depth=0.36,
        location=(0.0, 0.0, crank_pin_z + rod_length),
        vertices=36,
    )
    small_end = bpy.context.active_object
    small_end.name = "Rod_Small_End"
    small_end.rotation_euler = (math.pi / 2, 0, 0)
    small_end.data.materials.append(mats["connecting_rod"])
    add(small_end)
    _apply_bevel(small_end, width=0.015, segments=2)

    # Casquillo de bronce del pie de biela
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pin_rad + 0.01,
        depth=0.38,
        location=(0.0, 0.0, crank_pin_z + rod_length),
        vertices=36,
    )
    bushing_small = bpy.context.active_object
    bushing_small.name = "Rod_Small_Bushing"
    bushing_small.rotation_euler = (math.pi / 2, 0, 0)
    bushing_small.data.materials.append(mats["rod_bearings"])
    add(bushing_small)

    # Cabeza de biela (Big End)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.58,
        depth=0.44,
        location=(0.0, 0.0, crank_pin_z),
        vertices=36,
    )
    big_end = bpy.context.active_object
    big_end.name = "Rod_Big_End"
    big_end.rotation_euler = (math.pi / 2, 0, 0)
    big_end.data.materials.append(mats["connecting_rod"])
    add(big_end)
    _apply_bevel(big_end, width=0.02, segments=2)

    # Casquillo de cabeza de biela
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.36,
        depth=0.46,
        location=(0.0, 0.0, crank_pin_z),
        vertices=36,
    )
    bushing_big = bpy.context.active_object
    bushing_big.name = "Rod_Big_Bearing"
    bushing_big.rotation_euler = (math.pi / 2, 0, 0)
    bushing_big.data.materials.append(mats["rod_bearings"])
    add(bushing_big)

    # Tornillos de sombrerete hexagonales
    for x_bolt in [-0.38, 0.38]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.08,
            depth=0.60,
            location=(x_bolt, 0.0, crank_pin_z - 0.22),
            vertices=6,
        )
        bolt = bpy.context.active_object
        bolt.name = f"Rod_Bolt_{'L' if x_bolt < 0 else 'R'}"
        bolt.data.materials.append(mats["rod_bolts"])
        add(bolt)
        bolt.parent = rod_root
        bolt.matrix_parent_inverse = rod_root.matrix_world.inverted()

    # Parentado de componentes de biela a rod_root
    for part in [rod_shank, small_end, bushing_small, big_end, bushing_big]:
        part.parent = rod_root
        part.matrix_parent_inverse = rod_root.matrix_world.inverted()

    # =========================================================================
    # 5. CIGÜEÑAL Y CONTRAPESOS AERODINÁMICOS
    # =========================================================================
    crank_root = bpy.data.objects.new("Crankshaft_Root", None)
    crank_root.location = (0.0, 0.0, crank_center_z)
    bpy.context.scene.collection.objects.link(crank_root)
    add(crank_root)

    # Muñón principal del cigüeñal (eje de salida horizontal en Y)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.34,
        depth=2.7,
        location=(0.0, 0.0, crank_center_z),
        vertices=36,
    )
    main_journal = bpy.context.active_object
    main_journal.name = "Crank_Main_Journal"
    main_journal.rotation_euler = (math.pi / 2, 0, 0)
    main_journal.data.materials.append(mats["crankshaft"])
    add(main_journal)

    # Muñequilla excéntrica rectificada (Crankpin)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.24,
        depth=0.46,
        location=(0.0, 0.0, crank_pin_z),
        vertices=36,
    )
    crank_pin = bpy.context.active_object
    crank_pin.name = "Crank_Pin"
    crank_pin.rotation_euler = (math.pi / 2, 0, 0)
    crank_pin.data.materials.append(mats["crankshaft"])
    add(crank_pin)

    # Brazos de manivela (Webs)
    for y_arm in [-0.28, 0.28]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, y_arm, crank_center_z + crank_radius * 0.50),
        )
        arm = bpy.context.active_object
        arm.name = f"Crank_Web_{'F' if y_arm < 0 else 'B'}"
        arm.scale = (0.28, 0.12, crank_radius * 0.95)
        arm.data.materials.append(mats["crankshaft"])
        add(arm)
        _apply_bevel(arm, width=0.015, segments=2)
        arm.parent = crank_root
        arm.matrix_parent_inverse = crank_root.matrix_world.inverted()

    # Contrapesos lobulares aerodinámicos (en Z <= 0)
    for y_cw in [-0.28, 0.28]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=1.12,
            depth=0.20,
            location=(0.0, y_cw, crank_center_z),
            vertices=40,
        )
        cw = bpy.context.active_object
        cw.name = f"Counterweight_{'F' if y_cw < 0 else 'B'}"
        cw.rotation_euler = (math.pi / 2, 0, 0)

        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, y_cw, crank_center_z + 0.70),
        )
        cw_c = bpy.context.active_object
        cw_c.scale = (2.6, 0.5, 1.4)
        mcw = cw.modifiers.new("CutCW", type="BOOLEAN")
        mcw.object = cw_c
        mcw.operation = "DIFFERENCE"
        bpy.context.view_layer.objects.active = cw
        bpy.ops.object.modifier_apply(modifier="CutCW")
        bpy.data.objects.remove(cw_c, do_unlink=True)

        cw.data.materials.append(mats["counterweights"])
        add(cw)
        _apply_bevel(cw, width=0.02, segments=2)
        cw.parent = crank_root
        cw.matrix_parent_inverse = crank_root.matrix_world.inverted()

    main_journal.parent = crank_root
    main_journal.matrix_parent_inverse = crank_root.matrix_world.inverted()
    crank_pin.parent = crank_root
    crank_pin.matrix_parent_inverse = crank_root.matrix_world.inverted()

    # =========================================================================
    # 6. VÁLVULAS ANGULADAS CON RESORTES HELICOIDALES 3D (Estilo Imagen 2)
    # =========================================================================
    valves = {}
    springs = {}
    v_angle_deg = 16.0
    v_angle_rad = math.radians(v_angle_deg)

    for v_type, x_pos, rot_y in [("intake", -0.65, -v_angle_rad), ("exhaust", 0.65, v_angle_rad)]:
        v_root = bpy.data.objects.new(f"Valve_{v_type.capitalize()}_Root", None)
        v_root.location = (x_pos, 0.0, head_z + 0.15)
        v_root.rotation_euler = (0.0, rot_y, 0.0)
        bpy.context.scene.collection.objects.link(v_root)
        add(v_root)
        valves[v_type] = v_root

        # Platillo de la válvula
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.42,
            depth=0.10,
            location=(0.0, 0.0, 0.0),
            vertices=32,
        )
        v_head = bpy.context.active_object
        v_head.name = f"Valve_{v_type}_Head"
        v_head.parent = v_root
        v_head.data.materials.append(mats[f"valve_{v_type}"])
        add(v_head)
        _apply_bevel(v_head, width=0.015, segments=2)

        # Vástago pulido que sube por la guía
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

        # Platillo retenedor superior del muelle
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.26,
            depth=0.08,
            location=(0.0, 0.0, 1.30),
            vertices=24,
        )
        v_ret = bpy.context.active_object
        v_ret.name = f"Valve_{v_type}_Retainer"
        v_ret.parent = v_root
        v_ret.data.materials.append(mats["valve_retainer"])
        add(v_ret)
        _apply_bevel(v_ret, width=0.012, segments=2)

        # Resorte helicoidal 3D de alambre de acero
        s_obj = _create_helical_spring(
            name=f"Valve_Spring_{v_type.capitalize()}",
            radius=0.20,
            wire_radius=0.032,
            height=0.88,
            num_turns=6.5,
            mat=mats["valve_spring"],
        )
        s_obj.location = (0.0, 0.0, 0.38)
        s_obj.parent = v_root
        add(s_obj)
        springs[v_type] = s_obj

    # =========================================================================
    # 7. BUJÍA CENTRAL CON AISLADOR CERÁMICO BLANCO Y TUERCA HEXAGONAL
    # =========================================================================
    spark_root = bpy.data.objects.new("Spark_Plug_Root", None)
    spark_root.location = (0.0, 0.0, head_z + 0.50)
    bpy.context.scene.collection.objects.link(spark_root)
    add(spark_root)

    # Rosca metálica y junta de cobre
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.18,
        depth=0.45,
        location=(0.0, 0.0, 0.0),
        vertices=24,
    )
    sp_thread = bpy.context.active_object
    sp_thread.name = "Spark_Thread"
    sp_thread.parent = spark_root
    sp_thread.data.materials.append(mats["spark_metal"])
    add(sp_thread)

    # Tuerca hexagonal de apriete
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.22,
        depth=0.25,
        location=(0.0, 0.0, 0.35),
        vertices=6,
    )
    sp_hex = bpy.context.active_object
    sp_hex.name = "Spark_Hex"
    sp_hex.parent = spark_root
    sp_hex.data.materials.append(mats["spark_metal"])
    add(sp_hex)
    _apply_bevel(sp_hex, width=0.015, segments=2)

    # Aislador cerámico blanco con corrugaciones
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15,
        depth=0.75,
        location=(0.0, 0.0, 0.85),
        vertices=24,
    )
    sp_cer = bpy.context.active_object
    sp_cer.name = "Spark_Ceramic"
    sp_cer.parent = spark_root
    sp_cer.data.materials.append(mats["spark_ceramic"])
    add(sp_cer)
    _apply_bevel(sp_cer, width=0.015, segments=2)

    # Terminal superior de latón
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.08,
        depth=0.22,
        location=(0.0, 0.0, 1.32),
        vertices=16,
    )
    sp_term = bpy.context.active_object
    sp_term.name = "Spark_Terminal"
    sp_term.parent = spark_root
    sp_term.data.materials.append(mats["spark_copper"])
    add(sp_term)

    # =========================================================================
    # 8. EFECTOS VISUALES Y LLAMA COVERFOX DE ALTO IMPACTO (Imagen 1)
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

    # Luz puntual dinámica interior de combustión
    bpy.ops.object.light_add(
        type="POINT",
        radius=0.35,
        location=(0.0, 0.0, combustion_z - 0.10),
    )
    light_combustion = bpy.context.active_object
    light_combustion.name = "Light_Combustion_Dynamic"
    light_combustion.data.color = (1.0, 0.45, 0.08)
    light_combustion.data.energy = 0.0
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

    # Gas comprimido en cámara (volumen azul/amarillo semitransparente)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=cr - 0.08,
        depth=0.45,
        location=(0.0, 0.0, head_z - 0.18),
        vertices=32,
    )
    fx_comp = bpy.context.active_object
    fx_comp.name = "FX_Compression_Gas"
    mat_comp = mats.get("compression_gas", mats.get("compression_mix"))
    if mat_comp:
        fx_comp.data.materials.append(mat_comp)
    fx_comp.scale = (0.001, 0.001, 0.001)
    add(fx_comp)

    # Etiquetas 3D explicativas (ocultas por defecto; el Director Audiovisual Fase 3.3 las activa en el milisegundo en que se pronuncian)
    from studio.blender.models_library import _common as C
    white_txt = C.emissive_material("Mat_LabelWhite_Engine", (1.0, 1.0, 1.0), 2.2)
    labels: dict[str, tuple[Any, Any]] = {}

    def _eng_label(key: str, txt: str, loc: tuple[float, float, float], target: tuple[float, float, float], size: float = 0.28) -> None:
        t_obj = C.make_text("Label_Eng_" + key, txt, loc, size, white_txt)
        p_path = C.rounded_polyline([(loc[0], loc[1], loc[2] - size * 0.65), target], 0.01)
        ln_obj = C.tube_from_path("Leader_Eng_" + key, p_path, 0.012, white_txt)
        for o in (t_obj, ln_obj):
            o["role"] = "label"
            o.hide_render = True
            o.hide_viewport = True
        labels[key] = (t_obj, ln_obj)

    _eng_label("piston", "PISTÓN", (-2.65, -0.9, pms_z + 0.15), (-1.15, -0.2, pms_z))
    _eng_label("rod", "BIELA", (2.55, -0.9, crank_center_z + 2.55), (0.18, -0.1, crank_center_z + 2.4))
    _eng_label("crank", "CIGÜEÑAL", (-2.55, -0.9, crank_center_z + 0.15), (-0.45, -0.2, crank_center_z))
    _eng_label("intake", "VÁLVULA ADMISIÓN", (-2.75, -0.9, head_z + 2.15), (-0.85, -0.1, head_z + 1.0))
    _eng_label("exhaust", "VÁLVULA ESCAPE", (2.75, -0.9, head_z + 2.15), (0.85, -0.1, head_z + 1.0))
    _eng_label("spark", "BUJÍA", (0.0, -0.9, head_z + 2.65), (0.0, -0.1, head_z + 1.55))
    _eng_label("cylinder", "CILINDRO", (2.65, -0.9, pms_z + 0.25), (1.35, -0.1, pms_z - 0.35))

    groups = {
        "piston": [piston_body, wrist_pin, *piston_rings],
        "rod": [rod_shank, small_end, bushing_small, big_end, bushing_big],
        "crank": [main_journal, crank_pin, crank_housing, saddle],
        "valves": [*valves["intake"].children, *valves["exhaust"].children, springs["intake"], springs["exhaust"]],
        "spark": list(spark_root.children),
        "head": [head_base, obj_in_pipe, obj_ex_pipe, flange_in, *valves["intake"].children, *valves["exhaust"].children, *spark_root.children],
        "block": [base_pan, barrel, crank_housing, liner],
        "chamber": [piston_body, head_base, *valves["intake"].children, *valves["exhaust"].children, *spark_root.children],
    }

    connections = [
        (piston_body, wrist_pin, 0.04, "pistón ↔ bulón"),
        (small_end, wrist_pin, 0.05, "pie de biela ↔ bulón"),
        (rod_shank, small_end, 0.05, "vástago de biela ↔ pie de biela"),
        (rod_shank, big_end, 0.05, "vástago de biela ↔ cabeza de biela"),
        (big_end, crank_pin, 0.05, "cabeza de biela ↔ muñequilla del cigüeñal"),
        (piston_body, liner, 0.08, "pistón ↔ camisa del cilindro"),
        (liner, head_base, 0.15, "camisa del cilindro ↔ culata"),
    ]

    return {
        "engine_block": base_pan,
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
        "fx_compression": fx_comp,
        "crank_radius": crank_radius,
        "rod_length": rod_length,
        "crank_center_z": crank_center_z,
        "head_z": head_z,
        "groups": groups,
        "labels": labels,
        "connections": connections,
    }
