"""Perfiles de renderizado para Blender 5.3 (Fase 10).

Permite adaptar la calidad según los recursos locales del usuario:
- Borrador (Draft): Pruebas rápidas (15 FPS, 16 samples, ~3-5 seg por escena).
- Estándar (Standard): Calidad educativa recomendada (30 FPS, 32 samples con EEVEE Next).
- Alta Calidad (High): Producción final (30 FPS, 64 samples con sombras volumétricas).
"""

from __future__ import annotations

from typing import Any

RENDER_PROFILES: dict[str, dict[str, Any]] = {
    "draft": {
        "id": "draft",
        "name": "⚡ Borrador Rápido (15 FPS, 8 Samples - Ultrarrápido)",
        "fps": 15,
        "samples": 8,
        "eevee_shadows": False,
        "motion_blur": False,
        "dof": False,
        "resolution_scale": 50,
        "desc": "Optimizado para CPU/gráficos integrados (~0.3s/frame). Ideal para pruebas y prototipos instantáneos.",
    },
    "standard": {
        "id": "standard",
        "name": "🎬 Estándar Educativo (24 FPS, 16 Samples - Recomendado)",
        "fps": 24,
        "samples": 16,
        "eevee_shadows": True,
        "motion_blur": False,
        "dof": True,
        "resolution_scale": 75,
        "desc": "Equilibrio óptimo entre velocidad y belleza visual de maqueta 3D.",
    },
    "high": {
        "id": "high",
        "name": "💎 Alta Calidad (30 FPS, 32 Samples, 1080p Nativo)",
        "fps": 30,
        "samples": 32,
        "eevee_shadows": True,
        "motion_blur": True,
        "dof": True,
        "resolution_scale": 100,
        "desc": "Máxima fidelidad con sombras suaves y resolución nativa completa.",
    },
}


def get_render_profile(profile_key: str = "standard") -> dict[str, Any]:
    return RENDER_PROFILES.get(profile_key) or RENDER_PROFILES["standard"]
