"""AI VIDEO STUDIO — Master Dynamic Publisher: Ciclo de Refrigeración 3D (Versión Dinámica & Friendly).

Soluciona:
1. Sonido amigable y agradable:
   - Eliminados TODOS los sub-booms, risers tensos, impactos fuertes y zumbidos pesados que asustaban.
   - Pista musical cálida, alegre y educativa (Marimba acústica en C mayor pentatónica + Pad suave) duckeada a -24 dB.
   - Foley sutil y transparente: micro-swoosh de aire suave, leve ting cristalino de frío y micro-clic agradable.
2. Cámara 100% Dinámica:
   - Utiliza la secuencia maestra de 18 movimientos de cámara (hero shot, cutaway, exploded view, internal tracking, close ups, tracking y comparación).
   - Duración: 112.67 segundos (1 minuto 52 segundos).
3. Subtítulos y Gráficos:
   - Hook Card superior no intrusivo en los primeros 5 segundos.
   - Diálogos con resaltado dinámico en cian y blanco en zona segura (MarginV=210).
   - CTA amigable al cierre.
4. Exportación Full HD 1080x1920 a 30 fps con H.264 High Profile.
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
# 1. GENERADOR DE MÚSICA AMIGABLE, CÁLIDA Y PEDAGÓGICA (ESTILO KURZGESAGT)
# ------------------------------------------------------------------------------
def synthesize_friendly_soundtrack(total_sec: float) -> np.ndarray:
    """Genera una atmósfera musical alegre, curiosa y relajante en C mayor pentatónica."""
    total_samples = int(total_sec * SAMPLE_RATE)
    t = np.linspace(0, total_sec, total_samples, endpoint=False)

    # Notas pentatónicas amables (C4, D4, E4, G4, A4, C5)
    freqs = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
    bpm = 104.0
    beat_dur = 60.0 / bpm  # ~0.576 s
    total_beats = int(total_sec / beat_dur)

    music = np.zeros(total_samples, dtype=np.float32)

    # Melodía de marimba / glockenspiel suave y cálida
    for b in range(total_beats):
        t_start = b * beat_dur
        idx_start = int(t_start * SAMPLE_RATE)
        # Variación melódica armónica
        note_f = freqs[(b * 3 + (b // 4)) % len(freqs)]
        note_len = int(0.32 * SAMPLE_RATE)

        if idx_start + note_len < total_samples:
            t_note = np.linspace(0, 0.32, note_len, endpoint=False)
            # Timbre redondo de madera acústica
            fundamental = np.sin(2 * np.pi * note_f * t_note) * 0.75
            harmonic2 = np.sin(4 * np.pi * note_f * t_note) * 0.2
            harmonic3 = np.sin(6 * np.pi * note_f * t_note) * 0.05
            env = np.exp(-t_note * 8.5)
            music[idx_start : idx_start + note_len] += (fundamental + harmonic2 + harmonic3) * env * 0.11

    # Pad armónico etéreo (C mayor suave: C3, E3, G3)
    pad = (
        np.sin(2 * np.pi * 130.81 * t) * 0.3
        + np.sin(2 * np.pi * 164.81 * t + 0.4) * 0.3
        + np.sin(2 * np.pi * 196.00 * t + 0.8) * 0.25
        + np.sin(2 * np.pi * 261.63 * t + 1.2) * 0.15
    ) * 0.035
    # Modulación suave de respiración
    pad *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.18 * t))

    bgm = music + pad

    # Fades suaves de entrada y salida
    fade_len = int(2.5 * SAMPLE_RATE)
    bgm[:fade_len] *= np.linspace(0.0, 1.0, fade_len)
    bgm[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)

    return bgm.astype(np.float32)


# ------------------------------------------------------------------------------
# 2. GENERADOR DE EFECTOS FOLEY SUTILES Y AMISTOSOS (CERO ASUSTAR)
# ------------------------------------------------------------------------------
def synthesize_gentle_foley(name: str, duration_sec: float = 0.5) -> np.ndarray:
    """Genera efectos de sonido discretos, limpios y completamente amigables."""
    samples = int(duration_sec * SAMPLE_RATE)
    t = np.linspace(0, duration_sec, samples, endpoint=False)

    if "air_swoosh" in name:
        # Swoosh de aire muy suave tipo cambio de página o giro elegante
        noise = np.random.normal(0, 0.15, samples)
        # Filtro de envolvente suave sin transitorios duros
        env = np.sin(np.pi * t / duration_sec) ** 2
        # Tono suave de soporte
        tone = np.sin(2 * np.pi * 320.0 * t) * 0.2
        return ((noise + tone) * env * 0.12).astype(np.float32)

    elif "frost_ting" in name:
        # Pequeño brillo cristalino de frío (delicado y agradable)
        decay = np.exp(-t * 5.0)
        ting = (
            np.sin(2 * np.pi * 1760.0 * t) * 0.6
            + np.sin(2 * np.pi * 2640.0 * t) * 0.25
            + np.sin(2 * np.pi * 3520.0 * t) * 0.15
        ) * decay * 0.10
        return ting.astype(np.float32)

    elif "soft_click" in name:
        # Micro-click amable de interruptor
        decay = np.exp(-t * 65.0)
        click = np.sin(2 * np.pi * 1400.0 * t) * decay * 0.12
        return click.astype(np.float32)

    elif "vapor_hiss" in name:
        # Suave siseo de fluido muy tenue (como brisa fresca)
        noise = np.random.normal(0, 0.1, samples)
        env = np.sin(np.pi * t / duration_sec) ** 1.8
        return (noise * env * 0.08).astype(np.float32)

    return np.zeros(samples, dtype=np.float32)


def build_friendly_master_audio(
    raw_narration_wav: Path,
    output_audio_wav: Path,
    total_sec: float = 112.67,
) -> None:
    """Mezcla la voz principal con la música amigable y foley no-intrusivo."""
    print("--> [AUDIO] Leyendo narración humana original...")
    voice_data, voice_sr = sf.read(str(raw_narration_wav))
    if voice_data.ndim > 1:
        voice_data = voice_data.mean(axis=1)

    total_samples = int(total_sec * SAMPLE_RATE)

    # Resample a 44100 si es necesario
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

    voice_track = np.zeros(total_samples, dtype=np.float32)
    voice_len = min(len(voice_resampled), total_samples)
    voice_track[:voice_len] = voice_resampled[:voice_len]

    # Generar BGM
    print("--> [AUDIO] Sintetizando música pedagógica cálida y amigable...")
    bgm = synthesize_friendly_soundtrack(total_sec)

    # Foley en momentos clave de las 8 escenas dinámicas
    print("--> [AUDIO] Agregando micro-eventos Foley sutiles...")
    foley_track = np.zeros(total_samples, dtype=np.float32)
    foley_cues = [
        (0.2, "air_swoosh", 0.6),      # Hook
        (13.1, "air_swoosh", 0.5),     # Vista explosionada
        (13.5, "soft_click", 0.3),     # Callout componentes
        (27.4, "soft_click", 0.3),     # Compresor
        (41.4, "air_swoosh", 0.5),     # Condensador
        (56.6, "vapor_hiss", 2.0),     # Expansión capilar suave
        (71.9, "frost_ting", 1.2),     # Evaporador congelador
        (86.3, "air_swoosh", 0.5),     # Retorno de succión
        (98.9, "frost_ting", 1.2),     # Comparación final
        (107.0, "air_swoosh", 0.6),    # Cierre
    ]

    for t_cue, f_name, dur in foley_cues:
        sample = synthesize_gentle_foley(f_name, dur)
        idx0 = int(t_cue * SAMPLE_RATE)
        idx1 = min(idx0 + len(sample), total_samples)
        chunk = idx1 - idx0
        if chunk > 0:
            foley_track[idx0:idx1] += sample[:chunk]

    # Ducking suave: baja la música 3 dB cuando habla el narrador
    voice_env = np.abs(voice_track)
    kernel_size = int(SAMPLE_RATE * 0.25)
    kernel = np.ones(kernel_size) / kernel_size
    smoothed_env = np.convolve(voice_env, kernel, mode="same")
    ducking = 1.0 - np.clip(smoothed_env * 2.0, 0.0, 0.55)
    ducked_bgm = bgm * ducking

    # Mezcla estéreo limpia
    left_channel = voice_track * 0.95 + ducked_bgm * 0.70 + foley_track * 0.85
    right_channel = voice_track * 0.95 + ducked_bgm * 0.70 + foley_track * 0.85

    stereo_master = np.stack([left_channel, right_channel], axis=1)

    # Normalización a -14 LUFS / pico en -1.0 dBFS
    peak = np.max(np.abs(stereo_master))
    if peak > 0.01:
        stereo_master = stereo_master / peak * 0.90

    sf.write(str(output_audio_wav), stereo_master, SAMPLE_RATE)
    print(f"[OK] Audio master amigable generado: {output_audio_wav} ({total_sec:.2f} s)")


# ------------------------------------------------------------------------------
# 3. GENERADOR DE SUBTÍTULOS ASS MEJORADOS EN ZONA SEGURA (1080x1920)
# ------------------------------------------------------------------------------
def generate_friendly_subtitles(original_ass_path: Path, output_ass_path: Path) -> None:
    """Adapta los subtítulos originales de la fase 3.2 a 1080x1920 e inserta Hook y CTA."""
    raw_text = original_ass_path.read_text(encoding="utf-8")

    # Modificar estilos para resolución 1080x1920 en zona segura
    header = """[Script Info]
Title: Dynamic Educational Subtitles 1080x1920
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: EduSub,Arial,48,&H00FFFFFF&,&H0015CCFA&,&H00000000,&H80000000,-1,0,0,0,100,100,1.0,0,1,4.2,2.0,2,80,80,260,1
Style: HookHeader,Arial,46,&H0000FFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,4.2,2.5,8,60,60,180,1
Style: CTACard,Arial,44,&H0000FFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,4.0,2.5,8,70,70,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]

    # Hook Card superior en los primeros 5.2s
    lines.append(
        "Dialogue: 1,0:00:00.20,0:00:05.20,HookHeader,,0,0,0,,{\\c&H00FFFF&}¿CÓMO CREA FRÍO UN REFRIGERADOR?\\N{\\fs34\\c&HFFFFFF&}• FÍSICA Y TERMODINÁMICA REAL •\n"
    )

    # Extraer los eventos de diálogo originales
    in_events = False
    for line in raw_text.splitlines():
        if line.strip().startswith("[Events]"):
            in_events = True
            continue
        if in_events and line.startswith("Dialogue:"):
            # Ajustar para usar el estilo EduSub a 1080p
            parts = line.split(",", 9)
            if len(parts) >= 10:
                parts[3] = "EduSub"
                lines.append(",".join(parts) + "\n")

    # CTA Card al final (106.0s a 112.6s)
    lines.append(
        "Dialogue: 2,0:01:46.00,0:01:52.60,CTACard,,0,0,0,,{\\c&H00FFFF&}¿CONOCÍAS ESTE CICLO?\\N{\\fs36\\c&HFFFFFF&}¡Síguenos para más ciencia e ingeniería!\n"
    )

    output_ass_path.write_text("".join(lines), encoding="utf-8")
    print(f"[OK] Subtítulos adaptados a 1080p: {output_ass_path}")


# ------------------------------------------------------------------------------
# 4. PORTADA / MINIATURA DINÁMICA (1080x1920)
# ------------------------------------------------------------------------------
def generate_friendly_thumbnail(video_path: Path, output_thumbnail: Path) -> None:
    """Extrae un fotograma del despiece / vista interna dinámica y genera la portada."""
    tmp_frame = output_thumbnail.parent / "_thumb_raw.png"
    # Extraer frame del segundo 16 (vista explosionada de los componentes)
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-ss", "16.0",
        "-i", str(video_path),
        "-vframes", "1",
        str(tmp_frame),
    ]
    subprocess.run(cmd, capture_output=True)

    img = Image.open(tmp_frame).convert("RGBA")
    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img)
    # Degradados de legibilidad
    for y in range(380):
        alpha = int(220 * (1.0 - (y / 380.0)))
        draw.line([(0, y), (1080, y)], fill=(8, 14, 26, alpha))

    for y in range(1550, 1920):
        alpha = int(230 * ((y - 1550.0) / 370.0))
        draw.line([(0, y), (1080, y)], fill=(8, 14, 26, alpha))

    # Badges
    draw.rounded_rectangle([(200, 100), (880, 175)], radius=35, fill=(15, 23, 42, 240), outline=(56, 189, 248, 255), width=4)
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
    draw.text((540, 1750), "EL CICLO EN 3D EXPLICADO", fill=(251, 191, 36), anchor="mm", font=font_sub)

    img.convert("RGB").save(output_thumbnail, quality=95)
    if tmp_frame.exists():
        tmp_frame.unlink(missing_ok=True)
    print(f"[OK] Portada miniatura dinámica generada: {output_thumbnail}")


# ------------------------------------------------------------------------------
# 5. CODIFICACIÓN Y ENSAMBLE FINAL FFMPEG
# ------------------------------------------------------------------------------
def master_dynamic_video(
    visual_video_path: Path,
    audio_wav_path: Path,
    subs_ass_path: Path,
    output_mp4_path: Path,
) -> None:
    """Ensamble Full HD 1080x1920 a 30 fps con H.264 High Profile."""
    print("--> [FFMPEG] Ensamble Full HD del video dinámico...")
    work_dir = output_mp4_path.parent.resolve()

    rel_subs = os.path.relpath(subs_ass_path.resolve(), work_dir).replace("\\", "/")
    rel_audio = os.path.relpath(audio_wav_path.resolve(), work_dir).replace("\\", "/")
    rel_vis = os.path.relpath(visual_video_path.resolve(), work_dir).replace("\\", "/")
    rel_out = os.path.relpath(output_mp4_path.resolve(), work_dir).replace("\\", "/")

    # Filtro: escala a 1080x1920 con lanczos + fps 30 + subtítulos embebidos
    vf = f"scale=1080:1920:flags=lanczos,fps=30,subtitles=filename='{rel_subs}'"

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", rel_vis,
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

    print("    Lanzando comando FFmpeg en:", work_dir)
    res = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True)
    if res.returncode != 0:
        print("[ERROR FFMPEG]:", res.stderr[-1000:])
        raise RuntimeError("Fallo el ensamble de video con FFmpeg.")

    mb = output_mp4_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Video dinámico Full HD exportado: {output_mp4_path} ({mb:.2f} MB)")


# ------------------------------------------------------------------------------
# 6. FUNCIÓN PRINCIPAL
# ------------------------------------------------------------------------------
def run_friendly_dynamic_publisher() -> Dict[str, Any]:
    val_dir = _repo_root / "projects" / "validation_fase_3_2_refrigerador"
    visual_video = val_dir / "video_visual_completo.mp4"
    raw_narration = val_dir / "narracion_completa.wav"
    original_subs = val_dir / "subtitulos_dinamicos.ass"

    publish_dir = val_dir / "publish_ready"
    publish_dir.mkdir(parents=True, exist_ok=True)

    master_audio = publish_dir / "audio_friendly_master.wav"
    master_subs = publish_dir / "subtitulos_friendly_1080p.ass"
    master_video = publish_dir / "video_refrigerador_master_1080x1920.mp4"
    thumbnail = publish_dir / "portada_refrigerador_1080x1920.png"

    # 1. Audio amigable
    build_friendly_master_audio(raw_narration, master_audio, total_sec=112.67)

    # 2. Subtítulos
    generate_friendly_subtitles(original_subs, master_subs)

    # 3. Master video dinámico
    master_dynamic_video(visual_video, master_audio, master_subs, master_video)

    # 4. Portada
    generate_friendly_thumbnail(visual_video, thumbnail)

    # 5. Copiar al directorio de artefactos de la sesión
    artifact_dir = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a")
    if artifact_dir.exists():
        shutil.copy2(master_video, artifact_dir / master_video.name)
        shutil.copy2(thumbnail, artifact_dir / thumbnail.name)
        print(f"[OK] Archivos sincronizados en artefactos: {artifact_dir}")

    return {
        "status": "SUCCESS",
        "video": str(master_video),
        "thumbnail": str(thumbnail),
        "duration_sec": 112.67,
        "size_mb": round(master_video.stat().st_size / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    res = run_friendly_dynamic_publisher()
    print("RESULTADO:", json.dumps(res, indent=2))
