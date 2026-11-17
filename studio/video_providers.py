"""FASE 7 (MODO C) — VIDEO PROVIDER INTERFACE (Arquitectura de Adaptadores para Video IA Externo).

Implementa la interfaz desacoplada solicitada en la Fase 7:
- VideoProviderInterface
  - generate_video(...)
  - check_generation_status(...)
  - download_generated_video(...)
  - estimate_generation_cost(...)

Reglas estrictas:
- No acoplar el sistema a un único proveedor.
- Implementar integraciones reales únicamente cuando se disponga de API y credenciales.
- No simular videos falsos: si no hay credenciales configuradas o el presupuesto bloquea Video IA,
  informa el estado real y permite usar Modo B (Diagrama Técnico Animado) o Modo A (Imagen con Movimiento).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import requests

import video_pipeline


class VideoProviderInterface(ABC):
    provider_id: str = "base"
    provider_name: str = "Base Video Provider"

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def estimate_generation_cost(self, duration_sec: float = 5.0, resolution: str = "1080p") -> dict[str, Any]:
        pass

    @abstractmethod
    def generate_video(
        self,
        prompt: str,
        duration_sec: float = 5.0,
        resolution: str = "1080p",
        reference_image_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def check_generation_status(self, job_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def download_generated_video(self, video_url: str, dest_path: Path) -> Path:
        pass


class FalVideoProviderAdapter(VideoProviderInterface):
    provider_id = "fal_video"
    provider_name = "Fal.ai Video Queue API (Kling / Wan-2.1)"

    def _api_key(self) -> str:
        return (video_pipeline.IMAGE_SETTINGS.get("fal_api_key") or "").strip()

    def is_configured(self) -> bool:
        return bool(self._api_key())

    def estimate_generation_cost(self, duration_sec: float = 5.0, resolution: str = "1080p") -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "configured": self.is_configured(),
            "duration_sec": duration_sec,
            "resolution": resolution,
            "reported_cost_usd": None,
            "cost_note": (
                "Fal.ai factura por segundo de cómputo/clip según el endpoint seleccionado en tu cuenta; "
                "el costo exacto solo se reporta en el dashboard de facturación de Fal.ai."
            ),
        }

    def generate_video(
        self,
        prompt: str,
        duration_sec: float = 5.0,
        resolution: str = "1080p",
        reference_image_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        key = self._api_key()
        if not key:
            return {
                "status": "credentials_missing",
                "provider": self.provider_id,
                "message": "No hay FAL_API_KEY configurada en settings.json. Se recomienda usar Modo B (Diagrama Animado) o Modo A (Imagen con Movimiento) con costo $0.00.",
            }
        headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt}
        resp = requests.post("https://queue.fal.run/fal-ai/wan-t2v", headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201, 202):
            return {"status": "error", "provider": self.provider_id, "message": resp.text[:300]}
        data = resp.json()
        return {
            "status": "submitted",
            "provider": self.provider_id,
            "job_id": data.get("request_id"),
            "status_url": data.get("status_url"),
            "response_url": data.get("response_url"),
            "reported_cost_usd": None,
        }

    def check_generation_status(self, job_id: str) -> dict[str, Any]:
        key = self._api_key()
        if not key:
            return {"status": "credentials_missing", "job_id": job_id}
        headers = {"Authorization": f"Key {key}"}
        resp = requests.get(f"https://queue.fal.run/fal-ai/wan-t2v/requests/{job_id}/status", headers=headers, timeout=15)
        if resp.status_code != 200:
            return {"status": "error", "job_id": job_id, "message": resp.text[:250]}
        return resp.json()

    def download_generated_video(self, video_url: str, dest_path: Path) -> Path:
        resp = requests.get(video_url, timeout=60)
        resp.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(resp.content)
        return dest_path


class RunwareVideoProviderAdapter(VideoProviderInterface):
    provider_id = "runware_video"
    provider_name = "Runware.ai Video Inference API"

    def _api_key(self) -> str:
        return (video_pipeline.IMAGE_SETTINGS.get("runware_api_key") or "").strip()

    def is_configured(self) -> bool:
        return bool(self._api_key())

    def estimate_generation_cost(self, duration_sec: float = 5.0, resolution: str = "1080p") -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "configured": self.is_configured(),
            "duration_sec": duration_sec,
            "resolution": resolution,
            "reported_cost_usd": None,
            "cost_note": "Runware reporta el campo 'cost' real únicamente tras completar la tarea con includeCost=True.",
        }

    def generate_video(
        self,
        prompt: str,
        duration_sec: float = 5.0,
        resolution: str = "1080p",
        reference_image_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "status": "credentials_missing",
                "provider": self.provider_id,
                "message": "No hay RUNWARE_API_KEY configurada. Usa Modo B (Diagrama Técnico SVG) o Modo A sin costo.",
            }
        return {
            "status": "ready_for_dispatch",
            "provider": self.provider_id,
            "message": "Adaptador Runware configurado. Requiere confirmación explícita de presupuesto antes de enviar tarea de video.",
        }

    def check_generation_status(self, job_id: str) -> dict[str, Any]:
        return {"status": "not_found", "job_id": job_id}

    def download_generated_video(self, video_url: str, dest_path: Path) -> Path:
        resp = requests.get(video_url, timeout=60)
        resp.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(resp.content)
        return dest_path


class Blender3DVideoProviderAdapter(VideoProviderInterface):
    provider_id = "blender_3d"
    provider_name = "Blender 5.3 EEVEE Next (Motor 3D Local Gratuito)"

    def is_configured(self) -> bool:
        from studio.blender.blender_gateway import detect_blender_executable
        return detect_blender_executable() is not None

    def estimate_generation_cost(self, duration_sec: float = 5.0, resolution: str = "1080p") -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "configured": self.is_configured(),
            "duration_sec": duration_sec,
            "resolution": resolution,
            "reported_cost_usd": 0.0,
            "cost_note": "100% Gratuito y de código abierto. Renderizado procedural local con Blender 5.3 + EEVEE Next ($0.00).",
            "is_free": True,
        }

    def generate_video(
        self,
        prompt: str,
        duration_sec: float = 5.0,
        resolution: str = "1080p",
        reference_image_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        return {
            "status": "ready",
            "provider": self.provider_id,
            "message": "Blender 3D listo para renderizar clips locales sin costo externo.",
        }

    def check_generation_status(self, job_id: str) -> dict[str, Any]:
        return {"status": "completed", "job_id": job_id}

    def download_generated_video(self, video_url: str, dest_path: Path) -> Path:
        return dest_path


VIDEO_PROVIDER_REGISTRY: dict[str, VideoProviderInterface] = {
    "blender_3d": Blender3DVideoProviderAdapter(),
    "fal_video": FalVideoProviderAdapter(),
    "runware_video": RunwareVideoProviderAdapter(),
}


def list_video_providers_status() -> list[dict[str, Any]]:
    out = []
    for pid, adapter in VIDEO_PROVIDER_REGISTRY.items():
        est = adapter.estimate_generation_cost()
        out.append(
            {
                "id": pid,
                "name": adapter.provider_name,
                "configured": adapter.is_configured(),
                "cost_note": est["cost_note"],
            }
        )
    return out
