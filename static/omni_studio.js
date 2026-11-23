/**
 * OMNI-STUDIO — Controlador Frontend del Modo Cine Híbrido Multimodal
 * Unifica Blender 5.3, IA Fotorrealista, Lemo-Opuscar, Earshot Foley y Pedalboard.
 */

let activeOmniScript = null;

async function initOmniStudio() {
  try {
    const res = await fetch("/api/omni/topics");
    const data = await res.json();
    if (data.status === "success" && data.topics) {
      renderOmniTopicChips(data.topics);
    }
  } catch (e) {
    console.warn("Aviso al cargar temas de Omni-Studio:", e);
  }
}

function selectOmniTopic(title) {
  const input = document.getElementById("omniTopicInput");
  if (input) {
    input.value = title;
    input.focus();
    input.classList.add("ring-2", "ring-amber-400", "border-amber-400");
    setTimeout(() => {
      input.classList.remove("ring-2", "ring-amber-400", "border-amber-400");
    }, 1500);
  }
}

function discoverRandomOmniTopic() {
  const input = document.getElementById("omniTopicInput");
  const current = (input?.value || "").trim();
  const pool = Array.isArray(OMNI_VERIFIED_TOPICS) && OMNI_VERIFIED_TOPICS.length ? OMNI_VERIFIED_TOPICS : [];
  const candidates = pool.filter(t => (t.title || t) !== current);
  const picked = (candidates.length ? candidates : pool)[Math.floor(Math.random() * (candidates.length ? candidates.length : pool.length))];
  if (picked) {
    selectOmniTopic(picked.title || picked);
  }
  const btnRand = document.getElementById("btnOmniRandomScript");
  if (btnRand) {
    const orig = btnRand.innerHTML;
    btnRand.innerHTML = "<span>✨ ¡Tema cargado! Clic en Redactar</span>";
    setTimeout(() => { btnRand.innerHTML = orig; }, 2200);
  }
}

function renderOmniTopicChips(topics) {
  const container = document.getElementById("omniTopicChips");
  if (!container) return;
  container.innerHTML = "";
  topics.forEach((t) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-medium transition border border-slate-700/60 flex items-center gap-1";
    chip.innerHTML = `<span>💡</span><span>${t.title}</span>`;
    chip.onclick = () => {
      selectOmniTopic(t.title);
    };
    container.appendChild(chip);
  });
}

async function generateOmniScript(useRandom = false, specificId = "") {
  const input = document.getElementById("omniTopicInput");
  const query = useRandom ? "" : (specificId || (input ? input.value : ""));
  const btn = document.getElementById("btnOmniGenerateScript");
  const btnRand = document.getElementById("btnOmniRandomScript");

  if (btn) btn.disabled = true;
  if (btnRand) btnRand.disabled = true;

  try {
    const res = await fetch("/api/omni/script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: query }),
    });
    if (!res.ok) throw new Error("Error en el servidor al generar guion híbrido.");
    const data = await res.json();
    activeOmniScript = data;
    if (input) input.value = data.title;
    renderOmniActs(data);
  } catch (err) {
    alert("Error al redactar guion híbrido: " + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (btnRand) btnRand.disabled = false;
  }
}

function renderOmniActs(data) {
  const actsContainer = document.getElementById("omniActsList");
  const section = document.getElementById("omniScriptSection");
  if (!actsContainer || !section) return;

  section.classList.remove("hidden");
  actsContainer.innerHTML = "";

  data.acts.forEach((act, idx) => {
    const card = document.createElement("div");
    card.className = "p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2 hover:border-indigo-500/40 transition";

    let badgeColor = "bg-indigo-500/20 text-indigo-300 border-indigo-500/40";
    if (act.visual_engine === "blender_3d") {
      badgeColor = "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
    } else if (act.visual_engine === "opuscar_vector") {
      badgeColor = "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }

    card.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
        <div class="flex items-center gap-2">
          <span class="w-5 h-5 rounded-full bg-slate-800 text-[11px] font-bold text-slate-300 flex items-center justify-center">${act.act_number}</span>
          <h4 class="text-xs font-bold text-white">${act.title}</h4>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeColor}">${act.engine_label}</span>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-violet-500/20 text-violet-300 border border-violet-500/40">🔊 ${act.foley_accent}</span>
        </div>
      </div>
      <textarea
        rows="2"
        class="w-full rounded-lg bg-slate-950 border border-slate-700/80 px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition"
        onchange="updateOmniActText(${idx}, this.value)"
      >${act.text}</textarea>
    `;
    actsContainer.appendChild(card);
  });

  // Scroll suave hacia el guion generado
  section.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function updateOmniActText(index, newText) {
  if (activeOmniScript && activeOmniScript.acts && activeOmniScript.acts[index]) {
    activeOmniScript.acts[index].text = newText;
  }
}

async function renderOmniMasterVideo() {
  if (!activeOmniScript || !activeOmniScript.acts || activeOmniScript.acts.length === 0) {
    alert("Primero genera o selecciona un guion híbrido.");
    return;
  }

  const btn = document.getElementById("btnOmniRenderMaster");
  const progBox = document.getElementById("omniProgressBox");
  const progBar = document.getElementById("omniProgressBar");
  const progText = document.getElementById("omniProgressText");
  const videoCard = document.getElementById("omniVideoCard");
  const videoPlayer = document.getElementById("omniVideoPlayer");
  const dlBtn = document.getElementById("omniDownloadBtn");
  const zipBtn = document.getElementById("omniZipBtn");

  const voice = document.getElementById("omniVoiceSelect")?.value || "es-MX-JorgeNeural";
  const format = document.getElementById("omniFormatSelect")?.value || "vertical";

  if (btn) btn.disabled = true;
  if (progBox) progBox.classList.remove("hidden");
  if (videoCard) videoCard.classList.add("hidden");

  // Secuencia de estados de progreso visual en tiempo real
  const progressSteps = [
    { pct: "15%", msg: "1/5 Sintetizando locución neuronal HD y fonemas..." },
    { pct: "40%", msg: "2/5 Renderizando maqueta 3D en Blender 5.3 EEVEE Next y cuadros IA..." },
    { pct: "65%", msg: "3/5 Sintetizando pista Foley psicoacústica Earshot (Whooshes, Risers, Sub-Booms)..." },
    { pct: "85%", msg: "4/5 Masterizando audio con Spotify Pedalboard (Ducking + EQ)..." },
    { pct: "95%", msg: "5/5 Compilando MP4 Full HD con subtítulos estilo Karaoke y Ken Burns..." },
  ];

  let stepIdx = 0;
  const interval = setInterval(() => {
    if (stepIdx < progressSteps.length) {
      if (progBar) progBar.style.width = progressSteps[stepIdx].pct;
      if (progText) progText.textContent = progressSteps[stepIdx].msg;
      stepIdx++;
    }
  }, 4000);

  try {
    const res = await fetch("/api/omni/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: activeOmniScript.title,
        acts: activeOmniScript.acts,
        voice: voice,
        format: format,
      }),
    });

    clearInterval(interval);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al compilar el video híbrido.");
    }

    const data = await res.json();

    if (progBar) progBar.style.width = "100%";
    if (progText) progText.textContent = "¡Obra maestra híbrida producida con éxito!";

    if (videoCard) videoCard.classList.remove("hidden");
    if (videoPlayer) {
      videoPlayer.src = `${data.video_url}?t=${Date.now()}`;
      videoPlayer.load();
      videoPlayer.play().catch(() => {});
    }

    if (dlBtn) dlBtn.href = data.video_url;
    if (zipBtn) zipBtn.href = data.zip_url;

    const titleEl = document.getElementById("omniVideoTitle");
    if (titleEl) titleEl.textContent = data.title;

    const metaEl = document.getElementById("omniVideoMeta");
    if (metaEl) {
      metaEl.textContent = `${Math.round(data.duration)}s · Full HD · Híbrido: Blender 5.3 3D + IA + Opuscar + Foley`;
    }

    videoCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    clearInterval(interval);
    alert("Error al producir video híbrido: " + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Exportación 1-clic desde Lemo-Opuscar a Automatizador YouTube
async function exportOpuscarToYouTube() {
  if (typeof activeOpuscarScript === "undefined" || !activeOpuscarScript) {
    alert("Genera o redacta primero un guion en Lemo-Opuscar.");
    return;
  }

  const scenes = (activeOpuscarScript.scenes || []).map((sc, i) => ({
    text: sc.narration || sc.text || `Escena ${i + 1}`,
    duration: sc.duration_sec || 8.0,
  }));

  try {
    const res = await fetch("/api/opuscar/export-to-youtube", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: activeOpuscarScript.title || "Proyecto desde Opuscar",
        scenes: scenes,
        style: "cinematic",
        voice: "es-MX-JorgeNeural",
      }),
    });

    if (!res.ok) throw new Error("Error al exportar a YouTube.");
    const data = await res.json();
    alert(`¡Proyecto creado con éxito en Automatizador YouTube (${data.project_id})! Cambiando de pestaña...`);
    if (typeof switchMode === "function") {
      switchMode("youtube");
      if (typeof window.expLoadProjectById === "function") {
        window.expLoadProjectById(data.project_id);
      }
    }
  } catch (err) {
    alert("Error al exportar: " + err.message);
  }
}

window.initOmniStudio = initOmniStudio;
window.generateOmniScript = generateOmniScript;
window.renderOmniMasterVideo = renderOmniMasterVideo;
window.updateOmniActText = updateOmniActText;
window.exportOpuscarToYouTube = exportOpuscarToYouTube;

window.addEventListener("DOMContentLoaded", () => {
  setTimeout(initOmniStudio, 600);
});
