"""Biblioteca de materiales PBR hiperrealistas para Motor 3D en Blender 5.3 (Fase 2.1 - Alto Realismo CAD).

Estilo de Ilustración Mecánica Técnica (Coverfox / Precision Engineering):
- Metales maquinados con anisotropía y micro-rugosidad (camisa rectificada, pistón de aluminio forjado, cigüeñal rectificado a espejo).
- Fundición granular de bloque con sutil relieve procedural (cast iron bump).
- Bujía con porcelana esmaltada de alto brillo (clearcoat).
- Aros de bronce nitrurado y casquillos dorados pulidos.
- Resortes helicoidales de acero de alta tensión.
- Explosión de combustión multicapa estilo Coverfox (núcleo blanco incandescente, cuerpo naranja ardiente, llamas exteriores carmesí).
- Fondo de estudio cream cálido neutro libre de sombras sucias.
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
    roughness: float = 0.35,
    metallic: float = 0.0,
    alpha: float = 1.0,
    anisotropic: float = 0.0,
    coat_weight: float = 0.0,
    coat_roughness: float = 0.05,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
    use_cast_bump: bool = False,
) -> Any:
    """Crea o actualiza un material Principled BSDF PBR avanzado en Blender 5.3."""
    if bpy is None:
        return None

    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name=name)

    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    bsdf = nodes.get("Principled BSDF")

    if not bsdf:
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")

    # Propiedades estándar del Principled BSDF
    if "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = base_color
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if "Anisotropic" in bsdf.inputs and anisotropic > 0.0:
        bsdf.inputs["Anisotropic"].default_value = anisotropic
    if "Coat Weight" in bsdf.inputs and coat_weight > 0.0:
        bsdf.inputs["Coat Weight"].default_value = coat_weight
    if "Coat Roughness" in bsdf.inputs and coat_weight > 0.0:
        bsdf.inputs["Coat Roughness"].default_value = coat_roughness

    if emission_color and emission_strength > 0.0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission_color
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength

    # Relieve procedural sutil para piezas de fundición granular (Cast Iron)
    if use_cast_bump:
        bump_node = nodes.get("Procedural_Cast_Bump")
        noise_node = nodes.get("Procedural_Cast_Noise")
        if not bump_node:
            bump_node = nodes.new("ShaderNodeBump")
            bump_node.name = "Procedural_Cast_Bump"
            bump_node.inputs["Strength"].default_value = 0.07
            bump_node.inputs["Distance"].default_value = 0.10
        if not noise_node:
            noise_node = nodes.new("ShaderNodeTexNoise")
            noise_node.name = "Procedural_Cast_Noise"
            noise_node.inputs["Scale"].default_value = 45.0
            noise_node.inputs["Detail"].default_value = 3.5
            noise_node.inputs["Roughness"].default_value = 0.70
        links.new(noise_node.outputs["Fac"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])

    # Configuración de transparencia para EEVEE
    if alpha < 0.99:
        if hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = "HASHED"

    return mat


def setup_engine_materials() -> dict[str, Any]:
    """Instancia y devuelve la biblioteca completa de materiales PBR de alto realismo."""
    return {
        # 1. Estudio de Maqueta (Fondo Slate Blue Elegante estilo Referencia CAD 2.3)
        "studio_floor": get_or_create_material(
            "Mat_StudioFloor",
            base_color=hex_to_rgba("#1E2A36"),  # Slate blue oscuro para suelo
            roughness=0.90,
            metallic=0.0,
            emission_color=hex_to_rgba("#1E2A36"),
            emission_strength=0.90,
        ),
        "studio_backdrop": get_or_create_material(
            "Mat_StudioBackdrop",
            base_color=hex_to_rgba("#253545"),  # Slate blue de la referencia
            roughness=0.95,
            metallic=0.0,
            emission_color=hex_to_rgba("#253545"),
            emission_strength=0.90,
        ),

        # 2. Bloque del Motor y Estructura Mecánica
        "engine_block": get_or_create_material(
            "Mat_EngineBlock",
            base_color=hex_to_rgba("#8E9DAE"),  # Aluminio técnico claro de fundición
            roughness=0.55,
            metallic=0.35,
            use_cast_bump=True,
        ),
        "cutaway_rim": get_or_create_material(
            "Mat_CutawayRim",
            base_color=hex_to_rgba("#B8C4D0"),  # Cara de corte seccionada: acero pulido satinado
            roughness=0.25,
            metallic=0.75,
            anisotropic=0.35,
        ),
        "manifold_pipes": get_or_create_material(
            "Mat_ManifoldPipes",
            base_color=hex_to_rgba("#1E242B"),  # Tubos oscuros de colectores de la referencia
            roughness=0.40,
            metallic=0.60,
        ),
        "oil_pan": get_or_create_material(
            "Mat_OilPan",
            base_color=hex_to_rgba("#2B3846"),  # Chapa de cárter gris azulada
            roughness=0.45,
            metallic=0.50,
        ),
        "cylinder_liner": get_or_create_material(
            "Mat_CylinderLiner",
            base_color=hex_to_rgba("#CAD4DE"),  # Camisa de acero rectificado con brillo satinado
            roughness=0.18,
            metallic=0.90,
            anisotropic=0.40,
        ),

        # 3. Conjunto Pistón de Precisión (Cobre Anodizado de Alto Impacto)
        "piston": get_or_create_material(
            "Mat_Piston",
            base_color=hex_to_rgba("#C86432"),  # Cobre / bronce anodizado cálido de la referencia
            roughness=0.22,
            metallic=0.85,
            anisotropic=0.40,
        ),
        "piston_rings": get_or_create_material(
            "Mat_PistonRings",
            base_color=hex_to_rgba("#D97706"),  # Aros de bronce nitrurado dorado de fricción
            roughness=0.18,
            metallic=0.92,
        ),
        "wrist_pin": get_or_create_material(
            "Mat_WristPin",
            base_color=hex_to_rgba("#1A2027"),  # Bulón de acero templado y rectificado a espejo
            roughness=0.12,
            metallic=0.95,
        ),

        # 4. Biela Forjada y Cojinetes
        "connecting_rod": get_or_create_material(
            "Mat_ConnectingRod",
            base_color=hex_to_rgba("#687684"),  # Bridas exteriores de acero mecanizado
            roughness=0.28,
            metallic=0.70,
        ),
        "rod_recess": get_or_create_material(
            "Mat_RodRecess",
            base_color=hex_to_rgba("#3B444C"),  # Canal en I forjado oscuro
            roughness=0.48,
            metallic=0.55,
        ),
        "rod_bearings": get_or_create_material(
            "Mat_RodBearings",
            base_color=hex_to_rgba("#F59E0B"),  # Bronce fosforoso de cojinetes pulido
            roughness=0.16,
            metallic=0.95,
        ),
        "rod_bolts": get_or_create_material(
            "Mat_RodBolts",
            base_color=hex_to_rgba("#15181C"),  # Tornillos de biela pavonados de alta resistencia
            roughness=0.18,
            metallic=0.90,
        ),

        # 5. Cigüeñal y Volante
        "crankshaft": get_or_create_material(
            "Mat_Crankshaft",
            base_color=hex_to_rgba("#4B5563"),  # Muñequilla y muñones rectificados
            roughness=0.14,
            metallic=0.95,
        ),
        "counterweights": get_or_create_material(
            "Mat_Counterweights",
            base_color=hex_to_rgba("#23282E"),  # Contrapesos en forja oscura
            roughness=0.45,
            metallic=0.65,
        ),
        "flywheel": get_or_create_material(
            "Mat_Flywheel",
            base_color=hex_to_rgba("#333B42"),  # Volante de inercia macizo
            roughness=0.35,
            metallic=0.75,
        ),

        # 6. Válvulas y Resortes Helicoidales
        "valve_intake": get_or_create_material(
            "Mat_ValveIntake",
            base_color=hex_to_rgba("#0EA5E9"),  # Válvula de admisión en aleación cian satinada
            roughness=0.25,
            metallic=0.55,
        ),
        "valve_exhaust": get_or_create_material(
            "Mat_ValveExhaust",
            base_color=hex_to_rgba("#EA580C"),  # Válvula de escape en acero térmico naranja
            roughness=0.25,
            metallic=0.55,
        ),
        "valve_spring": get_or_create_material(
            "Mat_ValveSpring",
            base_color=hex_to_rgba("#CAD4E0"),  # Alambre de acero de resorte de alta tensión
            roughness=0.18,
            metallic=0.92,
        ),
        "valve_retainer": get_or_create_material(
            "Mat_ValveRetainer",
            base_color=hex_to_rgba("#1E242B"),  # Platillo retenedor de válvula pavonado
            roughness=0.22,
            metallic=0.88,
        ),

        # 7. Bujía de Alta Precisión
        "spark_ceramic": get_or_create_material(
            "Mat_SparkCeramic",
            base_color=hex_to_rgba("#FFFFFF"),  # Porcelana blanca pura vidriada
            roughness=0.06,
            metallic=0.0,
            coat_weight=1.0,
            coat_roughness=0.04,
        ),
        "spark_metal": get_or_create_material(
            "Mat_SparkMetal",
            base_color=hex_to_rgba("#64748B"),  # Acero cincado de rosca y tuerca
            roughness=0.25,
            metallic=0.85,
        ),
        "spark_copper": get_or_create_material(
            "Mat_SparkCopper",
            base_color=hex_to_rgba("#B45309"),  # Junta de cobre de estanqueidad
            roughness=0.20,
            metallic=0.90,
        ),

        # 8. Efectos Volumétricos y Fuego Coverfox
        "electric_spark": get_or_create_material(
            "Mat_ElectricSpark",
            base_color=(0.4, 0.85, 1.0, 1.0),
            roughness=0.05,
            metallic=0.0,
            emission_color=(0.35, 0.85, 1.0, 1.0),
            emission_strength=45.0,
        ),
        "flame_outer": get_or_create_material(
            "Mat_FlameOuter",
            base_color=(0.95, 0.15, 0.05, 0.98),
            roughness=0.15,
            metallic=0.0,
            emission_color=(1.0, 0.20, 0.05, 1.0),
            emission_strength=30.0,
        ),
        "flame_mid": get_or_create_material(
            "Mat_FlameMid",
            base_color=(1.0, 0.50, 0.05, 1.0),
            roughness=0.10,
            metallic=0.0,
            emission_color=(1.0, 0.55, 0.05, 1.0),
            emission_strength=42.0,
        ),
        "flame_core": get_or_create_material(
            "Mat_FlameCore",
            base_color=(1.0, 0.98, 0.85, 1.0),
            roughness=0.05,
            metallic=0.0,
            emission_color=(1.0, 0.98, 0.80, 1.0),
            emission_strength=60.0,
        ),
        "intake_flow": get_or_create_material(
            "Mat_IntakeFlow",
            base_color=hex_to_rgba("#38BDF8", alpha=0.60),
            roughness=0.20,
            metallic=0.0,
            alpha=0.60,
            emission_color=(0.20, 0.75, 1.0, 1.0),
            emission_strength=4.0,
        ),
        "exhaust_flow": get_or_create_material(
            "Mat_ExhaustFlow",
            base_color=hex_to_rgba("#F97316", alpha=0.60),
            roughness=0.20,
            metallic=0.0,
            alpha=0.60,
            emission_color=(1.0, 0.55, 0.15, 1.0),
            emission_strength=4.0,
        ),
        "compression_gas": get_or_create_material(
            "Mat_CompressionGas",
            base_color=hex_to_rgba("#FDE047", alpha=0.50),
            roughness=0.25,
            metallic=0.0,
            alpha=0.50,
            emission_color=(1.0, 0.90, 0.30, 1.0),
            emission_strength=4.0,
        ),

        # 9. Materiales Especiales para Transmisión Automática, Refrigerador e Impresora 3D (Fase 3)
        "brass_gold": get_or_create_material(
            "Mat_BrassGold",
            base_color=hex_to_rgba("#F59E0B"),  # Latón dorado pulido
            roughness=0.18,
            metallic=0.92,
        ),
        "ring_gear_blue": get_or_create_material(
            "Mat_RingGearBlue",
            base_color=hex_to_rgba("#2563EB"),  # Corona exterior azul anodizado
            roughness=0.25,
            metallic=0.85,
        ),
        "fluid_atf": get_or_create_material(
            "Mat_FluidATF",
            base_color=hex_to_rgba("#DC2626", alpha=0.65),  # Fluido ATF rojo rubí
            roughness=0.15,
            metallic=0.10,
            alpha=0.65,
            emission_color=(0.85, 0.15, 0.15, 1.0),
            emission_strength=1.5,
        ),
        "clutch_plate": get_or_create_material(
            "Mat_ClutchPlate",
            base_color=hex_to_rgba("#475569"),  # Discos de fricción en acero templado
            roughness=0.35,
            metallic=0.75,
        ),
        "copper_coil": get_or_create_material(
            "Mat_CopperCoil",
            base_color=hex_to_rgba("#EA580C"),  # Cobre brillante para serpentines
            roughness=0.18,
            metallic=0.92,
        ),
        "white_cabinet": get_or_create_material(
            "Mat_WhiteCabinet",
            base_color=hex_to_rgba("#E2E8F0"),  # Gabinete exterior blanco perla
            roughness=0.30,
            metallic=0.15,
        ),
        "compressor_black": get_or_create_material(
            "Mat_CompressorBlack",
            base_color=hex_to_rgba("#0F172A"),  # Esmalte negro brillante del compresor
            roughness=0.20,
            metallic=0.80,
        ),
        "frost_blue": get_or_create_material(
            "Mat_FrostBlue",
            base_color=hex_to_rgba("#38BDF8"),  # Zona fría / hielo congelador
            roughness=0.45,
            metallic=0.10,
            emission_color=(0.20, 0.75, 1.0, 1.0),
            emission_strength=2.5,
        ),
        "heat_red": get_or_create_material(
            "Mat_HeatRed",
            base_color=hex_to_rgba("#EF4444"),  # Calor disipado por condensador
            roughness=0.30,
            metallic=0.10,
            emission_color=(1.0, 0.25, 0.10, 1.0),
            emission_strength=3.0,
        ),
        "vslot_black": get_or_create_material(
            "Mat_VSlotBlack",
            base_color=hex_to_rgba("#111827"),  # Perfil de aluminio V-Slot negro
            roughness=0.45,
            metallic=0.50,
        ),
        "filament_orange": get_or_create_material(
            "Mat_FilamentOrange",
            base_color=hex_to_rgba("#F97316"),  # Filamento PLA naranja neón
            roughness=0.25,
            metallic=0.05,
        ),
        "extrusion_glow": get_or_create_material(
            "Mat_ExtrusionGlow",
            base_color=hex_to_rgba("#FDBA74"),  # Plástico fundido incandescente
            roughness=0.10,
            metallic=0.0,
            emission_color=(1.0, 0.60, 0.20, 1.0),
            emission_strength=8.0,
        ),
        "pei_bed": get_or_create_material(
            "Mat_PeiBed",
            base_color=hex_to_rgba("#D97706"),  # Placa PEI dorada texturizada
            roughness=0.55,
            metallic=0.65,
        ),
    }
