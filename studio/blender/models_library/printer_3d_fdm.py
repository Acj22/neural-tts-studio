"""Impresora 3D FDM cartesiana — modelo explicativo completo (Fase 3.1, rehecho).

Estructura: marco y columnas de perfil de aluminio V-Slot RANURADO (ranura en T real), husillos Z con
motor NEMA 17 y tuerca de latón, riel X con carro de ruedas y correa GT2 dentada, cama que se desliza
en Y sobre rieles (correa GT2 + motor), cama de aluminio con lámina PEI y 4 resortes de nivelación,
extrusor directo (motor + engranaje de arrastre + filamento desde el carrete), hotend (disipador con
aletas, heat-break, bloque calefactor, boquilla de latón) y ventilador de capa con tobera.

Cinemática correcta: la cabeza se mueve en X y Z; la cama en Y. Para dibujar un círculo la boquilla
recorre x = R·cosθ mientras la cama se desplaza y = -R·senθ (movimiento relativo exacto).
La pieza (vaso en modo espiral) se deposita en 16 segmentos por vuelta que aparecen cuando la
boquilla pasa sobre ellos (deposición real, no un cilindro que crece).

Limitaciones declaradas: sin cableado, sin pantalla ni fuente; correa Y/X en tramo único; perfil V-Slot
simplificado sin agujero central; carrete en soporte superior (no en el lateral).
"""

from __future__ import annotations

import math
from typing import Any

try:
    import bpy
    import bmesh
    from mathutils import Vector
except ImportError:  # pragma: no cover
    bpy = None
    bmesh = None
    Vector = None

from studio.blender.materials import setup_engine_materials, get_or_create_material, hex_to_rgba
from studio.blender.models_library import _common as C

LAYERS = 22
SEGS = 16
LAYER_H = 0.055
BED_TOP = 0.95
NOZZLE_DZ = 0.55            # z del riel X menos z de la punta de la boquilla
Y_NOZ = 0.62                # y de la boquilla (fija en el mundo)
ZG0 = BED_TOP + 0.03 + NOZZLE_DZ


def _vslot_profile(h: float = 0.1) -> list[tuple[float, float]]:
    """Contorno del perfil 2020 con ranura en T en cada cara (sin agujero central)."""
    w, t, c, e = 0.045, 0.022, 0.13, 0.05
    base = [(-h, h), (-w / 2, h), (-w / 2, h - t), (-c / 2, h - t), (-c / 2, h - t - e),
            (c / 2, h - t - e), (c / 2, h - t), (w / 2, h - t), (w / 2, h)]
    pts: list[tuple[float, float]] = []
    for k in range(4):
        a = -k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        for (x, z) in base:
            pts.append((x * ca - z * sa, x * sa + z * ca))
    # cierre de esquina (cada lado empieza en la esquina anterior)
    return pts


def _vslot(name: str, length: float, axis: str, center, mat: Any, h: float = 0.1) -> Any:
    prof = _vslot_profile(h)
    n = len(prof)
    verts = [(x, -length / 2, z) for (x, z) in prof] + [(x, length / 2, z) for (x, z) in prof]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    o = C.mesh_object(name, verts, faces, mat, flat=True)
    if axis == "X":
        o.rotation_euler = (0, 0, math.pi / 2)
    elif axis == "Z":
        o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = tuple(center)
    return o


def _arc_prism(name: str, rin: float, rout: float, z0: float, z1: float, a0: float, a1: float, steps: int, mat: Any) -> Any:
    verts, faces = [], []
    for s in range(steps + 1):
        a = a0 + (a1 - a0) * s / steps
        ca, sa = math.cos(a), math.sin(a)
        verts += [(rin * ca, rin * sa, z0), (rout * ca, rout * sa, z0), (rout * ca, rout * sa, z1), (rin * ca, rin * sa, z1)]
    for s in range(steps):
        b, nb = s * 4, (s + 1) * 4
        faces += [(b + 0, b + 1, nb + 1, nb + 0), (b + 1, b + 2, nb + 2, nb + 1),
                  (b + 2, b + 3, nb + 3, nb + 2), (b + 3, b + 0, nb + 0, nb + 3)]
    faces.append((0, 3, 2, 1))
    last = steps * 4
    faces.append((last, last + 1, last + 2, last + 3))
    return C.mesh_object(name, verts, faces, mat, flat=True)


def _nema(name: str, center, axis: str, mat_body: Any, mat_shaft: Any, parent: Any = None) -> list:
    """Motor NEMA 17 (cuerpo 0.42x0.42x0.46) con eje que sale hacia +axis."""
    cx, cy, cz = center
    sz = {"X": (0.46, 0.42, 0.42), "Y": (0.42, 0.46, 0.42), "Z": (0.42, 0.42, 0.46)}[axis]
    body = C.box(name + "_Body", sz, center, mat_body, bev=0.012)
    off = {"X": (0.23 + 0.12, 0, 0), "Y": (0, 0.23 + 0.12, 0), "Z": (0, 0, 0.23 + 0.12)}[axis]
    sh = C.cylinder(name + "_Shaft", 0.026, 0.25, (cx + off[0], cy + off[1], cz + off[2]), axis, mat_shaft, 12)
    flange = C.cylinder(name + "_Boss", 0.1, 0.03, (cx + off[0] * 0.55, cy + off[1] * 0.55, cz + off[2] * 0.55), axis, mat_shaft, 20)
    out = [body, sh, flange]
    if parent is not None:
        for o in out:
            C.keep_parent(o, parent)
    return out


def _belt(name: str, size, center, mat: Any, tooth_axis: str, n_teeth: int, mat_teeth: Any) -> list:
    b = C.box(name, size, center, mat)
    objs = [b]
    # dientes GT2: un cubo con modificador Array
    L = {"X": size[0], "Y": size[1], "Z": size[2]}[tooth_axis]
    step = L / n_teeth
    tsz = {"X": (step * 0.5, size[1] * 1.4, size[2] * 1.4), "Y": (size[0] * 1.4, step * 0.5, size[2] * 1.4),
           "Z": (size[0] * 1.4, size[1] * 1.4, step * 0.5)}[tooth_axis]
    start = {"X": (center[0] - L / 2 + step / 2, center[1], center[2]),
             "Y": (center[0], center[1] - L / 2 + step / 2, center[2]),
             "Z": (center[0], center[1], center[2] - L / 2 + step / 2)}[tooth_axis]
    t = C.box(name + "_Teeth", tsz, start, mat_teeth)
    m = t.modifiers.new("Array", type="ARRAY")
    m.count = n_teeth
    m.use_relative_offset = False
    m.use_constant_offset = True
    m.constant_offset_displace = {"X": (step, 0, 0), "Y": (0, step, 0), "Z": (0, 0, step)}[tooth_axis]
    objs.append(t)
    return objs


def create_printer_3d_3d(center_z: float = 2.0) -> dict[str, Any]:
    if bpy is None:
        return {}
    mats = setup_engine_materials()
    data: dict[str, Any] = {"components": {}, "groups": {}, "meta": {"center_z": center_z}}
    G = data["groups"]

    def grp(name: str, *objs: Any) -> None:
        for o in objs:
            if o is not None:
                G.setdefault(name, []).append(o)
                o["comp_group"] = name

    vs = mats["vslot_black"]
    steel = mats["cutaway_rim"]
    brass = mats["brass_gold"]
    black = mats["compressor_black"]
    alu = mats["engine_block"]
    belt_m = get_or_create_material("Mat_BeltGT2", hex_to_rgba("#15181C"), roughness=0.6)
    belt_t = get_or_create_material("Mat_BeltTeeth", hex_to_rgba("#2B3038"), roughness=0.6)
    white_txt = C.emissive_material("Mat_LabelWhite", (1, 1, 1), 2.2)
    heat = C.emissive_material("Mat_HotBlock", (1.0, 0.32, 0.08), 2.4)
    glow = C.emissive_material("Mat_MoltenBead", (1.0, 0.62, 0.12), 8.0)
    fan_m = get_or_create_material("Mat_FanBlue", hex_to_rgba("#2563EB"), roughness=0.4)
    pla = mats["filament_orange"]

    # ------------------------------------------------------------------ MARCO (perfil V-Slot ranurado)
    frame = []
    for y in (-0.6, 1.8):
        frame.append(_vslot(f"Base_Cross_{'F' if y < 0 else 'B'}", 3.4, "X", (0, y, 0.1), vs))
    for x in (-1.5, 1.5):
        frame.append(_vslot(f"Base_Side_{'L' if x < 0 else 'R'}", 2.2, "Y", (x, 0.6, 0.1), vs))
    for x in (-0.85, 0.85):
        frame.append(_vslot(f"Y_Rail_{'L' if x < 0 else 'R'}", 2.4, "Y", (x, 0.6, 0.3), vs))
    posts = []
    for x in (-1.5, 1.5):
        p = _vslot(f"Z_Post_{'L' if x < 0 else 'R'}", 4.0, "Z", (x, 1.0, 2.2), vs)
        posts.append(p)
    top_bar = _vslot("Top_Crossbar", 2.8, "X", (0, 1.0, 4.1), vs)
    grp("frame", *frame, *posts, top_bar)
    foot = []
    for x in (-1.5, 1.5):
        for y in (-0.6, 1.8):
            foot.append(C.cylinder(f"Rubber_Foot_{x}_{y}", 0.09, 0.06, (x, y, -0.03), "Z", belt_m, 16))
    grp("frame", *foot)

    # ------------------------------------------------------------------ EJES Z: husillos + motores + tuercas
    z_parts = []
    z_motor_list = []
    screws = []
    for x in (-1.2, 1.2):
        mot = _nema(f"Z_Motor_{'L' if x < 0 else 'R'}", (x, 1.8, 0.2 + 0.23), "Z", black, steel)
        z_motor_list += mot
        sc = C.cylinder(f"Leadscrew_Z_{'L' if x < 0 else 'R'}", 0.045, 3.2, (x, 1.8, 0.2 + 0.46 + 0.1 + 1.6), "Z", steel, 12)
        screws.append(sc)
        z_parts.append(sc)
        # roscado visual: anillos finos
        for k in range(26):
            ring = C.cylinder(f"Thread_{x}_{k}", 0.058, 0.014, (x, 1.8, 0.9 + k * 0.12), "Z", steel, 12, flat=True)
            z_parts.append(ring)
    grp("z_axis", *z_motor_list, *z_parts)
    # carril lineal vertical en las columnas
    for x in (-1.5, 1.5):
        grp("z_axis", C.cylinder(f"Z_Smooth_Rod_{x}", 0.03, 3.6, (x, 0.86, 2.2), "Z", steel, 10))

    # ------------------------------------------------------------------ PÓRTICO X (se mueve en Z)
    gantry_root = C.empty("Gantry_Root", (0, 0, ZG0))
    rail_x = _vslot("X_Rail", 2.7, "X", (0, 1.0, 0), vs)
    rail_x.parent = gantry_root
    nuts = []
    arms = []
    for x in (-1.2, 1.2):
        arm = C.box(f"Z_Nut_Arm_{x}", (0.14, 0.78, 0.14), (x, 1.41, 0), alu, bev=0.01)
        nut = C.cylinder(f"Z_Brass_Nut_{x}", 0.09, 0.2, (x, 1.8, 0), "Z", brass, 16)
        arms.append(arm)
        nuts.append(nut)
        arm.parent = gantry_root
        nut.parent = gantry_root
    xmotor = _nema("X_Motor", (-1.9, 1.0, 0), "X", black, steel)
    # el eje del motor mira hacia +X: giramos ubicación del eje invirtiendo
    for o in xmotor:
        o.parent = gantry_root
    # ruedas del carro de pórtico en columna (placas con ruedas)
    plates = []
    for x in (-1.5, 1.5):
        pl = C.box(f"Z_Carriage_Plate_{x}", (0.24, 0.1, 0.5), (x, 0.84, 0), alu, bev=0.01)
        pl.parent = gantry_root
        plates.append(pl)
    # correa X (GT2)
    belt_x = _belt("X_Belt", (3.5, 0.016, 0.05), (-0.1, 0.88, 0.0), belt_m, "X", 90, belt_t)
    for o in belt_x:
        o.parent = gantry_root
    pul_x = C.cylinder("X_Pulley_Motor", 0.07, 0.07, (-1.9, 0.88, 0), "Y", steel, 16)
    pul_x.parent = gantry_root
    idler_x = C.cylinder("X_Idler", 0.07, 0.05, (1.68, 0.88, 0), "Y", steel, 16)
    idler_x.parent = gantry_root
    grp("x_axis", rail_x, *arms, *nuts, *xmotor, *plates, *belt_x, pul_x, idler_x)

    # ------------------------------------------------------------------ CARRO + EXTRUSOR + HOTEND
    carriage = C.empty("Carriage_Root", (0, 0, 0))
    carriage.parent = gantry_root
    tip_dz = -NOZZLE_DZ  # z local de la punta
    # placa y ruedas (sobre el riel X)
    cplate = C.box("Carriage_Plate", (0.62, 0.06, 1.25), (0, 0.87, tip_dz + 0.85), alu, bev=0.012)
    wheels = []
    for dx in (-0.2, 0.2):
        for dz in (-0.09, 0.09):
            wheels.append(C.cylinder(f"Carriage_Wheel_{dx}_{dz}", 0.065, 0.04, (dx, 0.9, dz), "Y", belt_m, 20))
    cmount = C.box("Hotend_Mount", (0.3, 0.16, 0.6), (0, 0.76, tip_dz + 0.62), alu, bev=0.01)
    # hotend: disipador con aletas
    fins = []
    for k in range(9):
        fins.append(C.cylinder(f"Heatsink_Fin_{k}", 0.165, 0.016, (0, Y_NOZ, tip_dz + 0.62 + k * 0.045), "Z", steel, 24))
    hs_core = C.cylinder("Heatsink_Core", 0.07, 0.42, (0, Y_NOZ, tip_dz + 0.8), "Z", steel, 16)
    heatbreak = C.cylinder("Heat_Break", 0.04, 0.14, (0, Y_NOZ, tip_dz + 0.52), "Z", steel, 12)
    heatblock = C.box("Heater_Block", (0.22, 0.22, 0.2), (0, Y_NOZ, tip_dz + 0.37), heat, bev=0.01)
    nozzle = C.cylinder("Brass_Nozzle", 0.075, 0.2, (0, Y_NOZ, tip_dz + 0.15), "Z", brass, 20, r2=0.012)
    nozzle.rotation_euler = (math.pi, 0, 0)  # base ancha arriba, punta abajo
    nozzle_hex = C.cylinder("Nozzle_Hex", 0.06, 0.07, (0, Y_NOZ, tip_dz + 0.27), "Z", brass, 6)
    # ventilador de capa + tobera
    fan = C.box("Layer_Fan", (0.34, 0.12, 0.34), (-0.36, Y_NOZ - 0.04, tip_dz + 0.55), fan_m, bev=0.01)
    fan_hub = C.cylinder("Layer_Fan_Hub", 0.07, 0.03, (-0.36, Y_NOZ - 0.11, tip_dz + 0.55), "Y", black, 16)
    duct = C.cylinder("Fan_Duct", 0.07, 0.34, (-0.2, Y_NOZ - 0.04, tip_dz + 0.28), "X", fan_m, 14, r2=0.04)
    duct.rotation_euler = (0, -math.pi / 2 * 0.0 + math.radians(90 + 25), 0)
    # extrusor (motor + engranaje de arrastre)
    emotor = _nema("Extruder_Motor", (0.42, 0.66, tip_dz + 1.18), "X", black, steel)
    # el eje del extrusor debe apuntar hacia -X: reposicionar eje/boss
    for o in emotor:
        if o.name.endswith("_Shaft"):
            o.location = (0.42 - 0.35, 0.66, tip_dz + 1.18)
        if o.name.endswith("_Boss"):
            o.location = (0.42 - 0.19, 0.66, tip_dz + 1.18)
    drive_gear = C.make_gear("Extruder_Drive_Gear", 14, 0.085, 0.014, 0.05, (0, 0, 0), brass)
    drive_gear.rotation_euler = (0, 0, math.pi / 2)  # eje del engranaje -> X
    drive_gear.location = (0.0, Y_NOZ + 0.1, tip_dz + 1.18)
    idler = C.cylinder("Extruder_Idler", 0.05, 0.04, (0.0, Y_NOZ - 0.09, tip_dz + 1.18), "X", steel, 16)
    ext_parts = [cplate, *wheels, cmount, *fins, hs_core, heatbreak, heatblock, nozzle, nozzle_hex, fan, fan_hub, duct,
                 *emotor, drive_gear, idler]
    for o in ext_parts:
        o.parent = carriage
    # el parent de carriage está en gantry_root (que se mueve en z); las partes creadas con coordenadas
    # globales relativas (z local) ya quedan en el frame correcto porque gantry_root.z se aplicó:
    grp("extruder", cplate, *wheels, cmount, *emotor, drive_gear, idler)
    grp("hotend", *fins, hs_core, heatbreak, heatblock, nozzle_hex, fan, fan_hub, duct)
    grp("nozzle", nozzle)

    # ------------------------------------------------------------------ FILAMENTO + CARRETE
    spool_root = C.empty("Spool_Root", (0, 0.85, 4.75))
    spool_core = C.cylinder("Spool_Wound", 0.5, 0.36, (0, 0, 0), "Y", pla, 40)
    spool_f1 = C.cylinder("Spool_Flange_Front", 0.74, 0.03, (0, -0.2, 0), "Y", get_or_create_material("Mat_SpoolFlange", hex_to_rgba("#E2E8F0"), 0.5, 0.0, 0.55), 40)
    spool_f2 = C.cylinder("Spool_Flange_Back", 0.74, 0.03, (0, 0.2, 0), "Y", get_or_create_material("Mat_SpoolFlange", hex_to_rgba("#E2E8F0"), 0.5, 0.0, 0.55), 40)
    spool_hub = C.cylinder("Spool_Hub", 0.14, 0.44, (0, 0, 0), "Y", belt_m, 20)
    spool_mark = C.box("Spool_Marker", (0.06, 0.4, 0.2), (0, 0, 0.58), brass)
    for o in (spool_core, spool_f1, spool_f2, spool_hub, spool_mark):
        o.parent = spool_root
    holder = C.box("Spool_Holder", (0.16, 0.9, 0.16), (0, 1.12, 4.75), vs, bev=0.01)
    holder_post = C.box("Spool_Holder_Post", (0.16, 0.16, 0.7), (0, 1.12, 4.35), vs, bev=0.01)
    grp("filament_spool", spool_core, spool_f1, spool_f2, spool_hub, spool_mark, holder, holder_post)
    fil = C.cylinder("Filament_Line", 0.03, 1.0, (0, 0, 0), "Z", pla, 10)
    fil.parent = None
    rings = []
    ring_mat = C.emissive_material("Mat_FilRing", (1.0, 1.0, 1.0), 1.0)
    for k in range(5):
        r = C.cylinder(f"Filament_Marker_{k}", 0.042, 0.03, (0, 0, 0), "Z", ring_mat, 12)
        r["role"] = "fx"
        rings.append(r)
    grp("filament_spool", fil, *rings)

    # ------------------------------------------------------------------ CAMA (se mueve en Y)
    bed_root = C.empty("Bed_Root", (0, Y_NOZ, 0))
    bed_parts = []
    bplate = C.box("Bed_Carriage_Plate", (1.9, 1.9, 0.05), (0, 0, 0.5), alu, bev=0.01)
    bed_parts.append(bplate)
    for x in (-0.85, 0.85):
        for y in (-0.7, 0.7):
            w = C.cylinder(f"Y_Wheel_{x}_{y}", 0.065, 0.06, (x, y, 0.455), "X", belt_m, 20)
            br = C.box(f"Y_Wheel_Bracket_{x}_{y}", (0.07, 0.12, 0.09), (x, y, 0.5), alu)
            bed_parts += [w, br]
    spr, knobs = [], []
    for x in (-0.78, 0.78):
        for y in (-0.78, 0.78):
            hx = C.helix_path((x, y, 0.53), "Z", 0.3, 0.065, 5.5, 12)
            s = C.tube_from_path(f"Bed_Spring_{x}_{y}", hx, 0.013, steel)
            s.location = (0, 0, 0)
            kn = C.cylinder(f"Bed_Knob_{x}_{y}", 0.09, 0.05, (x, y, 0.5 - 0.04), "Z", fan_m, 14)
            spr.append(s)
            knobs.append(kn)
    bed_al = C.box("Heated_Bed_Aluminum", (1.9, 1.9, 0.07), (0, 0, 0.86 - 0.0 + 0.035 - 0.035 + 0.0), alu, bev=0.01)
    bed_al.location.z = 0.895 - 0.03
    pei = C.box("PEI_Print_Sheet", (1.82, 1.82, 0.02), (0, 0, 0.94), mats["pei_bed"], bev=0.005)
    bed_parts += [bed_al, pei, *spr, *knobs]
    # abrazadera de correa Y
    clamp = C.box("Y_Belt_Clamp", (0.16, 0.2, 0.08), (-0.3, 0, 0.42), alu)
    ybelt = _belt("Y_Belt", (0.018, 2.5, 0.05), (-0.3, 0.0, 0.34), belt_m, "Y", 100, belt_t)
    bed_parts += [clamp]
    for o in bed_parts:
        o.parent = bed_root
    # NOTA: partes de la cama creadas en coords globales con y local; bed_root en y=Y_NOZ: ajustar
    grp("bed", *bed_parts)
    # correa y motor Y son estáticos (no cuelgan de la cama)
    for o in ybelt:
        o.location.y += Y_NOZ
    ymotor = _nema("Y_Motor", (-0.3, -0.62, 0.34), "Y", black, steel)
    ymotor[1].location.y = -0.62 - 0.35
    ymotor[2].location.y = -0.62 - 0.19
    ypulley = C.cylinder("Y_Pulley", 0.07, 0.07, (-0.3, -0.62, 0.34), "X", steel, 16)
    yidler = C.cylinder("Y_Idler", 0.07, 0.05, (-0.3, 1.85, 0.34), "X", steel, 16)
    grp("y_axis_bed", *ybelt, *ymotor, ypulley, yidler, *[o for o in G.get("bed", []) if o.name.startswith("Y_Wheel")])

    # ------------------------------------------------------------------ PIEZA IMPRESA (vaso en modo espiral)
    seg_objs: list[list[Any]] = []
    for k in range(LAYERS):
        zc0 = BED_TOP + k * LAYER_H
        row = []
        for j in range(SEGS):
            frac_z = k / (LAYERS - 1)
            r_out = 0.36 + 0.10 * math.sin(frac_z * math.pi * 1.4 + 0.3)
            a0 = 2 * math.pi * j / SEGS
            a1 = 2 * math.pi * (j + 1) / SEGS
            sgm = _arc_prism(f"Part_L{k}_S{j}", r_out - 0.035, r_out, zc0, zc0 + LAYER_H, a0, a1, 3, pla)
            sgm.parent = bed_root
            sgm["layer"] = k
            sgm["seg"] = j
            row.append(sgm)
        seg_objs.append(row)
    flat = [o for row in seg_objs for o in row]
    grp("printed_part", *flat)
    bead = C.sphere("Molten_Bead", 0.045, (0, Y_NOZ, BED_TOP + 0.05), glow, 10)
    bead["role"] = "fx"
    grp("nozzle", bead)

    # ------------------------------------------------------------------ INDICADORES DE EJES Y ETIQUETAS
    ax_mats = {"X": C.emissive_material("Mat_AxisX", (1.0, 0.15, 0.15), 4.0),
               "Y": C.emissive_material("Mat_AxisY", (0.2, 1.0, 0.3), 4.0),
               "Z": C.emissive_material("Mat_AxisZ", (0.25, 0.55, 1.0), 4.0)}
    ax = {}
    ax["X"] = C.make_arrow("Axis_X", 0.9, 0.025, ax_mats["X"])
    ax["X"].parent = carriage
    ax["X"].location = (-0.3, 0.1, tip_dz + 1.75)
    tx = C.make_text("Axis_X_Text", "X", (1.0, 0.1, tip_dz + 1.75), 0.3, ax_mats["X"])
    tx.parent = carriage
    ax["Y"] = C.make_arrow("Axis_Y", 0.9, 0.025, ax_mats["Y"])
    ax["Y"].rotation_euler = (0, 0, math.pi / 2)
    ax["Y"].parent = bed_root
    ax["Y"].location = (1.25, -0.5, 1.15)
    ty = C.make_text("Axis_Y_Text", "Y", (1.25, 0.65, 1.15), 0.3, ax_mats["Y"], rot=(math.pi / 2, 0, 0))
    ty.parent = bed_root
    ax["Z"] = C.make_arrow("Axis_Z", 0.9, 0.025, ax_mats["Z"])
    ax["Z"].rotation_euler = (0, -math.pi / 2, 0)
    ax["Z"].parent = gantry_root
    ax["Z"].location = (1.95, 0.9, -0.2)
    tz = C.make_text("Axis_Z_Text", "Z", (1.95, 0.9, 0.85), 0.3, ax_mats["Z"])
    tz.parent = gantry_root
    axis_objs = {"X": [ax["X"], tx], "Y": [ax["Y"], ty], "Z": [ax["Z"], tz]}
    for lst in axis_objs.values():
        for o in lst:
            o["role"] = "label"
            for ch in getattr(o, "children", []):
                ch["role"] = "label"
    grp("labels", *[o for lst in axis_objs.values() for o in lst],
        *[ch for lst in axis_objs.values() for o in lst for ch in o.children])

    labels = {}

    def label(key, txt, loc, target, size=0.26):
        t = C.make_text("Label_" + key, txt, loc, size, white_txt)
        p = C.rounded_polyline([(loc[0], loc[1], loc[2] - size * 0.7), target], 0.01)
        ln = C.tube_from_path("Leader_" + key, p, 0.012, white_txt)
        for o in (t, ln):
            o["role"] = "label"
        labels[key] = (t, ln)

    cz = ZG0
    label("frame", "ESTRUCTURA V-SLOT", (-2.3, -0.9, 0.55), (-1.5, -0.6, 0.15))
    label("zaxis", "EJE Z (HUSILLOS)", (2.35, -0.9, 3.2), (1.2, 1.8, 3.0))
    label("xaxis", "EJE X", (-2.3, -0.9, 3.3), (-1.0, 1.0, cz))
    label("extruder", "EXTRUSOR", (2.1, -0.9, cz + 1.9), (0.42, 0.66, cz - NOZZLE_DZ + 1.3))
    label("hotend", "HOTEND", (-2.1, -0.9, cz + 1.0), (-0.1, Y_NOZ, cz - NOZZLE_DZ + 0.7))
    label("nozzle", "BOQUILLA", (-2.2, -0.9, 1.35), (0.0, Y_NOZ, cz - NOZZLE_DZ + 0.12))
    label("bed", "CAMA (EJE Y)", (2.3, -0.9, 0.55), (0.9, 0.0, 0.93))
    label("spool", "FILAMENTO", (2.3, -0.9, 4.8), (0.7, 0.85, 4.8))
    temp = C.make_text("Txt_Temp", "≈ 200 °C", (0.9, -0.1, cz - NOZZLE_DZ + 0.42), 0.17,
                       C.emissive_material("Mat_TxtHot", (1.0, 0.45, 0.15), 4.0))
    temp["role"] = "label"
    grp("labels", *[o for (t, ln) in labels.values() for o in (t, ln)], temp)

    data["components"] = {
        "frame": G["frame"], "z_axis": G["z_axis"], "x_axis": G["x_axis"], "y_axis_bed": G["y_axis_bed"],
        "extruder": G["extruder"], "hotend": G["hotend"], "nozzle": G["nozzle"], "bed": G["bed"],
        "filament_spool": G["filament_spool"], "printed_part": G["printed_part"],
    }
    data["gantry_root"] = gantry_root
    data["carriage"] = carriage
    data["bed_root"] = bed_root
    data["spool_root"] = spool_root
    data["fil_line"] = fil
    data["fil_rings"] = rings
    data["drive_gear"] = drive_gear
    data["bead"] = bead
    data["seg_objs"] = seg_objs
    data["labels"] = labels
    data["axis_objs"] = axis_objs
    data["temp_text"] = temp
    data["heatblock"] = heatblock
    data["fan_hub"] = fan_hub
    data["connections"] = [
        (rail_x, plates[0], 0.04, "riel X ↔ placa del pórtico"),
        (nuts[0], screws[0], 0.04, "tuerca de latón ↔ husillo Z"),
        (screws[0], z_motor_list[0], 0.12, "husillo Z ↔ motor Z"),
        (cplate, rail_x, 0.06, "carro ↔ riel X"),
        (heatblock, nozzle, 0.06, "bloque calefactor ↔ boquilla"),
        (hs_core, heatbreak, 0.06, "disipador ↔ heat-break"),
        (heatbreak, heatblock, 0.06, "heat-break ↔ bloque"),
        (cmount, cplate, 0.06, "soporte hotend ↔ carro"),
        (bed_al, pei, 0.03, "cama ↔ lámina PEI"),
        (seg_objs[0][0], pei, 0.03, "primera capa ↔ lámina PEI"),
    ]
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


def _radius(k: float) -> float:
    frac = max(0.0, min(1.0, k / (LAYERS - 1)))
    return 0.36 + 0.10 * math.sin(frac * math.pi * 1.4 + 0.3) - 0.0175


def _pose_head(d: dict[str, Any], f: int, x: float, dy: float, zg: float) -> None:
    d["carriage"].location = (x, 0, 0)
    d["carriage"].keyframe_insert(data_path="location", frame=f)
    d["bed_root"].location = (0, Y_NOZ + dy, 0)
    d["bed_root"].keyframe_insert(data_path="location", frame=f)
    d["gantry_root"].location = (0, 0, zg)
    d["gantry_root"].keyframe_insert(data_path="location", frame=f)


def _filament(d: dict[str, Any], f: int, x: float, zg: float, feed: float) -> None:
    T = Vector((0.0, 0.85, 4.75 - 0.5))
    B = Vector((x, Y_NOZ, zg - NOZZLE_DZ + 1.18 - 0.05))
    v = B - T
    fl = d["fil_line"]
    fl.location = (T + B) / 2
    fl.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    fl.scale = (1, 1, v.length)
    for p in ("location", "rotation_euler", "scale"):
        fl.keyframe_insert(data_path=p, frame=f)
    for i, r in enumerate(d["fil_rings"]):
        ph = (feed * 1.0 + i / len(d["fil_rings"])) % 1.0
        pt = T + v * ph
        r.location = pt
        r.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
        r.keyframe_insert(data_path="location", frame=f)
        r.keyframe_insert(data_path="rotation_euler", frame=f)


def _print_run(d: dict[str, Any], f0: int, f1: int, k_start: float, k_end: float, prefill: bool = True) -> None:
    """Imprime del 'layer continuo' k_start a k_end durante [f0,f1]; capas previas ya existentes."""
    seg = d["seg_objs"]
    n = f1 - f0
    for k, row in enumerate(seg):
        for j, o in enumerate(row):
            lc = k + (j + 1) / SEGS
            if lc <= k_start:
                _vis(o, True)  # ya impreso
            elif lc > k_end:
                _vis(o, False)
            else:
                fr = f0 + int(round((lc - k_start) / max(1e-6, (k_end - k_start)) * n))
                _vis_key(o, False, f0)
                _vis_key(o, True, min(f1, max(f0, fr)))
    for f in range(f0, f1 + 1):
        lc = k_start + (k_end - k_start) * (f - f0) / n
        theta = 2 * math.pi * (lc % 1.0)
        R = _radius(lc)
        x = R * math.cos(theta)
        dy = -R * math.sin(theta)
        zg = ZG0 + lc * LAYER_H
        _pose_head(d, f, x, dy, zg)
        _filament(d, f, x, zg, (f - f0) * 0.03)
        d["bead"].location = (x, Y_NOZ, zg - NOZZLE_DZ - 0.0)
        d["bead"].keyframe_insert(data_path="location", frame=f)
        _vis_key(d["bead"], True, f)
        d["drive_gear"].rotation_euler = (0, 0, math.pi / 2 + (f - f0) * 0.4)
        d["drive_gear"].keyframe_insert(data_path="rotation_euler", frame=f)
        d["spool_root"].rotation_euler = (0, -(f - f0) * 0.03, 0)
        d["spool_root"].keyframe_insert(data_path="rotation_euler", frame=f)


def _static_part(d: dict[str, Any], k_done: float) -> None:
    for k, row in enumerate(d["seg_objs"]):
        for j, o in enumerate(row):
            _vis(o, (k + (j + 1) / SEGS) <= k_done)


def _hide_extras(d: dict[str, Any]) -> None:
    for t, ln in d["labels"].values():
        _vis(t, False)
        _vis(ln, False)
    for lst in d["axis_objs"].values():
        for o in lst:
            _vis(o, False)
            for ch in o.children:
                _vis(ch, False)
    _vis(d["temp_text"], False)
    _vis(d["bead"], False)


def _pulse(objs: list, f0: int, f1: int, amp: float = 0.06) -> None:
    for o in objs:
        s0 = o.scale.copy()
        o.keyframe_insert(data_path="scale", frame=f0)
        o.scale = s0 * (1 + amp)
        o.keyframe_insert(data_path="scale", frame=(f0 + f1) // 2)
        o.scale = s0
        o.keyframe_insert(data_path="scale", frame=f1)


def build_printer_3d_keyframes(
    printer_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    scene_phase: str = "overview",
    highlight_component: str | None = None,
) -> None:
    if bpy is None:
        return
    C.set_interp("LINEAR")
    d = printer_data
    G = d["groups"]
    f0, f1 = start_frame, max(start_frame + 8, end_frame)
    total = f1 - f0
    _hide_extras(d)
    d["meta"]["phase_applied"] = scene_phase

    if scene_phase in ("components", "components_identify"):
        _print_run(d, f0, f1, 8.0, 12.0)
        order = [("frame", "frame"), ("zaxis", "z_axis"), ("xaxis", "x_axis"), ("bed", "bed"),
                 ("extruder", "extruder"), ("hotend", "hotend"), ("nozzle", "nozzle"), ("spool", "filament_spool")]
        seg = total // (len(order) + 1)
        for i, (lk, gk) in enumerate(order):
            t_on = f0 + seg * i
            t, ln = d["labels"][lk]
            for o in (t, ln):
                _vis_key(o, False, f0)
                _vis_key(o, True, max(f0, t_on))
            _pulse(G.get(gk, []), t_on, min(f1, t_on + seg), 0.05)
    elif scene_phase in ("hotend", "extrusion", "extruder"):
        _print_run(d, f0, f1, 6.0, 8.5)
        _vis(d["temp_text"], True)
        for k in ("extruder", "hotend", "nozzle"):
            t, ln = d["labels"][k]
            _vis(t, True)
            _vis(ln, True)
        # bloque calefactor pulsa
        hb = d["heatblock"]
        for f in range(f0, f1 + 1, 3):
            s = 1.0 + 0.04 * math.sin((f - f0) * 0.6)
            hb.scale = (s, s, s)
            hb.keyframe_insert(data_path="scale", frame=f)
    elif scene_phase in ("axis_motion", "movement"):
        _static_part(d, 12.0)
        n3 = total // 3
        segs = [("X", f0, f0 + n3), ("Y", f0 + n3, f0 + 2 * n3), ("Z", f0 + 2 * n3, f1)]
        for f in range(f0, f1 + 1):
            x = dy = 0.0
            zg = ZG0 + 12.0 * LAYER_H
            if f <= segs[0][2]:
                u = (f - f0) / max(1, n3)
                x = 0.75 * math.sin(u * 2 * math.pi)
            elif f <= segs[1][2]:
                u = (f - segs[1][1]) / max(1, n3)
                dy = 0.45 * math.sin(u * 2 * math.pi)
            else:
                u = (f - segs[2][1]) / max(1, f1 - segs[2][1])
                zg += 0.55 * math.sin(u * math.pi)
            _pose_head(d, f, x, dy, zg)
            _filament(d, f, x, zg, 0.0)
        for axn, fa, fb in segs:
            for ax_, lst in d["axis_objs"].items():
                for o in lst:
                    vis = ax_ == axn
                    _vis_key(o, vis, fa)
                    for ch in o.children:
                        _vis_key(ch, vis, fa)
        for k, g in (("xaxis", "x_axis"), ("bed", "bed"), ("zaxis", "z_axis")):
            t, ln = d["labels"][k]
            _vis(t, False)
            _vis(ln, False)
        for lk, (fa, fb) in {"xaxis": (f0, f0 + n3), "bed": (f0 + n3, f0 + 2 * n3), "zaxis": (f0 + 2 * n3, f1)}.items():
            t, ln = d["labels"][lk]
            for o in (t, ln):
                _vis_key(o, False, f0)
                _vis_key(o, True, fa)
    elif scene_phase in ("layer_by_layer", "layers"):
        _print_run(d, f0, f1, 0.0, float(LAYERS))
    elif scene_phase == "cooling":
        _print_run(d, f0, f1, 10.0, 15.0)
        _vis(d["labels"]["hotend"][0], True)
        _vis(d["labels"]["hotend"][1], True)
    elif scene_phase in ("comparison", "states"):
        _print_run(d, f0, f1, 0.0, float(LAYERS))
    elif scene_phase in ("conclusion", "finished"):
        # pieza terminada, el cabezal asciende y la cama avanza para mostrarla
        _static_part(d, float(LAYERS))
        for f in range(f0, f1 + 1):
            u = (f - f0) / max(1, total)
            zg = ZG0 + LAYERS * LAYER_H + 0.9 * min(1.0, u * 1.6)
            dy = -0.55 * min(1.0, max(0.0, (u - 0.2) / 0.5))
            _pose_head(d, f, 0.0, dy, zg)
            _filament(d, f, 0.0, zg, 0.0)
    else:  # overview
        _print_run(d, f0, f1, 5.0, 12.0)
