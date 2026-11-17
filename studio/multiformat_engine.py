"""FASE 9, 10, 11 y 14 — MULTIFORMAT ENGINE, SMART REFRAME & RENDER ENGINE.

Motor de renderizado inteligente para AI VIDEO STUDIO (EXPLAINER AI):
- Soporta versión Corta (9:16, 1080x1920) y versión Larga (16:9, 1920x1080).
- Reencuadre Inteligente por plataforma (YouTube Video, YouTube Shorts, TikTok, Instagram Reels, Facebook Reels, Facebook Video)
  respetando las zonas seguras de cada interfaz móvil o de escritorio.
- Zonas visuales diferenciadas: los diagramas, las etiquetas numeradas y los subtítulos dinámicos .ASS
  nunca se solapan entre sí.
- Soporta renderizar 1 escena de prueba (Fase 14) en pocos segundos antes del renderizado completo.
- Reutiliza los recursos maestros entre plataformas del mismo formato para evitar trabajo redundante.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional

import imageio_ffmpeg
from PIL import Image, ImageFilter

import video_pipeline
from studio.diagram_engine import (
    generate_scene_svg_diagram,
    render_animated_diagram_frame,
    render_mode_a_enhanced_frame,
)
from studio.models import load_platform_profiles


def generate_platform_safe_ass_subtitles(
    scenes: list[dict[str, Any]],
    width: int,
    height: int,
    subtitle_style: str = "hormozi_yellow",
    safe_zone: Optional[dict[str, Any]] = None,
) -> str:
    """Genera subtítulos dinámicos .ASS respetando los márgenes seguros específicos de cada plataforma
    (TikTok, Instagram Reels, YouTube Shorts, Facebook Reels o YouTube 16:9) para no chocar con
    los botones de la red social ni con los diagramas educativos."""
    base_ass = video_pipeline.generate_ass_subtitles(
        scenes=scenes,
        width=width,
        height=height,
        subtitle_style=subtitle_style,
    )
    if not safe_zone:
        return base_ass

    is_vertical = height > width
    margin_v_pct = float(safe_zone.get("subtitle_margin_v_pct", 0.23 if is_vertical else 0.085))
    left_pct = float(safe_zone.get("left_pct", 0.06 if is_vertical else 0.05))
    right_pct = float(safe_zone.get("right_pct", 0.15 if is_vertical else 0.05))

    margin_v = int(height * margin_v_pct)
    margin_l = int(width * left_pct)
    margin_r = int(width * right_pct)
    font_size = int(height * 0.046) if not is_vertical else int(width * 0.058)

    # Actualizar la línea Style: ViralSub con los márgenes seguros exactos de la plataforma
    lines = base_ass.splitlines()
    updated_lines = []
    for ln in lines:
        if ln.startswith("Style: ViralSub,"):
            parts = ln.split(",")
            if len(parts) >= 23:
                parts[2] = str(font_size)
                parts[19] = str(margin_l)
                parts[20] = str(margin_r)
                parts[21] = str(margin_v)
                ln = ",".join(parts)
        updated_lines.append(ln)
    return "\n".join(updated_lines) + "\n"


def render_single_scene_preview(
    project_dir: Path,
    scene: dict[str, Any],
    version: str = "short",
    visual_style_key: str = "3d_educational",
    aspect_ratio: str = "9:16",
    subtitle_style: str = "hormozi_yellow",
) -> Path:
    """Renderiza una sola escena de prueba en .MP4 (Fase 14) con su audio real, diagrama/imagen
    animada y subtítulos en zonas seguras para previsualizar antes del renderizado completo."""
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    preview_dir = project_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    scene_id = scene.get("scene_id", f"S{scene.get('index', 1):02d}")
    frames_dir = preview_dir / f"frames_{scene_id}_{width}x{height}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    dur = max(1.5, float(scene.get("duration_sec", 4.0)))
    fps_keyframes = 12
    steps = max(8, min(90, int(round(dur * fps_keyframes))))
    step_dur = dur / float(steps)

    # Cargar imagen base si existe
    img_path = project_dir / "images" / f"{scene_id}.png"
    base_img: Optional[Image.Image] = None
    if img_path.exists():
        try:
            base_img = Image.open(img_path).convert("RGB")
        except Exception:
            base_img = None

    # Asegurar que exista también el SVG del diagrama
    svg_path = project_dir / "diagrams" / f"{scene_id}.svg"
    generate_scene_svg_diagram(scene, visual_style_key=visual_style_key, width=width, height=height, dest_svg_path=svg_path)

    vignette = video_pipeline._build_vignette_overlay(width, height, strength=0.30)
    safe_zone = {"top_pct": 0.12, "bottom_pct": 0.24, "left_pct": 0.06, "right_pct": 0.14, "subtitle_margin_v_pct": 0.23} if height > width else {"top_pct": 0.06, "bottom_pct": 0.12, "left_pct": 0.05, "right_pct": 0.05, "subtitle_margin_v_pct": 0.085}

    concat_lines: list[str] = []
    last_f: Optional[Path] = None
    visual_mode = scene.get("visual_mode", "mode_b_diagram")

    for s_i in range(steps):
        prog = s_i / float(max(1, steps - 1))
        if visual_mode == "mode_a_image" and base_img is not None:
            frame = render_mode_a_enhanced_frame(
                base_img=base_img,
                progress=prog,
                camera_motion=scene.get("camera_motion", "zoom_in"),
                width=width,
                height=height,
                scene=scene,
                safe_zone=safe_zone,
                vignette_overlay=vignette,
            )
        else:
            frame = render_animated_diagram_frame(
                scene=scene,
                progress=prog,
                width=width,
                height=height,
                visual_style_key=visual_style_key,
                safe_zone=safe_zone,
                base_illustration=base_img,
            )

        fpath = frames_dir / f"f_{s_i:03d}.jpg"
        frame.save(fpath, format="JPEG", quality=94, subsampling=0)
        safe_p = str(fpath.resolve()).replace("\\", "/")
        concat_lines.append(f"file '{safe_p}'")
        concat_lines.append(f"duration {step_dur:.3f}")
        last_f = fpath

    if last_f is not None:
        concat_lines.append(f"file '{str(last_f.resolve()).replace(chr(92), '/')}'")

    concat_txt = frames_dir / "concat.txt"
    concat_txt.write_text("\n".join(concat_lines), encoding="utf-8")

    # Subtítulo .ASS local para esta escena (ajustando start_sec=0 -> dur)
    local_scene = dict(scene)
    local_scene["start_sec"] = 0.0
    local_scene["end_sec"] = dur
    ass_name = f"sub_{scene_id}.ass"
    ass_path = preview_dir / ass_name
    ass_path.write_text(
        generate_platform_safe_ass_subtitles([local_scene], width=width, height=height, subtitle_style=subtitle_style, safe_zone=safe_zone),
        encoding="utf-8",
    )

    scene_wav = project_dir / "audio" / f"{scene_id}.wav"
    out_mp4 = preview_dir / f"preview_{scene_id}_{width}x{height}.mp4"

    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_txt.resolve()),
    ]
    if scene_wav.exists():
        cmd.extend(["-i", str(scene_wav.resolve())])

    cmd.extend(
        [
            "-vf",
            f"ass={ass_name}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-movflags",
            "+faststart",
        ]
    )
    if scene_wav.exists():
        cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])
    cmd.append(str(out_mp4.resolve()))

    proc = subprocess.run(cmd, cwd=str(preview_dir.resolve()), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Error FFmpeg en vista previa de escena: {proc.stderr[-350:]}")
    return out_mp4


def render_explainer_version_video(
    project_dir: Path,
    scenes: list[dict[str, Any]],
    version: str = "short",
    platform_id: str = "youtube_shorts",
    visual_style_key: str = "3d_educational",
    subtitle_style: str = "hormozi_yellow",
    bg_music: str = "doc_mystery",
    bg_music_volume: float = 0.14,
    burn_subtitles: bool = True,
    transition: str = "crossfade",
    transition_duration: float = 0.45,
) -> dict[str, Any]:
    """Renderiza una versión completa (Short 9:16 o Long 16:9) adaptada al perfil de plataforma
    seleccionado (con Reencuadre Inteligente, Diagramas Modo B + Imágenes Modo A, Audio con Auto-Ducking
    y Subtítulos en Zonas Seguras)."""
    profiles = load_platform_profiles()
    profile = profiles.get(platform_id) or (profiles["youtube_shorts"] if version == "short" else profiles["youtube_video"])

    width = int(profile["width"])
    height = int(profile["height"])
    safe_zone = profile.get("safe_zone") or {}

    exports_dir = project_dir / "exports" / platform_id
    exports_dir.mkdir(parents=True, exist_ok=True)

    # Reutilización inteligente de fotogramas base por (version, width, height) (Fase 14)
    shared_frames_dir = project_dir / "exports" / f"_shared_frames_{version}_{width}x{height}"
    shared_concat_file = shared_frames_dir / "concat_list.txt"

    diagrams_dir = project_dir / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    if not shared_concat_file.exists():
        shared_frames_dir.mkdir(parents=True, exist_ok=True)
        vignette = video_pipeline._build_vignette_overlay(width, height, strength=0.30)
        fps_keyframes = 6
        concat_lines: list[str] = []
        last_frame_path: Optional[Path] = None

        scene_base_imgs: list[Optional[Image.Image]] = []
        for sc in scenes:
            scene_id = sc.get("scene_id", f"S{sc.get('index', 1):02d}")
            img_file = project_dir / "images" / f"{scene_id}.png"
            b_img = None
            if img_file.exists():
                try:
                    b_img = Image.open(img_file).convert("RGB")
                except Exception:
                    b_img = None
            scene_base_imgs.append(b_img)

            svg_path = diagrams_dir / f"{scene_id}.svg"
            if not svg_path.exists():
                generate_scene_svg_diagram(sc, visual_style_key=visual_style_key, width=width, height=height, dest_svg_path=svg_path)

        num_scenes = len(scenes)
        for i, sc in enumerate(scenes):
            scene_id = sc.get("scene_id", f"S{i+1:02d}")
            dur = max(0.4, float(sc.get("duration_sec", 4.0)))
            has_next = i < num_scenes - 1
            t_dur = min(float(transition_duration), dur * 0.4, 0.8) if (has_next and transition != "none") else 0.0
            hold_dur = max(0.15, dur - t_dur) if t_dur >= 0.15 else dur

            hold_steps = max(4, min(48, int(round(hold_dur * fps_keyframes))))
            hold_step_dur = hold_dur / float(hold_steps)
            visual_mode = sc.get("visual_mode", "mode_b_diagram")
            base_img = scene_base_imgs[i]

            end_curr_frame: Optional[Image.Image] = None
            for hs in range(hold_steps):
                prog = hs / float(max(1, hold_steps - 1))
                if visual_mode == "mode_a_image" and base_img is not None:
                    frame = render_mode_a_enhanced_frame(
                        base_img=base_img,
                        progress=prog,
                        camera_motion=sc.get("camera_motion", "zoom_in"),
                        width=width,
                        height=height,
                        scene=sc,
                        safe_zone=safe_zone,
                        vignette_overlay=vignette,
                    )
                else:
                    frame = render_animated_diagram_frame(
                        scene=sc,
                        progress=prog,
                        width=width,
                        height=height,
                        visual_style_key=visual_style_key,
                        safe_zone=safe_zone,
                        base_illustration=base_img,
                    )
                end_curr_frame = frame
                fpath = shared_frames_dir / f"{scene_id}_h_{hs:03d}.jpg"
                frame.save(fpath, format="JPEG", quality=92, subsampling=0)
                safe_p = str(fpath.resolve()).replace("\\", "/")
                concat_lines.append(f"file '{safe_p}'")
                concat_lines.append(f"duration {hold_step_dur:.3f}")
                last_frame_path = fpath

            if t_dur >= 0.15 and has_next and end_curr_frame is not None:
                next_sc = scenes[i + 1]
                next_base = scene_base_imgs[i + 1]
                if next_sc.get("visual_mode") == "mode_a_image" and next_base is not None:
                    start_next_frame = render_mode_a_enhanced_frame(
                        base_img=next_base,
                        progress=0.0,
                        camera_motion=next_sc.get("camera_motion", "zoom_in"),
                        width=width,
                        height=height,
                        scene=next_sc,
                        safe_zone=safe_zone,
                        vignette_overlay=vignette,
                    )
                else:
                    start_next_frame = render_animated_diagram_frame(
                        scene=next_sc,
                        progress=0.0,
                        width=width,
                        height=height,
                        visual_style_key=visual_style_key,
                        safe_zone=safe_zone,
                        base_illustration=next_base,
                    )

                t_steps = max(4, min(10, int(round(t_dur * 12))))
                t_step_dur = t_dur / float(t_steps)
                for ts in range(1, t_steps + 1):
                    raw_a = ts / float(t_steps)
                    alpha = raw_a * raw_a * (3.0 - 2.0 * raw_a)
                    blended = Image.blend(end_curr_frame, start_next_frame, alpha)
                    tpath = shared_frames_dir / f"trans_{i+1:03d}_{ts:02d}.jpg"
                    blended.save(tpath, format="JPEG", quality=91, subsampling=0)
                    safe_tp = str(tpath.resolve()).replace("\\", "/")
                    concat_lines.append(f"file '{safe_tp}'")
                    concat_lines.append(f"duration {t_step_dur:.3f}")
                    last_frame_path = tpath

        if last_frame_path is not None:
            concat_lines.append(f"file '{str(last_frame_path.resolve()).replace(chr(92), '/')}'")

        shared_concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    # Crear enlace en exports_dir/frames para el inspector de fotogramas negros (Fase 16)
    frames_dir = exports_dir / "frames"
    concat_file = shared_concat_file

    # Audio maestro + Música con Auto-Ducking (reutilizado por versión)
    narration_wav = project_dir / f"narracion_{version}.wav"
    if not narration_wav.exists():
        narration_wav = project_dir / "narracion_completa.wav"
    shared_mixed_wav = project_dir / "exports" / f"_shared_audio_{version}.wav"
    if not shared_mixed_wav.exists():
        final_audio = video_pipeline.mix_narration_with_bg_music(
            narration_wav_path=narration_wav,
            output_wav_path=shared_mixed_wav,
            bg_music_style=bg_music,
            bg_music_volume=bg_music_volume,
        )
    else:
        final_audio = shared_mixed_wav

    # Subtítulos .SRT y .ASS con márgenes seguros de la plataforma
    srt_content = video_pipeline.generate_srt_content(scenes)
    srt_path = exports_dir / f"subtitulos_{platform_id}.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    ass_filename = f"subtitulos_{platform_id}.ass"
    ass_path = exports_dir / ass_filename
    ass_content = generate_platform_safe_ass_subtitles(
        scenes=scenes,
        width=width,
        height=height,
        subtitle_style=subtitle_style,
        safe_zone=safe_zone,
    )
    ass_path.write_text(ass_content, encoding="utf-8")

    output_mp4 = exports_dir / f"video_{platform_id}.mp4"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file.resolve()),
        "-i",
        str(final_audio.resolve()),
    ]
    if burn_subtitles and ass_path.exists():
        cmd.extend(["-vf", f"ass={ass_filename}"])

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-crf",
            "17",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-shortest",
            str(output_mp4.resolve()),
        ]
    )

    proc = subprocess.run(cmd, cwd=str(exports_dir.resolve()), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Error en FFmpeg ({platform_id}): {proc.stderr[-400:]}")

    return {
        "platform_id": platform_id,
        "platform_name": profile["name"],
        "version_source": version,
        "width": width,
        "height": height,
        "aspect_ratio": profile["aspect_ratio"],
        "video_path": str(output_mp4),
        "srt_path": str(srt_path),
        "ass_path": str(ass_path),
    }
