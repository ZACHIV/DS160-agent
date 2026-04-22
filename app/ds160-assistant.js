const SERVER_BASE = "http://127.0.0.1:8765";

const bundle = window.DS160_DRAFT_BUNDLE;
const state = {
  currentPageId: bundle.pages[0]?.page_id || null,
  completed: {},
  serverConnected: false,
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

function getPage(pageId) {
  return bundle.pages.find((page) => page.page_id === pageId);
}

function renderSummary() {
  const { status_counts: counts, page_count: pages, hard_stops: hardStops } = bundle.summary;
  summary.innerHTML = `
    <div class="summary-card">
      <span class="eyebrow">Case</span>
      <strong>${bundle.case_id}</strong>
    </div>
    <div class="summary-card">
      <span class="eyebrow">Ready / Review / Blocked</span>
      <strong>${counts.ready} / ${counts.needs_review} / ${counts.blocked}</strong>
    </div>
    <div class="summary-card">
      <span class="eyebrow">Flow Pages / Hard Stops</span>
      <strong>${pages} / ${hardStops.length}</strong>
    </div>
  `;
}

function renderTopSteps() {
  topSteps.innerHTML = bundle.top_steps
    .map((step, index) => {
      const active = index === 0 ? "active" : "";
      return `<div class="top-step ${active}">${step.label}</div>`;
    })
    .join("");
}

function renderNav() {
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
                <span class="token fill">AUTOFILL</span>
              </header>
              <div class="field-value">${item.proposed_value ?? "<empty>"}</div>
              <div class="field-meta">Evidence: ${(item.evidence_refs || []).join(", ") || "n/a"}</div>
            </article>
          `
        )
        .join("")
    : `<article class="field-card"><header><strong>${page.label}</strong><span class="token planned">${page.status === "planned" ? "PENDING" : "REFERENCE"}</span></header><div class="field-meta">当前页还没有本地草稿字段，但导航和状态已经对齐正式 DS-160 流程。</div></article>`;
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
                  ${item.kind === "review" ? "REVIEW" : "BLOCKED"}
                </span>
              </header>
              <div class="review-note">${item.notes || "No note."}</div>
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

// ---------------------------------------------------------------------------
// Server connection
// ---------------------------------------------------------------------------

function showFillResult(ok, message, detail) {
  fillResult.style.display = "block";
  fillResult.className = "fill-result " + (ok ? "fill-ok" : "fill-err");
  fillResult.innerHTML = `<strong>${message}</strong>${detail ? `<div class="fill-detail">${detail}</div>` : ""}`;
  clearTimeout(fillResult._timer);
  if (ok) {
    fillResult._timer = setTimeout(() => { fillResult.style.display = "none"; }, 5000);
  }
}

async function checkServerStatus() {
  try {
    const res = await fetch(`${SERVER_BASE}/status`, { signal: AbortSignal.timeout(2000) });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    state.serverConnected = data.connected;
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
  } catch {
    state.serverConnected = false;
    serverStatus.textContent = "服务未启动";
    serverStatus.style.color = "var(--c-err, #eb5757)";
  }
}

// ---------------------------------------------------------------------------
// Fill / Save actions
// ---------------------------------------------------------------------------

fillButton.addEventListener("click", async () => {
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
  } catch (err) {
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
  } catch (err) {
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

// Poll server status every 5 seconds
checkServerStatus();
setInterval(checkServerStatus, 5000);

render();
