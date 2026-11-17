"""FASE 6 y FASE 8 — STORYBOARD ENGINE & VISUAL CONSISTENCY ENGINE.

Convierte semánticamente los guiones educativos (Corto y Largo) en un Storyboard técnico
donde cada escena ayuda a comprender lo que se está narrando, clasificando el recurso entre
las 10 tipologías educativas y manteniendo consistencia visual en todo el proyecto.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import video_pipeline
from studio.models import SCENE_RESOURCE_TYPES, VISUAL_CONSISTENCY_STYLES


CAMERA_MOTIONS_CYCLE = [
    "zoom_in",
    "pan_horizontal",
    "cutaway_focus",
    "zoom_out",
    "pan_vertical",
    "parallax",
    "selective_focus",
]


def _detect_topic_mechanism_family(topic: str, question: str = "") -> str:
    s = (topic + " " + question).lower()
    if any(w in s for w in ("motor", "combusti", "pist", "cilindro", "otto", "cigueñal", "cigüeñal")):
        return "combustion_engine"
    if any(w in s for w in ("cajero", "atm", "billete", "dispensador", "banc")):
        return "atm_machine"
    if any(w in s for w in ("gps", "satelit", "satélit", "trilateraci", "posicionamiento")):
        return "gps_system"
    if any(w in s for w in ("pantalla", "tactil", "táctil", "touch", "capacitiv", "ito")):
        return "touchscreen"
    if any(w in s for w in ("transmisi", "caja automatica", "caja automática", "planetario", "convertidor de par")):
        return "auto_transmission"
    return "generic_mechanism"


def _select_semantic_resource_type(
    narration_text: str,
    section_key: str,
    scene_idx: int,
    mechanism_family: str,
) -> str:
    """Selecciona semánticamente el tipo de recurso (entre los 10 tipos de escena)
    según lo que explica la narración en ese instante."""
    if section_key in ("gancho", "pregunta", "conclusion"):
        return "illustrative_image"

    low = narration_text.lower()

    if any(w in low for w in ("vs", "diferencia", "mientras que", "mitos", "mito", "compar", "a diferencia de", "confusión")):
        return "comparison"
    if any(w in low for w in ("microscópic", "átomo", "electrón", "iones", "picofaradio", "campo electrostático", "ito", "nanosegundo")):
        return "microscopic_view"
    if any(w in low for w in ("órbita", "satélite", "planeta", "tierra", "20,200 km", "coordenadas", "red bancaria", "switch interbancario")):
        return "map_view"
    if any(w in low for w in ("%", "por ciento", "bar", "°c", "grados", "14.7", "microsegundos", "velocidad", "relación", "cifra", "entre ")):
        return "data_chart"
    if any(w in low for w in ("corte", "interior", "dentro de", "carcasa", "bóveda", "cámara de combustión", "capas", "convertidor de par")):
        return "cutaway_view"
    if any(w in low for w in ("etapa", "paso", "primero", "segundo", "tercero", "admisión", "compresión", "expansión", "escape", "secuencia")):
        return "step_by_step"
    if any(w in low for w in ("gira", "movimiento", "pistón", "cigüeñal", "rodillo", "engranaje", "planetario", "turbina", "válvula")):
        return "component_animation"
    if section_key in ("conceptos_fundamentales", "contexto", "resumen"):
        return "technical_diagram"
    if scene_idx == 1:
        return "illustrative_image"
    return "technical_diagram" if scene_idx % 2 == 0 else "illustrative_image"


def _extract_labels_and_elements_for_scene(
    narration_text: str,
    resource_type: str,
    mechanism_family: str,
    step_cursor: int,
    research: dict[str, Any],
) -> tuple[list[str], list[str], str, dict[str, Any]]:
    """Construye los elementos importantes, etiquetas legibles y especificación técnica del diagrama
    para que nunca se tapen los componentes y correspondan exactamente al concepto narrado."""
    concepts = research.get("core_concepts") or []
    diag_seq = research.get("diagram_sequence") or []

    if mechanism_family == "combustion_engine":
        engine_steps = [
            {
                "step_index": 1,
                "concept": "Vista general del motor de 4 tiempos",
                "labels": ["1. Culata y Válvulas", "2. Bloque de Cilindros", "3. Pistón y Biela", "4. Cigüeñal y Cárter"],
                "elements": ["Complete engine block cutaway", "Cylinder head", "Piston assembly", "Crankshaft"],
                "phase": "overview",
            },
            {
                "step_index": 2,
                "concept": "Acercamiento al cilindro y cámara hermética",
                "labels": ["1. Cámara de Combustión", "2. Camisa del Cilindro", "3. Conductos de Refrigeración", "4. Carrera (PMS → PMI)"],
                "elements": ["Cylinder bore close-up", "Cooling jacket", "Top Dead Center (TDC)", "Bottom Dead Center (BDC)"],
                "phase": "cylinder_zoom",
            },
            {
                "step_index": 3,
                "concept": "Anatomía del pistón, anillos y biela",
                "labels": ["1. Cabeza del Pistón", "2. Anillos de Compresión", "3. Bulón Articulado", "4. Biela de Acero"],
                "elements": ["Piston crown", "Compression & oil rings", "Wrist pin", "Connecting rod"],
                "phase": "piston_id",
            },
            {
                "step_index": 4,
                "concept": "1er Tiempo: Admisión de aire y combustible",
                "labels": ["1. Válvula Admisión ABIERTA", "2. Entrada Aire + Gasolina (14.7:1)", "3. Pistón Descendiendo ↓", "4. Vacío de Succión"],
                "elements": ["Open intake valve", "Blue air-fuel mist entering", "Downward piston motion", "Crankshaft 0°-180°"],
                "phase": "intake",
            },
            {
                "step_index": 5,
                "concept": "2do Tiempo: Compresión adiabática",
                "labels": ["1. Ambas Válvulas CERRADAS", "2. Pistón Ascendiendo ↑", "3. Compresión (10:1)", "4. Aumento de Presión y T°"],
                "elements": ["Both valves sealed", "Upward piston compression", "Compressed air-fuel charge", "Crankshaft 180°-360°"],
                "phase": "compression",
            },
            {
                "step_index": 6,
                "concept": "Ignición: Salto de chispa y frente de llama",
                "labels": ["1. Electrodo de Bujía", "2. Arco Eléctrico (20,000 V)", "3. Frente de Llama Controlado", "4. Pico > 2,000 °C"],
                "elements": ["Spark plug electrode", "High-voltage electric spark", "Progressive flame front", "Peak chamber pressure"],
                "phase": "combustion",
            },
            {
                "step_index": 7,
                "concept": "3er Tiempo: Expansión (Carrera de Fuerza)",
                "labels": ["1. Gases en Expansión (60 bar)", "2. Empuje de Fuerza ↓", "3. Trabajo Mecánico Útil", "4. Impulso a la Biela"],
                "elements": ["Expanding hot gases", "Power stroke downward force", "Connecting rod thrust", "Crankshaft 360°-540°"],
                "phase": "expansion",
            },
            {
                "step_index": 8,
                "concept": "Movimiento del cigüeñal y 4to Tiempo: Escape",
                "labels": ["1. Válvula Escape ABIERTA", "2. Expulsión de Gases ↑", "3. Giro del Cigüeñal (720°)", "4. Volante de Inercia"],
                "elements": ["Open exhaust valve", "Exhaust gas expulsion", "Rotating crankshaft torque", "Flywheel rotational output"],
                "phase": "crankshaft_exhaust",
            },
        ]
        chosen = engine_steps[(step_cursor - 1) % len(engine_steps)]
        return (
            chosen["elements"],
            chosen["labels"],
            chosen["concept"],
            {"template": "combustion_engine", "step_index": chosen["step_index"], "phase": chosen["phase"]},
        )

    if mechanism_family == "atm_machine":
        atm_steps = [
            {
                "step_index": 1,
                "concept": "Arquitectura interna del Cajero Automático",
                "labels": ["1. Lector Chip EMV", "2. Teclado Cifrado EPP", "3. Bóveda de Acero CEN", "4. Casetes de Billetes"],
                "elements": ["ATM upper cabinet", "Encrypted PIN pad", "Reinforced lower vault", "Currency cassettes"],
                "phase": "atm_overview",
            },
            {
                "step_index": 2,
                "concept": "Cifrado en hardware y autorización ISO 8583",
                "labels": ["1. Lectura Chip EMV", "2. Cifrado AES/3DES en Teclado", "3. Mensaje ISO 8583", "4. Validación HSM Banco"],
                "elements": ["EMV smartcard chip", "Hardware PIN encryption", "ISO 8583 network packet", "Bank HSM verification"],
                "phase": "atm_crypto",
            },
            {
                "step_index": 3,
                "concept": "Extracción por vacío y rodillos de fricción",
                "labels": ["1. Casete por Denominación", "2. Ventosa de Vacío / Rodillo", "3. Separador Anti-Doble", "4. Banda Transportadora"],
                "elements": ["Cash cassette", "Vacuum pick-up roller", "Friction separator", "High-speed transport belt"],
                "phase": "atm_picker",
            },
            {
                "step_index": 4,
                "concept": "Sensor óptico/ultrasónico de espesor y entrega",
                "labels": ["1. Sensor Ultrasónico de Grosor", "2. Cajón de Rechazo (Reject Bin)", "3. Acumulador (Stacker)", "4. Obturador Exterior (Shutter)"],
                "elements": ["Ultrasonic thickness sensor", "Reject bin diverter", "Escrow bill stacker", "Output shutter slot"],
                "phase": "atm_sensor",
            },
        ]
        chosen = atm_steps[(step_cursor - 1) % len(atm_steps)]
        return (
            chosen["elements"],
            chosen["labels"],
            chosen["concept"],
            {"template": "atm_machine", "step_index": chosen["step_index"], "phase": chosen["phase"]},
        )

    if mechanism_family == "gps_system":
        gps_steps = [
            {
                "step_index": 1,
                "concept": "Constelación de satélites GPS en órbita media (MEO)",
                "labels": ["1. 31 Satélites Activos", "2. Altitud: 20,200 km (MEO)", "3. 6 Planos Orbitales", "4. Visibilidad Mínima: 4 Satélites"],
                "elements": ["Earth globe", "6 MEO orbital rings at 20,200 km", "GPS satellites", "Line of sight to receiver"],
                "phase": "gps_constellation",
            },
            {
                "step_index": 2,
                "concept": "Reloj atómico y cálculo de distancia d = c × Δt",
                "labels": ["1. Reloj Atómico (Cesio/Rubidio)", "2. Señal de Radio (t₁)", "3. Recepción Pasiva (t₂)", "4. Distancia = c × (t₂ - t₁)"],
                "elements": ["Atomic clock nanosecond pulse", "Radio wave propagation at light speed", "Passive smartphone receiver", "Pseudorange formula"],
                "phase": "gps_time_of_flight",
            },
            {
                "step_index": 3,
                "concept": "Trilateración 3D e intersección de 4 esferas",
                "labels": ["1. Satélite 1: Esfera de Distancia", "2. Satélite 2: Círculo de Corte", "3. Satélite 3: 2 Puntos Posibles", "4. Satélite 4: Corrige Reloj (Δt)"],
                "elements": ["Intersecting distance spheres", "3D trilateration point", "4th satellite clock bias correction", "Exact Lat/Lon/Alt"],
                "phase": "gps_trilateration",
            },
            {
                "step_index": 4,
                "concept": "Corrección Relativista de Einstein (+38 µs/día)",
                "labels": ["1. Relatividad Especial (-7 µs/día)", "2. Relatividad General (+45 µs/día)", "3. Desfase Neto: +38 µs/día", "4. Compensación Evita 10 km Error"],
                "elements": ["Orbital velocity time dilation", "Gravitational time dilation", "+38 microseconds net shift", "Relativistic frequency offset"],
                "phase": "gps_relativity",
            },
        ]
        chosen = gps_steps[(step_cursor - 1) % len(gps_steps)]
        return (
            chosen["elements"],
            chosen["labels"],
            chosen["concept"],
            {"template": "gps_system", "step_index": chosen["step_index"], "phase": chosen["phase"]},
        )

    if mechanism_family == "touchscreen":
        ts_steps = [
            {
                "step_index": 1,
                "concept": "Capas en corte de una pantalla táctil capacitiva",
                "labels": ["1. Cristal Templado Protector", "2. Filas Conductoras ITO (Eje X)", "3. Aislante Dieléctrico", "4. Columnas ITO (Eje Y) + OLED"],
                "elements": ["Protective cover glass", "Transparent ITO X-axis layer", "Dielectric insulator", "ITO Y-axis layer over OLED"],
                "phase": "touch_layers",
            },
            {
                "step_index": 2,
                "concept": "Cuadrícula de capacitancia mutua y campo electrostático",
                "labels": ["1. Diamantes de Óxido de Indio (ITO)", "2. Electrodo Transmisor (Tx)", "3. Electrodo Receptor (Rx)", "4. Líneas de Campo Eléctrico"],
                "elements": ["Microscopic ITO diamond grid", "Transmitting electrode", "Receiving electrode", "Electrostatic field lines"],
                "phase": "touch_grid",
            },
            {
                "step_index": 3,
                "concept": "Alteración del campo por el dedo humano conductor",
                "labels": ["1. Dedo Humano (Conductor Iónico)", "2. Desvío de Carga (~1 pF)", "3. Caída de Capacitancia Mutua", "4. Chip Controlador Calcula (X,Y)"],
                "elements": ["Conductive human fingertip", "Distorted electrostatic field", "Capacitance drop at node (X,Y)", "Multi-touch controller IC"],
                "phase": "touch_finger",
            },
        ]
        chosen = ts_steps[(step_cursor - 1) % len(ts_steps)]
        return (
            chosen["elements"],
            chosen["labels"],
            chosen["concept"],
            {"template": "touchscreen", "step_index": chosen["step_index"], "phase": chosen["phase"]},
        )

    if mechanism_family == "auto_transmission":
        at_steps = [
            {
                "step_index": 1,
                "concept": "Convertidor de Par: acoplamiento hidrodinámico",
                "labels": ["1. Bomba Impulsora (Motor)", "2. Fluido ATF en Giro", "3. Estator (Multiplica Par x2)", "4. Turbina (Eje de Entrada)"],
                "elements": ["Impeller pump driven by engine", "Toroidal ATF fluid flow", "One-way stator blades", "Output turbine + lock-up clutch"],
                "phase": "torque_converter",
            },
            {
                "step_index": 2,
                "concept": "Tren de Engranajes Planetarios (Epicicloidal)",
                "labels": ["1. Engranaje Solar (Centro)", "2. Piñones Satélites", "3. Porta-Satélites (Carrier)", "4. Corona Anular Exterior"],
                "elements": ["Central sun gear", "Planet pinion gears", "Planet carrier arm", "Outer ring gear (annulus)"],
                "phase": "planetary_gearset",
            },
            {
                "step_index": 3,
                "concept": "Embragues multidisco y Cuerpo de Válvulas Mecatrónico",
                "labels": ["1. Paquetes de Embrague Hidráulico", "2. Bloqueo Selectivo de Corona/Sol", "3. Cuerpo de Válvulas (Laberinto)", "4. Solenoides TCU Electrónicos"],
                "elements": ["Multi-plate hydraulic clutch packs", "Selective gear locking", "Hydraulic valve body labyrinth", "Electronic TCU solenoids"],
                "phase": "valve_body",
            },
        ]
        chosen = at_steps[(step_cursor - 1) % len(at_steps)]
        return (
            chosen["elements"],
            chosen["labels"],
            chosen["concept"],
            {"template": "auto_transmission", "step_index": chosen["step_index"], "phase": chosen["phase"]},
        )

    # Plantilla semántica universal para cualquier otro tema
    concept_obj = concepts[(step_cursor - 1) % len(concepts)] if concepts else {"name": "Mecanismo Principal", "role": "Transformación física"}
    seq_label = diag_seq[(step_cursor - 1) % len(diag_seq)] if diag_seq else f"Etapa #{step_cursor}: {concept_obj['name']}"
    labels = [
        f"1. Entrada / Captación",
        f"2. {concept_obj['name'][:28]}",
        f"3. Proceso Interno",
        f"4. Salida Verificada",
    ]
    elements = [
        concept_obj["name"],
        "Primary mechanism cutaway",
        "Directional energy/signal flow",
        "Output actuator",
    ]
    return (
        elements,
        labels,
        re.sub(r"^\d+\.\s*", "", seq_label),
        {"template": "universal_diagram", "step_index": step_cursor, "phase": resource_type},
    )


def build_consistent_image_prompt(
    narration_text: str,
    concept_explained: str,
    key_elements: list[str],
    visual_style_key: str,
    topic: str,
    translated_subject: Optional[str] = None,
) -> str:
    """Construye el prompt de imagen aplicando las reglas del Visual Consistency Engine (Fase 8)."""
    style_cfg = VISUAL_CONSISTENCY_STYLES.get(visual_style_key) or VISUAL_CONSISTENCY_STYLES["3d_educational"]
    elements_str = ", ".join(key_elements[:4])
    en_subject = translated_subject or f"{elements_str} ({concept_explained})"
    en_subject = video_pipeline._sanitize_text_triggers(en_subject)
    palette_hex = ", ".join(
        [
            style_cfg["palette"]["bg_primary"],
            style_cfg["palette"]["accent_primary"],
            style_cfg["palette"]["accent_secondary"],
        ]
    )
    return (
        f"{style_cfg['prompt_prefix']}. "
        f"MAIN EDUCATIONAL SUBJECT: {en_subject}. "
        f"KEY VISIBLE COMPONENTS: {elements_str}. "
        f"ORIENTATION & CONTINUITY: {style_cfg['orientation_rule']}. "
        f"LIGHTING & PALETTE: {style_cfg['lighting_rule']}, cohesive color harmony ({palette_hex}). "
        "Purely visual technical illustration without any written letters, numbers, or watermarks."
    )


def generate_storyboard_from_script(
    script_branch: dict[str, Any],
    research: dict[str, Any],
    visual_style_key: str = "3d_educational",
    version_prefix: str = "S",
    speed: float = 1.0,
) -> list[dict[str, Any]]:
    """Convierte el guion (Corto o Largo) en una lista estructurada de escenas de Storyboard (Fase 6)."""
    topic = research.get("canonical_topic") or research.get("topic") or "Sistema técnico"
    question = research.get("main_question") or ""
    mechanism_family = _detect_topic_mechanism_family(topic, question)

    scenes: list[dict[str, Any]] = []
    sections = script_branch.get("sections") or []

    scene_counter = 0
    diagram_step_cursor = 0
    current_time_sec = 0.0

    for sec in sections:
        sec_key = sec.get("key", "seccion")
        sec_title = sec.get("title", "Sección")
        raw_text = (sec.get("text") or "").strip()
        if not raw_text:
            continue

        # En versión corta cada sección genera 1-2 escenas dinámicas; en versión larga divide por oraciones/beats
        beats = video_pipeline.split_script_into_scenes(raw_text, mode="sentence")
        if not beats:
            beats = [raw_text]

        for beat in beats:
            scene_counter += 1
            scene_id = f"{version_prefix}{scene_counter:02d}"
            resource_type = _select_semantic_resource_type(beat, sec_key, scene_counter, mechanism_family)
            res_meta = SCENE_RESOURCE_TYPES.get(resource_type, SCENE_RESOURCE_TYPES["illustrative_image"])
            visual_mode = res_meta["default_mode"]

            is_intro_or_outro = sec_key in ("gancho", "pregunta", "conclusion", "introduccion")
            if is_intro_or_outro:
                step_idx = 1
            elif visual_mode == "mode_b_diagram":
                diagram_step_cursor += 1
                step_idx = diagram_step_cursor
            else:
                step_idx = max(1, diagram_step_cursor)

            key_elements, labels, concept_explained, diagram_spec = _extract_labels_and_elements_for_scene(
                narration_text=beat,
                resource_type=resource_type,
                mechanism_family=mechanism_family,
                step_cursor=step_idx,
                research=research,
            )

            words = len(beat.split())
            est_dur = round(max(3.2, (words / 2.38) / max(0.65, speed) + 0.3), 2)
            start_sec = round(current_time_sec, 2)
            end_sec = round(start_sec + est_dur, 2)
            current_time_sec = end_sec

            camera_motion = CAMERA_MOTIONS_CYCLE[(scene_counter - 1) % len(CAMERA_MOTIONS_CYCLE)]
            image_prompt = build_consistent_image_prompt(
                narration_text=beat,
                concept_explained=concept_explained,
                key_elements=key_elements,
                visual_style_key=visual_style_key,
                topic=topic,
            )
            animation_prompt = (
                f"Animated educational {resource_type}: {concept_explained}. "
                f"Smooth directional motion highlighting {', '.join(labels[:3])} with camera {camera_motion}."
            )

            scenes.append(
                {
                    "scene_id": scene_id,
                    "index": scene_counter,
                    "section_key": sec_key,
                    "section_title": sec_title,
                    "text": beat,
                    "narration_text": beat,
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": est_dur,
                    "timestamp_label": f"{video_pipeline.format_mm_ss(start_sec)} → {video_pipeline.format_mm_ss(end_sec)}",
                    "concept_explained": concept_explained,
                    "visual_description": f"[{res_meta['name']}] {concept_explained} — Elementos: {', '.join(labels)}",
                    "resource_type": resource_type,
                    "resource_type_label": res_meta["name"],
                    "visual_mode": visual_mode,
                    "image_prompt": image_prompt,
                    "animation_prompt": animation_prompt,
                    "key_elements": key_elements,
                    "labels": labels,
                    "diagram_spec": diagram_spec,
                    "camera_motion": camera_motion,
                    "transition": "crossfade",
                    "status": "pending",
                    "manual_edits_locked": False,
                    "audio_url": None,
                    "image_url": None,
                    "diagram_svg_url": None,
                    "preview_video_url": None,
                }
            )

    return scenes
