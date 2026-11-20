"""AI VIDEO STUDIO — Pipeline Maestro Paper-Cut 9:16: El Castillo de Chapultepec.
Renderizado determinista a 24 fps con Playwright + Edge-TTS + Subtítulos Big Focus ASS.
"""

import io
import json
import math
import shutil
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from playwright.sync_api import sync_playwright

repo_root = Path(__file__).resolve().parent.parent.parent
output_dir = repo_root / "projects" / "opuscar_chapultepec"
output_dir.mkdir(parents=True, exist_ok=True)
frames_dir = output_dir / "frames"
frames_dir.mkdir(parents=True, exist_ok=True)

html_template = repo_root / "studio" / "opuscar" / "templates" / "chapultepec_castillo.html"
ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100

# 1. Leer timeline
timeline_file = output_dir / "timeline.json"
with open(timeline_file, "r", encoding="utf-8") as f:
    timeline_data = json.load(f)

TOTAL_DURATION = float(timeline_data["total_duration"])
scenes = timeline_data["scenes"]

def build_audio_tracks():
    """Genera la pista de narración continua y música clásica de época."""
    print("[AUDIO] Ensamblando narración continua y ambiente orquestal...", flush=True)
    n_samples = int(SR * TOTAL_DURATION)
    narr_track = np.zeros(n_samples, dtype=np.float32)

    for sc in scenes:
        p = Path(sc["path"])
        cmd = [ffmpeg_bin, "-i", str(p), "-f", "wav", "-ar", str(SR), "-ac", "1", "-"]
        proc = subprocess.run(cmd, capture_output=True, check=True)
        data, _ = sf.read(io.BytesIO(proc.stdout))
        
        idx_start = int(sc["t_start"] * SR)
        idx_end = min(n_samples, idx_start + len(data))
        narr_track[idx_start:idx_end] = data[:idx_end - idx_start]

    # Música de cámara clásica / cuerdas de época (vals imperial sutil)
    bgm = np.zeros(n_samples, dtype=np.float32)
    chords = [
        [220.0, 277.18, 329.63], # A maj
        [164.81, 246.94, 329.63], # E maj
        [185.0, 220.0, 277.18],  # F# min
        [146.83, 220.0, 293.66], # D maj
    ]
    bar_dur = 2.4
    n_bars = int(TOTAL_DURATION / bar_dur) + 1
    
    for b in range(n_bars):
        chord = chords[b % len(chords)]
        b_start = int(b * bar_dur * SR)
        t_bar = np.linspace(0, bar_dur, int(SR * bar_dur), False)
        wave = np.zeros_like(t_bar)
        for freq in chord:
            wave += np.sin(2 * np.pi * freq * t_bar) * 0.12
            wave += np.sin(2 * np.pi * freq * 2 * t_bar) * 0.04
        env = np.sin(np.pi * t_bar / bar_dur) ** 0.8
        wave *= env
        b_end = min(n_samples, b_start + len(wave))
        bgm[b_start:b_end] += wave[:b_end - b_start]

    narr_wav = output_dir / "narration_full.wav"
    bgm_wav = output_dir / "bgm_imperial.wav"
    sf.write(str(narr_wav), np.int16(np.clip(narr_track, -1, 1) * 32767), SR)
    sf.write(str(bgm_wav), np.int16(np.clip(bgm, -1, 1) * 32767), SR)

    # Master audio
    master_m4a = output_dir / "master_audio_chapultepec.m4a"
    filter_complex = (
        "[0:a]volume=1.35,alimiter=limit=0.98[vox];"
        "[1:a]volume=0.08,lowpass=f=5500[music];"
        "[vox][music]amix=inputs=2:duration=first:dropout_transition=2[outa]"
    )
    cmd_mix = [
        ffmpeg_bin, "-y",
        "-i", str(narr_wav.resolve()),
        "-i", str(bgm_wav.resolve()),
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        str(master_m4a.resolve())
    ]
    subprocess.run(cmd_mix, check=True)
    return master_m4a

def generate_subtitles_ass():
    """Genera subtítulos Big Focus ASS sincronizados en zona segura (MarginV=260 en 1080x1920)."""
    sub_path = output_dir / "subtitles_chapultepec.ass"
    header = """[Script Info]
Title: El Castillo de Chapultepec — Big Focus Subtitles 1080p
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BigFocus,Arial Black,44,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H90000000,-1,0,0,0,100,100,0,0,1,5.2,2.8,2,50,50,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = []
    for sc in scenes:
        for item in sc["subs"]:
            t0, t1 = float(item[0]), float(item[1])
            txt = "\\N".join(item[2:])
            lines.append(f"Dialogue: 0,{fmt(t0)},{fmt(t1)},BigFocus,,0,0,0,,{txt}")

    sub_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return sub_path

def render_video_frames(fps=30):
    """Renderiza cuadros deterministas en 1080x1920 con Playwright."""
    total_frames = int(TOTAL_DURATION * fps)
    print(f"[RENDER] Renderizando {total_frames} cuadros en 1080x1920 a {fps} fps ({TOTAL_DURATION}s)...", flush=True)
    t0 = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(f"file:///{html_template.resolve()}")
        page.wait_for_timeout(1000)
        page.evaluate("window.manualMode = true;")

        for f in range(total_frames):
            t_sec = f / float(fps)
            page.evaluate(f"window.renderFrame({t_sec});")
            frame_path = frames_dir / f"frame_{f:05d}.png"
            page.locator("#c").screenshot(path=str(frame_path))
            if f % 250 == 0 or f == total_frames - 1:
                prog = (f + 1) / total_frames * 100.0
                fps_render = (f + 1) / max(0.1, time.time() - t0)
                print(f"[RENDER] Cuadro {f+1}/{total_frames} ({prog:.1f}%) · {fps_render:.1f} fps", flush=True)

        browser.close()

def multiplex_final_video(master_audio: Path, subtitles_ass: Path, fps=30):
    """Multiplexa fotogramas + audio maestro + subtítulos con FFmpeg a 60 fps fluidos."""
    final_video = output_dir / "chapultepec_diorama_9_16.mp4"
    print("[FFMPEG] Multiplexando video final 1080x1920 @ 60 fps con subtítulos incrustados...", flush=True)

    cmd = [
        ffmpeg_bin, "-y",
        "-framerate", str(fps),
        "-i", str((frames_dir / "frame_%05d.png").resolve()),
        "-i", str(master_audio.resolve()),
        "-vf", f"subtitles='{subtitles_ass.name}'",
        "-r", "60",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-shortest",
        str(final_video.resolve())
    ]
    subprocess.run(cmd, cwd=str(output_dir.resolve()), check=True)
    print(f"[FFMPEG] ¡Video compilado con éxito! {final_video} ({final_video.stat().st_size / (1024*1024):.2f} MB)", flush=True)

    # Copiar también directamente a projects/opuscar_/opuscar__720x1280.mp4 (para la UI modal del usuario)
    opuscar_dir = repo_root / "projects" / "opuscar_"
    opuscar_dir.mkdir(parents=True, exist_ok=True)
    target_modal = opuscar_dir / "opuscar__720x1280.mp4"
    shutil.copy2(final_video, target_modal)
    print(f"[MODAL] Actualizado video de la interfaz: {target_modal}", flush=True)

    # Copiar a directorio de artefactos
    brain_dir = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a")
    artifact_vid = brain_dir / "video_chapultepec_diorama_9_16.mp4"
    shutil.copy2(final_video, artifact_vid)
    print(f"[ARTIFACT] Copiado a artefactos: {artifact_vid}", flush=True)

if __name__ == "__main__":
    audio_m4a = build_audio_tracks()
    subs_ass = generate_subtitles_ass()
    render_video_frames(fps=30)
    multiplex_final_video(audio_m4a, subs_ass, fps=30)
