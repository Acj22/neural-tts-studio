"""Catálogo de Temas Especializados para el Módulo Animated Shorts (3D/WebGL + Física Rapier + PixelFX + Earshot)."""

from __future__ import annotations
from typing import Any, Dict, List

ANIMATED_SHORTS_TOPICS: List[Dict[str, Any]] = [
    {
        "id": "arqueologia_enigma",
        "category": "Arqueología & Enigmas del Pasado",
        "icon": "🏛️",
        "description": "Descubrimientos documentados, tumbas selladas, ciudades perdidas y tecnología ancestral verificada.",
        "preset_titles": [
            "La Cripta Sellada de Pakal: El Misterio del Templo de las Inscripciones",
            "Sacsayhuamán y los Bloques de 120 Toneladas que Desafían la Ingeniería",
            "El Mecanismo de Anticitera: La Primera Computadora Mecánica del Mundo Antiguo",
            "Gobekli Tepe: El Templo de 11,500 Años que Reescribió la Historia Humana",
        ],
        "default_title": "La Cripta Sellada de Pakal: El Misterio del Templo de las Inscripciones",
        "style_preset": "ink_parchment_3d",
        "foley_theme": "ancient_tomb",
    },
    {
        "id": "ingenieria_extrema",
        "category": "Ingeniería Imposible & Mecánica Extrema",
        "icon": "⚙️",
        "description": "Turbinas de aviación, colisionadores de partículas, superestructuras y mecanismos de ultraprecisión.",
        "preset_titles": [
            "El Gran Colisionador del CERN: Acelerando Protones al 99.99% de la Luz",
            "¿Cómo Soporta un Turbofán de Titanio 1,700°C sin Fundirse en Vuelo?",
            "La Presa de las Tres Gargantas: La Masa de Agua que Frenó la Rotación de la Tierra",
            "El Telescopio James Webb: El Despliegue de 178 Mecanismos a 1.5 Millones de km",
        ],
        "default_title": "¿Cómo Soporta un Turbofán de Titanio 1,700°C sin Fundirse en Vuelo?",
        "style_preset": "blueprint_rapier_physics",
        "foley_theme": "mechanical_precision",
    },
    {
        "id": "fronteras_ciencia",
        "category": "Fronteras de la Ciencia & Física Cuántica",
        "icon": "🔬",
        "description": "Entrelazamiento cuántico, antimateria, fusión nuclear y experimentos que desafían la intuición.",
        "preset_titles": [
            "Entrelazamiento Cuántico: La 'Acción Fantasmagórica' que Einstein Rechazó",
            "El Experimento de la Doble Rendija: Cuando el Observador Cambia la Realidad",
            "Fusión Nuclear en el ITER: Recreando un Sol Artificial a 150 Millones de °C",
            "El Enigma de la Antimateria: ¿Por Qué el Universo no se Aniquiló a Sí Mismo?",
        ],
        "default_title": "Entrelazamiento Cuántico: La 'Acción Fantasmagórica' que Einstein Rechazó",
        "style_preset": "quantum_pixelfx_particles",
        "foley_theme": "sci_fi_subtle",
    },
    {
        "id": "fuerzas_naturaleza",
        "category": "Fuerzas de la Naturaleza Extrema",
        "icon": "🌋",
        "description": "Supervolcanes, fosas abisales, megaterremotos y fenómenos geológicos titánicos.",
        "preset_titles": [
            "La Fosa de las Marianas: La Presión que Aplastaría un Submarino Nuclear",
            "El Supervolcán de Yellowstone: La Cámara Magmática de 60 Kilómetros",
            "La Falla de San Andrés: Por Qué los Geólogos Saben que el 'Big One' Llegará",
            "Relámpagos del Catatumbo: La Fábrica de Tormentas más Extrema del Planeta",
        ],
        "default_title": "La Fosa de las Marianas: La Presión que Aplastaría un Submarino Nuclear",
        "style_preset": "elemental_particle_world",
        "foley_theme": "nature_rumble",
    },
    {
        "id": "odisea_espacial",
        "category": "Odisea Espacial & Astrofísica",
        "icon": "🚀",
        "description": "Agujeros negros, sondas interestelares, estrellas de neutrones y el horizonte de sucesos.",
        "preset_titles": [
            "Sonda Voyager 1: El Objeto Humano que ya Navega el Espacio Interestelar",
            "Estrellas de Neutrones: Una Cucharada que Pesa Mil Millones de Toneladas",
            "El Horizonte de Sucesos de un Agujero Negro: Donde el Tiempo se Detiene",
            "El Océano Oculto de Europa: La Luna de Júpiter con más Agua que la Tierra",
        ],
        "default_title": "Sonda Voyager 1: El Objeto Humano que ya Navega el Espacio Interestelar",
        "style_preset": "space_cosmic_webgl",
        "foley_theme": "deep_space",
    },
]


def get_all_animated_shorts_topics() -> List[Dict[str, Any]]:
    return ANIMATED_SHORTS_TOPICS


def get_topic_by_id(topic_id: str) -> Dict[str, Any] | None:
    return next((t for t in ANIMATED_SHORTS_TOPICS if t["id"] == topic_id), None)
