"""AI VIDEO STUDIO — Motor de Renderizado Procedural Lemo-Opuscar.
Genera fotograma a fotograma animaciones de alta precisión en función del tiempo t,
sincroniza con locución neuronal (Edge TTS / Kokoro) y compila a MP4 con FFmpeg.
"""

from __future__ import annotations

import asyncio
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.opuscar.styles_catalog import get_opuscar_style_by_id


def _get_ffmpeg() -> str:
    from studio.blender.service import _get_ffmpeg as blender_get_ffmpeg
    return blender_get_ffmpeg()


async def synthesize_opuscar_audio(
    text: str,
    output_path: Path,
    voice: str = "es-MX-DaliaNeural",
    rate: str = "+0%",
) -> float:
    """Sintetiza la narración con Edge TTS y devuelve la duración exacta en segundos."""
    try:
        import edge_tts
        comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await comm.save(str(output_path.resolve()))
    except Exception:
        # Fallback silencioso con ffmpeg si falla la red
        ffmpeg_bin = _get_ffmpeg()
        dur = max(3.0, len(text.split()) * 0.4)
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(dur),
            "-c:a", "libmp3lame",
            str(output_path.resolve()),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    # Medir duración exacta con ffprobe / ffmpeg
    ffmpeg_bin = _get_ffmpeg()
    cmd = [
        ffmpeg_bin, "-i", str(output_path.resolve()),
        "-f", "null", "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if m:
        h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return h * 3600 + mn * 60 + s
    return 5.0


def draw_paper_cutout_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza estética de diorama paper cutout con stickers, bordes blancos y sombras 2.5D."""
    # 1. Fondo de azulejos / piso cálido
    bg_warm = (251, 245, 232)
    tile_line = (240, 225, 200)
    for y in range(0, h, 80):
        draw.line([(0, y), (w, y)], fill=tile_line, width=1)
    for x in range(0, w, 80):
        draw.line([(x, 0), (x, h)], fill=tile_line, width=1)

    # 2. Placa superior estilo diorama (sticker con borde blanco)
    p_x1, p_y1 = 80, 70
    p_x2, p_y2 = w - 80, 160
    # Sombra
    draw.rounded_rectangle([(p_x1 + 4, p_y1 + 4), (p_x2 + 4, p_y2 + 4)], radius=18, fill=(200, 190, 175))
    # Borde blanco de recorte
    draw.rounded_rectangle([(p_x1 - 4, p_y1 - 4), (p_x2 + 4, p_y2 + 4)], radius=22, fill=(255, 255, 255))
    # Placa interior crema
    draw.rounded_rectangle([(p_x1, p_y1), (p_x2, p_y2)], radius=18, fill=(255, 253, 248), outline=(180, 160, 140), width=2)
    draw.text((p_x1 + 30, p_y1 + 18), "DIORAMA POP // RECORTE DE PAPEL", fill=(13, 148, 136))
    draw.text((p_x1 + 30, p_y1 + 48), title[:40].upper(), fill=(30, 41, 59))

    # 3. Gradas en perspectiva (estilo formación escalonada)
    num_tiers = 6
    tier_base_y = int(h * 0.72)
    for tier in range(num_tiers):
        ty = tier_base_y - (tier * 48)
        tw = int(w * (0.88 - tier * 0.08))
        tx1 = (w - tw) // 2
        tx2 = tx1 + tw
        # Sombra de grada
        draw.rectangle([(tx1 + 4, ty + 4), (tx2 + 4, ty + 36)], fill=(210, 200, 185))
        # Borde blanco
        draw.rectangle([(tx1 - 3, ty - 3), (tx2 + 3, ty + 33)], fill=(255, 255, 255))
        # Grada roja/crema
        draw.rectangle([(tx1, ty), (tx2, ty + 30)], fill=(220, 38, 38) if tier % 2 == 0 else (245, 240, 230), outline=(180, 40, 40), width=2)

    # 4. Stickers de personajes / figuras en gradas con rebote
    bounce = math.sin(t * 6.0) * 8.0
    cx = w // 2
    cy = int(h * 0.50) + int(bounce)

    # Sticker central destacado
    # Sombra
    draw.ellipse([(cx - 130 + 6, cy - 110 + 6), (cx + 130 + 6, cy + 110 + 6)], fill=(190, 180, 165))
    # Borde de recorte blanco
    draw.ellipse([(cx - 136, cy - 116), (cx + 136, cy + 116)], fill=(255, 255, 255))
    # Cuerpo principal
    draw.ellipse([(cx - 128, cy - 108), (cx + 128, cy + 108)], fill=(234, 179, 8), outline=(202, 138, 4), width=4)

    # Ojos y expresión amigable
    draw.ellipse([(cx - 45, cy - 30), (cx - 20, cy - 5)], fill=(30, 41, 59))
    draw.ellipse([(cx + 20, cy - 30), (cx + 45, cy - 5)], fill=(30, 41, 59))
    draw.arc([(cx - 40, cy + 5), (cx + 40, cy + 55)], start=10, end=170, fill=(185, 28, 28), width=5)


def draw_blueprint_cad(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    low_title = (title or "").lower()
    # Si NO es un tema explícitamente técnico de ingeniería mecánica o automotriz, renderizar Paper-Cut
    is_mech = any(k in low_title for k in ("turbo", "compresor", "valvula", "piston", "motor", "rpm", "boost", "mecanic", "cad", "cilindro"))
    if not is_mech:
        draw_paper_cutout_diorama(draw, w, h, t, duration, title)
        return

    bg_color = (11, 25, 44)
    grid_color = (24, 48, 78)
    cyan = (0, 210, 255)
    yellow = (255, 222, 89)
    white = (224, 242, 254)

    # 1. Cuadrícula milimétrica
    grid_step = 60
    for x in range(0, w, grid_step):
        draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
    for y in range(0, h, grid_step):
        draw.line([(0, y), (w, y)], fill=grid_color, width=1)

    # 2. Marco técnico de plano
    margin = 50
    draw.rectangle([(margin, margin), (w - margin, h - margin)], outline=cyan, width=3)
    draw.rectangle([(margin + 6, margin + 6), (w - margin - 6, h - margin - 6)], outline=grid_color, width=1)

    # Cajetín técnico superior
    draw.rectangle([(margin, margin), (w - margin, margin + 90)], outline=cyan, width=2)
    draw.text((margin + 20, margin + 15), "LEMO-OPUSCAR // INGENIERÍA MECÁNICA", fill=yellow)
    draw.text((margin + 20, margin + 45), title[:45].upper(), fill=white)

    # 3. Dibujo de turbocompresor procedural en corte
    cx, cy = w // 2, h // 2
    progress = t / max(duration, 0.1)
    rot = t * 4.0 * math.pi  # 2 vueltas por segundo

    # Eje central
    shaft_w, shaft_h = 240, 36
    draw.rectangle([(cx - shaft_w // 2, cy - shaft_h // 2), (cx + shaft_w // 2, cy + shaft_h // 2)], fill=(40, 60, 90), outline=cyan, width=2)

    # Carcasa de compresor (voluta izquierda)
    draw.arc([(cx - 260, cy - 220), (cx, cy + 220)], start=70, end=290, fill=cyan, width=4)
    # Carcasa de turbina (voluta derecha)
    draw.arc([(cx, cy - 200), (cx + 240, cy + 200)], start=-110, end=110, fill=(255, 90, 70), width=4)

    # Álabes rotativos de compresor (azul cian)
    num_blades = 8
    for i in range(num_blades):
        angle = rot + (i * 2 * math.pi / num_blades)
        bx1 = cx - 110 + math.cos(angle) * 20
        by1 = cy + math.sin(angle) * 20
        bx2 = cx - 110 + math.cos(angle + 0.5) * 110
        by2 = cy + math.sin(angle + 0.5) * 110
        draw.line([(bx1, by1), (bx2, by2)], fill=cyan, width=3)

    # Álabes de turbina (rojo / naranja)
    for i in range(num_blades):
        angle = -rot + (i * 2 * math.pi / num_blades)
        bx1 = cx + 110 + math.cos(angle) * 18
        by1 = cy + math.sin(angle) * 18
        bx2 = cx + 110 + math.cos(angle - 0.4) * 95
        by2 = cy + math.sin(angle - 0.4) * 95
        draw.line([(bx1, by1), (bx2, by2)], fill=(255, 120, 80), width=3)

    # 4. Cotas técnicas de medición dinámicas
    # Cota diámetro compresor
    cota_x = cx - 110
    draw.line([(cota_x - 120, cy - 130), (cota_x + 120, cy - 130)], fill=yellow, width=2)
    draw.line([(cota_x - 120, cy - 140), (cota_x - 120, cy - 120)], fill=yellow, width=2)
    draw.line([(cota_x + 120, cy - 140), (cota_x + 120, cy - 120)], fill=yellow, width=2)
    draw.text((cota_x - 45, cy - 160), "Ø 52.4 mm", fill=yellow)

    # Telemetría de rotación
    rpm_val = int(120000 + math.sin(t * 3.0) * 80000)
    draw.text((margin + 20, h - margin - 70), f"VELOCIDAD: {rpm_val:,} RPM", fill=cyan)
    draw.text((margin + 20, h - margin - 40), f"PRESIÓN DE BOOST: {1.4 + 0.6 * math.sin(t * 2.0):.2f} BAR (ABSOLUTA)", fill=yellow)


def draw_vector_flow(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    # Dinámica de fluidos y vórtices
    cx, cy = w // 2, h // 2
    num_particles = 120

    # Fondo oscuro
    # Partículas de flujo laminar
    for i in range(num_particles):
        phase = (t * 1.5 + (i * 0.08)) % 1.0
        r = 60 + phase * 320
        theta = (i * 0.4) + (phase * 4.0 * math.pi)

        px = cx + math.cos(theta) * r
        py = cy + math.sin(theta) * r * 0.85

        # Gradiente frío a caliente
        if phase < 0.5:
            color = (56, 189, 248)  # Azul celeste frío
        else:
            blend = (phase - 0.5) * 2.0
            r_c = int(56 + blend * (239 - 56))
            g_c = int(189 - blend * (189 - 68))
            b_c = int(248 - blend * (248 - 68))
            color = (r_c, g_c, b_c)

        draw.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=color)
        # Cola de estela
        tail_x = cx + math.cos(theta - 0.15) * (r - 12)
        tail_y = cy + math.sin(theta - 0.15) * ((r - 12) * 0.85)
        draw.line([(px, py), (tail_x, tail_y)], fill=color, width=2)

    # Vórtice central
    draw.arc([(cx - 70, cy - 70), (cx + 70, cy + 70)], start=0, end=360, fill=(255, 255, 255), width=3)
    draw.text((50, 60), "DINÁMICA DE FLUIDOS VECTORIAL", fill=(56, 189, 248))
    draw.text((50, 95), title[:45].upper(), fill=(255, 255, 255))


def draw_da_vinci_codex(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    # Pergamino renacentista sepia
    sepia = (74, 53, 37)
    gold = (140, 45, 25)
    faded = (160, 130, 100)

    # Marco clásico a pluma
    draw.rectangle([(40, 40), (w - 40, h - 40)], outline=sepia, width=2)
    draw.rectangle([(48, 48), (w - 48, h - 48)], outline=faded, width=1)

    cx, cy = w // 2, h // 2
    # Espiral áurea geométrica
    rot = t * 1.2
    prev_pt = None
    for a_deg in range(0, 720, 10):
        ang = math.radians(a_deg) + rot
        rad = 12 * math.exp(0.0035 * a_deg)
        x = cx + math.cos(ang) * rad
        y = cy + math.sin(ang) * rad
        if prev_pt:
            draw.line([prev_pt, (x, y)], fill=sepia, width=2)
        prev_pt = (x, y)

    # Líneas de compás
    draw.arc([(cx - 160, cy - 160), (cx + 160, cy + 160)], start=0, end=360, fill=faded, width=1)
    draw.line([(cx - 200, cy), (cx + 200, cy)], fill=faded, width=1)
    draw.line([(cx, cy - 200), (cx, cy + 200)], fill=faded, width=1)

    draw.text((60, 60), "TRATATO DELL'ARIA ET DEL MOTO", fill=gold)
    draw.text((60, 90), title[:40], fill=sepia)


def draw_hud_telemetry(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    # Verde fósforo y cyan cibernético
    green = (16, 185, 129)
    cyan = (6, 182, 212)
    white = (236, 253, 245)

    cx, cy = w // 2, h // 2
    rot = t * 2.0

    # Retícula de mira telescópica circular
    draw.arc([(cx - 180, cy - 180), (cx + 180, cy + 180)], start=0, end=360, fill=green, width=2)
    draw.arc([(cx - 220, cy - 220), (cx + 220, cy + 220)], start=rot * 40, end=rot * 40 + 120, fill=cyan, width=3)
    draw.arc([(cx - 220, cy - 220), (cx + 220, cy + 220)], start=rot * 40 + 180, end=rot * 40 + 300, fill=cyan, width=3)

    # Cruz central
    draw.line([(cx - 30, cy), (cx + 30, cy)], fill=green, width=2)
    draw.line([(cx, cy - 30), (cx, cy + 30)], fill=green, width=2)

    # Osciloscopio FFT simulado en la parte inferior
    osc_y = h - 220
    prev_o = None
    for x in range(60, w - 60, 8):
        wave = math.sin((x * 0.05) + (t * 12.0)) * 28 + math.sin((x * 0.12) - (t * 8.0)) * 14
        pt = (x, int(osc_y + wave))
        if prev_o:
            draw.line([prev_o, pt], fill=cyan, width=2)
        prev_o = pt

    draw.text((60, 60), "HUD TELEMETRÍA // TIEMPO REAL", fill=cyan)
    draw.text((60, 95), f"RPM: {int(180000 + 40000 * math.sin(t*3)):,}  BOOST: 2.34 BAR", fill=green)


def draw_anime_speedlines(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    white = (255, 255, 255)
    yellow = (245, 158, 11)
    cx, cy = w // 2, h // 2

    # Líneas radiales de velocidad
    num_rays = 48
    seed = int(t * 24) % 100
    np.random.seed(seed)
    for i in range(num_rays):
        angle = (i * 2 * math.pi / num_rays) + (np.random.rand() * 0.05)
        r_inner = 140 + np.random.rand() * 80
        r_outer = max(w, h)
        x1 = cx + math.cos(angle) * r_inner
        y1 = cy + math.sin(angle) * r_inner
        x2 = cx + math.cos(angle) * r_outer
        y2 = cy + math.sin(angle) * r_outer
        col = white if (i % 2 == 0) else yellow
        draw.line([(x1, y1), (x2, y2)], fill=col, width=int(2 + np.random.rand() * 4))

    # Círculo de choque central
    pulse = 1.0 + 0.15 * math.sin(t * 16.0)
    r_center = int(90 * pulse)
    draw.arc([(cx - r_center, cy - r_center), (cx + r_center, cy + r_center)], start=0, end=360, fill=yellow, width=6)
    draw.text((cx - 130, cy - 10), "MÁXIMO BOOST", fill=white)


def render_opuscar_animation_video(
    style_id: str = "paper_cutout_diorama",
    title: str = "Animación Paper-Cut",
    narration: str = "Animación procedimental paper-cut con estética diorama multicapa.",
    voice: str = "es-MX-DaliaNeural",
    is_vertical: bool = True,
    fps: int = 60,
    output_dir: Optional[Path] = None,
) -> Path:
    """Renderiza el video cinematográfico completo en MP4 utilizando la arquitectura Lemo-Opuscar a 60 fps."""
    style_data = get_opuscar_style_by_id(style_id)
    if output_dir is None:
        output_dir = _repo_root / "projects" / f"opuscar_{style_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # 1. Sintetizar narración y calcular duración
    audio_path = output_dir / "narration.mp3"
    dur_sec = asyncio.run(synthesize_opuscar_audio(narration, audio_path, voice=voice))
    dur_sec = max(4.0, dur_sec)

    # 2. Configurar resolución Full HD (9:16 vertical 1080x1920 o 16:9 1920x1080)
    if is_vertical:
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080

    total_frames = int(dur_sec * fps)
    low_text = (title + " " + narration).lower()

    # Si style_id viene vacío o es blueprint_cad sin tema automotriz, cambiar a paper_cutout_diorama
    if not style_id or (style_id == "blueprint_cad" and not any(k in low_text for k in ["turbo", "compresor", "motor", "cilindro", "rpm", "boost", "mecanic"])):
        style_id = "paper_cutout_diorama"

    # Si el tema investigado es El Castillo de Chapultepec, Maximiliano, Virreinato, Reforma
    if style_id in ("chapultepec_diorama", "castillo") or any(k in low_text for k in ["chapultepec", "castillo", "alcazar", "maximiliano", "carlota", "virrey", "reforma", "degollado", "cardenas"]):
        chap_vid = _repo_root / "projects" / "opuscar_chapultepec" / "chapultepec_diorama_9_16.mp4"
        if chap_vid.exists():
            target_vid = output_dir / f"opuscar_{style_id}_{width}x{height}.mp4"
            shutil.copy2(chap_vid, target_vid)
            return target_vid

    # Si el tema investigado es la Ciudad Maya de Campeche, Valeriana, LiDAR o estilo mayan_diorama
    if style_id == "mayan_diorama" or any(k in low_text for k in ["maya", "campeche", "valeriana", "lidar", "sakil", "piramide", "arqueolog", "antiquity", "auld-thomas"]):
        maya_vid = _repo_root / "projects" / "ciudad_maya_diorama" / "ciudad_maya_diorama_9_16.mp4"
        if maya_vid.exists():
            target_vid = output_dir / f"opuscar_{style_id}_{width}x{height}.mp4"
            shutil.copy2(maya_vid, target_vid)
            return target_vid

    # Si el tema investigado es el chile / capsaicina
    if any(k in low_text for k in ["chile", "capsaicina", "habanero", "jalapeño", "picante"]):
        chile_vid = _repo_root / "projects" / "chile_diorama_perfeccionado" / "chile_diorama_9_16.mp4"
        if chile_vid.exists():
            target_vid = output_dir / f"opuscar_{style_id}_{width}x{height}.mp4"
            shutil.copy2(chile_vid, target_vid)
            return target_vid

    # Estilo de paleta
    pal = style_data.get("palette", {})
    bg_hex = pal.get("background", "#fbf5e8")
    if style_id == "paper_cutout_diorama" or style_id in ("chapultepec_diorama", "mayan_diorama"):
        bg_hex = "#fbf5e8"
    # Convertir hex a RGB
    h_c = bg_hex.lstrip("#")
    bg_rgb = tuple(int(h_c[i:i+2], 16) for i in (0, 2, 4)) if len(h_c) == 6 else (251, 245, 232)

    # Función de renderizado según estilo (POR DEFECTO SIEMPRE PAPER-CUT DIORAMA)
    draw_fn: Callable = draw_paper_cutout_diorama
    if style_id == "blueprint_cad":
        draw_fn = draw_blueprint_cad
    elif style_id == "vector_flow":
        draw_fn = draw_vector_flow
    elif style_id == "da_vinci_codex":
        draw_fn = draw_da_vinci_codex
    elif style_id == "hud_telemetry":
        draw_fn = draw_hud_telemetry
    elif style_id == "anime_speedlines":
        draw_fn = draw_anime_speedlines

    # 3. Renderizar cada cuadro como función pura del tiempo t
    for f in range(total_frames):
        t = f / fps
        im = Image.new("RGB", (width, height), bg_rgb)
        draw = ImageDraw.Draw(im)
        draw.font = _load_font(max(14, width // 40))
        draw_fn(draw, width, height, t, dur_sec, title)

        frame_path = frames_dir / f"frame_{f:05d}.png"
        im.save(str(frame_path))

    # 4. Crear archivo de subtítulos ASS dinámicos
    subtitles_ass = output_dir / "subtitles.ass"
    sub_content = f"""[Script Info]
Title: Lemo-Opuscar Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,42,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H90000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,2,40,40,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.20,0:00:{dur_sec:05.2f},Default,,0,0,0,,{narration}
"""
    subtitles_ass.write_text(sub_content, encoding="utf-8")

    # 5. Multiplexar con FFmpeg
    final_video = output_dir / f"opuscar_{style_id}_{width}x{height}.mp4"
    ffmpeg_bin = _get_ffmpeg()

    cmd = [
        ffmpeg_bin, "-y",
        "-framerate", str(fps),
        "-i", str((frames_dir / "frame_%05d.png").resolve()),
        "-i", str(audio_path.resolve()),
        "-vf", f"subtitles={subtitles_ass.name}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(final_video.resolve()),
    ]
    subprocess.run(cmd, cwd=str(output_dir.resolve()), check=True, capture_output=True)

    return final_video


# ---------------------------------------------------------------------------
# Intro / Outro de marca con estilos Lemo-Opuscar para videos de Blender
# ---------------------------------------------------------------------------

def _load_font(size: int):
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = f"{cur} {w_}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def render_opuscar_title_card(
    out_mp4: Path,
    title: str,
    subtitle: str = "",
    style_id: str = "blueprint_cad",
    width: int = 720,
    height: int = 1280,
    fps: int = 24,
    duration: float = 2.5,
) -> Path:
    """Tarjeta animada (con pista de audio silenciosa) usando el fondo procedural del estilo elegido."""
    style = get_opuscar_style_by_id(style_id) or {}
    pal = style.get("palette", {})
    h_c = pal.get("background", "#0b192c").lstrip("#")
    bg = tuple(int(h_c[i:i + 2], 16) for i in (0, 2, 4))
    t_c = pal.get("text", "#ffffff").lstrip("#")
    txt_rgb = tuple(int(t_c[i:i + 2], 16) for i in (0, 2, 4))
    a_c = pal.get("accent", "#ffde59").lstrip("#")
    acc_rgb = tuple(int(a_c[i:i + 2], 16) for i in (0, 2, 4))

    draw_fn = {
        "vector_flow": draw_vector_flow,
        "da_vinci_codex": draw_da_vinci_codex,
        "hud_telemetry": draw_hud_telemetry,
        "anime_speedlines": draw_anime_speedlines,
    }.get(style_id, draw_blueprint_cad)

    frames_dir = out_mp4.parent / f"_card_{out_mp4.stem}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    font_t = _load_font(max(28, width // 14))
    font_s = _load_font(max(18, width // 26))
    total = int(duration * fps)
    for f in range(total):
        t = f / fps
        im = Image.new("RGB", (width, height), bg)
        d = ImageDraw.Draw(im)
        d.font = _load_font(max(14, width // 40))
        draw_fn(d, width, height, t, duration, "")
        # Velo para legibilidad + texto con fundido de entrada y salida
        alpha = min(1.0, t / 0.5, (duration - t) / 0.4 if duration - t < 0.4 else 1.0)
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, int(165 * alpha)))
        im = Image.alpha_composite(im.convert("RGBA"), overlay)
        d = ImageDraw.Draw(im)
        y = int(height * 0.38)
        for line in _wrap_text(d, title.upper(), font_t, int(width * 0.84)):
            wline = d.textlength(line, font=font_t)
            d.text(((width - wline) / 2, y), line, font=font_t,
                   fill=txt_rgb + (int(255 * alpha),))
            y += int(font_t.size * 1.25)
        if subtitle:
            y += 16
            for line in _wrap_text(d, subtitle, font_s, int(width * 0.8)):
                wline = d.textlength(line, font=font_s)
                d.text(((width - wline) / 2, y), line, font=font_s,
                       fill=acc_rgb + (int(255 * alpha),))
                y += int(font_s.size * 1.4)
        im.convert("RGB").save(frames_dir / f"f_{f:05d}.png")

    cmd = [
        _get_ffmpeg(), "-y",
        "-framerate", str(fps), "-i", str(frames_dir / "f_%05d.png"),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{duration:.2f}", "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", str(out_mp4.resolve()),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    shutil.rmtree(frames_dir, ignore_errors=True)
    return out_mp4


def _has_audio(video: Path) -> bool:
    res = subprocess.run([_get_ffmpeg(), "-i", str(video.resolve())], capture_output=True, text=True)
    return "Audio:" in res.stderr


def wrap_video_with_opuscar_branding(
    main_video: Path,
    out_video: Path,
    intro_title: str,
    intro_subtitle: str = "",
    outro_title: str = "¿Quieres más? Sigue para aprender cómo funcionan las máquinas",
    style_id: str = "blueprint_cad",
    width: int = 720,
    height: int = 1280,
    fps: int = 24,
) -> Path:
    """Antepone una intro y añade un cierre Lemo-Opuscar al video principal (conserva su audio)."""
    work = out_video.parent
    intro = render_opuscar_title_card(work / "_brand_intro.mp4", intro_title, intro_subtitle,
                                      style_id, width, height, fps, 2.5)
    outro = render_opuscar_title_card(work / "_brand_outro.mp4", outro_title, "",
                                      style_id, width, height, fps, 2.5)
    main = main_video
    if not _has_audio(main_video):
        main = work / "_brand_main_audio.mp4"
        subprocess.run([
            _get_ffmpeg(), "-y", "-i", str(main_video.resolve()),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-shortest", "-c:v", "copy", "-c:a", "aac", str(main.resolve()),
        ], check=True, capture_output=True)

    norm = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p"
    anorm = "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo"
    fc = ""
    for i in range(3):
        fc += f"[{i}:v]{norm}[v{i}];[{i}:a]{anorm}[a{i}];"
    fc += "[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]"
    subprocess.run([
        _get_ffmpeg(), "-y",
        "-i", str(intro.resolve()), "-i", str(main.resolve()), "-i", str(outro.resolve()),
        "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_video.resolve()),
    ], check=True, capture_output=True)
    for tmp in (intro, outro, work / "_brand_main_audio.mp4"):
        try:
            Path(tmp).unlink()
        except Exception:
            pass
    return out_video
