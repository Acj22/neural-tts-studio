"""AI VIDEO STUDIO — Orquestador de Renderizado y Ensamble Completo.
Tema: Turbocompresor Automotriz (Showcase Vertical 9:16).

Flujo unificado de alta fidelidad:
1. Síntesis de narración continua por etapas con Edge-TTS (es-MX-DaliaNeural, voz mexicana amena).
2. Generación de subtítulos dinámicos ASS en Zona Segura inferior (MarginV=150).
3. Renderizado de la animación vertical 9:16 en Blender con EEVEE.
4. Muxing y codificación final con FFmpeg a H.264 / AAC.
"""

from __future__ import annotations

import argparse
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
        "name": "1. Gancho: Multiplicador de potencia",
        "start_sec": 0.5,
        "rate": "+2%",
        "text": "¿Cómo puede un motor pequeño producir la fuerza demoledora de un motor gigante? El secreto se llama turbocompresor: un prodigio de la ingeniería que reutiliza energía que antes se desperdiciaba para duplicar la potencia del auto.",
        "subs": [
            (0.5, 4.2, "¿Cómo produce un motor pequeño", "la fuerza de un gigante?"),
            (4.5, 8.8, "El secreto es el turbocompresor:", "recicla energía desperdiciada..."),
            (9.0, 14.0, "¡Para duplicar la potencia", "y la aceleración del motor!"),
        ],
    },
    {
        "stage_id": "st2_architecture",
        "name": "2. Arquitectura de 5 componentes",
        "start_sec": 15.0,
        "rate": "+2%",
        "text": "Para entender su magia, dividámoslo en cinco piezas clave: la turbina de escape al rojo vivo, el cartucho central de lubricación CHRA, la rueda compresora de aluminio billet, la entrada de aire fresco y la válvula wastegate.",
        "subs": [
            (15.0, 18.2, "Conozcamos sus 5 componentes clave:"),
            (18.5, 22.0, "Turbina de Inconel y Cartucho CHRA,"),
            (22.2, 25.8, "Rueda compresora de aluminio billet,"),
            (26.0, 29.5, "Entrada de aire y Válvula wastegate."),
        ],
    },
    {
        "stage_id": "st3_turbine",
        "name": "3. Lado Caliente: Turbina Inconel",
        "start_sec": 30.0,
        "rate": "+2%",
        "text": "Todo arranca en el lado caliente. Los gases de escape salen del motor a novecientos cincuenta grados centígrados, chocando con furia contra la turbina de Inconel para hacerla girar a velocidades extremas.",
        "subs": [
            (30.0, 34.0, "Gases de escape a 950 °C"),
            (34.2, 38.5, "chocan contra la turbina de Inconel,"),
            (38.8, 44.5, "haciéndola girar a velocidades extremas."),
        ],
    },
    {
        "stage_id": "st4_chra",
        "name": "4. Cartucho Central CHRA",
        "start_sec": 45.5,
        "rate": "+2%",
        "text": "En el centro está el cartucho CHRA. Un eje de acero templado une ambas ruedas a más de ciento cincuenta mil revoluciones por minuto. Flota literalmente sobre un colchón de aceite presurizado para resistir la fricción.",
        "subs": [
            (45.5, 49.2, "En el centro, el cartucho CHRA:"),
            (49.5, 54.0, "Gira a más de 150,000 RPM"),
            (54.2, 60.0, "flotando sobre una película de aceite."),
        ],
    },
    {
        "stage_id": "st5_compressor",
        "name": "5. Lado Frío: Compresor Billet",
        "start_sec": 61.0,
        "rate": "+2%",
        "text": "Al otro lado tenemos el lado frío. Al girar solidaria con la turbina, la rueda compresora succiona aire fresco del exterior, lo comprime a gran presión y lo manda directo a las cámaras de combustión.",
        "subs": [
            (61.0, 65.0, "En el lado frío, el compresor billet"),
            (65.2, 69.8, "aspira aire fresco del exterior"),
            (70.0, 75.5, "y lo inyecta a alta presión al motor."),
        ],
    },
    {
        "stage_id": "st6_wastegate",
        "name": "6. Válvula Wastegate de Alivio",
        "start_sec": 76.5,
        "rate": "+2%",
        "text": "Pero si la presión de boost sube demasiado, entra la compuerta wastegate. Esta válvula de alivio se abre automáticamente para desviar los gases sobrantes al escape, salvando al motor de presiones destructivas.",
        "subs": [
            (76.5, 80.5, "Si la presión sube demasiado:"),
            (80.8, 85.0, "la compuerta wastegate se abre"),
            (85.2, 91.0, "para proteger el motor de sobrepresión."),
        ],
    },
    {
        "stage_id": "st7_closure",
        "name": "7. Ciclo Continuo de Boost",
        "start_sec": 92.0,
        "rate": "+2%",
        "text": "Así funciona el ciclo: energía de desecho convertida en pura aceleración, eficiencia y potencia instantánea. ¡Ingeniería automotriz llevada al límite!",
        "subs": [
            (92.0, 96.0, "Energía de escape convertida"),
            (96.2, 100.5, "en aceleración y eficiencia pura."),
            (101.0, 104.5, "¡Ingeniería automotriz al límite!"),
        ],
    },
]


def generate_subtitles_ass(output_path: Path) -> None:
    """Genera archivo de subtítulos ASS en zona segura inferior (MarginV=150)."""
    ass_header = """[Script Info]
Title: Turbocompresor Automotriz Educativo 9:16
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TurboSub,Montserrat,34,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.8,1.5,2,50,50,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def fmt_time(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = []
    for stage in SCRIPT_STAGES:
        for item in stage["subs"]:
            t0, t1 = item[0], item[1]
            txt = "\\N".join(item[2:]) if len(item) > 3 else (item[2] if len(item) == 3 else "")
            lines.append(f"Dialogue: 0,{fmt_time(t0)},{fmt_time(t1)},TurboSub,,0,0,0,,{txt}")

    output_path.write_text(ass_header + "\n".join(lines) + "\n", encoding="utf-8")


async def generate_narration_audio(output_dir: Path) -> Path:
    """Genera la pista de audio continua y alineada con Edge-TTS en Dalia (mexicana)."""
    import edge_tts

    voice = "es-MX-DaliaNeural"
    sr = 24000
    total_samples = int(105.0 * sr)
    full_audio = np.zeros(total_samples, dtype=np.float32)

    for stage in SCRIPT_STAGES:
        t_start = stage["start_sec"]
        text = stage["text"]
        rate = stage.get("rate", "+2%")
        tmp_mp3 = output_dir / f"tmp_voice_{stage['stage_id']}.mp3"

        tts = edge_tts.Communicate(text, voice, rate=rate)
        await tts.save(str(tmp_mp3))

        data, file_sr = sf.read(str(tmp_mp3))
        if data.ndim > 1:
            data = data.mean(axis=1)

        idx_start = int(t_start * sr)
        idx_end = min(idx_start + len(data), total_samples)
        full_audio[idx_start:idx_end] = data[:idx_end - idx_start]

        if tmp_mp3.exists():
            tmp_mp3.unlink()

    out_wav = output_dir / "narration_turbo_master.wav"
    sf.write(str(out_wav), full_audio, sr)
    return out_wav


BLENDER_RENDER_RUNNER = """
import sys
from pathlib import Path

repo_root = r"{repo_root}"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import bpy
from mathutils import Vector
from studio.blender.educational_vertical_framework import (
    Educational916FrameworkConfig,
    setup_educational_scene_base,
)
from studio.blender.models_library.turbocharger_specialized import (
    build_specialized_turbocharger_model,
    generate_turbo_adaptive_labels,
    animate_turbo_vertical_showcase,
)

cfg = Educational916FrameworkConfig()
cfg.render_width = {width}
cfg.render_height = {height}

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
    for item in list(coll):
        coll.remove(item, do_unlink=True)

scene_info = setup_educational_scene_base(cfg)
cam_obj = scene_info["camera"]

model_data = build_specialized_turbocharger_model(center_z=1.25)
cam_pos = Vector((2.4, -4.0, 2.3))
cam_target = Vector((0.0, 0.0, 1.25))
cam_obj.location = cam_pos
cam_obj.rotation_euler = (cam_target - cam_pos).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

labels_dict = generate_turbo_adaptive_labels(model_data, cam_pos, cam_target, cfg)
animate_turbo_vertical_showcase(model_data, cam_obj, cfg, labels_dict=labels_dict)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE" if hasattr(scene.render, "engine") else "BLENDER_EEVEE_NEXT"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.frame_start = {frame_start}
scene.frame_end = {frame_end}
scene.frame_step = {frame_step}

if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 6
if hasattr(scene, "eevee") and hasattr(scene.eevee, "volumetric_samples"):
    scene.eevee.volumetric_samples = 4
    scene.eevee.volumetric_shadow_samples = 4

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
                if saved_count % 30 == 0 or saved_count == expected_frames or saved_count <= 5:
                    print(f"    [Progreso Blender] Cuadro {saved_count}/{expected_frames} ({pct:.1f}%)")
            elif "Error" in line_str or "Exception" in line_str:
                print(f"    [LOG] {line_str}")
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Fallo el renderizado en Blender (codigo {proc.returncode}).")
    print("[OK] Cuadros renderizados en Blender. Normalizando secuencia contigua para FFmpeg...")

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


def compose_final_video_ffmpeg(
    frames_dir: Path,
    audio_wav: Path,
    subs_ass: Path,
    output_mp4: Path,
    source_fps: int = 12,
    target_fps: int = 24,
) -> None:
    print("--> Componiendo video vertical 9:16 con FFmpeg...")

    work_dir = output_mp4.parent.resolve()
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
        print("[STDERR FFMPEG]:", res.stderr)
        raise RuntimeError(f"FFmpeg fallo con codigo {res.returncode}")

    print(f"[EXITO] Video maestro generado: {output_mp4} ({output_mp4.stat().st_size / 1024 / 1024:.2f} MB)")


async def main():
    parser = argparse.ArgumentParser(description="Renderizador de video vertical del Turbocompresor.")
    parser.add_argument("--preview", action="store_true", help="Genera clip de prueba rápido")
    parser.add_argument("--step", type=int, default=2, help="Paso de cuadros (default 2)")
    args = parser.parse_args()

    out_dir = _repo_root / "projects" / "showcase_turbocharger_vertical_9_16"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "rendered_frames"

    print("1. Generando subtitulos ASS en zona segura...")
    sub_path = out_dir / "subtitles_turbo_safezone.ass"
    generate_subtitles_ass(sub_path)

    print("2. Sintetizando locucion continua con Edge-TTS (Dalia)...")
    audio_wav = await generate_narration_audio(out_dir)

    total_frames = 480 if args.preview else 2520
    frame_step = args.step
    source_fps = 24 // frame_step

    print(f"3. Renderizando frames en Blender ({total_frames} cuadros, step={frame_step})...")
    render_blender_frames(
        frames_dir=frames_dir,
        width=720,
        height=1280,
        total_frames=total_frames,
        frame_step=frame_step,
    )

    mp4_name = "preview_turbocharger_9_16.mp4" if args.preview else "video_showcase_turbocharger_vertical_9_16.mp4"
    out_mp4 = out_dir / mp4_name
    print("4. Ensamblando video maestro final...")
    compose_final_video_ffmpeg(
        frames_dir=frames_dir,
        audio_wav=audio_wav,
        subs_ass=sub_path,
        output_mp4=out_mp4,
        source_fps=source_fps,
        target_fps=24,
    )

    # Copiar a artifacts para visualización inmediata
    art_dir = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a")
    if art_dir.exists() and out_mp4.exists():
        import shutil
        target_art = art_dir / mp4_name
        shutil.copy2(out_mp4, target_art)
        print(f"[OK] Copiado a artifacts: {target_art}")

    print("=== PROCESO COMPLETADO EXITOSAMENTE ===")


if __name__ == "__main__":
    asyncio.run(main())
