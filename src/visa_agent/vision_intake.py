from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Callable
from urllib import request

from visa_agent.intake_contract import intake_field_errors, missing_required_intake_fields, normalized_intake_payload, validate_intake_payload


@dataclass(frozen=True)
class VisionDocumentSpec:
    kind: str
    label: str
    description: str
    required: bool = True


@dataclass(frozen=True)
class VisionUploadedDocument:
    kind: str
    filename: str
    media_type: str
    base64_data: str


@dataclass(frozen=True)
class VisionDocumentReport:
    kind: str
    filename: str
    status: str
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VisionIntakeResult:
    intake_document: dict[str, object] | None
    missing_fields: list[str]
    warnings: list[str]
    documents: list[VisionDocumentReport]

    def to_dict(self) -> dict[str, object]:
        return {
            "intake_document": self.intake_document,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
            "documents": [item.to_dict() for item in self.documents],
        }


VISION_DOCUMENT_SPECS = [
    VisionDocumentSpec(
        kind="passport_bio",
        label="护照资料页",
        description="上传中国护照个人信息页清晰照片或扫描件。需要能看清英文姓名、护照号、出生地、性别、签发日期和失效日期。",
    ),
    VisionDocumentSpec(
        kind="trip_proof",
        label="赴美行程或邀请材料",
        description="上传行程单、邀请函，或一张写明赴美目的、到达日期、停留时长、费用承担方的截图。",
    ),
    VisionDocumentSpec(
        kind="us_contact_proof",
        label="美国联系人材料",
        description="上传联系人名片、邀请函页，或一张写明姓名、电话、地址、城市、州、邮编、邮箱的截图。",
    ),
    VisionDocumentSpec(
        kind="employment_proof",
        label="工作或学校材料",
        description="上传在职证明、工作名片、学校证明，或一张写明职业、单位名称、单位地址的截图。",
    ),
    VisionDocumentSpec(
        kind="family_info_sheet",
        label="家庭信息材料",
        description="上传户口本相关页、结婚证补充页，或一张写明婚姻状态、父母姓名、配偶姓名的截图。",
    ),
    VisionDocumentSpec(
        kind="security_questionnaire",
        label="安全背景问卷",
        description="上传一张写明“是否有传染病相关情况”“是否有逮捕或犯罪记录”的是/否截图或照片。",
    ),
]


class VisionModelClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("VISION_MODEL_API_KEY", "")
        self.model = model or os.environ.get("VISION_MODEL_NAME", "")
        self.base_url = (base_url or os.environ.get("VISION_MODEL_BASE_URL", "")).rstrip("/")

    def extract_fields(self, documents: list[VisionUploadedDocument], schema: dict[str, object]) -> dict[str, object]:
        if not self.api_key or not self.model or not self.base_url:
            raise RuntimeError("视觉模型未配置，请设置 VISION_MODEL_API_KEY、VISION_MODEL_NAME、VISION_MODEL_BASE_URL")
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是美国签证资料整理助手。请只根据用户上传的图片，提取并返回一个 JSON 对象。"
                        "这个对象必须只包含目标 schema 中定义的字段。"
                        "缺失或无法确认的字段不要猜测，直接填 null。"
                        "布尔字段必须返回 true 或 false。"
                    ),
                },
                {
                    "role": "user",
                    "content": self._message_content(documents, schema),
                },
            ],
        }
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=90) as resp:
            response_payload = json.loads(resp.read().decode("utf-8"))
        content = response_payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("视觉模型没有返回对象结构")
        return parsed

    def build_prompt_text(self, documents: list[VisionUploadedDocument], schema: dict[str, object]) -> str:
        doc_lines = "\n".join(f"- {document.kind}: {document.filename}" for document in documents) or "- 未选择文件"
        return (
            "你是美国签证资料整理助手。请根据我接下来上传的图片，直接返回一个 JSON 对象。\n"
            "要求：\n"
            "1. 只允许返回 schema 中定义的字段\n"
            "2. 不要输出 markdown\n"
            "3. 不要输出解释文字\n"
            "4. 缺失或无法确认的字段请填 null\n"
            "5. 布尔字段必须返回 true 或 false\n\n"
            f"这次我会上传这些材料：\n{doc_lines}\n\n"
            f"目标 schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
        )

    def _message_content(self, documents: list[VisionUploadedDocument], schema: dict[str, object]) -> list[dict[str, object]]:
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    "请把上传图片整理成 intake-v1 结构。"
                    "输出必须是一个 JSON 对象，只能包含 schema 中的字段。"
                    "禁止输出 markdown、解释文字或额外字段。\n\n"
                    f"目标 schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
                ),
            }
        ]
        for document in documents:
            content.append(
                {
                    "type": "text",
                    "text": f"文件类型: {document.kind}; 文件名: {document.filename}",
                }
            )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": document.base64_data},
                }
            )
        return content


def build_prompt_text(documents: list[VisionUploadedDocument], schema: dict[str, object]) -> str:
    return VisionModelClient().build_prompt_text(documents, schema)


def vision_document_specs() -> list[dict[str, object]]:
    return [asdict(item) for item in VISION_DOCUMENT_SPECS]


def extract_intake_from_documents(
    documents: list[VisionUploadedDocument],
    schema: dict[str, object],
    model_extractor: Callable[[list[VisionUploadedDocument], dict[str, object]], dict[str, object]] | None = None,
) -> VisionIntakeResult:
    extractor = model_extractor or VisionModelClient().extract_fields
    warnings: list[str] = []
    reports: list[VisionDocumentReport] = []
    spec_by_kind = {item.kind: item for item in VISION_DOCUMENT_SPECS}

    for spec in VISION_DOCUMENT_SPECS:
        match = next((item for item in documents if item.kind == spec.kind), None)
        if not match:
            warnings.append(f"缺少必传文件：{spec.label}")
            reports.append(
                VisionDocumentReport(
                    kind=spec.kind,
                    filename="",
                    status="missing",
                    warnings=[f"未上传 {spec.label}"],
                )
            )
        else:
            reports.append(
                VisionDocumentReport(
                    kind=spec.kind,
                    filename=match.filename,
                    status="processed",
                    warnings=[],
                )
            )

    for uploaded in documents:
        if uploaded.kind not in spec_by_kind:
            warnings.append(f"忽略未知文件类型：{uploaded.kind}")

    raw_payload = extractor(documents, schema)
    intake_document, missing_fields, validation_warnings = _build_complete_intake(raw_payload)
    warnings.extend(validation_warnings)
    return VisionIntakeResult(
        intake_document=intake_document,
        missing_fields=missing_fields,
        warnings=_unique_list(warnings),
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
    return validate_intake_payload(payload), [], []


def _unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
