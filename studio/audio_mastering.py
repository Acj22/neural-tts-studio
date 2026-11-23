"""Módulo de Masterización de Audio de Alta Fidelidad para AI Video Studio.

Utiliza Spotify Pedalboard (C++ / JUCE) para compresión transparente, ecualización vocal,
filtro pasaltas contra ruidos sordos y limitador con techo a -0.8 dB para evitar saturación digital.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("studio.audio_mastering")

try:
    import pedalboard
    _PEDALBOARD_AVAILABLE = True
except ImportError:
    _PEDALBOARD_AVAILABLE = False


def build_voice_mastering_board() -> Optional[pedalboard.Pedalboard]:
    """Construye una cadena de masterización vocal optimizada para locución."""
    if not _PEDALBOARD_AVAILABLE:
        return None
    try:
        return pedalboard.Pedalboard([
            # 1. Filtro paso alto para eliminar frecuencias subgraves inaudibles (<38 Hz)
            pedalboard.HighpassFilter(cutoff_frequency_hz=38.0),
            # 2. Resaltar presencia vocal clara en 3.2 kHz
            pedalboard.PeakFilter(cutoff_frequency_hz=3200.0, gain_db=1.5, q=1.0),
            # 3. Compresor para pegar la voz y asegurar volumen parejo
            pedalboard.Compressor(threshold_db=-17.0, ratio=2.6, attack_ms=12.0, release_ms=90.0),
            # 4. Ganancia de compensación
            pedalboard.Gain(gain_db=1.5),
            # 5. Limitador estricto para evitar clipping digital en móviles/altavoces
            pedalboard.Limiter(threshold_db=-0.8),
        ])
    except Exception as exc:
        logger.warning(f"No se pudo crear cadena Pedalboard: {exc}")
        return None


def master_audio_samples(samples: np.ndarray, sample_rate: int = 24000) -> np.ndarray:
    """Masteriza un arreglo de muestras de audio en memoria (NumPy float32)."""
    board = build_voice_mastering_board()
    if board is None or len(samples) == 0:
        return samples

    try:
        # Asegurar tipo float32
        data = samples.astype(np.float32)
        # Normalizar si supera 1.0
        max_val = np.max(np.abs(data))
        if max_val > 1.0:
            data = data / max_val
        # Procesar con Pedalboard liberando el GIL
        mastered = board(data, sample_rate)
        return mastered.astype(np.float32)
    except Exception as exc:
        logger.warning(f"Fallo en master_audio_samples: {exc}, devolviendo original")
        return samples

# Alias para compatibilidad con pipelines
apply_studio_mastering = master_audio_samples


def master_audio_file(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """Lee un archivo de audio (WAV/MP3), aplica la cadena Pedalboard y lo guarda."""
    if output_path is None:
        output_path = input_path

    if not _PEDALBOARD_AVAILABLE:
        return input_path

    try:
        from pedalboard.io import AudioFile
        with AudioFile(str(input_path.resolve())) as f:
            audio = f.read(f.frames)
            sr = f.samplerate

        board = build_voice_mastering_board()
        if board:
            mastered = board(audio, sr)
            with AudioFile(str(output_path.resolve()), "w", sr, mastered.shape[0]) as out:
                out.write(mastered)
            logger.info(f"Audio masterizado con Spotify Pedalboard: {output_path.name}")
            return output_path
    except Exception as exc:
        logger.warning(f"Aviso al masterizar archivo con Pedalboard ({exc}), conservando original.")

    return input_path
