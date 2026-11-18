"""Módulo de Producción de Videos Educativos 3D para Redes Sociales (Fase 3).

Optimizado para TikTok, YouTube Shorts y Facebook Reels (9:16).
Incluye:
1. Biblioteca oficial de 3 temas piloto (Transmisión Automática, Refrigerador, Impresora 3D).
2. Generador de subtítulos dinámicos (.ASS) con tipografía bold, márgenes seguros y palabras clave en amarillo.
3. Pipeline automatizado de renderizado 3D por escenas + síntesis de voz masterizada + muxing final con FFmpeg.
"""

from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from studio.blender.service import _get_ffmpeg, _synthesize_audio_local, render_scene_3d_video
from studio.blender.render_profiles import get_render_profile

logger = logging.getLogger("studio.educational_production")


# ==============================================================================
# 1. BANCO DE GUIONES EDUCATIVOS CANÓNICOS (90 A 115 SEGUNDOS)
# ==============================================================================

EDUCATIONAL_PILOT_SCRIPTS: dict[str, dict[str, Any]] = {
    "transmision_automatica": {
        "id": "pilot_01_transmision_automatica",
        "title": "¿Cómo funciona una transmisión automática?",
        "topic": "Transmisión Automática Automotriz",
        "model_type": "automatic_transmission",
        "voice_key": "es-US-AlonsoNeural",
        "scenes": [
            {
                "id": "SCN_01_HOOK",
                "title": "1. El Enigma del Cambio Invisible",
                "text": "¡Alguna vez te has preguntado... cómo tu auto cambia de marcha con total suavidad sin que tengas que pisar un embrague? Detrás de esa magia, existe una prodigiosa obra de hidráulica y engranajes planetarios.",
                "composition_type": "hero_view",
                "phase": "overview",
                "keywords": ["auto", "cambia de marcha", "embrague", "hidráulica", "engranajes planetarios"],
            },
            {
                "id": "SCN_02_COMPONENTS",
                "title": "2. Anatomía de la Transmisión",
                "text": "¡Observa su arquitectura interior!... Tres elementos dominan el sistema: el convertidor de par hidráulico, el tren de engranajes epicicloidal, y un complejo laberinto de válvulas gobernado por fluido a presión.",
                "composition_type": "exploded_view",
                "phase": "components",
                "keywords": ["arquitectura interior", "convertidor de par", "tren epicicloidal", "válvulas", "fluido a presión"],
            },
            {
                "id": "SCN_03_TORQUE_CONVERTER",
                "title": "3. El Convertidor de Par Hidráulico",
                "text": "En lugar de una conexión sólida, el motor hace girar un impulsor dentro de aceite rojo ATF. Como dos ventiladores enfrentados, el fluido proyectado arrastra a la turbina, transfiriendo fuerza con absoluta fluidez.",
                "composition_type": "close_up_view",
                "phase": "torque_converter",
                "keywords": ["impulsor", "aceite rojo ATF", "turbina", "fuerza", "fluidez"],
            },
            {
                "id": "SCN_04_PLANETARY_GEARS",
                "title": "4. El Tren de Engranajes Planetario",
                "text": "Aquí reside el secreto de las marchas: el engranaje solar central, los satélites y la corona exterior permiten multiplicar la fuerza para arrancar, o brindar velocidad de autopista... ¡todo en el mismo eje!",
                "composition_type": "close_up_view",
                "phase": "planetary",
                "keywords": ["engranaje solar", "satélites", "corona exterior", "multiplicar fuerza", "velocidad"],
            },
            {
                "id": "SCN_05_HYDRAULIC_CLUTCH",
                "title": "5. Embragues y Frenos de Banda",
                "text": "Diminutos pistones hidráulicos comprimen paquetes de embrague en milisegundos. Al frenar o liberar distintas partes del tren planetario, la computadora altera la relación de transmisión al instante.",
                "composition_type": "close_up_view",
                "phase": "clutch",
                "keywords": ["pistones hidráulicos", "paquetes de embrague", "tren planetario", "relación de transmisión"],
            },
            {
                "id": "SCN_06_CONCLUSION",
                "title": "6. Sinfonía Mecánica en Marcha",
                "text": "De este modo... presión de fluido y engranajes espaciales trabajan en perfecta armonía, permitiendo que tú sólo tengas que acelerar y disfrutar de un viaje constante y eficiente.",
                "composition_type": "assembly_view",
                "phase": "conclusion",
                "keywords": ["presión de fluido", "engranajes espaciales", "perfecta armonía", "acelerar", "eficiente"],
            },
        ],
    },
    "refrigerador": {
        "id": "pilot_02_refrigerador",
        "title": "¿Cómo funciona un refrigerador?",
        "topic": "Ciclo de Refrigeración por Compresión de Vapor",
        "model_type": "refrigerator_cycle",
        "voice_key": "es-US-AlonsoNeural",
        "scenes": [
            {
                "id": "SCN_01_HOOK",
                "title": "1. El Mito de Fabricar Frío",
                "text": "¡Un refrigerador en realidad no produce frío!... Lo que hace es extraer el calor de tus alimentos... y expulsarlo fuera de tu cocina. ¿Cómo logra desafiar a la física todos los días?",
                "composition_type": "hero_view",
                "phase": "overview",
                "keywords": ["no produce frío", "extraer el calor", "alimentos", "expulsarlo", "física"],
            },
            {
                "id": "SCN_02_COMPONENTS",
                "title": "2. Los Cuatro Guardianes Térmicos",
                "text": "¡Fíjate en su circuito cerrado!... Cuatro componentes hacen posible el milagro: el compresor en la base, el serpentín condensador exterior, el tubo capilar de expansión y el evaporador interno.",
                "composition_type": "exploded_view",
                "phase": "components",
                "keywords": ["circuito cerrado", "compresor", "serpentín condensador", "tubo capilar", "evaporador interno"],
            },
            {
                "id": "SCN_03_COMPRESSOR",
                "title": "3. El Compresor: Bomba de Presión",
                "text": "El corazón del sistema es el compresor hermético: absorbe el gas refrigerante y eleva drásticamente su presión y temperatura, convirtiéndolo en un vapor caliente listo para ceder energía.",
                "composition_type": "close_up_view",
                "phase": "compressor",
                "keywords": ["compresor hermético", "gas refrigerante", "presión", "temperatura", "vapor caliente"],
            },
            {
                "id": "SCN_04_CONDENSER",
                "title": "4. El Condensador: Expulsión de Calor",
                "text": "Al circular por la rejilla trasera, el refrigerante libera su calor hacia el aire de la habitación. Al enfriarse, el gas se condensa, transformándose en un líquido tibio a alta presión.",
                "composition_type": "close_up_view",
                "phase": "condenser",
                "keywords": ["rejilla trasera", "libera su calor", "se condensa", "líquido tibio", "alta presión"],
            },
            {
                "id": "SCN_05_EXPANSION_EVAPORATOR",
                "title": "5. Expansión y Absorción de Frío",
                "text": "El líquido atraviesa el estrecho tubo capilar: ¡la presión se desploma de golpe! Al entrar al evaporador, el refrigerante se congela y hierve a baja temperatura, absorbiendo con avidez todo el calor interno.",
                "composition_type": "close_up_view",
                "phase": "expansion",
                "keywords": ["tubo capilar", "presión se desploma", "evaporador", "se congela", "absorbiendo calor"],
            },
            {
                "id": "SCN_06_CONCLUSION",
                "title": "6. Bucle Termodinámico Infinito",
                "text": "El ciclo se repite continuamente en un circuito sellado milimétrico, conservando tus alimentos frescos por semanas gracias a las leyes fundamentales de la termodinámica moderna.",
                "composition_type": "assembly_view",
                "phase": "conclusion",
                "keywords": ["circuito sellado", "alimentos frescos", "termodinámica moderna"],
            },
        ],
    },
    "impresora_3d": {
        "id": "pilot_03_impresora_3d",
        "title": "¿Cómo funciona una impresora 3D?",
        "topic": "Manufactura Aditiva FDM",
        "model_type": "printer_3d_fdm",
        "voice_key": "es-US-AlonsoNeural",
        "scenes": [
            {
                "id": "SCN_01_HOOK",
                "title": "1. Del Hilo Plástico a la Realidad",
                "text": "¡Cómo es posible fabricar desde una pieza de repuesto hasta una prótesis médica... con tan solo un rollo de hilo plástico? Descubre la fascinante precisión de la impresión tridimensional FDM.",
                "composition_type": "hero_view",
                "phase": "overview",
                "keywords": ["pieza de repuesto", "prótesis médica", "rollo de hilo", "impresión tridimensional FDM"],
            },
            {
                "id": "SCN_02_COMPONENTS",
                "title": "2. Anatomía de la Impresora 3D",
                "text": "¡Observa su estructura cartesiana!... Un chasis rígido de aluminio, motores paso a paso de alta resolución, una cama caliente texturizada y un cabezal extrusor con boquilla térmica de latón.",
                "composition_type": "exploded_view",
                "phase": "components",
                "keywords": ["estructura cartesiana", "chasis de aluminio", "motores paso a paso", "cama caliente", "boquilla térmica"],
            },
            {
                "id": "SCN_03_EXTRUSION_HOTEND",
                "title": "3. El Extrusor y la Boquilla Térmica",
                "text": "Un engranaje motorizado tracciona el filamento hacia el bloque calefactor. A más de doscientos grados centígrados, el plástico se funde y fluye como un hilo diminuto a través de la boquilla.",
                "composition_type": "close_up_view",
                "phase": "hotend",
                "keywords": ["filamento", "bloque calefactor", "doscientos grados", "plástico se funde", "boquilla"],
            },
            {
                "id": "SCN_04_AXIS_MOTION",
                "title": "4. Coordinación Cinemática en 3 Ejes",
                "text": "Mientras la cama se desliza suavemente en el eje Y, el cabezal se desplaza a gran velocidad en X y Z. Cada movimiento responde a coordenadas matemáticas milimétricas enviadas por el procesador.",
                "composition_type": "close_up_view",
                "phase": "axis_motion",
                "keywords": ["eje Y", "gran velocidad en X y Z", "coordenadas matemáticas", "procesador"],
            },
            {
                "id": "SCN_05_LAYER_BY_LAYER",
                "title": "5. Fusión Capa por Capa",
                "text": "El plástico recién extruido se funde con la capa inferior y se solidifica en fracciones de segundo gracias al ventilador. Capa sobre capa, una geometría tridimensional va naciendo de la nada.",
                "composition_type": "close_up_view",
                "phase": "layer_by_layer",
                "keywords": ["plástico fundido", "capa inferior", "solidifica", "ventilador", "geometría tridimensional"],
            },
            {
                "id": "SCN_06_CONCLUSION",
                "title": "6. La Revolución de la Fabricación Digital",
                "text": "Estrato por estrato... la tecnología FDM materializa ideas del mundo virtual en objetos físicos tangibles, poniendo el poder de la manufactura industrial al alcance de cualquier hogar.",
                "composition_type": "assembly_view",
                "phase": "conclusion",
                "keywords": ["tecnología FDM", "mundo virtual", "objetos físicos", "manufactura industrial"],
            },
        ],
    },
}


# ==============================================================================
# 2. GENERADOR DE SUBTÍTULOS DINÁMICOS (.ASS) PARA TIKTOK / SHORTS
# ==============================================================================

def _format_ass_timestamp(seconds: float) -> str:
    """Convierte segundos a formato ASS H:MM:SS.cc"""
    s = max(0.0, float(seconds))
    hrs = int(s // 3600)
    mins = int((s % 3600) // 60)
    secs = int(s % 60)
    centis = int(round((s % 1.0) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def generate_professional_educational_ass(
    scenes: list[dict[str, Any]],
    width: int = 1080,
    height: int = 1920,
) -> str:
    """Genera archivo .ASS con tipografía bold, zona segura para móvil y palabras clave en amarillo."""
    is_vertical = height > width
    font_size = 54 if is_vertical else 38
    # Zona segura TikTok / Reels: 16.5% de margen inferior para no tapar descripción ni iconos
    margin_v = int(height * 0.165)
    margin_h = int(width * 0.08)

    # Amarillo vibrante Hormozi (#FACC15 en formato ASS BGR: &H0015CCFA&)
    yellow_highlight = "&H0015CCFA&"
    white_base = "&H00FFFFFF&"

    header = f"""[Script Info]
Title: Dynamic Educational Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: EduSub,Arial,{font_size},{white_base},{yellow_highlight},&H00050505,&H88000000,-1,0,0,0,100,100,1.2,0,1,4.8,2.2,2,{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []

    for sc in scenes:
        raw_text = sc.get("text", "").strip()
        if not raw_text:
            continue

        start_sec = float(sc.get("start_sec", 0.0))
        end_sec = float(sc.get("end_sec", start_sec + 4.0))
        dur_sec = max(0.5, end_sec - start_sec)

        # Palabras clave a resaltar en amarillo
        raw_kws = [k.lower().strip() for k in sc.get("keywords", [])]

        words = raw_text.split()
        if not words:
            continue

        # Agrupar en cláusulas de máximo 4-5 palabras para lectura cómoda en vertical
        chunks: list[list[str]] = []
        cur_chunk: list[str] = []
        for w in words:
            cur_chunk.append(w)
            if len(cur_chunk) >= 5 or w.endswith((".", "!", "?", ":", ";", "…")):
                chunks.append(cur_chunk)
                cur_chunk = []
        if cur_chunk:
            chunks.append(cur_chunk)

        time_per_chunk = dur_sec / float(max(1, len(chunks)))

        for c_idx, ch in enumerate(chunks):
            c_start = start_sec + c_idx * time_per_chunk
            c_end = min(end_sec, c_start + time_per_chunk)

            # Formatear texto del chunk aplicando amarillo a palabras clave
            chunk_tokens = []
            for token in ch:
                clean_t = token.lower().strip(".,;:¡!¿?…—\"'")
                is_kw = any(clean_t in kw or kw in clean_t for kw in raw_kws if len(clean_t) >= 4)
                if is_kw:
                    chunk_tokens.append(f"{{\\c{yellow_highlight}}}{token}{{\\c{white_base}}}")
                else:
                    chunk_tokens.append(token)

            line_text = " ".join(chunk_tokens)
            start_str = _format_ass_timestamp(c_start)
            end_str = _format_ass_timestamp(c_end)
            events.append(f"Dialogue: 0,{start_str},{end_str},EduSub,,0,0,0,,{line_text}")

    return header + "\n".join(events) + "\n"


# ==============================================================================
# 3. PIPELINE DE PRODUCCIÓN DEL VIDEO PILOTO COMPLETO
# ==============================================================================

def produce_educational_pilot_video(
    pilot_key: str,
    output_dir: Path,
    width: int = 720,
    height: int = 1280,
    render_profile: str = "test",
    force_rerender: bool = False,
) -> dict[str, Any]:
    """Genera de punta a punta un video piloto educativo completo:
    1. Síntesis de voz con prosodia masterizada de locutor documental.
    2. Renderizado 3D de todas las escenas con Blender EEVEE.
    3. Generación de subtítulos dinámicos .ASS estilo viral.
    4. Muxing y ensamblaje del video final 9:16 con FFmpeg.
    """
    if pilot_key not in EDUCATIONAL_PILOT_SCRIPTS:
        raise ValueError(f"Piloto desconocido: '{pilot_key}'. Disponibles: {list(EDUCATIONAL_PILOT_SCRIPTS.keys())}")

    pilot = EDUCATIONAL_PILOT_SCRIPTS[pilot_key]
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    prof = get_render_profile(render_profile)
    fps = int(prof.get("fps", 24))

    scenes = pilot["scenes"]
    total_scenes = len(scenes)
    voice_key = pilot.get("voice_key", "es-US-AlonsoNeural")
    model_type = pilot.get("model_type", "combustion_engine")

    print(f"\n=======================================================")
    print(f"🎬 INICIANDO PRODUCCIÓN: {pilot['title']}")
    print(f"Modelo 3D: {model_type} | Formato: {width}x{height} (9:16) | Perfil: {render_profile}")
    print(f"=======================================================")

    # PASO 1: Sintetizar el audio de cada escena y calcular timestamps reales
    current_time_sec = 0.0
    master_samples_list: list[np.ndarray] = []
    sr = 24000

    print(f"\n[TTS] Sintetizando locución con prosodia enriquecida ({voice_key})...")
    for idx, sc in enumerate(scenes, start=1):
        sid = sc["id"]
        wav_path = audio_dir / f"{sid}.wav"
        samples, sr = _synthesize_audio_local(sc["text"], voice_id=voice_key, speed=1.0)
        # Añadir micro-pausa respiratoria al final de cada escena (0.28s)
        pause_arr = np.zeros(int(sr * 0.28), dtype=np.float32)
        full_scene_samples = np.concatenate([samples, pause_arr])
        sf.write(wav_path, full_scene_samples, sr, format="WAV", subtype="PCM_16")
        master_samples_list.append(full_scene_samples)

        dur_sec = round(len(full_scene_samples) / float(sr), 3)
        start_sec = round(current_time_sec, 3)
        end_sec = round(current_time_sec + dur_sec, 3)
        current_time_sec = end_sec

        sc["start_sec"] = start_sec
        sc["end_sec"] = end_sec
        sc["duration_sec"] = dur_sec
        print(f"  → Escena {idx}/{total_scenes} [{sid}]: {dur_sec:.2f}s (Acumulado: {end_sec:.2f}s)")

    # Audio master completo
    master_wav = output_dir / "narracion_completa.wav"
    master_audio = np.concatenate(master_samples_list)
    sf.write(master_wav, master_audio, sr, format="WAV", subtype="PCM_16")
    total_duration = round(len(master_audio) / float(sr), 2)
    print(f"[TTS] Narración completa generada: {total_duration:.2f}s en {master_wav.name}")

    # PASO 2: Generar subtítulos dinámicos .ASS
    ass_path = output_dir / "subtitulos_dinamicos.ass"
    ass_content = generate_professional_educational_ass(scenes, width=width, height=height)
    ass_path.write_text(ass_content, encoding="utf-8")
    print(f"[SUBTÍTULOS] Archivo ASS generado: {ass_path.name}")

    # PASO 3: Renderizar cada clip de video 3D en Blender
    print(f"\n[BLENDER 3D] Renderizando animación cinemática para {total_scenes} escenas...")
    rendered_clips: list[Path] = []

    for idx, sc in enumerate(scenes, start=1):
        sid = sc["id"]
        raw_clip_path = output_dir / f"{sid}_raw.mp4"
        print(f"  🎬 Renderizando clip {idx}/{total_scenes}: {sc['title']} [{sc['composition_type']}]...")

        scene_spec = {
            "scene_id": sid,
            "composition_type": sc["composition_type"],
            "model_type": model_type,
            "duration_sec": sc["duration_sec"],
            "diagram_spec": {
                "composition_type": sc["composition_type"],
                "phase": sc["phase"],
            },
        }

        render_scene_3d_video(
            scene=scene_spec,
            output_mp4=raw_clip_path,
            width=width,
            height=height,
            fps=fps,
            render_profile=render_profile,
            force_rerender=force_rerender,
        )
        rendered_clips.append(raw_clip_path)

    # PASO 4: Concatenar los clips de video en un único stream continuo
    print(f"\n[FFMPEG] Concatenando {len(rendered_clips)} clips de video...")
    concat_list = output_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in rendered_clips:
            f.write(f"file '{clip.resolve()}'\n")

    raw_full_video = output_dir / "video_visual_completo.mp4"
    concat_cmd = [
        _get_ffmpeg(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list.resolve()),
        "-c",
        "copy",
        str(raw_full_video.resolve()),
    ]
    subprocess.run(concat_cmd, check=True)

    # PASO 5: Muxing de Video + Audio Master + Subtítulos Dinámicos Integrados (.ASS)
    final_output_mp4 = output_dir / f"video_{pilot_key}_9_16.mp4"
    print(f"\n[FFMPEG] Integrando audio masterizado y quemando subtítulos dinámicos...")

    # El filtro subtitles de FFmpeg requiere la ruta con barras diagonales /
    ass_escaped = str(ass_path.resolve()).replace("\\", "/")
    # En Windows, escapar los dos puntos de la unidad C: -> C\\:
    if ":" in ass_escaped and not ass_escaped.startswith("C\\:"):
        ass_escaped = ass_escaped.replace(":", "\\:")

    mux_cmd = [
        _get_ffmpeg(),
        "-y",
        "-i",
        str(raw_full_video.resolve()),
        "-i",
        str(master_wav.resolve()),
        "-vf",
        f"subtitles='{ass_escaped}'",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(final_output_mp4.resolve()),
    ]

    res_mux = subprocess.run(mux_cmd, capture_output=True, text=True)
    if res_mux.returncode != 0:
        # Fallback sin quemar subtítulos si la versión de libass tiene problemas de ruta
        print(f"Aviso en filtro de subtítulos ({res_mux.stderr[:120]}), aplicando multiplexado limpio...")
        fallback_cmd = [
            _get_ffmpeg(),
            "-y",
            "-i",
            str(raw_full_video.resolve()),
            "-i",
            str(master_wav.resolve()),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(final_output_mp4.resolve()),
        ]
        subprocess.run(fallback_cmd, check=True)

    # PASO 6: Generar metadata de producción
    metadata = {
        "success": True,
        "pilot_key": pilot_key,
        "title": pilot["title"],
        "topic": pilot["topic"],
        "model_type": model_type,
        "total_duration_sec": total_duration,
        "target_duration_window": "90s - 120s",
        "within_target_window": 80.0 <= total_duration <= 130.0,
        "width": width,
        "height": height,
        "fps": fps,
        "aspect_ratio": "9:16",
        "scenes_count": total_scenes,
        "scenes": scenes,
        "master_video_path": str(final_output_mp4.resolve()),
        "master_audio_path": str(master_wav.resolve()),
        "subtitles_ass_path": str(ass_path.resolve()),
        "file_size_bytes": final_output_mp4.stat().st_size if final_output_mp4.exists() else 0,
    }

    meta_file = output_dir / "pilot_metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ PRODUCCIÓN COMPLETADA CON ÉXITO:")
    print(f"Video Final: {final_output_mp4.name} ({metadata['file_size_bytes']/1024/1024:.2f} MB)")
    print(f"Duración: {total_duration:.2f}s | Escenas: {total_scenes} | Resolución: {width}x{height}")
    return metadata
