import base64
import io
import json
import logging
import os
import random
import re
import shutil
import subprocess
import textwrap
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import imageio_ffmpeg
import numpy as np
import requests
from deep_translator import MyMemoryTranslator
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger("video_pipeline")

STYLE_PRESETS = {
    "cinematic": "Cinematic photorealistic 8k movie still, dramatic volumetric lighting, shallow depth of field, ultra detailed, no text, no watermark",
    "documentary": "National Geographic and Netflix historical documentary style photography, moody atmospheric lighting, hyper-realistic, 8k, no text",
    "scifi": "Futuristic cyberpunk sci-fi concept art, neon accents, Unreal Engine 5 render, cinematic composition, 8k, no text",
    "anime": "High quality anime feature film background and character art, Makoto Shinkai style lighting, vibrant colors, detailed, no text",
    "3d_animation": "Pixar and DreamWorks 3D animated movie style, soft global illumination, expressive, rich textures, 8k render, no text",
    "dark_mystery": "Dark mystery thriller atmosphere, chiaroscuro lighting, cinematic shadows, moody and suspenseful photography, no text",
    "illustration": "Modern digital editorial illustration, dramatic composition, concept art, no text",
    "3d_blender": "Photorealistic 3D engineering cutaway diorama render, Blender Eevee Next studio lighting, exploded view mechanical model, metallic materials, high precision, octane render look, 8k, no text",
    "sketch_bw": "Hand-drawn black ink line art sketch on a pure white background, minimalist stick figure / pencil-sketch look, no color, no text, no watermark",
    "none": "",
    "custom_only": "",
}


def format_srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total_sec = int(seconds)
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def format_mm_ss(seconds: float) -> str:
    mins = int(seconds) // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


def translate_es_to_en(text: str) -> str:
    """Traduce el texto hablado de un timestamp al inglés para que FLUX.1 comprenda
    con precisión cada objeto, acción, lugar y emoción mencionada en ese instante."""
    clean = text.strip()
    if not clean:
        return ""
    # 1. Google Translate API directa y veloz
    try:
        from urllib.parse import quote
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=es&tl=en&dt=t&q={quote(clean)}"
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"},
            timeout=6,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and data[0]:
                translated = "".join([part[0] for part in data[0] if part and part[0]]).strip()
                if translated:
                    return translated
    except Exception:
        pass

    # 2. Respaldo MyMemory
    try:
        translated = MyMemoryTranslator(source="es-ES", target="en-US").translate(clean)
        if translated and isinstance(translated, str) and "MYMEMORY WARNING" not in translated.upper():
            return translated.strip()
    except Exception:
        pass
    return clean


def analyze_reference_image(img_bytes: bytes) -> dict[str, Any]:
    """Analiza una imagen de referencia para extraer su atmósfera lumínica, contraste,
    temperatura de color y paleta cromática para guiar la generación de todas las escenas."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    small = img.resize((128, 128), Image.Resampling.BILINEAR)
    arr = np.asarray(small, dtype=np.float32) / 255.0

    r_mean, g_mean, b_mean = float(arr[:, :, 0].mean()), float(arr[:, :, 1].mean()), float(arr[:, :, 2].mean())
    luminance = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    lum_mean = float(luminance.mean())
    lum_std = float(luminance.std())

    max_c = arr.max(axis=2)
    min_c = arr.min(axis=2)
    sat = np.where(max_c > 1e-4, (max_c - min_c) / np.maximum(max_c, 1e-4), 0.0)
    sat_mean = float(sat.mean())

    if lum_mean < 0.28:
        lighting_en = "low-key dark atmospheric lighting, deep dramatic shadows, chiaroscuro mood"
        lighting_es = "Iluminación oscura / Low-key dramática"
    elif lum_mean > 0.68:
        lighting_en = "high-key bright luminous lighting, soft clean exposure"
        lighting_es = "Iluminación brillante / High-key clara"
    else:
        lighting_en = "balanced cinematic lighting, rich midtones"
        lighting_es = "Iluminación cinematográfica equilibrada"

    if lum_std > 0.26:
        contrast_en = "high contrast dramatic dynamic range"
        contrast_es = "Alto contraste"
    elif lum_std < 0.14:
        contrast_en = "soft muted contrast, hazy atmospheric depth"
        contrast_es = "Contraste suave / Atmosférico"
    else:
        contrast_en = "natural filmic contrast"
        contrast_es = "Contraste fílmico natural"

    if sat_mean < 0.14:
        sat_en = "monochromatic desaturated noir color palette"
        sat_es = "Paleta desaturada / Noir"
    elif sat_mean < 0.30:
        sat_en = "muted cinematic film color grading"
        sat_es = "Colores sobrios de cine"
    elif sat_mean > 0.58:
        sat_en = "vibrant hyper-saturated rich colors"
        sat_es = "Colores vibrantes de alta saturación"
    else:
        sat_en = "rich natural color harmony"
        sat_es = "Saturación cromática rica"

    warmth = r_mean - b_mean
    if warmth > 0.09:
        temp_en = "warm golden amber and sepia color cast"
        temp_es = "Tonos cálidos / Ámbar"
    elif warmth < -0.08:
        temp_en = "cool cyan and deep blue atmospheric color cast"
        temp_es = "Tonos fríos / Azulados"
    else:
        temp_en = "balanced teal and warm highlights color grading"
        temp_es = "Balance térmico neutro / Teal & Orange"

    quant = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT).convert("RGB")
    q_colors = quant.getcolors() or []
    q_colors.sort(key=lambda x: x[0], reverse=True)
    hex_palette = []
    for _, rgb in q_colors[:5]:
        hex_palette.append(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")

    extracted_prompt = f"{lighting_en}, {contrast_en}, {sat_en}, {temp_en}, dominant color palette ({', '.join(hex_palette[:3])})"
    summary_es = f"{lighting_es} · {contrast_es} · {sat_es} · {temp_es}"

    return {
        "extracted_prompt": extracted_prompt,
        "summary_es": summary_es,
        "palette": hex_palette,
    }


def apply_reference_color_match(
    target_img: Image.Image,
    ref_img: Image.Image,
    strength: float = 0.55,
) -> Image.Image:
    """Transfiere la atmósfera cromática e iluminación de la imagen de referencia (Reinhard color grading)
    a cada escena generada para mantener consistencia visual entre todas las imágenes del video."""
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0.01:
        return target_img

    tgt = np.asarray(target_img.convert("RGB"), dtype=np.float32)
    ref = np.asarray(ref_img.convert("RGB").resize(target_img.size, Image.Resampling.BILINEAR), dtype=np.float32)

    matched = np.empty_like(tgt)
    for c in range(3):
        t_mean, t_std = tgt[:, :, c].mean(), max(tgt[:, :, c].std(), 1.0)
        r_mean, r_std = ref[:, :, c].mean(), max(ref[:, :, c].std(), 1.0)
        blended_std = t_std * (1.0 - 0.6 * strength) + r_std * (0.6 * strength)
        normalized = (tgt[:, :, c] - t_mean) * (blended_std / t_std) + r_mean
        matched[:, :, c] = (1.0 - strength) * tgt[:, :, c] + strength * normalized

    matched = np.clip(matched, 0, 255).astype(np.uint8)
    return Image.fromarray(matched, mode="RGB")


def _split_long_sentence_into_visual_beats(sentence: str, max_beat_chars: int = 135) -> list[str]:
    """Si una oración es larga y contiene varias ideas separadas por conectores o signos,
    la divide en pulsos visuales ('beats') para que cada timestamp tenga su propia imagen alusiva."""
    sentence = sentence.strip()
    if len(sentence) <= max_beat_chars:
        return [sentence]

    # Dividir primero por punto y coma, dos puntos o conectores narrativos fuertes
    parts = re.split(
        r"(?<=[;:])\s+|,\s+(?=pero\b|aunque\b|mientras\b|donde\b|cuando\b|sin embargo\b|hasta que\b|porque\b|ya que\b)",
        sentence,
        flags=re.IGNORECASE,
    )
    beats: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if not current:
            current = part
        elif len(current) + 2 + len(part) <= max_beat_chars:
            current = f"{current}, {part}" if not current.endswith((";", ":")) else f"{current} {part}"
        else:
            if len(current) >= 35:
                beats.append(current)
                current = part
            else:
                current = f"{current}, {part}"
    if current:
        if beats and len(current) < 35:
            beats[-1] = f"{beats[-1]} {current}"
        else:
            beats.append(current)
    return beats


def split_script_into_scenes(script: str, mode: str = "sentence") -> list[str]:
    """Divide el guion en fragmentos para calcular primero el timestamp exacto de cada frase
    y luego generar una imagen directamente alusiva a lo que dice ese timestamp.
    - 'sentence' (Recomendado): 1 timestamp e imagen por cada oración/idea hablada (~4-8 seg).
    - 'auto': agrupa ideas cortas en bloques de ~8-12 seg.
    - 'paragraph': 1 timestamp e imagen por cada párrafo.
    """
    paragraphs = [p.strip() for p in re.split(r"\n+", script) if p.strip()]
    if not paragraphs:
        return []

    if mode == "paragraph":
        scenes: list[str] = []
        for p in paragraphs:
            if len(p) <= 380:
                scenes.append(p)
            else:
                scenes.extend(_group_sentences(p, target_chars=260))
        return scenes

    if mode == "sentence":
        raw_beats: list[str] = []
        for p in paragraphs:
            sents = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", p) if s.strip()]
            for s in sents:
                raw_beats.extend(_split_long_sentence_into_visual_beats(s, max_beat_chars=140))

        # Unir fragmentos demasiado breves (<30 caracteres) con el siguiente para evitar timestamps de <1.5s
        merged_beats: list[str] = []
        buffer = ""
        for b in raw_beats:
            if not buffer:
                buffer = b
            elif len(buffer) < 35:
                buffer = f"{buffer} {b}"
            else:
                merged_beats.append(buffer)
                buffer = b
        if buffer:
            if merged_beats and len(buffer) < 28:
                merged_beats[-1] = f"{merged_beats[-1]} {buffer}"
            else:
                merged_beats.append(buffer)
        return merged_beats

    # Modo 'auto' (~8-12 seg por imagen)
    scenes = []
    for p in paragraphs:
        scenes.extend(_group_sentences(p, target_chars=175))
    return scenes


def _group_sentences(text: str, target_chars: int = 175) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…;])\s+", text) if s.strip()]
    grouped: list[str] = []
    current = ""
    for sent in sentences:
        if not current:
            current = sent
        elif len(current) + 1 + len(sent) <= target_chars:
            current = f"{current} {sent}"
        else:
            grouped.append(current)
            current = sent
    if current:
        grouped.append(current)
    return grouped


import os
import uuid
from urllib.parse import quote

# Ajustes de generación de imágenes (los carga/guarda app.py desde settings.json)
IMAGE_SETTINGS: dict[str, Any] = {
    "provider": os.environ.get("IMAGE_PROVIDER", "auto"),
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "gemini_1psid": os.environ.get("GEMINI_1PSID", ""),
    "gemini_1psidts": os.environ.get("GEMINI_1PSIDTS", ""),
    "hf_token": os.environ.get("HF_TOKEN", ""),
    "runware_api_key": os.environ.get("RUNWARE_API_KEY", ""),
    "together_api_key": os.environ.get("TOGETHER_API_KEY", ""),
    "fal_api_key": os.environ.get("FAL_API_KEY", ""),
    "allow_fallback": True,
}
try:
    _sfile = Path(__file__).parent / "settings.json"
    if _sfile.exists():
        IMAGE_SETTINGS.update(json.loads(_sfile.read_text(encoding="utf-8")))
except Exception:
    pass

_LAST_GEMINI_CALL_TS: float = 0.0


def _hf_headers(use_token: bool = True, rotate_ip: bool = False) -> dict[str, str]:
    """Cabeceras para los Spaces de Hugging Face.
    Si el token agotó su cuota diaria de ZeroGPU (0s left), permite rotar sesión con X-Forwarded-For."""
    headers = {"User-Agent": "Mozilla/5.0"}
    token = (IMAGE_SETTINGS.get("hf_token") or "").strip()
    if use_token and token:
        headers["Authorization"] = f"Bearer {token}"
    if rotate_ip:
        ip = f"{random.randint(11, 199)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        headers["X-Forwarded-For"] = ip
        headers["X-Real-IP"] = ip
    return headers


FIXED_COMPOSITION = (
    "Identical layout rules for every image in the series: one clear main subject, "
    "full scene visible with the same camera distance and framing, uncluttered background, "
    "same drawing/rendering technique and same character design in all images"
)


def extract_key_elements(english_text: str, max_items: int = 4) -> list[str]:
    """Separa la frase hablada (ya traducida) en elementos visuales concretos (sujeto, acción,
    lugar, contraste) para que el generador dibuje exactamente lo que se menciona y nada más."""
    text = re.sub(r"[\"«»¡!¿?]", "", english_text or "").strip().rstrip(".")
    pieces = re.split(r",|;|:|\bbut\b|\bwhile\b|\bwhere\b|\bthat\b|\bso\b|\band\b|\bwhich\b|\bbecause\b", text, flags=re.IGNORECASE)
    items: list[str] = []
    for p in pieces:
        p = re.sub(r"^(even so|however|then|also|just|only)\s+", "", p.strip(), flags=re.IGNORECASE).strip()
        if len(p.split()) >= 3 and p.lower() not in (i.lower() for i in items):
            items.append(p)
    return items[:max_items]


# Reglas universales (compatibles con cualquier época o tema) para volver concretas frases abstractas
_VISUAL_EXPANSION_RULES: list[tuple[str, str]] = [
    (
        r"\b(neanderthal|cave|prehistoric|stone age|pleistocene|ancient human)\b",
        "a prehistoric stone cave illuminated by a warm campfire, rough rock walls, and a primitive character inside the cave",
    ),
    (
        r"\b(tooth|teeth|jaw|dental|dentist|mouth|infection|ache|pain)\b",
        "a character wincing in pain while holding his swollen jaw and cheek with one hand",
    ),
    (
        r"\b(plant|herb|bark|mushrooms?|mold|penicillin|aspirin|remedy|medicinal)\b",
        "wild green medicinal plants, tree bark, and natural moss/mold growing on damp rocks being gathered and examined",
    ),
    (
        r"\b(scientist|researcher|archaeologist|fossil|skull|skeleton|dna|microscope|laboratory)\b",
        "scientists in a research laboratory examining an ancient fossilized jawbone and teeth under a magnifying lens and microscope",
    ),
    (
        r"\b(ocean|trench|deep sea|submarine|abyss|bioluminescent|underwater)\b",
        "a deep dark underwater ocean trench with glowing bioluminescent marine creatures swimming in the abyss",
    ),
    (
        r"\b(bunker|radar|soviet|cold war|missile|nuclear|icbm|warhead|launch)\b",
        "a military radar control room with glowing radar screens, a world map display on the wall, and an operator at the console",
    ),
    (
        r"\b(satellite|orbit|space|sunlight reflecting)\b",
        "an orbital satellite high in space above the curved Earth with sunlight glinting off high-altitude clouds",
    ),
]


def _generate_storyboard_descriptions_with_gemini_llm(spanish_texts: list[str]) -> Optional[list[str]]:
    """Usa el modelo gratuito de texto/visión de Google AI Studio (gemini-3.1-flash-lite / gemini-3-flash-preview)
    como Director de Storyboard para convertir cada oración del guion en una composición visual icónica en inglés,
    con objetos centrales claros y acciones físicas fáciles de dibujar por modelos de difusión."""
    api_key = (IMAGE_SETTINGS.get("gemini_api_key") or "").strip()
    if not api_key or not spanish_texts:
        return None

    results: list[str] = []
    batch_size = 25
    models = ["gemini-3.1-flash-lite-preview", "gemini-3-flash-preview", "gemma-4-31b-it"]

    for start_idx in range(0, len(spanish_texts), batch_size):
        batch = spanish_texts[start_idx : start_idx + batch_size]
        numbered = "\n".join(f"{i + 1}. {txt}" for i, txt in enumerate(batch))
        prompt = (
            "You are an expert storyboard illustrator (like Kurzgesagt / WaitButWhy / MinuteEarth) designing clear 2D educational illustrations.\n"
            f"Below are {len(batch)} consecutive Spanish narration lines from a script.\n"
            "For EACH numbered line, design ONE unmistakable, iconic visual scene (18 to 30 English words max) that directly illustrates the exact point being spoken.\n"
            "CRITICAL RULES FOR DIFFUSION IMAGE GENERATORS:\n"
            "1. Put the MAIN PHYSICAL SUBJECT or ICONIC PROP front and center in full view (for example: if the line talks about teeth and dental plaque becoming a time capsule, explicitly describe: 'A giant white molar tooth in the center covered in yellow hardened dental plaque, a dentist tool scraping it on the left, and an hourglass beside it').\n"
            "2. NEVER use confusing visual metaphors like 'resembling a rocky geological cliff' or 'a tapestry of history', because diffusion models draw metaphors literally.\n"
            "3. Include clear character actions and props in the same frame when relevant (e.g., a Neanderthal holding his swollen jaw by a cave fire, or a scientist examining the tooth with a magnifying glass).\n"
            "4. NEVER include written words, text labels, letters, or numbers.\n"
            f"Return ONLY a valid JSON array of {len(batch)} English strings in the exact same order.\n\n"
            f"{numbered}"
        )

        batch_out: Optional[list[str]] = None
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
            }
            try:
                r = requests.post(url, json=payload, timeout=30)
                if r.status_code != 200:
                    continue
                cand_text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                cand_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", cand_text, flags=re.DOTALL).strip()
                parsed = json.loads(cand_text)
                if isinstance(parsed, list) and len(parsed) == len(batch):
                    batch_out = [str(item).strip() for item in parsed]
                    break
            except Exception:
                continue

        if not batch_out:
            return None
        results.extend(batch_out)

    return results


def _sanitize_text_triggers(english_text: str) -> str:
    """Reemplaza expresiones que incitan al generador de imágenes a escribir letras/palabras en pantalla
    por equivalentes puramente visuales (iconos, símbolos luminosos, pantallas gráficas)."""
    s = english_text
    s = re.sub(
        r"\ba word lit up([^.]*?):\s*[\w\-]+",
        r"a glowing red warning alert symbol and rocket icon flashing\1",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\b(word|words|text|message|sign|letters|caption)\s+(lit up|appeared|flashed|saying|reading|that said|on the screen)[^.,;]*",
        "a glowing red warning symbol and graphical alert icon flashing on the monitor screen",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r":\s*(launch|attack|missile|warning|danger)\b", " showing a flashing red rocket alert icon", s, flags=re.IGNORECASE)
    return s


def _extract_visual_setting_anchor(translations_en: list[str]) -> str:
    """Extrae una descripción breve del escenario/tema físico general a partir de las primeras escenas del guion
    para que ninguna escena posterior pierda el contexto de dónde ocurre la historia."""
    joined = " ".join(translations_en[:4]).strip()
    if not joined:
        return ""
    joined = re.sub(r"[\"«»¡!¿?]", "", joined)
    # Tomar la primera oración informativa como ancla de escenario
    first_sent = re.split(r"(?<=[.!?])\s+", joined)[0].strip().rstrip(".")
    if len(first_sent) > 130:
        first_sent = first_sent[:130].rsplit(" ", 1)[0]
    return first_sent


def _concretize_visual_action(
    english_action: str,
    prev_en: Optional[str] = None,
    next_en: Optional[str] = None,
    global_anchor: Optional[str] = None,
) -> tuple[str, str]:
    """Convierte cualquier frase hablada (incluso abstracta o reflexiva) en una instrucción
    visual concreta con objetos físicos, acción del personaje y continuidad con las escenas vecinas."""
    clean_en = _sanitize_text_triggers(english_action)
    visual_additions: list[str] = []

    for pattern, visual_cue in _VISUAL_EXPANSION_RULES:
        if re.search(pattern, clean_en, flags=re.IGNORECASE):
            visual_additions.append(visual_cue)
            if len(visual_additions) >= 2:
                break

    # Si la frase es corta o muy abstracta (sin pista visual detectada), apoyarse en la escena vecina y el ancla global
    neighbor_context = ""
    if not visual_additions:
        for nb in (prev_en, next_en):
            if nb:
                for pattern, visual_cue in _VISUAL_EXPANSION_RULES:
                    if re.search(pattern, nb, flags=re.IGNORECASE):
                        visual_additions.append(visual_cue)
                        break
            if visual_additions:
                break
        if prev_en:
            neighbor_context = _sanitize_text_triggers(prev_en)

    concrete_cues = "; ".join(visual_additions)
    if concrete_cues:
        scene_visual = f"{clean_en} (Visual elements to draw in the scene: {concrete_cues})"
    elif neighbor_context:
        scene_visual = f"{clean_en} (Continuing in the same scene as: {neighbor_context})"
    else:
        scene_visual = clean_en

    context_line = global_anchor or ""
    return scene_visual, context_line


def _extract_compact_style_header(style_block: str) -> str:
    """Extrae un encabezado compacto de estilo (~18 palabras) para que incluso los modelos gratuitos con ventana
    CLIP de 77 tokens (~55 palabras) lean SIEMPRE tanto el estilo visual (ej: stick-figures en fondo blanco)
    como el objeto central de la escena dentro de las primeras 50 palabras."""
    low = style_block.lower()
    if "stick figure" in low or ("sketch" in low and "white background" in low):
        return (
            "2D hand-drawn black ink sketch on pure white paper background, vibrant flat color fills, "
            "simple stick-figure characters with round white heads, dot eyes and messy spiky hair"
        )
    words = style_block.split()
    if len(words) <= 22:
        return style_block.rstrip(".")
    return " ".join(words[:22]).rstrip(".,;:")


def build_scene_prompt(
    scene_text: str,
    style_key: str = "cinematic",
    custom_style_prompt: Optional[str] = None,
    ref_style_descriptor: Optional[str] = None,
    translated_en: Optional[str] = None,
    global_context_en: Optional[str] = None,
    timestamp_label: Optional[str] = None,
    prev_translated_en: Optional[str] = None,
    next_translated_en: Optional[str] = None,
) -> str:
    """Construye un prompt de Storyboard optimizado para modelos de difusión (ventana CLIP de 77 tokens) y modelos LLM:
    1. Primeras 28 palabras: Objeto físico central y acción exacta de la escena (diseñada por Gemini 3.1 Flash).
    2. Siguientes 22 palabras: Resumen compacto del estilo (stick-figures / tinta negra / fondo blanco puro) dentro del límite de 55 palabras.
    3. Resto: Reglas completas de estilo para motores T5/LLM."""
    english_action = (translated_en or scene_text).strip()
    english_action = re.sub(r"[\"«»¡!¿?]", "", english_action).strip()
    clean_action = _sanitize_text_triggers(english_action)

    master = (custom_style_prompt or "").strip()
    if master:
        style_block = master
    else:
        style_block = STYLE_PRESETS.get(style_key, "")
        if ref_style_descriptor and ref_style_descriptor.strip():
            style_block = f"{style_block}, {ref_style_descriptor.strip()}".strip(", ")

    parts: list[str] = [f"SCENE TO DRAW: {clean_action}"]
    if style_block:
        compact_header = _extract_compact_style_header(style_block)
        parts.append(f"STYLE: {compact_header}")
        if len(style_block.split()) > 22:
            parts.append(style_block)
    parts.append("No text, no letters, no written words, no numbers, no watermark")

    return ". ".join(p.strip().rstrip(".") for p in parts if p.strip()) + "."


def populate_timestamp_visual_prompts(
    scenes_meta: list[dict[str, Any]],
    style_key: str = "cinematic",
    custom_style_prompt: Optional[str] = None,
    ref_style_descriptor: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Una vez calculados los timestamps exactos de la narración:
    1. Si hay clave gratuita de Google AI Studio, usa Gemini 3.1 Flash como Director de Storyboard para convertir
       cada frase del guion en una escena física concreta y fiel a la época/tema del guion.
    2. Si no hay clave Gemini, traduce en paralelo y aplica expansión visual determinista."""
    texts_es = [sc["text"] for sc in scenes_meta]
    gemini_scenes_en = _generate_storyboard_descriptions_with_gemini_llm(texts_es)
    if gemini_scenes_en and len(gemini_scenes_en) == len(texts_es):
        translations_en = gemini_scenes_en
    else:
        with ThreadPoolExecutor(max_workers=6) as executor:
            translations_en = list(executor.map(translate_es_to_en, texts_es))

    global_context_en = _extract_visual_setting_anchor(translations_en)

    total = len(scenes_meta)
    for i, (sc, tr_en) in enumerate(zip(scenes_meta, translations_en)):
        prev_en = translations_en[i - 1] if i > 0 else None
        next_en = translations_en[i + 1] if i + 1 < total else None
        sc["translated_en"] = tr_en
        sc["image_prompt"] = build_scene_prompt(
            scene_text=sc["text"],
            style_key=style_key,
            custom_style_prompt=custom_style_prompt,
            ref_style_descriptor=ref_style_descriptor,
            translated_en=tr_en,
            global_context_en=global_context_en,
            timestamp_label=sc.get("timestamp_label"),
            prev_translated_en=prev_en,
            next_translated_en=next_en,
        )
    return scenes_meta


def generate_srt_content(scenes: list[dict[str, Any]]) -> str:
    blocks = []
    for idx, sc in enumerate(scenes, start=1):
        start_str = format_srt_time(sc["start_sec"])
        end_str = format_srt_time(sc["end_sec"])
        blocks.append(f"{idx}\n{start_str} --> {end_str}\n{sc['text']}\n")
    return "\n".join(blocks)


def _crop_and_resize_to_target(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Ajusta una imagen al tamaño objetivo (ej. 1920x1080) mediante recorte centrado proporcional
    si la relación de aspecto difiere, evitando deformar o estirar a los personajes."""
    src_w, src_h = img.size
    if (src_w, src_h) == (target_w, target_h):
        return img

    src_ratio = src_w / max(1.0, float(src_h))
    tgt_ratio = target_w / max(1.0, float(target_h))

    if abs(src_ratio - tgt_ratio) > 0.06:
        if src_ratio > tgt_ratio:
            new_w = int(round(src_h * tgt_ratio))
            left = max(0, (src_w - new_w) // 2)
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(round(src_w / tgt_ratio))
            top = max(0, (src_h - new_h) // 2)
            img = img.crop((0, top, src_w, top + new_h))

    resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return resized.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=2))


_GEMINI_FREE_TIER_NO_IMAGE_KEY: str = ""


def _generate_with_gemini(
    prompt: str,
    width: int,
    height: int,
    seed: int,
    reference_image_path: Optional[Path] = None,
) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes usando Google AI Studio (Gemini 2.5/3.1 Flash Image).
    Si la clave está en Free Tier sin facturación para imagen (limit: 0), cede inmediatamente el paso
    a FLUX.1-dev (28 pasos) mientras sigue usando Gemini 3.1 Flash gratis como Director de Storyboard."""
    global _LAST_GEMINI_CALL_TS, _GEMINI_FREE_TIER_NO_IMAGE_KEY
    api_key = (IMAGE_SETTINGS.get("gemini_api_key") or "").strip()
    if not api_key:
        return None, "Falta tu API Key gratuita de Google AI Studio (aistudio.google.com/apikey)"
    if _GEMINI_FREE_TIER_NO_IMAGE_KEY == api_key:
        return None, "Usando Gemini 3.1 como Director de Prompts + FLUX.1-dev (28 pasos) para dibujo"

    aspect_str = "16:9 widescreen horizontal landscape" if width >= height else "9:16 vertical portrait"
    aspect_code = "16:9" if width >= height else "9:16"

    # Preparar imagen de referencia en base64 si existe en el proyecto
    ref_part = None
    if reference_image_path and reference_image_path.exists():
        try:
            ref_im = Image.open(reference_image_path).convert("RGB")
            ref_im.thumbnail((768, 768), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            ref_im.save(buf, format="PNG")
            ref_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            ref_part = {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": ref_b64,
                }
            }
        except Exception:
            ref_part = None

    if ref_part:
        text_instruction = (
            f"Use the attached reference image STRICTLY as the visual style, line-art technique, shading, color palette, "
            f"and character design reference. Do NOT copy the static pose or background of the reference image. "
            f"Instead, generate a brand-new {aspect_str} storyboard illustration that depicts the exact scene and action below:\n\n"
            f"{prompt}\n\n"
            f"Important: Draw the specific environment, objects, and character action described above in a {aspect_str} frame. No text or letters."
        )
        parts = [ref_part, {"text": text_instruction}]
    else:
        text_instruction = (
            f"Generate a high-quality {aspect_str} storyboard illustration depicting the exact scene and action below:\n\n"
            f"{prompt}\n\n"
            f"Important: Draw the specific physical environment, props, and character action clearly in {aspect_str} composition. No text or letters."
        )
        parts = [{"text": text_instruction}]

    gemini_models = [
        "gemini-2.5-flash-image",
        "gemini-3.1-flash-image",
        "gemini-3.1-flash-lite-image",
        "gemini-3-pro-image",
    ]

    last_err = "Error desconocido en Gemini"
    free_tier_zero_limit = False
    for attempt in range(2):
        if free_tier_zero_limit:
            break
        elapsed = time.time() - _LAST_GEMINI_CALL_TS
        if elapsed < 4.5:
            time.sleep(4.5 - elapsed)

        # 1. Probar primero con el endpoint oficial de Google Imagen 3
        try:
            imagen_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
            imagen_payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": aspect_code}
            }
            resp_img = requests.post(imagen_url, json=imagen_payload, timeout=35)
            if resp_img.status_code == 200:
                img_data = resp_img.json()
                preds = img_data.get("predictions") or []
                if preds and preds[0].get("bytesBase64Encoded"):
                    raw_b = base64.b64decode(preds[0]["bytesBase64Encoded"])
                    return Image.open(io.BytesIO(raw_b)).convert("RGB"), ""
        except Exception:
            pass

        for model_name in gemini_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                },
            }
            try:
                _LAST_GEMINI_CALL_TS = time.time()
                resp = requests.post(url, json=payload, timeout=45)
                if resp.status_code == 429:
                    if "limit: 0" in resp.text:
                        _GEMINI_FREE_TIER_NO_IMAGE_KEY = api_key
                        last_err = "La cuenta gratuita de Google AI Studio permite Gemini Director de Prompts gratis, pero requiere vincular facturación para el endpoint directo de imagen; usando automáticamente FLUX.1-dev (28 pasos)"
                        free_tier_zero_limit = True
                        break
                    last_err = "Límite por minuto de Google AI Studio alcanzado; esperando unos segundos..."
                    time.sleep(8.0 + attempt * 4.0)
                    break
                if resp.status_code == 404:
                    last_err = f"Modelo {model_name} no habilitado en esta cuenta"
                    continue
                if resp.status_code != 200:
                    err_json = resp.json() if resp.text else {}
                    msg = err_json.get("error", {}).get("message", resp.text[:160])
                    last_err = f"Gemini HTTP {resp.status_code}: {msg}"
                    continue

                data = resp.json()
                candidates = data.get("candidates") or []
                for cand in candidates:
                    c_parts = (cand.get("content") or {}).get("parts") or []
                    for p in c_parts:
                        inline = p.get("inlineData") or p.get("inline_data")
                        if inline and inline.get("data"):
                            raw_bytes = base64.b64decode(inline["data"])
                            return Image.open(io.BytesIO(raw_bytes)).convert("RGB"), ""
                last_err = "Gemini respondió sin imagen adjunta"
            except Exception as exc:
                last_err = str(exc)

    return None, last_err


def _generate_with_runware(prompt: str, w: int, h: int, seed: int) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes con Runware.ai (FLUX.1-dev a 28 pasos, ultra bajo costo ~$0.0013/img)."""
    api_key = (IMAGE_SETTINGS.get("runware_api_key") or "").strip()
    if not api_key:
        return None, "Falta tu API Key de Runware.ai"

    rw_w = max(512, min(1344, (w // 64) * 64))
    rw_h = max(512, min(1344, (h // 64) * 64))
    payload = [
        {"taskType": "authentication", "apiKey": api_key},
        {
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "positivePrompt": prompt,
            "width": rw_w,
            "height": rw_h,
            "model": "runware:101@1",  # FLUX.1-dev (alta obediencia al prompt)
            "steps": 28,
            "CFGScale": 3.5,
            "seed": seed,
            "numberResults": 1,
            "outputFormat": "PNG",
        },
    ]
    try:
        r = requests.post("https://api.runware.ai/v1", json=payload, timeout=45)
        if r.status_code != 200:
            return None, f"Runware HTTP {r.status_code}: {r.text[:160]}"
        items = r.json().get("data") or []
        for item in items:
            if item.get("imageURL"):
                img_bytes = requests.get(item["imageURL"], timeout=30).content
                return Image.open(io.BytesIO(img_bytes)).convert("RGB"), ""
        return None, f"Runware sin imagen: {r.text[:160]}"
    except Exception as exc:
        return None, str(exc)


def _generate_with_together(prompt: str, w: int, h: int, seed: int) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes con Together AI usando FLUX.1-dev (28 pasos)."""
    api_key = (IMAGE_SETTINGS.get("together_api_key") or "").strip()
    if not api_key:
        return None, "Falta tu API Key de Together AI"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for model_id, steps in [("black-forest-labs/FLUX.1-dev", 28), ("black-forest-labs/FLUX.1-schnell", 4)]:
        payload = {
            "model": model_id,
            "prompt": prompt,
            "width": w,
            "height": h,
            "steps": steps,
            "n": 1,
            "seed": seed,
            "response_format": "b64_json",
        }
        try:
            r = requests.post("https://api.together.xyz/v1/images/generations", headers=headers, json=payload, timeout=50)
            if r.status_code == 200:
                data = r.json().get("data") or []
                if data and data[0].get("b64_json"):
                    raw = base64.b64decode(data[0]["b64_json"])
                    return Image.open(io.BytesIO(raw)).convert("RGB"), ""
                if data and data[0].get("url"):
                    raw = requests.get(data[0]["url"], timeout=30).content
                    return Image.open(io.BytesIO(raw)).convert("RGB"), ""
        except Exception as exc:
            last_err = str(exc)
            continue
    return None, "Error al generar en Together AI"


def _generate_with_fal(prompt: str, w: int, h: int, seed: int) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes con Fal.ai usando FLUX.1-dev (28 pasos)."""
    api_key = (IMAGE_SETTINGS.get("fal_api_key") or "").strip()
    if not api_key:
        return None, "Falta tu API Key de Fal.ai"

    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
    img_size = "landscape_16_9" if w >= h else "portrait_16_9"
    payload = {
        "prompt": prompt,
        "image_size": img_size,
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "seed": seed,
        "num_images": 1,
    }
    try:
        r = requests.post("https://fal.run/fal-ai/flux/dev", headers=headers, json=payload, timeout=55)
        if r.status_code != 200:
            return None, f"Fal.ai HTTP {r.status_code}: {r.text[:160]}"
        images = r.json().get("images") or []
        if images and images[0].get("url"):
            raw = requests.get(images[0]["url"], timeout=30).content
            return Image.open(io.BytesIO(raw)).convert("RGB"), ""
        return None, "Fal.ai no devolvió imagen"
    except Exception as exc:
        return None, str(exc)


def _generate_with_pollinations(prompt: str, w: int, h: int, seed: int) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes 100% gratis y sin cuenta con Pollinations AI."""
    last_err = "Pollinations ocupado"
    clean_p = quote(prompt[:750])
    urls = [
        f"https://image.pollinations.ai/prompt/{clean_p}?width={w}&height={h}&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{clean_p}?nologo=true",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=35, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                return Image.open(io.BytesIO(r.content)).convert("RGB"), ""
            if r.status_code == 402:
                last_err = "Pollinations cuota temporal de 45s por IP"
            else:
                last_err = f"Pollinations HTTP {r.status_code}"
        except Exception as exc:
            last_err = str(exc)
        time.sleep(1.2)
    return None, last_err


def _generate_with_subnp_magic(prompt: str) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes 100% gratis, sin cuenta, sin API Key y sin límite de 15 imágenes (MagicStudio vía SubNP).
    Ideal para continuar videos largos cuando se agota la cuota diaria de Hugging Face ZeroGPU."""
    last_err = "Servidor MagicStudio ocupado"
    for attempt in range(2):
        try:
            r = requests.post(
                "https://subnp.com/api/free/generate",
                json={"prompt": prompt[:950], "model": "magic"},
                timeout=35,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                img_url = None
                for line in r.text.splitlines():
                    if line.startswith("data:"):
                        raw = line[len("data:") :].strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                            if obj.get("imageUrl"):
                                img_url = obj["imageUrl"]
                                break
                            if obj.get("error"):
                                last_err = str(obj["error"])
                        except Exception:
                            pass
                if img_url:
                    img_resp = requests.get(img_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
                    if img_resp.status_code == 200:
                        return Image.open(io.BytesIO(img_resp.content)).convert("RGB"), ""
            else:
                last_err = f"MagicStudio HTTP {r.status_code}"
        except Exception as exc:
            last_err = str(exc)
        time.sleep(1.5)
    return None, last_err


def _get_hf_token_candidates() -> list[str]:
    """Permite pegar 1 o varios tokens gratuitos de Hugging Face separados por coma (ej: hf_uno, hf_dos)
    más un intento sin token para multiplicar la cuota diaria gratuita."""
    raw = (IMAGE_SETTINGS.get("hf_token") or "").strip()
    tokens = [t.strip() for t in re.split(r"[,;\s]+", raw) if t.strip().startswith("hf_")]
    tokens.append("")  # Intento anónimo por IP
    return tokens


_EXHAUSTED_HF_TOKENS: set[str] = set()


def _generate_with_hf_spaces(
    prompt: str,
    w: int,
    h: int,
    seed: int,
    prefer_dev_28: bool = True,
) -> tuple[Optional[Image.Image], str]:
    """Genera imágenes usando Spaces de Hugging Face rotando entre todos los tokens configurados."""
    dev_spaces = [
        ("https://multimodalart-flux-1-merged.hf.space", "/gradio_api/call/infer", [prompt, seed, False, w, h, 3.5, 8]),
        ("https://black-forest-labs-flux-1-schnell.hf.space", "/gradio_api/call/infer", [prompt, seed, False, w, h, 4]),
        ("https://black-forest-labs-flux-1-dev.hf.space", "/gradio_api/call/infer", [prompt, seed, False, w, h, 3.5, 28]),
        ("https://stabilityai-stable-diffusion-3-5-large-turbo.hf.space", "/gradio_api/call/infer", [prompt, "text, watermark, blurry, deformed, letters", seed, False, w, h, 0.0, 4]),
    ]
    fast_spaces = [
        ("https://black-forest-labs-flux-1-schnell.hf.space", "/gradio_api/call/infer", [prompt, seed, False, w, h, 4]),
        ("https://multimodalart-flux-1-merged.hf.space", "/gradio_api/call/infer", [prompt, seed, False, w, h, 3.5, 8]),
        ("https://stabilityai-stable-diffusion-3-5-large-turbo.hf.space", "/gradio_api/call/infer", [prompt, "text, watermark, blurry, deformed, letters", seed, False, w, h, 0.0, 4]),
    ]
    spaces = dev_spaces if prefer_dev_28 else fast_spaces
    last_error = "Cuota de Hugging Face ZeroGPU agotada"

    candidates = [t for t in _get_hf_token_candidates() if t not in _EXHAUSTED_HF_TOKENS]
    if not candidates:
        return None, last_error

    for tok in candidates:
        req_headers = {"User-Agent": "Mozilla/5.0"}
        if tok:
            req_headers["Authorization"] = f"Bearer {tok}"
            # Intentar primero el Router Oficial Serverless de Hugging Face (no consume ZeroGPU por IP si el token tiene permiso Inference Providers)
            for router_model in ("black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"):
                try:
                    r_inf = requests.post(
                        f"https://router.huggingface.co/hf-inference/models/{router_model}",
                        headers=req_headers,
                        json={"inputs": prompt, "parameters": {"width": w, "height": h, "seed": seed}},
                        timeout=32,
                    )
                    if r_inf.status_code == 200 and "image" in (r_inf.headers.get("content-type") or ""):
                        return Image.open(io.BytesIO(r_inf.content)).convert("RGB"), ""
                    if r_inf.status_code == 403 and "sufficient permissions to call inference providers" in r_inf.text.lower():
                        last_error = (
                            "Tu Token de Hugging Face es de solo lectura ('Read') y ya agotó la cuota ZeroGPU de hoy. "
                            "Crea un token con el permiso 'Make calls to Inference Providers' en huggingface.co/settings/tokens"
                        )
                        break
                except Exception:
                    pass

        zero_left_count = 0
        for base_url, endpoint, data_args in spaces:
            try:
                call_resp = requests.post(
                    f"{base_url}{endpoint}",
                    json={"data": data_args},
                    timeout=18,
                    headers=req_headers,
                )
                if call_resp.status_code != 200:
                    last_error = f"HTTP {call_resp.status_code} en {base_url.split('//')[1][:25]}"
                    continue

                event_id = call_resp.json().get("event_id")
                if not event_id:
                    continue

                sse_resp = requests.get(
                    f"{base_url}{endpoint}/{event_id}",
                    timeout=55,
                    headers=req_headers,
                )
                img_url = None
                is_err = False
                cur_event = ""
                for line in sse_resp.text.splitlines():
                    if line.startswith("event:"):
                        cur_event = line.split(":", 1)[1].strip().lower()
                        if "error" in cur_event:
                            is_err = True
                    elif line.startswith("data:"):
                        raw_json = line[len("data:") :].strip()
                        if not raw_json or raw_json == "null":
                            continue
                        try:
                            payload = json.loads(raw_json)
                            if isinstance(payload, dict) and payload.get("error"):
                                err_str = str(payload["error"])
                                last_error = err_str[:140]
                                if "0s left" in err_str.lower():
                                    zero_left_count += 1
                            elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
                                # Ignorar frames intermedios de 'generating' (ruido latente del paso 1); tomar solo 'complete'
                                if cur_event in ("complete", ""):
                                    cand_url = payload[0].get("url")
                                    if not cand_url and payload[0].get("path"):
                                        cand_url = f"{base_url}/gradio_api/file={payload[0]['path']}"
                                    if cand_url:
                                        img_url = cand_url
                        except Exception:
                            pass

                if img_url and not is_err:
                    img_bytes = requests.get(img_url, timeout=30, headers=req_headers).content
                    return Image.open(io.BytesIO(img_bytes)).convert("RGB"), ""
                if zero_left_count >= 2:
                    _EXHAUSTED_HF_TOKENS.add(tok)
                    break
            except Exception as exc:
                last_error = str(exc)

    return None, last_error


import threading as _threading
_GEMINI_PRO_LOCK = _threading.Lock()


def _generate_with_gemini_pro_web(
    prompt: str,
    width: int,
    height: int,
    reference_image_path: Optional[Path] = None,
) -> tuple[Optional[Image.Image], str]:
    """Usa directamente la suscripción de Gemini Pro (gemini.google.com) del usuario mediante gemini-webapi
    para generar ilustraciones con Nano Banana / Imagen 3 sin pagar API adicional."""
    psid = (IMAGE_SETTINGS.get("gemini_1psid") or "").strip()
    psidts = (IMAGE_SETTINGS.get("gemini_1psidts") or "").strip() or None
    extra_cookies: list[dict[str, Any]] = IMAGE_SETTINGS.get("gemini_cookies_list") or []
    if not psid and not extra_cookies:
        return (
            None,
            "Falta conectar tu sesión de Gemini Pro. Haz clic en '🌐 Conectar Gemini Pro en 1 Clic (Captura Automática)' en '🔑 Configurar Motor de Imágenes'.",
        )

    import asyncio
    import sys
    from gemini_webapi import GeminiClient
    import gemini_webapi.utils as _gutils

    try:
        import gemini_webapi.utils.load_browser_cookies as _lbc
        _lbc.load_browser_cookies = lambda *a, **k: {}
        gat_mod = sys.modules.get("gemini_webapi.utils.get_access_token")
        if gat_mod is not None:
            gat_mod.load_browser_cookies = lambda *a, **k: {}
            if not getattr(gat_mod, "_patched_safe_extract", False):
                _orig_extract = gat_mod._extract_payload

                def _safe_extract_payload(response):
                    url_str = str(getattr(response, "url", "") or "")
                    txt_str = getattr(response, "text", "") or ""
                    if (
                        "accounts.google.com" in url_str
                        or "ServiceLogin" in url_str
                        or "boq_identityfrontend" in txt_str
                    ):
                        return None
                    return _orig_extract(response)

                gat_mod._extract_payload = _safe_extract_payload
                gat_mod._patched_safe_extract = True
    except Exception:
        pass

    aspect_str = "16:9 widescreen horizontal landscape" if width >= height else "9:16 vertical portrait"
    files = [str(reference_image_path)] if (reference_image_path and reference_image_path.exists()) else None

    full_prompt = (
        f"Generate a high-quality image ({aspect_str}) using your image generation tool. "
        f"Depict the following scene with rich details, no text, no letters, no watermark:\n\n"
        f"{prompt}"
    )

    short_scene = prompt.split("STYLE:")[0].replace("SCENE TO DRAW:", "").strip()

    async def _async_gen() -> tuple[Optional[Image.Image], str]:
        from gemini_webapi.utils import rotate_1psidts
        import tempfile

        # Limpiar cualquier caché residual de sesión no autenticada para evitar que opaque las cookies frescas
        for cdir in (Path(tempfile.gettempdir()) / "gemini_webapi", Path(os.path.expandvars(r"%TEMP%\gemini_webapi"))):
            try:
                if cdir.exists():
                    for f in cdir.glob(".cached_cookies_*.json"):
                        f.unlink(missing_ok=True)
            except Exception:
                pass

        client = GeminiClient(psid or None, psidts)
        osid_val = (IMAGE_SETTINGS.get("gemini_osid") or "").strip()

        # Configurar cookies adicionales sin que cookies viejas sobreescriban las principales
        for c in extra_cookies:
            c_name = (c.get("name") or "").strip()
            c_val = (c.get("value") or "").strip()
            c_dom = (c.get("domain") or ".google.com").strip()
            if c_name in ("OSID", "__Secure-OSID", "__Secure-1PSID", "__Secure-1PSIDTS", "__Secure-3PSID", "__Secure-3PSIDTS"):
                continue
            if c_name and c_val:
                client._cookies.set(c_name, c_val, domain=c_dom, secure=True)

        if osid_val:
            client._cookies.set("__Secure-OSID", osid_val, domain="gemini.google.com", secure=True)
            client._cookies.set("OSID", osid_val, domain="gemini.google.com", secure=True)
        if psid:
            client._cookies.set("__Secure-1PSID", psid, domain=".google.com", secure=True)
            client._cookies.set("__Secure-3PSID", psid, domain=".google.com", secure=True)
        if psidts:
            client._cookies.set("__Secure-1PSIDTS", psidts, domain=".google.com", secure=True)
            client._cookies.set("__Secure-3PSIDTS", psidts, domain=".google.com", secure=True)

        try:
            await client.init(timeout=30, auto_close=False, auto_refresh=False)

            acc_status = getattr(client, "account_status", None)
            if acc_status == 1016 or str(acc_status).endswith("UNAUTHENTICATED"):
                return (
                    None,
                    "Google indica que las cookies expiraron o fueron rotadas. Para renovar todas las cookies sincronizadas en 1 clic: en gemini.google.com abre F12 → pestaña Network (Red), presiona F5, clic derecho en la primera fila ('app') → Copy → Copy as cURL (cmd), pégalo en el cuadro 'Opción 1: Pegar cURL' y pulsa Sincronizar Sesión.",
                )

            try:
                if client.client is not None:
                    rotated_ts = await rotate_1psidts(client.client)
                    if rotated_ts and rotated_ts != psidts:
                        IMAGE_SETTINGS["gemini_1psidts"] = rotated_ts
                        for c in (IMAGE_SETTINGS.get("gemini_cookies_list") or []):
                            if c.get("name") in ("__Secure-1PSIDTS", "__Secure-3PSIDTS"):
                                c["value"] = rotated_ts
                        sf = Path(__file__).parent / "settings.json"
                        sf.write_text(json.dumps(IMAGE_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

            response = await client.generate_content(full_prompt, files=files, temporary=True)

            # Sincronizar cookie de timestamp si Google la rotó en esta llamada
            try:
                live_ts = client.cookies.get("__Secure-1PSIDTS")
                if live_ts and live_ts != IMAGE_SETTINGS.get("gemini_1psidts"):
                    IMAGE_SETTINGS["gemini_1psidts"] = live_ts
                    for c in (IMAGE_SETTINGS.get("gemini_cookies_list") or []):
                        if c.get("name") in ("__Secure-1PSIDTS", "__Secure-3PSIDTS"):
                            c["value"] = live_ts
                    sf = Path(__file__).parent / "settings.json"
                    sf.write_text(json.dumps(IMAGE_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
            txt_first = (response.text or "").strip()
            if not response.images and (
                "Solo soy una IA que trabaja con textos" in txt_first
                or "text-based AI" in txt_first
                or "can't create it" in txt_first
                or "I can try to find an image" in txt_first
            ):
                return (
                    None,
                    "Tu sesión de Gemini Pro bajó a modo invitado sin generador de imágenes. Haz clic en '🌐 Conectar Gemini Pro en 1 Clic (Captura Automática)' en '🔑 Configurar Motor de Imágenes' para sincronizar todas las cookies de sesión.",
                )

            if not response.images:
                await asyncio.sleep(1.5)
                response = await client.generate_content(
                    f"Generate an image using your image generation tool ({aspect_str}): {short_scene}. No text, no watermark.",
                    temporary=True,
                )
            if not response.images:
                txt_preview = (response.text or "").strip()[:140]
                return None, f"Gemini Pro respondió con texto sin imagen ({txt_preview})"

            tmp_dir = Path(__file__).parent / "outputs" / "gemini_web_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            fname = f"gweb_{int(time.time() * 1000)}_{random.randint(100, 999)}.png"
            saved_file = await response.images[0].save(path=str(tmp_dir), filename=fname, full_size=True)

            if saved_file and Path(saved_file).exists():
                im = Image.open(saved_file).convert("RGB")
                try:
                    Path(saved_file).unlink(missing_ok=True)
                except Exception:
                    pass
                return im, ""
            return None, "No se pudo descargar la imagen generada desde Gemini Pro"
        except Exception as exc:
            return None, f"Sesión de Gemini Pro: {exc}"
        finally:
            try:
                await client.close()
            except Exception:
                pass

    with _GEMINI_PRO_LOCK:
        res_box: list[tuple[Optional[Image.Image], str]] = [(None, "Tiempo de espera agotado en Gemini Pro")]

        def _runner():
            try:
                res_box[0] = asyncio.run(_async_gen())
            except Exception as exc:
                res_box[0] = (None, f"Gemini Pro: {exc}")

        t = _threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join(timeout=75)
        return res_box[0]


def generate_image_for_scene(
    prompt: str,
    width: int,
    height: int,
    dest_path: Path,
    seed: Optional[int] = None,
    reference_image_path: Optional[Path] = None,
    color_match_strength: float = 0.45,
) -> Path:
    """Genera la imagen de una escena combinando:
    1. Suscripción de Gemini Pro (gemini.google.com) / Google AI Studio / Hugging Face Multi-Token / Runware / MagicStudio."""
    if seed is None:
        seed = random.randint(1000, 9999999)

    w = max(512, min(1024, (width // 32) * 32))
    h = max(512, min(1024, (height // 32) * 32))
    if width > height:
        w, h = 1024, 576
    elif height > width:
        w, h = 576, 1024

    provider = (IMAGE_SETTINGS.get("provider") or "auto").strip().lower()
    allow_fallback = bool(IMAGE_SETTINGS.get("allow_fallback"))
    generated_img: Optional[Image.Image] = None
    used_provider = ""
    last_error = "No se pudo generar la imagen"
    provider_errors: list[str] = []

    if provider == "gemini_pro":
        chain = ["gemini_pro"]
        if allow_fallback:
            chain.extend(["hf_dev", "pollinations", "magic"])
    elif provider == "magic":
        chain = ["magic", "hf_dev"]
    elif provider == "gemini":
        chain = []
        if (IMAGE_SETTINGS.get("gemini_1psid") or "").strip():
            chain.append("gemini_pro")
        chain.append("gemini")
        if allow_fallback:
            chain.extend(["hf_dev", "magic", "pollinations"])
    elif provider == "runware":
        chain = ["runware", "hf_dev", "magic", "pollinations"]
    elif provider == "together":
        chain = ["together", "hf_dev", "magic", "pollinations"]
    elif provider == "fal":
        chain = ["fal", "hf_dev", "magic", "pollinations"]
    elif provider == "pollinations":
        chain = ["pollinations", "magic", "hf_dev"]
    elif provider == "hf_dev":
        chain = ["hf_dev", "magic", "pollinations"]
    elif provider == "hf_fast":
        chain = ["hf_fast", "magic", "pollinations"]
    else:
        chain = []
        if (IMAGE_SETTINGS.get("gemini_1psid") or "").strip():
            chain.append("gemini_pro")
        if (IMAGE_SETTINGS.get("runware_api_key") or "").strip():
            chain.append("runware")
        if (IMAGE_SETTINGS.get("fal_api_key") or "").strip():
            chain.append("fal")
        if (IMAGE_SETTINGS.get("together_api_key") or "").strip():
            chain.append("together")
        chain.extend(["hf_dev", "magic", "pollinations"])

    for eng in chain:
        if eng == "gemini_pro":
            generated_img, last_error = _generate_with_gemini_pro_web(prompt, width, height, reference_image_path)
        elif eng == "gemini":
            generated_img, last_error = _generate_with_gemini(prompt, width, height, seed, reference_image_path)
        elif eng == "magic":
            generated_img, last_error = _generate_with_subnp_magic(prompt)
        elif eng == "runware":
            generated_img, last_error = _generate_with_runware(prompt, w, h, seed)
        elif eng == "together":
            generated_img, last_error = _generate_with_together(prompt, w, h, seed)
        elif eng == "fal":
            generated_img, last_error = _generate_with_fal(prompt, w, h, seed)
        elif eng == "pollinations":
            generated_img, last_error = _generate_with_pollinations(prompt, w, h, seed)
        elif eng == "hf_dev":
            generated_img, last_error = _generate_with_hf_spaces(prompt, w, h, seed, prefer_dev_28=True)
        elif eng == "hf_fast":
            generated_img, last_error = _generate_with_hf_spaces(prompt, w, h, seed, prefer_dev_28=False)

        if generated_img is not None:
            used_provider = eng
            break
        provider_errors.append(f"{eng}: {str(last_error)[:220]}")
        if eng == "gemini_pro":
            logger.warning(f"[GEMINI_PRO] Falló generación con Gemini Pro: {last_error}")
            if allow_fallback:
                logger.info("[GEMINI_PRO] Activando motor de respaldo automático (Pollinations / HF)...")

    # Respaldo opcional si el usuario activó allow_fallback
    if generated_img is None and allow_fallback and "pollinations" not in chain:
        generated_img, last_error = _generate_with_pollinations(prompt, w, h, seed)
        if generated_img is not None:
            used_provider = "pollinations"

    if generated_img is None:
        raise RuntimeError(str(last_error) if provider == "gemini_pro" and not allow_fallback else (" | ".join(provider_errors) or str(last_error)))

    generated_img = _crop_and_resize_to_target(generated_img, width, height)

    # Si el estilo pide fondo blanco puro (ej: boceto en papel blanco / stick figures), no teñir el blanco con color_match
    prompt_low = prompt.lower()
    is_white_bg_sketch = "white background" in prompt_low or "white paper" in prompt_low
    effective_strength = 0.0 if is_white_bg_sketch else (color_match_strength * 0.45 if used_provider == "gemini" else color_match_strength)
    if reference_image_path and reference_image_path.exists() and effective_strength > 0:
        try:
            ref_img = Image.open(reference_image_path).convert("RGB")
            generated_img = apply_reference_color_match(generated_img, ref_img, strength=effective_strength)
        except Exception:
            pass

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    generated_img.save(dest_path, format="PNG")
    return dest_path


def _load_ui_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Carga una fuente TrueType compatible con Windows (Arial/Segoe) y Linux/Docker (DejaVu)."""
    names = (
        ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_subtitle_on_image(img: Image.Image, text: str) -> Image.Image:
    out = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = out.size
    font_size = max(22, int(h * 0.036))
    font = _load_ui_font(font_size, bold=True)

    max_chars_per_line = max(28, int(w / (font_size * 0.58)))
    lines = textwrap.wrap(text, width=max_chars_per_line)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] += "..."

    line_height = int(font_size * 1.32)
    total_h = len(lines) * line_height + 24
    box_w = int(w * 0.88)
    box_x = (w - box_w) // 2
    box_y = h - total_h - int(h * 0.06)

    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + total_h],
        radius=16,
        fill=(10, 14, 26, 205),
    )

    curr_y = box_y + 12
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        draw.text((tx, curr_y), line, font=font, fill=(255, 255, 255, 255))
        curr_y += line_height

    return Image.alpha_composite(out, overlay).convert("RGB")


def _create_placeholder_image(
    width: int,
    height: int,
    scene_idx: int,
    text: str,
    ts_label: str,
    draw_sub: bool = True,
) -> Image.Image:
    img = Image.new("RGB", (width, height), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, width - 40, height - 40], outline=(99, 102, 241), width=3)
    font_title = _load_ui_font(34, bold=False)
    draw.text((80, 80), f"Escena #{scene_idx}  [{ts_label}]", fill=(165, 180, 252), font=font_title)
    return _draw_subtitle_on_image(img, text) if draw_sub else img


# ==============================================================================
# 1. GENERADOR DE SUBTÍTULOS DINÁMICOS (.ASS) ESTILO VIRAL / HORMOZI / DOCUMENTAL
# ==============================================================================

def _format_ass_time(seconds: float) -> str:
    """Convierte segundos a formato ASS H:MM:SS.cc (centésimas)."""
    seconds = max(0.0, float(seconds))
    total_cs = int(round(seconds * 100))
    hrs = total_cs // 360000
    rem = total_cs % 360000
    mins = rem // 6000
    rem = rem % 6000
    secs = rem // 100
    cs = rem % 100
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def _escape_ass_text(text: str) -> str:
    return (
        text.replace("\\", "")
        .replace("{", "(")
        .replace("}", ")")
        .replace("\n", " ")
        .strip()
    )


def _group_words_for_dynamic_subs(words: list[str], max_words: int = 5, max_chars: int = 32) -> list[list[str]]:
    """Agrupa las palabras de una escena en cláusulas sintácticas completas (4 a 6 palabras)
    con sentido gramatical natural para lectura cómoda en pantalla sin cortes bruscos."""
    if not words:
        return []
    groups: list[list[str]] = []
    current: list[str] = []
    curr_len = 0

    BREAK_AFTER_PUNCT = (",", ";", ":", ".", "!", "?", "…")
    INSEPARABLE_PREPOSITIONS = {"de", "del", "en", "con", "por", "a", "al", "sin", "sobre", "tras", "hacia", "desde", "un", "una", "unos", "unas", "el", "la", "los", "las", "su", "sus", "mi", "mis", "tu", "tus"}

    for idx, item in enumerate(words):
        w = item if isinstance(item, str) else (item.get("word") or "")
        w_len = len(w)
        low_w = w.lower().strip(".,;:!?()\"'")
        is_punct = any(w.endswith(p) for p in BREAK_AFTER_PUNCT)

        current.append(w)
        curr_len += (1 + w_len) if curr_len > 0 else w_len

        should_split = False
        if is_punct and len(current) >= 2:
            should_split = True
        elif len(current) >= max_words:
            if low_w not in INSEPARABLE_PREPOSITIONS or len(current) >= max_words + 2:
                should_split = True
        elif curr_len >= max_chars and len(current) >= 3:
            if low_w not in INSEPARABLE_PREPOSITIONS:
                should_split = True

        if should_split and idx < len(words) - 1:
            groups.append(current)
            current = []
            curr_len = 0

    if current:
        if len(current) == 1 and groups and len(groups[-1]) <= max_words:
            groups[-1].extend(current)
        else:
            groups.append(current)

    return groups


def generate_ass_subtitles(
    scenes: list[dict[str, Any]],
    width: int = 1920,
    height: int = 1080,
    subtitle_style: str = "hormozi_yellow",
) -> str:
    """Genera un archivo de subtítulos Advanced SubStation Alpha (.ASS) con resaltado palabra por palabra,
    animación Pop suave y bordes gruesos de alto contraste para atrapar la atención del espectador."""
    is_vertical = height > width
    font_size = int(height * 0.052) if not is_vertical else int(width * 0.068)
    margin_v = int(height * 0.095) if not is_vertical else int(height * 0.16)
    margin_h = int(width * 0.08)

    # Colores en formato ASS (&HAABBGGRR)
    # Blanco puro: &H00FFFFFF
    # Amarillo vibrante (#FACC15 -> R=FA, G=CC, B=15): &H0015CCFA
    # Cyan neón (#38BDF8 -> R=38, G=BD, B=F8): &H00F8BD38
    # Verde esmeralda (#4ADE80 -> R=4A, G=DE, B=80): &H0080DE4A
    highlight_map = {
        "hormozi_yellow": "&H0015CCFA&",
        "hormozi_cyan": "&H00F8BD38&",
        "hormozi_green": "&H0080DE4A&",
    }
    active_color = highlight_map.get(subtitle_style, "&H0015CCFA&")
    base_white = "&H00FFFFFF&"

    header = f"""[Script Info]
Title: Dynamic YouTube Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralSub,Arial,{font_size},&H00FFFFFF,&H0015CCFA,&H00080808,&H88000000,-1,0,0,0,100,100,1.2,0,1,5.0,2.8,2,{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []

    max_words_per_chunk = 5 if is_vertical else 6
    max_chars_per_chunk = 30 if is_vertical else 38

    for sc in scenes:
        raw_text = _escape_ass_text(sc.get("text", ""))
        if not raw_text:
            continue
        words = [w for w in raw_text.split() if w]
        if not words:
            continue

        start_sec = float(sc.get("start_sec", 0.0))
        end_sec = float(sc.get("end_sec", start_sec + 2.0))
        scene_dur = max(0.3, end_sec - start_sec)
        # Descontar la pequeña pausa de silencio al final de cada escena para que las palabras sincronicen con la voz
        speak_dur = max(0.25, scene_dur - min(0.22, scene_dur * 0.12))

        # Peso temporal proporcional a la longitud de cada palabra (+ pequeña pausa tras comas/puntos)
        weights: list[float] = []
        for w in words:
            base_w = max(2.2, float(len(w)))
            if w.endswith((",", ";", ":")):
                base_w += 2.2
            elif w.endswith((".", "!", "?", "…")):
                base_w += 3.0
            weights.append(base_w)
        total_weight = sum(weights) or 1.0

        groups = _group_words_for_dynamic_subs(words, max_words=max_words_per_chunk, max_chars=max_chars_per_chunk)

        word_cursor = 0
        curr_t = start_sec

        for grp in groups:
            grp_len = len(grp)
            grp_weights = weights[word_cursor : word_cursor + grp_len]
            grp_dur = speak_dur * (sum(grp_weights) / total_weight)
            grp_start = curr_t
            grp_end = min(end_sec, grp_start + grp_dur)

            if subtitle_style == "cinematic_pop":
                # Frase corta completa con entrada Pop elástica
                phrase_str = " ".join(grp)
                pop_tag = r"{\fscx88\fscy88\t(0,110,\fscx103\fscy103)\t(110,200,\fscx100\fscy100)}"
                events.append(
                    f"Dialogue: 0,{_format_ass_time(grp_start)},{_format_ass_time(grp_end)},ViralSub,,0,0,0,,{pop_tag}{phrase_str}"
                )
            else:
                # Resaltado palabra por palabra estilo Hormozi / Viral con color activo y escala 112%
                w_time = grp_start
                grp_w_sum = sum(grp_weights) or 1.0
                for j, w_active in enumerate(grp):
                    w_dur = grp_dur * (grp_weights[j] / grp_w_sum)
                    w_start = w_time
                    w_end = grp_end if j == grp_len - 1 else min(grp_end, w_start + w_dur)
                    w_time = w_end

                    if w_end - w_start < 0.03:
                        continue

                    rendered_tokens: list[str] = []
                    for k, token in enumerate(grp):
                        if k == j:
                            rendered_tokens.append(
                                f"{{\\c{active_color}\\fscx112\\fscy112}}{token}{{\\c{base_white}\\fscx100\\fscy100}}"
                            )
                        else:
                            rendered_tokens.append(token)

                    line_prefix = r"{\fscx93\fscy93\t(0,85,\fscx100\fscy100)}" if j == 0 else ""
                    line_text = line_prefix + " ".join(rendered_tokens)
                    events.append(
                        f"Dialogue: 0,{_format_ass_time(w_start)},{_format_ass_time(w_end)},ViralSub,,0,0,0,,{line_text}"
                    )

            curr_t = grp_end
            word_cursor += grp_len

    return header + "\n".join(events) + "\n"


# ==============================================================================
# 2. MÚSICA DE FONDO SIN COPYRIGHT (100% LIBRE DE CONTENT ID) + VOICE DUCKING
# ==============================================================================

ROYALTY_FREE_MUSIC_CATALOG: dict[str, dict[str, str]] = {
    "doc_mystery": {
        "id": "doc_mystery",
        "name": "🕵️ Misterio / Investigación Documental (Pad Profundo + Pulso ★)",
        "desc": "Atmósfera envolvente estilo documental de investigación, historia y misterios.",
    },
    "warm_story": {
        "id": "warm_story",
        "name": "🌅 Storytelling Cálido / Reflexivo (Piano Rhodes + Cuerdas ★)",
        "desc": "Acordes cálidos e íntimos ideales para historias humanas, finanzas y análisis.",
    },
    "lofi_chill": {
        "id": "lofi_chill",
        "name": "☕ Lo-Fi Chill / Estudio Suave (Acordes Jazz + Pulso Relajado)",
        "desc": "Fondo moderno y relajado que acompaña la voz sin distraer.",
    },
    "dark_suspense": {
        "id": "dark_suspense",
        "name": "🌑 Suspenso Oscuro / Intriga Cinematográfica",
        "desc": "Tensión cinematográfica profunda para temas de impacto o revelaciones.",
    },
    "inspiring_science": {
        "id": "inspiring_science",
        "name": "🚀 Ciencia, Futuro y Descubrimiento (Ambient Cristalino)",
        "desc": "Arpegios espaciales e inspiradores para tecnología, ciencia y universo.",
    },
    "none": {
        "id": "none",
        "name": "🔇 Sin Música de Fondo (Solo la voz del narrador)",
        "desc": "El video se renderiza únicamente con la voz del locutor.",
    },
}


def generate_royalty_free_music(style: str = "doc_mystery", duration_sec: float = 15.0, sr: int = 24000) -> np.ndarray:
    """Sintetiza música instrumental de fondo 100% libre de derechos de autor y Content ID
    con progresiones armónicas ricas, filtro cálido y reverberación ambiental."""
    dur = max(3.0, min(float(duration_sec), 1800.0))
    n_samples = int(sr * dur)
    if style == "none" or not style:
        return np.zeros(n_samples, dtype=np.float32)

    # Sintetizamos un ciclo musical de 16 segundos (4 acordes de 4 segundos) perfectamente loopable
    loop_sec = 16.0
    loop_n = int(sr * loop_sec)
    t = np.linspace(0.0, loop_sec, loop_n, endpoint=False, dtype=np.float32)

    # Progresiones de acordes en Hz (4 compases de 4.0s cada uno)
    progressions: dict[str, list[list[float]]] = {
        "doc_mystery": [
            # Dm9 -> Bbmaj7 -> Gm9 -> A7sus4
            [73.42, 146.83, 174.61, 220.00, 261.63, 329.63],
            [58.27, 116.54, 174.61, 220.00, 293.66, 349.23],
            [98.00, 146.83, 196.00, 233.08, 293.66, 392.00],
            [55.00, 110.00, 164.81, 196.00, 220.00, 293.66],
        ],
        "warm_story": [
            # Am9 -> Fmaj7 -> Cmaj9 -> G6
            [110.00, 164.81, 220.00, 261.63, 329.63, 493.88],
            [87.31, 174.61, 220.00, 261.63, 329.63, 440.00],
            [65.41, 130.81, 196.00, 246.94, 293.66, 392.00],
            [98.00, 146.83, 196.00, 246.94, 329.63, 392.00],
        ],
        "lofi_chill": [
            # Fmaj9 -> Em7 -> Dm9 -> Cmaj7
            [87.31, 174.61, 220.00, 261.63, 329.63, 392.00],
            [82.41, 164.81, 196.00, 246.94, 293.66, 392.00],
            [73.42, 146.83, 174.61, 220.00, 261.63, 329.63],
            [65.41, 130.81, 164.81, 196.00, 246.94, 329.63],
        ],
        "dark_suspense": [
            # Cm -> Abmaj7 -> Fm7 -> G7b9
            [65.41, 130.81, 155.56, 196.00, 261.63, 311.13],
            [51.91, 103.83, 155.56, 207.65, 246.94, 311.13],
            [43.65, 87.31, 130.81, 174.61, 207.65, 261.63],
            [49.00, 98.00, 146.83, 196.00, 233.08, 293.66],
        ],
        "inspiring_science": [
            # Cmaj9 -> Gadd9 -> Am7 -> Fmaj7#11
            [65.41, 130.81, 196.00, 246.94, 293.66, 392.00],
            [98.00, 146.83, 196.00, 246.94, 293.66, 440.00],
            [110.00, 164.81, 220.00, 261.63, 329.63, 392.00],
            [87.31, 174.61, 220.00, 261.63, 329.63, 369.99],
        ],
    }

    chords = progressions.get(style, progressions["doc_mystery"])
    bar_sec = 4.0
    bar_n = int(sr * bar_sec)
    loop_buf = np.zeros(loop_n, dtype=np.float32)

    for b_idx, notes in enumerate(chords):
        start_i = b_idx * bar_n
        end_i = min(loop_n, start_i + bar_n)
        seg_n = end_i - start_i
        bt = np.linspace(0.0, bar_sec, seg_n, endpoint=False, dtype=np.float32)

        # Envolvente suave de pad con fundido cruzado natural
        env_pad = np.sin(np.pi * (bt / bar_sec)) ** 0.65
        chord_sig = np.zeros(seg_n, dtype=np.float32)

        for n_i, freq in enumerate(notes):
            # Ligero detune analógico (chorus cálido) para sonido rico y orgánico
            detune = 1.0 + (0.0018 if n_i % 2 == 0 else -0.0018)
            amp = 0.28 if n_i == 0 else (0.18 / (1.0 + 0.22 * n_i))
            sig = np.sin(2.0 * np.pi * freq * bt) + 0.45 * np.sin(2.0 * np.pi * (freq * detune) * bt + 0.4)
            if style in ("warm_story", "lofi_chill"):
                # Segundo armónico suave tipo piano eléctrico Rhodes
                sig += 0.18 * np.sin(2.0 * np.pi * (freq * 2.0) * bt) * np.exp(-bt * 0.9)
            chord_sig += amp * sig * env_pad

        # Arpegio / pulso melódico sutil según el estilo
        arp_notes = notes[1:]
        steps = 8 if style in ("doc_mystery", "inspiring_science", "warm_story") else 4
        step_sec = bar_sec / float(steps)
        step_n = int(sr * step_sec)
        for s_i in range(steps):
            s_start = s_i * step_n
            s_end = min(seg_n, s_start + step_n)
            if s_end <= s_start:
                continue
            st = np.linspace(0.0, (s_end - s_start) / float(sr), s_end - s_start, endpoint=False, dtype=np.float32)
            note_f = arp_notes[(s_i + b_idx) % len(arp_notes)] * (2.0 if style == "inspiring_science" else 1.0)
            pluck_env = np.clip(st / 0.025, 0.0, 1.0) * np.exp(-st * (3.8 if style != "dark_suspense" else 2.2))
            pluck = np.sin(2.0 * np.pi * note_f * st) + 0.25 * np.sin(2.0 * np.pi * (note_f * 2.0) * st)
            arp_gain = 0.09 if style != "dark_suspense" else 0.05
            chord_sig[s_start:s_end] += arp_gain * pluck * pluck_env

        # Pulso sub-grave suave (heartbeat / lo-fi pulse)
        if style in ("doc_mystery", "dark_suspense", "lofi_chill"):
            beats = 4 if style != "dark_suspense" else 2
            beat_n = seg_n // beats
            for k in range(beats):
                k_start = k * beat_n
                k_end = min(seg_n, k_start + int(sr * 0.45))
                kt = np.linspace(0.0, (k_end - k_start) / float(sr), k_end - k_start, endpoint=False, dtype=np.float32)
                sub_f = 55.0 * (1.0 + 0.6 * np.exp(-kt * 18.0))
                sub_env = np.exp(-kt * 7.5)
                chord_sig[k_start:k_end] += 0.16 * np.sin(2.0 * np.pi * sub_f * kt) * sub_env

        loop_buf[start_i:end_i] += chord_sig

    # Reverberación ambiental multi-tap (delays primos para cola espacial sin resonancia metálica)
    reverb = loop_buf.copy()
    for delay_ms, decay in ((113, 0.36), (197, 0.26), (311, 0.18), (463, 0.12)):
        shift = int(sr * (delay_ms / 1000.0))
        reverb += decay * np.roll(loop_buf, shift)

    # Filtro paso-bajo FFT (< 2400 Hz) para que la música sea cálida y deje libre la banda de la voz (2.5-5 kHz)
    freqs = np.fft.rfftfreq(loop_n, d=1.0 / float(sr))
    spec = np.fft.rfft(reverb)
    cutoff = 1600.0 if style in ("lofi_chill", "dark_suspense") else 2300.0
    lp_mask = 1.0 / (1.0 + (freqs / cutoff) ** 4)
    # También atenuamos ligeramente 350-800 Hz para dar espacio al cuerpo del locutor
    voice_pocket = 1.0 - 0.22 * np.exp(-0.5 * ((freqs - 520.0) / 220.0) ** 2)
    filtered_loop = np.fft.irfft(spec * lp_mask * voice_pocket, n=loop_n).astype(np.float32)

    peak = float(np.max(np.abs(filtered_loop)))
    if peak > 1e-5:
        filtered_loop = (filtered_loop / peak) * 0.85

    # Repetir el ciclo para cubrir toda la duración del video
    repeats = (n_samples // loop_n) + 2
    full_music = np.tile(filtered_loop, repeats)[:n_samples]

    # Fade-in suave de 1.2s y fade-out de 2.2s al final
    fade_in = min(int(sr * 1.2), n_samples // 4)
    fade_out = min(int(sr * 2.2), n_samples // 3)
    if fade_in > 10:
        full_music[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)
    if fade_out > 10:
        full_music[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)

    return full_music


def _load_custom_music_resampled(custom_path: Path, target_n: int, sr: int = 24000) -> np.ndarray:
    """Carga un archivo MP3/WAV personalizado usando FFmpeg a la frecuencia de muestreo de la narración."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_wav = custom_path.parent / "_tmp_custom_music_24k.wav"
    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-y",
        "-i",
        str(custom_path),
        "-ac",
        "1",
        "-ar",
        str(sr),
        str(tmp_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not tmp_wav.exists():
        return np.zeros(target_n, dtype=np.float32)
    try:
        import soundfile as sf

        data, _ = sf.read(tmp_wav, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if len(data) < 100:
            return np.zeros(target_n, dtype=np.float32)
        peak = float(np.max(np.abs(data)))
        if peak > 1e-5:
            data = (data / peak) * 0.85
        repeats = (target_n // len(data)) + 2
        looped = np.tile(data, repeats)[:target_n]
        fade_out = min(int(sr * 2.2), target_n // 3)
        if fade_out > 10:
            looped[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)
        return looped.astype(np.float32)
    finally:
        try:
            tmp_wav.unlink(missing_ok=True)
        except Exception:
            pass


def mix_narration_with_bg_music(
    narration_wav_path: Path,
    output_wav_path: Path,
    bg_music_style: str = "doc_mystery",
    bg_music_volume: float = 0.14,
    custom_music_path: Optional[Path] = None,
    scenes: Optional[list[dict[str, Any]]] = None,
    enable_foley: bool = False,
) -> Path:
    """Mezcla la narración maestra con música de fondo aplicando Auto-Ducking inteligente.
    Los efectos de sonido (SFX/Foley) se mantienen desactivados por defecto para máxima claridad."""
    import soundfile as sf

    if not narration_wav_path.exists():
        return narration_wav_path

    voice_samples, sr = sf.read(narration_wav_path, dtype="float32")
    if voice_samples.ndim > 1:
        voice_samples = voice_samples.mean(axis=1)
    n_samples = len(voice_samples)
    dur_sec = n_samples / float(sr)

    # 1. Capa de Foley desactivada para una mezcla limpia centrada en voz y música
    foley_samples = np.zeros(n_samples, dtype=np.float32)
    if enable_foley and scenes and len(scenes) > 1:
        try:
            from studio.animated_shorts.earshot_sound_designer import synthesize_foley_sample
            for idx, sc in enumerate(scenes):
                st_sec = float(sc.get("start_sec", 0.0))
                st_samp = int(st_sec * sr)
                if st_samp >= n_samples:
                    continue
                if idx == 0:
                    fx_name = "foley_cinematic_riser"
                elif idx == len(scenes) - 1:
                    fx_name = "foley_sub_boom"
                elif idx % 3 == 0:
                    fx_name = "foley_metal_click"
                else:
                    fx_name = "foley_camera_glide"
                fx_audio = synthesize_foley_sample(fx_name, duration_sec=0.85)
                # Resamplear si difiere de sr
                end_samp = min(n_samples, st_samp + len(fx_audio))
                flen = end_samp - st_samp
                if flen > 0:
                    foley_samples[st_samp:end_samp] += fx_audio[:flen] * 0.32
        except Exception as e_foley:
            logger.debug(f"Aviso al sintetizar Foley: {e_foley}")

    # 2. Capa de Música de fondo con Auto-Ducking
    if bg_music_style != "none" and bg_music_volume > 0.005:
        if bg_music_style == "custom" and custom_music_path and custom_music_path.exists():
            music_samples = _load_custom_music_resampled(custom_music_path, n_samples, sr=sr)
        else:
            music_samples = generate_royalty_free_music(bg_music_style, duration_sec=dur_sec, sr=sr)

        if len(music_samples) < n_samples:
            music_samples = np.pad(music_samples, (0, n_samples - len(music_samples)))
        else:
            music_samples = music_samples[:n_samples]

        # Auto-Ducking envolvente suave (ventana de 280ms)
        win = max(64, int(sr * 0.28))
        kernel = np.ones(win, dtype=np.float32) / float(win)
        voice_env = np.convolve(np.abs(voice_samples), kernel, mode="same")
        speaking_mask = np.clip(voice_env / 0.035, 0.0, 1.0)

        base_vol = float(np.clip(bg_music_volume, 0.0, 0.55))
        ducking_gain = base_vol * (1.38 - 0.38 * speaking_mask)
        music_layer = music_samples * ducking_gain
    else:
        music_layer = np.zeros(n_samples, dtype=np.float32)

    mixed = voice_samples + foley_samples + music_layer
    try:
        from studio.audio_mastering import apply_studio_mastering
        mixed = apply_studio_mastering(mixed, sample_rate=sr)
    except Exception as exc:
        logger.debug(f"Mastering fallback: {exc}")
        peak = float(np.max(np.abs(mixed)))
        if peak > 0.96:
            mixed = (mixed / peak) * 0.95

    sf.write(output_wav_path, mixed.astype(np.float32), sr, format="WAV", subtype="PCM_16")
    return output_wav_path


# ==============================================================================
# 3. EFECTOS DE CÁMARA VIVA Y ATMÓSFERA VISUAL MIENTRAS PASA CADA IMAGEN
# ==============================================================================

def _build_vignette_overlay(width: int, height: int, strength: float = 0.36) -> Image.Image:
    """Crea una máscara RGBA con viñeta óptica de cine y partículas sutiles de luz."""
    x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
    y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    radius = np.sqrt(xx * xx + yy * yy)
    vig = np.clip((radius - 0.58) / 0.82, 0.0, 1.0) ** 1.6
    alpha = (vig * 255.0 * strength).astype(np.uint8)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, mode="RGBA")


def _render_camera_motion_frame(
    base_img: Image.Image,
    progress: float,
    motion_type: str,
    width: int,
    height: int,
    vignette_overlay: Optional[Image.Image] = None,
) -> Image.Image:
    """Aplica movimiento continuo de cámara (Ken Burns Zoom-In, Zoom-Out, Pan Lateral)
    con impacto visual cinemático: zoom-punch en transiciones, micro-paneo orgánico
    y viñeta de alto contraste."""
    import math

    p = float(np.clip(progress, 0.0, 1.0))
    smooth_p = 0.35 * p + 0.65 * (p * p * (3.0 - 2.0 * p))

    # Zoom-punch dinámico en el primer 15% del corte para enganchar la vista
    punch = 0.038 * math.exp(-p * 14.0)

    # Micro-movimiento documental (handheld micro-shake sutil)
    shake_x = 0.003 * math.sin(p * 22.0)
    shake_y = 0.003 * math.cos(p * 28.0)

    if motion_type == "zoom_in":
        zoom = 1.0 + 0.14 * smooth_p + punch
        cx, cy = 0.5 + shake_x, 0.48 + shake_y
    elif motion_type == "zoom_out":
        zoom = (1.14 - 0.13 * smooth_p) + punch
        cx, cy = 0.5 + shake_x, 0.48 + shake_y
    elif motion_type == "pan_right":
        zoom = 1.12 + punch
        cx = 0.44 + 0.12 * smooth_p + shake_x
        cy = 0.49 + shake_y
    elif motion_type == "pan_left":
        zoom = 1.12 + punch
        cx = 0.56 - 0.12 * smooth_p + shake_x
        cy = 0.49 + shake_y
    else:
        return base_img

    crop_w = width / zoom
    crop_h = height / zoom
    left = max(0.0, min(width - crop_w, (width * cx) - (crop_w / 2.0)))
    top = max(0.0, min(height - crop_h, (height * cy) - (crop_h / 2.0)))

    framed = base_img.resize(
        (width, height),
        resample=Image.Resampling.BILINEAR,
        box=(left, top, left + crop_w, top + crop_h),
    )

    if vignette_overlay is not None:
        framed_rgba = framed.convert("RGBA")
        framed = Image.alpha_composite(framed_rgba, vignette_overlay).convert("RGB")

    return framed


def render_project_video(
    project_dir: Path,
    scenes: list[dict[str, Any]],
    width: int = 1920,
    height: int = 1080,
    burn_subtitles: bool = True,
    transition: str = "crossfade",
    transition_duration: float = 0.5,
    subtitle_style: str = "hormozi_yellow",
    camera_effect: str = "ken_burns_mix",
    bg_music: str = "doc_mystery",
    bg_music_volume: float = 0.14,
    custom_music_path: Optional[Path] = None,
) -> Path:
    # Forzar salida en Full HD 1080p manteniendo la relación de aspecto (1920x1080 horizontal o 1080x1920 vertical)
    if width >= height and width < 1920:
        width, height = 1920, 1080
    elif height > width and height < 1920:
        width, height = 1080, 1920

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    frames_dir = project_dir / "render_frames"
    if frames_dir.exists():
        for old_f in frames_dir.glob("*.jpg"):
            try:
                old_f.unlink()
            except Exception:
                pass
    frames_dir.mkdir(parents=True, exist_ok=True)

    use_ass_subs = burn_subtitles and subtitle_style != "classic_box"
    burn_static_box = burn_subtitles and subtitle_style == "classic_box"

    # 1. Cargar fotogramas base de cada escena en Full HD 1080p
    raw_scene_images: list[tuple[Image.Image, float, str, str]] = []
    motion_cycle = ["zoom_in", "pan_right", "zoom_out", "pan_left"]

    for idx, sc in enumerate(scenes, start=1):
        img_file = project_dir / "images" / f"scene_{idx:03d}.png"
        sc_text = sc.get("text", "")
        if img_file.exists():
            base_img = Image.open(img_file).convert("RGB")
            if base_img.size != (width, height):
                base_img = base_img.resize((width, height), Image.Resampling.LANCZOS)
                base_img = base_img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
            if burn_static_box:
                base_img = _draw_subtitle_on_image(base_img, sc_text)
        else:
            ts_label = f"{format_mm_ss(sc['start_sec'])} - {format_mm_ss(sc['end_sec'])}"
            base_img = _create_placeholder_image(width, height, idx, sc_text, ts_label, draw_sub=burn_static_box)

        duration = max(0.4, float(sc.get("duration_sec", 1.0)))
        if camera_effect in ("living_ai_motion", "ken_burns_mix"):
            m_type = motion_cycle[(idx - 1) % len(motion_cycle)]
        elif camera_effect == "zoom_in_dramatic":
            m_type = "zoom_in"
        elif camera_effect == "pan_cinema":
            m_type = "pan_right" if idx % 2 == 1 else "pan_left"
        else:
            m_type = "none"

        raw_scene_images.append((base_img, duration, m_type, sc_text))

    vignette_overlay = _build_vignette_overlay(width, height, strength=0.32) if camera_effect != "none" else None

    black_img = Image.new("RGB", (width, height), (0, 0, 0)) if transition == "fade_black" else None
    white_img = Image.new("RGB", (width, height), (255, 255, 255)) if transition == "fade_white" else None

    # 2. Preparar pista de audio final (Narración + Música Sin Copyright con Auto-Ducking; SIN efectos sonoros molestos)
    narration_path = project_dir / "narracion_completa.wav"
    mixed_audio_path = project_dir / "audio_mezclado_final.wav"
    final_audio_path = mix_narration_with_bg_music(
        narration_wav_path=narration_path,
        output_wav_path=mixed_audio_path,
        bg_music_style=bg_music,
        bg_music_volume=bg_music_volume,
        custom_music_path=custom_music_path,
        scenes=scenes,
        enable_foley=False,  # Quitar efectos de sonido procedimentales manteniendo la música
    )

    # 3. Generar archivo de subtítulos dinámicos .ASS si está activado
    ass_filename = "subtitulos_dinamicos.ass"
    ass_path = project_dir / ass_filename
    if use_ass_subs:
        ass_content = generate_ass_subtitles(
            scenes=scenes,
            width=width,
            height=height,
            subtitle_style=subtitle_style,
        )
        ass_path.write_text(ass_content, encoding="utf-8")

    output_mp4 = project_dir / "video_youtube.mp4"
    tmp_mp4 = project_dir / f"video_youtube_tmp_{os.getpid()}_{int(time.time()*1000)}.mp4"

    # 4. Renderizado 100% fluido a 30 FPS continuos por pipe directo a FFmpeg (cero congelamientos, cero stepped judder)
    render_fps = 30
    num_scenes = len(raw_scene_images)
    log_err_path = project_dir / "render_ffmpeg.log"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(render_fps),
        "-i", "-",
        "-i", str(final_audio_path.resolve()),
    ]
    if use_ass_subs and ass_path.exists():
        cmd.extend(["-vf", f"ass={ass_filename}"])

    cmd.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-crf",
            "18",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            str(tmp_mp4.resolve()),
        ]
    )

    def _get_rendered_scene_frame(base: Image.Image, t_sec: float, p_norm: float, dur_s: float, m_dir: str, text_s: str) -> Image.Image:
        if camera_effect == "living_ai_motion":
            try:
                from studio.living_scene_engine import render_living_scene_frame
                return render_living_scene_frame(
                    base_img=base,
                    t=t_sec,
                    scene_duration=dur_s,
                    scene_text=text_s,
                    width=width,
                    height=height,
                    motion_type=m_dir,
                    vignette_overlay=vignette_overlay,
                )
            except Exception as e_liv:
                logger.debug(f"Aviso en living motion: {e_liv}")
        return _render_camera_motion_frame(
            base,
            p_norm,
            m_dir,
            width,
            height,
            vignette_overlay=vignette_overlay,
        )

    with open(log_err_path, "wb") as err_file:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_dir.resolve()),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=err_file,
        )
        assert proc.stdin is not None
        try:
            for i in range(num_scenes):
                curr_base, dur, curr_motion, sc_text = raw_scene_images[i]
                has_next = i < num_scenes - 1
                t_dur = (
                    min(float(transition_duration), dur * 0.40, 0.85)
                    if (has_next and transition and transition != "none")
                    else 0.0
                )
                scene_frames = max(1, int(round(dur * render_fps)))
                trans_frames = max(2, int(round(t_dur * render_fps))) if t_dur >= 0.12 else 0
                hold_frames = max(1, scene_frames - trans_frames)

                # Fotogramas principales de la escena
                for f in range(hold_frames):
                    t_sec = f / float(render_fps)
                    p_prog = f / float(max(1, scene_frames))
                    frame = _get_rendered_scene_frame(curr_base, t_sec, p_prog, dur, curr_motion, sc_text)
                    proc.stdin.write(frame.tobytes())

                # Transición fluida con la siguiente escena
                if trans_frames > 0 and has_next:
                    next_base, next_dur, next_motion, next_text = raw_scene_images[i + 1]
                    for s in range(trans_frames):
                        f_cur = hold_frames + s
                        t_sec_cur = f_cur / float(render_fps)
                        p_cur = f_cur / float(max(1, scene_frames))
                        end_curr = _get_rendered_scene_frame(curr_base, t_sec_cur, p_cur, dur, curr_motion, sc_text)

                        t_sec_next = s / float(render_fps)
                        p_next = (s / float(max(1, trans_frames))) * (t_dur / max(0.5, next_dur))
                        start_next = _get_rendered_scene_frame(next_base, t_sec_next, p_next, next_dur, next_motion, next_text)

                        raw_a = (s + 1) / float(trans_frames)
                        alpha = raw_a * raw_a * (3.0 - 2.0 * raw_a)

                        if transition == "crossfade":
                            blended = Image.blend(end_curr, start_next, alpha)
                        elif transition == "fade_black" and black_img:
                            if alpha <= 0.5:
                                blended = Image.blend(end_curr, black_img, alpha * 2.0)
                            else:
                                blended = Image.blend(black_img, start_next, (alpha - 0.5) * 2.0)
                        elif transition == "fade_white" and white_img:
                            if alpha <= 0.5:
                                blended = Image.blend(end_curr, white_img, alpha * 2.0)
                            else:
                                blended = Image.blend(white_img, start_next, (alpha - 0.5) * 2.0)
                        elif transition == "slide_left":
                            blended = Image.new("RGB", (width, height))
                            shift = int(round(width * alpha))
                            blended.paste(end_curr, (-shift, 0))
                            blended.paste(start_next, (width - shift, 0))
                        else:
                            blended = Image.blend(end_curr, start_next, alpha)

                        proc.stdin.write(blended.tobytes())

            proc.stdin.close()
        except Exception:
            try:
                proc.stdin.close()
            except Exception:
                pass
            raise
        proc.wait()

    if proc.returncode != 0:
        if tmp_mp4.exists():
            try:
                tmp_mp4.unlink()
            except Exception:
                pass
        err_msg = log_err_path.read_text(encoding="utf-8", errors="ignore") if log_err_path.exists() else "Unknown"
        raise RuntimeError(f"Error en FFmpeg (returncode {proc.returncode}): {err_msg[-400:]}")

    # Reemplazo atómico hacia el archivo definitivo para evitar archivos corruptos o colisiones de lectura
    try:
        os.replace(str(tmp_mp4), str(output_mp4))
    except Exception:
        try:
            if output_mp4.exists():
                output_mp4.unlink()
            shutil.move(str(tmp_mp4), str(output_mp4))
        except Exception as e_mv:
            logger.error(f"Error al mover video temporal a definitivo: {e_mv}")
            if tmp_mp4.exists() and not output_mp4.exists():
                tmp_mp4.rename(output_mp4)

    return output_mp4


def create_project_zip(project_dir: Path, meta: dict[str, Any]) -> Path:
    zip_path = project_dir / "paquete_youtube.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        wav_path = project_dir / "narracion_completa.wav"
        if wav_path.exists():
            zf.write(wav_path, arcname="narracion_completa.wav")

        srt_path = project_dir / "subtitulos_timestamps.srt"
        if srt_path.exists():
            zf.write(srt_path, arcname="subtitulos_timestamps.srt")

        json_path = project_dir / "project.json"
        if json_path.exists():
            zf.write(json_path, arcname="timestamps_escenas.json")

        report_lines = ["=== REPORTE DE ESCENAS Y TIMESTAMPS PARA YOUTUBE ===\n"]
        if meta.get("custom_style_prompt"):
            report_lines.append(f"Prompt Maestro de Estilo: {meta['custom_style_prompt']}\n")
        for sc in meta.get("scenes", []):
            idx = sc["index"]
            t_start = format_mm_ss(sc["start_sec"])
            t_end = format_mm_ss(sc["end_sec"])
            report_lines.append(f"Timestamp #{idx:02d} [{t_start} -> {t_end}] ({sc['duration_sec']:.2f}s)")
            report_lines.append(f"Lo que dice la voz (ES): {sc['text']}")
            if sc.get("translated_en"):
                report_lines.append(f"Acción Visual Alusiva (EN): {sc['translated_en']}")
            report_lines.append(f"Prompt Completo Imagen: {sc['image_prompt']}\n")
        zf.writestr("guion_timestamps_y_prompts.txt", "\n".join(report_lines))

        images_dir = project_dir / "images"
        if images_dir.exists():
            for sc in meta.get("scenes", []):
                idx = sc["index"]
                img_p = images_dir / f"scene_{idx:03d}.png"
                if img_p.exists():
                    t_start = format_mm_ss(sc["start_sec"]).replace(":", "m").replace(".", "s")
                    t_end = format_mm_ss(sc["end_sec"]).replace(":", "m").replace(".", "s")
                    zf.write(img_p, arcname=f"imagenes/escena_{idx:02d}_{t_start}_a_{t_end}.png")

        mp4_path = project_dir / "video_youtube.mp4"
        if mp4_path.exists():
            zf.write(mp4_path, arcname="video_youtube.mp4")

    return zip_path
