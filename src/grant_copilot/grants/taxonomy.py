"""grants.gov facet codes for eligibility-aware search (applicant + category)."""

from __future__ import annotations

# grants.gov "eligibilities" codes (applicant types) — the subset relevant to us.
APPLICANT_TYPES: list[tuple[str, str]] = [
    ("12", "Nonprofit (501(c)(3))"),
    ("13", "Nonprofit (non-501(c)(3))"),
    ("06", "Public / State higher education"),
    ("20", "Private higher education"),
    ("07", "Native American tribal government"),
    ("11", "Native American tribal organization"),
    ("23", "Small business"),
    ("21", "Individual"),
    ("99", "Unrestricted / any"),
]

# grants.gov "fundingCategories" codes.
FOCUS_AREAS: list[tuple[str, str]] = [
    ("ED", "Education"),
    ("ENV", "Environment"),
    ("HL", "Health"),
    ("CD", "Community Development"),
    ("IS", "Income Security & Social Services"),
    ("FN", "Food & Nutrition"),
    ("HO", "Housing"),
    ("ELT", "Employment & Training"),
    ("AR", "Arts"),
    ("HU", "Humanities"),
    ("ST", "Science & Technology"),
    ("NR", "Natural Resources"),
    ("O", "Other"),
]

_APPLICANT_LABELS = dict(APPLICANT_TYPES)
_FOCUS_LABELS = dict(FOCUS_AREAS)


def applicant_label(code: str) -> str:
    return _APPLICANT_LABELS.get(code, code)


def focus_label(code: str) -> str:
    return _FOCUS_LABELS.get(code, code)
