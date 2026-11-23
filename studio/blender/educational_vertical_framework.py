"""AI VIDEO STUDIO — Framework Educativo Vertical 9:16 (Blender + EEVEE).

Base reutilizable para videos educativos de alto impacto destinados a:
TikTok, YouTube Shorts, Instagram Reels y Facebook Reels (~1:30 a 1:50 min / 90-110 s).

ARQUITECTURA MODULAR DESACOPLADA:
1. `SafeZone916Config`: Zonas seguras para redes verticales (evita interfaces, botones y subtítulos).
2. `Camera916Config`: Ópticas y movimientos cinemáticos suaves continuos (cero tomas estáticas).
3. `EeveeLightingConfig`: Iluminación de estudio de 4 fuentes + ciclorama con sombras suaves.
4. `EeveeMaterialsPalette`: Paleta de materiales PBR de maqueta técnica y fluidos.
5. `AdaptiveLabelsSystem`: Algoritmo matemático 3D -> 2D con anti-colisión y ajuste a zonas seguras.
6. `TimelineRetentionDirector`: Planificación de tiempos, beats de retención y micro-movimientos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import bpy
    from mathutils import Matrix, Quaternion, Vector
except ImportError:
    bpy = None
    Matrix = None
    Quaternion = None
    Vector = None


# ==============================================================================
# 1. PARÁMETROS CONFIGURABLES: ENCUADRE Y ZONAS SEGURAS 9:16
# ==============================================================================

@dataclass
class SafeZone916Config:
    """Delimita el área visible segura en videos verticales 9:16 para evitar que
    elementos clave queden tapados por interfaces de TikTok, Reels y Shorts."""

    # Márgenes en porcentaje de pantalla normalizada [0.0 - 1.0]
    safe_top_pct: float = 0.14       # 14% superior (barra de estado, buscador TikTok, logo Live)
    safe_bottom_pct: float = 0.22    # 22% inferior (subtítulos dinámicos, pie de cuenta, descripción, audio)
    safe_left_pct: float = 0.08      # 8% lateral izquierdo
    safe_right_pct: float = 0.12     # 12% lateral derecho (botones verticales: Like, Comentarios, Compartir)

    # Rango efectivo [u_min, u_max] x [v_min, v_max]
    def get_safe_u_bounds(self) -> Tuple[float, float]:
        return (self.safe_left_pct, 1.0 - self.safe_right_pct)

    def get_safe_v_bounds(self) -> Tuple[float, float]:
        return (self.safe_bottom_pct, 1.0 - self.safe_top_pct)

    def clamp_screen_uv(self, u: float, v: float, padding: float = 0.02) -> Tuple[float, float]:
        """Ajusta estrictamente una coordenada de pantalla (u, v) dentro de la zona segura."""
        u_min, u_max = self.get_safe_u_bounds()
        v_min, v_max = self.get_safe_v_bounds()
        clamped_u = max(u_min + padding, min(u_max - padding, u))
        clamped_v = max(v_min + padding, min(v_max - padding, v))
        return (clamped_u, clamped_v)

    def is_in_safe_zone(self, u: float, v: float) -> bool:
        u_min, u_max = self.get_safe_u_bounds()
        v_min, v_max = self.get_safe_v_bounds()
        return (u_min <= u <= u_max) and (v_min <= v <= v_max)


# ==============================================================================
# 2. PARÁMETROS CONFIGURABLES: CÁMARA CINEMÁTICA Y MOVIMIENTOS SUAVES
# ==============================================================================

@dataclass
class Camera916Config:
    """Configuración óptica y dinámica de cámara optimizada para formato 9:16."""
    lens_mm: float = 54.0            # Distancia focal (52-58mm evita distorsión angular vertical)
    sensor_width_mm: float = 36.0    # Full frame sensor
    sensor_fit: str = "VERTICAL"     # Adaptación vertical para encuadres en smartphone
    clip_start: float = 0.1
    clip_end: float = 500.0

    # Dinámica de micro-movimientos para retención continua (nunca estática)
    orbit_speed_deg_sec: float = 0.85   # Micro-rotación orbital suave en azimut
    dolly_zoom_amplitude: float = 0.08  # Variación sutil de distancia (8%) para dar respiración
    elevation_drift_deg: float = 1.2    # Variación vertical suave
    interpolation_type: str = "BEZIER"  # Curvas de aceleración y desaceleración suaves

    # Márgenes de encuadre en el algoritmo fit
    default_frame_margin: float = 0.065 # 6.5% de aire alrededor del objeto protagonista


# ==============================================================================
# 3. PARÁMETROS CONFIGURABLES: ILUMINACIÓN Y AMBIENTE EEVEE NEXT
# ==============================================================================

@dataclass
class EeveeLightingConfig:
    """Setup de iluminación de estudio de 4 fuentes + ciclorama con sombras suaves."""
    # Key Light (Luz Principal cálida direccional)
    key_energy_w: float = 680.0
    key_color_rgb: Tuple[float, float, float] = (1.0, 0.98, 0.95)
    key_location: Tuple[float, float, float] = (5.5, -9.5, 7.5)
    key_size_m: float = 4.5

    # Fill Light (Luz de Relleno fría suave para levantar sombras sin contraste duro)
    fill_energy_w: float = 320.0
    fill_color_rgb: Tuple[float, float, float] = (0.88, 0.94, 1.0)
    fill_location: Tuple[float, float, float] = (-5.5, -7.5, 5.0)
    fill_size_m: float = 5.5

    # Rim / Kicker Light (Luz de Recorte trasera para perfilar bordes metálicos)
    rim_energy_w: float = 460.0
    rim_color_rgb: Tuple[float, float, float] = (0.95, 0.98, 1.0)
    rim_location: Tuple[float, float, float] = (0.0, 8.0, 6.5)
    rim_size_m: float = 4.0

    # Top Light (Cenital suave para iluminar cavidades y cortes interiores)
    top_energy_w: float = 290.0
    top_color_rgb: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    top_location: Tuple[float, float, float] = (0.0, -1.0, 9.0)

    # Entorno y Fondo (Ciclorama Slate Blue educativo)
    backdrop_color_rgb: Tuple[float, float, float] = (0.141, 0.216, 0.282) # #243748
    backdrop_emission_strength: float = 0.75
    ambient_world_strength: float = 0.65
    use_soft_shadows: bool = True


# ==============================================================================
# 4. PARÁMETROS CONFIGURABLES: ESTILOS DE ETIQUETAS Y LÍNEAS GUÍA
# ==============================================================================

@dataclass
class LabelStyleConfig:
    """Estilo tipográfico y geométrico de etiquetas 3D y líneas de anclaje."""
    font_size: float = 0.050          # Calibrado para legibilidad perfecta sin desbordar márgenes 9:16
    extrude: float = 0.008           # Grosor 3D sutil para legibilidad
    bevel_depth: float = 0.0015      # Biselado fino anti-aliased
    text_color_rgb: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    text_emission_strength: float = 3.6  # Emisión alta para contraste técnico
    leader_line_radius: float = 0.0045   # Radio fino estilizado del tubo directriz
    leader_line_color_rgb: Tuple[float, float, float] = (0.92, 0.96, 1.0)
    leader_line_emission: float = 2.4
    anchor_sphere_radius: float = 0.018  # Esfera de anclaje discreta sobre el componente
    anti_collision_min_u_dist: float = 0.20  # Distancia horizontal mínima entre etiquetas en pantalla
    anti_collision_min_v_dist: float = 0.085 # Distancia vertical mínima entre etiquetas en pantalla


# ==============================================================================
# 5. PARÁMETROS CONFIGURABLES: TIEMPOS Y RITMO POR ETAPA (TIMELINE RETENTION)
# ==============================================================================

@dataclass
class StageTiming:
    """Define una etapa narrativa con sus micro-beats visuales para retención continua."""
    stage_id: str
    name: str
    start_sec: float
    end_sec: float
    description: str
    camera_intent: str       # 'hero_orbit', 'macro_dolly', 'axial_travel', 'wide_recap', etc.
    active_component: str    # Nombre del componente protagonista
    active_labels: List[str] # Lista de etiquetas activas en esta etapa
    visual_changes_sec: float = 3.5  # Cada cuántos segundos ocurre un micro-cambio de atención


@dataclass
class TimelinePlanConfig:
    """Plan temporal completo para sostener la retención en ~1:30–1:50 min (90–110s)."""
    target_duration_sec: float = 105.0  # 1 min 45 segundos por defecto
    fps: int = 24
    stages: List[StageTiming] = field(default_factory=list)

    @property
    def total_frames(self) -> int:
        return int(round(self.target_duration_sec * self.fps))


# ==============================================================================
# 6. CONFIGURACIÓN MAESTRA UNIFICADA (REUTILIZABLE PARA CUALQUIER TEMA 9:16)
# ==============================================================================

@dataclass
class Educational916FrameworkConfig:
    """Configuración maestra completamente desacoplada de la lógica del modelo."""
    safe_zones: SafeZone916Config = field(default_factory=SafeZone916Config)
    camera: Camera916Config = field(default_factory=Camera916Config)
    lighting: EeveeLightingConfig = field(default_factory=EeveeLightingConfig)
    labels: LabelStyleConfig = field(default_factory=LabelStyleConfig)
    timeline: TimelinePlanConfig = field(default_factory=TimelinePlanConfig)
    render_width: int = 720
    render_height: int = 1280


# ==============================================================================
# 7. MOTOR MATEMÁTICO: PROYECCIÓN, ZONAS SEGURAS Y ANTI-COLISIÓN DE ETIQUETAS
# ==============================================================================

class AdaptiveLabelsEngine:
    """Calcula la posición 3D óptima de etiquetas y líneas directrices,
    proyectándolas a coordenadas de pantalla 2D, aplicando clamp estricto a las
    zonas seguras y resolviendo cualquier superposición (anti-collision)."""

    def __init__(self, safe_zones: SafeZone916Config, label_style: LabelStyleConfig):
        self.safe_zones = safe_zones
        self.style = label_style

    @staticmethod
    def project_3d_to_screen_uv(
        point_3d: Vector,
        cam_pos: Vector,
        cam_target: Vector,
        lens_mm: float,
        width: int,
        height: int,
        sensor_w: float = 36.0,
        cam_obj: Optional[Any] = None,
        scene: Optional[Any] = None,
    ) -> Tuple[float, float, float]:
        """Proyecta un punto 3D al espacio de pantalla [0, 1] x [0, 1] y distancia en profundidad."""
        if bpy is not None and cam_obj is not None:
            try:
                from bpy_extras.object_utils import world_to_camera_view
                sc = scene or bpy.context.scene
                co_cam = world_to_camera_view(sc, cam_obj, point_3d)
                return (co_cam.x, co_cam.y, abs(co_cam.z))
            except Exception:
                pass

        forward = (cam_target - cam_pos).normalized()
        right = forward.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(forward).normalized()

        v = point_3d - cam_pos
        depth = v.dot(forward)
        if depth <= 0.01:
            return (0.5, 0.5, depth)

        # Para sensor_fit == "VERTICAL", la dimensión de referencia es 24mm de alto
        half_sensor_h = 12.0
        ty = half_sensor_h / lens_mm
        tx = ty * (width / height)

        x_norm = v.dot(right) / (depth * tx)
        y_norm = v.dot(up) / (depth * ty)

        u = (x_norm + 1.0) * 0.5
        v_coord = (y_norm + 1.0) * 0.5
        return (u, v_coord, depth)

    @staticmethod
    def unproject_screen_uv_to_3d(
        u: float,
        v: float,
        depth: float,
        cam_pos: Vector,
        cam_target: Vector,
        lens_mm: float,
        width: int,
        height: int,
        sensor_w: float = 36.0,
        cam_obj: Optional[Any] = None,
        scene: Optional[Any] = None,
    ) -> Vector:
        """Convierte una coordenada de pantalla UV [0, 1] a una posición 3D exacta en el espacio."""
        if bpy is not None and cam_obj is not None:
            try:
                sc = scene or bpy.context.scene
                corners = cam_obj.data.view_frame(scene=sc)
                c_bl = corners[2]
                c_tr = corners[0]
                x_f = c_bl.x + u * (c_tr.x - c_bl.x)
                y_f = c_bl.y + v * (c_tr.y - c_bl.y)
                z_f = c_bl.z
                d_scale = depth / abs(z_f)
                p_loc = Vector((x_f, y_f, z_f)) * d_scale
                return cam_obj.matrix_world @ p_loc
            except Exception:
                pass

        forward = (cam_target - cam_pos).normalized()
        right = forward.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(forward).normalized()

        half_sensor_h = 12.0
        ty = half_sensor_h / lens_mm
        tx = ty * (width / height)

        x_norm = (u * 2.0) - 1.0
        y_norm = (v * 2.0) - 1.0

        p_3d = cam_pos + forward * depth + right * (x_norm * depth * tx) + up * (y_norm * depth * ty)
        return p_3d

    def solve_label_positions_2d(
        self,
        anchors_2d: Dict[str, Tuple[float, float, str]],  # key -> (u, v, preferred_side: 'left'|'right')
    ) -> Dict[str, Tuple[float, float]]:
        """Ajusta las posiciones 2D de etiquetas en pantalla respetando las zonas seguras
        y dispersando colisiones verticales u horizontales."""
        u_min, u_max = self.safe_zones.get_safe_u_bounds()
        v_min, v_max = self.safe_zones.get_safe_v_bounds()
        solved: Dict[str, Tuple[float, float]] = {}

        # 1. Asignación inicial en columnas laterales seguras (Left: u=0.30, Right: u=0.72)
        for key, (orig_u, orig_v, side) in anchors_2d.items():
            if side == "left":
                target_u = 0.30
            elif side == "right":
                target_u = 0.72
            else:
                target_u = 0.30 if orig_u < 0.5 else 0.72

            target_v = max(v_min + 0.07, min(v_max - 0.07, orig_v))
            solved[key] = (target_u, target_v)

        # 2. Algoritmo de relajación anti-colisión (Iterative Repulsion)
        keys = list(solved.keys())
        min_u = self.style.anti_collision_min_u_dist
        min_v = self.style.anti_collision_min_v_dist

        for _ in range(16):  # Hasta 16 iteraciones de relajación
            collision_found = False
            for i in range(len(keys)):
                k1 = keys[i]
                u1, v1 = solved[k1]
                for j in range(i + 1, len(keys)):
                    k2 = keys[j]
                    u2, v2 = solved[k2]

                    du = abs(u1 - u2)
                    dv = abs(v1 - v2)
                    if du < min_u and dv < min_v:
                        collision_found = True
                        # Dispersión vertical con margen garantizado
                        push_v = max(0.045, (min_v - dv) * 0.65)
                        if v1 >= v2:
                            new_v1 = v1 + push_v
                            new_v2 = v2 - push_v
                        else:
                            new_v1 = v1 - push_v
                            new_v2 = v2 + push_v

                        # Clamp dentro de la zona segura garantizando holgura de 4.5%
                        new_u1, new_v1 = self.safe_zones.clamp_screen_uv(u1, new_v1, padding=0.045)
                        new_u2, new_v2 = self.safe_zones.clamp_screen_uv(u2, new_v2, padding=0.045)
                        solved[k1] = (new_u1, new_v1)
                        solved[k2] = (new_u2, new_v2)

            if not collision_found:
                break

        return solved


# ==============================================================================
# 8. CONSTRUCTOR VISUAL DE ESCENA EN BLENDER (GENÉRICO Y REUTILIZABLE)
# ==============================================================================

def setup_educational_scene_base(
    config: Educational916FrameworkConfig,
) -> Dict[str, Any]:
    """Inicializa en Blender la base reutilizable:
    cámara 9:16 con sensor vertical, iluminación de estudio de 4 fuentes,
    telón ciclorama Slate Blue y configuración del motor EEVEE."""
    if bpy is None:
        return {"status": "headless_mock"}

    scene = bpy.context.scene
    render = scene.render

    # Configuración de render vertical 9:16
    render.resolution_x = config.render_width
    render.resolution_y = config.render_height
    render.resolution_percentage = 100
    render.fps = config.timeline.fps

    # Colección para iluminación y entorno
    studio_col = bpy.data.collections.get("Studio_Lighting")
    if not studio_col:
        studio_col = bpy.data.collections.new("Studio_Lighting")
        scene.collection.children.link(studio_col)

    # 1. Entorno 360° Studio World (sin plano partido que corte el horizonte) + Iluminación ambiental PBR
    lt = config.lighting
    if not scene.world:
        scene.world = bpy.data.worlds.new("Studio_World_360")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.09, 0.14, 0.21, 1.0)
        bg_node.inputs[1].default_value = 1.45

    plane_bg = bpy.data.objects.get("Studio_Backdrop_Plane")
    if plane_bg:
        bpy.data.objects.remove(plane_bg, do_unlink=True)
        plane_bg = None

    target_center = Vector((0.0, 0.0, 1.25))

    def _aim_light_at_center(l_obj: Any) -> None:
        direction = target_center - Vector(l_obj.location)
        if direction.length > 0.001:
            l_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    # 2. Key Light (apuntada directamente al modelo)
    key_obj = bpy.data.objects.get("Light_Key_Studio")
    if not key_obj:
        bpy.ops.object.light_add(type="AREA", radius=lt.key_size_m, location=lt.key_location)
        key_obj = bpy.context.active_object
        key_obj.name = "Light_Key_Studio"
        key_obj.data.energy = lt.key_energy_w * 2.2
        key_obj.data.color = lt.key_color_rgb
        _aim_light_at_center(key_obj)
        studio_col.objects.link(key_obj)
        if key_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(key_obj)

    # 3. Fill Light (apuntada directamente al modelo)
    fill_obj = bpy.data.objects.get("Light_Fill_Studio")
    if not fill_obj:
        bpy.ops.object.light_add(type="AREA", radius=lt.fill_size_m, location=lt.fill_location)
        fill_obj = bpy.context.active_object
        fill_obj.name = "Light_Fill_Studio"
        fill_obj.data.energy = lt.fill_energy_w * 2.4
        fill_obj.data.color = lt.fill_color_rgb
        _aim_light_at_center(fill_obj)
        studio_col.objects.link(fill_obj)
        if fill_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(fill_obj)

    # 4. Rim Light (apuntada directamente al modelo)
    rim_obj = bpy.data.objects.get("Light_Rim_Studio")
    if not rim_obj:
        bpy.ops.object.light_add(type="AREA", radius=lt.rim_size_m, location=lt.rim_location)
        rim_obj = bpy.context.active_object
        rim_obj.name = "Light_Rim_Studio"
        rim_obj.data.energy = lt.rim_energy_w * 2.2
        rim_obj.data.color = lt.rim_color_rgb
        _aim_light_at_center(rim_obj)
        studio_col.objects.link(rim_obj)
        if rim_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(rim_obj)

    # 5. Top Light + Front Specular Light
    top_obj = bpy.data.objects.get("Light_Top_Studio")
    if not top_obj:
        bpy.ops.object.light_add(type="AREA", radius=4.0, location=lt.top_location)
        top_obj = bpy.context.active_object
        top_obj.name = "Light_Top_Studio"
        top_obj.data.energy = lt.top_energy_w * 2.0
        top_obj.data.color = lt.top_color_rgb
        _aim_light_at_center(top_obj)
        studio_col.objects.link(top_obj)
        if top_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(top_obj)

    front_obj = bpy.data.objects.get("Light_Front_Studio")
    if not front_obj:
        bpy.ops.object.light_add(type="AREA", radius=3.5, location=(0.5, -5.5, 1.8))
        front_obj = bpy.context.active_object
        front_obj.name = "Light_Front_Studio"
        front_obj.data.energy = 650.0
        front_obj.data.color = (1.0, 0.99, 0.96)
        _aim_light_at_center(front_obj)
        studio_col.objects.link(front_obj)
        if front_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(front_obj)

    # 6. Cámara Director Vertical 9:16
    cam_obj = bpy.data.objects.get("Director_Camera_Obj")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Director_Camera")
        cam_obj = bpy.data.objects.new("Director_Camera_Obj", cam_data)
        scene.collection.objects.link(cam_obj)

    scene.camera = cam_obj
    cam_data = cam_obj.data
    cam_data.lens = config.camera.lens_mm
    cam_data.sensor_fit = config.camera.sensor_fit
    cam_data.sensor_width = config.camera.sensor_width_mm
    cam_data.clip_start = config.camera.clip_start
    cam_data.clip_end = config.camera.clip_end

    # Configuracion tecnica de render 9:16 de alta fluidez (>= 24 fps + Motion Blur)
    scene.render.fps = config.timeline.fps
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.5
    scene.render.motion_blur_position = 'CENTER'

    if hasattr(scene, 'eevee'):
        if hasattr(scene.eevee, 'taa_render_samples'):
            scene.eevee.taa_render_samples = 16
        if hasattr(scene.eevee, 'use_shadows'):
            scene.eevee.use_shadows = True
        if hasattr(scene.eevee, 'use_fast_gi'):
            scene.eevee.use_fast_gi = True

    return {
        "scene": scene,
        "camera": cam_obj,
        "lights": {"key": key_obj, "fill": fill_obj, "rim": rim_obj, "top": top_obj},
        "backdrop": plane_bg,
    }


def create_adaptive_3d_label(
    name: str,
    text: str,
    anchor_3d: Vector,
    target_screen_u: float,
    target_screen_v: float,
    cam_pos: Vector,
    cam_target: Vector,
    config: Educational916FrameworkConfig,
    collection: Optional[Any] = None,
    cam_obj: Optional[Any] = None,
) -> Tuple[Any, Any]:
    """Construye en Blender el texto 3D y la línea directriz orientada y anclada al componente.
    Utiliza una capa de primer plano HUD (Camera-Parented Near Overlay) a depth=0.45m con
    un badge de fondo de alto contraste, garantizando que NINGUNA parte del modelo 3D
    pueda superponerse u ocluir las letras en ningún ángulo ni zoom."""
    if bpy is None:
        return (None, None)

    scene = bpy.context.scene
    col = collection or scene.collection
    cam = cam_obj or scene.camera or bpy.data.objects.get("Director_Camera_Obj") or bpy.data.objects.get("Camera_916")

    hud_dist = 0.45
    if cam:
        corners = cam.data.view_frame(scene=scene)
        c_tr = corners[0]
        c_bl = corners[2]
        z_ref = abs(c_bl.z)
        scale = hud_dist / z_ref
        frame_w = (c_tr.x - c_bl.x) * scale
        frame_h = (c_tr.y - c_bl.y) * scale
    else:
        frame_w = 0.125
        frame_h = 0.222

# loc_x/loc_y recalculados con clamping mas abajo

    # Material texto blanco luminiscente
    mat_txt = bpy.data.materials.get("Mat_AdaptiveLabel_Text")
    if not mat_txt:
        mat_txt = bpy.data.materials.new("Mat_AdaptiveLabel_Text")
        mat_txt.use_nodes = True
        b = mat_txt.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = (*config.labels.text_color_rgb, 1.0)
            if "Emission Color" in b.inputs:
                b.inputs["Emission Color"].default_value = (*config.labels.text_color_rgb, 1.0)
            if "Emission Strength" in b.inputs:
                b.inputs["Emission Strength"].default_value = 2.0

    # Material badge oscuro semi-transparente para legibilidad 100% sobre cualquier fondo
    mat_bg = bpy.data.materials.get("Mat_AdaptiveLabel_Badge")
    if not mat_bg:
        mat_bg = bpy.data.materials.new("Mat_AdaptiveLabel_Badge")
        mat_bg.use_nodes = True
        b_bg = mat_bg.node_tree.nodes.get("Principled BSDF")
        if b_bg:
            b_bg.inputs["Base Color"].default_value = (0.04, 0.07, 0.12, 0.92)
            b_bg.inputs["Roughness"].default_value = 0.3

    font_size = frame_h * 0.021
    char_w = font_size * 0.58
    badge_w = len(text) * char_w + font_size * 0.9
    badge_h = font_size * 1.55

    # 2. Clamping estricto a Zonas Seguras 9:16 (10% a 90% ancho, y >= 26% alto para no chocar con subtitulos/UI)
    half_w_norm = (badge_w * 0.5) / max(frame_w, 0.001)
    half_h_norm = (badge_h * 0.5) / max(frame_h, 0.001)

    min_u = max(0.10, half_w_norm + 0.02)
    max_u = min(0.90, 1.0 - half_w_norm - 0.02)
    clamped_u = max(min_u, min(max_u, target_screen_u))

    min_v = max(0.26, half_h_norm + 0.02)  # Zona segura estricta >= 26% para subtitulos inferiores
    max_v = min(0.88, 1.0 - half_h_norm - 0.02)  # Margen superior para UI de Reels/Shorts
    clamped_v = max(min_v, min(max_v, target_screen_v))

    loc_x = (clamped_u - 0.5) * frame_w
    loc_y = (clamped_v - 0.5) * frame_h
    loc_z = -hud_dist

    # Objeto Texto 3D parented a cámara
    txt_curve = bpy.data.curves.new(f"{name}_txt_curve", type="FONT")
    txt_curve.body = text
    txt_curve.size = font_size
    txt_curve.align_x = "CENTER"
    txt_curve.align_y = "CENTER"
    txt_curve.extrude = font_size * 0.03

    txt_obj = bpy.data.objects.new(f"Label_{name}", txt_curve)
    if cam:
        txt_obj.parent = cam
        txt_obj.matrix_parent_inverse = Matrix.Identity(4)
        txt_obj.location = Vector((loc_x, loc_y, loc_z + 0.002))
        txt_obj.rotation_euler = (0, 0, 0)
    else:
        txt_obj.location = cam_pos
    txt_obj["role"] = "label"
    txt_obj.data.materials.append(mat_txt)
    txt_obj.visible_shadow = False
    col.objects.link(txt_obj)

    # Backdrop Badge Plane parented a cámara
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    bg_obj = bpy.context.active_object
    bg_obj.name = f"Badge_{name}"
    if cam:
        bg_obj.parent = cam
        bg_obj.matrix_parent_inverse = Matrix.Identity(4)
        bg_obj.location = Vector((loc_x, loc_y, loc_z))
        bg_obj.scale = Vector((badge_w, badge_h, 1.0))
        bg_obj.rotation_euler = (0, 0, 0)
    bg_obj["role"] = "label"
    bg_obj.data.materials.append(mat_bg)
    bg_obj.visible_shadow = False
    col.objects.link(bg_obj)
    if bg_obj.name in scene.collection.objects and col != scene.collection:
        scene.collection.objects.unlink(bg_obj)

    # Material línea
    mat_line = bpy.data.materials.get("Mat_AdaptiveLeader_Line")
    if not mat_line:
        mat_line = bpy.data.materials.new("Mat_AdaptiveLeader_Line")
        mat_line.use_nodes = True
        b_l = mat_line.node_tree.nodes.get("Principled BSDF")
        if b_l:
            b_l.inputs["Base Color"].default_value = (*config.labels.leader_line_color_rgb, 1.0)
            if "Emission Color" in b_l.inputs:
                b_l.inputs["Emission Color"].default_value = (*config.labels.leader_line_color_rgb, 1.0)
            if "Emission Strength" in b_l.inputs:
                b_l.inputs["Emission Strength"].default_value = config.labels.leader_line_emission

    # Trazado de Línea Directriz en espacio local de la cámara (Camera-Parented)
    right_offset = -badge_w * 0.5 if target_screen_u >= 0.5 else badge_w * 0.5
    start_cam_local = Vector((loc_x + right_offset, loc_y, loc_z))
    shelf_cam_local = Vector((loc_x + right_offset + (-0.008 if target_screen_u >= 0.5 else 0.008), loc_y, loc_z))

    cam_inv = cam.matrix_world.inverted() if cam else Matrix.Identity(4)
    p0 = start_cam_local
    p1 = shelf_cam_local
    p2 = cam_inv @ anchor_3d

    curve_line = bpy.data.curves.new(f"{name}_leader_curve", type="CURVE")
    curve_line.dimensions = "3D"
    curve_line.bevel_depth = font_size * 0.05
    curve_line.bevel_resolution = 3
    curve_line.use_fill_caps = True

    spline = curve_line.splines.new("POLY")
    spline.points.add(2)
    pts = [p0, p1, p2]
    for i, p in enumerate(pts):
        spline.points[i].co = (p.x, p.y, p.z, 1.0)

    line_obj = bpy.data.objects.new(f"Leader_{name}", curve_line)
    if cam:
        line_obj.parent = cam
        line_obj.matrix_parent_inverse = Matrix.Identity(4)
        line_obj.location = Vector((0, 0, 0))
        line_obj.rotation_euler = (0, 0, 0)
    line_obj["role"] = "label"
    line_obj.visible_shadow = False
    line_obj.data.materials.append(mat_line)
    col.objects.link(line_obj)

    # Esfera micro de anclaje
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016, location=anchor_3d)
    dot_obj = bpy.context.active_object
    dot_obj.name = f"Dot_{name}"
    dot_obj["role"] = "label"
    dot_obj.visible_shadow = False
    dot_obj.data.materials.append(mat_line)
    col.objects.link(dot_obj)
    if dot_obj.name in scene.collection.objects and col != scene.collection:
        scene.collection.objects.unlink(dot_obj)

    txt_obj["badge_obj"] = bg_obj
    txt_obj["dot_obj"] = dot_obj
    line_obj["dot_obj"] = dot_obj

    return (txt_obj, line_obj)


# ==============================================================================
# 9. CONSTRUCTORES MODULARES DE ALTA FIDELIDAD PARA MÚLTIPLES OBJETOS
# ==============================================================================

def create_hinged_appliance_door(
    name: str,
    hinge_pos: Tuple[float, float, float],
    width: float,
    height: float,
    open_angle_deg: float = 38.0,
    mat_outer: Any = None,
    mat_liner: Any = None,
    mat_gasket: Any = None,
    num_bins: int = 2,
    bev_outer: float = 0.035,
    bev_liner: float = 0.030,
) -> Dict[str, Any]:
    """Crea un ensamblaje articulado modular de alta fidelidad para puertas/paneles de electrodomésticos
    y maquinaria educativa, con jerarquía local limpia y sin desajustes de matrices.
    
    Incluye:
    - Empty bisagra (pivot) en `hinge_pos` rotado según `open_angle_deg`.
    - Carcasa exterior biselada de acabado electrodoméstico.
    - Panel interior moldeado (liner) emparentado con matriz local.
    - Burlete de goma perimetral (gasket seal).
    - Balconetes interiores / estantes en la puerta (multi-tier bins).
    """
    if bpy is None:
        return {}

    from studio.blender.models_library import _common as C

    hinge_empty = C.empty(f"{name}_Hinge", hinge_pos)
    hinge_empty.rotation_euler = (0, 0, math.radians(open_angle_deg))

    # 1. Carcasa exterior
    door_outer = C.box(f"{name}_Outer", (width, 0.09, height), (0, 0, 0), mat_outer, bev=bev_outer)
    door_outer.parent = hinge_empty
    door_outer.matrix_parent_inverse.identity()
    door_outer.location = (width / 2, 0.045, 0)

    # 2. Panel interior moldeado (liner)
    liner_w = max(0.1, width - 0.12)
    liner_h = max(0.1, height - 0.12)
    door_liner = C.box(f"{name}_Liner", (liner_w, 0.035, liner_h), (0, 0, 0), mat_liner, bev=bev_liner)
    door_liner.parent = hinge_empty
    door_liner.matrix_parent_inverse.identity()
    door_liner.location = (width / 2, -0.015, 0)

    # 3. Burlete perimetral de goma
    gasket_w = max(0.1, width - 0.04)
    gasket_h = max(0.1, height - 0.04)
    door_gasket = C.box(f"{name}_Gasket", (gasket_w, 0.02, gasket_h), (0, 0, 0), mat_gasket, bev=0.01)
    door_gasket.parent = hinge_empty
    door_gasket.matrix_parent_inverse.identity()
    door_gasket.location = (width / 2, -0.010, 0)

    # 4. Balconetes interiores en la puerta (multi-tier bins)
    bins = []
    if num_bins > 0:
        bin_spacing = (height - 0.30) / max(1, num_bins - 1) if num_bins > 1 else 0
        bin_z_start = -height / 2 + 0.18
        for i in range(num_bins):
            bz = bin_z_start + i * bin_spacing if num_bins > 1 else 0
            bin_obj = C.box(f"{name}_Bin_{i+1}", (width * 0.72, 0.07, 0.11), (0, 0, 0), mat_liner, bev=0.015)
            bin_obj.parent = hinge_empty
            bin_obj.matrix_parent_inverse.identity()
            bin_obj.location = (width / 2, -0.055, bz)
            bins.append(bin_obj)

    return {
        "hinge": hinge_empty,
        "outer": door_outer,
        "liner": door_liner,
        "gasket": door_gasket,
        "bins": bins,
    }


def create_compartment_led_light(
    name: str,
    location: Tuple[float, float, float],
    energy: float = 22.0,
    color_rgb: Tuple[float, float, float] = (1.0, 0.97, 0.92),
    radius: float = 0.12,
) -> Any:
    """Crea una fuente de luz LED interna suave para cavidades de electrodomésticos y piezas mecánicas,
    resaltando la profundidad de estantes y componentes."""
    if bpy is None:
        return None
    light_data = bpy.data.lights.new(f"{name}_Data", 'POINT')
    light_data.energy = energy
    light_data.color = color_rgb
    light_data.shadow_soft_size = radius
    light_obj = bpy.data.objects.new(name, light_data)
    light_obj.location = location
    bpy.context.scene.collection.objects.link(light_obj)
    return light_obj


def animate_smooth_rotation(
    obj: Any,
    start_frame: int,
    end_frame: int,
    start_rot_z_deg: float,
    end_rot_z_deg: float,
) -> None:
    """Añade animación de rotación en Z con interpolación Bézier suave (ease-in-out)."""
    if obj is None or bpy is None:
        return
    obj.animation_data_create()
    obj.rotation_euler = (0, 0, math.radians(start_rot_z_deg))
    obj.keyframe_insert(data_path="rotation_euler", index=2, frame=start_frame)
    obj.rotation_euler = (0, 0, math.radians(end_rot_z_deg))
    obj.keyframe_insert(data_path="rotation_euler", index=2, frame=end_frame)
    
    # Asegurar interpolación Bézier suave
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        fcurves = getattr(action, "fcurves", None)
        if not fcurves and hasattr(action, "layers"):
            for layer in action.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            if fc.data_path == "rotation_euler" and fc.array_index == 2:
                                for kp in fc.keyframe_points:
                                    kp.interpolation = "BEZIER"
        elif fcurves:
            for fc in fcurves:
                if fc.data_path == "rotation_euler" and fc.array_index == 2:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "BEZIER"

