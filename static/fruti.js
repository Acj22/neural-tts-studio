// ============================================================================
// 🍓 FRUTINOVELAS — Frontend Controller (Diálogos Multi-Voz + Animación Local)
// ============================================================================

let frutiParsedCast = [];
let currentFrutiProject = null;
let frutiMusicB64 = null;
let frutiMusicExt = "mp3";

const EMOTION_LABELS = {
  normal: "😐 Normal",
  grito: "🤬 Grito / Furia (Sacudida + Zoom)",
  llanto: "😭 Llanto / Tristeza (Vaivén + Azul)",
  sorpresa: "😱 Sorpresa / Impacto (Flash + Zoom)",
  drama: "🎭 Drama Telenovela (Triple Zoom)",
  risa: "😂 Risa / Burla (Rebote rápido)",
  susurro: "🤫 Susurro / Secreto (Sombra)"
};

function frutiShowError(msg) {
  const el = document.getElementById("frutiError");
  if (!el) return;
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
  } else {
    el.textContent = msg;
    el.classList.remove("hidden");
  }
}

function frutiShowProgress(msg) {
  const el = document.getElementById("frutiProgress");
  if (!el) return;
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
  } else {
    el.textContent = msg;
    el.classList.remove("hidden");
  }
}

function frutiLoadSample() {
  const sample = `# Episodio Piloto: "El Jugo de la Traición"
Narrador: En una lujosa mansión de Guadalajara, el amor estaba a punto de pudrirse.
[Fresa] (llorando): ¡Dime la verdad, Cocardo! ¿Me estás engañando con la Papaya?
[Cocardo]: ¡Cálmate mi reina! Solo me pidió que le ayudara a abrir su cáscara.
[Fresa] (sorpresa): ¿¡QUÉ!? ¡Entonces explícame por qué tienes semillas de papaya en el bigote!
[Cocardo] (drama): Está bien... lo confieso. ¡Ella sí comprende mi corazón tropical!
[Fresa] (gritando): ¡ERES UN CÍNICO, COCARDO! ¡Nuestro matrimonio se va directo a la licuadora!
Narrador: ¿Podrá Fresa superar esta traición? Descúbrelo en el próximo capítulo.`;
  const box = document.getElementById("frutiScript");
  if (box) box.value = sample;
}

function frutiGetSpanishVoices() {
  const all = (typeof voicesCatalog !== "undefined" && voicesCatalog.kokoro) ? voicesCatalog.kokoro : [];
  const es = all.filter((v) => (v.lang || "").startsWith("es"));
  return es.length ? es : all;
}

async function frutiParse() {
  frutiShowError(null);
  const script = (document.getElementById("frutiScript").value || "").trim();
  if (!script) {
    frutiShowError("Por favor escribe o carga un guion con diálogos primero.");
    return;
  }

  const btn = document.getElementById("frutiBtnParse");
  btn.disabled = true;
  frutiShowProgress("⏳ Analizando guion y detectando personajes...");

  try {
    const res = await fetch("/api/fruti/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ script })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorDetail(err, res.status));
    }
    const data = await res.json();
    frutiParsedCast = data.characters || [];
    frutiRenderCastEditor(data.lines || []);
  } catch (e) {
    frutiShowError(e.message);
  } finally {
    btn.disabled = false;
    frutiShowProgress(null);
  }
}

function frutiRenderCastEditor(lines) {
  const box = document.getElementById("frutiCastBox");
  const list = document.getElementById("frutiCastList");
  const count = document.getElementById("frutiCastCount");
  box.classList.remove("hidden");
  count.textContent = `${frutiParsedCast.length} personajes · ${lines.length} diálogos`;
  list.innerHTML = "";

  const voices = frutiGetSpanishVoices();

  frutiParsedCast.forEach((ch, idx) => {
    const voiceOpts = voices
      .map((v) => `<option value="${v.id}" ${v.id === ch.voice ? "selected" : ""}>${v.name}</option>`)
      .join("");

    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3";
    card.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2.5">
          <input type="color" id="frutiCharColor_${idx}" value="${ch.color || "#f43f5e"}" class="w-6 h-6 rounded cursor-pointer bg-transparent border-0" />
          <span class="font-bold text-sm text-white">${ch.name}</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] mono">${ch.line_count} línea(s)</span>
          ${ch.is_narrator ? `<span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[11px]">Narrador / Voz en Off</span>` : ""}
        </div>
        ${!ch.is_narrator ? `
        <div class="flex items-center gap-2 text-xs">
          <label class="text-slate-400">Fruta/Verdura:</label>
          <input id="frutiCharFruit_${idx}" value="${(ch.fruit || "").replace(/"/g, "&quot;")}" placeholder="ej. fresa, coco, aguacate" class="rounded-lg bg-slate-950 border border-slate-700 px-2.5 py-1 text-xs text-white w-32" />
          <select id="frutiCharGender_${idx}" class="rounded-lg bg-slate-950 border border-slate-700 px-2 py-1 text-xs text-white">
            <option value="F" ${ch.gender === "F" ? "selected" : ""}>♀ Femenino</option>
            <option value="M" ${ch.gender !== "F" ? "selected" : ""}>♂ Masculino</option>
          </select>
        </div>` : ""}
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
        <div class="sm:col-span-7">
          <label class="block text-[11px] text-slate-400 mb-1">Voz Neuronal Asignada:</label>
          <select id="frutiCharVoice_${idx}" class="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white">
            ${voiceOpts}
          </select>
        </div>
        <div class="sm:col-span-5">
          <label class="block text-[11px] text-slate-400 mb-1">Velocidad / Tono: <span id="frutiCharSpeedVal_${idx}" class="mono text-pink-300">${ch.speed}x</span></label>
          <input id="frutiCharSpeed_${idx}" type="range" min="0.75" max="1.35" step="0.05" value="${ch.speed}"
            oninput="document.getElementById('frutiCharSpeedVal_${idx}').textContent = this.value + 'x'"
            class="w-full" />
        </div>
      </div>

      ${!ch.is_narrator ? `
      <div>
        <label class="block text-[11px] text-slate-400 mb-1">Apariencia / Rasgos del personaje (para generar su retrato 3D):</label>
        <input id="frutiCharDesc_${idx}" value="${(ch.description || "").replace(/"/g, "&quot;")}"
          class="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs text-slate-200" />
      </div>` : ""}
    `;
    list.appendChild(card);
  });
}

async function frutiCreate() {
  frutiShowError(null);
  const script = (document.getElementById("frutiScript").value || "").trim();
  if (!script || !frutiParsedCast.length) {
    frutiShowError("Primero detecta los personajes del guion.");
    return;
  }

  const characters = frutiParsedCast.map((ch, idx) => ({
    name: ch.name,
    slug: ch.slug,
    is_narrator: !!ch.is_narrator,
    voice: document.getElementById(`frutiCharVoice_${idx}`).value,
    speed: parseFloat(document.getElementById(`frutiCharSpeed_${idx}`).value),
    color: document.getElementById(`frutiCharColor_${idx}`).value,
    fruit: (!ch.is_narrator && document.getElementById(`frutiCharFruit_${idx}`)) ? document.getElementById(`frutiCharFruit_${idx}`).value.trim() : "",
    gender: (!ch.is_narrator && document.getElementById(`frutiCharGender_${idx}`)) ? document.getElementById(`frutiCharGender_${idx}`).value : ch.gender,
    description: (!ch.is_narrator && document.getElementById(`frutiCharDesc_${idx}`)) ? document.getElementById(`frutiCharDesc_${idx}`).value.trim() : ""
  }));

  const payload = {
    script,
    characters,
    setting: document.getElementById("frutiSetting").value.trim(),
    aspect_ratio: document.getElementById("frutiAspect").value,
    line_pause: parseFloat(document.getElementById("frutiPause").value),
    style_prompt: document.getElementById("frutiStyle").value.trim(),
    lang: document.getElementById("langSelect") ? document.getElementById("langSelect").value : "es-mx"
  };

  const btn = document.getElementById("frutiBtnCreate");
  btn.disabled = true;
  frutiShowProgress("🎙️ Sintetizando las voces de cada personaje y calculando tiempos exactos...");

  try {
    const res = await fetch("/api/fruti/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorDetail(err, res.status));
    }
    currentFrutiProject = await res.json();
    frutiRenderProjectUI();
  } catch (e) {
    frutiShowError(e.message);
  } finally {
    btn.disabled = false;
    frutiShowProgress(null);
  }
}

function frutiRenderProjectUI() {
  if (!currentFrutiProject) return;
  const p = currentFrutiProject;
  document.getElementById("frutiProjectBox").classList.remove("hidden");
  document.getElementById("frutiDurBadge").textContent = `${p.lines.length} diálogos · ${p.total_duration_sec}s`;
  document.getElementById("frutiWavLink").href = p.master_audio_url;
  document.getElementById("frutiSrtLink").href = p.srt_url;
  document.getElementById("frutiAudio").src = p.master_audio_url + `?t=${Date.now()}`;

  if (p.video_url) {
    document.getElementById("frutiVideoBox").classList.remove("hidden");
    document.getElementById("frutiVideo").src = p.video_url;
    document.getElementById("frutiVideoLink").href = p.video_url;
  } else {
    document.getElementById("frutiVideoBox").classList.add("hidden");
  }

  // 1. Renderizar tarjetas de personajes + toma grupal
  const grid = document.getElementById("frutiCharGrid");
  grid.innerHTML = "";
  const visualItems = [
    ...p.characters.filter((c) => !c.is_narrator),
    { ...p.group, is_group: true, color: "#a855f7" }
  ];

  visualItems.forEach((item) => {
    const slug = item.slug;
    const isGroup = !!item.is_group;
    const mouth = item.mouth || { x: 0.5, y: 0.58, w: 0.14, enabled: true };
    const mxPct = Math.round((mouth.x || 0.5) * 100);
    const myPct = Math.round((mouth.y || 0.58) * 100);

    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3 flex flex-col justify-between";
    card.innerHTML = `
      <div class="space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="font-bold text-xs text-white flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background:${item.color || "#f43f5e"}"></span>
            ${item.name}
          </span>
          <span class="text-[10px] text-slate-400 mono">${isGroup ? "Escena Narrador" : (item.fruit_en || "Personaje")}</span>
        </div>

        <div class="relative w-full h-64 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center">
          ${item.image_url ? `
            <img
              id="frutiImg_${slug}"
              src="${item.image_url}"
              onclick="${!isGroup ? `frutiClickMouth('${slug}', event, this)` : ""}"
              class="w-full h-full object-cover ${!isGroup ? "cursor-crosshair" : ""}"
              title="${!isGroup ? "Haz clic donde está la boca para posicionar la animación" : ""}"
            />
            ${!isGroup && mouth.enabled ? `
              <div
                style="left:${mxPct}%; top:${myPct}%; transform:translate(-50%,-50%);"
                class="pointer-events-none absolute px-2 py-0.5 rounded-full bg-rose-600/90 border border-white text-[10px] text-white font-bold shadow-lg"
              >👄 Boca</div>
            ` : ""}
          ` : `
            <div class="text-center p-4 text-xs text-slate-500">
              <p class="font-semibold text-slate-400">Sin retrato aún</p>
              <p class="text-[11px] mt-1">Se usará un avatar animado provisional o genera/sube su retrato abajo.</p>
            </div>
          `}
        </div>

        ${!isGroup ? `
        <div class="p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 space-y-1.5 text-[11px]">
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-1.5 text-slate-300 cursor-pointer">
              <input type="checkbox" ${mouth.enabled ? "checked" : ""} onchange="frutiToggleMouth('${slug}', this.checked)" class="accent-pink-500" />
              Animar boca al hablar
            </label>
            <span class="text-slate-500 mono">x:${mxPct}% y:${myPct}%</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-slate-400">Tamaño boca:</span>
            <input type="range" min="0.06" max="0.28" step="0.01" value="${mouth.w || 0.14}"
              onchange="frutiMouthWidth('${slug}', parseFloat(this.value))" class="flex-1" />
          </div>
        </div>` : ""}

        <div>
          <label class="block text-[10px] uppercase tracking-wider text-slate-400 mb-1">Prompt del retrato:</label>
          <textarea id="frutiPrompt_${slug}" rows="2" class="w-full rounded-lg bg-slate-950 border border-slate-800 p-2 text-[11px] text-slate-300">${(item.prompt || "").replace(/</g, "&lt;")}</textarea>
        </div>
      </div>

      <div class="flex items-center gap-1.5 pt-1">
        <button id="frutiBtnImg_${slug}" onclick="frutiGenerateCharImage('${slug}', false)" class="flex-1 py-2 px-2 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 text-xs font-semibold">
          🎨 ${item.image_url ? "Regenerar" : "Generar IA"}
        </button>
        ${item.image_url ? `
        <button onclick="frutiGenerateCharImage('${slug}', true)" title="Probar otra variación" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200">🎲</button>
        ` : ""}
        <label title="Subir imagen desde tu PC" class="cursor-pointer py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200">
          📤
          <input type="file" accept="image/*" class="hidden" onchange="frutiUploadCharImage('${slug}', this)" />
        </label>
      </div>
    `;
    grid.appendChild(card);
  });

  // 2. Renderizar línea de tiempo de diálogos
  const linesEl = document.getElementById("frutiLines");
  linesEl.innerHTML = "";
  const charBySlug = {};
  p.characters.forEach((c) => { charBySlug[c.slug] = c; });

  p.lines.forEach((ln) => {
    const ch = charBySlug[ln.slug] || {};
    const emoOpts = Object.keys(EMOTION_LABELS)
      .map((k) => `<option value="${k}" ${ln.emotion === k ? "selected" : ""}>${EMOTION_LABELS[k]}</option>`)
      .join("");

    const row = document.createElement("div");
    row.className = "p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2.5";
    row.innerHTML = `
      <div class="space-y-1 flex-1">
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span class="px-2 py-0.5 rounded font-bold text-slate-950" style="background:${ch.color || "#94a3b8"}">${ln.speaker}</span>
          <span class="text-slate-400 mono text-[11px]">⏱ ${ln.timestamp_label}</span>
        </div>
        <p class="text-xs text-slate-100">"${ln.text.replace(/</g, "&lt;")}"</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <select onchange="frutiChangeLineEmotion(${ln.index}, this.value)" class="rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-pink-200">
          ${emoOpts}
        </select>
        <audio src="${ln.audio_url}" controls class="h-7 w-36"></audio>
      </div>
    `;
    linesEl.appendChild(row);
  });
}

async function frutiGenerateCharImage(slug, variation = false) {
  if (!currentFrutiProject) return;
  frutiShowError(null);
  const btn = document.getElementById(`frutiBtnImg_${slug}`);
  const promptEl = document.getElementById(`frutiPrompt_${slug}`);
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Generando...";
  }
  try {
    const res = await fetch(`/api/fruti/${currentFrutiProject.project_id}/character/${slug}/image`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: promptEl ? promptEl.value.trim() : null,
        variation: !!variation
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorDetail(err, res.status));
    }
    currentFrutiProject = await res.json();
    frutiRenderProjectUI();
  } catch (e) {
    frutiShowError(`Personaje (${slug}): ${e.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "🎨 Regenerar";
    }
  }
}

async function frutiGenerateAllImages() {
  if (!currentFrutiProject) return;
  const targets = [
    ...currentFrutiProject.characters.filter((c) => !c.is_narrator && !c.image_url),
    ...(!currentFrutiProject.group.image_url ? [currentFrutiProject.group] : [])
  ];
  if (!targets.length) {
    alert("¡Todos los personajes ya tienen su imagen!");
    return;
  }
  for (let i = 0; i < targets.length; i++) {
    frutiShowProgress(`🎨 Generando retrato ${i + 1} de ${targets.length} (${targets[i].name})...`);
    await frutiGenerateCharImage(targets[i].slug, false);
  }
  frutiShowProgress(null);
}

function frutiUploadCharImage(slug, input) {
  if (!currentFrutiProject || !input.files || !input.files[0]) return;
  const reader = new FileReader();
  reader.onload = async (ev) => {
    try {
      const res = await fetch(`/api/fruti/${currentFrutiProject.project_id}/character/${slug}/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_b64: ev.target.result })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(parseErrorDetail(err, res.status));
      }
      currentFrutiProject = await res.json();
      frutiRenderProjectUI();
    } catch (e) {
      frutiShowError(e.message);
    }
  };
  reader.readAsDataURL(input.files[0]);
}

function frutiFindChar(slug) {
  if (!currentFrutiProject) return null;
  return currentFrutiProject.characters.find((c) => c.slug === slug);
}

async function frutiSaveMouth(slug, mouthObj) {
  if (!currentFrutiProject) return;
  const res = await fetch(`/api/fruti/${currentFrutiProject.project_id}/character/${slug}/mouth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mouthObj)
  });
  if (res.ok) {
    currentFrutiProject = await res.json();
    frutiRenderProjectUI();
  }
}

function frutiClickMouth(slug, ev, imgEl) {
  const ch = frutiFindChar(slug);
  if (!ch) return;
  const rect = imgEl.getBoundingClientRect();
  const x = Math.max(0.05, Math.min(0.95, (ev.clientX - rect.left) / rect.width));
  const y = Math.max(0.05, Math.min(0.95, (ev.clientY - rect.top) / rect.height));
  const m = ch.mouth || { x: 0.5, y: 0.58, w: 0.14, enabled: true };
  frutiSaveMouth(slug, { x, y, w: m.w || 0.14, enabled: true });
}

function frutiToggleMouth(slug, enabled) {
  const ch = frutiFindChar(slug);
  if (!ch) return;
  const m = ch.mouth || { x: 0.5, y: 0.58, w: 0.14, enabled: true };
  frutiSaveMouth(slug, { x: m.x, y: m.y, w: m.w, enabled: !!enabled });
}

function frutiMouthWidth(slug, w) {
  const ch = frutiFindChar(slug);
  if (!ch) return;
  const m = ch.mouth || { x: 0.5, y: 0.58, w: 0.14, enabled: true };
  frutiSaveMouth(slug, { x: m.x, y: m.y, w: w, enabled: m.enabled !== false });
}

async function frutiChangeLineEmotion(lineIndex, emotion) {
  if (!currentFrutiProject) return;
  const res = await fetch(`/api/fruti/${currentFrutiProject.project_id}/line/${lineIndex}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ emotion })
  });
  if (res.ok) {
    currentFrutiProject = await res.json();
  }
}

function frutiOnMusic(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  frutiMusicExt = (file.name.split(".").pop() || "mp3").toLowerCase();
  const reader = new FileReader();
  reader.onload = (ev) => {
    frutiMusicB64 = ev.target.result;
    document.getElementById("frutiMusicStatus").textContent = `🎵 Música cargada: ${file.name}`;
  };
  reader.readAsDataURL(file);
}

async function frutiRender() {
  if (!currentFrutiProject) return;
  frutiShowError(null);
  const btn = document.getElementById("frutiBtnRender");
  btn.disabled = true;
  btn.textContent = "⏳ Animando bocas, cámara dramática y renderizando MP4...";

  try {
    const payload = {
      burn_subtitles: document.getElementById("frutiSubs").checked,
      intensity: parseFloat(document.getElementById("frutiIntensity").value),
      music_b64: frutiMusicB64,
      music_ext: frutiMusicExt,
      music_volume: parseFloat(document.getElementById("frutiMusicVol").value)
    };
    const res = await fetch(`/api/fruti/${currentFrutiProject.project_id}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorDetail(err, res.status));
    }
    currentFrutiProject = await res.json();
    frutiRenderProjectUI();
  } catch (e) {
    frutiShowError(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "🎬 Animar y Renderizar Frutinovela (.MP4)";
  }
}
