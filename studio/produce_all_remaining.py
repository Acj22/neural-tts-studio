"""Script secuencial para producción completa de los tres videos piloto de la Fase 3.1.

Genera:
1. pilot_01_transmision_automatica (Categoría: Mecánica)
2. pilot_02_refrigerador (Categoría: Electrodomésticos)
3. pilot_03_impresora_3d (Categoría: Impresión y fabricación)

Copia los videos finales (.mp4) y capturas comparativas (.png) al directorio de artefactos.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from studio.blender.service import _get_ffmpeg
from studio.educational_production import produce_educational_pilot_video

ARTIFACT_DIR = Path(r"C:\Users\angel.cruz\.gemini\antigravity\brain\5d14dc05-8e69-4318-b168-48e564bb8d5a")

PILOTS = [
    ("transmision_automatica", Path("projects/pilot_01_transmision_automatica"), "video_transmision_automatica_v31_9_16.mp4", "snapshot_v31_pilot_1_transmision.png"),
    ("refrigerador", Path("projects/pilot_02_refrigerador"), "video_refrigerador_v31_9_16.mp4", "snapshot_v31_pilot_2_refrigerador.png"),
    ("impresora_3d", Path("projects/pilot_03_impresora_3d"), "video_impresora_3d_v31_9_16.mp4", "snapshot_v31_pilot_3_impresora_3d.png"),
]


def extract_snapshot(video_path: Path, output_png: Path, timestamp_sec: float = 28.0) -> None:
    cmd = [
        _get_ffmpeg(),
        "-y",
        "-ss",
        f"{timestamp_sec:.2f}",
        "-i",
        str(video_path.resolve()),
        "-frames:v",
        "1",
        str(output_png.resolve()),
    ]
    subprocess.run(cmd, check=False, capture_output=True)


def main() -> None:
    t0 = time.time()
    only_filter = sys.argv[1].strip() if len(sys.argv) > 1 else None

    for p_key, out_dir, art_video_name, art_snap_name in PILOTS:
        if only_filter and only_filter not in p_key:
            continue

        print(f"\n🚀 [FASE 3.1] PRODUCIENDO PILOTO ESPECIALIZADO: {p_key}...")
        res = produce_educational_pilot_video(
            pilot_key=p_key,
            output_dir=out_dir,
            width=720,
            height=1280,
            render_profile="test",
            force_rerender=True,
        )

        final_mp4 = Path(res["master_video_path"])
        if final_mp4.is_file() and ARTIFACT_DIR.is_dir():
            shutil.copy2(final_mp4, ARTIFACT_DIR / art_video_name)
            shutil.copy2(final_mp4, ARTIFACT_DIR / f"video_{p_key}_9_16.mp4")
            snap_path = ARTIFACT_DIR / art_snap_name
            extract_snapshot(final_mp4, snap_path, timestamp_sec=min(35.0, res["total_duration_sec"] * 0.45))
            print(f"📦 Copiado a artefactos: {art_video_name} y {art_snap_name}")

    print(f"\n🎉 PRODUCCIÓN FASE 3.1 FINALIZADA EN {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
