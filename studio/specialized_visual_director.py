"""Director Visual Especializado por Categoría y Proceso (Fase 3.1 — Punto 4).

Selecciona y planifica las tomas cinematográficas y pedagógicas según:
1. La categoría temática detectada por `content_classifier.py` (9 categorías).
2. El proceso físico/mecánico explicado en cada escena.
3. Las 9 tipologías oficiales de toma:
   - presentacion_general (Presentación general)
   - despiece (Despiece / Exploded view)
   - corte_transversal (Corte transversal)
   - seguimiento_movimiento (Seguimiento de movimiento)
   - primer_plano (Primer plano / Macro)
   - vista_superior (Vista superior)
   - vista_lateral (Vista lateral)
   - vista_interna (Vista interna)
   - comparacion_estados (Comparación de estados)
4. Regla anti-repetición estricta: prohíbe usar la misma tipología de cámara en escenas consecutivas
   y asigna una intención educativa explícita (`pedagogical_intent`) a cada plano.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from studio.content_classifier import classify_educational_topic, VisualCategoryStrategy


# Catálogo oficial de las 9 tomas pedagógicas (Fase 3.1 - Punto 4)
OFFICIAL_SHOT_CATALOG: dict[str, dict[str, Any]] = {
    "presentacion_general": {
        "shot_id": "presentacion_general",
        "legacy_alias": "hero_view",
        "label": "Presentación General 3/4",
        "default_intent": "Contextualizar la arquitectura completa del sistema y su escala global.",
        "lens": 52,
        "margin": 0.08,
        "keys": [
            {"t": 0.0, "az": 22.0, "el": 14.0, "pad": 0.10},
            {"t": 1.0, "az": 14.0, "el": 11.0, "pad": 0.06},
        ],
    },
    "despiece": {
        "shot_id": "despiece",
        "legacy_alias": "exploded_view",
        "label": "Despiece Axial / Identificación de Subsistemas",
        "default_intent": "Separar e identificar visualmente cada componente principal y su jerarquía estructural.",
        "lens": 50,
        "margin": 0.09,
        "keys": [
            {"t": 0.0, "az": 28.0, "el": 16.0, "pad": 0.12},
            {"t": 1.0, "az": -18.0, "el": 14.0, "pad": 0.08},
        ],
    },
    "corte_transversal": {
        "shot_id": "corte_transversal",
        "legacy_alias": "cutaway_view",
        "label": "Corte Transversal Frontal",
        "default_intent": "Exponer el interior del mecanismo o circuito sin obstrucción de carcasa.",
        "lens": 56,
        "margin": 0.07,
        "keys": [
            {"t": 0.0, "az": 4.0, "el": 6.0, "pad": 0.06},
            {"t": 1.0, "az": -4.0, "el": 5.0, "pad": 0.04},
        ],
    },
    "seguimiento_movimiento": {
        "shot_id": "seguimiento_movimiento",
        "legacy_alias": "tracking_shot",
        "label": "Seguimiento Cinemático de Movimiento",
        "default_intent": "Acompañar la trayectoria activa del fluido, cabezal o tren de fuerza en tiempo real.",
        "lens": 54,
        "margin": 0.08,
        "track": True,
        "keys": [
            {"t": 0.0, "az": -24.0, "el": 12.0, "pad": 0.08},
            {"t": 0.5, "az": 10.0, "el": 15.0, "pad": 0.06},
            {"t": 1.0, "az": 28.0, "el": 10.0, "pad": 0.08},
        ],
    },
    "primer_plano": {
        "shot_id": "primer_plano",
        "legacy_alias": "close_up_view",
        "label": "Primer Plano Macro Focalizado",
        "default_intent": "Aislar un componente crítico para observar su geometría de precisión y fenómeno físico local.",
        "lens": 64,
        "margin": 0.08,
        "keys": [
            {"t": 0.0, "az": 16.0, "el": 10.0, "pad": 0.08},
            {"t": 1.0, "az": 6.0, "el": 8.0, "pad": 0.04},
        ],
    },
    "vista_superior": {
        "shot_id": "vista_superior",
        "legacy_alias": "top_view",
        "label": "Vista Superior / Cenital Oblicua",
        "default_intent": "Dominar la distribución espacial en planta, trayectorias X-Y o intercambio térmico superior.",
        "lens": 50,
        "margin": 0.08,
        "keys": [
            {"t": 0.0, "az": 18.0, "el": 42.0, "pad": 0.10},
            {"t": 1.0, "az": -12.0, "el": 38.0, "pad": 0.06},
        ],
    },
    "vista_lateral": {
        "shot_id": "vista_lateral",
        "legacy_alias": "side_view",
        "label": "Vista Lateral Técnica",
        "default_intent": "Evidenciar la disposición longitudinal, etapas axiales o disipación térmica en perfil.",
        "lens": 54,
        "margin": 0.08,
        "keys": [
            {"t": 0.0, "az": 58.0, "el": 12.0, "pad": 0.10},
            {"t": 1.0, "az": 42.0, "el": 10.0, "pad": 0.07},
        ],
    },
    "vista_interna": {
        "shot_id": "vista_interna",
        "legacy_alias": "cutaway_shot",
        "label": "Vista Interna de Cámara / Núcleo",
        "default_intent": "Penetrar en la cavidad funcional (tren planetario, cámara de compresión o zona de fusión).",
        "lens": 62,
        "margin": 0.07,
        "keys": [
            {"t": 0.0, "az": -8.0, "el": 4.0, "pad": 0.05},
            {"t": 1.0, "az": 8.0, "el": 2.0, "pad": 0.03},
        ],
    },
    "comparacion_estados": {
        "shot_id": "comparacion_estados",
        "legacy_alias": "assembly_view",
        "label": "Comparación de Estados / Regímenes",
        "default_intent": "Contrastar estados operativos (reducción vs directa vs reversa, alta vs baja presión, inicio vs pieza terminada).",
        "lens": 54,
        "margin": 0.08,
        "keys": [
            {"t": 0.0, "az": -14.0, "el": 10.0, "pad": 0.08},
            {"t": 0.5, "az": 0.0, "el": 8.0, "pad": 0.06},
            {"t": 1.0, "az": 16.0, "el": 12.0, "pad": 0.08},
        ],
    },
}

FALLBACK_ROTATION_ORDER: list[str] = [
    "presentacion_general",
    "despiece",
    "corte_transversal",
    "primer_plano",
    "vista_lateral",
    "vista_interna",
    "seguimiento_movimiento",
    "vista_superior",
    "comparacion_estados",
]


@dataclass
class DirectedScenePlan:
    scene_id: str
    title: str
    category_id: str
    shot_type: str
    composition_type: str
    phase: str
    focus_group: str | list[str]
    pedagogical_intent: str
    camera_plan: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SpecializedVisualDirector:
    """Director de escenas especializado por categoría y proceso educativo (Fase 3.1)."""

    def __init__(self) -> None:
        self.shot_catalog = OFFICIAL_SHOT_CATALOG

    def build_camera_plan(
        self,
        shot_type: str,
        focus_group: str | list[str] = "all",
        intent: str | None = None,
        custom_keys: list[dict[str, Any]] | None = None,
        lens_override: float | None = None,
        track_override: bool | None = None,
    ) -> dict[str, Any]:
        base = self.shot_catalog.get(shot_type, self.shot_catalog["presentacion_general"])
        plan = {
            "shot": base["shot_id"],
            "label": base["label"],
            "intent": intent or base["default_intent"],
            "frame": focus_group,
            "lens": float(lens_override or base["lens"]),
            "margin": float(base.get("margin", 0.08)),
            "track": bool(track_override if track_override is not None else base.get("track", False)),
            "keys": custom_keys if custom_keys else list(base["keys"]),
        }
        return plan

    def direct_script_scenes(
        self,
        topic_or_title: str,
        model_type: str,
        scenes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Enriquece la lista de escenas con clasificación temática, selección de tomas sin repetición
        y planes de cámara precisos con encuadre matemático garantizado."""
        strategy: VisualCategoryStrategy = classify_educational_topic(topic_or_title, model_type_hint=model_type)
        prev_shot: str | None = None
        directed_plans: list[dict[str, Any]] = []
        used_shots: list[str] = []

        for idx, sc in enumerate(scenes):
            requested_shot = sc.get("shot_type") or sc.get("composition_type") or "presentacion_general"
            # Normalizar si viene como alias heredado
            shot_id = self._normalize_shot_id(requested_shot, sc.get("phase", "overview"), idx)

            # Regla anti-repetición estricta: nunca repetir el mismo shot_id en escenas consecutivas
            if shot_id == prev_shot:
                shot_id = self._pick_non_repeating_alternative(prev_shot, used_shots)

            prev_shot = shot_id
            used_shots.append(shot_id)

            focus_group = sc.get("focus_group", "all")
            intent = sc.get("pedagogical_intent") or self.shot_catalog[shot_id]["default_intent"]
            custom_keys = sc.get("camera_keys")
            lens_override = sc.get("lens")
            track_override = sc.get("track")

            cam_plan = self.build_camera_plan(
                shot_type=shot_id,
                focus_group=focus_group,
                intent=intent,
                custom_keys=custom_keys,
                lens_override=lens_override,
                track_override=track_override,
            )

            sc["shot_type"] = shot_id
            sc["composition_type"] = self.shot_catalog[shot_id]["legacy_alias"]
            sc["pedagogical_intent"] = intent
            sc["category_id"] = strategy.category_id
            sc["camera_plan"] = cam_plan

            directed_plans.append(
                DirectedScenePlan(
                    scene_id=sc["id"],
                    title=sc["title"],
                    category_id=strategy.category_id,
                    shot_type=shot_id,
                    composition_type=sc["composition_type"],
                    phase=sc.get("phase", "overview"),
                    focus_group=focus_group,
                    pedagogical_intent=intent,
                    camera_plan=cam_plan,
                ).to_dict()
            )

        return {
            "category": {
                "category_id": strategy.category_id,
                "name": strategy.name,
                "description": strategy.description,
                "primary_lighting_style": strategy.primary_lighting_style,
                "dominant_camera_modes": strategy.dominant_camera_modes,
                "preferred_fx": strategy.preferred_fx,
                "color_palette": strategy.color_palette,
                "pedagogical_focus": strategy.pedagogical_focus,
            },
            "unique_shot_types_count": len(set(used_shots)),
            "consecutive_duplicates": self._count_consecutive_duplicates(used_shots),
            "shot_sequence": used_shots,
            "directed_scenes": directed_plans,
        }

    def _normalize_shot_id(self, raw_shot: str, phase: str, idx: int) -> str:
        if raw_shot in self.shot_catalog:
            return raw_shot
        alias_map = {
            "hero_view": "presentacion_general",
            "hero_shot": "presentacion_general",
            "exploded_view": "despiece",
            "cutaway_view": "corte_transversal",
            "cutaway_shot": "corte_transversal",
            "tracking_shot": "seguimiento_movimiento",
            "close_up_view": "primer_plano",
            "top_view": "vista_superior",
            "side_view": "vista_lateral",
            "internal_view": "vista_interna",
            "assembly_view": "comparacion_estados",
        }
        if raw_shot in alias_map:
            return alias_map[raw_shot]
        return FALLBACK_ROTATION_ORDER[idx % len(FALLBACK_ROTATION_ORDER)]

    def _pick_non_repeating_alternative(self, prev_shot: str | None, used_shots: list[str]) -> str:
        for candidate in FALLBACK_ROTATION_ORDER:
            if candidate != prev_shot and candidate not in used_shots:
                return candidate
        for candidate in FALLBACK_ROTATION_ORDER:
            if candidate != prev_shot:
                return candidate
        return "presentacion_general"

    @staticmethod
    def _count_consecutive_duplicates(shots: list[str]) -> int:
        return sum(1 for i in range(1, len(shots)) if shots[i] == shots[i - 1])
