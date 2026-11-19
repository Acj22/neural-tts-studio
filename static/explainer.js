/**
 * AI VIDEO STUDIO — Módulo Principal: EXPLAINER AI (¿CÓMO FUNCIONA?)
 * Lógica interactiva de las Fases 2 a 18 (Research, Script Corto/Largo, Storyboard Semántico,
 * Diagramas Técnicos SVG Modo B, Imágenes Modo A, Reencuadre Multiplataforma, Social Packager,
 * Quality Control de 14 puntos y Control de Costos).
 */

let expCatalog = null;
let expCurrentProject = null;
let expPreviewResearch = null;
let expActiveSubTab = "research";
let expActiveVersion = "short";

// Inmediata exposición global de seguridad para evitar ReferenceError en eventos DOM
window.expLoadProjectById = window.expLoadProjectById || (async function(id) {
  if (typeof expLoadProjectById === "function" && expLoadProjectById !== window.expLoadProjectById) {
    return await expLoadProjectById(id);
  }
});
window.expLoadProject = window.expLoadProject || window.expLoadProjectById;

const EXPLAINER_BENCHMARK_TOPICS = {
  motor: {
    project_name: "¿Cómo funciona un motor de combustión?",
    topic: "Cómo funciona un motor de combustión interna de 4 tiempos",
    main_question: "¿Cómo transforma un motor de combustión la gasolina en movimiento rotativo a través de sus 4 tiempos?",
    category: "automoviles"
  },
  cajero: {
    project_name: "¿Cómo funciona un cajero automático?",
    topic: "Cómo funciona un cajero automático (ATM) por dentro",
    main_question: "¿Cómo valida tu tarjeta EMV, cifra tu PIN y cuenta los billetes sin equivocarse un cajero automático?",
    category: "economia_cotidiana"
  },
  gps: {
    project_name: "¿Cómo funciona el GPS?",
    topic: "Cómo funciona el Sistema de Posicionamiento Global (GPS)",
    main_question: "¿Cómo calculan los satélites GPS y los relojes atómicos tu ubicación exacta en la Tierra?",
    category: "espacio"
  },
  pantalla: {
    project_name: "¿Cómo funciona una pantalla táctil?",
    topic: "Cómo funciona una pantalla táctil capacitiva",
    main_question: "¿Cómo detecta el cristal de tu teléfono la posición exacta de tus dedos mediante campos electrostáticos?",
    category: "electronica"
  },
  transmision: {
    project_name: "¿Cómo funciona una transmisión automática?",
    topic: "Cómo funciona una transmisión automática (Convertidor de par y engranajes planetarios)",
    main_question: "¿Cómo cambia de marcha una transmisión automática usando fluido a presión y engranajes planetarios?",
    category: "ingenieria"
  }
};

function expLoadPresetTopic(key) {
  const preset = EXPLAINER_BENCHMARK_TOPICS[key];
  if (!preset) return;
  document.getElementById("expProjectName").value = preset.project_name;
  document.getElementById("expTopic").value = preset.topic;
  document.getElementById("expQuestion").value = preset.main_question;
  document.getElementById("expCategory").value = preset.category;
}

function expSetProgress(visible, text = "", pct = 10) {
  const box = document.getElementById("expProgressBox");
  if (!box) return;
  if (!visible) {
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  document.getElementById("expProgressText").textContent = text;
  document.getElementById("expProgressPct").textContent = `${Math.round(pct)}%`;
  document.getElementById("expProgressBar").style.width = `${Math.max(5, Math.min(100, pct))}%`;
}

function expShowError(msg) {
  const el = document.getElementById("expErrorBox");
  if (!el) return;
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
  } else {
    el.textContent = msg;
    el.classList.remove("hidden");
  }
}

async function initExplainerStudio() {
  try {
    const res = await fetch("/api/explainer/catalog");
    if (res.ok) {
      expCatalog = await res.json();
      populateExplainerFormCatalogs();
    }
    await loadExplainerProjectsList();
  } catch (e) {
    console.warn("Error cargando catálogo de Explainer AI:", e);
  }
}

function populateExplainerFormCatalogs() {
  if (!expCatalog) return;
  const catSel = document.getElementById("expCategory");
  if (catSel && expCatalog.categories) {
    catSel.innerHTML = "";
    expCatalog.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.name} — ${c.focus}`;
      catSel.appendChild(opt);
    });
    catSel.value = "automoviles";
  }

  const styleSel = document.getElementById("expVisualStyle");
  if (styleSel && expCatalog.visual_styles) {
    styleSel.innerHTML = "";
    expCatalog.visual_styles.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name;
      styleSel.appendChild(opt);
    });
  }
}

function populateExplainerVoiceSelect() {
  const vSel = document.getElementById("expVoiceSelect");
  if (!vSel || typeof voicesCatalog === "undefined") return;
  const list = voicesCatalog.edge || voicesCatalog.kokoro || [];
  vSel.innerHTML = "";
  list.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.id;
    opt.textContent = v.name;
    vSel.appendChild(opt);
  });
}

async function loadExplainerProjectsList() {
  const sel = document.getElementById("expSavedProjectsSelect");
  if (!sel) return;
  try {
    const res = await fetch("/api/explainer/projects");
    if (!res.ok) return;
    const data = await res.json();
    const list = data.projects || [];
    sel.innerHTML = `<option value="">📂 Cargar Proyecto Maestro Explainer AI (${list.length} guardados)...</option>`;
    list.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.project_id;
      opt.textContent = `[Short:${p.short_scenes_count} · Long:${p.long_scenes_count} · Exp:${p.exports_count}] ${p.project_name}`;
      if (expCurrentProject && expCurrentProject.project_id === p.project_id) {
        opt.selected = true;
      }
      sel.appendChild(opt);
    });
  } catch (e) { /* ignore */ }
}

async function expLoadProjectById(projectId) {
  if (!projectId) return;
  expShowError("");
  try {
    const res = await fetch(`/api/explainer/project/${projectId}`);
    if (!res.ok) throw new Error("No se pudo cargar el proyecto maestro.");
    expCurrentProject = await res.json();
    expPreviewResearch = expCurrentProject.research || null;
    renderExplainerWorkspace();
    loadExplainerProjectsList();
  } catch (err) {
    expShowError(err.message);
  }
}
window.expLoadProject = expLoadProjectById;
window.expLoadProjectById = expLoadProjectById;

async function expRunStandaloneResearch() {
  const topic = (document.getElementById("expTopic").value || "").trim();
  if (!topic) {
    expShowError("Por favor escribe el tema a investigar primero.");
    return;
  }
  expShowError("");
  expSetProgress(true, "Fase 4 (Research Engine): Consultando Wikipedia ES/EN, Crossref DOI y analizando conceptos verificables...", 35);
  try {
    const res = await fetch("/api/explainer/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic,
        main_question: document.getElementById("expQuestion").value.trim(),
        category: document.getElementById("expCategory").value,
        target_audience: document.getElementById("expAudience").value.trim(),
        user_notes: document.getElementById("expUserNotes").value.trim()
      })
    });
    if (!res.ok) throw new Error("Error ejecutando la investigación documental.");
    expPreviewResearch = await res.json();
    document.getElementById("expWorkspaceBox").classList.remove("hidden");
    expSwitchSubTab("research");
    renderExplainerResearchTab(expPreviewResearch);
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

async function expCreateMasterProject(autoExportAll = false) {
  const topic = (document.getElementById("expTopic").value || "").trim();
  if (!topic) {
    expShowError("Por favor ingresa un tema para el proyecto educativo.");
    return;
  }
  expShowError("");
  const btnCreate = document.getElementById("btnExpCreate");
  const btnFull = document.getElementById("btnExpCreateFull");
  if (btnCreate) btnCreate.disabled = true;
  if (btnFull) btnFull.disabled = true;

  try {
    expSetProgress(true, "Paso 1/3: Ejecutando Research Engine + Redactando Guion Corto (1-3m) y Guion Largo (5-10m) + Creando Storyboards y Diagramas SVG...", 25);
    const payload = {
      project_name: document.getElementById("expProjectName").value.trim(),
      topic,
      main_question: document.getElementById("expQuestion").value.trim(),
      category: document.getElementById("expCategory").value,
      target_audience: document.getElementById("expAudience").value.trim(),
      lang: "es-mx",
      duration_mode: document.getElementById("expDurationMode").value,
      screen_format: document.getElementById("expScreenFormat").value,
      visual_style: document.getElementById("expVisualStyle").value,
      engine: "edge",
      voice: document.getElementById("expVoiceSelect").value || "es-MX-JorgeNeural",
      speed: parseFloat(document.getElementById("expSpeed").value) || 1.0,
      pitch_hz: -2,
      studio_mastering: true,
      bg_music: document.getElementById("expBgMusic").value,
      bg_music_volume: 0.14,
      subtitle_style: "hormozi_yellow",
      user_notes: document.getElementById("expUserNotes").value.trim(),
      existing_research: (expPreviewResearch && expPreviewResearch.topic === topic) ? expPreviewResearch : null
    };

    const res = await fetch("/api/explainer/project/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "No se pudo crear el proyecto maestro.");
    }
    expCurrentProject = await res.json();
    expPreviewResearch = expCurrentProject.research;
    renderExplainerWorkspace();
    await loadExplainerProjectsList();

    if (autoExportAll) {
      expSetProgress(true, "Paso 2/3: Sintetizando narración neuronal y ensamblando versiones multiplataforma con diagramas animados y zonas seguras...", 65);
      await expRunMultiPlatformExport(["youtube_shorts", "youtube_video", "tiktok", "instagram_reels", "facebook_reels"]);
      expSwitchSubTab("export");
    } else {
      expSwitchSubTab("storyboard");
    }
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  } finally {
    if (btnCreate) btnCreate.disabled = false;
    if (btnFull) btnFull.disabled = false;
  }
}

async function expDuplicateCurrentProject() {
  if (!expCurrentProject) return;
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/duplicate`, { method: "POST" });
    if (!res.ok) throw new Error("No se pudo duplicar el proyecto.");
    expCurrentProject = await res.json();
    renderExplainerWorkspace();
    await loadExplainerProjectsList();
  } catch (err) {
    expShowError(err.message);
  }
}

function expSwitchSubTab(tab) {
  expActiveSubTab = tab;
  const tabs = ["research", "scripts", "storyboard", "export", "qc"];
  tabs.forEach((t) => {
    const panel = document.getElementById(`expSubPanel_${t}`);
    const btn = document.getElementById(`expSubBtn_${t}`);
    if (panel) panel.classList.toggle("hidden", t !== tab);
    if (btn) {
      btn.className = t === tab
        ? "px-3.5 py-2 rounded-xl text-xs font-bold bg-emerald-500 text-slate-950 shadow transition"
        : "px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-900 text-slate-300 hover:text-white border border-slate-800 transition";
    }
  });
}

function expSwitchVersion(ver) {
  expActiveVersion = ver;
  const btnS = document.getElementById("btnExpVerShort");
  const btnL = document.getElementById("btnExpVerLong");
  if (btnS && btnL) {
    btnS.className = ver === "short"
      ? "px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-500 text-white"
      : "px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300";
    btnL.className = ver === "long"
      ? "px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-500 text-white"
      : "px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300";
  }
  if (expCurrentProject) {
    renderExplainerScriptsTab();
    renderExplainerStoryboardTab();
  }
}

function renderExplainerWorkspace() {
  if (!expCurrentProject) return;
  document.getElementById("expWorkspaceBox").classList.remove("hidden");
  document.getElementById("expActiveProjectTitle").textContent = expCurrentProject.project_name || expCurrentProject.topic;
  document.getElementById("expActiveProjectBadge").textContent = `ID: ${expCurrentProject.project_id}`;
  const zipBtn = document.getElementById("expMasterZipLink");
  if (zipBtn) zipBtn.href = expCurrentProject.zip_url || `/api/explainer/project/${expCurrentProject.project_id}/zip`;

  renderExplainerResearchTab(expCurrentProject.research);
  renderExplainerScriptsTab();
  renderExplainerStoryboardTab();
  renderExplainerExportsTab();
  renderExplainerQCTab();
}

function renderExplainerResearchTab(research) {
  if (!research) return;
  const container = document.getElementById("expResearchContent");
  if (!container) return;

  const conceptsHtml = (research.core_concepts || []).map((c) => `
    <div class="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
      <div class="text-xs font-bold text-emerald-300">⚙️ ${c.name}</div>
      <div class="text-xs text-slate-300 mt-1">${c.role}</div>
    </div>
  `).join("");

  const factsHtml = (research.verified_facts || []).map((f) => `<li class="text-xs text-slate-200 leading-relaxed">✅ ${f}</li>`).join("");
  const estHtml = (research.estimates_and_approximations || []).map((e) => `<li class="text-xs text-amber-200 leading-relaxed">📊 ${e}</li>`).join("");
  const nuancesHtml = (research.contradictions_or_nuances || []).map((n) => `<li class="text-xs text-indigo-200 leading-relaxed">⚖️ ${n}</li>`).join("");
  const verHtml = (research.needs_verification || []).map((v) => `<li class="text-xs text-rose-200 leading-relaxed">🔎 ${v}</li>`).join("");

  const sourcesHtml = (research.sources || []).map((s, idx) => `
    <div class="p-3 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-xs font-bold text-white">📚 Fuente #${idx + 1}: ${s.title}</span>
        <span class="text-[11px] mono text-slate-400">Pub: ${s.publication_date} · Consulta: ${s.consultation_date}</span>
      </div>
      <div class="text-[11px] text-emerald-300">🏛️ ${s.author_or_institution} — <a href="${s.url}" target="_blank" class="underline text-indigo-300 break-all">${s.url}</a></div>
      <p class="text-xs text-slate-300 pt-1">${s.backed_information}</p>
    </div>
  `).join("");

  container.innerHTML = `
    ${research.external_source_warning ? `<div class="p-3 rounded-xl bg-amber-500/15 border border-amber-500/40 text-xs text-amber-200">${research.external_source_warning}</div>` : ""}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">${conceptsHtml}</div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
      <div class="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
        <h4 class="text-xs font-bold uppercase tracking-wider text-emerald-300">Hechos Técnicos Verificados</h4>
        <ul class="space-y-1.5">${factsHtml}</ul>
      </div>
      <div class="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
        <h4 class="text-xs font-bold uppercase tracking-wider text-amber-300">Estimaciones y Rangos Operativos (Separados de Hechos)</h4>
        <ul class="space-y-1.5">${estHtml}</ul>
      </div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 space-y-2">
        <h4 class="text-xs font-bold uppercase tracking-wider text-indigo-300">Contradicciones / Mitos vs. Realidad</h4>
        <ul class="space-y-1.5">${nuancesHtml}</ul>
      </div>
      <div class="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-2">
        <h4 class="text-xs font-bold uppercase tracking-wider text-rose-300">Información Sujeta a Modelo / Verificación</h4>
        <ul class="space-y-1.5">${verHtml}</ul>
      </div>
    </div>
    <div class="space-y-2 pt-2">
      <h4 class="text-xs font-bold uppercase tracking-wider text-slate-300">Fuentes Documentales Registradas (${(research.sources || []).length})</h4>
      <div class="space-y-2">${sourcesHtml || '<p class="text-xs text-slate-400">Sin fuentes externas registradas.</p>'}</div>
    </div>
  `;
}

function renderExplainerScriptsTab() {
  if (!expCurrentProject || !expCurrentProject.scripts) return;
  const branch = expCurrentProject.scripts[expActiveVersion] || expCurrentProject.scripts.short;
  const listEl = document.getElementById("expScriptSectionsList");
  const statsEl = document.getElementById("expScriptStatsBadge");
  const audioEl = document.getElementById("expVersionAudioPlayer");
  if (!listEl) return;

  const realDur = branch.real_audio_duration_sec ? `${branch.real_audio_duration_sec}s reales (Audio WAV)` : "Pendiente de sintetizar audio real";
  if (statsEl) {
    statsEl.textContent = `${branch.word_count} palabras · Est: ${branch.estimated_duration_sec}s · Real: ${realDur}`;
  }

  const audioUrl = (expCurrentProject.audio_urls || {})[expActiveVersion];
  if (audioEl) {
    if (audioUrl) {
      audioEl.src = audioUrl;
      audioEl.classList.remove("hidden");
    } else {
      audioEl.classList.add("hidden");
    }
  }

  listEl.innerHTML = "";
  (branch.sections || []).forEach((sec) => {
    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-2";
    card.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <span class="text-xs font-bold text-indigo-300">${sec.title}</span>
          <span class="text-[11px] text-slate-400 ml-2">(${sec.goal})</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[11px] mono text-emerald-300">~${sec.estimated_duration_sec}s</span>
          <button onclick="expSaveOrRegenSection('${sec.key}', false)" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 font-semibold">💾 Guardar texto</button>
          <button onclick="expSaveOrRegenSection('${sec.key}', true)" class="px-2.5 py-1 rounded bg-indigo-500/25 hover:bg-indigo-500/40 border border-indigo-500/30 text-[11px] text-indigo-200 font-semibold">🔄 Regenerar sección</button>
        </div>
      </div>
      <textarea id="expSecTxt_${sec.key}" rows="3" class="w-full rounded-lg bg-slate-900 border border-slate-800 p-2.5 text-xs text-slate-100 leading-relaxed">${sec.text}</textarea>
    `;
    listEl.appendChild(card);
  });

  // Mostrar también las variaciones adaptadas por red social
  const adaptBox = document.getElementById("expPlatformAdaptationsBox");
  if (adaptBox && expCurrentProject.scripts.platform_adaptations) {
    const ad = expCurrentProject.scripts.platform_adaptations;
    adaptBox.innerHTML = Object.values(ad).map((item) => `
      <div class="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-amber-300 uppercase">${item.platform_id}</span>
          <span class="text-[11px] mono text-slate-400">Fuente: ${item.version_source} (~${item.estimated_duration_sec}s)</span>
        </div>
        <div class="text-[11px] text-slate-400">${item.adaptation_note}</div>
      </div>
    `).join("");
  }
}

async function expSaveOrRegenSection(sectionKey, regenerate) {
  if (!expCurrentProject) return;
  const txtEl = document.getElementById(`expSecTxt_${sectionKey}`);
  const newText = txtEl ? txtEl.value.trim() : "";
  expSetProgress(true, regenerate ? `Regenerando sección '${sectionKey}'...` : `Guardando sección '${sectionKey}'...`, 50);
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/script/section`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        version: expActiveVersion,
        section_key: sectionKey,
        new_text: newText,
        regenerate: !!regenerate,
        instruction: ""
      })
    });
    if (!res.ok) throw new Error("No se pudo actualizar la sección del guion.");
    expCurrentProject = await res.json();
    renderExplainerWorkspace();
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

async function expSynthesizeVersionAudio(ver) {
  if (!expCurrentProject) return;
  expSetProgress(true, `Sintetizando voz neuronal ultra-natural y midiendo duración real (${ver})...`, 45);
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/synthesize/${ver}`, { method: "POST" });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error sintetizando narración.");
    }
    expCurrentProject = await res.json();
    renderExplainerWorkspace();
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

function renderExplainerStoryboardTab() {
  if (!expCurrentProject || !expCurrentProject.storyboards) return;
  const scenes = expCurrentProject.storyboards[expActiveVersion] || [];
  const listEl = document.getElementById("expStoryboardScenesList");
  const countEl = document.getElementById("expStoryboardCountBadge");
  if (!listEl) return;
  if (countEl) countEl.textContent = `${scenes.length} escenas (${expActiveVersion === "short" ? "Short 9:16" : "Long 16:9"})`;

  listEl.innerHTML = "";
  const resTypes = (expCatalog && expCatalog.scene_resource_types) || [];
  const compTypes = (expCatalog && expCatalog.composition_types) || [
    { id: "hero_view", name: "HERO VIEW (Vista General)" },
    { id: "close_up_view", name: "CLOSE-UP (Detalle Macro)" },
    { id: "cutaway_view", name: "CUTAWAY (Corte Interior)" },
    { id: "process_view", name: "PROCESS VIEW (Flujo Cinemático)" },
    { id: "comparison_view", name: "COMPARISON (Comparativa)" },
    { id: "infographic_view", name: "INFOGRAPHIC (Datos y HUD)" }
  ];

  scenes.forEach((sc) => {
    const sid = sc.scene_id;
    const resOptions = resTypes.map((rt) => `<option value="${rt.id}" ${rt.id === sc.resource_type ? "selected" : ""}>${rt.name}</option>`).join("");
    const currentComp = sc.composition_type || (sc.diagram_spec && sc.diagram_spec.composition_type) || "hero_view";
    const compOptions = compTypes.map((ct) => `<option value="${ct.id}" ${ct.id === currentComp ? "selected" : ""}>${ct.name}</option>`).join("");
    const visualPreviewHtml = (sc.visual_mode === "mode_a_image" && sc.image_url)
      ? `<img src="${sc.image_url}" class="w-full h-48 object-cover rounded-lg border border-slate-700" />`
      : (sc.diagram_svg_url
          ? `<img src="${sc.diagram_svg_url}" class="w-full h-48 object-contain bg-slate-950 rounded-lg border border-indigo-500/40" />`
          : `<div class="w-full h-48 rounded-lg bg-slate-950 border border-dashed border-slate-700 flex items-center justify-center text-xs text-slate-400">Sin vista previa aún</div>`);

    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-slate-950/90 border border-slate-800 grid grid-cols-1 lg:grid-cols-12 gap-4";
    card.innerHTML = `
      <div class="lg:col-span-7 space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold text-xs mono">${sid}</span>
            <span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-xs mono">⏱ ${sc.timestamp_label} (${sc.duration_sec}s)</span>
            <span class="text-xs font-bold text-amber-300">${sc.concept_explained}</span>
          </div>
          <div class="flex items-center gap-1">
            <button onclick="expSceneAction('${sid}', 'move_up')" title="Subir escena" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs">↑</button>
            <button onclick="expSceneAction('${sid}', 'move_down')" title="Bajar escena" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs">↓</button>
            <button onclick="expSceneAction('${sid}', 'duplicate')" title="Duplicar escena" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs">➕</button>
            <button onclick="expSaveSceneEdits('${sid}')" class="px-2.5 py-1 rounded bg-emerald-500/25 hover:bg-emerald-500/40 text-emerald-200 text-xs font-semibold">💾 Guardar</button>
          </div>
        </div>

        <textarea id="expScText_${sid}" rows="2" class="w-full rounded-lg bg-slate-900 border border-slate-800 p-2 text-xs text-slate-100">${sc.narration_text}</textarea>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <div>
            <label class="block text-[10px] uppercase text-slate-400 mb-0.5">Tipo de Escena</label>
            <select id="expScResType_${sid}" class="w-full rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-xs text-white">${resOptions}</select>
          </div>
          <div>
            <label class="block text-[10px] uppercase text-amber-300 font-bold mb-0.5">Composición (6 Planos)</label>
            <select id="expScCompType_${sid}" class="w-full rounded-lg bg-slate-900 border border-amber-500/50 px-2 py-1.5 text-xs text-amber-200">${compOptions}</select>
          </div>
          <div>
            <label class="block text-[10px] uppercase text-slate-400 mb-0.5">Modalidad Visual</label>
            <select id="expScMode_${sid}" class="w-full rounded-lg bg-slate-900 border border-indigo-500/40 px-2 py-1.5 text-xs text-white">
              <option value="mode_d_blender3d" ${sc.visual_mode === "mode_d_blender3d" ? "selected" : ""}>🎬 Modo D: Animación 3D Blender ($0)</option>
              <option value="mode_b_diagram" ${sc.visual_mode === "mode_b_diagram" ? "selected" : ""}>📐 Modo B: Diagrama SVG ($0)</option>
              <option value="mode_a_image" ${sc.visual_mode === "mode_a_image" ? "selected" : ""}>🖼️ Modo A: Imagen IA</option>
              <option value="mode_c_video" ${sc.visual_mode === "mode_c_video" ? "selected" : ""}>🎬 Modo C: Video IA</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] uppercase text-slate-400 mb-0.5">Movimiento / Cámara</label>
            <select id="expScCam_${sid}" class="w-full rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-xs text-white">
              <option value="zoom_in" ${sc.camera_motion === "zoom_in" ? "selected" : ""}>🔍 Zoom In</option>
              <option value="zoom_out" ${sc.camera_motion === "zoom_out" ? "selected" : ""}>🔎 Zoom Out</option>
              <option value="pan_horizontal" ${sc.camera_motion === "pan_horizontal" ? "selected" : ""}>↔️ Pan Horizontal</option>
              <option value="pan_vertical" ${sc.camera_motion === "pan_vertical" ? "selected" : ""}>↕️ Pan Vertical</option>
              <option value="parallax" ${sc.camera_motion === "parallax" ? "selected" : ""}>✨ Parallax 2.5D</option>
              <option value="selective_focus" ${sc.camera_motion === "selective_focus" ? "selected" : ""}>🎯 Enfoque Selectivo</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-[10px] uppercase text-amber-300 mb-0.5">Etiquetas Técnicas del Diagrama (separadas por '|', anti-colisión):</label>
          <input id="expScLabels_${sid}" value="${(sc.labels || []).join(' | ')}" class="w-full rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1.5 text-xs text-amber-200" />
        </div>
      </div>

      <div class="lg:col-span-5 space-y-2">
        ${visualPreviewHtml}
        <div class="flex flex-wrap items-center gap-2">
          <button onclick="expGenerateSceneVisual('${sid}')" class="flex-1 py-1.5 px-3 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 text-xs font-semibold">
            🎨 Generar / Actualizar Visual
          </button>
          <button onclick="expPreviewSingleSceneMP4('${sid}')" class="py-1.5 px-3 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/40 text-emerald-200 text-xs font-semibold">
            ▶️ Probar Escena (.MP4)
          </button>
        </div>
        ${sc.preview_video_url ? `<video src="${sc.preview_video_url}" controls class="w-full max-h-48 rounded-lg bg-black border border-emerald-500/40"></video>` : ""}
      </div>
    `;
    listEl.appendChild(card);
  });
}

async function expSaveSceneEdits(sceneId) {
  if (!expCurrentProject) return;
  const narration_text = document.getElementById(`expScText_${sceneId}`).value.trim();
  const resource_type = document.getElementById(`expScResType_${sceneId}`).value;
  const compEl = document.getElementById(`expScCompType_${sceneId}`);
  const composition_type = compEl ? compEl.value : "hero_view";
  const visual_mode = document.getElementById(`expScMode_${sceneId}`).value;
  const camera_motion = document.getElementById(`expScCam_${sceneId}`).value;
  const rawLabels = document.getElementById(`expScLabels_${sceneId}`).value;
  const labels = rawLabels.split("|").map((s) => s.trim()).filter(Boolean);

  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/scene/${expActiveVersion}/${sceneId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "update",
        narration_text,
        resource_type,
        composition_type,
        visual_mode,
        camera_motion,
        labels
      })
    });
    if (!res.ok) throw new Error("No se pudo guardar la escena.");
    expCurrentProject = await res.json();
    renderExplainerStoryboardTab();
  } catch (err) {
    expShowError(err.message);
  }
}

async function expSceneAction(sceneId, action) {
  if (!expCurrentProject) return;
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/scene/${expActiveVersion}/${sceneId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    if (!res.ok) throw new Error("No se pudo modificar el orden de la escena.");
    expCurrentProject = await res.json();
    renderExplainerStoryboardTab();
  } catch (err) {
    expShowError(err.message);
  }
}

async function expGenerateSceneVisual(sceneId) {
  if (!expCurrentProject) return;
  await expSaveSceneEdits(sceneId);
  expSetProgress(true, `Generando recurso visual para escena ${sceneId}...`, 50);
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/scene/${expActiveVersion}/${sceneId}/generate-visual`, {
      method: "POST"
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "No se pudo generar el visual.");
    }
    expCurrentProject = await res.json();
    renderExplainerWorkspace();
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

async function expPreviewSingleSceneMP4(sceneId) {
  if (!expCurrentProject) return;
  expSetProgress(true, `Renderizando escena de prueba ${sceneId} en .MP4 (Fase 14)...`, 60);
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/scene/${expActiveVersion}/${sceneId}/preview`, {
      method: "POST"
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al renderizar vista previa.");
    }
    await expLoadProjectById(expCurrentProject.project_id);
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

async function expRunMultiPlatformExport(platformsOverride = null) {
  if (!expCurrentProject) return;
  let platforms = platformsOverride;
  if (!platforms) {
    platforms = [];
    document.querySelectorAll(".expPlatChk:checked").forEach((chk) => platforms.push(chk.value));
  }
  if (!platforms.length) {
    expShowError("Selecciona al menos una plataforma para exportar.");
    return;
  }
  expShowError("");
  expSetProgress(true, `Iniciando exportación de ${platforms.length} plataformas...`, 10);
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        platforms,
        synthesize_missing_audio: true,
        generate_ai_images_for_mode_a: false,
        burn_subtitles: true,
        async_mode: true
      })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al iniciar exportación.");
    }

    // Polling del estado de exportación cada 1.5s
    while (true) {
      await new Promise((r) => setTimeout(r, 1500));
      const stRes = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/export-status`);
      if (!stRes.ok) break;
      const job = await stRes.json();
      if (job.status === "completed") {
        expSetProgress(true, "¡Exportación finalizada! Recargando proyecto...", 100);
        break;
      } else if (job.status === "error") {
        throw new Error(job.error || "Error durante el renderizado.");
      } else {
        const platMsg = job.current_platform ? `Renderizando ${job.current_platform}` : "Procesando...";
        expSetProgress(true, `${platMsg} (${(job.platforms_done || []).length}/${platforms.length} completadas)...`, job.progress_pct || 25);
      }
    }

    await expLoadProjectById(expCurrentProject.project_id);
    expSwitchWorkspaceTab("exports");
    expSetProgress(false);
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

function renderExplainerExportsTab() {
  if (!expCurrentProject) return;
  const grid = document.getElementById("expSocialPackagesGrid");
  if (!grid) return;
  const packages = expCurrentProject.social_packages || {};
  const exportsMap = expCurrentProject.exports || {};
  const keys = Object.keys(packages);

  if (!keys.length) {
    grid.innerHTML = `<div class="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-400">Selecciona arriba las plataformas deseadas y presiona <strong>🚀 Exportar Plataformas Seleccionadas</strong> para generar los videos .MP4 reencuadrados, las portadas y los textos de cada red social.</div>`;
    return;
  }

  grid.innerHTML = "";
  keys.forEach((pid) => {
    const pkg = packages[pid];
    const exp = exportsMap[pid] || {};
    const card = document.createElement("div");
    card.className = "p-4 rounded-2xl bg-slate-950/90 border border-emerald-500/30 space-y-3";
    card.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
        <div>
          <span class="text-sm font-bold text-white">${exp.platform_name || pid}</span>
          <span class="ml-2 px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-xs mono">${exp.width || ""}×${exp.height || ""} (${exp.aspect_ratio || ""})</span>
        </div>
        <div class="flex items-center gap-2">
          ${pkg.video_url ? `<a href="${pkg.video_url}" download="video_${pid}.mp4" class="px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs">⬇ Video .MP4</a>` : ""}
          ${pkg.cover_url ? `<a href="${pkg.cover_url}" download="portada_${pid}.png" class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 font-semibold text-xs">🖼️ Portada</a>` : ""}
          ${pkg.srt_url ? `<a href="${pkg.srt_url}" download="subtitulos_${pid}.srt" class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 font-semibold text-xs">💬 .SRT</a>` : ""}
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
        <div class="md:col-span-5 space-y-2">
          ${pkg.video_url ? `<video src="${pkg.video_url}" controls class="w-full max-h-64 rounded-xl bg-black border border-slate-800"></video>` : ""}
          ${pkg.cover_url ? `<img src="${pkg.cover_url}" class="w-full max-h-44 object-contain rounded-xl bg-slate-900 border border-slate-800" title="Portada personalizada generada" />` : ""}
        </div>
        <div class="md:col-span-7 space-y-2 text-xs">
          <div>
            <label class="block text-[10px] uppercase text-slate-400">Título adaptado (${pid}):</label>
            <input id="expSocTitle_${pid}" value="${(pkg.title || "").replace(/"/g, "&quot;")}" class="w-full rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1.5 text-xs text-white font-semibold" />
          </div>
          <div>
            <label class="block text-[10px] uppercase text-slate-400">Descripción única para ${pid}:</label>
            <textarea id="expSocDesc_${pid}" rows="4" class="w-full rounded-lg bg-slate-900 border border-slate-800 p-2 text-xs text-slate-200">${pkg.description || ""}</textarea>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] uppercase text-slate-400">Texto de publicación:</label>
              <input id="expSocPost_${pid}" value="${(pkg.post_text || "").replace(/"/g, "&quot;")}" class="w-full rounded-lg bg-slate-900 border border-slate-800 px-2 py-1 text-xs text-slate-200" />
            </div>
            <div>
              <label class="block text-[10px] uppercase text-amber-300">Pregunta para comentarios:</label>
              <input id="expSocQuestion_${pid}" value="${(pkg.comment_question || "").replace(/"/g, "&quot;")}" class="w-full rounded-lg bg-slate-900 border border-slate-800 px-2 py-1 text-xs text-amber-200" />
            </div>
          </div>
          <div class="flex items-center justify-between gap-2 pt-1">
            <input id="expSocTags_${pid}" value="${(pkg.hashtags || []).join(' ')}" class="flex-1 rounded-lg bg-slate-900 border border-slate-800 px-2 py-1 text-xs text-indigo-300 mono" />
            <button onclick="expSaveSocialPackage('${pid}')" class="px-3 py-1.5 rounded-lg bg-indigo-500/25 hover:bg-indigo-500/40 border border-indigo-500/40 text-indigo-200 text-xs font-semibold">💾 Guardar Copy</button>
          </div>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

async function expSaveSocialPackage(pid) {
  if (!expCurrentProject) return;
  try {
    const res = await fetch(`/api/explainer/project/${expCurrentProject.project_id}/social/${pid}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: document.getElementById(`expSocTitle_${pid}`).value,
        description: document.getElementById(`expSocDesc_${pid}`).value,
        post_text: document.getElementById(`expSocPost_${pid}`).value,
        comment_question: document.getElementById(`expSocQuestion_${pid}`).value,
        hashtags: document.getElementById(`expSocTags_${pid}`).value.split(/\s+/).filter(Boolean)
      })
    });
    if (!res.ok) throw new Error("No se pudo guardar el paquete social.");
    expCurrentProject = await res.json();
  } catch (err) {
    expShowError(err.message);
  }
}

function renderExplainerQCTab() {
  if (!expCurrentProject) return;
  const qc = expCurrentProject.quality_control || {};
  const ledger = expCurrentProject.cost_ledger || {};
  const summary = ledger.summary || {};

  const qcBox = document.getElementById("expQCList");
  if (qcBox) {
    const checksHtml = (qc.checks || []).map((c) => `
      <div class="p-2.5 rounded-xl bg-slate-950 border ${c.status === 'pass' ? 'border-emerald-500/30' : 'border-amber-500/40'} flex items-start justify-between gap-2">
        <div>
          <div class="text-xs font-bold ${c.status === 'pass' ? 'text-emerald-300' : 'text-amber-300'}">
            ${c.status === 'pass' ? '✅' : '⚠️'} ${c.name}
          </div>
          <div class="text-[11px] text-slate-300 mt-0.5">${c.detail}</div>
        </div>
      </div>
    `).join("");
    qcBox.innerHTML = checksHtml;
  }

  const costBox = document.getElementById("expCostSummaryBox");
  if (costBox) {
    costBox.innerHTML = `
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="text-slate-400">Diagramas SVG Locales</div>
          <div class="text-lg font-bold text-emerald-300 mono">${summary.diagrams_rendered_local || 0} ($0.00)</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="text-slate-400">Imágenes IA Generadas</div>
          <div class="text-lg font-bold text-indigo-300 mono">${summary.images_generated || 0}</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="text-slate-400">Costo Reportado API</div>
          <div class="text-lg font-bold text-amber-300 mono">$${Number(summary.reported_cost_usd || 0).toFixed(4)} USD</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="text-slate-400">Tiempo Procesamiento</div>
          <div class="text-lg font-bold text-slate-200 mono">${summary.total_processing_sec || 0}s (Err: ${summary.errors_count || 0})</div>
        </div>
      </div>
    `;
  }
}

function expOpenBlender3DModal() {
  const modal = document.getElementById("expBlender3DModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  const vid = document.getElementById("expBlenderModalVideo");
  if (vid) {
    vid.src = `/projects/_prototype_blender_3d/prototipo_motor_4_tiempos_3d_9_16.mp4?t=${Date.now()}`;
    vid.play().catch(() => {});
  }
}

function expCloseBlender3DModal() {
  const modal = document.getElementById("expBlender3DModal");
  if (modal) modal.classList.add("hidden");
  const vid = document.getElementById("expBlenderModalVideo");
  if (vid) vid.pause();
}

async function expRunBlenderBenchmark() {
  expSetProgress(true, "Iniciando benchmark de las 8 escenas en Blender 5.3...", 30);
  try {
    const res = await fetch("/api/explainer/blender/prototype", { method: "POST" });
    if (!res.ok) throw new Error("Error al ejecutar benchmark.");
    expSetProgress(false);
    expOpenBlender3DModal();
  } catch (err) {
    expSetProgress(false);
    expShowError(err.message);
  }
}

function playBlenderScene(sceneKey) {
  const vid = document.getElementById("blenderLiveVideoPlayer");
  if (!vid) return;
  if (sceneKey === "master") {
    vid.src = `/projects/_prototype_blender_3d/prototipo_motor_4_tiempos_3d_9_16.mp4?t=${Date.now()}`;
  } else {
    vid.src = `/projects/_prototype_blender_3d/PROT_0${sceneKey}_final.mp4?t=${Date.now()}`;
  }
  vid.play().catch(() => {});
}

async function runCustomBlenderRender() {
  const model = document.getElementById("blenderModelSelect").value;
  const comp = document.getElementById("blenderCompositionSelect").value;
  const fmt = document.getElementById("blenderFormatSelect").value;
  const prof = document.getElementById("blenderProfileSelect").value;
  const narr = (document.getElementById("blenderNarrationInput").value || "").trim();

  const progBox = document.getElementById("blenderProgressBarContainer");
  const progText = document.getElementById("blenderProgressText");
  const progBar = document.getElementById("blenderProgressBar");
  const progPct = document.getElementById("blenderProgressPct");
  const errBox = document.getElementById("blenderErrorBox");

  if (errBox) { errBox.classList.add("hidden"); errBox.textContent = ""; }
  if (progBox) progBox.classList.remove("hidden");
  if (progText) progText.textContent = `Iniciando renderizado 3D en Blender 5.3 (${comp})...`;
  if (progBar) progBar.style.width = "25%";
  if (progPct) progPct.textContent = "25%";

  const btn = document.getElementById("btnBlenderRenderScene");
  if (btn) btn.disabled = true;

  try {
    const refFileInput = document.getElementById("blenderReferenceFile");
    const refModeEl = document.getElementById("blenderReferenceModeSelect");
    const profEl = document.getElementById("blenderVisualProfileSelect");
    const summaryEl = document.getElementById("blenderVisualDirectionSummary");
    const hiddenPathEl = document.getElementById("blenderReferencePathHidden");

    const refMode = refModeEl ? refModeEl.value : "full";
    const visProfId = profEl && profEl.value ? profEl.value : null;
    let savedRefPath = hiddenPathEl && hiddenPathEl.value ? hiddenPathEl.value : null;

    if (refFileInput && refFileInput.files && refFileInput.files.length > 0 && refMode !== "autonomous") {
      if (progText) progText.textContent = "Analizando imagen de referencia con OpenCV local (Modo A)...";
      const fd = new FormData();
      fd.append("file", refFileInput.files[0]);
      fd.append("reference_mode", refMode);
      fd.append("topic", narr || model);
      fd.append("model_type", model);
      const upRes = await fetch("/api/explainer/blender/upload-reference", { method: "POST", body: fd });
      if (upRes.ok) {
        const upData = await upRes.json();
        savedRefPath = upData.saved_reference_path || null;
        if (hiddenPathEl) hiddenPathEl.value = savedRefPath || "";
        if (summaryEl && upData.visual_direction) {
          const bd = upData.visual_direction.backdrop || {};
          const mt = upData.visual_direction.materials || {};
          summaryEl.textContent = `Modo A Activo (${refMode}): Fondo ${bd.bg_hex || ""} · Cuerpo ${mt.primary_body_hex || ""} · Acento ${mt.accent_moving_hex || ""}`;
        }
      }
    } else if (summaryEl && refMode === "autonomous") {
      savedRefPath = null;
      summaryEl.textContent = `Modo B Autónomo activo: Perfil ${visProfId || "seleccionado por significado del contenido"}.`;
    }

    const payload = {
      model_name: model,
      composition: comp,
      is_vertical: fmt === "9:16",
      render_profile: prof,
      duration_sec: 4.0,
      narration: narr,
      reference_image_path: savedRefPath,
      reference_mode: refMode,
      visual_profile_id: visProfId
    };
    if (progBar) progBar.style.width = "50%";
    if (progPct) progPct.textContent = "50%";
    if (progText) progText.textContent = "Procesando geometría 3D, animación cinemática y sombreado EEVEE Next...";

    const res = await fetch("/api/explainer/blender/render-scene", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al renderizar escena en Blender.");
    }
    const data = await res.json();
    if (progBar) progBar.style.width = "100%";
    if (progPct) progPct.textContent = "100%";
    if (progText) progText.textContent = "¡Renderizado completado con éxito!";

    const vid = document.getElementById("blenderLiveVideoPlayer");
    if (vid) {
      vid.src = `${data.video_url}?t=${Date.now()}`;
      vid.play().catch(() => {});
    }
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

async function rebuildBlenderBenchmark() {
  const progBox = document.getElementById("blenderProgressBarContainer");
  const progText = document.getElementById("blenderProgressText");
  const progBar = document.getElementById("blenderProgressBar");
  const progPct = document.getElementById("blenderProgressPct");
  const errBox = document.getElementById("blenderErrorBox");

  if (errBox) { errBox.classList.add("hidden"); errBox.textContent = ""; }
  if (progBox) progBox.classList.remove("hidden");
  if (progText) progText.textContent = "Re-ejecutando benchmark completo de 8 escenas en Blender 5.3...";
  if (progBar) progBar.style.width = "20%";

  try {
    const res = await fetch("/api/explainer/blender/prototype", { method: "POST" });
    if (!res.ok) throw new Error("Error en la ejecución del benchmark.");
    const data = await res.json();
    if (progBar) progBar.style.width = "100%";
    if (progText) progText.textContent = "¡Benchmark completo renderizado y ensamblado!";
    const vid = document.getElementById("blenderLiveVideoPlayer");
    if (vid) {
      vid.src = `/projects/_prototype_blender_3d/prototipo_motor_4_tiempos_3d_9_16.mp4?t=${Date.now()}`;
      vid.play().catch(() => {});
    }
    setTimeout(() => { if (progBox) progBox.classList.add("hidden"); }, 2500);
  } catch (err) {
    if (errBox) {
      errBox.textContent = err.message;
      errBox.classList.remove("hidden");
    }
    if (progBox) progBox.classList.add("hidden");
  }
}

window.expOpenBlender3DModal = expOpenBlender3DModal;
window.expCloseBlender3DModal = expCloseBlender3DModal;
window.expRunBlenderBenchmark = expRunBlenderBenchmark;
window.playBlenderScene = playBlenderScene;
window.runCustomBlenderRender = runCustomBlenderRender;
window.rebuildBlenderBenchmark = rebuildBlenderBenchmark;

window.addEventListener("DOMContentLoaded", () => {
  initExplainerStudio();
  setTimeout(populateExplainerVoiceSelect, 900);
});
