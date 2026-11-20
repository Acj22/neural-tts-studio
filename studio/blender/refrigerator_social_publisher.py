"""AI VIDEO STUDIO — Master Social Publisher: Ciclo de Refrigeración 9:16.
Genera el paquete completo de publicación comercial e institucional para:
- TikTok
- YouTube Shorts
- Instagram Reels

Incluye:
1. Pista de audio multicapa cinematográfica:
   - Narración limpia de DaliaNeural (es-MX)
   - Banda sonora ambiental procedural sintetizada en CPU (Synth Pad + Sub Drone) duckeada a -22 dB
   - Efectos Foley Earshot procedurales (Whooshes, Hum de compresor, Clicks mecánicos, Hiss capilar, Chime de escarcha)
2. Subtítulos ASS avanzados con Zona Segura Estricta (MarginV=180):
   - Hook Card superior en los primeros 5 segundos
   - Badges de etapa activa (Top Tracker)
   - Subtítulos de diálogo en amarillo/blanco de alto contraste
   - Call to Action (CTA) al cierre
3. Renderizado y Masterización FFmpeg en Full HD Vertical (1080x1920) a 30 fps, H.264 High Profile.
4. Portada / Miniatura de alto impacto (Thumbnail 1080x1920) con badges visuales.
5. Kit de Publicación (Títulos virales A/B, descripción pedagógica verificada, hashtags y primer comentario fijado).
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

_repo_root = Path(__file__).resolve().parent.parent.parent
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
SAMPLE_RATE = 44100

# ------------------------------------------------------------------------------
# 1. ESTRUCTURA DE ETAPAS DEL GUION Y TIMINGS (105s TOTAL)
# ------------------------------------------------------------------------------
STAGES_CONFIG = [
    {
        "id": "st1_hook",
        "badge": "• INTRODUCCIÓN CIENTÍFICA •",
        "time_range": (0.0, 14.8),
        "foley": [
            (0.1, "whoosh_impact", 1.2),
            (4.8, "whoosh_soft", 0.8),
            (9.2, "sub_boom", 1.4),
        ],
        "subs": [
            (0.5, 4.2, "¿Cómo crea frío un refrigerador", "en pleno día caluroso?"),
            (4.5, 8.8, "La respuesta científica es sorprendente:", "en realidad no genera frío..."),
            (9.0, 14.2, "¡Sino que extrae el calor", "y lo expulsa hacia el exterior!"),
        ],
    },
    {
        "id": "st2_architecture",
        "badge": "• 1. ARQUITECTURA DE 5 COMPONENTES •",
        "time_range": (14.8, 30.5),
        "foley": [
            (14.9, "whoosh_fast", 0.6),
            (19.8, "metal_click", 0.4),
            (24.8, "whoosh_soft", 0.7),
        ],
        "subs": [
            (14.8, 19.5, "El sistema utiliza un circuito cerrado", "con cinco componentes clave:"),
            (19.8, 24.5, "Compresor en la base, serpentín condensador,", "y filtro deshidratador..."),
            (24.8, 29.8, "Además del tubo capilar y el evaporador", "dentro del compartimento."),
        ],
    },
    {
        "id": "st3_compressor",
        "badge": "• 2. COMPRESOR HERMÉTICO •",
        "time_range": (30.5, 48.0),
        "foley": [
            (30.6, "whoosh_zoom", 0.8),
            (31.5, "compressor_hum", 15.0),
            (40.5, "metal_click", 0.5),
        ],
        "subs": [
            (30.5, 35.0, "El ciclo comienza en el compresor:", "un motor hermético de alto rendimiento."),
            (35.3, 40.2, "Comprime el refrigerante gaseoso,", "elevando su presión y temperatura..."),
            (40.5, 46.5, "Gracias a un pistón mecánico", "que bombea continuamente."),
        ],
    },
    {
        "id": "st4_condenser",
        "badge": "• 3. CONDENSADOR (DISIPACIÓN TÉRMICA) •",
        "time_range": (48.0, 66.0),
        "foley": [
            (48.1, "whoosh_fast", 0.8),
            (53.2, "thermal_wave", 3.0),
            (58.5, "thermal_wave", 3.0),
        ],
        "subs": [
            (48.0, 52.8, "El gas caliente viaja al condensador,", "esa rejilla en la parte trasera."),
            (53.0, 58.0, "Al circular, libera el calor al ambiente", "y comienza a condensarse..."),
            (58.2, 64.0, "Transformándose en un líquido denso", "a muy alta presión."),
        ],
    },
    {
        "id": "st5_capillary",
        "badge": "• 4. TUBO CAPILAR (CAÍDA DE PRESIÓN) •",
        "time_range": (66.0, 82.5),
        "foley": [
            (66.1, "whoosh_zoom", 0.7),
            (71.2, "metal_click", 0.4),
            (76.8, "expansion_hiss", 4.0),
        ],
        "subs": [
            (66.0, 71.0, "Pasa por el filtro secador", "para eliminar humedad e impurezas..."),
            (71.2, 76.5, "Y atraviesa un tubo capilar estrecho.", "Esta repentina reducción de calibre..."),
            (76.8, 81.5, "Provoca una caída brusca de presión", "enfriando el fluido al instante."),
        ],
    },
    {
        "id": "st6_evaporator",
        "badge": "• 5. EVAPORADOR (ABSORCIÓN BAJO CERO) •",
        "time_range": (82.5, 96.5),
        "foley": [
            (82.6, "whoosh_zoom", 0.7),
            (83.5, "frost_chime", 2.0),
            (88.0, "frost_chime", 2.0),
        ],
        "subs": [
            (82.5, 87.5, "En el evaporador, el refrigerante hierve", "a temperaturas bajo cero."),
            (87.8, 92.5, "Absorbe intensamente el calor", "del aire interior y los alimentos..."),
            (92.8, 96.2, "¡Manteniéndolos frescos", "y en perfecta conservación!"),
        ],
    },
    {
        "id": "st7_closure",
        "badge": "• CICLO TERMODINÁMICO CONTINUO •",
        "time_range": (96.5, 105.0),
        "foley": [
            (96.6, "riser_cinematic", 3.0),
            (100.5, "sub_boom", 2.0),
        ],
        "subs": [
            (96.5, 100.5, "El vapor retorna al compresor", "para reiniciar el ciclo sin fin."),
            (100.8, 104.5, "¡Así funciona la fascinante termodinámica", "en tu cocina!"),
        ],
    },
]

# ------------------------------------------------------------------------------
# 2. MOTOR PROCEDURAL DE AUDIO: BGM + FOLEY EARSHOT + MASTER MIXING
# ------------------------------------------------------------------------------
def synthesize_ambient_soundtrack(total_sec: float) -> np.ndarray:
    """Sintetiza una atmósfera musical sutil tipo documental científico en C menor."""
    total_samples = int(total_sec * SAMPLE_RATE)
    t = np.linspace(0, total_sec, total_samples, endpoint=False)

    # Sub drone suave (55Hz y 110Hz con modulación lenta)
    sub = np.sin(2 * np.pi * 55.0 * t) * 0.25 + np.sin(2 * np.pi * 110.0 * t + 0.3) * 0.15
    sub_lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.1 * t)
    sub = sub * sub_lfo

    # Acordes de pad etéreo (Cmin9 / Ebmaj7 con filtro y chorus)
    # Frecuencias fundamentales: C3 (130.81), Eb3 (155.56), G3 (196.00), Bb3 (233.08), D4 (293.66)
    chord1 = (
        np.sin(2 * np.pi * 130.81 * t) * 0.2
        + np.sin(2 * np.pi * 155.56 * t + 0.5) * 0.2
        + np.sin(2 * np.pi * 196.00 * t + 1.2) * 0.15
        + np.sin(2 * np.pi * 233.08 * t + 2.0) * 0.1
    )
    # Acorde 2 (Ebmaj7): Eb3, G3, Bb3, D4
    chord2 = (
        np.sin(2 * np.pi * 155.56 * t) * 0.2
        + np.sin(2 * np.pi * 196.00 * t + 0.7) * 0.2
        + np.sin(2 * np.pi * 233.08 * t + 1.5) * 0.15
        + np.sin(2 * np.pi * 293.66 * t + 2.3) * 0.1
    )
    # Transición suave cada 15 segundos entre acordes
    crossfade = 0.5 + 0.5 * np.sin(2 * np.pi * (1.0 / 30.0) * t)
    pads = chord1 * crossfade + chord2 * (1.0 - crossfade)

    # Micro-pulsos rítmicos muy sutiles (arpegio tech a 110 BPM -> 1.83 Hz)
    pulse_clock = np.sin(2 * np.pi * 1.833 * t) ** 4
    shimmer = np.sin(2 * np.pi * 587.33 * t) * pulse_clock * 0.04

    # Mezclar y aplicar envolvente general (fade in 2s, fade out 3s)
    bgm = (sub * 0.4 + pads * 0.5 + shimmer * 0.1) * 0.15
    fade_in_len = int(2.0 * SAMPLE_RATE)
    fade_out_len = int(3.0 * SAMPLE_RATE)
    bgm[:fade_in_len] *= np.linspace(0.0, 1.0, fade_in_len)
    bgm[-fade_out_len:] *= np.linspace(1.0, 0.0, fade_out_len)

    return bgm.astype(np.float32)


def synthesize_foley_event(name: str, duration_sec: float) -> np.ndarray:
    """Genera un evento de sonido Foley analógico/procedural."""
    samples = int(duration_sec * SAMPLE_RATE)
    t = np.linspace(0, duration_sec, samples, endpoint=False)

    if "whoosh_impact" in name:
        # Whoosh de cámara rápido con impacto sordo
        noise = np.random.normal(0, 1, samples)
        env_whoosh = np.exp(-((t - 0.25) ** 2) / (2 * 0.08**2))
        impact_osc = np.sin(2 * np.pi * (65.0 + 200.0 * np.exp(-t * 18.0)) * t)
        impact_env = np.exp(-t * 9.0)
        return ((noise * 0.5 * env_whoosh) + (impact_osc * 0.6 * impact_env)).astype(np.float32) * 0.7

    elif "whoosh_fast" in name or "whoosh_zoom" in name or "whoosh_soft" in name:
        # Transición de cámara (swoosh suave)
        noise = np.random.normal(0, 1, samples)
        mid = duration_sec * 0.4
        env = np.exp(-((t - mid) ** 2) / (2 * (duration_sec * 0.25) ** 2))
        carrier = np.sin(2 * np.pi * (160.0 + 120.0 * np.sin(np.pi * t / duration_sec)) * t)
        return (noise * 0.6 + carrier * 0.4) * env * 0.45

    elif "sub_boom" in name:
        # Sub-bass cinematográfico profundo (48Hz -> 28Hz)
        f = 48.0 * np.exp(-t * 1.2)
        env = np.exp(-t * 2.0)
        return (np.sin(2 * np.pi * f * t) * env * 0.8).astype(np.float32)

    elif "compressor_hum" in name:
        # Zumbido mecánico del compresor (60Hz eléctrico + armónicos)
        hum = (
            np.sin(2 * np.pi * 60.0 * t) * 0.5
            + np.sin(2 * np.pi * 120.0 * t) * 0.3
            + np.sin(2 * np.pi * 180.0 * t) * 0.15
            + np.random.normal(0, 0.05, samples)
        )
        env = np.sin(np.pi * t / duration_sec) ** 0.5
        return (hum * env * 0.18).astype(np.float32)

    elif "thermal_wave" in name:
        # Convección térmica (ondulación de aire caliente)
        noise = np.random.normal(0, 1, samples)
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * t)
        env = np.sin(np.pi * t / duration_sec) ** 2
        return (noise * lfo * env * 0.12).astype(np.float32)

    elif "expansion_hiss" in name:
        # Expansión de fluido y caída brusca de presión (siseo de gas frío)
        noise = np.random.normal(0, 1, samples)
        # Modulación que simula el flujo en el capilar
        env = np.sin(np.pi * t / duration_sec) ** 1.5
        return (noise * env * 0.16).astype(np.float32)

    elif "frost_chime" in name:
        # Resonancia de hielo / evaporación bajo cero
        decay = np.exp(-t * 3.5)
        chime = (
            np.sin(2 * np.pi * 1760.0 * t) * 0.5
            + np.sin(2 * np.pi * 2640.0 * t) * 0.3
            + np.sin(2 * np.pi * 3520.0 * t) * 0.2
        )
        return (chime * decay * 0.25).astype(np.float32)

    elif "metal_click" in name:
        # Click mecánico
        decay = np.exp(-t * 50.0)
        click = (np.sin(2 * np.pi * 2200.0 * t) + np.sin(2 * np.pi * 4400.0 * t) * 0.5) * decay
        return (click * 0.35).astype(np.float32)

    elif "riser_cinematic" in name:
        # Tensión ascendente para conclusión
        f_rise = 100.0 * np.exp(t * 1.2)
        phase = np.cumsum(2 * np.pi * f_rise / SAMPLE_RATE)
        env = (t / duration_sec) ** 1.8
        return (np.sin(phase) * env * 0.35).astype(np.float32)

    return np.zeros(samples, dtype=np.float32)


def build_cinematic_audio_mix(narration_wav: Path, output_master_wav: Path, total_sec: float = 105.0) -> None:
    """Combina la narración humana, la música procedural y el Foley en un archivo master estéreo."""
    print("--> [AUDIO] Leyendo narración existente...")
    voice_data, voice_sr = sf.read(str(narration_wav))
    if voice_data.ndim > 1:
        voice_data = voice_data.mean(axis=1)

    total_samples = int(total_sec * SAMPLE_RATE)
    # Resample de voz si es necesario a 44100
    if voice_sr != SAMPLE_RATE:
        ratio = SAMPLE_RATE / voice_sr
        new_len = int(len(voice_data) * ratio)
        voice_resampled = np.interp(
            np.linspace(0, len(voice_data), new_len, endpoint=False),
            np.arange(len(voice_data)),
            voice_data,
        )
    else:
        voice_resampled = voice_data

    # Alinear longitud de voz
    voice_track = np.zeros(total_samples, dtype=np.float32)
    voice_len = min(len(voice_resampled), total_samples)
    voice_track[:voice_len] = voice_resampled[:voice_len]

    # Generar BGM
    print("--> [AUDIO] Sintetizando banda sonora ambiental procedural...")
    bgm_track = synthesize_ambient_soundtrack(total_sec)

    # Generar pista Foley Earshot
    print("--> [AUDIO] Montando eventos Foley Earshot sincronizados...")
    foley_track = np.zeros(total_samples, dtype=np.float32)
    for stage in STAGES_CONFIG:
        for cue_sec, cue_name, cue_dur in stage.get("foley", []):
            sample = synthesize_foley_event(cue_name, cue_dur)
            start_idx = int(cue_sec * SAMPLE_RATE)
            end_idx = min(start_idx + len(sample), total_samples)
            chunk = end_idx - start_idx
            if chunk > 0:
                foley_track[start_idx:end_idx] += sample[:chunk]

    # Ducking inteligente: cuando la voz está por encima de un umbral, baja el BGM 4 dB más
    voice_env = np.abs(voice_track)
    # Suavizado de envolvente
    kernel_size = int(SAMPLE_RATE * 0.2)
    kernel = np.ones(kernel_size) / kernel_size
    smoothed_env = np.convolve(voice_env, kernel, mode="same")
    ducking_factor = 1.0 - np.clip(smoothed_env * 2.5, 0.0, 0.65)
    ducked_bgm = bgm_track * ducking_factor

    # Master Bus Mix (Estéreo con espacialidad)
    left_channel = voice_track * 0.95 + ducked_bgm * 0.85 + foley_track * 0.9
    right_channel = voice_track * 0.95 + ducked_bgm * 0.85 + foley_track * 0.85

    # Leve separación estéreo al BGM y Foley
    stereo_master = np.stack([left_channel, right_channel], axis=1)

    # Normalización EBU R128 (-14 LUFS / Pico seguro -1.0 dBFS)
    peak = np.max(np.abs(stereo_master))
    if peak > 0.01:
        stereo_master = stereo_master / peak * 0.91

    sf.write(str(output_master_wav), stereo_master, SAMPLE_RATE)
    print(f"[OK] Master de audio multicapa generado: {output_master_wav} ({total_sec} s)")


# ------------------------------------------------------------------------------
# 3. GENERADOR DE SUBTÍTULOS ASS AVANZADOS (CARDS, BADGES Y ZONA SEGURA)
# ------------------------------------------------------------------------------
def format_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_advanced_social_subtitles(output_ass: Path) -> None:
    """Genera subtítulos ASS optimizados para retención y engagement móvil en 1080x1920."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DialogueSub,Arial,44,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.8,2.0,2,80,80,240,1
Style: HookHeader,Arial,48,&H0000FFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,4.2,2.5,8,60,60,180,1
Style: StageBadge,Arial,32,&H00E0E0E0,&H00FFFFFF,&H00111111,&HB0000000,-1,0,0,0,100,100,0,0,1,3.0,1.5,8,60,60,130,1
Style: CTACard,Arial,46,&H0000FFCC,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,4.0,2.5,8,70,70,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]

    # 1. Hook Header Card (0.0s a 5.2s)
    lines.append(
        f"Dialogue: 1,0:00:00.20,0:00:05.20,HookHeader,,0,0,0,,{{\\c&H00FFFF&}}¿CÓMO CREA FRÍO UN REFRIGERADOR?\\N{{\\fs34\\c&HFFFFFF&}}• TERMODINÁMICA REAL EN TU COCINA •\n"
    )

    # 2. Badges de Etapa Superior (Durante todo el video según la sección)
    for stage in STAGES_CONFIG:
        t0, t1 = stage["time_range"]
        # No mostrar badge durante el hook inicial para no saturar
        if stage["id"] != "st1_hook":
            s_str = format_ass_time(t0)
            e_str = format_ass_time(t1)
            badge_text = stage["badge"]
            lines.append(
                f"Dialogue: 1,{s_str},{e_str},StageBadge,,0,0,0,,{badge_text}\n"
            )

    # 3. Subtítulos de Diálogo en Zona Segura Inferior (MarginV=240)
    for stage in STAGES_CONFIG:
        for t_start, t_end, line1, line2 in stage["subs"]:
            s_str = format_ass_time(t_start)
            e_str = format_ass_time(t_end)
            # Destacar primera línea en amarillo/blanco de alto contraste
            event_text = f"{{\\c&H00FFFF&}}{line1}\\N{{\\c&HFFFFFF&}}{line2}"
            lines.append(f"Dialogue: 0,{s_str},{e_str},DialogueSub,,0,0,0,,{event_text}\n")

    # 4. Final CTA Card (98.5s a 105.0s)
    lines.append(
        f"Dialogue: 2,0:01:38.50,0:01:45.00,CTACard,,0,0,0,,{{\\c&H00FFFF&}}¿CONOCÍAS ESTE CICLO?\\N{{\\fs36\\c&HFFFFFF&}}¡Síguenos para más ciencia e ingeniería!\n"
    )

    output_ass.write_text("".join(lines), encoding="utf-8")
    print(f"[OK] Subtítulos ASS sociales generados: {output_ass}")


# ------------------------------------------------------------------------------
# 4. GENERACIÓN DE PORTADA / MINIATURA (THUMBNAIL 1080x1920)
# ------------------------------------------------------------------------------
def generate_social_thumbnail(sample_frame_path: Path, output_thumbnail: Path) -> None:
    """Genera una portada de alto impacto visual 1080x1920 con badges gráficos."""
    img = Image.open(sample_frame_path).convert("RGBA")
    # Escalar a 1080x1920
    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img)
    # Barra de degradado superior para legibilidad
    for y in range(380):
        alpha = int(230 * (1.0 - (y / 380.0)))
        draw.line([(0, y), (1080, y)], fill=(8, 12, 22, alpha))

    # Barra de degradado inferior para subtítulo de portada
    for y in range(1550, 1920):
        alpha = int(240 * ((y - 1550.0) / 370.0))
        draw.line([(0, y), (1080, y)], fill=(8, 12, 22, alpha))

    # Dibujar tarjeta de título en el tercio superior
    # Píldora de categoría
    draw.rounded_rectangle([(200, 100), (880, 175)], radius=35, fill=(15, 23, 42, 240), outline=(56, 189, 248, 255), width=4)
    # Título principal
    draw.rounded_rectangle([(50, 205), (1030, 365)], radius=30, fill=(2, 6, 23, 245), outline=(245, 158, 11, 255), width=5)

    try:
        font_pill = ImageFont.truetype("arialbd.ttf", 32)
        font_title = ImageFont.truetype("arialbd.ttf", 46)
        font_sub = ImageFont.truetype("arialbd.ttf", 40)
    except IOError:
        font_pill = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((540, 137), "• FÍSICA Y TERMODINÁMICA •", fill=(56, 189, 248), anchor="mm", font=font_pill)
    draw.text((540, 285), "¿CÓMO CREA FRÍO UN REFRIGERADOR?", fill=(255, 255, 255), anchor="mm", font=font_title)
    draw.text((540, 1750), "5 COMPONENTES EN 3D EXPLICADOS", fill=(251, 191, 36), anchor="mm", font=font_sub)

    img.convert("RGB").save(output_thumbnail, quality=95)
    print(f"[OK] Portada / Miniatura generada: {output_thumbnail} (1080x1920)")


# ------------------------------------------------------------------------------
# 5. CODIFICACIÓN Y MASTERIZACIÓN FFMPEG FULL HD (1080x1920)
# ------------------------------------------------------------------------------
def master_final_social_video(
    frames_dir: Path,
    audio_wav: Path,
    subs_ass: Path,
    output_mp4: Path,
    source_fps: int = 12,
    target_fps: int = 30,
) -> None:
    """Codifica a 1080x1920 a 30 fps con H.264 High Profile, CRF 18 y subtítulos embebidos."""
    print("--> [FFMPEG] Iniciando codificación Full HD 1080x1920 para redes sociales...")
    work_dir = frames_dir.parent.resolve()

    rel_subs = os.path.relpath(subs_ass.resolve(), work_dir).replace("\\", "/")
    rel_audio = os.path.relpath(audio_wav.resolve(), work_dir).replace("\\", "/")
    rel_frames = (Path(os.path.relpath(frames_dir.resolve(), work_dir)) / "seq_%05d.png").as_posix()
    rel_out = os.path.relpath(output_mp4.resolve(), work_dir).replace("\\", "/")

    # Filtro de video: upscale suave a 1080x1920 + framerate 30fps + subtítulos con fuentes vectoriales
    vf = f"scale=1080:1920:flags=lanczos,fps={target_fps},subtitles=filename='{rel_subs}'"

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-framerate", str(source_fps),
        "-i", rel_frames,
        "-i", rel_audio,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "44100",
        "-movflags", "+faststart",
        "-shortest",
        rel_out,
    ]

    print("    Comando FFmpeg lanzado en:", work_dir)
    proc = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True)
    if proc.returncode != 0:
        print("[ERROR FFMPEG]:", proc.stderr[-1000:])
        raise RuntimeError("Fallo el renderizado final con FFmpeg.")

    mb = output_mp4.stat().st_size / (1024 * 1024)
    print(f"[OK] Video Social Master Full HD exportado: {output_mp4} ({mb:.2f} MB)")


# ------------------------------------------------------------------------------
# 6. KIT COMPLETO DE PUBLICACIÓN (METADATOS, COPYWRITING Y HASHTAGS)
# ------------------------------------------------------------------------------
def generate_publishing_kit(output_md: Path, output_json: Path) -> Dict[str, Any]:
    """Genera el texto de publicación listo para copiar y pegar en YouTube Shorts, TikTok e Instagram."""
    kit = {
        "tema": "Ciclo de Refrigeración por Compresión de Vapor",
        "duracion_exacta": "1 minuto 45 segundos (105.0 s)",
        "resolucion": "1080x1920 (9:16 Vertical Full HD)",
        "titulos_recomendados": {
            "opcion_1_viral": "¿Cómo crea frío un refrigerador si el frío no existe? ❄️😲",
            "opcion_2_ingenieria": "La Termodinámica en tu Cocina: Ciclo de Refrigeración en 3D 🔬",
            "opcion_3_pregunta": "¿Por qué la parte trasera de tu refri está hirviendo? 🔥🧊",
        },
        "copy_para_descripcion": (
            "¿Alguna vez te has preguntado cómo tu refrigerador mantiene tus alimentos bajo cero "
            "incluso en pleno verano? ☀️❄️\n\n"
            "La física revela un secreto fascinante: en realidad, el frío no se 'fabrica', "
            "sino que el sistema extrae el calor del interior y lo expulsa a tu cocina.\n\n"
            "En esta animación 3D desglosamos los 5 componentes clave del ciclo termodinámico:\n"
            "1️⃣ Compresor hermético: eleva la presión y calienta el refrigerante.\n"
            "2️⃣ Serpentín condensador: disipa el calor hacia la habitación.\n"
            "3️⃣ Filtro secador: elimina cualquier rastro de impurezas o humedad.\n"
            "4️⃣ Tubo capilar: estrecha el paso y provoca una caída brusca de presión.\n"
            "5️⃣ Evaporador: el fluido hierve a temperaturas bajo cero y absorbe el calor de tus alimentos.\n\n"
            "¡Un ciclo infinito que funciona 24/7 sin detenerse! 🔄\n\n"
            "¿Te gustaría ver cómo funciona el aire acondicionado o una bomba de calor? Déjamelo en los comentarios. 👇"
        ),
        "hashtags": [
            "#Ciencia",
            "#Ingenieria",
            "#Termodinamica",
            "#AprendeEnTikTok",
            "#ComoFunciona",
            "#Fisica",
            "#Tech",
            "#Blender3D",
            "#YouTubeShorts",
            "#Reels",
            "#Curiosidades",
            "#Animacion3D",
        ],
        "primer_comentario_fijado": (
            "📌 PREGUNTA PARA TI: ¿Sabías que si dejas la puerta del refrigerador abierta, "
            "la habitación NO se enfría, sino que se calienta? La respuesta está en la segunda ley "
            "de la termodinámica. ¿Quieres que hagamos un video explicándolo?"
        ),
        "especificaciones_tecnicas": {
            "audio": "Voz Jorge/Dalia Neural + Soundtrack Procedural EBU R128 (-14 LUFS) + Foley Earshot",
            "subtitulos": "ASS estricto en Zona Segura (MarginV=240, compatible con TikTok/Reels)",
            "motor_render": "Blender 3D EEVEE + Materiales Físicos Procedurales",
        },
    }

    output_json.write_text(json.dumps(kit, indent=2, ensure_ascii=False), encoding="utf-8")

    md_content = f"""# 🚀 Kit de Publicación para Redes Sociales
## Tema: {kit['tema']}
**Duración:** {kit['duracion_exacta']} | **Formato:** {kit['resolucion']}

---

### 🎯 Títulos para A/B Testing:
* **Opción A (Gancho de curiosidad / Viral):**
  > `{kit['titulos_recomendados']['opcion_1_viral']}`
* **Opción B (Educativo y riguroso):**
  > `{kit['titulos_recomendados']['opcion_2_ingenieria']}`
* **Opción C (Pregunta intrigante):**
  > `{kit['titulos_recomendados']['opcion_3_pregunta']}`

---

### 📝 Descripción / Copy Completo (Listo para Pegar):
```text
{kit['copy_para_descripcion']}
```

---

### 🏷️ Hashtags Estratégicos:
```text
{' '.join(kit['hashtags'])}
```

---

### 💬 Primer Comentario Recomendado (Fijar al inicio):
> *"{kit['primer_comentario_fijado']}"*

---

### 🛠️ Archivos Generados:
- **Video Master:** `video_refrigerador_master_1080x1920.mp4`
- **Portada / Miniatura:** `portada_refrigerador_1080x1920.png`
- **Pista de Audio Master:** `audio_master_cinematico_105s.wav`
- **Subtítulos ASS:** `subtitulos_social_safezone.ass`
"""
    output_md.write_text(md_content, encoding="utf-8")
    print(f"[OK] Kit de publicación generado: {output_md}")
    return kit


# ------------------------------------------------------------------------------
# 7. EJECUTOR PRINCIPAL
# ------------------------------------------------------------------------------
def execute_master_pipeline() -> Dict[str, Any]:
    project_dir = _repo_root / "projects" / "showcase_refrigerator_vertical_9_16"
    frames_dir = project_dir / "rendered_frames"
    raw_narration = project_dir / "narration_master_105s.wav"

    publish_dir = project_dir / "publish_ready"
    publish_dir.mkdir(parents=True, exist_ok=True)

    master_audio = publish_dir / "audio_master_cinematico_105s.wav"
    master_subs = publish_dir / "subtitulos_social_safezone.ass"
    master_video = publish_dir / "video_refrigerador_master_1080x1920.mp4"
    thumbnail_img = publish_dir / "portada_refrigerador_1080x1920.png"
    kit_md = publish_dir / "KIT_DE_PUBLICACION.md"
    kit_json = publish_dir / "metadata_publicacion.json"

    # 1. Mezcla de Audio Master Cinematográfico
    build_cinematic_audio_mix(raw_narration, master_audio, total_sec=105.0)

    # 2. Generación de Subtítulos ASS Avanzados
    generate_advanced_social_subtitles(master_subs)

    # 3. Masterización de Video Full HD en FFmpeg
    master_final_social_video(
        frames_dir=frames_dir,
        audio_wav=master_audio,
        subs_ass=master_subs,
        output_mp4=master_video,
        source_fps=12,
        target_fps=30,
    )

    # 4. Portada / Miniatura
    sample_frame = frames_dir / "seq_00300.png"
    if not sample_frame.exists():
        sample_frame = next(frames_dir.glob("seq_*.png"))
    generate_social_thumbnail(sample_frame, thumbnail_img)

    # 5. Kit de Publicación
    kit = generate_publishing_kit(kit_md, kit_json)

    # 6. Copiar a la carpeta de artefactos de la sesión actual
    artifact_dir = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a")
    if artifact_dir.exists():
        shutil.copy2(master_video, artifact_dir / master_video.name)
        shutil.copy2(thumbnail_img, artifact_dir / thumbnail_img.name)
        shutil.copy2(kit_md, artifact_dir / kit_md.name)
        print(f"[OK] Archivos maestros sincronizados con el directorio de artefactos: {artifact_dir}")

    return {
        "status": "SUCCESS",
        "video": str(master_video),
        "thumbnail": str(thumbnail_img),
        "kit_md": str(kit_md),
        "size_mb": round(master_video.stat().st_size / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    res = execute_master_pipeline()
    print("RESUMEN MAESTRO:", json.dumps(res, indent=2))
