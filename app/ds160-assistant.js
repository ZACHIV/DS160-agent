const SERVER_BASE = "http://127.0.0.1:8765";

const state = {
  bundle: null,
  currentPageId: null,
  completed: {},
  serverConnected: false,
  dossierLoaded: false,
  logs: [],
};

const pageNav = document.getElementById("page-nav");
const summary = document.getElementById("summary");
const pageTitle = document.getElementById("page-title");
const metricFill = document.getElementById("metric-fill");
const metricReview = document.getElementById("metric-review");
const metricBlocked = document.getElementById("metric-blocked");
const serverStatus = document.getElementById("server-status");
const fillResult = document.getElementById("fill-result");
const fillButton = document.getElementById("fill-page");
const intakeFile = document.getElementById("intake-file");
const loadIntakeButton = document.getElementById("load-intake");
const intakeDocStatus = document.getElementById("intake-doc-status");


function currentBundle() {
  return state.bundle;
}


function getPage(pageId) {
  return currentBundle()?.pages.find((page) => page.page_id === pageId);
}


function pushLog(level, title, detail) {
  const timestamp = new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  state.logs.unshift({ level, title, detail, timestamp });
  state.logs = state.logs.slice(0, 12);
  renderLogs();
}


function renderLogs() {
  fillResult.innerHTML = state.logs.length
    ? state.logs
        .map(
          (item) => `
            <article class="terminal-line ${item.level}">
              <header>
                <strong>${item.title}</strong>
                <span>${item.timestamp}</span>
              </header>
              <div class="terminal-detail">${item.detail || "无附加信息"}</div>
            </article>
          `
        )
        .join("")
    : `<article class="terminal-line idle"><header><strong>空</strong><span>--:--:--</span></header><div class="terminal-detail">--</div></article>`;
}


function renderEmptyState() {
  summary.innerHTML = `
    <div class="summary-card">
      <span class="eyebrow">状态</span>
      <strong>未导入</strong>
    </div>
  `;
  pageNav.innerHTML = `
    <section class="flow-section">
      <div class="flow-section-title">页面</div>
      <div class="summary-card">--</div>
    </section>
  `;
  pageTitle.textContent = "--";
  metricFill.textContent = "0";
  metricReview.textContent = "0";
  metricBlocked.textContent = "0";
  renderLogs();
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


function renderMetrics(page) {
  metricFill.textContent = page.autofill_count;
  metricReview.textContent = page.review_count;
  metricBlocked.textContent = page.blocked_count;
}


function render() {
  if (!currentBundle()) {
    renderEmptyState();
    return;
  }
  const page = getPage(state.currentPageId);
  if (!page) return;
  pageTitle.textContent = `${page.label}${state.completed[page.page_id] ? " · 已完成预填" : ""}`;
  renderSummary();
  renderNav();
  renderMetrics(page);
  renderLogs();
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
  pushLog("info", "Bundle", `${data.bundle.pages.length} pages`);
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
      intakeDocStatus.textContent = "已导入";
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
    pushLog("error", "文件", "未选择");
    return;
  }
  loadIntakeButton.disabled = true;
  loadIntakeButton.textContent = "导入中…";
  intakeDocStatus.textContent = "导入中";
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
    intakeDocStatus.textContent = "已导入";
    await fetchBundle();
    pushLog("success", "导入", file.name);
  } catch (error) {
    pushLog("error", "导入失败", error.message || "失败");
    intakeDocStatus.textContent = "导入失败";
  } finally {
    loadIntakeButton.disabled = false;
    loadIntakeButton.textContent = "导入 JSON";
    checkServerStatus();
  }
}


loadIntakeButton.addEventListener("click", loadIntakeDocument);

fillButton.addEventListener("click", async () => {
  if (!currentBundle()) {
    pushLog("error", "填入", "未导入");
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
      pushLog(
        "success",
        `填入成功 (${data.page_key})`,
        `已填: ${data.filled.join(", ") || "无"} | 缺失: ${data.missing.join(", ") || "无"}`
      );
    } else {
      const msg = data.detail || data.message || "填入失败";
      pushLog("error", "填入失败", msg);
    }
  } catch {
    pushLog("error", "网络错误", "服务未启动");
  } finally {
    fillButton.disabled = false;
    fillButton.textContent = "一键填入";
    checkServerStatus();
  }
});


checkServerStatus();
setInterval(checkServerStatus, 5000);
render();
