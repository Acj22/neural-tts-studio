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
        # 1. Estudio de Maqueta (Fondo Cream Técnico Libre de Sombras Sucias)
        "studio_floor": get_or_create_material(
            "Mat_StudioFloor",
            base_color=hex_to_rgba("#FAF5EC"),  # Cream cálido tipo ilustración Coverfox
            roughness=0.90,
            metallic=0.0,
            emission_color=hex_to_rgba("#FAF5EC"),
            emission_strength=0.95,
        ),
        "studio_backdrop": get_or_create_material(
            "Mat_StudioBackdrop",
            base_color=hex_to_rgba("#FAF5EC"),  # Fondo cálido nítido
            roughness=0.95,
            metallic=0.0,
            emission_color=hex_to_rgba("#FAF5EC"),
            emission_strength=0.95,
        ),

        # 2. Bloque del Motor y Estructura
        "engine_block": get_or_create_material(
            "Mat_EngineBlock",
            base_color=hex_to_rgba("#24282D"),  # Fundición gris grafito oscuro de alto contraste
            roughness=0.60,
            metallic=0.15,
        ),
        "cutaway_rim": get_or_create_material(
            "Mat_CutawayRim",
            base_color=hex_to_rgba("#475569"),  # Borde biselado de sección técnica
            roughness=0.40,
            metallic=0.55,
        ),
        "cylinder_liner": get_or_create_material(
            "Mat_CylinderLiner",
            base_color=hex_to_rgba("#CAD4DE"),  # Acero cromado satinado de camisa
            roughness=0.22,
            metallic=0.85,
        ),

        # 3. Pistón y Conjunto Móvil Superior
        "piston": get_or_create_material(
            "Mat_Piston",
            base_color=hex_to_rgba("#D2D9E0"),  # Aleación de aluminio satinado de pistón
            roughness=0.28,
            metallic=0.60,
        ),
        "piston_rings": get_or_create_material(
            "Mat_PistonRings",
            base_color=hex_to_rgba("#D97706"),  # Aros de bronce nitrurado dorado
            roughness=0.22,
            metallic=0.85,
        ),
        "wrist_pin": get_or_create_material(
            "Mat_WristPin",
            base_color=hex_to_rgba("#1E242B"),  # Bulón de acero templado oscuro de alta dureza
            roughness=0.18,
            metallic=0.90,
        ),

        # 4. Biela Forjada y Cojinetes
        "connecting_rod": get_or_create_material(
            "Mat_ConnectingRod",
            base_color=hex_to_rgba("#687684"),  # Acero forjado mecanizado
            roughness=0.32,
            metallic=0.65,
        ),
        "rod_recess": get_or_create_material(
            "Mat_RodRecess",
            base_color=hex_to_rgba("#485460"),  # Canal en I forjado
            roughness=0.45,
            metallic=0.50,
        ),
        "rod_bearings": get_or_create_material(
            "Mat_RodBearings",
            base_color=hex_to_rgba("#D97706"),  # Bronce de fricción dorado pulido
            roughness=0.25,
            metallic=0.85,
        ),
        "rod_bolts": get_or_create_material(
            "Mat_RodBolts",
            base_color=hex_to_rgba("#1E242B"),  # Tornillos de biela pavonados
            roughness=0.20,
            metallic=0.85,
        ),

        # 5. Cigüeñal y Volante (Acero técnico mecanizado)
        "crankshaft": get_or_create_material(
            "Mat_Crankshaft",
            base_color=hex_to_rgba("#363E46"),  # Acero templado mecanizado
            roughness=0.38,
            metallic=0.70,
        ),
        "counterweights": get_or_create_material(
            "Mat_Counterweights",
            base_color=hex_to_rgba("#262B30"),  # Forja oscura contrastada para contrapesos
            roughness=0.45,
            metallic=0.60,
        ),
        "flywheel": get_or_create_material(
            "Mat_Flywheel",
            base_color=hex_to_rgba("#363E46"),  # Volante de inercia
            roughness=0.40,
            metallic=0.65,
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
            emission_strength=35.0,
        ),
        "flame_combustion": get_or_create_material(
            "Mat_FlameCombustion",
            base_color=(1.0, 0.35, 0.05, 0.95),
            roughness=0.15,
            metallic=0.0,
            alpha=0.95,
            emission_color=(1.0, 0.50, 0.05, 1.0),
            emission_strength=25.0,
        ),
        "flame_core": get_or_create_material(
            "Mat_FlameCore",
            base_color=(1.0, 0.95, 0.85, 1.0),
            roughness=0.1,
            metallic=0.0,
            alpha=1.0,
            emission_color=(1.0, 0.95, 0.80, 1.0),
            emission_strength=45.0,
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
