/**
 * Controlador frontend para el Módulo Animated Shorts
 * (Claude Animated Shorts + React Three Rapier + PixelFX + Earshot)
 */

let shortsTopics = [];
let activeShortsScript = null;

async function initShortsStudio() {
  try {
    const res = await fetch("/api/animated-shorts/topics");
    const data = await res.json();
    if (data.status === "success") {
      shortsTopics = data.topics;
      renderShortsTopicCards();
    }
  } catch (err) {
    console.error("Error inicializando Animated Shorts Studio:", err);
  }
}

function renderShortsTopicCards() {
  const container = document.getElementById("shortsTopicsContainer");
  if (!container) return;

  container.innerHTML = "";
  shortsTopics.forEach((topic, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `p-3 rounded-xl border text-left transition flex flex-col gap-1.5 ${
      idx === 0
        ? "bg-violet-600/20 border-violet-500 text-white shadow-lg shadow-violet-500/10"
        : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700 hover:text-white"
    }`;
    btn.id = `shortsTopicBtn_${topic.id}`;
    btn.onclick = () => selectShortsTopic(topic.id);

    btn.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="text-xl">${topic.icon}</span>
        <span class="text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">
          ${topic.style_preset}
        </span>
      </div>
      <h4 class="text-xs font-bold text-white mt-1">${topic.category}</h4>
      <p class="text-[11px] text-slate-400 line-clamp-2">${topic.description}</p>
    `;
    container.appendChild(btn);
  });

  if (shortsTopics.length > 0) {
    selectShortsTopic(shortsTopics[0].id);
  }
}

function selectShortsTopic(topicId) {
  const topic = shortsTopics.find((t) => t.id === topicId);
  if (!topic) return;

  // Actualizar estilos activos de botones
  shortsTopics.forEach((t) => {
    const b = document.getElementById(`shortsTopicBtn_${t.id}`);
    if (b) {
      if (t.id === topicId) {
        b.className =
          "p-3 rounded-xl border text-left transition flex flex-col gap-1.5 bg-violet-600/20 border-violet-500 text-white shadow-lg shadow-violet-500/10";
      } else {
        b.className =
          "p-3 rounded-xl border text-left transition flex flex-col gap-1.5 bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700 hover:text-white";
      }
    }
  });

  // Actualizar input de tema y opciones de títulos pre-investigados
  const titleInput = document.getElementById("shortsTitleInput");
  const presetsSelect = document.getElementById("shortsPresetsSelect");

  if (titleInput) {
    titleInput.value = topic.default_title;
  }

  if (presetsSelect) {
    presetsSelect.innerHTML = "";
    topic.preset_titles.forEach((pt) => {
      const opt = document.createElement("option");
      opt.value = pt;
      opt.textContent = pt;
      presetsSelect.appendChild(opt);
    });
    presetsSelect.onchange = () => {
      titleInput.value = presetsSelect.value;
    };
  }

  document.getElementById("shortsActiveTopicId").value = topicId;
}

async function generateShortsScript() {
  const topicId = document.getElementById("shortsActiveTopicId").value;
  const title = document.getElementById("shortsTitleInput").value;
  const statusEl = document.getElementById("shortsScriptStatus");
  const container = document.getElementById("shortsScriptContainer");

  if (statusEl) {
    statusEl.innerHTML = `
      <span class="inline-flex items-center gap-1.5 text-violet-400 font-semibold animate-pulse text-xs">
        <svg class="animate-spin h-3.5 w-3.5 text-violet-400" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        Investigando fuentes reales y estructurando guion en 5 actos...
      </span>
    `;
  }

  try {
    const res = await fetch("/api/animated-shorts/generate-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_id: topicId, title }),
    });

    const data = await res.json();
    if (data.status === "success") {
      activeShortsScript = data.script;
      renderShortsScriptPreview(data.script);
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-xs text-emerald-400 font-bold">✓ Guion investigado y estructurado con éxito (${data.script.total_duration_sec}s)</span>`;
      }
    } else {
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-xs text-rose-400 font-bold">Error: ${data.detail}</span>`;
      }
    }
  } catch (err) {
    console.error("Error al generar guion:", err);
    if (statusEl) {
      statusEl.innerHTML = `<span class="text-xs text-rose-400 font-bold">Error de red al generar guion</span>`;
    }
  }
}

function renderShortsScriptPreview(script) {
  const container = document.getElementById("shortsScriptContainer");
  if (!container) return;

  let html = `
    <div class="space-y-4">
      <!-- Metadatos de Investigación Real -->
      <div class="p-3.5 rounded-xl bg-violet-950/40 border border-violet-500/30 space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-violet-300">📚 Fuentes Documentales Verificadas:</span>
          <span class="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            Reglas de Investigación 100% Cumplidas
          </span>
        </div>
        <ul class="text-[11px] text-slate-300 list-disc list-inside space-y-1">
          ${script.historical_sources.map((s) => `<li>${s}</li>`).join("")}
        </ul>
      </div>

      <!-- Desglose de Escenas en 5 Actos -->
      <div class="space-y-3">
  `;

  script.scenes.forEach((sc) => {
    html += `
      <div class="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 hover:border-slate-700 transition">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-white">${sc.act_name}</span>
          <span class="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
            ${sc.time_range[0]}s — ${sc.time_range[1]}s (${(sc.time_range[1] - sc.time_range[0]).toFixed(1)}s)
          </span>
        </div>
        <p class="text-xs text-slate-200 leading-relaxed font-medium bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
          "${sc.narration}"
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1">
          <div class="flex items-start gap-1.5">
            <span class="text-violet-400 font-bold">🎬 Visual:</span>
            <span>${sc.visual_direction}</span>
          </div>
          <div class="flex items-start gap-1.5">
            <span class="text-amber-400 font-bold">🔊 Earshot:</span>
            <span class="font-mono text-amber-300/80">${sc.earshot_foley.join(", ")}</span>
          </div>
        </div>
      </div>
    `;
  });

  html += `
      </div>

      <!-- Botón de Acción para Foley Earshot -->
      <div class="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800">
        <span class="text-xs text-slate-400">Pista foley procedimental con Earshot lista para compilación.</span>
        <button
          type="button"
          onclick="compileEarshotFoley()"
          class="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white text-xs font-bold shadow-lg shadow-amber-600/20 flex items-center gap-2 transition"
        >
          <span>🔊</span>
          <span>Sintetizar Foley con Earshot</span>
        </button>
      </div>
    </div>
  `;

  container.innerHTML = html;
}

async function compileEarshotFoley() {
  if (!activeShortsScript) return;

  const statusEl = document.getElementById("shortsScriptStatus");
  if (statusEl) {
    statusEl.innerHTML = `<span class="text-xs text-amber-400 font-semibold animate-pulse">Sintetizando ondas procedimentales y foley multipista con Earshot...</span>`;
  }

  try {
    const res = await fetch("/api/animated-shorts/generate-foley", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic_id: activeShortsScript.topic_id,
        title: activeShortsScript.title,
        scenes: activeShortsScript.scenes,
        total_duration_sec: activeShortsScript.total_duration_sec,
      }),
    });

    const data = await res.json();
    if (data.status === "success") {
      if (statusEl) {
        statusEl.innerHTML = `
          <div class="flex items-center gap-2">
            <span class="text-xs text-emerald-400 font-bold">✓ Pista Foley Earshot sintetizada:</span>
            <audio controls src="${data.foley_wav_url}" class="h-6 w-56"></audio>
          </div>
        `;
      }
    }
  } catch (err) {
    console.error("Error generando foley:", err);
  }
}

// Inicializar al cargar el script
document.addEventListener("DOMContentLoaded", () => {
  initShortsStudio();
});
