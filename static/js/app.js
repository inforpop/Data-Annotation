/* Dashboard de Data Annotation — Clássica x Quântica */
(() => {
  const COLORS = {
    classical: { positivo: "#1b8a4c", neutro: "#8a94a6", negativo: "#c0392b" },
    quantum: { "base": "#2a6fdb", "superposição": "#e07b39", "emaranhado": "#6c3fc9" },
  };
  const state = {
    active: "classical",
    current: { classical: null, quantum: null },
    startedAt: { classical: 0, quantum: 0 },
    charts: { classical: {}, quantum: {} },
    busy: false,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const panel = (d) => $(`#panel-${d}`);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const annotatorInput = $("#annotator");
  try { annotatorInput.value = localStorage.getItem("annotator") || annotatorInput.value; } catch (e) { /* sem storage */ }
  const annotator = () => annotatorInput.value.trim() || "anônimo";

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return res.json();
  }

  // ---------------------------------------------------------- item atual
  async function loadNext(domain) {
    const p = panel(domain);
    const data = await api(`/api/${domain}/next?annotator=${encodeURIComponent(annotator())}`);
    const body = $(".item-body", p);
    const buttons = $$(".label-btn", p);
    buttons.forEach((b) => b.classList.remove("suggested"));

    if (data.finished) {
      state.current[domain] = null;
      body.innerHTML = `<div class="done">🎉 Todos os ${data.total} itens foram anotados por <b>${esc(annotator())}</b>.<br>Exporte os resultados ou clique em “Recomeçar”.</div>`;
      $(".suggestion", p).textContent = "";
      $(".position", p).textContent = `${data.total}/${data.total}`;
      buttons.forEach((b) => (b.disabled = true));
      if (domain === "quantum") drawProbs(null);
      return;
    }

    const item = data.item;
    state.current[domain] = item;
    state.startedAt[domain] = performance.now();
    buttons.forEach((b) => (b.disabled = false));
    $(".position", p).textContent = `Item ${data.position} de ${data.total} · ${item.id}`;

    if (domain === "classical") {
      body.innerHTML = `<p>“${esc(item.text)}”</p>`;
    } else {
      body.innerHTML = `<pre>${esc(item.diagram)}</pre><div class="ket">|ψ⟩ = ${esc(item.ket)}</div>`;
      drawProbs(item.probs);
    }
    $(".suggestion", p).innerHTML = `🤖 Pré-anotação do modelo: <b>${esc(item.suggestion)}</b> <span class="hint">(Enter aceita)</span>`;
    const sug = buttons.find((b) => b.dataset.label === item.suggestion);
    if (sug) sug.classList.add("suggested");
  }

  async function annotate(domain, label) {
    const item = state.current[domain];
    if (!item || state.busy) return;
    state.busy = true;
    const seconds = (performance.now() - state.startedAt[domain]) / 1000;
    const fb = $(".feedback", panel(domain));
    try {
      const res = await api(`/api/${domain}/annotate`, {
        method: "POST",
        body: JSON.stringify({ item_id: item.id, label, annotator: annotator(), seconds }),
      });
      const f = res.feedback;
      let msg = f.correct ? `✅ Correto! Gabarito: ${f.gold}` : `❌ Gabarito: ${f.gold} (você marcou ${label})`;
      if (f.concurrence !== undefined) msg += ` · concorrência C = ${f.concurrence}`;
      fb.textContent = msg;
      fb.className = `feedback ${f.correct ? "ok" : "bad"}`;
      await Promise.all([loadNext(domain), loadStats(domain)]);
    } catch (e) {
      fb.textContent = `Erro ao salvar: ${e.message}`;
      fb.className = "feedback bad";
    } finally {
      state.busy = false;
    }
  }

  // ------------------------------------------------------------ métricas
  const fmt = {
    progress_pct: (v) => `${v}%`,
    accuracy_human_vs_gold: (v) => (v == null ? "—" : `${v}%`),
    accuracy_model_vs_gold: (v) => (v == null ? "—" : `${v}%`),
    kappa_human_vs_model: (v) => (v == null ? "—" : v.toFixed(2)),
    corrections: (v) => v,
    avg_seconds: (v) => (v == null ? "—" : `${v}s`),
  };

  async function loadStats(domain) {
    const s = await api(`/api/${domain}/stats?annotator=${encodeURIComponent(annotator())}`);
    const p = panel(domain);
    $$("[data-kpi]", p).forEach((el) => {
      const k = el.dataset.kpi;
      el.textContent = fmt[k] ? fmt[k](s[k]) : s[k];
    });
    drawDistribution(domain, s);
    drawConfusion(domain, s);
  }

  // Fallback simples (barras em HTML) caso o CDN do Chart.js não carregue
  function htmlBars(canvas, labels, values, colors, max) {
    const box = canvas.parentElement;
    const top = max || Math.max(1, ...values);
    box.innerHTML = '<div class="bars">' + labels.map((l, i) =>
      `<div class="bar-row"><span>${esc(l)}</span><div class="bar-track"><div class="bar-fill" style="width:${(100 * values[i]) / top}%;background:${colors[i]}"></div></div><b>${max ? values[i].toFixed(2) : values[i]}</b></div>`
    ).join("") + "</div>";
    box.appendChild(canvas);
    canvas.style.display = "none";
  }

  function drawDistribution(domain, s) {
    const ctx = $(".chart-dist", panel(domain));
    const labels = s.labels;
    const values = labels.map((l) => s.label_distribution[l]);
    const colors = labels.map((l) => COLORS[domain][l]);
    const ch = state.charts[domain].dist;
    if (ch) {
      ch.data.datasets[0].data = values;
      ch.update();
      return;
    }
    if (!window.Chart) return htmlBars(ctx, labels, values, colors);
    state.charts[domain].dist = new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ label: "Anotações", data: values, backgroundColor: colors, borderRadius: 6 }] },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } },
      },
    });
  }

  function drawProbs(probs) {
    const ctx = $(".chart-probs", panel("quantum"));
    const labels = ["|00⟩", "|01⟩", "|10⟩", "|11⟩"];
    const values = probs ? ["00", "01", "10", "11"].map((k) => probs[k]) : [0, 0, 0, 0];
    if (!window.Chart) return htmlBars(ctx, labels, values, labels.map(() => "#6c3fc9"), 1);
    const ch = state.charts.quantum.probs;
    if (ch) {
      ch.data.datasets[0].data = values;
      ch.update();
      return;
    }
    state.charts.quantum.probs = new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ label: "P(medição)", data: values, backgroundColor: "#6c3fc9", borderRadius: 6 }] },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 1 }, x: { grid: { display: false } } },
      },
    });
  }

  function drawConfusion(domain, s) {
    const box = $(".confusion", panel(domain));
    const L = s.labels;
    if (!s.annotations) {
      box.innerHTML = `<p class="hint">Ainda sem anotações.</p>`;
      return;
    }
    let html = "<table><tr><th>gabarito ↓ / humano →</th>" + L.map((l) => `<th>${esc(l)}</th>`).join("") + "</tr>";
    s.confusion_human_vs_gold.forEach((row, i) => {
      html += `<tr><th>${esc(L[i])}</th>` + row.map((v, j) => `<td class="${i === j ? "diag" : ""}">${v}</td>`).join("") + "</tr>";
    });
    box.innerHTML = html + "</table>";
  }

  // --------------------------------------------------------------- eventos
  $$(".tab").forEach((t) =>
    t.addEventListener("click", () => {
      $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
      $$(".panel").forEach((x) => x.classList.toggle("active", x.id === `panel-${t.dataset.tab}`));
      state.active = t.dataset.tab;
    })
  );

  $$(".panel").forEach((p) => {
    const domain = p.dataset.domain;
    $$(".label-btn", p).forEach((b) => b.addEventListener("click", () => annotate(domain, b.dataset.label)));
    $(".reset", p).addEventListener("click", async () => {
      await api(`/api/${domain}/reset`, { method: "POST", body: JSON.stringify({ annotator: annotator() }) });
      $(".feedback", p).textContent = "";
      await Promise.all([loadNext(domain), loadStats(domain)]);
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.target === annotatorInput) return;
    const d = state.active;
    const labels = window.LABELS[d];
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= labels.length) annotate(d, labels[n - 1]);
    else if (e.key === "Enter" && state.current[d]) annotate(d, state.current[d].suggestion);
  });

  annotatorInput.addEventListener("change", () => {
    try { localStorage.setItem("annotator", annotator()); } catch (e) { /* ok */ }
    refreshAll();
  });

  function refreshAll() {
    ["classical", "quantum"].forEach((d) => {
      loadNext(d);
      loadStats(d);
    });
  }
  refreshAll();
})();
