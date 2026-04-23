const SERVER_BASE = "http://127.0.0.1:8765";
const OFFLINE_MODE_MESSAGE = "已切换到离线模式：本地服务未连接。你仍然可以上传图片、复制提示词、粘贴模型结果和手动填写。";

const FALLBACK_VISION_MANIFEST = [
  { kind: "passport_bio", label: "护照资料页", description: "上传中国护照个人信息页清晰照片或扫描件。", required: true },
  { kind: "trip_proof", label: "赴美行程或邀请材料", description: "上传行程单、邀请函或其他行程说明材料。", required: true },
  { kind: "us_contact_proof", label: "美国联系人材料", description: "上传联系人信息、邀请函页或名片。", required: true },
  { kind: "employment_proof", label: "工作或学校材料", description: "上传在职证明、学校证明或工作说明。", required: true },
  { kind: "family_info_sheet", label: "家庭信息材料", description: "上传父母、配偶或美国亲属信息材料。", required: true },
  { kind: "security_questionnaire", label: "安全背景问卷", description: "上传安全问题确认材料。", required: true },
];

const FALLBACK_SCHEMA_DOCUMENT = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "https://local.ds160/dossier.schema.json",
  title: "China B1/B2 Applicant Dossier",
  required: ["case_id", "identity", "travel_plan", "employment_education", "family_contacts", "security_background", "evidence_catalog"],
};

const REQUIRED_PATHS = [
  "case_id",
  "identity.surname",
  "identity.given_names",
  "identity.sex",
  "identity.marital_status",
  "identity.date_of_birth",
  "identity.birth_city",
  "identity.birth_country",
  "identity.nationality",
  "identity.passport_number",
  "identity.passport_issuance_country",
  "identity.passport_issue_date",
  "identity.passport_expiration_date",
  "identity.source_ids",
  "travel_plan.visa_class",
  "travel_plan.source_ids",
  "employment_education.source_ids",
  "family_contacts.source_ids",
  "security_background.yes_no_answers.communicable_disease",
  "security_background.yes_no_answers.arrest_history",
  "security_background.source_ids",
  "evidence_catalog",
];

const DATE_PATHS = [
  "identity.date_of_birth",
  "identity.passport_issue_date",
  "identity.passport_expiration_date",
  "travel_plan.intended_arrival_date",
];

const EMAIL_PATHS = ["travel_plan.us_contact_email"];
const ENUMS = {
  "identity.sex": ["MALE", "FEMALE"],
  "identity.marital_status": ["SINGLE", "MARRIED", "DIVORCED", "WIDOWED"],
  "travel_plan.intended_length_of_stay_unit": ["DAYS", "WEEKS", "MONTHS"],
  "employment_education.primary_occupation": ["BUSINESSPERSON", "STUDENT", "OTHER"],
};
const JSON_TEXTAREA_PATHS = ["security_background.explanations", "evidence_catalog"];
const ARRAY_INPUT_PATHS = [
  "identity.source_ids",
  "travel_plan.source_ids",
  "employment_education.source_ids",
  "family_contacts.source_ids",
  "security_background.source_ids",
];
const BOOLEAN_PATHS = [
  "security_background.yes_no_answers.communicable_disease",
  "security_background.yes_no_answers.arrest_history",
];

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
  offlineMode: false,
};


function activateOfflineMode() {
  state.offlineMode = true;
  submitStatus.textContent = OFFLINE_MODE_MESSAGE;
}


function normalizeValue(value) {
  return typeof value === "string" ? value.trim() : value;
}


function normalizedOptional(value) {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value).trim();
  return text ? text : null;
}


function parseJsonText(value, fallback) {
  const text = String(value || "").trim();
  if (!text) {
    return fallback;
  }
  return JSON.parse(text);
}


function parseStringArray(value) {
  const text = String(value || "").trim();
  if (!text) {
    return [];
  }
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}


function setNestedValue(target, path, value) {
  const parts = path.split(".");
  let cursor = target;
  for (let index = 0; index < parts.length - 1; index += 1) {
    const key = parts[index];
    if (!cursor[key] || typeof cursor[key] !== "object" || Array.isArray(cursor[key])) {
      cursor[key] = {};
    }
    cursor = cursor[key];
  }
  cursor[parts[parts.length - 1]] = value;
}


function getNestedValue(target, path) {
  return path.split(".").reduce((value, part) => (value && typeof value === "object" ? value[part] : undefined), target);
}


function manualFormFieldNames() {
  return Array.from(manualForm.elements)
    .map((field) => field.name)
    .filter(Boolean);
}


function normalizeModelResult(result) {
  return result && typeof result === "object" ? result : {};
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


function renderItems(element, items, emptyText, formatter) {
  if (!items.length) {
    element.className = "item-list empty";
    element.textContent = emptyText;
    return;
  }
  element.className = "item-list";
  element.innerHTML = items.map(formatter).join("");
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
  manualForm.querySelectorAll(".missing-field").forEach((field) => field.classList.remove("missing-field"));
  manualForm.querySelectorAll(".is-missing").forEach((field) => field.classList.remove("is-missing"));
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


function setFieldValue(name, value) {
  const field = manualForm.elements.namedItem(name);
  if (!field || value === undefined || field instanceof RadioNodeList) {
    return;
  }
  if (field.type === "checkbox") {
    field.checked = Boolean(value);
    return;
  }
  if (JSON_TEXTAREA_PATHS.includes(name)) {
    field.value = value && typeof value === "object" ? JSON.stringify(value, null, 2) : "";
    return;
  }
  if (ARRAY_INPUT_PATHS.includes(name)) {
    field.value = Array.isArray(value) ? value.join(", ") : "";
    return;
  }
  field.value = value ?? "";
}


function applyPayloadToManualForm(payload) {
  if (!payload) {
    return;
  }
  manualFormFieldNames().forEach((fieldName) => {
    setFieldValue(fieldName, getNestedValue(payload, fieldName));
  });
}


function validateFormAgainstSchema() {
  const formNames = manualFormFieldNames();
  const missingFormFields = REQUIRED_PATHS.filter((fieldName) => !formNames.includes(fieldName));
  if (missingFormFields.length) {
    throw new Error("采集页字段与 dossier 定义不一致，请检查表单配置");
  }
}


function validateDossierPayload(payload) {
  const missing = REQUIRED_PATHS.filter((path) => {
    const value = getNestedValue(payload, path);
    if (typeof value === "boolean") {
      return false;
    }
    if (Array.isArray(value)) {
      return value.length === 0;
    }
    return value === null || value === undefined || value === "";
  });

  const invalids = {};
  for (const path of DATE_PATHS) {
    const value = getNestedValue(payload, path);
    if (value && !/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
      invalids[path] = "请使用年-月-日格式。";
    }
  }
  for (const path of EMAIL_PATHS) {
    const value = getNestedValue(payload, path);
    if (value && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(value))) {
      invalids[path] = "请输入有效邮箱。";
    }
  }
  for (const [path, values] of Object.entries(ENUMS)) {
    const value = getNestedValue(payload, path);
    if (value && !values.includes(value)) {
      invalids[path] = "请按当前选项填写。";
    }
  }
  if (!Array.isArray(payload.evidence_catalog)) {
    invalids["evidence_catalog"] = "必须是 JSON 数组。";
  }
  if (payload.evidence_catalog && Array.isArray(payload.evidence_catalog)) {
    payload.evidence_catalog.forEach((item, index) => {
      if (!item || typeof item !== "object" || !item.id || !item.kind || !item.description) {
        invalids[`evidence_catalog`] = `第 ${index + 1} 条证据缺少 id/kind/description。`;
      }
    });
  }
  if (!payload.security_background?.explanations || typeof payload.security_background.explanations !== "object" || Array.isArray(payload.security_background.explanations)) {
    invalids["security_background.explanations"] = "必须是 JSON 对象。";
  }

  return { missing, invalids };
}


function refreshManualValidation(scrollToFirst = false) {
  let payload;
  try {
    payload = manualPayload();
  } catch (error) {
    renderItems(missingFields, [], "没有缺失字段。", issueCard);
    renderItems(visionWarnings, [error.message || "JSON 字段格式错误。"], "没有额外提醒。", warningCard);
    return { missing: [], invalids: { json: error.message || "JSON 字段格式错误。" } };
  }
  const { missing, invalids } = validateDossierPayload(payload);
  const problemFields = [...new Set([...missing, ...Object.keys(invalids)])];
  if (problemFields.length) {
    highlightMissingFields(problemFields, scrollToFirst);
    Object.entries(invalids).forEach(([fieldName, message]) => setFieldHint(fieldName, message));
  } else {
    clearMissingHighlights();
  }
  renderItems(missingFields, problemFields, "没有缺失字段。", issueCard);
  renderItems(visionWarnings, Object.values(invalids), "没有额外提醒。", warningCard);
  return { missing, invalids };
}


function manualPayload() {
  const payload = {
    case_id: normalizedOptional(manualForm.elements.namedItem("case_id").value),
    identity: {
      surname: normalizedOptional(manualForm.elements.namedItem("identity.surname").value),
      given_names: normalizedOptional(manualForm.elements.namedItem("identity.given_names").value),
      native_full_name: normalizedOptional(manualForm.elements.namedItem("identity.native_full_name").value),
      sex: normalizedOptional(manualForm.elements.namedItem("identity.sex").value),
      marital_status: normalizedOptional(manualForm.elements.namedItem("identity.marital_status").value),
      date_of_birth: normalizedOptional(manualForm.elements.namedItem("identity.date_of_birth").value),
      birth_city: normalizedOptional(manualForm.elements.namedItem("identity.birth_city").value),
      birth_province: normalizedOptional(manualForm.elements.namedItem("identity.birth_province").value),
      birth_country: normalizedOptional(manualForm.elements.namedItem("identity.birth_country").value),
      nationality: normalizedOptional(manualForm.elements.namedItem("identity.nationality").value),
      passport_number: normalizedOptional(manualForm.elements.namedItem("identity.passport_number").value),
      passport_issuance_country: normalizedOptional(manualForm.elements.namedItem("identity.passport_issuance_country").value),
      passport_issue_date: normalizedOptional(manualForm.elements.namedItem("identity.passport_issue_date").value),
      passport_expiration_date: normalizedOptional(manualForm.elements.namedItem("identity.passport_expiration_date").value),
      passport_book_number: normalizedOptional(manualForm.elements.namedItem("identity.passport_book_number").value),
      source_ids: parseStringArray(manualForm.elements.namedItem("identity.source_ids").value),
    },
    travel_plan: {
      visa_class: normalizedOptional(manualForm.elements.namedItem("travel_plan.visa_class").value),
      purpose_notes: normalizedOptional(manualForm.elements.namedItem("travel_plan.purpose_notes").value),
      intended_arrival_date: normalizedOptional(manualForm.elements.namedItem("travel_plan.intended_arrival_date").value),
      intended_length_of_stay_value: normalizedOptional(manualForm.elements.namedItem("travel_plan.intended_length_of_stay_value").value),
      intended_length_of_stay_unit: normalizedOptional(manualForm.elements.namedItem("travel_plan.intended_length_of_stay_unit").value),
      payer_name: normalizedOptional(manualForm.elements.namedItem("travel_plan.payer_name").value),
      us_contact_name: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_name").value),
      us_contact_organization: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_organization").value),
      us_contact_address_line1: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_address_line1").value),
      us_contact_city: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_city").value),
      us_contact_state: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_state").value),
      us_contact_postal_code: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_postal_code").value),
      us_contact_phone: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_phone").value),
      us_contact_email: normalizedOptional(manualForm.elements.namedItem("travel_plan.us_contact_email").value),
      source_ids: parseStringArray(manualForm.elements.namedItem("travel_plan.source_ids").value),
    },
    employment_education: {
      primary_occupation: normalizedOptional(manualForm.elements.namedItem("employment_education.primary_occupation").value),
      current_employer_name: normalizedOptional(manualForm.elements.namedItem("employment_education.current_employer_name").value),
      current_employer_address: normalizedOptional(manualForm.elements.namedItem("employment_education.current_employer_address").value),
      monthly_income_local: normalizedOptional(manualForm.elements.namedItem("employment_education.monthly_income_local").value),
      school_name: normalizedOptional(manualForm.elements.namedItem("employment_education.school_name").value),
      source_ids: parseStringArray(manualForm.elements.namedItem("employment_education.source_ids").value),
    },
    family_contacts: {
      father_full_name: normalizedOptional(manualForm.elements.namedItem("family_contacts.father_full_name").value),
      mother_full_name: normalizedOptional(manualForm.elements.namedItem("family_contacts.mother_full_name").value),
      spouse_full_name: normalizedOptional(manualForm.elements.namedItem("family_contacts.spouse_full_name").value),
      us_relative_name: normalizedOptional(manualForm.elements.namedItem("family_contacts.us_relative_name").value),
      us_relative_status: normalizedOptional(manualForm.elements.namedItem("family_contacts.us_relative_status").value),
      source_ids: parseStringArray(manualForm.elements.namedItem("family_contacts.source_ids").value),
    },
    security_background: {
      yes_no_answers: {
        communicable_disease: manualForm.elements.namedItem("security_background.yes_no_answers.communicable_disease").checked,
        arrest_history: manualForm.elements.namedItem("security_background.yes_no_answers.arrest_history").checked,
      },
      explanations: parseJsonText(manualForm.elements.namedItem("security_background.explanations").value, {}),
      source_ids: parseStringArray(manualForm.elements.namedItem("security_background.source_ids").value),
    },
    evidence_catalog: parseJsonText(manualForm.elements.namedItem("evidence_catalog").value, []),
  };
  return payload;
}


async function buildExportDocument(payload) {
  try {
    const res = await fetch(`${SERVER_BASE}/dossier/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "无法生成 dossier");
    }
    return data.dossier;
  } catch {
    activateOfflineMode();
    return payload;
  }
}


async function renderManualResult(payload) {
  clearMissingHighlights();
  const exportDocument = await buildExportDocument(payload);
  state.latestJsonText = JSON.stringify(exportDocument, null, 2);
  jsonPreview.textContent = state.latestJsonText;
  renderItems(missingFields, [], "手填方式已补齐当前 dossier。", issueCard);
  renderItems(visionWarnings, [], "没有额外提醒。", warningCard);
  renderItems(documentReports, [], "这次使用的是手动填写。", reportCard);
  downloadButton.disabled = false;
  copyButton.disabled = false;
  submitStatus.textContent = "手动整理完成，当前导出的是可直接导入执行页的 full dossier。";
}


function buildLocalPromptText(documents) {
  const schemaDocument = state.schema || FALLBACK_SCHEMA_DOCUMENT;
  const docLines = documents.map((document) => `- ${document.kind}: ${document.filename}`).join("\n") || "- 未选择文件";
  return [
    "你是美国签证资料整理助手。请根据我接下来上传的图片，直接返回一个完整 dossier JSON 对象。",
    "要求：",
    "1. 只允许返回 schema 中定义的字段",
    "2. 不要输出 markdown",
    "3. 不要输出解释文字",
    "4. 缺失或无法确认的字段请填 null，source_ids 至少填能确认的来源 id",
    "5. evidence_catalog 必须返回数组",
    "",
    `这次我会上传这些材料：\n${docLines}`,
    "",
    `目标 schema:\n${JSON.stringify(schemaDocument, null, 2)}`,
  ].join("\n");
}


function manifestCard(doc) {
  const inputId = `upload-${doc.kind}`;
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
      <div class="upload-control">
        <input id="${inputId}" class="manifest-file-input" type="file" accept="image/*" data-upload-kind="${doc.kind}" />
        <label for="${inputId}" class="upload-trigger">选择图片</label>
        <div class="manifest-note" data-note-kind="${doc.kind}">尚未选择文件。</div>
      </div>
    </article>
  `;
}


function renderManifest() {
  manifestGrid.innerHTML = state.manifest.map(manifestCard).join("");
  manifestGrid.querySelectorAll("[data-upload-kind]").forEach((input) => {
    input.addEventListener("change", () => {
      const note = manifestGrid.querySelector(`[data-note-kind="${input.dataset.uploadKind}"]`);
      note.textContent = input.files?.[0] ? `已选择：${input.files[0].name}` : "尚未选择文件。";
    });
  });
}


async function loadManifest() {
  try {
    const res = await fetch(`${SERVER_BASE}/vision-intake/manifest`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "无法读取图片整理清单");
    }
    state.manifest = data.documents || [];
  } catch {
    state.manifest = FALLBACK_VISION_MANIFEST;
    activateOfflineMode();
  }
  renderManifest();
}


async function loadSchema() {
  try {
    const res = await fetch(`${SERVER_BASE}/dossier-schema`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "无法读取 dossier schema");
    }
    state.schema = data.schema_document;
  } catch {
    state.schema = FALLBACK_SCHEMA_DOCUMENT;
    activateOfflineMode();
  }
  validateFormAgainstSchema();
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


async function copyTextToClipboard(text) {
  if (!text) {
    throw new Error("没有可复制的内容");
  }
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Fall back for file:// pages or browsers without clipboard permission.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "0";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) {
    throw new Error("当前页面无法直接复制，请手动复制。");
  }
}


function flashButtonSuccess(button, successText, defaultText) {
  if (button.dataset.resetTimer) {
    window.clearTimeout(Number(button.dataset.resetTimer));
  }
  button.textContent = successText;
  const timerId = window.setTimeout(() => {
    button.textContent = defaultText;
    delete button.dataset.resetTimer;
  }, 1800);
  button.dataset.resetTimer = String(timerId);
}


async function copyPrompt() {
  copyPromptButton.disabled = true;
  copyPromptButton.textContent = "生成中…";
  try {
    const documents = await collectUploads();
    if (!documents.length) {
      throw new Error("至少需要上传一份图片材料");
    }
    let promptText = "";
    let usedLocalPrompt = false;
    try {
      const res = await fetch(`${SERVER_BASE}/vision-intake/prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ documents }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "提示词生成失败");
      }
      promptText = data.prompt_text;
    } catch {
      activateOfflineMode();
      usedLocalPrompt = true;
      promptText = buildLocalPromptText(documents);
    }
    await copyTextToClipboard(promptText);
    flashButtonSuccess(copyPromptButton, "已复制", "一键复制提示词");
    submitStatus.textContent = usedLocalPrompt
      ? "提示词已复制。当前使用的是离线提示词，请把同样的图片上传到外部大模型。"
      : "提示词已复制。下一步请去外部大模型上传同样的图片并运行。";
  } catch (error) {
    submitStatus.textContent = error.message || "提示词复制失败，请稍后再试。";
  } finally {
    copyPromptButton.disabled = false;
    if (copyPromptButton.textContent === "生成中…") {
      copyPromptButton.textContent = "一键复制提示词";
    }
  }
}


function openResultDialog() {
  resultInput.value = "";
  resultDialog.showModal();
}


function buildLocalValidationResult(result) {
  const dossier = normalizeModelResult(result);
  const { missing, invalids } = validateDossierPayload(dossier);
  const warnings = Object.entries(invalids).map(([fieldName, message]) => `${fieldName}: ${message}`);
  return {
    ok: true,
    dossier_document: missing.length || Object.keys(invalids).length ? null : dossier,
    missing_fields: missing.length ? missing : Object.keys(invalids),
    warnings,
    documents: [],
  };
}


async function renderExtractionResult(data) {
  const partialPayload = data.dossier_document || {};
  applyPayloadToManualForm(partialPayload);
  if (data.missing_fields?.length) {
    highlightMissingFields(data.missing_fields || []);
  } else {
    clearMissingHighlights();
  }
  renderItems(missingFields, data.missing_fields || [], "没有缺失字段。", issueCard);
  renderItems(visionWarnings, data.warnings || [], "没有额外提醒。", warningCard);
  renderItems(documentReports, data.documents || [], "没有文档处理结果。", reportCard);

  if (data.dossier_document) {
    state.latestJsonText = JSON.stringify(data.dossier_document, null, 2);
    jsonPreview.textContent = state.latestJsonText;
    downloadButton.disabled = false;
    copyButton.disabled = false;
    submitStatus.textContent = "资料整理完成，识别结果已经回填到表单，当前导出的是 full dossier。";
  } else {
    state.latestJsonText = "";
    jsonPreview.textContent = "材料已经读取，但 dossier 还不完整。可以补传更清晰的图片，或者直接用下方手填内容补齐。";
    downloadButton.disabled = true;
    copyButton.disabled = true;
    submitStatus.textContent = "已把识别到的内容回填到表单，请补齐剩余信息。";
  }
}


async function applyModelResult() {
  try {
    const parsed = JSON.parse(resultInput.value);
    let data;
    try {
      const res = await fetch(`${SERVER_BASE}/vision-intake/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result: parsed }),
      });
      data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "模型结果处理失败");
      }
    } catch {
      activateOfflineMode();
      data = buildLocalValidationResult(parsed);
    }
    await renderExtractionResult(data);
    resultDialog.close();
    submitStatus.textContent = data.dossier_document
      ? "模型结果已应用，资料可以直接导出为 full dossier。"
      : "模型结果已应用，但还有缺失或格式问题，请继续补齐。";
  } catch (error) {
    submitStatus.textContent = error.message || "无法应用模型结果。";
  }
}


function downloadJson() {
  if (!state.latestJsonText) {
    return;
  }
  const blob = new Blob([state.latestJsonText], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "china-b1b2-dossier.json";
  link.click();
  URL.revokeObjectURL(url);
}


async function copyJson() {
  if (!state.latestJsonText) {
    return;
  }
  try {
    await copyTextToClipboard(state.latestJsonText);
    flashButtonSuccess(copyButton, "已复制", "复制资料内容");
    submitStatus.textContent = "已复制资料内容。下一步去执行页导入即可。";
  } catch {
    submitStatus.textContent = "复制失败，请直接下载资料文件。";
  }
}


copyPromptButton.addEventListener("click", copyPrompt);
pasteResultButton.addEventListener("click", openResultDialog);
applyResultButton.addEventListener("click", applyModelResult);
manualForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  let payload;
  try {
    payload = manualPayload();
  } catch (error) {
    submitStatus.textContent = error.message || "JSON 字段格式错误。";
    refreshManualValidation(true);
    return;
  }
  const { missing, invalids } = validateDossierPayload(payload);
  if (missing.length || Object.keys(invalids).length) {
    refreshManualValidation(true);
    submitStatus.textContent = "还有未填写或格式不对的信息，请先补齐高亮位置。";
    return;
  }
  await renderManualResult(payload);
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
