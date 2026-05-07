"""Generic fill engine that executes PageDefinitions via CDP."""

from __future__ import annotations

import json
from typing import Any

from visa_agent.browser.cdp_client import CDPWebSocket, find_target_websocket_url, list_debug_targets  # noqa: F401
from visa_agent.browser.page_spec import FieldBinding, FillPhase, PageDefinition
from visa_agent.browser.visible_control import VisibleControlResult, _runtime_eval
from visa_agent.schema import ApplicantDossier

# JS helpers injected once at the start of every CDP expression
_JS_HELPERS = (
    "const setText=(sel,val)=>{"
    "const el=document.querySelector(sel);"
    "if(!el)return false;"
    "el.value=val;"
    "el.dispatchEvent(new Event('input',{bubbles:true}));"
    "el.dispatchEvent(new Event('change',{bubbles:true}));"
    "return true};"
    "const setSelect=(sel,val)=>{"
    "const el=document.querySelector(sel);"
    "if(!el)return false;"
    "el.value=val;"
    "el.dispatchEvent(new Event('change',{bubbles:true}));"
    "return true};"
    "const setSelectText=(sel,text)=>{"
    "const el=document.querySelector(sel);"
    "if(!el)return false;"
    "const opt=[...el.options].find(o=>(o.textContent||'').trim()===text);"
    "if(!opt){"
    "const optPartial=[...el.options].find(o=>(o.textContent||'').trim().toLowerCase().includes(text.toLowerCase()));"
    "if(!optPartial)return false;"
    "el.value=optPartial.value}"
    "else{el.value=opt.value}"
    "el.dispatchEvent(new Event('change',{bubbles:true}));"
    "return true};"
    "const setRadio=(name,val)=>{"
    "const el=document.querySelector(`input[name=\"${name}\"][value=\"${val}\"]`);"
    "if(!el)return false;"
    "el.checked=true;"
    "el.dispatchEvent(new Event('click',{bubbles:true}));"
    "el.dispatchEvent(new Event('change',{bubbles:true}));"
    "return true};"
    "const setRadioClick=(name,val)=>{"
    "const el=document.querySelector(`input[name=\"${name}\"][value=\"${val}\"]`);"
    "if(!el)return false;"
    "el.click();"
    "return true};"
    "const setCb=(sel,checked)=>{"
    "const el=document.querySelector(sel);"
    "if(!el)return false;"
    "if(el.checked!==checked)el.click();"
    "return true};"
    "const r={filled:[],missing:[]};"
    "const ok=(name)=>r.filled.push(name);"
    "const miss=(name)=>r.missing.push(name);"
    "const vr={checked:[],mismatches:[]};"
    "const vok=(name)=>vr.checked.push(name);"
    "const vmiss=(name,detail)=>vr.mismatches.push({field:name,detail});"
    "const verifyText=(sel,expected)=>{"
    "const el=document.querySelector(sel);if(!el){vmiss(sel,'ELEMENT_NOT_FOUND');return false}"
    "if(el.value!==expected){vmiss(sel,`got ${el.value}, expected ${expected}`);return false}"
    "vok(sel);return true};"
    "const verifyRadio=(name,val)=>{"
    "const el=document.querySelector(`input[name=\"${name}\"][value=\"${val}\"]`);"
    "if(!el||!el.checked){vmiss(name,`radio ${val} not checked`);return false}"
    "vok(name);return true};"
    "const verifyCb=(sel,expected)=>{"
    "const el=document.querySelector(sel);if(!el){vmiss(sel,'ELEMENT_NOT_FOUND');return false}"
    "if(el.checked!==expected){vmiss(sel,`got ${el.checked}, expected ${expected}`);return false}"
    "vok(sel);return true};"
)


def _resolve_value(field: FieldBinding, dossier: ApplicantDossier) -> str | bool | None:
    """Resolve the value for a field binding from its configured source."""
    if field.resolver is not None:
        return field.resolver(dossier)
    if field.source_path is not None:
        return _resolve_path(dossier, field.source_path)
    return field.hardcoded


def _resolve_path(dossier: ApplicantDossier, path: str) -> Any:
    """Resolve a dotted path like 'identity.surname' on the dossier."""
    parts = path.split(".")
    current: Any = dossier
    for part in parts:
        if current is None:
            return None
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _should_fill(field: FieldBinding, dossier: ApplicantDossier) -> bool:
    """Check whether a field should be included in this fill pass."""
    if field.condition is not None:
        return field.condition(dossier)
    return True


def _generate_fill_js(binding: FieldBinding, value: Any, var_name: str) -> str:
    """Generate a single JS fill expression for a field binding.

    The generated code uses ok(name)/miss(name) to record the result.
    """
    fid = json.dumps(binding.field_id)
    sel = json.dumps(binding.selector)
    val = json.dumps(str(value) if value is not None else "")

    kind = binding.input_kind
    if kind == "text":
        return f"setText({sel},{val})?ok({fid}):miss({fid})"
    elif kind == "select_value":
        return f"setSelect({sel},{val})?ok({fid}):miss({fid})"
    elif kind == "select_text":
        return f"setSelectText({sel},{val})?ok({fid}):miss({fid})"
    elif kind in ("radio_click", "radio"):
        choice = json.dumps(binding.choice_value or "Y")
        name = json.dumps(binding.selector)  # For radios, selector IS the name attribute
        if kind == "radio_click":
            return f"setRadioClick({name},{choice})?ok({fid}):miss({fid})"
        else:
            return f"setRadio({name},{choice})?ok({fid}):miss({fid})"
    elif kind == "checkbox":
        checked = "true" if value else "false"
        return f"setCb({sel},{checked})?ok({fid}):miss({fid})"
    else:
        return f"miss({fid})"


def _generate_verify_js(binding: FieldBinding, expected_value: Any) -> str:
    """Generate JS expression to verify a field's value matches expected."""
    sel = json.dumps(binding.verify_selector or binding.selector)
    val = json.dumps(str(expected_value) if expected_value is not None else "")

    kind = binding.input_kind
    if kind in ("radio_click", "radio"):
        choice = json.dumps(binding.choice_value or "Y")
        return f"verifyRadio({json.dumps(binding.selector)},{choice})"
    elif kind == "checkbox":
        checked = "true" if expected_value else "false"
        return f"verifyCb({sel},{checked})"
    else:
        return f"verifyText({sel},{val})"


def _generate_phase_js(phase: FillPhase, dossier: ApplicantDossier) -> str:
    """Generate the complete JS expression for a fill phase."""
    fill_lines: list[str] = []
    verify_lines: list[str] = []

    for binding in phase.fields:
        if not _should_fill(binding, dossier):
            continue
        value = _resolve_value(binding, dossier)
        fill_lines.append(" " + _generate_fill_js(binding, value))
        if binding.verify:
            verify_lines.append(" " + _generate_verify_js(binding, value))

    lines = ["(()=>{", _JS_HELPERS] + fill_lines
    if verify_lines:
        lines.append(" " + ";".join(verify_lines) + ";")
    lines.append(" return {filled:r.filled,missing:r.missing,validations:vr};})()")

    return "\n".join(lines)


def _find_page_ws_url(page_def: PageDefinition) -> str:
    """Find the WebSocket URL for a CEAC tab matching this page definition."""
    targets = list_debug_targets()
    for target in targets:
        url = target.get("url") or ""
        title = target.get("title") or ""
        if _matches_page_def(page_def, url, title):
            ws_url = target.get("webSocketDebuggerUrl")
            if ws_url:
                return str(ws_url)
    raise RuntimeError(
        f"No target found for page {page_def.page_key!r} "
        f"using matchers {page_def.url_matchers!r}"
    )


def _matches_page_def(page_def: PageDefinition, url: str, title: str) -> bool:
    """Check if a URL/title pair matches a page definition."""
    from urllib.parse import parse_qs, unquote, urlparse

    parsed = urlparse(url)
    node = parse_qs(parsed.query).get("node", [None])[0]
    if node:
        node = unquote(node)
    else:
        marker = "node="
        if marker in url:
            tail = url.split(marker, 1)[1]
            node = unquote(tail.split("&", 1)[0].split("#", 1)[0])

    for matcher in page_def.url_matchers:
        if matcher.startswith("node="):
            node_name = matcher.split("=", 1)[1]
            if node is not None and node == node_name:
                return True
            if matcher in url:
                return True
        elif matcher in title or matcher in url:
            return True
    return False


def execute_phase(
    page_def: PageDefinition, phase: FillPhase, dossier: ApplicantDossier
) -> tuple[list[str], list[str]]:
    """Execute a single fill phase via CDP.

    Returns (filled_field_ids, missing_field_ids).
    """
    # When a phase has a wait_selector, use MutationObserver for deterministic
    # waiting (the selector appears as a DOM reaction to the prior phase).
    # Otherwise, a brief pause lets the browser event loop process the prior
    # interaction — 50 ms is enough for click handlers, not for full DOM changes.
    if phase.wait_selector:
        _wait_for_selector_mutation(page_def, phase.wait_selector)
    elif phase.wait_before_ms > 0:
        _minimal_sleep_ms(50)

    ws_url = _find_page_ws_url(page_def)
    expression = _generate_phase_js(phase, dossier)

    try:
        result = _runtime_eval(ws_url, expression)
        payload = dict(result.get("value") or {})
        return (
            list(payload.get("filled") or []),
            list(payload.get("missing") or []),
        )
    except Exception:
        applicable = [
            b.field_id for b in phase.fields
            if _should_fill(b, dossier)
        ]
        return ([], applicable)


def _minimal_sleep_ms(ms: int) -> None:
    """Minimal yield to let the browser event loop process a prior click/change.

    Used only when no specific DOM-change selector is known.  Kept as small
    as possible — 50 ms is enough for a `click()` handler to fire.
    """
    import time
    time.sleep(ms / 1000.0)


def _wait_for_selector_mutation(
    page_def: PageDefinition, selector: str, timeout_ms: int = 5000,
) -> bool:
    """Wait for a CSS selector via MutationObserver — no polling.

    Injects a script that watches the live DOM with MutationObserver and
    resolves a Promise when the target element appears.  Falls back to
    a timeout so a missing selector never hangs the fill.
    """
    expression = (
        "(() => {"
        f"const sel = {json.dumps(selector)};"
        "if (document.querySelector(sel)) return true;"
        "let _tid;"
        "return new Promise((resolve) => {"
        "const observer = new MutationObserver(() => {"
        "if (document.querySelector(sel)) {"
        "observer.disconnect(); clearTimeout(_tid); resolve(true);"
        "}"
        "});"
        "observer.observe(document.documentElement, {childList:true,subtree:true});"
        f"_tid = setTimeout(() => {{ observer.disconnect(); resolve(false); }}, {timeout_ms});"
        "});"
        "})()"
    )
    try:
        ws_url = _find_page_ws_url(page_def)
        result = _runtime_eval(ws_url, expression)
        return bool(result.get("value", False))
    except Exception:
        return False


def execute_page(page_def: PageDefinition, dossier: ApplicantDossier) -> VisibleControlResult:
    """Execute all phases of a page definition against the live CEAC page.

    Returns a VisibleControlResult compatible with the existing _PAGE_FILL_HANDLERS interface.
    """
    all_filled: list[str] = []
    all_missing: list[str] = []

    for i, phase in enumerate(page_def.phases):
        filled, missing = execute_phase(page_def, phase, dossier)
        all_filled.extend(filled)
        all_missing.extend(missing)

        # If this is not the last phase, re-establish WebSocket connection
        # and check for post-phase selector waits
        if i < len(page_def.phases) - 1:
            for binding in phase.fields:
                if binding.wait_selector_after:
                    _wait_for_selector_mutation(
                        page_def, binding.wait_selector_after
                    )

    return VisibleControlResult(
        action=f"fill_{page_def.page_key}_page",
        ok=len(all_missing) == 0,
        payload={"filled": all_filled, "missing": all_missing},
    )
