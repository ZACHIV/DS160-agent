"""DOM selector drift detection for DS-160 form pages.

Compares expected selectors against what's actually in the live DOM
and reports mismatches as warnings.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from visa_agent.automation.evidence import VisualEvidenceStore
from visa_agent.browser.cdp_client import CDPWebSocket, find_target_websocket_url


SAMPLE_SELECTORS: dict[str, list[str]] = {
    "personal1": [
        "input[name$='surnames']",
        "input[name$='givenNames']",
        "select[name$='gender']",
        "select[name$='maritalStatus']",
    ],
    "personal2": [
        "input[name$='birthCity']",
        "input[name$='birthCountry']",
        "input[name$='nationality']",
        "input[name$='alienPermitNumber']",
    ],
    "passport": [
        "input[name$='passportNumber']",
        "input[name$='passportIssuanceDate']",
        "input[name$='passportExpirationDate']",
    ],
    "travel": [
        "input[name$='purposeOfTrip']",
        "input[name$='intendedArrivalDate']",
        "select[name$='lengthOfStayUnit']",
    ],
    "address_phone": [
        "input[name$='homeAddressLine1']",
        "input[name$='homeCity']",
        "input[name$='homeCountry']",
        "input[name$='primaryPhoneNumber']",
    ],
    "us_contact": [
        "input[name$='usContactName']",
        "input[name$='usContactOrg']",
        "input[name$='usContactAddressLine1']",
    ],
    "work_education_present": [
        "select[name$='primaryOccupation']",
        "input[name$='employerName']",
        "input[name$='employerAddressLine1']",
        "input[name$='monthlyIncome']",
    ],
}


@dataclass
class DriftReport:
    page_key: str
    total_expected: int
    found: int
    missing: list[str] = field(default_factory=list)
    healthy: bool = True
    evidence_path: str | None = None


def _capture_drift_evidence(ws_url: str, page_key: str) -> str | None:
    evidence = VisualEvidenceStore().screenshot(ws_url, kind="drift", label=page_key)
    return evidence.path if evidence else None


def check_page_selectors(
    page_key: str,
    cdp_port: int = 9222,
    *,
    save_evidence_on_warning: bool = True,
) -> DriftReport:
    """Check which expected selectors exist in the current page DOM.

    Requires Chrome running with remote debugging on cdp_port and the
    target DS-160 page to be open.
    """
    expected = SAMPLE_SELECTORS.get(page_key, [])
    if not expected:
        return DriftReport(page_key=page_key, total_expected=0, found=0, healthy=True)

    ws_url = find_target_websocket_url(port=cdp_port)
    if not ws_url:
        return DriftReport(page_key=page_key, total_expected=len(expected), found=0,
                           missing=list(expected), healthy=False)

    missing: list[str] = []
    try:
        with CDPWebSocket(ws_url) as client:
            for selector in expected:
                response = client.call(
                    "Runtime.evaluate",
                    {
                        "expression": f"document.querySelector({selector!r}) !== null",
                        "returnByValue": True,
                    },
                )
                result = response.get("result", {}).get("result", {}).get("value", False)
                if not result:
                    missing.append(selector)
    except Exception:
        evidence_path = _capture_drift_evidence(ws_url, page_key) if save_evidence_on_warning else None
        return DriftReport(page_key=page_key, total_expected=len(expected), found=0,
                           missing=list(expected), healthy=False, evidence_path=evidence_path)

    found = len(expected) - len(missing)
    healthy = len(missing) <= 2 or (len(expected) > 0 and found / len(expected) >= 0.5)
    evidence_path = None
    if not healthy and save_evidence_on_warning:
        evidence_path = _capture_drift_evidence(ws_url, page_key)
    return DriftReport(
        page_key=page_key,
        total_expected=len(expected),
        found=found,
        missing=missing,
        healthy=healthy,
        evidence_path=evidence_path,
    )
