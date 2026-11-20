"""AI VIDEO STUDIO — Mejoras de calidad automáticas para TODOS los modelos 3D.

Se ejecutan dentro de Blender (render_worker) y son agnósticas del modelo:
1. Detalle PBR de Poly Haven (rugosidad + normal + variación tonal) sobre los materiales
   metálicos existentes, PRESERVANDO el color didáctico (frío = azul, caliente = rojo, etc.).
2. Reflejos HDRI de estudio solo para rayos secundarios (el fondo de la dirección visual no cambia).
3. Hoja de inspección multi-ángulo (4 vistas) renderizada antes del video como control de calidad.

Todo tiene respaldo: sin internet o sin caché, el render continúa con los materiales procedurales.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import bpy
    from mathutils import Vector
except ImportError:  # pragma: no cover
    bpy = None
    Vector = None

from studio.blender import polyhaven_library as ph

_log = logging.getLogger("studio.quality")

PBR_TEXTURE_CANDIDATES = ["metal_plate", "metal_plate_02", "rusty_metal_02"]
HDRI_CANDIDATES = ["studio_small_08", "studio_small_03"]
SKIP_NAME_TOKENS = ("label", "text", "fx", "glow", "flame", "fire", "spark", "glass", "arrow", "particle", "halo",
                    "pedestal", "floor", "ground", "stage", "backdrop", "studio")


def _principled(mat: Any) -> Optional[Any]:
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def _input_value(node: Any, name: str, default: float = 0.0) -> float:
    sock = node.inputs.get(name)
    if sock is None or sock.is_linked or not hasattr(sock, "default_value"):
        return default
    try:
        return float(sock.default_value)
    except Exception:
        return default


def _is_eligible(mat: Any, bsdf: Any) -> bool:
    name = (mat.name or "").lower()
    if any(tok in name for tok in SKIP_NAME_TOKENS):
        return False
    if _input_value(bsdf, "Emission Strength") > 0.05:
        return False
    if _input_value(bsdf, "Alpha", 1.0) < 0.95:
        return False
    if _input_value(bsdf, "Transmission Weight") > 0.05:
        return False
    return _input_value(bsdf, "Metallic") >= 0.4  # solo superficies metálicas


def _load_texture_maps(resolution: str = "1k") -> Dict[str, Path]:
    for asset_id in PBR_TEXTURE_CANDIDATES:
        try:
            maps = ph.download_pbr_texture_maps(asset_id, resolution)
        except Exception as exc:  # red caída
            _log.warning("Poly Haven no disponible (%s): %s", asset_id, exc)
            maps = {}
        if maps.get("roughness") and maps.get("normal"):
            maps["asset_id"] = asset_id  # type: ignore[assignment]
            return maps
    return {}


def apply_pbr_detail_to_scene(strength: float = 0.15, uv_scale: float = 6.0) -> Dict[str, Any]:
    """Añade microdetalle PBR real a los materiales metálicos de la escena actual."""
    report: Dict[str, Any] = {"applied": False, "materials": [], "asset": None}
    if bpy is None:
        return report

    maps = _load_texture_maps()
    if not maps:
        report["reason"] = "sin texturas en caché ni red; se mantienen materiales procedurales"
        return report
    report["asset"] = maps.pop("asset_id")  # type: ignore[arg-type]

    # Imágenes compartidas entre todos los materiales (una sola carga en memoria)
    img_rough = bpy.data.images.load(str(maps["roughness"]))
    img_rough.colorspace_settings.name = "Non-Color"
    img_norm = bpy.data.images.load(str(maps["normal"]))
    img_norm.colorspace_settings.name = "Non-Color"
    img_diff = bpy.data.images.load(str(maps["diffuse"])) if maps.get("diffuse") else None

    used = {slot.material for o in bpy.data.objects if o.type == "MESH" for slot in o.material_slots if slot.material}
    for mat in used:
        bsdf = _principled(mat)
        if bsdf is None or not _is_eligible(mat, bsdf) or mat.get("pbr_detail"):
            continue
        tree, nodes, links = mat.node_tree, mat.node_tree.nodes, mat.node_tree.links
        x0 = bsdf.location.x - 900
        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (x0, -300)
        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (x0 + 200, -300)
        mapping.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
        links.new(coord.outputs["Object"], mapping.inputs["Vector"])

        # Normal map suave (microrayones) combinado con la normal existente si la hay
        t_norm = nodes.new("ShaderNodeTexImage")
        t_norm.image = img_norm
        t_norm.location = (x0 + 400, -600)
        links.new(mapping.outputs["Vector"], t_norm.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (x0 + 700, -600)
        nmap.inputs["Strength"].default_value = strength
        links.new(t_norm.outputs["Color"], nmap.inputs["Color"])
        old_normal = bsdf.inputs["Normal"].links[0].from_socket if bsdf.inputs["Normal"].is_linked else None
        if old_normal is not None:
            # El normal map de Blender acepta una normal base en su entrada "Normal"? No: se usa Bump encadenado
            bump = nodes.new("ShaderNodeBump")
            bump.location = (x0 + 700, -800)
            bump.inputs["Strength"].default_value = 0.2
            links.new(t_norm.outputs["Color"], bump.inputs["Height"])
            links.new(old_normal, bump.inputs["Normal"])
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        else:
            links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

        # Rugosidad: mezcla 50% del valor original con el mapa real (variación de pulido/desgaste)
        t_rough = nodes.new("ShaderNodeTexImage")
        t_rough.image = img_rough
        t_rough.location = (x0 + 400, -300)
        links.new(mapping.outputs["Vector"], t_rough.inputs["Vector"])
        base_rough = bsdf.inputs["Roughness"]
        mix_r = nodes.new("ShaderNodeMath")
        mix_r.operation = "ADD"
        mix_r.location = (x0 + 700, -300)
        mul_r = nodes.new("ShaderNodeMath")
        mul_r.operation = "MULTIPLY"
        mul_r.location = (x0 + 550, -250)
        mul_r.inputs[1].default_value = 0.5
        links.new(t_rough.outputs["Color"], mul_r.inputs[0])
        if base_rough.is_linked:
            src = base_rough.links[0].from_socket
            half = nodes.new("ShaderNodeMath")
            half.operation = "MULTIPLY"
            half.inputs[1].default_value = 0.5
            half.location = (x0 + 550, -350)
            links.new(src, half.inputs[0])
            links.new(half.outputs["Value"], mix_r.inputs[0])
        else:
            mix_r.inputs[0].default_value = float(base_rough.default_value) * 0.5
        links.new(mul_r.outputs["Value"], mix_r.inputs[1])
        links.new(mix_r.outputs["Value"], base_rough)

        # Variación tonal sutil multiplicativa que conserva el color didáctico
        if img_diff is not None:
            t_diff = nodes.new("ShaderNodeTexImage")
            t_diff.image = img_diff
            t_diff.location = (x0 + 400, 0)
            links.new(mapping.outputs["Vector"], t_diff.inputs["Vector"])
            bw = nodes.new("ShaderNodeRGBToBW")
            bw.location = (x0 + 600, 100)
            links.new(t_diff.outputs["Color"], bw.inputs["Color"])
            lum = nodes.new("ShaderNodeMath")
            lum.operation = "MULTIPLY_ADD"
            lum.location = (x0 + 780, 100)
            lum.inputs[1].default_value = 0.5
            lum.inputs[2].default_value = 0.62
            links.new(bw.outputs["Val"], lum.inputs[0])
            mixc = nodes.new("ShaderNodeMix")
            mixc.data_type = "RGBA"
            mixc.blend_type = "MULTIPLY"
            mixc.location = (x0 + 960, 0)
            mixc.inputs[0].default_value = 0.6
            bc = bsdf.inputs["Base Color"]
            if bc.is_linked:
                links.new(bc.links[0].from_socket, mixc.inputs[6])
            else:
                mixc.inputs[6].default_value = bc.default_value
            links.new(lum.outputs["Value"], mixc.inputs[7])
            links.new(mixc.outputs[2], bc)

        mat["pbr_detail"] = True
        report["materials"].append(mat.name)

    report["applied"] = bool(report["materials"])
    return report


def apply_hdri_reflections(strength: float = 0.65, rotation_deg: float = 35.0) -> Dict[str, Any]:
    """HDRI de estudio visible solo en reflejos/iluminación; el fondo original se conserva."""
    report: Dict[str, Any] = {"applied": False}
    if bpy is None:
        return report
    hdri: Optional[Path] = None
    for asset in HDRI_CANDIDATES:
        try:
            hdri = ph.download_hdri(asset, "1k")
        except Exception as exc:
            _log.warning("HDRI no disponible (%s): %s", asset, exc)
            hdri = None
        if hdri:
            report["asset"] = asset
            break
    if not hdri:
        report["reason"] = "HDRI no disponible; se mantiene el entorno actual"
        return report

    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("World_Studio")
    scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links

    # Color de fondo actual (el que fijó la dirección visual)
    bg_color = (0.02, 0.02, 0.03, 1.0)
    bg_strength = 1.0
    for n in nodes:
        if n.type == "BACKGROUND":
            bg_color = tuple(n.inputs["Color"].default_value)
            bg_strength = float(n.inputs["Strength"].default_value)
            break
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    out.location = (700, 0)
    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (500, 0)
    lp = nodes.new("ShaderNodeLightPath")
    lp.location = (300, 200)
    bg_cam = nodes.new("ShaderNodeBackground")
    bg_cam.location = (300, 50)
    bg_cam.inputs["Color"].default_value = bg_color
    bg_cam.inputs["Strength"].default_value = bg_strength
    bg_env = nodes.new("ShaderNodeBackground")
    bg_env.location = (300, -150)
    bg_env.inputs["Strength"].default_value = strength

    env = nodes.new("ShaderNodeTexEnvironment")
    env.location = (50, -150)
    env.image = bpy.data.images.load(str(hdri))
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-150, -150)
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(rotation_deg))
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-350, -150)

    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    links.new(env.outputs["Color"], bg_env.inputs["Color"])
    links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(bg_env.outputs["Background"], mix.inputs[1])
    links.new(bg_cam.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    report["applied"] = True
    return report


def model_objects(data: Optional[Dict[str, Any]]) -> List[Any]:
    """Objetos reales del modelo (sin pedestal/estudio), a partir de los grupos del constructor."""
    objs: List[Any] = []
    seen = set()
    for lst in ((data or {}).get("groups") or {}).values():
        for o in lst:
            if o is None or id(o) in seen or getattr(o, "type", "") != "MESH":
                continue
            seen.add(id(o))
            if o.get("role") in ("label", "fx"):
                continue
            objs.append(o)
    return objs


def build_default_camera_plan(shot: str, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Plan de cámara con encuadre automático al modelo (para tomas genéricas sin plan del director)."""
    groups = list(((data or {}).get("groups") or {}).keys())
    if not groups:
        return None
    presets = {
        "hero_view": [(0.0, 32, 14), (1.0, -22, 16)],
        "isometric": [(0.0, 45, 35), (1.0, 40, 33)],
        "side_view": [(0.0, 90, 4), (1.0, 84, 6)],
        "top_view": [(0.0, 10, 80), (1.0, -10, 78)],
        "turntable_orbit": [(0.0, 0, 14), (0.25, 90, 14), (0.5, 180, 14), (0.75, 270, 14), (1.0, 360, 14)],
    }
    keys = presets.get(shot)
    if not keys:
        return None
    return {
        "shot": shot, "intent": "auto-encuadre al modelo", "lens": 54, "frame": groups, "margin": 0.07,
        "keys": [{"t": t, "az": az, "el": el, "pad": 0.04} for t, az, el in keys],
    }


def _scene_bbox(objs: Optional[List[Any]] = None) -> Optional[tuple]:
    pts: List[Any] = []
    for o in (objs if objs else bpy.data.objects):
        if o.type != "MESH" or o.hide_render or o.get("role") in ("label", "fx"):
            continue
        for corner in o.bound_box:
            pts.append(o.matrix_world @ Vector(corner))
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def render_inspection_tiles(out_dir: Path, tile: int = 480, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Renderiza 4 vistas (hero, frontal, superior, lateral) del estado actual de la escena."""
    report: Dict[str, Any] = {"tiles": {}}
    if bpy is None:
        return report
    from studio.blender import camera_plans as cp
    objs = model_objects(data)
    scene = bpy.context.scene
    pts = cp._frame_points(scene, scene.frame_current, objs if objs else None)
    if not pts:
        return report
    lens, tw = 50.0, int(tile)
    saved = dict(
        cam=scene.camera, rx=scene.render.resolution_x, ry=scene.render.resolution_y,
        pct=scene.render.resolution_percentage, path=scene.render.filepath,
        frame=scene.frame_current,
    )
    cam_data = bpy.data.cameras.new("QC_Cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("QC_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = tile
    scene.render.resolution_percentage = 100
    out_dir.mkdir(parents=True, exist_ok=True)

    views = {"hero": (35, 18), "front": (0, 0), "top": (0, 89), "side": (90, 0)}
    try:
        for name, (az_d, el_d) in views.items():
            az, el = math.radians(az_d), math.radians(el_d)
            target, d_fit = cp.fit(pts, az, el, lens, tw, tw, 0.08)
            d_vec, _, _ = cp._basis(az, el)
            cam.location = target + d_vec * d_fit * 1.04
            cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            path = out_dir / f"qc_{name}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            report["tiles"][name] = str(path)
    finally:
        scene.camera = saved["cam"]
        scene.render.resolution_x, scene.render.resolution_y = saved["rx"], saved["ry"]
        scene.render.resolution_percentage = saved["pct"]
        scene.render.filepath = saved["path"]
        scene.frame_set(saved["frame"])
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
    return report
