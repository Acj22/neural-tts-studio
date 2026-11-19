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

    # 1. Telón de fondo ciclorama
    lt = config.lighting
    mat_bg = bpy.data.materials.get("Mat_StudioBackdrop")
    if not mat_bg:
        mat_bg = bpy.data.materials.new("Mat_StudioBackdrop")
        mat_bg.use_nodes = True
        bsdf = mat_bg.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bg_col = (*lt.backdrop_color_rgb, 1.0)
            if "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.02, 0.03, 0.04, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.95
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = bg_col
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = lt.backdrop_emission_strength

    plane_bg = bpy.data.objects.get("Studio_Backdrop_Plane")
    if not plane_bg:
        bpy.ops.mesh.primitive_plane_add(size=70.0, location=(0, 14.0, 3.0))
        plane_bg = bpy.context.active_object
        plane_bg.name = "Studio_Backdrop_Plane"
        plane_bg.rotation_euler = (math.radians(90), 0, 0)
        plane_bg.data.materials.append(mat_bg)
        studio_col.objects.link(plane_bg)
        if plane_bg.name in scene.collection.objects:
            scene.collection.objects.unlink(plane_bg)

    # 2. Key Light
    key_obj = bpy.data.objects.get("Light_Key_Studio")
    if not key_obj:
        bpy.ops.object.light_add(type="AREA", radius=lt.key_size_m, location=lt.key_location)
        key_obj = bpy.context.active_object
        key_obj.name = "Light_Key_Studio"
        key_obj.data.energy = lt.key_energy_w
        key_obj.data.color = lt.key_color_rgb
        studio_col.objects.link(key_obj)
        if key_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(key_obj)

    # 3. Fill Light
    fill_obj = bpy.data.objects.get("Light_Fill_Studio")
    if not fill_obj:
        bpy.ops.object.light_add(type="AREA", radius=lt.fill_size_m, location=lt.fill_location)
        fill_obj = bpy.context.active_object
        fill_obj.name = "Light_Fill_Studio"
        fill_obj.data.energy = lt.fill_energy_w
        fill_obj.data.color = lt.fill_color_rgb
        studio_col.objects.link(fill_obj)
        if fill_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(fill_obj)

    # 4. Rim Light
    rim_obj = bpy.data.objects.get("Light_Rim_Studio")
    if not rim_obj:
        bpy.ops.object.light_add(type="AREA", radius=lt.rim_size_m, location=lt.rim_location)
        rim_obj = bpy.context.active_object
        rim_obj.name = "Light_Rim_Studio"
        rim_obj.data.energy = lt.rim_energy_w
        rim_obj.data.color = lt.rim_color_rgb
        studio_col.objects.link(rim_obj)
        if rim_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(rim_obj)

    # 5. Top Light
    top_obj = bpy.data.objects.get("Light_Top_Studio")
    if not top_obj:
        bpy.ops.object.light_add(type="AREA", radius=4.0, location=lt.top_location)
        top_obj = bpy.context.active_object
        top_obj.name = "Light_Top_Studio"
        top_obj.data.energy = lt.top_energy_w
        top_obj.data.color = lt.top_color_rgb
        studio_col.objects.link(top_obj)
        if top_obj.name in scene.collection.objects:
            scene.collection.objects.unlink(top_obj)

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
) -> Tuple[Any, Any]:
    """Construye en Blender el texto 3D y la línea directriz orientada y anclada al componente."""
    if bpy is None:
        return (None, None)

    col = collection or bpy.context.scene.collection
    depth = (anchor_3d - cam_pos).length * 0.88
    label_engine = AdaptiveLabelsEngine(config.safe_zones, config.labels)

    # Posición 3D del texto en el plano de cámara
    text_pos_3d = label_engine.unproject_screen_uv_to_3d(
        target_screen_u,
        target_screen_v,
        depth,
        cam_pos,
        cam_target,
        config.camera.lens_mm,
        config.render_width,
        config.render_height,
        cam_obj=bpy.context.scene.camera if bpy is not None else None,
        scene=bpy.context.scene if bpy is not None else None,
    )

    # Material de etiqueta blanca luminosa
    mat_lbl = bpy.data.materials.get("Mat_AdaptiveLabel_Text")
    if not mat_lbl:
        mat_lbl = bpy.data.materials.new("Mat_AdaptiveLabel_Text")
        mat_lbl.use_nodes = True
        b = mat_lbl.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = (*config.labels.text_color_rgb, 1.0)
            if "Emission Color" in b.inputs:
                b.inputs["Emission Color"].default_value = (*config.labels.text_color_rgb, 1.0)
            if "Emission Strength" in b.inputs:
                b.inputs["Emission Strength"].default_value = config.labels.text_emission_strength

    # 1. Objeto de Texto 3D
    txt_curve = bpy.data.curves.new(f"{name}_txt_curve", type="FONT")
    txt_curve.body = text
    txt_curve.size = config.labels.font_size
    txt_curve.align_x = "CENTER"
    txt_curve.align_y = "CENTER"
    txt_curve.extrude = config.labels.extrude
    txt_curve.bevel_depth = config.labels.bevel_depth

    txt_obj = bpy.data.objects.new(f"Label_{name}", txt_curve)
    txt_obj.location = text_pos_3d

    # Orientar texto hacia la cámara (Billboard matemática estricta paralela al plano de pantalla)
    forward_cam = (cam_target - cam_pos).normalized()
    right_cam = forward_cam.cross(Vector((0, 0, 1))).normalized()
    up_cam = right_cam.cross(forward_cam).normalized()
    billboard_mat = Matrix((right_cam, up_cam, -forward_cam)).transposed()
    txt_obj.rotation_euler = billboard_mat.to_euler()
    txt_obj["role"] = "label"
    txt_obj.data.materials.append(mat_lbl)
    # Desactivar sombras de la etiqueta para evitar textos fantasma o sombras proyectadas
    txt_obj.visible_shadow = False
    col.objects.link(txt_obj)

    # 2. Línea Directriz y Punto de Anclaje
    mat_line = bpy.data.materials.get("Mat_AdaptiveLeader_Line")
    if not mat_line:
        mat_line = bpy.data.materials.new("Mat_AdaptiveLeader_Line")
        mat_line.use_nodes = True
        b = mat_line.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = (*config.labels.leader_line_color_rgb, 1.0)
            if "Emission Color" in b.inputs:
                b.inputs["Emission Color"].default_value = (*config.labels.leader_line_color_rgb, 1.0)
            if "Emission Strength" in b.inputs:
                b.inputs["Emission Strength"].default_value = config.labels.leader_line_emission

    # Esfera de anclaje discreta sobre el componente físico
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=config.labels.anchor_sphere_radius,
        location=anchor_3d,
    )
    dot_obj = bpy.context.active_object
    dot_obj.name = f"Dot_{name}"
    dot_obj["role"] = "label"
    dot_obj.visible_shadow = False
    dot_obj.data.materials.append(mat_line)
    col.objects.link(dot_obj)
    if dot_obj.name in bpy.context.scene.collection.objects and col != bpy.context.scene.collection:
        bpy.context.scene.collection.objects.unlink(dot_obj)

    # Conexión exacta al extremo correspondiente de la palabra:
    # Si la etiqueta está en la mitad derecha (u >= 0.5), la línea arranca en el extremo izquierdo.
    # Si está en la mitad izquierda (u < 0.5), la línea arranca en el extremo derecho.
    half_text_w = len(text) * config.labels.font_size * 0.31
    if target_screen_u >= 0.5:
        text_anchor = text_pos_3d - right_cam * (half_text_w + 0.02)
        shoulder_pt = text_anchor - right_cam * 0.07
    else:
        text_anchor = text_pos_3d + right_cam * (half_text_w + 0.02)
        shoulder_pt = text_anchor + right_cam * 0.07

    curve_line = bpy.data.curves.new(f"{name}_leader_curve", type="CURVE")
    curve_line.dimensions = "3D"
    curve_line.bevel_depth = config.labels.leader_line_radius
    curve_line.bevel_resolution = 4
    curve_line.use_fill_caps = True

    spline = curve_line.splines.new("BEZIER")
    spline.bezier_points.add(2)
    # Trazado técnico recto: texto -> repisa horizontal -> punto en la pieza
    pts = [text_anchor, shoulder_pt, anchor_3d]
    for i, p in enumerate(pts):
        bp = spline.bezier_points[i]
        bp.co = p
        bp.handle_left_type = "VECTOR"
        bp.handle_right_type = "VECTOR"

    line_obj = bpy.data.objects.new(f"Leader_{name}", curve_line)
    line_obj["role"] = "label"
    line_obj.visible_shadow = False
    line_obj.data.materials.append(mat_line)
    col.objects.link(line_obj)

    return (txt_obj, line_obj)
