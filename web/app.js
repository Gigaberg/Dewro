/* Harmonize — frontend logic. Talks to the Flask API, renders results. */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function spinner(label) {
  return `<div class="glass-card rounded-2xl p-6 flex items-center gap-4">
    <div class="spinner"></div><span class="text-sub font-medium">${esc(label)}</span></div>`;
}

function errorBox(msg) {
  return `<div class="rounded-2xl p-5 bg-red-50 border border-red-200 text-red-700 text-sm font-medium">${esc(msg)}</div>`;
}

function metrics(items) {
  return `<div class="grid grid-cols-3 gap-4 mb-6">${items.map((m) => `
    <div class="glass-card rounded-2xl p-5 text-center">
      <div class="text-3xl font-black text-ink">${esc(m.value)}</div>
      <div class="text-xs font-semibold uppercase tracking-wide text-sub mt-1">${esc(m.label)}</div>
    </div>`).join("")}</div>`;
}

function table(cols, rows) {
  if (!rows.length) return `<p class="text-sub text-sm">No rows.</p>`;
  return `<div class="table-wrap glass-card"><table class="data-table w-full">
    <thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${cols.map((c) => `<td>${esc(r[c])}</td>`).join("")}</tr>`).join("")}</tbody>
  </table></div>`;
}

/* ------------------------------------------------------------------ */
/* Tab navigation                                                      */
/* ------------------------------------------------------------------ */
function showTab(name) {
  $$(".panel").forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== name));
  $$(".tabbtn").forEach((b) => {
    const on = b.dataset.tab === name;
    b.classList.toggle("bg-ink", on);
    b.classList.toggle("text-white", on);
    b.classList.toggle("text-sub", !on);
  });
  $$(".tab-link").forEach((l) => l.classList.toggle("active", l.dataset.tab === name));
}

$$("[data-tab]").forEach((el) =>
  el.addEventListener("click", () => {
    showTab(el.dataset.tab);
    closeMenu();
  }));

/* Sub-source toggles (paste / flipkart / csv …) */
function wireSrcTabs(tabsSel, onChange) {
  const container = $(tabsSel);
  if (!container) return;
  const section = container.closest("section");
  const btns = $$(".srcbtn", container);
  const setActive = (src) => {
    btns.forEach((b) => {
      const on = b.dataset.src === src;
      b.classList.toggle("bg-ink", on);
      b.classList.toggle("text-white", on);
      b.classList.toggle("bg-slate-100", !on);
      b.classList.toggle("text-sub", !on);
    });
    $$("[data-src-panel]", section).forEach((p) =>
      p.classList.toggle("hidden", p.dataset.srcPanel !== src));
    if (onChange) onChange(src);
  };
  btns.forEach((b) => b.addEventListener("click", () => setActive(b.dataset.src)));
  setActive(btns[0].dataset.src);
  return setActive;
}

/* ------------------------------------------------------------------ */
/* Mobile menu                                                         */
/* ------------------------------------------------------------------ */
const mobileMenu = $("#mobileMenu");
function closeMenu() {
  mobileMenu.classList.add("translate-x-full");
  $("#iconOpen").classList.remove("hidden");
  $("#iconClose").classList.add("hidden");
  document.body.style.overflow = "auto";
}
$("#menuBtn").addEventListener("click", () => {
  const open = mobileMenu.classList.contains("translate-x-full");
  if (open) {
    mobileMenu.classList.remove("translate-x-full");
    $("#iconOpen").classList.add("hidden");
    $("#iconClose").classList.remove("hidden");
    document.body.style.overflow = "hidden";
  } else closeMenu();
});

/* ------------------------------------------------------------------ */
/* Live slider labels                                                  */
/* ------------------------------------------------------------------ */
const bindLabel = (input, label, fmt = (v) => v) => {
  const i = $(input), l = $(label);
  if (i && l) i.addEventListener("input", () => (l.textContent = fmt(i.value)));
};
bindLabel("#pipeThresh", "#pipeThreshVal");
bindLabel("#pipeLimit", "#pipeLimitVal");
bindLabel("#dupThresh", "#dupThreshVal");
bindLabel("#dupLimit", "#dupLimitVal");

/* ------------------------------------------------------------------ */
/* Populate Flipkart categories                                        */
/* ------------------------------------------------------------------ */
async function loadCategories() {
  try {
    const { categories } = await api("/api/flipkart/categories");
    const opts = categories.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    ["#pipeCat", "#dupCat"].forEach((s) => { if ($(s)) $(s).innerHTML = opts; });
  } catch (e) { /* non-fatal */ }
}

/* ------------------------------------------------------------------ */
/* DATA tab                                                            */
/* ------------------------------------------------------------------ */
async function loadOverview() {
  const el = $("#dataOverview");
  el.innerHTML = spinner("Loading dataset overview…");
  try {
    const { columns, rows } = await api("/api/data/overview");
    el.innerHTML = table(columns, rows);
  } catch (e) { el.innerHTML = errorBox(e.message); }
}
async function loadPreview() {
  const el = $("#dataPreview");
  el.innerHTML = spinner("Loading preview…");
  try {
    const { tables, error } = await api("/api/data/preview?dataset=" + $("#dataPick").value);
    if (error) { el.innerHTML = errorBox(error); return; }
    el.innerHTML = tables.map((t) =>
      `<h3 class="font-semibold text-sub mt-5 mb-2">${esc(t.name)}</h3>${table(t.columns, t.rows)}`).join("");
  } catch (e) { el.innerHTML = errorBox(e.message); }
}
$("#dataPick").addEventListener("change", loadPreview);

/* ------------------------------------------------------------------ */
/* PIPELINE tab                                                        */
/* ------------------------------------------------------------------ */
let pipeSrc = "paste";
let csvRows = null;
wireSrcTabs("#pipeSrcTabs", (src) => (pipeSrc = src));

$("#pipeCsv").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  const wrap = $("#pipeCsvColWrap");
  wrap.classList.remove("hidden");
  $("#pipeCsvCol").innerHTML = `<option>loading…</option>`;
  try {
    const { columns, rows, suggested } = await api("/api/csv/inspect", { method: "POST", body: fd });
    csvRows = rows;
    $("#pipeCsvCol").innerHTML = columns.map((c) =>
      `<option value="${esc(c)}"${c === suggested ? " selected" : ""}>${esc(c)}</option>`).join("");
  } catch (err) { $("#pipeCsvCol").innerHTML = `<option>${esc(err.message)}</option>`; }
});

$("#pipeRun").addEventListener("click", async () => {
  const out = $("#pipeOut");
  const body = {
    threshold: parseFloat($("#pipeThresh").value),
    method: $("#pipeMethod").value,
    run_t5: $("#pipeT5").checked,
  };
  if (pipeSrc === "paste") {
    body.texts = $("#pipePaste").value.split("\n").map((s) => s.trim()).filter(Boolean);
  } else if (pipeSrc === "flipkart") {
    body.category = $("#pipeCat").value;
    body.limit = parseInt($("#pipeLimit").value, 10);
  } else {
    if (!csvRows) { out.innerHTML = errorBox("Upload a CSV and pick a column first."); return; }
    const col = $("#pipeCsvCol").value;
    body.texts = csvRows.map((r) => r[col]).filter(Boolean);
  }
  out.innerHTML = spinner("Harmonizing descriptions… (first run loads the model)");
  try {
    const d = await api("/api/pipeline", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const csvBlob = "data:text/csv;charset=utf-8," + encodeURIComponent(d.csv);
    out.innerHTML =
      metrics([
        { label: "Descriptions in", value: d.n_in },
        { label: "Harmonized records", value: d.n_records },
        { label: "Duplicate groups", value: d.n_groups },
      ]) +
      `<div class="flex items-center justify-between mb-3">
         <h3 class="font-serif text-xl font-bold">Harmonized records</h3>
         <a href="${csvBlob}" download="harmonized_records.csv"
            class="text-sm font-semibold text-brand hover:underline">↓ Download CSV</a>
       </div>` +
      table(d.columns, d.rows);
  } catch (e) { out.innerHTML = errorBox(e.message); }
});

/* ------------------------------------------------------------------ */
/* DUPLICATES tab                                                      */
/* ------------------------------------------------------------------ */
let dupSrc = "flipkart";
wireSrcTabs("#dupSrcTabs", (src) => (dupSrc = src));

$("#dupRun").addEventListener("click", async () => {
  const out = $("#dupOut");
  const body = { threshold: parseFloat($("#dupThresh").value), method: $("#dupMethod").value };
  if (dupSrc === "flipkart") {
    body.category = $("#dupCat").value;
    body.limit = parseInt($("#dupLimit").value, 10);
  } else {
    body.texts = $("#dupPaste").value.split("\n").map((s) => s.trim()).filter(Boolean);
  }
  out.innerHTML = spinner("Embedding and clustering…");
  try {
    const d = await api("/api/dedupe", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let html = metrics([
      { label: "Items", value: d.n_items },
      { label: "Duplicate groups", value: d.n_groups },
      { label: "Items in a group", value: d.n_in_groups },
    ]);
    if (!d.groups.length) html += `<p class="text-sub">No duplicate groups at this threshold. Try lowering it.</p>`;
    html += d.groups.map((g) => `
      <div class="glass-card rounded-2xl p-5 mb-4">
        <div class="flex items-center justify-between mb-3">
          <h4 class="font-semibold">Group ${g.id} — ${g.size} items</h4>
          <span class="text-xs font-semibold text-brand bg-brand/10 px-2.5 py-1 rounded-full">top ${g.top.toFixed(2)}</span>
        </div>
        <ul class="list-disc pl-5 text-sm text-ink/90 space-y-1 mb-3">
          ${g.members.map((m) => `<li>${esc(m)}</li>`).join("")}
        </ul>
        ${table(["a", "b", "sim"], g.pairs.map((p) => ({ a: p.a, b: p.b, sim: p.sim })))}
      </div>`).join("");
    out.innerHTML = html;
  } catch (e) { out.innerHTML = errorBox(e.message); }
});

/* ------------------------------------------------------------------ */
/* EXTRACT tab                                                         */
/* ------------------------------------------------------------------ */
let exSrc = "text";
wireSrcTabs("#exSrcTabs", (src) => (exSrc = src));

$("#exRun").addEventListener("click", async () => {
  const out = $("#exOut");
  const body = { source: exSrc };
  if (exSrc === "text") body.text = $("#exText").value;
  else if (exSrc === "wdc") body.index = parseInt($("#exWdcIdx").value, 10);
  else body.index = parseInt($("#exFkIdx").value, 10);

  out.innerHTML = spinner("Extracting attributes…");
  try {
    const d = await api("/api/extract", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let html = "";
    if (body.source !== "text")
      html += `<div class="glass-card rounded-2xl p-4 mb-4 text-sm text-sub"><span class="font-semibold text-ink">Raw:</span> ${esc(d.text)}</div>`;
    if (!d.spacy)
      html += `<div class="rounded-xl p-3 mb-4 bg-amber-50 border border-amber-200 text-amber-800 text-xs">spaCy model missing — regex rules still active.</div>`;
    const extractedTbl = table(["field", "value"], d.fields);
    if (d.gold) {
      html += `<div class="grid md:grid-cols-2 gap-5">
        <div><h4 class="font-semibold mb-2">Extracted (this pipeline)</h4>${extractedTbl}</div>
        <div><h4 class="font-semibold mb-2">WDC-PAVE gold <span class="text-xs font-normal text-sub">(illustrative)</span></h4>${table(["field", "value"], d.gold)}</div>
      </div>`;
    } else if (!d.fields.length) {
      html += `<p class="text-sub">No attributes found.</p>`;
    } else {
      html += extractedTbl;
    }
    out.innerHTML = html;
  } catch (e) { out.innerHTML = errorBox(e.message); }
});

/* ------------------------------------------------------------------ */
/* STANDARDIZE tab                                                     */
/* ------------------------------------------------------------------ */
$("#stdRun").addEventListener("click", async () => {
  const out = $("#stdOut");
  out.innerHTML = spinner("Normalizing…");
  try {
    const d = await api("/api/standardize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("#stdText").value, run_t5: $("#stdT5").checked }),
    });
    let html = `<div class="grid md:grid-cols-2 gap-5">
      <div class="glass-card rounded-2xl p-5">
        <div class="text-xs font-semibold uppercase tracking-wide text-sub mb-2">Raw</div>
        <div class="font-mono text-sm text-ink/90">${esc(d.raw)}</div>
      </div>
      <div class="rounded-2xl p-5 bg-emerald-50 border border-emerald-200">
        <div class="text-xs font-semibold uppercase tracking-wide text-emerald-700 mb-2">Normalized (rules)</div>
        <div class="font-medium text-emerald-900">${esc(d.normalized)}</div>
      </div></div>`;
    if (d.t5 !== undefined)
      html += `<div class="rounded-2xl p-5 bg-blue-50 border border-blue-200 mt-5">
        <div class="text-xs font-semibold uppercase tracking-wide text-brand mb-2">t5-small cleanup (illustrative)</div>
        <div class="text-ink/90">${esc(d.t5)}</div></div>`;
    out.innerHTML = html;
  } catch (e) { out.innerHTML = errorBox(e.message); }
});

/* ------------------------------------------------------------------ */
/* Init                                                                */
/* ------------------------------------------------------------------ */
showTab("pipeline");
loadCategories();
loadOverview();
loadPreview();
