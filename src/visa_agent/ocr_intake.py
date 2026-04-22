from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from typing import Callable
from urllib import request
from uuid import uuid4
import re

from visa_agent.intake_contract import intake_field_errors, missing_required_intake_fields, normalized_intake_payload, validate_intake_payload
from visa_agent.intake import ApplicantIntake, intake_to_dict


@dataclass(frozen=True)
class OCRDocumentSpec:
    kind: str
    label: str
    description: str
    language: str
    required: bool = True


@dataclass(frozen=True)
class OCRUploadedDocument:
    kind: str
    filename: str
    media_type: str
    base64_data: str


@dataclass(frozen=True)
class OCRDocumentReport:
    kind: str
    filename: str
    status: str
    extracted_fields: dict[str, object]
    warnings: list[str]
    text_preview: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OCRIntakeResult:
    intake_document: dict[str, object] | None
    missing_fields: list[str]
    warnings: list[str]
    documents: list[OCRDocumentReport]

    def to_dict(self) -> dict[str, object]:
        return {
            "intake_document": self.intake_document,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
            "documents": [item.to_dict() for item in self.documents],
        }


OCR_DOCUMENT_SPECS = [
    OCRDocumentSpec(
        kind="passport_bio",
        label="护照资料页",
        description="上传中国护照个人信息页清晰照片或扫描件。需要能看到英文姓名、护照号、出生地、性别、签发/失效日期。",
        language="eng",
    ),
    OCRDocumentSpec(
        kind="trip_proof",
        label="赴美行程或邀请材料",
        description="上传行程单、邀请函，或一张写有 Trip Purpose / Arrival Date / Length of Stay / Payer 的截图。",
        language="eng",
    ),
    OCRDocumentSpec(
        kind="us_contact_proof",
        label="美国联系人材料",
        description="上传联系人名片、邀请函页，或一张写有 Contact Name / Phone / Address / City / State / Postal Code / Email 的截图。",
        language="eng",
    ),
    OCRDocumentSpec(
        kind="employment_proof",
        label="工作或学校材料",
        description="上传在职证明、工作名片、学校证明，或一张写有 Occupation / Employer / Employer Address 的截图。",
        language="eng",
    ),
    OCRDocumentSpec(
        kind="family_info_sheet",
        label="家庭信息材料",
        description="上传户口本相关页、结婚证补充页，或一张写有 Marital Status / Father / Mother / Spouse 的截图。",
        language="chs",
    ),
    OCRDocumentSpec(
        kind="security_questionnaire",
        label="安全背景问卷",
        description="上传一张写有 Communicable Disease / Arrest History 对应 Yes 或 No 的截图或照片。",
        language="eng",
    ),
]


class OCRSpaceClient:
    def __init__(self, api_key: str | None = None, endpoint: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OCR_SPACE_API_KEY", "helloworld")
        self.endpoint = endpoint or os.environ.get("OCR_SPACE_ENDPOINT", "https://api.ocr.space/parse/image")

    def extract_text(self, document: OCRUploadedDocument, language: str) -> str:
        boundary = f"----CodexOCR{uuid4().hex}"
        fields = {
            "base64Image": document.base64_data,
            "language": language,
            "detectOrientation": "true",
            "scale": "true",
            "isOverlayRequired": "false",
            "OCREngine": "2",
        }
        body = _multipart_form_body(fields, boundary)
        req = request.Request(
            self.endpoint,
            data=body,
            headers={
                "apikey": self.api_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("IsErroredOnProcessing"):
            errors = payload.get("ErrorMessage") or payload.get("ErrorDetails") or ["OCR processing failed"]
            raise RuntimeError("; ".join(errors if isinstance(errors, list) else [str(errors)]))
        parsed = payload.get("ParsedResults") or []
        return "\n".join(item.get("ParsedText", "") for item in parsed).strip()


def _multipart_form_body(fields: dict[str, str], boundary: str) -> bytes:
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def ocr_document_specs() -> list[dict[str, object]]:
    return [asdict(item) for item in OCR_DOCUMENT_SPECS]


def extract_intake_from_documents(
    documents: list[OCRUploadedDocument],
    ocr_extractor: Callable[[OCRUploadedDocument, str], str] | None = None,
) -> OCRIntakeResult:
    extractor = ocr_extractor or OCRSpaceClient().extract_text
    field_values: dict[str, object] = {}
    warnings: list[str] = []
    reports: list[OCRDocumentReport] = []
    spec_by_kind = {item.kind: item for item in OCR_DOCUMENT_SPECS}

    for spec in OCR_DOCUMENT_SPECS:
        match = next((item for item in documents if item.kind == spec.kind), None)
        if not match:
            warnings.append(f"缺少必传文件：{spec.label}")
            reports.append(
                OCRDocumentReport(
                    kind=spec.kind,
                    filename="",
                    status="missing",
                    extracted_fields={},
                    warnings=[f"未上传 {spec.label}"],
                    text_preview="",
                )
            )
            continue
        try:
            text = extractor(match, spec.language)
            extracted = _extract_fields_for_kind(spec.kind, text)
            report_warnings = _warnings_for_kind(spec.kind, extracted)
            reports.append(
                OCRDocumentReport(
                    kind=spec.kind,
                    filename=match.filename,
                    status="processed",
                    extracted_fields=extracted,
                    warnings=report_warnings,
                    text_preview=text[:500],
                )
            )
            field_values.update({key: value for key, value in extracted.items() if value not in (None, "")})
            warnings.extend(report_warnings)
        except Exception as exc:
            reports.append(
                OCRDocumentReport(
                    kind=spec.kind,
                    filename=match.filename,
                    status="error",
                    extracted_fields={},
                    warnings=[str(exc)],
                    text_preview="",
                )
            )
            warnings.append(f"{spec.label} OCR 失败：{exc}")

    for uploaded in documents:
        if uploaded.kind not in spec_by_kind:
            warnings.append(f"忽略未知文件类型：{uploaded.kind}")

    intake_document, missing_fields, validation_warnings = _build_complete_intake(field_values)
    return OCRIntakeResult(
        intake_document=intake_document,
        missing_fields=missing_fields,
        warnings=_unique_list(warnings + validation_warnings),
        documents=reports,
    )


def _build_complete_intake(field_values: dict[str, object]) -> tuple[dict[str, object] | None, list[str], list[str]]:
    payload = normalized_intake_payload(field_values)
    missing = missing_required_intake_fields(payload)
    if missing:
        return None, missing, []
    errors = intake_field_errors(payload)
    if errors:
        invalid_fields = list(errors.keys())
        warnings = [f"{field} 格式或取值不符合要求" for field in invalid_fields]
        return None, invalid_fields, warnings
    intake = ApplicantIntake(**validate_intake_payload(payload))
    return intake_to_dict(intake), missing, []


def _warnings_for_kind(kind: str, extracted: dict[str, object]) -> list[str]:
    expectations = {
        "passport_bio": ["surname", "given_names", "sex", "date_of_birth", "birth_city", "passport_number", "passport_issue_date", "passport_expiration_date"],
        "trip_proof": ["trip_purpose", "intended_arrival_date", "intended_length_of_stay_value", "intended_length_of_stay_unit", "payer_name"],
        "us_contact_proof": ["us_contact_name", "us_contact_phone", "us_contact_address_line1", "us_contact_city", "us_contact_state", "us_contact_postal_code"],
        "employment_proof": ["primary_occupation", "current_employer_name", "current_employer_address"],
        "family_info_sheet": ["marital_status", "father_full_name", "mother_full_name"],
        "security_questionnaire": ["communicable_disease", "arrest_history"],
    }
    return [f"{kind} 未识别到 {field}" for field in expectations.get(kind, []) if extracted.get(field) in (None, "")]


def _extract_fields_for_kind(kind: str, text: str) -> dict[str, object]:
    normalized = _normalize_text(text)
    if kind == "passport_bio":
        return _extract_passport_fields(normalized)
    if kind == "trip_proof":
        return _extract_trip_fields(normalized)
    if kind == "us_contact_proof":
        return _extract_contact_fields(normalized)
    if kind == "employment_proof":
        return _extract_employment_fields(normalized)
    if kind == "family_info_sheet":
        return _extract_family_fields(normalized)
    if kind == "security_questionnaire":
        return _extract_security_fields(normalized)
    return {}


def _normalize_text(text: str) -> str:
    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned.strip()


def _extract_passport_fields(text: str) -> dict[str, object]:
    sex = _search(text, [r"\bSex[: ]+([MF])\b", r"\bSEX[: ]+([MF])\b"])
    sex_value = {"M": "MALE", "F": "FEMALE"}.get((sex or "").upper(), None)
    return {
        "surname": _search(text, [r"Surname(?:/姓)?[: ]+([^\n]+)", r"\bSurname[: ]+([^\n]+)"]),
        "given_names": _search(text, [r"Given Names?(?:/名)?[: ]+([^\n]+)", r"\bGiven Names?[: ]+([^\n]+)"]),
        "native_full_name": _search(text, [r"姓名[:： ]+([^\n]+)"]),
        "sex": sex_value,
        "date_of_birth": _parse_date(
            _search(text, [r"Date of Birth[: ]+([0-9A-Z\-\/ ]+)", r"Birth Date[: ]+([0-9A-Z\-\/ ]+)"])
        ),
        "birth_city": _search(text, [r"Place of Birth[: ]+([A-Z][A-Z\s]+)", r"出生地[:： ]+([^\n]+)"]),
        "passport_number": _search(text, [r"Passport No\.?[: ]+([A-Z0-9]+)", r"\bNo\.?[: ]+([A-Z0-9]{8,})"]),
        "passport_issue_date": _parse_date(_search(text, [r"Date of Issue[: ]+([0-9A-Z\-\/ ]+)", r"Issue Date[: ]+([0-9A-Z\-\/ ]+)"])),
        "passport_expiration_date": _parse_date(
            _search(text, [r"Date of Expiry[: ]+([0-9A-Z\-\/ ]+)", r"Expiry Date[: ]+([0-9A-Z\-\/ ]+)", r"Expiration Date[: ]+([0-9A-Z\-\/ ]+)"])
        ),
    }


def _extract_trip_fields(text: str) -> dict[str, object]:
    stay_raw = _search(text, [r"(?:Length of Stay|停留时长)[:： ]+([^\n]+)"])
    stay_value, stay_unit = _parse_stay(stay_raw or text)
    return {
        "trip_purpose": _parse_trip_purpose(text),
        "intended_arrival_date": _parse_date(_search(text, [r"(?:Arrival Date|预计到达日期)[:： ]+([0-9A-Z\-\/ ]+)"])),
        "intended_length_of_stay_value": stay_value,
        "intended_length_of_stay_unit": stay_unit,
        "payer_name": _search(text, [r"(?:Payer|费用承担方|付款人)[:： ]+([^\n]+)", r"(?:Paid By)[:： ]+([^\n]+)"]),
    }


def _extract_contact_fields(text: str) -> dict[str, object]:
    return {
        "us_contact_name": _search(text, [r"(?:Contact Name|联系人姓名)[:： ]+([^\n]+)", r"Name[:： ]+([^\n]+)"]),
        "us_contact_organization": _search(text, [r"(?:Organization|Company|机构名称)[:： ]+([^\n]+)"]),
        "us_contact_phone": _search(text, [r"(?:Phone|Tel|联系电话)[:： ]+([+0-9() \-]{7,})"]),
        "us_contact_address_line1": _search(text, [r"(?:Address|地址)[:： ]+([^\n]+)"]),
        "us_contact_city": _search(text, [r"(?:City|城市)[:： ]+([^\n]+)"]),
        "us_contact_state": _search(text, [r"(?:State|州)[:： ]+([^\n]+)"]),
        "us_contact_postal_code": _search(text, [r"(?:Postal Code|ZIP|邮编)[:： ]+([A-Z0-9\- ]+)"]),
        "us_contact_email": _search(text, [r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})"]),
    }


def _extract_employment_fields(text: str) -> dict[str, object]:
    employer = _search(text, [r"(?:Employer|Company|单位名称|当前单位)[:： ]+([^\n]+)"])
    occupation = _search(text, [r"(?:Occupation|职业)[:： ]+([^\n]+)"])
    return {
        "primary_occupation": _parse_occupation(occupation or text),
        "current_employer_name": employer,
        "current_employer_address": _search(text, [r"(?:Employer Address|Company Address|单位地址)[:： ]+([^\n]+)", r"(?:Address|地址)[:： ]+([^\n]+)"]),
    }


def _extract_family_fields(text: str) -> dict[str, object]:
    marital = _search(text, [r"(?:Marital Status|婚姻状态)[:： ]+([^\n]+)"])
    return {
        "marital_status": _parse_marital_status(marital or text),
        "father_full_name": _search(text, [r"(?:Father|父亲)[:： ]+([^\n]+)"]),
        "mother_full_name": _search(text, [r"(?:Mother|母亲)[:： ]+([^\n]+)"]),
        "spouse_full_name": _search(text, [r"(?:Spouse|配偶)[:： ]+([^\n]+)"]),
    }


def _extract_security_fields(text: str) -> dict[str, object]:
    return {
        "communicable_disease": _parse_yes_no(_search(text, [r"(?:Communicable Disease|传染病)[:： ]+([^\n]+)"])),
        "arrest_history": _parse_yes_no(_search(text, [r"(?:Arrest History|被捕记录|犯罪记录)[:： ]+([^\n]+)"])),
    }


def _search(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip(" :：\n\t")
            return value.replace("<", " ").strip()
    return None


def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip().upper().replace(".", " ").replace(",", " ")
    text = re.sub(r"\s+", " ", text)
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%d %m %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    compact = re.search(r"(\d{4})[^\d]?(\d{2})[^\d]?(\d{2})", text)
    if compact:
        return f"{compact.group(1)}-{compact.group(2)}-{compact.group(3)}"
    return None


def _parse_stay(raw: str) -> tuple[str | None, str | None]:
    match = re.search(r"(\d+)\s*(DAY|DAYS|WEEK|WEEKS|MONTH|MONTHS|天|周|月)", raw, flags=re.IGNORECASE)
    if not match:
        return None, None
    unit_map = {
        "DAY": "DAYS",
        "DAYS": "DAYS",
        "天": "DAYS",
        "WEEK": "WEEKS",
        "WEEKS": "WEEKS",
        "周": "WEEKS",
        "MONTH": "MONTHS",
        "MONTHS": "MONTHS",
        "月": "MONTHS",
    }
    return match.group(1), unit_map[match.group(2).upper()]


def _parse_trip_purpose(text: str) -> str | None:
    lower = text.lower()
    if "business_tourism" in lower:
        return "business_tourism"
    if ("business" in lower or "meeting" in lower or "supplier" in lower) and ("tour" in lower or "tourism" in lower or "travel" in lower):
        return "business_tourism"
    if "family_visit" in lower or "visit family" in lower or "friend" in lower:
        return "family_visit"
    if "tourism" in lower or "tour" in lower or "travel" in lower:
        return "tourism"
    if "business" in lower or "meeting" in lower or "supplier" in lower:
        return "business"
    return None


def _parse_occupation(text: str) -> str | None:
    lower = text.lower()
    if "student" in lower or "学生" in lower:
        return "STUDENT"
    if any(token in lower for token in ["businessperson", "manager", "employee", "staff", "sales", "company", "企业", "经理"]):
        return "BUSINESSPERSON"
    if "other" in lower or "其他" in lower:
        return "OTHER"
    return None


def _parse_marital_status(text: str) -> str | None:
    lower = text.lower()
    if "single" in lower or "未婚" in lower:
        return "SINGLE"
    if "married" in lower or "已婚" in lower:
        return "MARRIED"
    if "divorced" in lower or "离婚" in lower:
        return "DIVORCED"
    if "widowed" in lower or "丧偶" in lower:
        return "WIDOWED"
    return None


def _parse_yes_no(text: str | None) -> bool | None:
    if not text:
        return None
    lower = text.lower()
    if any(token in lower for token in ["yes", "是", "有"]):
        return True
    if any(token in lower for token in ["no", "否", "无"]):
        return False
    return None


def _unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
