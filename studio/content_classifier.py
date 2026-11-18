"""Clasificador de Contenido Educativo y Estrategias Visuales por Categoría (Fase 3.1).

Clasifica automáticamente temas educativos y asigna estrategias visuales diferenciadas:
- Paleta de materiales PBR.
- Esquema de iluminación de estudio.
- Comportamiento de cámara preferente.
- Efectos visuales especializados (flujos térmicos, partículas, líneas de fuerza, capas).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VisualCategoryStrategy:
    category_id: str
    name: str
    description: str
    primary_lighting_style: str
    dominant_camera_modes: list[str]
    preferred_fx: list[str]
    color_palette: dict[str, str]
    pedagogical_focus: str


# ==============================================================================
# TAXONOMÍA OFICIAL DE CATEGORÍAS EDUCATIVAS (9 CATEGORÍAS)
# ==============================================================================

CATEGORY_STRATEGIES: dict[str, VisualCategoryStrategy] = {
    "mecanica": VisualCategoryStrategy(
        category_id="mecanica",
        name="Mecánica & Maquinaria",
        description="Engranajes, transmisiones, motores, mecanismos biela-manivela, bombas y válvulas.",
        primary_lighting_style="studio_cad_metallic",
        dominant_camera_modes=["cutaway_view", "close_up_view", "tracking_shot", "exploded_view"],
        preferred_fx=["stress_lines", "gear_mesh_highlight", "torque_vectors"],
        color_palette={
            "base_metal": "#8E9DAE",
            "accent_brass": "#F59E0B",
            "accent_anodized": "#2563EB",
            "friction_part": "#C86432",
            "backdrop": "#1E2A36",
        },
        pedagogical_focus="Comprensión cinemática: transmisión de par, reducción de velocidad y contacto entre piezas.",
    ),
    "electrodomesticos": VisualCategoryStrategy(
        category_id="electrodomesticos",
        name="Electrodomésticos & Climatización",
        description="Refrigeradores, bombas de calor, aire acondicionado, lavadoras, microondas.",
        primary_lighting_style="studio_appliance_clean",
        dominant_camera_modes=["cutaway_view", "top_view", "hero_view", "internal_loop"],
        preferred_fx=["thermal_gradient", "heat_dissipation_waves", "frost_glow", "fluid_pulses"],
        color_palette={
            "body_clean": "#F1F5F9",
            "heat_high_pressure": "#EF4444",
            "cold_low_pressure": "#38BDF8",
            "coils_copper": "#EA580C",
            "backdrop": "#1E293B",
        },
        pedagogical_focus="Ciclos termodinámicos cerrados: transferencia de calor, cambio de fase y presiones.",
    ),
    "impresion_fabricacion": VisualCategoryStrategy(
        category_id="impresion_fabricacion",
        name="Impresión 3D & Fabricación Digital",
        description="Impresoras 3D FDM/SLA, corte láser, fresado CNC, extrusión, manufactura aditiva.",
        primary_lighting_style="maker_lab_accent",
        dominant_camera_modes=["macro_nozzle", "axis_tracking", "isometric_view", "layer_sweep"],
        preferred_fx=["extrusion_glow", "layer_build_growth", "gantry_motion_lines"],
        color_palette={
            "frame_vslot": "#111827",
            "bed_pei": "#D97706",
            "nozzle_brass": "#F59E0B",
            "filament_plastic": "#F97316",
            "backdrop": "#0F172A",
        },
        pedagogical_focus="Manufactura cartesiana: coordenadas X/Y/Z, fusión térmica y estratificación capa a capa.",
    ),
    "electronica": VisualCategoryStrategy(
        category_id="electronica",
        name="Electrónica & Circuitos",
        description="Semiconductores, microcontroladores, condensadores, inductores, fuentes conmutadas.",
        primary_lighting_style="pcb_micro_glow",
        dominant_camera_modes=["macro_zoom", "top_view", "layer_split"],
        preferred_fx=["electron_pulse", "pcb_trace_glow", "signal_wave"],
        color_palette={
            "pcb_substrate": "#065F46",
            "copper_traces": "#F59E0B",
            "silicon_die": "#1F2937",
            "solder_tin": "#E2E8F0",
            "backdrop": "#022C22",
        },
        pedagogical_focus="Flujo eléctrico: transporte de carga, conmutación y caída de potencial.",
    ),
    "procesos_industriales": VisualCategoryStrategy(
        category_id="procesos_industriales",
        name="Procesos Industriales & Metalurgia",
        description="Fundición, soldadura, inyección de polímeros, prensado hidráulico, siderurgia.",
        primary_lighting_style="forge_industrial_warm",
        dominant_camera_modes=["high_angle_pan", "tracking_shot", "side_cutaway"],
        preferred_fx=["molten_glow", "spark_burst", "smoke_stream", "mold_press"],
        color_palette={
            "molten_metal": "#F97316",
            "cast_iron": "#334155",
            "cool_steel": "#94A3B8",
            "hydraulic_arm": "#EAB308",
            "backdrop": "#1C1917",
        },
        pedagogical_focus="Transformación de materiales: presión hidrostática, fusión y solidificación en molde.",
    ),
    "energia": VisualCategoryStrategy(
        category_id="energia",
        name="Energía & Baterías",
        description="Celdas de iones de litio, reactores nucleares, paneles solares, turbinas eólicas.",
        primary_lighting_style="energy_ambient_cool",
        dominant_camera_modes=["turntable_orbit", "internal_cell", "exploded_view"],
        preferred_fx=["lithium_ion_flux", "photovoltaic_flow", "magnetic_fields"],
        color_palette={
            "anode_copper": "#EA580C",
            "cathode_alum": "#CBD5E1",
            "separator_poly": "#FEF08A",
            "electric_cyan": "#06B6D4",
            "backdrop": "#082F49",
        },
        pedagogical_focus="Conversión energética: intercambio iónico, eficiencia de conversión y balance térmico.",
    ),
    "transporte": VisualCategoryStrategy(
        category_id="transporte",
        name="Transporte & Aerodinámica",
        description="Trenes maglev, aviación, propulsión a chorro, cohetes, suspensión automotriz.",
        primary_lighting_style="wind_tunnel_aero",
        dominant_camera_modes=["chase_cam", "side_view", "isometric_view"],
        preferred_fx=["streamline_smoke", "shockwave_pulse", "lift_vectors"],
        color_palette={
            "fuselage_carbon": "#1E293B",
            "titanium_turbine": "#94A3B8",
            "thrust_flame": "#38BDF8",
            "backdrop": "#0F172A",
        },
        pedagogical_focus="Dinámica de fluidos: sustentación, empuje, resistencia aerodinámica y flotación magnética.",
    ),
    "ciencia": VisualCategoryStrategy(
        category_id="ciencia",
        name="Ciencia Fundamental & Física",
        description="Termodinámica, óptica, campos electromagnéticos, átomos, relatividad, acústica.",
        primary_lighting_style="scientific_minimalist",
        dominant_camera_modes=["orbit_sweep", "macro_zoom", "hero_view"],
        preferred_fx=["wave_interference", "atomic_orbitals", "light_refraction"],
        color_palette={
            "quantum_purple": "#8B5CF6",
            "photon_yellow": "#FDE047",
            "vacuum_black": "#030712",
            "backdrop": "#0B0F19",
        },
        pedagogical_focus="Leyes universales: conservación de energía, entropía y dualidad onda-partícula.",
    ),
    "tecnologia": VisualCategoryStrategy(
        category_id="tecnologia",
        name="Tecnología Digital & Computación",
        description="Discos SSD, fibra óptica, pantallas OLED, sensores CMOS, servidores.",
        primary_lighting_style="cleanroom_high_key",
        dominant_camera_modes=["macro_zoom", "pan_up", "exploded_view"],
        preferred_fx=["data_bus_stream", "optical_pulse", "pixel_subgrid"],
        color_palette={
            "fiber_glass": "#38BDF8",
            "laser_emitter": "#EC4899",
            "metal_chassis": "#E2E8F0",
            "backdrop": "#0F172A",
        },
        pedagogical_focus="Transmisión y almacenamiento de datos: luz guiada, pulsos binarios y litografía.",
    ),
}


# ==============================================================================
# CLASIFICADOR INTELIGENTE BASADO EN LÉXICO Y MODELOS
# ==============================================================================

CATEGORY_KEYWORDS_MAP: dict[str, list[str]] = {
    "mecanica": [
        "transmisión", "transmision", "engranaje", "engranajes", "planetario", "epicicloidal",
        "motor", "pistón", "piston", "cigüeñal", "biela", "válvula", "embrague", "clutch",
        "cárter", "bomba", "hidráulica", "freno", "diferencial", "árbol de levas",
    ],
    "electrodomesticos": [
        "refrigerador", "nevera", "congelador", "compresor", "condensador", "evaporador",
        "capilar", "refrigerante", "aire acondicionado", "lavadora", "microondas",
        "termostato", "calor", "enfriar", "escarcha", "termodinámica",
    ],
    "impresion_fabricacion": [
        "impresora 3d", "impresora", "fdm", "filamento", "extrusor", "hotend", "boquilla",
        "cama caliente", "pei", "capa por capa", "aditiva", "gantry", "eje x", "eje y", "eje z",
        "cnc", "fresadora", "corte láser", "pla", "petg", "abs",
    ],
    "electronica": [
        "circuito", "chip", "transistor", "microchip", "condensador", "resistencia",
        "placa base", "pcb", "voltaje", "corriente", "semiconductor", "diodo",
    ],
    "procesos_industriales": [
        "fundición", "soldadura", "molde", "inyección de plástico", "forja", "laminado",
        "alto horno", "prensa", "extrusión de aluminio", "acería",
    ],
    "energia": [
        "batería", "bateria", "litio", "ion-litio", "celda", "reactor nuclear", "fisión",
        "panel solar", "fotovoltaico", "turbina eólica", "generador", "hidroeléctrica",
    ],
    "transporte": [
        "maglev", "tren", "avión", "cohete", "turbofán", "aerodinámica", "sustentación",
        "cohete espacial", "propulsión", "alerón", "hipersónico",
    ],
    "ciencia": [
        "cuántica", "átomo", "fotón", "gravedad", "entropía", "ondas", "láser", "relatividad",
        "termodinámica pura", "refracción", "prisma",
    ],
    "tecnologia": [
        "fibra óptica", "ssd", "disco duro", "oled", "pantalla", "sensor cmos", "antena 5g",
        "servidor", "memoria ram", "procesador cpu",
    ],
}


def classify_educational_topic(title_or_text: str, model_type_hint: str | None = None) -> VisualCategoryStrategy:
    """Clasifica el tema del video educativo en una de las 9 categorías oficiales."""
    if model_type_hint:
        hint = model_type_hint.lower().strip()
        if "transmission" in hint or "gear" in hint or "engine" in hint:
            return CATEGORY_STRATEGIES["mecanica"]
        if "refrigerator" in hint or "fridge" in hint or "thermal" in hint:
            return CATEGORY_STRATEGIES["electrodomesticos"]
        if "printer" in hint or "fdm" in hint or "3d" in hint:
            return CATEGORY_STRATEGIES["impresion_fabricacion"]

    normalized = title_or_text.lower()
    scores: dict[str, int] = {cat: 0 for cat in CATEGORY_STRATEGIES}

    for cat, kws in CATEGORY_KEYWORDS_MAP.items():
        for kw in kws:
            pattern = r"\b" + re.escape(kw) + r"\b"
            matches = len(re.findall(pattern, normalized))
            scores[cat] += matches * (3 if len(kw) > 6 else 2)

    best_cat = max(scores, key=lambda c: scores[c])
    if scores[best_cat] > 0:
        return CATEGORY_STRATEGIES[best_cat]

    # Fallback por defecto: Mecánica general
    return CATEGORY_STRATEGIES["mecanica"]
