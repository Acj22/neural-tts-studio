# Análisis Arquitectónico y Estratégico de Repositorios para AI Video Studio

Este documento presenta una evaluación exhaustiva de los 10 repositorios y tecnologías clave para la generación de contenido audiovisual de alta calidad, desglosando su arquitectura, requerimientos de cómputo (CPU vs GPU vs WebGL), sinergias con los módulos existentes del estudio y su combinación para producción automatizada de video vertical (9:16) y horizontal (16:9).

---

## 1. Blender MCP (GPU)
* **Repositorio:** [`ahujasid/mcp-for-blender`](https://github.com/ahujasid/mcp-for-blender)
* **Requisitos:** GPU (NVIDIA RTX recomendada para EEVEE Next / Cycles) + Python + Blender 4.x/5.x.
* **Arquitectura:**
  * **Blender Add-on:** Corre dentro de Blender y levanta un servidor de sockets local bidireccional (puerto `9876`).
  * **Servidor MCP:** Traduce llamadas de herramientas del protocolo MCP (*Model Context Protocol*) a scripts ejecutables de Blender Python (`bpy`).
* **Valor para nuestros módulos:**
  * Actualmente nuestro `Motor 3D Blender` funciona por lotes headless (`blender.exe -b --python script.py`).
  * Al integrar el bridge socket de este repositorio (`studio/blender/addon_studio_bridge.py` y `studio/blender/blender_gateway.py`), podemos inspeccionar en vivo el viewport de Blender, consultar los nombres de los objetos, ajustar materiales PBR en tiempo real y ejecutar micro-correcciones interactivas sin reiniciar la instancia de Blender.

---

## 2. lemo-opuscar (CPU)
* **Repositorio:** [`lemomo-ai/lemo-opuscar`](https://github.com/lemomo-ai/lemo-opuscar)
* **Requisitos:** CPU (Node.js / Python + Chromium sin cabeza vía Playwright/Puppeteer + FFmpeg).
* **Arquitectura:**
  * Motor de "Cine en Código" procedimental en HTML5 Canvas y CSS3.
  * Renderizado fotograma a fotograma sin pérdida de calidad (resolución nativa 1080x1920 Full HD) y composición directa con FFmpeg incrustando subtítulos ASS y audio maestro.
* **Valor para nuestros módulos:**
  * Ya es el corazón de nuestro módulo `Lemo-Opuscar` (con estilos como Paper-Cutout Diorama, Blueprint CAD, Origami y Low-Poly).
  * Garantiza 60 fps constantes en motion graphics sin artefactos de compresión ni deformaciones generativas de IA.

---

## 3. claude-animated-shorts (GPU / WebGL)
* **Repositorio:** [`mromidev/claude-animated-shorts`](https://github.com/mromidev/claude-animated-shorts)
* **Requisitos:** WebGL en navegador (aceleración GPU ligera en cliente) + Remotion / Three.js + Node.js/Python.
* **Arquitectura:**
  * Especializado en videos verticales (9:16) de 55 a 70 segundos.
  * Combina personajes 2D estilizados con contorno de tinta (*ink outlines*) dentro de dioramas 3D pintados en Three.js con movimientos de cámara continuos (*camera glides*), voces y efectos de sonido foley.
* **Valor para nuestros módulos:**
  * Es el candidato ideal para un nuevo módulo de storytelling dinámico: permite narrar historias históricas, científicas y técnicas con estética de cómic/animación de vanguardia, logrando un engagement y retención superiores a las imágenes fijas.

---

## 4. pixelfx (CPU)
* **Repositorio:** [`patch-gg/pixelfx`](https://github.com/patch-gg/pixelfx)
* **Requisitos:** CPU (código determinista puro en TypeScript/Python o Canvas).
* **Arquitectura:**
  * Más de 200 efectos visuales (VFX) procedimentales basados en código: fuego, chispas, humo, ondas de choque, rayos, auras mágicas y partículas UI.
  * Utiliza búferes duales de color y luz en lugar de pesadas hojas de sprites o texturas pre-renderizadas.
* **Valor para nuestros módulos:**
  * Se puede inyectar tanto en los lienzos Canvas de `Lemo-Opuscar` como en los overlays de `Blender 3D` y `Animated Shorts`: aporta chispas de soldadura en motores, humo de pólvora en cañones, destellos de fuego en turbinas o runas místicas en dioramas arqueológicos sin coste en VRAM.

---

## 5. react-three-rapier (GPU / WebGL)
* **Repositorio:** [`pmndrs/react-three-rapier`](https://github.com/pmndrs/react-three-rapier)
* **Requisitos:** WebGL + WebAssembly (Wasm Rapier Physics engine).
* **Arquitectura:**
  * Enlace oficial de Three.js / React Three Fiber con el motor de física de cuerpo rígido **Rapier** en Rust/Wasm.
  * Soporta colisiones en tiempo real, gravedad, articulaciones mecánicas (*joints*), dinámica de cadenas y partículas físicas.
* **Valor para nuestros módulos:**
  * Permite crear animaciones educativas donde las piezas reaccionan a leyes físicas reales: engranajes que transmiten par mecánico real, piezas que caen y encajan dinámicamente, o despieces que rebotan con elasticidad realista.

---

## 6. huashu-motion (CPU)
* **Repositorio:** [`alchaincyf/huashu-motion`](https://github.com/alchaincyf/huashu-motion)
* **Requisitos:** CPU (HTML5/CSS3 + GSAP + Playwright + FFmpeg).
* **Arquitectura:**
  * Habilidad de agente para generar videos promocionales de producto de estándar comercial y motion graphics cinéticos.
  * Permite control granular fotograma a fotograma mediante inspección de layouts vectoriales SVG y tipografía cinética.
* **Valor para nuestros módulos:**
  * Excelente para transiciones de datos numéricos en pantalla (contadores a 60 fps, gráficas cinéticas de presión/temperatura y títulos de capítulo de estética Apple).

---

## 7. Modelos Abiertos de Video en GPU: Wan 2.2 y LTX Video
* **Repositorios:** [`Wan-Video/Wan2.2`](https://github.com/Wan-Video/Wan2.2) y [`Lightricks/LTX-Video`](https://github.com/Lightricks/LTX-Video)
* **Requisitos:** GPU VRAM alta (16GB - 24GB VRAM para inferencia local con Torch / Diffusers / ComfyUI) o API remota.
* **Arquitectura:**
  * Modelos de difusión de video de última generación (DiT - Diffusion Transformers).
  * **Wan 2.2:** Destaca en coherencia temporal y movimiento cinematográfico fluido a 720p/1080p.
  * **LTX Video:** Ultrarrápido, optimizado para generar planos de acción y transiciones en segundos.
* **Valor para nuestros módulos:**
  * Complementan las secuencias procedimentales (Blender / Opuscar) generando clips fotorrealistas de transición (B-roll de época, tomas aéreas dramáticas o rostros históricos).

---

## 8. rea-video (CPU)
* **Repositorio:** [`JuneYaooo/rea-video`](https://github.com/JuneYaooo/rea-video)
* **Requisitos:** CPU (Python + OpenCV / FFmpeg + OCR).
* **Arquitectura:**
  * Herramienta de ingeniería inversa forense para videos virales.
  * Analiza cualquier MP4 de referencia toma por toma: detecta cortes de cámara, cadencia de fotogramas, texto en pantalla (OCR), paleta cromática dominante y estructura narrativa, exportando un informe estructurado (`VIDEO.md`).
* **Valor para nuestros módulos:**
  * Permite importar un video de referencia de TikTok o YouTube y generar automáticamente el plano de rodaje (*blueprint*) para replicar su ritmo visual con contenido educativo e investigación real.

---

## 9. HyperFrames (CPU)
* **Repositorio:** [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes)
* **Requisitos:** CPU (Motor de renderizado headless basado en Chromium/Playwright + Web Audio API).
* **Arquitectura:**
  * Framework de edición de video programática y determinista desarrollado por HeyGen.
  * Utiliza un modelo de línea de tiempo con escenas desacopladas, interpolaciones matemáticamente precisas (*seekable animations*) y mezcla de audio multipista.
* **Valor para nuestros módulos:**
  * Estandariza la sincronización 1:1 entre el audio de locución (TTS) y los disparadores visuales, eliminando desfases temporales y garantizando que ningún subtítulo aparezca antes o después de la frase correspondiente.

---

## 10. Earshot (CPU, "Sirve con todos")
* **Repositorio:** [`Leonxlnx/earshot`](https://github.com/Leonxlnx/earshot)
* **Requisitos:** CPU pura (Python / NumPy / SciPy + FFmpeg).
* **Arquitectura:**
  * Kit de diseño sonoro procedimental y análisis psicoacústico para agentes de IA.
  * Genera, alinea y mezcla efectos de sonido foley (whooshes de transición, impactos secos, clicks mecánicos, zumbidos ambientales, risers cinemáticos) y verifica la sincronización precisa imagen-sonido.
* **Valor para nuestros módulos:**
  * **Universal:** Resuelve de raíz la carencia de dinamismo sonoro en videos procedurales. Se conecta tanto a `Blender 3D` como a `Lemo-Opuscar` y `Animated Shorts` para que cada corte de escena, aparición de tarjeta o rotación de pieza tenga un refuerzo auditivo profesional.

---

## Sinergia de Integración: El Módulo "Animated Shorts & Sound Lab"

Combinando:
$$\text{claude-animated-shorts} + \text{react-three-rapier} + \text{pixelfx} + \text{Earshot} + \text{HyperFrames}$$

Creamos una factoría de contenidos verticales 9:16 con:
1. **Investigación y Calidad Histórica Obligatoria:** Guiones documentados, con fuentes fiables y sin inventar datos.
2. **Generación de Título:** Fórmulas de alto impacto cognitivo y retención comprobada.
3. **Escenografía Dinámica:** Personajes entintados 2D sobre mundos 3D WebGL con física Rapier y partículas PixelFX.
4. **Diseño Sonoro Integral (Earshot):** Locución neuronal sincronizada 1:1, banda sonora ambiental y foley procedimental por toma.
