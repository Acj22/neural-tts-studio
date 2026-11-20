"""API Router para el Módulo Animated Shorts (3D/WebGL + Física Rapier + PixelFX + Earshot)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from studio.animated_shorts.topics_catalog import get_all_animated_shorts_topics, get_topic_by_id
from studio.animated_shorts.script_generator import generate_animated_short_script
from studio.animated_shorts.earshot_sound_designer import generate_earshot_foley_track
from studio.animated_shorts.renderer import render_animated_short_video

logger = logging.getLogger("studio.animated_shorts")

router = APIRouter(prefix="/api/animated-shorts", tags=["Animated Shorts Engine"])

PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "projects"
LAST_SHORTS_RENDER_FILE = PROJECTS_DIR / "animated_shorts" / "last_render.json"


class ScriptGenerationRequest(BaseModel):
    topic_id: str = Field(..., description="ID del tema (arqueologia_enigma, ingenieria_extrema, etc.)")
    title: Optional[str] = Field(None, description="Título opcional personalizado o preset")


class FoleyGenerationRequest(BaseModel):
    topic_id: str = Field(...)
    title: str = Field(...)
    scenes: List[Dict[str, Any]] = Field(...)
    total_duration_sec: float = Field(65.0)


class RenderVideoRequest(BaseModel):
    topic_id: str = Field(..., description="ID de la categoría temática")
    title: str = Field(..., description="Título del animated short")
    scenes: List[Dict[str, Any]] = Field(..., description="Lista de escenas en 5 actos con narración")
    voice: str = Field("es-MX-DaliaNeural", description="Voz neuronal para la narración")
    fps: int = Field(30, description="Fotogramas por segundo (30 o 60 fps)")


@router.get("/topics")
def list_topics():
    """Devuelve las categorías de temas, preset de títulos y configuraciones de producción."""
    return {
        "status": "success",
        "topics": get_all_animated_shorts_topics(),
    }


@router.get("/topic/{topic_id}")
def get_topic_detail(topic_id: str):
    """Devuelve la información de un tema específico con sus presets."""
    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Tema '{topic_id}' no encontrado.")
    return {"status": "success", "topic": topic}


@router.post("/generate-script")
def generate_script_endpoint(req: ScriptGenerationRequest):
    """Genera un guion de 5 actos verificado bajo las reglas obligatorias de investigación histórica y científica."""
    try:
        script_data = generate_animated_short_script(req.topic_id, req.title)
        return {
            "status": "success",
            "script": script_data,
        }
    except Exception as e:
        logger.error(f"Error generando guion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-foley")
def generate_foley_endpoint(req: FoleyGenerationRequest):
    """Construye y compila la pista foley procedural con Earshot alineada a los timestamps."""
    try:
        slug = req.title.lower().replace(" ", "_").replace(":", "").replace("¿", "").replace("?", "")[:30]
        out_wav = PROJECTS_DIR / "animated_shorts" / f"foley_{slug}.wav"
        res_path = generate_earshot_foley_track(req.scenes, req.total_duration_sec, out_wav)
        return {
            "status": "success",
            "foley_wav_url": f"/projects/animated_shorts/{res_path.name}",
            "total_duration_sec": req.total_duration_sec,
        }
    except Exception as e:
        logger.error(f"Error generando foley: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last-video")
def get_last_shorts_video():
    """Devuelve los metadatos y URL del último animated short renderizado."""
    if LAST_SHORTS_RENDER_FILE.exists():
        try:
            import json
            data = json.loads(LAST_SHORTS_RENDER_FILE.read_text(encoding="utf-8"))
            return {"status": "success", "has_video": True, "video": data}
        except Exception:
            pass
    return {"status": "success", "has_video": False, "video": None}


@router.post("/render-video")
def render_shorts_video_endpoint(req: RenderVideoRequest):
    """Compila el video animado en 5 actos con narración, foley Earshot y subtítulos 9:16."""
    try:
        import time, json
        video_path, dur_sec = render_animated_short_video(
            topic_id=req.topic_id,
            title=req.title,
            scenes=req.scenes,
            voice=req.voice,
            fps=req.fps,
        )
        rel_url = f"/projects/{video_path.parent.name}/{video_path.name}"
        data = {
            "status": "success",
            "title": req.title,
            "topic_id": req.topic_id,
            "video_url": rel_url,
            "filename": video_path.name,
            "duration": dur_sec,
            "fps": req.fps,
            "voice": req.voice,
            "timestamp": time.time(),
        }
        LAST_SHORTS_RENDER_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_SHORTS_RENDER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    except Exception as e:
        logger.exception("Error al compilar Animated Short:")
        raise HTTPException(status_code=500, detail=str(e))
