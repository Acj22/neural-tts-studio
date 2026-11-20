"""AI VIDEO STUDIO — Catálogo de Estilos Cinematográficos y Animación en Código Lemo-Opuscar.
Inspirado en el repositorio open-source https://github.com/lemomo-ai/lemo-opuscar

Concepto: Cine y animación generados 100% mediante código procedimental determinista
(Canvas HTML5 / WebGL / p5.js / Matplotlib / Cairo), calculados en función del tiempo t,
sincronizados con locución neuronal y exportados a video MP4 (9:16 vertical o 16:9).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


OPUSCAR_STATIONS = [
    {
        "id": "technical_engineering",
        "name": "📐 Técnico, Blueprints & Ingeniería",
        "description": "Planos CAD, rejillas milimétricas, cotas dinámicas y esquemas de fluidos/presión.",
    },
    {
        "id": "vintage_manuscripts",
        "name": "📜 Manuscritos & Ciencia Clásica",
        "description": "Códices renacentistas estilo Da Vinci, grabados en aguafuerte y pizarras de física.",
    },
    {
        "id": "cyber_hud_telemetry",
        "name": "🛰️ Telemetría HUD & Datos Cibernéticos",
        "description": "Interfaces holográficas tácticas, osciloscopios, diales de RPM/PSI y radares térmicos.",
    },
    {
        "id": "graphic_kinetic",
        "name": "🎨 Diseño Gráfico Cinético & Bauhaus",
        "description": "Tipografía cinética de alto impacto, minimalismo suizo y geometría modernista.",
    },
    {
        "id": "anime_cel_dynamics",
        "name": "⚡ Anime & Dinámica Cel-Shaded",
        "description": "Líneas de velocidad radial cinemáticas, halos de energía y estética manga técnica.",
    },
    {
        "id": "cinema_retro",
        "name": "🎞️ Cine de Autor & Pixel Art",
        "description": "Film noir de alto contraste, claroscuro dramático y animación de píxeles 16-bit.",
    },
]


OPUSCAR_STYLES: List[Dict[str, Any]] = [
    {
        "id": "ojo_sahara_diorama",
        "name": "Diorama Ojo del Sahara & Geología (Estructura de Richat 🌍)",
        "station": "graphic_kinetic",
        "badge": "Geología / Maravillas 🌍",
        "description": "Diorama geológico paper-cut con dunas de arena del Sahara, anillos concéntricos en perspectiva elíptica 2.5D de 40 km de diámetro, domo intrusivo, escaneo orbital y micro-animaciones dinámicas.",
        "palette": {
            "background": "#fbf5e8",
            "grid": "#e6dcbf",
            "primary": "#b45309",
            "accent": "#0284c7",
            "text": "#0f172a",
        },
        "default_title": "El Rincón Más Asombroso de la Tierra: El Ojo del Sahara",
        "default_narration": "En medio del desierto de Mauritania existe una gigantesca estructura concéntrica de 40 kilómetros visible desde el espacio: la mística Estructura de Richat.",
        "default_fps": 60,
        "default_duration": 60.0,
    },
    {
        "id": "chapultepec_diorama",
        "name": "Diorama Castillo de Chapultepec & Virreinato (Alcázar Real ★)",
        "station": "graphic_kinetic",
        "badge": "Histórico / Alcázar ★",
        "description": "Estilo multicapa paper-cut artesanal con el Cerro del Chapulín, Castillo de Chapultepec, bosque de ahuehuetes, carruaje imperial, bandera ondeante y cotas de altitud.",
        "palette": {
            "background": "#fbf5e8",
            "grid": "#e6dcbf",
            "primary": "#d97706",
            "accent": "#15803d",
            "text": "#0f172a",
        },
        "default_title": "El Castillo de Chapultepec: El Único Alcázar Real de América",
        "default_narration": "¿Sabías que en el corazón de la Ciudad de México se alza el único castillo real de monarquía europea jamás habitado en todo el continente americano?",
        "default_fps": 60,
        "default_duration": 88.0,
    },
    {
        "id": "mayan_diorama",
        "name": "Diorama Maya & Arqueología Prehispánica (LiDAR ★)",
        "station": "graphic_kinetic",
        "badge": "Histórico / Arqueología ★",
        "description": "Estilo multicapa paper-cut con selva tropical, pirámides ceremoniales, canchas de juego de pelota, calzadas sacbéob, escáner láser LiDAR y contadores dinámicos.",
        "palette": {
            "background": "#fbf5e8",
            "grid": "#e6dcbf",
            "primary": "#15803d",
            "accent": "#06b6d4",
            "text": "#14532d",
        },
        "default_title": "El Secreto Oculto de México: La Ciudad Maya de Valeriana",
        "default_narration": "En 2024, arqueólogos con tecnología láser LiDAR descubrieron Valeriana en la selva de Campeche: 6,674 estructuras prehispánicas ocultas bajo los árboles.",
        "default_fps": 60,
        "default_duration": 77.0,
    },
    {
        "id": "paper_cutout_diorama",
        "name": "Diorama de Stickers & Papel Recortado (Estilo Lemo-Opuscar)",
        "station": "graphic_kinetic",
        "badge": "Viral / Animación ★",
        "description": "Estilo multicapa con stickers de contorno blanco brillante, sombras 2.5D, gradas masivas de personajes, placas de matrícula y objetos pop.",
        "palette": {
            "background": "#fbf5e8",
            "grid": "#f3dcb8",
            "primary": "#dc2626",
            "accent": "#0d9488",
            "text": "#0f766e",
        },
        "default_title": "El Truco Biológico de la Capsaicina",
        "default_narration": "¿Sabías que cuando comes chile en realidad no te estás quemando? Tu cuerpo cree que hay fuego y activa todas las alarmas a la vez.",
        "default_fps": 60,
        "default_duration": 8.0,
    },
    {
        "id": "blueprint_cad",
        "name": "Plano Técnico Blueprint (CAD Cianotipo)",
        "station": "technical_engineering",
        "badge": "Ingeniería ★",
        "description": "Fondo azul cianotipo técnico, cuadrícula milimétrica, cotas numéricas vivas, flechas de tolerancia y dibujo vectorial paramétrico.",
        "palette": {
            "background": "#0b192c",
            "grid": "#1e3e62",
            "primary": "#00d2ff",
            "accent": "#ffde59",
            "text": "#e0f2fe",
        },
        "default_title": "Turbocompresor: Esquema de Sección y Flujos",
        "default_narration": "El compresor aspira aire atmosférico a través de la caracola fría, incrementando la densidad de oxígeno antes de entrar al cilindro.",
        "default_fps": 30,
        "default_duration": 6.0,
    },
    {
        "id": "vector_flow",
        "name": "Dinámica de Fluidos & Vórtice Vectorial",
        "station": "technical_engineering",
        "badge": "Termodinámica",
        "description": "Partículas vectoriales trazadas en tiempo real siguiendo ecuaciones de flujo laminar, gradientes térmicos de azul frío a rojo incandescente.",
        "palette": {
            "background": "#030712",
            "grid": "#111827",
            "primary": "#38bdf8",
            "accent": "#ef4444",
            "text": "#f9fafb",
        },
        "default_title": "Gradiente Térmico: Escape Caliente vs Admisión Fría",
        "default_narration": "Los gases de escape a ochocientos grados hacen girar la turbina a más de doscientas mil revoluciones por minuto.",
        "default_fps": 30,
        "default_duration": 6.0,
    },
    {
        "id": "da_vinci_codex",
        "name": "Códice Da Vinci (Manuscrito Renacentista)",
        "station": "vintage_manuscripts",
        "badge": "Histórico ★",
        "description": "Textura de pergamino envejecido, bocetos a pluma en tinta sepia, líneas de compás geométricas y anotaciones caligráficas especulares.",
        "palette": {
            "background": "#f4ecd8",
            "grid": "#dfd2b5",
            "primary": "#4a3525",
            "accent": "#8c2d19",
            "text": "#3d2b1f",
        },
        "default_title": "Tratado de la Máquina de Fuego y Viento",
        "default_narration": "Observad cómo el movimiento del aire engendra fuerza motriz constante, transformando el soplo en potencia mecánica.",
        "default_fps": 60,
        "default_duration": 6.0,
    },
    {
        "id": "chalkboard_physics",
        "name": "Pizarra Universitaria de Física Cuántica",
        "station": "vintage_manuscripts",
        "badge": "Académico",
        "description": "Pizarra de pizarra verde oscura o carbón con trazos de tiza blanca, ecuaciones diferenciales animadas y vectores de fuerza anotados a mano.",
        "palette": {
            "background": "#14211b",
            "grid": "#1d3329",
            "primary": "#ffffff",
            "accent": "#fef08a",
            "text": "#f0fdf4",
        },
        "default_title": "Ecuación de Estado y Rendimiento Volumétrico",
        "default_narration": "La primera ley de la termodinámica dicta que la energía no se destruye: el calor del escape se transforma en presión útil.",
        "default_fps": 60,
        "default_duration": 6.0,
    },
    {
        "id": "hud_telemetry",
        "name": "HUD de Telemetría Militar & Aeroespacial",
        "station": "cyber_hud_telemetry",
        "badge": "Cyber / Sci-Fi",
        "description": "Visualización holográfica con retículas de puntería cinemáticas, diales de RPM circulares, osciloscopio FFT en tiempo real y lectura de telemetría.",
        "palette": {
            "background": "#020617",
            "grid": "#0f172a",
            "primary": "#10b981",
            "accent": "#06b6d4",
            "text": "#ecfdf5",
        },
        "default_title": "Telemetría de Banco de Pruebas: 220,000 RPM",
        "default_narration": "Presión de sobrealimentación estabilizada en dos punto dos bares. Temperatura de entrada en zona nominal.",
        "default_fps": 30,
        "default_duration": 6.0,
    },
    {
        "id": "radar_sweep",
        "name": "Barrido de Radar Sintético & Sensores Térmicos",
        "station": "cyber_hud_telemetry",
        "badge": "Sensores",
        "description": "Línea de barrido angular continua en 360 grados, ecos de fósforo persistentes y mapa de calor infrarrojo.",
        "palette": {
            "background": "#050d0a",
            "grid": "#0d261e",
            "primary": "#22c55e",
            "accent": "#eab308",
            "text": "#dcfce7",
        },
        "default_title": "Escaneo Térmico de Cavidad del Turbocompresor",
        "default_narration": "El sensor infrarrojo detecta la disipación térmica a través de la carcasa de fundición nodular.",
        "default_fps": 30,
        "default_duration": 6.0,
    },
    {
        "id": "swiss_kinetic",
        "name": "Tipografía Cinética Suiza (Swiss Design)",
        "station": "graphic_kinetic",
        "badge": "Diseño Minimal",
        "description": "Composiciones geométricas asimétricas, fuentes sans-serif contundentes, rejilla tipográfica estricta y transiciones rítmicas sincopadas.",
        "palette": {
            "background": "#f8fafc",
            "grid": "#e2e8f0",
            "primary": "#0f172a",
            "accent": "#dc2626",
            "text": "#020617",
        },
        "default_title": "PRESIÓN · POTENCIA · EFICIENCIA",
        "default_narration": "Más oxígeno en la cámara significa más combustible quemado y un cuarenta por ciento más de potencia neta.",
        "default_fps": 30,
        "default_duration": 5.0,
    },
    {
        "id": "bauhaus_geometry",
        "name": "Geometría Rítmica Bauhaus",
        "station": "graphic_kinetic",
        "badge": "Vanguardia",
        "description": "Formas geométricas puras (círculos concéntricos, triángulos de fuerza, arcos rotativos) en colores primarios puros sobre fondo hueso.",
        "palette": {
            "background": "#f5f2eb",
            "grid": "#e3ded2",
            "primary": "#1e293b",
            "accent": "#e11d48",
            "text": "#0f172a",
        },
        "default_title": "La Forma Sigue a la Función Mecánica",
        "default_narration": "Cada curva de la voluta está calculada para convertir la velocidad cinética en presión estática uniforme.",
        "default_fps": 60,
        "default_duration": 5.0,
    },
    {
        "id": "anime_speedlines",
        "name": "Líneas de Hipervelocidad Anime (Kinetic Impact)",
        "station": "anime_cel_dynamics",
        "badge": "Impacto / Acción",
        "description": "Efecto radial de velocidad cinematográfica, rayos cinéticos convergentes, sacudida de cámara programada y destellos de potencia máxima.",
        "palette": {
            "background": "#09090b",
            "grid": "#18181b",
            "primary": "#fafafa",
            "accent": "#f59e0b",
            "text": "#ffffff",
        },
        "default_title": "¡PICO DE BOOST AL MÁXIMO!",
        "default_narration": "Cuando la válvula wastegate se cierra por completo, la turbina alcanza su régimen límite instantáneamente.",
        "default_fps": 30,
        "default_duration": 4.5,
    },
    {
        "id": "film_noir",
        "name": "Cine Negro & Claroscuro Técnico (Film Noir)",
        "station": "cinema_retro",
        "badge": "Cinematográfico",
        "description": "Iluminación rasante dramática, sombras proyectadas hiperdefinidas, grano analógico de 35mm y estética industrial en blanco y negro.",
        "palette": {
            "background": "#000000",
            "grid": "#1a1a1a",
            "primary": "#e5e5e5",
            "accent": "#ffffff",
            "text": "#fafafa",
        },
        "default_title": "Anatomía del Metal: El Eje Flotante",
        "default_narration": "En la penumbra del cárter, una película micrométrica de aceite sostiene el rotor sin contacto metálico directo.",
        "default_fps": 60,
        "default_duration": 6.0,
    },
]


def get_all_opuscar_styles() -> List[Dict[str, Any]]:
    return OPUSCAR_STYLES


def get_opuscar_style_by_id(style_id: str) -> Optional[Dict[str, Any]]:
    for s in OPUSCAR_STYLES:
        if s["id"] == style_id:
            return s
    return OPUSCAR_STYLES[0]
