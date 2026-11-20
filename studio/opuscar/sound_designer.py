"""Sound Designer procedural para videos diorama y cortos animados.
Genera música de fondo energética (Latin Funk 120 BPM) y efectos de sonido
(SFX) sincronizados al milisegundo con la narración.
"""

import math
import struct
import wave
import subprocess
from pathlib import Path
import numpy as np
import imageio_ffmpeg

SR = 44100

def generate_sfx_elements():
    """Genera efectos de sonido individuales de alta fidelidad."""
    sfx = {}

    # 1. Whoosh + Pop elástico (0:00 - chile cayendo con rebote)
    dur = 0.45
    t = np.linspace(0, dur, int(SR * dur), False)
    # Whoosh (ruido blanco filtrado con barrido)
    noise = np.random.uniform(-1, 1, len(t))
    sweep = np.sin(2 * np.pi * (150 + 600 * t) * t)
    whoosh = noise * 0.4 * np.exp(-((t - 0.15) ** 2) / 0.01) + sweep * 0.3 * (1 - t / dur)
    # Pop / Boing
    t_pop = np.linspace(0, 0.25, int(SR * 0.25), False)
    f_pop = 320 * np.exp(-t_pop * 15) + 120 * np.sin(t_pop * 45)
    pop = np.sin(2 * np.pi * np.cumsum(f_pop) / SR) * np.exp(-t_pop * 18)
    # Combinar
    sig_whoosh_pop = np.copy(whoosh)
    sig_whoosh_pop[int(SR * 0.18):int(SR * 0.18) + len(pop)] += pop * 0.8
    sfx["whoosh_pop"] = sig_whoosh_pop

    # 2. Stamp / Mechanical Ding (caída de placa)
    dur = 0.5
    t = np.linspace(0, dur, int(SR * dur), False)
    impact = np.random.uniform(-1, 1, len(t)) * np.exp(-t * 60) * 0.6
    bell = (np.sin(2 * np.pi * 1046.5 * t) * 0.6 + np.sin(2 * np.pi * 2093.0 * t) * 0.4) * np.exp(-t * 12)
    sfx["stamp_ding"] = impact + bell

    # 3. Sensor Cascade (secuencia de bleeps electrónicos en arpegio)
    dur = 4.5
    cascade = np.zeros(int(SR * dur))
    # 14 bleeps en cascada
    freqs = [440, 523, 587, 659, 783, 880, 1046, 1174, 1318, 1567, 1760, 2093, 2349, 2637]
    for i, f in enumerate(freqs):
        start_sec = i * 0.28
        start_idx = int(SR * start_sec)
        bleep_dur = 0.18
        t_b = np.linspace(0, bleep_dur, int(SR * bleep_dur), False)
        # Tono dual sci-fi con FM
        sig_b = (np.sin(2 * np.pi * f * t_b) + 0.3 * np.sin(2 * np.pi * (f * 2) * t_b)) * np.exp(-t_b * 22)
        end_idx = min(len(cascade), start_idx + len(sig_b))
        cascade[start_idx:end_idx] += sig_b[:end_idx - start_idx] * 0.35
    sfx["sensor_cascade"] = cascade

    # 4. Steam Sizzle ("Tssss" vapor de calor)
    dur = 1.4
    t = np.linspace(0, dur, int(SR * dur), False)
    noise_steam = np.random.uniform(-1, 1, len(t))
    # Modulación de siseo
    envelope = np.exp(-t * 2.8) * (1 - np.exp(-t * 25))
    mod = 1.0 + 0.25 * np.sin(2 * np.pi * 18 * t)
    sfx["steam_sizzle"] = noise_steam * envelope * mod * 0.45

    # 5. Water Drops (gotas de sudor y lágrimas "plop-bloop")
    dur = 4.0
    drops = np.zeros(int(SR * dur))
    drop_times = [0.1, 0.6, 1.2, 1.9, 2.5, 3.2]
    for i, dt in enumerate(drop_times):
        start_idx = int(SR * dt)
        dur_d = 0.12
        t_d = np.linspace(0, dur_d, int(SR * dur_d), False)
        # Barrido de tono ascendente característico de gota de agua (1400Hz -> 2200Hz)
        base_f = 1200 + (i % 3) * 200
        freq_sweep = base_f + 800 * (t_d / dur_d) ** 0.5
        sig_d = np.sin(2 * np.pi * np.cumsum(freq_sweep) / SR) * np.exp(-t_d * 35)
        end_idx = min(len(drops), start_idx + len(sig_d))
        drops[start_idx:end_idx] += sig_d[:end_idx - start_idx] * 0.55
    sfx["water_drops"] = drops

    # 6. Ta-Da Fanfare (acorde festivo latino)
    dur = 1.2
    t = np.linspace(0, dur, int(SR * dur), False)
    # Acorde mayor brillante (Do, Mi, Sol, Do octava)
    chord = (
        np.sin(2 * np.pi * 523.25 * t) * 0.35 +
        np.sin(2 * np.pi * 659.25 * t) * 0.35 +
        np.sin(2 * np.pi * 783.99 * t) * 0.35 +
        np.sin(2 * np.pi * 1046.50 * t) * 0.40
    ) * np.exp(-t * 3.5)
    sfx["tada_fanfare"] = chord

    # 7. Magic Sparkles (cascada de campanitas de endorfinas)
    dur = 3.5
    sparkles = np.zeros(int(SR * dur))
    # 12 notas de celesta en escala pentatónica
    pentatonic = [1046.5, 1174.7, 1318.5, 1567.9, 1760.0, 2093.0, 2349.3, 2637.0, 3136.0]
    for i in range(16):
        f = pentatonic[i % len(pentatonic)]
        st = i * 0.18 + np.random.uniform(0, 0.05)
        s_idx = int(SR * st)
        t_chime = np.linspace(0, 0.35, int(SR * 0.35), False)
        sig_chime = np.sin(2 * np.pi * f * t_chime) * np.exp(-t_chime * 14)
        e_idx = min(len(sparkles), s_idx + len(sig_chime))
        sparkles[s_idx:e_idx] += sig_chime[:e_idx - s_idx] * 0.25
    sfx["magic_sparkles"] = sparkles

    # 8. Boxing Ring Bell (campana metálica de ring "Clang-Clang!")
    dur = 1.8
    bell_track = np.zeros(int(SR * dur))
    for hit_time in [0.0, 0.35]:
        hit_idx = int(SR * hit_time)
        t_bell = np.linspace(0, 1.2, int(SR * 1.2), False)
        # Frecuencias armónicas metálicas de campana
        b_sig = (
            np.sin(2 * np.pi * 1318.5 * t_bell) * 0.5 +
            np.sin(2 * np.pi * 2637.0 * t_bell) * 0.3 +
            np.sin(2 * np.pi * 3951.0 * t_bell) * 0.2
        ) * np.exp(-t_bell * 4.5)
        end_b = min(len(bell_track), hit_idx + len(t_bell))
        bell_track[hit_idx:end_b] += b_sig[:end_b - hit_idx] * 0.6
    sfx["boxing_bell"] = bell_track

    return sfx

def compose_latin_funk_bgm(total_duration_sec=38.3):
    """Compone una pista completa de Latin Funk / Cumbia Groove a 120 BPM."""
    bpm = 120
    beat_dur = 60.0 / bpm  # 0.5 seg
    bar_dur = beat_dur * 4  # 2.0 seg
    n_samples = int(SR * total_duration_sec)
    bgm = np.zeros(n_samples)

    # Definir samples de batería individuales
    # Kick
    dur_k = 0.22
    t_k = np.linspace(0, dur_k, int(SR * dur_k), False)
    f_k = 140 * np.exp(-t_k * 30) + 42
    kick = np.sin(2 * np.pi * np.cumsum(f_k) / SR) * np.exp(-t_k * 14) * 0.85

    # Snare / Rimshot
    dur_s = 0.18
    t_s = np.linspace(0, dur_s, int(SR * dur_s), False)
    snare = (np.random.uniform(-1, 1, len(t_s)) * 0.7 + np.sin(2 * np.pi * 240 * t_s) * 0.3) * np.exp(-t_s * 25) * 0.55

    # Hi-hat / Maraca
    dur_h = 0.06
    t_h = np.linspace(0, dur_h, int(SR * dur_h), False)
    hihat = np.random.uniform(-1, 1, len(t_h)) * np.exp(-t_h * 70) * 0.28

    # Construir bucles de compás
    total_bars = int(math.ceil(total_duration_sec / bar_dur))

    # Progresión armónica: Re menor -> Fa mayor -> Sol menor -> La 7
    # Frecuencias de bajo (Re=73.4Hz, Fa=87.3Hz, Sol=98.0Hz, La=110.0Hz)
    chords_bass = [73.42, 87.31, 97.99, 110.00]
    # Tríadas para piano/órgano
    chords_piano = [
        [293.66, 349.23, 440.00],  # Dm
        [349.23, 440.00, 523.25],  # F
        [392.00, 466.16, 587.33],  # Gm
        [440.00, 554.37, 659.25],  # A
    ]

    for b in range(total_bars):
        bar_start_sec = b * bar_dur
        bar_idx = int(SR * bar_start_sec)
        chord_idx = b % 4
        root_f = chords_bass[chord_idx]
        piano_notes = chords_piano[chord_idx]

        # 1. Batería en el compás (4 tiempos)
        for beat in range(4):
            beat_time = beat * beat_dur
            beat_sample = bar_idx + int(SR * beat_time)

            # Kick en tiempo 1, tiempo 3 y síncopa en 2.5
            if beat in [0, 2]:
                end_k = min(n_samples, beat_sample + len(kick))
                if beat_sample < n_samples:
                    bgm[beat_sample:end_k] += kick[:end_k - beat_sample]

            # Ghost kick sincopado latino
            if beat == 1:
                ghost_sample = beat_sample + int(SR * (beat_dur * 0.5))
                end_gk = min(n_samples, ghost_sample + len(kick))
                if ghost_sample < n_samples:
                    bgm[ghost_sample:end_gk] += kick[:end_gk - ghost_sample] * 0.6

            # Snare en tiempos 2 y 4
            if beat in [1, 3]:
                end_s = min(n_samples, beat_sample + len(snare))
                if beat_sample < n_samples:
                    bgm[beat_sample:end_s] += snare[:end_s - beat_sample]

            # Hi-hat en semicorcheas (16th notes)
            for sub in range(4):
                sub_sample = beat_sample + int(SR * (sub * beat_dur / 4))
                end_h = min(n_samples, sub_sample + len(hihat))
                accent = 1.2 if sub % 2 == 0 else 0.7
                if sub_sample < n_samples:
                    bgm[sub_sample:end_h] += hihat[:end_h - sub_sample] * accent

            # Acorde de Piano / Órgano a contratiempo (off-beat reggae/funk)
            offbeat_sample = beat_sample + int(SR * (beat_dur * 0.5))
            if offbeat_sample < n_samples:
                dur_p = 0.16
                t_p = np.linspace(0, dur_p, int(SR * dur_p), False)
                chord_sig = np.zeros(len(t_p))
                for note in piano_notes:
                    chord_sig += np.sin(2 * np.pi * note * t_p) + 0.3 * np.sin(2 * np.pi * (note * 2) * t_p)
                chord_sig = chord_sig * np.exp(-t_p * 18) * 0.22
                end_p = min(n_samples, offbeat_sample + len(chord_sig))
                bgm[offbeat_sample:end_p] += chord_sig[:end_p - offbeat_sample]

        # 2. Línea de bajo Funk sincronizada (Root -> Octave -> Fifth)
        bass_pattern = [
            (0.0, root_f, 0.28),
            (0.375, root_f * 2, 0.18),
            (0.75, root_f * 1.5, 0.22),
            (1.0, root_f, 0.25),
            (1.375, root_f * 1.33, 0.18),
            (1.75, root_f * 1.5, 0.20),
        ]
        for note_rel_t, note_f, note_len in bass_pattern:
            note_sample = bar_idx + int(SR * (note_rel_t * beat_dur * 2))
            if note_sample < n_samples:
                t_b = np.linspace(0, note_len, int(SR * note_len), False)
                # Tono con armónicos cálidos de bajo analógico
                sig_bass = (
                    np.sin(2 * np.pi * note_f * t_b) * 0.7 +
                    np.sin(2 * np.pi * (note_f * 2) * t_b) * 0.25 +
                    np.sin(2 * np.pi * (note_f * 3) * t_b) * 0.1
                ) * np.exp(-t_b * 7) * 0.45
                end_b = min(n_samples, note_sample + len(sig_bass))
                bgm[note_sample:end_b] += sig_bass[:end_b - note_sample]

    # Aplicar envolvente general: Fade-in suave (0.5s) y Fade-out musical final (2.0s)
    t_all = np.linspace(0, total_duration_sec, n_samples, False)
    fade_in = np.clip(t_all / 0.6, 0.0, 1.0)
    fade_out = np.clip((total_duration_sec - t_all) / 2.2, 0.0, 1.0)
    bgm = bgm * fade_in * fade_out

    # Normalizar master de música
    peak = np.max(np.abs(bgm))
    if peak > 0:
        bgm = bgm / peak * 0.85

    return bgm

def build_complete_soundtrack(output_dir: Path, narration_file: Path):
    """Genera la pista de SFX, BGM y las mezcla con la narración en alta calidad."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    # 1. Medir duración exacta de la narración
    res = subprocess.run([ffmpeg_bin, "-i", str(narration_file.resolve())], capture_output=True, text=True)
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    total_sec = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3)) if m else 38.28

    print(f"[AUDIO] Generando elementos sonoros para {total_sec:.2f} segundos...")

    # 2. Generar SFX procedurables
    sfx_dict = generate_sfx_elements()
    sfx_track = np.zeros(int(SR * total_sec))

    # Colocar los efectos en la línea de tiempo exacta
    cue_points = [
        ("whoosh_pop", 0.35, 0.95),       # Gancho: Chile entra con rebote
        ("stamp_ding", 1.20, 0.80),       # Gancho: Placa ¿FUEGO REAL? aterriza
        ("sensor_cascade", 5.64, 0.75),   # Escena 2: Receptores TRPV1 en gradas se activan
        ("steam_sizzle", 16.10, 0.85),    # Escena 3: Calor y siseo de sudor
        ("water_drops", 17.50, 0.90),     # Escena 3: Gotas de sudor y lágrimas plop-plop
        ("tada_fanfare", 25.25, 0.80),    # Escena 4: Entrada festiva de tacos y comida
        ("magic_sparkles", 26.50, 0.70),  # Escena 4: Lluvia dorada de endorfinas
        ("boxing_bell", 33.99, 0.95),     # Escena 5: ¡Ding-Ding! Duelo Versus
    ]

    for name, start_t, gain in cue_points:
        sig = sfx_dict[name]
        start_idx = int(SR * start_t)
        end_idx = min(len(sfx_track), start_idx + len(sig))
        if start_idx < len(sfx_track):
            sfx_track[start_idx:end_idx] += sig[:end_idx - start_idx] * gain

    # Exportar pista de SFX a WAV
    sfx_wav = output_dir / "sfx_track.wav"
    sfx_int16 = np.int16(np.clip(sfx_track, -1.0, 1.0) * 32767)
    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(sfx_int16.tobytes())

    # 3. Componer la pista de música BGM (Latin Funk)
    bgm_sig = compose_latin_funk_bgm(total_sec)
    bgm_wav = output_dir / "bgm_track.wav"
    bgm_int16 = np.int16(np.clip(bgm_sig, -1.0, 1.0) * 32767)
    with wave.open(str(bgm_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(bgm_int16.tobytes())

    # 4. Mezclar profesionalmente con FFmpeg:
    # - Voz: 0 dB (volumen 1.0, cristalina)
    # - BGM: -19 dB (volumen 0.14, base rítmica de acompañamiento envolvente)
    # - SFX: -4 dB (volumen 0.65, acentos punchy)
    master_audio = output_dir / "master_audio_mixed.m4a"
    filter_complex = (
        "[0:a]volume=1.05[vox];"
        "[1:a]volume=0.15,lowpass=f=7500[music];"
        "[2:a]volume=0.75[sfx];"
        "[vox][music][sfx]amix=inputs=3:duration=first:dropout_transition=2[outa]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(narration_file.resolve()),
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
    print(f"[AUDIO] Master de Audio Completo -> {master_audio}")
    return master_audio

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent.parent
    proj_dir = base_dir / "projects" / "chile_capsaicina_diorama"
    narr_file = base_dir / "full_narration_chile.mp3"
    build_complete_soundtrack(proj_dir, narr_file)
