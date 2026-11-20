import asyncio
import edge_tts
import soundfile as sf
import io
import numpy as np

# Definición de subtítulos y narración 100% IDÉNTICOS palabra por palabra
SUB_CHUNKS = [
    # STAGE 1 (0:00 - 15:00)
    {"stage": 1, "t_start": 0.8, "text": "¿Cómo produce un motor pequeño la fuerza de un gigante?", "display": "¿Cómo produce un motor pequeño\\Nla fuerza de un gigante?"},
    {"stage": 1, "t_start": 4.6, "text": "El secreto es el turbocompresor: recicla energía desperdiciada...", "display": "El secreto es el turbocompresor:\\Nrecicla energía desperdiciada..."},
    {"stage": 1, "t_start": 9.2, "text": "¡Para duplicar la potencia y la aceleración del motor!", "display": "¡Para duplicar la potencia\\Ny la aceleración del motor!"},

    # STAGE 2 (15:00 - 30:00)
    {"stage": 2, "t_start": 15.5, "text": "Conozcamos sus cinco componentes clave:", "display": "Conozcamos sus 5 componentes clave:"},
    {"stage": 2, "t_start": 18.5, "text": "Turbina de Inconel y Cartucho CHRA,", "display": "Turbina de Inconel y Cartucho CHRA,"},
    {"stage": 2, "t_start": 21.8, "text": "Rueda compresora de aluminio billet,", "display": "Rueda compresora de aluminio billet,"},
    {"stage": 2, "t_start": 25.2, "text": "Entrada de aire fresco y Válvula wastegate.", "display": "Entrada de aire fresco y Válvula wastegate."},

    # STAGE 3 (30:00 - 45:00)
    {"stage": 3, "t_start": 30.8, "text": "Gases de escape a novecientos cincuenta grados centígrados", "display": "Gases de escape a 950 °C"},
    {"stage": 3, "t_start": 35.2, "text": "chocan contra la turbina de Inconel,", "display": "chocan contra la turbina de Inconel,"},
    {"stage": 3, "t_start": 38.5, "text": "haciéndola girar a velocidades extremas.", "display": "haciéndola girar a velocidades extremas."},

    # STAGE 4 (45:00 - 60:00)
    {"stage": 4, "t_start": 45.8, "text": "En el centro, el cartucho CHRA:", "display": "En el centro, el cartucho CHRA:"},
    {"stage": 4, "t_start": 48.8, "text": "Gira a más de ciento cincuenta mil revoluciones por minuto", "display": "Gira a más de 150,000 RPM"},
    {"stage": 4, "t_start": 53.5, "text": "flotando sobre una película de aceite.", "display": "flotando sobre una película de aceite."},

    # STAGE 5 (60:00 - 75:00)
    {"stage": 5, "t_start": 61.2, "text": "En el lado frío, el compresor billet", "display": "En el lado frío, el compresor billet"},
    {"stage": 5, "t_start": 64.6, "text": "aspira aire fresco del exterior", "display": "aspira aire fresco del exterior"},
    {"stage": 5, "t_start": 67.8, "text": "y lo inyecta a alta presión al motor.", "display": "y lo inyecta a alta presión al motor."},

    # STAGE 6 (75:00 - 90:00)
    {"stage": 6, "t_start": 76.5, "text": "Si la presión sube demasiado:", "display": "Si la presión sube demasiado:"},
    {"stage": 6, "t_start": 79.5, "text": "la compuerta wastegate se abre", "display": "la compuerta wastegate se abre"},
    {"stage": 6, "t_start": 82.5, "text": "para proteger el motor de sobrepresión.", "display": "para proteger el motor de sobrepresión."},

    # STAGE 7 (90:00 - 105:00)
    {"stage": 7, "t_start": 91.8, "text": "Energía de escape convertida", "display": "Energía de escape convertida"},
    {"stage": 7, "t_start": 94.6, "text": "en aceleración y eficiencia pura.", "display": "en aceleración y eficiencia pura."},
    {"stage": 7, "t_start": 98.0, "text": "¡Ingeniería automotriz al límite!", "display": "¡Ingeniería automotriz al límite!"},
]

async def measure_and_generate():
    voice = 'es-MX-DaliaNeural'
    rate = '+2%'
    sr = 24000
    total_sec = 105.0
    full_audio = np.zeros(int(total_sec * sr), dtype=np.float32)

    timed_subs = []

    for item in SUB_CHUNKS:
        tts = edge_tts.Communicate(item['text'], voice, rate=rate)
        audio = b''
        async for chunk in tts.stream():
            if chunk['type'] == 'audio':
                audio += chunk['data']
        data, file_sr = sf.read(io.BytesIO(audio))
        if data.ndim > 1:
            data = data.mean(axis=1)
        dur = len(data) / file_sr

        t0 = item['t_start']
        t1 = t0 + dur + 0.25  # pequeño margen de lectura

        idx0 = int(t0 * sr)
        idx1 = idx0 + len(data)
        if idx1 <= len(full_audio):
            full_audio[idx0:idx1] += data
        else:
            full_audio[idx0:] += data[:len(full_audio) - idx0]

        timed_subs.append((t0, t1, item['display'], item['text']))
        print(f"[{t0:05.2f} - {t1:05.2f}] Spoken: \"{item['text']}\" -> Sub: \"{item['display']}\"")

    # Guardar audio maestro de narración
    out_wav = r"C:\Users\angel.cruz\.gemini\antigravity\scratch\neural-tts-studio\projects\showcase_turbocharger_vertical_9_16\narration_turbo_master.wav"
    sf.write(out_wav, full_audio, sr)
    print(f"Master narration saved: {out_wav} ({total_sec}s)")

    # Generar ASS sincronizado al milisegundo
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    ass_lines = [
        "[Script Info]",
        "Title: Turbocompresor Automotriz Educativo 9:16",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "PlayResX: 720",
        "PlayResY: 1280",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: TurboSub,Montserrat,34,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.8,1.5,2,50,50,150,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for t0, t1, disp, _ in timed_subs:
        ass_lines.append(f"Dialogue: 0,{fmt(t0)},{fmt(t1)},TurboSub,,0,0,0,,{disp}")

    out_ass = r"C:\Users\angel.cruz\.gemini\antigravity\scratch\neural-tts-studio\projects\showcase_turbocharger_vertical_9_16\subtitles_turbo_safezone.ass"
    with open(out_ass, 'w', encoding='utf-8') as f:
        f.write("\n".join(ass_lines) + "\n")
    print(f"Master ASS subtitles saved: {out_ass}")

if __name__ == '__main__':
    asyncio.run(measure_and_generate())
