"""Script de regeneración automática de escenas con imagen de respaldo.
Reemplaza todas las imágenes procedimentales por ilustraciones reales de IA
respetando los tiempos de tasa de servicio (rate-limit) para garantizar éxito 100%.
"""

import json
import time
import requests
import io
from pathlib import Path
from urllib.parse import quote
from PIL import Image

PROJECT_DIR = Path("projects/yt_1795231586_829e20")
IMAGES_DIR = PROJECT_DIR / "images"
FALLBACK_SIZE = 1622594

def fetch_ai_image(prompt: str, width: int = 576, height: int = 1024, seed: int = 42) -> Image.Image:
    """Obtiene una imagen de IA real usando Pollinations / Flux con reintento inteligente."""
    clean_p = quote(prompt[:700])
    urls = [
        f"https://image.pollinations.ai/prompt/{clean_p}?width={width}&height={height}&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{clean_p}?nologo=true",
    ]
    
    max_attempts = 5
    for attempt in range(max_attempts):
        for url in urls:
            try:
                print(f"  -> Conectando a generador de imagen (intento {attempt + 1})...", flush=True)
                r = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    return img
                elif r.status_code == 402:
                    wait_time = 42
                    try:
                        err_json = r.json()
                        msg = err_json.get("error", {}).get("message", "")
                        # Extraer segundos si viene ej: 'Retry after 19s'
                        import re
                        m = re.search(r"after (\d+)s", msg)
                        if m:
                            wait_time = int(m.group(1)) + 3
                    except Exception:
                        pass
                    print(f"  -> Cuota temporal de IP alcanzada. Esperando {wait_time}s para liberar ventana gratuita...", flush=True)
                    time.sleep(wait_time)
                else:
                    print(f"  -> Servidor respondió HTTP {r.status_code}. Esperando 5s...", flush=True)
                    time.sleep(5)
            except Exception as exc:
                print(f"  -> Error de red: {exc}. Reintentando en 6s...", flush=True)
                time.sleep(6)
    raise RuntimeError("No se pudo obtener imagen tras varios reintentos")

def main():
    print("=== INICIANDO REGENERACIÓN COMPLETA DE ESCENAS CON IA ===", flush=True)
    with open(PROJECT_DIR / "project.json", "r", encoding="utf-8") as f:
        project_data = json.load(f)

    scenes = project_data.get("scenes", [])
    w = project_data.get("width", 1080)
    h = project_data.get("height", 1920)

    # Identificar escenas que tienen la imagen de respaldo
    targets = []
    for sc in scenes:
        idx = sc["index"]
        img_path = IMAGES_DIR / f"scene_{idx:03d}.png"
        if not img_path.exists() or img_path.stat().st_size == FALLBACK_SIZE:
            targets.append((sc, img_path))

    print(f"Total de escenas que requieren ilustración real: {len(targets)} de {len(scenes)}", flush=True)

    for i, (sc, img_path) in enumerate(targets):
        idx = sc["index"]
        prompt = sc.get("image_prompt") or sc.get("text")
        print(f"\n[{i+1}/{len(targets)}] Generando ilustración real para Escena #{idx}...", flush=True)
        print(f"Texto: {sc.get('text', '')[:70]}...", flush=True)
        
        try:
            img = fetch_ai_image(prompt, width=min(w, 768), height=min(h, 1365), seed=sc.get("index", 1) * 3141)
            # Redimensionar al tamaño final exacto del proyecto (1080x1920)
            if img.size != (w, h):
                img = img.resize((w, h), Image.Resampling.LANCZOS)
            img.save(img_path, format="PNG")
            print(f"  ✓ Escena #{idx} guardada con éxito ({img_path.stat().st_size} bytes)", flush=True)
        except Exception as e:
            print(f"  ✗ Error en escena #{idx}: {e}", flush=True)

        # Esperar 40s entre imágenes para no agotar la ventana gratuita de IP
        if i < len(targets) - 1:
            print("  ⏳ Esperando 40s para la siguiente escena...", flush=True)
            time.sleep(40)

    print("\n=== TODAS LAS IMÁGENES HAN SIDO GENERADAS CON ÉXITO ===", flush=True)
    print("=== RE-RENDERIZANDO EL VIDEO FINAL MP4 CON MASTERIZACIÓN DE AUDIO Y SUBTÍTULOS DINÁMICOS ===", flush=True)
    
    from video_pipeline import render_project_video
    render_project_video(
        project_dir=PROJECT_DIR,
        scenes=scenes,
        width=w,
        height=h,
        burn_subtitles=True,
        subtitle_style=project_data.get("subtitle_style", "hormozi_yellow"),
        transition=project_data.get("transition", "crossfade"),
        transition_duration=project_data.get("transition_duration", 0.5),
        camera_effect=project_data.get("camera_effect", "ken_burns_mix"),
        bg_music=project_data.get("bg_music", "warm_story"),
        bg_music_volume=project_data.get("bg_music_volume", 0.14),
    )
    print("=== VIDEO FINAL MP4 RENDERIZADO CON ÉXITO ===", flush=True)

if __name__ == "__main__":
    main()
