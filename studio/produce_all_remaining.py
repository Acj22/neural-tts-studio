"""Script secuencial para producción automática de los tres pilotos educativos (Fase 3)."""

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import time
from studio.educational_production import produce_educational_pilot_video

PILOTS = ["transmision_automatica", "refrigerador", "impresora_3d"]

for p_key in PILOTS:
    out_dir = Path(f"projects/pilot_{p_key}") if not p_key.startswith("0") else Path(f"projects/{p_key}")
    if p_key == "transmision_automatica":
        out_dir = Path("projects/pilot_01_transmision_automatica")
    elif p_key == "refrigerador":
        out_dir = Path("projects/pilot_02_refrigerador")
    elif p_key == "impresora_3d":
        out_dir = Path("projects/pilot_03_impresora_3d")

    target_video = out_dir / f"video_{p_key}_9_16.mp4"
    if target_video.exists() and target_video.stat().st_size > 500000:
        print(f"✅ Piloto {p_key} ya existe en {target_video.name}. Saltando...")
        continue

    print(f"\n🚀 INICIANDO PRODUCCIÓN DE PILOTO: {p_key}...")
    try:
        res = produce_educational_pilot_video(
            pilot_key=p_key,
            output_dir=out_dir,
            width=720,
            height=1280,
            render_profile="test",
            force_rerender=False,
        )
        print(f"✅ FINALIZADO: {p_key} -> {res.get('total_duration_sec')}s")
    except Exception as exc:
        print(f"❌ Error en {p_key}: {exc}")
