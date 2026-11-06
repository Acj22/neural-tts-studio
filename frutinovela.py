"""Motor de Frutinovelas: guion de diálogos multi-voz + animación local tipo "títere digital".

Animación (Nivel 1, 100% local y gratis, sin GPU):
  - Cada personaje tiene 1 sola imagen (retrato). El narrador usa una toma grupal.
  - La boca se anima con la energía (RMS) del audio de su diálogo, fotograma por fotograma.
  - La "cámara" aplica efectos de telenovela según la emoción de cada línea:
    zoom dramático triple, sacudida al gritar, tinte azul al llorar, rebote al reír, etc.
  - Plano / contraplano automático: siempre se ve al personaje que está hablando.
  - Los fotogramas se envían directo a FFmpeg (rawvideo) para no llenar el disco.
"""

from __future__ import annotations

import math
import re
import subprocess
import textwrap
import unicodedata
from pathlib import Path
from typing import Any, Optional

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

from video_pipeline import format_mm_ss, format_srt_time, translate_es_to_en

NARRATOR_ALIASES = {"narrador", "narradora", "narrator", "voz en off", "voz", "narracion"}

# Nombre (sin acentos, minúsculas) -> descripción en inglés para el generador de imágenes
FRUIT_MAP = {
    "fresa": "strawberry", "coco": "coconut", "mango": "mango", "platano": "banana", "banana": "banana",
    "pina": "pineapple", "uva": "grape", "sandia": "watermelon", "papaya": "papaya", "manzana": "apple",
    "naranja": "orange", "limon": "lemon", "lima": "lime", "aguacate": "avocado", "pera": "pear",
    "durazno": "peach", "melocoton": "peach", "cereza": "cherry", "kiwi": "kiwi", "melon": "melon",
    "tomate": "tomato", "jitomate": "tomato", "zanahoria": "carrot", "cebolla": "onion", "chile": "chili pepper",
    "elote": "corn cob", "papa": "potato", "brocoli": "broccoli", "guayaba": "guava", "mandarina": "tangerine",
    "toronja": "grapefruit", "frambuesa": "raspberry", "arandano": "blueberry", "granada": "pomegranate",
    "higo": "fig", "ciruela": "plum", "maracuya": "passion fruit", "tuna": "prickly pear", "nopal": "cactus paddle",
    "pepino": "cucumber", "berenjena": "eggplant", "calabaza": "pumpkin", "mora": "blackberry", "lichi": "lychee",
    "pitaya": "dragon fruit", "chabacano": "apricot", "datil": "date fruit", "nuez": "walnut", "cacahuate": "peanut",
}

EMOTIONS = ["normal", "grito", "llanto", "sorpresa", "drama", "risa", "susurro"]

EMOTION_KEYWORDS = {
    "grito": ["grit", "enoj", "furios", "molest", "rabia", "enfurec", "colera", "histeric"],
    "llanto": ["llor", "trist", "sollo", "deprim", "lagrim"],
    "sorpresa": ["sorprend", "impact", "shock", "asombr", "incredul"],
    "drama": ["dram", "suspens", "revel", "secreto", "zoom", "tension"],
    "risa": ["riendo", "rie", "risa", "carcaj", "burl"],
    "susurro": ["susurr", "bajito", "en voz baja"],
}

# Ajuste de velocidad de voz según emoción (se aplica al sintetizar)
EMOTION_SPEED = {"grito": 1.08, "llanto": 0.9, "sorpresa": 1.05, "drama": 0.92, "risa": 1.05, "susurro": 0.93}

CHAR_COLORS = ["#f43f5e", "#f59e0b", "#22c55e", "#3b82f6", "#a855f7", "#ec4899", "#14b8a6", "#eab308", "#ef4444"]

DEFAULT_FRUTI_STYLE = (
    "3D animated feature film style like Pixar and DreamWorks, glossy realistic fruit skin texture, "
    "the fruit itself is the character's head and body with a cute expressive cartoon face, small arms, "
    "dramatic Latin American telenovela soap-opera lighting, shallow depth of field, highly detailed render"
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(name)).strip("_") or "personaje"


def is_narrator(name: str) -> bool:
    return _norm(name) in NARRATOR_ALIASES


def detect_fruit(name: str) -> Optional[str]:
    n = _norm(name)
    # Primero coincidencia exacta, luego por prefijo (ej. "Cocardo" -> coco, "Fresita" -> fresa)
    if n in FRUIT_MAP:
        return FRUIT_MAP[n]
    for word in n.split():
        for key in sorted(FRUIT_MAP, key=len, reverse=True):
            # "Cocardo" -> coco, "Fresita" -> fresa, "Manguito" -> mango
            if word.startswith(key) or word.startswith(key[: max(3, len(key) - 1)]):
                return FRUIT_MAP[key]
    return None


def guess_gender(name: str) -> str:
    n = _norm(name).split()[0] if _norm(name) else ""
    if n.endswith(("ita", "ina", "ela", "isa")):
        return "F"
    if n.endswith("a") and not n.endswith(("ma", "ista")):
        return "F"
    return "M"


def detect_emotion(text: str) -> str:
    t = text.strip()
    letters = [c for c in t if c.isalpha()]
    upper_ratio = sum(1 for c in letters if c.isupper()) / max(1, len(letters))
    if ("?!" in t or "!?" in t or "¡¿" in t or "¿¡" in t):
        return "sorpresa"
    if t.count("!") >= 2 or (len(letters) > 8 and upper_ratio > 0.6):
        return "grito"
    return "normal"


def _emotion_from_direction(direction: str) -> Optional[str]:
    d = _norm(direction)
    for emo, keys in EMOTION_KEYWORDS.items():
        if any(k in d for k in keys):
            return emo
    return None


_BRACKET_RE = re.compile(r"^\s*\[([^\]]{1,40})\]\s*(\([^)]*\))?\s*[:：]?\s*(.+)$")
_PLAIN_RE = re.compile(r"^\s*([A-Za-zÁÉÍÓÚÑÜáéíóúñü][\wÁÉÍÓÚÑÜáéíóúñü .'\-]{0,29}?)\s*(\([^)]*\))?\s*:\s*(.+)$")


def parse_dialogue_script(script: str) -> list[dict[str, Any]]:
    """Convierte un guion tipo:
        [Fresa] (llorando): ¡Me engañaste, Cocardo!
        Cocardo: Mi amor, déjame explicarte...
        Narrador: Y así comenzó la tragedia.
    en una lista de líneas {speaker, text, emotion}. Las líneas sin personaje se asignan al Narrador.
    Las líneas que empiezan con '#', '//' o 'ESCENA' se ignoran (notas del guionista)."""
    lines: list[dict[str, Any]] = []
    for raw in (script or "").splitlines():
        row = raw.strip()
        if not row or row.startswith(("#", "//", "---")) or _norm(row).startswith(("escena", "capitulo", "episodio")):
            continue

        speaker, direction, text = None, "", row
        m = _BRACKET_RE.match(row)
        if m:
            speaker, direction, text = m.group(1).strip(), (m.group(2) or ""), m.group(3).strip()
        else:
            m = _PLAIN_RE.match(row)
            if m and len(m.group(1).split()) <= 4:
                speaker, direction, text = m.group(1).strip(), (m.group(2) or ""), m.group(3).strip()

        # Acotaciones al inicio del texto: "(gritando) ¡Eres un cínico!"
        lead = re.match(r"^\(([^)]*)\)\s*[:：]?\s*(.*)$", text)
        if lead:
            direction = f"{direction} ({lead.group(1)})"
            text = lead.group(2).strip()
        # Quitar acotaciones restantes dentro del texto hablado
        inner = re.findall(r"\(([^)]*)\)", text)
        if inner:
            direction = f"{direction} " + " ".join(f"({x})" for x in inner)
            text = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip()

        if not text:
            continue
        if not speaker:
            speaker = "Narrador"
        if is_narrator(speaker):
            speaker = "Narrador"

        emotion = _emotion_from_direction(direction) if direction.strip() else None
        lines.append(
            {
                "speaker": speaker,
                "slug": slugify(speaker),
                "text": text,
                "direction": direction.strip(" ()"),
                "emotion": emotion or detect_emotion(text),
            }
        )
    return lines


def default_character_profiles(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Construye el elenco detectado con voz, velocidad y descripción sugeridas."""
    seen: dict[str, dict[str, Any]] = {}
    female_voices = ["es_f_valeria", "ef_dora", "es_f_sofia"]
    male_voices = ["es_m_eric", "em_santa", "es_m_liam", "es_m_braulio", "em_alex", "im_nicola"]
    f_i = m_i = 0
    for ln in lines:
        slug = ln["slug"]
        if slug in seen:
            seen[slug]["line_count"] += 1
            continue
        name = ln["speaker"]
        narrator = is_narrator(name)
        fruit = detect_fruit(name)
        gender = guess_gender(name)
        if narrator:
            voice, speed, desc = "es_m_daniel", 0.95, ""
        elif gender == "F":
            voice = female_voices[f_i % len(female_voices)]
            speed = [1.05, 1.0, 1.1][f_i % 3]
            f_i += 1
            desc = "personaje femenino con pestañas largas, labios rojos, aretes de perla y mirada dramática"
        else:
            voice = male_voices[m_i % len(male_voices)]
            speed = [1.0, 0.95, 1.05][m_i % 3]
            m_i += 1
            desc = "personaje masculino con bigote, cejas pobladas y camisa desabotonada de galán de telenovela"
        seen[slug] = {
            "name": name,
            "slug": slug,
            "is_narrator": narrator,
            "fruit_en": fruit or "",
            "gender": gender,
            "voice": voice,
            "speed": speed,
            "description": desc,
            "color": "#94a3b8" if narrator else CHAR_COLORS[len([c for c in seen.values() if not c["is_narrator"]]) % len(CHAR_COLORS)],
            "line_count": 1,
        }
    return list(seen.values())


def build_character_prompt(char: dict[str, Any], style_prompt: str, setting_en: str) -> str:
    desc_es = (char.get("description") or "").strip()
    desc_en = translate_es_to_en(desc_es) if desc_es else ""
    fruit = char.get("fruit_en") or "fruit"
    gender = "female" if char.get("gender") == "F" else "male"
    subject = f"An anthropomorphic {gender} {fruit} character"
    if desc_en:
        subject += f" ({desc_en})"
    parts = [
        subject,
        "medium close-up portrait of this single character facing the camera, centered in the frame, "
        "big expressive eyes, cartoon eyebrows, mouth closed and clearly visible in the middle of the face",
        f"background: {setting_en}" if setting_en else "",
        style_prompt or DEFAULT_FRUTI_STYLE,
        "no text, no letters, no watermark",
    ]
    return ". ".join(p.strip().rstrip(".") for p in parts if p.strip()) + "."


def build_group_prompt(chars: list[dict[str, Any]], style_prompt: str, setting_en: str) -> str:
    cast = [c for c in chars if not c.get("is_narrator")]
    who = ", ".join(
        f"a {'female' if c.get('gender') == 'F' else 'male'} {c.get('fruit_en') or 'fruit'} character" for c in cast[:5]
    ) or "anthropomorphic fruit characters"
    parts = [
        f"Wide establishing shot of {len(cast) or 'several'} anthropomorphic fruit characters together in a dramatic telenovela scene: {who}",
        f"setting: {setting_en}" if setting_en else "",
        style_prompt or DEFAULT_FRUTI_STYLE,
        "no text, no letters, no watermark",
    ]
    return ". ".join(p.strip().rstrip(".") for p in parts if p.strip()) + "."


def generate_fruti_srt(lines: list[dict[str, Any]]) -> str:
    blocks = []
    for i, ln in enumerate(lines, start=1):
        who = "" if ln["slug"] == "narrador" else f"{ln['speaker']}: "
        blocks.append(f"{i}\n{format_srt_time(ln['start_sec'])} --> {format_srt_time(ln['speech_end_sec'])}\n{who}{ln['text']}\n")
    return "\n".join(blocks)


def timestamp_label(a: float, b: float) -> str:
    return f"{format_mm_ss(a)} → {format_mm_ss(b)}"


# ----------------------------------------------------------------------------------------------
# ANIMACIÓN
# ----------------------------------------------------------------------------------------------

def compute_mouth_envelope(samples: np.ndarray, sr: int, fps: int) -> np.ndarray:
    """Apertura de boca (0..1) por fotograma a partir del volumen (RMS) del audio."""
    hop = max(1, int(round(sr / fps)))
    n = int(math.ceil(len(samples) / hop))
    padded = np.zeros(n * hop, dtype=np.float32)
    padded[: len(samples)] = samples
    rms = np.sqrt(np.mean(padded.reshape(n, hop) ** 2, axis=1))
    voiced = rms[rms > 1e-4]
    ref = float(np.percentile(voiced, 90)) if voiced.size else 1.0
    norm = np.clip(rms / max(ref, 1e-6), 0.0, 1.2)
    norm[norm < 0.14] = 0.0  # compuerta de ruido: boca cerrada en silencios
    out = np.zeros_like(norm)
    prev = 0.0
    for i, v in enumerate(norm):
        # Variación tipo "sílaba" para que la boca no se quede abierta fija en vocales largas
        v = v * (0.72 + 0.28 * abs(math.sin(i * 1.9)))
        prev = max(v, prev * 0.5)  # ataque inmediato, cierre suave
        out[i] = prev
    return np.clip(out, 0.0, 1.0)


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for name in (
        ("arialbd.ttf", "segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else ("arial.ttf", "segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    ):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = (h or "#ffffff").lstrip("#")
    try:
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except Exception:
        return (255, 255, 255)


def _placeholder_plate(pw: int, ph: int, name: str, color: str) -> Image.Image:
    img = Image.new("RGB", (pw, ph), (24, 16, 32))
    draw = ImageDraw.Draw(img)
    rgb = _hex_to_rgb(color)
    for y in range(0, ph, 4):
        k = y / ph
        draw.rectangle([0, y, pw, y + 4], fill=(int(30 + 40 * k), int(14 + 10 * k), int(40 + 30 * k)))
    r = int(min(pw, ph) * 0.22)
    cx, cy = pw // 2, int(ph * 0.45)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb)
    draw.ellipse([cx - r // 3 - 12, cy - r // 4 - 12, cx - r // 3 + 12, cy - r // 4 + 12], fill=(255, 255, 255))
    draw.ellipse([cx + r // 3 - 12, cy - r // 4 - 12, cx + r // 3 + 12, cy - r // 4 + 12], fill=(255, 255, 255))
    font = _load_font(int(pw * 0.07))
    bbox = draw.textbbox((0, 0), name, font=font)
    draw.text(((pw - (bbox[2] - bbox[0])) // 2, cy + r + 30), name, font=font, fill=(255, 255, 255))
    return img


class _Plate:
    """Imagen del personaje preparada a mayor tamaño que el lienzo para permitir zoom y sacudidas."""

    def __init__(self, img: Optional[Image.Image], W: int, H: int, margin: float, mouth: Optional[dict], name: str, color: str):
        self.pw, self.ph = int(W * margin), int(H * margin)
        self.mouth = None
        if img is None:
            self.img = _placeholder_plate(self.pw, self.ph, name, color)
            if mouth is not None:
                self.mouth = {
                    "x": self.pw * 0.5,
                    "y": self.ph * 0.48,
                    "w": min(self.pw, self.ph) * 0.16,
                    "lip": (70, 20, 30),
                }
            return
        iw, ih = img.size
        scale = max(self.pw / iw, self.ph / ih)
        rw, rh = int(math.ceil(iw * scale)), int(math.ceil(ih * scale))
        resized = img.convert("RGB").resize((rw, rh), Image.Resampling.LANCZOS)
        ox, oy = (rw - self.pw) // 2, (rh - self.ph) // 2
        self.img = resized.crop((ox, oy, ox + self.pw, oy + self.ph))
        if mouth and mouth.get("enabled", True):
            mx = float(mouth.get("x", 0.5)) * rw - ox
            my = float(mouth.get("y", 0.58)) * rh - oy
            mw = max(8.0, float(mouth.get("w", 0.14)) * rw)
            sx0, sy0 = int(max(0, mx - mw / 2)), int(max(0, my - mw / 4))
            sx1, sy1 = int(min(self.pw, sx0 + max(2, mw))), int(min(self.ph, sy0 + max(2, mw / 2)))
            if sx1 > sx0 and sy1 > sy0:
                patch = self.img.crop((sx0, sy0, sx1, sy1)).resize((1, 1))
                skin = patch.getpixel((0, 0))
            else:
                skin = (180, 80, 80)
            self.mouth = {
                "x": mx,
                "y": my,
                "w": mw,
                "lip": tuple(int(c * 0.55) for c in skin),
            }


def _draw_mouth(region: Image.Image, cx: float, cy: float, mw: float, openness: float, lip: tuple) -> None:
    if openness < 0.08:
        return
    ss = 3  # supermuestreo para bordes suaves
    w = mw * (0.72 + 0.28 * openness)
    h = max(4.0, mw * 0.58 * openness)
    pad = mw * 0.15
    pw_, ph_ = int((w + pad * 2) * ss), int((h + pad * 2) * ss)
    if pw_ < 6 or ph_ < 6:
        return
    patch = Image.new("RGBA", (pw_, ph_), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    x0, y0, x1, y1 = pad * ss, pad * ss, (pad + w) * ss, (pad + h) * ss
    if x1 <= x0 + 2 or y1 <= y0 + 2:
        return
    lip_w = max(2, int(mw * 0.06 * ss))
    d.ellipse([x0, y0, x1, y1], fill=(46, 10, 16, 255), outline=lip + (255,), width=lip_w)
    # Lengua
    tx0, ty0 = x0 + (x1 - x0) * 0.22, y0 + (y1 - y0) * 0.55
    tx1, ty1 = x1 - (x1 - x0) * 0.22, y1 - lip_w
    if tx1 > tx0 + 2 and ty1 > ty0 + 2:
        d.ellipse([tx0, ty0, tx1, ty1], fill=(214, 86, 98, 255))
    # Dientes superiores
    if openness > 0.35:
        dx0, dy0 = x0 + (x1 - x0) * 0.25, y0 + lip_w
        dx1, dy1 = x1 - (x1 - x0) * 0.25, y0 + lip_w + (y1 - y0) * 0.16
        if dx1 > dx0 + 2 and dy1 > dy0 + 2:
            d.rectangle([dx0, dy0, dx1, dy1], fill=(250, 250, 245, 255))
    patch = patch.resize((max(1, pw_ // ss), max(1, ph_ // ss)), Image.Resampling.LANCZOS)
    region.paste(patch, (int(cx - w / 2 - pad), int(cy - h / 2 - pad)), patch)


def _subtitle_overlay(W: int, H: int, speaker: str, text: str, color: str, narrator: bool) -> tuple[Image.Image, tuple[int, int]]:
    font_size = max(22, int(W * (0.048 if H > W else 0.03)))
    font = _load_font(font_size)
    name_font = _load_font(int(font_size * 0.85))
    max_chars = max(18, int((W * 0.84) / (font_size * 0.56)))
    lines = textwrap.wrap(text, width=max_chars)[:4]
    lh = int(font_size * 1.3)
    name_h = 0 if narrator else int(font_size * 1.15)
    box_w = int(W * 0.9)
    box_h = name_h + len(lines) * lh + 26
    ov = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=18, fill=(8, 8, 16, 200))
    y = 12
    if not narrator:
        d.text((20, y), speaker.upper(), font=name_font, fill=_hex_to_rgb(color) + (255,))
        y += name_h
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=font)
        d.text(((box_w - (bb[2] - bb[0])) // 2, y), ln, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
        y += lh
    # En vertical se coloca arriba de la zona de botones de TikTok/Reels
    pos_y = int(H * 0.68) if H > W else H - box_h - int(H * 0.06)
    return ov, ((W - box_w) // 2, pos_y)


def _ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def render_frutinovela_video(
    project_dir: Path,
    meta: dict[str, Any],
    burn_subtitles: bool = True,
    intensity: float = 1.0,
    music_path: Optional[Path] = None,
    music_volume: float = 0.15,
    fps: int = 24,
) -> Path:
    W, H = int(meta["width"]), int(meta["height"])
    margin = 1.22
    audio_path = project_dir / "narracion_completa.wav"
    samples, sr = sf.read(audio_path, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    env = compute_mouth_envelope(samples, sr, fps)
    total_dur = len(samples) / float(sr)
    total_frames = int(math.ceil(total_dur * fps))

    # Preparar placas de cada personaje y de la toma grupal
    plates: dict[str, _Plate] = {}
    for ch in meta["characters"]:
        img_file = project_dir / "images" / f"char_{ch['slug']}.png"
        img = Image.open(img_file) if img_file.exists() else None
        if ch.get("is_narrator"):
            continue
        plates[ch["slug"]] = _Plate(img, W, H, margin, ch.get("mouth"), ch["name"], ch.get("color", "#ffffff"))
    group_file = project_dir / "images" / "char__group.png"
    group_plate = _Plate(Image.open(group_file) if group_file.exists() else None, W, H, margin, None, "Frutinovela", "#a855f7")

    chars_by_slug = {c["slug"]: c for c in meta["characters"]}
    subs: list[Optional[tuple[Image.Image, tuple[int, int]]]] = []
    for ln in meta["lines"]:
        if burn_subtitles:
            ch = chars_by_slug.get(ln["slug"], {})
            subs.append(_subtitle_overlay(W, H, ln["speaker"], ln["text"], ch.get("color", "#ffffff"), ln["slug"] == "narrador"))
        else:
            subs.append(None)

    tint_cache: dict[tuple, Image.Image] = {}

    def tint(frame: Image.Image, rgb: tuple, alpha: float) -> Image.Image:
        if alpha <= 0.01:
            return frame
        if rgb not in tint_cache:
            tint_cache[rgb] = Image.new("RGB", (W, H), rgb)
        return Image.blend(frame, tint_cache[rgb], min(0.6, alpha))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_mp4 = project_dir / "frutinovela.mp4"
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(audio_path)]
    if music_path and music_path.exists():
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]
        cmd += [
            "-filter_complex",
            f"[2:a]volume={max(0.0, min(1.0, music_volume)):.3f}[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
            "-map", "0:v", "-map", "[a]",
        ]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_mp4)]

    log_path = project_dir / "render_log.txt"
    with open(log_path, "w", encoding="utf-8", errors="ignore") as log_f:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log_f)
        lines = meta["lines"]
        li = 0
        k = float(intensity)
        try:
            for f in range(total_frames):
                t = f / fps
                while li < len(lines) - 1 and t >= lines[li]["end_sec"]:
                    li += 1
                ln = lines[li]
                tl = max(0.0, t - ln["start_sec"])
                dur = max(0.3, ln["end_sec"] - ln["start_sec"])
                speaking = t <= ln["speech_end_sec"]
                o = float(env[f]) if (f < len(env) and speaking) else 0.0
                emo = ln.get("emotion", "normal")

                plate = group_plate if ln["slug"] == "narrador" or ln["slug"] not in plates else plates[ln["slug"]]

                # --- Cámara base: acercamiento lento alterno (plano / contraplano) ---
                prog = min(1.0, tl / dur)
                z = 1.0 + (0.05 * prog if li % 2 == 0 else 0.05 * (1 - prog)) * k
                ox = oy = 0.0
                tint_rgb, tint_a = (0, 0, 0), 0.0

                # Rebote al hablar
                oy -= o * 7 * k
                z += o * 0.012 * k

                if emo == "grito":
                    z += 0.07 * k
                    amp = (3 + 11 * o) * k
                    ox += math.sin(f * 2.7) * amp
                    oy += math.cos(f * 3.3) * amp
                    tint_rgb, tint_a = (200, 20, 20), (0.05 + 0.10 * o) * k
                elif emo == "sorpresa":
                    z += 0.18 * _ease_out(tl / 0.35) * k
                    if tl < 0.08:
                        tint_rgb, tint_a = (255, 255, 255), 0.55
                elif emo == "drama":
                    step = min(3, int(tl / 0.28))  # ta-ta-taaan: zoom triple de telenovela
                    z += 0.09 * step * k
                    tint_rgb, tint_a = (60, 0, 40), 0.10 * k
                elif emo == "llanto":
                    ox += math.sin(t * 1.4) * 9 * k
                    oy += math.sin(t * 0.9) * 4 * k
                    tint_rgb, tint_a = (30, 70, 170), 0.16 * k
                elif emo == "risa":
                    oy -= abs(math.sin(t * 11)) * 10 * k * (0.4 + o)
                elif emo == "susurro":
                    z += 0.04 * k
                    tint_rgb, tint_a = (0, 0, 0), 0.22 * k

                # --- Recorte de la placa según zoom/offset ---
                vw, vh = W / z, H / z
                cx = plate.pw / 2 + ox
                cy = plate.ph / 2 + oy
                cx = min(max(cx, vw / 2), plate.pw - vw / 2)
                cy = min(max(cy, vh / 2), plate.ph - vh / 2)
                x0, y0 = int(cx - vw / 2), int(cy - vh / 2)
                region = plate.img.crop((x0, y0, x0 + int(vw), y0 + int(vh)))

                if plate.mouth and o > 0:
                    m = plate.mouth
                    _draw_mouth(region, m["x"] - x0, m["y"] - y0, m["w"], o, m["lip"])

                frame = region.resize((W, H), Image.Resampling.BILINEAR)
                frame = tint(frame, tint_rgb, tint_a)

                sub = subs[li]
                if sub is not None and speaking:
                    ov, pos = sub
                    frame.paste(ov, pos, ov)

                proc.stdin.write(frame.tobytes())
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.wait()

    if proc.returncode != 0:
        tail = log_path.read_text(encoding="utf-8", errors="ignore")[-500:]
        raise RuntimeError(f"Error en FFmpeg al renderizar la frutinovela: {tail}")
    return out_mp4
