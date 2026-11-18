"""Control de calidad técnico del modelo 3D (Fase 3.1) — se ejecuta dentro de Blender.

- Componentes requeridos presentes (no se inventan componentes: si falta uno, se informa).
- Conexiones mecánicas: separación entre cajas envolventes (AABB) de pares que deben tocarse.
- Cámara: ver camera_plans.apply_camera_plan (cut_risk / target_inside).
"""

from __future__ import annotations

from typing import Any

try:
    import bpy
    from mathutils import Vector
except ImportError:  # pragma: no cover
    bpy = None
    Vector = None

REQUIRED_COMPONENTS: dict[str, list[str]] = {
    "automatic_transmission": ["sun_gear", "planets", "carrier", "ring_gear", "brake_band", "clutch_discs",
                               "impeller", "turbine", "stator", "valve_body", "input_shaft", "output_tube"],
    "refrigerator_cycle": ["compressor", "condenser", "dryer_filter", "capillary_tube", "evaporator",
                           "suction_line", "discharge_line", "liquid_line", "cabinet", "refrigerant_particles"],
    "printer_3d_fdm": ["frame", "z_axis", "x_axis", "y_axis_bed", "extruder", "hotend", "nozzle", "bed",
                       "filament_spool", "printed_part"],
    "combustion_engine": ["engine_block", "cylinder_liner", "cylinder_head", "piston_root", "rod_root",
                          "crank_root", "valve_intake", "valve_exhaust"],
}


def _flatten(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            out.extend(_flatten(x))
        return out
    return [v]


def check_required(model_type: str, data: dict[str, Any]) -> dict[str, Any]:
    comps = data.get("components", {})
    required = REQUIRED_COMPONENTS.get(model_type, [])
    missing = [r for r in required if not _flatten(comps.get(r)) and r not in data]
    return {"required": required, "missing": missing, "ok": not missing}


def _aabb(obj: Any, dg: Any) -> tuple[Any, Any] | None:
    if obj is None or obj.type not in ("MESH", "CURVE", "FONT"):
        return None
    ev = obj.evaluated_get(dg)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def _gap(a: tuple, b: tuple) -> float:
    gx = max(a[0].x - b[1].x, b[0].x - a[1].x, 0.0)
    gy = max(a[0].y - b[1].y, b[0].y - a[1].y, 0.0)
    gz = max(a[0].z - b[1].z, b[0].z - a[1].z, 0.0)
    return (gx * gx + gy * gy + gz * gz) ** 0.5


def check_connections(data: dict[str, Any], frame: int | None = None) -> dict[str, Any]:
    scene = bpy.context.scene
    if frame is not None:
        scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    results = []
    for (a, b, tol, label) in data.get("connections", []):
        ba, bb = _aabb(a, dg), _aabb(b, dg)
        if ba is None or bb is None:
            results.append({"pair": label, "gap": None, "ok": False, "note": "objeto sin geometría"})
            continue
        g = _gap(ba, bb)
        results.append({"pair": label, "gap": round(g, 4), "tolerance": tol, "ok": g <= tol})
    return {"checks": results, "ok": all(r["ok"] for r in results)}


def check_animation_motion(f0: int = 1, f1: int = 48) -> dict[str, Any]:
    """Verifica que la escena tenga movimiento funcional real entre f0 y f1 (Puntos 3.4 y 10)."""
    scene = bpy.context.scene
    objs = [
        o for o in scene.objects
        if o.type in ("MESH", "EMPTY", "CURVE") and not o.name.startswith(("Studio_", "Director_"))
    ]
    scene.frame_set(f0)
    bpy.context.view_layer.update()
    snap0 = {o.name: (o.matrix_world.translation.copy(), o.matrix_world.to_euler()) for o in objs}

    q1 = max(f0 + 1, f0 + (f1 - f0) // 4)
    mid = max(f0 + 1, (f0 + f1) // 2)
    q3 = max(f0 + 1, f0 + (3 * (f1 - f0)) // 4)
    moving: set[str] = set()
    for fr in (q1, mid, q3, f1):
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        for o in objs:
            t0, r0 = snap0[o.name]
            t1 = o.matrix_world.translation
            r1 = o.matrix_world.to_euler()
            dt = (t1 - t0).length
            dr = abs(r1.x - r0.x) + abs(r1.y - r0.y) + abs(r1.z - r0.z)
            if dt > 1e-3 or dr > 1e-3:
                moving.add(o.name)

    scene.frame_set(f0)
    return {
        "has_functional_motion": len(moving) > 0,
        "moving_objects_count": len(moving),
        "sample_moving_objects": sorted(list(moving))[:8],
        "ok": len(moving) > 0,
    }
