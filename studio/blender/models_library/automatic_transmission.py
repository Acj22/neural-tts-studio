"""Transmisión automática — modelo explicativo del tren planetario (Fase 3.1, rehecho).

Diseño didáctico (eje de la transmisión a lo largo de Y; la cámara mira hacia +Y):
- Tren planetario simple REAL: Sol Zs=24, Planetarios Zp=12 (x4), Corona Zr=48 (= Zs + 2·Zp).
  Radios primitivos proporcionales al número de dientes y dientes que engranan geométricamente.
- Cinemática exacta por la ecuación de Willis:  ωs·Zs + ωr·Zr = ωc·(Zs + Zr)
    * 1ª marcha (reducción): corona FIJA  -> ωc = ωs/3 (reducción 3:1)
    * Directa 1:1: sol y portasatélites acoplados por embrague -> todo gira solidario
    * Reversa: portasatélites FIJO -> ωr = -ωs·Zs/Zr = -ωs/2 (sentido contrario)
- Código de color: ROJO = elemento retenido, VERDE = entrada, AZUL = salida.
- Convertidor de par con impulsor, turbina y estator; cuerpo de válvulas y servo del freno.

Limitaciones declaradas (ver models_metadata.json): un solo juego planetario simple (las
transmisiones reales combinan 2-3), portasatélites simplificado a placa trasera, sin bomba
de aceite ni solenoides eléctricos.
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

from studio.blender.materials import setup_engine_materials
from studio.blender.models_library import _common as C

KS = 0.0225                       # radio primitivo por diente
ZS, ZP, ZR = 24, 12, 48
RS, RP, RR = ZS * KS, ZP * KS, ZR * KS
ORBIT = RS + RP                   # 0.81
MOD = 2 * KS
GEAR_W = 0.5

# Tasas relativas por modo (en unidades de ω0 del sol): (sol, portasatélites, corona, giro planeta relativo)
MODE_RATES = {
    "reduction": (1.0, 1.0 / 3.0, 0.0, -2.0 * (1.0 - 1.0 / 3.0)),
    "direct":    (1.0, 1.0, 1.0, 0.0),
    "reverse":   (1.0, 0.0, -0.5, -2.0),
}
MODE_LABELS = {
    "reduction": "1ª MARCHA  ·  CORONA FIJA  ·  REDUCCIÓN 3:1",
    "direct": "DIRECTA 1:1  ·  EMBRAGUE UNE SOL Y PORTASATÉLITES",
    "reverse": "REVERSA  ·  PORTASATÉLITES FIJO  ·  GIRO INVERSO",
}


def create_automatic_transmission_3d(center_z: float = 2.0) -> dict[str, Any]:
    if bpy is None:
        return {}
    mats = setup_engine_materials()
    cz = center_z
    data: dict[str, Any] = {"components": {}, "groups": {}, "meta": {"center_z": cz}}
    G = data["groups"]

    def grp(name: str, *objs: Any) -> None:
        for o in objs:
            G.setdefault(name, []).append(o)
            o["comp_group"] = name

    white = C.emissive_material("Mat_LabelWhite", (1, 1, 1), 2.2)
    green = C.emissive_material("Mat_MarkGreen", (0.15, 1.0, 0.35), 4.0)
    red = C.emissive_material("Mat_MarkRed", (1.0, 0.12, 0.10), 4.0)
    blue = C.emissive_material("Mat_MarkBlue", (0.15, 0.55, 1.0), 4.0)
    yellow = C.emissive_material("Mat_MarkYellow", (1.0, 0.85, 0.1), 3.0)
    atf = mats.get("fluid_atf")

    # ------------------------------------------------------------------ pivotes
    sun_pivot = C.empty("Sun_Pivot", (0, 0, cz))
    carrier_pivot = C.empty("Carrier_Pivot", (0, 0, cz))
    ring_pivot = C.empty("Ring_Pivot", (0, 0, cz))
    impeller_root = C.empty("Impeller_Root", (0, 0, cz))
    turbine_root = C.empty("Turbine_Root", (0, 0, cz))
    data["pivots"] = {"sun": sun_pivot, "carrier": carrier_pivot, "ring": ring_pivot,
                      "impeller": impeller_root, "turbine": turbine_root}

    def child(o: Any, parent: Any) -> Any:
        o.parent = parent
        return o

    # ------------------------------------------------------------------ SOL
    sun = C.make_gear("Planetary_Sun_Gear", ZS, RS, MOD, GEAR_W, (0, 0, 0), mats["brass_gold"])
    child(sun, sun_pivot)
    cap = C.cylinder("Sun_Hub_Cap", 0.13, 0.06, (0, -0.28, 0), "Y", mats["cutaway_rim"], 24)
    child(cap, sun_pivot)
    shaft = C.cylinder("Trans_Input_Shaft", 0.2, 3.95, (0, 0.25 + 3.95 / 2, 0), "Y", mats["crankshaft"], 24)
    child(shaft, sun_pivot)
    key_s = C.box("Input_Shaft_Marker", (0.09, 0.3, 0.09), (0, 2.65, 0.22), mats["rod_bearings"])
    child(key_s, sun_pivot)
    sun_mark = bpy.ops.mesh.primitive_torus_add(major_radius=0.19, minor_radius=0.028, major_segments=32,
                                                minor_segments=8, location=(0, -0.3, 0), rotation=(math.pi / 2, 0, 0))
    sun_mark = bpy.context.active_object
    sun_mark.name = "Mark_Sun_Input"
    C.set_mat(sun_mark, green)
    child(sun_mark, sun_pivot)
    grp("sun", sun, cap, shaft, key_s, sun_mark)
    sun_mark["role"] = "marker"

    # ------------------------------------------------------------------ PORTASATÉLITES + PLANETARIOS
    plate = C.cylinder("Planetary_Carrier", 1.05, 0.12, (0, 0.37, 0), "Y", mats["connecting_rod"], 48)
    child(plate, carrier_pivot)
    tube = C.cylinder("Carrier_Output_Tube", 0.34, 0.87, (0, 0.865, 0), "Y", mats["cutaway_rim"], 32)
    child(tube, carrier_pivot)
    key_c = C.box("Output_Tube_Marker", (0.1, 0.28, 0.08), (0, 0.95, 0.36), mats["valve_exhaust"])
    child(key_c, carrier_pivot)
    grp("carrier", plate, tube, key_c)

    planets, pins, mounts, pin_red, pin_blue = [], [], [], [], []
    for k in range(4):
        a = k * math.pi / 2
        mount = C.empty(f"Planet_Mount_{k+1}", (ORBIT * math.cos(a), 0, ORBIT * math.sin(a)))
        mount.parent = carrier_pivot
        mounts.append(mount)
        pg = C.make_gear(f"Planetary_Pinion_{k+1}", ZP, RP, MOD, GEAR_W, (0, 0, 0), mats["cylinder_liner"],
                         hole_r=0.0, phase=math.pi / 12)
        child(pg, mount)
        pin = C.cylinder(f"Planet_Pin_{k+1}", 0.07, 0.69, (0, 0.025, 0), "Y", mats["wrist_pin"], 16)
        child(pin, mount)
        pc_cap = C.cylinder(f"Planet_Pin_Cap_{k+1}", 0.1, 0.05, (0, -0.31, 0), "Y", mats["cutaway_rim"], 16)
        child(pc_cap, mount)
        for lst, mat_, nm in ((pin_red, red, "Red"), (pin_blue, blue, "Blue")):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.024, major_segments=24,
                                             minor_segments=8, location=(0, -0.34, 0),
                                             rotation=(math.pi / 2, 0, 0))
            m_ = bpy.context.active_object
            m_.name = f"Mark_Pin_{nm}_{k+1}"
            C.set_mat(m_, mat_)
            m_["role"] = "marker"
            child(m_, mount)
            lst.append(m_)
        planets.append(pg)
        pins.append(pin)
        grp("planets", pg, pin, pc_cap)
        grp("carrier", pin)

    # ------------------------------------------------------------------ CORONA + TAMBOR
    ring = C.make_ring_gear("Planetary_Ring_Gear", ZR, RR, MOD, 1.32, GEAR_W, (0, 0, 0), mats["ring_gear_blue"])
    child(ring, ring_pivot)
    drum = C.revolve("Ring_Drum", [(1.36, 0.25), (1.36, 1.55)], 0, 2 * math.pi, 48, mats["ring_gear_blue"], 0.08)
    drum.location = (0, 0, 0)
    child(drum, ring_pivot)
    drum_plate = C.revolve("Ring_Drum_Plate", [(0.42, 1.55), (1.4, 1.55)], 0, 2 * math.pi, 48,
                           mats["ring_gear_blue"], 0.08)
    child(drum_plate, ring_pivot)
    grp("ring", ring, drum, drum_plate)

    def torus_world(name: str, major: float, minor: float, loc, mat) -> Any:
        bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=64,
                                         minor_segments=8, location=loc, rotation=(math.pi / 2, 0, 0))
        o = bpy.context.active_object
        o.name = name
        C.set_mat(o, mat)
        o["role"] = "marker"
        return o

    ring_red = torus_world("Mark_Ring_Held", 1.40, 0.035, (0, -0.28, cz), red)
    ring_blue = torus_world("Mark_Ring_Output", 1.40, 0.035, (0, -0.28, cz), blue)
    ring_green = torus_world("Mark_Ring_Input", 1.40, 0.035, (0, -0.28, cz), green)

    # Banda de freno + servo hidráulico
    band = torus_world("Trans_Brake_Band", 1.48, 0.055, (0, 0.9, cz), mats["clutch_plate"])
    band["role"] = "part"
    servo = C.cylinder("Trans_Brake_Servo", 0.14, 0.55, (2.05, 0.9, cz), "X", mats["brass_gold"], 20)
    rod = C.cylinder("Trans_Brake_Servo_Rod", 0.05, 0.5, (1.7, 0.9, cz), "X", mats["wrist_pin"], 12)
    grp("brake", band, servo, rod)

    # ------------------------------------------------------------------ EMBRAGUE MULTIDISCO
    clutch_discs = []
    for i in range(6):
        d = C.cylinder(f"Clutch_Disc_{i+1}", 1.15, 0.06, (0, 1.85 + 0.1 * i, cz), "Y",
                       mats["clutch_plate"] if i % 2 == 0 else mats["cutaway_rim"], 40)
        clutch_discs.append(d)
    grp("clutch", *clutch_discs)

    # ------------------------------------------------------------------ CARCASA SECCIONADA (corte de 120° arriba)
    a0, a1 = math.radians(150), math.radians(390)
    case = C.revolve("Trans_Main_Case", [(1.78, -0.6), (1.78, 2.8)], a0, a1, 48, mats["engine_block"], 0.1,
                     center=(0, 0, cz))
    flange = C.revolve("Trans_Case_Flange", [(1.62, -0.6), (2.0, -0.6)], a0, a1, 48, mats["engine_block"], 0.12,
                       center=(0, 0, cz))
    bell = C.revolve("Trans_Bellhousing", [(1.95, 2.8), (1.95, 4.9)], a0, a1, 48, mats["engine_block"], 0.1,
                     center=(0, 0, cz))
    grp("housing", case, flange, bell)

    # ------------------------------------------------------------------ CONVERTIDOR DE PAR
    prof = [(1.0 + 0.55 * math.cos(t), 3.75 + 0.55 * math.sin(t)) for t in
            [i * 2 * math.pi / 28 for i in range(29)]]
    shell = C.revolve("Converter_Housing", prof, a0, a1, 48, mats["manifold_pipes"], 0.06, center=(0, 0, cz))
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.34, major_segments=48, minor_segments=14,
                                     location=(0, 3.75, cz), rotation=(math.pi / 2, 0, 0))
    fluid = bpy.context.active_object
    fluid.name = "Converter_ATF_Fluid"
    C.set_mat(fluid, atf)
    C.smooth(fluid)
    impeller_vanes, turbine_vanes, stator_vanes = [], [], []
    for i in range(20):
        ang = i * 2 * math.pi / 20
        for lst, y, tilt, root, mat_, nm in ((impeller_vanes, 4.05, 0.6, impeller_root, mats["piston"], "Impeller"),
                                              (turbine_vanes, 3.45, -0.6, turbine_root, mats["cutaway_rim"], "Turbine")):
            v = C.box(f"Converter_{nm}_Vane_{i+1}", (0.8, 0.36, 0.05), (1.0 * math.cos(ang), y, 1.0 * math.sin(ang)), mat_)
            v.rotation_euler = (tilt, -ang, 0)
            child(v, root)
            lst.append(v)
    for i in range(12):
        ang = i * 2 * math.pi / 12
        v = C.box(f"Converter_Stator_Vane_{i+1}", (0.45, 0.3, 0.05), (0.62 * math.cos(ang), 3.75, cz + 0.62 * math.sin(ang)),
                  mats["valve_intake"])
        v.rotation_euler = (0.5, -ang, 0)
        stator_vanes.append(v)
    flywheel = C.cylinder("Engine_Flywheel_Plate", 1.95, 0.22, (0, 4.95, cz), "Y", mats["counterweights"], 48)
    grp("converter", shell, fluid, *impeller_vanes, *turbine_vanes, *stator_vanes)
    grp("engine_side", flywheel)

    # ------------------------------------------------------------------ CUERPO DE VÁLVULAS (hidráulica)
    vb = C.box("Valve_Body", (1.7, 2.4, 0.32), (0, 1.2, cz - 1.93), mats["oil_pan"], bev=0.02)
    spools = []
    for i in range(6):
        s = C.cylinder(f"Valve_Spool_{i+1}", 0.07, 0.5, (-0.65 + 0.26 * i, -0.02, cz - 1.93), "Y", mats["brass_gold"], 14)
        spools.append(s)
    hyd_mat = C.emissive_material("Mat_HydraulicLine", (0.95, 0.2, 0.1), 1.2)
    path1 = C.rounded_polyline([(0.5, 1.2, cz - 1.78), (1.95, 1.2, cz - 1.78), (1.95, 0.9, cz - 1.0), (1.95, 0.9, cz - 0.16)], 0.18)
    line_brake = C.tube_from_path("Hydraulic_Line_Brake", path1, 0.035, hyd_mat)
    path2 = C.rounded_polyline([(-0.5, 1.9, cz - 1.78), (-1.95, 1.9, cz - 1.78), (-1.95, 2.1, cz - 0.3), (-1.2, 2.1, cz - 0.05)], 0.18)
    line_clutch = C.tube_from_path("Hydraulic_Line_Clutch", path2, 0.035, hyd_mat)
    grp("hydraulics", vb, *spools, line_brake, line_clutch)

    # ------------------------------------------------------------------ ETIQUETAS
    labels = {}
    def label(key: str, txt: str, loc, target, size=0.30):
        t = C.make_text("Label_" + key, txt, loc, size, white)
        p = C.rounded_polyline([(loc[0], loc[1], loc[2] - size * 0.7), target], 0.01)
        ln = C.tube_from_path("Leader_" + key, p, 0.012, white)
        labels[key] = (t, ln)
        for o in (t, ln):
            o["role"] = "label"
    ly = -1.1
    label("sun", "SOL", (-2.5, ly, cz + 1.7), (0.0, -0.3, cz + 0.02))
    label("planets", "PLANETARIOS", (2.5, ly, cz + 1.9), (ORBIT + 0.02, -0.3, cz + 0.1))
    label("carrier", "PORTASATÉLITES", (-2.6, ly, cz - 1.5), (0.57, -0.1, cz - 0.57))
    label("ring", "CORONA", (2.5, ly, cz - 1.6), (0.9, -0.28, cz - 0.9))
    status_text = {}
    for m, txt in MODE_LABELS.items():
        t = C.make_text("Status_" + m, txt, (0, -1.1, cz + 1.92), 0.135, yellow)
        t["role"] = "label"
        status_text[m] = t
    legend = [C.make_text("Legend_Held", "■ FIJO", (-1.05, -1.1, cz - 1.92), 0.15, red),
              C.make_text("Legend_In", "■ ENTRADA", (0.0, -1.1, cz - 1.92), 0.15, green),
              C.make_text("Legend_Out", "■ SALIDA", (1.05, -1.1, cz - 1.92), 0.15, blue)]
    for t in legend:
        t["role"] = "label"
    data["labels"] = labels
    data["status_text"] = status_text
    data["legend"] = legend

    for o in bpy.data.objects:
        if o.type == "MESH" and "comp_group" not in o.keys() and o.get("role") not in ("marker", "label"):
            pass

    data["components"] = {
        "sun_gear": sun, "planets": planets, "planet_pins": pins, "carrier": plate, "ring_gear": ring,
        "ring_drum": drum, "brake_band": band, "brake_servo": servo, "clutch_discs": clutch_discs,
        "impeller": impeller_vanes, "turbine": turbine_vanes, "stator": stator_vanes,
        "atf_fluid": fluid, "valve_body": vb, "housing": case, "input_shaft": shaft, "output_tube": tube,
        "converter_housing": shell, "flywheel": flywheel,
    }
    data["markers"] = {"sun_in": sun_mark, "ring_red": ring_red, "ring_blue": ring_blue, "ring_green": ring_green,
                       "pin_red": pin_red, "pin_blue": pin_blue}
    data["mounts"] = mounts
    data["planet_gears"] = planets
    data["converter_shell"] = shell
    data["connections"] = [
        (shaft, sun, 0.02, "eje de entrada ↔ engranaje solar"),
        (plate, tube, 0.02, "placa del portasatélites ↔ tubo de salida"),
        (pins[0], plate, 0.02, "pasador ↔ portasatélites"),
        (planets[0], sun, 0.02, "planetario ↔ solar (engrane)"),
        (planets[0], ring, 0.02, "planetario ↔ corona (engrane)"),
        (ring, drum, 0.02, "corona ↔ tambor"),
        (rod, band, 0.02, "vástago del servo ↔ banda de freno"),
        (servo, rod, 0.02, "servo ↔ vástago"),
        (line_brake, vb, 0.05, "línea hidráulica ↔ cuerpo de válvulas"),
    ]
    data["explode_groups"] = {
        "sun": [sun_pivot], "carrier": [carrier_pivot], "ring": [ring_pivot],
        "clutch": clutch_discs, "converter": [impeller_root, turbine_root, shell, fluid] + stator_vanes,
        "engine_side": [flywheel], "case": [case, flange, bell],
    }
    return data


# =============================================================================
# ANIMACIÓN
# =============================================================================

def _vis(obj: Any, visible: bool) -> None:
    obj.hide_render = not visible
    obj.hide_viewport = not visible


def _set_mode_markers(d: dict[str, Any], mode: str) -> None:
    m = d["markers"]
    for o in [m["ring_red"], m["ring_blue"], m["ring_green"], *m["pin_red"], *m["pin_blue"]]:
        _vis(o, False)
    _vis(m["sun_in"], True)
    if mode == "reduction":
        _vis(m["ring_red"], True)
        for o in m["pin_blue"]:
            _vis(o, True)
    elif mode == "reverse":
        for o in m["pin_red"]:
            _vis(o, True)
        _vis(m["ring_blue"], True)
    elif mode == "direct":
        _vis(m["ring_blue"], True)
        for o in m["pin_blue"]:
            _vis(o, True)


def _hide_all_labels(d: dict[str, Any]) -> None:
    for t, ln in d["labels"].values():
        _vis(t, False)
        _vis(ln, False)
    for t in d["status_text"].values():
        _vis(t, False)
    for t in d["legend"]:
        _vis(t, False)


def _keyrot(obj: Any, angle: float, frame: int) -> None:
    cur = obj.rotation_euler.copy()
    obj.rotation_euler = (cur.x, -angle, cur.z)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _drive(d: dict[str, Any], segments: list[tuple[int, int, str]], w0_rad_per_frame: float) -> None:
    """Anima sol/portasatélites/corona/planetarios integrando tasas por segmento (interpolación lineal)."""
    p = d["pivots"]
    th = {"s": 0.0, "c": 0.0, "r": 0.0, "p": 0.0}
    f0 = segments[0][0]
    for key_, obj in (("s", p["sun"]), ("c", p["carrier"]), ("r", p["ring"])):
        _keyrot(obj, 0.0, f0)
    for g in d["planet_gears"]:
        g.rotation_euler = (0, 0, 0)
        g.keyframe_insert(data_path="rotation_euler", frame=f0)
    for (fa, fb, mode) in segments:
        rs, rc, rr, rp = MODE_RATES[mode]
        n = (fb - fa)
        th["s"] += rs * w0_rad_per_frame * n
        th["c"] += rc * w0_rad_per_frame * n
        th["r"] += rr * w0_rad_per_frame * n
        th["p"] += rp * w0_rad_per_frame * n
        _keyrot(p["sun"], th["s"], fb)
        _keyrot(p["carrier"], th["c"], fb)
        _keyrot(p["ring"], th["r"], fb)
        for g in d["planet_gears"]:
            g.rotation_euler = (0, -th["p"], 0)
            g.keyframe_insert(data_path="rotation_euler", frame=fb)


def _w0(frames: int, rev_per_sec: float = 0.22) -> float:
    fps = bpy.context.scene.render.fps
    return 2 * math.pi * rev_per_sec / fps


def _spin_pair(d: dict[str, Any], f0: int, f1: int, ratio_turbine: tuple[float, float]) -> None:
    fps = bpy.context.scene.render.fps
    w = 2 * math.pi * 0.45 / fps
    imp, tur = d["pivots"]["impeller"], d["pivots"]["turbine"]
    mid = (f0 + f1) // 2
    _keyrot(imp, 0.0, f0)
    _keyrot(tur, 0.0, f0)
    ai = w * (mid - f0)
    at = w * ratio_turbine[0] * (mid - f0)
    _keyrot(imp, ai, mid)
    _keyrot(tur, at, mid)
    ai2 = ai + w * (f1 - mid)
    at2 = at + w * ratio_turbine[1] * (f1 - mid)
    _keyrot(imp, ai2, f1)
    _keyrot(tur, at2, f1)


def _flow_particles(d: dict[str, Any], f0: int, f1: int) -> None:
    """Esferas de flujo ATF recorriendo el toroide (impulsor -> turbina -> estator -> impulsor)."""
    cz = d["meta"]["center_z"]
    mat = C.emissive_material("Mat_FlowParticle", (1.0, 0.25, 0.1), 6.0)
    fps = bpy.context.scene.render.fps
    loop_frames = int(fps * 2.2)
    for k in range(9):
        tor = math.radians(40 + k * 12)
        s = C.sphere(f"Flow_Particle_{k}", 0.05, (0, 0, 0), mat, 8)
        s["role"] = "fx"
        f = f0
        phase0 = (k % 3) / 3.0
        while f <= f1:
            t = 2 * math.pi * (((f - f0) / loop_frames + phase0) % 1.0)
            r = 1.0 + 0.30 * math.cos(t)
            y = 3.75 + 0.30 * math.sin(t)
            s.location = (r * math.cos(tor), y, cz + r * math.sin(tor))
            s.keyframe_insert(data_path="location", frame=f)
            f += max(1, loop_frames // 14)
        s.location = s.location
        s.keyframe_insert(data_path="location", frame=f1)


def _explode(d: dict[str, Any], f0: int, f1: int) -> None:
    ex = d["explode_groups"]
    offs = {"sun": -1.7, "carrier": -0.75, "ring": 0.0, "clutch": 1.0, "converter": 2.0, "engine_side": 2.6, "case": 0.0}
    fm = f0 + max(2, int((f1 - f0) * 0.35))
    for k, objs in ex.items():
        for o in objs:
            o.keyframe_insert(data_path="location", frame=f0)
            base = o.location.copy()
            o.location = (base.x, base.y + offs[k], base.z)
            o.keyframe_insert(data_path="location", frame=fm)
            o.keyframe_insert(data_path="location", frame=f1)
            o.location = base


def _pulse(objs: list, f0: int, f1: int, amp: float = 0.07) -> None:
    for o in objs:
        s0 = o.scale.copy()
        o.keyframe_insert(data_path="scale", frame=f0)
        o.scale = s0 * (1 + amp)
        o.keyframe_insert(data_path="scale", frame=(f0 + f1) // 2)
        o.scale = s0
        o.keyframe_insert(data_path="scale", frame=f1)


def build_transmission_keyframes(
    trans_data: dict[str, Any],
    start_frame: int = 1,
    end_frame: int = 120,
    scene_phase: str = "overview",
    highlight_component: str | None = None,
) -> None:
    if bpy is None:
        return
    C.set_interp("LINEAR")
    d = trans_data
    f0, f1 = start_frame, max(start_frame + 8, end_frame)
    total = f1 - f0
    w0 = _w0(total)
    _hide_all_labels(d)
    d["meta"]["phase_applied"] = scene_phase

    if "exploded" in scene_phase or scene_phase == "components":
        _set_mode_markers(d, "reduction")
        for o in [d["markers"]["sun_in"], d["markers"]["ring_red"], *d["markers"]["pin_blue"]]:
            _vis(o, False)
        _explode(d, f0, f1)
        _drive(d, [(f0, f1, "reduction")], w0 * 0.5)
    elif "converter" in scene_phase:
        _set_mode_markers(d, "direct")
        for o in [d["markers"]["sun_in"], d["markers"]["ring_blue"], *d["markers"]["pin_blue"]]:
            _vis(o, False)
        _spin_pair(d, f0, f1, (0.25, 0.92))
        _flow_particles(d, f0, f1)
    elif scene_phase == "planetary_intro":
        _set_mode_markers(d, "reduction")
        for o in [d["markers"]["sun_in"], d["markers"]["ring_red"], *d["markers"]["pin_blue"]]:
            _vis(o, False)
        _drive(d, [(f0, f1, "reduction")], w0 * 0.35)
        order = ["sun", "planets", "carrier", "ring"]
        group_objs = {"sun": [d["pivots"]["sun"]], "planets": d["mounts"], "carrier": [d["pivots"]["carrier"]], "ring": [d["pivots"]["ring"]]}
        seg = total // (len(order) + 1)
        for i, k in enumerate(order):
            t_on = f0 + seg * i
            t_off = f0 + seg * (i + 1) + seg // 2
            t_, ln = d["labels"][k]
            for o in (t_, ln):
                o.hide_render = True; o.hide_viewport = True
                o.keyframe_insert(data_path="hide_render", frame=f0)
                o.keyframe_insert(data_path="hide_viewport", frame=f0)
                _vis(o, True)
                o.keyframe_insert(data_path="hide_render", frame=max(f0, t_on))
                o.keyframe_insert(data_path="hide_viewport", frame=max(f0, t_on))
            _pulse(group_objs[k], t_on, min(f1, t_on + seg), 0.06)
    elif scene_phase in ("planetary_reduction", "planetary", "gear"):
        _set_mode_markers(d, "reduction")
        _vis(d["status_text"]["reduction"], True)
        for t in d["legend"]:
            _vis(t, True)
        _drive(d, [(f0, f1, "reduction")], w0)
    elif scene_phase == "planetary_direct":
        _set_mode_markers(d, "direct")
        _vis(d["status_text"]["direct"], True)
        for t in d["legend"]:
            _vis(t, True)
        _drive(d, [(f0, f1, "direct")], w0)
        for i, c in enumerate(d["components"]["clutch_discs"]):
            c.keyframe_insert(data_path="location", frame=f0)
            b = c.location.copy()
            c.location = (b.x, b.y - 0.045 * (i - 2.5) * 0.9, b.z)
            c.keyframe_insert(data_path="location", frame=f1)
            c.location = b
    elif scene_phase == "planetary_reverse":
        _set_mode_markers(d, "reverse")
        _vis(d["status_text"]["reverse"], True)
        for t in d["legend"]:
            _vis(t, True)
        _drive(d, [(f0, f1, "reverse")], w0)
    elif scene_phase == "planetary_compare":
        # Tres estados consecutivos con leyenda y marcadores sincronizados.
        for t in d["legend"]:
            _vis(t, True)
        n3 = total // 3
        segs = [(f0, f0 + n3, "reduction"), (f0 + n3, f0 + 2 * n3, "direct"), (f0 + 2 * n3, f1, "reverse")]
        _drive(d, segs, w0)
        m = d["markers"]
        mode_items = {
            "reduction": [m["ring_red"], *m["pin_blue"]],
            "direct": [m["ring_blue"], *m["pin_blue"]],
            "reverse": [*m["pin_red"], m["ring_blue"]],
        }
        all_items = {id(o): o for v in mode_items.values() for o in v}
        for (fa, fb, mode) in segs:
            for o in all_items.values():
                _vis(o, o in mode_items[mode])
                o.keyframe_insert(data_path="hide_render", frame=fa)
                o.keyframe_insert(data_path="hide_viewport", frame=fa)
            for mname, t in d["status_text"].items():
                _vis(t, mname == mode)
                t.keyframe_insert(data_path="hide_render", frame=fa)
                t.keyframe_insert(data_path="hide_viewport", frame=fa)
    elif "clutch" in scene_phase or "direct_drive" in scene_phase:
        _set_mode_markers(d, "direct")
        _vis(d["status_text"]["direct"], True)
        _drive(d, [(f0, f0 + total // 2, "reduction"), (f0 + total // 2, f1, "direct")], w0)
        for i, c in enumerate(d["components"]["clutch_discs"]):
            base = c.location.copy()
            c.location = base
            c.keyframe_insert(data_path="location", frame=f0)
            c.keyframe_insert(data_path="location", frame=f0 + total // 2)
            c.location = (base.x, base.y - 0.045 * (i - 2.5) * 0.9, base.z)
            c.keyframe_insert(data_path="location", frame=f0 + total // 2 + 8)
            c.keyframe_insert(data_path="location", frame=f1)
            c.location = base
    else:  # overview / conclusion
        _set_mode_markers(d, "reduction")
        for o in [d["markers"]["sun_in"], d["markers"]["ring_red"], *d["markers"]["pin_blue"]]:
            _vis(o, False)
        _drive(d, [(f0, f1, "reduction")], w0 * 0.8)
        _spin_pair(d, f0, f1, (0.9, 0.9))
