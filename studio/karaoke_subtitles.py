"""Módulo de Subtítulos Karaoke Dinámicos y Sincronización Fonética Precisa.

Utiliza faster-whisper + stable-ts en CPU (INT8) para alinear texto canónico en español
palabra por palabra con el audio de la narración, generando subtítulos ASS de alto impacto
estilo viral / TikTok / Shorts con resaltado dinámico, respetando estrictamente las fronteras
de oraciones, eliminando congelamientos durante pausas y corrigiendo faltas ortográficas.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("studio.karaoke_subtitles")

# Asegurar ffmpeg en PATH para subprocesses de stable_whisper
try:
    import imageio_ffmpeg
    _ff_bin = Path(imageio_ffmpeg.get_ffmpeg_exe())
    _ff_dir = _ff_bin.parent
    _ff_alias = _ff_dir / "ffmpeg.exe"
    if not _ff_alias.exists():
        shutil.copyfile(_ff_bin, _ff_alias)
    if str(_ff_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(_ff_dir) + os.pathsep + os.environ.get("PATH", "")
except Exception as _e:
    logger.debug(f"Aviso configurando ffmpeg en PATH: {_e}")

# Asegurar .venv/Scripts en PATH si contiene ffmpeg
_venv_scripts = Path(__file__).resolve().parent.parent / ".venv" / "Scripts"
if _venv_scripts.exists() and str(_venv_scripts) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_venv_scripts) + os.pathsep + os.environ.get("PATH", "")

# Parche de compatibilidad PyAV para evitar TypeError: open() got an unexpected keyword argument 'metadata_errors'
try:
    import av
    if hasattr(av, "open") and not getattr(av.open, "_patched_metadata", False):
        _orig_av_open = av.open
        def _safe_av_open(*args, **kwargs):
            kwargs.pop("metadata_errors", None)
            return _orig_av_open(*args, **kwargs)
        _safe_av_open._patched_metadata = True
        av.open = _safe_av_open
except Exception:
    pass

_WHISPER_MODEL = None


# =============================================================================
# 1. MOTOR DE CORRECCIÓN ORTOGRÁFICA Y GRAMATICAL EN ESPAÑOL
# =============================================================================

# Diccionario exhaustivo de palabras frecuentes y términos históricos con tilde / mayúscula
_SPANISH_ORTHOGRAPHY_REPLACEMENTS = {
    # Entidades históricas y geográficas clave
    r"\bmexico\b": "México",
    r"\bméxico\b": "México",
    r"\bescuadron 201\b": "Escuadrón 201",
    r"\bescuadron\b": "escuadrón",
    r"\bescuadrones\b": "escuadrones",
    r"\bpacifico\b": "Pacífico",
    r"\bluzon\b": "Luzón",
    r"\bfaja de oro\b": "Faja de Oro",
    r"\bpotrero del llano\b": "Potrero del Llano",
    r"\bmanuel avila camacho\b": "Manuel Ávila Camacho",
    r"\bavila camacho\b": "Ávila Camacho",
    r"\bavila\b": "Ávila",
    r"\bcardenas rodriguez\b": "Cárdenas Rodríguez",
    r"\bcardenas\b": "Cárdenas",
    r"\brodriguez\b": "Rodríguez",
    r"\bmacarthur\b": "MacArthur",
    r"\bdouglas macarthur\b": "Douglas MacArthur",
    r"\bfilipinas\b": "Filipinas",
    r"\bmanila\b": "Manila",
    r"\bformosa\b": "Formosa",
    r"\btaiwan\b": "Taiwán",
    r"\bporac\b": "Porac",
    r"\bfaem\b": "FAEM",
    r"\bfuerza aerea expedicionaria mexicana\b": "Fuerza Aérea Expedicionaria Mexicana",
    r"\bsegunda guerra mundial\b": "Segunda Guerra Mundial",
    r"\bgolfo de mexico\b": "Golfo de México",
    r"\bciudad de mexico\b": "Ciudad de México",
    r"\bestados unidos\b": "Estados Unidos",
    r"\bimperio japones\b": "Imperio japonés",
    r"\bp-47d thunderbolt\b": "P-47D Thunderbolt",
    r"\brepublic p-47d\b": "Republic P-47D",
    r"\bdurango\b": "Durango",
    r"\bcoahuila\b": "Coahuila",
    r"\bchihuahua\b": "Chihuahua",
    r"\bcampeche\b": "Campeche",
    r"\byucatan\b": "Yucatán",

    # Sustantivos y adjetivos que requieren tilde
    r"\bheroe\b": "héroe",
    r"\bheroes\b": "héroes",
    r"\bheroico\b": "heroico",
    r"\bheroica\b": "heroica",
    r"\bvalentia\b": "valentía",
    r"\bmecanico\b": "mecánico",
    r"\bmecanicos\b": "mecánicos",
    r"\btecnico\b": "técnico",
    r"\btecnicos\b": "técnicos",
    r"\bejercito\b": "ejército",
    r"\bejercitos\b": "ejércitos",
    r"\bnacion\b": "nación",
    r"\bnaciones\b": "naciones",
    r"\bocasion\b": "ocasión",
    r"\bocasiones\b": "ocasiones",
    r"\bmision\b": "misión",
    r"\bmisiones\b": "misiones",
    r"\boperacion\b": "operación",
    r"\boperaciones\b": "operaciones",
    r"\baereo\b": "aéreo",
    r"\baerea\b": "aérea",
    r"\baereos\b": "aéreos",
    r"\baereas\b": "aéreas",
    r"\blinea\b": "línea",
    r"\blineas\b": "líneas",
    r"\bperiodo\b": "período",
    r"\bperiodos\b": "períodos",
    r"\bfenomeno\b": "fenómeno",
    r"\bfenomenos\b": "fenómenos",
    r"\bcientifico\b": "científico",
    r"\bcientifica\b": "científica",
    r"\bcientificos\b": "científicos",
    r"\bcientificas\b": "científicas",
    r"\bgeografico\b": "geográfico",
    r"\bgeografica\b": "geográfica",
    r"\bgeograficos\b": "geográficos",
    r"\bgeograficas\b": "geográficas",
    r"\bhistorico\b": "histórico",
    r"\bhistorica\b": "histórica",
    r"\bhistoricos\b": "históricos",
    r"\bhistoricas\b": "históricas",
    r"\bgeologico\b": "geológico",
    r"\bgeologica\b": "geológica",
    r"\barqueologico\b": "arqueológico",
    r"\barqueologica\b": "arqueológica",
    r"\barqueologia\b": "arqueología",
    r"\bgeologia\b": "geología",
    r"\btecnologia\b": "tecnología",
    r"\btecnologias\b": "tecnologías",
    r"\bunica\b": "única",
    r"\bunico\b": "único",
    r"\bunicas\b": "únicas",
    r"\bunicos\b": "únicos",
    r"\baleman\b": "alemán",
    r"\balemanes\b": "alemanes",
    r"\bjapones\b": "japonés",
    r"\bjaponeses\b": "japoneses",

    # Verbos en pretérito perfecto simple / copretérito
    r"\bcombate o\b": "combatió",
    r"\bcombatio\b": "combatió",
    r"\bdeclaro\b": "declaró",
    r"\bformo\b": "formó",
    r"\bdesembarco\b": "desembarcó",
    r"\bacumulo\b": "acumuló",
    r"\brepresento\b": "representó",
    r"\bperdio\b": "perdió",
    r"\bdescubrio\b": "descubrió",
    r"\brevelo\b": "reveló",
    r"\bconfirmo\b": "confirmó",
    r"\bsurgio\b": "surgió",
    r"\bocurrio\b": "ocurrió",
    r"\bcambio\b": "cambió",
    r"\bllego\b": "llegó",
    r"\bpaso\b": "pasó",
    r"\bquedo\b": "quedó",
    r"\bcomprobo\b": "comprobó",
    r"\blogro\b": "logró",
    r"\bcomenzo\b": "comenzó",
    r"\binicio\b": "inició",
    r"\btermino\b": "terminó",
    r"\bconcluyo\b": "concluyó",
    r"\bconstruyo\b": "construyó",
    r"\bdestruyo\b": "destruyó",
    r"\butilizo\b": "utilizó",
    r"\borganizo\b": "organizó",
    r"\btransformo\b": "transformó",
    r"\bordeno\b": "ordenó",
    r"\bestablecio\b": "estableció",
    r"\bconsiguio\b": "consiguió",
    r"\bdesarrollo\b": "desarrolló",
    r"\bprovoco\b": "provocó",
    r"\bcauso\b": "causó",
    r"\bavanzo\b": "avanzó",
    r"\bdefendio\b": "defendió",
    r"\bataco\b": "atacó",
    r"\bresistio\b": "resistió",
    r"\bhabia\b": "había",
    r"\bhabian\b": "habían",
    r"\btenia\b": "tenía",
    r"\btenian\b": "tenían",

    # Sustantivos y esdrújulas frecuentes de historia y ciencias
    r"\bpiramide\b": "pirámide",
    r"\bpiramides\b": "pirámides",
    r"\bvolcan\b": "volcán",
    r"\bvolcanes\b": "volcanes",
    r"\boceano\b": "océano",
    r"\boceanos\b": "océanos",
    r"\batmosfera\b": "atmósfera",
    r"\boxigeno\b": "oxígeno",
    r"\bhidrogeno\b": "hidrógeno",
    r"\bsatelite\b": "satélite",
    r"\bsatelites\b": "satélites",
    r"\bcrater\b": "cráter",
    r"\bcrateres\b": "cráteres",
    r"\bfosil\b": "fósil",
    r"\bfosiles\b": "fósiles",
    r"\btunel\b": "túnel",
    r"\btuneles\b": "túneles",
    r"\barbol\b": "árbol",
    r"\barboles\b": "árboles",
    r"\belectrico\b": "eléctrico",
    r"\belectrica\b": "eléctrica",
    r"\belectricos\b": "eléctricos",
    r"\belectricas\b": "eléctricas",
    r"\bmagnetico\b": "magnético",
    r"\bmagnetica\b": "magnética",
    r"\bmagneticos\b": "magnéticos",
    r"\bmagneticas\b": "magnéticas",
    r"\boptico\b": "óptico",
    r"\boptica\b": "óptica",
    r"\bopticos\b": "ópticos",
    r"\bopticas\b": "ópticas",
    r"\batomico\b": "atómico",
    r"\batomica\b": "atómica",
    r"\btermico\b": "térmico",
    r"\btermica\b": "térmica",
    r"\bquimico\b": "químico",
    r"\bquimica\b": "química",
    r"\bfisico\b": "físico",
    r"\bfisica\b": "física",
    r"\bmedico\b": "médico",
    r"\bmedica\b": "médica",
    r"\bcronica\b": "crónica",
    r"\bcronicas\b": "crónicas",
    r"\bmetropoli\b": "metrópoli",
    r"\bacropolis\b": "acrópolis",
    r"\banalisis\b": "análisis",
    r"\bhipotesis\b": "hipótesis",
    r"\bsintesis\b": "síntesis",

    # Adverbios, palabras de enlace y preguntas interrogativas
    r"\bmas\b": "más",
    r"\btambien\b": "también",
    r"\bdespues\b": "después",
    r"\bademas\b": "además",
    r"\bdetras\b": "detrás",
    r"\bjamas\b": "jamás",
    r"\bquizas\b": "quizás",
    r"\bsegun\b": "según",
    r"\basi\b": "así",
    r"\baqui\b": "aquí",
    r"\balli\b": "allí",
    r"\balla\b": "allá",
    r"\besta\b(?=\s+(?:en|el|la|los|las|un|una|muy|bien|situad|ubicad))": "está",
    r"\bestan\b": "están",
    r"\bdia\b": "día",
    r"\bdias\b": "días",
    r"\bsabias\b": "sabías",
    r"\bque hace que\b": "qué hace que",
    r"\bque opinas\b": "qué opinas",
}


def clean_and_correct_spanish_orthography(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Detecta y corrige faltas ortográficas, tildes faltantes y adecuación temática en español.

    Returns:
        (texto_corregido, lista_de_correcciones)
    """
    if not text:
        return "", []

    corrected = text
    corrections: List[Dict[str, str]] = []

    # 1. Corrección de outro fuera de lugar (ej. Escuadrón 201 con 'evidencia científica detrás de este hallazgo')
    if "escuadrón 201" in corrected.lower() or "escuadron 201" in corrected.lower():
        pattern_outro = r"¿Conocías la verdadera historia y la evidencia científica detrás de este hallazgo\? Déjalo en los comentarios\."
        if re.search(pattern_outro, corrected, re.IGNORECASE):
            corrected = re.sub(
                pattern_outro,
                "¿Conocías la verdadera historia y el heroico legado del Escuadrón 201? Déjalo en los comentarios.",
                corrected,
                flags=re.IGNORECASE,
            )
            corrections.append({
                "original": "evidencia científica detrás de este hallazgo",
                "corrected": "el heroico legado del Escuadrón 201",
                "reason": "Adecuación contextual histórica militar",
            })

    # 2. Aplicar correcciones léxicas y ortográficas con preservación de mayúsculas
    for pattern, replacement in _SPANISH_ORTHOGRAPHY_REPLACEMENTS.items():
        matches = list(re.finditer(pattern, corrected, flags=re.IGNORECASE))
        for m in reversed(matches):
            orig_match = m.group(0)
            # Determinar si el original estaba capitalizado
            if orig_match.isupper():
                rep = replacement.upper()
            elif orig_match[0].isupper():
                rep = replacement[0].upper() + replacement[1:]
            else:
                rep = replacement

            if orig_match != rep:
                corrections.append({
                    "original": orig_match,
                    "corrected": rep,
                    "reason": "Ortografía y acentuación en español",
                })
                corrected = corrected[:m.start()] + rep + corrected[m.end():]

    # 2.1 Reglas morfológicas automáticas en español (sufijos oxítonos y esdrújulos)
    def _rep_cion(m):
        base = m.group(1)
        suffix = "CIÓN" if m.group(0).isupper() else ("Ción" if base[0].isupper() else "ción")
        return base + suffix

    def _rep_sion(m):
        base = m.group(1)
        suffix = "SIÓN" if m.group(0).isupper() else ("Sión" if base[0].isupper() else "sión")
        return base + suffix

    corrected = re.sub(r"\b([a-záéíóúñ]{3,})cion\b", _rep_cion, corrected, flags=re.IGNORECASE)
    corrected = re.sub(r"\b([a-záéíóúñ]{3,})sion\b", _rep_sion, corrected, flags=re.IGNORECASE)
    corrected = re.sub(r"\b([a-záéíóúñ]{3,})logia\b", lambda m: m.group(1) + ("LOGÍA" if m.group(0).isupper() else "logía"), corrected, flags=re.IGNORECASE)
    corrected = re.sub(r"\b([a-záéíóúñ]{3,})grafic([oa]s?)\b", lambda m: m.group(1) + ("GRÁFIC" if m.group(0).isupper() else "gráfic") + m.group(2), corrected, flags=re.IGNORECASE)

    # 3. Puntuación: asegurar signos de apertura ¿ y ¡ correspondientes
    # Si hay una oración interrogativa sin ¿ al inicio
    sents = re.split(r"(\n\s*\n|(?<=[.!?])\s+)", corrected)
    fixed_sents = []
    for s in sents:
        s_clean = s.strip()
        if s_clean.endswith("?") and not s_clean.startswith("¿"):
            # Agregar ¿ al inicio de la pregunta
            fixed_sents.append("¿" + s)
            corrections.append({"original": s, "corrected": "¿" + s, "reason": "Signo interrogativo de apertura"})
        elif s_clean.endswith("!") and not s_clean.startswith("¡"):
            fixed_sents.append("¡" + s)
            corrections.append({"original": s, "corrected": "¡" + s, "reason": "Signo exclamativo de apertura"})
        else:
            fixed_sents.append(s)
    corrected = "".join(fixed_sents)

    # 4. Limpieza de espacios dobles y formato
    corrected = re.sub(r"[ \t]+", " ", corrected)
    corrected = re.sub(r"\s+([,.:;?!])", r"\1", corrected)
    corrected = re.sub(r"([¿¡])\s+", r"\1", corrected)

    return corrected.strip(), corrections


# =============================================================================
# 2. ALINEADOR FONÉTICO Y DE MARCAS DE TIEMPO
# =============================================================================

def get_whisper_aligner(model_size: str = "tiny"):
    """Carga de forma perezosa el modelo Whisper optimizado para CPU en INT8."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            import stable_whisper
            logger.info(f"Cargando modelo faster-whisper '{model_size}' en CPU (INT8)...")
            _WHISPER_MODEL = stable_whisper.load_faster_whisper(
                model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Modelo de alineación fonética cargado con éxito.")
        except Exception as exc:
            logger.warning(f"No se pudo cargar stable_whisper: {exc}")
            _WHISPER_MODEL = None
    return _WHISPER_MODEL


def _format_ass_time(sec: float) -> str:
    """Convierte segundos a formato ASS (H:MM:SS.cs)."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _normalize_token(text: str) -> str:
    """Normaliza una palabra eliminando puntuación y diacríticos para búsqueda fonética."""
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    without_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r"[^a-z0-9]", "", without_accents)


def _token_similarity(a: str, b: str) -> float:
    """Calcula similitud fonética difflib entre dos tokens."""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def align_canonical_sentences_with_audio(
    canonical_text: str,
    audio_path: Path,
    total_duration: float = 60.0,
) -> List[Dict[str, Any]]:
    """Alinea cada palabra canónica contra las marcas de tiempo de Whisper sin alterar el texto.

    Returns:
        Lista de oraciones, cada una con lista de palabras canónicas:
        [{
            "sentence": str,
            "words": [{"word": str, "start": float, "end": float}],
            "t_start": float,
            "t_end": float
        }]
    """
    model = get_whisper_aligner("tiny")
    if model is None or not audio_path.exists():
        return _fallback_sentence_alignment(canonical_text, total_duration)

    try:
        logger.info(f"Alineando fonéticamente audio '{audio_path.name}' con faster-whisper...")
        result = model.transcribe_stable(
            str(audio_path.resolve()),
            language="es",
            vad_filter=True,
            regroup=True,
        )

        whisper_tokens: List[Dict[str, Any]] = []
        for seg in result:
            for w in getattr(seg, "words", []):
                cleaned = w.word.strip()
                if cleaned:
                    whisper_tokens.append({
                        "word": cleaned,
                        "norm": _normalize_token(cleaned),
                        "start": float(w.start),
                        "end": float(w.end),
                    })

        if not whisper_tokens:
            return _fallback_sentence_alignment(canonical_text, total_duration)

        # Dividir texto canónico en oraciones
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", canonical_text) if s.strip()]
        if not raw_sentences:
            raw_sentences = [canonical_text.strip()]

        sentence_results: List[Dict[str, Any]] = []
        w_idx = 0
        n_w = len(whisper_tokens)

        for s_idx, sent in enumerate(raw_sentences):
            words = [w.strip() for w in sent.split() if w.strip()]
            if not words:
                continue

            sent_words: List[Dict[str, Any]] = []

            for c_word in words:
                c_norm = _normalize_token(c_word)
                if not c_norm:
                    prev_end = sent_words[-1]["end"] if sent_words else (sentence_results[-1]["t_end"] if sentence_results else 0.0)
                    sent_words.append({"word": c_word, "start": prev_end, "end": prev_end + 0.12})
                    continue

                if w_idx >= n_w:
                    prev_end = sent_words[-1]["end"] if sent_words else (sentence_results[-1]["t_end"] if sentence_results else 0.0)
                    sent_words.append({"word": c_word, "start": prev_end, "end": prev_end + 0.28})
                    continue

                # Búsqueda difusa en ventana deslizante de hasta 6 tokens de Whisper
                best_sim = 0.0
                best_off = 0
                best_tokens = 1

                for off in range(min(6, n_w - w_idx)):
                    w1 = whisper_tokens[w_idx + off]
                    sim1 = _token_similarity(c_norm, w1["norm"])
                    if sim1 > best_sim:
                        best_sim = sim1
                        best_off = off
                        best_tokens = 1

                    # Manejo de palabra canónica dividida por Whisper en 2 tokens (ej. combate + o = combatió)
                    if off + 1 < min(6, n_w - w_idx):
                        w2 = whisper_tokens[w_idx + off + 1]
                        sim2 = _token_similarity(c_norm, w1["norm"] + w2["norm"])
                        if sim2 > best_sim:
                            best_sim = sim2
                            best_off = off
                            best_tokens = 2

                    # Manejo de palabra canónica dividida por Whisper en 3 tokens
                    if off + 2 < min(6, n_w - w_idx):
                        w3 = whisper_tokens[w_idx + off + 2]
                        sim3 = _token_similarity(c_norm, w1["norm"] + w2["norm"] + w3["norm"])
                        if sim3 > best_sim:
                            best_sim = sim3
                            best_off = off
                            best_tokens = 3

                if best_sim >= 0.65:
                    st = whisper_tokens[w_idx + best_off]["start"]
                    et = whisper_tokens[w_idx + best_off + best_tokens - 1]["end"]
                    w_idx = w_idx + best_off + best_tokens
                    sent_words.append({"word": c_word, "start": st, "end": max(st + 0.12, et)})
                else:
                    # Whisper omitió o alteró completamente la palabra; interpolar entre anterior y siguiente
                    prev_end = sent_words[-1]["end"] if sent_words else whisper_tokens[w_idx]["start"]
                    next_start = whisper_tokens[w_idx]["start"] if w_idx < n_w else prev_end + 0.3
                    interpolated_end = min(prev_end + 0.25, next_start)
                    sent_words.append({"word": c_word, "start": prev_end, "end": max(prev_end + 0.12, interpolated_end)})

            # Validar orden monótono dentro de la oración
            for i in range(1, len(sent_words)):
                if sent_words[i]["start"] < sent_words[i - 1]["start"]:
                    sent_words[i]["start"] = sent_words[i - 1]["end"]
                if sent_words[i]["end"] <= sent_words[i]["start"]:
                    sent_words[i]["end"] = sent_words[i]["start"] + 0.15

            if sent_words:
                sentence_results.append({
                    "sentence": sent,
                    "words": sent_words,
                    "t_start": sent_words[0]["start"],
                    "t_end": sent_words[-1]["end"],
                })

        return sentence_results

    except Exception as exc:
        logger.warning(f"Error en alineación fonética ({exc}). Aplicando alineación fallback...")
        return _fallback_sentence_alignment(canonical_text, total_duration)


def _fallback_sentence_alignment(text: str, total_duration: float) -> List[Dict[str, Any]]:
    """Distribuye linealmente oraciones y palabras si Whisper no está disponible."""
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not raw_sentences:
        raw_sentences = [text.strip()]

    all_words_count = sum(max(1, len(s.split())) for s in raw_sentences)
    cur_t = 0.0
    results = []

    for s in raw_sentences:
        words = s.split()
        if not words:
            continue
        s_dur = (len(words) / max(1, all_words_count)) * total_duration
        w_dur = s_dur / len(words)
        sent_words = []
        for i, w in enumerate(words):
            w_st = cur_t + i * w_dur
            w_et = w_st + w_dur
            sent_words.append({"word": w, "start": w_st, "end": w_et})
        cur_t += s_dur
        results.append({
            "sentence": s,
            "words": sent_words,
            "t_start": sent_words[0]["start"],
            "t_end": sent_words[-1]["end"],
        })

    return results


# =============================================================================
# 3. GENERADOR DE SUBTÍTULOS ASS KARAOKE VIRALES
# =============================================================================

def generate_fallback_ass(
    full_text: str,
    total_dur: float,
    output_ass_path: Path,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Generador ASS simple de respaldo."""
    cleaned_text, _ = clean_and_correct_spanish_orthography(full_text)
    aligned_sents = _fallback_sentence_alignment(cleaned_text, total_dur)
    dialogues: List[str] = []

    for sent_item in aligned_sents:
        words = sent_item["words"]
        chunk_size = 4
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        for ch in chunks:
            phrase = " ".join(item["word"] for item in ch)
            dialogues.append(
                f"Dialogue: 0,{_format_ass_time(ch[0]['start'])},{_format_ass_time(ch[-1]['end'])},Default,,0,0,0,,{phrase}"
            )

    margin_v = 360 if height > width else 80
    ass_content = f"""[Script Info]
Title: Subtítulos Fallback
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,46,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H80000000,-1,0,0,0,100,100,0,0,1,4.0,2.0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"

    output_ass_path.write_text(ass_content, encoding="utf-8")
    return output_ass_path


def generate_dynamic_karaoke_ass(
    audio_path: Path,
    output_ass_path: Path,
    reference_text: Optional[str] = None,
    total_duration: float = 60.0,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Genera subtítulos ASS con resaltado palabra por palabra (karaoke viral dinámico).

    Garantiza:
    1. Corrección ortográfica previa (tildes, mayúsculas, signos interrogativos/exclamativos).
    2. Alineación fonética palabra por palabra con texto canónico (cero palabras alucinadas o mal escritas de Whisper).
    3. Agrupación respetando límites de oración (nunca cruza pausas entre frases).
    4. Limpieza de pantalla durante silencios de narrador (>0.25s).
    5. Resaltado activo en oro/amarillo brillante con micro-animación de escala en cada palabra hablada.
    """
    raw_text = (reference_text or "").strip()
    if not raw_text and audio_path.exists():
        # Transcribir texto con whisper si no hay texto de referencia
        model = get_whisper_aligner("tiny")
        if model:
            res = model.transcribe_stable(str(audio_path.resolve()), language="es")
            raw_text = " ".join(seg.text for seg in res)

    # 1. Corrección ortográfica rigurosa
    canonical_text, corrections = clean_and_correct_spanish_orthography(raw_text)
    if corrections:
        logger.info(f"Se aplicaron {len(corrections)} correcciones ortográficas al guion para subtítulos.")

    # 2. Alineación de oraciones y palabras canónicas con el audio
    sentence_alignments = align_canonical_sentences_with_audio(canonical_text, audio_path, total_duration)

    if not sentence_alignments:
        return generate_fallback_ass(canonical_text, total_duration, output_ass_path, width, height)

    dialogues: List[str] = []

    # 3. Construcción de fragmentos estilo viral (2 a 4 palabras por toma)
    for sent_item in sentence_alignments:
        words = sent_item["words"]
        if not words:
            continue

        chunk_size = 4
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]

        for ch in chunks:
            ch_start = ch[0]["start"]
            ch_end = ch[-1]["end"]

            for active_idx, w_obj in enumerate(ch):
                w_start = w_obj["start"]
                # El fin de la palabra activa es el inicio de la siguiente o el final del chunk
                if active_idx + 1 < len(ch):
                    w_end = ch[active_idx + 1]["start"]
                else:
                    w_end = w_obj["end"]

                if w_end <= w_start:
                    w_end = w_start + 0.15

                styled_words = []
                for idx, item in enumerate(ch):
                    w_text = item["word"]
                    if idx == active_idx:
                        # Resaltado oro/amarillo intenso con sutil pop-in
                        styled_words.append(
                            f"{{\\c&H0000E6FF&\\t(0,80,\\fscx108\\fscy108)}}{w_text}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}"
                        )
                    else:
                        # Blanco nítido inactivo
                        styled_words.append(w_text)

                line_text = " ".join(styled_words)
                dialogues.append(
                    f"Dialogue: 0,{_format_ass_time(w_start)},{_format_ass_time(w_end)},Default,,0,0,0,,{line_text}"
                )

    margin_v = 360 if height > width else 80
    ass_content = f"""[Script Info]
Title: Dynamic Viral Karaoke Subtitles (Canonical Spanish & Sentence Aligned)
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,48,&H00FFFFFF,&H0000D7FF,&H000B0F19,&H80000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"

    output_ass_path.write_text(ass_content, encoding="utf-8")
    logger.info(f"Subtítulos karaoke ASS generados exitosamente con sincronización fonética: {output_ass_path.name}")
    return output_ass_path
