# DIRECTRICES MAESTRAS PARA PIPELINE DE VIDEOS VERTICALES (9:16) ESTILO PAPER-CUT

Documento normativo de observancia obligatoria para todo guion, código de animación procedimental, diseño sonoro y renderizado de videos en formato vertical 9:16 con estética *paper-cut* (recortes de papel con borde blanco, sombra proyectada suave 2.5D y cuadrícula milimétrica).

---

## 1. Especificaciones Técnicas de Renderizado
* **Tasa de fotogramas (FPS):**
  - Renderizar a **60 fps** (o mínimo **30 fps**).
  - **PROHIBIDO USAR 24 fps** para este estilo: al tratarse de *motion graphics* con recortes nítidos, curvas de rebote (*back-out/overshoot*), contadores numéricos rápidos y paneos continuos de cámara, 24 fps genera saltos visuales (*judder*) evidentes en pantallas móviles modernas de 60 Hz y 120 Hz. 60 fps garantiza suavidad cristalina en cada micro-animación.
* **Formato y Resolución:**
  - **Vertical 9:16 nativo en 1080x1920 px** (Full HD vertical).
  - Respetar rigurosamente las zonas seguras de TikTok, Instagram Reels y YouTube Shorts:
    - *Margen superior:* Título y placas entre $Y = 120$ y $Y = 320$.
    - *Área central de acción:* $Y = 320$ a $Y = 1480$.
    - *Margen inferior seguro:* Subtítulos y CTAs situados entre $Y = 1480$ y $Y = 1720$ (evitando la barra de interfaz y botones de interacción social).

---

## 2. Sincronización Audio-Visual y Subtítulos 1:1 (Prioridad Crítica)
* **Disparadores por marca de tiempo (Timestamps exactos):**
  - Ningún cambio de escena o entrada gráfica puede ocurrir de forma arbitraria o desfasada.
  - Cada transición, tarjeta, cota o animación debe estar anclada exactamente al timestamp de inicio o final de la frase correspondiente en la locución neuronal (Edge-TTS / Kokoro).
* **Subtítulos estrictamente 1:1:**
  - Los subtítulos deben generarse a partir de la **misma cadena de texto exacta** enviada al motor de síntesis de voz (TTS) o mediante alineación directa del audio.
  - **Prohibido** emplear resúmenes, sinónimos, acrónimos no pronunciados o incluir palabras que la voz no mencione de forma literal.
* **Cierre sincronizado:**
  - Las pantallas finales (encuestas, preguntas para comentarios, botones de llamada a la acción) deben hacer su entrada (*pop-in*) en el instante exacto en que la voz formula la pregunta final, jamás antes ni solapándose con la narración del dato previo.

---

## 3. Variedad Visual por Bloque Narrativo (Cero Escenarios Monótonos)
* **Prohibido mantener el mismo escenario estático:**
  - Nunca dejar la misma ilustración central intacta durante todo el video.
* **Evolución visual cada 6 a 10 segundos:**
  - En cada bloque narrativo o cambio de tema/época, el escenario debe transformarse visiblemente:
    - **Cambio de encuadre o toma:** Acercamiento de cámara (*close-up*) a una zona específica del diorama, paneo o ángulo diferente.
    - **Nuevos elementos interactivos:** Inclusión de nuevos recortes de papel que interactúan con el diorama (personajes en silueta, vehículos de época, artefactos, maquinaria, documentos, cortes esquemáticos o vegetación).
    - **Metamorfosis temática:** Conexión orgánica entre escenas (ej. si se pasa del castillo colonial a la avenida moderna, la calzada se despliega transformando el entorno).

---

## 4. Reglas de Animación y Dinamismo (Cero Escenas Congeladas)
* **Regla de los 2 segundos:**
  - Ningún elemento ni escena puede permanecer inmóvil por más de 2 segundos. El espectador debe percibir dinamismo constante.
* **Entradas escalonadas (*Staggered Pop-In*):**
  - Prohibido hacer cortes secos donde toda la escena ya aparezca armada.
  - Los elementos deben entrar de forma secuencial: primero la base principal, 0.15s - 0.25s después los secundarios y luego etiquetas o personajes.
  - Uso obligatorio de curvas de *easing* con rebote (*overshoot / easeOutBack*), simulando pegatinas físicas que se adhieren a la pantalla en tiempo real.
* **Movimiento de cámara constante (Ken Burns Procedural):**
  - Aplicar un *zoom* lento y continuo (1% a 3%) o un reencuadre suave a lo largo de cada toma para dar sensación de tridimensionalidad y volumen.
* **Movimiento ambiental (*Idle Motion*):**
  - Todo elemento en reposo debe tener micro-animaciones en bucle según su naturaleza:
    - Vegetación: oscilación suave con $\sin(\omega t + \phi)$.
    - Banderas y telas: ondeado senoidal continuo.
    - Agua: ondas concéntricas o flujo continuo.
    - Luces / fuego: pulsos cálidos de escala o resplandor.
    - Vehículos / personajes: balanceo, suspensión o rotación de ruedas.
* **Transiciones con Causa y Efecto:**
  - Evitar tomas desconectadas. Si una escena introduce una acción (ej. un escaneo o medición) y la siguiente muestra el resultado, enlazarlas visualmente de manera fluida.

---

## 5. Datos Animados y Claridad Visual
* **Correspondencia visual estricta:**
  - Cada elemento en pantalla debe representar de forma inequívoca lo que dice el guion en ese segundo exacto. Prohibido agregar decoraciones superfluas no mencionadas por el narrador.
* **Visualización dinámica de cifras en tiempo real:**
  - Siempre que el guion mencione un dato numérico (fechas, años, población, metros de altitud o cantidades):
    - **Años y cantidades:** Contadores numéricos que giran en pantalla de $0 \to N$.
    - **Medidas físicas:** Reglas de cota vertical u horizontal que se trazan junto al objeto.
    - **Estadísticas o proporciones:** Barras de porcentaje o comparativas que crecen dinámicamente.

---

## 6. Composición y Consistencia Estética (Formato 9:16)
* **Ocupación del espacio vertical:**
  - Escalar la composición para aprovechar el área segura entre la placa superior y los subtítulos inferiores, evitando grandes bloques de fondo vacío.
* **Coherencia artesanal total (100% Paper-Cut):**
  - Todo recurso gráfico debe mantener la textura y corte de papel:
    - Borde blanco exterior limpio ($4\text{px} - 8\text{px}$ en 1080p).
    - Sombra arrojada 2.5D suave (`shadowBlur = 16-24`, `shadowOffsetY = 8-14`).
    - Paleta de color armónica sobre fondo cálido con cuadrícula milimétrica artesanal.
  - **TERMINANTEMENTE PROHIBIDO:** Usar emojis estándar del sistema operativo o gráficos rasterizados que rompan la estética de recorte físico.

---

## 7. Estructura de Guion y Retención
* **Gancho Inmediato (< 3 segundos):**
  - Prohibido abrir con introducciones lentas o fechas descriptivas (ej. *"En octubre de..."* o *"A simple vista parecería..."*).
  - Abrir directo con el dato más sorprendente, la intriga visual o la paradoja central.
* **Ritmo ágil y directo:**
  - Frases concisas, directas y con alta densidad informativa verificada.
* **Cierre interactivo:**
  - Formular una pregunta directa final para disparar comentarios, acompañada de una tarjeta interactiva de votación A vs B con pop-in al segundo exacto de la pregunta.
