"""Centralized DS-160 page definitions.

Every hardcoded selector lives here — auditable, versionable, and
separated from execution logic.  When CEAC changes a control ID,
the fix is a one-line data change, not a hunt through fill functions.

Each PageDefinition feeds into fill_engine.execute_page().
"""

from __future__ import annotations

from visa_agent.browser.page_spec import FieldBinding, FillPhase, PageDefinition
from visa_agent.schema import ApplicantDossier

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _month_abbrev(month: str) -> str:
    return {
        "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR",
        "05": "MAY", "06": "JUN", "07": "JUL", "08": "AUG",
        "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC",
    }[month]


def _sanitize_name(value: str | None) -> str:
    raw = (value or "").upper()
    cleaned = "".join(
        ch if (ch.isalnum() or ch in {"-", "'", "&", " "}) else " "
        for ch in raw
    )
    return " ".join(cleaned.split())


def _normalize_phone(phone: str | None, fallback: str = "862155558800") -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits if 5 <= len(digits) <= 15 else fallback


def _split_surname_given(full_name: str | None) -> tuple[str, str]:
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def _split_first_surname(full_name: str | None) -> tuple[str, str]:
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _visa_type_value(visa_class: str | None) -> str:
    mapping = {"B1/B2": "B", "B1": "B", "B2": "B", "F1": "F", "J1": "J", "H1B": "H"}
    if not visa_class:
        return "B"
    return mapping.get(visa_class.upper(), visa_class[0])


def _travel_purpose_value(visa_class: str | None) -> str:
    mapping = {"B1/B2": "B1-B2", "B1": "B1-CF", "B2": "B2-TM"}
    return mapping.get((visa_class or "").strip().upper(), "B1-B2")


def _occupation_label(value: str | None) -> str:
    mapping = {
        "BUSINESSPERSON": "BUSINESS", "BUSINESS": "BUSINESS",
        "ENGINEER": "ENGINEERING", "ENGINEERING": "ENGINEERING",
        "STUDENT": "STUDENT", "NOT EMPLOYED": "NOT EMPLOYED",
    }
    return mapping.get((value or "").upper(), "BUSINESS")


def _los_unit_label(unit: str | None) -> str:
    mapping = {
        "DAY": "Day(s)", "DAYS": "Day(s)",
        "WEEK": "Week(s)", "WEEKS": "Week(s)",
        "MONTH": "Month(s)", "MONTHS": "Month(s)",
        "YEAR": "Year(s)", "YEARS": "Year(s)",
    }
    return mapping.get((unit or "").strip().upper(), "Day(s)")


def _departure_date(dossier: ApplicantDossier) -> str:
    t = dossier.travel_plan
    if not (t.intended_arrival_date and t.intended_length_of_stay_value):
        return ""
    try:
        from datetime import date, timedelta
        arr = date.fromisoformat(t.intended_arrival_date)
        dep = arr + timedelta(days=int(t.intended_length_of_stay_value))
        return dep.strftime("%Y-%m-%d")
    except Exception:
        return ""


def _us_contact_relationship(dossier: ApplicantDossier) -> str:
    return "BUSINESS ASSOCIATE" if dossier.travel_plan.us_contact_organization else "OTHER"


# ---------------------------------------------------------------------------
# ASP.NET control ID prefix
# ---------------------------------------------------------------------------

_FV = "ctl00_SiteContentPlaceHolder_FormView1"

# ---------------------------------------------------------------------------
# Simple pages (lambdas only — no separate builder functions needed)
# ---------------------------------------------------------------------------

PERSONAL1 = PageDefinition(
    page_key="personal1",
    url_matchers=["node=Personal1", "Personal Information 1"],
    phases=[
        FillPhase(label="ensure", fields=[
            FieldBinding("other_names_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblOtherNames",
                         "radio_click", choice_value="N", hardcoded="N"),
            FieldBinding("telecode_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblTelecodeQuestion",
                         "radio_click", choice_value="N", hardcoded="N"),
        ]),
        FillPhase(label="fill", wait_before_ms=1000, fields=[
            FieldBinding("surname", f"#{_FV}_tbxAPP_SURNAME", "text",
                         source_path="identity.surname"),
            FieldBinding("given_names", f"#{_FV}_tbxAPP_GIVEN_NAME", "text",
                         source_path="identity.given_names"),
            FieldBinding("native_full_name", f"#{_FV}_tbxAPP_FULL_NAME_NATIVE", "text",
                         source_path="identity.native_full_name"),
            FieldBinding("native_name_na_off", f"#{_FV}_cbexAPP_FULL_NAME_NATIVE_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("sex", f"#{_FV}_ddlAPP_GENDER", "select_text",
                         source_path="identity.sex"),
            FieldBinding("marital_status", f"#{_FV}_ddlAPP_MARITAL_STATUS", "select_text",
                         source_path="identity.marital_status"),
            FieldBinding("dob_day", f"#{_FV}_ddlDOBDay", "select_text",
                         resolver=lambda d: d.identity.date_of_birth[8:10] if d.identity.date_of_birth else None),
            FieldBinding("dob_month", f"#{_FV}_ddlDOBMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.identity.date_of_birth[5:7]) if d.identity.date_of_birth else None),
            FieldBinding("dob_year", f"#{_FV}_tbxDOBYear", "text",
                         resolver=lambda d: d.identity.date_of_birth[0:4] if d.identity.date_of_birth else None),
            FieldBinding("birth_city", f"#{_FV}_tbxAPP_POB_CITY", "text",
                         source_path="identity.birth_city"),
            FieldBinding("birth_province", f"#{_FV}_tbxAPP_POB_ST_PROVINCE", "text",
                         source_path="identity.birth_province"),
            FieldBinding("birth_province_na_off", f"#{_FV}_cbexAPP_POB_ST_PROVINCE_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("birth_country", f"#{_FV}_ddlAPP_POB_CNTRY", "select_text",
                         source_path="identity.birth_country"),
        ]),
    ],
)

PERSONAL2 = PageDefinition(
    page_key="personal2",
    url_matchers=["node=Personal2", "Personal Information 2"],
    phases=[
        FillPhase(label="ensure", fields=[
            FieldBinding("other_nationality_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblAPP_OTH_NATL_IND",
                         "radio_click", choice_value="N", hardcoded="N"),
            FieldBinding("perm_res_other_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPermResOtherCntryInd",
                         "radio_click", choice_value="N", hardcoded="N"),
        ]),
        FillPhase(label="fill", wait_before_ms=1000, fields=[
            FieldBinding("nationality", f"#{_FV}_ddlAPP_NATL", "select_text",
                         source_path="identity.nationality"),
            FieldBinding("national_id_na", f"#{_FV}_cbexAPP_NATIONAL_ID_NA",
                         "checkbox", hardcoded=True),
            FieldBinding("ssn_na", f"#{_FV}_cbexAPP_SSN_NA", "checkbox", hardcoded=True),
            FieldBinding("tax_id_na", f"#{_FV}_cbexAPP_TAX_ID_NA", "checkbox", hardcoded=True),
        ]),
    ],
)

PASSPORT = PageDefinition(
    page_key="passport",
    url_matchers=["node=PptVisa", "node=PassportType", "Passport Information"],
    phases=[
        FillPhase(label="fill", fields=[
            FieldBinding("passport_type", f"#{_FV}_ddlPPT_TYPE", "select_text",
                         hardcoded="REGULAR"),
            FieldBinding("passport_number", f"#{_FV}_tbxPPT_NUM", "text",
                         source_path="identity.passport_number"),
            FieldBinding("book_no_na", f"#{_FV}_cbexPPT_BOOK_NUM_NA", "checkbox",
                         hardcoded=True),
            FieldBinding("passport_issued_country", f"#{_FV}_ddlPPT_ISSUED_CNTRY",
                         "select_text", source_path="identity.passport_issuance_country"),
            FieldBinding("passport_issue_city", f"#{_FV}_tbxPPT_ISSUED_IN_CITY", "text",
                         source_path="identity.birth_city"),
            FieldBinding("passport_issue_state", f"#{_FV}_tbxPPT_ISSUED_IN_STATE", "text",
                         source_path="identity.birth_province"),
            FieldBinding("passport_issue_country_region", f"#{_FV}_ddlPPT_ISSUED_IN_CNTRY",
                         "select_text", source_path="identity.passport_issuance_country"),
            FieldBinding("issue_day", f"#{_FV}_ddlPPT_ISSUED_DTEDay", "select_text",
                         resolver=lambda d: d.identity.passport_issue_date[8:10] if d.identity.passport_issue_date else None),
            FieldBinding("issue_month", f"#{_FV}_ddlPPT_ISSUED_DTEMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.identity.passport_issue_date[5:7]) if d.identity.passport_issue_date else None),
            FieldBinding("issue_year", f"#{_FV}_tbxPPT_ISSUEDYear", "text",
                         resolver=lambda d: d.identity.passport_issue_date[0:4] if d.identity.passport_issue_date else None),
            FieldBinding("expiry_na_off", f"#{_FV}_cbxPPT_EXPIRE_NA", "checkbox",
                         hardcoded=False),
            FieldBinding("expiry_day", f"#{_FV}_ddlPPT_EXPIRE_DTEDay", "select_text",
                         resolver=lambda d: d.identity.passport_expiration_date[8:10] if d.identity.passport_expiration_date else None),
            FieldBinding("expiry_month", f"#{_FV}_ddlPPT_EXPIRE_DTEMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.identity.passport_expiration_date[5:7]) if d.identity.passport_expiration_date else None),
            FieldBinding("expiry_year", f"#{_FV}_tbxPPT_EXPIREYear", "text",
                         resolver=lambda d: d.identity.passport_expiration_date[0:4] if d.identity.passport_expiration_date else None),
            FieldBinding("lost_passport_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblLOST_PPT_IND",
                         "radio", choice_value="N", hardcoded="N"),
        ]),
    ],
)

TRAVEL = PageDefinition(
    page_key="travel",
    url_matchers=["node=Travel", "Travel Information"],
    phases=[
        FillPhase(label="ensure_specific_travel", fields=[
            FieldBinding("specific_travel_yes",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblSpecificTravel",
                         "radio_click", choice_value="Y", hardcoded="Y",
                         wait_selector_after=f"#{_FV}_ddlARRIVAL_US_DTEDay"),
        ]),
        FillPhase(label="ensure_visa_type", wait_before_ms=1000, fields=[
            FieldBinding("visa_type",
                         f"#{_FV}_dlPrincipalAppTravel_ctl00_ddlPurposeOfTrip",
                         "select_value",
                         resolver=lambda d: _visa_type_value(d.travel_plan.visa_class),
                         wait_selector_after=f"#{_FV}_dlPrincipalAppTravel_ctl00_ddlOtherPurpose"),
        ]),
        FillPhase(label="fill", wait_before_ms=1000, fields=[
            FieldBinding("purpose_specify",
                         f"#{_FV}_dlPrincipalAppTravel_ctl00_ddlOtherPurpose",
                         "select_value",
                         resolver=lambda d: _travel_purpose_value(d.travel_plan.visa_class)),
            FieldBinding("arrival_day", f"#{_FV}_ddlARRIVAL_US_DTEDay", "select_text",
                         resolver=lambda d: d.travel_plan.intended_arrival_date[8:10].lstrip("0") or d.travel_plan.intended_arrival_date[8:10] if d.travel_plan.intended_arrival_date else None),
            FieldBinding("arrival_month", f"#{_FV}_ddlARRIVAL_US_DTEMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.travel_plan.intended_arrival_date[5:7]) if d.travel_plan.intended_arrival_date else None),
            FieldBinding("arrival_year", f"#{_FV}_tbxARRIVAL_US_DTEYear", "text",
                         resolver=lambda d: d.travel_plan.intended_arrival_date[0:4] if d.travel_plan.intended_arrival_date else None),
            FieldBinding("departure_day", f"#{_FV}_ddlDEPARTURE_US_DTEDay", "select_text",
                         resolver=lambda d: (_dp := _departure_date(d)) and (_dp[8:10].lstrip("0") or _dp[8:10]) or None),
            FieldBinding("departure_month", f"#{_FV}_ddlDEPARTURE_US_DTEMonth", "select_text",
                         resolver=lambda d: (_dp := _departure_date(d)) and _month_abbrev(_dp[5:7]) or None),
            FieldBinding("departure_year", f"#{_FV}_tbxDEPARTURE_US_DTEYear", "text",
                         resolver=lambda d: (_dp := _departure_date(d)) and _dp[0:4] or None),
            FieldBinding("arrive_city", f"#{_FV}_tbxArriveCity", "text",
                         source_path="travel_plan.us_contact_city"),
            FieldBinding("depart_city", f"#{_FV}_tbxDepartCity", "text",
                         source_path="travel_plan.us_contact_city"),
            FieldBinding("travel_location",
                         f"#{_FV}_dtlTravelLoc_ctl00_tbxSPECTRAVEL_LOCATION", "text",
                         resolver=lambda d: ", ".join(filter(None, [d.travel_plan.us_contact_city, d.travel_plan.us_contact_state]))),
            FieldBinding("us_addr1", f"#{_FV}_tbxStreetAddress1", "text",
                         source_path="travel_plan.us_contact_address_line1"),
            FieldBinding("us_city", f"#{_FV}_tbxCity", "text",
                         source_path="travel_plan.us_contact_city"),
            FieldBinding("us_state", f"#{_FV}_ddlTravelState", "select_text",
                         source_path="travel_plan.us_contact_state"),
            FieldBinding("us_zip", f"#{_FV}_tbZIPCode", "text",
                         source_path="travel_plan.us_contact_postal_code"),
            FieldBinding("payer", f"#{_FV}_ddlWhoIsPaying", "select_value",
                         resolver=lambda d: "P" if d.travel_plan.payer_name else "S"),
        ]),
    ],
)

TRAVEL_COMPANIONS = PageDefinition(
    page_key="travel_companions",
    url_matchers=["node=TravelCompanions", "Travel Companions"],
    phases=[
        FillPhase(label="fill", fields=[
            FieldBinding("no_companions",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblOtherPersonsTravelingWithYou",
                         "radio_click", choice_value="N", hardcoded="N"),
        ]),
    ],
)

# ---------------------------------------------------------------------------
# Complex page builders
# ---------------------------------------------------------------------------


def _build_previous_travel_phases() -> list[FillPhase]:
    def _has_prev_travel(d: ApplicantDossier) -> bool:
        return bool(d.previous_travel and d.previous_travel.has_previous_us_travel)

    def _has_prev_visa(d: ApplicantDossier) -> bool:
        return bool(d.previous_travel and d.previous_travel.has_previous_us_visa)

    def _prev_arrival_date(d: ApplicantDossier) -> str | None:
        p = d.previous_travel
        return p.last_arrival_date if p else None

    def _prev_visa_date(d: ApplicantDossier) -> str | None:
        p = d.previous_travel
        return p.previous_visa_issue_date if p else None

    def _yes_no(d: ApplicantDossier, key: str) -> str:
        p = d.previous_travel
        if p is None:
            return "N"
        return "Y" if getattr(p, key, False) else "N"

    return [
        FillPhase(label="ensure_prev_travel", fields=[
            FieldBinding("prev_us_travel",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_US_TRAVEL_IND",
                         "radio_click",
                         resolver=lambda d: "Y" if (d.previous_travel and d.previous_travel.has_previous_us_travel) else "N",
                         wait_selector_after=f"#{_FV}_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_DTEDay"),
        ]),
        FillPhase(label="ensure_prev_visa", wait_before_ms=1000, fields=[
            FieldBinding("prev_visa",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_IND",
                         "radio_click",
                         resolver=lambda d: "Y" if (d.previous_travel and d.previous_travel.has_previous_us_visa) else "N",
                         wait_selector_after=f"#{_FV}_ddlPREV_VISA_ISSUED_DTEDay"),
        ]),
        FillPhase(label="fill", wait_before_ms=1000, fields=[
            FieldBinding("prev_visit_day",
                         f"#{_FV}_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_DTEDay",
                         "select_text",
                         resolver=lambda d: _prev_arrival_date(d) and (_prev_arrival_date(d)[8:10].lstrip("0") or _prev_arrival_date(d)[8:10]),
                         condition=_has_prev_travel),
            FieldBinding("prev_visit_month",
                         f"#{_FV}_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_DTEMonth",
                         "select_text",
                         resolver=lambda d: _prev_arrival_date(d) and _month_abbrev(_prev_arrival_date(d)[5:7]),
                         condition=_has_prev_travel),
            FieldBinding("prev_visit_year",
                         f"#{_FV}_dtlPREV_US_VISIT_ctl00_tbxPREV_US_VISIT_DTEYear",
                         "text",
                         resolver=lambda d: _prev_arrival_date(d) and _prev_arrival_date(d)[0:4],
                         condition=_has_prev_travel),
            FieldBinding("prev_los_value",
                         f"#{_FV}_dtlPREV_US_VISIT_ctl00_tbxPREV_US_VISIT_LOS",
                         "text",
                         resolver=lambda d: d.previous_travel.last_length_of_stay_value if d.previous_travel else None,
                         condition=_has_prev_travel),
            FieldBinding("prev_los_unit",
                         f"#{_FV}_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_LOS_CD",
                         "select_text",
                         resolver=lambda d: _los_unit_label(d.previous_travel.last_length_of_stay_unit) if d.previous_travel else None,
                         condition=_has_prev_travel),
            FieldBinding("driver_lic",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_US_DRIVER_LIC_IND",
                         "radio_click",
                         resolver=lambda d: _yes_no(d, "has_us_driver_license"),
                         condition=_has_prev_travel),
            # Previous visa detail fields
            FieldBinding("prev_visa_day",
                         f"#{_FV}_ddlPREV_VISA_ISSUED_DTEDay",
                         "select_text",
                         resolver=lambda d: _prev_visa_date(d) and (_prev_visa_date(d)[8:10].lstrip("0") or _prev_visa_date(d)[8:10]),
                         condition=_has_prev_visa),
            FieldBinding("prev_visa_month",
                         f"#{_FV}_ddlPREV_VISA_ISSUED_DTEMonth",
                         "select_text",
                         resolver=lambda d: _prev_visa_date(d) and _month_abbrev(_prev_visa_date(d)[5:7]),
                         condition=_has_prev_visa),
            FieldBinding("prev_visa_year",
                         f"#{_FV}_tbxPREV_VISA_ISSUED_DTEYear",
                         "text",
                         resolver=lambda d: _prev_visa_date(d) and _prev_visa_date(d)[0:4],
                         condition=_has_prev_visa),
            FieldBinding("foil_na", f"#{_FV}_cbxPREV_VISA_FOIL_NUMBER_NA",
                         "checkbox", hardcoded=True, condition=_has_prev_visa),
            FieldBinding("same_type_yes",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_SAME_TYPE_IND",
                         "radio", choice_value="Y", hardcoded="Y",
                         condition=_has_prev_visa),
            FieldBinding("same_country_yes",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_SAME_CNTRY_IND",
                         "radio", choice_value="Y", hardcoded="Y",
                         condition=_has_prev_visa),
            FieldBinding("ten_print",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_TEN_PRINT_IND",
                         "radio_click",
                         resolver=lambda d: _yes_no(d, "ten_print_collected"),
                         condition=_has_prev_visa),
            FieldBinding("visa_lost",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_LOST_IND",
                         "radio_click",
                         resolver=lambda d: _yes_no(d, "visa_ever_lost"),
                         condition=_has_prev_visa),
            FieldBinding("visa_cancelled",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_CANCELLED_IND",
                         "radio_click",
                         resolver=lambda d: _yes_no(d, "visa_ever_cancelled"),
                         condition=_has_prev_visa),
            # Always-filled fields
            FieldBinding("prev_visa_refused",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_REFUSED_IND",
                         "radio",
                         resolver=lambda d: _yes_no(d, "visa_ever_refused")),
            FieldBinding("iv_petition",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblIV_PETITION_IND",
                         "radio",
                         resolver=lambda d: _yes_no(d, "has_immigrant_petition")),
        ]),
    ]


def _build_address_phone_phases() -> list[FillPhase]:
    def _pc(d: ApplicantDossier, attr: str, fallback: str = "") -> str:
        c = d.personal_contact
        if c is None:
            return fallback
        return getattr(c, attr, fallback) or fallback

    def _has_contact(d: ApplicantDossier) -> bool:
        c = d.personal_contact
        return c is not None and bool(c.home_address_line1)

    return [
        FillPhase(label="fill", fields=[
            FieldBinding("home_addr1", f"#{_FV}_tbxAPP_ADDR_LN1", "text",
                         resolver=lambda d: _pc(d, "home_address_line1"),
                         condition=_has_contact),
            FieldBinding("home_addr2", f"#{_FV}_tbxAPP_ADDR_LN2", "text",
                         resolver=lambda d: _pc(d, "home_address_line2"),
                         condition=_has_contact),
            FieldBinding("home_city", f"#{_FV}_tbxAPP_ADDR_CITY", "text",
                         resolver=lambda d: _pc(d, "home_city"), condition=_has_contact),
            FieldBinding("home_state", f"#{_FV}_tbxAPP_ADDR_STATE", "text",
                         resolver=lambda d: _pc(d, "home_state"), condition=_has_contact),
            FieldBinding("home_state_na_off", f"#{_FV}_cbexAPP_ADDR_STATE_NA",
                         "checkbox", hardcoded=False, condition=_has_contact),
            FieldBinding("home_postal", f"#{_FV}_tbxAPP_ADDR_POSTAL_CD", "text",
                         resolver=lambda d: _pc(d, "home_postal_code"),
                         condition=_has_contact),
            FieldBinding("home_postal_na_off", f"#{_FV}_cbexAPP_ADDR_POSTAL_CD_NA",
                         "checkbox", hardcoded=False, condition=_has_contact),
            FieldBinding("home_country", f"#{_FV}_ddlCountry", "select_text",
                         resolver=lambda d: _pc(d, "home_country", d.identity.birth_country or "CHINA"),
                         condition=_has_contact),
            FieldBinding("mailing_same_yes",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblMailingAddrSame",
                         "radio", choice_value="Y", hardcoded="Y",
                         condition=_has_contact),
            FieldBinding("primary_phone", f"#{_FV}_tbxAPP_HOME_TEL", "text",
                         resolver=lambda d: _normalize_phone(_pc(d, "primary_phone", ""), ""),
                         condition=_has_contact),
            FieldBinding("secondary_phone_na", f"#{_FV}_cbexAPP_MOBILE_TEL_NA",
                         "checkbox", hardcoded=True, condition=_has_contact),
            FieldBinding("work_phone", f"#{_FV}_tbxAPP_BUS_TEL", "text",
                         resolver=lambda d: _normalize_phone(_pc(d, "work_phone", ""), ""),
                         condition=_has_contact),
            FieldBinding("work_phone_na_off", f"#{_FV}_cbexAPP_BUS_TEL_NA",
                         "checkbox", hardcoded=False, condition=_has_contact),
            FieldBinding("other_phone_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblAddPhone",
                         "radio", choice_value="N", hardcoded="N",
                         condition=_has_contact),
            FieldBinding("email", f"#{_FV}_tbxAPP_EMAIL_ADDR", "text",
                         resolver=lambda d: _pc(d, "email"), condition=_has_contact),
            FieldBinding("other_email_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblAddEmail",
                         "radio", choice_value="N", hardcoded="N",
                         condition=_has_contact),
            FieldBinding("social_none",
                         f"#{_FV}_dtlSocial_ctl00_ddlSocialMedia", "select_text",
                         hardcoded="NONE", condition=_has_contact),
            FieldBinding("social_ident",
                         f"#{_FV}_dtlSocial_ctl00_tbxSocialMediaIdent", "text",
                         hardcoded="", condition=_has_contact),
            FieldBinding("other_platform_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblAddSocial",
                         "radio", choice_value="N", hardcoded="N",
                         condition=_has_contact),
            # Verify key fields
            FieldBinding("verify_home_addr1", f"#{_FV}_tbxAPP_ADDR_LN1", "text",
                         verify=True, verify_selector=f"#{_FV}_tbxAPP_ADDR_LN1",
                         resolver=lambda d: _pc(d, "home_address_line1"),
                         condition=_has_contact),
            FieldBinding("verify_home_city", f"#{_FV}_tbxAPP_ADDR_CITY", "text",
                         verify=True, verify_selector=f"#{_FV}_tbxAPP_ADDR_CITY",
                         resolver=lambda d: _pc(d, "home_city"), condition=_has_contact),
            FieldBinding("verify_email", f"#{_FV}_tbxAPP_EMAIL_ADDR", "text",
                         verify=True, verify_selector=f"#{_FV}_tbxAPP_EMAIL_ADDR",
                         resolver=lambda d: _pc(d, "email"), condition=_has_contact),
        ]),
    ]


def _build_us_contact_phases() -> list[FillPhase]:
    return [
        FillPhase(label="ensure", fields=[
            FieldBinding("contact_name_known", f"#{_FV}_cbxUS_POC_NAME_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("contact_org_known", f"#{_FV}_cbxUS_POC_ORG_NA_IND",
                         "checkbox", hardcoded=False),
            FieldBinding("contact_relationship", f"#{_FV}_ddlUS_POC_REL_TO_APP",
                         "select_text",
                         resolver=lambda d: _us_contact_relationship(d)),
        ]),
        FillPhase(label="fill", wait_before_ms=1500, fields=[
            FieldBinding("contact_surname", f"#{_FV}_tbxUS_POC_SURNAME", "text",
                         resolver=lambda d: _split_surname_given(d.travel_plan.us_contact_name)[0]),
            FieldBinding("contact_given_names", f"#{_FV}_tbxUS_POC_GIVEN_NAME", "text",
                         resolver=lambda d: _split_surname_given(d.travel_plan.us_contact_name)[1]),
            FieldBinding("contact_organization", f"#{_FV}_tbxUS_POC_ORGANIZATION", "text",
                         source_path="travel_plan.us_contact_organization"),
            FieldBinding("contact_addr1", f"#{_FV}_tbxUS_POC_ADDR_LN1", "text",
                         source_path="travel_plan.us_contact_address_line1"),
            FieldBinding("contact_addr2", f"#{_FV}_tbxUS_POC_ADDR_LN2", "text",
                         hardcoded=""),
            FieldBinding("contact_city", f"#{_FV}_tbxUS_POC_ADDR_CITY", "text",
                         source_path="travel_plan.us_contact_city"),
            FieldBinding("contact_state", f"#{_FV}_ddlUS_POC_ADDR_STATE", "select_text",
                         resolver=lambda d: (d.travel_plan.us_contact_state or "").upper()),
            FieldBinding("contact_postal", f"#{_FV}_tbxUS_POC_ADDR_POSTAL_CD", "text",
                         source_path="travel_plan.us_contact_postal_code"),
            FieldBinding("contact_phone", f"#{_FV}_tbxUS_POC_HOME_TEL", "text",
                         resolver=lambda d: _normalize_phone(d.travel_plan.us_contact_phone, "4155550100")),
            FieldBinding("contact_email_na_off", f"#{_FV}_cbexUS_POC_EMAIL_ADDR_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("contact_email", f"#{_FV}_tbxUS_POC_EMAIL_ADDR", "text",
                         source_path="travel_plan.us_contact_email"),
        ]),
    ]


def _build_work_education_present_phases() -> list[FillPhase]:
    def _emp_date(d: ApplicantDossier, part: str) -> str | None:
        dt = d.employment_education.current_employment_start_date
        if not dt:
            return None
        if part == "day":
            return dt[8:10].lstrip("0") or dt[8:10]
        if part == "month":
            return _month_abbrev(dt[5:7])
        return dt[0:4]

    return [
        FillPhase(label="ensure_occupation", fields=[
            FieldBinding("occupation", f"#{_FV}_ddlPresentOccupation",
                         "select_text",
                         resolver=lambda d: _occupation_label(d.employment_education.primary_occupation),
                         wait_selector_after=f"#{_FV}_tbxEmpSchName"),
        ]),
        FillPhase(label="fill", wait_before_ms=2500, fields=[
            FieldBinding("employer_name", f"#{_FV}_tbxEmpSchName", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.current_employer_name)),
            FieldBinding("employer_addr1", f"#{_FV}_tbxEmpSchAddr1", "text",
                         resolver=lambda d: d.employment_education.current_employer_address or ""),
            FieldBinding("employer_addr2", f"#{_FV}_tbxEmpSchAddr2", "text",
                         hardcoded=""),
            FieldBinding("employer_city", f"#{_FV}_tbxEmpSchCity", "text",
                         resolver=lambda d: d.employment_education.employer_city or ""),
            FieldBinding("employer_state_na_off", f"#{_FV}_cbxWORK_EDUC_ADDR_STATE_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("employer_state", f"#{_FV}_tbxWORK_EDUC_ADDR_STATE", "text",
                         resolver=lambda d: d.employment_education.employer_state or ""),
            FieldBinding("employer_postal_na_off", f"#{_FV}_cbxWORK_EDUC_ADDR_POSTAL_CD_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("employer_postal", f"#{_FV}_tbxWORK_EDUC_ADDR_POSTAL_CD", "text",
                         resolver=lambda d: d.employment_education.employer_postal_code or ""),
            FieldBinding("employer_phone", f"#{_FV}_tbxWORK_EDUC_TEL", "text",
                         resolver=lambda d: _normalize_phone(d.employment_education.employer_phone, "")),
            FieldBinding("employer_country", f"#{_FV}_ddlEmpSchCountry", "select_text",
                         resolver=lambda d: d.employment_education.employer_country or d.identity.birth_country or "CHINA"),
            FieldBinding("start_day", f"#{_FV}_ddlEmpDateFromDay", "select_text",
                         resolver=lambda d: _emp_date(d, "day")),
            FieldBinding("start_month", f"#{_FV}_ddlEmpDateFromMonth", "select_text",
                         resolver=lambda d: _emp_date(d, "month")),
            FieldBinding("start_year", f"#{_FV}_tbxEmpDateFromYear", "text",
                         resolver=lambda d: _emp_date(d, "year")),
            FieldBinding("salary_na_off", f"#{_FV}_cbxCURR_MONTHLY_SALARY_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("monthly_income", f"#{_FV}_tbxCURR_MONTHLY_SALARY", "text",
                         source_path="employment_education.monthly_income_local"),
            FieldBinding("duties", f"#{_FV}_tbxDescribeDuties", "text",
                         resolver=lambda d: d.employment_education.current_job_duties or ""),
        ]),
    ]


def _build_work_education_previous_phases() -> list[FillPhase]:
    def _has_prev_employer(d: ApplicantDossier) -> bool:
        e = d.employment_education
        return bool(e.previous_employer_name)

    def _has_education(d: ApplicantDossier) -> bool:
        e = d.employment_education
        return bool(e.school_name)

    def _date_part(val: str | None, part: str) -> str | None:
        if not val:
            return None
        if part == "day":
            return val[8:10].lstrip("0") or val[8:10]
        if part == "month":
            return _month_abbrev(val[5:7])
        return val[0:4]

    return [
        FillPhase(label="ensure_prev_employer", fields=[
            FieldBinding("previously_employed_yes",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblPreviouslyEmployed",
                         "radio_click", choice_value="Y", hardcoded="Y"),
        ]),
        FillPhase(label="ensure_education", wait_before_ms=1000, fields=[
            FieldBinding("other_education_yes",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblOtherEduc",
                         "radio_click", choice_value="Y", hardcoded="Y"),
        ]),
        FillPhase(label="fill", wait_before_ms=1000, fields=[
            # Previous employer fields
            FieldBinding("prev_employer_name",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbEmployerName", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.previous_employer_name),
                         condition=_has_prev_employer),
            FieldBinding("prev_employer_addr1",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbEmployerStreetAddress1", "text",
                         resolver=lambda d: d.employment_education.previous_employer_address or "",
                         condition=_has_prev_employer),
            FieldBinding("prev_employer_addr2",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbEmployerStreetAddress2", "text",
                         hardcoded="", condition=_has_prev_employer),
            FieldBinding("prev_employer_city",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbEmployerCity", "text",
                         resolver=lambda d: d.employment_education.previous_employer_city or "",
                         condition=_has_prev_employer),
            FieldBinding("prev_employer_state_na_off",
                         f"#{_FV}_dtlPrevEmpl_ctl00_cbxPREV_EMPL_ADDR_STATE_NA",
                         "checkbox", hardcoded=False, condition=_has_prev_employer),
            FieldBinding("prev_employer_state",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbxPREV_EMPL_ADDR_STATE", "text",
                         resolver=lambda d: d.employment_education.previous_employer_state or "",
                         condition=_has_prev_employer),
            FieldBinding("prev_employer_postal_na_off",
                         f"#{_FV}_dtlPrevEmpl_ctl00_cbxPREV_EMPL_ADDR_POSTAL_CD_NA",
                         "checkbox", hardcoded=False, condition=_has_prev_employer),
            FieldBinding("prev_employer_postal",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbxPREV_EMPL_ADDR_POSTAL_CD", "text",
                         resolver=lambda d: d.employment_education.previous_employer_postal_code or "",
                         condition=_has_prev_employer),
            FieldBinding("prev_employer_country",
                         f"#{_FV}_dtlPrevEmpl_ctl00_DropDownList2", "select_text",
                         resolver=lambda d: d.employment_education.previous_employer_country or d.identity.birth_country or "CHINA",
                         condition=_has_prev_employer),
            FieldBinding("prev_employer_phone",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbEmployerPhone", "text",
                         resolver=lambda d: _normalize_phone(d.employment_education.previous_employer_phone, ""),
                         condition=_has_prev_employer),
            FieldBinding("prev_job_title",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbJobTitle", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.previous_job_title),
                         condition=_has_prev_employer),
            FieldBinding("prev_supervisor_surname_known",
                         f"#{_FV}_dtlPrevEmpl_ctl00_cbxSupervisorSurname_NA",
                         "checkbox", hardcoded=False, condition=_has_prev_employer),
            FieldBinding("prev_supervisor_given_known",
                         f"#{_FV}_dtlPrevEmpl_ctl00_cbxSupervisorGivenName_NA",
                         "checkbox", hardcoded=False, condition=_has_prev_employer),
            FieldBinding("prev_supervisor_surname",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbSupervisorSurname", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.previous_supervisor_surname),
                         condition=_has_prev_employer),
            FieldBinding("prev_supervisor_given",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbSupervisorGivenName", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.previous_supervisor_given_name),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_from_day",
                         f"#{_FV}_dtlPrevEmpl_ctl00_ddlEmpDateFromDay", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.previous_employment_start_date, "day"),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_from_month",
                         f"#{_FV}_dtlPrevEmpl_ctl00_ddlEmpDateFromMonth", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.previous_employment_start_date, "month"),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_from_year",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbxEmpDateFromYear", "text",
                         resolver=lambda d: _date_part(d.employment_education.previous_employment_start_date, "year"),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_to_day",
                         f"#{_FV}_dtlPrevEmpl_ctl00_ddlEmpDateToDay", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.previous_employment_end_date, "day"),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_to_month",
                         f"#{_FV}_dtlPrevEmpl_ctl00_ddlEmpDateToMonth", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.previous_employment_end_date, "month"),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_to_year",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbxEmpDateToYear", "text",
                         resolver=lambda d: _date_part(d.employment_education.previous_employment_end_date, "year"),
                         condition=_has_prev_employer),
            FieldBinding("prev_emp_duties",
                         f"#{_FV}_dtlPrevEmpl_ctl00_tbDescribeDuties", "text",
                         resolver=lambda d: d.employment_education.previous_job_duties or "",
                         condition=_has_prev_employer),
            # Education fields
            FieldBinding("school_name",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolName", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.school_name),
                         condition=_has_education),
            FieldBinding("school_addr1",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolAddr1", "text",
                         resolver=lambda d: d.employment_education.school_address_line1 or "",
                         condition=_has_education),
            FieldBinding("school_addr2",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolAddr2", "text",
                         hardcoded="", condition=_has_education),
            FieldBinding("school_city",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolCity", "text",
                         resolver=lambda d: d.employment_education.school_city or "",
                         condition=_has_education),
            FieldBinding("school_state_na_off",
                         f"#{_FV}_dtlPrevEduc_ctl00_cbxEDUC_INST_ADDR_STATE_NA",
                         "checkbox", hardcoded=False, condition=_has_education),
            FieldBinding("school_state",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxEDUC_INST_ADDR_STATE", "text",
                         resolver=lambda d: d.employment_education.school_state or "",
                         condition=_has_education),
            FieldBinding("school_postal_na_off",
                         f"#{_FV}_dtlPrevEduc_ctl00_cbxEDUC_INST_POSTAL_CD_NA",
                         "checkbox", hardcoded=False, condition=_has_education),
            FieldBinding("school_postal",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxEDUC_INST_POSTAL_CD", "text",
                         resolver=lambda d: d.employment_education.school_postal_code or "",
                         condition=_has_education),
            FieldBinding("school_country",
                         f"#{_FV}_dtlPrevEduc_ctl00_ddlSchoolCountry", "select_text",
                         resolver=lambda d: d.employment_education.school_country or d.identity.birth_country or "CHINA",
                         condition=_has_education),
            FieldBinding("school_course",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolCourseOfStudy", "text",
                         resolver=lambda d: _sanitize_name(d.employment_education.major_or_course_of_study),
                         condition=_has_education),
            FieldBinding("school_from_day",
                         f"#{_FV}_dtlPrevEduc_ctl00_ddlSchoolFromDay", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.school_attendance_start_date, "day"),
                         condition=_has_education),
            FieldBinding("school_from_month",
                         f"#{_FV}_dtlPrevEduc_ctl00_ddlSchoolFromMonth", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.school_attendance_start_date, "month"),
                         condition=_has_education),
            FieldBinding("school_from_year",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolFromYear", "text",
                         resolver=lambda d: _date_part(d.employment_education.school_attendance_start_date, "year"),
                         condition=_has_education),
            FieldBinding("school_to_day",
                         f"#{_FV}_dtlPrevEduc_ctl00_ddlSchoolToDay", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.school_attendance_end_date, "day"),
                         condition=_has_education),
            FieldBinding("school_to_month",
                         f"#{_FV}_dtlPrevEduc_ctl00_ddlSchoolToMonth", "select_text",
                         resolver=lambda d: _date_part(d.employment_education.school_attendance_end_date, "month"),
                         condition=_has_education),
            FieldBinding("school_to_year",
                         f"#{_FV}_dtlPrevEduc_ctl00_tbxSchoolToYear", "text",
                         resolver=lambda d: _date_part(d.employment_education.school_attendance_end_date, "year"),
                         condition=_has_education),
        ]),
    ]


def _build_work_education_additional_phases() -> list[FillPhase]:
    staged_radios = [
        ("clan_tribe_yes", "ctl00$SiteContentPlaceHolder$FormView1$rblCLAN_TRIBE_IND"),
        ("countries_visited_yes", "ctl00$SiteContentPlaceHolder$FormView1$rblCOUNTRIES_VISITED_IND"),
        ("organization_yes", "ctl00$SiteContentPlaceHolder$FormView1$rblORGANIZATION_IND"),
        ("specialized_skills_yes", "ctl00$SiteContentPlaceHolder$FormView1$rblSPECIALIZED_SKILLS_IND"),
        ("military_service_yes", "ctl00$SiteContentPlaceHolder$FormView1$rblMILITARY_SERVICE_IND"),
        ("insurgent_org_yes", "ctl00$SiteContentPlaceHolder$FormView1$rblINSURGENT_ORG_IND"),
    ]

    def _date_part(val: str | None, part: str) -> str | None:
        if not val:
            return None
        if part == "day":
            return val[8:10].lstrip("0") or val[8:10]
        if part == "month":
            return _month_abbrev(val[5:7])
        return val[0:4]

    phases: list[FillPhase] = []
    for field_id, radio_name in staged_radios:
        phases.append(FillPhase(
            label=f"staged_{field_id}",
            wait_before_ms=1000,
            fields=[FieldBinding(field_id, radio_name, "radio_click",
                                 choice_value="Y", hardcoded="Y")],
        ))

    phases.append(FillPhase(label="fill_details", wait_before_ms=1000, fields=[
        FieldBinding("clan_name", f"#{_FV}_tbxCLAN_TRIBE_NAME", "text",
                     resolver=lambda d: d.employment_education.clan_or_tribe_name or ""),
        FieldBinding("language_name", f"#{_FV}_dtlLANGUAGES_ctl00_tbxLANGUAGE_NAME", "text",
                     resolver=lambda d: d.employment_education.languages or ""),
        FieldBinding("country_visited", f"#{_FV}_dtlCountriesVisited_ctl00_ddlCOUNTRIES_VISITED",
                     "select_text",
                     resolver=lambda d: d.employment_education.countries_visited or ""),
        FieldBinding("organization_name", f"#{_FV}_dtlORGANIZATIONS_ctl00_tbxORGANIZATION_NAME",
                     "text",
                     resolver=lambda d: d.employment_education.organization_memberships or ""),
        FieldBinding("specialized_skills_expl", f"#{_FV}_tbxSPECIALIZED_SKILLS_EXPL", "text",
                     resolver=lambda d: d.employment_education.specialized_skills_description or ""),
        FieldBinding("military_country", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_ddlMILITARY_SVC_CNTRY",
                     "select_text",
                     resolver=lambda d: d.employment_education.military_service_country or ""),
        FieldBinding("military_branch", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_tbxMILITARY_SVC_BRANCH",
                     "text", resolver=lambda d: d.employment_education.military_branch or ""),
        FieldBinding("military_rank", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_tbxMILITARY_SVC_RANK",
                     "text", resolver=lambda d: d.employment_education.military_rank or ""),
        FieldBinding("military_specialty", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_tbxMILITARY_SVC_SPECIALTY",
                     "text", resolver=lambda d: d.employment_education.military_specialty or ""),
        FieldBinding("military_from_day", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_ddlMILITARY_SVC_FROMDay",
                     "select_text", resolver=lambda d: _date_part(d.employment_education.military_service_start_date, "day")),
        FieldBinding("military_from_month", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_ddlMILITARY_SVC_FROMMonth",
                     "select_text", resolver=lambda d: _date_part(d.employment_education.military_service_start_date, "month")),
        FieldBinding("military_from_year", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_tbxMILITARY_SVC_FROMYear",
                     "text", resolver=lambda d: _date_part(d.employment_education.military_service_start_date, "year")),
        FieldBinding("military_to_day", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_ddlMILITARY_SVC_TODay",
                     "select_text", resolver=lambda d: _date_part(d.employment_education.military_service_end_date, "day")),
        FieldBinding("military_to_month", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_ddlMILITARY_SVC_TOMonth",
                     "select_text", resolver=lambda d: _date_part(d.employment_education.military_service_end_date, "month")),
        FieldBinding("military_to_year", f"#{_FV}_dtlMILITARY_SERVICE_ctl00_tbxMILITARY_SVC_TOYear",
                     "text", resolver=lambda d: _date_part(d.employment_education.military_service_end_date, "year")),
        FieldBinding("insurgent_expl", f"#{_FV}_tbxINSURGENT_ORG_EXPL", "text",
                     resolver=lambda d: d.employment_education.insurgent_organization_explanation or ""),
    ]))
    return phases


def _build_family_relatives_phases() -> list[FillPhase]:
    def _father_surname(d: ApplicantDossier) -> str:
        return _split_first_surname(d.family_contacts.father_full_name)[0]

    def _father_given(d: ApplicantDossier) -> str:
        return _split_first_surname(d.family_contacts.father_full_name)[1]

    def _mother_surname(d: ApplicantDossier) -> str:
        return _split_first_surname(d.family_contacts.mother_full_name)[0]

    def _mother_given(d: ApplicantDossier) -> str:
        return _split_first_surname(d.family_contacts.mother_full_name)[1]

    return [
        FillPhase(label="fill", fields=[
            # Father surname
            FieldBinding("father_surname_known", f"#{_FV}_cbxFATHER_SURNAME_UNK_IND",
                         "checkbox", hardcoded=False,
                         condition=lambda d: bool(_father_surname(d))),
            FieldBinding("father_surname_unknown", f"#{_FV}_cbxFATHER_SURNAME_UNK_IND",
                         "checkbox", hardcoded=True,
                         condition=lambda d: not bool(_father_surname(d))),
            FieldBinding("father_surname", f"#{_FV}_tbxFATHER_SURNAME", "text",
                         resolver=lambda d: _father_surname(d)),
            # Father given
            FieldBinding("father_given_known", f"#{_FV}_cbxFATHER_GIVEN_NAME_UNK_IND",
                         "checkbox", hardcoded=False,
                         condition=lambda d: bool(_father_given(d))),
            FieldBinding("father_given_unknown", f"#{_FV}_cbxFATHER_GIVEN_NAME_UNK_IND",
                         "checkbox", hardcoded=True,
                         condition=lambda d: not bool(_father_given(d))),
            FieldBinding("father_given", f"#{_FV}_tbxFATHER_GIVEN_NAME", "text",
                         resolver=lambda d: _father_given(d)),
            # Father DOB
            FieldBinding("father_dob_known", f"#{_FV}_cbxFATHER_DOB_UNK_IND",
                         "checkbox", hardcoded=False,
                         condition=lambda d: bool(d.family_contacts.father_date_of_birth)),
            FieldBinding("father_dob_unknown", f"#{_FV}_cbxFATHER_DOB_UNK_IND",
                         "checkbox", hardcoded=True,
                         condition=lambda d: not bool(d.family_contacts.father_date_of_birth)),
            FieldBinding("father_dob_day", f"#{_FV}_ddlFathersDOBDay", "select_text",
                         resolver=lambda d: d.family_contacts.father_date_of_birth[8:10] if d.family_contacts.father_date_of_birth else None),
            FieldBinding("father_dob_month", f"#{_FV}_ddlFathersDOBMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.family_contacts.father_date_of_birth[5:7]) if d.family_contacts.father_date_of_birth else None),
            FieldBinding("father_dob_year", f"#{_FV}_tbxFathersDOBYear", "text",
                         resolver=lambda d: d.family_contacts.father_date_of_birth[0:4] if d.family_contacts.father_date_of_birth else None),
            FieldBinding("father_in_us_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblFATHER_LIVE_IN_US_IND",
                         "radio", choice_value="N", hardcoded="N"),
            # Mother surname
            FieldBinding("mother_surname_known", f"#{_FV}_cbxMOTHER_SURNAME_UNK_IND",
                         "checkbox", hardcoded=False,
                         condition=lambda d: bool(_mother_surname(d))),
            FieldBinding("mother_surname_unknown", f"#{_FV}_cbxMOTHER_SURNAME_UNK_IND",
                         "checkbox", hardcoded=True,
                         condition=lambda d: not bool(_mother_surname(d))),
            FieldBinding("mother_surname", f"#{_FV}_tbxMOTHER_SURNAME", "text",
                         resolver=lambda d: _mother_surname(d)),
            # Mother given
            FieldBinding("mother_given_known", f"#{_FV}_cbxMOTHER_GIVEN_NAME_UNK_IND",
                         "checkbox", hardcoded=False,
                         condition=lambda d: bool(_mother_given(d))),
            FieldBinding("mother_given_unknown", f"#{_FV}_cbxMOTHER_GIVEN_NAME_UNK_IND",
                         "checkbox", hardcoded=True,
                         condition=lambda d: not bool(_mother_given(d))),
            FieldBinding("mother_given", f"#{_FV}_tbxMOTHER_GIVEN_NAME", "text",
                         resolver=lambda d: _mother_given(d)),
            # Mother DOB
            FieldBinding("mother_dob_known", f"#{_FV}_cbxMOTHER_DOB_UNK_IND",
                         "checkbox", hardcoded=False,
                         condition=lambda d: bool(d.family_contacts.mother_date_of_birth)),
            FieldBinding("mother_dob_unknown", f"#{_FV}_cbxMOTHER_DOB_UNK_IND",
                         "checkbox", hardcoded=True,
                         condition=lambda d: not bool(d.family_contacts.mother_date_of_birth)),
            FieldBinding("mother_dob_day", f"#{_FV}_ddlMothersDOBDay", "select_text",
                         resolver=lambda d: d.family_contacts.mother_date_of_birth[8:10] if d.family_contacts.mother_date_of_birth else None),
            FieldBinding("mother_dob_month", f"#{_FV}_ddlMothersDOBMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.family_contacts.mother_date_of_birth[5:7]) if d.family_contacts.mother_date_of_birth else None),
            FieldBinding("mother_dob_year", f"#{_FV}_tbxMothersDOBYear", "text",
                         resolver=lambda d: d.family_contacts.mother_date_of_birth[0:4] if d.family_contacts.mother_date_of_birth else None),
            FieldBinding("mother_in_us_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblMOTHER_LIVE_IN_US_IND",
                         "radio", choice_value="N", hardcoded="N"),
            FieldBinding("immediate_relatives_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblUS_IMMED_RELATIVE_IND",
                         "radio", choice_value="N", hardcoded="N"),
            FieldBinding("other_relatives_no",
                         "ctl00$SiteContentPlaceHolder$FormView1$rblUS_OTHER_RELATIVE_IND",
                         "radio", choice_value="N", hardcoded="N"),
        ]),
    ]


def _build_family_spouse_phases() -> list[FillPhase]:
    return [
        FillPhase(label="fill", fields=[
            FieldBinding("spouse_surname", f"#{_FV}_tbxSpouseSurname", "text",
                         resolver=lambda d: _split_first_surname(d.family_contacts.spouse_full_name)[0]),
            FieldBinding("spouse_given", f"#{_FV}_tbxSpouseGivenName", "text",
                         resolver=lambda d: _split_first_surname(d.family_contacts.spouse_full_name)[1]),
            FieldBinding("spouse_dob_day", f"#{_FV}_ddlDOBDay", "select_text",
                         resolver=lambda d: d.family_contacts.spouse_date_of_birth[8:10] if d.family_contacts.spouse_date_of_birth else None),
            FieldBinding("spouse_dob_month", f"#{_FV}_ddlDOBMonth", "select_text",
                         resolver=lambda d: _month_abbrev(d.family_contacts.spouse_date_of_birth[5:7]) if d.family_contacts.spouse_date_of_birth else None),
            FieldBinding("spouse_dob_year", f"#{_FV}_tbxDOBYear", "text",
                         resolver=lambda d: d.family_contacts.spouse_date_of_birth[0:4] if d.family_contacts.spouse_date_of_birth else None),
            FieldBinding("spouse_nationality", f"#{_FV}_ddlSpouseNatDropDownList", "select_text",
                         resolver=lambda d: d.family_contacts.spouse_nationality or d.identity.nationality or "CHINA"),
            FieldBinding("spouse_birth_city_known", f"#{_FV}_cbexSPOUSE_POB_CITY_NA",
                         "checkbox", hardcoded=False),
            FieldBinding("spouse_birth_city", f"#{_FV}_tbxSpousePOBCity", "text",
                         resolver=lambda d: d.family_contacts.spouse_birth_city or ""),
            FieldBinding("spouse_birth_country", f"#{_FV}_ddlSpousePOBCountry", "select_text",
                         resolver=lambda d: d.family_contacts.spouse_birth_country or d.identity.birth_country or "CHINA"),
            FieldBinding("spouse_address_type", f"#{_FV}_ddlSpouseAddressType", "select_text",
                         hardcoded="Same as Home Address"),
        ]),
    ]


# ---------------------------------------------------------------------------
# Complex pages (use the builders above)
# ---------------------------------------------------------------------------

PREVIOUS_TRAVEL = PageDefinition(
    page_key="previous_travel",
    url_matchers=["node=PreviousUSTravel", "Previous U.S. Travel Information"],
    phases=_build_previous_travel_phases(),
)

ADDRESS_PHONE = PageDefinition(
    page_key="address_phone",
    url_matchers=["node=AddressPhone", "Address and Phone Information"],
    phases=_build_address_phone_phases(),
)

US_CONTACT = PageDefinition(
    page_key="us_contact",
    url_matchers=["node=USContact", "U.S. Point of Contact Information"],
    phases=_build_us_contact_phases(),
)

WORK_EDUCATION_PRESENT = PageDefinition(
    page_key="work_education_present",
    url_matchers=["node=WorkEducation1", "Present Work/Education/Training Information"],
    phases=_build_work_education_present_phases(),
)

WORK_EDUCATION_PREVIOUS = PageDefinition(
    page_key="work_education_previous",
    url_matchers=["node=WorkEducation2", "Previous Work/Education/Training Information"],
    phases=_build_work_education_previous_phases(),
)

WORK_EDUCATION_ADDITIONAL = PageDefinition(
    page_key="work_education_additional",
    url_matchers=["node=WorkEducation3", "Additional Work/Education/Training Information"],
    phases=_build_work_education_additional_phases(),
)

FAMILY_RELATIVES = PageDefinition(
    page_key="family_relatives",
    url_matchers=["node=Relatives", "Family Information: Relatives"],
    phases=_build_family_relatives_phases(),
)

FAMILY_SPOUSE = PageDefinition(
    page_key="family_spouse",
    url_matchers=["node=Spouse", "Family Information: Spouse"],
    phases=_build_family_spouse_phases(),
)


# ---------------------------------------------------------------------------
# Security pages (shared builder)
# ---------------------------------------------------------------------------

def _build_security_page(
    page_key: str,
    url_matchers: list[str],
    questions: list[tuple[str, str, str]],
) -> PageDefinition:
    def _sec_yes(dossier: ApplicantDossier, key: str) -> bool:
        return bool(dossier.security_background.yes_no_answers.get(key, False))

    def _sec_explanation(dossier: ApplicantDossier, key: str) -> str:
        return dossier.security_background.explanations.get(
            key, "Explanation available upon request."
        )

    phases: list[FillPhase] = []
    for answer_key, radio_name, textarea_sel in questions:
        fields: list[FieldBinding] = [
            FieldBinding(
                f"{answer_key}",
                radio_name,
                "radio_click",
                resolver=lambda d, k=answer_key: "Y" if _sec_yes(d, k) else "N",
            ),
        ]
        if textarea_sel:
            fields.append(
                FieldBinding(
                    f"{answer_key}_explanation",
                    textarea_sel,
                    "text",
                    resolver=lambda d, k=answer_key: _sec_explanation(d, k),
                    condition=lambda d, k=answer_key: _sec_yes(d, k),
                )
            )
        phases.append(FillPhase(
            label=f"question_{answer_key}",
            wait_before_ms=1000 if phases else 0,
            fields=fields,
        ))

    return PageDefinition(
        page_key=page_key,
        url_matchers=url_matchers,
        phases=phases,
    )


SECURITY_PART1 = _build_security_page("security_part1", [
    "node=SecurityandBackground1", "Security and Background: Part 1",
], [
    ("communicable_disease", "ctl00$SiteContentPlaceHolder$FormView1$rblDisease",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxDisease"),
    ("physical_or_mental_disorder", "ctl00$SiteContentPlaceHolder$FormView1$rblDisorder",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxDisorder"),
    ("drug_abuser", "ctl00$SiteContentPlaceHolder$FormView1$rblDruguser",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxDruguser"),
])

SECURITY_PART2 = _build_security_page("security_part2", [
    "node=SecurityandBackground2", "Security and Background: Part 2",
], [
    ("arrested_or_convicted", "ctl00$SiteContentPlaceHolder$FormView1$rblArrested",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxArrested"),
    ("controlled_substances", "ctl00$SiteContentPlaceHolder$FormView1$rblControlledSubstances",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxControlledSubstances"),
    ("prostitution_or_vice", "ctl00$SiteContentPlaceHolder$FormView1$rblProstitution",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxProstitution"),
    ("money_laundering", "ctl00$SiteContentPlaceHolder$FormView1$rblMoneyLaundering",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxMoneyLaundering"),
    ("human_trafficking", "ctl00$SiteContentPlaceHolder$FormView1$rblHumanTrafficking",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxHumanTrafficking"),
    ("assisted_severe_trafficking", "ctl00$SiteContentPlaceHolder$FormView1$rblAssistedSevereTrafficking",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxAssistedSevereTrafficking"),
    ("human_trafficking_related", "ctl00$SiteContentPlaceHolder$FormView1$rblHumanTraffickingRelated",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxHumanTraffickingRelated"),
])

SECURITY_PART3 = _build_security_page("security_part3", [
    "node=SecurityandBackground3", "Security and Background: Part 3",
], [
    ("illegal_activity", "ctl00$SiteContentPlaceHolder$FormView1$rblIllegalActivity",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxIllegalActivity"),
    ("terrorist_activity", "ctl00$SiteContentPlaceHolder$FormView1$rblTerroristActivity",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxTerroristActivity"),
    ("terrorist_support", "ctl00$SiteContentPlaceHolder$FormView1$rblTerroristSupport",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxTerroristSupport"),
    ("terrorist_org", "ctl00$SiteContentPlaceHolder$FormView1$rblTerroristOrg",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxTerroristOrg"),
    ("terrorist_rel", "ctl00$SiteContentPlaceHolder$FormView1$rblTerroristRel",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxTerroristRel"),
    ("genocide", "ctl00$SiteContentPlaceHolder$FormView1$rblGenocide",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxGenocide"),
    ("torture", "ctl00$SiteContentPlaceHolder$FormView1$rblTorture",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxTorture"),
    ("extrajudicial_violence", "ctl00$SiteContentPlaceHolder$FormView1$rblExViolence",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxExViolence"),
    ("child_soldier", "ctl00$SiteContentPlaceHolder$FormView1$rblChildSoldier",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxChildSoldier"),
    ("religious_freedom", "ctl00$SiteContentPlaceHolder$FormView1$rblReligiousFreedom",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxReligiousFreedom"),
    ("population_controls", "ctl00$SiteContentPlaceHolder$FormView1$rblPopulationControls",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxPopulationControls"),
    ("transplant", "ctl00$SiteContentPlaceHolder$FormView1$rblTransplant",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxTransplant"),
])

SECURITY_PART4 = _build_security_page("security_part4", [
    "node=SecurityandBackground4", "Security and Background: Part 4",
], [
    ("removal_hearing", "ctl00$SiteContentPlaceHolder$FormView1$rblRemovalHearing",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxRemovalHearing"),
    ("immigration_fraud", "ctl00$SiteContentPlaceHolder$FormView1$rblImmigrationFraud",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxImmigrationFraud"),
    ("fail_to_attend", "ctl00$SiteContentPlaceHolder$FormView1$rblFailToAttend",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxFailToAttend"),
    ("visa_violation", "ctl00$SiteContentPlaceHolder$FormView1$rblVisaViolation",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxVisaViolation"),
    ("deport", "ctl00$SiteContentPlaceHolder$FormView1$rblDeport",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxDeport_EXPL"),
])

SECURITY_PART5 = _build_security_page("security_part5", [
    "node=SecurityandBackground5", "Security and Background: Part 5",
], [
    ("child_custody", "ctl00$SiteContentPlaceHolder$FormView1$rblChildCustody",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxChildCustody"),
    ("voting_violation", "ctl00$SiteContentPlaceHolder$FormView1$rblVotingViolation",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxVotingViolation"),
    ("renounce_exp", "ctl00$SiteContentPlaceHolder$FormView1$rblRenounceExp",
     "#ctl00_SiteContentPlaceHolder_FormView1_tbxRenounceExp"),
    ("attend_public_school_without_reimbursing", "ctl00$SiteContentPlaceHolder$FormView1$rblAttWoReimb",
     ""),
])

# ---------------------------------------------------------------------------
# Master registry
# ---------------------------------------------------------------------------

ALL_PAGES: list[PageDefinition] = [
    PERSONAL1,
    PERSONAL2,
    PASSPORT,
    TRAVEL,
    TRAVEL_COMPANIONS,
    PREVIOUS_TRAVEL,
    ADDRESS_PHONE,
    US_CONTACT,
    WORK_EDUCATION_PRESENT,
    WORK_EDUCATION_PREVIOUS,
    WORK_EDUCATION_ADDITIONAL,
    FAMILY_RELATIVES,
    FAMILY_SPOUSE,
    SECURITY_PART1,
    SECURITY_PART2,
    SECURITY_PART3,
    SECURITY_PART4,
    SECURITY_PART5,
]

PAGE_REGISTRY: dict[str, PageDefinition] = {p.page_key: p for p in ALL_PAGES}
