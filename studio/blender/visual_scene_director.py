"""Director Visual Inteligente de Escenas 3D (Fase 2.3 - Cinematic Engine).

Módulo de Dirección Automática de Escenas y Narrativa Visual Cinematográfica:
- Mapea fragmentos de narración técnica a composiciones y encuadres con intención educativa.
- Aplica las 10 plantillas cinematográficas estándar (Hero, Isometric, Close-up, Tracking, Orbit, Cutaway, Exploded, Assembly, Top, Side).
- Garantiza variedad visual: prohíbe tomas repetitivas consecutivas.
- Sincroniza el foco narrativo (objeto protagonista) con movimientos de cámara y resaltado de componentes (Highlight pulse).
- Proporciona la secuencia canónica de 12 escenas para el motor de cuatro tiempos según especificaciones de la Fase 2.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VisualSceneSpec:
    """Especificación semántica y cinematográfica de una escena 3D."""

    id: str
    title: str
    text: str
    concept: str
    target_component: str  # "engine_complete", "piston", "connecting_rod", "crankshaft", "valves", "combustion_chamber"
    action: str            # "overview", "orbit", "exploded_view", "assembly_shot", "intake_stroke", etc.
    shot_type: str         # "hero_shot", "isometric_shot", "close_up", "tracking_shot", "orbit_shot", "cutaway_shot", "exploded_view", "assembly_shot", "top_view", "side_view"
    shot_subtype: str      # Subtoma específica de encuadre
    camera_movement: str   # "static", "dolly_in", "orbit_sweep", "tracking", "high_angle_pan"
    duration_sec: float = 4.0
    cycle_phase: str = "full_cycle"
    highlight_component: Optional[str] = None
    visual_fx: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializa la escena en un diccionario para el orquestador de renderizado."""
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "concept": self.concept,
            "target_component": self.target_component,
            "action": self.action,
            "composition": self.shot_subtype or self.shot_type,
            "shot_type": self.shot_type,
            "shot_subtype": self.shot_subtype,
            "camera_movement": self.camera_movement,
            "duration_sec": self.duration_sec,
            "phase": self.cycle_phase,
            "cycle_phase": self.cycle_phase,
            "highlight_component": self.highlight_component,
            "visual_fx": self.visual_fx,
        }


class VisualSceneDirector:
    """Director automático de escenas con inteligencia compositiva y variedad cinemática."""

    # Catálogo de las 10 plantillas reutilizables (Fase 2.3 - Sección 3)
    SHOT_TEMPLATES = {
        "A": "hero_shot",        # Presentación del objeto completo
        "B": "isometric_shot",   # Vista tridimensional técnica a 45°
        "C": "close_up",         # Acercamiento a una pieza específica
        "D": "tracking_shot",    # Seguimiento de una pieza en movimiento
        "E": "orbit_shot",       # Cámara orbitando alrededor del objeto
        "F": "cutaway_shot",     # Corte transversal para mostrar el interior
        "G": "exploded_view",    # Separación axial de componentes
        "H": "assembly_shot",    # Ensamblaje inverso de componentes
        "I": "top_view",         # Vista superior de culata y válvulas
        "J": "side_view",        # Vista lateral ortogonal
    }

    def __init__(self) -> None:
        self.last_shot_type: Optional[str] = None

    def validate_and_enrich_sequence(self, scenes: list[dict[str, Any]]) -> list[VisualSceneSpec]:
        """Aplica reglas de variedad cinematográfica y enriquece la secuencia."""
        enriched: list[VisualSceneSpec] = []
        last_shot: Optional[str] = None

        for sc in scenes:
            raw_shot = sc.get("shot_type") or sc.get("composition") or "hero_shot"
            concept = sc.get("concept", "general")
            comp = sc.get("target_component", "engine_complete")

            # Regla de Variedad: Evitar duplicación de cámara consecutiva salvo continuidad justificada
            if raw_shot == last_shot and not sc.get("force_repeat_shot", False):
                # Variar inteligentemente según el componente
                if comp == "piston":
                    raw_shot = "cutaway_shot" if last_shot == "close_up" else "close_up"
                elif comp == "valves":
                    raw_shot = "top_view" if last_shot == "close_up" else "close_up"
                elif comp == "connecting_rod":
                    raw_shot = "tracking_shot" if last_shot != "tracking_shot" else "side_cutaway"
                elif comp == "engine_complete":
                    raw_shot = "isometric_shot" if last_shot == "hero_shot" else "hero_shot"

            # Determinar subtipo de cámara para encuadre preciso
            shot_subtype = sc.get("shot_subtype") or sc.get("composition") or raw_shot
            if raw_shot == "close_up":
                if comp == "piston":
                    shot_subtype = "close_up_piston"
                elif comp in ("crankshaft", "crank"):
                    shot_subtype = "close_up_crank"
                elif comp in ("valves", "valve"):
                    shot_subtype = "close_up_valves"
                elif comp in ("combustion_chamber", "chamber"):
                    shot_subtype = "close_up_chamber"
            elif raw_shot == "tracking_shot":
                shot_subtype = "tracking_rod" if comp == "connecting_rod" else "component_track"
            elif raw_shot == "hero_shot":
                shot_subtype = "hero_view"
            elif raw_shot == "orbit_shot":
                shot_subtype = "turntable_orbit"
            elif raw_shot == "cutaway_shot":
                shot_subtype = "cutaway_view"
            elif raw_shot == "top_view":
                shot_subtype = "valve_top_view"
            elif raw_shot == "isometric_shot":
                shot_subtype = "isometric_view"
            elif raw_shot == "assembly_shot":
                shot_subtype = "assembly_view"

            spec = VisualSceneSpec(
                id=sc.get("id", f"SCN_{len(enriched)+1:02d}"),
                title=sc.get("title", f"Escena {len(enriched)+1}"),
                text=sc.get("text", ""),
                concept=concept,
                target_component=comp,
                action=sc.get("action", "motion"),
                shot_type=raw_shot,
                shot_subtype=shot_subtype,
                camera_movement=sc.get("camera_movement", "slow_dolly"),
                duration_sec=float(sc.get("duration_sec", 4.0)),
                cycle_phase=sc.get("phase", sc.get("cycle_phase", "full_cycle")),
                highlight_component=sc.get("highlight_component") or (comp if comp in ("piston", "connecting_rod", "crankshaft", "valves") else None),
                visual_fx=sc.get("visual_fx", {}),
            )

            last_shot = spec.shot_type
            enriched.append(spec)

        return enriched

    @classmethod
    def get_canonical_12_scenes_sequence(cls) -> list[dict[str, Any]]:
        """Devuelve la secuencia oficial obligatoria de 12 escenas de la Fase 2.3."""
        return [
            # 1. Presentación del motor completo
            {
                "id": "SCN_01_HERO",
                "title": "1. Presentación del Motor Completo",
                "text": "El motor de cuatro tiempos es la cúspide de la ingeniería automotriz moderna.",
                "concept": "overview",
                "target_component": "engine_complete",
                "action": "overview",
                "shot_type": "hero_shot",
                "shot_subtype": "hero_view",
                "phase": "hero_intro",
                "camera_movement": "slow_dolly",
            },
            # 2. Órbita de cámara
            {
                "id": "SCN_02_ORBIT",
                "title": "2. Exploración Orbital 360°",
                "text": "Su arquitectura compacta integra cárter, bloque y culata en perfecta simetría.",
                "concept": "3d_volume",
                "target_component": "engine_complete",
                "action": "orbit",
                "shot_type": "orbit_shot",
                "shot_subtype": "turntable_orbit",
                "phase": "full_cycle",
                "camera_movement": "orbit_sweep",
            },
            # 3. Despiece de componentes
            {
                "id": "SCN_03_EXPLODED",
                "title": "3. Despiece Axial de Componentes",
                "text": "Cada componente mecánico soporta presiones colosales y fricción extrema.",
                "concept": "exploded_mechanics",
                "target_component": "engine_complete",
                "action": "explode_parts",
                "shot_type": "exploded_view",
                "shot_subtype": "exploded_view",
                "phase": "exploded_view",
                "camera_movement": "pan_up",
            },
            # 4. Primer plano del pistón
            {
                "id": "SCN_04_PISTON",
                "title": "4. Pistón y Aros de Compresión",
                "text": "El pistón de aluminio anodizado recibe el impacto de los gases mediante sus aros selladores.",
                "concept": "piston_mechanics",
                "target_component": "piston",
                "highlight_component": "piston",
                "action": "piston_motion",
                "shot_type": "close_up",
                "shot_subtype": "close_up_piston",
                "phase": "intake",
                "camera_movement": "macro_zoom",
            },
            # 5. Seguimiento de la biela
            {
                "id": "SCN_05_ROD_TRACK",
                "title": "5. Seguimiento Cinemático de la Biela",
                "text": "La biela forjada en viga I transforma la oscilación lineal en fuerza rotativa.",
                "concept": "rod_kinematics",
                "target_component": "connecting_rod",
                "highlight_component": "connecting_rod",
                "action": "spin_and_track",
                "shot_type": "tracking_shot",
                "shot_subtype": "tracking_rod",
                "phase": "full_cycle",
                "camera_movement": "tracking",
            },
            # 6. Primer plano del cigüeñal
            {
                "id": "SCN_06_CRANK",
                "title": "6. Cigüeñal y Muñequilla a Espejo",
                "text": "El cigüeñal canaliza el par motor asistido por contrapesos que absorben vibraciones.",
                "concept": "crank_torque",
                "target_component": "crankshaft",
                "highlight_component": "crankshaft",
                "action": "crank_torque",
                "shot_type": "close_up",
                "shot_subtype": "close_up_crank",
                "phase": "full_cycle",
                "camera_movement": "slow_dolly",
            },
            # 7. Vista superior de las válvulas
            {
                "id": "SCN_07_VALVES_TOP",
                "title": "7. Distribución y Resortes Helicoidales",
                "text": "En la culata, las válvulas abren y cierran con resortes helicoidales de alta tensión.",
                "concept": "valves_timing",
                "target_component": "valves",
                "highlight_component": "valves",
                "action": "valves_cycle",
                "shot_type": "top_view",
                "shot_subtype": "valve_top_view",
                "phase": "exhaust",
                "camera_movement": "high_angle_pan",
            },
            # 8. Animación de admisión
            {
                "id": "SCN_08_INTAKE",
                "title": "8. Primer Tiempo: Admisión",
                "text": "Tiempo uno: Admisión. La válvula izquierda desciende y el pistón aspira mezcla fresca.",
                "concept": "stroke_intake",
                "target_component": "combustion_chamber",
                "action": "open_intake_flow",
                "shot_type": "cutaway_shot",
                "shot_subtype": "cutaway_view",
                "phase": "intake",
                "visual_fx": {"intake_flow": True},
                "camera_movement": "slow_dolly",
            },
            # 9. Animación de compresión
            {
                "id": "SCN_09_COMPRESSION",
                "title": "9. Segundo Tiempo: Compresión",
                "text": "Tiempo dos: Compresión. Con ambas válvulas herméticamente cerradas, la mezcla se comprime.",
                "concept": "stroke_compression",
                "target_component": "combustion_chamber",
                "action": "compress_gas",
                "shot_type": "close_up",
                "shot_subtype": "close_up_chamber",
                "phase": "compression",
                "visual_fx": {"compression_gas": True},
                "camera_movement": "slow_dolly",
            },
            # 10. Animación de expansión
            {
                "id": "SCN_10_COMBUSTION",
                "title": "10. Tercer Tiempo: Expansión y Combustión",
                "text": "Tiempo tres: Expansión. La bujía detona la chispa y el estallido impulsa al pistón.",
                "concept": "stroke_expansion",
                "target_component": "combustion_chamber",
                "action": "ignite_combustion",
                "shot_type": "close_up",
                "shot_subtype": "close_up_chamber",
                "phase": "combustion",
                "visual_fx": {"spark_flame": True, "light_pulse": True},
                "camera_movement": "macro_zoom",
            },
            # 11. Animación de escape
            {
                "id": "SCN_11_EXHAUST",
                "title": "11. Cuarto Tiempo: Escape",
                "text": "Tiempo cuatro: Escape. La válvula derecha abre y el pistón expulsa los gases quemados.",
                "concept": "stroke_exhaust",
                "target_component": "combustion_chamber",
                "action": "open_exhaust_flow",
                "shot_type": "cutaway_shot",
                "shot_subtype": "cutaway_view",
                "phase": "exhaust",
                "visual_fx": {"exhaust_flow": True},
                "camera_movement": "slow_dolly",
            },
            # 12. Vista general del ciclo completo (Ensamblaje y marcha continua)
            {
                "id": "SCN_12_ASSEMBLY_CYCLE",
                "title": "12. Ciclo Continuo y Conclusión",
                "text": "Los cuatro tiempos se repiten miles de veces por minuto, impulsando al mundo con precisión.",
                "concept": "full_cycle_assembly",
                "target_component": "engine_complete",
                "action": "assemble_parts",
                "shot_type": "assembly_shot",
                "shot_subtype": "assembly_view",
                "phase": "assembly_shot",
                "camera_movement": "slow_dolly",
            },
        ]
