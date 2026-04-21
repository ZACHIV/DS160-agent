const bundle = window.DS160_DRAFT_BUNDLE;
const state = {
  currentPageId: bundle.pages[0]?.page_id || null,
  completed: {},
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
const applyButton = document.getElementById("apply-page");
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

applyButton.addEventListener("click", () => {
  state.completed[state.currentPageId] = true;
  render();
});

resetButton.addEventListener("click", () => {
  delete state.completed[state.currentPageId];
  render();
});

render();
