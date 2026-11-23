"""Catálogo enriquecido de Arquetipos de Escenas Paper-Cut 2.5D para LEMO-Opuscar.

Garantiza pertinencia temática absoluta (paleontología, arqueología, clima, vulcanología,
misterios geológicos, ingeniería y conflictos históricos), variedad visual continua a 60 FPS
y eliminación total de elementos visuales ajenos al tema del video.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

_FONT_CACHE: dict[tuple[int, bool], Any] = {}


def _load_font(size: int, bold: bool = True):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = (
        ("arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "arial.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf")
    )
    for name in candidates:
        try:
            f = ImageFont.truetype(name, size)
            _FONT_CACHE[key] = f
            return f
        except Exception:
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _draw_sticker_card(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    fill: tuple[int, int, int],
    outline: Optional[tuple[int, int, int]] = None,
    radius: int = 22,
    border_w: int = 6,
    shadow_offset: int = 10,
):
    """Dibuja una pieza de papel recortado 2.5D con sombra proyectada y borde blanco tipo sticker."""
    draw.rounded_rectangle(
        [(x1 + shadow_offset, y1 + shadow_offset), (x2 + shadow_offset, y2 + shadow_offset)],
        radius=radius,
        fill=(195, 180, 155),
    )
    draw.rounded_rectangle(
        [(x1 - border_w, y1 - border_w), (x2 + border_w, y2 + border_w)],
        radius=radius + 4,
        fill=(255, 255, 255),
    )
    draw.rounded_rectangle(
        [(x1, y1), (x2, y2)],
        radius=radius,
        fill=fill,
        outline=outline,
        width=3 if outline else 0,
    )


def _safe_rect(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, **kwargs):
    """Garantiza que un rectángulo en Pillow tenga x1 >= x0 e y1 >= y0."""
    x_min, x_max = int(min(x0, x1)), int(max(x0, x1))
    y_min, y_max = int(min(y0, y1)), int(max(y0, y1))
    if x_max > x_min and y_max > y_min:
        draw.rectangle([(x_min, y_min), (x_max, y_max)], **kwargs)


# =============================================================================
# DETECCIÓN DE MACRO-TEMA
# =============================================================================

# =============================================================================
# DETECCIÓN DE MACRO-TEMA Y EXTRACCIÓN DINÁMICA DE ENTIDADES
# =============================================================================

def extract_location_from_text(text: str) -> str:
    """Extrae dinámicamente la ciudad, región o país mencionado en el guion."""
    known = [
        "Tultepec", "Ciudad de México", "CDMX", "Durango", "Bolsón de Mapimí", "Mapimí", "Yucatán", "Campeche",
        "Chiapas", "Oaxaca", "Puebla", "Veracruz", "Zacatecas", "Sonora", "Coahuila", "Chihuahua", "Jalisco",
        "Guadalajara", "Monterrey", "Michoacán", "Guanajuato", "Querétaro", "San Luis Potosí", "Baja California",
        "Teotihuacán", "Palenque", "Chichén Itzá", "Calakmul", "Chapultepec", "Popocatépetl", "Iztaccíhuatl",
        "Paricutín", "Golfo de México", "Océano Pacífico", "Océano Atlántico", "Caribe", "Amazonas", "Egipto",
        "Roma", "Grecia", "París", "Londres", "Tokio", "Cabo Cañaveral", "Marte", "Luna", "Antártida"
    ]
    for loc in known:
        if re.search(rf"\b{re.escape(loc)}\b", text or "", re.IGNORECASE):
            return loc
    m = re.search(r"\b(?:en|de|hacia|cerca de|costas de|isla de|valle de|cuenca de)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\b", text or "")
    if m:
        cand = m.group(1).strip()
        if cand.lower() not in ("este", "esta", "estos", "aquel", "algún", "cada", "muchos", "todos", "primer", "segundo"):
            return cand
    return "MÉXICO"


def extract_years_from_text(text: str) -> list[str]:
    """Extrae cronología real del texto para la línea temporal."""
    found = re.findall(r"\b(1[4-9]\d{2}|20[0-3]\d)\b", text or "")
    prehist = re.findall(r"\b(\d+[\d,.]*\s*(?:AP|a\.C\.|d\.C\.|aC|dC|mil años))\b", text or "", re.IGNORECASE)
    res = []
    for p in prehist:
        res.append(p.upper().strip())
    for y in found:
        if y not in res:
            res.append(y)
    return res


def extract_metrics_from_text(text: str) -> list[tuple[str, str]]:
    """Extrae cifras y unidades reales mencionadas en la narración."""
    matches = re.findall(
        r"\b(\d+(?:[.,]\d+)?)\s*(metros|km|kilometros|grados|°C|horas|días|anos|años|piezas|huesos|ejemplares|especies|toneladas|habitantes|millones|por ciento|%)\b",
        text or "",
        re.IGNORECASE,
    )
    res = []
    for num, unit in matches:
        u_clean = unit.upper()
        if u_clean in ("METROS", "M"):
            lbl = "LONGITUD / ALTURA"
        elif u_clean in ("KM", "KILOMETROS"):
            lbl = "DISTANCIA / RADIO"
        elif u_clean in ("GRADOS", "°C"):
            lbl = "TEMPERATURA"
        elif u_clean in ("HUESOS", "PIEZAS", "EJEMPLARES", "ESPECIES"):
            lbl = "HALLAZGO FÓSIL"
        elif u_clean in ("HORAS", "DÍAS", "AÑOS"):
            lbl = "DURACIÓN TEMPORAL"
        elif u_clean in ("POR CIENTO", "%"):
            lbl = "INTEGRIDAD / PROPORCIÓN"
        else:
            lbl = "REGISTRO CLAVE"
        res.append((f"{num} {u_clean[:4]}", lbl))
    return res


def detect_macro_theme(text: str) -> str:
    """Clasifica el guion o título en una taxonomía de 12 categorías temáticas universales."""
    low = (text or "").lower()

    # 1. Paleontología & Fósiles
    if any(k in low for k in ("mamut", "fósil", "fosil", "hueso", "tultepec", "dinosaur", "pleistocen", "megafauna", "colmill", "esqueleto fósil", "caza prehistórica", "prehistori", "paleontol")):
        return "paleontologia"
    # 2. Arqueología & Civilizaciones Antiguas
    if any(k in low for k in ("maya", "pirámide", "piramide", "azteca", "teotihuac", "templo", "ruinas", "tumba", "códice", "jade", "chichén", "sakil", "sacbé", "arqueolog", "petroglifo", "palenque", "calakmul", "mesoameric", "inca", "egipto", "faraón")):
        return "arqueologia"
    # 3. Astronomía, Espacio & Meteoritos
    if any(k in low for k in ("espacio", "universo", "cosmos", "planeta", "galaxia", "satélite", "satelite", "meteorito", "cráter", "crater", "athena", "nasa", "astronom", "telescopio", "órbita", "orbita", "marte", "luna", "jupiter", "apolo", "cohete", "james webb", "zona del silencio", "anomalía magnétic")):
        return "astronomia_espacio"
    # 4. Océanos, Mares & Naufragios
    if any(k in low for k in ("océano", "oceano", "mar", "marítim", "maritim", "isla", "barco", "buque", "naufragio", "titanic", "submarino", "fosa", "abisal", "arrecife", "ballena", "tiburón", "pesca", "puerto", "laguna", "bermuda", "flannan", "nemo")):
        return "oceanos_maritimo"
    # 5. Biología, Genética & Medicina
    if any(k in low for k in ("célula", "celula", "adn", "genétic", "genetic", "virus", "bacteria", "microscop", "enfermedad", "vacuna", "medicina", "cerebro", "neurona", "órgano", "organo", "anatomía", "anatomia", "sangre", "proteína", "inmunit")):
        return "biologia_medicina"
    # 6. Clima Extremo & Fenómenos Atmosféricos
    if any(k in low for k in ("nieve", "nevada", "frío", "frio", "polar", "invierno", "ventisca", "helada", "bajo cero", "huracán", "huracan", "tornado", "ciclón", "tormenta", "sequía", "inundación")):
        return "clima_desastres"
    # 7. Vulcanología & Geología
    if any(k in low for k in ("volcán", "volcan", "erupción", "erupcion", "lava", "magma", "sismo", "terremoto", "popocatépetl", "ceniza", "geolog", "tectónic", "tectonic", "falla", "mineral", "cueva", "caverna")):
        return "volcan_geologia"
    # 8. Historia, Arquitectura & Monumentos
    if any(k in low for k in ("castillo", "palacio", "alcázar", "alcazar", "chapultepec", "virreinato", "imperio", "monarquía", "monarquia", "revolución", "revolucion", "independencia", "reforma", "monumento", "siglo", "histórico", "historico", "ciudad", "coliseo", "catedral", "virreinal")):
        return "historia_monumentos"
    # 9. Militar & Aviación Bélica (ESTRICTO: solo aviación moderna o fuerzas armadas contemporáneas)
    if any(k in low for k in ("escuadrón 201", "escuadron 201", "faem", "p-47", "cazabombardero", "fuerza aérea", "fuerza aerea", "segunda guerra mundial", "primera guerra mundial", "combate aéreo", "macarthur", "bombardero")):
        return "militar_conflicto"
    # 10. Tecnología, Computación & IA
    if any(k in low for k in ("computador", "microchip", "procesador", "internet", "inteligencia artificial", "software", "algoritmo", "ciber", "red neuronal", "hacker", "datos", "servidor", "robot", "tecnolog")):
        return "tecnologia_computacion"
    # 11. Ciencia, Física & Ingeniería
    if any(k in low for k in ("turbocompresor", "motor", "compresor", "refrigerador", "pistón", "válvula", "termodinám", "cilindro", "ingeniería", "ingenieria", "física", "fisica", "átomo", "atomo", "electricidad", "mecánic", "mecanic")):
        return "ciencia_ingenieria"
    # 12. Naturaleza, Selvas & Fauna
    if any(k in low for k in ("selva", "bosque", "fauna", "animal", "depredador", "ecosistema", "flora", "amazonas", "especie", "biodiversidad", "reserva natural", "mamífero", "mamifero")):
        return "naturaleza_fauna"

    return "documental_general"


# =============================================================================
# ARQUETIPOS TEMÁTICOS ORIGINALES Y PREHISTORIA
# =============================================================================

def _draw_scene_mamut_prehistorico(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Mamut lanudo/columbi en diorama paper-cut 2.5D con colmillos curvados, pelaje y paisaje pleistocénico."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(245, 238, 220), outline=(160, 120, 85), radius=28, border_w=7, shadow_offset=12)

    if pop < 0.20:
        return

    # 1. Cielo crepuscular pleistocénico
    _safe_rect(draw, cx - card_w + 8, cy - card_h + 8, cx + card_w - 8, cy + 40, fill=(254, 243, 199))
    # Sol ámbar pálido
    draw.ellipse([(cx + 120, cy - card_h + 30), (cx + 260, cy - card_h + 170)], fill=(253, 230, 138))

    # 2. Cordillera lejana con nieve
    pts_mount = [(cx - card_w, cy + 60), (cx - 240, cy - 40), (cx - 100, cy + 30), (cx + 80, cy - 70), (cx + 260, cy + 40), (cx + card_w, cy + 60)]
    draw.polygon(pts_mount, fill=(180, 140, 110))
    # Cumbres nevadas
    draw.polygon([(cx - 240, cy - 40), (cx - 210, cy - 10), (cx - 270, cy - 10)], fill=(255, 255, 255))
    draw.polygon([(cx + 80, cy - 70), (cx + 120, cy - 35), (cx + 40, cy - 35)], fill=(255, 255, 255))

    # 3. Suelo lacustre del lago de Xaltocan / ribera
    _safe_rect(draw, cx - card_w + 8, cy + 40, cx + card_w - 8, cy + card_h - 8, fill=(120, 85, 55))
    # Estratos de arcilla
    _safe_rect(draw, cx - card_w + 8, cy + 130, cx + card_w - 8, cy + card_h - 8, fill=(92, 64, 42))

    # 4. Mamut en relieve multicapa (balanceo y respiración suave)
    sway = math.sin(t * 1.8) * 6
    bx, by = cx - 20, cy + 25 + int(sway)

    # Patas traseras (en sombra)
    _safe_rect(draw, bx + 40, by + 40, bx + 85, by + 160, fill=(70, 42, 22))
    _safe_rect(draw, bx - 100, by + 40, bx - 55, by + 160, fill=(70, 42, 22))

    # Cuerpo macizo con joroba
    draw.ellipse([(bx - 170, by - 100), (bx + 140, by + 90)], fill=(105, 58, 28))
    # Capa de pelaje superior
    draw.polygon([(bx - 160, by - 20), (bx - 120, by - 95), (bx + 20, by - 105), (bx + 120, by - 40), (bx + 100, by + 20), (bx - 140, by + 30)], fill=(85, 45, 20))

    # Patas delanteras (primer plano)
    _safe_rect(draw, bx + 75, by + 45, bx + 120, by + 165, fill=(85, 45, 20))
    _safe_rect(draw, bx - 60, by + 45, bx - 15, by + 165, fill=(85, 45, 20))

    # Cabeza con cúpula alta típica de Mammuthus
    hx, hy = bx - 130, by - 55
    draw.ellipse([(hx - 75, hy - 85), (hx + 65, hy + 65)], fill=(92, 50, 24))
    # Oreja pequeña (adaptada al frío pleistocénico)
    draw.ellipse([(hx + 25, hy - 50), (hx + 60, hy - 15)], fill=(65, 32, 14))
    # Ojo inteligente
    draw.ellipse([(hx - 15, hy - 25), (hx - 3, hy - 13)], fill=(255, 255, 255))
    draw.ellipse([(hx - 12, hy - 22), (hx - 6, hy - 16)], fill=(15, 23, 42))

    # Trompa articulada con movimiento orgánico
    t_wave = math.sin(t * 2.2) * 12
    trunk_pts = [
        (hx - 50, hy + 25),
        (hx - 75 + int(t_wave * 0.5), hy + 90),
        (hx - 55 + int(t_wave), hy + 140),
        (hx - 30 + int(t_wave), hy + 125),
        (hx - 55 + int(t_wave * 0.5), hy + 85),
        (hx - 30, hy + 30),
    ]
    draw.polygon(trunk_pts, fill=(80, 42, 18))

    # Colmillos gigantes curvados en marfil con relieve 2.5D
    tusk_back = [(hx - 30, hy + 15), (hx - 130, hy + 45), (hx - 180, hy - 15), (hx - 160, hy - 85), (hx - 145, hy - 80), (hx - 160, hy - 10), (hx - 115, hy + 35), (hx - 25, hy + 22)]
    draw.polygon(tusk_back, fill=(230, 220, 195))

    tusk_front = [(hx - 40, hy + 25), (hx - 155, hy + 55), (hx - 215, hy - 5), (hx - 195, hy - 95), (hx - 178, hy - 90), (hx - 195, hy - 5), (hx - 140, hy + 45), (hx - 35, hy + 32)]
    draw.polygon([(x + 3, y + 4) for x, y in tusk_front], fill=(160, 130, 95))
    draw.polygon(tusk_front, fill=(255, 250, 235), outline=(190, 165, 125))

    # Cintilla técnica inferior
    f_badge = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(15, 23, 42), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "MAMMUTHUS COLUMBI // PLEISTOCENO TARDÍO • 14,000 AP"
    draw.text((cx - draw.textlength(lbl, font=f_badge) / 2, cy + card_h - 38), lbl, fill=(251, 191, 36), font=f_badge)


def _draw_scene_excavacion_fosiles(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Fosa de excavación arqueológica y paleontológica del INAH con cuadrícula de campo y huesos fósiles."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(240, 230, 210), outline=(130, 95, 65), radius=28, border_w=7, shadow_offset=12)

    if pop < 0.20:
        return

    # 1. Estratos geológicos de excavación
    layers = [
        (-card_h + 10, -80, (140, 105, 70), "CAPA SUPERFICIAL // HUMUS"),
        (-80, 20, (175, 140, 100), "ARCILLA LACUSTRE // LAGO XALTOCAN"),
        (20, 130, (120, 85, 55), "ESTRATO FÓSIL PLEISTOCÉNICO"),
        (130, card_h - 10, (85, 55, 35), "CENIZA VOLCÁNICA TOBA"),
    ]
    for y1_off, y2_off, col, _ in layers:
        _safe_rect(draw, cx - card_w + 10, cy + y1_off, cx + card_w - 10, cy + y2_off, fill=col)

    # 2. Cuadrícula métrica arqueológica
    f_grid = _load_font(13, bold=True)
    for gx in (cx - 260, cx - 90, cx + 80, cx + 250):
        draw.line([(gx, cy - card_h + 10), (gx, cy + card_h - 55)], fill=(255, 255, 255), width=2)
    for gy in (cy - 80, cy + 20, cy + 130):
        draw.line([(cx - card_w + 10, gy), (cx + card_w - 10, gy)], fill=(255, 255, 255), width=2)

    draw.text((cx - 250, cy - card_h + 20), "SECTOR A-1", fill=(255, 255, 255), font=f_grid)
    draw.text((cx - 80, cy - card_h + 20), "SECTOR A-2", fill=(255, 255, 255), font=f_grid)
    draw.text((cx + 90, cy - card_h + 20), "SECTOR B-1", fill=(255, 255, 255), font=f_grid)

    # 3. Fósiles expuestos en el sedimento
    sk_x, sk_y = cx - 80, cy + 60
    draw.ellipse([(sk_x - 90, sk_y - 50), (sk_x + 90, sk_y + 45)], fill=(250, 245, 230), outline=(160, 140, 110), width=4)
    draw.ellipse([(sk_x - 30, sk_y - 20), (sk_x + 5, sk_y + 15)], fill=(120, 85, 55))
    draw.polygon([(sk_x - 85, sk_y), (sk_x - 220, sk_y - 40), (sk_x - 210, sk_y - 65), (sk_x - 75, sk_y - 20)], fill=(255, 250, 235), outline=(160, 140, 110))

    # Costillas y vértebras fósiles en sector contiguo
    for r_i in range(5):
        rx = cx + 60 + r_i * 32
        ry = cy + 50 + int(math.sin(r_i) * 10)
        draw.arc([(rx - 15, ry - 35), (rx + 25, ry + 40)], start=160, end=350, fill=(255, 250, 235), width=8)

    # Escala métrica gráfica
    rule_x, rule_y = cx + 110, cy + 150
    for sq in range(6):
        fill_sq = (255, 255, 255) if sq % 2 == 0 else (15, 23, 42)
        _safe_rect(draw, rule_x + sq * 22, rule_y, rule_x + (sq + 1) * 22, rule_y + 12, fill=fill_sq)
    draw.text((rule_x + 140, rule_y - 2), "1 METRO", fill=(255, 255, 255), font=f_grid)

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 250, cy + card_h - 48, cx + 250, cy + card_h - 10, fill=(15, 23, 42), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "YACIMIENTO TULTEPEC // REGISTRO FÓSIL • INAH 2015-2019"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(251, 191, 36), font=f_b)


def _draw_scene_trampa_caza_prehistoria(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Corte transversal de las fosas-trampa de cacería humana en Tultepec I y II con estacas y cazadores."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(238, 228, 208), outline=(120, 85, 55), radius=28, border_w=7, shadow_offset=12)

    if pop < 0.20:
        return

    # Cielo / horizonte
    _safe_rect(draw, cx - card_w + 8, cy - card_h + 8, cx + card_w - 8, cy - 30, fill=(254, 240, 200))

    # Fosas excavadas en el terreno por humanos
    _safe_rect(draw, cx - card_w + 8, cy - 30, cx - 160, cy + card_h - 8, fill=(120, 85, 55))
    _safe_rect(draw, cx - 20, cy - 30, cx + 40, cy + card_h - 8, fill=(120, 85, 55))
    _safe_rect(draw, cx + 180, cy - 30, cx + card_w - 8, cy + card_h - 8, fill=(120, 85, 55))

    # Hueco de la Fosa 1 y 2
    f1_x1, f1_x2 = cx - 160, cx - 20
    _safe_rect(draw, f1_x1, cy - 30, f1_x2, cy + 120, fill=(65, 42, 24))
    f2_x1, f2_x2 = cx + 40, cx + 180
    _safe_rect(draw, f2_x1, cy - 30, f2_x2, cy + 120, fill=(65, 42, 24))

    # Estacas de madera afiladas
    for f_left, f_right in ((f1_x1, f1_x2), (f2_x1, f2_x2)):
        for sx in range(f_left + 15, f_right - 10, 24):
            draw.polygon([(sx, cy + 120), (sx + 8, cy + 50), (sx + 16, cy + 120)], fill=(190, 150, 100), outline=(90, 60, 30))

    # Siluetas de cazadores prehistóricos
    hunters_x = [cx - 240, cx - 200, cx + 220, cx + 270]
    for hx in hunters_x:
        draw.ellipse([(hx - 10, cy - 95), (hx + 10, cy - 40)], fill=(45, 25, 12))
        draw.ellipse([(hx - 8, cy - 112), (hx + 8, cy - 93)], fill=(45, 25, 12))
        draw.line([(hx - 15, cy - 125), (hx + 20, cy - 30)], fill=(180, 130, 80), width=3)
        draw.polygon([(hx - 18, cy - 132), (hx - 12, cy - 122), (hx - 22, cy - 120)], fill=(220, 220, 220))

    # Fuego de antorcha
    flame_f = int(math.sin(t * 8) * 4)
    fx, fy = cx - 200, cy - 118
    draw.ellipse([(fx - 7 + flame_f, fy - 14), (fx + 7 + flame_f, fy)], fill=(245, 158, 11))
    draw.ellipse([(fx - 4, fy - 10), (fx + 4, fy)], fill=(239, 68, 68))

    # Huellas de megafauna hacia la trampa
    for step in range(4):
        hx_track = cx - 90 + step * 45
        hy_track = cy - 45
        draw.ellipse([(hx_track, hy_track), (hx_track + 16, hy_track + 10)], fill=(80, 50, 30))

    f_tag = _load_font(13, bold=True)
    draw.text((f1_x1 + 18, cy - 20), "FOSA TRAMPA I", fill=(251, 191, 36), font=f_tag)
    draw.text((f2_x1 + 16, cy - 20), "FOSA TRAMPA II", fill=(251, 191, 36), font=f_tag)
    draw.text((cx - 130, cy + 130), "PROFUNDIDAD REGISTRADA: 1.70 METROS", fill=(255, 255, 255), font=f_tag)

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 250, cy + card_h - 48, cx + 250, cy + card_h - 10, fill=(15, 23, 42), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "PRIMERAS TRAMPAS DE CAZA EN EL MUNDO // TULTEPEC"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(251, 191, 36), font=f_b)


def _draw_scene_esqueleto_museo(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Reconstrucción del esqueleto de mamut al 85% de integridad con escala humana de 4 metros."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(56, 189, 248), radius=28, border_w=7, shadow_offset=12)

    if pop < 0.20:
        return

    _safe_rect(draw, cx - card_w + 10, cy + card_h - 60, cx + card_w - 10, cy + card_h - 10, fill=(30, 41, 59))

    mx, my = cx + 20, cy - 20
    draw.arc([(mx - 180, my - 130), (mx + 120, my + 50)], start=190, end=350, fill=(241, 245, 249), width=10)

    for i in range(8):
        c_x = mx - 120 + i * 26
        draw.arc([(c_x - 15, my - 70), (c_x + 20, my + 45)], start=160, end=340, fill=(226, 232, 240), width=5)

    draw.line([(mx - 110, my - 20), (mx - 125, my + 130)], fill=(241, 245, 249), width=12)
    draw.line([(mx - 60, my - 20), (mx - 75, my + 130)], fill=(203, 213, 225), width=10)
    draw.line([(mx + 45, my - 10), (mx + 55, my + 130)], fill=(241, 245, 249), width=12)
    draw.line([(mx + 85, my - 10), (mx + 95, my + 130)], fill=(203, 213, 225), width=10)

    draw.ellipse([(mx - 195, my - 95), (mx - 115, my - 20)], fill=(248, 250, 252), outline=(148, 163, 184), width=3)
    draw.arc([(mx - 310, my - 150), (mx - 145, my + 60)], start=70, end=210, fill=(255, 255, 255), width=9)

    hx = cx - 290
    hy = cy + 50
    draw.ellipse([(hx - 10, hy - 75), (hx + 10, hy - 50)], fill=(148, 163, 184))
    _safe_rect(draw, hx - 12, hy - 50, hx + 12, hy + 40, fill=(148, 163, 184))
    draw.line([(hx - 7, hy + 40), (hx - 7, hy + 80)], fill=(148, 163, 184), width=5)
    draw.line([(hx + 7, hy + 40), (hx + 7, hy + 80)], fill=(148, 163, 184), width=5)

    f_dim = _load_font(15, bold=True)
    draw.line([(cx + 175, my - 110), (cx + 175, my + 130)], fill=(251, 191, 36), width=3)
    draw.line([(cx + 165, my - 110), (cx + 185, my - 110)], fill=(251, 191, 36), width=3)
    draw.line([(cx + 165, my + 130), (cx + 185, my + 130)], fill=(251, 191, 36), width=3)
    draw.text((cx + 195, my - 10), "3.80 METROS", fill=(251, 191, 36), font=f_dim)

    _draw_sticker_card(draw, cx - 350, cy - card_h + 30, cx - 180, cy - card_h + 95, fill=(30, 41, 59), outline=(56, 189, 248), radius=14, border_w=3, shadow_offset=5)
    f_num = _load_font(28, bold=True)
    f_sub = _load_font(12, bold=True)
    draw.text((cx - 325, cy - card_h + 38), "85%", fill=(56, 189, 248), font=f_num)
    draw.text((cx - 340, cy - card_h + 74), "ESQUELETO COMPLETO", fill=(226, 232, 240), font=f_sub)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 250, cy + card_h - 48, cx + 250, cy + card_h - 10, fill=(30, 41, 59), outline=(56, 189, 248), radius=12, border_w=3, shadow_offset=4)
    lbl = "ADULTO JOVEN • 30 AÑOS // MUSEO DEL MAMUT"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(241, 245, 249), font=f_b)


# =============================================================================
# ARQUETIPOS DE ARQUEOLOGÍA (MAYAS, PIRÁMIDES Y TEMPLOS)
# =============================================================================

def _draw_scene_piramide_maya(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Pirámide mesoamericana escalonada en diorama paper-cut con templo y vegetación."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(240, 245, 235), outline=(5, 150, 105), radius=28, border_w=7, shadow_offset=12)

    # Sol dorado de fondo
    draw.ellipse([(cx - 90, cy - card_h + 30), (cx + 90, cy - card_h + 210)], fill=(251, 191, 36))

    # Base de selva
    draw.rectangle([(cx - card_w + 8, cy + 70), (cx + card_w - 8, cy + card_h - 8)], fill=(22, 101, 52))

    # Cuerpos escalonados de la pirámide (5 niveles)
    step_widths = [560, 460, 360, 260, 160]
    for lvl, sw in enumerate(step_widths):
        top_y = cy + 50 - lvl * 38
        draw.rectangle([(cx - sw // 2, top_y), (cx + sw // 2, top_y + 40)], fill=(217, 185, 145), outline=(140, 105, 70), width=2)

    # Escalinata ceremonial central
    draw.polygon([(cx - 45, cy + 90), (cx + 45, cy + 90), (cx + 25, cy - 140), (cx - 25, cy - 140)], fill=(245, 230, 205), outline=(120, 85, 55))

    # Templo superior
    draw.rectangle([(cx - 65, cy - 180), (cx + 65, cy - 140)], fill=(195, 160, 120), outline=(100, 70, 40), width=3)
    # Puerta oscura del adoratorio
    draw.rectangle([(cx - 18, cy - 165), (cx + 18, cy - 140)], fill=(15, 23, 42))

    # Fronda de palmeras y ceibas a los lados
    for side in (-1, 1):
        px = cx + side * (card_w - 80)
        draw.polygon([(px - 40, cy + 90), (px, cy - 30), (px + 40, cy + 90)], fill=(5, 150, 105))
        draw.polygon([(px - 60, cy + 60), (px - 10, cy + 10), (px + 20, cy + 70)], fill=(4, 120, 87))

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(6, 78, 59), outline=(52, 211, 153), radius=12, border_w=3, shadow_offset=4)
    lbl = "ARQUITECTURA CLÁSICA // CIVILIZACIÓN MESOAMERICANA"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


# =============================================================================
# ARQUETIPOS DE VULCANOLOGÍA Y CLIMA (VOLCANES / NIEVE)
# =============================================================================

def _draw_scene_volcan_erupcion(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Estratovolcán en erupción con columna eruptiva, ríos de lava en papel y sismograma."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(254, 242, 242), outline=(220, 38, 38), radius=28, border_w=7, shadow_offset=12)

    # 1. Columna de ceniza y piroclastos ascendente
    ash_pulse = math.sin(t * 3.5) * 8
    draw.ellipse([(cx - 140, cy - card_h + 15), (cx + 140, cy - 50)], fill=(148, 163, 184))
    draw.ellipse([(cx - 90 + int(ash_pulse), cy - card_h + 35), (cx + 110, cy - 90)], fill=(100, 116, 139))
    draw.ellipse([(cx - 160, cy - card_h + 60), (cx - 20, cy - 20)], fill=(71, 85, 105))

    # 2. Cono volcánico principal
    draw.polygon([(cx - card_w + 30, cy + card_h - 15), (cx + card_w - 30, cy + card_h - 15), (cx + 45, cy - 60), (cx - 45, cy - 60)], fill=(51, 65, 85))

    # Glaciar / Nieve en la cumbre
    draw.polygon([(cx - 45, cy - 60), (cx + 45, cy - 60), (cx + 80, cy - 5), (cx - 80, cy - 5)], fill=(255, 255, 255))

    # Cráter incandescente y lava
    draw.ellipse([(cx - 45, cy - 70), (cx + 45, cy - 50)], fill=(245, 158, 11))
    draw.ellipse([(cx - 25, cy - 65), (cx + 25, cy - 55)], fill=(239, 68, 68))

    # Ríos de lava paper-cut brillantes
    lava_pts = [(cx - 15, cy - 55), (cx - 35, cy + 20), (cx - 20, cy + 60), (cx - 50, cy + 120), (cx - 38, cy + 120), (cx - 10, cy + 55), (cx - 25, cy + 18), (cx - 5, cy - 55)]
    draw.polygon(lava_pts, fill=(239, 68, 68))

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(153, 27, 27), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "ACTIVIDAD VOLCÁNICA // MONITOREO GEOLÓGICO"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_clima_nieve(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Ciudad de México cubierta de nieve (1967) con copos en caída continua y termómetro."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(241, 245, 249), outline=(56, 189, 248), radius=28, border_w=7, shadow_offset=12)

    # Monumento a la Revolución / Skyline en silueta oscura con manto blanco
    mx = cx - 50
    my = cy + 40
    draw.rectangle([(mx - 90, my - 130), (mx + 90, my + 80)], fill=(71, 85, 105))
    draw.ellipse([(mx - 65, my - 190), (mx + 65, my - 90)], fill=(71, 85, 105))
    # Capa de nieve sobre la cúpula
    draw.arc([(mx - 70, my - 195), (mx + 70, my - 85)], start=180, end=360, fill=(255, 255, 255), width=14)

    # Copos de nieve cayendo en bucle infinito
    for i in range(28):
        fx = int(((i * 73 + t * 45) % (card_w * 2 - 30))) + cx - card_w + 15
        fy = int(((i * 97 + t * 95) % (card_h * 2 - 40))) + cy - card_h + 20
        draw.ellipse([(fx - 4, fy - 4), (fx + 4, fy + 4)], fill=(255, 255, 255))

    # Termómetro lateral en -4°C
    tx, ty = cx + 240, cy - 20
    draw.rounded_rectangle([(tx - 18, ty - 120), (tx + 18, ty + 90)], radius=12, fill=(15, 23, 42), outline=(56, 189, 248), width=3)
    draw.ellipse([(tx - 26, ty + 70), (tx + 26, ty + 120)], fill=(239, 68, 68))
    draw.rectangle([(tx - 7, ty - 10), (tx + 7, ty + 85)], fill=(239, 68, 68))

    f_t = _load_font(16, bold=True)
    draw.text((tx - 70, ty - 15), "-4 °C", fill=(239, 68, 68), font=f_t)

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(15, 23, 42), outline=(56, 189, 248), radius=12, border_w=3, shadow_offset=4)
    lbl = "FRENTE POLAR HISTÓRICO // REGISTRO BAJO CERO"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


# =============================================================================
# ARQUETIPOS DE ENIGMAS Y ESPACIO (METEORITOS / ZONA DEL SILENCIO)
# =============================================================================

def _draw_scene_meteorito_crater(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Meteorito Allende / bólido cósmico y cráter en el Bolsón de Mapimí."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(245, 158, 11), radius=28, border_w=7, shadow_offset=12)

    # Bólido estelar cayendo en diagonal
    mx = cx - 180 + int((t * 180) % 360)
    my = cy - 140 + int((t * 180) % 360)

    # Estela de fuego
    draw.polygon([(mx - 180, my - 130), (mx - 60, my - 40), (mx, my), (mx - 40, my - 60)], fill=(245, 158, 11))
    draw.polygon([(mx - 110, my - 85), (mx - 30, my - 20), (mx, my)], fill=(254, 243, 199))
    # Núcleo de meteorito
    draw.ellipse([(mx - 22, my - 22), (mx + 22, my + 22)], fill=(239, 68, 68), outline=(255, 255, 255), width=3)

    # Anillos de impacto / campo magnético
    for ring_i in range(1, 4):
        r_rad = ring_i * 45 + int(math.sin(t * 3.0 + ring_i) * 6)
        draw.ellipse([(cx - r_rad, cy + 90 - r_rad // 3), (cx + r_rad, cy + 90 + r_rad // 3)], outline=(56, 189, 248), width=3)

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(30, 41, 59), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "EVENTO DE IMPACTO // ANOMALÍA MAGNÉTICA"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(251, 191, 36), font=f_b)


# =============================================================================
# ARQUETIPOS MILITARES (ESCUADRÓN 201 / PACÍFICO)
# =============================================================================

def _draw_scene_combate_aereo(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Cazabombardero Republic P-47D Thunderbolt en vuelo dinámico con nubes paper-cut."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(241, 245, 249), outline=(148, 163, 184), radius=28, border_w=7, shadow_offset=12)

    # Avión P-47 Thunderbolt
    pitch = math.sin(t * 3.2) * 16
    roll = math.cos(t * 2.8) * 12
    bx, by = cx + int(roll), cy + int(pitch)

    # Alas con escarapelas
    draw.polygon([(bx - 250, by + 24), (bx + 250, by + 24), (bx + 184, by + 70), (bx - 184, by + 70)], fill=(71, 85, 105))
    # Escarapela mexicana (verde, blanco, rojo)
    for sign in (-1, 1):
        wx = bx + sign * 150
        draw.ellipse([(wx - 18, by + 32), (wx + 18, by + 62)], fill=(22, 101, 52))
        draw.ellipse([(wx - 12, by + 37), (wx + 12, by + 57)], fill=(255, 255, 255))
        draw.ellipse([(wx - 6, by + 42), (wx + 6, by + 52)], fill=(220, 38, 38))

    # Fuselaje central
    draw.ellipse([(bx - 46, by - 120), (bx + 46, by + 80)], fill=(51, 65, 85), outline=(255, 255, 255), width=3)
    # Cabina de cristal azul
    draw.ellipse([(bx - 28, by - 55), (bx + 28, by + 10)], fill=(56, 189, 248))
    # Hélice rotativa de 4 palas
    draw.line([(bx - 70, by - 120), (bx + 70, by - 120)], fill=(245, 158, 11), width=5)

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(15, 23, 42), outline=(56, 189, 248), radius=12, border_w=3, shadow_offset=4)
    lbl = "REPUBLIC P-47D // COMBATE AÉREO EN EL PACÍFICO"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_flota_naval(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Submarino U-boot y buque mercante en el Golfo de México."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))

    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(239, 68, 68), radius=28, border_w=7, shadow_offset=12)

    # Olas marinas
    draw.rectangle([(cx - card_w + 8, cy + 20), (cx + card_w - 8, cy + card_h - 8)], fill=(30, 58, 138))

    # Buque mercante / petrolero
    bx = cx - 40 + int(math.sin(t * 1.5) * 12)
    by = cy - 20
    draw.polygon([(bx - 140, by + 40), (bx + 140, by + 40), (bx + 110, by + 75), (bx - 110, by + 75)], fill=(185, 28, 28))
    draw.rectangle([(bx - 30, by - 30), (bx + 30, by + 40)], fill=(241, 245, 249))

    # Silueta de submarino en inmersión
    draw.ellipse([(cx - 180, cy + 85), (cx + 80, cy + 135)], fill=(15, 23, 42))

    # Cintilla inferior
    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(153, 27, 27), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "GOLFO DE MÉXICO // REGISTRO NAVAL 1942"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)

# =============================================================================
# ARQUETIPOS DE DOMINIO UNIVERSAL (ESPACIO, OCÉANOS, BIOLOGÍA, TECNOLOGÍA, MAPA)
# =============================================================================

def _draw_scene_espacio_cosmos(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Cosmos profundo, planeta con anillos, campo estelar y sonda espacial / satélite 2.5D."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(11, 19, 43), outline=(56, 189, 248), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    for i in range(24):
        sx = cx - card_w + 30 + ((i * 73 + 17) % (card_w * 2 - 60))
        sy = cy - card_h + 30 + ((i * 47 + 29) % (card_h * 2 - 70))
        twinkle = int(math.sin(t * 4.0 + i) * 2)
        sr = max(1, 2 + twinkle)
        draw.ellipse([(sx - sr, sy - sr), (sx + sr, sy + sr)], fill=(255, 255, 255))

    px = cx - 120
    py = cy - 40
    pr = 80
    draw.ellipse([(px - 140, py - 35), (px + 140, py + 35)], outline=(245, 158, 11), width=6)
    draw.ellipse([(px - pr, py - pr), (px + pr, py + pr)], fill=(30, 58, 138), outline=(56, 189, 248), width=3)
    draw.arc([(px - pr + 5, py - 20), (px + pr - 5, py + 20)], start=0, end=180, fill=(96, 165, 250), width=4)
    draw.arc([(px - 140, py - 35), (px + 140, py + 35)], start=0, end=180, fill=(251, 191, 36), width=8)

    sat_x = cx + 130 + int(math.sin(t * 1.8) * 10)
    sat_y = cy + 40 + int(math.cos(t * 1.5) * 8)
    pw, ph = 65, 34
    draw.rectangle([(sat_x - 110, sat_y - ph // 2), (sat_x - 110 + pw, sat_y + ph // 2)], fill=(30, 41, 59), outline=(96, 165, 250), width=2)
    draw.rectangle([(sat_x + 45, sat_y - ph // 2), (sat_x + 45 + pw, sat_y + ph // 2)], fill=(30, 41, 59), outline=(96, 165, 250), width=2)
    draw.line([(sat_x - 78, sat_y - ph // 2), (sat_x - 78, sat_y + ph // 2)], fill=(96, 165, 250), width=1)
    draw.line([(sat_x + 78, sat_y - ph // 2), (sat_x + 78, sat_y + ph // 2)], fill=(96, 165, 250), width=1)
    draw.rounded_rectangle([(sat_x - 36, sat_y - 28), (sat_x + 36, sat_y + 28)], radius=6, fill=(245, 158, 11), outline=(255, 255, 255), width=2)
    draw.arc([(sat_x - 22, sat_y - 48), (sat_x + 22, sat_y - 20)], start=180, end=360, fill=(255, 255, 255), width=3)
    draw.line([(sat_x, sat_y - 28), (sat_x, sat_y - 44)], fill=(255, 255, 255), width=2)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(15, 23, 42), outline=(56, 189, 248), radius=12, border_w=3, shadow_offset=4)
    lbl = "EXPLORACIÓN ESPACIAL // ÓRBITA & TELEMETRÍA"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_oceano_naufragio(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Océano abisal con olas estratificadas paper-cut y sumergible de exploración / silueta naval."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(8, 28, 48), outline=(14, 116, 144), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    for r_i in range(5):
        rx1 = cx - 180 + r_i * 90
        rx2 = rx1 + 50
        draw.polygon([(rx1, cy - card_h + 10), (rx2, cy - card_h + 10), (rx2 + 70, cy + 80), (rx1 + 30, cy + 80)], fill=(12, 45, 75))

    for wave_idx, (col, base_off, freq) in enumerate([((14, 116, 144), 60, 2.0), ((8, 80, 110), 110, 2.8), ((4, 50, 75), 160, 3.5)]):
        pts = [(cx - card_w + 10, cy + card_h - 10)]
        for x_step in range(cx - card_w + 10, cx + card_w - 5, 25):
            y_wave = int(cy + base_off - 120 + math.sin(t * freq + x_step * 0.02) * 12)
            pts.append((x_step, y_wave))
        pts.append((cx + card_w - 10, cy + card_h - 10))
        draw.polygon(pts, fill=col)

    sub_x = cx + int(math.sin(t * 1.5) * 20)
    sub_y = cy + 10 + int(math.cos(t * 1.8) * 10)
    draw.ellipse([(sub_x - 100, sub_y - 45), (sub_x + 80, sub_y + 45)], fill=(255, 255, 255))
    draw.ellipse([(sub_x - 95, sub_y - 40), (sub_x + 75, sub_y + 40)], fill=(245, 158, 11))
    draw.ellipse([(sub_x + 30, sub_y - 25), (sub_x + 70, sub_y + 25)], fill=(254, 240, 138), outline=(255, 255, 255), width=3)
    draw.rounded_rectangle([(sub_x - 40, sub_y - 65), (sub_x + 10, sub_y - 40)], radius=4, fill=(217, 119, 6), outline=(255, 255, 255), width=2)
    draw.polygon([(sub_x - 125, sub_y - 25), (sub_x - 95, sub_y), (sub_x - 125, sub_y + 25)], fill=(180, 83, 9))

    for b_i in range(5):
        bx = sub_x - 130 - b_i * 22
        by = sub_y - 10 - int((t * 50 + b_i * 35) % 140)
        draw.ellipse([(bx - 5, by - 5), (bx + 5, by + 5)], outline=(224, 242, 254), width=2)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(6, 78, 59), outline=(52, 211, 153), radius=12, border_w=3, shadow_offset=4)
    lbl = "EXPEDICIÓN OCEÁNICA // PROFUNDIDAD ABISAL"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_biologia_celula_adn(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Estructura molecular de ADN en hélice 2.5D y campo microscópico celular."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(16, 185, 129), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    lens_r = min(card_w - 40, card_h - 50)
    draw.ellipse([(cx - lens_r, cy - lens_r), (cx + lens_r, cy + lens_r)], fill=(19, 35, 52), outline=(51, 65, 85), width=3)

    helix_h = lens_r * 2 - 40
    step_y = 18
    num_rungs = helix_h // step_y
    y_start = cy - lens_r + 20

    for i in range(num_rungs):
        cur_y = y_start + i * step_y
        phase = t * 2.5 + i * 0.4
        x_left = cx + int(math.sin(phase) * 85)
        x_right = cx - int(math.sin(phase) * 85)

        col_rung = (245, 158, 11) if (i % 2 == 0) else (52, 211, 153)
        draw.line([(x_left, cur_y), (x_right, cur_y)], fill=col_rung, width=4)

        draw.ellipse([(x_left - 7, cur_y - 7), (x_left + 7, cur_y + 7)], fill=(239, 68, 68), outline=(255, 255, 255), width=2)
        draw.ellipse([(x_right - 7, cur_y - 7), (x_right + 7, cur_y + 7)], fill=(59, 130, 246), outline=(255, 255, 255), width=2)

    for c_i, (ox, oy, cr) in enumerate([(-180, -70, 28), (170, 60, 32), (-160, 90, 22), (180, -90, 24)]):
        draw.ellipse([(cx + ox - cr, cy + oy - cr), (cx + ox + cr, cy + oy + cr)], fill=(20, 83, 45), outline=(52, 211, 153), width=2)
        draw.ellipse([(cx + ox - 8, cy + oy - 8), (cx + ox + 8, cy + oy + 8)], fill=(134, 239, 172))

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(6, 78, 59), outline=(52, 211, 153), radius=12, border_w=3, shadow_offset=4)
    lbl = "INVESTIGACIÓN BIOLÓGICA // ESTRUCTURA GENÉTICA"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_mapa_ubicacion(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Mapa cartográfico 2.5D con curvas topográficas, rosa de los vientos y pin de localización dinámico."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(245, 238, 220), outline=(160, 120, 85), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    for gx in range(cx - card_w + 30, cx + card_w - 20, 60):
        draw.line([(gx, cy - card_h + 20), (gx, cy + card_h - 55)], fill=(225, 210, 185), width=1)
    for gy in range(cy - card_h + 30, cy + card_h - 55, 50):
        draw.line([(cx - card_w + 20, gy), (cx + card_w - 20, gy)], fill=(225, 210, 185), width=1)

    pts_land = [
        (cx - 280, cy + 90), (cx - 240, cy - 60), (cx - 140, cy - 110),
        (cx + 60, cy - 80), (cx + 200, cy - 120), (cx + 290, cy + 20),
        (cx + 180, cy + 100), (cx - 40, cy + 70), (cx - 180, cy + 120)
    ]
    draw.polygon([(x + 4, y + 4) for x, y in pts_land], fill=(210, 190, 160))
    draw.polygon(pts_land, fill=(235, 218, 190), outline=(180, 140, 100), width=2)

    target_x, target_y = cx + 20, cy - 15
    for r_i in range(3):
        radar_r = 30 + r_i * 40 + int((t * 25) % 40)
        draw.ellipse([(target_x - radar_r, target_y - radar_r), (target_x + radar_r, target_y + radar_r)], outline=(220, 38, 38), width=2)

    pin_y = target_y - int(math.sin(t * 3.0) * 8)
    draw.ellipse([(target_x - 22, pin_y - 48), (target_x + 22, pin_y - 4)], fill=(220, 38, 38), outline=(255, 255, 255), width=3)
    draw.polygon([(target_x - 18, pin_y - 20), (target_x + 18, pin_y - 20), (target_x, pin_y + 10)], fill=(220, 38, 38))
    draw.ellipse([(target_x - 7, pin_y - 32), (target_x + 7, pin_y - 18)], fill=(255, 255, 255))

    loc_name = scene.get("location_name") or extract_location_from_text(title + " " + scene.get("text", ""))
    f_b = _load_font(18, bold=True)

    _draw_sticker_card(draw, cx - 260, cy + card_h - 48, cx + 260, cy + card_h - 10, fill=(15, 23, 42), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = f"UBICACIÓN GEOGRÁFICA // {loc_name.upper()}"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(251, 191, 36), font=f_b)


def _draw_scene_historia_monumento(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Fachada arquitectónica clásica/palaciega en paper-cut con columnas dóricas y frontón monumental."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(248, 241, 228), outline=(140, 110, 80), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    base_y = cy + 110
    for s_i, dy in enumerate([0, 15, 30]):
        sw = 280 + s_i * 30
        draw.rectangle([(cx - sw, base_y + dy), (cx + sw, base_y + dy + 15)], fill=(210, 195, 175), outline=(160, 140, 120), width=2)

    col_w = 28
    col_h = 160
    col_xs = [cx - 200, cx - 70, cx + 70, cx + 200]
    for x_c in col_xs:
        draw.rectangle([(x_c - col_w // 2, base_y - col_h), (x_c + col_w // 2, base_y)], fill=(255, 252, 245), outline=(180, 160, 140), width=2)
        draw.line([(x_c - 4, base_y - col_h + 10), (x_c - 4, base_y - 10)], fill=(220, 205, 185), width=2)
        draw.line([(x_c + 4, base_y - col_h + 10), (x_c + 4, base_y - 10)], fill=(220, 205, 185), width=2)
        draw.rounded_rectangle([(x_c - col_w // 2 - 8, base_y - col_h - 14), (x_c + col_w // 2 + 8, base_y - col_h)], radius=3, fill=(190, 170, 150))

    ent_y = base_y - col_h - 14
    draw.rectangle([(cx - 260, ent_y - 20), (cx + 260, ent_y)], fill=(225, 210, 190), outline=(160, 140, 120), width=2)
    pts_ped = [(cx - 270, ent_y - 20), (cx + 270, ent_y - 20), (cx, ent_y - 105)]
    draw.polygon([(x + 4, y + 4) for x, y in pts_ped], fill=(190, 170, 150))
    draw.polygon(pts_ped, fill=(245, 235, 218), outline=(160, 140, 120), width=3)
    draw.ellipse([(cx - 22, ent_y - 75), (cx + 22, ent_y - 31)], fill=(245, 158, 11), outline=(255, 255, 255), width=2)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(120, 53, 15), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = "PATRIMONIO HISTÓRICO // ARQUITECTURA DOCUMENTADA"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_tecnologia_circuito(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Microprocesador central, pistas de circuito impreso PCB y paquetes de datos en 2.5D."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(6, 182, 212), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    tracks = [
        [(-220, -110), (-120, -110), (-60, -60)],
        [(-220, 0), (-90, 0)],
        [(-220, 110), (-120, 110), (-60, 60)],
        [(220, -110), (120, -110), (60, -60)],
        [(220, 0), (90, 0)],
        [(220, 110), (120, 110), (60, 60)],
        [(0, -180), (0, -80)],
        [(0, 180), (0, 80)],
    ]
    for trk in tracks:
        pts = [(cx + x, cy + y) for x, y in trk]
        draw.line(pts, fill=(30, 41, 59), width=8)
        draw.line(pts, fill=(6, 182, 212), width=3)
        draw.ellipse([(pts[0][0] - 6, pts[0][1] - 6), (pts[0][0] + 6, pts[0][1] + 6)], fill=(245, 158, 11), outline=(255, 255, 255), width=2)

    cpu_sz = 90
    _draw_sticker_card(draw, cx - cpu_sz, cy - cpu_sz, cx + cpu_sz, cy + cpu_sz, fill=(30, 41, 59), outline=(56, 189, 248), radius=16, border_w=4, shadow_offset=8)

    for pin_i in range(-3, 4):
        off = pin_i * 20
        draw.rectangle([(cx + off - 4, cy - cpu_sz - 12), (cx + off + 4, cy - cpu_sz)], fill=(245, 158, 11))
        draw.rectangle([(cx + off - 4, cy + cpu_sz), (cx + off + 4, cy + cpu_sz + 12)], fill=(245, 158, 11))
        draw.rectangle([(cx - cpu_sz - 12, cy + off - 4), (cx - cpu_sz, cy + off + 4)], fill=(245, 158, 11))
        draw.rectangle([(cx + cpu_sz, cy + off - 4), (cx + cpu_sz + 12, cy + off + 4)], fill=(245, 158, 11))

    pulse_r = int(28 + math.sin(t * 5.0) * 6)
    draw.ellipse([(cx - pulse_r, cy - pulse_r), (cx + pulse_r, cy + pulse_r)], fill=(6, 182, 212), outline=(255, 255, 255), width=3)
    f_cpu = _load_font(18, bold=True)
    draw.text((cx - draw.textlength("CORE", font=f_cpu) / 2, cy - 10), "CORE", fill=(255, 255, 255), font=f_cpu)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(15, 23, 42), outline=(6, 182, 212), radius=12, border_w=3, shadow_offset=4)
    lbl = "TECNOLOGÍA DE VANGUARDIA // SISTEMAS DIGITALES"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_ingenieria_maquinaria(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Engranajes mecánicos rotatorios en diorama 2.5D con cianotipo blueprint y vectores cinemáticos."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(23, 37, 84), outline=(96, 165, 250), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    for gx in range(cx - card_w + 30, cx + card_w - 20, 45):
        draw.line([(gx, cy - card_h + 20), (gx, cy + card_h - 55)], fill=(30, 58, 138), width=1)
    for gy in range(cy - card_h + 30, cy + card_h - 55, 45):
        draw.line([(cx - card_w + 20, gy), (cx + card_w - 20, gy)], fill=(30, 58, 138), width=1)

    def _draw_gear(gx: int, gy: int, radius: float, num_teeth: int, rot_angle: float, col_fill: tuple[int, int, int]):
        tooth_depth = 16
        pts = []
        for i in range(num_teeth):
            a1 = rot_angle + (i * 2 * math.pi / num_teeth)
            a2 = a1 + (math.pi / num_teeth) * 0.4
            a3 = a1 + (math.pi / num_teeth) * 0.6
            a4 = a1 + (math.pi / num_teeth)

            r_out = radius + tooth_depth
            pts.append((gx + int(math.cos(a1) * radius), gy + int(math.sin(a1) * radius)))
            pts.append((gx + int(math.cos(a2) * r_out), gy + int(math.sin(a2) * r_out)))
            pts.append((gx + int(math.cos(a3) * r_out), gy + int(math.sin(a3) * r_out)))
            pts.append((gx + int(math.cos(a4) * radius), gy + int(math.sin(a4) * radius)))

        draw.polygon([(x + 4, y + 4) for x, y in pts], fill=(15, 23, 42))
        draw.polygon(pts, fill=col_fill, outline=(255, 255, 255), width=3)
        draw.ellipse([(gx - 28, gy - 28), (gx + 28, gy + 28)], fill=(23, 37, 84), outline=(255, 255, 255), width=3)

    _draw_gear(cx - 75, cy - 25, 85, 10, t * 1.5, (245, 158, 11))
    _draw_gear(cx + 85, cy + 45, 58, 7, -t * (1.5 * 85 / 58) + 0.35, (56, 189, 248))

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(30, 58, 138), outline=(96, 165, 250), radius=12, border_w=3, shadow_offset=4)
    lbl = "INGENIERÍA APLICADA // CINEMÁTICA Y MECANISMOS"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_naturaleza_selva(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Dosel vegetal estratificado en paper-cut, fauna silvestre y cordillera tropical con rayos solares."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(236, 253, 245), outline=(22, 101, 52), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    draw.ellipse([(cx + 90, cy - card_h + 30), (cx + 210, cy - card_h + 150)], fill=(254, 240, 138))

    pts_bg = [(cx - card_w, cy + 30), (cx - 200, cy - 50), (cx - 40, cy + 10), (cx + 120, cy - 70), (cx + card_w, cy + 30)]
    draw.polygon(pts_bg, fill=(167, 243, 208))

    for foliage_idx, (col, y_base) in enumerate([((34, 197, 94), cy + 40), ((22, 163, 74), cy + 85), ((20, 83, 45), cy + 130)]):
        pts_fol = [(cx - card_w, cy + card_h - 10)]
        step = 35
        for x_f in range(cx - card_w, cx + card_w + step, step):
            wave = int(math.sin(t * 1.5 + x_f * 0.03 + foliage_idx) * 8)
            h_tree = 50 + ((x_f * 13) % 45)
            pts_fol.append((x_f, y_base - h_tree + wave))
        pts_fol.append((cx + card_w, cy + card_h - 10))
        draw.polygon(pts_fol, fill=col)

    for b_i, (bx_off, by_off) in enumerate([(-120, -90), (-60, -115), (40, -80)]):
        b_x = cx + bx_off + int(math.sin(t * 2.0 + b_i) * 15)
        b_y = cy + by_off + int(math.cos(t * 2.0 + b_i) * 6)
        draw.arc([(b_x - 18, b_y - 8), (b_x, b_y + 8)], start=180, end=360, fill=(20, 83, 45), width=3)
        draw.arc([(b_x, b_y - 8), (b_x + 18, b_y + 8)], start=180, end=360, fill=(20, 83, 45), width=3)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(20, 83, 45), outline=(34, 197, 94), radius=12, border_w=3, shadow_offset=4)
    lbl = "BIODIVERSIDAD Y FAUNA // RESERVA NATURAL"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


# =============================================================================
# ARQUETIPOS UNIVERSALES DINÁMICOS CON ADAPTACIÓN A DATOS REALES DEL GUION
# =============================================================================

def _draw_scene_expediente_dossier(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Carpeta Manila de expediente desclasificado con clip y sello oficial."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(254, 243, 199), outline=(180, 130, 80), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    for off, col in ((-20, (248, 250, 252)), (-10, (241, 245, 249)), (0, (255, 255, 255))):
        draw.rounded_rectangle([(cx - card_w + 35 + off, cy - card_h + 40 + off), (cx + card_w - 35 + off, cy + card_h - 60 + off)], radius=12, fill=col, outline=(203, 213, 225), width=2)

    for l_y in range(cy - card_h + 80, cy + 80, 24):
        draw.line([(cx - card_w + 60, l_y), (cx + card_w - 70, l_y)], fill=(148, 163, 184), width=3)

    f_seal = _load_font(26, bold=True)
    draw.rectangle([(cx - 160, cy - 25), (cx + 160, cy + 25)], fill=(254, 226, 226), outline=(220, 38, 38), width=4)
    draw.text((cx - 145, cy - 18), "EXPEDIENTE OFICIAL", fill=(220, 38, 38), font=f_seal)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(15, 23, 42), outline=(245, 158, 11), radius=12, border_w=3, shadow_offset=4)
    lbl = f"ARCHIVOS DOCUMENTADOS • {scene.get('badge_num', 'HISTORIA')}"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(251, 191, 36), font=f_b)


def _draw_scene_periodico_titulares(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Portada de periódico histórico con tipografía serifa y titular dinámico."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(254, 252, 247), outline=(100, 116, 139), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    f_head = _load_font(32, bold=True)
    f_date = _load_font(13, bold=False)
    draw.text((cx - 190, cy - card_h + 30), "EL HERALDO NACIONAL", fill=(15, 23, 42), font=f_head)
    draw.text((cx - 200, cy - card_h + 75), f"EDICIÓN ESPECIAL // {scene.get('badge_num', 'ARCHIVO HISTÓRICO')}", fill=(100, 116, 139), font=f_date)
    draw.line([(cx - card_w + 30, cy - card_h + 98), (cx + card_w - 30, cy - card_h + 98)], fill=(15, 23, 42), width=3)

    f_tit = _load_font(21, bold=True)
    summary_text = scene.get("summary", title).upper()[:42]
    draw.text((cx - card_w + 40, cy - card_h + 115), summary_text, fill=(185, 28, 28), font=f_tit)

    col_w = (card_w * 2 - 100) // 2
    for c_i in (0, 1):
        c_x = cx - card_w + 40 + c_i * (col_w + 20)
        for l_y in range(cy - 20, cy + card_h - 70, 18):
            draw.line([(c_x, l_y), (c_x + col_w - 15, l_y)], fill=(148, 163, 184), width=2)


def _draw_scene_linea_tiempo(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Cronología lineal de hitos adaptada a los años reales extraídos del texto."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(56, 189, 248), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    years = scene.get("years_list") or extract_years_from_text(title + " " + scene.get("text", ""))
    macro = scene.get("detected_macro") or detect_macro_theme(title + " " + scene.get("text", ""))

    if len(years) >= 3:
        milestones = [
            (years[0], "ORIGEN / ANTECEDENTE", (251, 191, 36)),
            (years[1], "SUCESO PRINCIPAL", (56, 189, 248)),
            (years[2], "EVIDENCIA / REGISTRO", (52, 211, 153)),
        ]
    elif len(years) == 2:
        milestones = [
            (years[0], "ORIGEN DOCUMENTADO", (251, 191, 36)),
            (years[1], "SUCESO HISTÓRICO", (56, 189, 248)),
            ("HOY", "INVESTIGACIÓN ACTUAL", (52, 211, 153)),
        ]
    elif len(years) == 1:
        milestones = [
            ("FASE I", "ANTECEDENTES", (251, 191, 36)),
            (years[0], "AÑO DOCUMENTADO", (56, 189, 248)),
            ("DICTAMEN", "EVIDENCIA FINAL", (52, 211, 153)),
        ]
    else:
        if macro == "paleontologia":
            milestones = [("14,000 AP", "PLEISTOCENO", (251, 191, 36)), ("2015", "HALLAZGO", (56, 189, 248)), ("2019", "TRAMPAS INAH", (52, 211, 153))]
        elif macro == "clima_desastres":
            milestones = [("1907", "REGISTRO", (148, 163, 184)), ("1920", "ANTECEDENTE", (56, 189, 248)), ("1967", "GRAN NEVADA", (239, 68, 68))]
        elif macro == "militar_conflicto":
            milestones = [("1942", "POTRERO LLANO", (239, 68, 68)), ("1944", "ENTRENAMIENTO", (245, 158, 11)), ("1945", "LUZÓN FILIPINAS", (52, 211, 153))]
        else:
            milestones = [("ACTO I", "ANTECEDENTE", (148, 163, 184)), ("ACTO II", "SUCESO", (56, 189, 248)), ("ACTO III", "EVIDENCIA", (52, 211, 153))]

    line_y = cy
    draw.line([(cx - card_w + 60, line_y), (cx + card_w - 60, line_y)], fill=(71, 85, 105), width=6)

    f_yr = _load_font(20, bold=True)
    f_sub = _load_font(12, bold=True)

    for idx, (yr, lbl, col) in enumerate(milestones):
        mx = cx - 220 + idx * 220
        draw.ellipse([(mx - 22, line_y - 22), (mx + 22, line_y + 22)], fill=(15, 23, 42), outline=col, width=5)
        draw.ellipse([(mx - 10, line_y - 10), (mx + 10, line_y + 10)], fill=col)
        draw.text((mx - draw.textlength(yr, font=f_yr) / 2, line_y - 58), yr, fill=col, font=f_yr)
        draw.text((mx - draw.textlength(lbl, font=f_sub) / 2, line_y + 35), lbl, fill=(241, 245, 249), font=f_sub)

    f_b = _load_font(18, bold=True)
    _draw_sticker_card(draw, cx - 240, cy + card_h - 48, cx + 240, cy + card_h - 10, fill=(30, 41, 59), outline=(56, 189, 248), radius=12, border_w=3, shadow_offset=4)
    lbl = "CRONOLOGÍA COMPROBADA // LÍNEA TEMPORAL"
    draw.text((cx - draw.textlength(lbl, font=f_b) / 2, cy + card_h - 38), lbl, fill=(255, 255, 255), font=f_b)


def _draw_scene_estadistica_record(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Métricas y cifras adaptativas según los números reales detectados en el guion."""
    cx, cy = w // 2, int(h * 0.51)
    card_w = max(40, int(420 * pop))
    card_h = max(35, int(330 * pop))
    _draw_sticker_card(draw, cx - card_w, cy - card_h, cx + card_w, cy + card_h, fill=(15, 23, 42), outline=(245, 158, 11), radius=28, border_w=7, shadow_offset=12)
    if pop < 0.20:
        return

    metrics = scene.get("metrics_list") or extract_metrics_from_text(title + " " + scene.get("text", ""))
    macro = scene.get("detected_macro") or detect_macro_theme(title + " " + scene.get("text", ""))

    if len(metrics) >= 2:
        c1_num, c1_lbl = metrics[0]
        c2_num, c2_lbl = metrics[1]
    elif len(metrics) == 1:
        c1_num, c1_lbl = metrics[0]
        c2_num, c2_lbl = "100%", "EVIDENCIA VERIFICADA"
    else:
        if macro == "paleontologia":
            c1_num, c1_lbl = "1,500+", "HUESOS FÓSILES"
            c2_num, c2_lbl = "14", "EJEMPLARES IDENTIFICADOS"
        elif macro == "clima_desastres":
            c1_num, c1_lbl = "-4 °C", "TEMPERATURA MÍNIMA"
            c2_num, c2_lbl = "8 CM", "CAPA DE NIEVE"
        elif macro == "militar_conflicto":
            c1_num, c1_lbl = "59", "MISIONES DE COMBATE"
            c2_num, c2_lbl = "280+", "HORAS DE VUELO"
        else:
            c1_num, c1_lbl = "100%", "EVIDENCIA VERIFICADA"
            c2_num, c2_lbl = "02", "REGISTROS CLAVE"

    f_big = _load_font(52, bold=True)
    f_lbl = _load_font(16, bold=True)

    draw.text((cx - 290, cy - 80), c1_num, fill=(251, 191, 36), font=f_big)
    draw.text((cx - 290, cy + 5), c1_lbl, fill=(241, 245, 249), font=f_lbl)

    draw.text((cx + 60, cy - 80), c2_num, fill=(56, 189, 248), font=f_big)
    draw.text((cx + 60, cy + 5), c2_lbl, fill=(241, 245, 249), font=f_lbl)


def _draw_scene_cierre_medallon(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Medallón Documental de Cierre adaptado a la temática con llamado a la acción."""
    cx, cy = w // 2, int(h * 0.49)
    mr = max(30, int(195 * pop))

    for r_i in range(12):
        ang = t * 0.8 + (r_i * math.pi / 6.0)
        x2 = cx + int(math.cos(ang) * (mr + 75))
        y2 = cy + int(math.sin(ang) * (mr + 75))
        draw.line([(cx, cy), (x2, y2)], fill=(245, 158, 11), width=8)

    draw.ellipse([(cx - mr - 8, cy - mr - 8), (cx + mr + 8, cy + mr + 8)], fill=(255, 255, 255))
    draw.ellipse([(cx - mr, cy - mr), (cx + mr, cy + mr)], fill=(15, 23, 42), outline=(251, 191, 36), width=6)

    f_big = _load_font(34, bold=True)
    f_cta = _load_font(21, bold=True)
    t1 = "HISTORIANDO"
    t2 = "EXPEDIENTE DOCUMENTAL"
    draw.text((cx - draw.textlength(t1, font=f_big) / 2, cy - 42), t1, fill=(251, 191, 36), font=f_big)
    draw.text((cx - draw.textlength(t2, font=f_cta) / 2, cy + 12), t2, fill=(241, 245, 249), font=f_cta)

    by = cy + mr + 85
    _draw_sticker_card(draw, cx - 340, by - 48, cx + 340, by + 48, fill=(217, 119, 6), outline=(255, 255, 255), radius=22, border_w=6, shadow_offset=9)
    q_txt = "¿QUÉ OPINAS? DÉJALO EN LOS COMENTARIOS"
    draw.text((cx - draw.textlength(q_txt, font=f_cta) / 2, by - 14), q_txt, fill=(255, 255, 255), font=f_cta)


# =============================================================================
# MAPEO Y DESPACHADOR CENTRAL DE 23 ARQUETIPOS
# =============================================================================

DISPATCHER: dict[str, Callable] = {
    # Paleontología & Fósiles
    "mamut_prehistorico": _draw_scene_mamut_prehistorico,
    "excavacion_fosiles": _draw_scene_excavacion_fosiles,
    "trampa_caza_prehistoria": _draw_scene_trampa_caza_prehistoria,
    "esqueleto_museo": _draw_scene_esqueleto_museo,

    # Arqueología & Culturas Antiguas
    "piramide_maya": _draw_scene_piramide_maya,

    # Astronomía & Espacio
    "espacio_cosmos": _draw_scene_espacio_cosmos,
    "meteorito_crater": _draw_scene_meteorito_crater,

    # Océanos & Mares
    "oceano_naufragio": _draw_scene_oceano_naufragio,

    # Biología & Medicina
    "biologia_celula_adn": _draw_scene_biologia_celula_adn,

    # Geografía & Cartografía Universal
    "mapa_ubicacion": _draw_scene_mapa_ubicacion,

    # Historia, Patrimonio & Arquitectura
    "historia_monumento": _draw_scene_historia_monumento,

    # Clima & Vulcanología
    "volcan_erupcion": _draw_scene_volcan_erupcion,
    "clima_nieve": _draw_scene_clima_nieve,

    # Tecnología, Computación & IA
    "tecnologia_circuito": _draw_scene_tecnologia_circuito,

    # Ciencia, Física & Mecánica
    "ingenieria_maquinaria": _draw_scene_ingenieria_maquinaria,

    # Naturaleza, Bosques & Fauna
    "naturaleza_selva": _draw_scene_naturaleza_selva,

    # Militar & Conflicto Bélico (ESTRICTO)
    "combate_aereo": _draw_scene_combate_aereo,
    "flota_naval": _draw_scene_flota_naval,

    # Universales adaptativos
    "expediente_dossier": _draw_scene_expediente_dossier,
    "cronica_expediente": _draw_scene_expediente_dossier,
    "periodico_titulares": _draw_scene_periodico_titulares,
    "linea_tiempo": _draw_scene_linea_tiempo,
    "estadistica_record": _draw_scene_estadistica_record,
    "cierre_medallon": _draw_scene_cierre_medallon,
}

# Fallbacks ilustrativos por macro-tema (GARANTÍA: Cero elementos bélicos fuera de militar)
THEME_FALLBACK_DISPATCHER: dict[str, Callable] = {
    "paleontologia": _draw_scene_mamut_prehistorico,
    "arqueologia": _draw_scene_piramide_maya,
    "astronomia_espacio": _draw_scene_espacio_cosmos,
    "oceanos_maritimo": _draw_scene_oceano_naufragio,
    "biologia_medicina": _draw_scene_biologia_celula_adn,
    "clima_desastres": _draw_scene_clima_nieve,
    "volcan_geologia": _draw_scene_volcan_erupcion,
    "militar_conflicto": _draw_scene_combate_aereo,
    "tecnologia_computacion": _draw_scene_tecnologia_circuito,
    "ciencia_ingenieria": _draw_scene_ingenieria_maquinaria,
    "naturaleza_fauna": _draw_scene_naturaleza_selva,
    "historia_monumentos": _draw_scene_historia_monumento,
    "documental_general": _draw_scene_mapa_ubicacion,
}


def render_archetype_scene(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, title: str, scene: dict[str, Any], pop: float):
    """Ejecuta el renderizador adecuado con fallback inteligente garantizado."""
    stype = scene.get("scene_type", "")
    fn = DISPATCHER.get(stype)
    if fn:
        fn(draw, w, h, t, title, scene, pop)
    else:
        macro = scene.get("detected_macro") or detect_macro_theme(title + " " + scene.get("text", ""))
        fallback_fn = THEME_FALLBACK_DISPATCHER.get(macro, _draw_scene_mapa_ubicacion)
        fallback_fn(draw, w, h, t, title, scene, pop)


# =============================================================================
# SEGMENTADOR DINÁMICO DE ESCENAS NO REPETITIVAS CON COHERENCIA TEMÁTICA TOTAL
# =============================================================================

def split_into_dynamic_scenes(narration: str, total_duration: float, title: str) -> list[dict[str, Any]]:
    """Divide el guion en escenas asignando rotaciones temáticas ricas, sin repeticiones y 100% pertinentes."""
    try:
        from studio.karaoke_subtitles import clean_and_correct_spanish_orthography
        narration, _ = clean_and_correct_spanish_orthography(narration)
        title, _ = clean_and_correct_spanish_orthography(title)
    except Exception:
        pass

    full_corpus = (title or "") + " " + (narration or "")
    macro = detect_macro_theme(full_corpus)
    loc_name = extract_location_from_text(full_corpus)
    years_list = extract_years_from_text(full_corpus)
    metrics_list = extract_metrics_from_text(full_corpus)

    # Catálogo dinámico de arquetipos según el macro-tema
    if macro == "paleontologia":
        theme_rotation = [
            "mamut_prehistorico",
            "excavacion_fosiles",
            "mapa_ubicacion",
            "trampa_caza_prehistoria",
            "esqueleto_museo",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
            "expediente_dossier",
        ]
        defaults_badge = [("14,000 AP", "PLEISTOCENO"), ("INAH", "INVESTIGACIÓN"), ("TULTEPEC", "YACIMIENTO"), ("FÓSIL", "PALEONTOLOGÍA")]
    elif macro == "arqueologia":
        theme_rotation = [
            "piramide_maya",
            "excavacion_fosiles",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "expediente_dossier",
            "estadistica_record",
        ]
        defaults_badge = [("INAH", "ARQUEOLOGÍA"), ("SIGLO VIII", "CLÁSICO MAYA"), ("MONUMENTO", "PATRIMONIO"), ("MÉXICO", "ZONA ARQUEOLÓGICA")]
    elif macro == "astronomia_espacio":
        theme_rotation = [
            "espacio_cosmos",
            "meteorito_crater",
            "mapa_ubicacion",
            "tecnologia_circuito",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
            "expediente_dossier",
        ]
        defaults_badge = [("NASA", "ASTRONOMÍA"), ("ÓRBITA", "TELEMETRÍA"), ("COSMOS", "EXPLORACIÓN"), ("ANOMALÍA", "CAMPO MAGNÉTICO")]
    elif macro == "oceanos_maritimo":
        theme_rotation = [
            "oceano_naufragio",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "expediente_dossier",
            "estadistica_record",
        ]
        defaults_badge = [("OCÉANO", "EXPEDICIÓN"), ("ABISAL", "PROFUNDIDAD"), ("MAR", "CRÓNICA NAVAL"), ("REGISTRO", "BITÁCORA")]
    elif macro == "biologia_medicina":
        theme_rotation = [
            "biologia_celula_adn",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
            "expediente_dossier",
        ]
        defaults_badge = [("CIENCIA", "BIOLOGÍA"), ("ADN", "GENÉTICA"), ("LAB", "INVESTIGACIÓN"), ("MÉDICO", "HALLAZGO")]
    elif macro == "clima_desastres":
        theme_rotation = [
            "clima_nieve",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "expediente_dossier",
            "estadistica_record",
        ]
        defaults_badge = [("CLIMA", "METEOROLOGÍA"), ("REGISTRO", "TEMPERATURA"), ("ATMÓSFERA", "FENÓMENO"), ("HISTORIA", "CRÓNICA CLIMÁTICA")]
    elif macro == "volcan_geologia":
        theme_rotation = [
            "volcan_erupcion",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "expediente_dossier",
            "estadistica_record",
        ]
        defaults_badge = [("VOLCÁN", "ESTRATOVOLCÁN"), ("CENIZA", "ACTIVIDAD"), ("SÍSMICO", "MAGNITUD"), ("ALERTA", "CENAPRED")]
    elif macro == "militar_conflicto":
        theme_rotation = [
            "combate_aereo",
            "flota_naval",
            "mapa_ubicacion",
            "expediente_dossier",
            "linea_tiempo",
            "periodico_titulares",
            "estadistica_record",
        ]
        defaults_badge = [("1945", "SEGUNDA GUERRA"), ("FAEM", "FUERZA AÉREA"), ("P-47D", "CAZABOMBARDEO"), ("PACÍFICO", "ZONA COMBATE")]
    elif macro == "tecnologia_computacion":
        theme_rotation = [
            "tecnologia_circuito",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
            "expediente_dossier",
        ]
        defaults_badge = [("TECNOLOGÍA", "COMPUTACIÓN"), ("CHIP", "PROCESAMIENTO"), ("DATOS", "ALGORITMO"), ("SISTEMAS", "INNOVACIÓN")]
    elif macro == "ciencia_ingenieria":
        theme_rotation = [
            "ingenieria_maquinaria",
            "tecnologia_circuito",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
            "expediente_dossier",
        ]
        defaults_badge = [("INGENIERÍA", "CINEMÁTICA"), ("MECÁNICA", "DISEÑO"), ("PRECISIÓN", "SISTEMAS"), ("CIENCIA", "DESARROLLO")]
    elif macro == "naturaleza_fauna":
        theme_rotation = [
            "naturaleza_selva",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
            "expediente_dossier",
        ]
        defaults_badge = [("FAUNA", "BIODIVERSIDAD"), ("ECOSISTEMA", "RESERVA"), ("ESPECIES", "CONSERVACIÓN"), ("NATURALEZA", "HÁBITAT")]
    elif macro == "historia_monumentos":
        theme_rotation = [
            "historia_monumento",
            "mapa_ubicacion",
            "periodico_titulares",
            "linea_tiempo",
            "expediente_dossier",
            "estadistica_record",
        ]
        defaults_badge = [("HISTORIA", "PATRIMONIO"), ("MONUMENTO", "ARQUITECTURA"), ("ARCHIVOS", "REGISTRO"), ("ÉPOCA", "CRÓNICA")]
    else:
        theme_rotation = [
            "mapa_ubicacion",
            "expediente_dossier",
            "periodico_titulares",
            "linea_tiempo",
            "estadistica_record",
        ]
        defaults_badge = [("ACTO I", "EXPEDIENTE"), ("HISTORIA", "REGISTRO"), ("ARCHIVO", "EVIDENCIA"), ("DOCUMENTAL", "CRÓNICA")]

    raw_paras = [p.strip() for p in re.split(r"\n+", narration or "") if p.strip()]
    beats = []

    for p in raw_paras:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]
        for s in sents:
            w = s.split()
            if len(w) > 16:
                parts = [sub.strip() for sub in re.split(r";\s*|(?<=,)\s+(?=lo que|cuyo|cuya|donde|cuando|pero|quien|representó|midiendo|descubierto|alcanzando)", s) if sub.strip()]
                if len(parts) > 1:
                    beats.extend(parts)
                else:
                    beats.append(s)
            else:
                beats.append(s)

    merged = []
    for b in beats:
        if merged and len(b.split()) <= 4:
            merged[-1] = merged[-1] + " " + b
        else:
            merged.append(b)

    total_words = sum(max(1, len(b.split())) for b in merged)
    scenes = []
    cur_t = 0.0
    total_b = len(merged)

    for idx, b_text in enumerate(merged):
        w_cnt = max(1, len(b_text.split()))
        dur = (w_cnt / float(total_words)) * total_duration if idx < total_b - 1 else max(1.0, total_duration - cur_t)

        if total_b > 1 and idx == total_b - 1:
            st = "cierre_medallon"
        else:
            st = theme_rotation[idx % len(theme_rotation)]

        clean_sum = re.sub(r"^[¿¡]+", "", b_text).split(".")[0].split("?")[0].strip()
        if len(clean_sum) > 50:
            clean_sum = clean_sum[:47] + "..."

        m_year = re.search(r"\b(1[4-9]\d{2}|20[0-3]\d)\b", b_text)
        if m_year:
            b_num, b_lbl = m_year.group(1), "AÑO DOCUMENTADO"
        else:
            m_metric = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(km|metros|horas|huesos|ejemplares|años|grados|por ciento)", b_text, re.IGNORECASE)
            if m_metric:
                b_num, b_lbl = f"{m_metric.group(1)} {m_metric.group(2)[:4].upper()}", "REGISTRO CLAVE"
            else:
                b_num, b_lbl = defaults_badge[idx % len(defaults_badge)]

        scenes.append({
            "index": idx + 1,
            "total": total_b,
            "text": b_text,
            "summary": clean_sum.upper(),
            "t_start": cur_t,
            "t_end": cur_t + dur,
            "duration": dur,
            "scene_type": st,
            "badge_num": b_num,
            "badge_label": b_lbl,
            "location_name": loc_name,
            "years_list": years_list,
            "metrics_list": metrics_list,
            "detected_macro": macro,
        })
        cur_t += dur

    return scenes
