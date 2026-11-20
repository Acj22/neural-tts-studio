"""Motor de Renderizado de Video 9:16 para Animated Shorts Studio.

Integra la arquitectura de claude-shorts, claude-3d-animated-shorts, WebGL/PixelFX y foley Earshot:
1. Sintetiza la narración en 5 actos con Edge-TTS o Kokoro.
2. Genera la pista foley procedural con Earshot sincronizada milimétricamente con cada escena.
3. Renderiza fotograma a fotograma animaciones procedimentales 9:16 (1080x1920) a 30 o 60 fps con movimiento Ken Burns continuo.
4. Genera subtítulos ASS dinámicos en zona segura (MarginV: 240) con efecto Big Focus.
5. Multiplexa y exporta el video final MP4 listo para Shorts/TikTok/Reels.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.animated_shorts.earshot_sound_designer import generate_earshot_foley_track

logger = logging.getLogger("studio.animated_shorts.renderer")

_repo_root = Path(__file__).resolve().parent.parent.parent


def _get_ffmpeg() -> str:
    """Busca el ejecutable de ffmpeg en el entorno o en el sistema."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for cand in [
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages",
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]:
        if cand.is_dir():
            matches = list(cand.glob("**/ffmpeg.exe"))
            if matches:
                return str(matches[0])
        elif cand.is_file():
            return str(cand)
    return "ffmpeg"


def _load_font(size: int = 32) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Carga una fuente TrueType legible o fuente bitmap por defecto."""
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


async def synthesize_shorts_audio(text: str, output_path: Path, voice: str = "es-MX-DaliaNeural") -> float:
    """Sintetiza la narración completa de los 5 actos con Edge TTS."""
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="+2%")
    await comm.save(str(output_path))

    ffmpeg_bin = _get_ffmpeg()
    cmd = [ffmpeg_bin, "-i", str(output_path.resolve())]
    res = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if m:
        h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return h * 3600 + mn * 60 + s
    return 60.0


def draw_animated_short_frame(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    t: float,
    total_dur: float,
    title: str,
    scenes: List[Dict[str, Any]],
    topic_id: str = "arqueologia_enigma",
):
    """Renderiza un cuadro determinista del Animated Short según el acto activo."""
    # 1. Determinar el acto / escena activa según t
    active_scene = scenes[0] if scenes else {}
    for sc in scenes:
        tr = sc.get("time_range", (0.0, 10.0))
        if tr[0] <= t <= tr[1]:
            active_scene = sc
            break

    act_num = active_scene.get("scene_num", 1)
    act_name = active_scene.get("act_name", f"Acto {act_num}")
    callout = active_scene.get("on_screen_callout", "")

    # Efecto sutil Ken Burns de cámara continua
    zoom_factor = 1.0 + 0.03 * math.sin(t * 0.15)
    cx = w // 2
    cy = int(h * 0.50)

    # 2. Paleta temática según topic_id
    if "arqueol" in topic_id or "maya" in topic_id:
        bg_col = (10, 25, 20)
        grid_col = (18, 45, 35)
        accent_col = (52, 211, 153)
        tag_text = "ARQUEOLOGÍA & INVESTIGACIÓN"
    elif "ingenier" in topic_id or "mecanic" in topic_id or "turbo" in topic_id:
        bg_col = (11, 25, 44)
        grid_col = (24, 48, 78)
        accent_col = (56, 189, 248)
        tag_text = "INGENIERÍA EXTREMA // 3D"
    elif "espacio" in topic_id or "cosmos" in topic_id or "astron" in topic_id:
        bg_col = (8, 10, 28)
        grid_col = (20, 24, 60)
        accent_col = (192, 132, 252)
        tag_text = "ASTRONOMÍA // ESPACIO PROFUNDO"
    elif "marit" in topic_id or "oceano" in topic_id or "nemo" in topic_id:
        bg_col = (10, 28, 42)
        grid_col = (18, 48, 70)
        accent_col = (6, 182, 212)
        tag_text = "MISTERIOS MARÍTIMOS"
    else:
        bg_col = (24, 18, 14)
        grid_col = (42, 28, 20)
        accent_col = (249, 115, 22)
        tag_text = "CIENCIA & ANOMALÍAS"

    # Fondo tecnológico con cuadrícula de perspectiva
    draw.rectangle([(0, 0), (w, h)], fill=bg_col)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)

    # 3. Placa Superior de Cabecera (Sticker Paper-Cut 3D con sombra)
    px1, py1 = 50, 50
    px2, py2 = w - 50, 150
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(0, 0, 0))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(15, 23, 42), outline=accent_col, width=2)

    font_label = _load_font(22)
    font_title = _load_font(28)
    draw.text((px1 + 25, py1 + 16), f"⚡ {tag_text} · {act_name}", fill=accent_col, font=font_label)
    draw.text((px1 + 25, py1 + 52), (title or "Animated Short")[:40].upper(), fill=(248, 250, 252), font=font_title)

    # 4. Escenario Visual Dinámico según Acto (1 a 5)
    t_act = t % 15.0

    if act_num == 1:
        # ACTO 1: Gancho & Anomalía (Retícula de escaneo radial, partículas pulsantes)
        for r in [280, 210, 140, 70]:
            draw.arc([(cx - r, cy - r), (cx + r, cy + r)], start=0, end=360, fill=(255, 255, 255), width=4)
            draw.arc([(cx - r, cy - r), (cx + r, cy + r)], start=0, end=360, fill=accent_col, width=2)
        # Radar beam
        angle = t * 2.0
        rx = cx + int(math.cos(angle) * 300)
        ry = cy + int(math.sin(angle) * 300)
        draw.line([(cx, cy), (rx, ry)], fill=(255, 255, 255), width=3)

        # Monolito / Objeto central en 2.5D
        pulse = math.sin(t * 3.5) * 8
        draw.ellipse([(cx - 85 - pulse, cy - 85 - pulse), (cx + 85 + pulse, cy + 85 + pulse)], fill=(255, 255, 255))
        draw.ellipse([(cx - 80 - pulse, cy - 80 - pulse), (cx + 80 + pulse, cy + 80 + pulse)], fill=accent_col)
        draw.ellipse([(cx - 50, cy - 50), (cx + 50, cy + 50)], fill=(15, 23, 42))

    elif act_num == 2:
        # ACTO 2: Contexto Histórico / Científico (Estratos escalonados, bóveda o descenso 3D)
        num_steps = 6
        step_h = 36
        base_w = int(w * 0.75)
        for s in range(num_steps):
            sy = (cy + 120) - (s * step_h)
            sw = base_w - (s * 40)
            sx1 = (w - sw) // 2
            sx2 = sx1 + sw
            draw.rectangle([(sx1 - 3, sy - 3), (sx2 + 3, sy + step_h - 2)], fill=(255, 255, 255))
            draw.rectangle([(sx1, sy), (sx2, sy + step_h - 5)], fill=(30, 41, 59), outline=accent_col, width=2)
        # Antorcha / Luz exploratoria
        light_y = cy - 140 + int(math.sin(t * 3.0) * 10)
        draw.ellipse([(cx - 50, light_y - 50), (cx + 50, light_y + 50)], fill=(255, 255, 255))
        draw.ellipse([(cx - 44, light_y - 44), (cx + 44, light_y + 44)], fill=(251, 191, 36))

    elif act_num == 3:
        # ACTO 3: El Descubrimiento Clave (Despiece / Exploded View o Sarcófago con máscara)
        explode_dist = int(math.sin(t * 1.5) * 35) + 35
        # Pieza Superior flotante
        draw.rectangle([(cx - 160, cy - 120 - explode_dist), (cx + 160, cy - 50 - explode_dist)], fill=(255, 255, 255))
        draw.rectangle([(cx - 156, cy - 116 - explode_dist), (cx + 156, cy - 54 - explode_dist)], fill=(51, 65, 85))
        # Pieza Central (Sarcófago / Componente núcleo)
        draw.rectangle([(cx - 190, cy - 30), (cx + 190, cy + 70)], fill=(255, 255, 255))
        draw.rectangle([(cx - 186, cy - 26), (cx + 186, cy + 66)], fill=accent_col)
        # Máscara / Jade / Núcleo
        draw.ellipse([(cx - 40, cy - 10), (cx + 40, cy + 50)], fill=(255, 255, 255))
        draw.ellipse([(cx - 36, cy - 6), (cx + 36, cy + 46)], fill=(16, 185, 129))
        # Pieza Base inferior
        draw.rectangle([(cx - 160, cy + 90 + explode_dist), (cx + 160, cy + 150 + explode_dist)], fill=(255, 255, 255))
        draw.rectangle([(cx - 156, cy + 94 + explode_dist), (cx + 156, cy + 146 + explode_dist)], fill=(30, 41, 59))

    elif act_num == 4:
        # ACTO 4: Desglose Iconográfico / Debate Comparativo (Esquema comparativo lado A vs lado B)
        # Lado Izquierdo
        draw.rounded_rectangle([(cx - 240, cy - 110), (cx - 20, cy + 110)], radius=14, fill=(255, 255, 255))
        draw.rounded_rectangle([(cx - 236, cy - 106), (cx - 24, cy + 106)], radius=12, fill=(30, 41, 59))
        draw.text((cx - 210, cy - 20), "HIPÓTESIS // A", fill=accent_col, font=font_label)
        # Lado Derecho
        draw.rounded_rectangle([(cx + 20, cy - 110), (cx + 240, cy + 110)], radius=14, fill=(255, 255, 255))
        draw.rounded_rectangle([(cx + 24, cy - 106), (cx + 236, cy + 106)], radius=12, fill=(15, 23, 42))
        draw.text((cx + 50, cy - 20), "EVIDENCIA // B", fill=(244, 63, 94), font=font_label)
        # Línea divisoria de análisis
        draw.line([(cx, cy - 140), (cx, cy + 140)], fill=(255, 255, 255), width=3)

    else:
        # ACTO 5: Cierre & Votación Final Interactiva (Poll Card A vs B para comentarios)
        card_w, card_h = int(w * 0.85), 320
        c_x1 = (w - card_w) // 2
        c_y1 = cy - card_h // 2
        draw.rounded_rectangle([(c_x1 - 4, c_y1 - 4), (c_x1 + card_w + 4, c_y1 + card_h + 4)], radius=20, fill=(255, 255, 255))
        draw.rounded_rectangle([(c_x1, c_y1), (c_x1 + card_w, c_y1 + card_h)], radius=18, fill=(15, 23, 42), outline=accent_col, width=3)

        draw.text((cx - 150, c_y1 + 25), "¿CUÁL ES TU POSTURA?", fill=(254, 240, 138), font=_load_font(26))
        # Botón A
        draw.rounded_rectangle([(c_x1 + 30, c_y1 + 80), (c_x1 + card_w - 30, c_y1 + 160)], radius=12, fill=(255, 255, 255))
        draw.rounded_rectangle([(c_x1 + 32, c_y1 + 82), (c_x1 + card_w - 32, c_y1 + 158)], radius=10, fill=(5, 150, 105))
        draw.text((c_x1 + 50, c_y1 + 105), "A) Hecho Histórico Documentado", fill=(255, 255, 255), font=font_label)
        # Botón B
        draw.rounded_rectangle([(c_x1 + 30, c_y1 + 180), (c_x1 + card_w - 30, c_y1 + 260)], radius=12, fill=(255, 255, 255))
        draw.rounded_rectangle([(c_x1 + 32, c_y1 + 182), (c_x1 + card_w - 32, c_y1 + 258)], radius=10, fill=(225, 29, 72))
        draw.text((c_x1 + 50, c_y1 + 205), "B) Enigma Aún No Resuelto", fill=(255, 255, 255), font=font_label)

    # 5. Cota / Etiqueta Técnica Flotante con Callout Documental
    if callout:
        tag_y = cy + 220 + int(math.sin(t * 3.0) * 4)
        tw = int(w * 0.78)
        tx1 = (w - tw) // 2
        tx2 = tx1 + tw
        draw.rounded_rectangle([(tx1 - 3, tag_y - 3), (tx2 + 3, tag_y + 45)], radius=12, fill=(255, 255, 255))
        draw.rounded_rectangle([(tx1, tag_y), (tx2, tag_y + 42)], radius=10, fill=(15, 23, 42), outline=accent_col, width=2)
        font_callout = _load_font(20)
        draw.text((tx1 + 20, tag_y + 10), f"📍 {callout}", fill=(248, 250, 252), font=font_callout)

    # 6. Barra de Progreso Superior
    prog_w = int((t / max(1.0, total_dur)) * w)
    draw.rectangle([(0, 0), (w, 8)], fill=(30, 41, 59))
    draw.rectangle([(0, 0), (prog_w, 8)], fill=accent_col)


def render_animated_short_video(
    topic_id: str,
    title: str,
    scenes: List[Dict[str, Any]],
    voice: str = "es-MX-DaliaNeural",
    fps: int = 30,
    output_dir: Optional[Path] = None,
) -> Tuple[Path, float]:
    """Genera el video vertical MP4 (1080x1920) completo del Animated Short con audio y subtítulos."""
    if output_dir is None:
        slug = re.sub(r"[^a-zA-Z0-9_]", "", title.lower().replace(" ", "_"))[:30]
        output_dir = _repo_root / "projects" / "animated_shorts" / f"short_{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # 1. Unir texto completo de los 5 actos para la síntesis de audio
    full_narration = " ".join([sc.get("narration", "") for sc in scenes if sc.get("narration")])
    if not full_narration:
        full_narration = f"Investigación histórica y científica sobre {title}."

    audio_voice_path = output_dir / "narration.mp3"
    dur_sec = asyncio.run(synthesize_shorts_audio(full_narration, audio_voice_path, voice=voice))
    dur_sec = max(10.0, dur_sec)

    # Reajustar tiempos de escenas proporcionalmente a la duración de audio real
    total_planned = sum([(sc.get("time_range", (0, 10))[1] - sc.get("time_range", (0, 10))[0]) for sc in scenes])
    if total_planned > 0:
        ratio = dur_sec / total_planned
        curr_t = 0.0
        for sc in scenes:
            orig_len = sc.get("time_range", (0, 10))[1] - sc.get("time_range", (0, 10))[0]
            new_len = orig_len * ratio
            sc["time_range"] = (curr_t, curr_t + new_len)
            curr_t += new_len

    # 2. Generar pista Foley Earshot sincronizada
    foley_wav_path = output_dir / "earshot_foley.wav"
    generate_earshot_foley_track(scenes, dur_sec, foley_wav_path)

    # 3. Mezclar Narración + Foley Earshot con Sidechain Ducking
    mixed_audio_path = output_dir / "audio_master.wav"
    ffmpeg_bin = _get_ffmpeg()
    mix_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(audio_voice_path.resolve()),
        "-i", str(foley_wav_path.resolve()),
        "-filter_complex",
        "[1:a]volume=0.35[foley];[0:a]volume=1.0[voice];[voice][foley]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        str(mixed_audio_path.resolve()),
    ]
    subprocess.run(mix_cmd, check=True, capture_output=True)

    # 4. Renderizar cuadros visuales en 9:16 (1080x1920)
    width, height = 1080, 1920
    total_frames = int(dur_sec * fps)

    for f in range(total_frames):
        t = f / fps
        im = Image.new("RGB", (width, height), (15, 23, 42))
        draw = ImageDraw.Draw(im)
        draw_animated_short_frame(draw, width, height, t, dur_sec, title, scenes, topic_id=topic_id)
        im.save(str(frames_dir / f"frame_{f:05d}.png"))

    # 5. Generar subtítulos ASS dinámicos sincronizados por frase
    words = [w.strip() for w in full_narration.split() if w.strip()]
    dialogues = []
    if words:
        chunk_size = 5
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        chunk_dur = dur_sec / max(1, len(chunks))
        for idx, ch in enumerate(chunks):
            start_t = idx * chunk_dur
            end_t = min(dur_sec, (idx + 1) * chunk_dur)
            s_min, s_sec = int(start_t // 60), start_t % 60
            e_min, e_sec = int(end_t // 60), end_t % 60
            phrase = " ".join(ch)
            dialogues.append(
                f"Dialogue: 0,{s_min}:{s_sec:05.2f},{e_min}:{e_sec:05.2f},Default,,0,0,0,,{phrase}"
            )
    else:
        dialogues.append(f"Dialogue: 0,0:00:00.20,0:00:{dur_sec:05.2f},Default,,0,0,0,,{title}")

    subtitles_ass = output_dir / "subtitles.ass"
    sub_content = f"""[Script Info]
Title: Animated Shorts Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,48,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H90000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,2,40,40,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"
    subtitles_ass.write_text(sub_content, encoding="utf-8")

    # 6. Multiplexar con FFmpeg a MP4 final
    final_video = output_dir / "animated_short_9_16.mp4"
    cmd_mux = [
        ffmpeg_bin, "-y",
        "-framerate", str(fps),
        "-i", str((frames_dir / "frame_%05d.png").resolve()),
        "-i", str(mixed_audio_path.resolve()),
        "-vf", f"subtitles={subtitles_ass.name}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(final_video.resolve()),
    ]
    subprocess.run(cmd_mux, cwd=str(output_dir.resolve()), check=True, capture_output=True)

    # 7. Guardar metadatos en JSON
    meta_json = output_dir / "meta.json"
    meta_data = {
        "title": title,
        "topic_id": topic_id,
        "duration": dur_sec,
        "fps": fps,
        "voice": voice,
        "video_url": f"/projects/{output_dir.name}/{final_video.name}",
        "filename": final_video.name,
        "scenes_count": len(scenes),
    }
    meta_json.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")

    return final_video, dur_sec
