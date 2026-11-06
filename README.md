---
title: Neural TTS Studio
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Neural TTS Studio (Kokoro-82M & Piper ONNX)

Estudio local de **Text-to-Speech (TTS)** neuronal optimizado para CPU mediante **ONNX Runtime**, sin requerir GPU dedicada ni claves de API externas.

## Características principales

1. **Doble Motor Neuronal Local**:
   - **Kokoro-82M v1.0 (Int8 ONNX)**: Voces expresivas en Español (`ef_dora`, `em_alex`, `em_santa`) e Inglés (`af_heart`, `af_bella`, `am_adam`, `bf_emma`, etc.).
   - **Piper TTS (ONNX)**: Síntesis ultrarrápida con voz en Español de México de alta calidad (`es_MX-claude-high`) preinstalada y descarga automática bajo demanda de más voces (`es_ES-sharvard-medium`, `es_ES-davefx-medium`, `en_US-lessac-medium`).
2. **Mezclador de Voz Propia (Voice Blender)**:
   - Permite combinar matemáticamente los vectores de estilo de dos voces de Kokoro para crear un timbre vocal único.
3. **Interfaz Web Interactiva + API REST**:
   - Visualizador de espectro de frecuencias en tiempo real.
   - Descarga directa en formato `.wav` (PCM 16-bit).
   - Documentación interactiva OpenAPI/Swagger en `http://127.0.0.1:7860/docs`.

## Cómo iniciar

Haz doble clic en [`iniciar_tts.bat`](./iniciar_tts.bat) o ejecuta desde la terminal:

```powershell
uv run python app.py
```

Luego abre en tu navegador: **http://127.0.0.1:7860**

## Uso desde otros proyectos (API Local)

Puedes invocar tu servidor TTS desde cualquier script o aplicación con una petición `POST` a `http://127.0.0.1:7860/api/tts`:

```python
import requests

resp = requests.post(
    "http://127.0.0.1:7860/api/tts",
    json={
        "text": "Hola, esta voz fue generada por mi propio servidor local.",
        "engine": "kokoro",
        "voice": "ef_dora",
        "lang": "es",
        "speed": 1.0,
    },
)
with open("salida.wav", "wb") as f:
    f.write(resp.content)
```
