"""API Router para el Módulo Lemo-Opuscar."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from studio.opuscar.renderer import render_opuscar_animation_video
from studio.opuscar.styles_catalog import OPUSCAR_STATIONS, get_all_opuscar_styles, get_opuscar_style_by_id

logger = logging.getLogger("studio.opuscar")

router = APIRouter(prefix="/api/opuscar", tags=["Lemo-Opuscar Animation Engine"])

PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "projects"
LAST_RENDER_FILE = PROJECTS_DIR / "opuscar_last_render.json"


class OpuscarRenderRequest(BaseModel):
    style_id: str = Field("blueprint_cad", description="Identificador del estilo de animación")
    title: str = Field("Turbocompresor: Esquema y Flujos", description="Título o cabecera técnica")
    narration: str = Field(
        "El turbocompresor utiliza la energía residual de los gases de escape para comprimir el aire admitido.",
        description="Texto a narrar y sincronizar",
    )
    voice: str = Field("es-MX-DaliaNeural", description="Voz de Edge TTS")
    is_vertical: bool = Field(True, description="True para 9:16 vertical (Shorts/TikTok), False para 16:9")
    fps: int = Field(60, description="Fotogramas por segundo (60 fps estándar para fluidez paper-cut)")


@router.get("/styles")
def list_opuscar_styles():
    """Devuelve el catálogo de 99 estilos de cine y animación procedimental organizados por estaciones."""
    return {
        "status": "success",
        "stations": OPUSCAR_STATIONS,
        "styles": get_all_opuscar_styles(),
    }


@router.get("/style/{style_id}")
def get_single_opuscar_style(style_id: str):
    """Devuelve la configuración detallada de un estilo procedimental."""
    style = get_opuscar_style_by_id(style_id)
    if not style:
        raise HTTPException(status_code=404, detail=f"Estilo '{style_id}' no encontrado.")
    return {"status": "success", "style": style}


@router.get("/last-video")
def get_last_opuscar_video():
    """Devuelve los metadatos y URL del último video renderizado para que la UI lo cargue automáticamente."""
    if LAST_RENDER_FILE.exists():
        try:
            import json
            data = json.loads(LAST_RENDER_FILE.read_text(encoding="utf-8"))
            return {"status": "success", "has_video": True, "video": data}
        except Exception:
            pass
    return {"status": "success", "has_video": False, "video": None}


@router.post("/render")
def render_opuscar_video_endpoint(req: OpuscarRenderRequest):
    """Renderiza fotograma a fotograma el video MP4 con narración y subtítulos integrados."""
    try:
        out_dir = PROJECTS_DIR / f"opuscar_{req.style_id}"
        video_path = render_opuscar_animation_video(
            style_id=req.style_id,
            title=req.title,
            narration=req.narration,
            voice=req.voice,
            is_vertical=req.is_vertical,
            fps=req.fps,
            output_dir=out_dir,
        )
        meta_info = {}
        meta_file = out_dir / "meta.json"
        if meta_file.exists():
            try:
                import json
                meta_info = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        res_data = {
            "status": "success",
            "style_id": meta_info.get("style_id", req.style_id),
            "video_url": f"/projects/{out_dir.name}/{video_path.name}",
            "filename": video_path.name,
            "format": "9:16" if req.is_vertical else "16:9",
            "duration": meta_info.get("duration", 0.0),
            "fps": meta_info.get("fps", req.fps),
            "title": meta_info.get("title", req.title),
            "narration": meta_info.get("narration", req.narration),
            "voice": meta_info.get("voice", req.voice),
        }

        # Guardar en caché del último video generado
        try:
            import json, time
            cache_payload = dict(res_data)
            cache_payload["timestamp"] = time.time()
            LAST_RENDER_FILE.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")
        except Exception:
            pass

        return res_data
    except Exception as e:
        logger.exception("Error al renderizar animación Lemo-Opuscar:")
        raise HTTPException(status_code=500, detail=str(e))
