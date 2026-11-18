"""Director Audiovisual Inteligente y Especializado por Categoría (Fase 3.1 y Fase 3.2).

Convierte cada guion y su audio real con marcas temporales por palabra (`WordBoundary` / alineación acústica)
en una Línea de Tiempo Audiovisual Estructurada (`AudiovisualBeat`), decidiendo por cada fragmento semántico:
- Qué objeto debe aparecer (`subject`).
- Qué componente debe destacarse (`highlight`).
- Qué acción física o mecánica debe realizar (`action`).
- Qué perfil de cámara 9:16 debe utilizarse (`camera`, entre los 11 perfiles reutilizables).
- Qué etiquetas e información deben mostrarse (`labels`) y en qué segundo exacto del audio (`label_triggers`)
  el narrador menciona el componente (prohibiendo mostrar etiquetas antes de ser explicadas).
- Cuándo comienza y termina exactamente cada acción (`start_time`, `end_time`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from studio.content_classifier import classify_educational_topic, VisualCategoryStrategy


# ==============================================================================
# 1. CATÁLOGO UNIFICADO DE 11 PERFILES DE CÁMARA 9:16 (FASE 3.2 — PUNTO 4)
# ==============================================================================
# Márgenes y holguras (pad) optimizados para formato vertical 9:16: aprovecha el espacio vertical
# evitando modelos pequeños y respetando las zonas seguras de subtítulos e interfaz móvil.

CAMERA_PROFILES_9_16: dict[str, dict[str, Any]] = {
    "hero_shot": {
        "shot_id": "hero_shot",
        "es_alias": "presentacion_general",
        "legacy_alias": "hero_view",
        "label": "Hero Shot 3/4 Vertical",
        "default_intent": "Presentar el sistema completo aprovechando la altura del formato 9:16.",
        "lens": 54,
        "margin": 0.055,
        "keys": [
            {"t": 0.0, "az": 20.0, "el": 13.0, "pad": 0.04},
            {"t": 1.0, "az": 12.0, "el": 10.0, "pad": 0.02},
        ],
    },
    "close_up": {
        "shot_id": "close_up",
        "es_alias": "primer_plano",
        "legacy_alias": "close_up_view",
        "label": "Close-Up de Subsistema",
        "default_intent": "Encuadrar de cerca el componente mencionado para observar su función mecánica.",
        "lens": 64,
        "margin": 0.055,
        "keys": [
            {"t": 0.0, "az": 14.0, "el": 9.0, "pad": 0.03},
            {"t": 1.0, "az": 5.0, "el": 7.0, "pad": 0.01},
        ],
    },
    "extreme_close_up": {
        "shot_id": "extreme_close_up",
        "es_alias": "macro_extremo",
        "legacy_alias": "close_up_view",
        "label": "Extreme Close-Up Macro",
        "default_intent": "Macro de máxima proximidad al punto de contacto físico (dientes, boquilla, capilar o pistón).",
        "lens": 74,
        "margin": 0.045,
        "keys": [
            {"t": 0.0, "az": 8.0, "el": 6.0, "pad": 0.01},
            {"t": 1.0, "az": -4.0, "el": 4.0, "pad": 0.0},
        ],
    },
    "isometric": {
        "shot_id": "isometric",
        "es_alias": "vista_isometrica",
        "legacy_alias": "isometric_view",
        "label": "Isometric Technical View",
        "default_intent": "Perspectiva isométrica tridimensional a 38° para apreciar profundidad y ejes simultáneos.",
        "lens": 58,
        "margin": 0.06,
        "keys": [
            {"t": 0.0, "az": 38.0, "el": 24.0, "pad": 0.04},
            {"t": 1.0, "az": 30.0, "el": 20.0, "pad": 0.03},
        ],
    },
    "orbit": {
        "shot_id": "orbit",
        "es_alias": "orbita",
        "legacy_alias": "turntable_orbit",
        "label": "Orbit Shot Suave",
        "default_intent": "Recorrido orbital continuo alrededor del mecanismo para revelar su volumetría 3D.",
        "lens": 54,
        "margin": 0.06,
        "keys": [
            {"t": 0.0, "az": -32.0, "el": 14.0, "pad": 0.04},
            {"t": 0.5, "az": 0.0, "el": 11.0, "pad": 0.03},
            {"t": 1.0, "az": 32.0, "el": 14.0, "pad": 0.04},
        ],
    },
    "tracking": {
        "shot_id": "tracking",
        "es_alias": "seguimiento_movimiento",
        "legacy_alias": "tracking_shot",
        "label": "Tracking Shot de Flujo / Movimiento",
        "default_intent": "Seguir dinámicamente el desplazamiento del refrigerante, cabezal o flujo de par.",
        "lens": 56,
        "margin": 0.055,
        "track": True,
        "keys": [
            {"t": 0.0, "az": -20.0, "el": 11.0, "pad": 0.03},
            {"t": 0.5, "az": 6.0, "el": 13.0, "pad": 0.02},
            {"t": 1.0, "az": 24.0, "el": 9.0, "pad": 0.03},
        ],
    },
    "side_view": {
        "shot_id": "side_view",
        "es_alias": "vista_lateral",
        "legacy_alias": "side_view",
        "label": "Side View Técnica",
        "default_intent": "Mostrar el perfil longitudinal, la disipación lateral de calor o el cierre axial de embragues.",
        "lens": 56,
        "margin": 0.055,
        "keys": [
            {"t": 0.0, "az": 52.0, "el": 10.0, "pad": 0.04},
            {"t": 1.0, "az": 38.0, "el": 8.0, "pad": 0.02},
        ],
    },
    "top_view": {
        "shot_id": "top_view",
        "es_alias": "vista_superior",
        "legacy_alias": "top_view",
        "label": "Top View / Picado Oblicuo",
        "default_intent": "Dominar la planta superior del mecanismo, alimentación de filamento o bandeja superior.",
        "lens": 52,
        "margin": 0.055,
        "keys": [
            {"t": 0.0, "az": 16.0, "el": 40.0, "pad": 0.04},
            {"t": 1.0, "az": -10.0, "el": 35.0, "pad": 0.02},
        ],
    },
    "cutaway": {
        "shot_id": "cutaway",
        "es_alias": "corte_transversal",
        "legacy_alias": "cutaway_view",
        "label": "Cutaway Frontal Seccionado",
        "default_intent": "Exponer de frente el plano de sección transversal del mecanismo sin distorsión angular.",
        "lens": 58,
        "margin": 0.05,
        "keys": [
            {"t": 0.0, "az": 3.0, "el": 5.0, "pad": 0.03},
            {"t": 1.0, "az": -3.0, "el": 4.0, "pad": 0.01},
        ],
    },
    "exploded_view": {
        "shot_id": "exploded_view",
        "es_alias": "despiece",
        "legacy_alias": "exploded_view",
        "label": "Exploded View / Despiece",
        "default_intent": "Apreciar la separación ordenada de componentes e identificar su relación espacial.",
        "lens": 52,
        "margin": 0.065,
        "keys": [
            {"t": 0.0, "az": 25.0, "el": 15.0, "pad": 0.05},
            {"t": 1.0, "az": -15.0, "el": 12.0, "pad": 0.03},
        ],
    },
    "internal_tracking": {
        "shot_id": "internal_tracking",
        "es_alias": "vista_interna",
        "legacy_alias": "cutaway_shot",
        "label": "Internal Tracking / Cavidad Funcional",
        "default_intent": "Seguir el proceso dentro de la cámara interior (tren planetario, compresor o zona de fusión).",
        "lens": 66,
        "margin": 0.048,
        "track": True,
        "keys": [
            {"t": 0.0, "az": -7.0, "el": 4.0, "pad": 0.02},
            {"t": 1.0, "az": 7.0, "el": 2.0, "pad": 0.01},
        ],
    },
    "state_comparison": {
        "shot_id": "state_comparison",
        "es_alias": "comparacion_estados",
        "legacy_alias": "assembly_view",
        "label": "Comparación de Estados Operativos",
        "default_intent": "Contrastar secuencialmente los estados o regímenes de operación del sistema completo.",
        "lens": 55,
        "margin": 0.055,
        "keys": [
            {"t": 0.0, "az": -12.0, "el": 9.0, "pad": 0.04},
            {"t": 0.5, "az": 0.0, "el": 7.0, "pad": 0.02},
            {"t": 1.0, "az": 14.0, "el": 10.0, "pad": 0.04},
        ],
    },
}

# Mapa bidireccional para aceptar tanto IDs Fase 3.2 (hero_shot, close_up...) como Fase 3.1 (presentacion_general...)
OFFICIAL_SHOT_CATALOG: dict[str, dict[str, Any]] = {}
for _k, _v in CAMERA_PROFILES_9_16.items():
    OFFICIAL_SHOT_CATALOG[_k] = _v
    OFFICIAL_SHOT_CATALOG[_v["es_alias"]] = _v

FALLBACK_ROTATION_ORDER: list[str] = [
    "hero_shot",
    "exploded_view",
    "cutaway",
    "internal_tracking",
    "close_up",
    "extreme_close_up",
    "side_view",
    "tracking",
    "top_view",
    "isometric",
    "orbit",
    "state_comparison",
]


# ==============================================================================
# 2. DICCIONARIO SEMÁNTICO DE SUJETOS, ACCIONES Y ETIQUETAS POR MODELO
# ==============================================================================

MODEL_SEMANTIC_KNOWLEDGE: dict[str, list[dict[str, Any]]] = {
    "refrigerator_cycle": [
        {
            "keywords": ["compresor", "aspira", "succión", "motor eléctrico", "bobinado", "rotor", "pistón", "comprime"],
            "subject": "compressor",
            "highlight": "compressor",
            "action": "compressor_piston_stroke",
            "default_camera": "internal_tracking",
            "label_key": "compressor",
            "label_display": "COMPRESOR",
        },
        {
            "keywords": ["alta presión", "vapor sobrecalentado", "vapor rojo", "línea de descarga", "descarga", "disparando su presión"],
            "subject": "compressor",
            "highlight": "circuit",
            "action": "high_pressure_discharge",
            "default_camera": "extreme_close_up",
            "label_key": "high",
            "label_display": "ALTA PRESIÓN · CALIENTE",
        },
        {
            "keywords": ["condensador", "ocho pasadas", "serpentín condensador", "aletas", "disipan el calor", "se condensa", "líquido naranja"],
            "subject": "condenser",
            "highlight": "condenser",
            "action": "condenser_heat_rejection",
            "default_camera": "side_view",
            "label_key": "condenser",
            "label_display": "CONDENSADOR",
        },
        {
            "keywords": ["filtro deshidratador", "filtro", "humedad"],
            "subject": "dryer",
            "highlight": "dryer",
            "action": "dryer_filtration",
            "default_camera": "close_up",
            "label_key": "dryer",
            "label_display": "FILTRO",
        },
        {
            "keywords": ["tubo capilar", "capilar", "siete espiras", "estrangula", "desplomen", "cae la presión", "expansión"],
            "subject": "capillary",
            "highlight": "capillary",
            "action": "capillary_pressure_drop",
            "default_camera": "extreme_close_up",
            "label_key": "expansion",
            "label_display": "TUBO CAPILAR",
        },
        {
            "keywords": ["evaporador", "congelador", "hierve", "bajo cero", "absorbiendo el calor", "baja presión"],
            "subject": "evaporator",
            "highlight": "evaporator",
            "action": "evaporator_heat_absorption",
            "default_camera": "cutaway",
            "label_key": "evaporator",
            "label_display": "EVAPORADOR",
        },
        {
            "keywords": ["alimentos", "botellas", "frutas", "frescos", "cocina"],
            "subject": "food",
            "highlight": "food",
            "action": "food_cooling_transfer",
            "default_camera": "cutaway",
            "label_key": None,
            "label_display": None,
        },
    ],
    "automatic_transmission": [
        {
            "keywords": ["convertidor de par", "bomba impulsora", "impulsor", "fluido rojo", "turbina", "estátor", "hidrodinámica"],
            "subject": "converter",
            "highlight": "converter",
            "action": "torque_converter_vortex",
            "default_camera": "cutaway",
            "label_key": None,
            "label_display": "CONVERTIDOR DE PAR",
        },
        {
            "keywords": ["engranaje solar", "solar", "veinticuatro dientes", "sol"],
            "subject": "sun",
            "highlight": "sun",
            "action": "sun_gear_input_drive",
            "default_camera": "extreme_close_up",
            "label_key": "sun",
            "label_display": "SOL",
        },
        {
            "keywords": ["satélites", "planetarios", "doce dientes", "ruedas intermedias"],
            "subject": "planets",
            "highlight": "planets",
            "action": "planet_pinions_orbit",
            "default_camera": "internal_tracking",
            "label_key": "planets",
            "label_display": "PLANETARIOS",
        },
        {
            "keywords": ["portasatélites", "carrier", "tercio de velocidad", "triple de fuerza", "inmoviliza"],
            "subject": "carrier",
            "highlight": "carrier",
            "action": "carrier_torque_output",
            "default_camera": "close_up",
            "label_key": "carrier",
            "label_display": "PORTASATÉLITES",
        },
        {
            "keywords": ["corona exterior", "corona", "cuarenta y ocho dientes", "invierten el sentido"],
            "subject": "ring",
            "highlight": "ring",
            "action": "ring_gear_reaction",
            "default_camera": "close_up",
            "label_key": "ring",
            "label_display": "CORONA",
        },
        {
            "keywords": ["banda de freno", "servo hidráulico", "frenos de banda", "bloquea fija"],
            "subject": "brake",
            "highlight": "brake",
            "action": "brake_band_clamp",
            "default_camera": "close_up",
            "label_key": "ring",
            "label_display": "CORONA",
        },
        {
            "keywords": ["embragues multidisco", "paquete de embragues", "embrague", "relación directa", "uno a uno"],
            "subject": "clutch",
            "highlight": "clutch",
            "action": "clutch_pack_lockup",
            "default_camera": "side_view",
            "label_key": None,
            "label_display": "EMBRAGUE 1:1",
        },
        {
            "keywords": ["cuerpo de válvulas", "válvulas hidráulicas", "presión hidráulica"],
            "subject": "hydraulics",
            "highlight": "hydraulics",
            "action": "hydraulic_valve_routing",
            "default_camera": "isometric",
            "label_key": None,
            "label_display": "CUERPO DE VÁLVULAS",
        },
    ],
    "printer_3d_fdm": [
        {
            "keywords": ["perfiles de aluminio", "v-slot", "estructura", "chasis"],
            "subject": "frame",
            "highlight": "frame",
            "action": "frame_stability",
            "default_camera": "isometric",
            "label_key": "frame",
            "label_display": "ESTRUCTURA V-SLOT",
        },
        {
            "keywords": ["carrete", "filamento", "hebra", "ácido poliláctico"],
            "subject": "filament_spool",
            "highlight": "filament_spool",
            "action": "spool_unwinding",
            "default_camera": "top_view",
            "label_key": "spool",
            "label_display": "FILAMENTO",
        },
        {
            "keywords": ["extrusor directo", "extrusor", "engranaje dentado", "rodamiento tensor", "tracción"],
            "subject": "extruder",
            "highlight": "extruder",
            "action": "extruder_gear_feed",
            "default_camera": "close_up",
            "label_key": "extruder",
            "label_display": "EXTRUSOR",
        },
        {
            "keywords": ["hotend", "aletas", "puente térmico", "bloque calefactor", "doscientos grados", "ventilador", "tobera"],
            "subject": "hotend",
            "highlight": "hotend",
            "action": "hotend_thermal_melt",
            "default_camera": "extreme_close_up",
            "label_key": "hotend",
            "label_display": "HOTEND",
        },
        {
            "keywords": ["boquilla", "cuatro décimas", "cordón fundido", "punta"],
            "subject": "nozzle",
            "highlight": "nozzle",
            "action": "nozzle_bead_extrusion",
            "default_camera": "extreme_close_up",
            "label_key": "nozzle",
            "label_display": "BOQUILLA",
        },
        {
            "keywords": ["eje x", "correa dentada", "carro lateralmente"],
            "subject": "x_axis",
            "highlight": "x_axis",
            "action": "x_axis_belt_sweep",
            "default_camera": "tracking",
            "label_key": "xaxis",
            "label_display": "EJE X",
        },
        {
            "keywords": ["eje y", "cama caliente", "plataforma móvil", "resortes de nivelación", "lámina dorada"],
            "subject": "bed",
            "highlight": "bed",
            "action": "y_axis_bed_sweep",
            "default_camera": "side_view",
            "label_key": "bed",
            "label_display": "CAMA (EJE Y)",
        },
        {
            "keywords": ["eje z", "husillos", "husillos roscados", "elevan el puente"],
            "subject": "z_axis",
            "highlight": "z_axis",
            "action": "z_axis_leadscrew_lift",
            "default_camera": "isometric",
            "label_key": "zaxis",
            "label_display": "EJE Z (HUSILLOS)",
        },
        {
            "keywords": ["capa", "capas", "estrato", "anillo", "pieza", "objeto terminado"],
            "subject": "printed_part",
            "highlight": "printed_part",
            "action": "spiral_layer_deposition",
            "default_camera": "internal_tracking",
            "label_key": "nozzle",
            "label_display": "BOQUILLA",
        },
    ],
}


@dataclass
class AudiovisualBeat:
    """Representación estructurada de cada unidad narrativa sincronizada (Fase 3.2 - Punto 2)."""
    beat_id: str
    narration: str
    start_time: float
    end_time: float
    local_start_sec: float
    local_end_sec: float
    subject: str | list[str]
    action: str
    camera: str
    highlight: str | list[str]
    labels: list[str]
    label_keys: list[str]
    label_triggers_local_sec: dict[str, float]
    label_triggers_global_sec: dict[str, float]
    transition: str = "smooth"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _norm(s: str) -> str:
    return re.sub(r"[^\wáéíóúüñÁÉÍÓÚÜÑ]", "", s).lower()


class SpecializedVisualDirector:
    """Director Audiovisual Inteligente (Fase 3.1 y Fase 3.2)."""

    def __init__(self) -> None:
        self.shot_catalog = OFFICIAL_SHOT_CATALOG
        self.profiles_9_16 = CAMERA_PROFILES_9_16

    def build_camera_plan(
        self,
        shot_type: str,
        focus_group: str | list[str] = "all",
        intent: str | None = None,
        custom_keys: list[dict[str, Any]] | None = None,
        lens_override: float | None = None,
        track_override: bool | None = None,
        beats: list[dict[str, Any]] | None = None,
        scene_duration_sec: float = 14.0,
    ) -> dict[str, Any]:
        base = self.shot_catalog.get(shot_type, self.shot_catalog["hero_shot"])
        plan: dict[str, Any] = {
            "shot": base["shot_id"],
            "es_alias": base["es_alias"],
            "label": base["label"],
            "intent": intent or base["default_intent"],
            "frame": focus_group,
            "lens": float(lens_override or base["lens"]),
            "margin": float(base.get("margin", 0.055)),
            "track": bool(track_override if track_override is not None else base.get("track", False)),
            "keys": custom_keys if custom_keys else list(base["keys"]),
        }
        # Si la escena tiene múltiples beats semánticos con cambios de sujeto/cámara, adjuntar sub-keyframes de cámara por beat
        if beats and len(beats) > 1 and scene_duration_sec > 0.5:
            beat_cam_steps = []
            for b in beats:
                b_cam = self.shot_catalog.get(b.get("camera", shot_type), base)
                t0 = max(0.0, min(1.0, float(b.get("local_start_sec", 0.0)) / scene_duration_sec))
                t1 = max(t0 + 0.05, min(1.0, float(b.get("local_end_sec", scene_duration_sec)) / scene_duration_sec))
                k0 = b_cam["keys"][0]
                k1 = b_cam["keys"][-1]
                beat_cam_steps.append({
                    "beat_id": b.get("beat_id"),
                    "t0": round(t0, 4),
                    "t1": round(t1, 4),
                    "frame": b.get("subject") or focus_group,
                    "camera": b_cam["shot_id"],
                    "lens": float(b_cam["lens"]),
                    "margin": float(b_cam.get("margin", 0.055)),
                    "az0": float(k0["az"]),
                    "el0": float(k0["el"]),
                    "pad0": float(k0["pad"]),
                    "az1": float(k1["az"]),
                    "el1": float(k1["el"]),
                    "pad1": float(k1["pad"]),
                    "transition": b.get("transition", "smooth"),
                })
            plan["beat_camera_steps"] = beat_cam_steps
        return plan

    def segment_narration_into_semantic_fragments(self, text: str) -> list[str]:
        """Divide el texto de una escena en 2 a 4 fragmentos semánticos que expresan una idea completa
        (Punto 3.2: Segmentación semántica, nunca por cantidad fija de palabras)."""
        raw = text.strip()
        if not raw:
            return []

        # 1. Dividir primero en oraciones completas (. ! ? : ;)
        parts = re.split(r"(?<=[.!?:;])\s+", raw)
        fragments: list[str] = []

        for p in parts:
            p = p.strip()
            if not p:
                continue
            words = p.split()
            # Si una oración supera ~16 palabras, buscar un conector semántico o coma explicativa para partirla en dos ideas completas
            if len(words) >= 15:
                mid_split = re.split(
                    r"(?:,\s+(?=mientras\b|haciendo\b|permitiendo\b|para\b|donde\b|y\s+enseguida\b|y\s+luego\b|abajo\b|arriba\b|allí\b))|(?:\s+(?=mientras\s+que\b|para\s+que\b))",
                    p,
                    maxsplit=1,
                )
                if len(mid_split) == 2 and len(mid_split[0].split()) >= 5 and len(mid_split[1].split()) >= 5:
                    fragments.append(mid_split[0].strip())
                    fragments.append(mid_split[1].strip())
                    continue
            fragments.append(p)

        # Fusionar fragmentos excesivamente cortos (< 4 palabras) con el adyacente
        merged: list[str] = []
        for frag in fragments:
            if merged and len(frag.split()) < 4:
                merged[-1] = f"{merged[-1]} {frag}"
            else:
                merged.append(frag)
        return merged

    def build_audiovisual_beats_for_scene(
        self,
        scene: dict[str, Any],
        model_type: str,
        word_timestamps: list[dict[str, Any]],
        scene_global_start_sec: float,
        scene_duration_sec: float,
        prev_camera: str | None = None,
    ) -> list[dict[str, Any]]:
        """Construye las unidades narrativas estructuradas (`AudiovisualBeat`) de una escena ancladas
        a las marcas temporales reales (`word_timestamps`) del audio sintetizado."""
        explicit_beats = scene.get("beats")
        if explicit_beats:
            fragments = [b["narration"].strip() for b in explicit_beats if b.get("narration")]
        else:
            fragments = self.segment_narration_into_semantic_fragments(scene.get("text", ""))

        if not fragments:
            fragments = [scene.get("text", "").strip()]

        # Alinear cada fragmento con las palabras reales en word_timestamps
        n_words = len(word_timestamps)
        word_cursor = 0
        beats_out: list[dict[str, Any]] = []
        knowledge = MODEL_SEMANTIC_KNOWLEDGE.get(model_type, [])
        last_cam = prev_camera

        for b_idx, frag_text in enumerate(fragments):
            frag_tokens = [w for w in frag_text.split() if w.strip()]
            frag_len = len(frag_tokens)

            if n_words > 0:
                start_w_idx = min(word_cursor, n_words - 1)
                if b_idx == len(fragments) - 1:
                    end_w_idx = n_words - 1
                else:
                    end_w_idx = min(n_words - 1, start_w_idx + max(1, frag_len) - 1)
                word_cursor = min(n_words, end_w_idx + 1)

                local_start = float(word_timestamps[start_w_idx]["start_sec"])
                if b_idx == 0:
                    local_start = 0.0
                elif beats_out:
                    # Continuidad sin huecos muertos entre el final del beat anterior y el inicio de este
                    local_start = max(beats_out[-1]["local_end_sec"], local_start)

                if b_idx == len(fragments) - 1:
                    local_end = scene_duration_sec
                else:
                    next_start = float(word_timestamps[min(n_words - 1, end_w_idx + 1)]["start_sec"])
                    local_end = round((float(word_timestamps[end_w_idx]["end_sec"]) + next_start) * 0.5, 3)
                    local_end = max(local_start + 0.6, min(scene_duration_sec, local_end))
                beat_words = word_timestamps[start_w_idx : end_w_idx + 1]
            else:
                frac0 = b_idx / len(fragments)
                frac1 = (b_idx + 1) / len(fragments)
                local_start = round(frac0 * scene_duration_sec, 3)
                local_end = round(frac1 * scene_duration_sec, 3)
                beat_words = []

            # Inferir o tomar especificación explícita del beat
            exp_b = explicit_beats[b_idx] if (explicit_beats and b_idx < len(explicit_beats)) else {}
            inferred = self._infer_semantics_from_text(frag_text, knowledge, scene)

            subject = exp_b.get("subject") or inferred["subject"]
            highlight = exp_b.get("highlight") or inferred["highlight"]
            action = exp_b.get("action") or inferred["action"]
            req_cam = exp_b.get("camera") or (scene.get("shot_type") if b_idx == 0 else inferred["camera"])
            cam_id = self._normalize_shot_id(str(req_cam), scene.get("phase", "overview"), b_idx)

            # Evitar mantener la misma cámara entre beats consecutivos; si el sujeto es un componente, alternar entre planos focalizados
            if cam_id == last_cam and len(fragments) > 1:
                alt_cam = inferred["camera"]
                alt_norm = self._normalize_shot_id(alt_cam, scene.get("phase", "overview"), b_idx + 1)
                if alt_norm != last_cam:
                    cam_id = alt_norm
                else:
                    component_cams = ["close_up", "extreme_close_up", "internal_tracking", "side_view", "isometric", "tracking"]
                    pool = component_cams if (subject and subject != "all") else FALLBACK_ROTATION_ORDER
                    cam_id = next((c for c in pool if c != last_cam), "close_up")
            last_cam = cam_id

            label_keys = exp_b.get("label_keys") or inferred["label_keys"]
            labels_display = exp_b.get("labels") or inferred["labels"]

            # Calcular el segundo exacto en que el narrador pronuncia cada componente etiquetado
            triggers_local: dict[str, float] = {}
            triggers_global: dict[str, float] = {}
            for lk in label_keys:
                trig_s = self._find_word_trigger_time(lk, frag_text, beat_words, local_start, knowledge)
                triggers_local[lk] = round(trig_s, 3)
                triggers_global[lk] = round(scene_global_start_sec + trig_s, 3)

            beat_obj = AudiovisualBeat(
                beat_id=f"{scene['id']}_B{b_idx + 1:02d}",
                narration=frag_text,
                start_time=round(scene_global_start_sec + local_start, 3),
                end_time=round(scene_global_start_sec + local_end, 3),
                local_start_sec=round(local_start, 3),
                local_end_sec=round(local_end, 3),
                subject=subject,
                action=action,
                camera=cam_id,
                highlight=highlight,
                labels=labels_display,
                label_keys=label_keys,
                label_triggers_local_sec=triggers_local,
                label_triggers_global_sec=triggers_global,
                transition=exp_b.get("transition", "smooth"),
            )
            beats_out.append(beat_obj.to_dict())

        return beats_out

    def _infer_semantics_from_text(
        self,
        frag_text: str,
        knowledge: list[dict[str, Any]],
        scene: dict[str, Any],
    ) -> dict[str, Any]:
        low = frag_text.lower()
        matched_subjects: list[str] = []
        matched_highlights: list[str] = []
        matched_actions: list[str] = []
        matched_cams: list[str] = []
        matched_lkeys: list[str] = []
        matched_ldisp: list[str] = []

        for rule in knowledge:
            for kw in rule["keywords"]:
                if kw in low:
                    if rule["subject"] not in matched_subjects:
                        matched_subjects.append(rule["subject"])
                    if rule["highlight"] not in matched_highlights:
                        matched_highlights.append(rule["highlight"])
                    matched_actions.append(rule["action"])
                    matched_cams.append(rule["default_camera"])
                    if rule.get("label_key") and rule["label_key"] not in matched_lkeys:
                        matched_lkeys.append(rule["label_key"])
                    if rule.get("label_display") and rule["label_display"] not in matched_ldisp:
                        matched_ldisp.append(rule["label_display"])
                    break

        default_focus = scene.get("focus_group", "all")
        subj: str | list[str] = matched_subjects if len(matched_subjects) > 1 else (matched_subjects[0] if matched_subjects else default_focus)
        high: str | list[str] = matched_highlights if len(matched_highlights) > 1 else (matched_highlights[0] if matched_highlights else default_focus)
        act = matched_actions[0] if matched_actions else f"process_{scene.get('phase', 'overview')}"
        cam = matched_cams[0] if matched_cams else scene.get("shot_type", "hero_shot")

        return {
            "subject": subj,
            "highlight": high,
            "action": act,
            "camera": cam,
            "label_keys": matched_lkeys,
            "labels": matched_ldisp,
        }

    def _find_word_trigger_time(
        self,
        label_key: str,
        frag_text: str,
        beat_words: list[dict[str, Any]],
        default_start_sec: float,
        knowledge: list[dict[str, Any]],
    ) -> float:
        """Encuentra el segundo exacto en `beat_words` donde el narrador pronuncia el término asociado a `label_key`."""
        if not beat_words:
            return default_start_sec

        # Palabras objetivo para esa etiqueta
        target_stems: list[str] = [label_key.lower()[:5]]
        for rule in knowledge:
            if rule.get("label_key") == label_key:
                for kw in rule["keywords"]:
                    for tok in kw.split():
                        cl = _norm(tok)
                        if len(cl) >= 4:
                            target_stems.append(cl[:5])

        for w in beat_words:
            cw = w.get("clean", "")
            if len(cw) >= 3 and any(cw.startswith(st) or st in cw for st in target_stems):
                return float(w["start_sec"])

        return default_start_sec

    def direct_script_scenes(
        self,
        topic_or_title: str,
        model_type: str,
        scenes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Planifica a nivel macro las escenas y valida la variedad de cámaras sin repeticiones consecutivas."""
        strategy: VisualCategoryStrategy = classify_educational_topic(topic_or_title, model_type_hint=model_type)
        prev_shot: str | None = None
        directed_plans: list[dict[str, Any]] = []
        used_shots: list[str] = []

        for idx, sc in enumerate(scenes):
            requested_shot = sc.get("shot_type") or sc.get("composition_type") or "hero_shot"
            shot_id = self._normalize_shot_id(requested_shot, sc.get("phase", "overview"), idx)

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
                beats=sc.get("audiovisual_beats"),
                scene_duration_sec=float(sc.get("duration_sec", 14.0)),
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
        if raw_shot in self.profiles_9_16:
            return raw_shot
        if raw_shot in self.shot_catalog:
            return self.shot_catalog[raw_shot]["shot_id"]
        alias_map = {
            "hero_view": "hero_shot",
            "presentacion_general": "hero_shot",
            "exploded_view": "exploded_view",
            "despiece": "exploded_view",
            "cutaway_view": "cutaway",
            "cutaway_shot": "cutaway",
            "corte_transversal": "cutaway",
            "tracking_shot": "tracking",
            "seguimiento_movimiento": "tracking",
            "close_up_view": "close_up",
            "primer_plano": "close_up",
            "macro_extremo": "extreme_close_up",
            "top_view": "top_view",
            "vista_superior": "top_view",
            "side_view": "side_view",
            "vista_lateral": "side_view",
            "internal_view": "internal_tracking",
            "vista_interna": "internal_tracking",
            "isometric_view": "isometric",
            "vista_isometrica": "isometric",
            "turntable_orbit": "orbit",
            "orbita": "orbit",
            "assembly_view": "state_comparison",
            "comparacion_estados": "state_comparison",
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
        return "hero_shot"

    @staticmethod
    def _count_consecutive_duplicates(shots: list[str]) -> int:
        return sum(1 for i in range(1, len(shots)) if shots[i] == shots[i - 1])


# Alias oficial solicitado en Fase 3.2 (Punto 2)
VisualDirector = SpecializedVisualDirector
