"""AI VIDEO STUDIO — Integración de Materiales PBR y Entornos HDRI de Poly Haven.
Inspirado en la arquitectura de assets de mcp-for-blender.

Características:
1. Acceso a más de 850 texturas PBR y 600 HDRIs gratuitos (CC0) mediante la API de Poly Haven.
2. Descarga y caché local en 1k/2k optimizado para renders rápidos en tiempo real (EEVEE).
3. Construcción automática de Node-Trees de materiales en Blender con soporte para
   Diffuse, Roughness, Normal GL (OpenGL) y Metallic, con mapeo UV y escala paramétrica.
4. Soporte para iluminación ambiental HDRI con control de rotación e intensidad.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_logger = logging.getLogger("studio.polyhaven")

try:
    import bpy
except ImportError:
    bpy = None

CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "polyhaven_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "AIVideoStudio-PolyHavenClient/1.0"


def fetch_json(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        _logger.warning("Error consultando Poly Haven API (%s): %s", url, e)
        return None


def search_polyhaven_textures(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Busca texturas PBR disponibles en Poly Haven."""
    url = "https://api.polyhaven.com/assets?t=textures"
    data = fetch_json(url)
    if not data:
        return []

    q = query.lower()
    results = []
    for asset_id, info in data.items():
        name = info.get("name", asset_id)
        categories = info.get("categories", [])
        tags = info.get("tags", [])
        full_text = f"{asset_id} {name} {' '.join(categories)} {' '.join(tags)}".lower()

        if not q or q in full_text:
            results.append({
                "id": asset_id,
                "name": name,
                "categories": categories,
                "tags": tags,
                "download_count": info.get("download_count", 0),
            })
            if len(results) >= limit:
                break
    return results


def download_pbr_texture_maps(asset_id: str, resolution: str = "1k") -> Dict[str, Path]:
    """Descarga los mapas PBR de una textura (Diffuse, Rough, Normal, Metal) si no existen en caché."""
    asset_dir = CACHE_DIR / "textures" / asset_id / resolution
    asset_dir.mkdir(parents=True, exist_ok=True)

    info_url = f"https://api.polyhaven.com/files/{asset_id}"
    files_info = fetch_json(info_url)
    if not files_info:
        return {}

    downloaded: Dict[str, Path] = {}
    channels = {
        "diffuse": ("Diffuse", "jpg"),
        "roughness": ("Rough", "jpg"),
        "normal": ("nor_gl", "jpg"),
        "metallic": ("Metal", "jpg"),
    }

    for ch_name, (poly_key, pref_fmt) in channels.items():
        if poly_key not in files_info:
            continue
        res_data = files_info[poly_key].get(resolution, {})
        fmt_data = res_data.get(pref_fmt) or next(iter(res_data.values()), None)
        if not fmt_data or "url" not in fmt_data:
            continue

        file_url = fmt_data["url"]
        ext = file_url.split(".")[-1]
        local_path = asset_dir / f"{asset_id}_{ch_name}_{resolution}.{ext}"

        if not local_path.exists() or local_path.stat().st_size == 0:
            try:
                req = urllib.request.Request(file_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    local_path.write_bytes(resp.read())
            except Exception as e:
                _logger.warning("Fallo al descargar mapa %s de %s: %s", ch_name, asset_id, e)
                continue

        if local_path.exists():
            downloaded[ch_name] = local_path

    return downloaded


def download_hdri(asset_id: str = "studio_small_08", resolution: str = "1k") -> Optional[Path]:
    """Descarga un HDRI de estudio para iluminación y reflejos realistas."""
    hdri_dir = CACHE_DIR / "hdris"
    hdri_dir.mkdir(parents=True, exist_ok=True)
    local_path = hdri_dir / f"{asset_id}_{resolution}.hdr"

    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path

    info_url = f"https://api.polyhaven.com/files/{asset_id}"
    files_info = fetch_json(info_url)
    if not files_info or "hdri" not in files_info:
        return None

    res_data = files_info["hdri"].get(resolution, {})
    hdr_data = res_data.get("hdr") or next(iter(res_data.values()), None)
    if not hdr_data or "url" not in hdr_data:
        return None

    try:
        req = urllib.request.Request(hdr_data["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=25) as resp:
            local_path.write_bytes(resp.read())
        return local_path
    except Exception as e:
        _logger.warning("Fallo al descargar HDRI %s: %s", asset_id, e)
        return None


def create_pbr_material_in_blender(
    mat_name: str,
    texture_maps: Dict[str, Path],
    uv_scale: float = 1.0,
    base_tint: Optional[Tuple[float, float, float, float]] = None,
) -> Any:
    """Crea un material Principled BSDF completo conectado a mapas PBR en Blender."""
    if bpy is None:
        return None

    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # 1. Output y Principled BSDF
    node_out = nodes.new(type="ShaderNodeOutputMaterial")
    node_out.location = (400, 0)
    node_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    node_bsdf.location = (0, 0)
    links.new(node_bsdf.outputs["BSDF"], node_out.inputs["Surface"])

    # 2. Texture Coordinate y Mapping
    node_coord = nodes.new(type="ShaderNodeTexCoord")
    node_coord.location = (-800, 0)
    node_map = nodes.new(type="ShaderNodeMapping")
    node_map.location = (-600, 0)
    node_map.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
    links.new(node_coord.outputs["Generated"], node_map.inputs["Vector"])

    # 3. Diffuse / Base Color
    if "diffuse" in texture_maps:
        img_diff = bpy.data.images.load(str(texture_maps["diffuse"]))
        node_diff = nodes.new(type="ShaderNodeTexImage")
        node_diff.location = (-350, 200)
        node_diff.image = img_diff
        links.new(node_map.outputs["Vector"], node_diff.inputs["Vector"])

        if base_tint:
            node_mix = nodes.new(type="ShaderNodeMix")
            node_mix.data_type = "RGBA"
            node_mix.blend_type = "MULTIPLY"
            node_mix.location = (-150, 200)
            node_mix.inputs[0].default_value = 0.65
            links.new(node_diff.outputs["Color"], node_mix.inputs[6])
            node_mix.inputs[7].default_value = base_tint
            links.new(node_mix.outputs[2], node_bsdf.inputs["Base Color"])
        else:
            links.new(node_diff.outputs["Color"], node_bsdf.inputs["Base Color"])

    # 4. Roughness
    if "roughness" in texture_maps:
        img_rough = bpy.data.images.load(str(texture_maps["roughness"]))
        img_rough.colorspace_settings.name = "Non-Color"
        node_rough = nodes.new(type="ShaderNodeTexImage")
        node_rough.location = (-350, -50)
        node_rough.image = img_rough
        links.new(node_map.outputs["Vector"], node_rough.inputs["Vector"])
        links.new(node_rough.outputs["Color"], node_bsdf.inputs["Roughness"])

    # 5. Metallic
    if "metallic" in texture_maps:
        img_metal = bpy.data.images.load(str(texture_maps["metallic"]))
        img_metal.colorspace_settings.name = "Non-Color"
        node_metal = nodes.new(type="ShaderNodeTexImage")
        node_metal.location = (-350, -300)
        node_metal.image = img_metal
        links.new(node_map.outputs["Vector"], node_metal.inputs["Vector"])
        links.new(node_metal.outputs["Color"], node_bsdf.inputs["Metallic"])
    else:
        node_bsdf.inputs["Metallic"].default_value = 0.85

    # 6. Normal Map
    if "normal" in texture_maps:
        img_norm = bpy.data.images.load(str(texture_maps["normal"]))
        img_norm.colorspace_settings.name = "Non-Color"
        node_norm_tex = nodes.new(type="ShaderNodeTexImage")
        node_norm_tex.location = (-350, -550)
        node_norm_tex.image = img_norm

        node_norm_map = nodes.new(type="ShaderNodeNormalMap")
        node_norm_map.location = (-120, -550)
        node_norm_map.inputs["Strength"].default_value = 1.0

        links.new(node_map.outputs["Vector"], node_norm_tex.inputs["Vector"])
        links.new(node_norm_tex.outputs["Color"], node_norm_map.inputs["Color"])
        links.new(node_norm_map.outputs["Normal"], node_bsdf.inputs["Normal"])

    return mat


def setup_hdri_environment_in_blender(hdri_path: Path, strength: float = 1.0) -> None:
    """Configura el entorno de iluminación y reflejos World con un HDRI en Blender."""
    if bpy is None or not hdri_path.exists():
        return

    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World_HDRI")
        bpy.context.scene.world = world

    world.use_nodes = True
    tree = world.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    node_out = nodes.new(type="ShaderNodeOutputWorld")
    node_out.location = (400, 0)

    node_bg = nodes.new(type="ShaderNodeBackground")
    node_bg.location = (150, 0)
    node_bg.inputs["Strength"].default_value = strength
    links.new(node_bg.outputs["Background"], node_out.inputs["Surface"])

    img_hdr = bpy.data.images.load(str(hdri_path))
    node_env = nodes.new(type="ShaderNodeTexEnvironment")
    node_env.location = (-150, 0)
    node_env.image = img_hdr
    links.new(node_env.outputs["Color"], node_bg.inputs["Color"])
