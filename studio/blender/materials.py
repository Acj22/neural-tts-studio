"""Biblioteca de materiales estilizados tipo Maqueta Educativa (Clay / Educational Model).

Colores suaves, acabados mate plásticos y metálicos limpios, sombras suaves
y emisión para efectos de chispa y combustión en Blender 5.3+ EEVEE Next.
"""

from __future__ import annotations

try:
    import bpy
except ImportError:
    bpy = None


def hex_to_rgba(hex_str: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """Convierte un color hexadecimal en tupla RGBA normalizada [0.0, 1.0]."""
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b, alpha)
    return (0.5, 0.5, 0.5, alpha)


def get_or_create_material(
    name: str,
    base_color: tuple[float, float, float, float],
    roughness: float = 0.55,
    metallic: float = 0.0,
    alpha: float = 1.0,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> Any:
    """Crea o reutiliza un material Principled BSDF estilizado en Blender."""
    if bpy is None:
        return None

    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")

    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = base_color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha

        if emission_color and emission_strength > 0:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = emission_color
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emission_strength

    # Configuración de transparencia para EEVEE Next en caso de vidrio o gas
    if alpha < 0.99:
        mat.blend_method = "BLEND" if hasattr(mat, "blend_method") else "HASHED"
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = "HASHED"

    return mat


def setup_engine_materials() -> dict[str, Any]:
    """Instancia y devuelve la paleta completa de materiales para el motor de 4 tiempos."""
    return {
        # Bloque de motor y fondo maqueta
        "studio_floor": get_or_create_material(
            "Mat_StudioFloor",
            base_color=hex_to_rgba("#0F172A"),
            roughness=0.85,
            metallic=0.0,
        ),
        "engine_block": get_or_create_material(
            "Mat_EngineBlock",
            base_color=hex_to_rgba("#1E293B"),
            roughness=0.55,
            metallic=0.25,
        ),
        "cylinder_liner": get_or_create_material(
            "Mat_CylinderLiner",
            base_color=hex_to_rgba("#334155"),
            roughness=0.35,
            metallic=0.6,
        ),
        "cutaway_glass": get_or_create_material(
            "Mat_CutawayGlass",
            base_color=(0.2, 0.4, 0.6, 0.18),
            roughness=0.1,
            metallic=0.0,
            alpha=0.22,
        ),
        # Conjunto Móvil (Pistón, Biela, Cigüeñal)
        "piston": get_or_create_material(
            "Mat_Piston",
            base_color=hex_to_rgba("#E2E8F0"),
            roughness=0.35,
            metallic=0.45,
        ),
        "piston_rings": get_or_create_material(
            "Mat_PistonRings",
            base_color=hex_to_rgba("#F59E0B"),
            roughness=0.3,
            metallic=0.75,
        ),
        "wrist_pin": get_or_create_material(
            "Mat_WristPin",
            base_color=hex_to_rgba("#94A3B8"),
            roughness=0.2,
            metallic=0.85,
        ),
        "connecting_rod": get_or_create_material(
            "Mat_ConnectingRod",
            base_color=hex_to_rgba("#475569"),
            roughness=0.45,
            metallic=0.55,
        ),
        "rod_bearings": get_or_create_material(
            "Mat_RodBearings",
            base_color=hex_to_rgba("#D97706"),
            roughness=0.3,
            metallic=0.7,
        ),
        "crankshaft": get_or_create_material(
            "Mat_Crankshaft",
            base_color=hex_to_rgba("#38BDF8"),
            roughness=0.35,
            metallic=0.5,
        ),
        "counterweights": get_or_create_material(
            "Mat_Counterweights",
            base_color=hex_to_rgba("#0284C7"),
            roughness=0.4,
            metallic=0.55,
        ),
        # Válvulas y Distribución
        "valve_intake": get_or_create_material(
            "Mat_ValveIntake",
            base_color=hex_to_rgba("#38BDF8"),
            roughness=0.35,
            metallic=0.45,
        ),
        "valve_exhaust": get_or_create_material(
            "Mat_ValveExhaust",
            base_color=hex_to_rgba("#F97316"),
            roughness=0.35,
            metallic=0.45,
        ),
        "valve_spring": get_or_create_material(
            "Mat_ValveSpring",
            base_color=hex_to_rgba("#94A3B8"),
            roughness=0.25,
            metallic=0.8,
        ),
        # Bujía
        "spark_ceramic": get_or_create_material(
            "Mat_SparkCeramic",
            base_color=hex_to_rgba("#F8FAFC"),
            roughness=0.15,
            metallic=0.0,
        ),
        "spark_metal": get_or_create_material(
            "Mat_SparkMetal",
            base_color=hex_to_rgba("#64748B"),
            roughness=0.25,
            metallic=0.85,
        ),
        # Efectos Físicos de los 4 Tiempos (Emisión & Gas)
        "electric_spark": get_or_create_material(
            "Mat_ElectricSpark",
            base_color=(0.5, 0.9, 1.0, 1.0),
            roughness=0.1,
            emission_color=(0.3, 0.8, 1.0, 1.0),
            emission_strength=20.0,
        ),
        "flame_combustion": get_or_create_material(
            "Mat_FlameCombustion",
            base_color=(1.0, 0.4, 0.05, 0.9),
            roughness=0.2,
            emission_color=(1.0, 0.45, 0.05, 1.0),
            emission_strength=15.0,
            alpha=0.92,
        ),
        "intake_flow": get_or_create_material(
            "Mat_IntakeFlow",
            base_color=(0.2, 0.65, 1.0, 0.45),
            roughness=0.3,
            alpha=0.45,
            emission_color=(0.2, 0.65, 1.0, 1.0),
            emission_strength=2.0,
        ),
        "exhaust_flow": get_or_create_material(
            "Mat_ExhaustFlow",
            base_color=(0.35, 0.35, 0.4, 0.55),
            roughness=0.5,
            alpha=0.55,
        ),
    }
