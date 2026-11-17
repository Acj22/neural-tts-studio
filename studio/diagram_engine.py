"""FASE 7 — HYBRID VISUAL ENGINE (Modo A: Movimiento Avanzado + Modo B: Diagramas Técnicos SVG y Animación de Componentes).

Genera:
1. Archivos SVG vectoriales limpios (.svg) con flechas, etiquetas, números y esquemas técnicos.
2. Fotogramas animados de alta resolución (1920x1080 en 16:9 y reencuadre inteligente nativo 1080x1920 en 9:16)
   donde las piezas (pistón, válvulas, cigüeñal, engranajes planetarios, ondas GPS, rodillos ATM, campo ITO)
   se mueven en sincronía con el progreso de la escena, con etiquetas anti-colisión que jamás tapan las piezas.
"""

from __future__ import annotations

import math
import re
import textwrap
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import video_pipeline
from studio.models import COMPOSITION_TYPES, VISUAL_CONSISTENCY_STYLES


def _hex_to_rgb(hex_str: str, default: tuple[int, int, int] = (56, 189, 248)) -> tuple[int, int, int]:
    h = (hex_str or "").strip().lstrip("#")
    if len(h) == 6:
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except Exception:
            pass
    return default


def generate_scene_svg_diagram(
    scene: dict[str, Any],
    visual_style_key: str = "3d_educational",
    width: int = 1920,
    height: int = 1080,
    dest_svg_path: Optional[Path] = None,
) -> str:
    """Genera un diagrama vectorial SVG estándar (Fase 7 - Modo B) con cuadrícula de ingeniería,
    componentes numerados, flechas direccionales y etiquetas fuera del área del mecanismo."""
    style = VISUAL_CONSISTENCY_STYLES.get(visual_style_key) or VISUAL_CONSISTENCY_STYLES["3d_educational"]
    pal = style["palette"]
    concept = (scene.get("concept_explained") or "Diagrama Técnico Explicativo").replace("&", "&amp;").replace("<", "&lt;")
    labels = scene.get("labels") or ["1. Entrada", "2. Mecanismo", "3. Proceso", "4. Salida"]
    res_label = (scene.get("resource_type_label") or "📐 Diagrama Técnico").replace("&", "&amp;")

    cx, cy = width // 2, int(height * 0.44)
    r_main = min(width, height) // 5

    nodes_svg = []
    positions = [
        (int(width * 0.18), int(height * 0.28)),
        (int(width * 0.82), int(height * 0.28)),
        (int(width * 0.18), int(height * 0.62)),
        (int(width * 0.82), int(height * 0.62)),
    ]
    anchor_offsets = [(-r_main // 2, -r_main // 3), (r_main // 2, -r_main // 3), (-r_main // 2, r_main // 3), (r_main // 2, r_main // 3)]

    for idx, lbl in enumerate(labels[:4]):
        clean_lbl = lbl.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        bx, by = positions[idx]
        ax, ay = cx + anchor_offsets[idx][0], cy + anchor_offsets[idx][1]
        nodes_svg.append(
            f'<line x1="{bx}" y1="{by}" x2="{ax}" y2="{ay}" stroke="{pal["accent_primary"]}" stroke-width="3" stroke-dasharray="6,4" marker-end="url(#arrow)" />'
            f'<circle cx="{ax}" cy="{ay}" r="8" fill="{pal["accent_secondary"]}" />'
            f'<rect x="{bx - 190}" y="{by - 28}" width="380" height="54" rx="12" fill="{pal["bg_secondary"]}" stroke="{pal["accent_primary"]}" stroke-width="2" />'
            f'<text x="{bx}" y="{by + 7}" fill="{pal["text"]}" font-family="Arial, sans-serif" font-size="21" font-weight="bold" text-anchor="middle">{clean_lbl}</text>'
        )

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
      <path d="M 48 0 L 0 0 0 48" fill="none" stroke="{pal["bg_secondary"]}" stroke-width="1"/>
    </pattern>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{pal["accent_primary"]}" />
    </marker>
  </defs>
  <rect width="100%" height="100%" fill="{pal["bg_primary"]}" />
  <rect width="100%" height="100%" fill="url(#grid)" />
  <rect x="60" y="42" width="{width - 120}" height="86" rx="16" fill="{pal["bg_secondary"]}" stroke="{pal["accent_primary"]}" stroke-width="2" />
  <text x="95" y="78" fill="{pal["accent_primary"]}" font-family="Arial, sans-serif" font-size="20" font-weight="bold">{res_label}</text>
  <text x="95" y="112" fill="{pal["text"]}" font-family="Arial, sans-serif" font-size="28" font-weight="bold">{concept}</text>
  <circle cx="{cx}" cy="{cy}" r="{r_main + 24}" fill="none" stroke="{pal["accent_primary"]}" stroke-width="2" stroke-dasharray="10,8" />
  <circle cx="{cx}" cy="{cy}" r="{r_main}" fill="{pal["bg_secondary"]}" stroke="{pal["accent_secondary"]}" stroke-width="4" />
  {"".join(nodes_svg)}
</svg>
"""
    if dest_svg_path is not None:
        dest_svg_path.parent.mkdir(parents=True, exist_ok=True)
        dest_svg_path.write_text(svg, encoding="utf-8")
    return svg


def _sanitize_display_text(text: str) -> str:
    """Elimina emojis no soportados por fuentes TrueType estándar y sustituye símbolos
    para evitar cuadros de glifo desconocido (tofu) o caracteres corruptos."""
    if not text:
        return ""
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    cleaned = re.sub(r"[🖼️📐⚖️🔢🔍🧬🗺️📈⚙️🎬✨💡🔥⚡⏱️🛠️]", "", cleaned)
    cleaned = cleaned.replace("→", " a ").replace("↓", " (Baja)").replace("↑", " (Sube)").replace("←", "<-")
    return re.sub(r"\s+", " ", cleaned).strip()


def _draw_callout_badge(
    draw: ImageDraw.ImageDraw,
    box_center: tuple[int, int],
    target_pt: tuple[int, int],
    label_text: str,
    is_active: bool,
    accent_rgb: tuple[int, int, int],
    active_rgb: tuple[int, int, int],
    bg_rgb: tuple[int, int, int],
    font: Any,
    box_w: int = 420,
    box_h: int = 58,
    opacity_mult: float = 1.0,
) -> None:
    """Dibuja una etiqueta técnica inteligente de alta visibilidad en móviles, con tipografía
    ampliada (32-36px), formato píldora y punto de anclaje de alta precisión."""
    if opacity_mult <= 0.05:
        return
    bx, by = box_center
    tx, ty = target_pt

    clean_lbl = _sanitize_display_text(label_text)
    if not clean_lbl:
        return

    line_col = active_rgb if is_active else (
        int(accent_rgb[0] * opacity_mult),
        int(accent_rgb[1] * opacity_mult),
        int(accent_rgb[2] * opacity_mult),
    )
    border_w = 4 if is_active else 2

    # Línea guía con trazado limpio hacia el punto del componente
    draw.line([(bx, by), (tx, ty)], fill=line_col, width=border_w)
    dot_r = 10 if is_active else 6
    draw.ellipse([tx - dot_r, ty - dot_r, tx + dot_r, ty + dot_r], fill=active_rgb if is_active else accent_rgb, outline=(255, 255, 255), width=2)

    x0, y0 = bx - box_w // 2, by - box_h // 2
    x1, y1 = bx + box_w // 2, by + box_h // 2

    # Fondo píldora de alto contraste
    fill_col = (18, 30, 52) if is_active else (12, 18, 30)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=fill_col, outline=line_col, width=border_w)

    short_lbl = clean_lbl if len(clean_lbl) <= 36 else (clean_lbl[:34] + "…")
    bbox = draw.textbbox((0, 0), short_lbl, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_col = (254, 240, 138) if is_active else (255, 255, 255)
    draw.text((bx - tw // 2, by - th // 2 - 2), short_lbl, font=font, fill=text_col)


def _draw_combustion_engine_cutaway(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    scale: float,
    progress: float,
    phase: str,
    accent_rgb: tuple[int, int, int],
    warn_rgb: tuple[int, int, int],
    ok_rgb: tuple[int, int, int],
    composition_type: str = "hero_view",
    font_hud: Optional[Any] = None,
) -> list[tuple[int, int]]:
    """Dibuja y anima el motor de combustión interna en corte con cinemática precisa (carrera amplia de 240px,
    4 tiempos sincronizados, flujo de gas con partículas, chispa eléctrica y cigüeñal balanceado),
    adaptando el encuadre según el tipo de composición (HERO, CLOSE-UP, CUTAWAY, PROCESS, INFOGRAPHIC)."""
    # 1. Determinar ángulo del cigüeñal según la fase operativa explicada
    if phase == "intake":
        crank_angle = 0.05 * math.pi + progress * 0.90 * math.pi  # 0° -> 180° (Pistón desciende al PMI)
    elif phase == "compression":
        crank_angle = 1.05 * math.pi + progress * 0.90 * math.pi  # 180° -> 360° (Pistón asciende al PMS)
    elif phase == "combustion":
        crank_angle = 2.0 * math.pi + progress * 0.25 * math.pi   # En el PMS: salto de chispa y pico de presión
    elif phase == "expansion":
        crank_angle = 2.10 * math.pi + progress * 0.85 * math.pi  # 360° -> 540° (Pistón desciende con fuerza útil)
    elif phase == "crankshaft_exhaust":
        crank_angle = 3.05 * math.pi + progress * 0.90 * math.pi  # 540° -> 720° (Pistón asciende y barre escape)
    else:
        crank_angle = progress * 4.0 * math.pi                    # Ciclo continuo fluido (720° completos)

    # 2. Ajuste de encuadre según el tipo de composición
    render_scale = scale
    offset_cy = cy

    if composition_type == "close_up_view":
        # Acercamiento macro al componente activo (Culata/Chispa o Pistón)
        render_scale = scale * 1.25
        if phase in ("combustion", "intake"):
            offset_cy = cy + int(140 * render_scale * 0.35)  # Enfocar culata arriba
        else:
            offset_cy = cy - int(90 * render_scale * 0.25)   # Enfocar pistón y biela

    cyl_w = int(185 * render_scale)
    cyl_h = int(245 * render_scale)
    cyl_top = offset_cy - int(160 * render_scale)
    cyl_bot = cyl_top + cyl_h
    crank_r = int(58 * render_scale)                         # Carrera del pistón = 2 * crank_r (~240px en 9:16)
    crank_y = cyl_bot + int(96 * render_scale)

    # 3. Bloque del motor con aletas metálicas y camisa interior
    fin_w = int(32 * render_scale)
    # Aletas de disipación térmica laterales
    for f_i in range(5):
        fy = cyl_top + int((24 + f_i * 42) * render_scale)
        fh = int(16 * render_scale)
        # Izquierda
        draw.rounded_rectangle([cx - cyl_w // 2 - fin_w, fy, cx - cyl_w // 2, fy + fh], radius=4, fill=(30, 41, 59), outline=accent_rgb, width=2)
        # Derecha
        draw.rounded_rectangle([cx + cyl_w // 2, fy, cx + cyl_w // 2 + fin_w, fy + fh], radius=4, fill=(30, 41, 59), outline=accent_rgb, width=2)

    # Carcasa exterior del bloque de cilindros
    draw.rounded_rectangle(
        [cx - cyl_w // 2 - int(24 * render_scale), cyl_top - int(44 * render_scale), cx + cyl_w // 2 + int(24 * render_scale), crank_y + crank_r + int(36 * render_scale)],
        radius=20,
        fill=(17, 24, 39),
        outline=accent_rgb,
        width=3,
    )

    # Canales de refrigeración líquida (Water Jackets)
    wj_w = int(16 * render_scale)
    draw.rounded_rectangle([cx - cyl_w // 2 - wj_w - 4, cyl_top + int(10 * render_scale), cx - cyl_w // 2 - 4, cyl_bot - int(10 * render_scale)], radius=6, fill=(14, 116, 144))
    draw.rounded_rectangle([cx + cyl_w // 2 + 4, cyl_top + int(10 * render_scale), cx + cyl_w // 2 + wj_w + 4, cyl_bot - int(10 * render_scale)], radius=6, fill=(14, 116, 144))

    # Camisa del cilindro (Cylinder bore)
    draw.rectangle(
        [cx - cyl_w // 2, cyl_top, cx + cyl_w // 2, cyl_bot],
        fill=(10, 15, 26),
        outline=(148, 163, 184),
        width=3,
    )

    # 4. Cinemática del pistón (Carrera armónica PMS -> PMI)
    norm_stroke = 0.5 * (1.0 - math.cos(crank_angle))
    stroke_travel = 2 * crank_r
    piston_top_y = cyl_top + int(24 * render_scale) + int(norm_stroke * stroke_travel)
    piston_h = int(66 * render_scale)
    piston_bot_y = piston_top_y + piston_h

    # 5. Estado térmico y color del fluido en la cámara de combustión
    cycle_deg = (math.degrees(crank_angle) % 720.0)
    is_intake_stroke = phase == "intake" or (0 <= cycle_deg < 180 and phase not in ("combustion", "expansion"))
    is_compression_stroke = phase == "compression" or (180 <= cycle_deg < 350 and phase not in ("combustion", "expansion"))
    is_power_stroke = phase in ("combustion", "expansion") or (350 <= cycle_deg < 540)
    is_exhaust_stroke = phase == "crankshaft_exhaust" or (540 <= cycle_deg < 720)

    if is_intake_stroke:
        gas_col = (30, 144, 255)     # Azul brillante: mezcla aire-gasolina fresca
    elif is_compression_stroke:
        gas_col = (234, 179, 8)      # Oro/ámbar denso: mezcla comprimida
    elif is_power_stroke:
        gas_col = (249, 115, 22)     # Naranja/fuego incandescente: deflagración
    else:
        gas_col = (100, 116, 139)    # Gris carbón: gases residuales quemados

    # Relleno de la cámara de combustión según el volumen variable del cilindro
    if piston_top_y > cyl_top + 4:
        draw.rectangle([cx - cyl_w // 2 + 3, cyl_top + 3, cx + cyl_w // 2 - 3, piston_top_y], fill=gas_col)

    # Partículas y líneas de flujo cinemático
    num_particles = 10 if composition_type in ("process_view", "cutaway_view") else 6
    for p_i in range(num_particles):
        px = cx - cyl_w // 3 + int((p_i / float(max(1, num_particles - 1))) * (2 * cyl_w // 3))
        if is_intake_stroke:
            py = cyl_top + 16 + int(((p_i * 22 + int(progress * 80)) % max(16, piston_top_y - cyl_top - 12)))
            p_col = (186, 230, 253)
        elif is_power_stroke:
            py = cyl_top + 18 + int((p_i * 17) % max(16, piston_top_y - cyl_top - 12))
            p_col = (254, 240, 138)
        else:
            py = cyl_top + 16 + int(((p_i * 19) % max(16, piston_top_y - cyl_top - 12)))
            p_col = (226, 232, 240)
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=p_col)

    # 6. Válvulas de Admisión (izquierda) y Escape (derecha) con apertura visible
    v_lift = int(16 * render_scale)
    intake_open = v_lift if is_intake_stroke else 0
    exhaust_open = v_lift if is_exhaust_stroke else 0

    v_left_x = cx - int(52 * render_scale)
    v_right_x = cx + int(52 * render_scale)

    # Colectores curvados de culata
    draw.arc([v_left_x - int(45 * render_scale), cyl_top - int(65 * render_scale), v_left_x + 10, cyl_top], start=180, end=270, fill=(30, 144, 255) if intake_open else (71, 85, 105), width=6)
    draw.arc([v_right_x - 10, cyl_top - int(65 * render_scale), v_right_x + int(45 * render_scale), cyl_top], start=270, end=360, fill=(239, 68, 68) if exhaust_open else (71, 85, 105), width=6)

    # Válvula de Admisión (Vástago y Cabeza biselada)
    draw.line([(v_left_x, cyl_top - int(42 * render_scale)), (v_left_x, cyl_top + intake_open)], fill=ok_rgb if intake_open else (203, 213, 225), width=5)
    draw.polygon([
        (v_left_x - int(20 * render_scale), cyl_top + intake_open + 2),
        (v_left_x + int(20 * render_scale), cyl_top + intake_open + 2),
        (v_left_x + int(14 * render_scale), cyl_top + intake_open - int(6 * render_scale)),
        (v_left_x - int(14 * render_scale), cyl_top + intake_open - int(6 * render_scale)),
    ], fill=ok_rgb if intake_open else (226, 232, 240), outline=(255, 255, 255))

    # Válvula de Escape (Vástago y Cabeza biselada)
    draw.line([(v_right_x, cyl_top - int(42 * render_scale)), (v_right_x, cyl_top + exhaust_open)], fill=warn_rgb if exhaust_open else (203, 213, 225), width=5)
    draw.polygon([
        (v_right_x - int(20 * render_scale), cyl_top + exhaust_open + 2),
        (v_right_x + int(20 * render_scale), cyl_top + exhaust_open + 2),
        (v_right_x + int(14 * render_scale), cyl_top + exhaust_open - int(6 * render_scale)),
        (v_right_x - int(14 * render_scale), cyl_top + exhaust_open - int(6 * render_scale)),
    ], fill=warn_rgb if exhaust_open else (226, 232, 240), outline=(255, 255, 255))

    # 7. Bujía central de ignición y Arco Eléctrico
    plug_w = int(12 * render_scale)
    draw.rectangle([cx - plug_w, cyl_top - int(48 * render_scale), cx + plug_w, cyl_top - int(10 * render_scale)], fill=(248, 250, 252), outline=accent_rgb, width=2)
    # Aislador cerámico con nervaduras
    draw.line([(cx - plug_w, cyl_top - int(38 * render_scale)), (cx + plug_w, cyl_top - int(38 * render_scale))], fill=(100, 116, 139), width=2)
    draw.line([(cx - plug_w, cyl_top - int(26 * render_scale)), (cx + plug_w, cyl_top - int(26 * render_scale))], fill=(100, 116, 139), width=2)
    # Electrodo central
    draw.line([(cx, cyl_top - int(10 * render_scale)), (cx, cyl_top + int(4 * render_scale))], fill=(245, 158, 11), width=4)

    # Ignición: Salto de chispa y frente de llama expansivo
    if is_power_stroke or (340 <= cycle_deg <= 410):
        # Rayo eléctrico ramificado
        spark_pts = [
            (cx, cyl_top + int(4 * render_scale)),
            (cx - int(7 * render_scale), cyl_top + int(12 * render_scale)),
            (cx + int(6 * render_scale), cyl_top + int(18 * render_scale)),
            (cx, cyl_top + int(26 * render_scale)),
        ]
        draw.line(spark_pts, fill=(255, 255, 255), width=4)
        # Frente de llama circular expansivo
        flame_r = int((24 + 16 * math.sin(progress * math.pi * 3)) * render_scale)
        draw.ellipse([cx - flame_r, cyl_top - int(flame_r * 0.4), cx + flame_r, cyl_top + flame_r + 10], outline=(245, 158, 11), width=3)
        draw.ellipse([cx - flame_r // 2, cyl_top, cx + flame_r // 2, cyl_top + flame_r], fill=(254, 240, 138))

    # 8. Pistón de aleación ligera y 3 anillos de sellado (Aros de fuego)
    draw.rounded_rectangle(
        [cx - cyl_w // 2 + 5, piston_top_y, cx + cyl_w // 2 - 5, piston_bot_y],
        radius=8,
        fill=(148, 163, 184),
        outline=(248, 250, 252),
        width=3,
    )
    # 3 aros de compresión dorados
    for r_i in range(3):
        ry = piston_top_y + int((10 + r_i * 9) * render_scale)
        draw.line([(cx - cyl_w // 2 + 5, ry), (cx + cyl_w // 2 - 5, ry)], fill=(250, 204, 21), width=3)

    # Falda del pistón y bulón central (Wrist Pin)
    pin_x = cx
    pin_y = (piston_top_y + piston_bot_y) // 2
    draw.ellipse([pin_x - int(12 * render_scale), pin_y - int(12 * render_scale), pin_x + int(12 * render_scale), pin_y + int(12 * render_scale)], fill=(30, 41, 59), outline=(255, 255, 255), width=2)

    # 9. Cinemática del Cigüeñal y Biela
    journal_x = cx + int(crank_r * math.sin(crank_angle))
    journal_y = crank_y - int(crank_r * math.cos(crank_angle))

    # Caja del cárter (Crankcase)
    draw.ellipse(
        [cx - crank_r - int(24 * render_scale), crank_y - crank_r - int(24 * render_scale), cx + crank_r + int(24 * render_scale), crank_y + crank_r + int(24 * render_scale)],
        fill=(15, 23, 42),
        outline=accent_rgb,
        width=3,
    )
    # Contrapeso del cigüeñal (rotación 180° opuesta al muñón de biela para balance estático)
    counter_ang = crank_angle + math.pi
    c_x0 = cx + int((crank_r + 14 * render_scale) * math.cos(counter_ang - 0.45))
    c_y0 = crank_y + int((crank_r + 14 * render_scale) * math.sin(counter_ang - 0.45))
    c_x1 = cx + int((crank_r + 14 * render_scale) * math.cos(counter_ang + 0.45))
    c_y1 = crank_y + int((crank_r + 14 * render_scale) * math.sin(counter_ang + 0.45))
    draw.chord([cx - crank_r - int(12 * render_scale), crank_y - crank_r - int(12 * render_scale), cx + crank_r + int(12 * render_scale), crank_y + crank_r + int(12 * render_scale)], start=math.degrees(counter_ang - 0.5), end=math.degrees(counter_ang + 0.5), fill=(51, 65, 85), outline=warn_rgb, width=2)

    # Biela de acero forjado (Connecting Rod) con perfil en I
    draw.line([(pin_x, pin_y), (journal_x, journal_y)], fill=(226, 232, 240), width=max(6, int(16 * render_scale)))
    draw.line([(pin_x, pin_y), (journal_x, journal_y)], fill=(71, 85, 105), width=max(3, int(8 * render_scale)))

    # Cojinetes articulados superior e inferior
    draw.ellipse([pin_x - int(8 * render_scale), pin_y - int(8 * render_scale), pin_x + int(8 * render_scale), pin_y + int(8 * render_scale)], fill=warn_rgb)
    draw.ellipse([journal_x - int(11 * render_scale), journal_y - int(11 * render_scale), journal_x + int(11 * render_scale), journal_y + int(11 * render_scale)], fill=accent_rgb, outline=(255, 255, 255), width=2)
    # Eje del cigüeñal
    draw.ellipse([cx - int(10 * render_scale), crank_y - int(10 * render_scale), cx + int(10 * render_scale), crank_y + int(10 * render_scale)], fill=(248, 250, 252))

    # Indicador de sentido de giro horario continuo
    draw.arc([cx - crank_r - 6, crank_y - crank_r - 6, cx + crank_r + 6, crank_y + crank_r + 6], start=45, end=225, fill=ok_rgb, width=3)

    # 10. Si la composición es INFOGRAPHIC VIEW: dibujar tarjetas de telemetría técnica
    if composition_type == "infographic_view" and font_hud is not None:
        card_w = int(220 * (scale / 2.0))
        card_h = int(72 * (scale / 2.0))
        # Tarjeta 1: Relación de compresión
        draw.rounded_rectangle([cx - cyl_w // 2 - card_w - 15, cyl_top + 20, cx - cyl_w // 2 - 15, cyl_top + 20 + card_h], radius=10, fill=(15, 23, 42), outline=accent_rgb, width=2)
        draw.text((cx - cyl_w // 2 - card_w - 5, cyl_top + 28), "COMPRESIÓN", font=font_hud, fill=accent_rgb)
        draw.text((cx - cyl_w // 2 - card_w - 5, cyl_top + 52), "10.5 : 1", font=font_hud, fill=(255, 255, 255))
        # Tarjeta 2: Presión máxima
        draw.rounded_rectangle([cx + cyl_w // 2 + 15, cyl_top + 20, cx + cyl_w // 2 + card_w + 15, cyl_top + 20 + card_h], radius=10, fill=(15, 23, 42), outline=warn_rgb, width=2)
        draw.text((cx + cyl_w // 2 + 25, cyl_top + 28), "PRESIÓN PICO", font=font_hud, fill=warn_rgb)
        draw.text((cx + cyl_w // 2 + 25, cyl_top + 52), "65 BAR", font=font_hud, fill=(255, 255, 255))

    # Puntos de anclaje de alta precisión para las etiquetas
    return [
        (v_left_x, cyl_top),
        (cx + cyl_w // 3, cyl_top + int(36 * render_scale)),
        (cx - cyl_w // 3, pin_y),
        (journal_x, crank_y),
    ]


def _draw_generic_or_specialized_mechanism(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    scale: float,
    progress: float,
    template: str,
    phase: str,
    accent_rgb: tuple[int, int, int],
    warn_rgb: tuple[int, int, int],
    ok_rgb: tuple[int, int, int],
    font_small: Any,
) -> list[tuple[int, int]]:
    """Dibuja y anima los diagramas especializados (GPS, Cajero ATM, Pantalla Táctil,
    Transmisión Automática o Diagrama Técnico Universal) y devuelve los 4 puntos de anclaje."""
    if template == "gps_system":
        r_earth = int(68 * scale)
        r_orbit = int(165 * scale)
        # Órbitas MEO
        draw.ellipse([cx - r_orbit, cy - int(r_orbit * 0.72), cx + r_orbit, cy + int(r_orbit * 0.72)], outline=(71, 85, 105), width=2)
        draw.ellipse([cx - int(r_orbit * 0.72), cy - r_orbit, cx + int(r_orbit * 0.72), cy + r_orbit], outline=(71, 85, 105), width=2)
        # Planeta Tierra en el centro
        draw.ellipse([cx - r_earth, cy - r_earth, cx + r_earth, cy + r_earth], fill=(14, 116, 144), outline=ok_rgb, width=3)
        # 4 Satélites emitiendo pulsos de radio (d = c * dt)
        sat_pts: list[tuple[int, int]] = []
        base_angles = [0.4, 1.9, 3.6, 5.1]
        for idx, b_ang in enumerate(base_angles):
            ang = b_ang + progress * 0.45
            sx = cx + int(r_orbit * math.cos(ang))
            sy = cy + int(r_orbit * 0.72 * math.sin(ang))
            sat_pts.append((sx, sy))
            # Línea de tiempo de vuelo hacia el receptor en la Tierra
            rx, ry = cx + int(12 * scale), cy - int(18 * scale)
            draw.line([(sx, sy), (rx, ry)], fill=accent_rgb if idx < 3 else warn_rgb, width=2)
            # Pulso viajando a la velocidad de la luz
            px = int(sx + (rx - sx) * ((progress * 2.0 + idx * 0.25) % 1.0))
            py = int(sy + (ry - sy) * ((progress * 2.0 + idx * 0.25) % 1.0))
            draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(254, 240, 138))
            draw.rectangle([sx - 10, sy - 7, sx + 10, sy + 7], fill=(226, 232, 240), outline=accent_rgb, width=2)
        return sat_pts

    if template == "touchscreen":
        # Capas en perspectiva y cuadrícula ITO con dedo humano alterando el campo electrostático
        w_box = int(280 * scale)
        h_box = int(190 * scale)
        x0, y0 = cx - w_box // 2, cy - h_box // 2
        draw.rounded_rectangle([x0, y0, x0 + w_box, y0 + h_box], radius=14, fill=(15, 23, 42), outline=accent_rgb, width=3)
        # Rejilla X (Cyan) e Y (Ámbar) de Óxido de Indio y Estaño (ITO)
        for gx in range(1, 6):
            lx = x0 + int((gx / 6.0) * w_box)
            draw.line([(lx, y0 + 12), (lx, y0 + h_box - 12)], fill=accent_rgb, width=2)
        for gy in range(1, 5):
            ly = y0 + int((gy / 5.0) * h_box)
            draw.line([(x0 + 12, ly), (x0 + w_box - 12, ly)], fill=warn_rgb, width=2)
        # Punto de contacto del dedo y ondas de caída de capacitancia (~1 pF)
        tx = cx + int(35 * math.sin(progress * math.pi * 2) * scale)
        ty = cy
        for ring in range(1, 4):
            rr = int((14 * ring + (progress * 18)) * scale)
            draw.ellipse([tx - rr, ty - rr, tx + rr, ty + rr], outline=ok_rgb, width=2)
        draw.ellipse([tx - 14, ty - 14, tx + 14, ty + 14], fill=(244, 63, 94), outline=(255, 255, 255), width=2)
        return [(x0 + 30, y0 + 25), (x0 + w_box - 30, y0 + 35), (tx, ty), (x0 + w_box - 35, y0 + h_box - 25)]

    if template == "auto_transmission":
        # Tren de engranajes planetarios girando en tiempo real (Solar + 3 Satélites + Corona)
        r_ring = int(145 * scale)
        r_sun = int(48 * scale)
        r_planet = int(42 * scale)
        r_carrier = r_sun + r_planet + 4
        # Corona exterior (Ring Gear)
        draw.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], fill=(15, 23, 42), outline=accent_rgb, width=5)
        # Engranaje Solar central (Sun Gear)
        draw.ellipse([cx - r_sun, cy - r_sun, cx + r_sun, cy + r_sun], fill=(30, 41, 59), outline=warn_rgb, width=4)
        # 3 Piñones Satélites orbitando sobre el Porta-Satélites
        planet_anchors: list[tuple[int, int]] = []
        for p_idx in range(3):
            ang = (p_idx * (2.0 * math.pi / 3.0)) + (progress * math.pi * 1.5)
            px = cx + int(r_carrier * math.cos(ang))
            py = cy + int(r_carrier * math.sin(ang))
            planet_anchors.append((px, py))
            draw.line([(cx, cy), (px, py)], fill=(148, 163, 184), width=3)
            draw.ellipse([px - r_planet, py - r_planet, px + r_planet, py + r_planet], fill=(22, 38, 62), outline=ok_rgb, width=3)
        return [(cx, cy), planet_anchors[0], planet_anchors[1], (cx + r_ring - 10, cy)]

    if template == "atm_machine":
        # Corte de Cajero Automático (Lector superior + Bóveda inferior con casetes, rodillos y sensor)
        w_atm = int(230 * scale)
        h_atm = int(260 * scale)
        x0, y0 = cx - w_atm // 2, cy - h_atm // 2
        draw.rounded_rectangle([x0, y0, x0 + w_atm, y0 + h_atm], radius=14, fill=(17, 24, 39), outline=accent_rgb, width=3)
        # Línea divisoria bóveda blindada
        mid_y = y0 + int(h_atm * 0.36)
        draw.line([(x0, mid_y), (x0 + w_atm, mid_y)], fill=warn_rgb, width=3)
        # Casetes de billetes abajo
        c1_y = mid_y + int(28 * scale)
        c2_y = mid_y + int(92 * scale)
        draw.rectangle([x0 + 22, c1_y, x0 + w_atm - 22, c1_y + int(44 * scale)], fill=(30, 41, 59), outline=ok_rgb, width=2)
        draw.rectangle([x0 + 22, c2_y, x0 + w_atm - 22, c2_y + int(44 * scale)], fill=(30, 41, 59), outline=accent_rgb, width=2)
        # Billete animado subiendo por los rodillos hacia el sensor óptico
        bill_y = int(c1_y - (progress * (c1_y - (y0 + 35))))
        draw.rectangle([cx - 28, bill_y - 10, cx + 28, bill_y + 10], fill=(34, 197, 94), outline=(255, 255, 255), width=2)
        return [(x0 + 35, y0 + 32), (x0 + w_atm - 35, y0 + 55), (cx, c1_y + 20), (x0 + w_atm - 30, mid_y + 15)]

    # Diagrama Técnico Universal (4 bloques conectados con pulso de señal animado)
    r_core = int(95 * scale)
    draw.ellipse([cx - r_core - 18, cy - r_core - 18, cx + r_core + 18, cy + r_core + 18], outline=accent_rgb, width=2)
    draw.ellipse([cx - r_core, cy - r_core, cx + r_core, cy + r_core], fill=(22, 32, 52), outline=warn_rgb, width=4)
    pulse_ang = progress * 2.0 * math.pi
    px = cx + int(r_core * math.cos(pulse_ang))
    py = cy + int(r_core * math.sin(pulse_ang))
    draw.ellipse([px - 9, py - 9, px + 9, py + 9], fill=ok_rgb, outline=(255, 255, 255), width=2)
    return [
        (cx - int(r_core * 0.7), cy - int(r_core * 0.7)),
        (cx + int(r_core * 0.7), cy - int(r_core * 0.7)),
        (cx - int(r_core * 0.7), cy + int(r_core * 0.7)),
        (cx + int(r_core * 0.7), cy + int(r_core * 0.7)),
    ]


def render_animated_diagram_frame(
    scene: dict[str, Any],
    progress: float,
    width: int = 1920,
    height: int = 1080,
    visual_style_key: str = "3d_educational",
    safe_zone: Optional[dict[str, Any]] = None,
    base_illustration: Optional[Image.Image] = None,
) -> Image.Image:
    """Renderiza un fotograma animado de alta resolución del Diagrama Educativo (Fase 7 - Modo B),
    adaptando su maquetación de forma nativa a 16:9 (horizontal) o 9:16 (vertical con zonas seguras)."""
    style = VISUAL_CONSISTENCY_STYLES.get(visual_style_key) or VISUAL_CONSISTENCY_STYLES["3d_educational"]
    pal = style["palette"]
    bg_rgb = _hex_to_rgb(pal["bg_primary"], (11, 17, 32))
    sec_rgb = _hex_to_rgb(pal["bg_secondary"], (30, 41, 59))
    accent_rgb = _hex_to_rgb(pal["accent_primary"], (56, 189, 248))
    warn_rgb = _hex_to_rgb(pal["accent_secondary"], (245, 158, 11))
    ok_rgb = _hex_to_rgb(pal["highlight"], (34, 197, 94))

    is_vertical = height > width
    img = Image.new("RGB", (width, height), bg_rgb)

    # Si existe ilustración base, podemos integrarla sutilmente como fondo técnico atenuado
    if base_illustration is not None:
        bg_copy = base_illustration.resize((width, height), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=8))
        img = Image.blend(img, bg_copy, 0.22)

    draw = ImageDraw.Draw(img)

    # 1. Cuadrícula técnica de ingeniería (Blueprint Grid)
    grid_step = 54
    grid_col = (min(255, bg_rgb[0] + 12), min(255, bg_rgb[1] + 16), min(255, bg_rgb[2] + 26))
    for gx in range(0, width, grid_step):
        draw.line([(gx, 0), (gx, height)], fill=grid_col, width=1)
    for gy in range(0, height, grid_step):
        draw.line([(0, gy), (width, gy)], fill=grid_col, width=1)

    # 2. Calcular área segura según el perfil de plataforma (Fase 11)
    top_pct = float((safe_zone or {}).get("top_pct", 0.12 if is_vertical else 0.06))
    bot_pct = float((safe_zone or {}).get("bottom_pct", 0.25 if is_vertical else 0.14))
    left_pct = float((safe_zone or {}).get("left_pct", 0.06 if is_vertical else 0.05))
    right_pct = float((safe_zone or {}).get("right_pct", 0.14 if is_vertical else 0.05))

    safe_x0 = int(width * left_pct)
    safe_x1 = int(width * (1.0 - right_pct))
    safe_y0 = int(height * top_pct)
    safe_y1 = int(height * (1.0 - bot_pct))
    safe_w = safe_x1 - safe_x0
    safe_h = safe_y1 - safe_y0

    font_badge = video_pipeline._load_ui_font(max(18, int(width * (0.024 if is_vertical else 0.015))), bold=True)
    font_title = video_pipeline._load_ui_font(max(24, int(width * (0.034 if is_vertical else 0.021))), bold=True)
    font_label = video_pipeline._load_ui_font(max(20, int(width * (0.032 if is_vertical else 0.018))), bold=True)
    font_hud = video_pipeline._load_ui_font(max(15, int(width * (0.020 if is_vertical else 0.013))), bold=True)

    # 3. Encabezado del concepto dentro de la zona segura superior (con sanitización tipográfica estricta)
    header_h = int(safe_h * (0.13 if is_vertical else 0.12))
    draw.rounded_rectangle(
        [safe_x0, safe_y0, safe_x1, safe_y0 + header_h],
        radius=14,
        fill=sec_rgb,
        outline=accent_rgb,
        width=2,
    )
    raw_res_label = scene.get("resource_type_label") or "Diagrama Técnico"
    raw_concept = scene.get("concept_explained") or "Funcionamiento Interno"
    clean_res = _sanitize_display_text(raw_res_label)
    clean_concept = _sanitize_display_text(raw_concept)

    comp_type = scene.get("composition_type") or (scene.get("diagram_spec") or {}).get("composition_type") or "hero_view"
    comp_badge = f"[{comp_type.replace('_view', '').upper()}]"

    draw.text((safe_x0 + 22, safe_y0 + 10), f"{scene.get('scene_id', 'S01')} · {clean_res} · {comp_badge}", font=font_badge, fill=accent_rgb)
    short_title = clean_concept if len(clean_concept) <= 56 else (clean_concept[:53] + "…")
    draw.text((safe_x0 + 22, safe_y0 + int(header_h * 0.46)), short_title, font=font_title, fill=(255, 255, 255))

    # Barra de progreso de secuencia dentro del encabezado
    bar_w = int((safe_w - 44) * float(np.clip(progress, 0.05, 1.0)))
    draw.rectangle([safe_x0 + 22, safe_y0 + header_h - 6, safe_x0 + 22 + bar_w, safe_y0 + header_h - 2], fill=warn_rgb)

    # 4. Centro geométrico y escala adaptativa según los 6 tipos de plano cinemático
    diag_spec = scene.get("diagram_spec") or {}
    template = diag_spec.get("template", "universal_diagram")
    phase = diag_spec.get("phase", "overview")

    comp_cfg = COMPOSITION_TYPES.get(comp_type) or COMPOSITION_TYPES["hero_view"]
    scale_key = "scale_9_16" if is_vertical else "scale_16_9"
    scale = float(comp_cfg.get(scale_key, 2.15 if is_vertical else 1.45))

    diag_cx = (safe_x0 + safe_x1) // 2
    diag_cy = safe_y0 + header_h + int((safe_h - header_h) * (0.46 if is_vertical else 0.50))

    if template == "combustion_engine":
        anchors = _draw_combustion_engine_cutaway(
            draw=draw,
            cx=diag_cx,
            cy=diag_cy,
            scale=scale,
            progress=progress,
            phase=phase,
            accent_rgb=accent_rgb,
            warn_rgb=warn_rgb,
            ok_rgb=ok_rgb,
            composition_type=comp_type,
            font_hud=font_hud,
        )
    else:
        anchors = _draw_generic_or_specialized_mechanism(
            draw=draw,
            cx=diag_cx,
            cy=diag_cy,
            scale=scale,
            progress=progress,
            template=template,
            phase=phase,
            accent_rgb=accent_rgb,
            warn_rgb=warn_rgb,
            ok_rgb=ok_rgb,
            font_small=font_badge,
        )

    # 5. Sistema de Etiquetas Inteligentes Progresivas (Fase C)
    labels = scene.get("labels") or ["1. Entrada", "2. Mecanismo", "3. Proceso", "4. Salida"]
    active_idx = min(len(labels) - 1, int(progress * len(labels)))

    if is_vertical:
        # En 9:16 vertical destacamos la etiqueta activa sin saturar el mecanismo
        target_pt = anchors[active_idx % len(anchors)] if anchors else (diag_cx, diag_cy)
        is_upper = target_pt[1] < diag_cy
        badge_y = (safe_y0 + header_h + int((safe_h - header_h) * 0.08)) if is_upper else (safe_y0 + header_h + int((safe_h - header_h) * 0.90))
        box_w = min(safe_w - 20, 500)
        box_h = 60

        _draw_callout_badge(
            draw=draw,
            box_center=(diag_cx, badge_y),
            target_pt=target_pt,
            label_text=labels[active_idx],
            is_active=True,
            accent_rgb=accent_rgb,
            active_rgb=warn_rgb,
            bg_rgb=sec_rgb,
            font=font_label,
            box_w=box_w,
            box_h=box_h,
            opacity_mult=1.0,
        )
    else:
        # En 16:9 colocamos las etiquetas en las columnas laterales
        left_col_x = safe_x0 + int(safe_w * 0.17)
        right_col_x = safe_x0 + int(safe_w * 0.83)
        upper_y = diag_cy - int((safe_h - header_h) * 0.22)
        lower_y = diag_cy + int((safe_h - header_h) * 0.22)
        badge_centers = [
            (left_col_x, upper_y),
            (right_col_x, upper_y),
            (left_col_x, lower_y),
            (right_col_x, lower_y),
        ]
        box_w = int(safe_w * 0.30)
        box_h = 56
        for idx in range(min(4, len(labels))):
            target_pt = anchors[idx % len(anchors)] if anchors else (diag_cx, diag_cy)
            is_cur = (idx == active_idx)
            _draw_callout_badge(
                draw=draw,
                box_center=badge_centers[idx],
                target_pt=target_pt,
                label_text=labels[idx],
                is_active=is_cur,
                accent_rgb=accent_rgb,
                active_rgb=warn_rgb,
                bg_rgb=sec_rgb,
                font=font_label,
                box_w=box_w,
                box_h=box_h,
                opacity_mult=1.0 if is_cur else 0.40,
            )

    return img


def render_mode_a_enhanced_frame(
    base_img: Image.Image,
    progress: float,
    camera_motion: str,
    width: int,
    height: int,
    scene: Optional[dict[str, Any]] = None,
    safe_zone: Optional[dict[str, Any]] = None,
    vignette_overlay: Optional[Image.Image] = None,
) -> Image.Image:
    """Modo A (Fase 7): Aplica movimientos avanzados sobre la imagen generada
    (zoom_in, zoom_out, pan_horizontal, pan_vertical, parallax, selective_focus, cutaway_focus)
    y reencuadre inteligente para formato vertical 9:16 o 16:9."""
    p = float(np.clip(progress, 0.0, 1.0))
    smooth_p = 0.35 * p + 0.65 * (p * p * (3.0 - 2.0 * p))

    # Si la imagen origen tiene otra relación de aspecto (ej. 16:9 reencuadrada a 9:16),
    # no hacemos un recorte ciego: componemos un fondo atmosférico + encuadre adaptativo centrado en el sujeto
    src_w, src_h = base_img.size
    target_ratio = width / float(height)
    src_ratio = src_w / float(src_h)

    if abs(target_ratio - src_ratio) > 0.25:
        # Reencuadre Inteligente (Smart Reframe Fase 11)
        bg_canvas = base_img.resize((width, height), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=22))
        dark_layer = Image.new("RGB", (width, height), (8, 12, 24))
        bg_canvas = Image.blend(bg_canvas, dark_layer, 0.45)

        # Escalar la ilustración principal para que sus elementos quepan completos en la zona segura central
        fg_w = int(width * 0.92)
        fg_h = int(fg_w / src_ratio)
        fg_img = base_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
        paste_x = (width - fg_w) // 2
        paste_y = int(height * 0.20)
        bg_canvas.paste(fg_img, (paste_x, paste_y))
        working_img = bg_canvas
    else:
        working_img = base_img if base_img.size == (width, height) else base_img.resize((width, height), Image.Resampling.LANCZOS)

    if camera_motion == "zoom_in":
        zoom = 1.0 + 0.14 * smooth_p
        cx, cy = 0.5, 0.47
    elif camera_motion == "zoom_out":
        zoom = 1.14 - 0.14 * smooth_p
        cx, cy = 0.5, 0.47
    elif camera_motion in ("pan_horizontal", "pan_right"):
        zoom = 1.12
        cx, cy = 0.43 + 0.14 * smooth_p, 0.48
    elif camera_motion == "pan_vertical":
        zoom = 1.12
        cx, cy = 0.50, 0.42 + 0.14 * smooth_p
    elif camera_motion == "parallax":
        zoom = 1.08 + 0.05 * math.sin(smooth_p * math.pi)
        cx, cy = 0.46 + 0.08 * smooth_p, 0.48
    elif camera_motion in ("selective_focus", "cutaway_focus"):
        zoom = 1.04 + 0.12 * smooth_p
        cx, cy = 0.50, 0.46
    else:
        zoom = 1.0 + 0.10 * smooth_p
        cx, cy = 0.5, 0.48

    crop_w = width / zoom
    crop_h = height / zoom
    left = max(0.0, min(width - crop_w, (width * cx) - (crop_w / 2.0)))
    top = max(0.0, min(height - crop_h, (height * cy) - (crop_h / 2.0)))

    framed = working_img.resize(
        (width, height),
        resample=Image.Resampling.BILINEAR,
        box=(left, top, left + crop_w, top + crop_h),
    )

    # Enfoque selectivo progresivo (de desenfoque suave periférico a nitidez total)
    if camera_motion == "selective_focus" and smooth_p < 0.35:
        blur_r = (0.35 - smooth_p) * 5.0
        if blur_r > 0.4:
            blurred = framed.filter(ImageFilter.GaussianBlur(radius=blur_r))
            framed = Image.blend(framed, blurred, 0.45)

    if vignette_overlay is not None:
        framed = Image.alpha_composite(framed.convert("RGBA"), vignette_overlay).convert("RGB")

    return framed
