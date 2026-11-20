"""AI VIDEO STUDIO — Pipeline Maestro de Videos Paper-Cut Verticales (9:16).
Cumplimiento estricto de las DIRECTRICES MAESTRAS:
1. Sincronización Audio-Visual 1:1 por Timestamps.
2. Regla de los 2 segundos, Staggered Pop-In y Ken Burns continuo.
3. Cifras dinámicas animadas (6,674 estructuras y 40,000 habitantes) y regla vertical de 15 m.
4. Composición 9:16 artesanal sin emojis estándar.
5. Gancho inmediato en los primeros 3 segundos y cierre interactivo.
"""

import asyncio
import io
import math
import shutil
import subprocess
import time
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from playwright.sync_api import sync_playwright

repo_root = Path(__file__).resolve().parent.parent.parent
output_dir = repo_root / "projects" / "ciudad_maya_diorama"
output_dir.mkdir(parents=True, exist_ok=True)
frames_dir = output_dir / "frames"
frames_dir.mkdir(parents=True, exist_ok=True)

html_template = repo_root / "studio" / "opuscar" / "templates" / "ciudad_maya_diorama.html"
ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
TOTAL_DURATION = 77.0

# 1. GUION PEDAGÓGICO DE 10 ESCENAS CON GANCHO INMEDIATO Y SUBTÍTULOS 1:1
SCRIPT_SCENES = [
    {
        "scene_id": "sc1_hook",
        "t_start": 0.3,
        "text": "Bajo la densa selva de Campeche existía una ciudad maya monumental y nadie la había visto.",
        "subs": [
            (0.3, 3.8, "Bajo la densa selva de Campeche...", "existía una {\\c&H0024E6FF&}CIUDAD MAYA MONUMENTAL{\\c&H00FFFFFF&}..."),
            (3.9, 7.3, "...¡y absolutamente nadie", "la había visto jamás!"),
        ]
    },
    {
        "scene_id": "sc2_expedition",
        "t_start": 7.5,
        "text": "El arqueólogo Luke Auld-Thomas de la Universidad de Tulane analizó datos del sensor láser LiDAR.",
        "subs": [
            (7.5, 11.1, "El arqueólogo {\\c&H0024E6FF&}LUKE AULD-THOMAS{\\c&H00FFFFFF&}", "de la Universidad de Tulane..."),
            (11.3, 14.8, "...analizó datos del {\\c&H0024E6FF&}SENSOR LÁSER LIDAR{\\c&H00FFFFFF&}", "junto a investigadores del INAH."),
        ]
    },
    {
        "scene_id": "sc3_laser_scan",
        "t_start": 15.0,
        "text": "Los pulsos de luz traspasaron la vegetación tropical, revelando el suelo en tres dimensiones.",
        "subs": [
            (15.0, 18.7, "Los {\\c&H0024E6FF&}PULSOS DE LUZ{\\c&H00FFFFFF&} traspasaron la selva,", "penetrándola por completo..."),
            (18.9, 22.3, "...revelando el terreno", "en {\\c&H0024E6FF&}TRES DIMENSIONES{\\c&H00FFFFFF&} sin talar un árbol."),
        ]
    },
    {
        "scene_id": "sc4_structures_counter",
        "t_start": 22.5,
        "text": "Aparecieron seis mil seiscientas setenta y cuatro estructuras prehispánicas ocultas por más de mil años.",
        "subs": [
            (22.5, 26.3, "¡Aparecieron {\\c&H0024E6FF&}6,674 ESTRUCTURAS{\\c&H00FFFFFF&}", "prehispánicas completamente intactas!"),
            (26.5, 29.8, "...que habían permanecido ocultas", "por más de {\\c&H0024E6FF&}MIL AÑOS DE HISTORIA{\\c&H00FFFFFF&}."),
        ]
    },
    {
        "scene_id": "sc5_pyramid_height",
        "t_start": 30.0,
        "text": "Bautizada como Valeriana, su Gran Acrópolis alberga pirámides templo de quince metros de altura.",
        "subs": [
            (30.0, 33.7, "Bautizada como {\\c&H0024E6FF&}VALERIANA{\\c&H00FFFFFF&}:", "su Gran Acrópolis ceremonial..."),
            (33.9, 37.3, "...alberga pirámides templo", "de {\\c&H0024E6FF&}QUINCE METROS DE ALTURA{\\c&H00FFFFFF&}."),
        ]
    },
    {
        "scene_id": "sc6_ballcourt",
        "t_start": 37.5,
        "text": "Encontraron una cancha reglamentaria para el juego de pelota pok-ta-pok y plazas de gobernantes.",
        "subs": [
            (37.5, 41.2, "Encontraron una {\\c&H0024E6FF&}CANCHA REGLAMENTARIA{\\c&H00FFFFFF&}", "para el sagrado {\\c&H0024E6FF&}JUEGO DE PELOTA{\\c&H00FFFFFF&}..."),
            (41.4, 44.8, "...plazas ceremoniales públicas", "y palacios de la élite gobernante."),
        ]
    },
    {
        "scene_id": "sc7_sacbe_causeway",
        "t_start": 45.0,
        "text": "Calzadas elevadas de piedra blanca conectaban los complejos urbanos con terrazas y reservas de agua.",
        "subs": [
            (45.0, 48.7, "Calzadas blancas {\\c&H0024E6FF&}(SACBÉOB){\\c&H00FFFFFF&}", "conectaban los centros cívicos..."),
            (48.9, 52.3, "...con terrazas de cultivo", "y sofisticadas {\\c&H0024E6FF&}RESERVAS DE AGUA{\\c&H00FFFFFF&}."),
        ]
    },
    {
        "scene_id": "sc8_population_scale",
        "t_start": 52.5,
        "text": "Se calcula que más de cuarenta mil personas habitaron esta metrópolis durante su apogeo maya.",
        "subs": [
            (52.5, 56.4, "Se calcula que más de {\\c&H0024E6FF&}40,000 PERSONAS{\\c&H00FFFFFF&}", "habitaron esta urbe..."),
            (56.6, 60.3, "...en su apogeo clásico", "entre el {\\c&H0024E6FF&}750 Y EL 850 D.C.{\\c&H00FFFFFF&}"),
        ]
    },
    {
        "scene_id": "sc9_collapse_drought",
        "t_start": 60.5,
        "text": "Hacia el año novecientos, severas megasequías provocaron su colapso y la selva devoró la ciudad.",
        "subs": [
            (60.5, 64.3, "Hacia el año {\\c&H0024E6FF&}900 D.C.{\\c&H00FFFFFF&}:", "severas megasequías provocaron su colapso..."),
            (64.5, 68.3, "...provocando el abandono,", "y la {\\c&H0024E6FF&}SELVA DEVORÓ LA CIUDAD{\\c&H00FFFFFF&}."),
        ]
    },
    {
        "scene_id": "sc10_closing_cta",
        "t_start": 68.5,
        "text": "Hoy es la segunda urbe maya más grande de la región. ¿Crees que aún hay más ciudades ocultas?",
        "subs": [
            (68.5, 71.5, "Es la {\\c&H0024E6FF&}SEGUNDA URBE MÁS GRANDE{\\c&H00FFFFFF&}", "solo superada por Calakmul."),
            (71.7, 76.8, "¿Crees que aún hay más ciudades ocultas?", "¡{\\c&H0024E6FF&}DEJA TU COMENTARIO Y COMPARTE{\\c&H00FFFFFF&}!"),
        ]
    }
]

async def generate_narration():
    """Genera la pista de locución continua sincronizada para 77.0 segundos."""
    voice = "es-MX-DaliaNeural"
    full_audio = np.zeros(int(TOTAL_DURATION * 24000), dtype=np.float32)

    for sc in SCRIPT_SCENES:
        t_start = sc["t_start"]
        text = sc["text"]
        tts = edge_tts.Communicate(text, voice, rate="+4%")
        buf = b""
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                buf += chunk["data"]
        data, sr = sf.read(io.BytesIO(buf))
        if data.ndim > 1:
            data = data.mean(axis=1)

        idx0 = int(t_start * 24000)
        idx1 = idx0 + len(data)
        if idx1 <= len(full_audio):
            full_audio[idx0:idx1] += data
        else:
            full_audio[idx0:] += data[:len(full_audio) - idx0]
        print(f"Narración [{sc['scene_id']}]: {len(data)/24000:.2f}s en t={t_start:.1f}s")

    out_narr = output_dir / "narration_maya.wav"
    sf.write(str(out_narr), full_audio, 24000)
    return out_narr

def generate_mayan_soundtrack(total_sec=77.0):
    """Genera efectos sonoros de selva/LiDAR y BGM mística prehispánica adaptada a 77s."""
    n_samples = int(SR * total_sec)
    sfx = np.zeros(n_samples)
    bgm = np.zeros(n_samples)

    # SFX: Viento y susurro de hojas en selva tropical
    t = np.linspace(0, total_sec, n_samples, False)
    jungle_wind = np.random.uniform(-1, 1, n_samples) * 0.05

    # Pulsos de escaneo láser LiDAR (en escenas 1, 3 y 4)
    for scan_t in [2.0, 5.0, 15.5, 17.5, 19.5, 22.8, 25.5]:
        s_idx = int(SR * scan_t)
        dur = 0.32
        t_s = np.linspace(0, dur, int(SR * dur), False)
        f_laser = 800 + 1600 * (t_s / dur) ** 2
        laser_chirp = np.sin(2 * np.pi * np.cumsum(f_laser) / SR) * 0.26 * np.exp(-t_s * 7)
        e_idx = min(n_samples, s_idx + len(laser_chirp))
        sfx[s_idx:e_idx] += laser_chirp[:e_idx - s_idx]

    # Campanas místicas de revelación arqueológica
    for bell_t in [7.5, 22.5, 30.0, 37.5, 45.0, 52.5, 68.5]:
        s_idx = int(SR * bell_t)
        dur = 2.2
        t_b = np.linspace(0, dur, int(SR * dur), False)
        bell = (np.sin(2 * np.pi * 528 * t_b) * 0.32 + np.sin(2 * np.pi * 1056 * t_b) * 0.16) * np.exp(-t_b * 1.8)
        e_idx = min(n_samples, s_idx + len(bell))
        sfx[s_idx:e_idx] += bell[:e_idx - s_idx]

    sfx += jungle_wind * 0.3

    # BGM: Fusión Prehispánica Mística
    bar_dur = 2.4
    n_bars = int(math.ceil(total_sec / bar_dur))
    notes = [293.66, 349.23, 392.00, 440.00, 523.25, 440.00, 349.23, 293.66]

    for b in range(n_bars):
        bar_start = int(b * bar_dur * SR)
        dur_drum = 0.55
        t_d = np.linspace(0, dur_drum, int(SR * dur_drum), False)
        drum = np.sin(2 * np.pi * 65 * np.exp(-t_d * 8) * t_d) * np.exp(-t_d * 4.5) * 0.55
        ed = min(n_samples, bar_start + len(drum))
        bgm[bar_start:ed] += drum[:ed - bar_start]

        note_freq = notes[b % len(notes)]
        t_flute = np.linspace(0, bar_dur, int(SR * bar_dur), False)
        flute = (
            np.sin(2 * np.pi * note_freq * t_flute) * 0.28 +
            np.sin(2 * np.pi * note_freq * 2 * t_flute) * 0.10 +
            np.random.uniform(-1, 1, len(t_flute)) * 0.03
        ) * np.sin(np.pi * t_flute / bar_dur) * 0.38
        ef = min(n_samples, bar_start + len(flute))
        bgm[bar_start:ef] += flute[:ef - bar_start]

    sfx_wav = output_dir / "sfx_maya.wav"
    bgm_wav = output_dir / "bgm_maya.wav"
    sf.write(str(sfx_wav), np.int16(np.clip(sfx, -1, 1) * 32767), SR)
    sf.write(str(bgm_wav), np.int16(np.clip(bgm, -1, 1) * 32767), SR)
    return sfx_wav, bgm_wav

def build_master_audio(narr_wav: Path, sfx_wav: Path, bgm_wav: Path):
    """Mezcla con voz dominante clara y ambiente equilibrado."""
    master_m4a = output_dir / "master_audio_maya.m4a"
    filter_complex = (
        "[0:a]volume=1.30,alimiter=limit=0.98[vox];"
        "[1:a]volume=0.06,lowpass=f=6000[music];"
        "[2:a]volume=0.14,lowpass=f=7000[sfx];"
        "[vox][music][sfx]amix=inputs=3:duration=first:dropout_transition=2[outa]"
    )
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(narr_wav.resolve()),
        "-i", str(bgm_wav.resolve()),
        "-i", str(sfx_wav.resolve()),
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        str(master_m4a.resolve())
    ]
    subprocess.run(cmd, check=True)
    return master_m4a

def generate_subtitles_ass():
    """Genera subtítulos Big Focus ASS sincronizados en zona segura (MarginV=230)."""
    sub_path = output_dir / "subtitles_maya.ass"
    header = """[Script Info]
Title: La Ciudad Maya de Valeriana en Campeche — Big Focus Subtitles
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BigFocus,Arial Black,34,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H90000000,-1,0,0,0,100,100,0,0,1,4.2,2.2,2,36,36,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = []
    for sc in SCRIPT_SCENES:
        for item in sc["subs"]:
            t0, t1 = item[0], item[1]
            txt = "\\N".join(item[2:])
            lines.append(f"Dialogue: 0,{fmt(t0)},{fmt(t1)},BigFocus,,0,0,0,,{txt}")

    sub_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return sub_path

def render_video_frames(total_sec=77.0, fps=24):
    """Renderiza los cuadros deterministas con Playwright."""
    total_frames = int(total_sec * fps)
    print(f"[OPUSCAR MAYA] Renderizando {total_frames} cuadros deterministas a 24 fps ({total_sec}s)...", flush=True)
    t0 = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
        )
        page = browser.new_page(viewport={"width": 720, "height": 1280})
        page.goto(f"file:///{html_template.resolve()}")
        page.wait_for_timeout(1000)
        page.evaluate("window.manualMode = true;")

        for f in range(total_frames):
            t_sec = f / float(fps)
            page.evaluate(f"window.renderFrame({t_sec});")
            frame_path = frames_dir / f"frame_{f:05d}.png"
            page.locator("#c").screenshot(path=str(frame_path))
            if f % 200 == 0 or f == total_frames - 1:
                prog = (f + 1) / total_frames * 100.0
                fps_render = (f + 1) / max(0.1, time.time() - t0)
                print(f"[OPUSCAR MAYA] Cuadro {f+1}/{total_frames} ({prog:.1f}%) · {fps_render:.1f} fps", flush=True)

        browser.close()

    render_dur = time.time() - t0
    print(f"[OPUSCAR MAYA] Renderizado completado en {render_dur:.1f}s", flush=True)

def mux_final_video(master_audio: Path, subtitles_ass: Path, total_sec=77.0, fps=24):
    """Compila los fotogramas y la pista de audio a MP4."""
    final_video = output_dir / "ciudad_maya_diorama_9_16.mp4"
    print("[OPUSCAR MAYA] Multiplexando video final con FFmpeg...", flush=True)

    ass_arg = str(subtitles_ass.resolve()).replace("\\", "/").replace(":", "\\:")
    cmd = [
        ffmpeg_bin, "-y",
        "-framerate", str(fps),
        "-i", str((frames_dir / "frame_%05d.png").resolve()),
        "-i", str(master_audio.resolve()),
        "-vf", f"subtitles='{ass_arg}'",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(final_video.resolve())
    ]
    subprocess.run(cmd, check=True)
    print(f"[OPUSCAR MAYA] ¡Video final completado exitosamente!: {final_video}", flush=True)
    return final_video

def main():
    print("=" * 70)
    print("AI VIDEO STUDIO — Pipeline Paper-Cut Maestro: Valeriana en Campeche")
    print("10 Escenas Dinámicas · 77.0 Segundos · 24 FPS Reales")
    print("Cumplimiento 100% Directrices Maestras Paper-Cut (Timestamps, Cifras, Ken Burns)")
    print("=" * 70)

    # 1. Narración continua con Edge TTS
    narr_wav = asyncio.run(generate_narration())

    # 2. SFX + BGM
    sfx_wav, bgm_wav = generate_mayan_soundtrack(TOTAL_DURATION)

    # 3. Audio Maestro
    master_audio = build_master_audio(narr_wav, sfx_wav, bgm_wav)

    # 4. Subtítulos Big Focus
    subtitles_ass = generate_subtitles_ass()

    # 5. Captura determinista de cuadros
    render_video_frames(TOTAL_DURATION, fps=24)

    # 6. Muxing final
    final_video = mux_final_video(master_audio, subtitles_ass, TOTAL_DURATION, fps=24)

    # 7. Replicar a proyectos y vistas web
    targets = [
        repo_root / "projects" / "opuscar_paper_cutout_diorama" / "opuscar_paper_cutout_diorama_720x1280.mp4",
        repo_root / "projects" / "opuscar_blueprint_cad" / "opuscar_blueprint_cad_720x1280.mp4",
        Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a\video_ciudad_maya_diorama_9_16.mp4")
    ]
    for tg in targets:
        tg.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(final_video, tg)
            print(f"[COPIA] Sincronizado a: {tg}")
        except Exception as e:
            print(f"[COPIA ERROR] {e}")

if __name__ == "__main__":
    main()
