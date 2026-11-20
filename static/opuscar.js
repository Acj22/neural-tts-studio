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

function drawPaperCutoutDiorama(ctx, w, h, t, dur, title) {
  const lowTitle = (title || "").toLowerCase();
  if (lowTitle.includes("sahara") || lowTitle.includes("richat") || lowTitle.includes("mauritania") || lowTitle.includes("desierto") || lowTitle.includes("cráter")) {
    drawOjoSaharaCanvas(ctx, w, h, t, dur, title);
    return;
  }
  if (lowTitle.includes("chapultepec") || lowTitle.includes("castillo") || lowTitle.includes("alcazar") || lowTitle.includes("maximiliano")) {
    drawChapultepecLive(ctx, w, h, t, dur, title);
    return;
  }
  if (lowTitle.includes("maya") || lowTitle.includes("campeche") || lowTitle.includes("selva") || lowTitle.includes("valeriana") || lowTitle.includes("lidar")) {
    drawMayaDioramaCanvas(ctx, w, h, t, dur, title);
    return;
  }
  // Fondo diorama cálido con azulejos
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, '#fcedd4');
  grad.addColorStop(0.65, '#f3dcb8');
  grad.addColorStop(0.65, '#a85b3d');
  grad.addColorStop(1, '#854228');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  // Zócalo
  ctx.fillStyle = '#5a2d18';
  ctx.fillRect(0, h * 0.64, w, 8);

  // Cuadrícula azulejos
  ctx.strokeStyle = 'rgba(210, 180, 140, 0.3)';
  ctx.lineWidth = 1;
  for (let x = 30; x < w; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h * 0.64); ctx.stroke(); }
  for (let y = 30; y < h * 0.64; y += 50) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Placa estilo matrícula arriba
  const pw = Math.min(w * 0.85, 380);
  const ph = 50;
  const px = (w - pw) / 2;
  const py = 25;
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.2)';
  ctx.shadowBlur = 8;
  ctx.shadowOffsetY = 4;
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.roundRect(px - 3, py - 3, pw + 6, ph + 6, 12); ctx.fill();
  ctx.fillStyle = '#fdfbf2';
  ctx.beginPath(); ctx.roundRect(px, py, pw, ph, 10); ctx.fill();
  ctx.strokeStyle = '#0f766e';
  ctx.lineWidth = 2.5;
  ctx.stroke();
  ctx.fillStyle = '#0f766e';
  ctx.font = 'bold 13px "Arial Black", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(title.toUpperCase(), w / 2, py + ph / 2);
  ctx.restore();

  // Gradas estilo estadio (homage exacto a imagen de referencia)
  const rows = 6;
  const startY = h * 0.28;
  for (let r = 0; r < rows; r++) {
    const y = startY + r * 38;
    const rw = w * 0.5 + r * 32;
    const rx = (w - rw) / 2;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); ctx.roundRect(rx - 4, y, rw + 8, 22, 6); ctx.fill();
    ctx.fillStyle = '#dc2626';
    ctx.beginPath(); ctx.roundRect(rx, y + 2, rw, 18, 5); ctx.fill();

    // Personajitos con gorrito
    const cols = 10;
    const sp = rw / cols;
    for (let c = 0; c < cols; c++) {
      const cx = rx + c * sp + sp / 2;
      const cy = y - 4;
      const fired = (r * cols + c) < ((t / dur) * rows * cols * 1.5);
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.arc(cx, cy, 7, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#0d9488';
      ctx.fillRect(cx - 5, cy, 10, 8);
      ctx.fillStyle = '#fed7aa';
      ctx.beginPath(); ctx.arc(cx, cy, 5.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.beginPath(); ctx.arc(cx, cy - 2, 5.5, Math.PI, Math.PI * 2); ctx.fill();

      // Linterna roja encendiéndose
      if (fired) {
        ctx.fillStyle = '#ef4444';
        ctx.beginPath(); ctx.arc(cx + 7, cy - 8, 3.5, 0, Math.PI * 2); ctx.fill();
      }
    }
  }

  // Sticker de Chile Habanero rebotando en el piso
  const cx = w / 2;
  const cy = h * 0.76 + Math.sin(t * 5) * 8;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.shadowColor = 'rgba(0,0,0,0.3)';
  ctx.shadowBlur = 10;
  ctx.shadowOffsetY = 6;
  // Borde blanco
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.ellipse(0, 0, 48, 68, 0, 0, Math.PI * 2);
  ctx.fill();
  // Interior degradado
  const cg = ctx.createLinearGradient(0, -60, 0, 60);
  cg.addColorStop(0, '#16a34a');
  cg.addColorStop(0.5, '#ea580c');
  cg.addColorStop(1, '#dc2626');
  ctx.fillStyle = cg;
  ctx.beginPath(); ctx.ellipse(0, 0, 42, 62, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#450a0a'; ctx.lineWidth = 2.5; ctx.stroke();
  // Ojitos
  ctx.fillStyle = '#ffffff';
  ctx.beginPath(); ctx.arc(-12, -10, 8, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(12, -10, 8, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.beginPath(); ctx.arc(-11, -10, 4, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(11, -10, 4, 0, Math.PI * 2); ctx.fill();
  // Sonrisa
  ctx.beginPath(); ctx.arc(0, 12, 10, 0.1, Math.PI - 0.1); ctx.stroke();
  ctx.restore();
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

    // Cargar en visor modal y reproductor inline
    const modal = document.getElementById("opuscarVideoModal");
    const vid = document.getElementById("opuscarModalVideo");
    const link = document.getElementById("opuscarDownloadLink");
    const inlineVid = document.getElementById("opuscarPreviewPlayer");
    const lastVideoCard = document.getElementById("opuscarLastVideoCard");

    if (vid) {
      vid.src = `${data.video_url}?t=${Date.now()}`;
      vid.load();
      vid.play().catch(() => {});
    }
    if (inlineVid) {
      inlineVid.src = `${data.video_url}?t=${Date.now()}`;
      inlineVid.load();
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
      pDesc.textContent = data.narration || narration || "Animación diorama multicapa paper-cut generada proceduralmente con sincronización 1:1 de audio, subtítulos y elementos visuales.";
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

function onOpuscarSearchCategoryChange() {
  const catEl = document.getElementById("opuscarSearchCategory");
  const chipsContainer = document.getElementById("opuscarTopicChips");
  if (!catEl || !chipsContainer) return;

  const category = catEl.value || "historia_mexico";
  const list = OPUSCAR_SEARCH_SUGGESTIONS[category] || [];
  chipsContainer.innerHTML = "";

  list.forEach((topic) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-amber-500/20 border border-slate-700 hover:border-amber-500/50 text-[11px] text-slate-300 hover:text-amber-200 transition text-left truncate max-w-xs";
    btn.textContent = `• ${topic}`;
    btn.title = topic;
    btn.onclick = () => {
      const qInput = document.getElementById("opuscarSearchQuery");
      if (qInput) qInput.value = topic;
      searchAndGenerateOpuscarScript(false);
    };
    chipsContainer.appendChild(btn);
  });
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

  if (useRandom) {
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

    // 4. Seleccionar estilo visual ideal según temática
    const styleSel = document.getElementById("opuscarStyleSelect");
    if (styleSel) {
      const qLow = (query + " " + (data.best_title || "")).toLowerCase();
      if (qLow.includes("sahara") || qLow.includes("richat") || qLow.includes("mauritania") || qLow.includes("desierto") || qLow.includes("cráter")) {
        styleSel.value = "ojo_sahara_diorama";
      } else if (qLow.includes("chapultepec") || qLow.includes("castillo") || qLow.includes("alcazar") || qLow.includes("maximiliano") || qLow.includes("reforma") || qLow.includes("palacio")) {
        styleSel.value = "chapultepec_diorama";
      } else if (qLow.includes("maya") || qLow.includes("campeche") || qLow.includes("valeriana") || qLow.includes("arqueol") || qLow.includes("pirámide")) {
        styleSel.value = "mayan_diorama";
      } else if (category === "lugares_mundo" || category === "historia_mexico") {
        styleSel.value = "paper_cutout_diorama";
      } else if (category === "misterio") {
        styleSel.value = "da_vinci_codex";
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

      if (titleP) titleP.textContent = data.best_title || query;
      if (durBadge) durBadge.textContent = data.estimated_duration_label || (durationMode === "shorts" ? "~75s (Shorts)" : "4-6 min");
      if (hookSpan) hookSpan.textContent = `Hook: "${data.thumbnail_hook || "VIRAL"}"`;
      if (tagsSpan) tagsSpan.textContent = (data.hashtags || []).slice(0, 4).join(" ");
    }
  } catch (err) {
    alert("No se pudo generar el guion: " + err.message);
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
window.onOpuscarSearchCategoryChange = onOpuscarSearchCategoryChange;
window.searchAndGenerateOpuscarScript = searchAndGenerateOpuscarScript;

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
