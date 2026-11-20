"""AI VIDEO STUDIO — Orquestador de Renderizado y Ensamble Completo.
Tema: Circuito de Refrigeración por Compresión de Vapor (Showcase Vertical 9:16).

Flujo unificado:
1. Síntesis de narración continua por etapas con Edge-TTS (es-MX-JorgeNeural).
2. Generación de subtítulos dinámicos ASS posicionados estrictamente dentro de la Zona Segura (MarginV=300).
3. Renderizado de la animación vertical 9:16 en Blender con EEVEE.
4. Muxing y codificación final con FFmpeg a H.264 / AAC.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import imageio_ffmpeg
import numpy as np
import soundfile as sf

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# ------------------------------------------------------------------------------
# 1. GUION PEDAGÓGICO DE 7 ETAPAS SINCRONIZADAS (105 Segundos)
# ------------------------------------------------------------------------------
SCRIPT_STAGES = [
    {
        "stage_id": "st1_hook",
        "name": "1. Hook & Intro",
        "start_sec": 0.5,
        "rate": "+4%",
        "text": "¿Alguna vez te has preguntado cómo un refrigerador crea frío en su interior en pleno día caluroso? La respuesta científica es sorprendente: en realidad, un refrigerador no genera frío, sino que extrae el calor y lo expulsa hacia el exterior.",
        "subs": [
            (0.5, 4.2, "¿Cómo crea frío un refrigerador", "en pleno día caluroso?"),
            (4.5, 8.8, "La respuesta científica es sorprendente:", "en realidad no genera frío..."),
            (9.0, 14.2, "¡Sino que extrae el calor", "y lo expulsa hacia el exterior!"),
        ],
    },
    {
        "stage_id": "st2_architecture",
        "name": "2. Arquitectura General",
        "start_sec": 14.8,
        "rate": "+2%",
        "text": "Para lograr esta transferencia de energía, el sistema utiliza un circuito cerrado con cinco componentes clave: el compresor en la base, el serpentín condensador exterior, el filtro secador, el tubo capilar y el evaporador dentro del congelador.",
        "subs": [
            (14.8, 19.5, "El sistema utiliza un circuito cerrado", "con cinco componentes clave:"),
            (19.8, 24.5, "Compresor en la base, serpentín condensador,", "y filtro deshidratador..."),
            (24.8, 29.8, "Además del tubo capilar y el evaporador", "dentro del compartimento."),
        ],
    },
    {
        "stage_id": "st3_compressor",
        "name": "3. Compresión",
        "start_sec": 30.5,
        "rate": "+0%",
        "text": "El ciclo comienza con el compresor hermético. Este motor comprime el refrigerante en estado gaseoso, aumentando drásticamente tanto su presión como su temperatura gracias a un pistón mecánico que bombea de forma continua.",
        "subs": [
            (30.5, 35.0, "El ciclo comienza en el compresor:", "un motor hermético de alto rendimiento."),
            (35.3, 40.2, "Comprime el refrigerante gaseoso,", "elevando su presión y temperatura..."),
            (40.5, 46.5, "Gracias a un pistón mecánico", "que bombea continuamente."),
        ],
    },
    {
        "stage_id": "st4_condenser",
        "name": "4. Condensación",
        "start_sec": 48.0,
        "rate": "+1%",
        "text": "El gas caliente y presurizado viaja hacia el condensador, esa rejilla en la parte trasera. Al circular por sus tubos, el refrigerante libera calor hacia la habitación y se condensa, transformándose en un líquido de alta presión.",
        "subs": [
            (48.0, 52.8, "El gas caliente viaja al condensador,", "esa rejilla en la parte trasera."),
            (53.0, 58.0, "Al circular, libera el calor al ambiente", "y comienza a condensarse..."),
            (58.2, 64.0, "Transformándose en un líquido denso", "a muy alta presión."),
        ],
    },
    {
        "stage_id": "st5_capillary",
        "name": "5. Expansión",
        "start_sec": 66.0,
        "rate": "+1%",
        "text": "Antes de entrar a la zona fría, el líquido pasa por un filtro que retiene impurezas y humedad, para luego atravesar un tubo capilar sumamente estrecho. Esta repentina reducción de calibre provoca una caída brusca de presión.",
        "subs": [
            (66.0, 71.0, "Pasa por el filtro secador", "para eliminar humedad e impurezas..."),
            (71.2, 76.5, "Y atraviesa un tubo capilar estrecho.", "Esta repentina reducción de calibre..."),
            (76.8, 81.5, "Provoca una caída brusca de presión", "enfriando el fluido al instante."),
        ],
    },
    {
        "stage_id": "st6_evaporator",
        "name": "6. Evaporación",
        "start_sec": 82.5,
        "rate": "+1%",
        "text": "Al llegar al evaporador a baja presión, el refrigerante hierve a temperaturas bajo cero. En este proceso, absorbe con avidez el calor del aire interior y de tus alimentos, manteniéndolos frescos y congelados.",
        "subs": [
            (82.5, 87.5, "En el evaporador, el refrigerante hierve", "a temperaturas bajo cero."),
            (87.8, 92.5, "Absorbe intensamente el calor", "del aire interior y los alimentos..."),
            (92.8, 97.2, "¡Manteniéndolos frescos", "y en perfecta conservación!"),
        ],
    },
    {
        "stage_id": "st7_closure",
        "name": "7. Síntesis & Cierre",
        "start_sec": 96.5,
        "rate": "+6%",
        "text": "Finalmente, el vapor retorna al compresor para repetir el ciclo sin fin. Así funciona la fascinante termodinámica en tu cocina.",
        "subs": [
            (96.5, 100.5, "El vapor retorna al compresor", "para reiniciar el ciclo sin fin."),
            (100.8, 104.5, "¡Así funciona la fascinante termodinámica", "en tu cocina!"),
        ],
    },
]


# ------------------------------------------------------------------------------
# 2. SÍNTESIS DE AUDIO MASTER (105.0 s)
# ------------------------------------------------------------------------------
async def generate_master_audio(output_wav: Path, target_total_sec: float = 105.0) -> None:
    import edge_tts

    voice = "es-MX-DaliaNeural"
    sample_rate = 24000
    total_samples = int(target_total_sec * sample_rate)
    master_buffer = np.zeros(total_samples, dtype=np.float32)

    tmp_dir = output_wav.parent / "_tts_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"--> Generando narración TTS con voz {voice} (expresiva, amena, mexicana)...")
    for stage in SCRIPT_STAGES:
        st_id = stage["stage_id"]
        txt = stage["text"]
        rate = stage.get("rate", "+0%")
        st_file = tmp_dir / f"{st_id}.mp3"

        communicate = edge_tts.Communicate(txt, voice, rate=rate, pitch="+2Hz")
        await communicate.save(str(st_file))

        data, sr = sf.read(str(st_file))
        if data.ndim > 1:
            data = data.mean(axis=1)

        # Resample si es necesario
        if sr != sample_rate:
            ratio = sample_rate / sr
            new_len = int(len(data) * ratio)
            data = np.interp(np.linspace(0, len(data), new_len, endpoint=False), np.arange(len(data)), data)

        start_sample = int(stage["start_sec"] * sample_rate)
        end_sample = min(start_sample + len(data), total_samples)
        chunk_len = end_sample - start_sample

        master_buffer[start_sample:end_sample] += data[:chunk_len].astype(np.float32)
        print(f"    - {stage['name']}: {len(data)/sample_rate:.2f}s montado en t={stage['start_sec']}s")

    # Normalizar volumen suavemente
    max_val = np.max(np.abs(master_buffer))
    if max_val > 0.01:
        master_buffer = master_buffer / max_val * 0.92

    sf.write(str(output_wav), master_buffer, sample_rate)
    print(f"[OK] Audio master sintetizado: {output_wav} ({target_total_sec} s)")


# ------------------------------------------------------------------------------
# 3. GENERADOR DE SUBTÍTULOS DINÁMICOS ASS (EN ZONA SEGURA)
# ------------------------------------------------------------------------------
def format_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_styled_ass_subtitles(output_ass: Path) -> None:
    """Genera subtítulos ASS optimizados para formato 9:16 vertical (720x1280).
    MarginV=300 sitúa el texto estrictamente por encima de la zona segura inferior (22% = 282px),
    evitando que la interfaz de TikTok / Reels / Shorts tape el texto."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: EducationalSafe,Arial,28,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.8,1.4,2,65,65,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for stage in SCRIPT_STAGES:
        for t_start, t_end, line1, line2 in stage["subs"]:
            s_str = format_ass_time(t_start)
            e_str = format_ass_time(t_end)
            event_text = f"{line1}\\N{line2}"
            lines.append(f"Dialogue: 0,{s_str},{e_str},EducationalSafe,,0,0,0,,{event_text}\n")

    output_ass.write_text("".join(lines), encoding="utf-8")
    print(f"[OK] Subtítulos ASS generados en zona segura: {output_ass}")


# ------------------------------------------------------------------------------
# 4. SCRIPT HELPER PARA BLENDER (RENDERIZADO HEADLESS CON EEVEE)
# ------------------------------------------------------------------------------
BLENDER_RENDER_RUNNER = """
import sys
from pathlib import Path
_repo_root = Path(r"{repo_root}")
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import bpy
from mathutils import Vector
from studio.blender.educational_vertical_framework import Educational916FrameworkConfig, setup_educational_scene_base
from studio.blender.models_library.refrigerator_pipeline_specialized import (
    build_specialized_refrigerator_model,
    generate_refrigerator_adaptive_labels,
    animate_refrigerator_vertical_showcase
)

cfg = Educational916FrameworkConfig()
cfg.render_width = {width}
cfg.render_height = {height}

# Limpiar escena
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
    for item in list(coll):
        coll.remove(item, do_unlink=True)

scene_info = setup_educational_scene_base(cfg)
cam = scene_info['camera']
m_data = build_specialized_refrigerator_model()

cam_pos = Vector((3.6, -8.2, 1.95))
cam_target = Vector((0.0, 0.0, 1.95))
cam.location = cam_pos
cam.rotation_euler = (cam_target - cam_pos).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

labels = generate_refrigerator_adaptive_labels(m_data, cam_pos, cam_target, cfg)
animate_refrigerator_vertical_showcase(m_data, cam, cfg, labels_dict=labels)

scene = bpy.context.scene
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.frame_start = {frame_start}
scene.frame_end = {frame_end}
scene.frame_step = {frame_step}

# Configuración EEVEE optimizada: sin ruido/grano en superficies metálicas
scene.eevee.taa_render_samples = 6
scene.eevee.volumetric_samples = 4
scene.eevee.volumetric_shadow_samples = 4
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = r"{out_frames_pattern}"

print("--> [BLENDER] Iniciando renderizado de animacion...")
bpy.ops.render.render(animation=True)
print("--> [BLENDER] Renderizado de cuadros completado.")
"""


def render_blender_frames(
    frames_dir: Path,
    width: int = 720,
    height: int = 1280,
    total_frames: int = 2520,
    frame_step: int = 2,
) -> None:
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = str((frames_dir / "frame_####.png").resolve())

    runner_py = frames_dir.parent / "_blender_render_runner.py"
    runner_code = BLENDER_RENDER_RUNNER.format(
        repo_root=str(_repo_root),
        width=width,
        height=height,
        frame_start=1,
        frame_end=total_frames,
        frame_step=frame_step,
        out_frames_pattern=pattern,
    )
    runner_py.write_text(runner_code, encoding="utf-8")

    cmd = [
        BLENDER_EXE,
        "-b",
        "--python",
        str(runner_py.resolve()),
    ]
    print(f"--> Ejecutando Blender Headless: {width}x{height}, {total_frames} frames (step={frame_step})...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    saved_count = 0
    expected_frames = total_frames // frame_step
    with proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            line_str = line.strip()
            if "Saved:" in line_str:
                saved_count += 1
                pct = (saved_count / expected_frames) * 100
                if saved_count % 25 == 0 or saved_count == expected_frames or saved_count <= 5:
                    print(f"    [Progreso Blender] Cuadro {saved_count}/{expected_frames} ({pct:.1f}%)")
            elif "Error" in line_str or "Exception" in line_str:
                print(f"    [LOG] {line_str}")
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Fallo el renderizado en Blender (codigo {proc.returncode}).")
    print("[OK] Cuadros renderizados en Blender. Normalizando secuencia contigua para FFmpeg...")

    # Renombrar a secuencia estrictamente contigua seq_%05d.png para FFmpeg
    for old_seq in frames_dir.glob("seq_*.png"):
        try:
            old_seq.unlink(missing_ok=True)
        except OSError:
            pass
    raw_frames = sorted(frames_dir.glob("frame_*.png"))
    for idx, fpath in enumerate(raw_frames, start=1):
        target_name = frames_dir / f"seq_{idx:05d}.png"
        fpath.replace(target_name)

    print(f"[OK] {len(raw_frames)} cuadros normalizados a secuencia contigua seq_%05d.png.")


# ------------------------------------------------------------------------------
# 5. ENSAMBLE FINAL FFMPEG (FRAMES + TTS + SUBTÍTULOS EN ZONA SEGURA)
# ------------------------------------------------------------------------------
def compose_final_video_ffmpeg(
    frames_dir: Path,
    audio_wav: Path,
    subs_ass: Path,
    output_mp4: Path,
    source_fps: int = 12,
    target_fps: int = 24,
    width: int = 720,
    height: int = 1280,
) -> None:
    print("--> Componiendo video vertical 9:16 con FFmpeg...")

    work_dir = output_mp4.parent.resolve()
    # Usar rutas relativas al directorio de trabajo para evitar conflictos de dos puntos en Windows
    rel_subs = subs_ass.resolve().relative_to(work_dir).as_posix()
    rel_audio = audio_wav.resolve().relative_to(work_dir).as_posix()
    rel_frames = (frames_dir.resolve().relative_to(work_dir) / "seq_%05d.png").as_posix()
    rel_out = output_mp4.resolve().relative_to(work_dir).as_posix()

    vf_filter = f"fps={target_fps},subtitles=filename='{rel_subs}'"

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-framerate", str(source_fps),
        "-i", rel_frames,
        "-i", rel_audio,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        rel_out,
    ]

    print("    Comando FFmpeg lanzado en cwd:", work_dir)
    res = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True)
    if res.returncode != 0:
        print("[ERROR FFMPEG]:", res.stderr[-800:])
        raise RuntimeError("Fallo el ensamble de video con FFmpeg.")

    file_size_mb = output_mp4.stat().st_size / (1024 * 1024)
    print(f"[OK] Video final generado: {output_mp4} ({file_size_mb:.2f} MB)")


# ------------------------------------------------------------------------------
# 6. FUNCIÓN PRINCIPAL ORQUESTADORA
# ------------------------------------------------------------------------------
async def run_pipeline(
    output_project_dir: Path,
    width: int = 720,
    height: int = 1280,
    total_frames: int = 2520,
    frame_step: int = 2,
) -> Dict[str, Any]:
    output_project_dir.mkdir(parents=True, exist_ok=True)

    master_audio_wav = output_project_dir / "narration_master_105s.wav"
    subs_ass = output_project_dir / "subtitles_safezone_9_16.ass"
    frames_dir = output_project_dir / "rendered_frames"
    final_video_mp4 = output_project_dir / "video_showcase_refrigerador_vertical_9_16.mp4"

    # 1. Sintetizar Audio Master
    await generate_master_audio(master_audio_wav, target_total_sec=105.0)

    # 2. Generar Subtítulos ASS
    generate_styled_ass_subtitles(subs_ass)

    # 3. Renderizar cuadros Blender
    render_blender_frames(
        frames_dir=frames_dir,
        width=width,
        height=height,
        total_frames=total_frames,
        frame_step=frame_step,
    )

    # 4. Ensamble FFmpeg
    source_fps = int(round(24 / frame_step))
    compose_final_video_ffmpeg(
        frames_dir=frames_dir,
        audio_wav=master_audio_wav,
        subs_ass=subs_ass,
        output_mp4=final_video_mp4,
        source_fps=source_fps,
        target_fps=24,
        width=width,
        height=height,
    )

    # 5. Copiar a la carpeta de artefactos de la sesion
    artifact_dir = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a")
    if artifact_dir.exists():
        import shutil
        dest_video = artifact_dir / final_video_mp4.name
        shutil.copy2(final_video_mp4, dest_video)
        print(f"[OK] Video copiado a artefactos: {dest_video}")

    return {
        "status": "SUCCESS",
        "video_path": str(final_video_mp4.resolve()),
        "audio_path": str(master_audio_wav.resolve()),
        "subtitles_path": str(subs_ass.resolve()),
        "size_mb": round(final_video_mp4.stat().st_size / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    import argparse
    from studio.blender.validate_educational_vertical import run_full_validation

    parser = argparse.ArgumentParser(description="Orquestador de Video Educativo Vertical 9:16 - Refrigerador")
    parser.add_argument("--preview", action="store_true", help="Renderizar los 7 fotogramas clave de control de calidad en ~20s")
    parser.add_argument("--clip", action="store_true", help="Renderizar un clip de prueba rapido de 10 segundos")
    parser.add_argument("--full", action="store_true", help="Renderizar el video completo de 105 segundos")
    args = parser.parse_args()

    out_dir = Path(__file__).resolve().parent.parent.parent / "projects" / "showcase_refrigerator_vertical_9_16"

    if args.preview:
        print("--> Modo Preview: Generando 7 fotogramas clave de control de calidad...")
        rep = run_full_validation(out_dir, render_sample_stills=True)
        print("PREVIEW RESULT:", json.dumps(rep["quality_metrics"], indent=2))
    elif args.clip:
        print("--> Modo Clip: Renderizando tramo de prueba de 10 segundos (f469 a f709)...")
        res = asyncio.run(run_pipeline(out_dir, width=720, height=1280, total_frames=709, frame_step=2))
        print("CLIP RESULT:", json.dumps(res, indent=2))
    else:
        # Por defecto o con --full, ejecutar pipeline completo
        print("--> Modo Completo: Renderizando video de 105 segundos (2520 frames)...")
        res = asyncio.run(run_pipeline(out_dir, width=720, height=1280, total_frames=2520, frame_step=2))
        print("PIPELINE RESULT:", json.dumps(res, indent=2))
