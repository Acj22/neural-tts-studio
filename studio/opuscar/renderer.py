"""AI VIDEO STUDIO — Motor de Renderizado Procedural Multi-Escena 2.5D Lemo-Opuscar.
Genera fotograma a fotograma animaciones Paper-Cut Diorama de 8 a 9 escenas dinámicas
en función del tiempo t y del guion real, sincroniza con locución neuronal (Edge TTS),
diseño sonoro foley + música documental y compila a MP4 con FFmpeg.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("studio.opuscar.renderer")

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.opuscar.styles_catalog import get_opuscar_style_by_id


def _get_ffmpeg() -> str:
    from studio.blender.service import _get_ffmpeg as blender_get_ffmpeg
    return blender_get_ffmpeg()


_FONT_CACHE: dict[tuple[int, bool], Any] = {}


def _load_font(size: int, bold: bool = True):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = (
        ("arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "arial.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf")
    )
    for name in candidates:
        try:
            f = ImageFont.truetype(name, size)
            _FONT_CACHE[key] = f
            return f
        except Exception:
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _clamp(val: float, mn: float, mx: float) -> float:
    return max(mn, min(mx, val))


def _ease_out_back(t: float, s: float = 1.45) -> float:
    p = _clamp(t, 0.0, 1.0)
    return 1.0 + (s + 1.0) * ((p - 1.0) ** 3) + s * ((p - 1.0) ** 2)


def _ease_out_cubic(t: float) -> float:
    p = _clamp(t, 0.0, 1.0)
    return 1.0 - ((1.0 - p) ** 3)


async def synthesize_opuscar_audio(
    text: str,
    output_path: Path,
    voice: str = "es-MX-DaliaNeural",
    rate: str = "+0%",
) -> float:
    """Sintetiza la narración con Edge TTS, mezcla ambiente documental sutil y devuelve la duración exacta."""
    edge_voice = voice if "Neural" in (voice or "") else "es-MX-DaliaNeural"
    raw_mp3 = output_path.parent / "_raw_voice.mp3"
    try:
        import edge_tts
        comm = edge_tts.Communicate(text=text, voice=edge_voice, rate=rate)
        await comm.save(str(raw_mp3.resolve()))
    except Exception:
        try:
            import edge_tts
            comm = edge_tts.Communicate(text=text, voice="es-MX-JorgeNeural", rate=rate)
            await comm.save(str(raw_mp3.resolve()))
        except Exception:
            ffmpeg_bin = _get_ffmpeg()
            dur = max(65.0, len(text.split()) * 0.42)
            cmd = [
                ffmpeg_bin, "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=mono",
                "-t", str(dur),
                "-c:a", "libmp3lame",
                str(raw_mp3.resolve()),
            ]
            subprocess.run(cmd, check=True, capture_output=True)

    # Medir duración y mezclar música ambiental documental + foley sutil
    ffmpeg_bin = _get_ffmpeg()
    try:
        import soundfile as sf
        cmd_wav = [ffmpeg_bin, "-y", "-i", str(raw_mp3.resolve()), "-f", "wav", "-ar", "44100", "-ac", "1", "-"]
        proc = subprocess.run(cmd_wav, capture_output=True, check=True)
        vox, sr = sf.read(io.BytesIO(proc.stdout), dtype="float32")
        n_samples = len(vox)
        dur_sec = n_samples / float(sr)

        # Generar colchón armónico documental suave
        bgm = np.zeros(n_samples, dtype=np.float32)
        chords = [
            [220.0, 261.63, 329.63],  # A min
            [174.61, 220.0, 261.63],  # F maj
            [146.83, 174.61, 220.0],  # D min
            [164.81, 207.65, 246.94], # E maj
        ]
        bar_dur = 2.8
        n_bars = int(dur_sec / bar_dur) + 1
        for b in range(n_bars):
            chord = chords[b % len(chords)]
            b_start = int(b * bar_dur * sr)
            t_bar = np.linspace(0, bar_dur, int(sr * bar_dur), endpoint=False)
            wave = np.zeros_like(t_bar)
            for freq in chord:
                wave += np.sin(2 * np.pi * freq * t_bar) * 0.10
                wave += np.sin(2 * np.pi * freq * 2.0 * t_bar) * 0.03
            env = np.sin(np.pi * t_bar / bar_dur) ** 0.8
            wave *= env
            b_end = min(n_samples, b_start + len(wave))
            if b_end > b_start:
                bgm[b_start:b_end] += wave[:b_end - b_start]

        mixed = vox * 1.15 + bgm * 0.075
        try:
            from studio.audio_mastering import apply_studio_mastering
            mixed = apply_studio_mastering(mixed, sample_rate=sr)
        except Exception:
            peak = float(np.max(np.abs(mixed))) if len(mixed) else 1.0
            if peak > 0.98:
                mixed = (mixed / peak) * 0.96

        wav_tmp = output_path.parent / "_master_mix.wav"
        sf.write(str(wav_tmp), mixed.astype(np.float32), sr, format="WAV", subtype="PCM_16")
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(wav_tmp.resolve()), "-c:a", "libmp3lame", "-b:a", "192k", str(output_path.resolve())],
            check=True,
            capture_output=True,
        )
        wav_tmp.unlink(missing_ok=True)
        raw_mp3.unlink(missing_ok=True)
        return dur_sec
    except Exception:
        if raw_mp3.exists():
            shutil.move(str(raw_mp3), str(output_path))

    cmd = [ffmpeg_bin, "-i", str(output_path.resolve()), "-f", "null", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if m:
        h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return h * 3600 + mn * 60 + s
    return 65.0


# ==============================================================================
# MOTOR UNIVERSAL DE ESCENAS PAPER-CUT 2.5D (8-9 ESCENAS DINÁMICAS POR VIDEO)
# ==============================================================================

SCENE_TYPES_SEQUENCE = [
    "panorama_geografico",
    "mapa_cartografico",
    "suceso_impacto",
    "instrumentos_anomalia",
    "corte_estratos",
    "cronica_expediente",
    "mito_vs_ciencia",
    "cierre_medalla",
]


def _extract_badge_from_text(text: str, scene_idx: int, title: str) -> tuple[str, str]:
    """Extrae el año histórico, cifra, coordenada o institución clave de la oración para el Badge 2.5D."""
    # 1. Buscar año de 4 dígitos (1400 - 2035)
    m_year = re.search(r"\b(1[4-9]\d{2}|20[0-3]\d)\b", text)
    if m_year:
        yr = m_year.group(1)
        return yr, "AÑO DOCUMENTADO"

    # 2. Buscar medida o cifra con unidad
    m_metric = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(km|metros|m\b|toneladas|años|grados|paralelo|niveles)", text, re.IGNORECASE)
    if m_metric:
        val = m_metric.group(1)
        unit = m_metric.group(2).upper()
        return f"{val} {unit[:3]}", "MEDICIÓN REAL"

    # 3. Buscar siglas o instituciones reales
    for inst, lbl in (
        ("PEMEX", "PROSPECCIÓN"),
        ("NASA", "AGENCIA ESPACIAL"),
        ("UNAM", "INVESTIGACIÓN"),
        ("INAH", "ARQUEOLOGÍA"),
        ("INECOL", "RESERVA BIOSFERA"),
        ("LIDAR", "ESCANEO LÁSER"),
        ("ATHENA", "PROYECTIL V-123"),
        ("ALLENDE", "CONDRO METEORITO"),
        ("MAPIMÍ", "PARALELO 27° N"),
    ):
        if inst.lower() in text.lower() or inst.lower() in title.lower():
            return inst, lbl

    defaults = [
        ("27° N", "LATITUD CRÍTICA"),
        ("ACT 02", "CARTOGRAFÍA"),
        ("1970", "REGISTRO OFICIAL"),
        ("MAG-01", "TELEMETRÍA"),
        ("ESTRATO", "SUBSUELO"),
        ("ARCHIVO", "FUENTE PRIMARIA"),
        ("CIENCIA", "VERIFICACIÓN"),
        ("DEBATE", "CONCLUSIÓN"),
    ]
    return defaults[scene_idx % len(defaults)]


def _classify_scene_type(scene_text: str, scene_idx: int, total_scenes: int) -> str:
    """Selecciona la composición visual 2.5D para cada escena sin repetir dos escenas seguidas iguales."""
    if scene_idx == 0:
        return "panorama_geografico"
    if scene_idx == total_scenes - 1:
        return "cierre_medalla"

    low = scene_text.lower()
    if any(k in low for k in ("cohete", "athena", "meteorito", "allende", "estrelló", "colisionó", "cayó", "impacto", "proyectil", "lanzado", "explosión", "cobalto")):
        return "suceso_impacto"
    if any(k in low for k in ("radio", "brújula", "magnétic", "señal", "onda", "giroscopio", "transmisión", "frecuencia", "instrumento")):
        return "instrumentos_anomalia"
    if any(k in low for k in ("subsuelo", "magnetita", "hierro", "mineral", "estrato", "túnel", "bajo tierra", "cueva", "cristal", "mercurio", "excavación", "arena")):
        return "corte_estratos"
    if any(k in low for k in ("mito", "leyenda", "ufólogo", "folclore", "teoría", "ciencia", "explicación", "contraste", "realidad")):
        return "mito_vs_ciencia"
    if any(k in low for k in ("mapa", "ubicad", "paralelo", "frontera", "kilómetros", "desierto", "vértice", "coordenada", "región", "ruta")):
        return "mapa_cartografico"
    if any(k in low for k in ("ingeniero", "investigador", "arqueólogo", "equipo", "informe", "archivo", "crónica", "documento", "registro", "von braun", "peña")):
        return "cronica_expediente"

    return SCENE_TYPES_SEQUENCE[scene_idx % len(SCENE_TYPES_SEQUENCE)]


def parse_narration_into_diorama_scenes(narration: str, total_duration: float, title: str) -> list[dict[str, Any]]:
    """Divide cualquier guion en escenas dinámicas de 4.5 a 7.5 segundos (12 a 22 escenas) con 16 arquetipos temáticos sin repetición."""
    try:
        from studio.opuscar.scene_archetypes import split_into_dynamic_scenes
        return split_into_dynamic_scenes(narration, total_duration, title)
    except Exception as e_split:
        logger.warning(f"Fallback en split_into_dynamic_scenes: {e_split}")

    raw_paras = [p.strip() for p in re.split(r"\n\s*\n", (narration or "").strip()) if p.strip()]
    if len(raw_paras) < 6:
        # Dividir por oraciones para garantizar entre 7 y 9 cambios de escena dinámicos
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (narration or "").strip()) if s.strip()]
        if len(sents) >= 6:
            raw_paras = sents
        elif not raw_paras:
            raw_paras = [title or "Investigación Documental"]

    total_words = sum(max(1, len(p.split())) for p in raw_paras)
    scenes: list[dict[str, Any]] = []
    cur_t = 0.0
    used_types: list[str] = []

    for idx, p_text in enumerate(raw_paras):
        w_count = max(1, len(p_text.split()))
        dur = (w_count / float(total_words)) * total_duration if idx < len(raw_paras) - 1 else max(0.5, total_duration - cur_t)
        s_type = _classify_scene_type(p_text, idx, len(raw_paras))
        if s_type in used_types:
            # Garantizar que las 8 escenas utilicen composiciones Paper-Cut 2.5D 100% distintas
            for alt in SCENE_TYPES_SEQUENCE:
                if alt not in used_types:
                    s_type = alt
                    break
            else:
                for alt in SCENE_TYPES_SEQUENCE:
                    if not used_types or alt != used_types[-1]:
                        s_type = alt
                        break
        used_types.append(s_type)
        b_num, b_lbl = _extract_badge_from_text(p_text, idx, title)

        # Resumen corto para la cintilla técnica inferior
        clean_summary = re.sub(r"^[¿¡]+", "", p_text).split(".")[0].split("?")[0].strip()
        if len(clean_summary) > 54:
            clean_summary = clean_summary[:51] + "..."

        scenes.append({
            "index": idx + 1,
            "total": len(raw_paras),
            "text": p_text,
            "summary": clean_summary.upper(),
            "t_start": cur_t,
            "t_end": cur_t + dur,
            "duration": dur,
            "scene_type": s_type,
            "badge_num": b_num,
            "badge_label": b_lbl,
        })
        cur_t += dur

    return scenes


def _draw_sticker_card(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    fill: tuple[int, int, int],
    outline: Optional[tuple[int, int, int]] = None,
    radius: int = 22,
    border_w: int = 6,
    shadow_offset: int = 10,
):
    """Dibuja una pieza de papel recortado 2.5D con sombra proyectada y borde blanco tipo sticker."""
    # 1. Sombra 2.5D
    draw.rounded_rectangle(
        [(x1 + shadow_offset, y1 + shadow_offset), (x2 + shadow_offset, y2 + shadow_offset)],
        radius=radius,
        fill=(195, 180, 155),
    )
    # 2. Borde blanco grueso de recorte de papel
    draw.rounded_rectangle(
        [(x1 - border_w, y1 - border_w), (x2 + border_w, y2 + border_w)],
        radius=radius + 4,
        fill=(255, 255, 255),
    )
    # 3. Cuerpo del sticker
    draw.rounded_rectangle(
        [(x1, y1), (x2, y2)],
        radius=radius,
        fill=fill,
        outline=outline,
        width=3 if outline else 0,
    )


def _draw_paper_cloud(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0):
    r1, r2, r3 = int(42 * scale), int(32 * scale), int(28 * scale)
    off = int(38 * scale)
    # Sombra
    for dx, r in ((0, r1), (off, r2), (-off, r3)):
        draw.ellipse([(cx + dx - r + 5, cy - r + 8), (cx + dx + r + 5, cy + r + 8)], fill=(215, 202, 180))
    # Nube blanca
    for dx, r in ((0, r1), (off, r2), (-off, r3)):
        draw.ellipse([(cx + dx - r, cy - r), (cx + dx + r, cy + r)], fill=(255, 255, 255))


def _draw_craft_background_and_hud(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    t: float,
    duration: float,
    title: str,
    scene: dict[str, Any],
    local_p: float,
):
    """Dibuja el fondo de papel artesanal, cuadrícula milimétrica, nubes, placa superior, badge 2.5D y cintilla."""
    # 1. Fondo papel cálido artesanal
    draw.rectangle([(0, 0), (w, h)], fill=(248, 240, 224))
    grid_col = (230, 218, 196)
    for y in range(0, h, 80):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    for x in range(0, w, 80):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)

    # Nubes paper-cut en movimiento continuo
    c1_x = int(((t * 24) % (w + 320)) - 160)
    c2_x = int((((t * 17) + 520) % (w + 320)) - 160)
    _draw_paper_cloud(draw, c1_x, 355, 1.05)
    _draw_paper_cloud(draw, c2_x, 465, 0.80)

    # 3. Badge de Año / Medición en esquina superior derecha con pop-in easeOutBack
    pop = _ease_out_back(_clamp(local_p * 2.2, 0.0, 1.0))
    if pop > 0.05:
        bw = int(135 * pop)
        bh = int(52 * pop)
        bx, by = w - 195, 120
        _draw_sticker_card(draw, bx - bw, by - bh, bx + bw, by + bh, fill=(15, 23, 42), outline=(245, 158, 11), radius=20, border_w=5, shadow_offset=7)
        if pop > 0.65:
            f_bnum = _load_font(36, bold=True)
            f_blbl = _load_font(14, bold=True)
            b_num = scene["badge_num"]
            b_lbl = scene["badge_label"]
            nw = draw.textlength(b_num, font=f_bnum)
            lw = draw.textlength(b_lbl, font=f_blbl)
            draw.text((bx - nw / 2, by - 36), b_num, fill=(251, 191, 36), font=f_bnum)
            draw.text((bx - lw / 2, by + 12), b_lbl, fill=(148, 163, 184), font=f_blbl)


def _draw_scene_1_panorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 1: Panorama Multicapa Paper-Cut adaptado al bioma o monumento del tema."""
    cx, cy = w // 2, int(h * 0.52)
    low = (title + " " + scene["text"]).lower()

    # Marco del diorama central
    dw, dh = max(40, int(420 * pop)), max(32, int(340 * pop))

    is_desert = any(k in low for k in ("desierto", "durango", "silencio", "mapim", "sahara", "duna", "coahuila", "chihuahua", "arena"))
    is_water = any(k in low for k in ("isla", "xochimilco", "muñeca", "mar", "océano", "barco", "agua", "canal", "laguna", "nemo"))
    is_maya = any(k in low for k in ("maya", "pirámide", "teotihuac", "cholula", "campeche", "valeriana", "templo", " arqueol", "tzompantli"))

    # Sol / Cielo circular en relieve paper-cut
    sun_r = int(145 * pop)
    sun_y = cy - int(150 * pop)
    # Anillos de campo magnético / ondas solares
    for ring_i in range(3, 0, -1):
        rr = sun_r + ring_i * 34 + int(math.sin(t * 3.0 + ring_i) * 8)
        draw.ellipse([(cx - rr, sun_y - rr), (cx + rr, sun_y + rr)], outline=(245, 158, 11) if is_desert else (56, 189, 248), width=3)
    draw.ellipse([(cx - sun_r - 6, sun_y - sun_r - 6), (cx + sun_r + 6, sun_y + sun_r + 6)], fill=(255, 255, 255))
    draw.ellipse([(cx - sun_r, sun_y - sun_r), (cx + sun_r, sun_y + sun_r)], fill=(251, 191, 36) if is_desert else (217, 119, 6))

    if is_desert:
        # Mesetas del Bolsón de Mapimí y Dunas en 3 capas paper-cut
        # Meseta trasera
        m_y = cy + int(20 * pop)
        pts_mesa = [(cx - 340, m_y + 180), (cx - 260, m_y - 70), (cx - 40, m_y - 70), (cx + 30, m_y + 180)]
        draw.polygon([(x, y - 6) for x, y in pts_mesa], fill=(255, 255, 255))
        draw.polygon(pts_mesa, fill=(180, 83, 9))

        pts_mesa2 = [(cx + 10, m_y + 180), (cx + 80, m_y - 95), (cx + 270, m_y - 95), (cx + 350, m_y + 180)]
        draw.polygon([(x, y - 6) for x, y in pts_mesa2], fill=(255, 255, 255))
        draw.polygon(pts_mesa2, fill=(154, 52, 18))

        # Dunas escalonadas con borde blanco sticker
        for dy_off, col in ((90, (217, 119, 6)), (160, (245, 158, 11)), (230, (251, 191, 36))):
            wave = int(math.sin(t * 2.0 + dy_off * 0.02) * 10)
            y_top = cy + dy_off + wave
            draw.ellipse([(cx - 460, y_top - 6), (cx + 460, y_top + 210)], fill=(255, 255, 255))
            draw.ellipse([(cx - 454, y_top), (cx + 454, y_top + 204)], fill=col)

        # Cactus Saguaro Paper-Cut Stickers a los lados
        for c_x, c_scale, phase in ((cx - 270, 1.0, 0.0), (cx + 275, 0.9, 1.5), (cx - 110, 0.75, 0.8)):
            sway = int(math.sin(t * 2.4 + phase) * 5)
            c_y = cy + int(150 * c_scale)
            ch = int(130 * c_scale)
            cw = int(22 * c_scale)
            # Borde blanco
            draw.rounded_rectangle([(c_x - cw - 5 + sway, c_y - ch - 5), (c_x + cw + 5 + sway, c_y + 10)], radius=14, fill=(255, 255, 255))
            draw.rounded_rectangle([(c_x - cw * 3 - 4 + sway, c_y - int(ch * 0.65) - 4), (c_x + cw * 3 + 4 + sway, c_y - int(ch * 0.45) + 4)], radius=10, fill=(255, 255, 255))
            # Verde cactus
            draw.rounded_rectangle([(c_x - cw + sway, c_y - ch), (c_x + cw + sway, c_y + 5)], radius=11, fill=(22, 163, 74))
            draw.rounded_rectangle([(c_x - cw * 3 + sway, c_y - int(ch * 0.65)), (c_x + cw * 3 + sway, c_y - int(ch * 0.45))], radius=8, fill=(21, 128, 61))

        # Torre de Telemetría / Antena en el centro
        draw.polygon([(cx - 45, cy + 160), (cx, cy - 30), (cx + 45, cy + 160)], fill=(255, 255, 255))
        draw.polygon([(cx - 38, cy + 158), (cx, cy - 22), (cx + 38, cy + 158)], fill=(30, 41, 59))
        beacon_r = 12 + int(math.sin(t * 8.0) * 4)
        draw.ellipse([(cx - beacon_r, cy - 30 - beacon_r), (cx + beacon_r, cy - 30 + beacon_r)], fill=(239, 68, 68), outline=(255, 255, 255), width=3)

    elif is_water:
        # Olas multicapa + Isla / Navío Paper-Cut
        for dy_off, col in ((60, (14, 116, 144)), (130, (8, 145, 178)), (200, (6, 182, 212))):
            wave = int(math.sin(t * 2.5 + dy_off * 0.03) * 14)
            y_top = cy + dy_off + wave
            draw.ellipse([(cx - 470, y_top - 6), (cx + 470, y_top + 220)], fill=(255, 255, 255))
            draw.ellipse([(cx - 464, y_top), (cx + 464, y_top + 214)], fill=col)
        # Isla / Trajinera central
        by = cy + 30 + int(math.sin(t * 2.6) * 10)
        draw.polygon([(cx - 170, by), (cx + 170, by), (cx + 120, by + 70), (cx - 120, by + 70)], fill=(255, 255, 255))
        draw.polygon([(cx - 162, by + 4), (cx + 162, by + 4), (cx + 114, by + 64), (cx - 114, by + 64)], fill=(180, 83, 9))
        draw.rounded_rectangle([(cx - 110, by - 85), (cx + 110, by + 4)], radius=18, fill=(22, 163, 74), outline=(255, 255, 255), width=5)

    elif is_maya:
        # Pirámide escalonada en 5 niveles con selva paper-cut
        draw.ellipse([(cx - 460, cy + 90), (cx + 460, cy + 340)], fill=(255, 255, 255))
        draw.ellipse([(cx - 454, cy + 96), (cx + 454, cy + 334)], fill=(21, 128, 61))
        for lvl in range(5):
            pw = 280 - lvl * 46
            py_top = cy + 110 - (lvl + 1) * 48
            _draw_sticker_card(draw, cx - pw, py_top, cx + pw, py_top + 46, fill=(226, 232, 240), outline=(148, 163, 184), radius=8, border_w=4, shadow_offset=6)
            draw.rectangle([(cx - 28, py_top), (cx + 28, py_top + 46)], fill=(148, 163, 184))

    else:
        # Cerro histórico + Fortaleza / Castillo Neoclásico + Bandera ondeando
        draw.ellipse([(cx - 460, cy + 75), (cx + 460, cy + 345)], fill=(255, 255, 255))
        draw.ellipse([(cx - 452, cy + 82), (cx + 452, cy + 338)], fill=(22, 163, 74))
        _draw_sticker_card(draw, cx - 280, cy - 110, cx + 280, cy + 110, fill=(248, 250, 252), outline=(203, 213, 225), radius=18, border_w=6, shadow_offset=9)
        _draw_sticker_card(draw, cx - 85, cy - 205, cx + 85, cy - 105, fill=(226, 232, 240), outline=(148, 163, 184), radius=12, border_w=5, shadow_offset=6)
        for ax in range(cx - 210, cx + 220, 70):
            draw.rounded_rectangle([(ax - 20, cy - 30), (ax + 20, cy + 75)], radius=14, fill=(30, 41, 59), outline=(255, 255, 255), width=2)
        # Bandera tricolor ondeando
        w_off = int(math.sin(t * 6.0) * 6)
        draw.line([(cx, cy - 205), (cx, cy - 295)], fill=(71, 85, 105), width=6)
        draw.rectangle([(cx + 3, cy - 295 + w_off), (cx + 33, cy - 240 + w_off)], fill=(22, 163, 74))
        draw.rectangle([(cx + 33, cy - 295 + w_off), (cx + 63, cy - 240 + w_off)], fill=(255, 255, 255))
        draw.rectangle([(cx + 63, cy - 295 + w_off), (cx + 93, cy - 240 + w_off)], fill=(220, 38, 38))


def _draw_scene_2_cartographic_map(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 2: Mapa Cartográfico en Pergamino 2.5D con Rosa de los Vientos, Paralelo y Ruta."""
    # Pergamino principal
    cx, cy = w // 2, int(h * 0.51)
    mw, mh = max(40, int(390 * pop)), max(28, int(275 * pop))

    # Pergamino principal
    _draw_sticker_card(draw, cx - mw, cy - mh, cx + mw, cy + mh, fill=(254, 243, 199), outline=(217, 119, 6), radius=26, border_w=7, shadow_offset=12)

    # Curvas de nivel topográficas y paralelo geográfico
    for r_i in range(1, 4):
        rx, ry = int(mw * 0.25 * r_i), int(mh * 0.22 * r_i)
        draw.ellipse([(cx - rx - 40, cy - ry + 10), (cx + rx - 40, cy + ry + 10)], outline=(245, 158, 11), width=2)

    # Línea de Paralelo / Coordenada
    draw.line([(cx - mw + 25, cy - 20), (cx + mw - 25, cy - 20)], fill=(180, 83, 9), width=3)
    f_map = _load_font(18, bold=True)
    draw.text((cx - mw + 38, cy - 48), "LATITUD // PARALELO DE INTERSECCIÓN GEOGRÁFICA", fill=(146, 64, 14), font=f_map)

    # Trayectoria animada punteada y Pin de impacto
    n_dots = 12
    active_dots = int(((t * 1.4) % 1.0) * n_dots) + 3
    for d_i in range(min(n_dots, active_dots)):
        p_r = d_i / float(n_dots)
        dx = int((cx - mw + 90) + p_r * (mw * 1.15))
        dy = int((cy - mh + 95) + math.sin(p_r * 3.14) * 90)
        draw.ellipse([(dx - 6, dy - 6), (dx + 6, dy + 6)], fill=(220, 38, 38), outline=(255, 255, 255), width=2)

    # Punto de impacto pulsante
    tx, ty = cx + 60, cy + 15
    pulse_r = int(24 + 14 * abs(math.sin(t * 4.0)))
    draw.ellipse([(tx - pulse_r, ty - pulse_r), (tx + pulse_r, ty + pulse_r)], outline=(220, 38, 38), width=4)
    draw.ellipse([(tx - 14, ty - 14), (tx + 14, ty + 14)], fill=(220, 38, 38), outline=(255, 255, 255), width=4)

    # Rosa de los vientos giratoria (abajo derecha del mapa)
    comp_x, comp_y, comp_r = cx + mw - 105, cy + mh - 95, 62
    draw.ellipse([(comp_x - comp_r - 4, comp_y - comp_r - 4), (comp_x + comp_r + 4, comp_y + comp_r + 4)], fill=(255, 255, 255))
    draw.ellipse([(comp_x - comp_r, comp_y - comp_r), (comp_x + comp_r, comp_y + comp_r)], fill=(15, 23, 42), outline=(245, 158, 11), width=3)
    ang = t * 1.8
    nx = comp_x + int(math.cos(ang) * (comp_r - 12))
    ny = comp_y + int(math.sin(ang) * (comp_r - 12))
    sx = comp_x - int(math.cos(ang) * (comp_r - 12))
    sy = comp_y - int(math.sin(ang) * (comp_r - 12))
    draw.line([(sx, sy), (nx, ny)], fill=(239, 68, 68), width=5)
    draw.ellipse([(comp_x - 6, comp_y - 6), (comp_x + 6, comp_y + 6)], fill=(255, 255, 255))

    # Sello de lacre rojo
    seal_x, seal_y = cx - mw + 115, cy + mh - 90
    draw.ellipse([(seal_x - 56, seal_y - 56), (seal_x + 56, seal_y + 56)], fill=(255, 255, 255))
    draw.ellipse([(seal_x - 50, seal_y - 50), (seal_x + 50, seal_y + 50)], fill=(185, 28, 28), outline=(251, 191, 36), width=3)
    f_seal = _load_font(16, bold=True)
    draw.text((seal_x - 36, seal_y - 18), "REGISTRO", fill=(254, 243, 199), font=f_seal)
    draw.text((seal_x - 24, seal_y + 4), scene["badge_num"][:6], fill=(251, 191, 36), font=f_seal)


def _draw_scene_3_impact_event(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 3: El Suceso Central en Acción (Cohete Athena / Meteorito Allende / Hallazgo Dinámico)."""
    cx, cy = w // 2, int(h * 0.51)
    rad = max(40, int(340 * pop))

    # Portal circular de cielo nocturno profundo tipo sticker 2.5D
    draw.ellipse([(cx - rad + 10, cy - rad + 12), (cx + rad + 10, cy + rad + 12)], fill=(190, 175, 150))
    draw.ellipse([(cx - rad - 8, cy - rad - 8), (cx + rad + 8, cy + rad + 8)], fill=(255, 255, 255))
    draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], fill=(15, 23, 42), outline=(56, 189, 248), width=4)

    # Estrellas parpadeantes dentro del portal
    for s_i in range(18):
        ang = s_i * 1.9
        dist = 70 + (s_i * 37) % (rad - 80)
        sx = cx + int(math.cos(ang) * dist)
        sy = cy + int(math.sin(ang) * dist)
        r_s = 3 + (s_i % 3)
        draw.ellipse([(sx - r_s, sy - r_s), (sx + r_s, sy + r_s)], fill=(254, 243, 199))

    # Estela diagonal de descenso (Cohete / Meteorito / Objeto protagonista)
    shift = int(math.sin(t * 3.2) * 24)
    rx, ry = cx + 40 + shift, cy + 20 + shift

    # Nubes de humo / plasma en papel recortado detrás de la trayectoria
    for p_i in range(5, 0, -1):
        px = rx - p_i * 42
        py = ry - p_i * 38
        pr = 26 + p_i * 7
        draw.ellipse([(px - pr - 4, py - pr - 4), (px + pr + 4, py + pr + 4)], fill=(255, 255, 255))
        draw.ellipse([(px - pr, py - pr), (px + pr, py + pr)], fill=(249, 115, 22) if p_i < 3 else (251, 191, 36))

    # Cuerpo del Cohete Athena / Bólido con borde blanco sticker
    body_pts = [(rx - 95, ry - 45), (rx - 45, ry - 95), (rx + 75, ry + 25), (rx + 25, ry + 75)]
    nose_pts = [(rx + 75, ry + 25), (rx + 135, ry + 115), (rx + 25, ry + 75)]
    draw.polygon([(x - 4, y - 4) for x, y in body_pts], fill=(255, 255, 255))
    draw.polygon(body_pts, fill=(241, 245, 249), outline=(30, 41, 59), width=3)
    draw.polygon(nose_pts, fill=(220, 38, 38), outline=(255, 255, 255), width=3)

    # Ondas de choque concéntricas en el punto de impacto inferior
    for w_i in range(1, 4):
        wr = int(50 * w_i + ((t * 60) % 45))
        draw.arc([(rx + 30 - wr, ry + 40 - wr // 2), (rx + 30 + wr, ry + 40 + wr // 2)], start=0, end=180, fill=(56, 189, 248), width=3)

    # Etiqueta técnica flotante dentro de la escena
    _draw_sticker_card(draw, cx - 230, cy + rad - 55, cx + 230, cy + rad + 25, fill=(220, 38, 38), outline=(255, 255, 255), radius=16, border_w=5, shadow_offset=7)
    f_lbl = _load_font(22, bold=True)
    lbl_txt = f"IMPACTO DOCUMENTADO • {scene['badge_num']}"
    tw = draw.textlength(lbl_txt, font=f_lbl)
    draw.text((cx - tw / 2, cy + rad - 28), lbl_txt, fill=(255, 255, 255), font=f_lbl)


def _draw_scene_4_magnetic_instruments(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 4: Consola de Instrumentación, Brújula Magnética Descontrolada y Osciloscopio de Radio."""
    cx, cy = w // 2, int(h * 0.51)
    cw, ch = max(40, int(400 * pop)), max(28, int(270 * pop))

    # Panel principal de telemetría
    _draw_sticker_card(draw, cx - cw, cy - ch, cx + cw, cy + ch, fill=(15, 23, 42), outline=(56, 189, 248), radius=26, border_w=7, shadow_offset=12)

    # 1. Brújula Magnética Gigante a la izquierda
    bx, by, br = cx - int(cw * 0.45), cy - 15, int(145 * pop)
    draw.ellipse([(bx - br - 5, by - br - 5), (bx + br + 5, by + br + 5)], fill=(255, 255, 255))
    draw.ellipse([(bx - br, by - br), (bx + br, by + br)], fill=(30, 41, 59), outline=(245, 158, 11), width=4)

    f_card = _load_font(20, bold=True)
    draw.text((bx - 8, by - br + 12), "N", fill=(239, 68, 68), font=f_card)
    draw.text((bx - 7, by + br - 34), "S", fill=(241, 245, 249), font=f_card)
    draw.text((bx + br - 28, by - 12), "E", fill=(241, 245, 249), font=f_card)
    draw.text((bx - br + 12, by - 12), "O", fill=(241, 245, 249), font=f_card)

    # Aguja magnética girando con anomalía
    needle_ang = t * 5.5 + math.sin(t * 9.0) * 1.4
    nx = bx + int(math.cos(needle_ang) * (br - 32))
    ny = by + int(math.sin(needle_ang) * (br - 32))
    sx = bx - int(math.cos(needle_ang) * (br - 32))
    sy = by - int(math.sin(needle_ang) * (br - 32))
    draw.line([(bx, by), (nx, ny)], fill=(239, 68, 68), width=8)
    draw.line([(bx, by), (sx, sy)], fill=(226, 232, 240), width=8)
    draw.ellipse([(bx - 12, by - 12), (bx + 12, by + 12)], fill=(245, 158, 11), outline=(255, 255, 255), width=3)

    # 2. Pantalla de Osciloscopio de Ondas de Radio a la derecha
    ox1, oy1 = cx + 10, cy - int(ch * 0.68)
    ox2, oy2 = cx + cw - 35, cy + int(ch * 0.25)
    draw.rounded_rectangle([(ox1, oy1), (ox2, oy2)], radius=16, fill=(6, 18, 28), outline=(16, 185, 129), width=3)

    mid_y = (oy1 + oy2) // 2
    prev_pt = None
    for x in range(ox1 + 14, ox2 - 14, 8):
        # La onda se atenúa en la mitad derecha simulando bloqueo de señal de radio
        rel_x = (x - ox1) / float(max(1, ox2 - ox1))
        amp = 55.0 if rel_x < 0.5 else 8.0
        wv = math.sin(x * 0.08 + t * 14.0) * amp * math.cos(t * 4.0)
        pt = (x, int(mid_y + wv))
        if prev_pt:
            draw.line([prev_pt, pt], fill=(16, 185, 129) if rel_x < 0.5 else (239, 68, 68), width=4)
        prev_pt = pt

    f_osc = _load_font(17, bold=True)
    draw.text((ox1 + 18, oy1 + 14), "SEÑAL RF // ANOMALÍA MAGNÉTICA", fill=(52, 211, 153), font=f_osc)

    # Banda inferior de lectura instrumental
    draw.rounded_rectangle([(cx + 10, oy2 + 22), (ox2, cy + ch - 35)], radius=14, fill=(30, 41, 59), outline=(245, 158, 11), width=2)
    draw.text((cx + 28, oy2 + 42), "INTERFERENCIA: MAGNETITA + IONIZACIÓN", fill=(251, 191, 36), font=f_osc)


def _draw_scene_5_strata_cutaway(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 5: Corte Transversal 2.5D de Estratos Subterráneos, Magnetita y Minerales."""
    cx, cy = w // 2, int(h * 0.51)
    sw = max(40, int(380 * pop))

    layers = [
        ("01 // SUPERFICIE Y CUENCA ÁRIDA", (217, 119, 6), -195),
        ("02 // CONCENTRACIÓN DE MAGNETITA Y HIERRO", (180, 83, 9), -65),
        ("03 // FÓSILES MARINOS Y SEDIMENTOS (MAR DE TETIS)", (120, 53, 15), 65),
        ("04 // NÚCLEO DE ANOMALÍA GEOMAGNÉTICA", (30, 41, 59), 195),
    ]
    f_lay = _load_font(20, bold=True)

    for idx, (lbl, col, y_off) in enumerate(layers):
        breathe = int(math.sin(t * 2.5 + idx * 0.9) * 6)
        ly1 = cy + y_off - 50 + breathe
        ly2 = cy + y_off + 50 + breathe
        _draw_sticker_card(draw, cx - sw, ly1, cx + sw, ly2, fill=col, outline=(255, 255, 255), radius=18, border_w=5, shadow_offset=8)
        draw.text((cx - sw + 28, ly1 + 36), lbl, fill=(255, 255, 255), font=f_lay)

        # Nodos minerales brillantes a la derecha de cada estrato
        node_x = cx + sw - 55
        node_y = (ly1 + ly2) // 2
        nr = 16 + int(math.sin(t * 5.0 + idx) * 4)
        draw.ellipse([(node_x - nr, node_y - nr), (node_x + nr, node_y + nr)], fill=(56, 189, 248) if idx == 3 else (251, 191, 36), outline=(255, 255, 255), width=3)


def _draw_scene_6_dossier_chronicle(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 6: Expediente Documental en 3 Tarjetas Paper-Cut Escalonadas."""
    cx, cy = w // 2, int(h * 0.51)
    cw = max(40, int(385 * pop))

    cards = [
        ("EXPEDIENTE DE CAMPO VERIFICADO", f"REGISTRO HISTÓRICO • {scene['badge_num']}", (185, 28, 28), -170),
        ("PROTAGONISTAS E INSTITUCIONES", "EVIDENCIA DOCUMENTADA EN ARCHIVOS OFICIALES", (30, 58, 138), 0),
        ("CRONOLOGÍA COMPROBADA", scene["summary"][:44], (6, 95, 70), 170),
    ]
    f_h = _load_font(22, bold=True)
    f_b = _load_font(17, bold=False)

    for idx, (head, body, accent_col, y_off) in enumerate(cards):
        c_pop = _ease_out_back(_clamp(pop * 1.4 - idx * 0.18, 0.0, 1.0))
        if c_pop <= 0.05:
            continue
        w_i = int(cw * c_pop)
        y1 = cy + y_off - 62
        y2 = cy + y_off + 62
        _draw_sticker_card(draw, cx - w_i, y1, cx + w_i, y2, fill=(255, 253, 248), outline=accent_col, radius=20, border_w=6, shadow_offset=9)
        draw.rounded_rectangle([(cx - w_i + 18, y1 + 18), (cx - w_i + 32, y2 - 18)], radius=5, fill=accent_col)
        draw.text((cx - w_i + 50, y1 + 24), head, fill=accent_col, font=f_h)
        draw.text((cx - w_i + 50, y1 + 66), body, fill=(15, 23, 42), font=f_b)


def _draw_scene_7_myth_vs_science(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 7: Comparativa Dual Paper-Cut (Mito Popular vs. Ciencia Comprobada)."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(30, int(195 * pop))
    card_h = max(38, int(245 * pop))

    # Tarjeta Izquierda: Mito y Leyenda
    lx = cx - card_w - 22
    _draw_sticker_card(draw, lx - card_w, cy - card_h, lx + card_w, cy + card_h, fill=(127, 29, 29), outline=(248, 113, 113), radius=24, border_w=6, shadow_offset=10)
    # Tarjeta Derecha: Ciencia y Geología
    rx = cx + card_w + 22
    _draw_sticker_card(draw, rx - card_w, cy - card_h, rx + card_w, cy + card_h, fill=(6, 78, 59), outline=(52, 211, 153), radius=24, border_w=6, shadow_offset=10)

    f_t = _load_font(23, bold=True)
    f_s = _load_font(17, bold=True)

    draw.text((lx - card_w + 26, cy - card_h + 32), "MITO POPULAR", fill=(254, 202, 202), font=f_t)
    draw.text((lx - card_w + 26, cy - card_h + 72), "• TEORÍAS Y FOLCLORE", fill=(255, 255, 255), font=f_s)
    draw.text((lx - card_w + 26, cy - card_h + 106), "• LEYENDAS ORALES", fill=(255, 255, 255), font=f_s)

    # Icono sticker en tarjeta izquierda
    ir = 68 + int(math.sin(t * 3.0) * 5)
    draw.ellipse([(lx - ir, cy + 40 - ir), (lx + ir, cy + 40 + ir)], fill=(220, 38, 38), outline=(255, 255, 255), width=5)

    draw.text((rx - card_w + 26, cy - card_h + 32), "CIENCIA REAL", fill=(167, 243, 208), font=f_t)
    draw.text((rx - card_w + 26, cy - card_h + 72), "• EVIDENCIA FÍSICA", fill=(255, 255, 255), font=f_s)
    draw.text((rx - card_w + 26, cy - card_h + 106), "• DATOS DE CAMPO", fill=(255, 255, 255), font=f_s)

    # Icono cristal/átomo en tarjeta derecha
    draw.ellipse([(rx - ir, cy + 40 - ir), (rx + ir, cy + 40 + ir)], fill=(16, 185, 129), outline=(255, 255, 255), width=5)

    # Medalla VS central
    _draw_sticker_card(draw, cx - 52, cy - 52, cx + 52, cy + 52, fill=(245, 158, 11), outline=(15, 23, 42), radius=26, border_w=5, shadow_offset=6)
    draw.text((cx - 20, cy - 14), "VS", fill=(15, 23, 42), font=_load_font(28, bold=True))


def _draw_scene_8_finale_medallion(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Escena 8: Medallón Documental de Cierre y Llamado al Debate."""
    cx, cy = w // 2, int(h * 0.49)
    mr = max(30, int(195 * pop))

    # Rayos solares giratorios en papel recortado
    for r_i in range(12):
        ang = t * 0.8 + (r_i * math.pi / 6.0)
        x2 = cx + int(math.cos(ang) * (mr + 75))
        y2 = cy + int(math.sin(ang) * (mr + 75))
        draw.line([(cx, cy), (x2, y2)], fill=(245, 158, 11), width=8)

    # Medallón circular 2.5D
    draw.ellipse([(cx - mr + 10, cy - mr + 12), (cx + mr + 10, cy + mr + 12)], fill=(195, 180, 155))
    draw.ellipse([(cx - mr - 8, cy - mr - 8), (cx + mr + 8, cy + mr + 8)], fill=(255, 255, 255))
    draw.ellipse([(cx - mr, cy - mr), (cx + mr, cy + mr)], fill=(15, 23, 42), outline=(251, 191, 36), width=6)

    f_big = _load_font(34, bold=True)
    f_cta = _load_font(22, bold=True)
    t1 = "HISTORIANDO"
    t2 = "EXPEDIENTE REAL"
    draw.text((cx - draw.textlength(t1, font=f_big) / 2, cy - 42), t1, fill=(251, 191, 36), font=f_big)
    draw.text((cx - draw.textlength(t2, font=f_cta) / 2, cy + 12), t2, fill=(241, 245, 249), font=f_cta)

    # Tarjeta pulsante de pregunta a la audiencia
    by = cy + mr + 85
    _draw_sticker_card(draw, cx - 340, by - 48, cx + 340, by + 48, fill=(217, 119, 6), outline=(255, 255, 255), radius=22, border_w=6, shadow_offset=9)
    q_txt = "¿QUÉ OPINAS? DÉJALO EN LOS COMENTARIOS"
    draw.text((cx - draw.textlength(q_txt, font=f_cta) / 2, by - 14), q_txt, fill=(255, 255, 255), font=f_cta)


_TRANS_BUF_A: Optional[Image.Image] = None
_TRANS_BUF_B: Optional[Image.Image] = None


def _render_scene_content(
    target_im: Image.Image,
    w: int,
    h: int,
    t: float,
    duration: float,
    title: str,
    scene: dict[str, Any],
    pop: float,
    local_p: float,
):
    """Renderiza una escena Paper-Cut 2.5D completa sobre la imagen dada."""
    draw = ImageDraw.Draw(target_im)
    _draw_craft_background_and_hud(draw, w, h, t, duration, title, scene, local_p)
    stype = scene.get("scene_type", "")
    try:
        from studio.opuscar.scene_archetypes import render_archetype_scene
        render_archetype_scene(draw, w, h, t, title, scene, pop)
        return
    except Exception as e_arch:
        logger.debug(f"Aviso en render_archetype_scene: {e_arch}")

    if stype == "panorama_geografico":
        _draw_scene_1_panorama(draw, w, h, t, title, scene, pop)
    elif stype == "mapa_cartografico":
        _draw_scene_2_cartographic_map(draw, w, h, t, title, scene, pop)
    elif stype == "suceso_impacto":
        _draw_scene_3_impact_event(draw, w, h, t, title, scene, pop)
    elif stype == "instrumentos_anomalia":
        _draw_scene_4_magnetic_instruments(draw, w, h, t, title, scene, pop)
    elif stype == "corte_estratos":
        _draw_scene_5_strata_cutaway(draw, w, h, t, title, scene, pop)
    elif stype == "cronica_expediente":
        _draw_scene_6_dossier_chronicle(draw, w, h, t, title, scene, pop)
    elif stype == "mito_vs_ciencia":
        _draw_scene_7_myth_vs_science(draw, w, h, t, title, scene, pop)
    else:
        _draw_scene_8_finale_medallion(draw, w, h, t, title, scene, pop)


def draw_multiscene_papercut_diorama(
    draw_or_img: Any,
    w: int,
    h: int,
    t: float,
    duration: float,
    title: str,
    scenes: list[dict[str, Any]],
):
    """Orquesta las 8-9 escenas Paper-Cut 2.5D con transiciones fluidas continuas (Hermite SmoothStep) a 60 FPS sin congelamientos."""
    global _TRANS_BUF_A, _TRANS_BUF_B

    target_im = draw_or_img if isinstance(draw_or_img, Image.Image) else getattr(draw_or_img, "_image", None)
    if target_im is None:
        target_im = Image.new("RGB", (w, h), (248, 240, 224))

    n_scenes = len(scenes)
    if n_scenes == 0:
        return

    # Comprobar si t cae en la ventana de transición entre escena i y escena i+1
    trans_scene_idx = -1
    trans_dur = 0.45
    for idx in range(n_scenes - 1):
        cur_sc = scenes[idx]
        t_trans_start = cur_sc["t_end"] - trans_dur
        t_trans_end = cur_sc["t_end"]
        if t_trans_start <= t < t_trans_end:
            trans_scene_idx = idx
            break

    if trans_scene_idx >= 0:
        # Transición fluida con mezcla de fotogramas sin saltos bruscos
        cur_sc = scenes[trans_scene_idx]
        next_sc = scenes[trans_scene_idx + 1]
        t_trans_start = cur_sc["t_end"] - trans_dur
        tau = _clamp((t - t_trans_start) / max(0.1, trans_dur), 0.0, 1.0)
        # Curva de interpolación Hermite SmoothStep C1 continua
        s = tau * tau * (3.0 - 2.0 * tau)

        if _TRANS_BUF_A is None or _TRANS_BUF_A.size != (w, h):
            _TRANS_BUF_A = Image.new("RGB", (w, h), (248, 240, 224))
            _TRANS_BUF_B = Image.new("RGB", (w, h), (248, 240, 224))

        # Renderizar escena saliente
        pop_out = 1.0 - 0.04 * s
        _render_scene_content(_TRANS_BUF_A, w, h, t, duration, title, cur_sc, pop=pop_out, local_p=1.0)

        # Renderizar escena entrante
        pop_in = 0.96 + 0.04 * s
        _render_scene_content(_TRANS_BUF_B, w, h, t, duration, title, next_sc, pop=pop_in, local_p=s)

        # Fusión continua de capas
        blended = Image.blend(_TRANS_BUF_A, _TRANS_BUF_B, s)
        target_im.paste(blended, (0, 0))
    else:
        # Estado estacionario de escena
        active_scene = scenes[-1]
        for sc in scenes:
            if sc["t_start"] <= t < sc["t_end"]:
                active_scene = sc
                break

        local_t = max(0.0, t - active_scene["t_start"])
        local_p = _clamp(local_t / max(0.2, active_scene["duration"]), 0.0, 1.0)

        # Solo la primera escena realiza el pop de apertura inicial
        if active_scene["index"] == 1:
            pop = _ease_out_back(_clamp(local_t / 0.50, 0.0, 1.0))
        else:
            pop = 1.0

        _render_scene_content(target_im, w, h, t, duration, title, active_scene, pop=pop, local_p=local_p)


def draw_paper_cutout_diorama(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str, narration: str = ""):
    scenes = parse_narration_into_diorama_scenes(narration or title, duration, title)
    draw_multiscene_papercut_diorama(draw, w, h, t, duration, title, scenes)


def draw_blueprint_cad(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str, narration: str = ""):
    draw_paper_cutout_diorama(draw, w, h, t, duration, title, narration)


def draw_vector_flow(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str, narration: str = ""):
    draw_paper_cutout_diorama(draw, w, h, t, duration, title, narration)


def draw_da_vinci_codex(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str, narration: str = ""):
    draw_paper_cutout_diorama(draw, w, h, t, duration, title, narration)


def draw_hud_telemetry(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str, narration: str = ""):
    draw_paper_cutout_diorama(draw, w, h, t, duration, title, narration)


def draw_anime_speedlines(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, duration: float, title: str, narration: str = ""):
    draw_paper_cutout_diorama(draw, w, h, t, duration, title, narration)


def render_opuscar_animation_video(
    style_id: str = "paper_cutout_diorama",
    title: str = "Animación Paper-Cut",
    narration: str = "Animación procedimental paper-cut con estética diorama multicapa.",
    voice: str = "es-MX-DaliaNeural",
    is_vertical: bool = True,
    fps: int = 60,
    output_dir: Optional[Path] = None,
) -> Path:
    """Renderiza el video cinematográfico completo en MP4 con 8-9 escenas dinámicas Paper-Cut 2.5D a 60 FPS."""
    if output_dir is None:
        output_dir = _repo_root / "projects" / f"opuscar_{style_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Limpieza ortográfica y gramatical previa del guion canónico
    try:
        from studio.karaoke_subtitles import clean_and_correct_spanish_orthography
        clean_narration, _ = clean_and_correct_spanish_orthography(narration)
        narration = clean_narration
    except Exception:
        pass

    # 1. Sintetizar narración + música documental y calcular duración exacta
    audio_path = output_dir / "narration.mp3"
    dur_sec = asyncio.run(synthesize_opuscar_audio(narration, audio_path, voice=voice))
    dur_sec = max(10.0, dur_sec)

    # 2. Configurar resolución Full HD (9:16 vertical 1080x1920 o 16:9 1920x1080)
    if is_vertical:
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080

    # Renderizar a 60 fps reales por pipe directo a FFmpeg (suavidad absoluta sin caídas de frames)
    render_fps = max(30, int(fps or 60))
    total_frames = int(dur_sec * render_fps)
    scenes = parse_narration_into_diorama_scenes(narration, dur_sec, title)

    # 3. Crear archivo de subtítulos ASS Big Focus
    subtitles_ass = output_dir / "subtitles.ass"
    try:
        from studio.karaoke_subtitles import generate_dynamic_karaoke_ass
        generate_dynamic_karaoke_ass(
            audio_path=audio_path,
            output_ass_path=subtitles_ass,
            reference_text=narration,
            total_duration=dur_sec,
            width=width,
            height=height,
        )
    except Exception:
        words = [w.strip() for w in narration.split() if w.strip()]
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
                dialogues.append(f"Dialogue: 0,0:{s_min:02d}:{s_sec:05.2f},0:{e_min:02d}:{e_sec:05.2f},Default,,0,0,0,,{phrase}")
        else:
            dialogues.append(f"Dialogue: 0,0:00:00.20,0:00:{dur_sec:05.2f},Default,,0,0,0,,{title}")

        sub_content = f"""[Script Info]
Title: Lemo-Opuscar Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,44,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H90000000,-1,0,0,0,100,100,0,0,1,4.8,2.6,2,50,50,245,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"
        subtitles_ass.write_text(sub_content, encoding="utf-8")

    # 4. Guardar metadatos
    meta_path = output_dir / "meta.json"
    try:
        meta_path.write_text(
            json.dumps({
                "duration": dur_sec,
                "fps": fps,
                "style_id": style_id,
                "title": title,
                "narration": narration,
                "voice": voice,
                "scenes_count": len(scenes),
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass

    # 5. Enviar cuadros directamente por pipe rawvideo a FFmpeg (ultra rápido y limpio)
    final_video = output_dir / f"opuscar_{style_id}_{width}x{height}.mp4"
    tmp_video = output_dir / f"opuscar_tmp_{os.getpid()}_{int(time.time()*1000)}.mp4"
    ffmpeg_bin = _get_ffmpeg()

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(render_fps),
        "-i", "-",
        "-i", str(audio_path.resolve()),
        "-vf", f"subtitles={subtitles_ass.name}",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        str(tmp_video.resolve()),
    ]
    log_err_path = output_dir / "ffmpeg_render.log"
    with open(log_err_path, "wb") as err_file:
        proc = subprocess.Popen(
            cmd,
            cwd=str(output_dir.resolve()),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=err_file,
        )
        assert proc.stdin is not None
        try:
            for f in range(total_frames):
                t = f / float(render_fps)
                im = Image.new("RGB", (width, height), (248, 240, 224))
                draw_multiscene_papercut_diorama(im, width, height, t, dur_sec, title, scenes)
                proc.stdin.write(im.tobytes())
            proc.stdin.close()
        except Exception as e_pipe:
            logger.error(f"Error procesando frames en pipe FFmpeg: {e_pipe}")
            try:
                proc.stdin.close()
            except Exception:
                pass
            raise e_pipe
        proc.wait()
    if proc.returncode != 0:
        if tmp_video.exists():
            try:
                tmp_video.unlink()
            except Exception:
                pass
        err_msg = (log_err_path.read_text(encoding="utf-8", errors="ignore") if log_err_path.exists() else "")[-400:]
        raise RuntimeError(f"Error FFmpeg en Lemo-Opuscar: {err_msg}")

    # Reemplazo atómico a destino final
    try:
        os.replace(str(tmp_video), str(final_video))
    except Exception:
        try:
            if final_video.exists():
                final_video.unlink()
            import shutil
            shutil.move(str(tmp_video), str(final_video))
        except Exception:
            if tmp_video.exists() and not final_video.exists():
                tmp_video.rename(final_video)

    meta_payload = {
        "style_id": style_id,
        "title": title,
        "narration": narration,
        "voice": voice,
        "duration": round(float(dur_sec), 2),
        "fps": render_fps,
        "width": width,
        "height": height,
        "scenes_count": len(scenes),
        "filename": final_video.name,
    }
    try:
        (output_dir / "meta.json").write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return final_video


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
    """Tarjeta animada con el fondo procedural del estilo elegido."""
    frames_dir = out_mp4.parent / f"_card_{out_mp4.stem}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    font_t = _load_font(max(28, width // 14))
    font_s = _load_font(max(18, width // 26))
    total = int(duration * fps)
    scenes = parse_narration_into_diorama_scenes(subtitle or title, duration, title)
    for f in range(total):
        t = f / fps
        im = Image.new("RGB", (width, height), (248, 240, 224))
        d = ImageDraw.Draw(im)
        draw_multiscene_papercut_diorama(d, width, height, t, duration, title, scenes)
        alpha = min(1.0, t / 0.5, (duration - t) / 0.4 if duration - t < 0.4 else 1.0)
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, int(165 * alpha)))
        im = Image.alpha_composite(im.convert("RGBA"), overlay)
        d = ImageDraw.Draw(im)
        y = int(height * 0.38)
        for line in _wrap_text(d, title.upper(), font_t, int(width * 0.84)):
            wline = d.textlength(line, font=font_t)
            d.text(((width - wline) / 2, y), line, font=font_t, fill=(255, 255, 255, int(255 * alpha)))
            y += int(font_t.size * 1.25)
        if subtitle:
            y += 16
            for line in _wrap_text(d, subtitle, font_s, int(width * 0.8)):
                wline = d.textlength(line, font=font_s)
                d.text(((width - wline) / 2, y), line, font=font_s, fill=(255, 222, 89, int(255 * alpha)))
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
    """Antepone una intro y añade un cierre Lemo-Opuscar al video principal."""
    work = out_video.parent
    intro = render_opuscar_title_card(work / "_brand_intro.mp4", intro_title, intro_subtitle, style_id, width, height, fps, 2.5)
    outro = render_opuscar_title_card(work / "_brand_outro.mp4", outro_title, "", style_id, width, height, fps, 2.5)
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
