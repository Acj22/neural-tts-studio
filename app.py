import base64
import io
import random
import json
import os
import re
import threading
import time
import uuid
import wave
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import numpy as np
import requests
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from kokoro_onnx import Kokoro
from piper import PiperVoice, SynthesisConfig
from pydantic import BaseModel, Field

import video_pipeline
import frutinovela as fruti
from PIL import Image
from video_pipeline import (
    analyze_reference_image,
    build_scene_prompt,
    create_project_zip,
    format_mm_ss,
    generate_image_for_scene,
    generate_srt_content,
    populate_timestamp_visual_prompts,
    render_project_video,
    split_script_into_scenes,
    translate_es_to_en,
)

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
PROJECTS_DIR = BASE_DIR / "projects"
MODELS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

SETTINGS_FILE = BASE_DIR / "settings.json"
if SETTINGS_FILE.exists():
    try:
        video_pipeline.IMAGE_SETTINGS.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except Exception as exc:
        print(f"Aviso: no se pudo leer settings.json: {exc}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Precargar modelos principales en memoria al iniciar el servidor
    try:
        engines.get_kokoro()
        for default_piper in ("es_MX-ald-medium", "es_MX-claude-high"):
            if (MODELS_DIR / f"{default_piper}.onnx").exists():
                engines.get_piper(default_piper)
    except Exception as e:
        print(f"Aviso al precargar modelos: {e}")
    yield


app = FastAPI(
    title="Neural TTS Studio API",
    description="Servidor local de Text-to-Speech neuronal con Kokoro-82M y Piper ONNX",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Protección opcional con contraseña (ej. en Hugging Face Spaces): define el secreto APP_PASSWORD
_APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
if _APP_PASSWORD:
    import secrets as _secrets

    @app.middleware("http")
    async def _basic_auth_middleware(request, call_next):
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("basic "):
            try:
                _user, _, pwd = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
                if _secrets.compare_digest(pwd, _APP_PASSWORD):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            content="Acceso restringido",
            headers={"WWW-Authenticate": 'Basic realm="Neural TTS Studio"'},
        )

# Catálogo de voces de Kokoro (incluye voces puras y perfiles masculinos en español premezclados)
KOKORO_VOICE_CATALOG = {
    # --- ESPAÑOL MASCULINAS ---
    "em_alex": {
        "name": "🇲🇽/🌎 Alex (Español · Masculina Estándar)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Neutro",
    },
    "em_santa": {
        "name": "🇲🇽/🌎 Santa (Español · Masculina Cálida/Profunda)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Profundo",
    },
    "es_m_mateo": {
        "name": "🎙️ Mateo (Español · Masculina Locutor Grave)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Radio / Locución",
        "recipe": ("em_alex", "am_onyx", 0.45),
    },
    "es_m_daniel": {
        "name": "🎬 Daniel (Español · Masculina Narrador Documental)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Documental",
        "recipe": ("em_alex", "bm_daniel", 0.42),
    },
    "es_m_eric": {
        "name": "🎧 Eric (Español · Masculina Podcast / Conversacional)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Natural",
        "recipe": ("em_alex", "am_eric", 0.45),
    },
    "es_m_liam": {
        "name": "⚡ Liam (Español · Masculina Joven / Dinámica)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Juvenil",
        "recipe": ("em_alex", "am_liam", 0.45),
    },
    "es_m_braulio": {
        "name": "🔥 Braulio (Español · Masculina Épica / Tráiler)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Intenso",
        "recipe": ("em_santa", "am_fenrir", 0.50),
    },
    "es_m_marco": {
        "name": "📖 Marco (Español · Masculina Audiolibro Sereno)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Pausado",
        "recipe": ("em_alex", "bm_george", 0.40),
    },
    "im_nicola": {
        "name": "🌊 Nicola (Español · Masculina Timbre Mediterráneo)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Melódico",
    },
    "am_onyx": {
        "name": "🔊 Onyx (Español · Masculina Voz Ultra Grave)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Grave",
    },
    "am_echo": {
        "name": "🌙 Echo (Español · Masculina Suave / Reflexiva)",
        "lang": "es-mx",
        "gender": "Masculina",
        "accent": "Español Suave",
    },
    # --- ESPAÑOL FEMENINAS ---
    "ef_dora": {
        "name": "🇲🇽/🌎 Dora (Español · Femenina Estándar)",
        "lang": "es-mx",
        "gender": "Femenina",
        "accent": "Español Neutro",
    },
    "es_f_valeria": {
        "name": "✨ Valeria (Español · Femenina Cálida / Narrativa)",
        "lang": "es-mx",
        "gender": "Femenina",
        "accent": "Español Expresivo",
        "recipe": ("ef_dora", "af_heart", 0.35),
    },
    "es_f_sofia": {
        "name": "🎙️ Sofía (Español · Femenina Profesional)",
        "lang": "es-mx",
        "gender": "Femenina",
        "accent": "Español Noticias",
        "recipe": ("ef_dora", "af_bella", 0.35),
    },
    # --- INGLÉS ---
    "af_heart": {"name": "🇺🇸 Heart (English US ★)", "lang": "en-us", "gender": "Femenina", "accent": "EE.UU. Expresiva"},
    "af_bella": {"name": "🇺🇸 Bella (English US)", "lang": "en-us", "gender": "Femenina", "accent": "EE.UU. Narrativa"},
    "af_nova": {"name": "🇺🇸 Nova (English US)", "lang": "en-us", "gender": "Femenina", "accent": "EE.UU. Clara"},
    "am_adam": {"name": "🇺🇸 Adam (English US)", "lang": "en-us", "gender": "Masculina", "accent": "EE.UU. Narrador"},
    "am_michael": {"name": "🇺🇸 Michael (English US)", "lang": "en-us", "gender": "Masculina", "accent": "EE.UU. Natural"},
    "am_fenrir": {"name": "🇺🇸 Fenrir (English US)", "lang": "en-us", "gender": "Masculina", "accent": "EE.UU. Enérgica"},
    "bf_emma": {"name": "🇬🇧 Emma (English UK)", "lang": "en-gb", "gender": "Femenina", "accent": "Británico"},
    "bm_george": {"name": "🇬🇧 George (English UK)", "lang": "en-gb", "gender": "Masculina", "accent": "Británico"},
}

PIPER_MODELS_CATALOG = {
    "es_MX-ald-medium": {
        "name": "🇲🇽 Ald (Español México · Masculina)",
        "lang": "es-MX",
        "gender": "Masculina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json",
    },
    "es_ES-davefx-medium": {
        "name": "🇪🇸 DaveFX (Español España · Masculina Narrador)",
        "lang": "es-ES",
        "gender": "Masculina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
    },
    "es_ES-carlfm-x_low": {
        "name": "🇪🇸 CarlFM (Español España · Masculina Ultrarrápida)",
        "lang": "es-ES",
        "gender": "Masculina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx.json",
    },
    "es_MX-claude-high": {
        "name": "🇲🇽 Claude (Español México · Femenina Alta Calidad)",
        "lang": "es-MX",
        "gender": "Femenina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx.json",
    },
    "es_AR-daniela-high": {
        "name": "🇦🇷 Daniela (Español Argentina · Femenina Alta Calidad)",
        "lang": "es-AR",
        "gender": "Femenina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx.json",
    },
    "es_ES-sharvard-medium": {
        "name": "🇪🇸 Sharvard (Español España · Masculina/Femenina)",
        "lang": "es-ES",
        "gender": "Masculina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json",
    },
    "en_US-lessac-medium": {
        "name": "🇺🇸 Lessac (English US · Femenina Natural)",
        "lang": "en-US",
        "gender": "Femenina",
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    },
}

# Catálogo de voces Ultra-Naturales gratuitas de Microsoft Edge Neural HD (sin cuenta ni suscripción)
EDGE_NEURAL_VOICE_CATALOG = {
    # --- MASCULINAS ESPAÑOL & MULTILINGUAL HD ---
    "es-MX-JorgeNeural": {
        "name": "🇲🇽 Jorge Neural HD (México · Masculina Cálida YouTube ★)",
        "lang": "es-MX",
        "gender": "Masculina",
        "accent": "México Natural",
    },
    "es-US-AlonsoNeural": {
        "name": "🌎 Alonso Neural HD (Latino Neutro · Locutor Documental ★)",
        "lang": "es-US",
        "gender": "Masculina",
        "accent": "Latino Neutro",
    },
    "en-US-AndrewMultilingualNeural": {
        "name": "🎙️ Andrew Multilingual HD (Masculina Podcast Realista · Español Fluido ★)",
        "lang": "es-MX",
        "gender": "Masculina",
        "accent": "Multilingual Podcast",
    },
    "en-US-BrianMultilingualNeural": {
        "name": "🎧 Brian Multilingual HD (Masculina Joven / Storytelling · Español Fluido)",
        "lang": "es-MX",
        "gender": "Masculina",
        "accent": "Multilingual Joven",
    },
    "es-CO-GonzaloNeural": {
        "name": "🇨🇴 Gonzalo Neural HD (Colombia · Masculina Clara y Natural)",
        "lang": "es-CO",
        "gender": "Masculina",
        "accent": "Colombia",
    },
    "es-AR-TomasNeural": {
        "name": "🇦🇷 Tomás Neural HD (Argentina · Masculina Expresiva / Historias)",
        "lang": "es-AR",
        "gender": "Masculina",
        "accent": "Argentina",
    },
    "es-ES-AlvaroNeural": {
        "name": "🇪🇸 Álvaro Neural HD (España · Masculina Grave Documental/Cine)",
        "lang": "es-ES",
        "gender": "Masculina",
        "accent": "España",
    },
    "es-VE-SebastianNeural": {
        "name": "🇻🇪 Sebastián Neural HD (Latino · Masculina Locución Fluida)",
        "lang": "es-VE",
        "gender": "Masculina",
        "accent": "Venezuela / Caribe",
    },
    "es-CL-LorenzoNeural": {
        "name": "🇨🇱 Lorenzo Neural HD (Chile · Masculina Narrador Sereno)",
        "lang": "es-CL",
        "gender": "Masculina",
        "accent": "Chile",
    },
    # --- FEMENINAS ESPAÑOL & MULTILINGUAL HD ---
    "es-MX-DaliaNeural": {
        "name": "🇲🇽 Dalia Neural HD (México · Femenina Cálida y Natural ★)",
        "lang": "es-MX",
        "gender": "Femenina",
        "accent": "México Natural",
    },
    "es-US-PalomaNeural": {
        "name": "🌎 Paloma Neural HD (Latino Neutro · Femenina Narradora Suave ★)",
        "lang": "es-US",
        "gender": "Femenina",
        "accent": "Latino Neutro",
    },
    "en-US-AvaMultilingualNeural": {
        "name": "🎙️ Ava Multilingual HD (Femenina Podcast Expresiva · Español Fluido ★)",
        "lang": "es-MX",
        "gender": "Femenina",
        "accent": "Multilingual Podcast",
    },
    "en-US-EmmaMultilingualNeural": {
        "name": "✨ Emma Multilingual HD (Femenina Cálida Audiolibro · Español Fluido)",
        "lang": "es-MX",
        "gender": "Femenina",
        "accent": "Multilingual Cálida",
    },
    "es-ES-ElviraNeural": {
        "name": "🇪🇸 Elvira Neural HD (España · Femenina Clara Documental)",
        "lang": "es-ES",
        "gender": "Femenina",
        "accent": "España",
    },
    "es-CO-SalomeNeural": {
        "name": "🇨🇴 Salomé Neural HD (Colombia · Femenina Expresiva)",
        "lang": "es-CO",
        "gender": "Femenina",
        "accent": "Colombia",
    },
    "es-AR-ElenaNeural": {
        "name": "🇦🇷 Elena Neural HD (Argentina · Femenina Natural)",
        "lang": "es-AR",
        "gender": "Femenina",
        "accent": "Argentina",
    },
}


def split_text_into_chunks(text: str, max_chars: int = 350) -> list[str]:
    """Divide textos largos (ej. 5,000 - 100,000 caracteres) en fragmentos seguros por oración
    para evitar que el fonemizador u ONNX desborden el límite de tokens por pasada."""
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    chunks: list[str] = []

    for para in paragraphs:
        # Separar por fin de oración conservando el signo de puntuación
        sentences = re.split(r"(?<=[.!?…;:])\s+", para)
        current = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) <= max_chars:
                if not current:
                    current = sent
                elif len(current) + 1 + len(sent) <= max_chars:
                    current = f"{current} {sent}"
                else:
                    chunks.append(current)
                    current = sent
            else:
                if current:
                    chunks.append(current)
                    current = ""
                # Si una sola oración supera max_chars, dividir por comas o palabras
                clauses = re.split(r"(?<=[,،—–-])\s+", sent)
                for clause in clauses:
                    if len(clause) <= max_chars:
                        if not current:
                            current = clause
                        elif len(current) + 1 + len(clause) <= max_chars:
                            current = f"{current} {clause}"
                        else:
                            chunks.append(current)
                            current = clause
                    else:
                        if current:
                            chunks.append(current)
                            current = ""
                        words = clause.split()
                        for w in words:
                            if not current:
                                current = w
                            elif len(current) + 1 + len(w) <= max_chars:
                                current = f"{current} {w}"
                            else:
                                chunks.append(current)
                                current = w
        if current:
            chunks.append(current)

    return chunks if chunks else [text[:max_chars]]


class EngineManager:
    def __init__(self) -> None:
        self.kokoro: Optional[Kokoro] = None
        self.piper_voices: dict[str, PiperVoice] = {}

    def _download_file(self, url: str, dest: Path) -> None:
        if dest.exists() and dest.stat().st_size > 0:
            return
        tmp_path = dest.with_suffix(dest.suffix + ".part")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        tmp_path.replace(dest)

    def get_kokoro(self) -> Kokoro:
        if self.kokoro is None:
            model_path = MODELS_DIR / "kokoro-v1.0.int8.onnx"
            voices_path = MODELS_DIR / "voices-v1.0.bin"
            self._download_file(
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
                model_path,
            )
            self._download_file(
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
                voices_path,
            )
            self.kokoro = Kokoro(str(model_path), str(voices_path))
        return self.kokoro

    def resolve_kokoro_voice_style(self, voice_id: str) -> np.ndarray:
        kokoro = self.get_kokoro()
        meta = KOKORO_VOICE_CATALOG.get(voice_id, {})
        if "recipe" in meta:
            v_a, v_b, weight_b = meta["recipe"]
            style_a = kokoro.get_voice_style(v_a)
            style_b = kokoro.get_voice_style(v_b)
            return (1.0 - float(weight_b)) * style_a + float(weight_b) * style_b
        available = set(kokoro.get_voices())
        if voice_id in available:
            return kokoro.get_voice_style(voice_id)
        raise HTTPException(status_code=400, detail=f"Voz '{voice_id}' no disponible en Kokoro.")

    def get_piper(self, voice_id: str) -> PiperVoice:
        if voice_id not in PIPER_MODELS_CATALOG:
            raise ValueError(f"Modelo Piper desconocido: {voice_id}")
        if voice_id not in self.piper_voices:
            info = PIPER_MODELS_CATALOG[voice_id]
            onnx_path = MODELS_DIR / f"{voice_id}.onnx"
            json_path = MODELS_DIR / f"{voice_id}.onnx.json"
            self._download_file(info["onnx_url"], onnx_path)
            self._download_file(info["json_url"], json_path)
            self.piper_voices[voice_id] = PiperVoice.load(
                str(onnx_path), config_path=str(json_path), use_cuda=False
            )
        return self.piper_voices[voice_id]


engines = EngineManager()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000, description="Texto a sintetizar (hasta 100,000 caracteres)")
    engine: str = Field("kokoro", description="Motor: 'kokoro' o 'piper'")
    voice: str = Field("em_alex", description="ID de la voz principal")
    lang: Optional[str] = Field(None, description="Código de idioma para fonemización (ej. 'es', 'en-us')")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Velocidad de lectura (0.5 a 2.0)")
    sentence_pause: float = Field(0.25, ge=0.0, le=1.5, description="Pausa entre oraciones en segundos")
    blend_voice: Optional[str] = Field(None, description="Segunda voz opcional para mezclar en Kokoro")
    blend_weight: float = Field(0.5, ge=0.0, le=1.0, description="Peso de la segunda voz (0.0 a 1.0)")
    noise_scale: float = Field(0.667, ge=0.1, le=1.5, description="Expresividad en Piper (noise_scale)")


@app.get("/api/voices")
def list_voices():
    kokoro_list = []
    for vid, meta in KOKORO_VOICE_CATALOG.items():
        kokoro_list.append(
            {
                "id": vid,
                "name": meta["name"],
                "lang": meta["lang"],
                "gender": meta["gender"],
                "accent": meta["accent"],
            }
        )

    piper_list = []
    for vid, meta in PIPER_MODELS_CATALOG.items():
        installed = (MODELS_DIR / f"{vid}.onnx").exists()
        piper_list.append(
            {
                "id": vid,
                "name": meta["name"],
                "lang": meta["lang"],
                "gender": meta["gender"],
                "installed": installed,
            }
        )

    edge_list = []
    for vid, meta in EDGE_NEURAL_VOICE_CATALOG.items():
        edge_list.append(
            {
                "id": vid,
                "name": meta["name"],
                "lang": meta["lang"],
                "gender": meta["gender"],
                "accent": meta["accent"],
            }
        )

    return {
        "kokoro": kokoro_list,
        "piper": piper_list,
        "edge": edge_list,
    }


def resolve_kokoro_lang_and_text(text: str, lang: Optional[str]) -> tuple[str, str]:
    """Normaliza la pronunciación para Español Mexicano ('es-mx') y Español Latino ('es-419')
    usando el motor de seseo latinoamericano de espeak-ng ('es-419') y adaptando fonética mexicana."""
    code = (lang or "es-mx").strip().lower()
    if code == "es-mx":
        # Adaptar palabras con 'x' de fonética mexicana (/x/ o /s/) antes del fonemizador
        mex_rules = [
            (r"\bM[eé]xico\b", "Méjico"),
            (r"\bmexican([oa]s?)\b", r"mejican\1"),
            (r"\bOaxaca\b", "Guajaca"),
            (r"\boaxaqueñ([oa]s?)\b", r"guajaqueñ\1"),
            (r"\bXochimilco\b", "Sochimilco"),
            (r"\bTlaxcala\b", "Tlascala"),
            (r"\bTexcoco\b", "Tescoco"),
            (r"\bXalapa\b", "Jalapa"),
            (r"\bTexas\b", "Tejas"),
        ]
        norm_text = text
        for pattern, repl in mex_rules:
            norm_text = re.sub(pattern, repl, norm_text, flags=re.IGNORECASE)
        return norm_text, "es-419"
    if code in ("es-419", "es-la", "es-latam"):
        return text, "es-419"
    return text, code


@app.post("/api/tts")
def synthesize_speech(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    try:
        if req.engine == "kokoro":
            kokoro = engines.get_kokoro()
            start_time = time.perf_counter()

            raw_lang = req.lang or KOKORO_VOICE_CATALOG.get(req.voice, {}).get("lang", "es-mx")
            norm_text, espeak_lang = resolve_kokoro_lang_and_text(text, raw_lang)
            style_a = engines.resolve_kokoro_voice_style(req.voice)

            if req.blend_voice and req.blend_voice != req.voice and req.blend_weight > 0:
                style_b = engines.resolve_kokoro_voice_style(req.blend_voice)
                w = float(req.blend_weight)
                voice_style = (1.0 - w) * style_a + w * style_b
            else:
                voice_style = style_a

            chunks = split_text_into_chunks(norm_text, max_chars=340)
            all_samples: list[np.ndarray] = []
            sample_rate = 24000

            for idx, chunk_text in enumerate(chunks):
                samples, sample_rate = kokoro.create(
                    chunk_text,
                    voice=voice_style,
                    speed=req.speed,
                    lang=espeak_lang,
                    trim=True,
                    sentence_pause=req.sentence_pause,
                )
                if len(samples) > 0:
                    all_samples.append(samples)
                    if idx < len(chunks) - 1 and req.sentence_pause > 0:
                        pause_samples = np.zeros(int(sample_rate * req.sentence_pause), dtype=np.float32)
                        all_samples.append(pause_samples)

            final_samples = np.concatenate(all_samples) if all_samples else np.zeros(2400, dtype=np.float32)

            buf = io.BytesIO()
            sf.write(buf, final_samples, sample_rate, format="WAV", subtype="PCM_16")
            wav_bytes = buf.getvalue()
            audio_duration = len(final_samples) / float(sample_rate)

        elif req.engine == "piper":
            voice = engines.get_piper(req.voice)
            start_time = time.perf_counter()
            syn_cfg = SynthesisConfig(
                length_scale=1.0 / max(req.speed, 0.25),
                noise_scale=req.noise_scale,
            )
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file, syn_config=syn_cfg)
            wav_bytes = buf.getvalue()

            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_in:
                frames = wav_in.getnframes()
                rate = wav_in.getframerate()
                audio_duration = frames / float(rate) if rate else 0.0
        else:
            raise HTTPException(status_code=400, detail="Motor inválido. Usa 'kokoro' o 'piper'.")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al sintetizar voz: {exc}") from exc

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    rtf = round((elapsed_ms / 1000.0) / max(audio_duration, 0.01), 3)

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Inference-Time-Ms": str(elapsed_ms),
            "X-Audio-Duration-Sec": f"{audio_duration:.2f}",
            "X-Real-Time-Factor": str(rtf),
            "Access-Control-Expose-Headers": "X-Inference-Time-Ms, X-Audio-Duration-Sec, X-Real-Time-Factor",
        },
    )


class AnalyzeImageRequest(BaseModel):
    image_b64: str = Field(..., description="Imagen de referencia en base64 (con o sin prefijo data:image/...)")


class YouTubeProjectRequest(BaseModel):
    script: str = Field(..., min_length=5, max_length=100000, description="Guion completo del video de YouTube")
    engine: str = Field("edge", description="Motor TTS: 'edge' (Ultra-Natural Gratis), 'kokoro' o 'piper'")
    voice: str = Field("es-MX-JorgeNeural", description="ID de voz")
    lang: Optional[str] = Field("es-mx", description="Idioma de fonemización")
    speed: float = Field(1.0, ge=0.5, le=2.0)
    sentence_pause: float = Field(0.25, ge=0.0, le=1.5)
    noise_scale: float = Field(0.667, ge=0.1, le=1.5)
    pitch_hz: int = Field(1, ge=-15, le=15, description="Ajuste de tono en Hz para voz de locutor (ej. +1Hz o 0Hz)")
    studio_mastering: bool = Field(True, description="Aplicar ecualización cálida de estudio, de-esser y prosodia natural")
    scene_mode: str = Field("auto", description="'auto', 'paragraph', o 'sentence'")
    style: str = Field("cinematic", description="Estilo visual base para las imágenes")
    custom_style_prompt: Optional[str] = Field(None, description="Prompt maestro de estilo / personajes fijos")
    reference_image_b64: Optional[str] = Field(None, description="Imagen de referencia de estilo en base64")
    color_match_strength: float = Field(0.45, ge=0.0, le=1.0, description="Fuerza de igualación cromática con la imagen de referencia")
    aspect_ratio: str = Field("16:9", description="'16:9' (YouTube) o '9:16' (Shorts/TikTok)")
    transition: str = Field("crossfade", description="Tipo de transición: 'crossfade', 'fade_black', 'fade_white', 'slide_left', 'none'")
    transition_duration: float = Field(0.5, ge=0.1, le=1.5, description="Duración de transición en segundos")
    subtitle_style: str = Field("hormozi_yellow", description="Estilo de subtítulos: 'hormozi_yellow', 'hormozi_cyan', 'hormozi_green', 'cinematic_pop', 'classic_box'")
    camera_effect: str = Field("ken_burns_mix", description="Efecto de movimiento mientras pasa la imagen: 'ken_burns_mix', 'zoom_in_dramatic', 'pan_cinema', 'none'")
    bg_music: str = Field("doc_mystery", description="Música de fondo sin copyright: 'doc_mystery', 'warm_story', 'lofi_chill', 'dark_suspense', 'inspiring_science', 'custom', 'none'")
    bg_music_volume: float = Field(0.14, ge=0.0, le=0.55, description="Volumen de música de fondo (con auto-ducking bajo la voz)")
    custom_music_b64: Optional[str] = Field(None, description="Archivo de música personalizado opcional en base64")


class YouTubeVoicePreviewRequest(BaseModel):
    text: str = Field(
        "En las profundidades del océano Pacífico existe un misterio que ningún científico ha logrado explicar.",
        min_length=2,
        max_length=1500,
    )
    engine: str = Field("edge")
    voice: str = Field("es-MX-JorgeNeural")
    lang: Optional[str] = Field("es-mx")
    speed: float = Field(1.0, ge=0.5, le=2.0)
    sentence_pause: float = Field(0.25, ge=0.0, le=1.5)
    noise_scale: float = Field(0.667, ge=0.1, le=1.5)
    pitch_hz: int = Field(1, ge=-15, le=15)
    studio_mastering: bool = Field(True)


class UpdateProjectVoiceRequest(BaseModel):
    engine: str = Field("edge")
    voice: str = Field("es-MX-JorgeNeural")
    lang: Optional[str] = Field("es-mx")
    speed: float = Field(1.0, ge=0.5, le=2.0)
    sentence_pause: float = Field(0.25, ge=0.0, le=1.5)
    noise_scale: float = Field(0.667, ge=0.1, le=1.5)
    pitch_hz: int = Field(1, ge=-15, le=15)
    studio_mastering: bool = Field(True)


class UpdateProjectStyleRequest(BaseModel):
    style: str = Field("cinematic")
    custom_style_prompt: Optional[str] = Field(None)
    reference_image_b64: Optional[str] = Field(None)
    color_match_strength: float = Field(0.45, ge=0.0, le=1.0)


class SceneImageRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="Prompt personalizado opcional para esta escena")
    color_match_strength: Optional[float] = Field(None, ge=0.0, le=1.0)
    variation: bool = Field(False, description="True para probar otra versión de la escena cambiando su semilla")


class SettingsRequest(BaseModel):
    provider: Optional[str] = Field(None, description="Motor de imágenes: 'auto', 'gemini_pro', 'gemini', 'runware', 'together', 'fal', 'hf_dev', 'hf_fast', 'pollinations'")
    gemini_api_key: Optional[str] = Field(None, description="API Key gratuita de Google AI Studio")
    gemini_curl: Optional[str] = Field(None, description="Comando cURL (cmd / bash) completo de gemini.google.com")
    gemini_1psid: Optional[str] = Field(None, description="Cookie __Secure-1PSID de gemini.google.com")
    gemini_1psidts: Optional[str] = Field(None, description="Cookie __Secure-1PSIDTS de gemini.google.com")
    gemini_osid: Optional[str] = Field(None, description="Cookie OSID / __Secure-OSID o bloque Copy as cURL de gemini.google.com")
    gemini_sid: Optional[str] = Field(None, description="Cookie maestra SID de Google")
    gemini_ssid: Optional[str] = Field(None, description="Cookie maestra SSID de Google")
    runware_api_key: Optional[str] = Field(None, description="API Key de Runware.ai")
    together_api_key: Optional[str] = Field(None, description="API Key de Together AI")
    fal_api_key: Optional[str] = Field(None, description="API Key de Fal.ai")
    hf_token: Optional[str] = Field(None, description="Token gratuito de Hugging Face")
    allow_fallback: Optional[bool] = Field(None, description="Permitir respaldo Pollinations")


class RenderVideoRequest(BaseModel):
    burn_subtitles: bool = Field(True, description="Incrustar subtítulos en el video MP4")
    transition: str = Field("crossfade", description="Tipo de transición: 'crossfade', 'fade_black', 'fade_white', 'slide_left', 'none'")
    transition_duration: float = Field(0.5, ge=0.1, le=1.5, description="Duración de la transición en segundos")
    subtitle_style: str = Field("hormozi_yellow", description="Estilo de subtítulos dinámicos")
    camera_effect: str = Field("living_ai_motion", description="Efecto de cámara o micro-animación en cada escena")
    bg_music: str = Field("doc_mystery", description="Música de fondo sin copyright")
    bg_music_volume: float = Field(0.14, ge=0.0, le=0.55, description="Volumen de música de fondo")
    custom_music_b64: Optional[str] = Field(None, description="Música personalizada opcional en base64")


def _decode_b64_image(b64_str: str) -> bytes:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    return base64.b64decode(b64_str)


@app.post("/api/style/analyze-image")
def analyze_style_image_endpoint(req: AnalyzeImageRequest):
    try:
        raw_bytes = _decode_b64_image(req.image_b64)
        return analyze_reference_image(raw_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo analizar la imagen de referencia: {exc}") from exc


def enhance_spanish_prosody_for_youtube(text: str, for_local_onnx: bool = False, expressive_mode: bool = True) -> str:
    """Pre-procesa el guion en español para que las pausas respiratorias,
    inflexiones, números, conectores y énfasis suenen con expresividad y cadencia humana."""
    t = text.strip()
    if not t:
        return t
    # Normalizar comillas y guiones largos para que el motor haga inflexión natural
    t = re.sub(r"\s*—\s*", ", ", t)
    t = re.sub(r"\s*–\s*", ", ", t)
    t = re.sub(r"(\d+)\s*%", r"\1 por ciento", t)
    t = re.sub(r"\bSr\.\s*", "Señor ", t)
    t = re.sub(r"\bSra\.\s*", "Señora ", t)
    t = re.sub(r"\bDr\.\s*", "Doctor ", t)
    t = re.sub(r"\bDra\.\s*", "Doctora ", t)

    if expressive_mode:
        # Pausas respiratorias naturales en conectores y transiciones narrativas
        t = re.sub(
            r"\b(Sin embargo|Por ejemplo|No obstante|En realidad|De hecho|Por eso|Además|Por lo tanto|En consecuencia)\s+(?!,)",
            r"\1, ",
            t,
            flags=re.IGNORECASE,
        )
        # Inflexión de atención en marcadores de énfasis documental
        t = re.sub(
            r"\b(Observa|Fíjate|Increíblemente|Sorprendentemente|Mira cómo|Presta atención a|Nota cómo)\s+(?!:|,|\.)",
            r"\1... ",
            t,
            flags=re.IGNORECASE,
        )
        # Separación respiratoria en enumeraciones de tiempos y partes
        t = re.sub(r"\b(Tiempo uno|Tiempo dos|Tiempo tres|Tiempo cuatro):?\s*", r"¡\1!... ", t, flags=re.IGNORECASE)
        t = re.sub(r"\b(Primer tiempo|Segundo tiempo|Tercer tiempo|Cuarto tiempo):?\s*", r"¡\1!... ", t, flags=re.IGNORECASE)

    if for_local_onnx:
        # En Kokoro y Piper (espeak-ng), micro-pausa adicional en conectores
        t = re.sub(
            r"\b(Sin embargo|Por ejemplo|No obstante|En realidad|De hecho|Por eso|Además)\s+(?!,)",
            r"\1, ",
            t,
        )
    return re.sub(r"\s{2,}", " ", t).strip()


def apply_studio_voice_mastering(samples: np.ndarray, sr: int = 24000) -> np.ndarray:
    """Cadena DSP de estudio ('Shure SM7B Broadcast Warmth & De-Esser'):
    1. Recorta silencios muertos al inicio/final con micro-fade suave (evita cortes robóticos).
    2. Ecualización FFT: filtro paso-alto <65Hz, cuerpo cálido en 115-230Hz (+1.8dB),
       limpieza nasal en 420Hz (-1.2dB), presencia clara en 3.2kHz (+1.0dB) y De-Esser en 6.5-10.5kHz (-3.0dB).
    3. Saturación suave de tubo/cinta (soft-knee tanh) y normalización uniforme de volumen."""
    if samples is None or len(samples) < 400:
        return samples
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=1)

    # 1. Recorte de silencio muerto en extremos (conservando 30ms de aire natural)
    abs_arr = np.abs(arr)
    active_idx = np.where(abs_arr > 0.0035)[0]
    if len(active_idx) > 100:
        pad = int(sr * 0.03)
        start_i = max(0, int(active_idx[0]) - pad)
        end_i = min(len(arr), int(active_idx[-1]) + pad)
        arr = arr[start_i:end_i]

    n = len(arr)
    if n < 400:
        return arr

    # 2. Ecualización de estudio + De-Esser en dominio de frecuencia
    freqs = np.fft.rfftfreq(n, d=1.0 / float(sr))
    spec = np.fft.rfft(arr)

    gain = np.ones_like(freqs, dtype=np.float32)
    # Filtro sub-grave (<65 Hz)
    gain *= np.clip((freqs - 45.0) / 30.0, 0.0, 1.0)
    # Cuerpo cálido de locutor (110 Hz - 240 Hz, +1.8 dB = x1.23)
    warmth = np.exp(-0.5 * ((freqs - 165.0) / 55.0) ** 2)
    gain *= 1.0 + 0.22 * warmth
    # Corte de resonancia encajonada (430 Hz, -1.2 dB)
    boxy = np.exp(-0.5 * ((freqs - 430.0) / 80.0) ** 2)
    gain *= 1.0 - 0.13 * boxy
    # Claridad de dicción (3200 Hz, +1.0 dB)
    clarity = np.exp(-0.5 * ((freqs - 3200.0) / 700.0) ** 2)
    gain *= 1.0 + 0.11 * clarity
    # De-Esser anti-metálico (6400 Hz - 10500 Hz, -3.0 dB = x0.71)
    sibilance = np.exp(-0.5 * ((freqs - 7800.0) / 1800.0) ** 2)
    gain *= 1.0 - 0.28 * sibilance

    processed = np.fft.irfft(spec * gain, n=n).astype(np.float32)

    # 3. Compresión / saturación cálida soft-knee y normalización consistente
    peak = float(np.max(np.abs(processed)))
    if peak > 1e-5:
        processed = processed / peak * 0.92
        processed = (np.tanh(processed * 1.18) / np.tanh(1.18)).astype(np.float32) * 0.88

    # 4. Micro-fades de 18ms en entrada y 28ms en salida para eliminar chasquidos digitales
    fade_in = min(int(sr * 0.018), n // 4)
    fade_out = min(int(sr * 0.028), n // 4)
    if fade_in > 8:
        processed[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)
    if fade_out > 8:
        processed[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)

    # 5. Masterización de estudio profesional con Spotify Pedalboard (C++ / JUCE)
    try:
        from studio.audio_mastering import master_audio_samples
        processed = master_audio_samples(processed, sr)
    except Exception:
        pass

    return processed


def _synthesize_with_edge_neural(
    text: str,
    voice_id: str,
    speed: float = 1.0,
    pitch_hz: int = 1,
    volume: str = "+15%",
) -> tuple[np.ndarray, int]:
    """Sintetiza voz ultra-natural y expresiva con Microsoft Edge Neural HD."""
    import asyncio
    import edge_tts

    target_voice = voice_id if voice_id in EDGE_NEURAL_VOICE_CATALOG else "es-MX-JorgeNeural"
    # Añadir un sutil impulso de cadencia (+3%) para que suene ágil, dinámico y no monótono
    rate_pct = int(round((float(speed) - 1.0) * 100)) + 3
    rate_str = f"{rate_pct:+d}%"
    pitch_val = int(round(float(pitch_hz)))
    pitch_str = f"{pitch_val:+d}Hz"

    clean_text = enhance_spanish_prosody_for_youtube(text, for_local_onnx=False, expressive_mode=True)

    async def _run_edge() -> bytes:
        last_err: Optional[Exception] = None
        for attempt in range(1, 6):
            try:
                comm = edge_tts.Communicate(clean_text, target_voice, rate=rate_str, pitch=pitch_str, volume=volume)
                audio_buf = bytearray()
                async for chunk in comm.stream():
                    if chunk.get("type") == "audio":
                        audio_buf.extend(chunk["data"])
                if audio_buf:
                    return bytes(audio_buf)
            except Exception as exc:
                last_err = exc
            await asyncio.sleep(0.45 * attempt)
        if last_err is not None:
            raise last_err
        return b""

    box: list[Optional[bytes]] = [None]
    err_box: list[Optional[Exception]] = [None]

    def _thread_target():
        try:
            box[0] = asyncio.run(_run_edge())
        except Exception as e:
            err_box[0] = e

    import threading

    t = threading.Thread(target=_thread_target, daemon=True)
    t.start()
    t.join(timeout=60)
    if err_box[0] is not None:
        raise RuntimeError(f"Error en Edge Neural HD: {err_box[0]}")
    if not box[0]:
        raise RuntimeError("Edge Neural HD no devolvió audio.")

    samples, sr = sf.read(io.BytesIO(box[0]), dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples.astype(np.float32), int(sr)


def _synthesize_segment_samples(
    text: str,
    engine: str = "edge",
    voice_id: str = "es-MX-JorgeNeural",
    lang: Optional[str] = None,
    speed: float = 1.0,
    sentence_pause: float = 0.15,
    noise_scale: float = 0.667,
    pitch_hz: int = 1,
    studio_mastering: bool = True,
) -> tuple[np.ndarray, int]:
    if engine == "edge":
        try:
            samples, sr = _synthesize_with_edge_neural(
                text=text,
                voice_id=voice_id,
                speed=speed,
                pitch_hz=pitch_hz,
            )
            if studio_mastering:
                samples = apply_studio_voice_mastering(samples, sr)
            return samples, sr
        except Exception as exc:
            print(f"Aviso: fallo temporal en Edge Neural HD ({exc}), usando Kokoro local como respaldo...")
            engine = "kokoro"
            if voice_id not in KOKORO_VOICE_CATALOG:
                voice_id = "es_m_mateo"

    if engine == "kokoro":
        kokoro = engines.get_kokoro()
        raw_lang = lang or KOKORO_VOICE_CATALOG.get(voice_id, {}).get("lang", "es-mx")
        prosody_text = enhance_spanish_prosody_for_youtube(text, for_local_onnx=True) if studio_mastering else text
        norm_text, espeak_lang = resolve_kokoro_lang_and_text(prosody_text, raw_lang)
        voice_style = engines.resolve_kokoro_voice_style(voice_id)
        chunks = split_text_into_chunks(norm_text, max_chars=340)
        parts: list[np.ndarray] = []
        sr = 24000
        for idx, ch in enumerate(chunks):
            samples, sr = kokoro.create(
                ch,
                voice=voice_style,
                speed=speed,
                lang=espeak_lang,
                trim=True,
                sentence_pause=sentence_pause,
            )
            if len(samples) > 0:
                if studio_mastering:
                    samples = apply_studio_voice_mastering(samples, sr)
                parts.append(samples)
                if idx < len(chunks) - 1 and sentence_pause > 0:
                    parts.append(np.zeros(int(sr * sentence_pause), dtype=np.float32))
        merged = np.concatenate(parts) if parts else np.zeros(2400, dtype=np.float32)
        return merged, sr

    elif engine == "piper":
        pvoice = engines.get_piper(voice_id)
        prosody_text = enhance_spanish_prosody_for_youtube(text, for_local_onnx=True) if studio_mastering else text
        syn_cfg = SynthesisConfig(length_scale=1.0 / max(speed, 0.25), noise_scale=noise_scale)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            pvoice.synthesize_wav(prosody_text, wav_file, syn_config=syn_cfg)
        buf.seek(0)
        samples, sr = sf.read(buf, dtype="float32")
        if studio_mastering:
            samples = apply_studio_voice_mastering(samples, int(sr))
        return samples, int(sr)
    else:
        raise HTTPException(status_code=400, detail="Motor inválido.")


@app.post("/api/youtube/voice-preview")
def preview_youtube_voice_endpoint(req: YouTubeVoicePreviewRequest):
    """Permite escuchar en 1 clic cómo suena la voz elegida en el Creador de Videos de YouTube."""
    try:
        samples, sr = _synthesize_segment_samples(
            text=req.text,
            engine=req.engine,
            voice_id=req.voice,
            lang=req.lang,
            speed=req.speed,
            sentence_pause=req.sentence_pause,
            noise_scale=req.noise_scale,
            pitch_hz=req.pitch_hz,
            studio_mastering=req.studio_mastering,
        )
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format="WAV", subtype="PCM_16")
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en vista previa de voz: {exc}") from exc


@app.get("/api/youtube/music-preview")
def preview_youtube_music_endpoint(style: str = "doc_mystery"):
    """Permite escuchar una muestra de 16 segundos de cualquiera de las pistas de música sin copyright integradas."""
    try:
        sr = 24000
        samples = video_pipeline.generate_royalty_free_music(style=style, duration_sec=16.0, sr=sr)
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format="WAV", subtype="PCM_16")
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando vista previa de música: {exc}") from exc


@app.post("/api/project/{project_id}/update-voice")
def update_project_voice_endpoint(project_id: str, req: UpdateProjectVoiceRequest):
    """Regenera únicamente la narración y los timestamps de un proyecto de YouTube existente
    CONSERVANDO todas las imágenes IA que ya fueron generadas."""
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    audio_dir = proj_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    master_samples_list: list[np.ndarray] = []
    current_time_sec = 0.0
    sample_rate = 24000
    cache_bust = int(time.time())

    for sc in meta.get("scenes", []):
        idx = int(sc["index"])
        sc_text = sc.get("text", "")
        samples, sample_rate = _synthesize_segment_samples(
            text=sc_text,
            engine=req.engine,
            voice_id=req.voice,
            lang=req.lang,
            speed=req.speed,
            sentence_pause=req.sentence_pause,
            noise_scale=req.noise_scale,
            pitch_hz=req.pitch_hz,
            studio_mastering=req.studio_mastering,
        )
        pause_after = np.zeros(int(sample_rate * max(0.2, req.sentence_pause)), dtype=np.float32)
        scene_full_samples = np.concatenate([samples, pause_after])

        scene_wav_path = audio_dir / f"scene_{idx:03d}.wav"
        sf.write(scene_wav_path, scene_full_samples, sample_rate, format="WAV", subtype="PCM_16")
        master_samples_list.append(scene_full_samples)

        dur_sec = round(len(scene_full_samples) / float(sample_rate), 3)
        start_sec = round(current_time_sec, 3)
        end_sec = round(current_time_sec + dur_sec, 3)
        current_time_sec = end_sec

        sc["start_sec"] = start_sec
        sc["end_sec"] = end_sec
        sc["duration_sec"] = dur_sec
        sc["timestamp_label"] = f"{format_mm_ss(start_sec)} → {format_mm_ss(end_sec)}"
        sc["audio_url"] = f"/projects/{project_id}/audio/scene_{idx:03d}.wav?t={cache_bust}"

    master_samples = np.concatenate(master_samples_list) if master_samples_list else np.zeros(2400, dtype=np.float32)
    master_wav_path = proj_dir / "narracion_completa.wav"
    sf.write(master_wav_path, master_samples, sample_rate, format="WAV", subtype="PCM_16")

    srt_content = generate_srt_content(meta.get("scenes", []))
    srt_path = proj_dir / "subtitulos_timestamps.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    meta["engine"] = req.engine
    meta["voice"] = req.voice
    meta["total_duration_sec"] = round(current_time_sec, 2)
    meta["master_audio_url"] = f"/projects/{project_id}/narracion_completa.wav?t={cache_bust}"
    meta["srt_url"] = f"/projects/{project_id}/subtitulos_timestamps.srt?t={cache_bust}"

    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.post("/api/project/create")
def create_youtube_project(req: YouTubeProjectRequest):
    raw_scenes = split_script_into_scenes(req.script, mode=req.scene_mode)
    if not raw_scenes:
        raise HTTPException(status_code=400, detail="El guion no contiene escenas válidas.")

    project_id = f"yt_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    proj_dir = PROJECTS_DIR / project_id
    audio_dir = proj_dir / "audio"
    images_dir = proj_dir / "images"
    audio_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    width, height = (1920, 1080) if req.aspect_ratio == "16:9" else (1080, 1920)

    # Procesar imagen de referencia de estilo si se proporcionó
    ref_style_descriptor: Optional[str] = None
    ref_image_url: Optional[str] = None
    if req.reference_image_b64:
        try:
            ref_bytes = _decode_b64_image(req.reference_image_b64)
            ref_path = proj_dir / "reference_style.png"
            ref_path.write_bytes(ref_bytes)
            ref_analysis = analyze_reference_image(ref_bytes)
            ref_style_descriptor = ref_analysis["extracted_prompt"]
            ref_image_url = f"/projects/{project_id}/reference_style.png?t={int(time.time())}"
        except Exception as exc:
            print(f"Aviso al guardar imagen de referencia: {exc}")

    scenes_meta: list[dict[str, Any]] = []
    master_samples_list: list[np.ndarray] = []
    current_time_sec = 0.0
    sample_rate = 24000

    # PASO 1: Sintetizar la narración y obtener primero los Timestamps exactos de cada frase
    for idx, sc_text in enumerate(raw_scenes, start=1):
        samples, sample_rate = _synthesize_segment_samples(
            text=sc_text,
            engine=req.engine,
            voice_id=req.voice,
            lang=req.lang,
            speed=req.speed,
            sentence_pause=req.sentence_pause,
            noise_scale=req.noise_scale,
            pitch_hz=req.pitch_hz,
            studio_mastering=req.studio_mastering,
        )
        pause_after = np.zeros(int(sample_rate * max(0.2, req.sentence_pause)), dtype=np.float32)
        scene_full_samples = np.concatenate([samples, pause_after])

        scene_wav_path = audio_dir / f"scene_{idx:03d}.wav"
        sf.write(scene_wav_path, scene_full_samples, sample_rate, format="WAV", subtype="PCM_16")
        master_samples_list.append(scene_full_samples)

        dur_sec = round(len(scene_full_samples) / float(sample_rate), 3)
        start_sec = round(current_time_sec, 3)
        end_sec = round(current_time_sec + dur_sec, 3)
        current_time_sec = end_sec

        scenes_meta.append(
            {
                "index": idx,
                "text": sc_text,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": dur_sec,
                "timestamp_label": f"{format_mm_ss(start_sec)} → {format_mm_ss(end_sec)}",
                "audio_url": f"/projects/{project_id}/audio/scene_{idx:03d}.wav",
                "translated_en": "",
                "image_prompt": "",
                "image_url": None,
            }
        )

    master_samples = np.concatenate(master_samples_list) if master_samples_list else np.zeros(2400, dtype=np.float32)
    master_wav_path = proj_dir / "narracion_completa.wav"
    sf.write(master_wav_path, master_samples, sample_rate, format="WAV", subtype="PCM_16")

    srt_content = generate_srt_content(scenes_meta)
    srt_path = proj_dir / "subtitulos_timestamps.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    # PASO 2: Con base en cada Timestamp y lo que dice la voz en ese instante,
    # traducir y construir el prompt visual alusivo para cada escena
    populate_timestamp_visual_prompts(
        scenes_meta=scenes_meta,
        style_key=req.style,
        custom_style_prompt=req.custom_style_prompt,
        ref_style_descriptor=ref_style_descriptor,
    )

    if req.custom_music_b64:
        try:
            music_bytes = _decode_b64_image(req.custom_music_b64)
            (proj_dir / "custom_bg_music.bin").write_bytes(music_bytes)
        except Exception as exc:
            print(f"Aviso al guardar música personalizada: {exc}")

    project_data = {
        "project_id": project_id,
        "engine": req.engine,
        "voice": req.voice,
        "width": width,
        "height": height,
        "aspect_ratio": req.aspect_ratio,
        "style": req.style,
        "seed": random.randint(1000, 9_999_999),
        "custom_style_prompt": req.custom_style_prompt or "",
        "ref_style_descriptor": ref_style_descriptor or "",
        "reference_image_url": ref_image_url,
        "color_match_strength": req.color_match_strength,
        "transition": req.transition,
        "transition_duration": req.transition_duration,
        "subtitle_style": req.subtitle_style,
        "camera_effect": req.camera_effect,
        "bg_music": req.bg_music,
        "bg_music_volume": req.bg_music_volume,
        "total_duration_sec": round(current_time_sec, 2),
        "master_audio_url": f"/projects/{project_id}/narracion_completa.wav",
        "srt_url": f"/projects/{project_id}/subtitulos_timestamps.srt",
        "video_url": None,
        "zip_url": f"/api/project/{project_id}/zip",
        "scenes": scenes_meta,
    }

    (proj_dir / "project.json").write_text(json.dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return project_data


@app.post("/api/project/{project_id}/update-style")
def update_project_style_endpoint(project_id: str, req: UpdateProjectStyleRequest):
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    meta["style"] = req.style
    meta["custom_style_prompt"] = req.custom_style_prompt or ""
    meta["color_match_strength"] = req.color_match_strength

    if req.reference_image_b64:
        try:
            ref_bytes = _decode_b64_image(req.reference_image_b64)
            ref_path = proj_dir / "reference_style.png"
            ref_path.write_bytes(ref_bytes)
            ref_analysis = analyze_reference_image(ref_bytes)
            meta["ref_style_descriptor"] = ref_analysis["extracted_prompt"]
            meta["reference_image_url"] = f"/projects/{project_id}/reference_style.png?t={int(time.time())}"
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Error en imagen de referencia: {exc}") from exc

    texts_es = [s.get("text", "") for s in meta.get("scenes", [])]
    gemini_scenes = video_pipeline._generate_storyboard_descriptions_with_gemini_llm(texts_es)
    if gemini_scenes and len(gemini_scenes) == len(texts_es):
        translations_en = gemini_scenes
        for sc, g_en in zip(meta["scenes"], gemini_scenes):
            sc["translated_en"] = g_en
    else:
        translations_en = [s.get("translated_en") or s.get("text", "") for s in meta.get("scenes", [])]

    global_context_en = video_pipeline._extract_visual_setting_anchor(translations_en)
    total_sc = len(meta["scenes"])
    for idx_i, sc in enumerate(meta["scenes"]):
        prev_en = translations_en[idx_i - 1] if idx_i > 0 else None
        next_en = translations_en[idx_i + 1] if idx_i + 1 < total_sc else None
        sc["image_prompt"] = build_scene_prompt(
            sc["text"],
            style_key=meta["style"],
            custom_style_prompt=meta.get("custom_style_prompt"),
            ref_style_descriptor=meta.get("ref_style_descriptor"),
            translated_en=sc.get("translated_en"),
            global_context_en=global_context_en,
            timestamp_label=sc.get("timestamp_label"),
            prev_translated_en=prev_en,
            next_translated_en=next_en,
        )

    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.get("/api/projects")
def list_youtube_projects_endpoint():
    """Lista todos los proyectos de YouTube guardados en disco para poder cargarlos y cambiarles la voz."""
    if not PROJECTS_DIR.exists():
        return {"projects": []}
    candidates = sorted(
        [p / "project.json" for p in PROJECTS_DIR.iterdir() if p.name.startswith("yt_") and (p / "project.json").exists()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    items = []
    for fpath in candidates:
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            scenes = data.get("scenes", [])
            first_text = (scenes[0].get("text", "") if scenes else "").strip()
            preview = (first_text[:52] + "...") if len(first_text) > 52 else (first_text or data.get("project_id", ""))
            img_count = sum(1 for s in scenes if s.get("image_url"))
            items.append(
                {
                    "project_id": data.get("project_id", fpath.parent.name),
                    "preview": preview,
                    "scenes_count": len(scenes),
                    "images_count": img_count,
                    "total_duration_sec": data.get("total_duration_sec", 0),
                    "has_video": bool(data.get("video_url")),
                    "voice": data.get("voice", ""),
                }
            )
        except Exception:
            pass
    return {"projects": items}


@app.get("/api/project/latest")
def get_latest_project_endpoint():
    if not PROJECTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No hay proyectos.")
    candidates = sorted(
        [p / "project.json" for p in PROJECTS_DIR.iterdir() if (p / "project.json").exists()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise HTTPException(status_code=404, detail="No hay proyectos.")
    return json.loads(candidates[0].read_text(encoding="utf-8"))


class YouTubeScriptSearchRequest(BaseModel):
    category: str = Field("historia_mexico", description="historia_mexico | misterio | terror | lugares_mundo")
    query: str = Field("", max_length=500, description="Tema específico a buscar o vacío para descubrir un tema viral")
    duration_mode: str = Field("youtube_4_6m", description="'shorts' (60-90s 9:16) o 'youtube_4_6m' (4-6 min 16:9)")


@app.get("/api/youtube/script-search-catalog")
def get_youtube_script_search_catalog():
    """Devuelve las categorías de búsqueda de guiones (Historia de México, Misterio, Terror, Lugares del Mundo) y sus temas sugeridos."""
    from studio.youtube_script_searcher import YOUTUBE_SEARCH_CATEGORIES
    return {"categories": YOUTUBE_SEARCH_CATEGORIES}


@app.get("/api/topics/diverse")
def get_diverse_topics_endpoint(category: Optional[str] = None, count: int = 8, refresh: bool = False):
    """Devuelve una lista variada y no repetitiva de temas documentados, consultando Wikipedia en vivo si refresh=True."""
    from studio.dynamic_topic_service import get_diverse_topics
    topics = get_diverse_topics(category=category, count=count, refresh=refresh)
    return {"status": "success", "topics": topics}


@app.get("/api/topics/categories")
def get_topic_categories_endpoint():
    """Devuelve las 8 grandes categorías temáticas disponibles con sus iconos y descripciones."""
    from studio.dynamic_topic_service import DEEP_TOPICS_POOL
    cats = []
    for cid, cdata in DEEP_TOPICS_POOL.items():
        cats.append({
            "id": cid,
            "name": cdata["name"],
            "icon": cdata["icon"],
            "badge": cdata["badge"],
            "total_topics": len(cdata["topics"]),
        })
    return {"status": "success", "categories": cats}


@app.post("/api/youtube/search-script")
def search_youtube_script_endpoint(req: YouTubeScriptSearchRequest):
    """Investiga en tiempo real el tema o categoría elegida y genera el guion + mejor título + alternativas para Shorts/TikTok o YouTube 4-6 min."""
    from studio.youtube_script_searcher import search_and_generate_youtube_script
    try:
        return search_and_generate_youtube_script(
            category=req.category,
            query=req.query,
            duration_mode=req.duration_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al buscar y generar el guion: {exc}") from exc


@app.get("/api/project/{project_id}")
def get_project_endpoint(project_id: str):
    meta_file = PROJECTS_DIR / project_id / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    return json.loads(meta_file.read_text(encoding="utf-8"))


@app.post("/api/project/{project_id}/scene/{scene_index}/image")
def generate_scene_image_endpoint(project_id: str, scene_index: int, req: SceneImageRequest):
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    target_scene = None
    for sc in meta["scenes"]:
        if sc["index"] == scene_index:
            target_scene = sc
            break
    if not target_scene:
        raise HTTPException(status_code=404, detail="Escena no encontrada.")

    legacy_markers = (
        "PRIMARY SCENE TO ILLUSTRATE:",
        "Story setting & environment continuity:",
        "world map display",
        "MAIN SUBJECT & ACTION IN FOREGROUND:",
    )
    if req.prompt and req.prompt.strip():
        candidate_p = req.prompt.strip()
        if not any(m in candidate_p for m in legacy_markers):
            target_scene["image_prompt"] = candidate_p

    if any(m in (target_scene.get("image_prompt") or "") for m in legacy_markers):
        target_scene["image_prompt"] = build_scene_prompt(
            scene_text=target_scene["text"],
            style_key=meta.get("style", "cinematic"),
            custom_style_prompt=meta.get("custom_style_prompt"),
            ref_style_descriptor=meta.get("ref_style_descriptor"),
            translated_en=target_scene.get("translated_en"),
        )

    ref_img_path = proj_dir / "reference_style.png"
    strength = req.color_match_strength if req.color_match_strength is not None else float(meta.get("color_match_strength", 0.45))

    # Semilla derivada por escena para que cada timestamp tenga una composición propia sin repetir encuadres
    base_seed = int(meta.get("seed") or random.randint(1000, 9_999_999))
    meta["seed"] = base_seed
    if req.variation:
        target_scene["variation"] = int(target_scene.get("variation", 0)) + 1
    scene_seed = base_seed + (scene_index * 137) + 7919 * int(target_scene.get("variation", 0))

    dest_img = proj_dir / "images" / f"scene_{scene_index:03d}.png"
    try:
        generate_image_for_scene(
            prompt=target_scene["image_prompt"],
            width=meta["width"],
            height=meta["height"],
            dest_path=dest_img,
            seed=scene_seed,
            reference_image_path=ref_img_path if ref_img_path.exists() else None,
            color_match_strength=strength,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    target_scene["image_url"] = f"/projects/{project_id}/images/scene_{scene_index:03d}.png?t={int(time.time())}"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_scene


def _mask_key(val: str) -> str:
    val = (val or "").strip()
    return (val[:4] + "…" + val[-3:]) if len(val) > 8 else ""


@app.get("/api/settings")
def get_settings_endpoint():
    s = video_pipeline.IMAGE_SETTINGS
    tok = s.get("hf_token") or ""
    gem = s.get("gemini_api_key") or ""
    psid = s.get("gemini_1psid") or ""
    psidts = s.get("gemini_1psidts") or ""
    osid = s.get("gemini_osid") or ""
    clist = s.get("gemini_cookies_list") or []
    if not osid and clist:
        for c in clist:
            if c.get("name") in ("OSID", "__Secure-OSID") and c.get("value"):
                osid = c["value"]
                break
    rw = s.get("runware_api_key") or ""
    tog = s.get("together_api_key") or ""
    fal = s.get("fal_api_key") or ""
    cnames = [c.get("name") for c in clist if c.get("name")]
    return {
        "provider": s.get("provider") or "gemini_pro",
        "has_gemini_pro": bool(psid and psidts),
        "has_gemini_pro_psid": bool(psid),
        "has_gemini_pro_psidts": bool(psidts),
        "has_gemini_pro_osid": bool(osid),
        "has_gemini_pro_sid": bool("SID" in cnames),
        "has_gemini_pro_ssid": bool("SSID" in cnames),
        "gemini_pro_hint": _mask_key(psid),
        "gemini_pro_ts_hint": _mask_key(psidts),
        "gemini_pro_osid_hint": _mask_key(osid),
        "gemini_cookies_count": len(clist),
        "gemini_cookies_names": cnames,
        "has_gemini": bool(gem),
        "gemini_hint": _mask_key(gem),
        "has_token": bool(tok),
        "token_hint": _mask_key(tok),
        "has_runware": bool(rw),
        "runware_hint": _mask_key(rw),
        "has_together": bool(tog),
        "together_hint": _mask_key(tog),
        "has_fal": bool(fal),
        "fal_hint": _mask_key(fal),
        "allow_fallback": bool(s.get("allow_fallback", True)),
    }


def _clear_gemini_webapi_cache() -> None:
    import tempfile
    for cdir in (
        Path(tempfile.gettempdir()) / "gemini_webapi",
        Path(os.path.expandvars(r"%TEMP%\gemini_webapi")),
    ):
        try:
            if cdir.exists():
                for f in cdir.glob(".cached_cookies_*.json"):
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        pass
        except Exception:
            pass


def _parse_cookie_block(raw_text: str) -> list[dict[str, str]]:
    """Extrae TODAS las cookies desde cualquier formato de F12:
    - Copy as cURL (cmd / bash)
    - Copy as PowerShell
    - Copy as fetch / Node.js
    - Copy request headers (cookie: ...)
    - Tabla de Application -> Cookies
    """
    raw = (raw_text or "").strip()
    if not raw:
        return []

    by_name: dict[str, dict[str, str]] = {}

    def _add_cookie(name: str, val: str, dom: str = "") -> None:
        n = name.strip().strip("\"'^\\")
        v = val.strip().strip("\"'^\\")
        if not n or not v or n.lower() in ("cookie", "path", "domain", "expires", "max-age", "secure", "httponly", "samesite"):
            return
        if "cookie:" in n.lower():
            n = re.split(r"cookie:\s*", n, flags=re.IGNORECASE)[-1].strip()
        n = re.sub(r"^[^a-zA-Z0-9_-]+", "", n).strip()
        if not n:
            return
        if not dom:
            dom = "gemini.google.com" if n in ("OSID", "__Secure-OSID", "COMPASS") else ".google.com"
        by_name[n] = {"name": n, "value": v, "domain": dom}

    # 1. Formato 'Copy as PowerShell': New-Object System.Net.Cookie("NAME", "VALUE", "/", "DOMAIN")
    ps_matches = re.findall(
        r'System\.Net\.Cookie\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,\s*["\'][^"\']*["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        raw,
    )
    for n, v, d in ps_matches:
        _add_cookie(n, v, d)
    if by_name:
        return list(by_name.values())

    # Limpiar escapes de Windows CMD (Copy as cURL cmd usa ^" y ^\^" y ^&)
    cleaned = raw.replace('^\\^"', '"').replace('^"', '"').replace("^'", "'").replace("^&", "&").replace("^\n", "").replace("^\r\n", "")

    # 2. Formato 'Copy as cURL' (-H "cookie: ..." / -b "..." / --cookie "...") o 'Copy as fetch' o headers
    cookie_strings: list[str] = []
    for pat in (
        r'(?i)(?:-H|--header)\s+["\']cookie:\s*([^"\']+)["\']',
        r'(?i)(?:-b|--cookie)\s+["\']([^"\']+)["\']',
        r'["\']?cookie["\']?\s*:\s*["\']([^"\']+)["\']',
        r'(?im)^cookie\s*:\s*(.+)$',
        r'(?im)\bcookie:\s*([^\r\n"\']+)',
    ):
        for m in re.finditer(pat, cleaned):
            cookie_strings.append(m.group(1).strip())

    if cookie_strings:
        for c_str in cookie_strings:
            for pair in c_str.split(";"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    _add_cookie(k, v)
        if by_name:
            return list(by_name.values())

    # 3. Formato Tabla F12 (separado por tabuladores)
    if "\t" in raw:
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if len(parts) >= 2:
                name, val = parts[0], parts[1]
                dom = ".google.com"
                for p in parts[2:]:
                    if "google.com" in p:
                        dom = p
                        break
                if name in ("OSID", "__Secure-OSID", "COMPASS") and dom == ".google.com":
                    dom = "gemini.google.com"
                _add_cookie(name, val, dom)
        if by_name:
            return list(by_name.values())

    # 4. Formato cadena directa k1=v1; k2=v2
    if ";" in cleaned and "=" in cleaned:
        for pair in cleaned.split(";"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                _add_cookie(k, v)
        if by_name:
            return list(by_name.values())

    return []


@app.post("/api/settings")
def save_settings_endpoint(req: SettingsRequest):
    if req.provider is not None:
        video_pipeline.IMAGE_SETTINGS["provider"] = req.provider.strip()
    if req.gemini_api_key is not None:
        val_gem = req.gemini_api_key.strip()
        if val_gem.startswith("hf_"):
            video_pipeline.IMAGE_SETTINGS["hf_token"] = val_gem
            video_pipeline._EXHAUSTED_HF_TOKENS.clear()
        else:
            video_pipeline.IMAGE_SETTINGS["gemini_api_key"] = val_gem

    cookie_updated = False
    existing = {
        c.get("name"): c
        for c in (video_pipeline.IMAGE_SETTINGS.get("gemini_cookies_list") or [])
        if c.get("name") and c.get("value")
    }

    # 1. Si se envía comando cURL completo o bloque de cookies, tiene prioridad máxima
    curl_candidates = [req.gemini_curl, req.gemini_osid, req.gemini_1psid, req.gemini_1psidts]
    for raw_field in curl_candidates:
        if raw_field:
            val = raw_field.strip()
            multi = _parse_cookie_block(val)
            if multi and len(multi) >= 2:
                # Bloque completo de sesión fresca: sincronizar exactamente la misma sesión
                existing.clear()
                for c in multi:
                    existing[c["name"]] = c
                    if c["name"] == "__Secure-1PSID":
                        video_pipeline.IMAGE_SETTINGS["gemini_1psid"] = c["value"]
                    elif c["name"] == "__Secure-1PSIDTS":
                        video_pipeline.IMAGE_SETTINGS["gemini_1psidts"] = c["value"]
                    elif c["name"] in ("__Secure-OSID", "OSID"):
                        video_pipeline.IMAGE_SETTINGS["gemini_osid"] = c["value"]
                cookie_updated = True
                break

    # 2. Procesar campos individuales si no venían en bloque multi-cookie
    if not cookie_updated:
        for raw_field, target_key in (
            (req.gemini_1psid, "gemini_1psid"),
            (req.gemini_1psidts, "gemini_1psidts"),
            (req.gemini_osid, "gemini_osid"),
        ):
            if raw_field is not None:
                val = raw_field.strip()
                if not val:
                    continue
                multi = _parse_cookie_block(val)
                if multi:
                    for c in multi:
                        existing[c["name"]] = c
                        if c["name"] == "__Secure-1PSID":
                            video_pipeline.IMAGE_SETTINGS["gemini_1psid"] = c["value"]
                        elif c["name"] == "__Secure-1PSIDTS":
                            video_pipeline.IMAGE_SETTINGS["gemini_1psidts"] = c["value"]
                        elif c["name"] in ("__Secure-OSID", "OSID"):
                            video_pipeline.IMAGE_SETTINGS["gemini_osid"] = c["value"]
                    cookie_updated = True
                else:
                    if val.startswith("sidts-"):
                        video_pipeline.IMAGE_SETTINGS["gemini_1psidts"] = val
                        existing["__Secure-1PSIDTS"] = {"name": "__Secure-1PSIDTS", "value": val, "domain": ".google.com"}
                    elif target_key == "gemini_osid":
                        video_pipeline.IMAGE_SETTINGS["gemini_osid"] = val
                        existing["__Secure-OSID"] = {"name": "__Secure-OSID", "value": val, "domain": "gemini.google.com"}
                        existing["OSID"] = {"name": "OSID", "value": val, "domain": "gemini.google.com"}
                    elif target_key == "gemini_1psid":
                        video_pipeline.IMAGE_SETTINGS["gemini_1psid"] = val
                        existing["__Secure-1PSID"] = {"name": "__Secure-1PSID", "value": val, "domain": ".google.com"}
                    else:
                        video_pipeline.IMAGE_SETTINGS[target_key] = val
                    cookie_updated = True

    # 3. Soporte para SID y SSID explícitos si se proporcionan por separado
    if req.gemini_sid is not None and req.gemini_sid.strip():
        existing["SID"] = {"name": "SID", "value": req.gemini_sid.strip(), "domain": ".google.com"}
        cookie_updated = True
    if req.gemini_ssid is not None and req.gemini_ssid.strip():
        existing["SSID"] = {"name": "SSID", "value": req.gemini_ssid.strip(), "domain": ".google.com"}
        cookie_updated = True

    if cookie_updated:
        # Asegurar concordancia absoluta entre claves raíz y gemini_cookies_list
        if video_pipeline.IMAGE_SETTINGS.get("gemini_1psid"):
            existing["__Secure-1PSID"] = {"name": "__Secure-1PSID", "value": video_pipeline.IMAGE_SETTINGS["gemini_1psid"], "domain": ".google.com"}
            existing["__Secure-3PSID"] = {"name": "__Secure-3PSID", "value": video_pipeline.IMAGE_SETTINGS["gemini_1psid"], "domain": ".google.com"}
        if video_pipeline.IMAGE_SETTINGS.get("gemini_1psidts"):
            existing["__Secure-1PSIDTS"] = {"name": "__Secure-1PSIDTS", "value": video_pipeline.IMAGE_SETTINGS["gemini_1psidts"], "domain": ".google.com"}
            existing["__Secure-3PSIDTS"] = {"name": "__Secure-3PSIDTS", "value": video_pipeline.IMAGE_SETTINGS["gemini_1psidts"], "domain": ".google.com"}
        if video_pipeline.IMAGE_SETTINGS.get("gemini_osid"):
            existing["__Secure-OSID"] = {"name": "__Secure-OSID", "value": video_pipeline.IMAGE_SETTINGS["gemini_osid"], "domain": "gemini.google.com"}
            existing["OSID"] = {"name": "OSID", "value": video_pipeline.IMAGE_SETTINGS["gemini_osid"], "domain": "gemini.google.com"}
        video_pipeline.IMAGE_SETTINGS["gemini_cookies_list"] = list(existing.values())
        _clear_gemini_webapi_cache()

    if req.runware_api_key is not None:
        video_pipeline.IMAGE_SETTINGS["runware_api_key"] = req.runware_api_key.strip()
    if req.together_api_key is not None:
        video_pipeline.IMAGE_SETTINGS["together_api_key"] = req.together_api_key.strip()
    if req.fal_api_key is not None:
        video_pipeline.IMAGE_SETTINGS["fal_api_key"] = req.fal_api_key.strip()
    if req.hf_token is not None:
        video_pipeline.IMAGE_SETTINGS["hf_token"] = req.hf_token.strip()
        video_pipeline._EXHAUSTED_HF_TOKENS.clear()
    if req.allow_fallback is not None:
        video_pipeline.IMAGE_SETTINGS["allow_fallback"] = bool(req.allow_fallback)
    elif "allow_fallback" not in video_pipeline.IMAGE_SETTINGS:
        video_pipeline.IMAGE_SETTINGS["allow_fallback"] = True

    SETTINGS_FILE.write_text(json.dumps(video_pipeline.IMAGE_SETTINGS, indent=2), encoding="utf-8")
    return get_settings_endpoint()


@app.post("/api/gemini-pro/verify-session")
def verify_gemini_pro_session_endpoint():
    """Verifica en tiempo real con Google si las cookies guardadas de Gemini Pro siguen activas y válidas."""
    import curl_cffi.requests as requests

    s = video_pipeline.IMAGE_SETTINGS
    psid = (s.get("gemini_1psid") or "").strip()
    psidts = (s.get("gemini_1psidts") or "").strip()
    osid = (s.get("gemini_osid") or "").strip()
    clist = s.get("gemini_cookies_list") or []

    if not psid:
        return {
            "valid": False,
            "status": "missing_cookies",
            "message": "Falta guardar las cookies de sesión de Gemini Pro. Pega el comando cURL cmd copiado de F12.",
            "cookies_count": len(clist),
        }

    c_names = {c.get("name") for c in clist if c.get("name")}
    has_sid = "SID" in c_names
    has_ssid = "SSID" in c_names
    has_osid = bool(osid) or "OSID" in c_names or "__Secure-OSID" in c_names

    session = requests.Session(impersonate="chrome124")
    for c in clist:
        n = c.get("name")
        v = c.get("value")
        d = c.get("domain", ".google.com")
        if n and v:
            session.cookies.set(n, v, domain=d)

    if psid:
        session.cookies.set("__Secure-1PSID", psid, domain=".google.com")
        session.cookies.set("__Secure-3PSID", psid, domain=".google.com")
    if psidts:
        session.cookies.set("__Secure-1PSIDTS", psidts, domain=".google.com")
        session.cookies.set("__Secure-3PSIDTS", psidts, domain=".google.com")
    if osid:
        session.cookies.set("__Secure-OSID", osid, domain="gemini.google.com")
        session.cookies.set("OSID", osid, domain="gemini.google.com")

    try:
        r = session.get("https://gemini.google.com/app", timeout=12, allow_redirects=False)
        # Si devuelve redirección HTTP hacia accounts.google.com / ServiceLogin:
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("location", "")
            if "accounts.google.com" in loc or "ServiceLogin" in loc:
                missing_note = ""
                if not has_sid or not has_ssid:
                    missing_note = " (Faltan las cookies maestras SID y SSID. Al copiar solo 3 cookies sueltas, Google rechaza la sesión. Usa 'Copy as cURL (cmd)' desde Network/Red para capturar las 18 cookies en 1 clic)."
                return {
                    "valid": False,
                    "status": "unauthenticated",
                    "message": f"Google rechazó la sesión y redirigió al login{missing_note}",
                    "cookies_count": len(clist),
                }

        # Si responde HTTP 200 en https://gemini.google.com/app:
        has_token = "SNlM0e" in r.text
        return {
            "valid": True,
            "status": "authenticated",
            "message": f"✅ ¡Sesión de Gemini Pro verificada y activa con Google! ({len(clist)} cookies sincronizadas{' · Token SNlM0e confirmado' if has_token else ''}). Lista para generar imágenes en máxima resolución.",
            "cookies_count": len(clist),
        }
    except Exception as e:
        return {
            "valid": False,
            "status": "network_error",
            "message": f"Error verificando cookies con Google: {e}",
            "cookies_count": len(clist),
        }
        return {
            "valid": False,
            "status": "network_error",
            "message": f"Error verificando cookies con Google: {e}",
            "cookies_count": len(clist),
        }


@app.post("/api/gemini-pro/login-browser")
def gemini_pro_login_browser_endpoint():
    """Abre una ventana de Chrome/Edge en https://gemini.google.com/app y captura automáticamente
    TODAS las cookies de sesión (__Secure-1PSID, __Secure-1PSIDTS, OSID, SID, etc.) en cuanto el usuario inicia sesión."""
    import subprocess
    import curl_cffi.requests

    browser_exe = None
    for candidate in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ):
        if Path(candidate).exists():
            browser_exe = candidate
            break
    if not browser_exe:
        raise HTTPException(status_code=500, detail="No se encontró Google Chrome ni Microsoft Edge instalado.")

    profile_dir = (BASE_DIR / ".gemini_pro_browser").resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    port = 9234

    # Forzar ventana visible (SW_SHOWNORMAL = 1) aunque el servidor corra en segundo plano
    si = None
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 1  # SW_SHOWNORMAL

    proc = subprocess.Popen(
        [
            browser_exe,
            f"--user-data-dir={profile_dir}",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            "https://gemini.google.com/app",
        ],
        startupinfo=si,
    )

    # Traer la ventana de Chrome al frente del escritorio en Windows
    if os.name == "nt":
        try:
            import ctypes
            time.sleep(1.2)
            user32 = ctypes.windll.user32
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def _bring_to_front(hwnd, lparam):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if "Gemini" in buf.value or "accounts.google" in buf.value.lower():
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                return True
            user32.EnumWindows(WNDENUMPROC(_bring_to_front), 0)
        except Exception:
            pass

    found_psid = ""
    found_psidts = ""
    found_cookies_list: list[dict[str, str]] = []
    deadline = time.time() + 120.0

    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                tabs_resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=2)
                if tabs_resp.status_code == 200:
                    tabs = tabs_resp.json()
                    ws_url = None
                    on_gemini_app = False
                    for tb in tabs:
                        tb_url = tb.get("url") or ""
                        if tb.get("webSocketDebuggerUrl") and tb_url.startswith("https://gemini.google.com") and "accounts.google.com" not in tb_url:
                            ws_url = tb["webSocketDebuggerUrl"]
                            on_gemini_app = True
                            break

                    if ws_url and on_gemini_app:
                        with curl_cffi.requests.Session() as sess:
                            ws = sess.ws_connect(ws_url)
                            ws.send_json({"id": 1, "method": "Network.getAllCookies"})
                            msg = ws.recv_json()
                            ws.close()
                        cookies = (msg.get("result") or {}).get("cookies") or []
                        cmap = {
                            c.get("name"): c.get("value")
                            for c in cookies
                            if "google.com" in (c.get("domain") or "")
                        }
                        # Verificar que esté autenticado en gemini.google.com (con OSID/__Secure-OSID y __Secure-1PSID)
                        has_gemini_osid = bool(cmap.get("OSID") or cmap.get("__Secure-OSID"))
                        if cmap.get("__Secure-1PSID") and has_gemini_osid and (cmap.get("SID") or cmap.get("__Secure-1PAPISID") or cmap.get("SSID")):
                            found_psid = cmap["__Secure-1PSID"]
                            found_psidts = cmap.get("__Secure-1PSIDTS", "")
                            found_cookies_list = [
                                {
                                    "name": str(c.get("name")),
                                    "value": str(c.get("value")),
                                    "domain": str(c.get("domain") or ".google.com"),
                                }
                                for c in cookies
                                if "google.com" in (c.get("domain") or "") and c.get("name") and c.get("value")
                            ]
                            break
            except Exception:
                pass
            time.sleep(1.5)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

    if not found_psid:
        raise HTTPException(
            status_code=400,
            detail="No se detectó inicio de sesión completo en gemini.google.com antes de cerrar la ventana. Inténtalo de nuevo y espera a que cargue el chat de Gemini.",
        )

    _clear_gemini_webapi_cache()
    video_pipeline.IMAGE_SETTINGS["gemini_1psid"] = found_psid
    video_pipeline.IMAGE_SETTINGS["gemini_1psidts"] = found_psidts
    video_pipeline.IMAGE_SETTINGS["gemini_cookies_list"] = found_cookies_list
    video_pipeline.IMAGE_SETTINGS["provider"] = "gemini_pro"
    SETTINGS_FILE.write_text(json.dumps(video_pipeline.IMAGE_SETTINGS, indent=2), encoding="utf-8")
    return get_settings_endpoint()


_PROJECT_RENDER_LOCKS: dict[str, threading.Lock] = {}
_PROJECT_RENDER_LOCKS_MUTEX = threading.Lock()


def _get_project_render_lock(project_id: str) -> threading.Lock:
    with _PROJECT_RENDER_LOCKS_MUTEX:
        if project_id not in _PROJECT_RENDER_LOCKS:
            _PROJECT_RENDER_LOCKS[project_id] = threading.Lock()
        return _PROJECT_RENDER_LOCKS[project_id]


@app.post("/api/project/{project_id}/render")
def render_video_endpoint(project_id: str, req: RenderVideoRequest):
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    lock = _get_project_render_lock(project_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ya se está renderizando este video. Por favor espera a que termine.")

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["transition"] = req.transition
        meta["transition_duration"] = req.transition_duration
        meta["subtitle_style"] = req.subtitle_style
        meta["camera_effect"] = req.camera_effect
        meta["bg_music"] = req.bg_music
        meta["bg_music_volume"] = req.bg_music_volume

        custom_music_file = proj_dir / "custom_bg_music.bin"
        if req.custom_music_b64:
            try:
                custom_music_file.write_bytes(_decode_b64_image(req.custom_music_b64))
            except Exception as exc:
                print(f"Aviso al guardar música personalizada en render: {exc}")

        render_project_video(
            project_dir=proj_dir,
            scenes=meta["scenes"],
            width=meta["width"],
            height=meta["height"],
            burn_subtitles=req.burn_subtitles,
            transition=req.transition,
            transition_duration=req.transition_duration,
            subtitle_style=req.subtitle_style,
            camera_effect=req.camera_effect,
            bg_music=req.bg_music,
            bg_music_volume=req.bg_music_volume,
            custom_music_path=custom_music_file if custom_music_file.exists() else None,
        )
        create_project_zip(proj_dir, meta)

        meta["video_url"] = f"/projects/{project_id}/video_youtube.mp4?t={int(time.time())}"
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        lock.release()


@app.get("/api/project/{project_id}/zip")
def download_project_zip_endpoint(project_id: str):
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    zip_path = create_project_zip(proj_dir, meta)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{project_id}_paquete_youtube.zip",
    )


@app.get("/")
def serve_index():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


# ==============================================================================================
# 🍓 FRUTINOVELAS: Guion de diálogos multi-voz + animación local de personajes
# ==============================================================================================

class FrutiParseRequest(BaseModel):
    script: str = Field(..., min_length=3, max_length=100000)


class FrutiCharacterIn(BaseModel):
    name: str
    slug: str
    voice: str = "es_m_eric"
    speed: float = Field(1.0, ge=0.6, le=1.6)
    description: str = ""
    fruit: str = Field("", description="Fruta o verdura del personaje en español (ej. 'fresa')")
    gender: str = "M"
    color: str = "#ffffff"
    is_narrator: bool = False


class FrutiCreateRequest(BaseModel):
    script: str = Field(..., min_length=3, max_length=100000)
    characters: list[FrutiCharacterIn]
    style_prompt: str = Field("", description="Estilo visual (vacío = estilo 3D Pixar de frutinovela)")
    setting: str = Field("", description="Escenario / locación en español")
    aspect_ratio: str = Field("9:16")
    line_pause: float = Field(0.35, ge=0.0, le=2.0)
    lang: str = Field("es-mx")


class FrutiImageRequest(BaseModel):
    prompt: Optional[str] = None
    variation: bool = False


class FrutiUploadRequest(BaseModel):
    image_b64: str


class FrutiMouthRequest(BaseModel):
    x: float = Field(0.5, ge=0.0, le=1.0)
    y: float = Field(0.6, ge=0.0, le=1.0)
    w: float = Field(0.14, ge=0.02, le=0.6)
    enabled: bool = True


class FrutiLineRequest(BaseModel):
    emotion: str = "normal"


class FrutiRenderRequest(BaseModel):
    burn_subtitles: bool = True
    intensity: float = Field(1.0, ge=0.0, le=2.0)
    music_b64: Optional[str] = Field(None, description="Música de fondo opcional (mp3/wav en base64)")
    music_ext: str = Field("mp3")
    music_volume: float = Field(0.15, ge=0.0, le=1.0)
    remove_music: bool = False


def _fruti_meta(project_id: str) -> tuple[Path, Path, dict[str, Any]]:
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Frutinovela no encontrada.")
    return proj_dir, meta_file, json.loads(meta_file.read_text(encoding="utf-8"))


def _fruit_to_en(fruit_es: str, fallback: str) -> str:
    f = (fruit_es or "").strip()
    if not f:
        return fallback
    detected = fruti.detect_fruit(f)
    return detected or translate_es_to_en(f) or fallback


@app.post("/api/fruti/parse")
def fruti_parse_endpoint(req: FrutiParseRequest):
    lines = fruti.parse_dialogue_script(req.script)
    if not lines:
        raise HTTPException(status_code=400, detail="No se detectaron diálogos. Usa el formato  [Personaje]: texto")
    chars = fruti.default_character_profiles(lines)
    fruit_es_by_en = {v: k for k, v in fruti.FRUIT_MAP.items()}
    for c in chars:
        c["fruit"] = fruit_es_by_en.get(c.get("fruit_en", ""), "")
    return {"characters": chars, "lines": lines, "emotions": fruti.EMOTIONS}


@app.post("/api/fruti/create")
def fruti_create_endpoint(req: FrutiCreateRequest):
    lines = fruti.parse_dialogue_script(req.script)
    if not lines:
        raise HTTPException(status_code=400, detail="El guion no contiene diálogos válidos.")

    chars_in = {c.slug: c for c in req.characters}
    defaults = {c["slug"]: c for c in fruti.default_character_profiles(lines)}

    project_id = f"fruti_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    proj_dir = PROJECTS_DIR / project_id
    (proj_dir / "audio").mkdir(parents=True, exist_ok=True)
    (proj_dir / "images").mkdir(parents=True, exist_ok=True)
    width, height = (720, 1280) if req.aspect_ratio == "9:16" else (1280, 720)

    characters: list[dict[str, Any]] = []
    for slug, d in defaults.items():
        c_in = chars_in.get(slug)
        ch = dict(d)
        if c_in:
            ch.update(
                voice=c_in.voice,
                speed=c_in.speed,
                description=c_in.description,
                gender=c_in.gender or d["gender"],
                color=c_in.color or d["color"],
                fruit=c_in.fruit,
            )
            ch["fruit_en"] = _fruit_to_en(c_in.fruit, d.get("fruit_en") or "fruit")
        if ch["voice"] not in KOKORO_VOICE_CATALOG:
            ch["voice"] = d["voice"]
        ch["mouth"] = {"x": 0.5, "y": 0.58, "w": 0.14, "enabled": True}
        ch["image_url"] = None
        ch["variation"] = 0
        characters.append(ch)
    by_slug = {c["slug"]: c for c in characters}

    # PASO 1: Sintetizar cada diálogo con la voz de su personaje y calcular timestamps
    master: list[np.ndarray] = []
    t = 0.0
    sr = 24000
    for idx, ln in enumerate(lines, start=1):
        ch = by_slug[ln["slug"]]
        speed = float(ch["speed"]) * fruti.EMOTION_SPEED.get(ln["emotion"], 1.0)
        samples, sr = _synthesize_segment_samples(
            text=ln["text"], engine="kokoro", voice_id=ch["voice"], lang=req.lang,
            speed=max(0.5, min(2.0, speed)), sentence_pause=0.15, noise_scale=0.667,
        )
        samples = samples.astype(np.float32)
        if ln["emotion"] == "susurro":
            samples *= 0.7
        speech_dur = len(samples) / float(sr)
        pause = np.zeros(int(sr * req.line_pause), dtype=np.float32)
        full = np.concatenate([samples, pause])
        sf.write(proj_dir / "audio" / f"line_{idx:03d}.wav", full, sr, format="WAV", subtype="PCM_16")
        master.append(full)
        dur = len(full) / float(sr)
        ln.update(
            index=idx,
            start_sec=round(t, 3),
            speech_end_sec=round(t + speech_dur, 3),
            end_sec=round(t + dur, 3),
            duration_sec=round(dur, 3),
            timestamp_label=fruti.timestamp_label(t, t + speech_dur),
            audio_url=f"/projects/{project_id}/audio/line_{idx:03d}.wav",
        )
        t += dur

    master_samples = np.concatenate(master) if master else np.zeros(2400, dtype=np.float32)
    sf.write(proj_dir / "narracion_completa.wav", master_samples, sr, format="WAV", subtype="PCM_16")
    (proj_dir / "subtitulos.srt").write_text(fruti.generate_fruti_srt(lines), encoding="utf-8")

    # PASO 2: Prompts visuales (1 retrato por personaje + 1 toma grupal para el narrador)
    setting_en = translate_es_to_en(req.setting) if req.setting.strip() else ""
    style = req.style_prompt.strip() or fruti.DEFAULT_FRUTI_STYLE
    for ch in characters:
        if not ch["is_narrator"]:
            ch["prompt"] = fruti.build_character_prompt(ch, style, setting_en)
    group = {
        "slug": "_group",
        "name": "Toma grupal (Narrador)",
        "prompt": fruti.build_group_prompt(characters, style, setting_en),
        "image_url": None,
        "variation": 0,
    }

    meta = {
        "type": "fruti",
        "project_id": project_id,
        "width": width,
        "height": height,
        "aspect_ratio": req.aspect_ratio,
        "style_prompt": style,
        "setting": req.setting,
        "seed": random.randint(1000, 9_999_999),
        "characters": characters,
        "group": group,
        "lines": lines,
        "total_duration_sec": round(t, 2),
        "master_audio_url": f"/projects/{project_id}/narracion_completa.wav",
        "srt_url": f"/projects/{project_id}/subtitulos.srt",
        "video_url": None,
        "has_music": False,
        "emotions": fruti.EMOTIONS,
    }
    (proj_dir / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.get("/api/fruti/{project_id}")
def fruti_get_endpoint(project_id: str):
    return _fruti_meta(project_id)[2]


def _fruti_target(meta: dict[str, Any], slug: str) -> dict[str, Any]:
    if slug == "_group":
        return meta["group"]
    for ch in meta["characters"]:
        if ch["slug"] == slug and not ch.get("is_narrator"):
            return ch
    raise HTTPException(status_code=404, detail="Personaje no encontrado.")


@app.post("/api/fruti/{project_id}/character/{slug}/image")
def fruti_character_image_endpoint(project_id: str, slug: str, req: FrutiImageRequest):
    proj_dir, meta_file, meta = _fruti_meta(project_id)
    target = _fruti_target(meta, slug)
    if req.prompt and req.prompt.strip():
        target["prompt"] = req.prompt.strip()
    if req.variation:
        target["variation"] = int(target.get("variation", 0)) + 1
    seed = int(meta["seed"]) + 7919 * int(target.get("variation", 0)) + (sum(map(ord, slug)) * 31)
    dest = proj_dir / "images" / f"char_{slug}.png"
    try:
        generate_image_for_scene(prompt=target["prompt"], width=meta["width"], height=meta["height"], dest_path=dest, seed=seed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    target["image_url"] = f"/projects/{project_id}/images/char_{slug}.png?t={int(time.time())}"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.post("/api/fruti/{project_id}/character/{slug}/upload")
def fruti_character_upload_endpoint(project_id: str, slug: str, req: FrutiUploadRequest):
    """Permite usar una imagen propia (hecha en Gemini, Bing, Midjourney, etc.) para el personaje."""
    proj_dir, meta_file, meta = _fruti_meta(project_id)
    target = _fruti_target(meta, slug)
    try:
        img = Image.open(io.BytesIO(_decode_b64_image(req.image_b64))).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Imagen inválida: {exc}") from exc
    img.save(proj_dir / "images" / f"char_{slug}.png", format="PNG")
    target["image_url"] = f"/projects/{project_id}/images/char_{slug}.png?t={int(time.time())}"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.post("/api/fruti/{project_id}/character/{slug}/mouth")
def fruti_character_mouth_endpoint(project_id: str, slug: str, req: FrutiMouthRequest):
    _, meta_file, meta = _fruti_meta(project_id)
    target = _fruti_target(meta, slug)
    target["mouth"] = {"x": req.x, "y": req.y, "w": req.w, "enabled": req.enabled}
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.post("/api/fruti/{project_id}/line/{index}")
def fruti_line_endpoint(project_id: str, index: int, req: FrutiLineRequest):
    _, meta_file, meta = _fruti_meta(project_id)
    if req.emotion not in fruti.EMOTIONS:
        raise HTTPException(status_code=400, detail="Emoción inválida.")
    for ln in meta["lines"]:
        if ln["index"] == index:
            ln["emotion"] = req.emotion
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


@app.post("/api/fruti/{project_id}/render")
def fruti_render_endpoint(project_id: str, req: FrutiRenderRequest):
    proj_dir, meta_file, meta = _fruti_meta(project_id)
    music_path = None
    for old in proj_dir.glob("musica_fondo.*"):
        if req.remove_music or req.music_b64:
            old.unlink(missing_ok=True)
        else:
            music_path = old
    if req.music_b64 and not req.remove_music:
        ext = re.sub(r"[^a-z0-9]", "", req.music_ext.lower())[:4] or "mp3"
        music_path = proj_dir / f"musica_fondo.{ext}"
        music_path.write_bytes(_decode_b64_image(req.music_b64))
    try:
        fruti.render_frutinovela_video(
            proj_dir, meta, burn_subtitles=req.burn_subtitles, intensity=req.intensity,
            music_path=music_path, music_volume=req.music_volume,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    meta["has_music"] = bool(music_path)
    meta["video_url"] = f"/projects/{project_id}/frutinovela.mp4?t={int(time.time())}"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


from studio.api import init_studio_router
from studio.opuscar.api import router as opuscar_router
from studio.animated_shorts.api import router as animated_shorts_router
from studio.omni_bridge import (
    OMNI_TOPIC_PRESETS,
    generate_omni_hybrid_script,
    render_omni_hybrid_video,
)

class OmniScriptRequest(BaseModel):
    topic: str = ""

class OmniRenderRequest(BaseModel):
    title: str
    acts: list[dict[str, Any]]
    voice: str = "es-MX-JorgeNeural"
    format: str = "vertical"

class OpuscarToYouTubeRequest(BaseModel):
    title: str
    scenes: list[dict[str, Any]]
    style: str = "cinematic"
    voice: str = "es-MX-JorgeNeural"

@app.get("/api/omni/topics")
def get_omni_topics():
    return {"status": "success", "topics": OMNI_TOPIC_PRESETS}

@app.post("/api/omni/script")
def get_omni_script(req: OmniScriptRequest):
    return generate_omni_hybrid_script(req.topic)

@app.post("/api/omni/render")
async def render_omni_video_endpoint(req: OmniRenderRequest):
    try:
        mp4_path, dur = await render_omni_hybrid_video(
            title=req.title,
            acts=req.acts,
            voice=req.voice,
            format_type=req.format,
        )
        proj_name = mp4_path.parent.name
        return {
            "status": "success",
            "title": req.title,
            "duration": dur,
            "video_url": f"/projects/{proj_name}/video_youtube.mp4",
            "zip_url": f"/projects/{proj_name}/paquete_youtube.zip",
            "project_id": proj_name,
        }
    except Exception as exc:
        print(f"Error al compilar video Omni-Studio: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/opuscar/export-to-youtube")
def export_opuscar_to_youtube(req: OpuscarToYouTubeRequest):
    slug = re.sub(r"[^a-zA-Z0-9_]", "", req.title.lower().replace(" ", "_"))[:25]
    project_id = f"yt_{int(time.time())}_{slug}"
    p_dir = PROJECTS_DIR / project_id
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "images").mkdir(parents=True, exist_ok=True)
    (p_dir / "audio").mkdir(parents=True, exist_ok=True)
    
    yt_scenes = []
    accum_t = 0.0
    for idx, sc in enumerate(req.scenes, start=1):
        dur = float(sc.get("duration", 8.0))
        text = sc.get("narration") or sc.get("text") or sc.get("title", f"Escena {idx}")
        yt_scenes.append({
            "index": idx,
            "text": text,
            "start_sec": accum_t,
            "end_sec": accum_t + dur,
            "duration_sec": dur,
            "timestamp_label": f"{video_pipeline.format_mm_ss(accum_t)} - {video_pipeline.format_mm_ss(accum_t + dur)}",
            "image_prompt": f"Cinematic photorealistic 8k render, {req.title}, {text[:100]}, no text",
            "image_url": None,
        })
        accum_t += dur
        
    meta = {
        "project_id": project_id,
        "title": req.title,
        "style": req.style,
        "width": 1920,
        "height": 1080,
        "voice": req.voice,
        "scenes": yt_scenes,
        "created_at": time.time(),
    }
    (p_dir / "project.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "success", "project_id": project_id, "meta": meta}

app.include_router(init_studio_router(PROJECTS_DIR, _synthesize_segment_samples))
app.include_router(opuscar_router)
app.include_router(animated_shorts_router)

app.mount("/projects", StaticFiles(directory=str(PROJECTS_DIR)), name="projects")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("app:app", host=host, port=port, reload=False)
