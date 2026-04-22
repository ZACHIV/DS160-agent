const SERVER_BASE = "http://127.0.0.1:8765";

const manifestGrid = document.getElementById("manifest-grid");
const manualForm = document.getElementById("manual-form");
const submitStatus = document.getElementById("submit-status");
const jsonPreview = document.getElementById("json-preview");
const copyPromptButton = document.getElementById("copy-prompt");
const pasteResultButton = document.getElementById("paste-result");
const downloadButton = document.getElementById("download-json");
const copyButton = document.getElementById("copy-json");
const missingFields = document.getElementById("missing-fields");
const visionWarnings = document.getElementById("vision-warnings");
const documentReports = document.getElementById("document-reports");
const resultDialog = document.getElementById("result-dialog");
const resultInput = document.getElementById("result-input");
const applyResultButton = document.getElementById("apply-result");

const state = {
  manifest: [],
  latestJsonText: "",
  schema: null,
};


function normalizeValue(value) {
  return typeof value === "string" ? value.trim() : value;
}


function renderItems(element, items, emptyText, formatter) {
  if (!items.length) {
    element.className = "item-list empty";
    element.textContent = emptyText;
    return;
  }
  element.className = "item-list";
  element.innerHTML = items.map(formatter).join("");
}


function schemaProperties() {
  return state.schema?.properties || {};
}


function schemaRequiredFields() {
  return state.schema?.required || [];
}


function setFieldValue(name, value) {
  const field = manualForm.elements.namedItem(name);
  if (!field || value === undefined) {
    return;
  }
  if (field instanceof RadioNodeList) {
    return;
  }
  if (field.type === "checkbox") {
    field.checked = Boolean(value);
    return;
  }
  field.value = value ?? "";
}


function fieldHasValue(fieldName) {
  const field = manualForm.elements.namedItem(fieldName);
  if (!field || field instanceof RadioNodeList) {
    return false;
  }
  if (field.type === "checkbox") {
    return true;
  }
  return String(field.value || "").trim() !== "";
}


function setFieldHint(fieldName, message) {
  const hint = manualForm.querySelector(`[data-hint-for="${fieldName}"]`);
  if (hint) {
    hint.textContent = message || "";
  }
}


function clearFieldHighlight(fieldName) {
  const field = manualForm.elements.namedItem(fieldName);
  if (!field || field instanceof RadioNodeList) {
    return;
  }
  field.classList.remove("missing-field");
  const wrapper = field.closest("label");
  if (wrapper) {
    wrapper.classList.remove("is-missing");
  }
  setFieldHint(fieldName, "");
}


function clearMissingHighlights() {
  manualForm.querySelectorAll(".missing-field").forEach((field) => {
    field.classList.remove("missing-field");
  });
  manualForm.querySelectorAll(".is-missing").forEach((field) => {
    field.classList.remove("is-missing");
  });
  manualForm.querySelectorAll("[data-hint-for]").forEach((hint) => {
    hint.textContent = "";
  });
}


function highlightMissingFields(fields, scrollToFirst = true) {
  clearMissingHighlights();
  let firstTarget = null;
  for (const fieldName of fields || []) {
    const field = manualForm.elements.namedItem(fieldName);
    setFieldHint(fieldName, "这里还需要补充。");
    if (!field || field instanceof RadioNodeList) {
      continue;
    }
    field.classList.add("missing-field");
    const wrapper = field.closest("label");
    if (wrapper) {
      wrapper.classList.add("is-missing");
      if (!firstTarget) {
        firstTarget = wrapper;
      }
    } else if (!firstTarget) {
      firstTarget = field;
    }
  }
  if (firstTarget && scrollToFirst) {
    firstTarget.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}


function applyPayloadToManualForm(payload) {
  if (!payload) {
    return;
  }
  Object.entries(payload).forEach(([key, value]) => {
    setFieldValue(key, value);
  });
}


function manualFormFieldNames() {
  return Array.from(manualForm.elements)
    .map((field) => field.name)
    .filter(Boolean);
}


function schemaFieldNames() {
  return Object.keys(schemaProperties());
}


function validateManualPayload(payload) {
  const missing = schemaRequiredFields().filter((fieldName) => {
    if (!(fieldName in payload)) {
      return true;
    }
    const value = payload[fieldName];
    return value === null || value === "";
  });
  const extras = Object.keys(payload).filter((fieldName) => !schemaFieldNames().includes(fieldName));
  const invalids = {};
  for (const [fieldName, spec] of Object.entries(schemaProperties())) {
    const value = payload[fieldName];
    if (value === null || value === "") {
      continue;
    }
    if (spec.enum && !spec.enum.includes(value)) {
      invalids[fieldName] = "请按当前选项填写。";
      continue;
    }
    if (spec.format === "date" && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      invalids[fieldName] = "请使用年-月-日格式。";
      continue;
    }
    if (spec.format === "email" && value && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)) {
      invalids[fieldName] = "请输入有效邮箱。";
      continue;
    }
    if (typeof value === "string" && spec.minLength && value.trim().length < spec.minLength) {
      invalids[fieldName] = "内容太短，请补充完整。";
    }
  }
  return { missing, extras, invalids };
}


function refreshManualValidation(scrollToFirst = false) {
  const payload = manualPayload();
  const { missing, invalids } = validateManualPayload(payload);
  const invalidFieldNames = Object.keys(invalids);
  const problemFields = [...new Set([...missing, ...invalidFieldNames])];
  if (problemFields.length) {
    highlightMissingFields(problemFields, scrollToFirst);
    for (const [fieldName, message] of Object.entries(invalids)) {
      setFieldHint(fieldName, message);
    }
    renderItems(missingFields, problemFields, "没有缺失字段。", issueCard);
  } else {
    clearMissingHighlights();
    renderItems(missingFields, [], "没有缺失字段。", issueCard);
  }
  renderItems(visionWarnings, Object.values(invalids), "没有额外提醒。", warningCard);
  return { missing, invalids };
}


function partialPayloadFromReports(reports) {
  const merged = {};
  for (const report of reports || []) {
    Object.assign(merged, report.extracted_fields || {});
  }
  return merged;
}


function manifestCard(doc) {
  return `
    <article class="manifest-card" data-kind="${doc.kind}">
      <header>
        <div>
          <p class="eyebrow">${doc.label}</p>
          <h3>${doc.label}</h3>
        </div>
        <span class="token required">${doc.required ? "必传" : "选传"}</span>
      </header>
      <p>${doc.description}</p>
      <div class="manifest-meta">
        <span class="token neutral">图片上传</span>
      </div>
      <input type="file" accept="image/*" data-upload-kind="${doc.kind}" />
      <div class="manifest-note" data-note-kind="${doc.kind}">尚未选择文件。</div>
    </article>
  `;
}


async function loadManifest() {
  submitStatus.textContent = "页面已准备好。你可以上传材料，也可以直接手动填写。";
  const res = await fetch(`${SERVER_BASE}/vision-intake/manifest`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "无法读取图片整理清单");
  }
  state.manifest = data.documents || [];
  manifestGrid.innerHTML = state.manifest.map(manifestCard).join("");
  manifestGrid.querySelectorAll("[data-upload-kind]").forEach((input) => {
    input.addEventListener("change", () => {
      const note = manifestGrid.querySelector(`[data-note-kind="${input.dataset.uploadKind}"]`);
      note.textContent = input.files?.[0] ? `已选择：${input.files[0].name}` : "尚未选择文件。";
    });
  });
}


async function loadSchema() {
  const res = await fetch(`${SERVER_BASE}/intake-schema`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "无法读取资料定义");
  }
  state.schema = data.schema_document;
  const missingFormFields = schemaFieldNames().filter((fieldName) => !manualFormFieldNames().includes(fieldName));
  const extraFormFields = manualFormFieldNames().filter((fieldName) => !schemaFieldNames().includes(fieldName));
  if (missingFormFields.length || extraFormFields.length) {
    throw new Error("采集页字段与资料定义不一致，请检查表单配置");
  }
  const enumMismatchFields = Object.entries(schemaProperties())
    .filter(([, spec]) => Array.isArray(spec.enum))
    .filter(([fieldName, spec]) => {
      const field = manualForm.elements.namedItem(fieldName);
      if (!field || field.tagName !== "SELECT") {
        return true;
      }
      const optionValues = Array.from(field.options).map((option) => option.value);
      return JSON.stringify(optionValues) !== JSON.stringify(spec.enum);
    })
    .map(([fieldName]) => fieldName);
  if (enumMismatchFields.length) {
    throw new Error("表单选项与资料定义不一致，请检查页面配置");
  }
}


function toBase64DataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}


async function collectUploads() {
  const documents = [];
  for (const spec of state.manifest) {
    const input = manifestGrid.querySelector(`[data-upload-kind="${spec.kind}"]`);
    const file = input?.files?.[0];
    if (!file) {
      continue;
    }
    documents.push({
      kind: spec.kind,
      filename: file.name,
      media_type: file.type || "image/jpeg",
      base64_data: await toBase64DataUrl(file),
    });
  }
  return documents;
}


function issueCard(value) {
  return `<article class="item-card"><strong>${value}</strong></article>`;
}


function warningCard(value) {
  return `<article class="item-card"><strong>${value}</strong></article>`;
}


function reportCard(doc) {
  return `
    <article class="item-card">
      <strong>${doc.filename || "未上传文件"}</strong>
      <span>${doc.status === "processed" ? "已处理" : doc.status === "missing" ? "未上传" : "处理失败"}</span>
      <span>${(doc.warnings || []).join(" | ") || "已读取这份材料。"}</span>
    </article>
  `;
}


function renderExtractionResult(data) {
  const partialPayload = data.intake_document || {};
  applyPayloadToManualForm(partialPayload);
  if (data.missing_fields?.length) {
    highlightMissingFields(data.missing_fields || []);
  } else {
    clearMissingHighlights();
  }
  renderItems(missingFields, data.missing_fields || [], "没有缺失字段。", issueCard);
  renderItems(visionWarnings, data.warnings || [], "没有额外提醒。", warningCard);
  renderItems(documentReports, data.documents || [], "没有文档处理结果。", reportCard);

  if (data.intake_document) {
    applyPayloadToManualForm(data.intake_document);
    clearMissingHighlights();
    state.latestJsonText = JSON.stringify(data.intake_document, null, 2);
    jsonPreview.textContent = state.latestJsonText;
    downloadButton.disabled = false;
    copyButton.disabled = false;
    submitStatus.textContent = "资料整理完成，识别结果已经回填到手填表单。下载后到执行页导入即可。";
  } else {
    state.latestJsonText = "";
    jsonPreview.textContent = "材料已经读取，但信息还不完整。可以补传更清晰的图片，或者直接用下方手填内容补齐。";
    downloadButton.disabled = true;
    copyButton.disabled = true;
    submitStatus.textContent = "已把识别到的内容回填到手填表单，请补齐剩余信息。";
  }
}


async function copyPrompt() {
  copyPromptButton.disabled = true;
  copyPromptButton.textContent = "生成中…";
  try {
    const documents = await collectUploads();
    if (!documents.length) {
      throw new Error("至少需要上传一份图片材料");
    }
    const res = await fetch(`${SERVER_BASE}/vision-intake/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ documents }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "提示词生成失败");
    }
    await navigator.clipboard.writeText(data.prompt_text);
    submitStatus.textContent = "提示词已复制。下一步请去外部大模型上传同样的图片并运行。";
  } catch (error) {
    submitStatus.textContent = error.message || "提示词复制失败，请稍后再试。";
  } finally {
    copyPromptButton.disabled = false;
    copyPromptButton.textContent = "一键复制提示词";
  }
}


function openResultDialog() {
  resultInput.value = "";
  resultDialog.showModal();
}


async function applyModelResult() {
  try {
    const parsed = JSON.parse(resultInput.value);
    const res = await fetch(`${SERVER_BASE}/vision-intake/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ result: parsed }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "模型结果处理失败");
    }
    renderExtractionResult(data);
    resultDialog.close();
    submitStatus.textContent = data.intake_document
      ? "模型结果已应用，资料可以直接导出。"
      : "模型结果已应用，但还有缺失或格式问题，请继续补齐。";
  } catch (error) {
    submitStatus.textContent = error.message || "无法应用模型结果。";
  }
}


function manualPayload() {
  const data = new FormData(manualForm);
  return {
    surname: normalizeValue(data.get("surname")),
    given_names: normalizeValue(data.get("given_names")),
    native_full_name: normalizeValue(data.get("native_full_name")) || null,
    sex: data.get("sex"),
    marital_status: data.get("marital_status"),
    date_of_birth: data.get("date_of_birth"),
    birth_city: normalizeValue(data.get("birth_city")),
    passport_number: normalizeValue(data.get("passport_number")),
    passport_issue_date: data.get("passport_issue_date"),
    passport_expiration_date: data.get("passport_expiration_date"),
    trip_purpose: data.get("trip_purpose"),
    intended_arrival_date: data.get("intended_arrival_date"),
    intended_length_of_stay_value: normalizeValue(data.get("intended_length_of_stay_value")),
    intended_length_of_stay_unit: data.get("intended_length_of_stay_unit"),
    payer_name: normalizeValue(data.get("payer_name")),
    us_contact_name: normalizeValue(data.get("us_contact_name")),
    us_contact_organization: normalizeValue(data.get("us_contact_organization")) || null,
    us_contact_phone: normalizeValue(data.get("us_contact_phone")),
    us_contact_address_line1: normalizeValue(data.get("us_contact_address_line1")),
    us_contact_city: normalizeValue(data.get("us_contact_city")),
    us_contact_state: normalizeValue(data.get("us_contact_state")),
    us_contact_postal_code: normalizeValue(data.get("us_contact_postal_code")),
    us_contact_email: normalizeValue(data.get("us_contact_email")) || null,
    primary_occupation: data.get("primary_occupation"),
    current_employer_name: normalizeValue(data.get("current_employer_name")),
    current_employer_address: normalizeValue(data.get("current_employer_address")),
    father_full_name: normalizeValue(data.get("father_full_name")),
    mother_full_name: normalizeValue(data.get("mother_full_name")),
    spouse_full_name: normalizeValue(data.get("spouse_full_name")) || null,
    communicable_disease: data.get("communicable_disease") === "on",
    arrest_history: data.get("arrest_history") === "on",
  };
}


function renderManualResult(payload) {
  clearMissingHighlights();
  state.latestJsonText = JSON.stringify(payload, null, 2);
  jsonPreview.textContent = state.latestJsonText;
  renderItems(missingFields, [], "手填方式已补齐当前页面内容。", issueCard);
  renderItems(visionWarnings, [], "没有额外提醒。", warningCard);
  renderItems(documentReports, [], "这次使用的是手动填写。", reportCard);
  downloadButton.disabled = false;
  copyButton.disabled = false;
  submitStatus.textContent = "手动整理完成。下载后到执行页导入即可。";
}


function downloadJson() {
  if (!state.latestJsonText) {
    return;
  }
  const blob = new Blob([state.latestJsonText], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "intake-v1.json";
  link.click();
  URL.revokeObjectURL(url);
}


async function copyJson() {
  if (!state.latestJsonText) {
    return;
  }
  try {
    await navigator.clipboard.writeText(state.latestJsonText);
    submitStatus.textContent = "已复制资料内容。下一步去执行页导入即可。";
  } catch {
    submitStatus.textContent = "复制失败，请直接下载资料文件。";
  }
}


copyPromptButton.addEventListener("click", copyPrompt);
pasteResultButton.addEventListener("click", openResultDialog);
applyResultButton.addEventListener("click", applyModelResult);
manualForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const payload = manualPayload();
  const { missing, extras, invalids } = validateManualPayload(payload);
  if (extras.length) {
    submitStatus.textContent = "页面字段配置有误，请刷新页面后重试。";
    return;
  }
  if (missing.length || Object.keys(invalids).length) {
    refreshManualValidation(true);
    submitStatus.textContent = "还有未填写或格式不对的信息，请先补齐高亮位置。";
    return;
  }
  renderManualResult(payload);
});
Array.from(manualForm.elements).forEach((field) => {
  if (!field.name) {
    return;
  }
  const eventName = field.type === "checkbox" || field.tagName === "SELECT" ? "change" : "input";
  field.addEventListener(eventName, () => {
    if (fieldHasValue(field.name)) {
      clearFieldHighlight(field.name);
    }
    refreshManualValidation(false);
  });
});
downloadButton.addEventListener("click", downloadJson);
copyButton.addEventListener("click", copyJson);
downloadButton.disabled = true;
copyButton.disabled = true;
Promise.all([loadSchema(), loadManifest()]).catch((error) => {
  submitStatus.textContent = error.message || "页面初始化失败，请确认服务已启动。";
});
