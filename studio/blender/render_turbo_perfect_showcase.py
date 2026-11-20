"""AI VIDEO STUDIO — Compilador Maestro del Turbocompresor 3D (14 Tomas Dinámicas · 131.7s).
Refactorizado según directrices maestras de producción vertical 9:16:
1. Render a 24 FPS reales con Motion Blur activado.
2. Zonas seguras 9:16 estrictas para Callouts (u: 10%-90%, v: >=28%).
3. Apuntado dinámico TRACK_TO, Exploded View real y compuerta wastegate articulada.
4. Modificadores Bevel + Weighted Normal y splines 3D emisivas continuas (sin conos planos).
5. Iluminación dual-temperature (Warm Inconel vs Cool Billet) y EEVEE Next denoise.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.blender.service import _get_ffmpeg

REPO_ROOT = _repo_root
OUTPUT_DIR = REPO_ROOT / "projects" / "showcase_turbocharger_vertical_9_16"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = OUTPUT_DIR / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
FFMPEG_EXE = _get_ffmpeg()

BLENDER_SCRIPT = OUTPUT_DIR / "blender_render_job.py"


def generate_blender_job_script(total_frames: int = 3161, frame_step: int = 1, width: int = 720, height: int = 1280, fps: int = 24):
    code = f'''import sys, math
from pathlib import Path
repo_root = r"{REPO_ROOT}"
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
    TURBO_TIMELINE_CUES,
)

cfg = Educational916FrameworkConfig()
cfg.render_width = {width}
cfg.render_height = {height}
cfg.timeline.target_duration_sec = 131.72
cfg.timeline.fps = {fps}

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
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.render.fps = {fps}
scene.frame_start = 1
scene.frame_end = {total_frames}
scene.frame_step = {frame_step}

# 1. Motion Blur Activado para realismo físico en rodetes a alta velocidad
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.5
scene.render.motion_blur_position = 'CENTER'

# 2. Configuración EEVEE Next / Denoising para superficies metálicas limpias
if hasattr(scene, "eevee"):
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 16
    if hasattr(scene.eevee, "use_fast_gi"):
        scene.eevee.use_fast_gi = True
    if hasattr(scene.eevee, "use_shadows"):
        scene.eevee.use_shadows = True

frames_out = r"{FRAMES_DIR}\\frame_"
scene.render.filepath = frames_out
print(f"[BLENDER JOB] Configurado: {{scene.frame_start}} a {{scene.frame_end}} (step={frame_step}) en {{frames_out}}")
bpy.ops.render.render(animation=True)
print("[BLENDER JOB] Render de animacion completado exitosamente.")
'''
    BLENDER_SCRIPT.write_text(code, encoding="utf-8")
    return BLENDER_SCRIPT


def main():
    parser = argparse.ArgumentParser(description="Renderizador y Compilador Maestro del Turbocompresor 3D Vertical (9:16)")
    parser.add_argument("--fps", type=int, default=24, help="Framerate de salida (minimo 24 fps)")
    parser.add_argument("--step", type=int, default=1, help="Paso de fotogramas (1 para 24 fps reales)")
    parser.add_argument("--width", type=int, default=720, help="Ancho de renderizado (720 o 1080)")
    parser.add_argument("--height", type=int, default=1280, help="Alto de renderizado (1280 o 1920)")
    parser.add_argument("--benchmark", action="store_true", help="Renderizar solo los primeros 120 fotogramas (5s de prueba)")
    args = parser.parse_args()

    fps = max(24, args.fps)
    frame_step = max(1, args.step)
    width = args.width
    height = args.height
    total_frames = 120 if args.benchmark else 3161

    print(f"=== INICIANDO PIPELINE DE RENDERIZADO DEL TURBOCOMPRESOR 3D ({total_frames} CUADROS @ {fps} FPS) ===")
    print(f"    Resolución: {width}x{height} (9:16)")
    print(f"    Frame Step: {frame_step}")
    print(f"    Motion Blur: ACTIVADO")
    print(f"    Zonas Seguras HUD: u in [0.10, 0.90], v >= 0.28")

    # Limpiar fotogramas anteriores
    for f in FRAMES_DIR.glob("*.png"):
        try:
            f.unlink()
        except Exception:
            pass

    # 1. Crear script de trabajo de Blender
    job_script = generate_blender_job_script(total_frames, frame_step, width, height, fps)

    # 2. Ejecutar Blender en modo headless
    expected_frames = total_frames // frame_step
    print(f"[BLENDER] Lanzando Blender 5.3 EEVEE para renderizar {expected_frames} cuadros a {width}x{height}...")
    t0 = time.time()
    cmd = [BLENDER_EXE, "-b", "-P", str(job_script.resolve())]
    subprocess.run(cmd, check=True)
    print(f"[BLENDER] Renderizado completado en {time.time()-t0:.1f}s.")

    # 3. Normalizar secuencia de cuadros para FFmpeg
    raw_frames = sorted(FRAMES_DIR.glob("frame_*.png"))
    for old_seq in FRAMES_DIR.glob("seq_*.png"):
        old_seq.unlink(missing_ok=True)
    for idx, fpath in enumerate(raw_frames, start=1):
        fpath.replace(FRAMES_DIR / f"seq_{idx:05d}.png")
    print(f"[NORM] {len(raw_frames)} cuadros normalizados a seq_%05d.png.")

    # 4. Compilación final con FFmpeg
    master_audio = OUTPUT_DIR / "turbo_master_soundtrack_mixed.m4a"
    sub_ass = OUTPUT_DIR / "subtitles_turbo_safezone.ass"
    final_video = OUTPUT_DIR / "video_showcase_turbocharger_vertical_9_16.mp4"

    source_fps = fps // frame_step

    print(f"[FFMPEG] Muxeando video MP4 con audio y subtítulos en {final_video}...")
    ffmpeg_cmd = [
        FFMPEG_EXE, "-y",
        "-framerate", str(source_fps),
        "-i", str((FRAMES_DIR / "seq_%05d.png").resolve()),
        "-i", str(master_audio.resolve()),
        "-vf", f"fps={fps},scale={width}:{height}:flags=bicubic,subtitles={sub_ass.name}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-crf", "18",
        "-r", str(fps),
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(final_video.resolve())
    ]
    subprocess.run(ffmpeg_cmd, cwd=str(OUTPUT_DIR), check=True)
    print(f"[FFMPEG] ¡Video final completado con éxito! ({final_video.stat().st_size / 1024 / 1024:.2f} MB)")

    # 5. Copiar a la carpeta de artefactos
    art_video = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a\video_turbo_3d_mecanico_con_sfx.mp4")
    shutil.copy2(str(final_video), str(art_video))
    print(f"[COPY] Video copiado a artefactos: {art_video}")


if __name__ == "__main__":
    main()
