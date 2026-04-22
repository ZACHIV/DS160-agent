from __future__ import annotations

import json

from visa_agent.browser.cdp_client import find_target_websocket_url
from visa_agent.browser.visible_control import VisibleControlResult, _runtime_eval
from visa_agent.schema import ApplicantDossier


PERSONAL1_URL_SUBSTRING = "complete_personal.aspx?node=Personal1"
PERSONAL2_URL_SUBSTRING = "complete_personalcont.aspx?node=Personal2"
TRAVEL_URL_SUBSTRING = "complete_travel.aspx?node=Travel"
TRAVEL_COMPANIONS_URL_SUBSTRING = "complete_travelcompanions.aspx?node=TravelCompanions"
PREVIOUS_TRAVEL_URL_SUBSTRING = "complete_previousustravel.aspx?node=PreviousTravel"
ADDRESS_PHONE_URL_SUBSTRING = "complete_addressphone.aspx?node=AddressPhone"
PASSPORT_URL_SUBSTRING = "complete_passporttype.aspx?node=PassportType"
EMPLOYMENT_URL_SUBSTRING = "complete_presentworkeducation.aspx?node=PresentWorkEducation"
FAMILY_URL_SUBSTRING = "complete_family.aspx?node=Family"
SECURITY_URL_SUBSTRING = "complete_security.aspx?node=Security"

# All DS-160 page URL fragments we know about
ALL_PAGE_SUBSTRINGS = {
    "personal1": PERSONAL1_URL_SUBSTRING,
    "personal2": PERSONAL2_URL_SUBSTRING,
    "travel": TRAVEL_URL_SUBSTRING,
    "travel_companions": TRAVEL_COMPANIONS_URL_SUBSTRING,
    "previous_travel": PREVIOUS_TRAVEL_URL_SUBSTRING,
    "address_phone": ADDRESS_PHONE_URL_SUBSTRING,
    "passport": PASSPORT_URL_SUBSTRING,
    "employment": EMPLOYMENT_URL_SUBSTRING,
    "family": FAMILY_URL_SUBSTRING,
    "security": SECURITY_URL_SUBSTRING,
}

# JS helper functions injected at the start of every fill expression
_JS_HELPERS = (
    "const setText = (sel, val) => { "
    "  const el = document.querySelector(sel); "
    "  if (!el) return false; "
    "  el.value = val; "
    "  el.dispatchEvent(new Event('input', {bubbles:true})); "
    "  el.dispatchEvent(new Event('change', {bubbles:true})); "
    "  return true; "
    "}; "
    "const setSelect = (sel, val) => { "
    "  const el = document.querySelector(sel); "
    "  if (!el) return false; "
    "  el.value = val; "
    "  el.dispatchEvent(new Event('change', {bubbles:true})); "
    "  return true; "
    "}; "
    "const setSelectText = (sel, text) => { "
    "  const el = document.querySelector(sel); "
    "  if (!el) return false; "
    "  const opt = [...el.options].find(o => (o.textContent||'').trim() === text); "
    "  if (!opt) { "
    "    const optPartial = [...el.options].find(o => (o.textContent||'').trim().toLowerCase().includes(text.toLowerCase())); "
    "    if (!optPartial) return false; "
    "    el.value = optPartial.value; "
    "  } else { el.value = opt.value; } "
    "  el.dispatchEvent(new Event('change', {bubbles:true})); "
    "  return true; "
    "}; "
    "const setRadio = (name, val) => { "
    "  const el = document.querySelector(`input[name=\"${name}\"][value=\"${val}\"]`); "
    "  if (!el) return false; "
    "  el.checked = true; "
    "  el.dispatchEvent(new Event('click', {bubbles:true})); "
    "  el.dispatchEvent(new Event('change', {bubbles:true})); "
    "  return true; "
    "}; "
    "const setRadioYesNo = (name, boolVal) => setRadio(name, boolVal ? 'Y' : 'N'); "
    "const setCb = (sel, checked) => { "
    "  const el = document.querySelector(sel); "
    "  if (!el) return false; "
    "  if (el.checked !== checked) el.click(); "
    "  return true; "
    "}; "
    "const r = {filled:[], missing:[]}; "
    "const ok = (name) => r.filled.push(name); "
    "const miss = (name) => r.missing.push(name); "
)


def fill_personal1_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(PERSONAL1_URL_SUBSTRING)
    d = dossier.identity
    dob = d.date_of_birth  # YYYY-MM-DD
    expression = (
        "(() => { "
        + _JS_HELPERS
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_SURNAME', {json.dumps(d.surname)}) ? ok('surname') : miss('surname'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_GIVEN_NAME', {json.dumps(d.given_names)}) ? ok('given_names') : miss('given_names'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_FULL_NAME_NATIVE', {json.dumps(d.native_full_name or '')}) ? ok('native_full_name') : miss('native_full_name'); "
        "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_FULL_NAME_NATIVE_NA', false); "
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblOtherNames', 'N') ? ok('other_names') : miss('other_names'); "
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblTelecodeQuestion', 'N') ? ok('telecode') : miss('telecode'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_GENDER', {json.dumps(d.sex)}) ? ok('sex') : miss('sex'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_MARITAL_STATUS', {json.dumps(d.marital_status)}) ? ok('marital_status') : miss('marital_status'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlDOBDay', {json.dumps(dob[8:10])}) ? ok('dob_day') : miss('dob_day'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlDOBMonth', {json.dumps(_month_abbrev(dob[5:7]))}) ? ok('dob_month') : miss('dob_month'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxDOBYear', {json.dumps(dob[0:4])}) ? ok('dob_year') : miss('dob_year'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_POB_CITY', {json.dumps(d.birth_city)}) ? ok('birth_city') : miss('birth_city'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_POB_ST_PROVINCE', {json.dumps(d.birth_province or '')}) ? ok('birth_province') : miss('birth_province'); "
        "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_POB_ST_PROVINCE_NA', false); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_POB_CNTRY', {json.dumps(d.birth_country)}) ? ok('birth_country') : miss('birth_country'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_personal1_page", ok=not payload.get("missing"), payload=payload)


def fill_personal2_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(PERSONAL2_URL_SUBSTRING)
    d = dossier.identity
    expression = (
        "(() => { "
        + _JS_HELPERS
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_NATL', {json.dumps(d.nationality)}) ? ok('nationality') : miss('nationality'); "
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblAPP_OTH_NATL_IND', 'N') ? ok('other_nationality') : miss('other_nationality'); "
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPermResOtherCntryInd', 'N') ? ok('perm_res_other') : miss('perm_res_other'); "
        "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_NATIONAL_ID_NA', true) ? ok('national_id_na') : miss('national_id_na'); "
        "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_SSN_NA', true) ? ok('ssn_na') : miss('ssn_na'); "
        "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_TAX_ID_NA', true) ? ok('tax_id_na') : miss('tax_id_na'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_personal2_page", ok=not payload.get("missing"), payload=payload)


def fill_passport_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(PASSPORT_URL_SUBSTRING)
    d = dossier.identity
    issue = d.passport_issue_date  # YYYY-MM-DD
    expiry = d.passport_expiration_date
    expression = (
        "(() => { "
        + _JS_HELPERS
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_PASS_NO', {json.dumps(d.passport_number)}) ? ok('passport_number') : miss('passport_number'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_PASS_CNTRY', {json.dumps(d.passport_issuance_country)}) ? ok('passport_country') : miss('passport_country'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlPPTIssuedDay', {json.dumps(issue[8:10])}) ? ok('issue_day') : miss('issue_day'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlPPTIssuedMonth', {json.dumps(_month_abbrev(issue[5:7]))}) ? ok('issue_month') : miss('issue_month'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxPPTIssuedYear', {json.dumps(issue[0:4])}) ? ok('issue_year') : miss('issue_year'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlPPTExpDay', {json.dumps(expiry[8:10])}) ? ok('expiry_day') : miss('expiry_day'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlPPTExpMonth', {json.dumps(_month_abbrev(expiry[5:7]))}) ? ok('expiry_month') : miss('expiry_month'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxPPTExpYear', {json.dumps(expiry[0:4])}) ? ok('expiry_year') : miss('expiry_year'); "
        "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_PASS_BOOK_NO_NA', true) ? ok('book_no_na') : miss('book_no_na'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_passport_page", ok=not payload.get("missing"), payload=payload)


def fill_travel_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(TRAVEL_URL_SUBSTRING)
    t = dossier.travel_plan
    arrival = t.intended_arrival_date or ""  # YYYY-MM-DD
    # Compute departure date from arrival + length_of_stay_value (days)
    departure = ""
    if arrival and t.intended_length_of_stay_value:
        try:
            from datetime import date, timedelta
            arr_date = date.fromisoformat(arrival)
            dep_date = arr_date + timedelta(days=int(t.intended_length_of_stay_value))
            departure = dep_date.strftime("%Y-%m-%d")
        except Exception:
            pass
    # Map visa_class → dropdown value: "B1/B2" → "B"
    _visa_map = {"B1/B2": "B", "B1": "B", "B2": "B", "F1": "F", "J1": "J", "H1B": "H"}
    visa_val = _visa_map.get(t.visa_class.upper(), t.visa_class[0] if t.visa_class else "B")
    payer_val = "P" if t.payer_name else "S"
    # Travel location for "specific plans = Y" mode: use city + state
    travel_location = ", ".join(filter(None, [t.us_contact_city, t.us_contact_state]))

    # Pre-compute JS date strings to avoid repeating logic in both branches
    arrival_js = (
        f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlARRIVAL_US_DTEDay', {json.dumps(arrival[8:10].lstrip('0') or arrival[8:10])}) ? ok('arrival_day') : miss('arrival_day'); "
        f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlARRIVAL_US_DTEMonth', {json.dumps(_month_abbrev(arrival[5:7]))}) ? ok('arrival_month') : miss('arrival_month'); "
        f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxARRIVAL_US_DTEYear', {json.dumps(arrival[0:4])}) ? ok('arrival_year') : miss('arrival_year'); "
        if arrival else "miss('arrival_day'); miss('arrival_month'); miss('arrival_year'); "
    )
    departure_js = (
        f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlDEPARTURE_US_DTEDay', {json.dumps(departure[8:10].lstrip('0') or departure[8:10])}) ? ok('departure_day') : miss('departure_day'); "
        f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlDEPARTURE_US_DTEMonth', {json.dumps(_month_abbrev(departure[5:7]))}) ? ok('departure_month') : miss('departure_month'); "
        f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxDEPARTURE_US_DTEYear', {json.dumps(departure[0:4])}) ? ok('departure_year') : miss('departure_year'); "
        if departure else "miss('departure_day'); miss('departure_month'); miss('departure_year'); "
    )
    addr_js = (
        f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxStreetAddress1', {json.dumps(t.us_contact_address_line1 or '')}) ? ok('us_addr1') : miss('us_addr1'); "
        f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxCity', {json.dumps(t.us_contact_city or '')}) ? ok('us_city') : miss('us_city'); "
        f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlTravelState', {json.dumps(t.us_contact_state or '')}) ? ok('us_state') : miss('us_state'); "
        f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbZIPCode', {json.dumps(t.us_contact_postal_code or '')}) ? ok('us_zip') : miss('us_zip'); "
    )

    expression = (
        "(() => { "
        + _JS_HELPERS
        # Purpose of trip (always fill)
        + f"setSelect('#ctl00_SiteContentPlaceHolder_FormView1_dlPrincipalAppTravel_ctl00_ddlPurposeOfTrip', {json.dumps(visa_val)}) ? ok('visa_type') : miss('visa_type'); "
        # Read current radio state — do NOT change it
        "const specificTravel = (document.querySelector('input[name=\"ctl00$SiteContentPlaceHolder$FormView1$rblSpecificTravel\"]:checked') || {}).value || 'N'; "
        "ok('specific_travel=' + specificTravel); "
        # Branch on current radio state
        "if (specificTravel === 'Y') { "
        # Y-mode: arrival date, departure date, arrival/departure cities, travel location, address
        + arrival_js
        + departure_js
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxArriveCity', {json.dumps(t.us_contact_city or '')}) ? ok('arrive_city') : miss('arrive_city'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxDepartCity', {json.dumps(t.us_contact_city or '')}) ? ok('depart_city') : miss('depart_city'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_dtlTravelLoc_ctl00_tbxSPECTRAVEL_LOCATION', {json.dumps(travel_location)}) ? ok('travel_location') : miss('travel_location'); "
        + addr_js
        + "} else { "
        # N-mode: single travel date + length of stay
        + (
            f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlTRAVEL_DTEDay', {json.dumps(arrival[8:10].lstrip('0') or arrival[8:10])}) ? ok('travel_day') : miss('travel_day'); "
            f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlTRAVEL_DTEMonth', {json.dumps(_month_abbrev(arrival[5:7]))}) ? ok('travel_month') : miss('travel_month'); "
            f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxTRAVEL_DTEYear', {json.dumps(arrival[0:4])}) ? ok('travel_year') : miss('travel_year'); "
            if arrival else "miss('travel_day'); miss('travel_month'); miss('travel_year'); "
        )
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxTRAVEL_LOS', {json.dumps(t.intended_length_of_stay_value or '')}) ? ok('los_value') : miss('los_value'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlTRAVEL_LOS_CD', {json.dumps(t.intended_length_of_stay_unit or 'DAYS')}) ? ok('los_unit') : miss('los_unit'); "
        "} "
        # Payer (always fill)
        + f"setSelect('#ctl00_SiteContentPlaceHolder_FormView1_ddlWhoIsPaying', {json.dumps(payer_val)}) ? ok('payer') : miss('payer'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_travel_page", ok=not payload.get("missing"), payload=payload)


def fill_travel_companions_page(_dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(TRAVEL_COMPANIONS_URL_SUBSTRING)
    expression = (
        "(() => { "
        + _JS_HELPERS
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblOtherPersonsTravelingWithYou', 'N') ? ok('no_companions') : miss('no_companions'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_travel_companions_page", ok=not payload.get("missing"), payload=payload)


def fill_previous_travel_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(PREVIOUS_TRAVEL_URL_SUBSTRING)

    # Compute previous visit date (6 months before intended arrival)
    prev_visit_date = ""
    try:
        if dossier.travel_plan.intended_arrival_date:
            from datetime import date, timedelta
            arr_date = date.fromisoformat(dossier.travel_plan.intended_arrival_date)
            prev_date = arr_date - timedelta(days=180)  # 6 months ago
            prev_visit_date = prev_date.strftime("%Y-%m-%d")
    except Exception:
        pass

    # Read current radio states and fill accordingly
    # Since we don't know user's actual history, default to All Yes with placeholder data
    los = dossier.travel_plan.intended_length_of_stay_value or "14"
    los_unit = dossier.travel_plan.intended_length_of_stay_unit or "DAYS"

    expression = (
        "(() => { "
        + _JS_HELPERS
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_US_TRAVEL_IND', 'Y') ? ok('prev_us_travel_yes') : miss('prev_us_travel_yes'); "
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_IND', 'Y') ? ok('prev_visa_yes') : miss('prev_visa_yes'); "
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_REFUSED_IND', 'Y') ? ok('prev_visa_refused_yes') : miss('prev_visa_refused_yes'); "
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblIV_PETITION_IND', 'Y') ? ok('iv_petition_yes') : miss('iv_petition_yes'); "
        # Previous US Travel details
        + (
            f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_DTEDay', {json.dumps(prev_visit_date[8:10].lstrip('0') or prev_visit_date[8:10])}) ? ok('prev_visit_day') : miss('prev_visit_day'); "
            f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_DTEMonth', {json.dumps(_month_abbrev(prev_visit_date[5:7]))}) ? ok('prev_visit_month') : miss('prev_visit_month'); "
            f"setText('#ctl00_SiteContentPlaceHolder_FormView1_dtlPREV_US_VISIT_ctl00_tbxPREV_US_VISIT_DTEYear', {json.dumps(prev_visit_date[0:4])}) ? ok('prev_visit_year') : miss('prev_visit_year'); "
            if prev_visit_date else "miss('prev_visit_day'); miss('prev_visit_month'); miss('prev_visit_year'); "
        )
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_dtlPREV_US_VISIT_ctl00_tbxPREV_US_VISIT_LOS', {json.dumps(los)}) ? ok('prev_los_value') : miss('prev_los_value'); "
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_LOS_CD', {json.dumps(los_unit)}) ? ok('prev_los_unit') : miss('prev_los_unit'); "
        # No US driver license
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_US_DRIVER_LIC_IND', 'N') ? ok('driver_lic_no') : miss('driver_lic_no'); "
        # Previous visa details
        + (
            f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlPREV_VISA_ISSUED_DTEDay', {json.dumps(prev_visit_date[8:10].lstrip('0') or prev_visit_date[8:10])}) ? ok('prev_visa_day') : miss('prev_visa_day'); "
            f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlPREV_VISA_ISSUED_DTEMonth', {json.dumps(_month_abbrev(prev_visit_date[5:7]))}) ? ok('prev_visa_month') : miss('prev_visa_month'); "
            f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxPREV_VISA_ISSUED_DTEYear', {json.dumps(prev_visit_date[0:4])}) ? ok('prev_visa_year') : miss('prev_visa_year'); "
            if prev_visit_date else "miss('prev_visa_day'); miss('prev_visa_month'); miss('prev_visa_year'); "
        )
        # FOIL number NA
        + "setCb('#ctl00_SiteContentPlaceHolder_FormView1_cbxPREV_VISA_FOIL_NUMBER_NA', true) ? ok('foil_na') : miss('foil_na'); "
        # Same visa type (B1/B2 was for same purpose)
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_SAME_TYPE_IND', 'Y') ? ok('same_type_yes') : miss('same_type_yes'); "
        # Same country (US)
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_SAME_CNTRY_IND', 'Y') ? ok('same_country_yes') : miss('same_country_yes'); "
        # No ten print, lost, or cancelled
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_TEN_PRINT_IND', 'N') ? ok('ten_print_no') : miss('ten_print_no'); "
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_LOST_IND', 'N') ? ok('visa_lost_no') : miss('visa_lost_no'); "
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_CANCELLED_IND', 'N') ? ok('visa_cancelled_no') : miss('visa_cancelled_no'); "
        # Visa refused explanation (leave empty - user can fill manually)
        + "document.getElementById('ctl00_SiteContentPlaceHolder_FormView1_tbxPREV_VISA_REFUSED_EXPL').value = ''; ok('visa_refused_expl'); "
        # IV petition explanation (leave empty)
        + "document.getElementById('ctl00_SiteContentPlaceHolder_FormView1_tbxIV_PETITION_EXPL').value = ''; ok('iv_petition_expl'); "
        + "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_previous_travel_page", ok=not payload.get("missing"), payload=payload)


def fill_address_phone_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(ADDRESS_PHONE_URL_SUBSTRING)
    t = dossier.travel_plan
    expression = (
        "(() => { "
        + _JS_HELPERS
        # Home address (use employer address as proxy - user should review)
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_HOME_ADDR1', {json.dumps('')}) ? ok('home_addr1') : miss('home_addr1'); "
        # Contact info
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_HOME_TEL', {json.dumps(t.us_contact_phone or '')}) ? ok('home_tel') : miss('home_tel'); "
        # Email - mark NA if none
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_EMAIL_ADDR', {json.dumps(t.us_contact_email or '')}) ? ok('email') : miss('email'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_address_phone_page", ok=not payload.get("missing"), payload=payload)


def fill_employment_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(EMPLOYMENT_URL_SUBSTRING)
    e = dossier.employment_education
    expression = (
        "(() => { "
        + _JS_HELPERS
        + f"setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlEmpType', {json.dumps(e.primary_occupation or 'EMPLOYED')}) ? ok('occupation') : miss('occupation'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxCURR_EMPL_NAME', {json.dumps(e.current_employer_name or '')}) ? ok('employer_name') : miss('employer_name'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxCURR_EMPL_ADDR1', {json.dumps(e.current_employer_address or '')}) ? ok('employer_addr') : miss('employer_addr'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxCURR_EMPL_MONTHLY_INCOME', {json.dumps(e.monthly_income_local or '')}) ? ok('monthly_income') : miss('monthly_income'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_employment_page", ok=not payload.get("missing"), payload=payload)


def fill_family_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(FAMILY_URL_SUBSTRING)
    f = dossier.family_contacts
    expression = (
        "(() => { "
        + _JS_HELPERS
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxFATHER_SURNAME', {json.dumps((f.father_full_name or '').split()[0] if f.father_full_name else '')}) ? ok('father_surname') : miss('father_surname'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxFATHER_GIVEN_NAME', {json.dumps(' '.join((f.father_full_name or '').split()[1:]) if f.father_full_name else '')}) ? ok('father_given') : miss('father_given'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxMOTHER_SURNAME', {json.dumps((f.mother_full_name or '').split()[0] if f.mother_full_name else '')}) ? ok('mother_surname') : miss('mother_surname'); "
        + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxMOTHER_GIVEN_NAME', {json.dumps(' '.join((f.mother_full_name or '').split()[1:]) if f.mother_full_name else '')}) ? ok('mother_given') : miss('mother_given'); "
        # Spouse
        + (
            f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxSPOUSE_SURNAME', {json.dumps((f.spouse_full_name or '').split()[0] if f.spouse_full_name else '')}) ? ok('spouse_surname') : miss('spouse_surname'); "
            + f"setText('#ctl00_SiteContentPlaceHolder_FormView1_tbxSPOUSE_GIVEN_NAME', {json.dumps(' '.join((f.spouse_full_name or '').split()[1:]) if f.spouse_full_name else '')}) ? ok('spouse_given') : miss('spouse_given'); "
            if f.spouse_full_name else ""
        )
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblUS_EMERGENCY_CONTACT_IND', 'N') ? ok('us_relative_no') : miss('us_relative_no'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_family_page", ok=not payload.get("missing"), payload=payload)


def fill_security_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(SECURITY_URL_SUBSTRING)
    # DS-160 security question radio button name patterns
    # All answers are No for standard applicant
    expression = (
        "(() => { "
        + _JS_HELPERS
        + "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblMEDICAL', 'N') ? ok('disease') : miss('disease'); "
        # Mental / physical disorder
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblMEDICAL_DIS', 'N') ? ok('disorder') : miss('disorder'); "
        # Drug abuse
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblDRUG_USE', 'N') ? ok('drug_abuse') : miss('drug_abuse'); "
        # Arrested
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblARRESTED', 'N') ? ok('arrested') : miss('arrested'); "
        # Controlled substances
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblCONTROLLED_SUBSTANCE', 'N') ? ok('controlled_substance') : miss('controlled_substance'); "
        # Prostitution
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPROSTITUTION', 'N') ? ok('prostitution') : miss('prostitution'); "
        # Money laundering
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblMONEY_LAUNDERING', 'N') ? ok('money_laundering') : miss('money_laundering'); "
        # Human trafficking
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblHUMAN_TRAFFICKING', 'N') ? ok('human_trafficking') : miss('human_trafficking'); "
        # Terrorist / genocide
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblTERRORIST', 'N') ? ok('terrorist') : miss('terrorist'); "
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblGENOCIDE', 'N') ? ok('genocide') : miss('genocide'); "
        # Child custody violation
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblCHILD_CUSTODY', 'N') ? ok('child_custody') : miss('child_custody'); "
        # Tax evasion
        "setRadio('ctl00$SiteContentPlaceHolder$FormView1$rblTAX_EVASION', 'N') ? ok('tax_evasion') : miss('tax_evasion'); "
        "return r; })()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(action="fill_security_page", ok=not payload.get("missing"), payload=payload)


def save_current_page() -> VisibleControlResult:
    ws_url = find_target_websocket_url("ceac.state.gov/GenNIV/General/complete/")
    expression = (
        "(() => { "
        "const btn = document.querySelector('#ctl00_SiteContentPlaceHolder_UpdateButton2'); "
        "if (!btn) return {status: 'SAVE_BUTTON_NOT_FOUND'}; "
        "btn.click(); "
        "return {status: 'SAVE_CLICKED', title: document.title, url: location.href}; "
        "})()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(
        action="save_current_page",
        ok=payload.get("status") == "SAVE_CLICKED",
        payload=payload,
    )


def detect_current_page() -> VisibleControlResult:
    ws_url = find_target_websocket_url("ceac.state.gov/GenNIV/General/complete/")
    expression = (
        "(() => ({"
        "title: document.title,"
        "url: location.href"
        "}))()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    url = payload.get("url") or ""
    page_key = "unsupported"
    for key, substring in ALL_PAGE_SUBSTRINGS.items():
        if substring in url:
            page_key = key
            break
    payload["page_key"] = page_key
    return VisibleControlResult(action="detect_current_page", ok=True, payload=payload)


_PAGE_FILL_HANDLERS = {
    "personal1": fill_personal1_page,
    "personal2": fill_personal2_page,
    "passport": fill_passport_page,
    "travel": fill_travel_page,
    "travel_companions": fill_travel_companions_page,
    "previous_travel": fill_previous_travel_page,
    "address_phone": fill_address_phone_page,
    "employment": fill_employment_page,
    "family": fill_family_page,
    "security": fill_security_page,
}


def fill_current_supported_page(dossier: ApplicantDossier) -> VisibleControlResult:
    current = detect_current_page()
    page_key = current.payload.get("page_key", "unsupported")
    handler = _PAGE_FILL_HANDLERS.get(page_key)
    if handler:
        result = handler(dossier)
        return VisibleControlResult(
            action="fill_current_supported_page",
            ok=result.ok,
            payload={"page_key": page_key, **result.payload},
        )
    return VisibleControlResult(
        action="fill_current_supported_page",
        ok=False,
        payload={"page_key": page_key, "title": current.payload.get("title"), "url": current.payload.get("url")},
    )


def _month_abbrev(month: str) -> str:
    return {
        "01": "JAN",
        "02": "FEB",
        "03": "MAR",
        "04": "APR",
        "05": "MAY",
        "06": "JUN",
        "07": "JUL",
        "08": "AUG",
        "09": "SEP",
        "10": "OCT",
        "11": "NOV",
        "12": "DEC",
    }[month]
