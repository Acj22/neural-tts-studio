"""Modelos de datos, catálogos, perfiles de plataformas, control de costos
e interfaz de publicación futura para AI VIDEO STUDIO (Módulo: EXPLAINER AI).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field

STUDIO_DIR = Path(__file__).resolve().parent
PROFILES_JSON_PATH = STUDIO_DIR / "platform_profiles.json"

# ==============================================================================
# 1. CATEGORÍAS OFICIALES DE EXPLAINER AI (FASE 3)
# ==============================================================================

CATEGORIES_CATALOG: list[dict[str, str]] = [
    {"id": "ciencia", "name": "🔬 Ciencia", "focus": "Principios físicos, químicos y biológicos verificables"},
    {"id": "tecnologia", "name": "💻 Tecnología", "focus": "Sistemas modernos, sensores, telecomunicaciones y dispositivos"},
    {"id": "ingenieria", "name": "⚙️ Ingeniería", "focus": "Diseño estructural, termodinámica, materiales y sistemas"},
    {"id": "automoviles", "name": "🚗 Automóviles", "focus": "Motores, transmisiones, frenos, suspensión y propulsión"},
    {"id": "electronica", "name": "🔌 Electrónica", "focus": "Circuitos, semiconductores, pantallas, baterías y señales"},
    {"id": "informatica", "name": "🖥️ Informática", "focus": "Algoritmos, redes, criptografía, hardware y software"},
    {"id": "naturaleza", "name": "🌿 Naturaleza", "focus": "Fenómenos naturales, ecosistemas, geología y biología"},
    {"id": "espacio", "name": "🚀 Espacio", "focus": "Órbitas, satélites, astrofísica y exploración espacial"},
    {"id": "economia_cotidiana", "name": "💳 Economía cotidiana", "focus": "Cajeros, pagos digitales, logística e infraestructura financiera"},
    {"id": "objetos_mecanismos", "name": "🔧 Objetos y mecanismos", "focus": "Engranajes, cerraduras, válvulas, bombas y máquinas cotidianas"},
    {"id": "procesos_industriales", "name": "🏭 Procesos industriales", "focus": "Manufactura, refinación, ensamblaje y automatización"},
    {"id": "cultura_general", "name": "🌍 Cultura general", "focus": "Historia de los inventos, infraestructura e impacto humano"},
]

# ==============================================================================
# 2. MOTOR DE CONSISTENCIA VISUAL — 5 ESTILOS EDUCATIVOS (FASE 8)
# ==============================================================================

VISUAL_CONSISTENCY_STYLES: dict[str, dict[str, Any]] = {
    "3d_educational": {
        "id": "3d_educational",
        "name": "🧊 Realismo 3D Educativo (Corte Técnico / Blender Studio ★)",
        "prompt_prefix": (
            "Educational 3D technical render style like Jared Owen and Animagraffs, clean studio global illumination, "
            "precision engineered 3D model on a dark slate blueprint background, color-coded internal components, "
            "orthographic three-quarter camera angle, crisp edges, ultra-clear mechanical proportions, no text, no watermark"
        ),
        "palette": {
            "bg_primary": "#0B1120",
            "bg_secondary": "#1E293B",
            "accent_primary": "#38BDF8",
            "accent_secondary": "#F59E0B",
            "highlight": "#22C55E",
            "danger": "#EF4444",
            "text": "#F8FAFC",
            "muted": "#94A3B8",
        },
        "orientation_rule": "Consistent 3/4 isometric or side cutaway perspective facing left-to-right flow",
        "lighting_rule": "Three-point soft studio lighting with cool cyan rim light and warm amber functional highlights",
    },
    "modern_infographic": {
        "id": "modern_infographic",
        "name": "📊 Infografía Moderna Vectorial (Estilo Kurzgesagt / Flat Design ★)",
        "prompt_prefix": (
            "Modern flat vector educational illustration style like Kurzgesagt, clean geometric shapes, "
            "vibrant high-contrast color blocks on deep navy background, clear visual hierarchy, "
            "minimalist uncluttered composition, no text, no letters, no watermark"
        ),
        "palette": {
            "bg_primary": "#0F172A",
            "bg_secondary": "#1E1B4B",
            "accent_primary": "#FACC15",
            "accent_secondary": "#38BDF8",
            "highlight": "#A855F7",
            "danger": "#F43F5E",
            "text": "#FFFFFF",
            "muted": "#CBD5E1",
        },
        "orientation_rule": "Flat frontal 2D orthographic view with centered primary subject and symmetrical balance",
        "lighting_rule": "Flat luminous vector shading with subtle ambient glow around active components",
    },
    "scientific_illustration": {
        "id": "scientific_illustration",
        "name": "🔬 Ilustración Científica de Precisión (Enciclopedia / NatGeo)",
        "prompt_prefix": (
            "Detailed scientific and anatomical textbook cutaway illustration, National Geographic technical plate style, "
            "precise cross-section detail, realistic material textures, clean neutral dark laboratory backdrop, "
            "sharp focus across the entire mechanism, no text, no watermark"
        ),
        "palette": {
            "bg_primary": "#090D16",
            "bg_secondary": "#172033",
            "accent_primary": "#10B981",
            "accent_secondary": "#60A5FA",
            "highlight": "#FBBF24",
            "danger": "#F87171",
            "text": "#F1F5F9",
            "muted": "#94A3B8",
        },
        "orientation_rule": "Cross-sectional sagittal or lateral cutaway showing internal layers clearly",
        "lighting_rule": "Neutral high-CRI scientific illumination revealing internal surface textures",
    },
    "explanatory_photo": {
        "id": "explanatory_photo",
        "name": "📸 Fotografía Explicativa Macro 8K (Documental Realista)",
        "prompt_prefix": (
            "High-resolution macro explanatory documentary photography, 8k photorealistic detail, "
            "clear view of physical mechanism and components in action, controlled studio lighting, "
            "natural colors, uncluttered background, no text, no watermark"
        ),
        "palette": {
            "bg_primary": "#0C121E",
            "bg_secondary": "#1A2436",
            "accent_primary": "#F59E0B",
            "accent_secondary": "#38BDF8",
            "highlight": "#34D399",
            "danger": "#EF4444",
            "text": "#F8FAFC",
            "muted": "#94A3B8",
        },
        "orientation_rule": "Eye-level macro lens framing focused directly on the active component",
        "lighting_rule": "Naturalistic cinematic key light with crisp specular highlights on metal and glass",
    },
    "technical_animation": {
        "id": "technical_animation",
        "name": "📐 Animación Técnica Blueprint CAD (Ingeniería / Esquema Luminoso)",
        "prompt_prefix": (
            "Technical CAD engineering blueprint schematic with glowing cyan and amber wireframe and solid cutaway layers, "
            "precision mechanical drafting aesthetic on dark Prussian blue grid background, ultra sharp lines, "
            "no written text, no watermark"
        ),
        "palette": {
            "bg_primary": "#071324",
            "bg_secondary": "#0E223D",
            "accent_primary": "#00E5FF",
            "accent_secondary": "#FFB300",
            "highlight": "#69F0AE",
            "danger": "#FF5252",
            "text": "#E0F7FA",
            "muted": "#80DEEA",
        },
        "orientation_rule": "Strict engineering schematic alignment with left-to-right signal/mechanical flow",
        "lighting_rule": "High-contrast self-illuminated CAD schematic lines over dark blueprint grid",
    },
}

# ==============================================================================
# 3. COMPOSICIONES CINEMÁTICAS (6 PLANOS) Y TIPOS DE RECURSO (FASE 6 Y FASE 7)
# ==============================================================================

COMPOSITION_TYPES: dict[str, dict[str, Any]] = {
    "hero_view": {
        "id": "hero_view",
        "name": "HERO VIEW (Vista General de Impacto)",
        "desc": "Vista imponente completa del mecanismo ocupando el 75-80% del ancho con halo tecnológico.",
        "scale_9_16": 2.15,
        "scale_16_9": 1.45,
    },
    "close_up_view": {
        "id": "close_up_view",
        "name": "CLOSE-UP VIEW (Acercamiento Macro Detallado)",
        "desc": "Zoom macro 3.5x en el componente clave (bujía, anillos de pistón, cigüeñal) con foco focal.",
        "scale_9_16": 3.40,
        "scale_16_9": 2.25,
    },
    "cutaway_view": {
        "id": "cutaway_view",
        "name": "CUTAWAY VIEW (Vista de Corte Transversal)",
        "desc": "Corte transparente donde se aprecia el interior mecánico iluminado e interactuando en tiempo real.",
        "scale_9_16": 2.50,
        "scale_16_9": 1.65,
    },
    "process_view": {
        "id": "process_view",
        "name": "PROCESS VIEW (Flujo Cinemático de Proceso)",
        "desc": "Representación dinámica del ciclo (admisión de mezcla, compresión, combustión y barrido de escape).",
        "scale_9_16": 2.45,
        "scale_16_9": 1.60,
    },
    "comparison_view": {
        "id": "comparison_view",
        "name": "COMPARISON VIEW (Comparación Técnica Directa)",
        "desc": "División de pantalla o contraste de estados/sistemas con indicadores técnicos comparativos.",
        "scale_9_16": 1.70,
        "scale_16_9": 1.25,
    },
    "infographic_view": {
        "id": "infographic_view",
        "name": "INFOGRAPHIC VIEW (Datos, Magnitudes e Indicadores)",
        "desc": "Tarjetas flotantes de alto contraste con indicadores de presión, relación de compresión y temperatura.",
        "scale_9_16": 1.95,
        "scale_16_9": 1.35,
    },
}

SCENE_RESOURCE_TYPES: dict[str, dict[str, str]] = {
    "illustrative_image": {
        "id": "illustrative_image",
        "icon": "🖼️",
        "name": "1. Imagen Ilustrativa con Movimiento",
        "default_mode": "mode_a_image",
        "desc": "Escena contextual o física con cámara viva (Zoom/Pan/Parallax/Enfoque).",
    },
    "technical_diagram": {
        "id": "technical_diagram",
        "icon": "📐",
        "name": "2. Diagrama Técnico Etiquetado",
        "default_mode": "mode_b_diagram",
        "desc": "Esquema SVG animado con flechas, numeración y componentes identificados.",
    },
    "comparison": {
        "id": "comparison",
        "icon": "⚖️",
        "name": "3. Comparación Lado a Lado",
        "default_mode": "mode_b_diagram",
        "desc": "Contraste visual directo entre dos estados, tecnologías o magnitudes.",
    },
    "step_by_step": {
        "id": "step_by_step",
        "icon": "🔢",
        "name": "4. Proceso Paso a Paso",
        "default_mode": "mode_b_diagram",
        "desc": "Secuencia numerada progresiva con flujo direccional animado.",
    },
    "cutaway_view": {
        "id": "cutaway_view",
        "icon": "🔍",
        "name": "5. Vista de Corte (Sección Interna)",
        "default_mode": "mode_b_diagram",
        "desc": "Interior del mecanismo mostrando cómo interactúan sus piezas internas.",
    },
    "microscopic_view": {
        "id": "microscopic_view",
        "icon": "🧬",
        "name": "6. Vista Microscópica / Atómica",
        "default_mode": "mode_b_diagram",
        "desc": "Acercamiento a electrones, sensores, células o capas sub-milimétricas.",
    },
    "map_view": {
        "id": "map_view",
        "icon": "🗺️",
        "name": "7. Mapa / Red Geoespacial",
        "default_mode": "mode_b_diagram",
        "desc": "Nodos orbitales, triangulación por satélite, redes o rutas geográficas.",
    },
    "data_chart": {
        "id": "data_chart",
        "icon": "📈",
        "name": "8. Gráfico de Datos / Magnitudes",
        "default_mode": "mode_b_diagram",
        "desc": "Visualización cuantitativa clara de velocidades, presiones, tiempos o porcentajes.",
    },
    "component_animation": {
        "id": "component_animation",
        "icon": "⚙️",
        "name": "9. Animación Dinámica de Componentes",
        "default_mode": "mode_b_diagram",
        "desc": "Movimiento cíclico sincronizado de piezas (pistón, engranajes, válvulas, ondas).",
    },
    "ai_video": {
        "id": "ai_video",
        "icon": "🎬",
        "name": "10. Video Generado por IA (Opcional)",
        "default_mode": "mode_c_video",
        "desc": "Clip generativo mediante proveedor externo de video IA (con control de costo).",
    },
}

# ==============================================================================
# 4. PERFILES MULTI-PLATAFORMA CONFIGURABLES Y VERIFICABLES (FASE 11)
# ==============================================================================

DEFAULT_PLATFORM_PROFILES: dict[str, dict[str, Any]] = {
    "youtube_video": {
        "id": "youtube_video",
        "name": "📺 YouTube Video (Horizontal Largo)",
        "platform": "YouTube",
        "version_source": "long",
        "aspect_ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "recommended_min_sec": 300,
        "recommended_max_sec": 600,
        "platform_max_sec_configurable": 43200,
        "safe_zone": {
            "top_pct": 0.06,
            "bottom_pct": 0.12,
            "left_pct": 0.05,
            "right_pct": 0.05,
            "diagram_box": [0.06, 0.07, 0.94, 0.78],
            "subtitle_margin_v_pct": 0.085,
        },
        "thumbnail_size": [1280, 720],
        "script_tone": "Explicación profunda, estructurada paso a paso, con ejemplos comparativos y curiosidades técnicas.",
        "spec_notes": "Resolución Full HD 1920x1080 (16:9), H.264 High Profile, AAC 256kbps, miniatura 1280x720.",
    },
    "youtube_shorts": {
        "id": "youtube_shorts",
        "name": "📱 YouTube Shorts (Vertical 9:16)",
        "platform": "YouTube Shorts",
        "version_source": "short",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "recommended_min_sec": 45,
        "recommended_max_sec": 175,
        "platform_max_sec_configurable": 180,
        "safe_zone": {
            "top_pct": 0.12,
            "bottom_pct": 0.24,
            "left_pct": 0.06,
            "right_pct": 0.14,
            "diagram_box": [0.06, 0.13, 0.88, 0.64],
            "subtitle_margin_v_pct": 0.23,
        },
        "thumbnail_size": [1080, 1920],
        "script_tone": "Gancho inmediato en los primeros 3 segundos, explicación condensada y visualmente directa.",
        "spec_notes": "YouTube Shorts permite hasta 3 minutos (180s) en formato vertical 9:16 (1080x1920). Zona inferior y lateral derecha reservadas para botones de la interfaz.",
    },
    "tiktok": {
        "id": "tiktok",
        "name": "🎵 TikTok (Vertical Dinámico 9:16)",
        "platform": "TikTok",
        "version_source": "short",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "recommended_min_sec": 60,
        "recommended_max_sec": 180,
        "platform_max_sec_configurable": 600,
        "safe_zone": {
            "top_pct": 0.13,
            "bottom_pct": 0.26,
            "left_pct": 0.06,
            "right_pct": 0.16,
            "diagram_box": [0.06, 0.14, 0.86, 0.62],
            "subtitle_margin_v_pct": 0.25,
        },
        "thumbnail_size": [1080, 1920],
        "script_tone": "Introducción ultra directa sin saludos, ritmo ágil, pregunta detonadora al final.",
        "spec_notes": "TikTok 1080x1920 (9:16). Margen derecho (16%) e inferior (26%) protegidos para iconos de perfil, likes y descripción.",
    },
    "instagram_reels": {
        "id": "instagram_reels",
        "name": "📸 Instagram Reels (Vertical 9:16)",
        "platform": "Instagram",
        "version_source": "short",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "recommended_min_sec": 45,
        "recommended_max_sec": 175,
        "platform_max_sec_configurable": 180,
        "safe_zone": {
            "top_pct": 0.12,
            "bottom_pct": 0.25,
            "left_pct": 0.06,
            "right_pct": 0.14,
            "diagram_box": [0.06, 0.13, 0.88, 0.63],
            "subtitle_margin_v_pct": 0.24,
        },
        "thumbnail_size": [1080, 1920],
        "script_tone": "Explicación visual, estética limpia y concisa ideal para guardar y compartir.",
        "spec_notes": "Instagram Reels 1080x1920 (9:16), zona central compatible con recorte 4:5 del feed de perfil.",
    },
    "facebook_reels": {
        "id": "facebook_reels",
        "name": "📘 Facebook Reels (Vertical Móvil 9:16)",
        "platform": "Facebook Reels",
        "version_source": "short",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "recommended_min_sec": 45,
        "recommended_max_sec": 175,
        "platform_max_sec_configurable": 180,
        "safe_zone": {
            "top_pct": 0.11,
            "bottom_pct": 0.24,
            "left_pct": 0.06,
            "right_pct": 0.14,
            "diagram_box": [0.06, 0.12, 0.88, 0.64],
            "subtitle_margin_v_pct": 0.23,
        },
        "thumbnail_size": [1080, 1920],
        "script_tone": "Claridad cotidiana con ejemplo práctico inmediato.",
        "spec_notes": "Facebook Reels 1080x1920 (9:16) con textos y diagramas dentro del área segura móvil.",
    },
    "facebook_video": {
        "id": "facebook_video",
        "name": "📘 Facebook Video (Horizontal 16:9 Educativo)",
        "platform": "Facebook Video",
        "version_source": "long",
        "aspect_ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "recommended_min_sec": 180,
        "recommended_max_sec": 600,
        "platform_max_sec_configurable": 14400,
        "safe_zone": {
            "top_pct": 0.06,
            "bottom_pct": 0.12,
            "left_pct": 0.05,
            "right_pct": 0.05,
            "diagram_box": [0.06, 0.07, 0.94, 0.78],
            "subtitle_margin_v_pct": 0.09,
        },
        "thumbnail_size": [1280, 720],
        "script_tone": "Narrativa desarrollada con contexto social/cotidiano y subtítulos permanentes para reproducción en feed.",
        "spec_notes": "Facebook Video 1920x1080 (o configurable a 9:16) optimizado para retención y comentarios.",
    },
}


def load_platform_profiles() -> dict[str, dict[str, Any]]:
    """Carga los perfiles de plataforma desde platform_profiles.json (creándolo si no existe)
    para que los límites de duración y zonas seguras sean 100% configurables y verificables."""
    if not PROFILES_JSON_PATH.exists():
        PROFILES_JSON_PATH.write_text(
            json.dumps(DEFAULT_PLATFORM_PROFILES, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_PLATFORM_PROFILES)
    try:
        loaded = json.loads(PROFILES_JSON_PATH.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_PLATFORM_PROFILES)
        merged.update(loaded)
        return merged
    except Exception:
        return dict(DEFAULT_PLATFORM_PROFILES)


def save_platform_profiles(profiles: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    PROFILES_JSON_PATH.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profiles


# ==============================================================================
# 5. CONTROL DE COSTOS Y PRESUPUESTO REAL (FASE 15)
# ==============================================================================

def create_default_cost_ledger() -> dict[str, Any]:
    return {
        "budget_config": {
            "max_budget_usd": 2.00,
            "max_generations": 120,
            "allow_ai_video": False,
            "prefer_local_animations": True,
            "require_cost_confirmation": True,
        },
        "summary": {
            "images_generated": 0,
            "diagrams_rendered_local": 0,
            "videos_generated_ai": 0,
            "tts_segments_synthesized": 0,
            "provider_requests": 0,
            "reported_cost_usd": 0.0,
            "unreported_cost_calls": 0,
            "total_processing_sec": 0.0,
            "errors_count": 0,
            "retries_count": 0,
        },
        "events": [],
    }


def record_cost_event(
    ledger: dict[str, Any],
    operation: str,
    provider: str,
    elapsed_sec: float,
    reported_cost_usd: Optional[float] = None,
    is_free_local_or_tier: bool = True,
    retries: int = 0,
    error: Optional[str] = None,
    details: str = "",
) -> dict[str, Any]:
    """Registra un evento real de consumo sin inventar tarifas cuando el proveedor no las reporta."""
    if not ledger or "summary" not in ledger:
        ledger = create_default_cost_ledger()

    s = ledger["summary"]
    s["provider_requests"] = int(s.get("provider_requests", 0)) + 1
    s["total_processing_sec"] = round(float(s.get("total_processing_sec", 0.0)) + float(elapsed_sec), 2)
    s["retries_count"] = int(s.get("retries_count", 0)) + int(retries)

    if error:
        s["errors_count"] = int(s.get("errors_count", 0)) + 1
    else:
        if operation == "image_generation":
            s["images_generated"] = int(s.get("images_generated", 0)) + 1
        elif operation == "diagram_generation":
            s["diagrams_rendered_local"] = int(s.get("diagrams_rendered_local", 0)) + 1
        elif operation == "ai_video_generation":
            s["videos_generated_ai"] = int(s.get("videos_generated_ai", 0)) + 1
        elif operation == "tts_synthesis":
            s["tts_segments_synthesized"] = int(s.get("tts_segments_synthesized", 0)) + 1

    if reported_cost_usd is not None:
        s["reported_cost_usd"] = round(float(s.get("reported_cost_usd", 0.0)) + float(reported_cost_usd), 5)
        cost_status = f"${reported_cost_usd:.4f} USD (reportado)"
    elif is_free_local_or_tier:
        cost_status = "$0.00 USD (local / nivel gratuito)"
    else:
        s["unreported_cost_calls"] = int(s.get("unreported_cost_calls", 0)) + 1
        cost_status = "No reportado por el proveedor en la respuesta API"

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "provider": provider,
        "elapsed_sec": round(float(elapsed_sec), 2),
        "reported_cost_usd": reported_cost_usd,
        "cost_status": cost_status,
        "retries": retries,
        "error": error,
        "details": details,
    }
    ledger.setdefault("events", []).append(event)
    return ledger


# ==============================================================================
# 6. ARQUITECTURA DE PUBLICACIÓN Y ESTADÍSTICAS FUTURAS (FASE 18)
# ==============================================================================

class PublishingPlatformAdapter:
    """Contrato arquitectónico oficial (Fase 18) para conectar cuentas y publicar mediante
    APIs oficiales (YouTube Data API v3, Meta Graph API, TikTok Content Posting API).
    NO simula publicaciones falsas: informa con transparencia el estado de configuración OAuth2."""

    SUPPORTED_PLATFORMS = {
        "youtube": {
            "name": "YouTube Data API v3",
            "required_env": ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
            "docs_url": "https://developers.google.com/youtube/v3/docs/videos/insert",
        },
        "facebook": {
            "name": "Meta Graph API (Facebook Reels & Videos)",
            "required_env": ["META_APP_ID", "META_APP_SECRET", "META_PAGE_ACCESS_TOKEN"],
            "docs_url": "https://developers.facebook.com/docs/video-api/",
        },
        "instagram": {
            "name": "Instagram Graph API (Reels Container Publishing)",
            "required_env": ["META_APP_ID", "INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_PAGE_ACCESS_TOKEN"],
            "docs_url": "https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media",
        },
        "tiktok": {
            "name": "TikTok Content Posting API v2",
            "required_env": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN"],
            "docs_url": "https://developers.tiktok.com/doc/content-posting-api-get-started",
        },
    }

    @classmethod
    def get_integration_status(cls) -> dict[str, Any]:
        import os

        status: dict[str, Any] = {}
        for key, spec in cls.SUPPORTED_PLATFORMS.items():
            configured = all(bool(os.environ.get(var, "").strip()) for var in spec["required_env"])
            status[key] = {
                "api_name": spec["name"],
                "connected": configured,
                "required_credentials": spec["required_env"],
                "docs_url": spec["docs_url"],
                "status_message": (
                    "Cuenta conectada vía credenciales OAuth2."
                    if configured
                    else "Listo arquitectónicamente. Conecta credenciales OAuth2 oficiales para habilitar publicación directa y estadísticas."
                ),
            }
        return status
