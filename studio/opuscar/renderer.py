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


def detect_diorama_archetype(text: str) -> str:
    """Clasifica el tema semántico para generar un diorama procedural auténtico."""
    low = (text or "").lower()
    if any(k in low for k in ("sahara", "richat", "mauritania")):
        return "ojo_sahara"
    if any(k in low for k in ("chapultepec", "alcazar", "maximiliano", "carlota")):
        return "chapultepec"
    if any(k in low for k in ("maya", "campeche", "valeriana", "lidar", "piramide", "sakil")):
        return "mayan"
    if any(k in low for k in ("mar", "oceano", "isla", "barco", "buque", "flannan", "celeste", "nemo", "agua", "laguna", "submarino", "fosa", "pacifico", "atlantico", "bermuda", "naufragio", "iceberg", "sentinel", "triangulo", "puerto")):
        return "oceanic"
    if any(k in low for k in ("tierra", "pozo", "kola", "mina", "cueva", "cristal", "naica", "fuego", "darvaza", "volcan", "montana", "montaña", "everest", "abismo", "salar", "hielo", "lava", "crater", "terremoto", "geolog", "centralia", "chimenea")):
        return "geological"
    if any(k in low for k in ("espacio", "planeta", "galaxia", "orbita", "agujero", "negro", "wow", "senal", "señal", "estrella", "satelite", "satélite", "universo", "cosmos", "nasa", "astron", "marte", "luna", "telescopio")):
        return "cosmic"
    if any(k in low for k in ("ciudad", "templo", "muralla", "monumento", "torre", "palacio", "catacumba", "paris", "historia", "roma", "coliseo", "antigu", "arquit", "tubos", "hospital", "castaneda", "castañeda", "obra")):
        return "architectural"
    return "mystery"


def draw_oceanic_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza diorama náutico/marítimo de papel recortado con olas dinámicas y navío."""
    # Fondo azul marino abisal con sonar
    draw.rectangle([(0, 0), (w, h)], fill=(12, 33, 49))
    grid_col = (18, 48, 71)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)

    # Placa superior
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(6, 18, 28))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(16, 44, 66), outline=(56, 189, 248), width=2)
    draw.text((px1 + 25, py1 + 16), "EXPLORACIÓN // OCÉANO & PUNTOS REMOTOS", fill=(56, 189, 248))
    draw.text((px1 + 25, py1 + 46), (title or "Misterio Oceánico")[:38].upper(), fill=(241, 245, 249))

    cx = w // 2
    cy = int(h * 0.52)

    # Olas en capas de papel recortado (4 niveles escalonados)
    wave_layers = [
        ((14, 116, 144), cy + 120, 0.0),
        ((12, 74, 96), cy + 70, 1.2),
        ((8, 51, 68), cy + 20, 2.4),
        ((6, 38, 52), cy - 30, 3.6),
    ]
    for col, base_y, phase in reversed(wave_layers):
        pts = [(0, h)]
        step = 40
        for x in range(0, w + step, step):
            wave_y = int(base_y + math.sin(t * 2.5 + phase + x * 0.015) * 16)
            pts.append((x, wave_y))
        pts.append((w, h))
        draw.polygon(pts, fill=col)
        # Borde blanco de espuma en la cresta de papel
        crest = [pts[1]]
        for p in pts[1:-1]:
            crest.append((p[0], p[1] - 2))
        for p in reversed(pts[1:-1]):
            crest.append((p[0], p[1] + 3))
        draw.polygon(crest, fill=(255, 255, 255))

    # Barco / Elemento central estilo sticker con sombra y borde blanco
    ship_y = cy - 40 + int(math.sin(t * 2.8) * 12)
    ship_rot = math.sin(t * 2.0) * 0.08
    # Casco
    draw.polygon([(cx - 140, ship_y), (cx + 140, ship_y), (cx + 90, ship_y + 60), (cx - 90, ship_y + 60)], fill=(255, 255, 255))
    draw.polygon([(cx - 134, ship_y + 3), (cx + 134, ship_y + 3), (cx + 86, ship_y + 56), (cx - 86, ship_y + 56)], fill=(225, 29, 72))
    # Mástiles
    draw.line([(cx, ship_y), (cx, ship_y - 120)], fill=(255, 255, 255), width=6)
    draw.line([(cx, ship_y), (cx, ship_y - 120)], fill=(245, 158, 11), width=4)
    draw.polygon([(cx, ship_y - 110), (cx + 80, ship_y - 70), (cx, ship_y - 30)], fill=(255, 255, 255))
    draw.polygon([(cx + 2, ship_y - 106), (cx + 74, ship_y - 70), (cx + 2, ship_y - 34)], fill=(241, 245, 249))

    # Cota técnica
    draw.rectangle([(cx - 120, cy + 180), (cx + 120, cy + 225)], fill=(255, 255, 255))
    draw.rectangle([(cx - 117, cy + 183), (cx + 117, cy + 222)], fill=(15, 23, 42))
    draw.text((cx - 100, cy + 194), "PROFUNDIDAD: >4,000 m", fill=(56, 189, 248))


def draw_geological_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza diorama de geología profunda, volcanes, cavernas y abismos."""
    # Fondo cálido ocre volcánico
    draw.rectangle([(0, 0), (w, h)], fill=(28, 18, 13))
    grid_col = (44, 28, 20)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)

    # Placa superior
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(12, 7, 5))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(45, 24, 16), outline=(249, 115, 22), width=2)
    draw.text((px1 + 25, py1 + 16), "GEOLOGÍA // ABISMOS & PROFUNDIDADES TERRESTRES", fill=(249, 115, 22))
    draw.text((px1 + 25, py1 + 46), (title or "Enigma Geológico")[:38].upper(), fill=(254, 243, 199))

    cx = w // 2
    cy = int(h * 0.52)

    # Estratos rocosos en capas paper-cut
    strata = [
        ((120, 53, 15), cy + 160),
        ((154, 52, 18), cy + 80),
        ((180, 83, 9), cy),
        ((217, 119, 6), cy - 80),
    ]
    for col, sy in strata:
        # Silueta dentada de roca con borde blanco
        draw.rectangle([(cx - int(w * 0.44) - 4, sy - 4), (cx + int(w * 0.44) + 4, sy + 64)], fill=(255, 255, 255))
        draw.rectangle([(cx - int(w * 0.44), sy), (cx + int(w * 0.44), sy + 60)], fill=col)

    # Pozo central / Falla vertical luminosa
    pulse = 0.5 + 0.5 * math.sin(t * 4.0)
    draw.rectangle([(cx - 38, cy - 140), (cx + 38, cy + 200)], fill=(255, 255, 255))
    draw.rectangle([(cx - 32, cy - 136), (cx + 32, cy + 196)], fill=(15, 23, 42))
    draw.rectangle([(cx - 16, cy - 130), (cx + 16, cy + 190)], fill=(int(249 + 6 * pulse), int(115 * pulse), 22))

    # Cota técnica
    draw.rectangle([(cx - 120, cy + 215), (cx + 120, cy + 260)], fill=(255, 255, 255))
    draw.rectangle([(cx - 117, cy + 218), (cx + 117, cy + 257)], fill=(15, 23, 42))
    draw.text((cx - 100, cy + 228), "SONDEO: 12,262 m // +180°C", fill=(251, 146, 60))


def draw_cosmic_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza diorama cósmico / astronómico con anillos orbitales y astros."""
    # Fondo espacio profundo
    draw.rectangle([(0, 0), (w, h)], fill=(8, 10, 24))
    # Estrellas de papel
    for i in range(25):
        sx = int((i * 137.5) % w)
        sy = int((i * 219.3) % h)
        twinkle = int(180 + 75 * math.sin(t * 3.0 + i))
        draw.ellipse([(sx - 2, sy - 2), (sx + 2, sy + 2)], fill=(twinkle, twinkle, 255))

    # Placa superior
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(4, 6, 16))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(15, 23, 42), outline=(168, 85, 247), width=2)
    draw.text((px1 + 25, py1 + 16), "ASTRONOMÍA // ENIGMAS DEL ESPACIO PROFUNDO", fill=(192, 132, 252))
    draw.text((px1 + 25, py1 + 46), (title or "Enigma Cósmico")[:38].upper(), fill=(243, 232, 255))

    cx = w // 2
    cy = int(h * 0.50)

    # Anillos orbitales en perspectiva
    for r, col, lw in [(260, (147, 51, 234), 4), (200, (192, 132, 252), 6), (140, (232, 121, 249), 4)]:
        draw.arc([(cx - r, cy - r // 2), (cx + r, cy + r // 2)], start=0, end=360, fill=(255, 255, 255), width=lw + 4)
        draw.arc([(cx - r, cy - r // 2), (cx + r, cy + r // 2)], start=0, end=360, fill=col, width=lw)

    # Cuerpo celeste central con sombra y borde blanco
    pulse = math.sin(t * 2.5) * 6
    draw.ellipse([(cx - 100 - 6, cy - 100 - 6), (cx + 100 + 6, cy + 100 + 6)], fill=(255, 255, 255))
    draw.ellipse([(cx - 96, cy - 96), (cx + 96, cy + 96)], fill=(88, 28, 135))
    draw.ellipse([(cx - 70 + pulse, cy - 70 + pulse), (cx + 70 + pulse, cy + 70 + pulse)], fill=(126, 34, 206))

    # Cota técnica
    draw.rectangle([(cx - 120, cy + 180), (cx + 120, cy + 225)], fill=(255, 255, 255))
    draw.rectangle([(cx - 117, cy + 183), (cx + 117, cy + 222)], fill=(15, 23, 42))
    draw.text((cx - 100, cy + 194), "RETÍCULA: ENIGMA CÓSMICO", fill=(216, 180, 254))


def draw_architectural_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza diorama de monumentos arquitectónicos históricos."""
    # Fondo plano arquitectónico cálido
    draw.rectangle([(0, 0), (w, h)], fill=(248, 245, 235))
    grid_col = (230, 220, 205)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)

    # Placa superior
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(195, 185, 170))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(255, 253, 248), outline=(67, 56, 202), width=2)
    draw.text((px1 + 25, py1 + 16), "ARQUITECTURA // MONUMENTOS HISTÓRICOS", fill=(67, 56, 202))
    draw.text((px1 + 25, py1 + 46), (title or "Monumento Histórico")[:38].upper(), fill=(15, 23, 42))

    cx = w // 2
    cy = int(h * 0.52)

    # Pedestal base
    draw.rectangle([(cx - int(w * 0.42) - 4, cy + 120 - 4), (cx + int(w * 0.42) + 4, cy + 180 + 4)], fill=(255, 255, 255))
    draw.rectangle([(cx - int(w * 0.42), cy + 120), (cx + int(w * 0.42), cy + 180)], fill=(203, 213, 225))

    # Columnata monumental (6 columnas)
    num_cols = 6
    col_w = 32
    span = int(w * 0.72)
    start_x = cx - span // 2
    for i in range(num_cols):
        col_x = start_x + int(i * (span - col_w) / (num_cols - 1))
        draw.rectangle([(col_x - 3, cy - 90 - 3), (col_x + col_w + 3, cy + 120 + 3)], fill=(255, 255, 255))
        draw.rectangle([(col_x, cy - 90), (col_x + col_w, cy + 120)], fill=(241, 245, 249), outline=(148, 163, 184), width=2)

    # Entablamento y frontón triangular superior
    draw.rectangle([(cx - int(w * 0.40) - 4, cy - 130 - 4), (cx + int(w * 0.40) + 4, cy - 90 + 4)], fill=(255, 255, 255))
    draw.rectangle([(cx - int(w * 0.40), cy - 130), (cx + int(w * 0.40), cy - 90)], fill=(226, 232, 240))
    # Frontón
    draw.polygon([(cx - int(w * 0.40) - 4, cy - 130), (cx, cy - 220 - 4), (cx + int(w * 0.40) + 4, cy - 130)], fill=(255, 255, 255))
    draw.polygon([(cx - int(w * 0.40), cy - 130), (cx, cy - 220), (cx + int(w * 0.40), cy - 130)], fill=(203, 213, 225))

    # Cota técnica
    draw.rectangle([(cx - 120, cy + 200), (cx + 120, cy + 245)], fill=(255, 255, 255))
    draw.rectangle([(cx - 117, cy + 203), (cx + 117, cy + 242)], fill=(15, 23, 42))
    draw.text((cx - 100, cy + 214), "ESTRUCTURA PATRIMONIAL", fill=(129, 140, 248))


def draw_mystery_archive_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza diorama de expediente clasificado, crímenes, conspiraciones y misterios."""
    # Fondo pergamino / archivo militar
    draw.rectangle([(0, 0), (w, h)], fill=(246, 241, 230))
    grid_col = (230, 220, 205)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)

    # Placa superior
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(190, 180, 165))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(255, 253, 248), outline=(220, 38, 38), width=2)
    draw.text((px1 + 25, py1 + 16), "EXPEDIENTE INVESTIGADO // CLASIFICADO", fill=(220, 38, 38))
    draw.text((px1 + 25, py1 + 46), (title or "Caso Sin Resolver")[:38].upper(), fill=(15, 23, 42))

    cx = w // 2
    cy = int(h * 0.52)

    # Carpeta de expediente inclinada con borde blanco
    rot_angle = math.sin(t * 1.5) * 2.0
    f_w, f_h = int(w * 0.68), 280
    fx1, fy1 = cx - f_w // 2, cy - f_h // 2
    draw.rectangle([(fx1 - 6, fy1 - 6), (fx1 + f_w + 6, fy1 + f_h + 6)], fill=(255, 255, 255))
    draw.rectangle([(fx1, fy1), (fx1 + f_w, fy1 + f_h)], fill=(217, 119, 6), outline=(180, 83, 9), width=3)

    # Sello CONFIDENCIAL en rojo
    draw.rectangle([(cx - 130, cy - 40), (cx + 130, cy + 20)], fill=(255, 255, 255))
    draw.rectangle([(cx - 126, cy - 36), (cx + 126, cy + 16)], fill=(220, 38, 38))
    draw.text((cx - 100, cy - 20), "CONFIDENCIAL // CLASIFICADO", fill=(255, 255, 255))

    # Lupa de investigación / Disco criptográfico giratorio
    dial_r = 85
    dial_angle = t * 1.8
    dx = cx + int(math.cos(dial_angle) * 30)
    dy = cy + 90
    draw.ellipse([(dx - dial_r - 4, dy - dial_r - 4), (dx + dial_r + 4, dy + dial_r + 4)], fill=(255, 255, 255))
    draw.ellipse([(dx - dial_r, dy - dial_r), (dx + dial_r, dy + dial_r)], fill=(241, 245, 249), outline=(100, 116, 139), width=3)
    draw.line([(dx, dy - dial_r + 5), (dx, dy + dial_r - 5)], fill=(220, 38, 38), width=3)
    draw.line([(dx - dial_r + 5, dy), (dx + dial_r - 5, dy)], fill=(220, 38, 38), width=3)

    # Cota técnica
    draw.rectangle([(cx - 120, cy + 215), (cx + 120, cy + 260)], fill=(255, 255, 255))
    draw.rectangle([(cx - 117, cy + 218), (cx + 117, cy + 257)], fill=(15, 23, 42))
    draw.text((cx - 100, cy + 228), "ESTADO: EN INVESTIGACIÓN", fill=(239, 68, 68))


def draw_paper_cutout_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza diorama procedural paper-cut adaptado automáticamente a CUALQUIER temática."""
    archetype = detect_diorama_archetype(title)
    if archetype == "ojo_sahara":
        draw_ojo_sahara_diorama(draw, w, h, t, duration, title)
    elif archetype == "chapultepec":
        draw_chapultepec_diorama(draw, w, h, t, duration, title)
    elif archetype == "mayan":
        draw_mayan_diorama(draw, w, h, t, duration, title)
    elif archetype == "oceanic":
        draw_oceanic_diorama(draw, w, h, t, duration, title)
    elif archetype == "geological":
        draw_geological_diorama(draw, w, h, t, duration, title)
    elif archetype == "cosmic":
        draw_cosmic_diorama(draw, w, h, t, duration, title)
    elif archetype == "architectural":
        draw_architectural_diorama(draw, w, h, t, duration, title)
    else:
        draw_mystery_archive_diorama(draw, w, h, t, duration, title)


def draw_mayan_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza el diorama de arqueología maya con pirámide escalonada y selva."""
    bg_jungle = (8, 28, 21)
    draw.rectangle([(0, 0), (w, h)], fill=bg_jungle)

    # Placa superior
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(4, 15, 11))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(16, 44, 34), outline=(52, 211, 153), width=2)
    draw.text((px1 + 25, py1 + 16), "ARQUEOLOGÍA PREHISPÁNICA // LIDAR EN CAMPECHE", fill=(52, 211, 153))
    draw.text((px1 + 25, py1 + 46), (title or "Ciudad Maya")[:38].upper(), fill=(241, 245, 249))

    cx = w // 2
    cy = int(h * 0.58)

    # Selva base
    draw.ellipse([(cx - int(w * 0.46), cy + 40), (cx + int(w * 0.46), cy + 220)], fill=(27, 67, 50), outline=(255, 255, 255), width=3)

    # Pirámide escalonada en 5 niveles
    steps = [
        (220, 40, cy - 20),
        (180, 36, cy - 56),
        (140, 32, cy - 88),
        (100, 28, cy - 116),
        (60, 24, cy - 140),
    ]
    for sw, sh, sy in steps:
        draw.rectangle([(cx - sw, sy), (cx + sw, sy + sh)], fill=(203, 213, 225), outline=(255, 255, 255), width=2)
        # Escalinata central
        draw.rectangle([(cx - 20, sy), (cx + 20, sy + sh)], fill=(148, 163, 184))

    # Templo superior
    draw.rectangle([(cx - 30, cy - 180), (cx + 30, cy - 140)], fill=(241, 245, 249), outline=(52, 211, 153), width=3)

    # Escaneo LiDAR dinámico
    laser_y = int((cy - 200) + ((t * 0.8) % 1.0) * 320)
    draw.line([(cx - 240, laser_y), (cx + 240, laser_y)], fill=(52, 211, 153), width=3)

    # Glifos de jade flotantes
    glyph_y = cy - 220 + int(math.sin(t * 3.0) * 8)
    draw.rounded_rectangle([(cx - 90, glyph_y), (cx + 90, glyph_y + 36)], radius=10, fill=(6, 78, 59), outline=(52, 211, 153), width=2)
    draw.text((cx - 70, glyph_y + 10), "VALERIANA • 6,674 ESTRUCTURAS", fill=(209, 250, 229))


def draw_ojo_sahara_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza el diorama geológico de papel recortado del Ojo del Sahara (Estructura de Richat)."""
    # 1. Fondo de arena del desierto con cuadrícula topográfica
    bg_sand = (248, 241, 227)
    grid_color = (230, 215, 190)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_color, width=1)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_color, width=1)

    # 2. Placa superior estilo paper-cut con borde blanco y sombra
    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 5, py1 + 5), (px2 + 5, py2 + 5)], radius=18, fill=(205, 190, 165))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(255, 253, 248), outline=(180, 130, 80), width=2)
    draw.text((px1 + 25, py1 + 16), "GEOLOGÍA // ESTRUCTURA DE RICHAT (MAURITANIA)", fill=(180, 83, 9))
    draw.text((px1 + 25, py1 + 46), (title or "El Ojo del Sahara")[:38].upper(), fill=(15, 23, 42))

    cx = w // 2
    cy = int(h * 0.48)

    # 3. Dunas del desierto en capas de papel recortado con sombras
    dune_layers = [
        (int(h * 0.76), (217, 119, 6), (180, 83, 9)),
        (int(h * 0.70), (245, 158, 11), (217, 119, 6)),
        (int(h * 0.64), (251, 191, 36), (245, 158, 11)),
    ]
    for dy, d_fill, d_border in dune_layers:
        wave = math.sin(t * 1.5 + dy * 0.01) * 8
        draw.ellipse([(cx - int(w * 0.65), dy + int(wave)), (cx + int(w * 0.65), dy + 280 + int(wave))], fill=d_fill, outline=d_border, width=3)

    # 4. Anillos concéntricos del Ojo del Sahara (Estructura de Richat - 40 km)
    # Perspectiva elíptica 2.5D
    rings = [
        (260, 140, (146, 64, 14), "Cinturón de cuarcita exterior"),
        (210, 112, (180, 83, 9), "Brecha hidrotermal"),
        (160, 84, (217, 119, 6), "Estrato de dolomía"),
        (110, 58, (14, 116, 144), "Depresión de basalto"),
        (65, 34, (2, 132, 199), "Núcleo intrusivo central"),
    ]
    pulse = 1.0 + 0.02 * math.sin(t * 3.0)

    # Sombra de la estructura completa
    draw.ellipse([(cx - int(270 * pulse) + 8, cy - int(148 * pulse) + 8), (cx + int(270 * pulse) + 8, cy + int(148 * pulse) + 8)], fill=(195, 175, 150))
    # Borde exterior blanco de sticker
    draw.ellipse([(cx - int(274 * pulse), cy - int(152 * pulse)), (cx + int(274 * pulse), cy + int(152 * pulse))], fill=(255, 255, 255))

    for rx, ry, r_color, _ in rings:
        r_x = int(rx * pulse)
        r_y = int(ry * pulse)
        draw.ellipse([(cx - r_x, cy - r_y), (cx + r_x, cy + r_y)], fill=r_color, outline=(255, 255, 255), width=3)

    # Centro de la estructura (domo)
    draw.ellipse([(cx - 24, cy - 14), (cx + 24, cy + 14)], fill=(255, 255, 255))
    draw.ellipse([(cx - 18, cy - 10), (cx + 18, cy + 10)], fill=(3, 105, 161))

    # 5. Cota de medición satelital (Ø 40 km)
    cota_y = cy + int(170 * pulse)
    draw.line([(cx - 220, cota_y), (cx + 220, cota_y)], fill=(15, 23, 42), width=2)
    draw.line([(cx - 220, cota_y - 10), (cx - 220, cota_y + 10)], fill=(15, 23, 42), width=2)
    draw.line([(cx + 220, cota_y - 10), (cx + 220, cota_y + 10)], fill=(15, 23, 42), width=2)
    draw.text((cx - 80, cota_y - 30), "DIÁMETRO: Ø 40 KM", fill=(15, 23, 42))

    # 6. Escaneo orbital dinámico
    scan_angle = t * 1.8
    scan_x = cx + int(math.cos(scan_angle) * 230)
    scan_y = cy + int(math.sin(scan_angle) * 120)
    draw.line([(cx, cy), (scan_x, scan_y)], fill=(2, 132, 199), width=2)
    draw.ellipse([(scan_x - 6, scan_y - 6), (scan_x + 6, scan_y + 6)], fill=(255, 255, 255), outline=(2, 132, 199), width=2)

    # 7. Badge de coordenadas geográficas
    bx1, by1 = cx - 180, int(h * 0.72)
    bx2, by2 = cx + 180, by1 + 52
    draw.rounded_rectangle([(bx1 + 3, by1 + 3), (bx2 + 3, by2 + 3)], radius=12, fill=(200, 185, 160))
    draw.rounded_rectangle([(bx1 - 2, by1 - 2), (bx2 + 2, by2 + 2)], radius=14, fill=(255, 255, 255))
    draw.rounded_rectangle([(bx1, by1), (bx2, by2)], radius=12, fill=(255, 253, 248), outline=(217, 119, 6), width=2)
    draw.text((bx1 + 20, by1 + 16), "COORD: 21°07' N · 11°24' W", fill=(180, 83, 9))


def draw_chapultepec_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str):
    """Renderiza el diorama multicapa de papel recortado del Castillo de Chapultepec."""
    bg_warm = (251, 245, 232)
    grid_color = (235, 222, 198)
    for y in range(0, h, 60): draw.line([(0, y), (w, y)], fill=grid_color, width=1)
    for x in range(0, w, 60): draw.line([(x, 0), (x, h)], fill=grid_color, width=1)

    px1, py1 = 60, 60
    px2, py2 = w - 60, 155
    draw.rounded_rectangle([(px1 + 4, py1 + 4), (px2 + 4, py2 + 4)], radius=18, fill=(200, 190, 175))
    draw.rounded_rectangle([(px1 - 3, py1 - 3), (px2 + 3, py2 + 3)], radius=21, fill=(255, 255, 255))
    draw.rounded_rectangle([(px1, py1), (px2, py2)], radius=18, fill=(255, 253, 248), outline=(180, 130, 80), width=2)
    draw.text((px1 + 25, py1 + 16), "HISTORIA DE MÉXICO // ALCÁZAR REAL", fill=(180, 83, 9))
    draw.text((px1 + 25, py1 + 46), (title or "Castillo de Chapultepec")[:38].upper(), fill=(15, 23, 42))

    cx = w // 2
    cy = int(h * 0.58)

    # Cerro verde del Chapulín
    draw.ellipse([(cx - int(w * 0.45) + 6, cy - 20 + 6), (cx + int(w * 0.45) + 6, cy + 180 + 6)], fill=(190, 180, 160))
    draw.ellipse([(cx - int(w * 0.45) - 3, cy - 20 - 3), (cx + int(w * 0.45) + 3, cy + 180 + 3)], fill=(255, 255, 255))
    draw.ellipse([(cx - int(w * 0.45), cy - 20), (cx + int(w * 0.45), cy + 180)], fill=(22, 163, 74), outline=(21, 128, 61), width=4)

    # Edificio del Castillo de Chapultepec
    draw.rounded_rectangle([(cx - 160, cy - 140), (cx + 160, cy - 20)], radius=12, fill=(255, 255, 255), outline=(203, 213, 225), width=3)
    draw.rounded_rectangle([(cx - 150, cy - 130), (cx + 150, cy - 30)], radius=8, fill=(248, 250, 252))

    # Arcadas neoclásicas
    for arch_x in range(cx - 130, cx + 130, 40):
        draw.rounded_rectangle([(arch_x, cy - 110), (arch_x + 24, cy - 40)], radius=6, fill=(30, 41, 59))
        draw.ellipse([(arch_x + 6, cy - 100), (arch_x + 18, cy - 80)], fill=(245, 158, 11))

    # Torreón central y reloj
    draw.rectangle([(cx - 40, cy - 200), (cx + 40, cy - 140)], fill=(255, 255, 255), outline=(203, 213, 225), width=3)
    draw.ellipse([(cx - 16, cy - 180), (cx + 16, cy - 148)], fill=(248, 250, 252), outline=(180, 83, 9), width=2)
    # Manecillas
    draw.line([(cx, cy - 164), (cx, cy - 174)], fill=(15, 23, 42), width=2)
    draw.line([(cx, cy - 164), (cx + 8, cy - 164)], fill=(15, 23, 42), width=2)

    # Asta y bandera de México
    wave = int(math.sin(t * 6.0) * 4)
    draw.line([(cx, cy - 200), (cx, cy - 260)], fill=(100, 116, 139), width=4)
    draw.rectangle([(cx + 2, cy - 260 + wave), (cx + 22, cy - 225 + wave)], fill=(22, 163, 74))
    draw.rectangle([(cx + 22, cy - 260 + wave), (cx + 42, cy - 225 + wave)], fill=(255, 255, 255))
    draw.rectangle([(cx + 42, cy - 260 + wave), (cx + 62, cy - 225 + wave)], fill=(220, 38, 38))

    # Cota de altitud
    draw.text((cx - 90, cy + 90), "ALTITUD: 2,325 m s.n.m.", fill=(255, 255, 255))


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

    # Detección inteligente de temática para garantizar correspondencia visual 1:1
    if any(k in low_text for k in ("sahara", "richat", "mauritania", "desierto", "crater")):
        style_id = "ojo_sahara_diorama"
        draw_fn = draw_ojo_sahara_diorama
    elif any(k in low_text for k in ("chapultepec", "castillo", "alcazar", "maximiliano", "carlota")):
        style_id = "chapultepec_diorama"
        draw_fn = draw_chapultepec_diorama
    elif any(k in low_text for k in ("maya", "campeche", "valeriana", "lidar", "piramide", "sakil")):
        style_id = "mayan_diorama"
        draw_fn = draw_mayan_diorama
    elif style_id == "ojo_sahara_diorama":
        draw_fn = draw_ojo_sahara_diorama
    elif style_id == "chapultepec_diorama":
        draw_fn = draw_chapultepec_diorama
    elif style_id == "mayan_diorama":
        draw_fn = draw_mayan_diorama
    elif style_id == "blueprint_cad" and not any(k in low_text for k in ["turbo", "compresor", "motor", "cilindro", "rpm", "boost", "mecanic"]):
        style_id = "paper_cutout_diorama"
        draw_fn = draw_paper_cutout_diorama
    elif style_id == "blueprint_cad":
        draw_fn = draw_blueprint_cad
    elif style_id == "vector_flow":
        draw_fn = draw_vector_flow
    elif style_id == "da_vinci_codex":
        draw_fn = draw_da_vinci_codex
    elif style_id == "hud_telemetry":
        draw_fn = draw_hud_telemetry
    elif style_id == "anime_speedlines":
        draw_fn = draw_anime_speedlines
    else:
        draw_fn = draw_paper_cutout_diorama

    # Estilo de paleta
    pal = (style_data or {}).get("palette", {})
    bg_hex = pal.get("background", "#fbf5e8")
    if style_id in ("paper_cutout_diorama", "chapultepec_diorama", "mayan_diorama", "ojo_sahara_diorama"):
        bg_hex = "#fbf5e8"
    h_c = bg_hex.lstrip("#")
    bg_rgb = tuple(int(h_c[i:i+2], 16) for i in (0, 2, 4)) if len(h_c) == 6 else (251, 245, 232)

    # 3. Renderizar cada cuadro como función pura del tiempo t
    for f in range(total_frames):
        t = f / fps
        im = Image.new("RGB", (width, height), bg_rgb)
        draw = ImageDraw.Draw(im)
        draw.font = _load_font(max(14, width // 40))
        draw_fn(draw, width, height, t, dur_sec, title)

        frame_path = frames_dir / f"frame_{f:05d}.png"
        im.save(str(frame_path))

    # 4. Crear archivo de subtítulos ASS dinámicos sincronizados progresivamente
    words = [w.strip() for w in narration.split() if w.strip()]
    dialogues = []
    if words:
        chunk_size = 5  # 4-6 palabras por línea para 9:16 vertical
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
Title: Lemo-Opuscar Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,44,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H90000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,2,40,40,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"
    subtitles_ass.write_text(sub_content, encoding="utf-8")

    # Guardar metadatos para la API / UI
    meta_path = output_dir / "meta.json"
    try:
        import json
        meta_path.write_text(
            json.dumps({
                "duration": dur_sec,
                "fps": fps,
                "style_id": style_id,
                "title": title,
                "narration": narration,
                "voice": voice,
            }, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

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
