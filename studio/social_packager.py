"""FASE 12 — SOCIAL MEDIA PACKAGER (Empaquetador de Publicación Multiplataforma).

Al terminar o exportar un proyecto, genera para cada plataforma seleccionada:
- Portada / Miniatura personalizada (1280x720 para YouTube/Facebook horizontal y 1080x1920 para Shorts/Reels/TikTok)
  manteniendo la identidad gráfica del canal EXPLAINER AI — ¿CÓMO FUNCIONA?.
- Título optimizado por red social.
- Descripción única adaptada (nunca idéntica entre plataformas).
- Hashtags específicos del tema y categoría (sin etiquetas genéricas vacías).
- Texto de publicación (post copy).
- Pregunta para incentivar comentarios.
- Categoría y ruta de subtítulos .SRT / .ASS.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFilter

import video_pipeline
from studio.diagram_engine import _hex_to_rgb, render_animated_diagram_frame
from studio.models import CATEGORIES_CATALOG, VISUAL_CONSISTENCY_STYLES, load_platform_profiles


def generate_platform_cover_image(
    project_dir: Path,
    platform_id: str,
    topic: str,
    main_question: str,
    visual_style_key: str,
    sample_scene: dict[str, Any],
    custom_title: Optional[str] = None,
) -> Path:
    """Genera la portada / miniatura personalizada en las dimensiones oficiales recomendadas
    para la plataforma (1280x720 en 16:9 o 1080x1920 en 9:16) con la identidad de EXPLAINER AI."""
    profiles = load_platform_profiles()
    profile = profiles.get(platform_id) or profiles["youtube_video"]
    thumb_w, thumb_h = profile.get("thumbnail_size", [1280, 720])

    style = VISUAL_CONSISTENCY_STYLES.get(visual_style_key) or VISUAL_CONSISTENCY_STYLES["3d_educational"]
    pal = style["palette"]
    accent_rgb = _hex_to_rgb(pal["accent_primary"], (56, 189, 248))
    warn_rgb = _hex_to_rgb(pal["accent_secondary"], (245, 158, 11))

    # Renderizar base visual con el motor de diagramas o primera imagen generada
    base_img: Optional[Image.Image] = None
    first_img_path = project_dir / "images" / f"{sample_scene.get('scene_id', 'S01')}.png"
    if first_img_path.exists():
        try:
            base_img = Image.open(first_img_path).convert("RGB")
        except Exception:
            base_img = None

    canvas = render_animated_diagram_frame(
        scene=sample_scene,
        progress=0.55,
        width=thumb_w,
        height=thumb_h,
        visual_style_key=visual_style_key,
        base_illustration=base_img,
    )

    # Añadir banda de alto contraste para el título de portada
    overlay = Image.new("RGBA", (thumb_w, thumb_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    is_vertical = thumb_h > thumb_w
    banner_h = int(thumb_h * (0.28 if is_vertical else 0.34))
    banner_y = int(thumb_h * (0.64 if is_vertical else 0.62))
    draw.rectangle([0, banner_y, thumb_w, banner_y + banner_h], fill=(7, 11, 22, 232))
    draw.line([(0, banner_y), (thumb_w, banner_y)], fill=(*accent_rgb, 255), width=5)

    font_tag = video_pipeline._load_ui_font(max(20, int(thumb_w * (0.028 if is_vertical else 0.020))), bold=True)
    font_main = video_pipeline._load_ui_font(max(30, int(thumb_w * (0.052 if is_vertical else 0.042))), bold=True)

    draw.rounded_rectangle([44, banner_y + 18, 420, banner_y + 60], radius=8, fill=(*warn_rgb, 255))
    draw.text((62, banner_y + 25), "EXPLAINER AI · ¿CÓMO FUNCIONA?", font=font_tag, fill=(10, 15, 28, 255))

    headline = (custom_title or topic or main_question).upper()
    wrapped = textwrap.wrap(headline, width=22 if is_vertical else 28)[:2]
    curr_y = banner_y + 74
    for line in wrapped:
        draw.text((46, curr_y), line, font=font_main, fill=(255, 255, 255, 255))
        curr_y += int(thumb_h * (0.048 if is_vertical else 0.072))

    final_cover = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    exports_dir = project_dir / "exports" / platform_id
    exports_dir.mkdir(parents=True, exist_ok=True)
    cover_path = exports_dir / f"portada_{platform_id}.png"
    final_cover.save(cover_path, format="PNG")
    return cover_path


def _build_specific_hashtags(topic: str, category_id: str) -> list[str]:
    words = [re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]", "", w) for w in topic.split() if len(w) > 3]
    topic_tag = "#" + "".join(w.capitalize() for w in words[:3]) if words else "#ComoFunciona"
    cat_tags_map = {
        "ciencia": ["#CienciaExplicada", "#FisicaCotidiana", "#DivulgacionCientifica"],
        "tecnologia": ["#TecnologiaExplicada", "#IngenieriaModerna", "#ComoFunciona"],
        "ingenieria": ["#Ingenieria", "#MecanicaExplicada", "#DisenoIndustrial"],
        "automoviles": ["#MecanicaAutomotriz", "#IngenieriaAutomotriz", "#Motores"],
        "electronica": ["#Electronica", "#HardwareExplicado", "#Sensores"],
        "informatica": ["#Informatica", "#SistemasDigitales", "#ArquitecturaDeComputadoras"],
        "espacio": ["#CienciaEspacial", "#Satelites", "#OrbitaTerrestre"],
        "economia_cotidiana": ["#TecnologiaFinanciera", "#SeguridadBancaria", "#IngenieriaCotidiana"],
        "objetos_mecanismos": ["#Mecanismos", "#MaquinasPorDentro", "#CorteTecnico"],
    }
    specific = cat_tags_map.get(category_id, ["#IngenieriaExplicada", "#CienciaAplicada", "#ComoFuncionaPorDentro"])
    return [topic_tag, "#ComoFunciona", *specific]


def build_social_media_package_for_platform(
    project_id: str,
    project_dir: Path,
    platform_id: str,
    research: dict[str, Any],
    scenes: list[dict[str, Any]],
    visual_style_key: str = "3d_educational",
    video_rel_url: Optional[str] = None,
    srt_rel_url: Optional[str] = None,
) -> dict[str, Any]:
    """Construye el paquete de publicación completo y diferenciado para una plataforma (Fase 12)."""
    topic = research.get("canonical_topic") or research.get("topic") or "Mecanismo Técnico"
    question = research.get("main_question") or f"¿Cómo funciona exactamente {topic}?"
    cat_id = research.get("category", "ingenieria")
    cat_obj = next((c for c in CATEGORIES_CATALOG if c["id"] == cat_id), CATEGORIES_CATALOG[0])
    sources = research.get("sources") or []
    facts = research.get("verified_facts") or []
    lead_fact = facts[0] if facts else f"Descubre paso a paso la arquitectura interna de {topic}."

    hashtags = _build_specific_hashtags(topic, cat_id)
    sample_scene = scenes[min(1, len(scenes) - 1)] if scenes else {"scene_id": "S01", "concept_explained": topic, "labels": ["1. Entrada", "2. Núcleo", "3. Control", "4. Salida"]}

    # Títulos, descripciones y textos diferenciados por red social (nunca idénticos)
    if platform_id == "youtube_video":
        title = f"¿Cómo Funciona {topic} por Dentro? (Explicación Técnica Paso a Paso)"
        sources_txt = "\n".join(f"• {s['title']}: {s['url']}" for s in sources[:4]) or "• Documentación técnica del proyecto"
        chapters_txt = "\n".join(
            f"{video_pipeline.format_mm_ss(sc.get('start_sec', 0.0))[:5]} {sc.get('concept_explained', sc.get('section_title', 'Escena'))}"
            for sc in scenes[:10]
        )
        description = (
            f"{question}\n\n"
            f"En este episodio de EXPLAINER AI abrimos en corte {topic.lower()} para analizar sus componentes reales, "
            f"su secuencia física de operación y los principios de ingeniería que lo hacen funcionar.\n\n"
            f"📌 DATO CLAVE VERIFICADO:\n{lead_fact}\n\n"
            f"⏱️ SECUENCIA TÉCNICA DEL VIDEO:\n{chapters_txt}\n\n"
            f"📚 FUENTES Y RESPALDO DOCUMENTAL:\n{sources_txt}\n\n"
            f"{' '.join(hashtags)}"
        )
        post_text = f"Nuevo análisis técnico en corte: desarmamos {topic.lower()} pieza por pieza para entender cómo funciona realmente."
        comment_q = f"¿Cuál de las etapas internas de {topic.lower()} te pareció más ingeniosa o qué mecanismo quieres que abramos en corte en el siguiente video?"

    elif platform_id == "youtube_shorts":
        title = f"Así funciona {topic} por dentro ⚙️🔍 #Shorts"
        description = (
            f"{question}\n"
            f"Resumen visual en corte técnico de {topic.lower()}: {lead_fact}\n\n"
            f"Mira la versión documental larga en nuestro canal para ver todos los diagramas paso a paso.\n"
            f"{' '.join(hashtags)}"
        )
        post_text = f"En menos de 2 minutos: lo que ocurre dentro de {topic.lower()} cada vez que entra en acción."
        comment_q = f"¿Conocías esta pieza clave dentro de {topic.lower()}? Déjalo en los comentarios 👇"

    elif platform_id == "tiktok":
        title = f"Lo que pasa dentro de {topic.lower()} en 1 segundo ⚡"
        description = (
            f"{question} Explicado con diagramas en corte paso a paso. "
            f"{lead_fact[:160]} {' '.join(hashtags)}"
        )
        post_text = f"Guarda este diagrama técnico de {topic.lower()} para cuando alguien te pregunte cómo funciona realmente."
        comment_q = "¿Qué otro objeto o máquina cotidiana desarmamos en el próximo video?"

    elif platform_id == "instagram_reels":
        title = f"Anatomía interna: ¿Cómo funciona {topic}?"
        description = (
            f"{question}\n\n"
            f"Deslizamos dentro de su estructura para ver cómo interactúan sus piezas clave:\n"
            f"🔹 {lead_fact}\n\n"
            f"📌 Guarda este Reel en tu colección de ingeniería y compártelo con alguien curioso.\n\n"
            f"{' '.join(hashtags)}"
        )
        post_text = f"Ingeniería visual paso a paso: así trabaja {topic.lower()} por dentro."
        comment_q = "¿Sabías cómo se sincronizan estas piezas? Cuéntanos en comentarios qué mecanismo te gustaría ver."

    elif platform_id == "facebook_reels":
        title = f"¿Cómo funciona realmente {topic} por dentro?"
        description = (
            f"{question} Aunque lo vemos todos los días, en su interior opera un mecanismo fascinante: {lead_fact}\n\n"
            f"{' '.join(hashtags)}"
        )
        post_text = f"Así se ve en corte técnico el funcionamiento interno de {topic.lower()}."
        comment_q = "¿Ya conocías cómo funciona este sistema por dentro o te sorprendió algún paso?"

    else:  # facebook_video
        title = f"Explicación Completa: ¿Cómo Funciona {topic} Paso a Paso?"
        description = (
            f"{question}\n\n"
            f"Acompáñanos a recorrer el interior de {topic.lower()} con diagramas animados e ilustraciones en corte.\n"
            f"Dato técnico: {lead_fact}\n\n"
            f"{' '.join(hashtags)}"
        )
        post_text = f"Video educativo completo: analizamos a fondo cada componente interno de {topic.lower()}."
        comment_q = "¿Qué parte de la explicación te resultó más interesante? Comparte tu opinión abajo."

    cover_path = generate_platform_cover_image(
        project_dir=project_dir,
        platform_id=platform_id,
        topic=topic,
        main_question=question,
        visual_style_key=visual_style_key,
        sample_scene=sample_scene,
        custom_title=topic,
    )
    ts = int(cover_path.stat().st_mtime) if cover_path.exists() else 1

    return {
        "platform_id": platform_id,
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "post_text": post_text,
        "comment_question": comment_q,
        "category": cat_obj["name"],
        "cover_url": f"/projects/{project_id}/exports/{platform_id}/portada_{platform_id}.png?t={ts}",
        "video_url": video_rel_url,
        "srt_url": srt_rel_url,
    }
