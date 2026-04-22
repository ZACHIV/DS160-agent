const SERVER_BASE = "http://127.0.0.1:8765";
const OFFLINE_MODE_MESSAGE = "已切换到离线模式：本地服务未连接。你仍然可以上传图片、复制提示词、粘贴模型结果和手动填写。";

const FALLBACK_VISION_MANIFEST = [
  {
    kind: "passport_bio",
    label: "护照资料页",
    description: "上传中国护照个人信息页清晰照片或扫描件。需要能看清英文姓名、护照号、出生地、性别、签发日期和失效日期。",
    required: true,
  },
  {
    kind: "trip_proof",
    label: "赴美行程或邀请材料",
    description: "上传行程单、邀请函，或一张写明赴美目的、到达日期、停留时长、费用承担方的截图。",
    required: true,
  },
  {
    kind: "us_contact_proof",
    label: "美国联系人材料",
    description: "上传联系人名片、邀请函页，或一张写明姓名、电话、地址、城市、州、邮编、邮箱的截图。",
    required: true,
  },
  {
    kind: "employment_proof",
    label: "工作或学校材料",
    description: "上传在职证明、工作名片、学校证明，或一张写明职业、单位名称、单位地址的截图。",
    required: true,
  },
  {
    kind: "family_info_sheet",
    label: "家庭信息材料",
    description: "上传户口本相关页、结婚证补充页，或一张写明婚姻状态、父母姓名、配偶姓名的截图。",
    required: true,
  },
  {
    kind: "security_questionnaire",
    label: "安全背景问卷",
    description: "上传一张写明“是否有传染病相关情况”“是否有逮捕或犯罪记录”的是/否截图或照片。",
    required: true,
  },
];

const FALLBACK_SCHEMA_DOCUMENT = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "https://local.ds160/intake-v1.schema.json",
  title: "DS-160 Intake V1",
  type: "object",
  additionalProperties: false,
  properties: {
    surname: { type: "string", minLength: 1 },
    given_names: { type: "string", minLength: 1 },
    native_full_name: { type: ["string", "null"] },
    sex: { type: "string", enum: ["MALE", "FEMALE"] },
    marital_status: { type: "string", enum: ["SINGLE", "MARRIED", "DIVORCED", "WIDOWED"] },
    date_of_birth: { type: "string", format: "date" },
    birth_city: { type: "string", minLength: 1 },
    passport_number: { type: "string", minLength: 1 },
    passport_issue_date: { type: "string", format: "date" },
    passport_expiration_date: { type: "string", format: "date" },
    trip_purpose: { type: "string", enum: ["business_tourism", "business", "tourism", "family_visit"] },
    intended_arrival_date: { type: "string", format: "date" },
    intended_length_of_stay_value: { type: "string", minLength: 1 },
    intended_length_of_stay_unit: { type: "string", enum: ["DAYS", "WEEKS", "MONTHS"] },
    payer_name: { type: "string", minLength: 1 },
    us_contact_name: { type: "string", minLength: 1 },
    us_contact_organization: { type: ["string", "null"] },
    us_contact_phone: { type: "string", minLength: 1 },
    us_contact_address_line1: { type: "string", minLength: 1 },
    us_contact_city: { type: "string", minLength: 1 },
    us_contact_state: { type: "string", minLength: 1 },
    us_contact_postal_code: { type: "string", minLength: 1 },
    us_contact_email: { type: ["string", "null"], format: "email" },
    primary_occupation: { type: "string", enum: ["BUSINESSPERSON", "STUDENT", "OTHER"] },
    current_employer_name: { type: "string", minLength: 1 },
    current_employer_address: { type: "string", minLength: 1 },
    father_full_name: { type: "string", minLength: 1 },
    mother_full_name: { type: "string", minLength: 1 },
    spouse_full_name: { type: ["string", "null"] },
    communicable_disease: { type: "boolean", default: false },
    arrest_history: { type: "boolean", default: false },
  },
  required: [
    "surname",
    "given_names",
    "sex",
    "marital_status",
    "date_of_birth",
    "birth_city",
    "passport_number",
    "passport_issue_date",
    "passport_expiration_date",
    "trip_purpose",
    "intended_arrival_date",
    "intended_length_of_stay_value",
    "intended_length_of_stay_unit",
    "payer_name",
    "us_contact_name",
    "us_contact_phone",
    "us_contact_address_line1",
    "us_contact_city",
    "us_contact_state",
    "us_contact_postal_code",
    "primary_occupation",
    "current_employer_name",
    "current_employer_address",
    "father_full_name",
    "mother_full_name",
    "communicable_disease",
    "arrest_history",
  ],
};

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


function activateOfflineMode() {
  state.offlineMode = true;
  submitStatus.textContent = OFFLINE_MODE_MESSAGE;
}


function flashButtonSuccess(button, successText, defaultText) {
  if (!button) {
    return;
  }
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


function renderManifest() {
  manifestGrid.innerHTML = state.manifest.map(manifestCard).join("");
  manifestGrid.querySelectorAll("[data-upload-kind]").forEach((input) => {
    input.addEventListener("change", () => {
      const note = manifestGrid.querySelector(`[data-note-kind="${input.dataset.uploadKind}"]`);
      note.textContent = input.files?.[0] ? `已选择：${input.files[0].name}` : "尚未选择文件。";
    });
  });
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


function buildLocalPromptText(documents) {
  const schemaDocument = state.schema || FALLBACK_SCHEMA_DOCUMENT;
  const docLines = documents.map((document) => `- ${document.kind}: ${document.filename}`).join("\n") || "- 未选择文件";
  return [
    "你是美国签证资料整理助手。请根据我接下来上传的图片，直接返回一个 JSON 对象。",
    "要求：",
    "1. 只允许返回 schema 中定义的字段",
    "2. 不要输出 markdown",
    "3. 不要输出解释文字",
    "4. 缺失或无法确认的字段请填 null",
    "5. 布尔字段必须返回 true 或 false",
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


function validateFormAgainstSchema() {
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
    const res = await fetch(`${SERVER_BASE}/intake-schema`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "无法读取资料定义");
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


function normalizeModelResult(result) {
  const payload = {};
  for (const fieldName of schemaFieldNames()) {
    const value = result[fieldName];
    if (value === undefined) {
      payload[fieldName] = null;
      continue;
    }
    payload[fieldName] = typeof value === "string" ? value.trim() : value;
  }
  return payload;
}


function buildLocalValidationResult(result) {
  const payload = normalizeModelResult(result);
  const { missing, invalids, extras } = validateManualPayload(payload);
  const warnings = [
    ...Object.entries(invalids).map(([fieldName, message]) => `${fieldName}: ${message}`),
    ...extras.map((fieldName) => `忽略未定义字段：${fieldName}`),
  ];
  return {
    ok: true,
    intake_document: missing.length || Object.keys(invalids).length ? null : payload,
    missing_fields: missing.length ? missing : Object.keys(invalids),
    warnings,
    documents: [],
  };
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
