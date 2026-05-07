"""DS-160 live form filling via Chrome DevTools Protocol.

Page-level selector definitions live in visa_agent.browser.page_definitions.
The fill engine in visa_agent.browser.fill_engine executes them.
This module provides page detection, navigation, and the handler registry.
"""

from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, unquote, urlparse

from visa_agent.browser.cdp_client import CDPWebSocket, find_target_websocket_url

from visa_agent.browser.visible_control import VisibleControlResult, _runtime_eval
from visa_agent.schema import ApplicantDossier


# ---------------------------------------------------------------------------
# URL substrings and page matchers (used by detect_current_page)
# ---------------------------------------------------------------------------

PERSONAL1_URL_SUBSTRING = "node=Personal1"
PERSONAL2_URL_SUBSTRING = "node=Personal2"
TRAVEL_URL_SUBSTRING = "node=Travel"
TRAVEL_COMPANIONS_URL_SUBSTRING = "node=TravelCompanions"
PREVIOUS_TRAVEL_URL_SUBSTRING = "node=PreviousUSTravel"
ADDRESS_PHONE_URL_SUBSTRING = "node=AddressPhone"
PASSPORT_URL_SUBSTRING = "node=PptVisa"
US_CONTACT_URL_SUBSTRING = "node=USContact"
WORK_EDUCATION_PRESENT_URL_SUBSTRING = "node=WorkEducation1"
WORK_EDUCATION_PREVIOUS_URL_SUBSTRING = "node=WorkEducation2"
WORK_EDUCATION_ADDITIONAL_URL_SUBSTRING = "node=WorkEducation3"
FAMILY_RELATIVES_URL_SUBSTRING = "node=Relatives"
FAMILY_SPOUSE_URL_SUBSTRING = "node=Spouse"
SECURITY_URL_SUBSTRING = "node=Security"

PAGE_MATCHERS = {
    "personal1": ["node=Personal1", "Personal Information 1"],
    "personal2": ["node=Personal2", "Personal Information 2"],
    "travel": ["node=Travel", "Travel Information"],
    "travel_companions": ["node=TravelCompanions", "Travel Companions"],
    "previous_travel": ["node=PreviousUSTravel", "Previous U.S. Travel Information"],
    "address_phone": ["node=AddressPhone", "Address and Phone Information"],
    "passport": ["node=PptVisa", "node=PassportType", "Passport Information"],
    "us_contact": ["node=USContact", "U.S. Point of Contact Information"],
    "work_education_present": ["node=WorkEducation1", "Present Work/Education/Training Information"],
    "work_education_previous": ["node=WorkEducation2", "Previous Work/Education/Training Information"],
    "work_education_additional": ["node=WorkEducation3", "Additional Work/Education/Training Information"],
    "family_relatives": ["node=Relatives", "Family Information: Relatives"],
    "family_spouse": ["node=Spouse", "Family Information: Spouse"],
    "security_part1": ["node=SecurityandBackground1", "Security and Background: Part 1"],
    "security_part2": ["node=SecurityandBackground2", "Security and Background: Part 2"],
    "security_part3": ["node=SecurityandBackground3", "Security and Background: Part 3"],
    "security_part4": ["node=SecurityandBackground4", "Security and Background: Part 4"],
    "security_part5": ["node=SecurityandBackground5", "Security and Background: Part 5"],
}

ALL_PAGE_SUBSTRINGS = {
    key: matchers[0] for key, matchers in PAGE_MATCHERS.items()
}


def _url_node_value(url: str) -> str | None:
    parsed = urlparse(url)
    node = parse_qs(parsed.query).get("node", [None])[0]
    if node:
        return unquote(node)
    marker = "node="
    if marker not in url:
        return None
    tail = url.split(marker, 1)[1]
    return unquote(tail.split("&", 1)[0].split("#", 1)[0])


def _matches_page(page_key: str, url: str, title: str) -> bool:
    node = _url_node_value(url)
    node_matchers = [matcher.split("=", 1)[1] for matcher in PAGE_MATCHERS[page_key] if matcher.startswith("node=")]
    if node is not None and node_matchers:
        return node in node_matchers

    for matcher in PAGE_MATCHERS[page_key]:
        if matcher.startswith("node="):
            if matcher in url:
                return True
            continue
        if matcher in title or matcher in url:
            return True
    return False


def _detect_page_key(url: str, title: str) -> str:
    for key in PAGE_MATCHERS:
        if _matches_page(key, url, title):
            return key
    return "unsupported"


# ---------------------------------------------------------------------------
# Fill handler registry
# Handlers are generated from declarative PageDefinitions.
# See: visa_agent.browser.page_definitions and visa_agent.browser.fill_engine
# ---------------------------------------------------------------------------


def _make_engine_handler(page_key: str):
    """Factory: produce a (dossier) -> VisibleControlResult handler."""

    from visa_agent.browser.page_definitions import PAGE_REGISTRY
    from visa_agent.browser.fill_engine import execute_page

    def _handler(dossier: ApplicantDossier) -> VisibleControlResult:
        return execute_page(PAGE_REGISTRY[page_key], dossier)

    return _handler


_PAGE_FILL_HANDLERS = {
    "personal1": _make_engine_handler("personal1"),
    "personal2": _make_engine_handler("personal2"),
    "passport": _make_engine_handler("passport"),
    "travel": _make_engine_handler("travel"),
    "travel_companions": _make_engine_handler("travel_companions"),
    "previous_travel": _make_engine_handler("previous_travel"),
    "address_phone": _make_engine_handler("address_phone"),
    "us_contact": _make_engine_handler("us_contact"),
    "work_education_present": _make_engine_handler("work_education_present"),
    "work_education_previous": _make_engine_handler("work_education_previous"),
    "work_education_additional": _make_engine_handler("work_education_additional"),
    "family_relatives": _make_engine_handler("family_relatives"),
    "family_spouse": _make_engine_handler("family_spouse"),
    "security_part1": _make_engine_handler("security_part1"),
    "security_part2": _make_engine_handler("security_part2"),
    "security_part3": _make_engine_handler("security_part3"),
    "security_part4": _make_engine_handler("security_part4"),
    "security_part5": _make_engine_handler("security_part5"),
}


def fill_current_supported_page(dossier: ApplicantDossier) -> VisibleControlResult:
    """Auto-detect the current page and fill it using the engine."""
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


# ---------------------------------------------------------------------------
# CDP operations (non-page-specific)
# ---------------------------------------------------------------------------


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


def extract_application_id() -> VisibleControlResult:
    ws_url = find_target_websocket_url("ceac.state.gov/GenNIV/General/complete/")
    expression = (
        "(() => { "
        "const text = document.body ? document.body.innerText : ''; "
        "const direct = text.match(/Application ID(?:\\s+is)?\\s*:?\\s*(AA[0-9A-Z]{8,})/i); "
        "const fallback = text.match(/\\b(AA[0-9A-Z]{8,})\\b/i); "
        "const application_id = direct ? direct[1].toUpperCase() : (fallback ? fallback[1].toUpperCase() : null); "
        "return {application_id, title: document.title, url: location.href}; "
        "})()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    return VisibleControlResult(
        action="extract_application_id",
        ok=bool(payload.get("application_id")),
        payload=payload,
    )


def detect_current_page() -> VisibleControlResult:
    ws_url = find_target_websocket_url("ceac.state.gov/GenNIV/General/complete/")
    expression = (
        "(() => {"
        "const text = document.body ? document.body.innerText : '';"
        "const direct = text.match(/Application ID(?:\\s+is)?\\s*:?\\s*(AA[0-9A-Z]{8,})/i);"
        "const fallback = text.match(/\\b(AA[0-9A-Z]{8,})\\b/i);"
        "return {"
        "title: document.title,"
        "url: location.href,"
        "application_id: direct ? direct[1].toUpperCase() : (fallback ? fallback[1].toUpperCase() : null)"
        "};"
        "})()"
    )
    result = _runtime_eval(ws_url, expression)
    payload = dict(result.get("value") or {})
    url = payload.get("url") or ""
    title = payload.get("title") or ""
    payload["page_key"] = _detect_page_key(url, title)
    return VisibleControlResult(action="detect_current_page", ok=True, payload=payload)


def click_next_and_wait(port: int = 9222, timeout_s: float = 30.0) -> VisibleControlResult:
    ws_url = find_target_websocket_url("ceac.state.gov/GenNIV/General/complete/")
    probe_expression = (
        "(() => ({ url: location.href, title: document.title }))()"
    )
    before = _runtime_eval(ws_url, probe_expression)
    before_url = dict(before.get("value") or {}).get("url") or ""

    click_expression = (
        "(() => { "
        "const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length); "
        "const label = (el) => [el.value, el.innerText, el.textContent, el.getAttribute('aria-label'), el.title, el.id, el.name].filter(Boolean).join(' ').trim(); "
        "const excluded = /\\b(save|back|previous|cancel|exit|sign\\s*out)\\b|continue\\s+application/i; "
        "const isNext = (text) => /^\\s*next\\b/i.test(text) || /\\bnext\\s*:/i.test(text) || /下一步/.test(text); "
        "const controls = [...document.querySelectorAll('input[type=\"submit\"], input[type=\"button\"], button, a')].filter(visible); "
        "let btn = controls.find((el) => { const text = label(el); return isNext(text) && !excluded.test(text); }); "
        "if (!btn) { "
        "  const selectors = ["
        "    '#ctl00_SiteContentPlaceHolder_UpdateButton3',"
        "    '#ctl00_SiteContentPlaceHolder_NextButton',"
        "    '#ctl00_SiteContentPlaceHolder_btnNext',"
        "    'input[name=\"ctl00$SiteContentPlaceHolder$UpdateButton3\"]'"
        "  ]; "
        "  btn = selectors.map((sel) => document.querySelector(sel)).find((el) => el && visible(el)); "
        "} "
        "if (!btn) return {status: 'NEXT_BUTTON_NOT_FOUND', controls: controls.map(label).slice(0, 20)}; "
        "const clicked = {id: btn.id || null, name: btn.name || null, label: label(btn)}; "
        "const suppressBeforeUnload = (ev) => { "
        "  try { ev.stopImmediatePropagation(); } catch (e) {} "
        "  try { ev.preventDefault(); } catch (e) {} "
        "  try { delete ev.returnValue; } catch (e) {} "
        "  try { ev.returnValue = undefined; } catch (e) {} "
        "}; "
        "window.addEventListener('beforeunload', suppressBeforeUnload, true); "
        "document.addEventListener('beforeunload', suppressBeforeUnload, true); "
        "if (typeof needToConfirm !== 'undefined') needToConfirm = false; "
        "if (document.body) document.body.onbeforeunload = null; "
        "window.onbeforeunload = null; "
        "btn.click(); "
        "return {status: 'NEXT_CLICKED', clicked, mode: 'click'}; "
        "})()"
    )
    click_result = _runtime_eval(ws_url, click_expression)
    click_payload = dict(click_result.get("value") or {})
    if click_payload.get("status") != "NEXT_CLICKED":
        return VisibleControlResult(
            action="click_next_and_wait",
            ok=False,
            payload={"status": click_payload.get("status"), "before_url": before_url},
        )

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            new_ws_url = find_target_websocket_url("ceac.state.gov/GenNIV/General/complete/")
            _accept_javascript_dialog(new_ws_url)
            probe = _runtime_eval(new_ws_url, probe_expression)
            new_url = dict(probe.get("value") or {}).get("url") or ""
            if new_url and new_url != before_url:
                title = dict(probe.get("value") or {}).get("title") or ""
                new_page_key = _detect_page_key(new_url, title)
                return VisibleControlResult(
                    action="click_next_and_wait",
                    ok=True,
                    payload={
                        "before_url": before_url,
                        "new_url": new_url,
                        "new_page_key": new_page_key,
                    },
                )
        except RuntimeError:
            pass
        time.sleep(0.2)

    return VisibleControlResult(
        action="click_next_and_wait",
        ok=False,
        payload={"status": "TIMEOUT", "before_url": before_url},
    )


def _accept_javascript_dialog(ws_url: str) -> None:
    try:
        with CDPWebSocket(ws_url) as client:
            client.call("Page.handleJavaScriptDialog", {"accept": True})
    except Exception:
        pass


def fill_and_continue(
    page_key: str,
    dossier: ApplicantDossier,
    save_wait_s: float = 2.0,
) -> dict[str, object]:
    """Fill a page via the engine, save, then click Next."""
    handler = _PAGE_FILL_HANDLERS.get(page_key)
    fill_result = None
    if handler:
        fill_result = handler(dossier)
    time.sleep(save_wait_s)
    next_result = click_next_and_wait()
    return {
        "page_key": page_key,
        "fill_ok": bool(fill_result and fill_result.ok),
        "fill_payload": fill_result.payload if fill_result else {},
        "next_ok": next_result.ok,
        "new_page_key": next_result.payload.get("new_page_key"),
        "application_id": detect_current_page().payload.get("application_id"),
    }
