"""Puente de ejecución y automatización headless de Blender 5.3+ (Fase 2).

Proporciona detección automática de binarios de Blender en Windows/Linux,
validación de hardware, ejecución controlada sin entorno gráfico (-b)
y renderizado procedural con EEVEE Next.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

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


def detect_blender_executable() -> Optional[Path]:
    """Detecta el binario ejecutable de Blender en el sistema local."""
    # 1. Variable de entorno personalizada
    custom_env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_BIN")
    if custom_env:
        p = Path(custom_env)
        if p.is_file() and os.access(p, os.X_OK):
            return p

    # 2. Rutas estándar en Windows
    for cand in DEFAULT_BLENDER_CANDIDATES:
        p = Path(cand)
        if p.exists() and p.is_file():
            return p

    # 3. Directorio de usuario / LocalAppData
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cand_user = Path(local_app_data) / "Programs" / "Blender Foundation"
        if cand_user.exists():
            for exe in cand_user.glob("**/blender.exe"):
                if exe.is_file():
                    return exe

    # 4. PATH del sistema
    which_path = shutil.which("blender") or shutil.which("blender.exe")
    if which_path:
        return Path(which_path)

    return None


def get_blender_status() -> dict[str, Any]:
    """Obtiene el diagnóstico y estado de Blender 5.3 en el sistema."""
    exe = detect_blender_executable()
    if not exe:
        return {
            "available": False,
            "version": None,
            "executable": None,
            "render_engine": None,
            "install_guide": "Blender no fue detectado automáticamente. Descarga Blender 5.3 gratuito y de código abierto desde https://www.blender.org/download/ o instala en 'C:\\Program Files\\Blender Foundation\\Blender 5.3\\'.",
        }

    try:
        res = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        first_line = (res.stdout.strip().splitlines() or ["Blender"])[0]
    except Exception as e:
        first_line = f"Detectado pero error al verificar versión: {e}"

    return {
        "available": True,
        "version": first_line,
        "executable": str(exe),
        "render_engine": "BLENDER_EEVEE",
        "install_guide": None,
    }


def execute_blender_script(
    script_path: Path,
    args: Optional[list[str]] = None,
    timeout_sec: int = 900,
    cwd: Optional[Path] = None,
) -> tuple[int, str, str]:
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
