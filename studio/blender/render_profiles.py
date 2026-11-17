"""Perfiles de renderizado optimizados para Blender 5.3 (Fase 2 - Perfeccionamiento).

Específicamente diseñados para funcionar en equipos con 8 GB de RAM y gráficos integrados
(Intel Core i5 11.ª gen / AMD Ryzen 7 / Intel Iris Xe / Radeon Graphics):

- test (Prueba rápida): 720 × 1280 (9:16), 24 FPS, 8 muestras EEVEE Next (~0.25s/frame).
- production (Producción final): 1080 × 1920 (9:16), 24 FPS, 16 muestras EEVEE Next (~0.5s/frame).
- production_16_9: 1920 × 1080 (16:9), 24 FPS, 16 muestras.
"""

from __future__ import annotations

from typing import Any

RENDER_PROFILES: dict[str, dict[str, Any]] = {
    # Perfil Oficial de Prueba (Punto 7)
    "test": {
        "id": "test",
        "name": "⚡ Prueba Rápida (720×1280, 24 FPS, 8 Samples)",
        "width": 720,
        "height": 1280,
        "fps": 24,
        "samples": 8,
        "resolution_scale": 100,
        "shadow_quality": "LOW",
        "use_soft_shadows": True,
        "desc": "Ultra optimizado para previsualización inmediata en Iris Xe (~0.25s/frame).",
    },
    # Perfil Oficial de Producción (Punto 7)
    "production": {
        "id": "production",
        "name": "💎 Producción Final (1080×1920 Full HD, 24 FPS, 16 Samples)",
        "width": 1080,
        "height": 1920,
        "fps": 24,
        "samples": 16,
        "resolution_scale": 100,
        "shadow_quality": "MEDIUM",
        "use_soft_shadows": True,
        "desc": "Máxima nitidez estética de maqueta educativa para redes y streaming vertical.",
    },
    # Variante horizontal para YouTube estándar
    "production_16_9": {
        "id": "production_16_9",
        "name": "📺 Producción Horizontal (1920×1080 Full HD, 24 FPS)",
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "samples": 16,
        "resolution_scale": 100,
        "shadow_quality": "MEDIUM",
        "use_soft_shadows": True,
        "desc": "Formato horizontal 16:9 con encuadre panorámico.",
    },
    # Alias retrocompatibles
    "draft": {
        "id": "draft",
        "name": "⚡ Borrador Rápido (720×1280, 24 FPS)",
        "width": 720,
        "height": 1280,
        "fps": 24,
        "samples": 8,
        "resolution_scale": 100,
        "shadow_quality": "LOW",
        "use_soft_shadows": True,
        "desc": "Alias de test.",
    },
    "standard": {
        "id": "standard",
        "name": "🎬 Estándar (1080×1920, 24 FPS)",
        "width": 1080,
        "height": 1920,
        "fps": 24,
        "samples": 16,
        "resolution_scale": 100,
        "shadow_quality": "MEDIUM",
        "use_soft_shadows": True,
        "desc": "Alias de production.",
    },
    "high": {
        "id": "high",
        "name": "💎 Alta Calidad (1080×1920, 24 FPS)",
        "width": 1080,
        "height": 1920,
        "fps": 24,
        "samples": 24,
        "resolution_scale": 100,
        "shadow_quality": "HIGH",
        "use_soft_shadows": True,
        "desc": "Perfil de alta fidelidad.",
    },
}


def get_render_profile(profile_key: str = "production") -> dict[str, Any]:
    """Obtiene la configuración del perfil solicitado o retorna production por defecto."""
    key = profile_key.lower().strip()
    return RENDER_PROFILES.get(key, RENDER_PROFILES["production"])
