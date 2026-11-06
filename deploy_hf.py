"""Despliega Neural TTS Studio en Hugging Face Spaces (Docker).

Uso (PowerShell):
    $env:HF_WRITE_TOKEN = "hf_xxx"   # Token con permiso WRITE
    uv run --with huggingface_hub python deploy_hf.py [nombre-del-space] [--public]

- Crea el Space como PRIVADO por defecto (recomendado: usa tus claves de API).
- Sube solo el código (sin modelos, proyectos ni settings.json).
- Copia tus claves de settings.json a los "Secrets" del Space (cifrados, no visibles).
"""

import json
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

BASE = Path(__file__).resolve().parent
FILES = [
    "Dockerfile",
    ".dockerignore",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "app.py",
    "video_pipeline.py",
    "frutinovela.py",
]
SECRET_MAP = {
    "gemini_api_key": "GEMINI_API_KEY",
    "hf_token": "HF_TOKEN",
    "gemini_1psid": "GEMINI_1PSID",
    "gemini_1psidts": "GEMINI_1PSIDTS",
    "runware_api_key": "RUNWARE_API_KEY",
    "together_api_key": "TOGETHER_API_KEY",
    "fal_api_key": "FAL_API_KEY",
}


def main() -> None:
    token = os.environ.get("HF_WRITE_TOKEN", "").strip()
    if not token:
        sys.exit("Falta la variable HF_WRITE_TOKEN con un token de Hugging Face con permiso WRITE.")

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    space_name = args[0] if args else "neural-tts-studio"
    private = "--public" not in sys.argv

    api = HfApi(token=token)
    user = api.whoami()["name"]
    repo_id = f"{user}/{space_name}"

    print(f"Creando Space {repo_id} ({'privado' if private else 'público'})...")
    api.create_repo(repo_id, repo_type="space", space_sdk="docker", private=private, exist_ok=True)

    # Secretos desde settings.json local
    settings_file = BASE / "settings.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
    for key, env_name in SECRET_MAP.items():
        val = (settings.get(key) or "").strip()
        if val:
            api.add_space_secret(repo_id, env_name, val)
            print(f"  Secreto configurado: {env_name}")
    provider = (settings.get("provider") or "auto").strip()
    api.add_space_variable(repo_id, "IMAGE_PROVIDER", provider)

    app_pwd = os.environ.get("APP_PASSWORD", "").strip()
    if app_pwd:
        api.add_space_secret(repo_id, "APP_PASSWORD", app_pwd)
        print("  Secreto configurado: APP_PASSWORD")

    print("Subiendo código...")
    for rel in FILES:
        api.upload_file(path_or_fileobj=str(BASE / rel), path_in_repo=rel, repo_id=repo_id, repo_type="space")
    api.upload_folder(folder_path=str(BASE / "static"), path_in_repo="static", repo_id=repo_id, repo_type="space")

    print(f"\nListo. Space: https://huggingface.co/spaces/{repo_id}")
    print("La primera construcción tarda ~5-8 minutos (instala dependencias y descarga voces).")


if __name__ == "__main__":
    main()
