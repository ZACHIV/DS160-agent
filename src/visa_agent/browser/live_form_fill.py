from __future__ import annotations

import json

from visa_agent.browser.cdp_client import find_target_websocket_url
from visa_agent.browser.visible_control import VisibleControlResult, _runtime_eval
from visa_agent.schema import ApplicantDossier


PERSONAL1_URL_SUBSTRING = "complete_personal.aspx?node=Personal1"
PERSONAL2_URL_SUBSTRING = "complete_personalcont.aspx?node=Personal2"


def fill_personal1_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(PERSONAL1_URL_SUBSTRING)
    expression = (
        "(() => { "
        "const setValue = (selector, value) => { "
        "  const el = document.querySelector(selector); "
        "  if (!el) return false; "
        "  el.value = value; "
        "  el.dispatchEvent(new Event('input', { bubbles: true })); "
        "  el.dispatchEvent(new Event('change', { bubbles: true })); "
        "  return true; "
        "}; "
        "const setChecked = (selector, checked) => { "
        "  const el = document.querySelector(selector); "
        "  if (!el) return false; "
        "  el.checked = checked; "
        "  el.dispatchEvent(new Event('click', { bubbles: true })); "
        "  el.dispatchEvent(new Event('change', { bubbles: true })); "
        "  return true; "
        "}; "
        "const setRadioByName = (name, value) => { "
        "  const el = document.querySelector(`input[name=\"${name}\"][value=\"${value}\"]`); "
        "  if (!el) return false; "
        "  el.checked = true; "
        "  el.click(); "
        "  return true; "
        "}; "
        "const setSelectByText = (selector, text) => { "
        "  const el = document.querySelector(selector); "
        "  if (!el) return false; "
        "  const option = [...el.options].find(opt => (opt.textContent || '').trim() === text); "
        "  if (!option) return false; "
        "  el.value = option.value; "
        "  el.dispatchEvent(new Event('change', { bubbles: true })); "
        "  return true; "
        "}; "
        "const result = { filled: [], missing: [] }; "
        + f"if (setValue('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_SURNAME', {json.dumps(dossier.identity.surname)})) result.filled.push('surname'); else result.missing.push('surname'); "
        + f"if (setValue('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_GIVEN_NAME', {json.dumps(dossier.identity.given_names)})) result.filled.push('given_names'); else result.missing.push('given_names'); "
        + f"if (setValue('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_FULL_NAME_NATIVE', {json.dumps(dossier.identity.native_full_name or '')})) result.filled.push('native_full_name'); else result.missing.push('native_full_name'); "
        "setChecked('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_FULL_NAME_NATIVE_NA', false); "
        "if (setRadioByName('ctl00$SiteContentPlaceHolder$FormView1$rblOtherNames', 'N')) result.filled.push('other_names=no'); else result.missing.push('other_names'); "
        "if (setRadioByName('ctl00$SiteContentPlaceHolder$FormView1$rblTelecodeQuestion', 'N')) result.filled.push('telecode=no'); else result.missing.push('telecode'); "
        + f"if (setSelectByText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_GENDER', {json.dumps(dossier.identity.sex)})) result.filled.push('sex'); else result.missing.push('sex'); "
        + f"if (setSelectByText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_MARITAL_STATUS', {json.dumps(dossier.identity.marital_status)})) result.filled.push('marital_status'); else result.missing.push('marital_status'); "
        + f"if (setSelectByText('#ctl00_SiteContentPlaceHolder_FormView1_ddlDOBDay', {json.dumps(dossier.identity.date_of_birth[8:10])})) result.filled.push('dob_day'); else result.missing.push('dob_day'); "
        + f"if (setSelectByText('#ctl00_SiteContentPlaceHolder_FormView1_ddlDOBMonth', {json.dumps(_month_abbrev(dossier.identity.date_of_birth[5:7]))})) result.filled.push('dob_month'); else result.missing.push('dob_month'); "
        + f"if (setValue('#ctl00_SiteContentPlaceHolder_FormView1_tbxDOBYear', {json.dumps(dossier.identity.date_of_birth[0:4])})) result.filled.push('dob_year'); else result.missing.push('dob_year'); "
        + f"if (setValue('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_POB_CITY', {json.dumps(dossier.identity.birth_city)})) result.filled.push('birth_city'); else result.missing.push('birth_city'); "
        + f"if (setValue('#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_POB_ST_PROVINCE', {json.dumps(dossier.identity.birth_province or '')})) result.filled.push('birth_province'); else result.missing.push('birth_province'); "
        "setChecked('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_POB_ST_PROVINCE_NA', false); "
        + f"if (setSelectByText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_POB_CNTRY', {json.dumps(dossier.identity.birth_country)})) result.filled.push('birth_country'); else result.missing.push('birth_country'); "
        "return result; "
        "})()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(
        action="fill_personal1_page",
        ok=not payload.get("missing"),
        payload=payload,
    )


def fill_personal2_page(dossier: ApplicantDossier) -> VisibleControlResult:
    ws_url = find_target_websocket_url(PERSONAL2_URL_SUBSTRING)
    expression = (
        "(() => { "
        "const setSelectText=(sel,text)=>{const el=document.querySelector(sel); if(!el) return false; const opt=[...el.options].find(o=>(o.textContent||'').trim()===text); if(!opt) return false; el.value=opt.value; el.dispatchEvent(new Event('change',{bubbles:true})); return true;}; "
        "const clickRadio=(name,val)=>{const el=document.querySelector(`input[name=\"${name}\"][value=\"${val}\"]`); if(!el) return false; el.checked=true; el.click(); return true;}; "
        "const clickCb=(sel)=>{const el=document.querySelector(sel); if(!el) return false; if(!el.checked) el.click(); return true;}; "
        "const result={filled:[], missing:[]}; "
        + f"if(setSelectText('#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_NATL', {json.dumps(dossier.identity.nationality)})) result.filled.push('nationality'); else result.missing.push('nationality'); "
        "if(clickRadio('ctl00$SiteContentPlaceHolder$FormView1$rblAPP_OTH_NATL_IND','N')) result.filled.push('other_nationality=no'); else result.missing.push('other_nationality'); "
        "if(clickRadio('ctl00$SiteContentPlaceHolder$FormView1$rblPermResOtherCntryInd','N')) result.filled.push('perm_res_other=no'); else result.missing.push('perm_res_other'); "
        "if(clickCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_NATIONAL_ID_NA')) result.filled.push('national_id=na'); else result.missing.push('national_id_na'); "
        "if(clickCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_SSN_NA')) result.filled.push('ssn=na'); else result.missing.push('ssn_na'); "
        "if(clickCb('#ctl00_SiteContentPlaceHolder_FormView1_cbexAPP_TAX_ID_NA')) result.filled.push('tax_id=na'); else result.missing.push('tax_id_na'); "
        "return result; "
        "})()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(
        action="fill_personal2_page",
        ok=not payload.get("missing"),
        payload=payload,
    )


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
    if PERSONAL1_URL_SUBSTRING in url:
        payload["page_key"] = "personal1"
    elif PERSONAL2_URL_SUBSTRING in url:
        payload["page_key"] = "personal2"
    else:
        payload["page_key"] = "unsupported"
    return VisibleControlResult(
        action="detect_current_page",
        ok=True,
        payload=payload,
    )


def fill_current_supported_page(dossier: ApplicantDossier) -> VisibleControlResult:
    current = detect_current_page()
    page_key = current.payload.get("page_key")
    if page_key == "personal1":
        result = fill_personal1_page(dossier)
        return VisibleControlResult(
            action="fill_current_supported_page",
            ok=result.ok,
            payload={"page_key": page_key, **result.payload},
        )
    if page_key == "personal2":
        result = fill_personal2_page(dossier)
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
