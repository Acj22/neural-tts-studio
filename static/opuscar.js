/**
 * AI VIDEO STUDIO — Módulo Lemo-Opuscar
 * Motor de Cine y Animación Procedimental 100% en Código (Canvas HTML5 / WebGL)
 * Inspirado en https://github.com/lemomo-ai/lemo-opuscar
 */

let opuscarCanvas = null;
let opuscarCtx = null;
let opuscarAnimationId = null;
let opuscarIsPlaying = true;
let opuscarCurrentTime = 0.0;
let opuscarDuration = 6.0;
let opuscarLastTimestamp = 0;
let opuscarFps = 30;
let opuscarCurrentStyle = "paper_cutout_diorama";

// Catálogo de estilos locales
const OPUSCAR_PRESETS = {
  ojo_sahara_diorama: {
    name: "Diorama Ojo del Sahara & Geología (Estructura de Richat 🌍)",
    bg: "#fbf5e8",
    draw: drawOjoSaharaCanvas,
    title: "El Rincón Más Asombroso de la Tierra: El Ojo del Sahara",
    narration: "En medio del desierto de Mauritania existe una gigantesca estructura concéntrica de 40 kilómetros visible desde el espacio: la mística Estructura de Richat."
  },
  chapultepec_diorama: {
    name: "Diorama Castillo de Chapultepec & Virreinato (Alcázar Real ★)",
    bg: "#fbf5e8",
    draw: drawChapultepecLive,
    title: "El Castillo de Chapultepec: El Único Alcázar Real de América",
    narration: "¿Sabías que en el corazón de la Ciudad de México se alza el único castillo real de monarquía europea jamás habitado en todo el continente americano?"
  },
  mayan_diorama: {
    name: "Diorama Maya & Arqueología Prehispánica (LiDAR ★)",
    bg: "#fbf5e8",
    draw: drawMayanDioramaLive,
    title: "El Secreto Oculto de México: La Ciudad Maya de Valeriana",
    narration: "En 2024, arqueólogos con tecnología láser LiDAR descubrieron Valeriana en la selva de Campeche: 6,674 estructuras prehispánicas ocultas bajo los árboles."
  },
  paper_cutout_diorama: {
    name: "Diorama de Stickers & Papel Recortado (Viral ★)",
    bg: "#fbf5e8",
    draw: drawPaperCutoutDiorama,
    title: "El Truco Biológico del Chile y la Capsaicina",
    narration: "¿Sabías que cuando comes chile en realidad no te estás quemando? Tu cuerpo cree que hay fuego y activa todas las alarmas a la vez."
  },
  blueprint_cad: {
    name: "Plano Técnico Blueprint (CAD Cianotipo)",
    bg: "#0b192c",
    draw: drawBlueprintCAD,
    title: "Turbocompresor: Esquema de Sección y Flujos",
    narration: "El compresor aspira aire atmosférico a través de la caracola fría, incrementando la densidad de oxígeno antes de entrar al cilindro."
  },
  vector_flow: {
    name: "Dinámica de Fluidos & Vórtice Vectorial",
    bg: "#030712",
    draw: drawVectorFlow,
    title: "Gradiente Térmico: Escape Caliente vs Admisión Fría",
    narration: "Los gases de escape a ochocientos grados hacen girar la turbina a más de doscientas mil revoluciones por minuto."
  },
  da_vinci_codex: {
    name: "Códice Da Vinci (Manuscrito Renacentista)",
    bg: "#f4ecd8",
    draw: drawDaVinciCodex,
    title: "Tratado de la Máquina de Fuego y Viento",
    narration: "Observad cómo el movimiento del aire engendra fuerza motriz constante, transformando el soplo en potencia mecánica."
  },
  hud_telemetry: {
    name: "HUD de Telemetría Militar & Aeroespacial",
    bg: "#020617",
    draw: drawHUDTelemetry,
    title: "Telemetría de Banco de Pruebas: 220,000 RPM",
    narration: "Presión de sobrealimentación estabilizada en dos punto dos bares. Temperatura de entrada en zona nominal."
  },
  anime_speedlines: {
    name: "Líneas de Hipervelocidad Anime",
    bg: "#09090b",
    draw: drawAnimeSpeedlines,
    title: "¡PICO DE BOOST AL MÁXIMO!",
    narration: "Cuando la válvula wastegate se cierra por completo, la turbina alcanza su régimen límite instantáneamente."
  },
  chalkboard_physics: {
    name: "Pizarra Universitaria de Física",
    bg: "#14211b",
    draw: drawChalkboardPhysics,
    title: "Ecuación de Estado y Rendimiento Volumétrico",
    narration: "La primera ley de la termodinámica dicta que la energía no se destruye: el calor del escape se transforma en presión útil."
  }
};

function initOpuscarModule() {
  opuscarCanvas = document.getElementById("opuscarCanvas");
  if (!opuscarCanvas) return;
  opuscarCtx = opuscarCanvas.getContext("2d");

  // Configurar tamaño
  resizeOpuscarCanvas();
  window.addEventListener("resize", resizeOpuscarCanvas);

  // Iniciar loop de animación determinista
  opuscarLastTimestamp = performance.now();
  requestAnimationFrame(opuscarLoop);

  // Cargar lista de estilos si existe el select
  const sel = document.getElementById("opuscarStyleSelect");
  if (sel) {
    sel.addEventListener("change", (e) => {
      setOpuscarStyle(e.target.value);
    });
  }

  // Cargar proyectos previos si los hay
  loadOpuscarStylesFromAPI();

  // Cargar y mostrar automáticamente el último video generado
  loadLastOpuscarVideo();
}

async function loadLastOpuscarVideo() {
  try {
    let videoData = null;
    // 1. Intentar cargar desde el backend el último render registrado
    try {
      const res = await fetch("/api/opuscar/last-video");
      if (res.ok) {
        const data = await res.json();
        if (data.has_video && data.video) {
          videoData = data.video;
        }
      }
    } catch (e) {
      console.warn("Error consultando último video en backend:", e);
    }

    // 2. Fallback a localStorage
    if (!videoData) {
      const local = localStorage.getItem("opuscar_last_video");
      if (local) {
        try { videoData = JSON.parse(local); } catch (e) {}
      }
    }

    if (!videoData || !videoData.video_url) return;

    // 3. Cargar en el reproductor de previsualización
    const inlineVid = document.getElementById("opuscarPreviewPlayer");
    const pTitle = document.getElementById("opuscarPreviewTitle");
    const pMeta = document.getElementById("opuscarPreviewMeta");
    const pDesc = document.getElementById("opuscarPreviewDesc");
    const dlBtn = document.getElementById("opuscarDownloadBtn");
    const openBtn = document.getElementById("opuscarOpenTabBtn");
    const modalVid = document.getElementById("opuscarModalVideo");
    const modalLink = document.getElementById("opuscarDownloadLink");

    const fullUrl = `${videoData.video_url}?t=${Date.now()}`;
    if (inlineVid) {
      inlineVid.src = fullUrl;
      inlineVid.load();
    }
    if (modalVid) modalVid.src = fullUrl;
    if (modalLink) {
      modalLink.href = videoData.video_url;
      modalLink.download = videoData.filename || "opuscar_video.mp4";
    }
    if (pTitle) pTitle.textContent = videoData.title || "Video Generado Automáticamente";
    if (pMeta) {
      const dur = videoData.duration ? `${Number(videoData.duration).toFixed(1)}s` : "60.0s";
      const fps = `${videoData.fps || 60} FPS`;
      const voice = (videoData.voice || "Dalia Neural").replace("es-MX-", "").replace("es-ES-", "");
      pMeta.textContent = `${dur} · ${fps} · ${voice} + Subtítulos Big Focus 1:1`;
    }
    if (pDesc) {
      pDesc.textContent = videoData.narration || "Animación diorama multicapa paper-cut generada automáticamente con sincronización procedural 1:1.";
    }
    if (dlBtn) {
      dlBtn.href = videoData.video_url;
      dlBtn.download = videoData.filename || "opuscar_video.mp4";
    }
    if (openBtn) {
      openBtn.href = videoData.video_url;
    }
  } catch (err) {
    console.warn("No se pudo cargar el último video de Opuscar:", err);
  }
}

function resizeOpuscarCanvas() {
  if (!opuscarCanvas) return;
  const rect = opuscarCanvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  opuscarCanvas.width = (rect.width || 640) * dpr;
  opuscarCanvas.height = (rect.height || 480) * dpr;
}

function setOpuscarStyle(styleId) {
  opuscarCurrentStyle = styleId;
  const preset = OPUSCAR_PRESETS[styleId];
  if (preset) {
    const titleInput = document.getElementById("opuscarTitleInput");
    const narrInput = document.getElementById("opuscarNarrationInput");
    if (titleInput && !titleInput.value.trim()) titleInput.value = preset.title;
    if (narrInput && !narrInput.value.trim()) narrInput.value = preset.narration;
  }
}

function opuscarLoop(now) {
  const dt = (now - opuscarLastTimestamp) / 1000;
  opuscarLastTimestamp = now;

  if (opuscarIsPlaying) {
    opuscarCurrentTime += dt;
    if (opuscarCurrentTime >= opuscarDuration) {
      opuscarCurrentTime = 0.0;
    }
  }

  renderOpuscarFrame(opuscarCurrentTime);

  // Actualizar slider y tiempo
  const slider = document.getElementById("opuscarTimeSlider");
  const timeLabel = document.getElementById("opuscarTimeLabel");
  if (slider && !slider.matches(":active")) {
    slider.value = (opuscarCurrentTime / opuscarDuration) * 100;
  }
  if (timeLabel) {
    timeLabel.textContent = `${opuscarCurrentTime.toFixed(2)}s / ${opuscarDuration.toFixed(1)}s`;
  }

  requestAnimationFrame(opuscarLoop);
}

function renderOpuscarFrame(t) {
  if (!opuscarCanvas || !opuscarCtx) return;
  const ctx = opuscarCtx;
  const w = opuscarCanvas.width;
  const h = opuscarCanvas.height;

  const preset = OPUSCAR_PRESETS[opuscarCurrentStyle] || OPUSCAR_PRESETS.blueprint_cad;
  ctx.fillStyle = preset.bg;
  ctx.fillRect(0, 0, w, h);

  const title = (document.getElementById("opuscarTitleInput")?.value || preset.title);
  preset.draw(ctx, w, h, t, opuscarDuration, title);
}

// -------------------------------------------------------------
// DIBUJADO PROCEDURAL DE ESTILOS (CANVAS)
// -------------------------------------------------------------

function drawMayaDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo de selva tropical profunda en degradado
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#081c15");
  grad.addColorStop(0.5, "#1b4332");
  grad.addColorStop(1, "#081c15");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  // Placa superior de diorama arqueológico
  const pw = Math.min(w * 0.9, 440);
  const ph = 50;
  const px = (w - pw) / 2;
  const py = 25;
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.4)";
  ctx.shadowBlur = 10;
  ctx.shadowOffsetY = 4;
  ctx.fillStyle = "#ffffff";
  ctx.beginPath(); ctx.roundRect(px - 3, py - 3, pw + 6, ph + 6, 12); ctx.fill();
  ctx.fillStyle = "#fdfbf7";
  ctx.beginPath(); ctx.roundRect(px, py, pw, ph, 10); ctx.fill();
  ctx.strokeStyle = "#15803d";
  ctx.lineWidth = 2.5;
  ctx.stroke();
  ctx.fillStyle = "#15803d";
  ctx.font = 'bold 12px "Arial Black", sans-serif';
  ctx.textAlign = "center";
  ctx.fillText("🌿 CAMPECHE: SELVA IMPENETRABLE", w / 2, py + 22);
  ctx.fillStyle = "#0f172a";
  ctx.font = 'bold 10px sans-serif';
  ctx.fillText(title.toUpperCase().slice(0, 48), w / 2, py + 38);
  ctx.restore();

  // Pirámide maya central estilo diorama de papel
  const cx = w / 2;
  const cy = h * 0.58;
  const steps = 5;
  const baseW = w * 0.65;
  const baseH = 22;

  // Sombra y silueta de pirámide
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.5)";
  ctx.shadowBlur = 14;
  ctx.shadowOffsetY = 8;
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.moveTo(cx - baseW / 2 - 8, cy + 50);
  ctx.lineTo(cx - baseW * 0.22 - 6, cy - steps * baseH - 30);
  ctx.lineTo(cx + baseW * 0.22 + 6, cy - steps * baseH - 30);
  ctx.lineTo(cx + baseW / 2 + 8, cy + 50);
  ctx.closePath();
  ctx.fill();

  // Peldaños escalonados de piedra caliza
  for (let s = 0; s < steps; s++) {
    const sw = baseW - (s * (baseW * 0.12));
    const sy = cy - (s * baseH);
    ctx.fillStyle = s % 2 === 0 ? "#52796f" : "#354f52";
    ctx.fillRect(cx - sw / 2, sy, sw, baseH - 2);
    ctx.strokeStyle = "#84a98c";
    ctx.lineWidth = 1;
    ctx.strokeRect(cx - sw / 2, sy, sw, baseH - 2);
  }
  // Templo superior
  const topY = cy - steps * baseH;
  ctx.fillStyle = "#e5e5e5";
  ctx.fillRect(cx - 36, topY - 26, 72, 26);
  ctx.fillStyle = "#1e293b";
  ctx.fillRect(cx - 14, topY - 20, 28, 20); // Puerta
  ctx.restore();

  // Dron con rayo láser LiDAR
  const droneY = 110 + Math.sin(t * 3) * 6;
  const droneX = cx + Math.sin(t * 2) * 60;
  // Haz láser cian translúcido
  ctx.fillStyle = "rgba(6, 182, 212, 0.18)";
  ctx.beginPath();
  ctx.moveTo(droneX, droneY + 12);
  ctx.lineTo(droneX - 160, cy + 40);
  ctx.lineTo(droneX + 160, cy + 40);
  ctx.closePath();
  ctx.fill();

  // Línea de barrido LiDAR
  const scanY = (cy - 100) + ((t * 80) % 180);
  ctx.strokeStyle = "#22d3ee";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(cx - baseW * 0.55, scanY);
  ctx.lineTo(cx + baseW * 0.55, scanY);
  ctx.stroke();

  // Cuerpo del Dron
  ctx.fillStyle = "#ffffff";
  ctx.beginPath(); ctx.ellipse(droneX, droneY, 44, 14, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#0284c7";
  ctx.beginPath(); ctx.ellipse(droneX, droneY, 38, 10, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#f97316";
  ctx.beginPath(); ctx.arc(droneX + 12, droneY, 6, 0, Math.PI * 2); ctx.fill();
}

function drawOjoSaharaCanvas(ctx, w, h, t, dur, title) {
  // Fondo de papel crema / arena del desierto
  ctx.fillStyle = '#fbf5e8';
  ctx.fillRect(0, 0, w, h);

  // Cuadrícula topográfica desértica
  ctx.strokeStyle = 'rgba(215, 195, 160, 0.35)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior estilo paper-cut con borde blanco y sombra
  ctx.save();
  ctx.fillStyle = 'rgba(180, 150, 110, 0.4)';
  ctx.beginPath(); ctx.roundRect(24, 24, w - 48, 64, 14); ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#b45309';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('GEOLOGÍA // ESTRUCTURA DE RICHAT (MAURITANIA)', 38, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'El Ojo del Sahara').slice(0, 38).toUpperCase(), 38, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.52;

  // Dunas de arena del desierto (capas en abanico)
  ctx.save();
  ctx.fillStyle = '#e2c59b';
  ctx.beginPath();
  ctx.ellipse(cx, cy + 90, w * 0.46, 120, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // Anillos concéntricos de la Estructura de Richat en perspectiva elíptica 2.5D
  const rings = [
    { rx: w * 0.42, ry: 130, color: '#f3e5cb', stroke: '#cbb085', lw: 10 },
    { rx: w * 0.35, ry: 105, color: '#ebd0a5', stroke: '#b89260', lw: 12 },
    { rx: w * 0.28, ry: 80,  color: '#c29d6a', stroke: '#8c6436', lw: 14 },
    { rx: w * 0.20, ry: 58,  color: '#8b5a2b', stroke: '#5c3814', lw: 12 },
    { rx: w * 0.12, ry: 36,  color: '#4a2c11', stroke: '#2e1806', lw: 10 }
  ];

  ctx.save();
  // Sombra proyectada del domo
  ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
  ctx.beginPath();
  ctx.ellipse(cx, cy + 18, w * 0.44, 136, 0, 0, Math.PI * 2);
  ctx.fill();

  // Borde blanco paper-cut alrededor de la estructura
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.ellipse(cx, cy, w * 0.44, 136, 0, 0, Math.PI * 2);
  ctx.fill();

  rings.forEach((r) => {
    ctx.fillStyle = r.color;
    ctx.strokeStyle = r.stroke;
    ctx.lineWidth = r.lw;
    ctx.beginPath();
    ctx.ellipse(cx, cy, r.rx, r.ry, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  });

  // Núcleo central / domo ígneo
  const corePulse = Math.sin(t * 3.0) * 3;
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.ellipse(cx, cy, 22 + corePulse, 14 + corePulse * 0.6, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#0284c7';
  ctx.beginPath();
  ctx.ellipse(cx, cy, 18 + corePulse, 10 + corePulse * 0.6, 0, 0, Math.PI * 2);
  ctx.fill();

  // Escaneo orbital radar satelital (línea giratoria)
  const scanAngle = (t * 1.5) % (Math.PI * 2);
  const scanLen = w * 0.40;
  ctx.strokeStyle = 'rgba(2, 132, 199, 0.6)';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(scanAngle) * scanLen, cy + Math.sin(scanAngle) * (scanLen * 0.32));
  ctx.stroke();

  // Cota y etiqueta técnica flotante "40 KM DIÁMETRO"
  const tagY = cy - 145 + Math.sin(t * 2.5) * 5;
  ctx.fillStyle = 'rgba(0,0,0,0.15)';
  ctx.beginPath(); ctx.roundRect(cx - 95, tagY + 4, 190, 36, 10); ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(cx - 97, tagY - 2, 194, 40, 12); ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.beginPath(); ctx.roundRect(cx - 95, tagY, 190, 36, 10); ctx.fill();
  ctx.fillStyle = '#38bdf8';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('DIÁMETRO: 40 KM • VISIBLE DESDE EL ESPACIO', cx, tagY + 22);

  ctx.restore();
}

function detectOpuscarArchetype(text) {
  const low = (text || "").toLowerCase();
  if (["escuadron", "escuadrón", "piloto", "caza", "avion", "avión", "aereo", "aéreo", "guerra", "201", "aguila", "águila", "militar"].some(k => low.includes(k))) return "aviation";
  if (["nieve", "helada", "frio", "frío", "clima", "tormenta", "invierno", "polar"].some(k => low.includes(k))) return "snow_weather";
  if (low.includes("sahara") || low.includes("richat") || low.includes("mauritania")) return "ojo_sahara";
  if (low.includes("chapultepec") || low.includes("alcazar") || low.includes("maximiliano") || low.includes("carlota")) return "chapultepec";
  if (low.includes("maya") || low.includes("campeche") || low.includes("valeriana") || low.includes("lidar") || low.includes("piramide") || low.includes("sakil")) return "mayan";
  if (["mar", "oceano", "isla", "barco", "buque", "flannan", "celeste", "nemo", "agua", "laguna", "submarino", "fosa", "pacifico", "atlantico", "bermuda", "naufragio", "iceberg", "sentinel", "triangulo", "puerto"].some(k => low.includes(k))) return "oceanic";
  if (["tierra", "pozo", "kola", "mina", "cueva", "cristal", "naica", "fuego", "darvaza", "volcan", "montana", "montaña", "everest", "abismo", "salar", "hielo", "lava", "crater", "terremoto", "geolog", "centralia"].some(k => low.includes(k))) return "geological";
  if (["espacio", "planeta", "galaxia", "orbita", "agujero", "negro", "wow", "senal", "señal", "estrella", "satelite", "satélite", "universo", "cosmos", "nasa", "astron", "marte", "luna", "telescopio"].some(k => low.includes(k))) return "cosmic";
  if (["ciudad", "templo", "muralla", "monumento", "torre", "palacio", "catacumba", "paris", "historia", "roma", "coliseo", "antigu", "arquit", "tubos", "hospital", "castaneda", "castañeda"].some(k => low.includes(k))) return "architectural";
  return "mystery";
}

function drawAviationDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo de cielo y papel cálido
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior estilo paper-cut
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#b45309';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('AVIACIÓN DE GUERRA // ESCUADRÓN 201', 36, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'Águilas Aztecas').slice(0, 36).toUpperCase(), 36, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.52;

  // Nubes pasando a velocidad
  ctx.fillStyle = '#ffffff';
  for (let i = 0; i < 3; i++) {
    const nx = ((t * 120 + i * 260) % (w + 200)) - 100;
    const ny = cy - 140 + i * 70;
    ctx.beginPath(); ctx.ellipse(nx, ny, 60, 20, 0, 0, Math.PI * 2); ctx.fill();
  }

  // Caza P-47 en vuelo
  const pitch = Math.sin(t * 3.2) * 12;
  const bx = cx;
  const by = cy + pitch;

  // Alas
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.ellipse(bx, by + 20, 210, 36, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#475569';
  ctx.beginPath(); ctx.ellipse(bx, by + 20, 204, 32, 0, 0, Math.PI * 2); ctx.fill();

  // Escarapelas tricolor
  for (const rx of [bx - 120, bx + 120]) {
    ctx.fillStyle = '#16a34a'; ctx.beginPath(); ctx.arc(rx, by + 20, 18, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(rx, by + 20, 12, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#dc2626'; ctx.beginPath(); ctx.arc(rx, by + 20, 6, 0, Math.PI * 2); ctx.fill();
  }

  // Fuselaje
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.ellipse(bx, by - 20, 42, 105, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#334155';
  ctx.beginPath(); ctx.ellipse(bx, by - 20, 38, 100, 0, 0, Math.PI * 2); ctx.fill();

  // Cabina
  ctx.fillStyle = '#38bdf8';
  ctx.beginPath(); ctx.ellipse(bx, by - 30, 22, 38, 0, 0, Math.PI * 2); ctx.fill();

  // Hélice
  const propAng = t * 30.0;
  ctx.strokeStyle = '#fbbf24';
  ctx.lineWidth = 5;
  for (let p = 0; p < 3; p++) {
    const a = propAng + p * (Math.PI * 2 / 3);
    ctx.beginPath();
    ctx.moveTo(bx, by - 120);
    ctx.lineTo(bx + Math.cos(a) * 90, (by - 120) + Math.sin(a) * 90);
    ctx.stroke();
  }
}

function drawSnowWeatherDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo de invierno oscuro
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(186, 230, 253, 0.15)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#0284c7';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('METEOROLOGÍA // HISTORIA DOCUMENTADA', 36, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'Nevada Histórica').slice(0, 36).toUpperCase(), 36, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.52;

  // Ciudad nevada
  for (let i = -2; i <= 2; i++) {
    const bx = cx + i * 90;
    const bh = 140 + Math.abs(i) * 30;
    ctx.fillStyle = '#334155';
    ctx.fillRect(bx - 35, cy + 120 - bh, 70, bh);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(bx - 40, cy + 120 - bh - 8, 80, 14);
  }

  // Copos de nieve animados
  ctx.fillStyle = '#ffffff';
  for (let s = 0; s < 40; s++) {
    const sy = ((t * 80 + s * 45) % (h * 0.7)) + (h * 0.15);
    const sx = (s * 37 + Math.sin(t * 3.0 + s) * 20) % w;
    ctx.beginPath(); ctx.arc(sx, sy, 3 + (s % 3), 0, Math.PI * 2); ctx.fill();
  }
}

function drawOceanicDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo azul marino profundo con sonar
  ctx.fillStyle = '#0c2131';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#0e7490';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('EXPLORACIÓN // OCÉANO & PUNTOS REMOTOS', 36, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'Misterio Oceánico').slice(0, 36).toUpperCase(), 36, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.52;

  // Olas escalonadas de papel
  const waves = [
    { col: '#0e7490', y: cy + 90, phase: 0 },
    { col: '#083344', y: cy + 40, phase: 1.5 },
    { col: '#04222f', y: cy - 10, phase: 3.0 }
  ];
  waves.reverse().forEach((wv) => {
    ctx.save();
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let x = 0; x <= w; x += 30) {
      const y = wv.y + Math.sin(t * 2.5 + wv.phase + x * 0.015) * 14 - 3;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.fill();

    ctx.fillStyle = wv.col;
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let x = 0; x <= w; x += 30) {
      const y = wv.y + Math.sin(t * 2.5 + wv.phase + x * 0.015) * 14;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.fill();
    ctx.restore();
  });

  // Navío / Barco estilo paper-cut con balanceo
  const shipY = cy - 40 + Math.sin(t * 2.8) * 10;
  const shipRot = Math.sin(t * 2.0) * 0.06;
  ctx.save();
  ctx.translate(cx, shipY);
  ctx.rotate(shipRot);
  // Casco blanco sticker
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.moveTo(-110, 0); ctx.lineTo(110, 0); ctx.lineTo(70, 48); ctx.lineTo(-70, 48);
  ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#e11d48';
  ctx.beginPath();
  ctx.moveTo(-105, 3); ctx.lineTo(105, 3); ctx.lineTo(66, 44); ctx.lineTo(-66, 44);
  ctx.closePath(); ctx.fill();

  // Velas
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(-3, -90, 6, 90);
  ctx.beginPath(); ctx.moveTo(0, -85); ctx.lineTo(60, -50); ctx.lineTo(0, -15); ctx.fill();
  ctx.fillStyle = '#f8fafc';
  ctx.beginPath(); ctx.moveTo(2, -80); ctx.lineTo(54, -50); ctx.lineTo(2, -20); ctx.fill();
  ctx.restore();

  // Cota técnica
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(cx - 100, cy + 140, 200, 36, 10); ctx.fill();
  ctx.fillStyle = '#082f49';
  ctx.beginPath(); ctx.roundRect(cx - 98, cy + 142, 196, 32, 8); ctx.fill();
  ctx.fillStyle = '#38bdf8';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('PROFUNDIDAD: >4,000 m', cx, cy + 162);
  ctx.textAlign = 'left';
}

function drawGeologicalDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo ocre volcánico / abisal
  ctx.fillStyle = '#1c120d';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(249, 115, 22, 0.15)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#c2410c';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('GEOLOGÍA // ABISMOS & PROFUNDIDADES TERRESTRES', 36, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'Enigma Geológico').slice(0, 36).toUpperCase(), 36, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.52;

  // Estratos rocosos
  const strata = [
    { col: '#78350f', y: cy + 110 },
    { col: '#9a3412', y: cy + 50 },
    { col: '#b45309', y: cy - 10 },
    { col: '#d97706', y: cy - 70 }
  ];
  strata.forEach((st) => {
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(cx - w * 0.44 - 4, st.y - 4, w * 0.88 + 8, 48);
    ctx.fillStyle = st.col;
    ctx.fillRect(cx - w * 0.44, st.y, w * 0.88, 40);
  });

  // Pozo vertical con pulso de calor
  const pulse = 0.5 + 0.5 * Math.sin(t * 4.0);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(cx - 28, cy - 100, 56, 240);
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(cx - 24, cy - 96, 48, 232);
  ctx.fillStyle = `rgb(249, ${Math.floor(115 * pulse)}, 22)`;
  ctx.fillRect(cx - 12, cy - 90, 24, 220);

  // Cota técnica
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(cx - 100, cy + 160, 200, 36, 10); ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.beginPath(); ctx.roundRect(cx - 98, cy + 162, 196, 32, 8); ctx.fill();
  ctx.fillStyle = '#fb923c';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('SONDEO: 12,262 m // +180°C', cx, cy + 182);
  ctx.textAlign = 'left';
}

function drawCosmicDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo espacio profundo
  ctx.fillStyle = '#080a18';
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 20; i++) {
    const sx = ((i * 137.5) % w);
    const sy = ((i * 219.3) % h);
    ctx.fillStyle = `rgba(255, 255, 255, ${0.4 + 0.6 * Math.sin(t * 3.0 + i)})`;
    ctx.beginPath(); ctx.arc(sx, sy, 2, 0, Math.PI * 2); ctx.fill();
  }

  // Placa superior
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#7e22ce';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('ASTRONOMÍA // ENIGMAS DEL ESPACIO PROFUNDO', 36, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'Enigma Cósmico').slice(0, 36).toUpperCase(), 36, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.50;

  // Anillos orbitales
  [180, 130, 90].forEach((r) => {
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.ellipse(cx, cy, r, r * 0.45, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = '#c084fc'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(cx, cy, r, r * 0.45, 0, 0, Math.PI * 2); ctx.stroke();
  });

  // Cuerpo celeste central
  const pulse = Math.sin(t * 2.5) * 4;
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.arc(cx, cy, 66 + pulse, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#581c87';
  ctx.beginPath(); ctx.arc(cx, cy, 62 + pulse, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#9333ea';
  ctx.beginPath(); ctx.arc(cx, cy, 45 + pulse, 0, Math.PI * 2); ctx.fill();

  // Cota técnica
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(cx - 100, cy + 140, 200, 36, 10); ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.beginPath(); ctx.roundRect(cx - 98, cy + 142, 196, 32, 8); ctx.fill();
  ctx.fillStyle = '#d8b4fe';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('RETÍCULA: ENIGMA CÓSMICO', cx, cy + 162);
  ctx.textAlign = 'left';
}

function drawArchitecturalDioramaCanvas(ctx, w, h, t, dur, title) {
  // Fondo cálido plano
  ctx.fillStyle = '#f8f5eb';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.25)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#4338ca';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('ARQUITECTURA // MONUMENTOS HISTÓRICOS', 36, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'Monumento Histórico').slice(0, 36).toUpperCase(), 36, 64);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.52;

  // Base y columnata
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(cx - w * 0.40 - 4, cy + 90 - 4, w * 0.80 + 8, 48);
  ctx.fillStyle = '#cbd5e1';
  ctx.fillRect(cx - w * 0.40, cy + 90, w * 0.80, 40);

  const numCols = 6;
  const colW = 24;
  const span = w * 0.70;
  const startX = cx - span / 2;
  for (let i = 0; i < numCols; i++) {
    const colX = startX + (i * (span - colW) / (numCols - 1));
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(colX - 3, cy - 70 - 3, colW + 6, 166);
    ctx.fillStyle = '#f1f5f9';
    ctx.fillRect(colX, cy - 70, colW, 160);
  }

  // Frontón superior
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.moveTo(cx - w * 0.38 - 4, cy - 70);
  ctx.lineTo(cx, cy - 140 - 4);
  ctx.lineTo(cx + w * 0.38 + 4, cy - 70);
  ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#cbd5e1';
  ctx.beginPath();
  ctx.moveTo(cx - w * 0.38, cy - 70);
  ctx.lineTo(cx, cy - 140);
  ctx.lineTo(cx + w * 0.38, cy - 70);
  ctx.closePath(); ctx.fill();

  // Cota técnica
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(cx - 100, cy + 150, 200, 36, 10); ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.beginPath(); ctx.roundRect(cx - 98, cy + 152, 196, 32, 8); ctx.fill();
  ctx.fillStyle = '#818cf8';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('ESTRUCTURA PATRIMONIAL', cx, cy + 172);
  ctx.textAlign = 'left';
}

function drawMysteryArchiveCanvas(ctx, w, h, t, dur, title) {
  // Motor Multi-Escena 2.5D Paper-Cut Diorama en tiempo real para cualquier tema nuevo
  const narrEl = document.getElementById('opuscarNarrationInput');
  const rawNarr = (narrEl && narrEl.value) ? narrEl.value : (title || 'Investigación Documental');
  let paras = rawNarr.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
  if (paras.length < 4) {
    const sents = rawNarr.split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(Boolean);
    if (sents.length >= 4) paras = sents;
  }
  const numScenes = Math.max(4, Math.min(8, paras.length || 8));
  const sceneDur = Math.max(2.5, (dur || 20) / numScenes);
  const sceneIdx = Math.floor(t / sceneDur) % numScenes;
  const localT = t % sceneDur;
  const activeText = paras[sceneIdx] || title || '';

  // Fondo papel craft con retícula sutil
  ctx.fillStyle = '#fbf5e8';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(218, 206, 184, 0.45)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 36) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 36) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Nubes paper-cut flotantes
  const drawStickerCloud = (cx0, cy0, sc) => {
    ctx.save();
    ctx.fillStyle = 'rgba(198, 185, 165, 0.55)';
    ctx.beginPath(); ctx.roundRect(cx0 - 38 * sc + 3, cy0 - 10 * sc + 4, 76 * sc, 24 * sc, 12 * sc); ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); ctx.roundRect(cx0 - 38 * sc, cy0 - 10 * sc, 76 * sc, 24 * sc, 12 * sc); ctx.fill();
    ctx.beginPath(); ctx.arc(cx0 - 14 * sc, cy0 - 10 * sc, 15 * sc, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx0 + 10 * sc, cy0 - 13 * sc, 18 * sc, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  };
  drawStickerCloud(((70 + t * 14) % (w + 120)) - 60, h * 0.20, 0.85);
  drawStickerCloud(((w - 60 - t * 10) % (w + 120)), h * 0.27, 0.7);

  // Badge superior derecho con año o cifra extraída del párrafo (sin placas superpuestas invasivas)
  const yearMatch = activeText.match(/\b(1[5-9]\d{2}|20[0-3]\d)\b/);
  const badgeVal = yearMatch ? yearMatch[1] : `ESC 0${sceneIdx + 1}`;
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(w - 118, 24, 102, 46, 12); ctx.fill();
  ctx.fillStyle = '#991b1b';
  ctx.beginPath(); ctx.roundRect(w - 115, 27, 96, 40, 10); ctx.fill();
  ctx.fillStyle = '#fef08a';
  ctx.font = 'bold 14px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(badgeVal, w - 67, 46);
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 8px sans-serif';
  ctx.fillText(yearMatch ? 'AÑO DOCUMENTADO' : 'ACTO VISUAL', w - 67, 60);
  ctx.restore();

  const cx = w / 2;
  const cy = h * 0.50;

  const drawSceneDiorama = (mode, sScale) => {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(sScale, sScale);
    ctx.translate(-cx, -cy);

    if (mode === 0) {
      // ESCENA 1: Panorama Desierto / Horizonte 2.5D con Sol, Dunas, Cactus y Antena
      const pulse = Math.sin(t * 3) * 4;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.arc(cx, cy - 55, 48 + pulse, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#f59e0b';
      ctx.beginPath(); ctx.arc(cx, cy - 55, 43 + pulse, 0, Math.PI * 2); ctx.fill();

      // Dunas en capas con borde blanco sticker
      const dunes = [
        { y: cy + 5, col: '#d97706' },
        { y: cy + 38, col: '#b45309' },
        { y: cy + 72, col: '#92400e' }
      ];
      dunes.forEach((d, idx) => {
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.roundRect(cx - w * 0.42 - 3, d.y - 3, w * 0.84 + 6, 48, 14); ctx.fill();
        ctx.fillStyle = d.col;
        ctx.beginPath(); ctx.roundRect(cx - w * 0.42, d.y, w * 0.84, 42, 12); ctx.fill();
      });

      // Torre de radio con ondas
      ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(cx + 55, cy + 5); ctx.lineTo(cx + 70, cy - 65); ctx.lineTo(cx + 85, cy + 5); ctx.stroke();
      for (let r = 1; r <= 3; r++) {
        const rad = ((t * 25 + r * 14) % 45);
        ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(cx + 70, cy - 65, rad, 0, Math.PI * 2); ctx.stroke();
      }
    } else if (mode === 1) {
      // ESCENA 2: Mapa Cartográfico Paralelo 27° N + Rosa de los Vientos
      const mw = w * 0.78, mh = 190;
      ctx.fillStyle = 'rgba(180,165,140,0.6)';
      ctx.beginPath(); ctx.roundRect(cx - mw / 2 + 5, cy - mh / 2 + 6, mw, mh, 16); ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.roundRect(cx - mw / 2 - 4, cy - mh / 2 - 4, mw + 8, mh + 8, 18); ctx.fill();
      ctx.fillStyle = '#f4e7ce';
      ctx.beginPath(); ctx.roundRect(cx - mw / 2, cy - mh / 2, mw, mh, 14); ctx.fill();

      // Paralelo 27° punteado y ruta animada
      ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath(); ctx.moveTo(cx - mw * 0.42, cy - 10); ctx.lineTo(cx + mw * 0.42, cy - 10); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#991b1b'; ctx.font = 'bold 10px sans-serif';
      ctx.fillText('PARALELO 27° N // VÉRTICE MAPIMÍ', cx - mw * 0.38, cy - 18);

      // Pin pulsante
      const pr = 12 + Math.sin(t * 5) * 4;
      ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(cx + 15, cy - 10, pr, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = '#dc2626';
      ctx.beginPath(); ctx.arc(cx + 15, cy - 10, 6, 0, Math.PI * 2); ctx.fill();
    } else if (mode === 2) {
      // ESCENA 3: Impacto Cohete Athena / Meteorito Allende en Portal Nocturno
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.arc(cx, cy, 102, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#0f172a';
      ctx.beginPath(); ctx.arc(cx, cy, 96, 0, Math.PI * 2); ctx.fill();

      // Estela de fuego y proyectil
      const off = Math.sin(t * 6) * 4;
      ctx.strokeStyle = '#f97316'; ctx.lineWidth = 10;
      ctx.beginPath(); ctx.moveTo(cx - 55, cy - 55); ctx.lineTo(cx + 15 + off, cy + 15 + off); ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.arc(cx + 22 + off, cy + 22 + off, 20, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#ef4444';
      ctx.beginPath(); ctx.arc(cx + 22 + off, cy + 22 + off, 16, 0, Math.PI * 2); ctx.fill();
    } else if (mode === 3) {
      // ESCENA 4: Brújula Magnética Descontrolada + Osciloscopio
      const cw = w * 0.78, ch = 195;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.roundRect(cx - cw / 2 - 4, cy - ch / 2 - 4, cw + 8, ch + 8, 18); ctx.fill();
      ctx.fillStyle = '#0f172a';
      ctx.beginPath(); ctx.roundRect(cx - cw / 2, cy - ch / 2, cw, ch, 14); ctx.fill();

      // Brújula izquierda
      const bx = cx - cw * 0.22, by = cy - 15;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.arc(bx, by, 44, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fef3c7';
      ctx.beginPath(); ctx.arc(bx, by, 39, 0, Math.PI * 2); ctx.fill();
      const ang = t * 4.2 + Math.sin(t * 7) * 1.1;
      ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx + Math.cos(ang) * 30, by + Math.sin(ang) * 30); ctx.stroke();

      // Onda de osciloscopio derecha
      ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 2.5;
      ctx.beginPath();
      for (let i = 0; i < 90; i += 3) {
        const wx = cx + 5 + i;
        const wy = by + Math.sin(t * 8 + i * 0.22) * 20;
        if (i === 0) ctx.moveTo(wx, wy); else ctx.lineTo(wx, wy);
      }
      ctx.stroke();
    } else if (mode === 4) {
      // ESCENA 5: Corte Geológico de Estratos y Magnetita
      const layers = [
        { name: '01. ARENA DESÉRTICA', col: '#d97706', y: cy - 68 },
        { name: '02. SEDIMENTO MARINO FÓSIL', col: '#b45309', y: cy - 18 },
        { name: '03. YACIMIENTO DE MAGNETITA (Fe3O4)', col: '#475569', y: cy + 32 }
      ];
      layers.forEach(l => {
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.roundRect(cx - w * 0.38 - 3, l.y - 3, w * 0.76 + 6, 42, 10); ctx.fill();
        ctx.fillStyle = l.col;
        ctx.beginPath(); ctx.roundRect(cx - w * 0.38, l.y, w * 0.76, 36, 8); ctx.fill();
        ctx.fillStyle = '#ffffff'; ctx.font = 'bold 10px sans-serif';
        ctx.fillText(l.name, cx - w * 0.34, l.y + 22);
      });
    } else {
      // ESCENA 6: Contraste Mito vs Ciencia / Medalla Documental
      const cardW = w * 0.36, cardH = 155;
      // Tarjeta Mito
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.roundRect(cx - cardW - 12, cy - cardH / 2 - 3, cardW + 6, cardH + 6, 14); ctx.fill();
      ctx.fillStyle = '#581c87';
      ctx.beginPath(); ctx.roundRect(cx - cardW - 9, cy - cardH / 2, cardW, cardH, 12); ctx.fill();
      ctx.fillStyle = '#e9d5ff'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText('MITO POPULAR', cx - cardW / 2 - 9, cy - 35);
      ctx.fillStyle = '#ffffff'; ctx.font = 'bold 11px sans-serif';
      ctx.fillText('ANOMALÍA / OVNI', cx - cardW / 2 - 9, cy + 15);

      // Tarjeta Ciencia
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.roundRect(cx + 6, cy - cardH / 2 - 3, cardW + 6, cardH + 6, 14); ctx.fill();
      ctx.fillStyle = '#065f46';
      ctx.beginPath(); ctx.roundRect(cx + 9, cy - cardH / 2, cardW, cardH, 12); ctx.fill();
      ctx.fillStyle = '#a7f3d0'; ctx.font = 'bold 10px sans-serif';
      ctx.fillText('CIENCIA REAL', cx + cardW / 2 + 9, cy - 35);
      ctx.fillStyle = '#ffffff'; ctx.font = 'bold 11px sans-serif';
      ctx.fillText('MAGNETITA + SOLAR', cx + cardW / 2 + 9, cy + 15);
      ctx.textAlign = 'left';
    }
    ctx.restore();
  };

  const transDur = 0.45;
  const isTrans = localT > (sceneDur - transDur);
  if (isTrans) {
    const tau = (localT - (sceneDur - transDur)) / transDur;
    const s = tau * tau * (3 - 2 * tau);
    // Escena saliente con suavizado Hermite
    ctx.save();
    ctx.globalAlpha = 1 - s;
    drawSceneDiorama(sceneIdx % 6, 1.0 - 0.04 * s);
    ctx.restore();
    // Escena entrante con suavizado Hermite
    ctx.save();
    ctx.globalAlpha = s;
    drawSceneDiorama((sceneIdx + 1) % 6, 0.96 + 0.04 * s);
    ctx.restore();
  } else {
    const pop = sceneIdx === 0 ? Math.min(1, localT / 0.45) : 1.0;
    const sScale = 0.85 + 0.15 * pop;
    drawSceneDiorama(sceneIdx % 6, sScale);
  }
}

function drawPixelFXAmbientParticles(ctx, w, h, t, accentColor = "rgba(245, 158, 11, 0.4)") {
  ctx.save();
  for (let i = 0; i < 22; i++) {
    const seed = i * 137.5;
    const px = ((Math.sin(seed + t * 0.4) * 0.45 + 0.5) * w);
    const py = (((seed * 29.3 + t * 50) % (h * 0.75)) + h * 0.12);
    const rad = 1.5 + (Math.sin(seed * 2.2 + t * 2.0) + 1.0) * 1.4;
    ctx.fillStyle = accentColor;
    ctx.beginPath();
    ctx.arc(px, py, rad, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawRollingCounterBadge(ctx, x, y, label, targetNum, unit, t, duration = 3.2) {
  ctx.save();
  const normT = Math.min(1.0, Math.max(0.0, t / duration));
  const easeVal = 1 - Math.pow(1 - normT, 3);
  const currentVal = Math.round(targetNum * easeVal);

  ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(x, y, 164, 46, 10);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#94a3b8';
  ctx.font = 'bold 9px sans-serif';
  ctx.fillText(label.toUpperCase(), x + 12, y + 16);

  ctx.fillStyle = '#fbbf24';
  ctx.font = 'bold 16px "Courier New", monospace';
  const formatted = currentVal.toLocaleString() + ' ' + (unit || '');
  ctx.fillText(formatted, x + 12, y + 36);
  ctx.restore();
}

function drawPaperCutoutDiorama(ctx, w, h, t, dur, title) {
  const archetype = detectOpuscarArchetype(title);
  if (archetype === "aviation") drawAviationDioramaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "snow_weather") drawSnowWeatherDioramaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "ojo_sahara") drawOjoSaharaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "chapultepec") drawChapultepecLive(ctx, w, h, t, dur, title);
  else if (archetype === "mayan") drawMayaDioramaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "oceanic") drawOceanicDioramaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "geological") drawGeologicalDioramaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "cosmic") drawCosmicDioramaCanvas(ctx, w, h, t, dur, title);
  else if (archetype === "architectural") drawArchitecturalDioramaCanvas(ctx, w, h, t, dur, title);
  else drawMysteryArchiveCanvas(ctx, w, h, t, dur, title);

  // Insignia dinámica con odómetro numérico según contexto
  if (archetype === "aviation") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Misiones Voladas", 59, "operativas", t);
  } else if (archetype === "snow_weather") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Temperatura Mínima", -4, "°C", t);
  } else if (archetype === "chapultepec") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Año de Construcción", 1785, "d.C.", t);
  } else if (archetype === "oceanic") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Profundidad Abisal", 11034, "metros", t);
  } else if (archetype === "mayan") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Antigüedad Estelar", 3200, "años", t);
  } else if (archetype === "ojo_sahara") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Diámetro Geológico", 40, "km", t);
  } else if (archetype === "cosmic") {
    drawRollingCounterBadge(ctx, 24, h - 86, "Distancia Orbital", 384400, "km", t);
  }

  // Efecto ambiental de partículas procedimentales (PixelFX)
  drawPixelFXAmbientParticles(ctx, w, h, t);
}

function drawChapultepecLive(ctx, w, h, t, dur, title) {
  // Fondo de papel crema
  ctx.fillStyle = '#fbf5e8';
  ctx.fillRect(0, 0, w, h);
  // Cuadrícula sutil
  ctx.strokeStyle = 'rgba(180, 160, 130, 0.2)';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa superior estilo paper-cut
  ctx.save();
  ctx.fillStyle = 'rgba(180, 165, 145, 0.5)';
  ctx.beginPath(); ctx.roundRect(24, 24, w - 48, 64, 14); ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(20, 20, w - 40, 64, 14); ctx.fill();
  ctx.fillStyle = '#b45309';
  ctx.font = 'bold 11px sans-serif';
  ctx.fillText('HISTORIA DE MÉXICO // ALCÁZAR REAL', 38, 42);
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 14px sans-serif';
  ctx.fillText((title || 'El Castillo de Chapultepec').slice(0, 38).toUpperCase(), 38, 64);
  ctx.restore();

  // Cerro del Chapulín
  const cx = w / 2;
  const cy = h * 0.65;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.fillStyle = 'rgba(160, 140, 115, 0.4)';
  ctx.beginPath(); ctx.ellipse(0, 20, w * 0.44, 90, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.ellipse(0, 14, w * 0.43, 86, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#16a34a';
  ctx.beginPath(); ctx.ellipse(0, 10, w * 0.42, 82, 0, 0, Math.PI * 2); ctx.fill();

  // Castillo de Chapultepec en miniatura
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(-120, -110, 240, 110, 12); ctx.fill();
  ctx.fillStyle = '#f8fafc';
  ctx.beginPath(); ctx.roundRect(-116, -106, 232, 102, 10); ctx.fill();

  // Torreón y bandera
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(-35, -150, 70, 50);
  ctx.fillStyle = '#e2e8f0';
  ctx.fillRect(-32, -148, 64, 46);

  // Bandera ondeante
  const fWave = Math.sin(t * 6.0) * 3;
  ctx.fillStyle = '#64748b';
  ctx.fillRect(-2, -180, 4, 34);
  ctx.fillStyle = '#16a34a';
  ctx.fillRect(2, -180 + fWave, 10, 18);
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(12, -180 + fWave, 10, 18);
  ctx.fillStyle = '#dc2626';
  ctx.fillRect(22, -180 + fWave, 10, 18);

  // Arcadas neoclásicas
  for (let i = -80; i <= 80; i += 28) {
    ctx.fillStyle = '#1e293b';
    ctx.beginPath(); ctx.roundRect(i - 9, -50, 18, 38, [8, 8, 2, 2]); ctx.fill();
  }

  // Medidor dinámico de altitud
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(-80, 40, 160, 32, 8); ctx.fill();
  ctx.fillStyle = '#b45309';
  ctx.font = 'bold 12px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('2,325 M S.N.M.', 0, 61);
  ctx.textAlign = 'left';

  ctx.restore();
}

function drawMayanDioramaLive(ctx, w, h, t, dur, title) {
  return drawMayaDioramaCanvas(ctx, w, h, t, dur, title);
}

function drawBlueprintCAD(ctx, w, h, t, dur, title) {
  const lowTitle = (title || "").toLowerCase();
  const isMech = ["turbo", "compresor", "valvula", "piston", "motor", "rpm", "boost", "mecanic", "cad", "cilindro"].some(k => lowTitle.includes(k));
  if (!isMech) {
    if (lowTitle.includes("sahara") || lowTitle.includes("richat") || lowTitle.includes("mauritania") || lowTitle.includes("desierto") || lowTitle.includes("cráter")) {
      drawOjoSaharaCanvas(ctx, w, h, t, dur, title);
    } else if (lowTitle.includes("maya") || lowTitle.includes("campeche") || lowTitle.includes("valeriana") || lowTitle.includes("lidar")) {
      drawMayaDioramaCanvas(ctx, w, h, t, dur, title);
    } else if (lowTitle.includes("chapultepec") || lowTitle.includes("castillo") || lowTitle.includes("alcazar") || lowTitle.includes("maximiliano")) {
      drawChapultepecLive(ctx, w, h, t, dur, title);
    } else {
      drawPaperCutoutDiorama(ctx, w, h, t, dur, title);
    }
    return;
  }
  const cyan = "#00d2ff";
  const grid = "#18304e";
  const yellow = "#ffde59";
  const white = "#e0f2fe";

  // Cuadrícula milimétrica
  ctx.strokeStyle = grid;
  ctx.lineWidth = 1;
  const step = 40;
  ctx.beginPath();
  for (let x = 0; x < w; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
  for (let y = 0; y < h; y += step) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
  ctx.stroke();

  // Marco exterior técnico
  ctx.strokeStyle = cyan;
  ctx.lineWidth = 3;
  ctx.strokeRect(20, 20, w - 40, h - 40);

  // Cajetín
  ctx.fillStyle = yellow;
  ctx.font = "bold 13px monospace";
  ctx.fillText("LEMO-OPUSCAR // BLUEPRINT CAD", 35, 45);
  ctx.fillStyle = white;
  ctx.font = "14px monospace";
  ctx.fillText(title.toUpperCase(), 35, 70);

  const cx = w / 2;
  const cy = h / 2;
  const rot = t * 6.0;

  // Eje central
  ctx.fillStyle = "#1e3e62";
  ctx.strokeStyle = cyan;
  ctx.lineWidth = 2;
  ctx.fillRect(cx - 90, cy - 14, 180, 28);
  ctx.strokeRect(cx - 90, cy - 14, 180, 28);

  // Volutas
  ctx.beginPath();
  ctx.arc(cx - 60, cy, 75, Math.PI * 0.4, Math.PI * 1.6);
  ctx.stroke();

  ctx.strokeStyle = "#ff5a46";
  ctx.beginPath();
  ctx.arc(cx + 60, cy, 70, -Math.PI * 0.6, Math.PI * 0.6);
  ctx.stroke();

  // Álabes compresor
  ctx.strokeStyle = cyan;
  for (let i = 0; i < 8; i++) {
    const a = rot + (i * Math.PI * 2 / 8);
    const x1 = cx - 60 + Math.cos(a) * 12;
    const y1 = cy + Math.sin(a) * 12;
    const x2 = cx - 60 + Math.cos(a + 0.4) * 65;
    const y2 = cy + Math.sin(a + 0.4) * 65;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  // Cotas
  ctx.strokeStyle = yellow;
  ctx.fillStyle = yellow;
  ctx.font = "11px monospace";
  ctx.fillText("Ø 52.4 mm", cx - 95, cy - 85);
  ctx.beginPath();
  ctx.moveTo(cx - 95, cy - 80);
  ctx.lineTo(cx - 25, cy - 80);
  ctx.stroke();

  const rpm = Math.floor(140000 + Math.sin(t * 3) * 60000);
  ctx.fillStyle = cyan;
  ctx.font = "bold 12px monospace";
  ctx.fillText(`RÉGIMEN: ${rpm.toLocaleString()} RPM`, 35, h - 35);
}

function drawVectorFlow(ctx, w, h, t, dur, title) {
  const cx = w / 2;
  const cy = h / 2;
  const n = 80;

  for (let i = 0; i < n; i++) {
    const phase = (t * 1.2 + (i * 0.08)) % 1.0;
    const r = 30 + phase * (w * 0.35);
    const theta = (i * 0.5) + (phase * 3 * Math.PI);
    const px = cx + Math.cos(theta) * r;
    const py = cy + Math.sin(theta) * r * 0.8;

    ctx.fillStyle = phase < 0.5 ? "#38bdf8" : "#ef4444";
    ctx.beginPath();
    ctx.arc(px, py, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, 35, 0, Math.PI * 2);
  ctx.stroke();

  ctx.fillStyle = "#38bdf8";
  ctx.font = "bold 13px monospace";
  ctx.fillText("DINÁMICA DE FLUIDOS VECTORIAL", 30, 45);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(title, 30, 70);
}

function drawDaVinciCodex(ctx, w, h, t, dur, title) {
  const sepia = "#4a3525";
  const faded = "#8c6b4e";

  ctx.strokeStyle = sepia;
  ctx.lineWidth = 2;
  ctx.strokeRect(20, 20, w - 40, h - 40);

  const cx = w / 2;
  const cy = h / 2;
  const rot = t * 1.5;

  ctx.strokeStyle = faded;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let a = 0; a < 720; a += 10) {
    const rad = (a * Math.PI / 180) + rot;
    const r = 8 * Math.exp(0.003 * a);
    const x = cx + Math.cos(rad) * r;
    const y = cy + Math.sin(rad) * r;
    if (a === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();

  ctx.fillStyle = sepia;
  ctx.font = "italic 15px Georgia, serif";
  ctx.fillText("Tratato dell'aria et del moto perpetuo", 35, 45);
  ctx.font = "13px Georgia, serif";
  ctx.fillText(title, 35, 70);
}

function drawHUDTelemetry(ctx, w, h, t, dur, title) {
  const green = "#10b981";
  const cyan = "#06b6d4";
  const cx = w / 2;
  const cy = h / 2;

  ctx.strokeStyle = green;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, 90, 0, Math.PI * 2);
  ctx.stroke();

  ctx.strokeStyle = cyan;
  ctx.lineWidth = 3;
  const rot = t * 3;
  ctx.beginPath();
  ctx.arc(cx, cy, 110, rot, rot + 1.8);
  ctx.stroke();

  // Cruz
  ctx.beginPath();
  ctx.moveTo(cx - 20, cy); ctx.lineTo(cx + 20, cy);
  ctx.moveTo(cx, cy - 20); ctx.lineTo(cx, cy + 20);
  ctx.stroke();

  ctx.fillStyle = cyan;
  ctx.font = "bold 13px monospace";
  ctx.fillText("HUD TELEMETRÍA // OPUSCAR", 30, 45);
  ctx.fillStyle = green;
  ctx.font = "12px monospace";
  ctx.fillText(`BOOST: ${(1.8 + 0.5 * Math.sin(t*2)).toFixed(2)} BAR · STATUS: NOMINAL`, 30, 70);
}

function drawAnimeSpeedlines(ctx, w, h, t, dur, title) {
  const cx = w / 2;
  const cy = h / 2;
  const n = 36;
  ctx.strokeStyle = "#ffffff";

  for (let i = 0; i < n; i++) {
    const a = (i * Math.PI * 2 / n);
    const r1 = 80 + (Math.sin(t * 20 + i) * 30);
    const r2 = Math.max(w, h);
    ctx.lineWidth = (i % 2 === 0) ? 3 : 1;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
    ctx.lineTo(cx + Math.cos(a) * r2, cy + Math.sin(a) * r2);
    ctx.stroke();
  }

  ctx.fillStyle = "#f59e0b";
  ctx.font = "900 18px Impact, sans-serif";
  ctx.fillText("¡SOBREALIMENTACIÓN PURA!", cx - 110, cy);
}

function drawChalkboardPhysics(ctx, w, h, t, dur, title) {
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 14px monospace";
  ctx.fillText("UNIVERSITAS // TERMODINÁMICA", 30, 45);
  ctx.font = "13px monospace";
  ctx.fillText("P·V = n·R·T   ΔU = Q - W", 30, 75);
  ctx.fillText("η = 1 - (T_c / T_h)", 30, 105);

  const cx = w / 2;
  const cy = h / 2 + 20;
  ctx.strokeStyle = "#fef08a";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, 60, 0, Math.PI * 2);
  ctx.stroke();

  ctx.fillStyle = "#fef08a";
  ctx.fillText(title, 30, h - 35);
}

// -------------------------------------------------------------
// CONTROLES DE LA INTERFAZ Y RENDERIZADO MP4
// -------------------------------------------------------------

function toggleOpuscarPlay() {
  opuscarIsPlaying = !opuscarIsPlaying;
  const btn = document.getElementById("btnOpuscarPlay");
  if (btn) btn.textContent = opuscarIsPlaying ? "⏸ Pausar" : "▶ Reproducir";
}

function scrubOpuscarTimeline(val) {
  opuscarCurrentTime = (val / 100) * opuscarDuration;
  renderOpuscarFrame(opuscarCurrentTime);
}

async function renderOpuscarVideo() {
  const selVal = document.getElementById("opuscarStyleSelect")?.value;
  const style = opuscarCurrentStyle || selVal || "paper_cutout_diorama";
  const title = document.getElementById("opuscarTitleInput")?.value || "Animación Técnica";
  const narr = document.getElementById("opuscarNarrationInput")?.value || "";
  const voice = document.getElementById("opuscarVoiceSelect")?.value || "es-MX-DaliaNeural";
  const fmt = document.getElementById("opuscarFormatSelect")?.value || "9:16";

  const btn = document.getElementById("btnRenderOpuscar");
  const progBox = document.getElementById("opuscarProgressBarContainer");
  const progText = document.getElementById("opuscarProgressText");
  const progBar = document.getElementById("opuscarProgressBar");
  const errBox = document.getElementById("opuscarErrorBox");

  if (errBox) { errBox.classList.add("hidden"); errBox.textContent = ""; }
  if (progBox) progBox.classList.remove("hidden");
  if (btn) btn.disabled = true;

  if (progText) progText.textContent = "Sintetizando locución con Edge TTS...";
  if (progBar) progBar.style.width = "30%";

  try {
    const payload = {
      style_id: style,
      title: title,
      narration: narr,
      voice: voice,
      is_vertical: fmt === "9:16",
      fps: 60
    };

    if (progText) progText.textContent = "Generando cuadros de animación procedimental en función de t...";
    if (progBar) progBar.style.width = "60%";

    const res = await fetch("/api/opuscar/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error en el render de Lemo-Opuscar.");
    }

    const data = await res.json();
    if (progBar) progBar.style.width = "100%";
    if (progText) progText.textContent = "¡Video compilado exitosamente!";

    // Guardar en almacenamiento local para recordar siempre el último video
    try {
      localStorage.setItem("opuscar_last_video", JSON.stringify(data));
    } catch (e) {}

    // Cargar en visor modal y reproductor inline
    const modal = document.getElementById("opuscarVideoModal");
    const vid = document.getElementById("opuscarModalVideo");
    const link = document.getElementById("opuscarDownloadLink");
    const inlineVid = document.getElementById("opuscarPreviewPlayer");
    const lastVideoCard = document.getElementById("opuscarLastVideoCard");

    const cacheBuster = `?t=${Date.now()}`;
    const fullVidUrl = `${data.video_url}${cacheBuster}`;

    if (inlineVid) {
      inlineVid.src = fullVidUrl;
      inlineVid.load();
      inlineVid.play().catch(() => {});
    }
    if (vid) {
      vid.src = fullVidUrl;
      vid.load();
      vid.play().catch(() => {});
    }
    if (lastVideoCard) {
      lastVideoCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (link) {
      link.href = data.video_url;
      link.download = data.filename;
    }
    const dlBtn = document.getElementById("opuscarDownloadBtn");
    const openBtn = document.getElementById("opuscarOpenTabBtn");
    const pTitle = document.getElementById("opuscarPreviewTitle");
    const pMeta = document.getElementById("opuscarPreviewMeta");
    const pDesc = document.getElementById("opuscarPreviewDesc");

    // Deseleccionar botones de showcase fijos
    ["btnShowcaseSahara", "btnShowcaseChapultepec", "btnShowcaseMaya", "btnShowcaseChile"].forEach((id) => {
      const b = document.getElementById(id);
      if (b) b.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1";
    });

    if (dlBtn) { dlBtn.href = data.video_url; dlBtn.download = data.filename; }
    if (openBtn) { openBtn.href = data.video_url; }
    if (pTitle) { pTitle.textContent = data.title || title; }
    if (pMeta) {
      const durLabel = data.duration ? `${Number(data.duration).toFixed(1)}s` : "60.0s";
      const fpsLabel = `${data.fps || 60} FPS`;
      const voiceLabel = (data.voice || voice || "Dalia Neural").replace("es-MX-", "").replace("es-ES-", "");
      pMeta.textContent = `${durLabel} · ${fpsLabel} · ${voiceLabel} + Subtítulos Big Focus 1:1`;
    }
    if (pDesc) {
      pDesc.textContent = data.narration || narr || "Animación diorama multicapa paper-cut generada proceduralmente con sincronización 1:1 de audio, subtítulos y elementos visuales.";
    }
    if (modal) modal.classList.remove("hidden");

    setTimeout(() => { if (progBox) progBox.classList.add("hidden"); }, 2500);
  } catch (err) {
    if (errBox) {
      errBox.textContent = err.message;
      errBox.classList.remove("hidden");
    }
    if (progBox) progBox.classList.add("hidden");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function selectOpuscarShowcase(type) {
  const vid = document.getElementById("opuscarPreviewPlayer");
  const title = document.getElementById("opuscarPreviewTitle");
  const meta = document.getElementById("opuscarPreviewMeta");
  const desc = document.getElementById("opuscarPreviewDesc");
  const dl = document.getElementById("opuscarDownloadBtn");
  const tab = document.getElementById("opuscarOpenTabBtn");
  const btnSahara = document.getElementById("btnShowcaseSahara");
  const btnChap = document.getElementById("btnShowcaseChapultepec");
  const btnMaya = document.getElementById("btnShowcaseMaya");
  const btnChile = document.getElementById("btnShowcaseChile");
  const modalVid = document.getElementById("opuscarModalVideo");
  const modalLink = document.getElementById("opuscarDownloadLink");

  if (type === 'sahara') {
    const url = "/projects/opuscar_ojo_sahara_diorama/opuscar_ojo_sahara_diorama_1080x1920.mp4";
    if (vid) { vid.src = url; vid.load(); vid.play().catch(() => {}); }
    if (title) title.textContent = "🌍 El Rincón Más Asombroso de la Tierra: El Ojo del Sahara";
    if (meta) meta.textContent = "60.0s · 60 FPS · Dalia Neural + Subtítulos Big Focus 1:1";
    if (desc) desc.textContent = "Animación diorama geológico de papel recortado: dunas del desierto de Mauritania, anillos concéntricos en perspectiva elíptica 2.5D de la Estructura de Richat (40 km), domo intrusivo central, radar orbital satelital y subtítulos progresivos 1:1.";
    if (dl) { dl.href = url; dl.download = "ojo_sahara_diorama_9_16.mp4"; }
    if (tab) { tab.href = url; }
    if (modalVid) { modalVid.src = `${url}?t=${Date.now()}`; }
    if (modalLink) { modalLink.href = url; modalLink.download = "ojo_sahara_diorama_9_16.mp4"; }
    if (btnSahara) { btnSahara.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 transition flex items-center gap-1"; }
    if (btnChap) { btnChap.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnMaya) { btnMaya.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnChile) { btnChile.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
  } else if (type === 'chapultepec') {
    const url = "/projects/opuscar_chapultepec/chapultepec_diorama_9_16.mp4";
    if (vid) { vid.src = url; vid.load(); vid.play().catch(() => {}); }
    if (title) title.textContent = "🏰 El Castillo de Chapultepec: El Único Alcázar Real de América";
    if (meta) meta.textContent = "88.0s · 60 FPS · Dalia Neural + Vals Imperial + Subtítulos Big Focus 1:1";
    if (desc) desc.textContent = "Animación diorama multicapa paper-cut: Cerro del Chapulín, alcázar neoclásico con reloj ornamental, bandera ondeante en tiempo real, cota vertical animada a 2,325 m s.n.m., Paseo de la Reforma con carruaje imperial de Maximiliano y Carlota, y votación final A vs B en los comentarios.";
    if (dl) { dl.href = url; dl.download = "chapultepec_diorama_9_16.mp4"; }
    if (tab) { tab.href = url; }
    if (modalVid) { modalVid.src = `${url}?t=${Date.now()}`; }
    if (modalLink) { modalLink.href = url; modalLink.download = "chapultepec_diorama_9_16.mp4"; }
    if (btnSahara) { btnSahara.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnChap) { btnChap.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 transition flex items-center gap-1"; }
    if (btnMaya) { btnMaya.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnChile) { btnChile.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
  } else if (type === 'maya') {
    const url = "/projects/ciudad_maya_diorama/ciudad_maya_diorama_9_16.mp4";
    if (vid) { vid.src = url; vid.load(); vid.play().catch(() => {}); }
    if (title) title.textContent = "🏛️ El Secreto Oculto de México: La Ciudad Maya de Campeche";
    if (meta) meta.textContent = "45.0s · Dalia Neural + SFX Láser LiDAR + Selva Prehispánica + Subtítulos Big Focus";
    if (desc) desc.textContent = "Animación diorama de papel recortado en 5 escenas coreografiadas: selva tropical de Campeche, barrido láser LiDAR descubriendo más de 6,000 estructuras ocultas, metrópoli clásica de Sakil con acrópolis y sacbéob, glifos mayas flotantes de jade (K'IN, AJAW, CH'EN, YAX) y votación interactiva \"¿Hay más ciudades ocultas?\".";
    if (dl) { dl.href = url; dl.download = "ciudad_maya_diorama_9_16.mp4"; }
    if (tab) { tab.href = url; }
    if (modalVid) { modalVid.src = `${url}?t=${Date.now()}`; }
    if (modalLink) { modalLink.href = url; modalLink.download = "ciudad_maya_diorama_9_16.mp4"; }
    if (btnSahara) { btnSahara.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnChap) { btnChap.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnMaya) { btnMaya.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 transition flex items-center gap-1"; }
    if (btnChile) { btnChile.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
  } else {
    const url = "/projects/chile_diorama_perfeccionado/chile_diorama_9_16.mp4";
    if (vid) { vid.src = url; vid.load(); vid.play().catch(() => {}); }
    if (title) title.textContent = "🌶️ ¿Fuego Real? El Truco del Chile y la Capsaicina";
    if (meta) meta.textContent = "38.3s · Dalia Neural + SFX Latin Funk + Subtítulos Big Focus en Zona Segura";
    if (desc) desc.textContent = "Animación estilo diorama de papel recortado con gradas masivas de vigilantes TRPV1, pila de fiesta taquera, subtítulos grandes en zona segura y diseño sonoro completo (música Latin Funk + efectos especiales).";
    if (dl) { dl.href = url; dl.download = "chile_diorama_9_16.mp4"; }
    if (tab) { tab.href = url; }
    if (modalVid) { modalVid.src = `${url}?t=${Date.now()}`; }
    if (modalLink) { modalLink.href = url; modalLink.download = "chile_diorama_9_16.mp4"; }
    if (btnSahara) { btnSahara.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnChap) { btnChap.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
    if (btnChile) { btnChile.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 transition flex items-center gap-1"; }
    if (btnMaya) { btnMaya.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1"; }
  }
}

function closeOpuscarVideoModal() {
  const modal = document.getElementById("opuscarVideoModal");
  const vid = document.getElementById("opuscarModalVideo");
  if (vid) vid.pause();
  if (modal) modal.classList.add("hidden");
}

async function loadOpuscarStylesFromAPI() {
  try {
    const res = await fetch("/api/opuscar/styles");
    if (!res.ok) return;
    const data = await res.json();
    const sel = document.getElementById("opuscarStyleSelect");
    if (sel && data.styles) {
      sel.innerHTML = "";
      data.styles.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = `${s.name} [${s.badge}]`;
        if (s.id === opuscarCurrentStyle) opt.selected = true;
        sel.appendChild(opt);
      });
    }
  } catch (e) {
    console.warn("Error cargando estilos de Lemo-Opuscar:", e);
  }
}

// Catálogo de Sugerencias Temáticas para el Buscador de Guiones Virales
const OPUSCAR_SEARCH_SUGGESTIONS = {
  historia_mexico: [
    "El río de mercurio líquido descubierto bajo Teotihuacán",
    "El misterio del Tesoro Perdido de Moctezuma en la Noche Triste",
    "La ciudad maya descubierta con láser LiDAR en la selva de Campeche",
    "Los túneles secretos y la ciudad oculta bajo el Centro de la CDMX",
    "La Cueva de los Cristales Gigantes de Naica en Chihuahua",
    "La Zona del Silencio en Durango: anomalías magnéticas y meteoritos",
    "El caníbal de la Guerrero: el caso criminal que conmocionó a México",
    "La verdadera historia de la Isla de las Muñecas en Xochimilco"
  ],
  misterio: [
    "El misterio del Paso Dyatlov en los Montes Urales",
    "El Manuscrito Voynich: el libro que ningún supercomputador descifró",
    "La desaparición inexplicable de los tres fareros de las Islas Flannan",
    "El misterio del barco Mary Celeste encontrado intacto sin tripulación",
    "El Pozo Superprofundo de Kola y los sonidos del fondo de la Tierra",
    "La Señal Wow! y los enigmas no resueltos del espacio profundo"
  ],
  terror: [
    "La Casa de los Tubos en Monterrey: la tragedia que detuvo la obra",
    "El Hospital Psiquiátrico La Castañeda: palacio de la locura en México",
    "El barco fantasma SS Ourang Medan y su aterrador mensaje SOS",
    "Las Catacumbas prohibidas de París y las salas secretas sin mapa",
    "El pueblo fantasma de Centralia donde el fuego arde bajo tierra",
    "El caso de la casa embrujada de Cañitas en la Ciudad de México"
  ],
  lugares_mundo: [
    "La Puerta al Infierno en Turkmenistán: el cráter de fuego de Darvaza",
    "El Ojo del Sahara: la gigantesca estructura concéntrica de Mauritania",
    "La Isla Sentinel del Norte: la isla más aislada y peligrosa del planeta",
    "El Punto Nemo: el lugar del planeta más alejado de cualquier humano",
    "El Salar de Uyuni en Bolivia: el espejo natural más grande del mundo",
    "Las cuevas de hielo luminiscentes de Islandia"
  ]
};

async function onOpuscarSearchCategoryChange(forceRefresh = false) {
  const catEl = document.getElementById("opuscarSearchCategory");
  const chipsContainer = document.getElementById("opuscarTopicChips");
  if (!catEl || !chipsContainer) return;

  const category = catEl.value || "historia_mexico";
  chipsContainer.innerHTML = `<span class="text-[10px] text-indigo-400 animate-pulse">Cargando temas dinámicos...</span>`;

  try {
    const res = await fetch(`/api/topics/diverse?category=${encodeURIComponent(category)}&count=10&refresh=${forceRefresh}`);
    if (res.ok) {
      const data = await res.json();
      if (data.status === "success" && data.topics && data.topics.length > 0) {
        chipsContainer.innerHTML = "";
        data.topics.forEach((tObj) => {
          const topic = tObj.title || tObj;
          const icon = tObj.icon || "•";
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-amber-500/20 border border-slate-700 hover:border-amber-500/50 text-[11px] text-slate-300 hover:text-amber-200 transition text-left truncate max-w-xs flex items-center gap-1";
          btn.innerHTML = `<span>${icon}</span> <span class="truncate">${topic}</span>`;
          btn.title = topic;
          btn.onclick = () => {
            selectOpuscarTopic(topic);
          };
          chipsContainer.appendChild(btn);
        });
        return;
      }
    }
  } catch (err) {
    console.warn("Fallo cargando temas dinámicos, usando catálogo local:", err);
  }

  // Fallback al catálogo local
  const list = OPUSCAR_SEARCH_SUGGESTIONS[category] || OPUSCAR_SEARCH_SUGGESTIONS["historia_mexico"];
  chipsContainer.innerHTML = "";
  list.forEach((topic) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-amber-500/20 border border-slate-700 hover:border-amber-500/50 text-[11px] text-slate-300 hover:text-amber-200 transition text-left truncate max-w-xs";
    btn.textContent = `• ${topic}`;
    btn.title = topic;
    btn.onclick = () => {
      selectOpuscarTopic(topic);
    };
    chipsContainer.appendChild(btn);
  });
}

function selectOpuscarTopic(topic) {
  const qInput = document.getElementById("opuscarSearchQuery");
  if (qInput) {
    qInput.value = topic;
    qInput.focus();
    qInput.classList.add("ring-2", "ring-amber-400", "border-amber-400");
    setTimeout(() => {
      qInput.classList.remove("ring-2", "ring-amber-400", "border-amber-400");
    }, 1500);
  }
}

function discoverRandomOpuscarTopic() {
  const catEl = document.getElementById("opuscarSearchCategory");
  const category = catEl ? catEl.value : "historia_mexico";
  const pool = OPUSCAR_SEARCH_SUGGESTIONS[category] || OPUSCAR_SEARCH_SUGGESTIONS["historia_mexico"] || [];
  const qInput = document.getElementById("opuscarSearchQuery");
  const current = (qInput?.value || "").trim();
  const candidates = pool.filter(t => t !== current);
  const chosen = (candidates.length ? candidates : pool)[Math.floor(Math.random() * (candidates.length ? candidates.length : pool.length))];
  if (chosen) {
    selectOpuscarTopic(chosen);
  }
  const btn = document.getElementById("btnOpuscarRandomScript");
  if (btn) {
    const orig = btn.innerHTML;
    btn.innerHTML = "<span>✨ ¡Tema listo! Clic en Investigar</span>";
    setTimeout(() => { btn.innerHTML = orig; }, 2200);
  }
}

async function searchAndGenerateOpuscarScript(useRandom = false) {
  const catEl = document.getElementById("opuscarSearchCategory");
  const durEl = document.getElementById("opuscarSearchDuration");
  const qInput = document.getElementById("opuscarSearchQuery");
  const btnSearch = document.getElementById("btnOpuscarSearchScript");
  const btnRandom = document.getElementById("btnOpuscarRandomScript");
  const resultCard = document.getElementById("opuscarScriptResultCard");

  const category = catEl ? catEl.value : "historia_mexico";
  const durationMode = durEl ? durEl.value : "shorts";
  let query = qInput ? qInput.value.trim() : "";

  if (!query || useRandom) {
    const pool = OPUSCAR_SEARCH_SUGGESTIONS[category] || [];
    query = pool.length ? pool[Math.floor(Math.random() * pool.length)] : "";
    if (qInput) qInput.value = query;
  }

  if (btnSearch) {
    btnSearch.disabled = true;
    btnSearch.innerHTML = "<span>⏳ Investigando...</span>";
  }
  if (btnRandom) btnRandom.disabled = true;

  try {
    const res = await fetch("/api/youtube/search-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category,
        query,
        duration_mode: durationMode
      })
    });
    if (!res.ok) {
      throw new Error(`Error en el servidor (${res.status})`);
    }
    const data = await res.json();

    // 1. Asignar el título generado
    const titleInput = document.getElementById("opuscarTitleInput");
    if (titleInput && data.best_title) {
      titleInput.value = data.best_title;
    }

    // 2. Asignar el guion estructurado
    const narrInput = document.getElementById("opuscarNarrationInput");
    if (narrInput && data.script) {
      narrInput.value = data.script;
    }

    // 3. Configurar formato automáticamente (9:16 para Shorts)
    const fmtSel = document.getElementById("opuscarFormatSelect");
    if (fmtSel) {
      fmtSel.value = durationMode === "shorts" ? "9:16" : "16:9";
    }

    // 4. Seleccionar estilo visual Paper-Cut 2.5D Multi-Escena por defecto para cualquier tema nuevo
    const styleSel = document.getElementById("opuscarStyleSelect");
    if (styleSel) {
      const qLow = (query + " " + (data.best_title || "")).toLowerCase();
      if (qLow.includes("sahara") || qLow.includes("richat") || qLow.includes("mauritania")) {
        styleSel.value = "ojo_sahara_diorama";
      } else if (qLow.includes("chapultepec")) {
        styleSel.value = "chapultepec_diorama";
      } else if (qLow.includes("valeriana") || (qLow.includes("maya") && qLow.includes("campeche"))) {
        styleSel.value = "mayan_diorama";
      } else {
        styleSel.value = "paper_cutout_diorama";
      }
      setOpuscarStyle(styleSel.value);
    }

    // 5. Mostrar tarjeta de resumen
    if (resultCard) {
      resultCard.classList.remove("hidden");
      const titleP = document.getElementById("opuscarResultBestTitle");
      const durBadge = document.getElementById("opuscarResultDurationBadge");
      const hookSpan = document.getElementById("opuscarResultHook");
      const tagsSpan = document.getElementById("opuscarResultTags");
      const scriptPreview = document.getElementById("opuscarResultScriptPreview");
      const wordCountSpan = document.getElementById("opuscarResultWordCount");

      if (titleP) titleP.textContent = data.best_title || query;
      if (durBadge) durBadge.textContent = data.estimated_duration_label || (durationMode === "shorts" ? "~75s (Shorts)" : "4-6 min");
      if (hookSpan) hookSpan.textContent = `Hook: "${data.thumbnail_hook || "VIRAL"}"`;
      if (tagsSpan) tagsSpan.textContent = (data.hashtags || []).slice(0, 4).join(" ");
      if (scriptPreview && data.script) {
        scriptPreview.textContent = data.script;
        const wc = data.word_count || data.script.trim().split(/\s+/).length;
        if (wordCountSpan) wordCountSpan.textContent = `${wc} palabras · ~${Math.round(wc / 2.5)}s`;
      }

      // Renderizar los 3 ganchos psicológicos de alta retención
      const hooksSec = document.getElementById("opuscarHooksSection");
      const hooksCont = document.getElementById("opuscarHooksContainer");
      if (hooksSec && hooksCont && data.hooks && data.hooks.length > 0) {
        hooksCont.innerHTML = "";
        data.hooks.forEach((hObj) => {
          const hBtn = document.createElement("button");
          hBtn.type = "button";
          hBtn.className = "p-2 rounded-lg bg-slate-900/90 hover:bg-amber-500/15 border border-slate-700/80 hover:border-amber-500/40 text-left transition space-y-0.5 group";
          hBtn.innerHTML = `
            <div class="flex items-center justify-between text-[10px] font-bold text-amber-300">
              <span>${hObj.type_name}</span>
              <span class="text-slate-400 group-hover:text-amber-200 text-[9px]">Aplicar Gancho ↵</span>
            </div>
            <p class="text-[11px] text-slate-300 group-hover:text-white leading-relaxed">"${hObj.text}"</p>
          `;
          hBtn.onclick = () => {
            if (narrInput && data.script) {
              // Reemplazar la primera oración del guion con el gancho seleccionado
              const sentences = data.script.split(/(?<=[.?!])\s+/);
              if (sentences.length > 1) {
                narrInput.value = hObj.text + " " + sentences.slice(1).join(" ");
              } else {
                narrInput.value = hObj.text + " " + data.script;
              }
              if (scriptPreview) scriptPreview.textContent = narrInput.value;
            }
          };
          hooksCont.appendChild(hBtn);
        });
        hooksSec.classList.remove("hidden");
      }
    }
  } catch (err) {
    const msg = err.message === "Failed to fetch"
      ? "El servidor local se estaba iniciando o reconectando. Ya está activo en 127.0.0.1:7860; por favor vuelve a hacer clic en 'Investigar y Redactar'."
      : err.message;
    alert("No se pudo generar el guion: " + msg);
  } finally {
    if (btnSearch) {
      btnSearch.disabled = false;
      btnSearch.innerHTML = "<span>✨ Investigar y Redactar</span>";
    }
    if (btnRandom) btnRandom.disabled = false;
  }
}

window.initOpuscarModule = initOpuscarModule;
window.setOpuscarStyle = setOpuscarStyle;
window.selectOpuscarShowcase = selectOpuscarShowcase;
window.toggleOpuscarPlay = toggleOpuscarPlay;
window.scrubOpuscarTimeline = scrubOpuscarTimeline;
window.renderOpuscarVideo = renderOpuscarVideo;
window.closeOpuscarVideoModal = closeOpuscarVideoModal;
window.searchAndGenerateOpuscarScript = searchAndGenerateOpuscarScript;
window.searchAndGenerateOpusCarScript = searchAndGenerateOpuscarScript;
window._realSearchAndGenerateOpuscarScript = searchAndGenerateOpuscarScript;
window.onOpuscarSearchCategoryChange = onOpuscarSearchCategoryChange;
window.onOpusCarSearchCategoryChange = onOpuscarSearchCategoryChange;
window._realOnOpuscarSearchCategoryChange = onOpuscarSearchCategoryChange;

window.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    initOpuscarModule();
    onOpuscarSearchCategoryChange();
  }, 500);
});

function openOpuscarCurrentInModal() {
  const inlineVid = document.getElementById("opuscarPreviewPlayer");
  const modal = document.getElementById("opuscarVideoModal");
  const modalVid = document.getElementById("opuscarModalVideo");
  const link = document.getElementById("opuscarDownloadLink");
  if (!modal || !modalVid) return;
  const currentSrc = (inlineVid && inlineVid.src) ? inlineVid.src : "/projects/opuscar_chapultepec/chapultepec_diorama_9_16.mp4";
  modalVid.src = currentSrc;
  modalVid.load();
  modalVid.play().catch(() => {});
  if (link) {
    link.href = currentSrc;
    link.download = currentSrc.split("/").pop().split("?")[0] || "video.mp4";
  }
  modal.classList.remove("hidden");
}
window.openOpuscarCurrentInModal = openOpuscarCurrentInModal;
