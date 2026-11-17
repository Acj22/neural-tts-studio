"""FASE 7 — HYBRID VISUAL ENGINE (Modo A: Movimiento Avanzado + Modo B: Diagramas Técnicos SVG y Animación de Componentes).

Genera:
1. Archivos SVG vectoriales limpios (.svg) con flechas, etiquetas, números y esquemas técnicos.
2. Fotogramas animados de alta resolución (1920x1080 en 16:9 y reencuadre inteligente nativo 1080x1920 en 9:16)
   donde las piezas (pistón, válvulas, cigüeñal, engranajes planetarios, ondas GPS, rodillos ATM, campo ITO)
   se mueven en sincronía con el progreso de la escena, con etiquetas anti-colisión que jamás tapan las piezas.
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import video_pipeline
from studio.models import VISUAL_CONSISTENCY_STYLES


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
    box_w: int = 330,
    box_h: int = 50,
) -> None:
    """Dibuja una etiqueta técnica con línea guía y punto de anclaje sin tapar el componente central."""
    bx, by = box_center
    tx, ty = target_pt
    line_col = active_rgb if is_active else accent_rgb
    border_w = 3 if is_active else 2

    # Línea guía desde el borde de la caja hasta el punto del componente
    draw.line([(bx, by), (tx, ty)], fill=line_col, width=border_w)
    draw.ellipse([tx - 7, ty - 7, tx + 7, ty + 7], fill=active_rgb if is_active else accent_rgb, outline=(255, 255, 255), width=2)

    x0, y0 = bx - box_w // 2, by - box_h // 2
    x1, y1 = bx + box_w // 2, by + box_h // 2
    fill_col = (min(255, bg_rgb[0] + 18), min(255, bg_rgb[1] + 24), min(255, bg_rgb[2] + 38)) if is_active else bg_rgb
    draw.rounded_rectangle([x0, y0, x1, y1], radius=11, fill=fill_col, outline=line_col, width=border_w)

    short_lbl = label_text if len(label_text) <= 32 else (label_text[:30] + "…")
    bbox = draw.textbbox((0, 0), short_lbl, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((bx - tw // 2, by - th // 2 - 2), short_lbl, font=font, fill=(255, 255, 255) if not is_active else (254, 249, 195))


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
) -> list[tuple[int, int]]:
    """Dibuja y anima el motor de combustión interna en corte (pistón, biela, cigüeñal,
    válvulas de admisión/escape, bujía con chispa y frente de llama) según el paso explicado."""
    # Determinar ángulo del cigüeñal según la fase explicada
    if phase == "intake":
        crank_angle = progress * math.pi  # 0 -> 180° (baja)
    elif phase == "compression":
        crank_angle = math.pi + progress * math.pi  # 180° -> 360° (sube)
    elif phase == "combustion":
        crank_angle = 2.0 * math.pi + (progress * 0.22 * math.pi)  # PMS + chispa
    elif phase == "expansion":
        crank_angle = 2.0 * math.pi + progress * math.pi  # 360° -> 540° (baja con fuerza)
    elif phase == "crankshaft_exhaust":
        crank_angle = 3.0 * math.pi + progress * math.pi  # 540° -> 720° (sube y gira)
    else:
        crank_angle = progress * 4.0 * math.pi  # Ciclo completo fluido

    cyl_w = int(170 * scale)
    cyl_h = int(230 * scale)
    cyl_top = cy - int(155 * scale)
    cyl_bot = cyl_top + cyl_h
    crank_y = cyl_bot + int(82 * scale)
    crank_r = int(46 * scale)

    # 1. Bloque de cilindros y aletas de refrigeración
    draw.rounded_rectangle(
        [cx - cyl_w // 2 - int(26 * scale), cyl_top - int(36 * scale), cx + cyl_w // 2 + int(26 * scale), crank_y + crank_r + int(36 * scale)],
        radius=16,
        fill=(22, 32, 50),
        outline=accent_rgb,
        width=3,
    )
    # Interior de la camisa del cilindro
    draw.rectangle(
        [cx - cyl_w // 2, cyl_top, cx + cyl_w // 2, cyl_bot],
        fill=(12, 18, 30),
        outline=(148, 163, 184),
        width=3,
    )

    # Posición cinemática real del pistón (0 = PMS arriba, 1 = PMI abajo)
    norm_stroke = 0.5 * (1.0 - math.cos(crank_angle))
    piston_top_y = cyl_top + int(34 * scale) + int(norm_stroke * (cyl_h - int(105 * scale)))
    piston_h = int(58 * scale)
    piston_bot_y = piston_top_y + piston_h

    # Color del gas en la cámara de combustión según el tiempo del ciclo
    cycle_deg = (math.degrees(crank_angle) % 720.0)
    if phase == "intake" or (0 <= cycle_deg < 180 and phase not in ("combustion", "expansion")):
        gas_col = (38, 130, 225)  # Mezcla fresca azul
    elif phase == "compression" or (180 <= cycle_deg < 350 and phase not in ("combustion", "expansion")):
        gas_col = (80, 165, 245)  # Mezcla comprimida densa
    elif phase in ("combustion", "expansion") or (350 <= cycle_deg < 540):
        gas_col = (245, 115, 28)  # Deflagración naranja/ámbar
    else:
        gas_col = (100, 116, 139)  # Gases de escape grises

    if piston_top_y > cyl_top + 4:
        draw.rectangle([cx - cyl_w // 2 + 3, cyl_top + 3, cx + cyl_w // 2 - 3, piston_top_y], fill=gas_col)

    # Partículas de aire/combustible o frente de llama
    for p_i in range(7):
        px = cx - cyl_w // 3 + int((p_i / 6.0) * (2 * cyl_w // 3))
        py = cyl_top + 14 + int(((p_i * 19 + int(progress * 60)) % max(12, piston_top_y - cyl_top - 16)))
        p_col = (254, 240, 138) if gas_col[0] > 200 else (186, 230, 253)
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=p_col)

    # 2. Válvulas de Admisión (izquierda) y Escape (derecha)
    intake_open = int(12 * scale) if (phase == "intake" or 10 <= cycle_deg <= 170) else 0
    exhaust_open = int(12 * scale) if (phase == "crankshaft_exhaust" or 545 <= cycle_deg <= 710) else 0

    v_left_x = cx - int(42 * scale)
    v_right_x = cx + int(42 * scale)
    # Válvula izquierda (Admisión)
    draw.line([(v_left_x, cyl_top - int(32 * scale)), (v_left_x, cyl_top + intake_open)], fill=ok_rgb if intake_open else (203, 213, 225), width=4)
    draw.line([(v_left_x - int(16 * scale), cyl_top + intake_open), (v_left_x + int(16 * scale), cyl_top + intake_open)], fill=ok_rgb if intake_open else (203, 213, 225), width=5)
    # Válvula derecha (Escape)
    draw.line([(v_right_x, cyl_top - int(32 * scale)), (v_right_x, cyl_top + exhaust_open)], fill=warn_rgb if exhaust_open else (203, 213, 225), width=4)
    draw.line([(v_right_x - int(16 * scale), cyl_top + exhaust_open), (v_right_x + int(16 * scale), cyl_top + exhaust_open)], fill=warn_rgb if exhaust_open else (203, 213, 225), width=5)

    # 3. Bujía central y arco de chispa
    draw.rectangle([cx - int(8 * scale), cyl_top - int(38 * scale), cx + int(8 * scale), cyl_top + int(4 * scale)], fill=(248, 250, 252), outline=accent_rgb, width=2)
    if phase in ("combustion", "expansion") or (345 <= cycle_deg <= 395):
        spark_r = int((14 + 8 * math.sin(progress * math.pi * 4)) * scale)
        draw.ellipse([cx - spark_r, cyl_top - spark_r // 2, cx + spark_r, cyl_top + spark_r + 6], fill=(254, 240, 138), outline=(245, 158, 11), width=3)

    # 4. Pistón y 3 anillos metálicos
    draw.rounded_rectangle(
        [cx - cyl_w // 2 + 5, piston_top_y, cx + cyl_w // 2 - 5, piston_bot_y],
        radius=6,
        fill=(148, 163, 184),
        outline=(241, 245, 249),
        width=2,
    )
    for r_i in range(3):
        ry = piston_top_y + int((8 + r_i * 7) * scale)
        draw.line([(cx - cyl_w // 2 + 5, ry), (cx + cyl_w // 2 - 5, ry)], fill=(250, 204, 21), width=2)

    # 5. Cigüeñal y Biela articulada
    pin_x, pin_y = cx, (piston_top_y + piston_bot_y) // 2
    journal_x = cx + int(crank_r * math.sin(crank_angle))
    journal_y = crank_y - int(crank_r * math.cos(crank_angle))

    # Círculo del cigüeñal
    draw.ellipse(
        [cx - crank_r - int(14 * scale), crank_y - crank_r - int(14 * scale), cx + crank_r + int(14 * scale), crank_y + crank_r + int(14 * scale)],
        fill=(15, 23, 42),
        outline=accent_rgb,
        width=3,
    )
    draw.ellipse([cx - crank_r, crank_y - crank_r, cx + crank_r, crank_y + crank_r], outline=(100, 116, 139), width=2)
    # Biela (Connecting rod)
    draw.line([(pin_x, pin_y), (journal_x, journal_y)], fill=(226, 232, 240), width=max(5, int(11 * scale)))
    draw.ellipse([pin_x - 7, pin_y - 7, pin_x + 7, pin_y + 7], fill=warn_rgb)
    draw.ellipse([journal_x - 8, journal_y - 8, journal_x + 8, journal_y + 8], fill=accent_rgb)
    draw.ellipse([cx - 8, crank_y - 8, cx + 8, crank_y + 8], fill=(248, 250, 252))

    # Devolver los 4 puntos de anclaje exactos para las etiquetas (1: Culata/Válvulas, 2: Cámara/Cilindro, 3: Pistón, 4: Cigüeñal)
    return [
        (v_left_x, cyl_top),
        (cx + cyl_w // 3, cyl_top + int(28 * scale)),
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

    font_badge = video_pipeline._load_ui_font(max(16, int(width * (0.020 if is_vertical else 0.013))), bold=True)
    font_title = video_pipeline._load_ui_font(max(20, int(width * (0.026 if is_vertical else 0.017))), bold=True)
    font_label = video_pipeline._load_ui_font(max(16, int(width * (0.021 if is_vertical else 0.0125))), bold=True)

    # 3. Encabezado del concepto dentro de la zona segura superior
    header_h = int(safe_h * (0.13 if is_vertical else 0.12))
    draw.rounded_rectangle(
        [safe_x0, safe_y0, safe_x1, safe_y0 + header_h],
        radius=14,
        fill=sec_rgb,
        outline=accent_rgb,
        width=2,
    )
    res_label = scene.get("resource_type_label") or "📐 Diagrama Técnico"
    concept_title = scene.get("concept_explained") or "Funcionamiento Interno"
    draw.text((safe_x0 + 22, safe_y0 + 10), f"{scene.get('scene_id', 'S01')} · {res_label}", font=font_badge, fill=accent_rgb)
    short_title = concept_title if len(concept_title) <= 58 else (concept_title[:55] + "…")
    draw.text((safe_x0 + 22, safe_y0 + int(header_h * 0.46)), short_title, font=font_title, fill=(255, 255, 255))

    # Barra de progreso de secuencia dentro del encabezado
    bar_w = int((safe_w - 44) * float(np.clip(progress, 0.05, 1.0)))
    draw.rectangle([safe_x0 + 22, safe_y0 + header_h - 6, safe_x0 + 22 + bar_w, safe_y0 + header_h - 2], fill=warn_rgb)

    # 4. Centro geométrico del diagrama y llamada al motor cinemático
    diag_spec = scene.get("diagram_spec") or {}
    template = diag_spec.get("template", "universal_diagram")
    phase = diag_spec.get("phase", "overview")

    diag_cx = (safe_x0 + safe_x1) // 2
    diag_cy = safe_y0 + header_h + int((safe_h - header_h) * (0.45 if is_vertical else 0.50))
    scale = (0.82 if is_vertical else 1.05)

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

    # 5. Posicionar etiquetas con anti-colisión (respetando formato 16:9 vs 9:16 para que NUNCA tapen el dibujo)
    labels = scene.get("labels") or ["1. Entrada", "2. Mecanismo", "3. Proceso", "4. Salida"]
    active_idx = min(len(labels) - 1, int(progress * len(labels)))

    if is_vertical:
        # En 9:16 colocamos 2 etiquetas arriba del mecanismo y 2 etiquetas debajo del mecanismo
        top_row_y = safe_y0 + header_h + int((safe_h - header_h) * 0.11)
        bot_row_y = safe_y0 + header_h + int((safe_h - header_h) * 0.85)
        col_left_x = safe_x0 + int(safe_w * 0.25)
        col_right_x = safe_x0 + int(safe_w * 0.75)
        badge_centers = [
            (col_left_x, top_row_y),
            (col_right_x, top_row_y),
            (col_left_x, bot_row_y),
            (col_right_x, bot_row_y),
        ]
        box_w = int(safe_w * 0.46)
        box_h = 46
    else:
        # En 16:9 colocamos las etiquetas en las columnas laterales izquierda y derecha, dejando el centro libre
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
        box_h = 52

    for idx, lbl in enumerate(labels[:4]):
        target_pt = anchors[idx % len(anchors)] if anchors else (diag_cx, diag_cy)
        _draw_callout_badge(
            draw=draw,
            box_center=badge_centers[idx],
            target_pt=target_pt,
            label_text=lbl,
            is_active=(idx == active_idx),
            accent_rgb=accent_rgb,
            active_rgb=warn_rgb,
            bg_rgb=sec_rgb,
            font=font_label,
            box_w=box_w,
            box_h=box_h,
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
