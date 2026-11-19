"""Router FastAPI modular para AI VIDEO STUDIO — EXPLAINER AI (¿CÓMO FUNCIONA?).

Conecta las Fases 2 a 20 reutilizando el motor de voz, imágenes, música y FFmpeg
de app.py y video_pipeline.py sin alterar ninguna ruta existente.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import video_pipeline
from studio.diagram_engine import generate_scene_svg_diagram
from studio.models import (
    CATEGORIES_CATALOG,
    COMPOSITION_TYPES,
    PublishingPlatformAdapter,
    SCENE_RESOURCE_TYPES,
    VISUAL_CONSISTENCY_STYLES,
    create_default_cost_ledger,
    load_platform_profiles,
    record_cost_event,
    save_platform_profiles,
)
from studio.blender.blender_gateway import get_blender_status
from studio.blender.render_profiles import get_render_profile
from studio.blender.service import (
    render_scene_3d_still,
    render_scene_3d_video,
    run_combustion_engine_prototype_benchmark,
)
from studio.multiformat_engine import (
    render_explainer_version_video,
    render_single_scene_preview,
)
from studio.quality_control import run_quality_control_inspection
from studio.research_engine import run_topic_research
from studio.script_engine import (
    build_platform_script_adaptations,
    estimate_speaking_duration_sec,
    generate_educational_scripts,
    regenerate_single_script_section,
)
from studio.social_packager import build_social_media_package_for_platform
from studio.storyboard_engine import (
    build_consistent_image_prompt,
    generate_storyboard_from_script,
)
from studio.video_providers import list_video_providers_status

router = APIRouter(prefix="/api/explainer", tags=["Explainer AI Studio"])

PROJECTS_DIR: Path = Path(__file__).resolve().parent.parent / "projects"
_SYNTHESIZE_FN: Optional[Callable[..., tuple[np.ndarray, int]]] = None


def init_studio_router(projects_dir: Path, synthesize_fn: Callable[..., tuple[np.ndarray, int]]) -> APIRouter:
    global PROJECTS_DIR, _SYNTHESIZE_FN
    PROJECTS_DIR = projects_dir
    _SYNTHESIZE_FN = synthesize_fn
    return router


# ==============================================================================
# MODELOS DE SOLICITUD (REQUEST SCHEMAS)
# ==============================================================================

class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)
    main_question: str = Field("", max_length=600)
    category: str = Field("ingenieria")
    target_audience: str = Field("Público general curioso y estudiantes")
    user_notes: str = Field("", max_length=15000)


class CreateExplainerProjectRequest(BaseModel):
    project_name: str = Field("", max_length=200)
    topic: str = Field(..., min_length=2, max_length=500)
    main_question: str = Field("", max_length=600)
    category: str = Field("ingenieria")
    target_audience: str = Field("Público general curioso y estudiantes")
    lang: str = Field("es-mx")
    duration_mode: str = Field("both", description="'short' (1-3m), 'long' (5-10m), o 'both'")
    screen_format: str = Field("both", description="'9:16', '16:9', o 'both'")
    visual_style: str = Field("3d_educational")
    engine: str = Field("edge")
    voice: str = Field("es-MX-JorgeNeural")
    speed: float = Field(1.0, ge=0.65, le=1.45)
    pitch_hz: int = Field(-2, ge=-12, le=12)
    studio_mastering: bool = Field(True)
    bg_music: str = Field("doc_mystery")
    bg_music_volume: float = Field(0.14, ge=0.0, le=0.50)
    subtitle_style: str = Field("hormozi_yellow")
    user_notes: str = Field("", max_length=15000)
    existing_research: Optional[dict[str, Any]] = None


class ScriptSectionUpdateRequest(BaseModel):
    version: str = Field("short", description="'short' o 'long'")
    section_key: str = Field(...)
    new_text: Optional[str] = None
    regenerate: bool = Field(False)
    instruction: str = Field("")


class SceneUpdateRequest(BaseModel):
    action: str = Field("update", description="'update', 'duplicate', 'move_up', 'move_down', 'delete'")
    narration_text: Optional[str] = None
    concept_explained: Optional[str] = None
    resource_type: Optional[str] = None
    composition_type: Optional[str] = None
    visual_mode: Optional[str] = None
    image_prompt: Optional[str] = None
    labels: Optional[list[str]] = None
    camera_motion: Optional[str] = None
    transition: Optional[str] = None
    duration_sec: Optional[float] = None


class MultiPlatformExportRequest(BaseModel):
    platforms: list[str] = Field(
        default_factory=lambda: ["youtube_shorts", "youtube_video", "tiktok", "instagram_reels", "facebook_reels", "facebook_video"]
    )
    synthesize_missing_audio: bool = Field(True)
    generate_ai_images_for_mode_a: bool = Field(False)
    burn_subtitles: bool = Field(True)
    async_mode: bool = Field(False)


class SocialPackageEditRequest(BaseModel):
    title: str
    description: str
    hashtags: list[str]
    post_text: str
    comment_question: str


class BudgetConfigRequest(BaseModel):
    max_budget_usd: float = Field(2.0, ge=0.0, le=500.0)
    max_generations: int = Field(120, ge=1, le=2000)
    allow_ai_video: bool = Field(False)
    prefer_local_animations: bool = Field(True)
    require_cost_confirmation: bool = Field(True)


# ==============================================================================
# HELPERS INTERNOS
# ==============================================================================

def _load_explainer_project(project_id: str) -> tuple[Path, dict[str, Any]]:
    proj_dir = PROJECTS_DIR / project_id
    meta_file = proj_dir / "project.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail=f"Proyecto '{project_id}' no encontrado.")
    return proj_dir, json.loads(meta_file.read_text(encoding="utf-8"))


def _save_explainer_project(proj_dir: Path, data: dict[str, Any]) -> dict[str, Any]:
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (proj_dir / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _generate_all_svg_diagrams_for_version(proj_dir: Path, scenes: list[dict[str, Any]], visual_style: str, version: str) -> None:
    w, h = (1080, 1920) if version == "short" else (1920, 1080)
    diagrams_dir = proj_dir / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    for sc in scenes:
        sid = sc.get("scene_id", f"S{sc.get('index', 1):02d}")
        svg_file = diagrams_dir / f"{sid}.svg"
        generate_scene_svg_diagram(sc, visual_style_key=visual_style, width=w, height=h, dest_svg_path=svg_file)
        sc["diagram_svg_url"] = f"/projects/{proj_dir.name}/diagrams/{sid}.svg?t={ts}"
        if sc.get("visual_mode") == "mode_b_diagram" and sc.get("status") == "pending":
            sc["status"] = "ready"


def _synthesize_version_audio(proj_dir: Path, meta: dict[str, Any], version: str) -> dict[str, Any]:
    """Sintetiza la narración real de cada escena para la versión indicada ('short' o 'long'),
    calcula los timestamps reales al milisegundo y actualiza el guion y storyboard sin acelerar la voz."""
    if _SYNTHESIZE_FN is None:
        raise RuntimeError("Función de síntesis TTS no inicializada.")

    scenes = (meta.get("storyboards") or {}).get(version) or []
    if not scenes:
        raise HTTPException(status_code=400, detail=f"No hay escenas en el storyboard '{version}'.")

    audio_dir = proj_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    engine = meta.get("engine", "edge")
    voice_id = meta.get("voice", "es-MX-JorgeNeural")
    lang = meta.get("lang", "es-mx")
    speed = float(meta.get("speed", 1.0))
    pitch_hz = int(meta.get("pitch_hz", -2))
    studio_mastering = bool(meta.get("studio_mastering", True))
    sentence_pause = 0.24

    master_parts: list[np.ndarray] = []
    curr_t = 0.0
    sr = 24000
    cache_bust = int(time.time())

    for sc in scenes:
        t0 = time.perf_counter()
        sid = sc.get("scene_id", f"{version[0].upper()}{sc.get('index', 1):02d}")
        text = (sc.get("narration_text") or sc.get("text") or "").strip()
        samples, sr = _SYNTHESIZE_FN(
            text=text,
            engine=engine,
            voice_id=voice_id,
            lang=lang,
            speed=speed,
            sentence_pause=sentence_pause,
            noise_scale=0.667,
            pitch_hz=pitch_hz,
            studio_mastering=studio_mastering,
        )
        pause_arr = np.zeros(int(sr * sentence_pause), dtype=np.float32)
        full_scene_samples = np.concatenate([samples, pause_arr])

        wav_file = audio_dir / f"{sid}.wav"
        sf.write(wav_file, full_scene_samples, sr, format="WAV", subtype="PCM_16")
        master_parts.append(full_scene_samples)

        dur = round(len(full_scene_samples) / float(sr), 3)
        start_s = round(curr_t, 3)
        end_s = round(curr_t + dur, 3)
        curr_t = end_s

        sc["start_sec"] = start_s
        sc["end_sec"] = end_s
        sc["duration_sec"] = dur
        sc["timestamp_label"] = f"{video_pipeline.format_mm_ss(start_s)} → {video_pipeline.format_mm_ss(end_s)}"
        sc["audio_url"] = f"/projects/{proj_dir.name}/audio/{sid}.wav?t={cache_bust}"

        record_cost_event(
            meta["cost_ledger"],
            operation="tts_synthesis",
            provider=engine,
            elapsed_sec=time.perf_counter() - t0,
            reported_cost_usd=0.0,
            is_free_local_or_tier=True,
            details=f"Voz {voice_id} en escena {sid} ({dur}s)",
        )

    master_arr = np.concatenate(master_parts) if master_parts else np.zeros(2400, dtype=np.float32)
    version_wav = proj_dir / f"narracion_{version}.wav"
    sf.write(version_wav, master_arr, sr, format="WAV", subtype="PCM_16")
    # También guardar copia en narracion_completa.wav para compatibilidad con reproductores clásicos
    sf.write(proj_dir / "narracion_completa.wav", master_arr, sr, format="WAV", subtype="PCM_16")

    real_total = round(curr_t, 2)
    if "scripts" in meta and version in meta["scripts"]:
        meta["scripts"][version]["real_audio_duration_sec"] = real_total
    meta.setdefault("audio_urls", {})[version] = f"/projects/{proj_dir.name}/narracion_{version}.wav?t={cache_bust}"
    return meta


# ==============================================================================
# ENDPOINTS REST DE EXPLAINER AI STUDIO
# ==============================================================================

@router.get("/catalog")
def get_explainer_catalog():
    """Devuelve categorías, estilos de consistencia visual, tipos de escena, perfiles de exportación,
    estado de adaptadores de video, publicación y estado del motor 3D Blender."""
    return {
        "categories": CATEGORIES_CATALOG,
        "visual_styles": list(VISUAL_CONSISTENCY_STYLES.values()),
        "scene_resource_types": list(SCENE_RESOURCE_TYPES.values()),
        "composition_types": list(COMPOSITION_TYPES.values()),
        "platform_profiles": load_platform_profiles(),
        "video_providers": list_video_providers_status(),
        "publishing_integrations": PublishingPlatformAdapter.get_integration_status(),
        "blender_status": get_blender_status(),
    }


@router.get("/blender/status")
def get_blender_status_endpoint():
    """Devuelve el estado, ruta del binario y soporte de EEVEE Next de Blender 5.3."""
    return get_blender_status()


@router.post("/blender/prototype")
def run_blender_prototype_endpoint(is_vertical: bool = True, render_profile: str = "draft"):
    """Ejecuta la prueba obligatoria (Punto 11) del Motor de 4 Tiempos en Blender 3D."""
    target_dir = PROJECTS_DIR / "_prototype_blender_3d"
    result = run_combustion_engine_prototype_benchmark(
        target_dir=target_dir,
        is_vertical=is_vertical,
        render_profile=render_profile,
    )
    return result


class BlenderSceneRenderRequest(BaseModel):
    model_name: str = "combustion_engine"
    composition: str = "hero_view"
    is_vertical: bool = True
    render_profile: str = "draft"
    duration_sec: float = 4.0
    narration: str = ""
    reference_image_path: Optional[str] = None
    reference_mode: str = "full"
    visual_profile_id: Optional[str] = None


class VisualDirectionRequest(BaseModel):
    topic: str = "Motor de Combustión de Cuatro Tiempos"
    model_type: str = "combustion_engine"
    reference_image_path: Optional[str] = None
    reference_mode: str = "full"
    visual_profile_id: Optional[str] = None


@router.get("/blender/visual-profiles")
def get_blender_visual_profiles_endpoint():
    """Devuelve la biblioteca de 8 perfiles visuales reutilizables y las 4 modalidades de referencia (Fase 3.3)."""
    from studio.visual_reference_director import VISUAL_PROFILES_LIBRARY, REFERENCE_MODES
    return {
        "visual_profiles": VISUAL_PROFILES_LIBRARY,
        "reference_modes": REFERENCE_MODES,
    }


@router.post("/blender/visual-direction")
def build_visual_direction_endpoint(req: VisualDirectionRequest):
    """Analiza una imagen de referencia con OpenCV (Modo A) o genera dirección artística autónoma (Modo B)."""
    from studio.visual_reference_director import VisualReferenceDirector, AutonomousVisualDirector

    if req.reference_image_path and Path(req.reference_image_path).is_file():
        vrd = VisualReferenceDirector()
        return vrd.build_visual_direction_from_reference(
            image_path=req.reference_image_path,
            reference_mode=req.reference_mode,
            topic_or_title=req.topic,
            model_type=req.model_type,
        )
    avd = AutonomousVisualDirector()
    return avd.generate_autonomous_visual_direction(
        topic_or_title=req.topic,
        model_type=req.model_type,
        preferred_profile_id=req.visual_profile_id,
    )


@router.post("/blender/upload-reference")
async def upload_visual_reference_endpoint(
    file: UploadFile = File(...),
    reference_mode: str = Form("full"),
    topic: str = Form("Motor Monocilíndrico"),
    model_type: str = Form("combustion_engine"),
):
    """Permite subir una imagen de referencia desde la interfaz web y analizarla con OpenCV local (Fase 3.3)."""
    from studio.visual_reference_director import VisualReferenceDirector

    refs_dir = PROJECTS_DIR / "_references"
    refs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "reference.png").name
    dest_path = refs_dir / safe_name
    content = await file.read()
    dest_path.write_bytes(content)

    vrd = VisualReferenceDirector()
    direction = vrd.build_visual_direction_from_reference(
        image_path=dest_path,
        reference_mode=reference_mode,
        topic_or_title=topic,
        model_type=model_type,
    )
    return {
        "success": True,
        "saved_reference_path": str(dest_path.resolve()),
        "visual_direction": direction,
    }


@router.post("/blender/render-scene")
def render_blender_scene_endpoint(req: BlenderSceneRenderRequest):
    """Renderiza una escena individual interactiva en Blender 5.3 con o sin narración."""
    import asyncio
    import io
    import shutil
    import subprocess
    import edge_tts
    import soundfile as sf
    from studio.blender.service import _get_ffmpeg

    target_dir = PROJECTS_DIR / "_prototype_blender_3d"
    target_dir.mkdir(parents=True, exist_ok=True)

    prof_data = get_render_profile(req.render_profile)
    if req.is_vertical:
        width = int(prof_data.get("width", 720))
        height = int(prof_data.get("height", 1280))
        if width > height:
            width, height = height, width
    else:
        width = int(prof_data.get("width", 1280))
        height = int(prof_data.get("height", 720))
        if height > width:
            width, height = height, width
    dur_sec = max(1.5, float(req.duration_sec))

    audio_path = None
    subtitles_path = None

    if req.narration and req.narration.strip():
        text = req.narration.strip()
        voice = "es-MX-JorgeNeural"

        async def _gen_audio():
            comm = edge_tts.Communicate(text, voice)
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf)

        raw = asyncio.run(_gen_audio())
        audio_path = target_dir / "custom_scene_audio.wav"
        audio_path.write_bytes(raw)
        data, sr = sf.read(io.BytesIO(raw))
        dur_sec = max(2.0, len(data) / float(sr))

        subtitles_path = target_dir / "custom_scene.srt"
        from video_pipeline import format_srt_time
        srt_content = f"1\n00:00:00,000 --> {format_srt_time(dur_sec)}\n{text}\n"
        subtitles_path.write_text(srt_content, encoding="utf-8")

    from studio.visual_reference_director import VisualReferenceDirector, AutonomousVisualDirector
    if req.reference_image_path and Path(req.reference_image_path).is_file():
        vis_dir = VisualReferenceDirector().build_visual_direction_from_reference(
            image_path=req.reference_image_path,
            reference_mode=req.reference_mode,
            topic_or_title=req.narration or req.model_name,
            model_type=req.model_name,
        )
    else:
        vis_dir = AutonomousVisualDirector().generate_autonomous_visual_direction(
            topic_or_title=req.narration or req.model_name,
            model_type=req.model_name,
            preferred_profile_id=req.visual_profile_id,
        )

    scene_spec = {
        "scene_id": "custom",
        "model_type": req.model_name,
        "composition_type": req.composition,
        "duration_sec": dur_sec,
        "visual_direction": vis_dir,
        "diagram_spec": {"composition_type": req.composition, "phase": "full_cycle"},
    }

    raw_mp4 = target_dir / "custom_scene_raw.mp4"
    if raw_mp4.exists():
        try:
            raw_mp4.unlink()
        except Exception:
            pass

    final_mp4 = target_dir / "custom_scene.mp4"
    if final_mp4.exists():
        try:
            final_mp4.unlink()
        except Exception:
            pass

    render_scene_3d_video(
        scene=scene_spec,
        output_mp4=raw_mp4,
        width=width,
        height=height,
        render_profile=req.render_profile,
    )

    ffmpeg_exe = _get_ffmpeg()
    if audio_path and audio_path.exists():
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(raw_mp4.resolve()),
            "-i", str(audio_path.resolve()),
        ]
        if subtitles_path and subtitles_path.exists():
            cmd.extend([
                "-vf", f"subtitles={subtitles_path.name}:force_style='FontSize=16,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=60'",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
            ])
        else:
            cmd.extend(["-c:v", "copy"])
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            str(final_mp4.resolve()),
        ])
        subprocess.run(cmd, cwd=str(target_dir.resolve()), check=True, capture_output=True)
    else:
        shutil.copyfile(raw_mp4, final_mp4)

    return {
        "success": True,
        "video_url": f"/projects/_prototype_blender_3d/{final_mp4.name}",
        "composition": req.composition,
        "duration_sec": dur_sec,
        "render_profile": req.render_profile,
    }


@router.post("/profiles")
def update_platform_profiles_endpoint(profiles: dict[str, dict[str, Any]]):
    return {"platform_profiles": save_platform_profiles(profiles)}


@router.post("/research")
def run_standalone_research_endpoint(req: ResearchRequest):
    """Ejecuta la Fase 4 (Research Engine) para que el usuario revise las fuentes, conceptos,
    hechos verificados, estimaciones y contradicciones antes de crear o actualizar el guion."""
    return run_topic_research(
        topic=req.topic,
        main_question=req.main_question,
        category=req.category,
        target_audience=req.target_audience,
        user_provided_notes=req.user_notes,
    )


@router.get("/projects")
def list_explainer_projects():
    """Lista los proyectos maestros de Explainer AI (exp_*) sin afectar los proyectos yt_* o fruti_*."""
    if not PROJECTS_DIR.exists():
        return {"projects": []}
    candidates = sorted(
        [p / "project.json" for p in PROJECTS_DIR.iterdir() if p.name.startswith("exp_") and (p / "project.json").exists()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    items = []
    for fpath in candidates:
        try:
            d = json.loads(fpath.read_text(encoding="utf-8"))
            sb = d.get("storyboards") or {}
            exports = d.get("exports") or {}
            items.append(
                {
                    "project_id": d.get("project_id", fpath.parent.name),
                    "project_name": d.get("project_name", d.get("topic", "")),
                    "topic": d.get("topic", ""),
                    "category": d.get("category", ""),
                    "visual_style": d.get("visual_style", "3d_educational"),
                    "short_scenes_count": len(sb.get("short") or []),
                    "long_scenes_count": len(sb.get("long") or []),
                    "exports_count": len(exports),
                    "updated_at": d.get("updated_at", ""),
                }
            )
        except Exception:
            pass
    return {"projects": items}


@router.get("/project/{project_id}")
def get_explainer_project(project_id: str):
    _, data = _load_explainer_project(project_id)
    return data


@router.post("/project/create")
def create_explainer_project_endpoint(req: CreateExplainerProjectRequest):
    """Crea un Proyecto Maestro completo de EXPLAINER AI (Investigación + Guiones Corto y Largo +
    Storyboards Semánticos + Diagramas SVG Técnicos + Control de Costos + Inspector de Calidad)."""
    t0 = time.perf_counter()
    project_id = f"exp_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    proj_dir = PROJECTS_DIR / project_id
    for sub in ("audio", "images", "diagrams", "exports", "previews"):
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)

    # 1. Investigación verificable (o usar la ya revisada por el usuario)
    research = req.existing_research or run_topic_research(
        topic=req.topic,
        main_question=req.main_question,
        category=req.category,
        target_audience=req.target_audience,
        user_provided_notes=req.user_notes,
    )

    # 2. Generación de Guiones Educativos (Short 1-3m y Long 5-10m + Adaptaciones por red social)
    scripts = generate_educational_scripts(
        research=research,
        duration_mode=req.duration_mode,
        speed=req.speed,
    )

    # 3. Storyboard Semántico (Short y Long)
    short_scenes = generate_storyboard_from_script(
        script_branch=scripts["short"],
        research=research,
        visual_style_key=req.visual_style,
        version_prefix="S",
        speed=req.speed,
    )
    long_scenes = generate_storyboard_from_script(
        script_branch=scripts["long"],
        research=research,
        visual_style_key=req.visual_style,
        version_prefix="L",
        speed=req.speed,
    )

    # 4. Generar Diagramas SVG Técnicos iniciales para todas las escenas (Modo B)
    _generate_all_svg_diagrams_for_version(proj_dir, short_scenes, req.visual_style, version="short")
    _generate_all_svg_diagrams_for_version(proj_dir, long_scenes, req.visual_style, version="long")

    # 5. Registro de Costos y Presupuesto
    ledger = create_default_cost_ledger()
    record_cost_event(
        ledger,
        operation="diagram_generation",
        provider="local_svg_engine",
        elapsed_sec=time.perf_counter() - t0,
        reported_cost_usd=0.0,
        is_free_local_or_tier=True,
        details=f"Generados {len(short_scenes) + len(long_scenes)} diagramas vectoriales SVG técnicos.",
    )

    project_name = req.project_name.strip() or f"¿Cómo funciona {research.get('canonical_topic', req.topic)}?"
    project_data: dict[str, Any] = {
        "project_id": project_id,
        "project_type": "explainer_ai",
        "module": "EXPLAINER AI — ¿CÓMO FUNCIONA?",
        "project_name": project_name,
        "topic": req.topic,
        "main_question": research.get("main_question", req.main_question),
        "category": req.category,
        "target_audience": req.target_audience,
        "lang": req.lang,
        "duration_mode": req.duration_mode,
        "screen_format": req.screen_format,
        "visual_style": req.visual_style,
        "engine": req.engine,
        "voice": req.voice,
        "speed": req.speed,
        "pitch_hz": req.pitch_hz,
        "studio_mastering": req.studio_mastering,
        "bg_music": req.bg_music,
        "bg_music_volume": req.bg_music_volume,
        "subtitle_style": req.subtitle_style,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "research": research,
        "scripts": scripts,
        "storyboards": {
            "short": short_scenes,
            "long": long_scenes,
        },
        "audio_urls": {"short": None, "long": None},
        "exports": {},
        "social_packages": {},
        "cost_ledger": ledger,
        "zip_url": f"/api/explainer/project/{project_id}/zip",
    }

    project_data["quality_control"] = run_quality_control_inspection(
        project_dir=proj_dir,
        project_data=project_data,
        version="short",
        platform_id="youtube_shorts",
    )

    return _save_explainer_project(proj_dir, project_data)


@router.post("/project/{project_id}/duplicate")
def duplicate_explainer_project_endpoint(project_id: str):
    """Duplica un proyecto maestro completo (Fase 17) reutilizando sus recursos para crear nuevas versiones."""
    src_dir, src_data = _load_explainer_project(project_id)
    new_id = f"exp_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    dst_dir = PROJECTS_DIR / new_id
    shutil.copytree(src_dir, dst_dir)

    src_data["project_id"] = new_id
    src_data["project_name"] = f"{src_data.get('project_name', 'Proyecto')} (Copia)"
    src_data["zip_url"] = f"/api/explainer/project/{new_id}/zip"
    return _save_explainer_project(dst_dir, src_data)


@router.post("/project/{project_id}/script/section")
def update_or_regenerate_script_section_endpoint(project_id: str, req: ScriptSectionUpdateRequest):
    """Edita o regenera una sección específica del guion corto o largo (Fase 5 y Fase 9),
    preservando todas las escenas que el usuario haya editado manualmente (manual_edits_locked)."""
    proj_dir, meta = _load_explainer_project(project_id)
    version = req.version if req.version in ("short", "long") else "short"

    if req.regenerate:
        meta["scripts"] = regenerate_single_script_section(
            scripts_bundle=meta["scripts"],
            research=meta["research"],
            version=version,
            section_key=req.section_key,
            custom_instruction=req.instruction,
            speed=float(meta.get("speed", 1.0)),
        )
    elif req.new_text is not None:
        branch = meta["scripts"][version]
        for s in branch.get("sections", []):
            if s["key"] == req.section_key:
                s["text"] = req.new_text.strip()
                s["estimated_duration_sec"] = estimate_speaking_duration_sec(s["text"], speed=float(meta.get("speed", 1.0)))
                break
        full_t = "\n\n".join(s["text"] for s in branch.get("sections", []))
        branch["full_text"] = full_t
        branch["word_count"] = len(full_t.split())
        branch["estimated_duration_sec"] = estimate_speaking_duration_sec(full_t, speed=float(meta.get("speed", 1.0)))
        meta["scripts"]["platform_adaptations"] = build_platform_script_adaptations(
            meta["scripts"]["short"]["sections"],
            meta["scripts"]["long"]["sections"],
            meta["research"],
        )

    # Actualizar storyboard de esa versión conservando las escenas con manual_edits_locked=True
    old_scenes = (meta.get("storyboards") or {}).get(version) or []
    locked_by_section: dict[str, list[dict[str, Any]]] = {}
    for sc in old_scenes:
        if sc.get("manual_edits_locked"):
            locked_by_section.setdefault(sc.get("section_key", ""), []).append(sc)

    prefix = "S" if version == "short" else "L"
    fresh_scenes = generate_storyboard_from_script(
        script_branch=meta["scripts"][version],
        research=meta["research"],
        visual_style_key=meta.get("visual_style", "3d_educational"),
        version_prefix=prefix,
        speed=float(meta.get("speed", 1.0)),
    )
    if locked_by_section:
        merged_scenes = []
        for f_sc in fresh_scenes:
            sec_k = f_sc.get("section_key", "")
            if sec_k in locked_by_section and sec_k != req.section_key:
                merged_scenes.extend(locked_by_section.pop(sec_k))
            elif sec_k not in locked_by_section:
                merged_scenes.append(f_sc)
        for idx, sc in enumerate(merged_scenes, start=1):
            sc["index"] = idx
            sc["scene_id"] = f"{prefix}{idx:02d}"
        fresh_scenes = merged_scenes

    _generate_all_svg_diagrams_for_version(proj_dir, fresh_scenes, meta.get("visual_style", "3d_educational"), version=version)
    meta["storyboards"][version] = fresh_scenes
    return _save_explainer_project(proj_dir, meta)


@router.post("/project/{project_id}/scene/{version}/{scene_id}")
def update_storyboard_scene_endpoint(project_id: str, version: str, scene_id: str, req: SceneUpdateRequest):
    """Permite editar, reordenar, duplicar o cambiar el modo visual de una escena (Fase 6 y Fase 13)
    marcándola con manual_edits_locked=True para no perder ajustes manuales."""
    proj_dir, meta = _load_explainer_project(project_id)
    scenes: list[dict[str, Any]] = (meta.get("storyboards") or {}).get(version) or []
    idx = next((i for i, s in enumerate(scenes) if s.get("scene_id") == scene_id), -1)
    if idx == -1:
        raise HTTPException(status_code=404, detail=f"Escena '{scene_id}' no encontrada.")

    prefix = "S" if version == "short" else "L"

    if req.action == "move_up" and idx > 0:
        scenes[idx - 1], scenes[idx] = scenes[idx], scenes[idx - 1]
    elif req.action == "move_down" and idx < len(scenes) - 1:
        scenes[idx + 1], scenes[idx] = scenes[idx], scenes[idx + 1]
    elif req.action == "duplicate":
        dup = json.loads(json.dumps(scenes[idx]))
        dup["manual_edits_locked"] = True
        scenes.insert(idx + 1, dup)
    elif req.action == "delete" and len(scenes) > 1:
        scenes.pop(idx)
    else:
        sc = scenes[idx]
        if req.narration_text is not None:
            sc["narration_text"] = req.narration_text.strip()
            sc["text"] = sc["narration_text"]
        if req.concept_explained is not None:
            sc["concept_explained"] = req.concept_explained.strip()
        if req.resource_type is not None and req.resource_type in SCENE_RESOURCE_TYPES:
            sc["resource_type"] = req.resource_type
            sc["resource_type_label"] = SCENE_RESOURCE_TYPES[req.resource_type]["name"]
        if req.composition_type is not None:
            sc["composition_type"] = req.composition_type
            sc["composition_type_label"] = COMPOSITION_TYPES.get(req.composition_type, {}).get("name", req.composition_type)
            if "diagram_spec" not in sc:
                sc["diagram_spec"] = {}
            sc["diagram_spec"]["composition_type"] = req.composition_type
        if req.visual_mode is not None:
            sc["visual_mode"] = req.visual_mode
        if req.image_prompt is not None:
            sc["image_prompt"] = req.image_prompt.strip()
        if req.labels is not None:
            sc["labels"] = [lbl.strip() for lbl in req.labels if lbl.strip()][:4]
        if req.camera_motion is not None:
            sc["camera_motion"] = req.camera_motion
        if req.transition is not None:
            sc["transition"] = req.transition
        if req.duration_sec is not None and req.duration_sec >= 1.0:
            sc["duration_sec"] = round(float(req.duration_sec), 2)
        sc["manual_edits_locked"] = True
        sc["status"] = "edited"

    # Re-indexar tiempos acumulados
    curr_t = 0.0
    for i, s in enumerate(scenes, start=1):
        s["index"] = i
        if req.action in ("duplicate", "delete"):
            s["scene_id"] = f"{prefix}{i:02d}"
        dur = float(s.get("duration_sec", 4.0))
        s["start_sec"] = round(curr_t, 2)
        s["end_sec"] = round(curr_t + dur, 2)
        s["timestamp_label"] = f"{video_pipeline.format_mm_ss(s['start_sec'])} → {video_pipeline.format_mm_ss(s['end_sec'])}"
        curr_t = s["end_sec"]

    _generate_all_svg_diagrams_for_version(proj_dir, scenes, meta.get("visual_style", "3d_educational"), version=version)
    meta["storyboards"][version] = scenes
    return _save_explainer_project(proj_dir, meta)


@router.post("/project/{project_id}/synthesize/{version}")
def synthesize_explainer_version_endpoint(project_id: str, version: str):
    """Sintetiza el audio neuronal de la versión 'short', 'long' o 'both' y sincroniza los timestamps reales."""
    proj_dir, meta = _load_explainer_project(project_id)
    try:
        if version == "both":
            _synthesize_version_audio(proj_dir, meta, "short")
            _synthesize_version_audio(proj_dir, meta, "long")
        else:
            _synthesize_version_audio(proj_dir, meta, version if version in ("short", "long") else "short")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error sintetizando narración: {exc}") from exc

    meta["quality_control"] = run_quality_control_inspection(
        project_dir=proj_dir,
        project_data=meta,
        version="short" if version != "long" else "long",
        platform_id="youtube_shorts" if version != "long" else "youtube_video",
    )
    return _save_explainer_project(proj_dir, meta)


@router.post("/project/{project_id}/scene/{version}/{scene_id}/generate-visual")
def generate_scene_visual_endpoint(project_id: str, version: str, scene_id: str):
    """Genera el recurso visual de una escena según su modo (Modo A: Imagen IA con consistencia,
    Modo B: Diagrama Técnico SVG animado, Modo C: Adaptador de Video IA con control de costos)."""
    proj_dir, meta = _load_explainer_project(project_id)
    scenes = (meta.get("storyboards") or {}).get(version) or []
    target_sc = next((s for s in scenes if s.get("scene_id") == scene_id), None)
    if not target_sc:
        raise HTTPException(status_code=404, detail=f"Escena '{scene_id}' no encontrada.")

    t0 = time.perf_counter()
    visual_mode = target_sc.get("visual_mode", "mode_b_diagram")
    w, h = (1080, 1920) if version == "short" else (1920, 1080)
    ts = int(time.time())

    if visual_mode == "mode_b_diagram":
        svg_path = proj_dir / "diagrams" / f"{scene_id}.svg"
        generate_scene_svg_diagram(
            target_sc,
            visual_style_key=meta.get("visual_style", "3d_educational"),
            width=w,
            height=h,
            dest_svg_path=svg_path,
        )
        target_sc["diagram_svg_url"] = f"/projects/{project_id}/diagrams/{scene_id}.svg?t={ts}"
        target_sc["status"] = "ready"
        record_cost_event(
            meta["cost_ledger"],
            operation="diagram_generation",
            provider="local_svg_engine",
            elapsed_sec=time.perf_counter() - t0,
            reported_cost_usd=0.0,
            is_free_local_or_tier=True,
            details=f"Diagrama SVG actualizado para {scene_id}",
        )
    elif visual_mode == "mode_a_image":
        # Verificar límite de generaciones configurado en Control de Costos (Fase 15)
        budget = (meta.get("cost_ledger") or {}).get("budget_config") or {}
        summary = (meta.get("cost_ledger") or {}).get("summary") or {}
        if int(summary.get("images_generated", 0)) >= int(budget.get("max_generations", 120)):
            raise HTTPException(
                status_code=400,
                detail="Se alcanzó el límite máximo de generaciones de imagen configurado en Control de Costos. Puedes aumentarlo o usar Modo B (Diagrama Técnico gratuito).",
            )
        dest_img = proj_dir / "images" / f"{scene_id}.png"
        provider_name = video_pipeline.IMAGE_SETTINGS.get("provider", "auto")
        try:
            video_pipeline.generate_image_for_scene(
                prompt=target_sc["image_prompt"],
                width=w,
                height=h,
                dest_path=dest_img,
                seed=1000 + target_sc.get("index", 1) * 137,
            )
            target_sc["image_url"] = f"/projects/{project_id}/images/{scene_id}.png?t={ts}"
            target_sc["status"] = "ready"
            is_free = provider_name in ("magic", "pollinations", "gemini_pro", "gemini", "hf_dev", "hf_fast", "auto")
            record_cost_event(
                meta["cost_ledger"],
                operation="image_generation",
                provider=provider_name,
                elapsed_sec=time.perf_counter() - t0,
                reported_cost_usd=0.0 if is_free else None,
                is_free_local_or_tier=is_free,
                details=f"Imagen IA Modo A generada para {scene_id} ({w}x{h})",
            )
        except Exception as exc:
            record_cost_event(
                meta["cost_ledger"],
                operation="image_generation",
                provider=provider_name,
                elapsed_sec=time.perf_counter() - t0,
                error=str(exc),
                details=f"Fallo al generar imagen en {scene_id}",
            )
            _save_explainer_project(proj_dir, meta)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    else:
        # Modo C: Video IA externo
        budget = (meta.get("cost_ledger") or {}).get("budget_config") or {}
        if not budget.get("allow_ai_video", False):
            raise HTTPException(
                status_code=400,
                detail="El Modo C (Video IA externo) está desactivado en el Panel de Control de Costos para proteger tu presupuesto. Actívalo en Control de Costos o usa Modo B (Diagrama Animado) / Modo A.",
            )

    return _save_explainer_project(proj_dir, meta)


@router.post("/project/{project_id}/scene/{version}/{scene_id}/preview")
def render_scene_preview_endpoint(project_id: str, version: str, scene_id: str):
    """Renderiza una escena de prueba en .MP4 (Fase 14) antes del renderizado completo."""
    proj_dir, meta = _load_explainer_project(project_id)
    scenes = (meta.get("storyboards") or {}).get(version) or []
    target_sc = next((s for s in scenes if s.get("scene_id") == scene_id), None)
    if not target_sc:
        raise HTTPException(status_code=404, detail=f"Escena '{scene_id}' no encontrada.")

    # Si aún no tiene audio WAV individual, sintetizarlo rápidamente
    scene_wav = proj_dir / "audio" / f"{scene_id}.wav"
    if not scene_wav.exists() and _SYNTHESIZE_FN is not None:
        samples, sr = _SYNTHESIZE_FN(
            text=target_sc.get("narration_text") or target_sc.get("text", ""),
            engine=meta.get("engine", "edge"),
            voice_id=meta.get("voice", "es-MX-JorgeNeural"),
            lang=meta.get("lang", "es-mx"),
            speed=float(meta.get("speed", 1.0)),
            sentence_pause=0.2,
            noise_scale=0.667,
            pitch_hz=int(meta.get("pitch_hz", -2)),
            studio_mastering=bool(meta.get("studio_mastering", True)),
        )
        scene_wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(scene_wav, samples, sr, format="WAV", subtype="PCM_16")
        target_sc["duration_sec"] = round(len(samples) / float(sr), 2)

    aspect = "9:16" if version == "short" else "16:9"
    mp4_path = render_single_scene_preview(
        project_dir=proj_dir,
        scene=target_sc,
        version=version,
        visual_style_key=meta.get("visual_style", "3d_educational"),
        aspect_ratio=aspect,
        subtitle_style=meta.get("subtitle_style", "hormozi_yellow"),
    )
    ts = int(time.time())
    target_sc["preview_video_url"] = f"/projects/{project_id}/previews/{mp4_path.name}?t={ts}"
    _save_explainer_project(proj_dir, meta)
    return {"scene_id": scene_id, "preview_video_url": target_sc["preview_video_url"]}


_EXPORT_JOBS: dict[str, dict[str, Any]] = {}


def _execute_export_pipeline(
    project_id: str,
    selected_platforms: list[str],
    synthesize_missing_audio: bool,
    burn_subtitles: bool,
) -> None:
    """Ejecuta la exportación multiplataforma actualizando el estado de progreso para evitar bloqueos HTTP."""
    proj_dir, meta = _load_explainer_project(project_id)
    profiles = load_platform_profiles()

    _EXPORT_JOBS[project_id] = {
        "status": "rendering",
        "progress_pct": 5,
        "current_platform": "Iniciando preparación y audio",
        "platforms_done": [],
        "error": None,
    }

    try:
        needed_versions = {profiles[p]["version_source"] for p in selected_platforms if p in profiles}
        for ver in needed_versions:
            wav_file = proj_dir / f"narracion_{ver}.wav"
            if synthesize_missing_audio and not wav_file.exists():
                _synthesize_version_audio(proj_dir, meta, ver)

        ts = int(time.time())
        total_p = max(1, len(selected_platforms))

        for idx, pid in enumerate(selected_platforms):
            if pid not in profiles:
                continue
            prof = profiles[pid]
            ver = prof["version_source"]
            scenes = (meta.get("storyboards") or {}).get(ver) or []
            if not scenes:
                continue

            _EXPORT_JOBS[project_id]["current_platform"] = prof["name"]
            _EXPORT_JOBS[project_id]["progress_pct"] = int(10 + (idx / total_p) * 85)

            t0 = time.perf_counter()
            export_info = render_explainer_version_video(
                project_dir=proj_dir,
                scenes=scenes,
                version=ver,
                platform_id=pid,
                visual_style_key=meta.get("visual_style", "3d_educational"),
                subtitle_style=meta.get("subtitle_style", "hormozi_yellow"),
                bg_music=meta.get("bg_music", "doc_mystery"),
                bg_music_volume=float(meta.get("bg_music_volume", 0.14)),
                burn_subtitles=burn_subtitles,
            )
            video_rel = f"/projects/{project_id}/exports/{pid}/video_{pid}.mp4?t={ts}"
            srt_rel = f"/projects/{project_id}/exports/{pid}/subtitulos_{pid}.srt?t={ts}"
            export_info["video_url"] = video_rel
            export_info["srt_url"] = srt_rel
            meta.setdefault("exports", {})[pid] = export_info

            # Paquete social adaptado
            social_pkg = build_social_media_package_for_platform(
                project_id=project_id,
                project_dir=proj_dir,
                platform_id=pid,
                research=meta.get("research") or {},
                scenes=scenes,
                visual_style_key=meta.get("visual_style", "3d_educational"),
                video_rel_url=video_rel,
                srt_rel_url=srt_rel,
            )
            meta.setdefault("social_packages", {})[pid] = social_pkg

            record_cost_event(
                meta["cost_ledger"],
                operation="multiplatform_render",
                provider=f"ffmpeg_{pid}",
                elapsed_sec=time.perf_counter() - t0,
                reported_cost_usd=0.0,
                is_free_local_or_tier=True,
                details=f"Renderizado MP4 + Portada + Copy para {prof['name']} ({prof['width']}x{prof['height']})",
            )
            _EXPORT_JOBS[project_id]["platforms_done"].append(pid)

        first_pid = selected_platforms[0]
        first_ver = profiles[first_pid]["version_source"]
        meta["quality_control"] = run_quality_control_inspection(
            project_dir=proj_dir,
            project_data=meta,
            version=first_ver,
            platform_id=first_pid,
        )
        _save_explainer_project(proj_dir, meta)

        _EXPORT_JOBS[project_id] = {
            "status": "completed",
            "progress_pct": 100,
            "current_platform": "Completado exitosamente",
            "platforms_done": list(selected_platforms),
            "error": None,
        }
    except Exception as exc:
        _EXPORT_JOBS[project_id] = {
            "status": "error",
            "progress_pct": 0,
            "current_platform": "",
            "platforms_done": _EXPORT_JOBS.get(project_id, {}).get("platforms_done", []),
            "error": str(exc),
        }


@router.post("/project/{project_id}/export")
def export_multiplatform_endpoint(project_id: str, req: MultiPlatformExportRequest):
    """Ejecuta la Exportación Multiplataforma (Fase 11) + Social Media Packager (Fase 12) +
    Quality Control (Fase 16). Admite async_mode=True para renderizado en segundo plano sin timeouts."""
    proj_dir, meta = _load_explainer_project(project_id)
    profiles = load_platform_profiles()

    selected = [p for p in req.platforms if p in profiles]
    if not selected:
        raise HTTPException(status_code=400, detail="Selecciona al menos una plataforma válida para exportar.")

    if req.async_mode:
        th = threading.Thread(
            target=_execute_export_pipeline,
            args=(project_id, selected, req.synthesize_missing_audio, req.burn_subtitles),
            daemon=True,
        )
        th.start()
        return {
            "status": "rendering",
            "project_id": project_id,
            "message": f"Exportación de {len(selected)} plataformas iniciada en segundo plano.",
        }

    # Modo sincrónico estándar
    _execute_export_pipeline(project_id, selected, req.synthesize_missing_audio, req.burn_subtitles)
    _, final_meta = _load_explainer_project(project_id)
    return final_meta


@router.get("/project/{project_id}/export-status")
def get_export_status_endpoint(project_id: str):
    """Consulta el estado del proceso de exportación en segundo plano."""
    job = _EXPORT_JOBS.get(project_id)
    if job:
        return job
    proj_dir, meta = _load_explainer_project(project_id)
    exports = meta.get("exports") or {}
    return {
        "status": "completed" if exports else "idle",
        "progress_pct": 100 if exports else 0,
        "current_platform": "",
        "platforms_done": list(exports.keys()),
        "error": None,
    }


@router.post("/project/{project_id}/social/{platform_id}")
def update_social_package_endpoint(project_id: str, platform_id: str, req: SocialPackageEditRequest):
    """Permite editar título, descripción, hashtags, post y pregunta antes de exportar el paquete (Fase 12)."""
    proj_dir, meta = _load_explainer_project(project_id)
    pkg = (meta.get("social_packages") or {}).get(platform_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Paquete social para '{platform_id}' aún no generado.")
    pkg["title"] = req.title.strip()
    pkg["description"] = req.description.strip()
    pkg["hashtags"] = [h.strip() for h in req.hashtags if h.strip()]
    pkg["post_text"] = req.post_text.strip()
    pkg["comment_question"] = req.comment_question.strip()
    return _save_explainer_project(proj_dir, meta)


@router.post("/project/{project_id}/budget")
def update_budget_config_endpoint(project_id: str, req: BudgetConfigRequest):
    """Actualiza la configuración de presupuesto y control de costos del proyecto (Fase 15)."""
    proj_dir, meta = _load_explainer_project(project_id)
    meta.setdefault("cost_ledger", create_default_cost_ledger())["budget_config"] = req.model_dump()
    return _save_explainer_project(proj_dir, meta)


@router.get("/project/{project_id}/zip")
def download_explainer_master_zip_endpoint(project_id: str):
    """Empaqueta el proyecto maestro completo (investigación, fuentes, guiones, storyboards, diagramas SVG,
    audios WAV, videos MP4 por plataforma, portadas PNG y textos de redes sociales) en un archivo .ZIP."""
    proj_dir, meta = _load_explainer_project(project_id)
    zip_path = proj_dir / f"{project_id}_ai_video_studio.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(proj_dir / "project.json", arcname="proyecto_maestro.json")
        zf.writestr(
            "01_investigacion_y_fuentes.json",
            json.dumps(meta.get("research", {}), ensure_ascii=False, indent=2),
        )
        zf.writestr(
            "02_guiones_corto_largo_y_plataformas.json",
            json.dumps(meta.get("scripts", {}), ensure_ascii=False, indent=2),
        )
        zf.writestr(
            "03_paquetes_redes_sociales.json",
            json.dumps(meta.get("social_packages", {}), ensure_ascii=False, indent=2),
        )
        zf.writestr(
            "04_reporte_calidad_y_costos.json",
            json.dumps(
                {
                    "quality_control": meta.get("quality_control", {}),
                    "cost_ledger": meta.get("cost_ledger", {}),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

        for wav_f in proj_dir.glob("narracion_*.wav"):
            zf.write(wav_f, arcname=f"audio/{wav_f.name}")

        for svg_f in (proj_dir / "diagrams").glob("*.svg"):
            zf.write(svg_f, arcname=f"diagramas_svg/{svg_f.name}")

        for img_f in (proj_dir / "images").glob("*.png"):
            zf.write(img_f, arcname=f"imagenes_ia/{img_f.name}")

        exports_root = proj_dir / "exports"
        if exports_root.exists():
            for plat_dir in exports_root.iterdir():
                if not plat_dir.is_dir():
                    continue
                pid = plat_dir.name
                for ext_pat in ("*.mp4", "*.png", "*.srt", "*.ass"):
                    for f in plat_dir.glob(ext_pat):
                        zf.write(f, arcname=f"exportaciones/{pid}/{f.name}")
                pkg = (meta.get("social_packages") or {}).get(pid)
                if pkg:
                    copy_txt = (
                        f"PLATAFORMA: {pid.upper()}\n"
                        f"TÍTULO: {pkg.get('title', '')}\n"
                        f"CATEGORÍA: {pkg.get('category', '')}\n\n"
                        f"DESCRIPCIÓN:\n{pkg.get('description', '')}\n\n"
                        f"TEXTO DE PUBLICACIÓN:\n{pkg.get('post_text', '')}\n\n"
                        f"PREGUNTA PARA COMENTARIOS:\n{pkg.get('comment_question', '')}\n\n"
                        f"HASHTAGS: {' '.join(pkg.get('hashtags', []))}\n"
                    )
                    zf.writestr(f"exportaciones/{pid}/copy_publicacion_{pid}.txt", copy_txt)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{project_id}_explainer_multiplataforma.zip",
    )
