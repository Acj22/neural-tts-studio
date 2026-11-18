"""Utilidades geométricas compartidas por los modelos procedurales (Fase 3.1).

Todo se genera con código propio de Blender (sin assets externos => sin licencias de terceros).
Convenciones: cámara frontal mira hacia +Y; X derecha; Z arriba.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

try:
    import bpy
    import bmesh
    import mathutils
    from mathutils import Vector
except ImportError:  # pragma: no cover
    bpy = None
    bmesh = None
    mathutils = None
    Vector = None


# ---------------------------------------------------------------------------
# Básicos
# ---------------------------------------------------------------------------

def smooth(obj: Any) -> Any:
    try:
        for p in obj.data.polygons:
            p.use_smooth = True
    except Exception:
        pass
    return obj


def bevel(obj: Any, width: float = 0.015, segments: int = 2) -> None:
    try:
        m = obj.modifiers.new("Bevel", type="BEVEL")
        m.width = width
        m.segments = segments
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(35.0)
    except Exception:
        pass


def set_mat(obj: Any, mat: Any) -> Any:
    if mat is not None and hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)
    return obj


def mesh_object(name: str, verts: list, faces: list, mat: Any = None, flat: bool = False, recalc: bool = True) -> Any:
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = not flat
    set_mat(obj, mat)
    return obj


def empty(name: str, loc: Sequence[float] = (0, 0, 0), parent: Any = None) -> Any:
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.2
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


def cylinder(name: str, r: float, length: float, center: Sequence[float], axis: str = "Z",
             mat: Any = None, verts: int = 32, parent: Any = None, r2: float | None = None,
             flat: bool = False) -> Any:
    """Cilindro/cono alineado a un eje ('X','Y','Z') con centro dado (coordenadas mundo)."""
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=length, location=center)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=length, location=center)
    o = bpy.context.active_object
    o.name = name
    if axis == "X":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    for p in o.data.polygons:
        p.use_smooth = not flat
    set_mat(o, mat)
    if parent is not None:
        keep_parent(o, parent)
    return o


def box(name: str, size: Sequence[float], center: Sequence[float], mat: Any = None,
        parent: Any = None, bev: float = 0.0) -> Any:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(size)
    set_mat(o, mat)
    if bev:
        # aplicar escala para que el bisel sea uniforme
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel(o, bev, 2)
    if parent is not None:
        keep_parent(o, parent)
    return o


def sphere(name: str, r: float, center: Sequence[float], mat: Any = None, seg: int = 16, parent: Any = None) -> Any:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(6, seg // 2), radius=r, location=center)
    o = bpy.context.active_object
    o.name = name
    smooth(o)
    set_mat(o, mat)
    if parent is not None:
        keep_parent(o, parent)
    return o


def keep_parent(child: Any, parent: Any) -> None:
    """Parentea conservando la transformación mundial actual."""
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


def tag(obj: Any, group: str) -> Any:
    """Etiqueta de componente (para QC, foco de cámara y animación)."""
    obj["comp_group"] = group
    return obj


# ---------------------------------------------------------------------------
# Engranajes (ejes a lo largo de Y; perfil en el plano XZ)
# ---------------------------------------------------------------------------

def _loops_to_mesh(name: str, outer: list, inner: list | None, y0: float, y1: float,
                   cx: float, cz: float, mat: Any, flat: bool = True) -> Any:
    """Prisma de anillo: 'outer' e 'inner' son listas (x,z) del mismo tamaño (o inner=None => disco)."""
    n = len(outer)
    verts: list = []
    for y in (y0, y1):
        for (x, z) in outer:
            verts.append((cx + x, y, cz + z))
    if inner:
        for y in (y0, y1):
            for (x, z) in inner:
                verts.append((cx + x, y, cz + z))
    else:
        verts.append((cx, y0, cz))
        verts.append((cx, y1, cz))
    faces: list = []
    o0, o1 = 0, n
    # pared exterior
    for i in range(n):
        j = (i + 1) % n
        faces.append((o0 + i, o0 + j, o1 + j, o1 + i))
    if inner:
        i0, i1 = 2 * n, 3 * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((i0 + i, i1 + i, i1 + j, i0 + j))
            faces.append((o0 + i, i0 + i, i0 + j, o0 + j))   # tapa y0
            faces.append((o1 + i, o1 + j, i1 + j, i1 + i))   # tapa y1
    else:
        c0, c1 = 2 * n, 2 * n + 1
        for i in range(n):
            j = (i + 1) % n
            faces.append((c0, o0 + j, o0 + i))
            faces.append((c1, o1 + i, o1 + j))
    return mesh_object(name, verts, faces, mat, flat=flat)


def gear_profile(n: int, r_pitch: float, module: float, internal: bool = False, phase: float = 0.0) -> list:
    """Perfil trapezoidal de dientes. Para engranaje interno los dientes apuntan hacia el centro."""
    add = module * 1.0
    ded = module * 1.15
    p = 2 * math.pi / n
    if internal:
        r_tip, r_root = r_pitch - add, r_pitch + ded
    else:
        r_tip, r_root = r_pitch + add, r_pitch - ded
    pts = []
    for j in range(n):
        c = phase + j * p
        for off, r in ((-0.30, r_root), (-0.17, r_tip), (0.17, r_tip), (0.30, r_root)):
            a = c + off * p
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def make_gear(name: str, n: int, r_pitch: float, module: float, width: float, center: Sequence[float],
              mat: Any, hole_r: float = 0.0, phase: float = 0.0) -> Any:
    """Engranaje externo con eje Y; 'center' = (x, y_medio, z). Origen del objeto en el centro del eje."""
    outer = gear_profile(n, r_pitch, module, False, phase)
    if hole_r > 0:
        inner = [(hole_r * math.cos(math.atan2(z, x)), hole_r * math.sin(math.atan2(z, x))) for (x, z) in outer]
    else:
        inner = None
    cx, cy, cz = center
    obj = _loops_to_mesh(name, outer, inner, -width / 2, width / 2, 0.0, 0.0, mat)
    obj.location = (cx, cy, cz)
    return obj


def make_ring_gear(name: str, n: int, r_pitch: float, module: float, r_out: float, width: float,
                   center: Sequence[float], mat: Any, phase: float = 0.0) -> Any:
    """Corona (engranaje interno) con eje Y."""
    inner = gear_profile(n, r_pitch, module, True, phase)
    outer = [(r_out * math.cos(math.atan2(z, x)), r_out * math.sin(math.atan2(z, x))) for (x, z) in inner]
    obj = _loops_to_mesh(name, outer, inner, -width / 2, width / 2, 0.0, 0.0, mat)
    obj.location = tuple(center)
    return obj


def revolve(name: str, profile: Sequence[tuple[float, float]], a0: float, a1: float, steps: int,
            mat: Any = None, thickness: float = 0.0, center: Sequence[float] = (0, 0, 0)) -> Any:
    """Superficie de revolución alrededor del eje Y. profile=[(r,y)...]; ángulos en rad (medidos de +X hacia +Z)."""
    verts = []
    cols = len(profile)
    for s in range(steps + 1):
        a = a0 + (a1 - a0) * s / steps
        for (r, y) in profile:
            verts.append((r * math.cos(a), y, r * math.sin(a)))
    faces = []
    for s in range(steps):
        for i in range(cols - 1):
            a_ = s * cols + i
            b_ = s * cols + i + 1
            c_ = (s + 1) * cols + i + 1
            d_ = (s + 1) * cols + i
            faces.append((a_, b_, c_, d_))
    obj = mesh_object(name, verts, faces, mat, flat=False)
    obj.location = tuple(center)
    if thickness > 0:
        m = obj.modifiers.new("Solid", type="SOLIDIFY")
        m.thickness = thickness
        m.offset = 0.0
    return obj


# ---------------------------------------------------------------------------
# Tuberías continuas con codos soldados
# ---------------------------------------------------------------------------

def rounded_polyline(points: Sequence[Sequence[float]], elbow_r: float = 0.12, res: int = 6) -> list:
    """Convierte vértices en trayectoria densa con esquinas redondeadas (curva de Bézier cuadrática)."""
    pts = [Vector(p) for p in points]
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d1 = (a - b)
        d2 = (c - b)
        l1, l2 = d1.length, d2.length
        if l1 < 1e-6 or l2 < 1e-6:
            continue
        r = min(elbow_r, l1 * 0.49, l2 * 0.49)
        p1 = b + d1.normalized() * r
        p2 = b + d2.normalized() * r
        for k in range(res + 1):
            t = k / res
            q = (1 - t) ** 2 * p1 + 2 * (1 - t) * t * b + t * t * p2
            out.append(q)
    out.append(pts[-1])
    return out


def path_length(path: Sequence[Any]) -> float:
    return sum((path[i + 1] - path[i]).length for i in range(len(path) - 1))


def path_point(path: Sequence[Any], s: float) -> Any:
    """Punto a fracción s∈[0,1] de la longitud de arco."""
    total = path_length(path)
    target = (s % 1.0) * total
    acc = 0.0
    for i in range(len(path) - 1):
        seg = (path[i + 1] - path[i]).length
        if acc + seg >= target and seg > 1e-9:
            return path[i].lerp(path[i + 1], (target - acc) / seg)
        acc += seg
    return path[-1].copy()


def tube_from_path(name: str, path: Sequence[Any], radius: float, mat: Any = None, res_u: int = 3,
                   bevel_res: int = 5) -> Any:
    cd = bpy.data.curves.new(name + "_curve", type="CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = radius
    cd.bevel_resolution = bevel_res
    cd.resolution_u = res_u
    cd.use_fill_caps = True
    sp = cd.splines.new("POLY")
    sp.points.add(len(path) - 1)
    for i, p in enumerate(path):
        sp.points[i].co = (p.x, p.y, p.z, 1.0)
    obj = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(obj)
    set_mat(obj, mat)
    return obj


def helix_path(center: Sequence[float], axis: str, length: float, radius: float, turns: float,
               pts_per_turn: int = 14) -> list:
    """Trayectoria helicoidal a lo largo de un eje, comienza en el centro del eje en 'center' (extremo inicial)."""
    cx, cy, cz = center
    n = int(turns * pts_per_turn)
    out = []
    for i in range(n + 1):
        f = i / n
        th = f * turns * 2 * math.pi
        a, b = radius * math.cos(th), radius * math.sin(th)
        if axis == "X":
            out.append(Vector((cx + f * length, cy + a, cz + b)))
        elif axis == "Y":
            out.append(Vector((cx + a, cy + f * length, cz + b)))
        else:
            out.append(Vector((cx + a, cy + b, cz + f * length)))
    return out


# ---------------------------------------------------------------------------
# Animación
# ---------------------------------------------------------------------------

def set_interp(kind: str = "LINEAR") -> None:
    """Interpolación por defecto de nuevos keyframes (compatible con Blender 5.x)."""
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = kind
    except Exception:
        pass


def key(obj: Any, path: str, frame: int, index: int = -1) -> None:
    obj.keyframe_insert(data_path=path, frame=frame, index=index) if index >= 0 else obj.keyframe_insert(data_path=path, frame=frame)


def key_visibility(obj: Any, visible: bool, frame: int) -> None:
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)


def make_text(name: str, text: str, loc: Sequence[float], size: float = 0.3, mat: Any = None,
              rot: Sequence[float] = (math.pi / 2, 0, 0)) -> Any:
    cu = bpy.data.curves.new(name + "_txt", type="FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.extrude = 0.02
    cu.bevel_depth = 0.004
    obj = bpy.data.objects.new(name, cu)
    obj.location = loc
    obj.rotation_euler = rot
    bpy.context.scene.collection.objects.link(obj)
    set_mat(obj, mat)
    return obj


def emissive_material(name: str, color: Sequence[float], strength: float = 3.0, alpha: float = 1.0) -> Any:
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = (*color[:3], 1.0)
        b.inputs["Roughness"].default_value = 0.35
        if "Emission Color" in b.inputs:
            b.inputs["Emission Color"].default_value = (*color[:3], 1.0)
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = strength
        if alpha < 1.0 and "Alpha" in b.inputs:
            b.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
    return m


def make_arrow(name: str, length: float, radius: float, mat: Any) -> Any:
    """Flecha (+X local) formada por fuste + cabeza cónica, unidas bajo un empty."""
    root = empty(name)
    shaft_len = length * 0.65
    c1 = cylinder(name + "_shaft", radius, shaft_len, (shaft_len / 2, 0, 0), "X", mat, 12)
    head_len = length * 0.35
    c2 = cylinder(name + "_head", radius * 2.4, head_len, (shaft_len + head_len / 2, 0, 0), "X", mat, 14, r2=0.0)
    for c in (c1, c2):
        c.parent = root
    root["is_arrow"] = True
    return root
