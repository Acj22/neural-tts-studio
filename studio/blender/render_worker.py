"""Trabajador de renderizado headless para Blender 5.3+ (Fase 3.1 y Fase 3.2).

1. Parsea la especificación JSON de la escena (incluyendo `camera_plan` y `audiovisual_beats`).
2. Construye el modelo procedural especializado y aplica la animación de la fase.
3. Sincroniza en la línea de tiempo de fotogramas (`synchronize_audiovisual_beats_in_scene`):
   - Aparición exacta de etiquetas 3D en el fotograma en que el narrador pronuncia el componente.
   - Resaltado (highlight pulse) del componente protagonista acotado estrictamente a su beat narrativo.
4. Control de calidad previo y posterior (componentes, conexiones mecánicas, movimiento funcional y cámara).
5. Renderiza la secuencia PNG con EEVEE y escribe `status.json` con el informe de QC y sincronización.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import bpy
except ImportError:
    bpy = None

from studio.blender.models_library.combustion_engine import create_combustion_engine_3d
from studio.blender.models_library.automatic_transmission import (
    create_automatic_transmission_3d,
    build_transmission_keyframes,
)
from studio.blender.models_library.refrigerator_cycle import (
    create_refrigerator_cycle_3d,
    build_refrigerator_keyframes,
)
from studio.blender.models_library.printer_3d_fdm import (
    create_printer_3d_3d,
    build_printer_3d_keyframes,
)
from studio.blender.animation_controller import build_4_stroke_cycle_keyframes
from studio.blender.camera_director import setup_studio_lighting, setup_camera_for_shot
from studio.blender.camera_plans import apply_camera_plan
from studio.blender.model_qc import check_required, check_connections, check_animation_motion
from studio.blender.render_profiles import get_render_profile


def clean_blender_scene() -> None:
    if bpy is None:
        return
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)


def _clear_visibility_fcurves(obj: Any) -> None:
    if obj and obj.animation_data and obj.animation_data.action:
        act = obj.animation_data.action
        if hasattr(act, "fcurves"):
            for fc in list(act.fcurves):
                if fc.data_path in ("hide_render", "hide_viewport"):
                    act.fcurves.remove(fc)


def synchronize_audiovisual_beats_in_scene(
    data: dict[str, Any],
    beats: list[dict[str, Any]] | None,
    fps: int,
    total_frames: int,
) -> dict[str, Any]:
    """Sincroniza etiquetas 3D y resaltados de componentes con las marcas temporales reales de cada beat
    (Fase 3.2 - Punto 3.3: No mostrar etiquetas antes de que el narrador mencione el componente;
    no mantener un resaltado después de que la explicación haya cambiado de tema)."""
    if not beats or bpy is None or not data:
        return {"beats_applied": 0, "label_triggers": {}, "highlight_windows": []}

    labels_dict: dict[str, tuple[Any, Any]] = data.get("labels", {})
    groups: dict[str, list[Any]] = data.get("groups", {})

    # Recolectar el primer segundo real en que el narrador menciona cada etiqueta dentro de esta escena
    first_trigger_sec: dict[str, float] = {}
    for b in beats:
        for lk, t_sec in (b.get("label_triggers_local_sec") or {}).items():
            if lk in labels_dict and lk not in first_trigger_sec:
                first_trigger_sec[lk] = float(t_sec)

    # Si esta escena tiene etiquetas mencionadas en sus beats, sincronizar su aparición exacta con la voz
    label_trigger_frames: dict[str, int] = {}
    if first_trigger_sec and labels_dict:
        for lk, pair in labels_dict.items():
            objs = list(pair) if isinstance(pair, (list, tuple)) else [pair]
            for o in objs:
                _clear_visibility_fcurves(o)
                if lk in first_trigger_sec:
                    f_on = max(1, min(total_frames, int(round(first_trigger_sec[lk] * fps)) + 1))
                    label_trigger_frames[lk] = f_on
                    if f_on > 1:
                        o.hide_render = True
                        o.hide_viewport = True
                        o.keyframe_insert(data_path="hide_render", frame=1)
                        o.keyframe_insert(data_path="hide_viewport", frame=1)
                    o.hide_render = False
                    o.hide_viewport = False
                    o.keyframe_insert(data_path="hide_render", frame=f_on)
                    o.keyframe_insert(data_path="hide_viewport", frame=f_on)
                else:
                    # Etiqueta no explicada en esta escena: mantener oculta
                    o.hide_render = True
                    o.hide_viewport = True
                    o.keyframe_insert(data_path="hide_render", frame=1)
                    o.keyframe_insert(data_path="hide_viewport", frame=1)

    # Sincronizar el resaltado (pulso de escala sutil) del componente protagonista dentro de los límites de su beat
    highlight_windows: list[dict[str, Any]] = []
    for b in beats:
        h_spec = b.get("highlight")
        if not h_spec or h_spec == "all":
            continue
        h_names = [h_spec] if isinstance(h_spec, str) else list(h_spec)
        t0 = float(b.get("local_start_sec", 0.0))
        t1 = float(b.get("local_end_sec", 0.0))
        f_start = max(1, min(total_frames, int(round(t0 * fps)) + 1))
        f_end = max(f_start + 2, min(total_frames, int(round(t1 * fps))))
        f_mid = (f_start + f_end) // 2

        pulsed_count = 0
        for hn in h_names:
            for obj in groups.get(hn, []):
                if obj is None or obj.get("role") in ("label", "fx"):
                    continue
                # No alterar escala de objetos que ya tienen animación de escala propia (ej. resortes o piezas creciendo)
                if obj.animation_data and obj.animation_data.action and hasattr(obj.animation_data.action, "fcurves"):
                    if any(fc.data_path == "scale" for fc in obj.animation_data.action.fcurves):
                        continue
                base_s = obj.scale.copy()
                obj.keyframe_insert(data_path="scale", frame=f_start)
                obj.scale = (base_s.x * 1.045, base_s.y * 1.045, base_s.z * 1.045)
                obj.keyframe_insert(data_path="scale", frame=f_mid)
                obj.scale = base_s
                obj.keyframe_insert(data_path="scale", frame=f_end)
                pulsed_count += 1

        highlight_windows.append({
            "beat_id": b.get("beat_id"),
            "highlight": h_spec,
            "start_frame": f_start,
            "end_frame": f_end,
            "pulsed_objects": pulsed_count,
        })

    return {
        "beats_applied": len(beats),
        "label_triggers_sec": first_trigger_sec,
        "label_trigger_frames": label_trigger_frames,
        "highlight_windows": highlight_windows,
    }


def run_blender_render(spec: dict) -> None:
    if bpy is None:
        raise RuntimeError("No se puede ejecutar fuera de Blender.")

    clean_blender_scene()

    profile_key = spec.get("render_profile", "production")
    profile = get_render_profile(profile_key)
    output_dir = Path(spec["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    single_frame = bool(spec.get("single_frame_only", False))

    width = int(spec.get("width") or profile.get("width", 1080))
    height = int(spec.get("height") or profile.get("height", 1920))
    fps = int(profile.get("fps") or spec.get("fps", 24))
    duration_sec = float(spec.get("duration_sec", 4.0))
    composition_type = spec.get("composition_type", "hero_view")
    cycle_phase = spec.get("cycle_phase", "full_cycle")
    camera_plan = spec.get("camera_plan")
    audiovisual_beats = spec.get("audiovisual_beats")

    is_vertical = height > width
    total_frames = 1 if single_frame else max(10, int(round(duration_sec * fps)))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = int(profile.get("resolution_scale", 100))
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames

    if hasattr(scene, "eevee"):
        samples_val = int(profile.get("samples", 16))
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = max(samples_val, int(spec.get("min_samples", 2)))
        if hasattr(scene.eevee, "use_shadows"):
            scene.eevee.use_shadows = True
        is_fast_preview = profile_key in ("test", "draft") or samples_val <= 8
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = not is_fast_preview
        if hasattr(scene.eevee, "use_fast_gi"):
            scene.eevee.use_fast_gi = True

    setup_studio_lighting()

    model_type = spec.get("model_type", "combustion_engine")
    highlight_comp = spec.get("highlight_component")
    data: dict[str, Any] = {}
    qc: dict[str, Any] = {"model_type": model_type, "phase": cycle_phase}

    if model_type == "automatic_transmission":
        data = create_automatic_transmission_3d(center_z=2.0)
        build_transmission_keyframes(trans_data=data, start_frame=1, end_frame=total_frames,
                                     scene_phase=cycle_phase, highlight_component=highlight_comp)
    elif model_type == "refrigerator_cycle":
        data = create_refrigerator_cycle_3d(center_z=2.2)
        build_refrigerator_keyframes(fridge_data=data, start_frame=1, end_frame=total_frames,
                                     scene_phase=cycle_phase, highlight_component=highlight_comp)
    elif model_type == "printer_3d_fdm":
        data = create_printer_3d_3d(center_z=2.0)
        build_printer_3d_keyframes(printer_data=data, start_frame=1, end_frame=total_frames,
                                   scene_phase=cycle_phase, highlight_component=highlight_comp)
    else:
        data = create_combustion_engine_3d(crank_radius=1.0, rod_length=3.6, cylinder_radius=1.30,
                                           piston_height=1.45, crank_center_z=0.0)
        build_4_stroke_cycle_keyframes(engine_data=data, start_frame=1, end_frame=total_frames,
                                       cycle_phase=cycle_phase, highlight_component=highlight_comp)

    # Sincronización de beats audiovisuales (etiquetas al segundo exacto de la voz y resaltados por beat)
    qc["audiovisual_sync"] = synchronize_audiovisual_beats_in_scene(data, audiovisual_beats, fps, total_frames)

    # QC técnico: componentes requeridos, conexiones en estado ensamblado y verificación de movimiento real
    qc["components"] = check_required(model_type, data)
    qc["connections"] = check_connections(data, frame=1) if data.get("connections") else {"checks": [], "ok": True}
    qc["motion"] = check_animation_motion(1, total_frames) if total_frames > 1 else {"has_functional_motion": True, "ok": True}

    # Cámara inteligente (con soporte multi-beat cuando la escena cambia de sujeto)
    if camera_plan:
        qc["camera"] = apply_camera_plan(camera_plan, data, width, height, 1, total_frames)
    else:
        setup_camera_for_shot(shot_type=composition_type, is_vertical=is_vertical, start_frame=1, end_frame=total_frames)
        qc["camera"] = {"shot": composition_type, "note": "cámara heredada (sin plan)"}

    scene.frame_set(1)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_dir / "frame_")

    print(f"[BLENDER_WORKER] Renderizando {total_frames} fotogramas a {width}x{height} ({profile_key}) fase={cycle_phase}")
    if single_frame:
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)

    (output_dir / "status.json").write_text(
        json.dumps({"success": True, "total_frames": total_frames, "width": width, "height": height, "fps": fps,
                    "render_profile": profile_key, "composition_type": composition_type,
                    "cycle_phase": cycle_phase, "qc": qc}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"[BLENDER_WORKER] Completado: {output_dir}")


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        idx = argv.index("--") + 1
        if idx < len(argv):
            spec_file = Path(argv[idx])
            if spec_file.is_file():
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_data = json.load(f)
                run_blender_render(spec_data)
                sys.exit(0)
    print("Error: Se requiere una ruta a un archivo de especificación JSON tras '--'.")
    sys.exit(1)
