"""Puente de ejecución y automatización para Blender 5.3+ (AI Video Studio).
Soporta modo dual:
1. Enlace en vivo por Socket TCP (<50ms de latencia, interactivo mientras Blender está abierto).
2. Modo Headless por Lotes (-b) sin entorno gráfico para producción desatendida.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("studio.blender")

DEFAULT_BLENDER_CANDIDATES = [
    r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender\blender.exe",
]

DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 9876


def detect_blender_executable() -> Optional[Path]:
    """Detecta el binario ejecutable de Blender en el sistema local."""
    custom_env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_BIN")
    if custom_env:
        p = Path(custom_env)
        if p.is_file() and os.access(p, os.X_OK):
            return p

    for cand in DEFAULT_BLENDER_CANDIDATES:
        p = Path(cand)
        if p.exists() and p.is_file():
            return p

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cand_user = Path(local_app_data) / "Programs" / "Blender Foundation"
        if cand_user.exists():
            for exe in cand_user.glob("**/blender.exe"):
                if exe.is_file():
                    return exe

    which_path = shutil.which("blender") or shutil.which("blender.exe")
    if which_path:
        return Path(which_path)

    return None


def is_blender_live_socket_running(
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
    timeout: float = 0.5,
) -> bool:
    """Comprueba si hay una sesión interactiva de Blender escuchando en el puerto del bridge."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(json.dumps({"type": "ping"}).encode("utf-8"))
            data = s.recv(1024).decode("utf-8")
            res = json.loads(data)
            return res.get("status") == "success" and res.get("pong", False)
    except Exception:
        return False


def send_blender_socket_command(
    command: Dict[str, Any],
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Envía un comando JSON a la sesión activa de Blender y espera la respuesta."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            payload = json.dumps(command, ensure_ascii=False).encode("utf-8")
            s.sendall(payload)
            chunks = []
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if len(chunk) < 65536:
                    break
            raw_resp = b"".join(chunks).decode("utf-8")
            return json.loads(raw_resp)
    except Exception as e:
        return {"status": "error", "message": f"Fallo de comunicación socket con Blender: {e}"}


def execute_blender_code_live(
    code: str,
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
) -> Dict[str, Any]:
    """Ejecuta código Python en la sesión viva de Blender por socket en milisegundos."""
    return send_blender_socket_command(
        {"type": "execute_code", "params": {"code": code}},
        host=host,
        port=port,
    )


def get_blender_status() -> Dict[str, Any]:
    """Diagnóstico completo del estado de Blender (CLI Headless + Socket Interactivo)."""
    exe = detect_blender_executable()
    live_socket = is_blender_live_socket_running()

    status: Dict[str, Any] = {
        "available": bool(exe),
        "version": None,
        "executable": str(exe) if exe else None,
        "render_engine": "BLENDER_EEVEE",
        "live_socket_connected": live_socket,
        "bridge_port": DEFAULT_BRIDGE_PORT,
        "mode": "live_socket" if live_socket else "headless_batch",
    }

    if exe:
        try:
            res = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=5)
            first_line = (res.stdout.strip().splitlines() or ["Blender"])[0]
            status["version"] = first_line
        except Exception as e:
            status["version"] = f"Error al verificar versión: {e}"

    return status


def execute_blender_script(
    script_path: Path,
    args: Optional[list[str]] = None,
    timeout_sec: int = 900,
    cwd: Optional[Path] = None,
) -> Tuple[int, str, str]:
    """Ejecuta un script de Python dentro del intérprete de Blender de forma headless (-b)."""
    exe = detect_blender_executable()
    if not exe:
        raise RuntimeError("No se encontró Blender instalado en el sistema. Consulta get_blender_status().")

    cmd = [str(exe), "-b", "--python", str(script_path)]
    if args:
        cmd.append("--")
        cmd.extend(args)

    logger.info("Ejecutando Blender CLI: %s", " ".join(cmd))
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        cwd=str(cwd) if cwd else None,
    )
    return res.returncode, res.stdout, res.stderr
