from __future__ import annotations

from visa_agent.browser.live_form_fill import detect_current_page, fill_current_supported_page
from visa_agent.schema import ApplicantDossier


def assist_current_visible_page(dossier: ApplicantDossier):
    return fill_current_supported_page(dossier)


def inspect_current_visible_page():
    return detect_current_page()

