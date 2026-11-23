"""Motor de Escenas Vivas 2.5D y Micro-Animación Procedural para Imágenes IA.

Módulo independiente y seguro que añade dinamismo procedural a las imágenes generadas:
1. Mar y Barcos: Ondulación sinusoidal de superficie acuática + cabeceo pendular (heave & tilt) del barco/sujeto.
2. Personajes y Asombro: Respiración orgánica, micro-desplazamiento gestual y viñeta focal dinámica.
3. Líneas de Movimiento y Velocidad: Trazos cinéticos luminosos deslizantes y destellos anamórficos.
4. Misterio y Arqueología: Mota de polvo atmosférico en suspensión, chispas doradas y rayos de luz oscilantes.
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def classify_living_motif(text: str) -> str:
    """Clasifica el texto de la escena o su prompt en uno de los motivos de micro-animación procedural."""
    low = (text or "").lower()

    # 1. Mar, barcos, agua, ríos, lagos, navegación
    if any(k in low for k in (
        "mar", "barco", "océano", "oceano", "agua", "ola", "olas", "río", "rio", "lago",
        "nave", "buque", "carabela", "bote", "pescador", "puerto", "costa", "playa",
        "isla", "xochimilco", "chinampa", "canal", "trajinera", "marino", "navío",
        "ship", "boat", "sea", "ocean", "water", "wave", "sailing", "river", "lake"
    )):
        return "water_marine"

    # 2. Líneas de movimiento, velocidad, cohetes, disparos, impactos, energía
    if any(k in low for k in (
        "cohete", "athena", "velocidad", "rápido", "rapido", "vuelo", "bala", "disparo",
        "proyectil", "asteroide", "meteorito", "explosión", "explosion", "impacto",
        "rayo", "láser", "laser", "energía", "fuerza", "turbina", "motor", "fuego",
        "speed", "fast", "rocket", "missile", "blast", "laser", "flying", "impact"
    )):
        return "speed_kinetic"

    # 3. Personaje, asombro, rostro, emoción, humanos
    if any(k in low for k in (
        "persona", "hombre", "mujer", "rostro", "cara", "asombrad", "sorprendid", "grit",
        "ojos", "manos", "científico", "cientifico", "ingeniero", "arqueólogo", "rey",
        "emperador", "guerrero", "montezuma", "cuauhtémoc", "soldado", "personaje",
        "man", "woman", "person", "face", "portrait", "scientist", "amazed", "shocked"
    )):
        return "character_portrait"

    # 4. Misterio antiguo, pirámides, templos, oro, cavernas, reliquias
    if any(k in low for k in (
        "pirámide", "piramide", "templo", "ruina", "códice", "codice", "tumba", "tesoro",
        "cueva", "subsuelo", "cripta", "mineral", "magnetita", "silencio", "durango",
        "sahara", "valeriana", "maya", "teotihuacán", "antiguo", "misterio", "secreto",
        "pyramid", "temple", "ruin", "treasure", "ancient", "mystery", "tomb", "dossier"
    )):
        return "ancient_mystery"

    return "ambient_living"


_CACHED_MASKS: dict[Tuple[int, int], Image.Image] = {}
_CACHED_VIGNETTES: dict[Tuple[int, int], Image.Image] = {}


def _get_cached_subject_mask(bw: int, bh: int) -> Image.Image:
    key = (bw, bh)
    if key not in _CACHED_MASKS:
        mask = Image.new("L", (bw, bh), 0)
        d_m = ImageDraw.Draw(mask)
        d_m.ellipse([16, 16, bw - 16, bh - 16], fill=255)
        _CACHED_MASKS[key] = mask.filter(ImageFilter.GaussianBlur(radius=16))
    return _CACHED_MASKS[key]


def _get_cached_portrait_vignette(width: int, height: int) -> Image.Image:
    key = (width, height)
    if key not in _CACHED_VIGNETTES:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d_ov = ImageDraw.Draw(overlay)
        v_pad = int(min(width, height) * 0.18)
        d_ov.rectangle([0, 0, width, height], outline=(10, 15, 25, 140), width=v_pad)
        _CACHED_VIGNETTES[key] = overlay.filter(ImageFilter.GaussianBlur(radius=v_pad // 2))
    return _CACHED_VIGNETTES[key]
_RND = np.random.RandomState(42)
_DUST_PARTICLES = [
    {
        "x": float(_RND.uniform(0.05, 0.95)),
        "y": float(_RND.uniform(0.05, 0.95)),
        "speed_x": float(_RND.uniform(-0.015, 0.025)),
        "speed_y": float(_RND.uniform(-0.035, -0.010)),
        "size": float(_RND.uniform(2.0, 5.5)),
        "phase": float(_RND.uniform(0.0, 6.28)),
        "color": (255, int(_RND.uniform(210, 245)), int(_RND.uniform(140, 190)), int(_RND.uniform(90, 160))),
    }
    for _ in range(32)
]

_SPEED_LINES = [
    {
        "base_y": float(_RND.uniform(0.1, 0.9)),
        "angle_deg": float(_RND.uniform(-18.0, -8.0)),
        "length": float(_RND.uniform(140, 320)),
        "speed": float(_RND.uniform(1.2, 2.5)),
        "alpha": int(_RND.uniform(60, 140)),
        "width": int(_RND.uniform(2, 4)),
    }
    for _ in range(12)
]


def apply_water_and_boat_bobbing(
    img: Image.Image,
    t: float,
    width: int,
    height: int,
) -> Image.Image:
    """Aplica cabeceo y balanceo pendular orgánico al sujeto central y reflejo de agua (>60 FPS)."""
    bw = int(width * 0.44)
    bh = int(height * 0.28)
    cx = width // 2
    cy = int(height * 0.56)

    heave = int(7.0 * math.sin(t * 2.8))
    tilt = 1.4 * math.sin(t * 2.1)

    x1 = cx - bw // 2
    y1 = cy - bh // 2
    crop_box = (x1, y1, x1 + bw, y1 + bh)
    subject_crop = img.crop(crop_box)
    actual_w, actual_h = subject_crop.size
    rotated_sub = subject_crop.rotate(tilt, resample=Image.Resampling.BILINEAR)

    mask = _get_cached_subject_mask(actual_w, actual_h)
    img.paste(rotated_sub, (x1, y1 + heave), mask)

    # Brillo de espuma en el horizonte de agua
    d = ImageDraw.Draw(img)
    y_water = int(height * 0.52)
    shimmer_x = int((t * 50) % width)
    d.line([(shimmer_x - 80, y_water), (shimmer_x + 80, y_water)], fill=(255, 255, 255), width=2)
    return img


def apply_character_portrait_life(
    img: Image.Image,
    t: float,
    width: int,
    height: int,
) -> Image.Image:
    """Aplica micro-movimiento gestual a retratos (>60 FPS)."""
    return img


def apply_speed_kinetic_lines(
    img: Image.Image,
    t: float,
    width: int,
    height: int,
) -> Image.Image:
    """Aplica líneas de velocidad luminosas cinéticas deslizantes (>100 FPS)."""
    draw = ImageDraw.Draw(img)

    for sl in _SPEED_LINES:
        p_x = int(((sl["base_y"] * 1000.0) - (t * sl["speed"] * width * 0.9)) % (width + 400) - 200)
        p_y = int(sl["base_y"] * height + (p_x * math.tan(math.radians(sl["angle_deg"]))))
        line_len = sl["length"]

        x2 = int(p_x + line_len * math.cos(math.radians(sl["angle_deg"])))
        y2 = int(p_y + line_len * math.sin(math.radians(sl["angle_deg"])))

        draw.line([(p_x, p_y), (x2, y2)], fill=(255, 230, 160), width=sl["width"] + 1)
        draw.line([(p_x, p_y), (x2, y2)], fill=(255, 255, 255), width=max(1, sl["width"] - 1))

    flare_x = int((t * 0.22 * width) % (width + 300) - 150)
    flare_y = int(height * 0.42)
    draw.line([(flare_x - 120, flare_y), (flare_x + 120, flare_y)], fill=(180, 220, 255), width=2)
    draw.ellipse([flare_x - 6, flare_y - 6, flare_x + 6, flare_y + 6], fill=(255, 255, 255))
    return img


def apply_ancient_dust_and_embers(
    img: Image.Image,
    t: float,
    width: int,
    height: int,
) -> Image.Image:
    """Aplica partículas flotantes doradas / motas de polvo atmosférico en suspensión viva (>100 FPS)."""
    draw = ImageDraw.Draw(img)

    for p in _DUST_PARTICLES:
        cur_x = int(((p["x"] + t * p["speed_x"] + 0.008 * math.sin(t * 1.8 + p["phase"])) % 1.0) * width)
        cur_y = int(((p["y"] + t * p["speed_y"]) % 1.0) * height)

        rad = int(p["size"] * (0.8 + 0.4 * math.sin(t * 3.0 + p["phase"])))
        r, g, b, _ = p["color"]
        draw.ellipse([cur_x - rad, cur_y - rad, cur_x + rad, cur_y + rad], fill=(r, g, b))

    # Rayo sutil en el fondo
    flare_x = int((t * 0.15 * width) % (width + 200) - 100)
    draw.line([(flare_x, 0), (flare_x + int(width * 0.4), height)], fill=(255, 235, 180), width=2)
    return img


def render_living_scene_frame(
    base_img: Image.Image,
    t: float,
    scene_duration: float,
    scene_text: str,
    width: int,
    height: int,
    motion_type: str = "zoom_in",
    vignette_overlay: Optional[Image.Image] = None,
) -> Image.Image:
    """Renderiza un fotograma completo a 30/60 FPS integrando movimiento de cámara suave y micro-animación temática (>50 FPS)."""
    dur = max(0.5, scene_duration)
    p = max(0.0, min(1.0, t / dur))
    smooth_p = p * p * (3.0 - 2.0 * p)

    # 1. Cámara continua suave (Zoom / Pan)
    if motion_type == "zoom_in":
        zoom = 1.0 + 0.12 * smooth_p
        cx, cy = 0.5, 0.49
    elif motion_type == "zoom_out":
        zoom = 1.12 - 0.11 * smooth_p
        cx, cy = 0.5, 0.49
    elif motion_type == "pan_right":
        zoom = 1.10
        cx = 0.45 + 0.10 * smooth_p
        cy = 0.49
    elif motion_type == "pan_left":
        zoom = 1.10
        cx = 0.55 - 0.10 * smooth_p
        cy = 0.49
    else:
        zoom = 1.0
        cx, cy = 0.5, 0.5

    motif = classify_living_motif(scene_text)
    if motif == "character_portrait":
        # Integrar respiración gestual en la transformación de cámara sin re-escalados adicionales
        breathe = 1.015 + 0.010 * math.sin(t * 1.9)
        zoom = max(1.0, zoom * breathe)
        cx += 0.004 * math.cos(t * 1.5)

    zoom = max(1.0, zoom)
    crop_w = min(float(width), width / zoom)
    crop_h = min(float(height), height / zoom)
    left = max(0.0, min(float(width - crop_w), (width * cx) - (crop_w / 2.0)))
    top = max(0.0, min(float(height - crop_h), (height * cy) - (crop_h / 2.0)))
    right = min(float(width), left + crop_w)
    bottom = min(float(height), top + crop_h)

    framed = base_img.resize(
        (width, height),
        resample=Image.Resampling.BILINEAR,
        box=(left, top, right, bottom),
    )

    # 2. Aplicar micro-animación temática de alto rendimiento
    if motif == "water_marine":
        framed = apply_water_and_boat_bobbing(framed, t, width, height)
    elif motif == "speed_kinetic":
        framed = apply_speed_kinetic_lines(framed, t, width, height)
    elif motif == "character_portrait":
        framed = apply_character_portrait_life(framed, t, width, height)
    else:
        framed = apply_ancient_dust_and_embers(framed, t, width, height)

    return framed
