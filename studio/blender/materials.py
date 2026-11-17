"""Biblioteca de materiales estilizados tipo Maqueta Educativa (Clay / Educational Model).

Fase 2 - Perfeccionamiento:
- Paleta de colores suaves y armoniosos con acabado mate cerámico/plástico.
- Fondo de estudio claro (beige suave / gris claro neutro).
- Metales satinados sin brillos cegadores.
- Diferenciación cromática nítida de cada componente mecánico.
- Emisión estilizada suave para chispa e ignición de combustión.
"""

from __future__ import annotations

from typing import Any

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
        mat = bpy.data.materials[name]
        # Actualizar valores
        if mat.node_tree:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
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
        return mat

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

    # Configuración de transparencia para EEVEE
    if alpha < 0.99:
        if hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = "HASHED"

    return mat


def setup_engine_materials() -> dict[str, Any]:
    """Instancia y devuelve la paleta estilizada completa de maqueta técnica educativa."""
    return {
        # 1. Estudio de Maqueta (Fondo y Mesa Clara)
        "studio_floor": get_or_create_material(
            "Mat_StudioFloor",
            base_color=hex_to_rgba("#E8ECEF"),  # Gris claro neutro cálido de estudio
            roughness=0.90,
            metallic=0.0,
        ),
        "studio_backdrop": get_or_create_material(
            "Mat_StudioBackdrop",
            base_color=hex_to_rgba("#F1F5F9"),  # Fondo suave
            roughness=0.95,
            metallic=0.0,
        ),

        # 2. Bloque del Motor y Estructura
        "engine_block": get_or_create_material(
            "Mat_EngineBlock",
            base_color=hex_to_rgba("#475569"),  # Grafito mate suave
            roughness=0.65,
            metallic=0.08,
        ),
        "cutaway_rim": get_or_create_material(
            "Mat_CutawayRim",
            base_color=hex_to_rgba("#CBD5E1"),  # Borde biselado de sección técnica
            roughness=0.35,
            metallic=0.45,
        ),
        "cylinder_liner": get_or_create_material(
            "Mat_CylinderLiner",
            base_color=hex_to_rgba("#94A3B8"),  # Acero satinado de camisa
            roughness=0.40,
            metallic=0.55,
        ),

        # 3. Pistón y Conjunto Móvil Superior
        "piston": get_or_create_material(
            "Mat_Piston",
            base_color=hex_to_rgba("#F8FAFC"),  # Aluminio satinado muy claro
            roughness=0.42,
            metallic=0.30,
        ),
        "piston_rings": get_or_create_material(
            "Mat_PistonRings",
            base_color=hex_to_rgba("#D97706"),  # Cobre/bronce satinado
            roughness=0.32,
            metallic=0.65,
        ),
        "wrist_pin": get_or_create_material(
            "Mat_WristPin",
            base_color=hex_to_rgba("#64748B"),  # Bulón de acero templado
            roughness=0.25,
            metallic=0.75,
        ),

        # 4. Biela Forjada y Cojinetes
        "connecting_rod": get_or_create_material(
            "Mat_ConnectingRod",
            base_color=hex_to_rgba("#475569"),  # Acero forjado satinado mate
            roughness=0.45,
            metallic=0.40,
        ),
        "rod_bearings": get_or_create_material(
            "Mat_RodBearings",
            base_color=hex_to_rgba("#D97706"),  # Bronce de fricción dorado pulido
            roughness=0.28,
            metallic=0.75,
        ),
        "rod_bolts": get_or_create_material(
            "Mat_RodBolts",
            base_color=hex_to_rgba("#E2E8F0"),  # Tornillos de biela nítidos
            roughness=0.25,
            metallic=0.80,
        ),

        # 5. Cigüeñal y Volante (Acero técnico mecanizado, no plástico)
        "crankshaft": get_or_create_material(
            "Mat_Crankshaft",
            base_color=hex_to_rgba("#64748B"),  # Acero templado mecanizado
            roughness=0.35,
            metallic=0.60,
        ),
        "counterweights": get_or_create_material(
            "Mat_Counterweights",
            base_color=hex_to_rgba("#334155"),  # Forja oscura contrastada para contrapesos
            roughness=0.50,
            metallic=0.45,
        ),
        "flywheel": get_or_create_material(
            "Mat_Flywheel",
            base_color=hex_to_rgba("#475569"),  # Volante de inercia
            roughness=0.45,
            metallic=0.40,
        ),

        # 6. Distribución (Válvulas y Resortes)
        "valve_intake": get_or_create_material(
            "Mat_ValveIntake",
            base_color=hex_to_rgba("#06B6D4"),  # Cian cielo pastel
            roughness=0.42,
            metallic=0.22,
        ),
        "valve_exhaust": get_or_create_material(
            "Mat_ValveExhaust",
            base_color=hex_to_rgba("#F97316"),  # Naranja coral pastel
            roughness=0.42,
            metallic=0.22,
        ),
        "valve_spring": get_or_create_material(
            "Mat_ValveSpring",
            base_color=hex_to_rgba("#CBD5E1"),  # Acero de muelle helicoidal
            roughness=0.30,
            metallic=0.65,
        ),
        "valve_guide": get_or_create_material(
            "Mat_ValveGuide",
            base_color=hex_to_rgba("#64748B"),  # Guía de válvula
            roughness=0.40,
            metallic=0.50,
        ),

        # 7. Bujía
        "spark_ceramic": get_or_create_material(
            "Mat_SparkCeramic",
            base_color=hex_to_rgba("#FFFFFF"),  # Porcelana blanca mate pura
            roughness=0.18,
            metallic=0.0,
        ),
        "spark_metal": get_or_create_material(
            "Mat_SparkMetal",
            base_color=hex_to_rgba("#64748B"),  # Acero de rosca y tuerca
            roughness=0.32,
            metallic=0.70,
        ),

        # 8. Efectos Volumétricos e Indicadores Explicativos
        "electric_spark": get_or_create_material(
            "Mat_ElectricSpark",
            base_color=(0.3, 0.8, 1.0, 1.0),
            roughness=0.1,
            metallic=0.0,
            emission_color=(0.22, 0.75, 1.0, 1.0),
            emission_strength=25.0,
        ),
        "flame_combustion": get_or_create_material(
            "Mat_FlameCombustion",
            base_color=(1.0, 0.65, 0.1, 0.90),
            roughness=0.2,
            metallic=0.0,
            alpha=0.88,
            emission_color=(1.0, 0.55, 0.05, 1.0),
            emission_strength=12.0,
        ),
        "intake_flow": get_or_create_material(
            "Mat_IntakeFlow",
            base_color=hex_to_rgba("#38BDF8", alpha=0.55),
            roughness=0.2,
            metallic=0.0,
            alpha=0.55,
            emission_color=(0.2, 0.7, 1.0, 1.0),
            emission_strength=3.0,
        ),
        "exhaust_flow": get_or_create_material(
            "Mat_ExhaustFlow",
            base_color=hex_to_rgba("#FB923C", alpha=0.55),
            roughness=0.2,
            metallic=0.0,
            alpha=0.55,
            emission_color=(1.0, 0.5, 0.1, 1.0),
            emission_strength=3.0,
        ),
        "compression_gas": get_or_create_material(
            "Mat_CompressionGas",
            base_color=hex_to_rgba("#FEF08A", alpha=0.45),
            roughness=0.3,
            metallic=0.0,
            alpha=0.45,
            emission_color=(1.0, 0.9, 0.25, 1.0),
            emission_strength=3.5,
        ),
    }
