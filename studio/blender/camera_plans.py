"""Cámaras por plan y multi-beat con encuadre automático 9:16 (Fase 3.1 y Fase 3.2) — se ejecuta dentro de Blender.

El Director Audiovisual (Python puro) decide *qué* mostrar, *cuándo* (marcas temporales reales de voz) y *por qué*;
este módulo calcula *dónde* situar la cámara en cada unidad narrativa (`beat_camera_steps`) para que:
1. El componente protagonista aproveche al máximo el formato vertical 9:16 (sin verse pequeño).
2. Ningún componente importante ni etiqueta activa quede cortado fuera de pantalla (`target_inside >= 0.999`).
3. Cuando la narración cambie de sujeto dentro de una escena, la cámara reencuadre suavemente hacia el nuevo sujeto
   en el fotograma exacto sincronizado con la voz.
4. Se audite en 2D que ninguna etiqueta activa se superponga con otra (`overlapping_labels_count == 0`).
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


def _resolve_focus_objs(groups: dict[str, list], frame_spec: Any) -> list | None:
    if not frame_spec or frame_spec == "all":
        return None
    names = [frame_spec] if isinstance(frame_spec, str) else list(frame_spec)
    objs = []
    for n in names:
        objs.extend(groups.get(n, []))
    return objs if objs else None


def _basis(az: float, el: float):
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
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


def fit(points: list, az: float, el: float, lens: float, w: int, h: int, margin: float = 0.055) -> tuple[Any, float]:
    """Devuelve (objetivo T centrado en pantalla, distancia óptima de encuadre 9:16)."""
    d_vec, right, up = _basis(az, el)
    tx, ty = _tans(lens, w, h)
    k = 1.0 - margin
    if not points:
        return Vector((0.0, 0.0, 2.0)), 8.0
    T = sum(points, Vector((0, 0, 0))) / max(1, len(points))
    dist = 8.0
    for _ in range(3):
        xs = [(p - T).dot(right) for p in points]
        ys = [(p - T).dot(up) for p in points]
        T = T + right * ((max(xs) + min(xs)) / 2.0) + up * ((max(ys) + min(ys)) / 2.0)
        dist = 0.0
        for p in points:
            v = p - T
            q = v.dot(d_vec)
            dist = max(dist, q + abs(v.dot(right)) / (tx * k), q + abs(v.dot(up)) / (ty * k))
    return T, max(1.8, dist)


def project_inside_and_fill(points: list, cam_pos: Any, target: Any, lens: float, w: int, h: int) -> tuple[float, float]:
    """Calcula (fracción de puntos dentro del cuadro [0..1], ratio de ocupación en pantalla [0..1])."""
    if not points:
        return 1.0, 0.65
    f = (target - cam_pos).normalized()
    right = f.cross(Vector((0, 0, 1)))
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(f).normalized()
    tx, ty = _tans(lens, w, h)
    ok = 0
    us: list[float] = []
    vs: list[float] = []
    for p in points:
        v = p - cam_pos
        z = v.dot(f)
        if z <= 0.01:
            continue
        ux = v.dot(right) / (z * tx)
        vy = v.dot(up) / (z * ty)
        us.append(ux)
        vs.append(vy)
        if abs(ux) <= 1.001 and abs(vy) <= 1.001:
            ok += 1
    inside = ok / len(points)
    if not us or not vs:
        return inside, 0.5
    span_u = min(2.0, max(us) - min(us)) / 2.0
    span_v = min(2.0, max(vs) - min(vs)) / 2.0
    fill = round(max(span_u, span_v), 3)
    return inside, fill


def check_label_overlaps_2d(scene: Any, cam_pos: Any, target: Any, lens: float, w: int, h: int) -> int:
    """Verifica si dos etiquetas 3D de tipo FONT visibles simultáneamente se superponen en proyección 2D."""
    f = (target - cam_pos).normalized()
    right = f.cross(Vector((0, 0, 1)))
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(f).normalized()
    tx, ty = _tans(lens, w, h)

    font_objs = [o for o in scene.objects if o.type == "FONT" and not o.hide_render]
    projected_boxes: list[tuple[str, float, float]] = []
    for fo in font_objs:
        loc = fo.matrix_world.translation
        v = loc - cam_pos
        z = v.dot(f)
        if z <= 0.05:
            continue
        u = v.dot(right) / (z * tx)
        vv = v.dot(up) / (z * ty)
        projected_boxes.append((fo.name, u, vv))

    overlaps = 0
    for i in range(len(projected_boxes)):
        for j in range(i + 1, len(projected_boxes)):
            _, u1, v1 = projected_boxes[i]
            _, u2, v2 = projected_boxes[j]
            if abs(u1 - u2) < 0.16 and abs(v1 - v2) < 0.055:
                overlaps += 1
    return overlaps


def apply_camera_plan(
    plan: dict[str, Any],
    data: dict[str, Any] | None,
    width: int,
    height: int,
    f0: int,
    f1: int,
) -> dict[str, Any]:
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("Director_Camera")
    cam_obj = bpy.data.objects.new("Director_Camera_Obj", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    base_lens = float(plan.get("lens", 54))
    cam_data.lens = base_lens
    cam_data.sensor_fit = "AUTO"
    cam_data.clip_end = 400.0
    cam_data.clip_start = 0.1

    groups = (data or {}).get("groups", {})
    qc_samples: list[dict[str, Any]] = []
    total_overlaps = 0

    beat_steps = plan.get("beat_camera_steps")
    if beat_steps and len(beat_steps) > 1:
        # Encuadre dinámico multi-beat sincronizado con cada fragmento semántico de la narración
        for b_idx, bstep in enumerate(beat_steps):
            t0 = float(bstep.get("t0", 0.0))
            t1 = float(bstep.get("t1", 1.0))
            fr0 = max(f0, min(f1, round(f0 + t0 * (f1 - f0))))
            fr1 = max(fr0 + 1, min(f1, round(f0 + t1 * (f1 - f0))))
            # Dejar 4 fotogramas de transición suave entre el final de un beat y el inicio del siguiente
            if b_idx > 0:
                fr0 = min(fr1 - 1, fr0 + 3)

            b_objs = _resolve_focus_objs(groups, bstep.get("frame", plan.get("frame", "all")))
            b_lens = float(bstep.get("lens", base_lens))
            b_margin = float(bstep.get("margin", plan.get("margin", 0.055)))

            pts_mid = _frame_points(scene, (fr0 + fr1) // 2, b_objs)
            if not pts_mid:
                pts_mid = _frame_points(scene, (fr0 + fr1) // 2, None)

            for fr, az_deg, el_deg, pad_val, t_val in (
                (fr0, float(bstep["az0"]), float(bstep["el0"]), float(bstep["pad0"]), t0),
                (fr1, float(bstep["az1"]), float(bstep["el1"]), float(bstep["pad1"]), t1),
            ):
                az = math.radians(az_deg)
                el = math.radians(el_deg)
                T, d_fit = fit(pts_mid, az, el, b_lens, width, height, b_margin)
                dist = d_fit * (1.0 + pad_val)
                d_vec, _, _ = _basis(az, el)
                pos = T + d_vec * dist

                cam_obj.location = pos
                cam_obj.rotation_euler = (T - pos).to_track_quat("-Z", "Y").to_euler()
                cam_data.lens = b_lens
                cam_obj.keyframe_insert(data_path="location", frame=fr)
                cam_obj.keyframe_insert(data_path="rotation_euler", frame=fr)
                cam_data.keyframe_insert(data_path="lens", frame=fr)

                inside_t, fill_ratio = project_inside_and_fill(pts_mid, pos, T, b_lens, width, height)
                scene.frame_set(fr)
                ov = check_label_overlaps_2d(scene, pos, T, b_lens, width, height)
                total_overlaps = max(total_overlaps, ov)
                qc_samples.append({
                    "beat_id": bstep.get("beat_id"),
                    "camera": bstep.get("camera"),
                    "t": round(t_val, 3),
                    "frame": fr,
                    "dist": round(dist, 2),
                    "target_inside": round(inside_t, 4),
                    "screen_fill_ratio": fill_ratio,
                    "label_overlaps": ov,
                })
    else:
        # Plan de cámara estándar por escena
        objs = _resolve_focus_objs(groups, plan.get("frame", "all"))
        n_samples = 5
        sample_frames = [round(f0 + (f1 - f0) * i / (n_samples - 1)) for i in range(n_samples)]
        pts_at = {f: _frame_points(scene, f, objs) for f in sample_frames}
        all_pts = [p for ps in pts_at.values() for p in ps]

        for kdef in plan["keys"]:
            t = float(kdef.get("t", 0.0))
            fr = round(f0 + t * (f1 - f0))
            pts = pts_at[min(sample_frames, key=lambda s: abs(s - fr))] if plan.get("track") else all_pts
            az = math.radians(float(kdef.get("az", 0.0)))
            el = math.radians(float(kdef.get("el", 10.0)))
            T, d_fit = fit(pts, az, el, base_lens, width, height, float(plan.get("margin", 0.055)))
            off = kdef.get("offset", (0, 0, 0))
            T = T + Vector(off)
            dist = d_fit * (1.0 + float(kdef.get("pad", 0.03)))
            d_vec, _, _ = _basis(az, el)
            pos = T + d_vec * dist
            cam_obj.location = pos
            cam_obj.rotation_euler = (T - pos).to_track_quat("-Z", "Y").to_euler()
            cam_obj.keyframe_insert(data_path="location", frame=fr)
            cam_obj.keyframe_insert(data_path="rotation_euler", frame=fr)
            inside_target, fill_ratio = project_inside_and_fill(pts, pos, T, base_lens, width, height)
            scene.frame_set(fr)
            ov = check_label_overlaps_2d(scene, pos, T, base_lens, width, height)
            total_overlaps = max(total_overlaps, ov)
            qc_samples.append({
                "t": t,
                "frame": fr,
                "dist": round(dist, 2),
                "target_inside": round(inside_target, 4),
                "screen_fill_ratio": fill_ratio,
                "label_overlaps": ov,
            })

    scene.frame_set(f0)
    avg_fill = round(sum(s.get("screen_fill_ratio", 0.65) for s in qc_samples) / max(1, len(qc_samples)), 3)
    return {
        "shot": plan.get("shot"),
        "intent": plan.get("intent"),
        "multi_beat_active": bool(beat_steps and len(beat_steps) > 1),
        "samples": qc_samples,
        "avg_screen_fill_ratio": avg_fill,
        "overlapping_labels_count": total_overlaps,
        "cut_risk": any(s["target_inside"] < 0.995 for s in qc_samples),
    }
