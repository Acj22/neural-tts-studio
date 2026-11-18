"""Refrigerador — circuito de compresión de vapor completo y cerrado (Fase 3.1, rehecho).

Circuito (un único lazo continuo de tubería con codos redondeados y zonas por color/estado):
  compresor -> línea de descarga (vapor caliente, alta presión) -> condensador (serpentín de 8 pasadas)
  -> línea de líquido -> filtro deshidratador -> tubo capilar helicoidal (dispositivo de expansión)
  -> subida interior -> evaporador (serpentín en el congelador) -> línea de succión -> compresor.

Partículas de refrigerante recorren cada zona (burbujas grandes = vapor, gotas pequeñas = líquido) y
cambian de color: rojo (vapor caliente) -> naranja (líquido) -> azul claro (mezcla fría) -> cian (vapor frío).
Flechas rojas expulsan calor del condensador; flechas naranja llevan el calor de los alimentos al evaporador.

Limitaciones declaradas: el condensador se muestra en un panel lateral (en un refrigerador real está
detrás o en las paredes); el tubo capilar sustituye a una válvula de expansión; sin ventilador ni
sistema de deshielo; la puerta se omite para mostrar el interior (corte frontal).
"""

from __future__ import annotations

import math
from typing import Any

try:
    import bpy
    from mathutils import Vector
except ImportError:  # pragma: no cover
    bpy = None
    Vector = None

from studio.blender.materials import setup_engine_materials, get_or_create_material, hex_to_rgba
from studio.blender.models_library import _common as C

SPEED = 0.85  # unidades/segundo del refrigerante


def _zone_mat(name: str, rgb, strength: float = 0.5, alpha: float = 1.0) -> Any:
    return C.emissive_material(name, rgb, strength, alpha)


def _serpentine(x0: float, x1: float, z_top: float, z_bot: float, rows: int, y: float, start_left: bool) -> list:
    pts = []
    zs = [z_top + (z_bot - z_top) * i / (rows - 1) for i in range(rows)]
    left = start_left
    for z in zs:
        a, b = (x0, x1) if left else (x1, x0)
        pts.append((a, y, z))
        pts.append((b, y, z))
        left = not left
    return pts


def create_refrigerator_cycle_3d(center_z: float = 2.2) -> dict[str, Any]:
    if bpy is None:
        return {}
    mats = setup_engine_materials()
    Z0 = center_z - 2.15
    Z = lambda z: Z0 + z  # noqa: E731
    data: dict[str, Any] = {"components": {}, "groups": {}, "meta": {"center_z": center_z}}
    G = data["groups"]

    def grp(name: str, *objs: Any) -> None:
        for o in objs:
            if o is None:
                continue
            G.setdefault(name, []).append(o)
            o["comp_group"] = name

    m_white = mats["white_cabinet"]
    m_foam = get_or_create_material("Mat_FoamInsulation", hex_to_rgba("#F5D66B"), roughness=0.9)
    m_liner = get_or_create_material("Mat_FridgeLiner", hex_to_rgba("#CBD5E1"), roughness=0.5)
    m_glass = get_or_create_material("Mat_GlassShelf", hex_to_rgba("#9ED8F0"), roughness=0.15, metallic=0.0, alpha=0.55)
    m_frost = mats["frost_blue"]
    white_txt = C.emissive_material("Mat_LabelWhite", (1, 1, 1), 2.2)

    # ------------------------------------------------------------------ GABINETE EN CORTE (3 capas visibles)
    def layered(name, axis, lo, hi, other_a, other_b, other_c, other_d, layers=(0.22, 0.56, 0.22), flip=False):
        """Pared de 3 capas (exterior blanca / espuma / interior). axis: 'x','y','z' = eje del espesor."""
        t = hi - lo
        cuts = [lo, lo + t * layers[0], lo + t * (layers[0] + layers[1]), hi]
        mlist = [m_white, m_foam, m_liner] if not flip else [m_liner, m_foam, m_white]
        out = []
        for i in range(3):
            a, b = cuts[i], cuts[i + 1]
            if axis == "x":
                size, ctr = (b - a, other_b - other_a, other_d - other_c), ((a + b) / 2, (other_a + other_b) / 2, (other_c + other_d) / 2)
            elif axis == "y":
                size, ctr = (other_b - other_a, b - a, other_d - other_c), ((other_a + other_b) / 2, (a + b) / 2, (other_c + other_d) / 2)
            else:
                size, ctr = (other_b - other_a, other_d - other_c, b - a), ((other_a + other_b) / 2, (other_c + other_d) / 2, (a + b) / 2)
            o = C.box(f"{name}_L{i+1}", size, ctr, mlist[i])
            out.append(o)
        grp("cabinet", *out)
        return out

    zb, zt = Z(0.68), Z(4.15)
    layered("Wall_Left", "x", -1.0, -0.82, -0.6, 0.6, zb, zt)
    layered("Wall_Right", "x", 0.82, 1.0, -0.6, 0.6, zb, zt, flip=True)
    layered("Wall_Back", "y", 0.42, 0.6, -1.0, 1.0, zb, zt, flip=True)
    layered("Wall_Top", "z", Z(3.97), zt, -1.0, 1.0, -0.6, 0.6, flip=True)
    layered("Wall_Bottom", "z", zb, Z(0.86), -1.0, 1.0, -0.6, 0.6)
    layered("Partition", "z", Z(2.75), Z(2.9), -0.82, 0.82, -0.6, 0.42, layers=(0.25, 0.5, 0.25))
    # panel de escarcha del congelador
    frost_back = C.box("Freezer_Frost_Panel", (1.64, 0.02, 1.07), (0, 0.41, Z(3.435)), m_frost)
    grp("cabinet", frost_back)

    # plinto (compartimento de máquinas) en corte
    plinth_floor = C.box("Plinth_Floor", (2.2, 1.3, 0.08), (0.0, 0.0, Z(0.04)), m_liner, bev=0.01)
    plinth_back = C.box("Plinth_Back", (2.2, 0.08, 0.68), (0.0, 0.66, Z(0.34)), m_white)
    plinth_left = C.box("Plinth_Left", (0.08, 1.3, 0.68), (-1.1, 0.0, Z(0.34)), m_white)
    grp("cabinet", plinth_floor, plinth_back, plinth_left)

    # estantes de cristal
    shelves = []
    for i, zr in enumerate((1.5, 2.15)):
        s = C.box(f"Glass_Shelf_{i+1}", (1.62, 1.0, 0.035), (0, -0.09, Z(zr)), m_glass)
        shelves.append(s)
    grp("food", *shelves)

    # alimentos estilizados
    food = []
    cols = {"green": "#2E9E4F", "red": "#D93A3A", "blue": "#3A7BD9", "white": "#F2F2F2", "yellow": "#F5C542",
            "orange": "#F28C28", "ice": "#BFE6FF"}
    fm = {k: get_or_create_material(f"Mat_Food_{k}", hex_to_rgba(v), roughness=0.45) for k, v in cols.items()}
    for i, x in enumerate((-0.62, -0.46, -0.30)):
        b = C.cylinder(f"Bottle_{i+1}", 0.075, 0.42, (x, -0.1, Z(0.86 + 0.21)), "Z", fm["green"], 20)
        n = C.cylinder(f"Bottle_Neck_{i+1}", 0.032, 0.16, (x, -0.1, Z(0.86 + 0.42 + 0.07)), "Z", fm["green"], 14)
        cp = C.cylinder(f"Bottle_Cap_{i+1}", 0.036, 0.03, (x, -0.1, Z(0.86 + 0.42 + 0.16)), "Z", fm["yellow"], 14)
        food += [b, n, cp]
    food.append(C.box("Milk_Carton", (0.2, 0.2, 0.36), (-0.02, -0.1, Z(0.86 + 0.18)), fm["blue"], bev=0.01))
    food.append(C.box("Cheese_Block", (0.26, 0.2, 0.14), (0.38, -0.1, Z(0.86 + 0.07)), fm["yellow"], bev=0.01))
    for i, x in enumerate((0.55, 0.68, 0.46)):
        food.append(C.sphere(f"Apple_{i+1}", 0.075, (x, -0.28 + 0.05 * i, Z(1.5 + 0.1)), fm["red"], 14))
    for i, x in enumerate((-0.5, -0.3, -0.1)):
        food.append(C.sphere(f"Tomato_{i+1}", 0.07, (x, -0.2, Z(2.15 + 0.095)), fm["red"], 14))
    food.append(C.box("Egg_Tray", (0.5, 0.22, 0.07), (0.45, -0.15, Z(2.15 + 0.06)), fm["white"], bev=0.01))
    for i in range(4):
        food.append(C.sphere(f"Egg_{i+1}", 0.045, (0.30 + 0.1 * i, -0.15, Z(2.15 + 0.13)), fm["white"], 10))
    food.append(C.box("Ice_Tray", (0.6, 0.35, 0.08), (-0.35, -0.1, Z(2.9 + 0.04)), fm["ice"], bev=0.01))
    food.append(C.box("Frozen_Bag", (0.38, 0.28, 0.1), (0.32, -0.1, Z(2.9 + 0.05)), fm["orange"], bev=0.02))
    grp("food", *food)

    # ------------------------------------------------------------------ COMPRESOR SECCIONADO
    comp_c = Vector((0.5, 0.25, Z(0.38)))
    comp_root = C.empty("Compressor_Root", tuple(comp_c))
    a0, a1 = math.radians(165), math.radians(375)
    shell_prof = [(0.30, -0.28), (0.30, 0.18), (0.285, 0.28), (0.22, 0.35), (0.12, 0.40), (0.05, 0.42)]
    shell = C.revolve("Compressor_Shell", shell_prof, a0, a1, 40, mats["compressor_black"], 0.03)
    shell.rotation_euler = (math.pi / 2, 0, 0)
    shell.parent = comp_root
    base = C.cylinder("Compressor_Base", 0.33, 0.04, (0, 0, -0.30), "Z", mats["compressor_black"], 32, parent=None)
    base.parent = comp_root
    stator = C.cylinder("Compressor_Stator_Windings", 0.19, 0.2, (0, 0, -0.04), "Z", mats["copper_coil"], 28)
    stator.parent = comp_root
    rotor_root = C.empty("Compressor_Rotor_Root", (0, 0, -0.04))
    rotor_root.parent = comp_root
    rotor = C.cylinder("Compressor_Rotor", 0.11, 0.22, (0, 0, 0), "Z", mats["cutaway_rim"], 24)
    rotor.parent = rotor_root
    rmark = C.box("Compressor_Rotor_Marker", (0.03, 0.03, 0.2), (0.1, 0, 0), mats["valve_exhaust"])
    rmark.parent = rotor_root
    cyl_block = C.cylinder("Compressor_Cylinder", 0.06, 0.30, (0.17, 0, -0.17), "X", mats["cylinder_liner"], 18)
    cyl_block.parent = comp_root
    piston = C.cylinder("Compressor_Piston", 0.052, 0.07, (0.17, 0, -0.17), "X", mats["piston"], 16)
    piston.parent = comp_root
    grp("compressor", shell, base, stator, rotor, rmark, cyl_block, piston)
    data["compressor_parts"] = {"root": comp_root, "rotor_root": rotor_root, "piston": piston,
                                "piston_base_x": 0.17, "base_loc": comp_c.copy()}

    # ------------------------------------------------------------------ CIRCUITO CERRADO
    # Zonas en orden de flujo: (nombre, puntos, rgb, spacing, radio de partícula, tipo)
    cond_x0, cond_x1 = 1.5, 2.6
    cond_rows = 8
    cond_ztop, cond_zbot = Z(3.72), Z(0.95)
    cond_pts = _serpentine(cond_x0, cond_x1, cond_ztop, cond_zbot, cond_rows, 0.10, True)
    # cond_pts: 16 puntos, fila i = pts[2i], pts[2i+1]; termina en el extremo izquierdo (x=1.5) de la fila 8
    half = cond_rows // 2  # 4 filas de vapor + 4 de líquido
    vap_pts = cond_pts[:2 * half]
    liq_pts = cond_pts[2 * half - 1:]  # parte del final de la fila 4 (x1) hasta el final

    ev_rows = 5
    ev_pts = _serpentine(-0.70, 0.70, Z(3.05), Z(3.81), ev_rows, 0.38, True)  # inicia izquierda, termina a la derecha

    discharge = [(0.80, 0.25, Z(0.40)), (1.22, 0.35, Z(0.50)), (1.22, 0.35, Z(3.72)), (1.50, 0.35, Z(3.72)), (cond_x0, 0.10, cond_ztop)]
    liquid = [(cond_x0, 0.10, cond_zbot), (cond_x0, -0.20, cond_zbot), (1.45, -0.20, Z(0.40)), (1.0, -0.20, Z(0.40))]
    capillary_start = (0.70, -0.20, Z(0.40))
    cap_helix = C.helix_path((0.70, -0.20, Z(0.40)), "X", -0.72, 0.085, 7, 14)  # de x=.70 a x=-.02
    riser = [(-0.02, -0.20, Z(0.40)), (-0.78, -0.20, Z(0.40)), (-0.78, 0.38, Z(0.40)), (-0.78, 0.38, ev_pts[0][2])]
    suction = [(0.70, 0.38, Z(3.81)), (0.78, 0.38, Z(3.81)), (0.78, 0.38, Z(0.78)), (0.62, 0.25, Z(0.68)), (0.62, 0.25, Z(0.64))]

    def P(lst, r):
        return C.rounded_polyline(lst, r, 7)

    zones = [
        # nombre, ruta, color, brillo, spacing, radio_partícula
        ("discharge", P(discharge, 0.14), (0.95, 0.12, 0.08), 0.8, 0.50, 0.062),
        ("cond_vapor", P([discharge[-1]] + vap_pts, 0.16), (0.98, 0.30, 0.10), 0.7, 0.48, 0.060),
        ("cond_liquid", P(liq_pts, 0.16), (1.0, 0.55, 0.10), 0.6, 0.30, 0.040),
        ("liquid_line", P(liquid, 0.14), (1.0, 0.62, 0.15), 0.5, 0.28, 0.040),
        ("capillary", cap_helix, (0.95, 0.75, 0.45), 0.5, 0.20, 0.030),
        ("riser", P(riser, 0.12), (0.55, 0.80, 1.0), 0.6, 0.32, 0.045),
        ("evaporator", P(ev_pts, 0.085), (0.25, 0.65, 1.0), 0.8, 0.40, 0.058),
        ("suction", P(suction, 0.12), (0.40, 0.95, 1.0), 0.7, 0.52, 0.060),
    ]
    tubes, zone_data = [], {}
    for name, path, rgb, strength, spacing, prad in zones:
        mat = _zone_mat(f"Mat_Zone_{name}", rgb, strength * 0.6)
        r = 0.016 if name == "capillary" else (0.045 if name in ("discharge", "suction") else 0.04)
        t = C.tube_from_path(f"Pipe_{name}", path, r, mat)
        tubes.append(t)
        zone_data[name] = {"path": path, "rgb": rgb, "spacing": spacing, "radius": prad,
                           "length": C.path_length(path)}
    grp("circuit", *tubes)
    grp("condenser", *[t for t in tubes if t.name in ("Pipe_cond_vapor", "Pipe_cond_liquid")])
    grp("evaporator", *[t for t in tubes if t.name == "Pipe_evaporator"])
    grp("capillary", *[t for t in tubes if t.name == "Pipe_capillary"])

    # juntas soldadas en los empalmes de zona
    welds = []
    for i in range(len(zones) - 1):
        a, b = zones[i][1][-1], zones[i + 1][1][0]
        w = C.sphere(f"Weld_{i+1}", 0.052, tuple((a + b) * 0.5), mats["brass_gold"], 10)
        welds.append(w)
    grp("circuit", *welds)

    # filtro deshidratador
    dryer = C.cylinder("Dryer_Filter", 0.075, 0.34, (1.17, -0.20, Z(0.40)), "X", mats["brass_gold"], 20)
    d_cap1 = C.cylinder("Dryer_Cap_A", 0.052, 0.05, (1.0, -0.2, Z(0.40)), "X", mats["brass_gold"], 14)
    d_cap2 = C.cylinder("Dryer_Cap_B", 0.052, 0.05, (1.36, -0.2, Z(0.40)), "X", mats["brass_gold"], 14)
    grp("dryer", dryer, d_cap1, d_cap2)

    # aletas / rejilla del condensador
    fins = []
    for i in range(12):
        x = cond_x0 + (cond_x1 - cond_x0) * i / 11
        f = C.box(f"Condenser_Fin_{i+1}", (0.018, 0.02, cond_ztop - cond_zbot + 0.2), (x, 0.17, (cond_ztop + cond_zbot) / 2), mats["cutaway_rim"])
        fins.append(f)
    grp("condenser", *fins)

    # pasacables en las paredes (el tubo atraviesa el aislamiento)
    grommets = []
    for (x, y, z) in ((-0.78, -0.0, Z(0.76)),):
        pass

    # ------------------------------------------------------------------ PARTÍCULAS DE REFRIGERANTE
    particles = []
    zone_particles: dict[str, list] = {}
    for name, zd in zone_data.items():
        L = zd["length"]
        n = max(2, int(round(L / zd["spacing"])))
        mat = _zone_mat(f"Mat_Part_{name}", zd["rgb"], 5.0)
        lst = []
        for i in range(n):
            s = C.sphere(f"Refrigerant_{name}_{i}", zd["radius"], tuple(zd["path"][0]), mat, 8)
            s["role"] = "fx"
            s["offset"] = i / n
            lst.append(s)
            particles.append(s)
        zone_particles[name] = lst
        zd["n"] = n
    grp("refrigerant", *particles)

    # ------------------------------------------------------------------ FLECHAS DE CALOR
    arrows_hot, arrows_cold = [], []
    red = C.emissive_material("Mat_HeatArrowRed", (1.0, 0.2, 0.1), 4.0)
    org = C.emissive_material("Mat_HeatArrowOrange", (1.0, 0.65, 0.1), 4.0)
    for i in range(5):
        a = C.make_arrow(f"HeatOut_{i+1}", 0.42, 0.018, red)
        a.location = (2.7, 0.1, Z(1.2 + i * 0.6))
        a["role"] = "fx"
        arrows_hot.append(a)
    for i in range(5):
        a = C.make_arrow(f"HeatIn_{i+1}", 0.34, 0.016, org)
        a.rotation_euler = (0, 0, math.pi / 2)  # apunta +Y (hacia el evaporador)
        a.location = (-0.55 + 0.275 * i, -0.45, Z(3.15 + (i % 3) * 0.28))
        a["role"] = "fx"
        arrows_cold.append(a)
    grp("heat_arrows", *arrows_hot, *arrows_cold)
    for a in arrows_hot + arrows_cold:
        for ch in a.children:
            ch["role"] = "fx"
            G["heat_arrows"].append(ch)

    # ------------------------------------------------------------------ ETIQUETAS
    labels = {}

    def label(key, txt, loc, target, size=0.26):
        t = C.make_text("Label_" + key, txt, loc, size, white_txt)
        p = C.rounded_polyline([(loc[0], loc[1], loc[2] - size * 0.7), target], 0.01)
        ln = C.tube_from_path("Leader_" + key, p, 0.012, white_txt)
        for o in (t, ln):
            o["role"] = "label"
        labels[key] = (t, ln)

    label("compressor", "COMPRESOR", (-1.15, -0.95, Z(-0.32)), (0.45, -0.05, Z(0.5)))
    label("condenser", "CONDENSADOR", (2.1, -0.6, Z(4.35)), (2.0, 0.1, cond_ztop + 0.05))
    label("expansion", "TUBO CAPILAR", (0.20, -0.95, Z(-0.68)), (0.35, -0.2, Z(0.32)))
    label("evaporator", "EVAPORADOR", (-1.9, -0.6, Z(4.45)), (-0.7, 0.38, Z(3.78)))
    label("dryer", "FILTRO", (1.65, -0.95, Z(-0.32)), (1.17, -0.2, Z(0.30)))
    ptxt = {
        "high": C.make_text("Txt_HighPressure", "ALTA PRESIÓN · CALIENTE", (1.75, -0.7, Z(-0.05)), 0.2,
                            C.emissive_material("Mat_TxtRed", (1.0, 0.25, 0.15), 3.0)),
        "low": C.make_text("Txt_LowPressure", "BAJA PRESIÓN · FRÍO", (0.0, -0.7, Z(4.55)), 0.2,
                           C.emissive_material("Mat_TxtBlue", (0.35, 0.75, 1.0), 3.0)),
        "drop": C.make_text("Txt_PressureDrop", "¡LA PRESIÓN CAE!", (0.35, -0.7, Z(-0.0)), 0.22,
                            C.emissive_material("Mat_TxtYellow", (1.0, 0.85, 0.1), 3.0)),
    }
    for t in ptxt.values():
        t["role"] = "label"
    grp("labels", *[o for (t, ln) in labels.values() for o in (t, ln)], *ptxt.values())

    data["components"] = {
        "cabinet": G["cabinet"], "compressor": G["compressor"], "condenser": G["condenser"],
        "dryer_filter": G["dryer"], "capillary_tube": G["capillary"], "evaporator": G["evaporator"],
        "suction_line": [t for t in tubes if t.name == "Pipe_suction"],
        "discharge_line": [t for t in tubes if t.name == "Pipe_discharge"],
        "liquid_line": [t for t in tubes if t.name == "Pipe_liquid_line"],
        "refrigerant_particles": particles, "food": G["food"],
    }
    data["zones"] = zone_data
    data["zone_particles"] = zone_particles
    data["labels"] = labels
    data["ptxt"] = ptxt
    data["arrows_hot"] = arrows_hot
    data["arrows_cold"] = arrows_cold
    # conexiones: extremos de cada zona deben tocar el siguiente (circuito sin cortes)
    conns = []
    pipes = {t.name: t for t in tubes}
    order = [z[0] for z in zones]
    for i in range(len(order) - 1):
        conns.append((pipes["Pipe_" + order[i]], pipes["Pipe_" + order[i + 1]], 0.06, f"{order[i]} ↔ {order[i+1]}"))
    conns.append((pipes["Pipe_suction"], shell, 0.12, "succión ↔ compresor"))
    conns.append((pipes["Pipe_discharge"], shell, 0.12, "descarga ↔ compresor"))
    conns.append((dryer, pipes["Pipe_liquid_line"], 0.06, "filtro ↔ línea de líquido"))
    data["connections"] = conns
    data["explode_groups"] = {}
    return data


# =============================================================================
# ANIMACIÓN
# =============================================================================

def _vis(o: Any, v: bool) -> None:
    o.hide_render = not v
    o.hide_viewport = not v


def _vis_key(o: Any, v: bool, f: int) -> None:
    _vis(o, v)
    o.keyframe_insert(data_path="hide_render", frame=f)
    o.keyframe_insert(data_path="hide_viewport", frame=f)


def _flow(d: dict[str, Any], f0: int, f1: int, speed_mul: float = 1.0, zones: list[str] | None = None) -> None:
    fps = bpy.context.scene.render.fps
    step = SPEED * speed_mul / fps
    for name, zd in d["zones"].items():
        if zones and name not in zones:
            continue
        L = zd["length"]
        path = zd["path"]
        for s in d["zone_particles"][name]:
            for f in range(f0, f1 + 1):
                frac = (s["offset"] + (f - f0) * step / L) % 1.0
                s.location = C.path_point(path, frac)
                s.keyframe_insert(data_path="location", frame=f)


def _arrows(d: dict[str, Any], f0: int, f1: int, show_hot: bool = True, show_cold: bool = True) -> None:
    fps = bpy.context.scene.render.fps
    loop = int(fps * 1.6)
    for i, a in enumerate(d["arrows_hot"]):
        base = a.location.copy()
        _vis(a, show_hot)
        for ch in a.children:
            _vis(ch, show_hot)
        if not show_hot:
            continue
        for f in range(f0, f1 + 1):
            ph = (((f - f0) / loop) + i * 0.2) % 1.0
            a.location = (base.x + ph * 0.75, base.y, base.z)
            a.scale = (0.5 + 0.8 * min(1.0, ph * 2) * (1 - max(0, ph - 0.7) / 0.3), 1, 1)
            a.keyframe_insert(data_path="location", frame=f)
            a.keyframe_insert(data_path="scale", frame=f)
    for i, a in enumerate(d["arrows_cold"]):
        base = a.location.copy()
        _vis(a, show_cold)
        for ch in a.children:
            _vis(ch, show_cold)
        if not show_cold:
            continue
        for f in range(f0, f1 + 1):
            ph = (((f - f0) / loop) + i * 0.17) % 1.0
            a.location = (base.x, base.y + ph * 0.75, base.z)
            s = 0.5 + 0.8 * min(1.0, ph * 2) * (1 - max(0, ph - 0.7) / 0.3)
            a.scale = (s, 1, 1)
            a.keyframe_insert(data_path="location", frame=f)
            a.keyframe_insert(data_path="scale", frame=f)


def _compressor(d: dict[str, Any], f0: int, f1: int, intensity: float = 1.0) -> None:
    cp = d["compressor_parts"]
    fps = bpy.context.scene.render.fps
    rev_per_s = 1.1 * intensity
    base = cp["base_loc"]
    rr = cp["rotor_root"]
    pis = cp["piston"]
    for f in range(f0, f1 + 1):
        t = (f - f0) / fps
        ang = 2 * math.pi * rev_per_s * t
        rr.rotation_euler = (0, 0, ang)
        rr.keyframe_insert(data_path="rotation_euler", frame=f)
        pis.location = (cp["piston_base_x"] + 0.07 * math.cos(ang), 0, -0.17)
        pis.keyframe_insert(data_path="location", frame=f)
        cp["root"].location = (base.x, base.y, base.z + 0.006 * math.sin(ang * 3.0) * intensity)
        cp["root"].keyframe_insert(data_path="location", frame=f)


def _hide_extras(d: dict[str, Any]) -> None:
    for t, ln in d["labels"].values():
        _vis(t, False)
        _vis(ln, False)
    for t in d["ptxt"].values():
        _vis(t, False)


def _show_label(d: dict[str, Any], key: str, f_on: int | None = None) -> None:
    t, ln = d["labels"][key]
    if f_on is None:
        _vis(t, True)
        _vis(ln, True)
    else:
        for o in (t, ln):
            _vis_key(o, False, 1)
            _vis_key(o, True, f_on)


def _pulse(objs: list, f0: int, f1: int, amp: float = 0.08) -> None:
    for o in objs:
        s0 = o.scale.copy()
        o.keyframe_insert(data_path="scale", frame=f0)
        o.scale = s0 * (1 + amp)
        o.keyframe_insert(data_path="scale", frame=(f0 + f1) // 2)
        o.scale = s0
        o.keyframe_insert(data_path="scale", frame=f1)


def build_refrigerator_keyframes(
    fridge_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    scene_phase: str = "overview",
    highlight_component: str | None = None,
) -> None:
    if bpy is None:
        return
    C.set_interp("LINEAR")
    d = fridge_data
    G = d["groups"]
    f0, f1 = start_frame, max(start_frame + 8, end_frame)
    total = f1 - f0
    _hide_extras(d)
    d["meta"]["phase_applied"] = scene_phase

    if scene_phase in ("components", "components_identify"):
        _flow(d, f0, f1, 0.6)
        _compressor(d, f0, f1, 0.5)
        _arrows(d, f0, f1, True, True)
        seq = [("compressor", "compressor"), ("condenser", "condenser"), ("dryer", "dryer"),
               ("expansion", "capillary"), ("evaporator", "evaporator")]
        seg = total // (len(seq) + 1)
        for i, (lk, gk) in enumerate(seq):
            t_on = f0 + seg * i
            _show_label(d, lk, t_on if i > 0 else None)
            _pulse(G.get(gk, []), t_on, min(f1, t_on + seg), 0.07)
    elif scene_phase == "compressor":
        _flow(d, f0, f1, 1.0, ["discharge", "suction", "cond_vapor", "evaporator"])
        _compressor(d, f0, f1, 1.0)
        _show_label(d, "compressor")
        _vis(d["ptxt"]["high"], True)
        _arrows(d, f0, f1, False, False)
    elif scene_phase == "condenser":
        _flow(d, f0, f1, 1.0, ["discharge", "cond_vapor", "cond_liquid", "liquid_line"])
        _compressor(d, f0, f1, 0.6)
        _arrows(d, f0, f1, True, False)
        _show_label(d, "condenser")
        _vis(d["ptxt"]["high"], True)
    elif scene_phase in ("expansion", "expansion_valve"):
        _flow(d, f0, f1, 0.8, ["liquid_line", "capillary", "riser", "cond_liquid"])
        _compressor(d, f0, f1, 0.4)
        _arrows(d, f0, f1, False, False)
        _show_label(d, "expansion")
        _show_label(d, "dryer")
        _vis(d["ptxt"]["drop"], True)
    elif scene_phase == "evaporator":
        _flow(d, f0, f1, 0.9, ["riser", "evaporator", "suction"])
        _compressor(d, f0, f1, 0.4)
        _arrows(d, f0, f1, False, True)
        _show_label(d, "evaporator")
        _vis(d["ptxt"]["low"], True)
    elif scene_phase in ("heat_balance", "comparison"):
        _flow(d, f0, f1, 0.9)
        _compressor(d, f0, f1, 0.8)
        _arrows(d, f0, f1, True, True)
        _vis(d["ptxt"]["high"], True)
        _vis(d["ptxt"]["low"], True)
    else:  # overview / conclusion
        _flow(d, f0, f1, 1.0)
        _compressor(d, f0, f1, 0.8)
        _arrows(d, f0, f1, True, True)
