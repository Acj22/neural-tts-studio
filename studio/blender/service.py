"""Servicio de alto nivel para el Motor 3D de Blender (Fase 2, 4 y 7).

Conecta la arquitectura de Explainer AI con la automatización local de Blender:
- Renderizado de clips de video MP4 por escena con EEVEE Next.
- Renderizado de fotogramas fijos para miniaturas de Storyboard.
- Ejecución del Prototipo Oficial del Motor de Cuatro Tiempos (Punto 11).
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

import video_pipeline
import imageio_ffmpeg
from studio.blender.blender_gateway import (
    detect_blender_executable,
    execute_blender_script,
    get_blender_status,
)
from studio.blender.render_profiles import get_render_profile

logger = logging.getLogger("studio.blender.service")


def _get_ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def render_scene_3d_video(
    scene: dict[str, Any],
    output_mp4: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    render_profile: str = "standard",
    force_rerender: bool = False,
) -> Path:
    """Renderiza una escena completa en video MP4 mediante Blender 5.3 + FFmpeg local."""
    exe = detect_blender_executable()
    if not exe:
        raise RuntimeError("Blender no está instalado en el sistema.")

    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    if not force_rerender and output_mp4.exists() and output_mp4.stat().st_size > 5000:
        logger.info("Clip MP4 %s ya existe en disco. Reutilizando caché...", output_mp4.name)
        return output_mp4

    temp_frames_dir = output_mp4.parent / f"_frames_{scene.get('scene_id', 'temp')}"
    temp_frames_dir.mkdir(parents=True, exist_ok=True)

    composition_type = scene.get("composition_type") or (scene.get("diagram_spec") or {}).get("composition_type") or "hero_view"
    cycle_phase = (scene.get("diagram_spec") or {}).get("phase") or "full_cycle"
    dur_sec = max(1.5, float(scene.get("duration_sec", 4.0)))

    prof = get_render_profile(render_profile)
    actual_fps = int(prof.get("fps", fps))

    spec = {
        "width": width,
        "height": height,
        "fps": actual_fps,
        "duration_sec": dur_sec,
        "composition_type": composition_type,
        "cycle_phase": cycle_phase,
        "model_type": scene.get("model_type", "combustion_engine"),
        "highlight_component": scene.get("highlight_component") or (scene.get("diagram_spec") or {}).get("highlight_component"),
        "render_profile": render_profile,
        "camera_plan": scene.get("camera_plan"),
        "output_dir": str(temp_frames_dir.resolve()),
        "single_frame_only": False,
    }

    spec_file = temp_frames_dir / "scene_spec.json"
    spec_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    worker_script = Path(__file__).resolve().parent / "render_worker.py"
    ret, out, err = execute_blender_script(
        script_path=worker_script,
        args=[str(spec_file.resolve())],
        timeout_sec=900,
    )

    if ret != 0:
        raise RuntimeError(f"Fallo en Blender Worker (código {ret}): {err or out}")

    # Compilar los fotogramas PNG en MP4 con FFmpeg local asegurando Full HD
    ffmpeg_cmd = [
        _get_ffmpeg(),
        "-y",
        "-framerate",
        str(actual_fps),
        "-i",
        str(temp_frames_dir / "frame_%04d.png"),
        "-vf",
        f"scale={width}:{height}:flags=lanczos",
        "-c:v",
        "libx264",
        "-r",
        "24",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_mp4.resolve()),
    ]

    res_ff = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
    if res_ff.returncode != 0:
        raise RuntimeError(f"Error al compilar MP4 con FFmpeg: {res_ff.stderr}")

    return output_mp4


def _synthesize_audio_local(
    text: str,
    voice_id: str = "es-US-AlonsoNeural",
    speed: float = 1.0,
    pitch_hz: int = 1,
    expressive: bool = True,
) -> tuple[Any, int]:
    """Sintetiza voz neuronal ultra-expresiva con prosodia humana y masterización DSP de estudio."""
    try:
        from app import _synthesize_segment_samples
        return _synthesize_segment_samples(
            text=text,
            engine="edge",
            voice_id=voice_id,
            speed=speed,
            pitch_hz=pitch_hz,
            studio_mastering=True,
        )
    except Exception:
        import asyncio
        import io
        import soundfile as sf
        import edge_tts
        from app import enhance_spanish_prosody_for_youtube, apply_studio_voice_mastering

        clean_text = enhance_spanish_prosody_for_youtube(text, expressive_mode=expressive)
        rate_pct = int(round((float(speed) - 1.0) * 100)) + (3 if expressive else 0)
        rate_str = f"{rate_pct:+d}%"
        pitch_str = f"{pitch_hz:+d}Hz"

        async def _edge_gen() -> bytes:
            comm = edge_tts.Communicate(clean_text, voice_id, rate=rate_str, pitch=pitch_str, volume="+15%")
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf)

        raw_bytes = asyncio.run(_edge_gen())
        samples, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32")
        mastered = apply_studio_voice_mastering(samples, sr)
        return mastered, sr


def render_scene_3d_still(
    scene: dict[str, Any],
    output_png: Path,
    width: int = 1080,
    height: int = 1920,
    render_profile: str = "draft",
) -> Path:
    """Renderiza un único fotograma PNG para miniatura o preview rápido en el Storyboard."""
    output_png.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_png.parent / f"_still_{scene.get('scene_id', 'temp')}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    composition_type = scene.get("composition_type") or (scene.get("diagram_spec") or {}).get("composition_type") or "hero_view"
    cycle_phase = (scene.get("diagram_spec") or {}).get("phase") or "full_cycle"

    spec = {
        "width": width,
        "height": height,
        "fps": 24,
        "duration_sec": 1.0,
        "composition_type": composition_type,
        "cycle_phase": cycle_phase,
        "model_type": scene.get("model_type", "combustion_engine"),
        "render_profile": render_profile,
        "camera_plan": scene.get("camera_plan"),
        "output_dir": str(temp_dir.resolve()),
        "single_frame_only": True,
    }

    spec_file = temp_dir / "still_spec.json"
    spec_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    worker_script = Path(__file__).resolve().parent / "render_worker.py"
    ret, out, err = execute_blender_script(
        script_path=worker_script,
        args=[str(spec_file.resolve())],
        timeout_sec=120,
    )

    rendered_frame = temp_dir / "frame_.png"
    if rendered_frame.is_file():
        if output_png.exists():
            output_png.unlink()
        rendered_frame.rename(output_png)
        return output_png

    raise RuntimeError(f"No se generó el fotograma 3D: {err or out}")


def run_combustion_engine_prototype_benchmark(
    target_dir: Path,
    is_vertical: bool = True,
    render_profile: str = "test",
    voice_key: str = "es-MX-JorgeNeural",
    force_rerender: bool = False,
) -> dict[str, Any]:
    """Construye y renderiza el Prototipo Oficial de 8 Escenas (Fase 2 - Perfeccionamiento):
    1. Presentación tridimensional del motor (hero_view).
    2. Acercamiento al cilindro y cámara (close_up_view).
    3. Despiece axial de componentes (exploded_view).
    4. Movimiento del pistón y carrera PMS a PMI (cutaway_view).
    5. Apertura y cierre sincronizado de válvulas (close_up_view).
    6. Movimiento del cigüeñal y biela transmitiendo torque (component_track).
    7. Representación completa de los cuatro tiempos (process_view).
    8. Vista general final con órbita 360° en marcha (turntable_orbit).
    Sincronizado con narración neuronal de Edge-TTS y subtítulos automáticos.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    prof = get_render_profile(render_profile)
    width = int(prof.get("width") or (1080 if is_vertical else 1920))
    height = int(prof.get("height") or (1920 if is_vertical else 1080))
    fps = int(prof.get("fps", 24))

    # Control de Calidad previo al renderizado (Punto 8)
    from studio.blender.qc_checker import run_blender_scene_quality_control
    qc_res = run_blender_scene_quality_control(shot_type="hero_view", is_vertical=is_vertical)
    (target_dir / "qc_report.json").write_text(json.dumps(qc_res, indent=2, ensure_ascii=False), encoding="utf-8")

    # Visual Scene Director (Fase 2.3 - 12 Escenas Oficiales Canónicas)
    from studio.blender.visual_scene_director import VisualSceneDirector
    director = VisualSceneDirector()
    scenes_spec = director.get_canonical_12_scenes_sequence()
    total_scenes = len(scenes_spec)

    rendered_clips = []
    total_start = time.time()

    for idx, sc in enumerate(scenes_spec, start=1):
        sid = sc["id"]
        scene_final_mp4 = target_dir / f"{sid}_final.mp4"
        if not force_rerender and scene_final_mp4.exists() and scene_final_mp4.stat().st_size > 10000:
            logger.info("Escena %d/%d (%s) ya renderizada previamente. Reutilizando clip.", idx, total_scenes, sid)
            rendered_clips.append(scene_final_mp4)
            continue

        logger.info("Renderizando escena %d/%d: %s [%s]", idx, total_scenes, sc["title"], sc.get("shot_type"))

        # A. Sintetizar voz neuronal Edge-TTS local
        audio_path = target_dir / f"{sid}_audio.wav"
        samples, sr = _synthesize_audio_local(sc["text"], voice_id=voice_key, speed=1.0)
        import soundfile as sf
        sf.write(audio_path, samples, sr, format="WAV", subtype="PCM_16")
        dur_sec = round(len(samples) / float(sr), 2) + 0.35

        # B. Renderizar animación 3D en Blender
        scene_mp4 = target_dir / f"{sid}_raw_video.mp4"
        scene_dict = {
            "scene_id": sid,
            "composition_type": sc["shot_subtype"],
            "diagram_spec": {"composition_type": sc["shot_subtype"], "phase": sc["phase"]},
            "highlight_component": sc.get("highlight_component"),
            "duration_sec": dur_sec,
        }
        render_scene_3d_video(
            scene=scene_dict,
            output_mp4=scene_mp4,
            width=width,
            height=height,
            fps=fps,
            render_profile=render_profile,
            force_rerender=force_rerender,
        )

        # C. Muxing de Audio y Subtitulado Dinámico por Cláusulas
        scene_final_mp4 = target_dir / f"{sid}_final.mp4"
        words = sc["text"].split()
        sub_chunks = video_pipeline._group_words_for_dynamic_subs(words, max_words=5, max_chars=34)

        # Generar archivo SRT temporal para la escena
        srt_path = target_dir / f"{sid}.srt"
        t_per_chunk = dur_sec / float(max(1, len(sub_chunks)))
        srt_lines = []
        for c_idx, chunk in enumerate(sub_chunks, start=1):
            t_s = (c_idx - 1) * t_per_chunk
            t_e = min(dur_sec, c_idx * t_per_chunk)
            s_str = f"{int(t_s//3600):02d}:{int((t_s%3600)//60):02d}:{int(t_s%60):02d},{int((t_s%1)*1000):03d}"
            e_str = f"{int(t_e//3600):02d}:{int((t_e%3600)//60):02d}:{int(t_e%60):02d},{int((t_e%1)*1000):03d}"
            srt_lines.append(f"{c_idx}\n{s_str} --> {e_str}\n{' '.join(chunk)}\n")
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

        # Integrar audio y subtítulo mejorado con mayor tamaño y legibilidad (Fase 2.3)
        font_size = 48 if is_vertical else 34
        sub_margin_v = 55 if is_vertical else 30
        sub_filter = f"subtitles={srt_path.name}:force_style='PlayResY={height},PlayResX={width},FontName=Arial,FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.8,Shadow=1.5,Alignment=2,MarginV={sub_margin_v}'"

        ff_cmd = [
            _get_ffmpeg(),
            "-y",
            "-i",
            str(scene_mp4.name),
            "-i",
            str(audio_path.name),
            "-vf",
            sub_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(scene_final_mp4.name),
        ]
        res = subprocess.run(ff_cmd, cwd=str(target_dir.resolve()), capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            # Fallback sin filtro de subtítulo si libass tiene problemas con la ruta
            ff_simple = [
                _get_ffmpeg(),
                "-y",
                "-i",
                str(scene_mp4.resolve()),
                "-i",
                str(audio_path.resolve()),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(scene_final_mp4.resolve()),
            ]
            subprocess.run(ff_simple, check=True)

        rendered_clips.append(scene_final_mp4)

    # D. Concatenar los 8 clips en el video final
    concat_txt = target_dir / "concat_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for clip in rendered_clips:
            f.write(f"file '{clip.resolve()}'\n")

    master_mp4 = target_dir / f"prototipo_motor_4_tiempos_3d_{'9_16' if is_vertical else '16_9'}.mp4"
    concat_cmd = [
        _get_ffmpeg(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_txt.resolve()),
        "-c",
        "copy",
        str(master_mp4.resolve()),
    ]
    subprocess.run(concat_cmd, check=True, timeout=180)

    total_time = round(time.time() - total_start, 2)
    # Ruta relativa para el reproductor web (video_url)
    try:
        rel_url = "/" + master_mp4.relative_to(Path.cwd()).as_posix()
    except ValueError:
        rel_url = "/" + master_mp4.name
    return {
        "success": True,
        "master_video_path": str(master_mp4.resolve()),
        "video_path": str(master_mp4.resolve()),      # alias para compatibilidad
        "video_url": rel_url,                          # URL para el reproductor web
        "scenes_count": len(rendered_clips),
        "total_render_time_sec": total_time,
        "width": width,
        "height": height,
        "aspect_ratio": "9:16" if is_vertical else "16:9",
        "render_profile": render_profile,
    }
