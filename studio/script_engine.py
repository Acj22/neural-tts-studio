"""FASE 5 — SCRIPT ENGINE (Motor de Guiones Educativos Originales Cortos y Largos).

Genera guiones estructurados pedagógicamente a partir de la investigación verificada (Fase 4):
- Versión Corta (Short: 1 a 3 minutos, 7 secciones obligatorias, ritmo ágil 9:16).
- Versión Larga (Long: 5 a 10 minutos, 10 secciones obligatorias, profundidad documental 16:9).
- Adaptaciones por plataforma (YouTube Largo, YouTube Shorts, TikTok, Instagram Reels, Facebook).
- Regeneración individual de cualquier sección o párrafo sin perder cambios manuales en el resto.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

import video_pipeline

SHORT_SECTIONS_SCHEMA: list[dict[str, str]] = [
    {"key": "gancho", "title": "1. Gancho de Alto Impacto", "goal": "Captar la atención inmediata con un fenómeno físico o paradoja cotidiana real."},
    {"key": "pregunta", "title": "2. Pregunta Central", "goal": "Plantear con claridad el misterio técnico que vamos a resolver."},
    {"key": "contexto", "title": "3. Contexto Esencial", "goal": "Ubicar dónde ocurre el proceso y por qué es indispensable."},
    {"key": "explicacion_principal", "title": "4. Explicación Principal (Mecanismo)", "goal": "Explicar paso a paso cómo interactúan sus piezas clave con una analogía clara."},
    {"key": "ejemplo", "title": "5. Ejemplo en Acción", "goal": "Aterrizar el principio físico en un instante concreto que el espectador reconoce."},
    {"key": "dato_interesante", "title": "6. Dato Verificado Sorprendente", "goal": "Revelar una cifra o matiz técnico respaldado por las fuentes."},
    {"key": "conclusion", "title": "7. Conclusión y Cierre", "goal": "Sintetizar la respuesta principal en una idea memorable."},
]

LONG_SECTIONS_SCHEMA: list[dict[str, str]] = [
    {"key": "introduccion", "title": "1. Introducción Inmersiva", "goal": "Abrir con una escena concreta en acción (sin saludos genéricos) y plantear la pregunta central."},
    {"key": "contexto", "title": "2. Contexto Histórico y Funcional", "goal": "Explicar qué problema humano o físico resuelve este sistema."},
    {"key": "conceptos_fundamentales", "title": "3. Conceptos Fundamentales", "goal": "Definir con sencillez y analogías los principios físicos y componentes base."},
    {"key": "explicacion_paso_a_paso", "title": "4. Explicación Paso a Paso", "goal": "Recorrer en orden cronológico cada etapa del proceso desde la entrada hasta la salida."},
    {"key": "funcionamiento_interno", "title": "5. Funcionamiento Interno en Corte", "goal": "Profundizar en la arquitectura interna, sensores, fuerzas o reacciones invisibles a simple vista."},
    {"key": "ejemplos", "title": "6. Ejemplos Cotidianos y Casos Reales", "goal": "Ilustrar cómo se comporta el sistema bajo distintas condiciones reales de uso."},
    {"key": "comparaciones", "title": "7. Comparaciones y Desmitificación", "goal": "Contrastarlo con tecnologías alternativas y aclarar errores o mitos frecuentes."},
    {"key": "curiosidades", "title": "8. Curiosidades y Magnitudes Asombrosas", "goal": "Compartir datos cuantitativos verificados y detalles de ingeniería sorprendentes."},
    {"key": "resumen", "title": "9. Resumen Estructural", "goal": "Conectar todas las piezas vistas en un repaso mental rápido y cristalino."},
    {"key": "conclusion", "title": "10. Conclusión Reflexiva", "goal": "Cerrar con el impacto del mecanismo y una pregunta abierta para la audiencia."},
]


def estimate_speaking_duration_sec(text: str, speed: float = 1.0) -> float:
    """Calcula la duración hablada estimada en español (~2.35 palabras/seg incluyendo pausas naturales).
    La duración definitiva siempre se comprueba contra el audio WAV real sintetizado."""
    words = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    sentences = [s for s in re.split(r"[.!?…]+", text or "") if s.strip()]
    if not sentences:
        sentences = ["."]
    base_sec = (len(words) / 2.38) + (len(sentences) * 0.28)
    return round(base_sec / max(0.65, min(float(speed), 1.45)), 1)


def _build_deterministic_short_sections(research: dict[str, Any]) -> list[dict[str, Any]]:
    topic = research.get("canonical_topic") or research.get("topic") or "este sistema"
    question = research.get("main_question") or f"¿Cómo funciona realmente {topic}?"
    concepts = research.get("core_concepts") or []
    facts = research.get("verified_facts") or []
    estimates = research.get("estimates_and_approximations") or []
    nuances = research.get("contradictions_or_nuances") or []
    diag_steps = research.get("diagram_sequence") or []

    c1 = concepts[0] if len(concepts) > 0 else {"name": "Núcleo principal", "role": "inicia la transformación"}
    c2 = concepts[1] if len(concepts) > 1 else {"name": "Mecanismo intermedio", "role": "transmite la energía"}
    c3 = concepts[2] if len(concepts) > 2 else {"name": "Sistema de control", "role": "regula la salida"}
    c4 = concepts[3] if len(concepts) > 3 else {"name": "Etapa final", "role": "entrega el resultado"}

    f1 = facts[0] if len(facts) > 0 else f"El funcionamiento de {topic} depende de la sincronización exacta de sus componentes internos."
    f2 = facts[1] if len(facts) > 1 else f"Cada etapa transforma la entrada inicial sin perder precisión."
    est1 = estimates[0] if len(estimates) > 0 else "Todo este ciclo ocurre en fracciones de segundo con tolerancias milimétricas."
    n1 = nuances[0] if len(nuances) > 0 else f"Lo que parece instantáneo por fuera es en realidad una cadena secuencial de pasos físicos."

    steps_narrative = ""
    if diag_steps:
        clean_steps = [re.sub(r"^\d+\.\s*", "", s) for s in diag_steps[:5]]
        steps_narrative = " Primero observamos " + ", seguido de ".join(clean_steps[:3]).lower() + f", hasta completar {clean_steps[-1].lower()}."

    sections_text = {
        "gancho": (
            f"Cada vez que se activa {topic.lower()}, en su interior ocurre una coreografía física de alta precisión que casi nadie llega a ver."
        ),
        "pregunta": (
            f"{question} Abramos su carcasa en corte para descubrirlo paso a paso."
        ),
        "contexto": (
            f"Su funcionamiento parte de un principio esencial: {c1['name'].lower()}, que {c1['role'].lower()}"
        ),
        "explicacion_principal": (
            f"Todo sucede en tres fases sincronizadas: primero actúa {c2['name']}, después interviene {c3['name']} y finalmente {c4['name']} entrega el movimiento o resultado final. "
            f"{f1}"
        ),
        "ejemplo": (
            f"Piénsalo como una cadena de precisión donde cada eslabón impulsa al siguiente: {f2}"
        ),
        "dato_interesante": (
            f"Un dato verificado sorprendente: {est1} Además, ten en cuenta que {n1[0].lower() + n1[1:] if len(n1) > 1 else n1}"
        ),
        "conclusion": (
            f"Así es como {topic.lower()} transforma leyes físicas exactas en tecnología cotidiana. "
            f"¿Qué otro mecanismo quieres que desarmemos en el próximo video?"
        ),
    }

    out: list[dict[str, Any]] = []
    for schema in SHORT_SECTIONS_SCHEMA:
        k = schema["key"]
        txt = sections_text[k].strip()
        out.append(
            {
                "key": k,
                "title": schema["title"],
                "goal": schema["goal"],
                "text": txt,
                "estimated_duration_sec": estimate_speaking_duration_sec(txt),
            }
        )
    return out


def _build_deterministic_long_sections(research: dict[str, Any]) -> list[dict[str, Any]]:
    topic = research.get("canonical_topic") or research.get("topic") or "este sistema"
    question = research.get("main_question") or f"¿Cómo funciona exactamente {topic}?"
    concepts = research.get("core_concepts") or []
    facts = research.get("verified_facts") or []
    estimates = research.get("estimates_and_approximations") or []
    nuances = research.get("contradictions_or_nuances") or []
    needs_ver = research.get("needs_verification") or []
    diag_steps = research.get("diagram_sequence") or []

    concept_templates = [
        "El primer componente clave es {name}, encargado de {role}.",
        "A su lado trabaja {name}, cuya función fundamental consiste en {role}.",
        "Asimismo, interviene {name}, responsable directo de {role}.",
        "Por su parte, {name} actúa asegurando que {role}.",
        "Adicionalmente, {name} complementa el ciclo al {role}.",
    ]
    concept_lines = []
    for idx, c in enumerate(concepts):
        tmpl = concept_templates[idx % len(concept_templates)]
        role_txt = c["role"].strip()
        role_clean = role_txt[0].lower() + role_txt[1:] if len(role_txt) > 1 else role_txt
        concept_lines.append(tmpl.format(name=c["name"], role=role_clean))
    concepts_paragraph = " ".join(concept_lines) if concept_lines else f"Los componentes internos de {topic} colaboran bajo tolerancias estrictas."

    facts_p1 = " ".join(facts[:2]) if facts else ""
    facts_p2 = " ".join(facts[2:]) if len(facts) > 2 else (facts[0] if facts else "")

    step_templates = [
        "Para comenzar, el diagrama técnico ilustra cómo {step}.",
        "En la siguiente etapa, se aprecia que {step}.",
        "A continuación, el flujo avanza hacia {step}.",
        "Posteriormente, el mecanismo ejecuta {step}.",
        "En la fase subsecuente, observamos {step}.",
        "Cerrando la secuencia, {step}.",
    ]
    step_lines = []
    for idx, st in enumerate(diag_steps):
        clean_st = re.sub(r"^\d+\.\s*", "", st).strip()
        clean_st_low = clean_st[0].lower() + clean_st[1:] if len(clean_st) > 1 else clean_st
        tmpl = step_templates[idx % len(step_templates)]
        step_lines.append(tmpl.format(step=clean_st_low))
    steps_paragraph = " ".join(step_lines) if step_lines else "El recorrido paso a paso comienza en la etapa de captación, atraviesa el núcleo de transformación y culmina en el mecanismo de salida."

    est_paragraph = " ".join(estimates) if estimates else "Las magnitudes operativas se mantienen dentro de márgenes estrictamente controlados por el diseño."
    nuance_paragraph = " ".join(nuances) if nuances else "Es fundamental distinguir entre las simplificaciones populares y el comportamiento físico real del sistema."
    ver_note = needs_ver[0] if needs_ver else "Las cifras puntuales pueden variar según la generación tecnológica y el fabricante específico."

    sections_text = {
        "introduccion": (
            f"A simple vista, {topic.lower()} parece operar como una caja cerrada donde todo sucede de manera casi mágica e instantánea. "
            f"Sin embargo, en el mismo segundo en que entra en operación, una cadena de fenómenos físicos, mecánicos y electrónicos trabaja con una precisión asombrosa. "
            f"{question} Vamos a desmontar cada una de sus capas para observar cómo interactúan sus piezas reales."
        ),
        "contexto": (
            f"Para comprender por qué {topic.lower()} fue diseñado de esta manera, primero debemos observar el desafío técnico que resuelve. "
            f"Transformar una orden, señal o fuente de energía bruta en un resultado controlado y seguro exige superar límites de tiempo, fricción, calor o distancia. "
            f"{facts_p1}"
        ),
        "conceptos_fundamentales": (
            f"Antes de poner el mecanismo en movimiento, identifiquemos las piezas clave sobre la mesa de ingeniería. "
            f"{concepts_paragraph} "
            f"Imagina que cada uno de estos elementos actúa como un eslabón especializado: si uno solo fallara o perdiera sincronía, todo el conjunto se detendría."
        ),
        "explicacion_paso_a_paso": (
            f"Ahora sigamos la secuencia completa en orden cronológico. "
            f"{steps_paragraph} "
            f"Observa cómo cada fase prepara exactamente las condiciones físicas que necesita la etapa siguiente para activarse sin interrupciones."
        ),
        "funcionamiento_interno": (
            f"Si hacemos un corte transversal y nos acercamos todavía más al interior del sistema, descubrimos la clave de su confiabilidad. "
            f"{facts_p2} "
            f"Esta arquitectura interna garantiza que las fuerzas, señales o flujos viajen exactamente por el canal previsto y con la intensidad necesaria."
        ),
        "ejemplos": (
            f"Veamos esto aplicado en una situación cotidiana real. Cuando el sistema enfrenta una demanda repentina —como un cambio brusco de carga, una lectura en movimiento o una validación de seguridad—, "
            f"sus sensores y componentes internos reajustan su respuesta en fracciones de segundo sin que el usuario tenga que intervenir manualmente."
        ),
        "comparaciones": (
            f"Aquí es donde suelen surgir las confusiones más comunes. {nuance_paragraph} "
            f"Comprender esta diferencia técnica nos permite entender por qué el diseño actual superó a los métodos anteriores."
        ),
        "curiosidades": (
            f"Las cifras e intervalos en los que opera {topic.lower()} demuestran el nivel de ingeniería alcanzado. "
            f"{est_paragraph} "
            f"Cabe tener presente que {ver_note[0].lower() + ver_note[1:] if len(ver_note) > 1 else ver_note}"
        ),
        "resumen": (
            f"En resumen, hemos visto que {topic.lower()} integra tres grandes bloques: primero, un sistema de entrada y lectura precisa; "
            f"segundo, un núcleo de transformación gobernado por leyes físicas verificables; y tercero, un mecanismo de salida que entrega el resultado con exactitud."
        ),
        "conclusion": (
            f"La próxima vez que tengas frente a ti {topic.lower()}, sabrás exactamente qué piezas se están moviendo y qué principios científicos están trabajando en su interior. "
            f"Déjanos en los comentarios: ¿qué parte de este mecanismo te pareció más ingeniosa o qué otro sistema quieres que analicemos a fondo?"
        ),
    }

    out: list[dict[str, Any]] = []
    for schema in LONG_SECTIONS_SCHEMA:
        k = schema["key"]
        txt = sections_text[k].strip()
        out.append(
            {
                "key": k,
                "title": schema["title"],
                "goal": schema["goal"],
                "text": txt,
                "estimated_duration_sec": estimate_speaking_duration_sec(txt),
            }
        )
    return out


def _generate_sections_with_gemini_if_available(
    research: dict[str, Any],
    version_type: str = "short",
    target_duration_sec: float = 120.0,
) -> Optional[list[dict[str, Any]]]:
    """Si hay API key de Google AI Studio, redacta un guion educativo fluido y riguroso
    respetando todas las secciones obligatorias y los datos verificados de la investigación."""
    api_key = (video_pipeline.IMAGE_SETTINGS.get("gemini_api_key") or "").strip()
    if not api_key:
        return None

    schema = SHORT_SECTIONS_SCHEMA if version_type == "short" else LONG_SECTIONS_SCHEMA
    target_words = int(round(target_duration_sec * 2.35))
    schema_desc = "\n".join(f'- "{s["key"]}": {s["title"]} ({s["goal"]})' for s in schema)

    prompt = (
        "Eres el guionista principal de 'EXPLAINER AI — ¿CÓMO FUNCIONA?', un canal de divulgación científica e ingeniería de altísima calidad.\n"
        f"Tema: {research.get('canonical_topic') or research.get('topic')}\n"
        f"Pregunta principal: {research.get('main_question')}\n"
        f"Público objetivo: {research.get('target_audience')}\n"
        f"Modalidad: {'GUION CORTO (1 a 3 minutos)' if version_type == 'short' else 'GUION LARGO DOCUMENTAL (5 a 10 minutos)'} (~{target_words} palabras en total).\n\n"
        "INFORMACIÓN VERIFICADA DE LA INVESTIGACIÓN (USA SOLO ESTOS DATOS, NO INVENTES HECHOS NI PRESENTES HIPÓTESIS COMO HECHOS):\n"
        f"- Conceptos clave: {json.dumps(research.get('core_concepts', []), ensure_ascii=False)}\n"
        f"- Hechos verificados: {json.dumps(research.get('verified_facts', []), ensure_ascii=False)}\n"
        f"- Estimaciones/rangos (indicar siempre que son aproximados): {json.dumps(research.get('estimates_and_approximations', []), ensure_ascii=False)}\n"
        f"- Matices/mitos a aclarar: {json.dumps(research.get('contradictions_or_nuances', []), ensure_ascii=False)}\n"
        f"- Secuencia de diagramas: {json.dumps(research.get('diagram_sequence', []), ensure_ascii=False)}\n\n"
        "REGLAS ESTRICTAS DE REDACCIÓN:\n"
        "1. Español natural, claro, envolvente y didáctico. Usa analogías físicas útiles.\n"
        "2. PROHIBIDO usar introducciones genéricas ('Hola a todos, en el video de hoy veremos...'). Entra directo al fenómeno.\n"
        "3. No repitas ideas entre secciones.\n"
        f"4. Devuelve ÚNICAMENTE un objeto JSON cuyas claves sean exactamente las siguientes secciones y cada valor sea el texto narrado de esa sección:\n{schema_desc}"
    )

    for model_name in ("gemini-3.1-flash-lite-preview", "gemini-3-flash-preview", "gemma-4-31b-it"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            r = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.35},
                },
                timeout=30,
            )
            if r.status_code != 200:
                continue
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.DOTALL).strip()
            parsed = json.loads(txt)
            if isinstance(parsed, dict) and all(s["key"] in parsed for s in schema):
                out = []
                for s in schema:
                    sec_txt = str(parsed[s["key"]]).strip()
                    out.append(
                        {
                            "key": s["key"],
                            "title": s["title"],
                            "goal": s["goal"],
                            "text": sec_txt,
                            "estimated_duration_sec": estimate_speaking_duration_sec(sec_txt),
                        }
                    )
                return out
        except Exception:
            continue
    return None


def build_platform_script_adaptations(
    short_sections: list[dict[str, Any]],
    long_sections: list[dict[str, Any]],
    research: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Genera variaciones del guion adaptadas al ritmo y lenguaje de cada plataforma (Fase 11)
    conservando el 100% de exactitud técnica de la investigación original."""
    topic = research.get("canonical_topic") or research.get("topic") or "este sistema"
    short_map = {s["key"]: s["text"] for s in short_sections}
    long_full = "\n\n".join(s["text"] for s in long_sections)
    short_full = "\n\n".join(s["text"] for s in short_sections)

    tiktok_text = "\n\n".join(
        [
            f"¿Alguna vez te preguntaste qué pasa exactamente dentro de {topic.lower()} en el instante en que se activa?",
            short_map.get("explicacion_principal", ""),
            short_map.get("dato_interesante", ""),
            "Guarda este video si te gusta la ingeniería explicada paso a paso y dime en comentarios qué desarmamos después.",
        ]
    ).strip()

    ig_reels_text = "\n\n".join(
        [
            short_map.get("gancho", ""),
            short_map.get("contexto", ""),
            short_map.get("explicacion_principal", ""),
            short_map.get("ejemplo", ""),
            "Comparte este diagrama con alguien curioso y guárdalo para consultarlo cuando quieras.",
        ]
    ).strip()

    fb_reels_text = "\n\n".join(
        [
            short_map.get("gancho", ""),
            short_map.get("pregunta", ""),
            short_map.get("explicacion_principal", ""),
            short_map.get("dato_interesante", ""),
            short_map.get("conclusion", ""),
        ]
    ).strip()

    return {
        "youtube_video": {
            "platform_id": "youtube_video",
            "version_source": "long",
            "adaptation_note": "Explicación documental completa de 10 secciones con desarrollo profundo, ejemplos y comparaciones.",
            "full_script": long_full,
            "estimated_duration_sec": estimate_speaking_duration_sec(long_full),
        },
        "youtube_shorts": {
            "platform_id": "youtube_shorts",
            "version_source": "short",
            "adaptation_note": "Estructura condensada de 7 bloques con gancho inmediato y cierre directo para Shorts (< 3 min).",
            "full_script": short_full,
            "estimated_duration_sec": estimate_speaking_duration_sec(short_full),
        },
        "tiktok": {
            "platform_id": "tiktok",
            "version_source": "short",
            "adaptation_note": "Introducción directa en el segundo 0, ritmo ágil centrado en el mecanismo y llamada a guardar/comentar.",
            "full_script": tiktok_text,
            "estimated_duration_sec": estimate_speaking_duration_sec(tiktok_text),
        },
        "instagram_reels": {
            "platform_id": "instagram_reels",
            "version_source": "short",
            "adaptation_note": "Explicación visual y concisa orientada a retención y guardados en Reels.",
            "full_script": ig_reels_text,
            "estimated_duration_sec": estimate_speaking_duration_sec(ig_reels_text),
        },
        "facebook_reels": {
            "platform_id": "facebook_reels",
            "version_source": "short",
            "adaptation_note": "Versión vertical clara con contexto cotidiano y pregunta final para abrir conversación.",
            "full_script": fb_reels_text,
            "estimated_duration_sec": estimate_speaking_duration_sec(fb_reels_text),
        },
        "facebook_video": {
            "platform_id": "facebook_video",
            "version_source": "long",
            "adaptation_note": "Desarrollo amplio con contexto completo ideal para reproducción en feed de Facebook.",
            "full_script": long_full,
            "estimated_duration_sec": estimate_speaking_duration_sec(long_full),
        },
    }


def generate_educational_scripts(
    research: dict[str, Any],
    duration_mode: str = "both",
    speed: float = 1.0,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Genera los guiones educativos corto (1-3 min) y largo (5-10 min) desde la misma investigación,
    adaptando estructura, ritmo y profundidad sin recortar mecánicamente el guion largo."""
    short_sections = (
        (_generate_sections_with_gemini_if_available(research, version_type="short", target_duration_sec=110.0) if use_llm else None)
        or _build_deterministic_short_sections(research)
    )
    long_sections = (
        (_generate_sections_with_gemini_if_available(research, version_type="long", target_duration_sec=330.0) if use_llm else None)
        or _build_deterministic_long_sections(research)
    )

    for s in short_sections:
        s["estimated_duration_sec"] = estimate_speaking_duration_sec(s["text"], speed=speed)
    for s in long_sections:
        s["estimated_duration_sec"] = estimate_speaking_duration_sec(s["text"], speed=speed)

    short_full_text = "\n\n".join(s["text"] for s in short_sections)
    long_full_text = "\n\n".join(s["text"] for s in long_sections)

    adaptations = build_platform_script_adaptations(short_sections, long_sections, research)

    return {
        "duration_mode": duration_mode,
        "short": {
            "version": "short",
            "label": "Versión Corta (Short / Reels / TikTok · 1 a 3 min)",
            "target_range_sec": [60, 180],
            "sections": short_sections,
            "full_text": short_full_text,
            "word_count": len(short_full_text.split()),
            "estimated_duration_sec": estimate_speaking_duration_sec(short_full_text, speed=speed),
            "real_audio_duration_sec": None,
        },
        "long": {
            "version": "long",
            "label": "Versión Larga Documental (YouTube / Facebook · 5 a 10 min)",
            "target_range_sec": [300, 600],
            "sections": long_sections,
            "full_text": long_full_text,
            "word_count": len(long_full_text.split()),
            "estimated_duration_sec": estimate_speaking_duration_sec(long_full_text, speed=speed),
            "real_audio_duration_sec": None,
        },
        "platform_adaptations": adaptations,
    }


def regenerate_single_script_section(
    scripts_bundle: dict[str, Any],
    research: dict[str, Any],
    version: str,
    section_key: str,
    custom_instruction: str = "",
    speed: float = 1.0,
) -> dict[str, Any]:
    """Regenera o ajusta únicamente una sección específica del guion corto o largo
    conservando intactas todas las demás secciones editadas por el usuario."""
    target_branch = scripts_bundle.get(version)
    if not target_branch:
        return scripts_bundle

    sections = target_branch.get("sections", [])
    target_sec = next((s for s in sections if s["key"] == section_key), None)
    if not target_sec:
        return scripts_bundle

    api_key = (video_pipeline.IMAGE_SETTINGS.get("gemini_api_key") or "").strip()
    new_text: Optional[str] = None

    if api_key:
        prompt = (
            f"Reescribe únicamente la sección '{target_sec['title']}' ({target_sec['goal']}) "
            f"del guion educativo sobre '{research.get('canonical_topic') or research.get('topic')}'.\n"
            f"Texto actual: {target_sec['text']}\n"
            f"Instrucción adicional: {custom_instruction or 'Hazlo aún más claro, didáctico y atractivo usando otra analogía verificable.'}\n"
            f"Hechos verificados: {json.dumps(research.get('verified_facts', []), ensure_ascii=False)}\n"
            "Devuelve SOLO el nuevo párrafo en español natural, sin comillas ni encabezados."
        )
        for model_name in ("gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
                if r.status_code == 200:
                    cand = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if len(cand) > 25:
                        new_text = cand
                        break
            except Exception:
                continue

    if not new_text:
        # Alternativa determinista enriquecida con otro enfoque pedagógico de la investigación
        facts = research.get("verified_facts") or []
        extra_fact = facts[len(target_sec["text"]) % len(facts)] if facts else ""
        if custom_instruction.strip():
            new_text = f"{target_sec['text']} ({custom_instruction.strip()}). {extra_fact}".strip()
        else:
            new_text = f"Observemos este punto desde otra perspectiva física: {target_sec['text']} {extra_fact}".strip()

    target_sec["text"] = new_text
    target_sec["estimated_duration_sec"] = estimate_speaking_duration_sec(new_text, speed=speed)

    full_text = "\n\n".join(s["text"] for s in sections)
    target_branch["full_text"] = full_text
    target_branch["word_count"] = len(full_text.split())
    target_branch["estimated_duration_sec"] = estimate_speaking_duration_sec(full_text, speed=speed)

    scripts_bundle["platform_adaptations"] = build_platform_script_adaptations(
        scripts_bundle["short"]["sections"],
        scripts_bundle["long"]["sections"],
        research,
    )
    return scripts_bundle
