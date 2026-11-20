"""Sound Designer de Alta Fidelidad para el Video 3D del Turbocompresor Automotriz.
Genera efectos de sonido mecánicos hiperrealistas (spool del turbo, válvula wastegate/blow-off,
flujo de gases incandescentes, cojinetes flotantes a 150k RPM, despiece metálico)
y música de fondo documental tecnológica (Tech Ambient a 110 BPM), mezclados con la narración.
"""

import math
import struct
import wave
import subprocess
from pathlib import Path
import numpy as np
import imageio_ffmpeg

SR = 44100

def generate_turbo_mechanical_sfx(total_duration_sec=105.0):
    """Genera la pista completa de efectos de sonido mecánicos y de fluidos para el turbo."""
    n_samples = int(SR * total_duration_sec)
    sfx = np.zeros(n_samples)
    scale = total_duration_sec / 105.0

    # 1. ETAPA 1: Rumble de motor en ralentí + aceleración suave
    dur_st1 = 13.5 * scale
    t_st1 = np.linspace(0, dur_st1, int(SR * dur_st1), False)
    rpm_curve = 800 + 400 * (t_st1 / max(dur_st1, 0.1)) ** 1.5
    f_engine = (rpm_curve / 60) * 2
    phase_eng = 2 * np.pi * np.cumsum(f_engine) / SR
    engine_rumble = (
        np.sin(phase_eng) * 0.45 +
        np.sin(phase_eng * 2) * 0.30 +
        np.sin(phase_eng * 3) * 0.15 +
        np.random.uniform(-1, 1, len(t_st1)) * 0.08
    ) * np.clip(t_st1 / 1.5, 0, 1) * np.clip((dur_st1 - t_st1) / 1.5, 0, 1) * 0.55
    s1 = int(SR * 0.4 * scale)
    e1 = min(n_samples, s1 + len(engine_rumble))
    sfx[s1:e1] += engine_rumble[:e1 - s1]

    # 2. ETAPA 2: Despiece axial - Clicks metálicos de precisión
    click_cues = [14.5 * scale, 17.0 * scale, 19.5 * scale, 22.0 * scale, 24.5 * scale, 27.0 * scale]
    for i, ct in enumerate(click_cues):
        s_idx = int(SR * ct)
        dur_c = 0.28
        t_c = np.linspace(0, dur_c, int(SR * dur_c), False)
        f_metal = 2800 + (i % 3) * 600
        metallic_click = (
            np.sin(2 * np.pi * f_metal * t_c) * 0.6 +
            np.sin(2 * np.pi * (f_metal * 1.6) * t_c) * 0.3 +
            np.random.uniform(-1, 1, len(t_c)) * np.exp(-t_c * 90) * 0.4
        ) * np.exp(-t_c * 24) * 0.65
        e_idx = min(n_samples, s_idx + len(metallic_click))
        if s_idx < n_samples:
            sfx[s_idx:e_idx] += metallic_click[:e_idx - s_idx]

    # 3. ETAPA 3: Lado Caliente - Gases de escape 950°C + giro de turbina
    dur_st3 = 10.5 * scale
    t_st3 = np.linspace(0, dur_st3, int(SR * dur_st3), False)
    exhaust_noise = np.random.uniform(-1, 1, len(t_st3))
    mod_exhaust = np.sin(2 * np.pi * 3.5 * t_st3) * 0.25 + 0.75
    exhaust_flow = exhaust_noise * mod_exhaust * np.clip(t_st3 / 2.0, 0, 1) * np.clip((dur_st3 - t_st3) / 1.5, 0, 1) * 0.40
    f_spool = 600 + 1600 * (t_st3 / max(dur_st3, 0.1)) ** 1.8
    phase_spool = 2 * np.pi * np.cumsum(f_spool) / SR
    turbine_whistle = np.sin(phase_spool) * (t_st3 / max(dur_st3, 0.1)) * 0.22
    s3 = int(SR * 28.5 * scale)
    e3 = min(n_samples, s3 + len(t_st3))
    if s3 < n_samples:
        sfx[s3:e3] += (exhaust_flow + turbine_whistle)[:e3 - s3]

    # 4. ETAPA 4: Cartucho CHRA - Giro a 150,000 RPM (2500 Hz) y lubricación
    dur_st4 = 11.5 * scale
    t_st4 = np.linspace(0, dur_st4, int(SR * dur_st4), False)
    f_bearing = 2500
    phase_bearing = 2 * np.pi * f_bearing * t_st4
    bearing_whine = (
        np.sin(phase_bearing) * 0.18 +
        np.sin(phase_bearing * 2) * 0.08 +
        np.random.uniform(-1, 1, len(t_st4)) * 0.06
    ) * np.clip(t_st4 / 1.8, 0, 1) * np.clip((dur_st4 - t_st4) / 1.8, 0, 1) * 0.45
    s4 = int(SR * 39.5 * scale)
    e4 = min(n_samples, s4 + len(t_st4))
    if s4 < n_samples:
        sfx[s4:e4] += bearing_whine[:e4 - s4]

    # 5. ETAPA 5: Lado Frío - Succión de aire exterior comprimido
    dur_st5 = 10.0 * scale
    t_st5 = np.linspace(0, dur_st5, int(SR * dur_st5), False)
    intake_noise = np.random.uniform(-1, 1, len(t_st5))
    intake_flow = intake_noise * np.exp(-((t_st5 - dur_st5 * 0.5) ** 2) / (dur_st5 * 2)) * 0.42
    f_comp = 1800 + 1200 * np.sin(t_st5 * 0.8) ** 2
    comp_whistle = np.sin(2 * np.pi * np.cumsum(f_comp) / SR) * 0.18
    s5 = int(SR * 52.0 * scale)
    e5 = min(n_samples, s5 + len(t_st5))
    if s5 < n_samples:
        sfx[s5:e5] += (intake_flow + comp_whistle)[:e5 - s5]

    # 6. ETAPA 6: Válvula Wastegate y Descarga de Sobrepresión ("PSSSHHH-tu-tu-tu")
    bov_cues = [63.0 * scale, 68.0 * scale]
    for bt in bov_cues:
        s_bov = int(SR * bt)
        if s_bov >= n_samples: continue
        dur_bov = 1.4
        t_b = np.linspace(0, dur_bov, int(SR * dur_bov), False)
        whoosh_bov = np.random.uniform(-1, 1, len(t_b)) * np.exp(-t_b * 3.8) * 0.65
        flutter_mod = np.sin(2 * np.pi * 18 * t_b) * 0.4 + 0.6
        bov_sound = whoosh_bov * flutter_mod
        e_bov = min(n_samples, s_bov + len(bov_sound))
        sfx[s_bov:e_bov] += bov_sound[:e_bov - s_bov]

    # 7. ETAPA 7: Régimen Continuo a Plena Carga (Full Boost)
    dur_st7 = 11.0 * scale
    t_st7 = np.linspace(0, dur_st7, int(SR * dur_st7), False)
    f_full = 1800 + 1500 * (t_st7 / max(dur_st7, 0.1)) ** 0.8
    full_spool = np.sin(2 * np.pi * np.cumsum(f_full) / SR) * 0.25
    engine_full = (
        np.sin(2 * np.pi * 85 * t_st7) * 0.35 +
        np.sin(2 * np.pi * 170 * t_st7) * 0.25 +
        np.random.uniform(-1, 1, len(t_st7)) * 0.12
    ) * np.clip(t_st7 / 1.0, 0, 1) * np.clip((dur_st7 - t_st7) / 2.0, 0, 1) * 0.50
    s7 = int(SR * 73.0 * scale)
    e7 = min(n_samples, s7 + len(t_st7))
    if s7 < n_samples:
        sfx[s7:e7] += (full_spool + engine_full)[:e7 - s7]

    # Normalizar SFX
    peak = np.max(np.abs(sfx))
    if peak > 0:
        sfx = sfx / peak * 0.88
    return sfx

def compose_tech_documentary_bgm(total_duration_sec=105.0):
    """Compone una pista documental técnica electrónica (Tech Ambient / Pulse) a 110 BPM."""
    bpm = 110
    beat_dur = 60.0 / bpm  # 0.545 seg
    bar_dur = beat_dur * 4  # 2.18 seg
    n_samples = int(SR * total_duration_sec)
    bgm = np.zeros(n_samples)

    # Samples de percusión electrónica moderna
    dur_k = 0.20
    t_k = np.linspace(0, dur_k, int(SR * dur_k), False)
    kick = np.sin(2 * np.pi * (120 * np.exp(-t_k * 25) + 38) * t_k) * np.exp(-t_k * 16) * 0.8

    dur_h = 0.05
    t_h = np.linspace(0, dur_h, int(SR * dur_h), False)
    hihat = np.random.uniform(-1, 1, len(t_h)) * np.exp(-t_h * 65) * 0.22

    dur_sn = 0.16
    t_sn = np.linspace(0, dur_sn, int(SR * dur_sn), False)
    snare = np.random.uniform(-1, 1, len(t_sn)) * np.exp(-t_sn * 28) * 0.45

    total_bars = int(math.ceil(total_duration_sec / bar_dur))

    # Progresión documental sofisticada en La menor (Am -> F -> C -> G)
    bass_roots = [55.0, 43.65, 65.41, 48.99]
    pad_frequencies = [
        [220.0, 261.63, 329.63],  # Am
        [174.61, 220.0, 261.63],  # F
        [261.63, 329.63, 392.0],  # C
        [196.0, 246.94, 293.66],  # G
    ]

    for b in range(total_bars):
        bar_start = int(SR * (b * bar_dur))
        chord_i = b % 4
        root = bass_roots[chord_i]
        pad_notes = pad_frequencies[chord_i]

        # 1. Pulso de Bajo Sintetizado en corcheas (8th notes)
        for eighth in range(8):
            eighth_sample = bar_start + int(SR * (eighth * beat_dur / 2))
            if eighth_sample < n_samples:
                dur_b = 0.18
                t_b = np.linspace(0, dur_b, int(SR * dur_b), False)
                sig_b = (np.sin(2 * np.pi * root * t_b) + 0.3 * np.sin(2 * np.pi * (root * 2) * t_b)) * np.exp(-t_b * 12) * 0.35
                end_b = min(n_samples, eighth_sample + len(sig_b))
                bgm[eighth_sample:end_b] += sig_b[:end_b - eighth_sample]

        # 2. Padrón rítmico minimalista de batería
        for beat in range(4):
            beat_sample = bar_start + int(SR * (beat * beat_dur))
            # Kick en 1 y 3
            if beat in [0, 2] and beat_sample < n_samples:
                end_k = min(n_samples, beat_sample + len(kick))
                bgm[beat_sample:end_k] += kick[:end_k - beat_sample]
            # Snare en 2 y 4
            if beat in [1, 3] and beat_sample < n_samples:
                end_sn = min(n_samples, beat_sample + len(snare))
                bgm[beat_sample:end_sn] += snare[:end_sn - beat_sample]
            # Hi-hat en cada tiempo
            if beat_sample < n_samples:
                end_h = min(n_samples, beat_sample + len(hihat))
                bgm[beat_sample:end_h] += hihat[:end_h - beat_sample]

        # 3. Pad atmosférico de sintetizador sostenido en cada compás
        if bar_start < n_samples:
            dur_pad = bar_dur
            t_pad = np.linspace(0, dur_pad, int(SR * dur_pad), False)
            sig_pad = np.zeros(len(t_pad))
            for note in pad_notes:
                sig_pad += np.sin(2 * np.pi * note * t_pad) + 0.2 * np.sin(2 * np.pi * (note * 2) * t_pad)
            # Envolvente suave de pad
            env_pad = np.sin(np.pi * t_pad / dur_pad) * 0.14
            sig_pad = sig_pad * env_pad
            end_pad = min(n_samples, bar_start + len(sig_pad))
            bgm[bar_start:end_pad] += sig_pad[:end_pad - bar_start]

    # Envolvente general (Fade in 1s y Fade out 2.5s)
    t_all = np.linspace(0, total_duration_sec, n_samples, False)
    fade_in = np.clip(t_all / 1.2, 0.0, 1.0)
    fade_out = np.clip((total_duration_sec - t_all) / 2.5, 0.0, 1.0)
    bgm = bgm * fade_in * fade_out

    peak = np.max(np.abs(bgm))
    if peak > 0:
        bgm = bgm / peak * 0.75
    return bgm

def build_turbo_soundtrack_master(proj_dir: Path, narration_wav: Path, total_sec: float = None):
    """Genera SFX, BGM y crea la pista de audio maestra del turbocompresor."""
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    if total_sec is None and narration_wav.exists():
        with wave.open(str(narration_wav), "r") as wf:
            total_sec = wf.getnframes() / float(wf.getframerate())
    if total_sec is None:
        total_sec = 84.0

    print(f"[TURBO SOUND] Generando efectos mecánicos y BGM tecnológico para {total_sec:.2f}s...")

    # 1. Pista de SFX mecánicos
    sfx_sig = generate_turbo_mechanical_sfx(total_sec)
    sfx_wav = proj_dir / "turbo_sfx_track.wav"
    sfx_int16 = np.int16(np.clip(sfx_sig, -1.0, 1.0) * 32767)
    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(sfx_int16.tobytes())

    # 2. Pista de Música BGM
    bgm_sig = compose_tech_documentary_bgm(total_sec)
    bgm_wav = proj_dir / "turbo_bgm_track.wav"
    bgm_int16 = np.int16(np.clip(bgm_sig, -1.0, 1.0) * 32767)
    with wave.open(str(bgm_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(bgm_int16.tobytes())

    # 3. Mezcla profesional con FFmpeg
    # - Voz de Dalia: 1.25 (impecable, cristalina y dominante al frente)
    # - BGM: 0.06 (-24.4 dB, fondo ambiental sutil)
    # - SFX: 0.15 (-16.5 dB, acentos mecánicos suaves que no tapan la voz)
    master_audio = proj_dir / "turbo_master_soundtrack_mixed.m4a"
    filter_complex = (
        "[0:a]volume=1.25,alimiter=limit=0.98[vox];"
        "[1:a]volume=0.06,lowpass=f=6000[music];"
        "[2:a]volume=0.15,lowpass=f=7500[sfx];"
        "[vox][music][sfx]amix=inputs=3:duration=first:dropout_transition=2[outa]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(narration_wav.resolve()),
        "-i", str(bgm_wav.resolve()),
        "-i", str(sfx_wav.resolve()),
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        str(master_audio.resolve())
    ]
    subprocess.run(cmd, check=True)
    print(f"[TURBO SOUND] Master de audio completo -> {master_audio}")
    return master_audio

if __name__ == "__main__":
    p_dir = Path(__file__).resolve().parent.parent.parent / "projects" / "showcase_turbocharger_vertical_9_16"
    narr = p_dir / "narration_turbo_master.wav"
    build_turbo_soundtrack_master(p_dir, narr)
