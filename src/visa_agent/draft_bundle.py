from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from visa_agent.browser.plan import compile_browser_execution_plan
from visa_agent.mapping import map_dossier_to_ds160
from visa_agent.planner import build_execution_plan
from visa_agent.schema import ApplicantDossier, load_dossier

TOP_STEPS = [
    {"id": "complete", "label": "COMPLETE"},
    {"id": "photo", "label": "PHOTO"},
    {"id": "review", "label": "REVIEW"},
    {"id": "sign", "label": "SIGN"},
]

FLOW_STRUCTURE = [
    {"section_id": "getting_started", "label": "Getting Started", "pages": [{"page_id": "getting_started", "label": "Getting Started"}]},
    {
        "section_id": "personal",
        "label": "Personal",
        "pages": [
            {"page_id": "personal_page_1", "label": "Personal 1"},
            {"page_id": "personal_page_2", "label": "Personal 2"},
        ],
    },
    {"section_id": "travel", "label": "Travel", "pages": [{"page_id": "travel_page", "label": "Travel"}]},
    {
        "section_id": "travel_companions",
        "label": "Travel Companions",
        "pages": [{"page_id": "travel_companions_page", "label": "Travel Companions"}],
    },
    {
        "section_id": "previous_us_travel",
        "label": "Previous U.S. Travel",
        "pages": [{"page_id": "previous_us_travel_page", "label": "Previous U.S. Travel"}],
    },
    {
        "section_id": "address_phone",
        "label": "Address and Phone",
        "pages": [{"page_id": "address_phone_page", "label": "Address and Phone"}],
    },
    {"section_id": "passport", "label": "Passport", "pages": [{"page_id": "passport_page", "label": "Passport"}]},
    {"section_id": "us_contact", "label": "U.S. Contact", "pages": [{"page_id": "us_contact_page", "label": "U.S. Contact"}]},
    {"section_id": "family", "label": "Family", "pages": [{"page_id": "family_page", "label": "Family"}]},
    {
        "section_id": "work_education_training",
        "label": "Work / Education / Training",
        "pages": [{"page_id": "employment_page", "label": "Work / Education / Training"}],
    },
    {
        "section_id": "security_background",
        "label": "Security and Background",
        "pages": [{"page_id": "security_page", "label": "Security and Background"}],
    },
]

PAGE_METADATA = {
    "getting_started": {
        "save_checkpoint": None,
        "fill": [],
        "review": [],
        "blocked": [],
        "autofill_count": 0,
        "review_count": 0,
        "blocked_count": 0,
        "status": "reference",
        "notes": ["入口页，不属于正式表单字段填写。"],
    },
    "personal_page_1": {"status": "implemented"},
    "personal_page_2": {"status": "implemented"},
    "travel_page": {"status": "implemented"},
    "travel_companions_page": {"status": "implemented"},
    "previous_us_travel_page": {"status": "implemented"},
    "address_phone_page": {"status": "implemented"},
    "passport_page": {"status": "implemented"},
    "us_contact_page": {"status": "implemented"},
    "family_page": {"status": "implemented"},
    "employment_page": {"status": "implemented"},
    "security_page": {"status": "implemented"},
}


def _empty_page(page_id: str, label: str) -> dict[str, object]:
    meta = PAGE_METADATA.get(page_id, {})
    return {
        "page_id": page_id,
        "label": label,
        "save_checkpoint": meta.get("save_checkpoint"),
        "fill": list(meta.get("fill", [])),
        "review": list(meta.get("review", [])),
        "blocked": list(meta.get("blocked", [])),
        "autofill_count": int(meta.get("autofill_count", 0)),
        "review_count": int(meta.get("review_count", 0)),
        "blocked_count": int(meta.get("blocked_count", 0)),
        "status": str(meta.get("status", "planned")),
        "notes": list(meta.get("notes", [])),
    }


def build_draft_bundle(dossier: ApplicantDossier) -> dict[str, object]:
    mapped = map_dossier_to_ds160(dossier)
    execution_plan = build_execution_plan(mapped)
    browser_plan = compile_browser_execution_plan(execution_plan)

    status_counts = {"ready": 0, "needs_review": 0, "blocked": 0}
    for field in mapped:
        status_counts[field.status] = status_counts.get(field.status, 0) + 1

    resolved_pages = {}
    for page in browser_plan.pages:
        existing = PAGE_METADATA.get(page.page_id, {})
        resolved_pages[page.page_id] = {
            "page_id": page.page_id,
            "label": next(
                (
                    item["label"]
                    for section in FLOW_STRUCTURE
                    for item in section["pages"]
                    if item["page_id"] == page.page_id
                ),
                page.page_id,
            ),
            "save_checkpoint": page.save_checkpoint,
            "fill": [asdict(item) for item in page.fill],
            "review": [asdict(item) for item in page.review],
            "blocked": [asdict(item) for item in page.blocked],
            "autofill_count": len(page.fill),
            "review_count": len(page.review),
            "blocked_count": len(page.blocked),
            "status": existing.get("status", "implemented"),
            "notes": list(existing.get("notes", [])),
        }

    resolved_pages["passport_page"] = {
        "page_id": "passport_page",
        "label": "Passport",
        "save_checkpoint": None,
        "fill": [
            {
                "field_id": "passport.number",
                "proposed_value": dossier.identity.passport_number,
                "evidence_refs": dossier.identity.source_ids,
            },
            {
                "field_id": "passport.issue_date",
                "proposed_value": dossier.identity.passport_issue_date,
                "evidence_refs": dossier.identity.source_ids,
            },
            {
                "field_id": "passport.expiration_date",
                "proposed_value": dossier.identity.passport_expiration_date,
                "evidence_refs": dossier.identity.source_ids,
            },
            {
                "field_id": "passport.issuance_country",
                "proposed_value": dossier.identity.passport_issuance_country,
                "evidence_refs": dossier.identity.source_ids,
            },
        ],
        "review": [
            {
                "field_id": "passport.book_number",
                "notes": "Chinese applicants often do not have a passport book number; confirm whether DS-160 should be marked as not applicable.",
            }
        ],
        "blocked": [],
        "autofill_count": 4,
        "review_count": 1,
        "blocked_count": 0,
        "status": "implemented",
        "notes": ["护照页已建模，护照本编号默认进入人工确认。"],
    }

    resolved_pages["personal_page_2"] = {
        "page_id": "personal_page_2",
        "label": "Personal 2",
        "save_checkpoint": None,
        "fill": [
            {
                "field_id": "identity.nationality",
                "proposed_value": dossier.identity.nationality,
                "evidence_refs": dossier.identity.source_ids,
            },
            {
                "field_id": "identity.other_nationality",
                "proposed_value": "NO",
                "evidence_refs": ["mock:personal2"],
            },
            {
                "field_id": "identity.permanent_resident_other_country",
                "proposed_value": "NO",
                "evidence_refs": ["mock:personal2"],
            },
            {
                "field_id": "identity.national_id_number",
                "proposed_value": "DOES NOT APPLY",
                "evidence_refs": ["mock:personal2"],
            },
            {
                "field_id": "identity.us_social_security_number",
                "proposed_value": "DOES NOT APPLY",
                "evidence_refs": ["mock:personal2"],
            },
            {
                "field_id": "identity.us_taxpayer_id_number",
                "proposed_value": "DOES NOT APPLY",
                "evidence_refs": ["mock:personal2"],
            },
        ],
        "review": [],
        "blocked": [],
        "autofill_count": 6,
        "review_count": 0,
        "blocked_count": 0,
        "status": "implemented",
        "notes": ["Personal 2 已补齐为完整本地草稿。无历史数据时，额外国籍、美国 SSN、美国税号均按 mock 样例处理为不适用。"],
    }

    resolved_pages["us_contact_page"] = {
        "page_id": "us_contact_page",
        "label": "U.S. Contact",
        "save_checkpoint": None,
        "fill": [
            {
                "field_id": "travel.us_contact_name",
                "proposed_value": dossier.travel_plan.us_contact_name,
                "evidence_refs": dossier.travel_plan.source_ids,
            },
            {
                "field_id": "travel.us_contact_organization",
                "proposed_value": dossier.travel_plan.us_contact_organization,
                "evidence_refs": dossier.travel_plan.source_ids,
            },
            {
                "field_id": "travel.us_contact_address_line1",
                "proposed_value": dossier.travel_plan.us_contact_address_line1,
                "evidence_refs": dossier.travel_plan.source_ids,
            },
            {
                "field_id": "travel.us_contact_city",
                "proposed_value": dossier.travel_plan.us_contact_city,
                "evidence_refs": dossier.travel_plan.source_ids,
            },
            {
                "field_id": "travel.us_contact_state",
                "proposed_value": dossier.travel_plan.us_contact_state,
                "evidence_refs": dossier.travel_plan.source_ids,
            },
            {
                "field_id": "travel.us_contact_postal_code",
                "proposed_value": dossier.travel_plan.us_contact_postal_code,
                "evidence_refs": dossier.travel_plan.source_ids,
            },
        ],
        "review": [],
        "blocked": [
            {
                "field_id": "travel.us_contact_phone",
                "notes": "U.S. contact phone is missing.",
            }
        ],
        "autofill_count": 6,
        "review_count": 0,
        "blocked_count": 1,
        "status": "implemented",
        "notes": ["美国联系人页已建模，当前仍缺联系人电话。"],
    }

    resolved_pages["travel_companions_page"] = {
        "page_id": "travel_companions_page",
        "label": "Travel Companions",
        "save_checkpoint": None,
        "fill": [
            {
                "field_id": "travel_companions.has_companions",
                "proposed_value": "YES",
                "evidence_refs": ["mock:travel_companions"],
            },
            {
                "field_id": "travel_companions.primary_companion_surname",
                "proposed_value": "WANG",
                "evidence_refs": ["mock:travel_companions"],
            },
            {
                "field_id": "travel_companions.primary_companion_given_name",
                "proposed_value": "LI",
                "evidence_refs": ["mock:travel_companions"],
            },
            {
                "field_id": "travel_companions.relationship",
                "proposed_value": "SPOUSE",
                "evidence_refs": ["mock:travel_companions"],
            },
        ],
        "review": [],
        "blocked": [],
        "autofill_count": 4,
        "review_count": 0,
        "blocked_count": 0,
        "status": "implemented",
        "notes": ["Travel Companions 当前为编造样例：默认与配偶同行，用于本地应用完整演示。"],
    }

    resolved_pages["previous_us_travel_page"] = {
        "page_id": "previous_us_travel_page",
        "label": "Previous U.S. Travel",
        "save_checkpoint": None,
        "fill": [
            {
                "field_id": "previous_us_travel.has_previous_us_travel",
                "proposed_value": "YES",
                "evidence_refs": ["mock:previous_us_travel"],
            },
            {
                "field_id": "previous_us_travel.last_arrival_date",
                "proposed_value": "2024-03-10",
                "evidence_refs": ["mock:previous_us_travel"],
            },
            {
                "field_id": "previous_us_travel.last_length_of_stay",
                "proposed_value": "7 DAYS",
                "evidence_refs": ["mock:previous_us_travel"],
            },
            {
                "field_id": "previous_us_travel.has_us_visa_issued",
                "proposed_value": "YES",
                "evidence_refs": ["mock:previous_us_travel"],
            },
            {
                "field_id": "previous_us_travel.visa_number",
                "proposed_value": "000123456789",
                "evidence_refs": ["mock:previous_us_travel"],
            },
        ],
        "review": [],
        "blocked": [],
        "autofill_count": 5,
        "review_count": 0,
        "blocked_count": 0,
        "status": "implemented",
        "notes": ["Previous U.S. Travel 当前为编造样例，用于消除本地应用中的占位页。"],
    }

    resolved_pages["address_phone_page"] = {
        "page_id": "address_phone_page",
        "label": "Address and Phone",
        "save_checkpoint": None,
        "fill": [
            {
                "field_id": "address.home_address_line1",
                "proposed_value": "88 Huaihai Middle Road",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "address.city",
                "proposed_value": "Shanghai",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "address.state_province",
                "proposed_value": "Shanghai",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "address.postal_code",
                "proposed_value": "200021",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "address.country",
                "proposed_value": "CHINA",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "phone.primary_phone",
                "proposed_value": "+86-21-5555-8800",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "phone.secondary_phone",
                "proposed_value": "DOES NOT APPLY",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "phone.work_phone",
                "proposed_value": "+86-21-6888-9900",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "phone.email",
                "proposed_value": "zhang.wei@example.cn",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "social.primary_platform",
                "proposed_value": "WECHAT",
                "evidence_refs": ["mock:address_phone"],
            },
            {
                "field_id": "social.primary_handle",
                "proposed_value": "zhangwei_cn",
                "evidence_refs": ["mock:address_phone"],
            },
        ],
        "review": [],
        "blocked": [],
        "autofill_count": 11,
        "review_count": 0,
        "blocked_count": 0,
        "status": "implemented",
        "notes": ["Address and Phone 当前为编造样例，用于本地应用完整演示。"],
    }

    pages = []
    navigation = []
    for section in FLOW_STRUCTURE:
        nav_pages = []
        for item in section["pages"]:
            page = resolved_pages.get(item["page_id"], _empty_page(item["page_id"], item["label"]))
            pages.append(page)
            nav_pages.append(
                {
                    "page_id": page["page_id"],
                    "label": page["label"],
                    "status": page["status"],
                }
            )
        navigation.append(
            {
                "section_id": section["section_id"],
                "label": section["label"],
                "pages": nav_pages,
            }
        )

    return {
        "case_id": dossier.case_id,
        "summary": {
            "status_counts": status_counts,
            "page_count": len(pages),
            "hard_stops": execution_plan.hard_stops,
        },
        "top_steps": TOP_STEPS,
        "navigation": navigation,
        "pages": pages,
    }


def export_draft_bundle_file(
    dossier_path: str | Path,
    output_path: str | Path,
) -> Path:
    dossier = load_dossier(dossier_path)
    bundle = build_draft_bundle(dossier)
    output = Path(output_path)
    output.write_text(
        "window.DS160_DRAFT_BUNDLE = " + json.dumps(bundle, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    return output
