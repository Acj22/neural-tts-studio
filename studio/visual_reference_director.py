"""Director de Referencias Visuales, Analizador OpenCV Local y Director Visual Autónomo (Fase 3.3).

Implementa los dos modos de operación unificados sobre el mismo motor de Blender + EEVEE + FFmpeg:
- MODO A (CON IMAGEN DE REFERENCIA): `VisualReferenceDirector` + `LocalVisualAnalyzer` (OpenCV + NumPy).
  Extrae paleta dominante (K-Means), color de fondo, silueta, centro visual, escala, proporciones,
  distribución vertical de componentes, dirección de luz principal, contraste y materiales aparentes;
  separa explícitamente características observables de características estimadas; soporta las 4 modalidades
  (`style`, `composition`, `model`, `full`); y ejecuta comparación iterativa con SSIM e histogramas.
- MODO B (SIN IMAGEN DE REFERENCIA): `AutonomousVisualDirector`.
  Interpreta tema, guion, categoría, objetos, procesos y complejidad visual para elegir entre los
  8 Perfiles Visuales Reutilizables (`VISUAL_PROFILES_LIBRARY`) y construir automáticamente la dirección
  artística completa del proyecto, incluyendo previsualización y auto-corrección antes del render final.
"""

from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from studio.content_classifier import classify_educational_topic, VisualCategoryStrategy


# ==============================================================================
# 1. BIBLIOTECA DE 8 PERFILES VISUALES REUTILIZABLES (FASE 3.3 — PUNTO 8)
# ==============================================================================

VISUAL_PROFILES_LIBRARY: dict[str, dict[str, Any]] = {
    "maqueta_tecnica_educativa": {
        "profile_id": "maqueta_tecnica_educativa",
        "name": "1. Maqueta Técnica Educativa",
        "description": "Estética limpia de maqueta física de ingeniería sobre ciclorama Slate Blue con metales satinados y acentos en cobre/latón.",
        "backdrop": {"bg_hex": "#2A4053", "floor_hex": "#1C2A36", "ambient_strength": 0.65},
        "lighting": {
            "key_energy": 680.0,
            "key_color": [1.0, 0.98, 0.95],
            "key_location": [6.0, -10.0, 8.2],
            "fill_energy": 320.0,
            "fill_color": [0.88, 0.93, 1.0],
            "rim_energy": 480.0,
            "rim_color": [1.0, 1.0, 1.0],
            "top_energy": 310.0,
            "temperature_kelvin": 5400,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#94A3B8",
            "primary_roughness": 0.42,
            "primary_metallic": 0.38,
            "cutaway_face_hex": "#E2E8F0",
            "cutaway_roughness": 0.18,
            "cutaway_metallic": 0.85,
            "accent_moving_hex": "#D07644",
            "accent_roughness": 0.22,
            "accent_metallic": 0.85,
            "dark_manifold_hex": "#1E242B",
            "highlight_hex": "#F59E0B",
        },
        "camera_defaults": {"lens": 56.0, "margin": 0.052, "pad": 0.03, "az_deg": 14.0, "el_deg": 10.0},
        "composition": {"target_fill_ratio": 0.74, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "corte_transversal_tecnico": {
        "profile_id": "corte_transversal_tecnico",
        "name": "2. Corte Transversal Técnico",
        "description": "Sección frontal plana de alta legibilidad para mostrar flujos internos, cámaras térmicas y ciclos termodinámicos.",
        "backdrop": {"bg_hex": "#243748", "floor_hex": "#182532", "ambient_strength": 0.70},
        "lighting": {
            "key_energy": 650.0,
            "key_color": [1.0, 0.99, 0.97],
            "key_location": [5.0, -11.0, 7.5],
            "fill_energy": 360.0,
            "fill_color": [0.90, 0.95, 1.0],
            "rim_energy": 420.0,
            "rim_color": [0.95, 0.98, 1.0],
            "top_energy": 290.0,
            "temperature_kelvin": 5600,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#CBD5E1",
            "primary_roughness": 0.38,
            "primary_metallic": 0.30,
            "cutaway_face_hex": "#F1F5F9",
            "cutaway_roughness": 0.16,
            "cutaway_metallic": 0.80,
            "accent_moving_hex": "#EA580C",
            "accent_roughness": 0.24,
            "accent_metallic": 0.82,
            "dark_manifold_hex": "#1E293B",
            "highlight_hex": "#38BDF8",
        },
        "camera_defaults": {"lens": 58.0, "margin": 0.050, "pad": 0.025, "az_deg": 4.0, "el_deg": 6.0},
        "composition": {"target_fill_ratio": 0.76, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "isometrico_industrial": {
        "profile_id": "isometrico_industrial",
        "name": "3. Isométrico Industrial",
        "description": "Perspectiva oblicua a 38° con iluminación cálida de planta industrial para líneas de producción, prensas y metalurgia.",
        "backdrop": {"bg_hex": "#1F2933", "floor_hex": "#141B22", "ambient_strength": 0.60},
        "lighting": {
            "key_energy": 720.0,
            "key_color": [1.0, 0.95, 0.88],
            "key_location": [7.5, -9.0, 9.0],
            "fill_energy": 280.0,
            "fill_color": [0.85, 0.90, 0.98],
            "rim_energy": 500.0,
            "rim_color": [1.0, 0.92, 0.80],
            "top_energy": 340.0,
            "temperature_kelvin": 4800,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#64748B",
            "primary_roughness": 0.45,
            "primary_metallic": 0.55,
            "cutaway_face_hex": "#CBD5E1",
            "cutaway_roughness": 0.22,
            "cutaway_metallic": 0.85,
            "accent_moving_hex": "#F97316",
            "accent_roughness": 0.25,
            "accent_metallic": 0.80,
            "dark_manifold_hex": "#111827",
            "highlight_hex": "#EAB308",
        },
        "camera_defaults": {"lens": 58.0, "margin": 0.058, "pad": 0.035, "az_deg": 36.0, "el_deg": 22.0},
        "composition": {"target_fill_ratio": 0.72, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "modelo_mecanico_estudio": {
        "profile_id": "modelo_mecanico_estudio",
        "name": "4. Modelo Mecánico de Estudio",
        "description": "Alto contraste especular para trenes de engranajes, transmisiones, rodamientos y acoplamientos de precisión.",
        "backdrop": {"bg_hex": "#223242", "floor_hex": "#17222D", "ambient_strength": 0.62},
        "lighting": {
            "key_energy": 710.0,
            "key_color": [1.0, 0.98, 0.95],
            "key_location": [6.5, -9.5, 8.5],
            "fill_energy": 310.0,
            "fill_color": [0.86, 0.92, 1.0],
            "rim_energy": 520.0,
            "rim_color": [1.0, 1.0, 1.0],
            "top_energy": 320.0,
            "temperature_kelvin": 5500,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#8E9DAE",
            "primary_roughness": 0.40,
            "primary_metallic": 0.45,
            "cutaway_face_hex": "#E2E8F0",
            "cutaway_roughness": 0.16,
            "cutaway_metallic": 0.88,
            "accent_moving_hex": "#F59E0B",
            "accent_roughness": 0.18,
            "accent_metallic": 0.92,
            "dark_manifold_hex": "#1E242B",
            "highlight_hex": "#2563EB",
        },
        "camera_defaults": {"lens": 60.0, "margin": 0.052, "pad": 0.025, "az_deg": 16.0, "el_deg": 11.0},
        "composition": {"target_fill_ratio": 0.75, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "visualizacion_tecnologica": {
        "profile_id": "visualizacion_tecnologica",
        "name": "5. Visualización Tecnológica",
        "description": "Iluminación de laboratorio Maker para impresoras 3D, robótica, CNC, sensores y dispositivos mecatrónicos.",
        "backdrop": {"bg_hex": "#1E2D3D", "floor_hex": "#131D28", "ambient_strength": 0.66},
        "lighting": {
            "key_energy": 670.0,
            "key_color": [0.98, 0.99, 1.0],
            "key_location": [6.0, -10.5, 8.0],
            "fill_energy": 330.0,
            "fill_color": [0.85, 0.94, 1.0],
            "rim_energy": 470.0,
            "rim_color": [0.92, 0.97, 1.0],
            "top_energy": 310.0,
            "temperature_kelvin": 5800,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#1F2937",
            "primary_roughness": 0.35,
            "primary_metallic": 0.50,
            "cutaway_face_hex": "#E2E8F0",
            "cutaway_roughness": 0.18,
            "cutaway_metallic": 0.88,
            "accent_moving_hex": "#F97316",
            "accent_roughness": 0.25,
            "accent_metallic": 0.20,
            "dark_manifold_hex": "#111827",
            "highlight_hex": "#D97706",
        },
        "camera_defaults": {"lens": 54.0, "margin": 0.055, "pad": 0.03, "az_deg": 20.0, "el_deg": 14.0},
        "composition": {"target_fill_ratio": 0.74, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "anatomia_3d": {
        "profile_id": "anatomia_3d",
        "name": "6. Anatomía 3D",
        "description": "Iluminación orgánica suave con materiales sub-superficiales satinados para estructuras biológicas y médicas.",
        "backdrop": {"bg_hex": "#1E2A38", "floor_hex": "#141C26", "ambient_strength": 0.72},
        "lighting": {
            "key_energy": 620.0,
            "key_color": [1.0, 0.97, 0.95],
            "key_location": [5.5, -10.0, 7.8],
            "fill_energy": 380.0,
            "fill_color": [0.92, 0.95, 1.0],
            "rim_energy": 410.0,
            "rim_color": [1.0, 0.94, 0.94],
            "top_energy": 280.0,
            "temperature_kelvin": 5200,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#E11D48",
            "primary_roughness": 0.36,
            "primary_metallic": 0.05,
            "cutaway_face_hex": "#FDA4AF",
            "cutaway_roughness": 0.28,
            "cutaway_metallic": 0.05,
            "accent_moving_hex": "#38BDF8",
            "accent_roughness": 0.25,
            "accent_metallic": 0.10,
            "dark_manifold_hex": "#881337",
            "highlight_hex": "#FACC15",
        },
        "camera_defaults": {"lens": 60.0, "margin": 0.055, "pad": 0.03, "az_deg": 12.0, "el_deg": 8.0},
        "composition": {"target_fill_ratio": 0.73, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "ciencia_visual": {
        "profile_id": "ciencia_visual",
        "name": "7. Ciencia Visual",
        "description": "Estética de laboratorio de física y química con alto contraste para partículas, reacciones, campos y ondas.",
        "backdrop": {"bg_hex": "#17253B", "floor_hex": "#0F1828", "ambient_strength": 0.68},
        "lighting": {
            "key_energy": 660.0,
            "key_color": [0.96, 0.98, 1.0],
            "key_location": [6.0, -10.0, 8.0],
            "fill_energy": 340.0,
            "fill_color": [0.85, 0.92, 1.0],
            "rim_energy": 490.0,
            "rim_color": [0.80, 0.95, 1.0],
            "top_energy": 300.0,
            "temperature_kelvin": 6000,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#38BDF8",
            "primary_roughness": 0.20,
            "primary_metallic": 0.40,
            "cutaway_face_hex": "#E0F2FE",
            "cutaway_roughness": 0.15,
            "cutaway_metallic": 0.70,
            "accent_moving_hex": "#F43F5E",
            "accent_roughness": 0.18,
            "accent_metallic": 0.50,
            "dark_manifold_hex": "#1E293B",
            "highlight_hex": "#A855F7",
        },
        "camera_defaults": {"lens": 56.0, "margin": 0.055, "pad": 0.03, "az_deg": 18.0, "el_deg": 12.0},
        "composition": {"target_fill_ratio": 0.74, "vertical_bias": 0.0, "detail_level": "high"},
    },
    "vista_explosionada": {
        "profile_id": "vista_explosionada",
        "name": "8. Vista Explosionada",
        "description": "Encuadre panorámico de despiece axial con separación ordenada de subsistemas y líneas guía claras.",
        "backdrop": {"bg_hex": "#253646", "floor_hex": "#192530", "ambient_strength": 0.68},
        "lighting": {
            "key_energy": 690.0,
            "key_color": [1.0, 0.98, 0.96],
            "key_location": [6.5, -10.5, 8.5],
            "fill_energy": 350.0,
            "fill_color": [0.88, 0.94, 1.0],
            "rim_energy": 460.0,
            "rim_color": [1.0, 1.0, 1.0],
            "top_energy": 310.0,
            "temperature_kelvin": 5500,
            "use_soft_shadows": True,
        },
        "materials": {
            "primary_body_hex": "#94A3B8",
            "primary_roughness": 0.40,
            "primary_metallic": 0.42,
            "cutaway_face_hex": "#E2E8F0",
            "cutaway_roughness": 0.18,
            "cutaway_metallic": 0.85,
            "accent_moving_hex": "#D97706",
            "accent_roughness": 0.20,
            "accent_metallic": 0.88,
            "dark_manifold_hex": "#1E242B",
            "highlight_hex": "#2563EB",
        },
        "camera_defaults": {"lens": 52.0, "margin": 0.065, "pad": 0.04, "az_deg": 24.0, "el_deg": 15.0},
        "composition": {"target_fill_ratio": 0.70, "vertical_bias": 0.0, "detail_level": "high"},
    },
}

REFERENCE_MODES: dict[str, str] = {
    "style": "A. Referencia de estilo (colores, materiales, iluminación, sombras, fondo y acabado)",
    "composition": "B. Referencia de composición (posición, escala, encuadre, perspectiva y márgenes)",
    "model": "C. Referencia de modelo (identificación de zonas y componentes observables del objeto)",
    "full": "D. Referencia completa (combina estilo, composición y orientación de modelo)",
}


def _rgb_to_hex(rgb: tuple[int, int, int] | list[int]) -> str:
    r, g, b = [max(0, min(255, int(round(c)))) for c in rgb[:3]]
    return f"#{r:02X}{g:02X}{b:02X}"


def _hex_to_rgb_norm(hex_str: str) -> list[float]:
    h = hex_str.lstrip("#")
    if len(h) == 6:
        return [round(int(h[0:2], 16) / 255.0, 4), round(int(h[2:4], 16) / 255.0, 4), round(int(h[4:6], 16) / 255.0, 4)]
    return [0.5, 0.5, 0.5]


# ==============================================================================
# 2. ANALIZADOR VISUAL LOCAL CON OPENCV (FASE 3.3 — PUNTOS 4, 6 Y 21)
# ==============================================================================

class LocalVisualAnalyzer:
    """Analizador local de imágenes mediante OpenCV y NumPy (100% gratuito y offline).
    Distingue explícitamente entre características observables y características estimadas."""

    def analyze_image(self, image_path: str | Path) -> dict[str, Any]:
        p = Path(image_path)
        if not p.is_file():
            raise FileNotFoundError(f"No se encontró la imagen de referencia: {p}")

        # Leer con soporte de rutas Unicode en Windows
        raw_bytes = np.fromfile(str(p), dtype=np.uint8)
        bgr = cv2.imdecode(raw_bytes, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError(f"OpenCV no pudo decodificar la imagen: {p}")

        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # 1. Color de fondo (observable en bordes superior, izquierdo y derecho)
        bw = max(4, int(min(h, w) * 0.06))
        top_strip = rgb[:bw, :, :].reshape(-1, 3)
        left_strip = rgb[:, :bw, :].reshape(-1, 3)
        right_strip = rgb[:, w - bw :, :].reshape(-1, 3)
        bottom_strip = rgb[h - bw :, :, :].reshape(-1, 3)
        bg_samples = np.concatenate([top_strip, left_strip, right_strip], axis=0)
        bg_rgb = np.median(bg_samples, axis=0)
        floor_rgb = np.median(bottom_strip, axis=0)
        bg_hex = _rgb_to_hex(bg_rgb)
        floor_hex = _rgb_to_hex(floor_rgb)

        # 2. Segmentación de silueta del objeto principal con sustracción de fondo adaptativa por fila (cancela gradientes verticales de ciclorama)
        border_cols = np.concatenate([lab[:, :bw, :], lab[:, w - bw :, :]], axis=1)  # (h, 2*bw, 3)
        row_bg_lab = np.median(border_cols, axis=1)[:, None, :]  # (h, 1, 3)
        dist_lab = np.linalg.norm(lab - row_bg_lab, axis=2)

        # Las marcas de agua del suelo tienen bajo contraste cromático (< 22 LAB); el objeto real supera ese umbral
        thr_lab = max(22.0, float(np.percentile(dist_lab, 72)) * 0.72)
        fg_mask = (dist_lab > thr_lab).astype(np.uint8) * 255

        # Ignorar marcas de agua sutiles en las esquinas exteriores (mantener componente conexa central principal)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

        num_labels, labels_im, stats, centroids = cv2.connectedComponentsWithStats(fg_mask)
        main_mask = np.zeros_like(fg_mask)
        if num_labels > 1:
            # Elegir las regiones significativas cercanas al centro horizontal
            best_score = -1.0
            best_idx = 1
            for lbl_i in range(1, num_labels):
                area = float(stats[lbl_i, cv2.CC_STAT_AREA])
                cx, cy = centroids[lbl_i]
                center_prox = 1.0 - 0.8 * (abs(cx - w * 0.5) / (w * 0.5))
                score = area * max(0.2, center_prox)
                if score > best_score:
                    best_score = score
                    best_idx = lbl_i
            main_mask[labels_im == best_idx] = 255
            # Incluir componentes adyacentes al cuerpo principal (como colectores curvos)
            x0 = stats[best_idx, cv2.CC_STAT_LEFT]
            y0 = stats[best_idx, cv2.CC_STAT_TOP]
            bw_box = stats[best_idx, cv2.CC_STAT_WIDTH]
            bh_box = stats[best_idx, cv2.CC_STAT_HEIGHT]
            for lbl_i in range(1, num_labels):
                if lbl_i == best_idx:
                    continue
                area = float(stats[lbl_i, cv2.CC_STAT_AREA])
                cx, cy = centroids[lbl_i]
                if area > (w * h * 0.003) and (x0 - w * 0.12 <= cx <= x0 + bw_box + w * 0.12) and (y0 - h * 0.08 <= cy <= y0 + bh_box + h * 0.08):
                    main_mask[labels_im == lbl_i] = 255
        else:
            main_mask = fg_mask

        ys, xs = np.where(main_mask > 0)
        if len(xs) < 50:
            xs = np.array([int(w * 0.25), int(w * 0.75)])
            ys = np.array([int(h * 0.15), int(h * 0.85)])

        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())
        obj_w = max(1, x_max - x_min)
        obj_h = max(1, y_max - y_min)

        center_u = round(float(xs.mean()) / w, 4)
        center_v = round(float(ys.mean()) / h, 4)
        fill_x = round(obj_w / float(w), 4)
        fill_y = round(obj_h / float(h), 4)
        area_ratio = round(float(np.count_nonzero(main_mask)) / float(w * h), 4)
        aspect_hw = round(obj_h / float(obj_w), 4)

        margins = {
            "top": round(y_min / float(h), 4),
            "bottom": round((h - y_max) / float(h), 4),
            "left": round(x_min / float(w), 4),
            "right": round((w - x_max) / float(w), 4),
        }

        # 3. Extracción de paleta dominante del objeto con K-Means (observable)
        fg_pixels = rgb[main_mask > 0].astype(np.float32)
        if len(fg_pixels) > 8000:
            idx_sub = np.linspace(0, len(fg_pixels) - 1, 8000, dtype=np.int32)
            fg_pixels = fg_pixels[idx_sub]

        k_clusters = min(5, max(2, len(fg_pixels) // 50))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 25, 1.0)
        _, k_labels, k_centers = cv2.kmeans(fg_pixels, k_clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        counts = np.bincount(k_labels.flatten(), minlength=k_clusters)
        order = np.argsort(-counts)

        palette_clusters: list[dict[str, Any]] = []
        primary_body_hex = "#94A3B8"
        accent_warm_hex = "#D07644"
        dark_part_hex = "#1E242B"
        cutaway_bright_hex = "#E2E8F0"

        best_warm_score = -1.0
        best_bright_lum = -1.0
        best_dark_lum = 999.0
        best_neutral_area = -1.0

        for rank_idx in order:
            c_rgb = k_centers[rank_idx]
            share = round(float(counts[rank_idx]) / max(1, len(k_labels)), 4)
            c_hex = _rgb_to_hex(c_rgb)
            r_v, g_v, b_v = float(c_rgb[0]), float(c_rgb[1]), float(c_rgb[2])
            lum = 0.299 * r_v + 0.587 * g_v + 0.114 * b_v
            warmth = (r_v - b_v) + 0.35 * (r_v - g_v)
            sat = (max(r_v, g_v, b_v) - min(r_v, g_v, b_v)) / max(1.0, max(r_v, g_v, b_v))

            if warmth > 32.0 and sat > 0.22:
                mat_class = "anodized_copper_or_brass"
                if warmth * share > best_warm_score:
                    best_warm_score = warmth * share
                    accent_warm_hex = c_hex
            elif lum < 75.0:
                mat_class = "dark_cast_or_composite"
                if lum < best_dark_lum:
                    best_dark_lum = lum
                    dark_part_hex = c_hex
            elif lum > 155.0:
                mat_class = "machined_cutaway_metal"
                if lum > best_bright_lum:
                    best_bright_lum = lum
                    cutaway_bright_hex = c_hex
                if share * (lum / 200.0) > best_neutral_area:
                    best_neutral_area = share * (lum / 200.0)
                    primary_body_hex = c_hex
            else:
                mat_class = "cast_aluminum_or_steel"
                if share * (lum / 220.0) > best_neutral_area:
                    best_neutral_area = share * (lum / 220.0)
                    primary_body_hex = c_hex

            palette_clusters.append({
                "hex": c_hex,
                "rgb": [int(round(r_v)), int(round(g_v)), int(round(b_v))],
                "share": share,
                "luminance": round(lum, 1),
                "saturation": round(sat, 3),
                "apparent_material": mat_class,
            })

        # 4. Análisis de iluminación, contraste y sombras (observable + dirección estimada)
        fg_gray = gray[main_mask > 0]
        rms_contrast = round(float(fg_gray.std()) / 128.0, 3) if len(fg_gray) > 10 else 0.35
        shadow_ratio = round(float(np.mean(fg_gray < 65.0)), 3) if len(fg_gray) > 10 else 0.15
        specular_ratio = round(float(np.mean(fg_gray > 215.0)), 3) if len(fg_gray) > 10 else 0.08

        # Determinar dirección de la luz principal comparando luminancia en cuadrantes del objeto
        mid_x = (x_min + x_max) // 2
        mid_y = (y_min + y_max) // 2
        left_lum = float(gray[y_min:y_max, x_min:mid_x].mean()) if mid_x > x_min else 128.0
        right_lum = float(gray[y_min:y_max, mid_x:x_max].mean()) if x_max > mid_x else 128.0
        top_lum = float(gray[y_min:mid_y, x_min:x_max].mean()) if mid_y > y_min else 128.0
        bot_lum = float(gray[mid_y:y_max, x_min:x_max].mean()) if y_max > mid_y else 128.0

        key_side = "left" if left_lum >= right_lum else "right"
        key_x_pos = -6.0 if key_side == "left" else 6.0
        key_el_est = 48.0 if top_lum >= bot_lum else 32.0

        # 5. Distribución vertical de componentes (tercio superior, medio e inferior de la silueta)
        z_top_cut = y_min + obj_h // 3
        z_mid_cut = y_min + (2 * obj_h) // 3
        zones_distribution = {}
        for z_name, r0, r1 in (("upper_zone", y_min, z_top_cut), ("middle_zone", z_top_cut, z_mid_cut), ("lower_zone", z_mid_cut, y_max)):
            sub_m = main_mask[r0:r1, x_min:x_max]
            sub_rgb = rgb[r0:r1, x_min:x_max]
            if np.count_nonzero(sub_m) > 20:
                med_c = np.median(sub_rgb[sub_m > 0], axis=0)
                w_span = round(float(np.where(sub_m > 0)[1].max() - np.where(sub_m > 0)[1].min()) / float(obj_w), 3)
                zones_distribution[z_name] = {
                    "dominant_hex": _rgb_to_hex(med_c),
                    "relative_width_span": w_span,
                }
            else:
                zones_distribution[z_name] = {"dominant_hex": primary_body_hex, "relative_width_span": 0.5}

        # 6. Estimación de ángulo de cámara y distancia (explícitamente marcados como ESTIMADOS)
        symmetry_diff = abs(center_u - 0.5)
        est_az_deg = round((center_u - 0.5) * 45.0, 1) if symmetry_diff > 0.04 else 3.0
        est_el_deg = 6.0
        est_lens_mm = 58.0 if fill_y >= 0.65 else 52.0

        return {
            "image_path": str(p.resolve()),
            "resolution": {"width": w, "height": h, "aspect_ratio": round(w / float(h), 3)},
            "observable_features": {
                "confidence": 0.92,
                "status": "observable",
                "backdrop_hex": bg_hex,
                "backdrop_rgb_norm": _hex_to_rgb_norm(bg_hex),
                "floor_hex": floor_hex,
                "floor_rgb_norm": _hex_to_rgb_norm(floor_hex),
                "visual_center_norm": {"u": center_u, "v": center_v},
                "object_scale_occupancy": {"fill_x": fill_x, "fill_y": fill_y, "area_ratio": area_ratio},
                "visual_proportions_hw": aspect_hw,
                "safe_margins": margins,
                "dominant_palette": palette_clusters,
                "extracted_material_roles": {
                    "primary_body_hex": primary_body_hex,
                    "cutaway_face_hex": cutaway_bright_hex,
                    "accent_moving_hex": accent_warm_hex,
                    "dark_manifold_hex": dark_part_hex,
                },
                "lighting_and_contrast": {
                    "rms_contrast": rms_contrast,
                    "shadow_ratio": shadow_ratio,
                    "specular_ratio": specular_ratio,
                    "key_light_dominant_side": key_side,
                    "top_vs_bottom_luminance_ratio": round(top_lum / max(1.0, bot_lum), 3),
                },
                "component_vertical_distribution": zones_distribution,
            },
            "estimated_features": {
                "confidence": 0.68,
                "status": "estimated",
                "note": "Características tridimensionales inferidas a partir de proyección 2D; la geometría interna exacta proviene del modelo procedural técnico.",
                "camera_type": "PERSP",
                "camera_azimuth_deg": est_az_deg,
                "camera_elevation_deg": est_el_deg,
                "camera_focal_length_mm": est_lens_mm,
                "camera_distance_pad": round(max(0.015, (1.0 - fill_y) * 0.14), 3),
                "key_light_location_3d": [key_x_pos, -10.0, 8.2],
                "key_light_elevation_deg": key_el_est,
                "apparent_roughness": round(max(0.18, min(0.55, 0.45 - specular_ratio * 1.2)), 3),
                "apparent_metallic": round(max(0.35, min(0.88, 0.40 + rms_contrast * 0.8)), 3),
            },
        }


# ==============================================================================
# 3. VISUAL REFERENCE DIRECTOR (MODO A: CON IMAGEN DE REFERENCIA — PUNTOS 4, 5, 7, 21)
# ==============================================================================

class VisualReferenceDirector:
    """Analiza una imagen de referencia del usuario, la traduce a parámetros de Blender según la
    modalidad elegida (`style`, `composition`, `model`, `full`) y compara iterativamente los renders."""

    def __init__(self) -> None:
        self.analyzer = LocalVisualAnalyzer()

    def build_visual_direction_from_reference(
        self,
        image_path: str | Path,
        reference_mode: str = "full",
        topic_or_title: str = "",
        model_type: str = "combustion_engine",
    ) -> dict[str, Any]:
        mode = reference_mode.lower().strip() if reference_mode else "full"
        if mode not in REFERENCE_MODES:
            mode = "full"

        analysis = self.analyzer.analyze_image(image_path)
        obs = analysis["observable_features"]
        est = analysis["estimated_features"]

        # Perfil base de respaldo para los campos no cubiertos por la modalidad seleccionada
        base_profile = json.loads(json.dumps(VISUAL_PROFILES_LIBRARY["corte_transversal_tecnico"]))

        use_style = mode in ("style", "full")
        use_comp = mode in ("composition", "full")
        use_model = mode in ("model", "full")

        # 1. Traducción de Iluminación y Fondo (Modalidades: style, full)
        if use_style:
            backdrop = {
                "bg_hex": obs["backdrop_hex"],
                "bg_rgb": obs["backdrop_rgb_norm"],
                "floor_hex": obs["floor_hex"],
                "floor_rgb": obs["floor_rgb_norm"],
                "ambient_strength": 0.68,
            }
            key_energy = round(640.0 * (0.85 + obs["lighting_and_contrast"]["rms_contrast"]), 1)
            fill_energy = round(340.0 * (1.1 - obs["lighting_and_contrast"]["shadow_ratio"]), 1)
            lighting = {
                "key_energy": key_energy,
                "key_color": [1.0, 0.98, 0.96],
                "key_location": est["key_light_location_3d"],
                "fill_energy": fill_energy,
                "fill_color": [0.88, 0.94, 1.0],
                "rim_energy": 470.0,
                "rim_color": [1.0, 1.0, 1.0],
                "top_energy": 310.0,
                "use_soft_shadows": True,
            }
            roles = obs["extracted_material_roles"]
            materials = {
                "primary_body_hex": roles["primary_body_hex"],
                "primary_roughness": 0.42,
                "primary_metallic": 0.14,
                "cutaway_face_hex": roles["cutaway_face_hex"],
                "cutaway_roughness": 0.34,
                "cutaway_metallic": 0.18,
                "accent_moving_hex": roles["accent_moving_hex"],
                "accent_roughness": 0.32,
                "accent_metallic": 0.28,
                "dark_manifold_hex": roles["dark_manifold_hex"],
                "highlight_hex": "#F59E0B",
            }
        else:
            backdrop = base_profile["backdrop"]
            backdrop["bg_rgb"] = _hex_to_rgb_norm(backdrop["bg_hex"])
            backdrop["floor_rgb"] = _hex_to_rgb_norm(backdrop["floor_hex"])
            lighting = base_profile["lighting"]
            materials = base_profile["materials"]

        # 2. Traducción de Cámara y Composición (Modalidades: composition, full)
        if use_comp:
            target_fill = round(max(0.68, min(0.86, obs["object_scale_occupancy"]["fill_y"])), 3)
            margin_val = round(max(0.038, min(0.085, (1.0 - target_fill) * 0.28)), 4)
            camera_cfg = {
                "camera_type": est["camera_type"],
                "lens": est["camera_focal_length_mm"],
                "az_deg": est["camera_azimuth_deg"],
                "el_deg": est["camera_elevation_deg"],
                "margin": margin_val,
                "pad": est["camera_distance_pad"],
                "target_offset": [0.0, 0.0, 0.0],
            }
            composition_cfg = {
                "target_fill_ratio": target_fill,
                "reference_center_uv": obs["visual_center_norm"],
                "reference_margins": obs["safe_margins"],
                "aspect_proportions_hw": obs["visual_proportions_hw"],
                "detail_level": "high",
            }
        else:
            camera_cfg = dict(base_profile["camera_defaults"])
            camera_cfg["target_offset"] = [0.0, 0.0, 0.0]
            composition_cfg = dict(base_profile["composition"])

        # 3. Orientación de Modelo y Distribución de Componentes (Modalidades: model, full)
        model_guidance = {
            "enabled": use_model,
            "model_type": model_type,
            "vertical_zones": obs["component_vertical_distribution"] if use_model else {},
            "policy": "Adaptar materiales y encuadre de zonas superior/media/inferior sin inventar piezas mecánicas ambiguas.",
        }

        return {
            "mode": "MODE_A_WITH_REFERENCE",
            "reference_mode": mode,
            "reference_mode_description": REFERENCE_MODES[mode],
            "reference_image_path": analysis["image_path"],
            "selected_profile_id": "custom_reference_profile",
            "backdrop": backdrop,
            "lighting": lighting,
            "materials": materials,
            "camera_defaults": camera_cfg,
            "composition": composition_cfg,
            "model_guidance": model_guidance,
            "analysis": analysis,
        }

    def compare_render_with_reference(
        self,
        rendered_path: str | Path,
        reference_path: str | Path,
    ) -> dict[str, Any]:
        """Compara un fotograma renderizado en Blender contra la imagen de referencia del usuario (Punto 21).
        Evalúa SSIM estructural, correlación de paleta/fondo, alineación de escala, posición y contraste,
        y sugiere ajustes paramétricos corregibles."""
        ref_an = self.analyzer.analyze_image(reference_path)
        ren_an = self.analyzer.analyze_image(rendered_path)

        ref_obs = ref_an["observable_features"]
        ren_obs = ren_an["observable_features"]

        # Cargar ambas imágenes redimensionadas a un lienzo común (360x360 centrado en la caja del objeto) para SSIM local
        ref_raw = cv2.imdecode(np.fromfile(str(reference_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        ren_raw = cv2.imdecode(np.fromfile(str(rendered_path), dtype=np.uint8), cv2.IMREAD_COLOR)

        ref_rs = cv2.resize(ref_raw, (320, 320), interpolation=cv2.INTER_AREA)
        ren_rs = cv2.resize(ren_raw, (320, 320), interpolation=cv2.INTER_AREA)

        # 1. SSIM (Structural Similarity Index) en luminancia
        g1 = cv2.cvtColor(ref_rs, cv2.COLOR_BGR2GRAY).astype(np.float32)
        g2 = cv2.cvtColor(ren_rs, cv2.COLOR_BGR2GRAY).astype(np.float32)
        c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
        mu1 = cv2.GaussianBlur(g1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(g2, (11, 11), 1.5)
        mu1_sq, mu2_sq, mu1_mu2 = mu1 * mu1, mu2 * mu2, mu1 * mu2
        sigma1_sq = cv2.GaussianBlur(g1 * g1, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(g2 * g2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(g1 * g2, (11, 11), 1.5) - mu1_mu2
        ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
        ssim_score = round(float(np.clip(ssim_map.mean(), 0.0, 1.0)), 4)

        # 2. Similitud de color de fondo y paleta
        bg_diff = np.linalg.norm(np.array(ref_obs["backdrop_rgb_norm"]) - np.array(ren_obs["backdrop_rgb_norm"]))
        backdrop_sim = round(float(max(0.0, 1.0 - bg_diff * 1.4)), 4)

        h1 = cv2.calcHist([cv2.cvtColor(ref_rs, cv2.COLOR_BGR2HSV)], [0, 1], None, [24, 24], [0, 180, 0, 256])
        h2 = cv2.calcHist([cv2.cvtColor(ren_rs, cv2.COLOR_BGR2HSV)], [0, 1], None, [24, 24], [0, 180, 0, 256])
        cv2.normalize(h1, h1)
        cv2.normalize(h2, h2)
        hist_corr = float(np.clip(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL), 0.0, 1.0))
        color_sim = round(0.55 * backdrop_sim + 0.45 * hist_corr, 4)

        # 3. Alineación de escala (normalizada por eje dominante para comparar referencias 16:9 contra renders 9:16) y posición
        ref_dom_fill = max(ref_obs["object_scale_occupancy"]["fill_x"], ref_obs["object_scale_occupancy"]["fill_y"])
        ren_dom_fill = max(ren_obs["object_scale_occupancy"]["fill_x"], ren_obs["object_scale_occupancy"]["fill_y"])
        scale_diff = ref_dom_fill - ren_dom_fill
        scale_sim = round(float(max(0.0, 1.0 - abs(scale_diff) * 1.1)), 4)

        du = ref_obs["visual_center_norm"]["u"] - ren_obs["visual_center_norm"]["u"]
        dv = ref_obs["visual_center_norm"]["v"] - ren_obs["visual_center_norm"]["v"]
        pos_sim = round(float(max(0.0, 1.0 - math.hypot(du, dv) * 1.8)), 4)

        # 4. Similitud de iluminación y contraste
        c_diff = abs(ref_obs["lighting_and_contrast"]["rms_contrast"] - ren_obs["lighting_and_contrast"]["rms_contrast"])
        light_sim = round(float(max(0.0, 1.0 - c_diff * 1.5)), 4)

        overall_score = round((0.22 * ssim_score + 0.28 * color_sim + 0.24 * scale_sim + 0.14 * pos_sim + 0.12 * light_sim) * 100.0, 2)

        # Detectar diferencias corregibles y calcular deltas de ajuste automático
        adjustments: dict[str, Any] = {}
        notes: list[str] = []
        if abs(scale_diff) > 0.035:
            pad_delta = round(-scale_diff * 0.12, 4)
            adjustments["pad_delta"] = pad_delta
            notes.append(f"Ajustar escala de encuadre (fill render={ren_dom_fill:.2f} vs ref={ref_dom_fill:.2f} -> pad_delta={pad_delta:+.3f})")
        if abs(dv) > 0.03:
            z_delta = round(-dv * 0.85, 3)
            adjustments["target_offset_z_delta"] = z_delta
            notes.append(f"Centrar altura vertical del modelo (dv={dv:+.3f} -> offset_z={z_delta:+.3f})")
        if c_diff > 0.05:
            key_mul = round(1.0 + (ref_obs["lighting_and_contrast"]["rms_contrast"] - ren_obs["lighting_and_contrast"]["rms_contrast"]) * 0.45, 3)
            adjustments["key_energy_multiplier"] = key_mul
            notes.append(f"Calibrar intensidad de luz principal (x{key_mul:.2f}) para igualar contraste")

        return {
            "overall_match_score": overall_score,
            "metrics": {
                "ssim_structural": ssim_score,
                "color_and_backdrop_similarity": color_sim,
                "backdrop_similarity": backdrop_sim,
                "scale_alignment": scale_sim,
                "position_alignment": pos_sim,
                "lighting_contrast_similarity": light_sim,
            },
            "reference_dominant_fill": ref_dom_fill,
            "rendered_dominant_fill": ren_dom_fill,
            "correctable_adjustments": adjustments,
            "correction_notes": notes,
        }


# ==============================================================================
# 4. AUTONOMOUS VISUAL DIRECTOR (MODO B: SIN IMAGEN DE REFERENCIA — PUNTOS 9, 10, 22)
# ==============================================================================

class AutonomousVisualDirector:
    """Diseña automáticamente la dirección artística, perfil visual, materiales, iluminación y estrategia
    de cámaras cuando el usuario no proporciona una imagen de referencia (Puntos 9, 10 y 22)."""

    def generate_autonomous_visual_direction(
        self,
        topic_or_title: str,
        model_type: str,
        scenes: list[dict[str, Any]] | None = None,
        preferred_profile_id: str | None = None,
    ) -> dict[str, Any]:
        strategy: VisualCategoryStrategy = classify_educational_topic(topic_or_title, model_type_hint=model_type)

        # Selección semántica del Perfil Visual más adecuado (Punto 9)
        if preferred_profile_id and preferred_profile_id in VISUAL_PROFILES_LIBRARY:
            profile_id = preferred_profile_id
            reason = f"Perfil seleccionado explícitamente: {preferred_profile_id}."
        else:
            profile_id, reason = self._select_profile_by_content_meaning(topic_or_title, model_type, strategy.category_id, scenes)

        profile = json.loads(json.dumps(VISUAL_PROFILES_LIBRARY[profile_id]))
        backdrop = profile["backdrop"]
        backdrop["bg_rgb"] = _hex_to_rgb_norm(backdrop["bg_hex"])
        backdrop["floor_rgb"] = _hex_to_rgb_norm(backdrop["floor_hex"])

        camera_cfg = dict(profile["camera_defaults"])
        camera_cfg["camera_type"] = "PERSP"
        camera_cfg["target_offset"] = [0.0, 0.0, 0.0]

        return {
            "mode": "MODE_B_AUTONOMOUS_NO_REFERENCE",
            "reference_mode": "autonomous",
            "reference_image_path": None,
            "selected_profile_id": profile_id,
            "selected_profile_name": profile["name"],
            "selection_reasoning": reason,
            "category_id": strategy.category_id,
            "category_name": strategy.name,
            "pedagogical_focus": strategy.pedagogical_focus,
            "backdrop": backdrop,
            "lighting": profile["lighting"],
            "materials": profile["materials"],
            "camera_defaults": camera_cfg,
            "composition": profile["composition"],
            "available_profiles_catalog": list(VISUAL_PROFILES_LIBRARY.keys()),
        }

    def _select_profile_by_content_meaning(
        self,
        topic_or_title: str,
        model_type: str,
        category_id: str,
        scenes: list[dict[str, Any]] | None,
    ) -> tuple[str, str]:
        low = f"{topic_or_title} {model_type}".lower()

        if "transmission" in low or "transmisión" in low or "planetario" in low:
            return (
                "modelo_mecanico_estudio",
                "Tema de transmisión de potencia y tren epicicloidal: requiere alto contraste metálico en latón/acero/azul cobalto y vistas de despiece y estados.",
            )
        if "refriger" in low or "termodin" in low or "calor" in low:
            return (
                "corte_transversal_tecnico",
                "Ciclo termodinámico cerrado con transferencia de calor: requiere corte transversal limpio y contraste entre zonas de alta y baja presión.",
            )
        if "printer" in low or "impresora" in low or "fdm" in low or "aditiva" in low:
            return (
                "visualizacion_tecnologica",
                "Manufactura digital cartesiana: requiere iluminación de laboratorio Maker que destaque perfiles V-Slot oscuros, cama PEI dorada y extrusión incandescente.",
            )
        if "engine" in low or "motor" in low or "pistón" in low or "combustión" in low:
            return (
                "maqueta_tecnica_educativa",
                "Motor térmico monocilíndrico: requiere estética de maqueta técnica seccionada con pistón de cobre y cámara de combustión abierta.",
            )
        if "fábrica" in low or "industrial" in low or "fundición" in low or category_id == "procesos_industriales":
            return ("isometrico_industrial", "Proceso de planta industrial: perspectiva isométrica con iluminación cálida.")
        if "corazón" in low or "anatomía" in low or "médic" in low:
            return ("anatomia_3d", "Estructura biológica: iluminación orgánica suave y contraste anatómico.")
        if "química" in low or "átomo" in low or "cuántic" in low or category_id in ("ciencia", "energia"):
            return ("ciencia_visual", "Fenómeno científico/energético: alto contraste sobre fondo de laboratorio oscuro.")

        return (
            "maqueta_tecnica_educativa",
            f"Selección autónoma para categoría '{category_id}': maqueta educativa de alta claridad.",
        )

    def evaluate_preview_without_reference(
        self,
        rendered_preview_path: str | Path,
        visual_direction: dict[str, Any],
    ) -> dict[str, Any]:
        """Evalúa automáticamente la previsualización contra el perfil visual seleccionado cuando NO hay
        imagen de referencia (Puntos 11 y 22): comprueba encuadre, escala, iluminación, contraste y bordes."""
        analyzer = LocalVisualAnalyzer()
        an = analyzer.analyze_image(rendered_preview_path)
        obs = an["observable_features"]

        fill_y = obs["object_scale_occupancy"]["fill_y"]
        fill_x = obs["object_scale_occupancy"]["fill_x"]
        max_fill = max(fill_x, fill_y)
        margins = obs["safe_margins"]
        contrast = obs["lighting_and_contrast"]["rms_contrast"]
        target_fill = float(visual_direction.get("composition", {}).get("target_fill_ratio", 0.74))

        clipping_detected = margins["top"] < 0.015 or margins["bottom"] < 0.015 or margins["left"] < 0.01 or margins["right"] < 0.01
        too_small = max_fill < 0.48
        contrast_ok = contrast >= 0.14

        adjustments: dict[str, Any] = {}
        notes: list[str] = []
        if clipping_detected:
            adjustments["pad_delta"] = 0.035
            notes.append("Detectado borde próximo al límite de pantalla: ampliando margen de cámara (+0.035).")
        elif too_small or (target_fill - max_fill) > 0.12:
            pad_delta = round(-max(0.015, (target_fill - max_fill) * 0.12), 4)
            adjustments["pad_delta"] = pad_delta
            notes.append(f"Modelo con ocupación moderada ({max_fill:.2f} vs objetivo {target_fill:.2f}): acercando cámara ({pad_delta:+.3f}).")

        if not contrast_ok:
            adjustments["key_energy_multiplier"] = 1.18
            notes.append("Contraste bajo detectado en previsualización: incrementando luz principal (+18%).")

        passed = (not clipping_detected) and (not too_small) and contrast_ok
        quality_score = round(
            (0.40 * (1.0 - min(0.5, abs(target_fill - max_fill))) + 0.35 * (0.0 if clipping_detected else 1.0) + 0.25 * min(1.0, contrast / 0.25)) * 100.0,
            2,
        )

        return {
            "passed": passed,
            "preview_quality_score": quality_score,
            "measured_fill_x": fill_x,
            "measured_fill_y": fill_y,
            "measured_margins": margins,
            "measured_rms_contrast": contrast,
            "clipping_detected": clipping_detected,
            "too_small_detected": too_small,
            "correctable_adjustments": adjustments,
            "auto_correction_notes": notes,
        }
