const SERVER_BASE = "http://127.0.0.1:8765";

const state = {
  bundle: null,
  currentPageId: null,
  completed: {},
  serverConnected: false,
  dossierLoaded: false,
};

const topSteps = document.getElementById("top-steps");
const pageNav = document.getElementById("page-nav");
const summary = document.getElementById("summary");
const pageTitle = document.getElementById("page-title");
const fieldList = document.getElementById("field-list");
const reviewList = document.getElementById("review-list");
const notesList = document.getElementById("notes-list");
const metricFill = document.getElementById("metric-fill");
const metricReview = document.getElementById("metric-review");
const metricBlocked = document.getElementById("metric-blocked");
const serverStatus = document.getElementById("server-status");
const fillResult = document.getElementById("fill-result");
const fillButton = document.getElementById("fill-page");
const saveButton = document.getElementById("save-page");
const resetButton = document.getElementById("reset-page");
const intakeFile = document.getElementById("intake-file");
const loadIntakeButton = document.getElementById("load-intake");
const intakeDocStatus = document.getElementById("intake-doc-status");


function currentBundle() {
  return state.bundle;
}


function getPage(pageId) {
  return currentBundle()?.pages.find((page) => page.page_id === pageId);
}


function showFillResult(ok, message, detail) {
  fillResult.style.display = "block";
  fillResult.className = "fill-result " + (ok ? "fill-ok" : "fill-err");
  fillResult.innerHTML = `<strong>${message}</strong>${detail ? `<div class="fill-detail">${detail}</div>` : ""}`;
  clearTimeout(fillResult._timer);
  if (ok) {
    fillResult._timer = setTimeout(() => {
      fillResult.style.display = "none";
    }, 5000);
  }
}


function renderEmptyState() {
  summary.innerHTML = `
    <div class="summary-card">
      <span class="eyebrow">状态</span>
      <strong>等待导入资料文件</strong>
    </div>
  `;
  pageNav.innerHTML = `
    <section class="flow-section">
      <div class="flow-section-title">先导入资料</div>
      <div class="summary-card">导入采集页生成的 full dossier 文件后，系统才会生成当前申请的页面清单。</div>
    </section>
  `;
  pageTitle.textContent = "等待资料";
  metricFill.textContent = "0";
  metricReview.textContent = "0";
  metricBlocked.textContent = "0";
  fieldList.innerHTML = `<article class="field-card"><header><strong>执行器未激活</strong><span class="token planned">等待导入</span></header><div class="field-meta">这个页面只负责执行填表，不能直接采集申请资料。</div></article>`;
  reviewList.innerHTML = `<article class="review-card"><strong>导入 dossier 文件后，这里会显示需要确认或补充的内容。</strong></article>`;
  notesList.innerHTML = `<article class="review-card"><strong>建议先在采集页整理资料，再回到这里导入。</strong></article>`;
}


function renderSummary() {
  const bundle = currentBundle();
  const { status_counts: counts, page_count: pages, hard_stops: hardStops } = bundle.summary;
  summary.innerHTML = `
    <div class="summary-card">
      <span class="eyebrow">申请</span>
      <strong>${bundle.case_id}</strong>
    </div>
    <div class="summary-card">
      <span class="eyebrow">可填 / 待确认 / 缺失</span>
      <strong>${counts.ready} / ${counts.needs_review} / ${counts.blocked}</strong>
    </div>
    <div class="summary-card">
      <span class="eyebrow">页面数 / 停止点</span>
      <strong>${pages} / ${hardStops.length}</strong>
    </div>
  `;
}


function renderTopSteps() {
  const bundle = currentBundle();
  topSteps.innerHTML = bundle.top_steps
    .map((step, index) => {
      const active = index === 0 ? "active" : "";
      return `<div class="top-step ${active}">${step.label}</div>`;
    })
    .join("");
}


function renderNav() {
  const bundle = currentBundle();
  pageNav.innerHTML = bundle.navigation
    .map((section) => {
      const buttons = section.pages
        .map((page) => {
          const active = page.page_id === state.currentPageId ? "active" : "";
          const done = state.completed[page.page_id] ? "done" : "";
          const planned = page.status === "planned" ? "planned" : "";
          const reference = page.status === "reference" ? "reference" : "";
          return `
            <button class="page-button ${active} ${done} ${planned} ${reference}" data-page-id="${page.page_id}">
              <div>${page.label}</div>
              <div class="page-meta">${page.status === "implemented" ? "已建模" : page.status === "reference" ? "参考页" : "待补充"}</div>
            </button>
          `;
        })
        .join("");
      return `
        <section class="flow-section">
          <div class="flow-section-title">${section.label}</div>
          ${buttons}
        </section>
      `;
    })
    .join("");

  pageNav.querySelectorAll("[data-page-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentPageId = button.dataset.pageId;
      render();
    });
  });
}


function renderFields(page) {
  metricFill.textContent = page.autofill_count;
  metricReview.textContent = page.review_count;
  metricBlocked.textContent = page.blocked_count;

  fieldList.innerHTML = page.fill.length
    ? page.fill
        .map(
          (item) => `
            <article class="field-card">
              <header>
                <strong>${item.field_id}</strong>
                <span class="token fill">自动填入</span>
              </header>
              <div class="field-value">${item.proposed_value ?? "<empty>"}</div>
              <div class="field-meta">来源：${(item.evidence_refs || []).join(", ") || "未标注"}</div>
            </article>
          `
        )
        .join("")
    : `<article class="field-card"><header><strong>${page.label}</strong><span class="token planned">${page.status === "planned" ? "待补充" : "参考页"}</span></header><div class="field-meta">当前页暂时没有可直接填入的资料。</div></article>`;
}


function renderReview(page) {
  const items = [
    ...page.review.map((item) => ({ ...item, kind: "review" })),
    ...page.blocked.map((item) => ({ ...item, kind: "blocked" })),
  ];

  reviewList.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <article class="review-card">
              <header>
                <strong>${item.field_id}</strong>
                <span class="token ${item.kind === "review" ? "review" : "blocked"}">
                  ${item.kind === "review" ? "待确认" : "缺失"}
                </span>
              </header>
              <div class="review-note">${item.notes || "需要人工处理。"}</div>
            </article>
          `
        )
        .join("")
    : `<article class="review-card"><strong>当前页没有 review / blocked 项。</strong></article>`;
}


function renderNotes(page) {
  const notes = page.notes || [];
  notesList.innerHTML = notes.length
    ? notes
        .map(
          (note) => `
            <article class="review-card">
              <header>
                <strong>${page.label}</strong>
                <span class="token planned">${page.status.toUpperCase()}</span>
              </header>
              <div class="review-note">${note}</div>
            </article>
          `
        )
        .join("")
    : `<article class="review-card"><strong>当前页没有额外说明。</strong></article>`;
}


function render() {
  if (!currentBundle()) {
    renderEmptyState();
    return;
  }
  const page = getPage(state.currentPageId);
  if (!page) return;
  pageTitle.textContent = `${page.label}${state.completed[page.page_id] ? " · 已完成预填" : ""}`;
  renderTopSteps();
  renderSummary();
  renderNav();
  renderFields(page);
  renderReview(page);
  renderNotes(page);
}


async function fetchBundle() {
  const res = await fetch(`${SERVER_BASE}/draft-bundle`, { signal: AbortSignal.timeout(3000) });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "无法构建 draft bundle");
  }
  state.bundle = data.bundle;
  state.currentPageId = data.bundle.pages[0]?.page_id || null;
  state.completed = {};
  render();
}


async function checkServerStatus() {
  try {
    const res = await fetch(`${SERVER_BASE}/status`, { signal: AbortSignal.timeout(2000) });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    state.serverConnected = data.connected;
    state.dossierLoaded = Boolean(data.dossier_document_loaded);
    if (!data.connected) {
      serverStatus.textContent = "未连接浏览器";
      serverStatus.style.color = "var(--c-warn, #f5a623)";
    } else if (!data.ceac_tab_found) {
      serverStatus.textContent = "已连接 (无DS-160标签)";
      serverStatus.style.color = "var(--c-warn, #f5a623)";
    } else {
      serverStatus.textContent = "已连接 ✓";
      serverStatus.style.color = "var(--c-ok, #6fcf97)";
    }
    if (data.dossier_document_loaded) {
      intakeDocStatus.textContent = "资料文件已载入。";
      if (!currentBundle()) {
        await fetchBundle();
      }
    }
  } catch {
    state.serverConnected = false;
    serverStatus.textContent = "服务未启动";
    serverStatus.style.color = "var(--c-err, #eb5757)";
  }
}


async function loadIntakeDocument() {
  const file = intakeFile.files?.[0];
  if (!file) {
    showFillResult(false, "缺少文件", "请选择一份 full dossier JSON 文档。");
    return;
  }
  loadIntakeButton.disabled = true;
  loadIntakeButton.textContent = "导入中…";
  intakeDocStatus.textContent = `正在载入 ${file.name} …`;
  try {
    const text = await file.text();
    const payload = JSON.parse(text);
    const res = await fetch(`${SERVER_BASE}/dossier-document`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "导入资料文档失败");
    }
      intakeDocStatus.textContent = `${file.name} 已导入。`;
    await fetchBundle();
    showFillResult(true, "导入成功", "已根据资料 JSON 构建执行 bundle。");
  } catch (error) {
    showFillResult(false, "导入失败", error.message || "请检查 JSON 格式");
    intakeDocStatus.textContent = "导入失败，请检查 schema 和服务状态。";
  } finally {
    loadIntakeButton.disabled = false;
    loadIntakeButton.textContent = "导入资料 JSON";
    checkServerStatus();
  }
}


loadIntakeButton.addEventListener("click", loadIntakeDocument);

fillButton.addEventListener("click", async () => {
  if (!currentBundle()) {
    showFillResult(false, "尚未导入资料", "请先导入一份资料 JSON 文件。");
    return;
  }
  fillButton.disabled = true;
  fillButton.textContent = "填入中…";
  try {
    const res = await fetch(`${SERVER_BASE}/fill-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_id: state.currentPageId }),
    });
    const data = await res.json();
    if (res.ok && data.ok) {
      state.completed[state.currentPageId] = true;
      render();
      showFillResult(true, `填入成功 (${data.page_key})`, `已填: ${data.filled.join(", ") || "无"} | 缺失: ${data.missing.join(", ") || "无"}`);
    } else {
      const msg = data.detail || data.message || "填入失败";
      showFillResult(false, "填入失败", msg);
    }
  } catch {
    showFillResult(false, "网络错误", "请确认本地服务已启动：python -m visa_agent.server");
  } finally {
    fillButton.disabled = false;
    fillButton.textContent = "一键填入当前页";
    checkServerStatus();
  }
});


saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  saveButton.textContent = "保存中…";
  try {
    const res = await fetch(`${SERVER_BASE}/save-page`, { method: "POST" });
    const data = await res.json();
    showFillResult(data.ok, data.ok ? "保存成功" : "保存按钮未找到", JSON.stringify(data.payload || {}));
  } catch {
    showFillResult(false, "网络错误", "请确认本地服务已启动");
  } finally {
    saveButton.disabled = false;
    saveButton.textContent = "保存当前页";
  }
});


resetButton.addEventListener("click", () => {
  delete state.completed[state.currentPageId];
  fillResult.style.display = "none";
  render();
});


checkServerStatus();
setInterval(checkServerStatus, 5000);
render();
