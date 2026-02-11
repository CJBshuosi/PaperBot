from __future__ import annotations

import re
from typing import Optional


_ARXIV_ID_RE = re.compile(
    r"(?P<id>(?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)
_DOI_RE = re.compile(r"(?P<doi>10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)


def normalize_arxiv_id(value: str | None) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None

    lowered = text.lower()
    for marker in ("arxiv.org/abs/", "arxiv.org/pdf/"):
        idx = lowered.find(marker)
        if idx >= 0:
            text = text[idx + len(marker) :]
            break

    text = text.replace("arxiv:", "")
    text = text.split("?", 1)[0].split("#", 1)[0]
    if text.lower().endswith(".pdf"):
        text = text[:-4]
    text = text.strip(" /")

    match = _ARXIV_ID_RE.search(text)
    if not match:
        return None
    return match.group("id")


def normalize_doi(value: str | None) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None

    lowered = text.lower()
    for marker in ("doi.org/", "dx.doi.org/"):
        idx = lowered.find(marker)
        if idx >= 0:
            text = text[idx + len(marker) :]
            break

    text = text.split("?", 1)[0].split("#", 1)[0].strip()
    match = _DOI_RE.search(text)
    if not match:
        return None
    return match.group("doi").strip().lower()


def normalize_paper_id(url_or_id: str | None) -> Optional[str]:
    arxiv_id = normalize_arxiv_id(url_or_id)
    if arxiv_id:
        return f"arxiv:{arxiv_id}"

    doi = normalize_doi(url_or_id)
    if doi:
        return f"doi:{doi}"

    return None
