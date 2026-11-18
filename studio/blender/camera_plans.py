"""Cámaras por plan con encuadre automático (Fase 3.1) — se ejecuta dentro de Blender.

El director visual (Python puro) decide *qué* mostrar y *por qué*; este módulo calcula *dónde* poner
la cámara para que los componentes importantes JAMÁS queden cortados:

  distancia mínima  d >= max_p [ q_p + |x_p| / (tan_x·(1-m)),  q_p + |y_p| / (tan_y·(1-m)) ]

donde (x_p, y_p, q_p) son las coordenadas del punto p en la base de la cámara. Cada clave del plan
define azimut/elevación/holgura (pad >= 0) por lo que la cámara solo puede acercarse hasta el
encuadre ajustado del grupo objetivo, nunca más.
"""

from __future__ import annotations

import math
from typing import Any

try:
    import bpy
    from mathutils import Vector
except ImportError:  # pragma: no cover
    bpy = None
    Vector = None

_EXCLUDE_PREFIX = ("Studio_", "Director_")


def _frame_points(scene: Any, frame: int, objs: list | None) -> list:
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    pts = []
    if objs is not None:
        visible_labels = [o for o in scene.objects if o.get("role") == "label" and not o.hide_render]
        pool = list(objs) + visible_labels
    else:
        pool = list(scene.objects)
    for o in pool:
        if o.type not in ("MESH", "CURVE", "FONT"):
            continue
        if o.name.startswith(_EXCLUDE_PREFIX):
            continue
        if o.hide_render:
            continue
        ev = o.evaluated_get(dg)
        mw = ev.matrix_world
        try:
            corners = ev.bound_box
        except Exception:
            continue
        for c in corners:
            pts.append(mw @ Vector(c))
    return pts


def _basis(az: float, el: float):
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))  # de objetivo a cámara
    f = -d
    right = f.cross(Vector((0, 0, 1)))
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(f).normalized()
    return d, right, up


def _tans(lens: float, w: int, h: int, sensor: float = 36.0) -> tuple[float, float]:
    half = (sensor / 2.0) / lens
    if w >= h:
        return half, half * h / w
    return half * w / h, half


def fit(points: list, az: float, el: float, lens: float, w: int, h: int, margin: float = 0.07) -> tuple[Any, float]:
    """Devuelve (objetivo T centrado en pantalla, distancia mínima de encuadre)."""
    d_vec, right, up = _basis(az, el)
    tx, ty = _tans(lens, w, h)
    k = 1.0 - margin
    T = sum(points, Vector((0, 0, 0))) / max(1, len(points))
    dist = 10.0
    for _ in range(3):
        xs = [(p - T).dot(right) for p in points]
        ys = [(p - T).dot(up) for p in points]
        T = T + right * ((max(xs) + min(xs)) / 2.0) + up * ((max(ys) + min(ys)) / 2.0)
        dist = 0.0
        for p in points:
            v = p - T
            q = v.dot(d_vec)
            dist = max(dist, q + abs(v.dot(right)) / (tx * k), q + abs(v.dot(up)) / (ty * k))
    return T, dist


def project_inside(points: list, cam_pos: Any, target: Any, lens: float, w: int, h: int) -> float:
    """Fracción de puntos dentro del cuadro (0..1) para el QC."""
    if not points:
        return 1.0
    f = (target - cam_pos).normalized()
    right = f.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(f).normalized()
    tx, ty = _tans(lens, w, h)
    ok = 0
    for p in points:
        v = p - cam_pos
        z = v.dot(f)
        if z <= 0.01:
            continue
        if abs(v.dot(right)) <= z * tx and abs(v.dot(up)) <= z * ty:
            ok += 1
    return ok / len(points)


def apply_camera_plan(plan: dict[str, Any], data: dict[str, Any] | None, width: int, height: int,
                      f0: int, f1: int) -> dict[str, Any]:
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("Director_Camera")
    cam_obj = bpy.data.objects.new("Director_Camera_Obj", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    lens = float(plan.get("lens", 50))
    cam_data.lens = lens
    cam_data.sensor_fit = "AUTO"
    cam_data.clip_end = 400.0
    cam_data.clip_start = 0.1
    if plan.get("dof"):
        cam_data.dof.use_dof = False

    groups = (data or {}).get("groups", {})
    frame_spec = plan.get("frame", "all")
    objs = None
    if frame_spec != "all":
        names = [frame_spec] if isinstance(frame_spec, str) else list(frame_spec)
        objs = []
        for n in names:
            objs.extend(groups.get(n, []))
        if not objs:
            objs = None

    n_samples = 5
    sample_frames = [round(f0 + (f1 - f0) * i / (n_samples - 1)) for i in range(n_samples)]
    pts_at = {f: _frame_points(scene, f, objs) for f in sample_frames}
    all_pts = [p for ps in pts_at.values() for p in ps]
    all_scene_pts = None
    must = plan.get("must_show")
    qc_samples = []

    keys = plan["keys"]
    # Inicializar cámara en f0 para que los cálculos usen la escena en f0
    for kdef in keys:
        t = float(kdef.get("t", 0.0))
        fr = round(f0 + t * (f1 - f0))
        if plan.get("track"):
            nearest = min(sample_frames, key=lambda s: abs(s - fr))
            pts = pts_at[nearest]
        else:
            pts = all_pts
        az = math.radians(float(kdef.get("az", 0.0)))
        el = math.radians(float(kdef.get("el", 10.0)))
        T, d_fit = fit(pts, az, el, lens, width, height, float(plan.get("margin", 0.07)))
        off = kdef.get("offset", (0, 0, 0))
        T = T + Vector(off)
        dist = d_fit * (1.0 + float(kdef.get("pad", 0.1)))
        d_vec, _, _ = _basis(az, el)
        pos = T + d_vec * dist
        cam_obj.location = pos
        cam_obj.rotation_euler = (T - pos).to_track_quat("-Z", "Y").to_euler()
        cam_obj.keyframe_insert(data_path="location", frame=fr)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=fr)
        inside_target = project_inside(pts, pos, T, lens, width, height)
        scene.frame_set(fr)
        everything = _frame_points(scene, fr, None)
        inside_all = project_inside(everything, pos, T, lens, width, height)
        qc_samples.append({"t": t, "dist": round(dist, 2), "target_inside": round(inside_target, 4),
                           "all_inside": round(inside_all, 4)})
    scene.frame_set(f0)
    return {"shot": plan.get("shot"), "intent": plan.get("intent"), "samples": qc_samples,
            "cut_risk": any(s["target_inside"] < 0.999 for s in qc_samples)}
