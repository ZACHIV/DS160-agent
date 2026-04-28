const SERVER_BASE = "http://127.0.0.1:8765";
const OFFLINE_MODE_MESSAGE = "已切换到离线模式：本地服务未连接。";

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

const manualForm = document.getElementById("manual-form");
const submitStatus = document.getElementById("submit-status");
const jsonPreview = document.getElementById("json-preview");
const downloadButton = document.getElementById("download-json");
const downloadEncryptedButton = document.getElementById("download-encrypted");
const encryptPassphraseInput = document.getElementById("encrypt-passphrase");
const copyButton = document.getElementById("copy-json");
const missingFields = document.getElementById("missing-fields");
const warnings = document.getElementById("warnings");

const photoUpload = document.getElementById("photo-upload");
const photoPreview = document.getElementById("photo-preview");

const state = {
  latestJsonText: "",
  schema: null,
  offlineMode: false,
  photoDataUrl: null,
};


function activateOfflineMode() {
  state.offlineMode = true;
  submitStatus.textContent = OFFLINE_MODE_MESSAGE;
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


function issueCard(value) {
  return `<article class="item-card"><strong>${value}</strong></article>`;
}


function warningCard(value) {
  return `<article class="item-card"><strong>${value}</strong></article>`;
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
    renderItems(warnings, [error.message || "JSON 字段格式错误。"], "没有额外提醒。", warningCard);
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
  renderItems(warnings, Object.values(invalids), "没有额外提醒。", warningCard);
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
}


function copyTextToClipboard(text) {
  if (!text) {
    throw new Error("没有可复制的内容");
  }
  if (navigator.clipboard?.writeText) {
    try {
      return navigator.clipboard.writeText(text);
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


async function downloadEncryptedJson() {
  if (!state.latestJsonText) {
    submitStatus.textContent = "请先生成资料。";
    return;
  }
  const passphrase = (encryptPassphraseInput.value || "").trim();
  if (passphrase.length < 8) {
    submitStatus.textContent = "加密密码至少需要8位字符。";
    return;
  }
  downloadEncryptedButton.disabled = true;
  downloadEncryptedButton.textContent = "加密中…";
  try {
    if (!state.offlineMode) {
      const res = await fetch(`${SERVER_BASE}/dossier-document/encrypt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passphrase }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        const encryptedJson = JSON.stringify(data.encrypted_payload, null, 2);
        const blob = new Blob([encryptedJson], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "china-b1b2-dossier.enc.json";
        link.click();
        URL.revokeObjectURL(url);
        submitStatus.textContent = "已下载加密文件。请妥善保管密码。";
        return;
      }
      throw new Error(data.detail || "服务端加密失败");
    }
    // Offline: encrypt client-side via Web Crypto
    const enc = new TextEncoder();
    const plaintext = enc.encode(state.latestJsonText);
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const keyMaterial = await crypto.subtle.importKey("raw", enc.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
    const key = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
      keyMaterial,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt"]
    );
    const nonce = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, plaintext);
    const payload = {
      format: "ds160-encrypted-v1",
      salt_b64: btoa(String.fromCharCode(...salt)),
      nonce_b64: btoa(String.fromCharCode(...nonce)),
      ciphertext_b64: btoa(String.fromCharCode(...new Uint8Array(ciphertext))),
    };
    const encryptedJson = JSON.stringify(payload, null, 2);
    const blob = new Blob([encryptedJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "china-b1b2-dossier.enc.json";
    link.click();
    URL.revokeObjectURL(url);
    submitStatus.textContent = "已下载加密文件（离线模式）。请妥善保管密码。";
  } catch (error) {
    submitStatus.textContent = (error && error.message) ? error.message : "加密导出失败";
  } finally {
    downloadEncryptedButton.disabled = false;
    downloadEncryptedButton.textContent = "下载加密文件";
  }
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


if (photoUpload) {
  photoUpload.addEventListener("change", function () {
    const file = photoUpload.files?.[0];
    if (!file) {
      state.photoDataUrl = null;
      photoPreview.style.display = "none";
      return;
    }
    if (!file.type.startsWith("image/")) {
      submitStatus.textContent = "照片必须是 JPEG 或 PNG 格式。";
      photoUpload.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = function (e) {
      const img = new Image();
      img.onload = function () {
        if (img.width < 600 || img.height < 600) {
          submitStatus.textContent = `照片尺寸 ${img.width}x${img.height}，需要至少 600x600 像素（2x2英寸）。`;
          state.photoDataUrl = null;
          photoPreview.style.display = "none";
          return;
        }
        state.photoDataUrl = e.target.result;
        photoPreview.src = e.target.result;
        photoPreview.style.display = "";
        submitStatus.textContent = `照片已就绪：${img.width}x${img.height} 像素`;
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}


function enrichPayloadWithPhoto(payload) {
  if (state.photoDataUrl) {
    if (!Array.isArray(payload.evidence_catalog)) {
      payload.evidence_catalog = [];
    }
    const existing = payload.evidence_catalog.find((e) => e.kind === "photo");
    if (!existing) {
      payload.evidence_catalog.push({
        id: "visa_photo",
        kind: "photo",
        description: "Visa application photo (digital)",
      });
    }
  }
  return payload;
}


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

  clearMissingHighlights();
  payload = enrichPayloadWithPhoto(payload);
  const exportDocument = await buildExportDocument(payload);
  state.latestJsonText = JSON.stringify(exportDocument, null, 2);
  jsonPreview.textContent = state.latestJsonText;
  renderItems(missingFields, [], "当前表单已补齐。", issueCard);
  renderItems(warnings, [], "没有额外提醒。", warningCard);
  downloadButton.disabled = false;
  downloadEncryptedButton.disabled = false;
  copyButton.disabled = false;
  submitStatus.textContent = "整理完成，当前导出的是可直接导入执行页的完整 dossier JSON 对象。";
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
downloadEncryptedButton.addEventListener("click", downloadEncryptedJson);
copyButton.addEventListener("click", copyJson);
downloadButton.disabled = true;
downloadEncryptedButton.disabled = true;
copyButton.disabled = true;

loadSchema().catch((error) => {
  submitStatus.textContent = error.message || "页面初始化失败，请确认服务已启动。";
});
