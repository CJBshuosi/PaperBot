from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

from paperbot.domain.paper_identity import normalize_arxiv_id, normalize_doi


class ZoteroConnector:
    """Thin wrapper around Zotero Web API with PaperBot mapping helpers."""

    def __init__(self, *, timeout_s: float = 30.0, base_url: str = "https://api.zotero.org"):
        self.timeout_s = timeout_s
        self.base_url = base_url.rstrip("/")
        self._user_agent = "PaperBot/2.0"

    def list_items(
        self,
        *,
        api_key: str,
        library_type: str,
        library_id: str,
        limit: int = 100,
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}{self._library_path(library_type, library_id)}/items"
        response = requests.get(
            url,
            headers=self._headers(api_key),
            params={
                "format": "json",
                "limit": max(1, min(int(limit), 100)),
                "start": max(0, int(start)),
            },
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def list_all_items(
        self,
        *,
        api_key: str,
        library_type: str,
        library_id: str,
        max_items: int = 200,
    ) -> List[Dict[str, Any]]:
        remaining = max(1, int(max_items))
        offset = 0
        rows: List[Dict[str, Any]] = []
        while remaining > 0:
            batch_size = min(remaining, 100)
            page = self.list_items(
                api_key=api_key,
                library_type=library_type,
                library_id=library_id,
                limit=batch_size,
                start=offset,
            )
            if not page:
                break
            rows.extend(page)
            if len(page) < batch_size:
                break
            remaining -= len(page)
            offset += len(page)
        return rows

    def create_items(
        self,
        *,
        api_key: str,
        library_type: str,
        library_id: str,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not items:
            return {}
        url = f"{self.base_url}{self._library_path(library_type, library_id)}/items"
        response = requests.post(
            url,
            headers=self._headers(api_key, include_json=True),
            json=items,
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def zotero_item_to_paper(item: Dict[str, Any]) -> Dict[str, Any]:
        record = (item or {}).get("data") if isinstance(item, dict) else {}
        if not isinstance(record, dict):
            record = {}

        title = str(record.get("title") or "").strip()
        doi = normalize_doi(record.get("DOI"))
        url = str(record.get("url") or "").strip()
        archive_location = str(record.get("archiveLocation") or "").strip()
        arxiv_id = normalize_arxiv_id(archive_location) or normalize_arxiv_id(url)
        if not arxiv_id:
            extra = str(record.get("extra") or "")
            match = re.search(r"arxiv\s*:\s*([^\s;]+)", extra, flags=re.IGNORECASE)
            if match:
                arxiv_id = normalize_arxiv_id(match.group(1))

        venue = str(
            record.get("publicationTitle")
            or record.get("proceedingsTitle")
            or record.get("conferenceName")
            or record.get("bookTitle")
            or record.get("journalAbbreviation")
            or ""
        ).strip()
        year = ZoteroConnector._extract_year(record.get("date"))
        authors = ZoteroConnector._extract_creators(record.get("creators"))

        identities: List[Dict[str, str]] = []
        if doi:
            identities.append({"source": "doi", "external_id": doi})
        if arxiv_id:
            identities.append({"source": "arxiv", "external_id": arxiv_id})

        return {
            "title": title,
            "abstract": str(record.get("abstractNote") or "").strip(),
            "authors": authors,
            "year": year,
            "venue": venue,
            "doi": doi,
            "url": url,
            "arxiv_id": arxiv_id,
            "source": "zotero",
            "primary_source": "zotero",
            "identities": identities,
            "zotero_key": str((item or {}).get("key") or record.get("key") or ""),
        }

    @staticmethod
    def paper_to_zotero_item(paper: Dict[str, Any]) -> Dict[str, Any]:
        title = str((paper or {}).get("title") or "").strip()
        creators = [
            ZoteroConnector._name_to_creator(author) for author in paper.get("authors") or []
        ]
        payload: Dict[str, Any] = {
            "itemType": "journalArticle",
            "title": title,
            "creators": [creator for creator in creators if creator],
        }

        year_raw = paper.get("year")
        if year_raw is not None:
            payload["date"] = str(year_raw)
        venue = str(paper.get("venue") or "").strip()
        if venue:
            payload["publicationTitle"] = venue
        abstract = str(paper.get("abstract") or "").strip()
        if abstract:
            payload["abstractNote"] = abstract
        doi = normalize_doi(paper.get("doi"))
        if doi:
            payload["DOI"] = doi
        url = str(paper.get("url") or "").strip()
        if url:
            payload["url"] = url
        arxiv_id = normalize_arxiv_id(paper.get("arxiv_id"))
        if arxiv_id:
            payload["archive"] = "arXiv"
            payload["archiveLocation"] = arxiv_id
        return payload

    @staticmethod
    def item_dedupe_key(item: Dict[str, Any]) -> Optional[str]:
        return ZoteroConnector.paper_dedupe_key(ZoteroConnector.zotero_item_to_paper(item))

    @staticmethod
    def paper_dedupe_key(paper: Dict[str, Any]) -> Optional[str]:
        doi = normalize_doi(paper.get("doi"))
        if doi:
            return f"doi:{doi}"
        arxiv_id = normalize_arxiv_id(paper.get("arxiv_id"))
        if arxiv_id:
            return f"arxiv:{arxiv_id.lower()}"
        url = str(paper.get("url") or "").strip().lower()
        if url:
            return f"url:{url}"
        title = re.sub(r"\s+", " ", str(paper.get("title") or "").strip().lower())
        if not title:
            return None
        year = str(paper.get("year") or "")
        return f"title:{title}|{year}"

    def _library_path(self, library_type: str, library_id: str) -> str:
        bucket = str(library_type or "").strip().lower()
        if bucket not in {"user", "group"}:
            raise ValueError("library_type must be 'user' or 'group'")
        external_id = str(library_id or "").strip()
        if not external_id:
            raise ValueError("library_id is required")
        return f"/{bucket}s/{external_id}"

    def _headers(self, api_key: str, *, include_json: bool = False) -> Dict[str, str]:
        headers = {
            "Zotero-API-Key": str(api_key or "").strip(),
            "Zotero-API-Version": "3",
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }
        if include_json:
            headers["Content-Type"] = "application/json"
        return headers

    @staticmethod
    def _extract_year(value: Any) -> Optional[int]:
        match = re.search(r"(19|20)\d{2}", str(value or ""))
        if not match:
            return None
        try:
            return int(match.group(0))
        except Exception:
            return None

    @staticmethod
    def _extract_creators(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        names: List[str] = []
        for creator in value:
            if not isinstance(creator, dict):
                continue
            creator_type = str(creator.get("creatorType") or "").strip().lower()
            if creator_type and creator_type not in {"author", "editor"}:
                continue
            full_name = str(creator.get("name") or "").strip()
            if full_name:
                names.append(full_name)
                continue
            first_name = str(creator.get("firstName") or "").strip()
            last_name = str(creator.get("lastName") or "").strip()
            merged = f"{first_name} {last_name}".strip()
            if merged:
                names.append(merged)
        return names

    @staticmethod
    def _name_to_creator(value: Any) -> Dict[str, str]:
        text = str(value or "").strip()
        if not text:
            return {}
        parts = text.split()
        if len(parts) >= 2:
            return {
                "creatorType": "author",
                "firstName": " ".join(parts[:-1]),
                "lastName": parts[-1],
            }
        return {"creatorType": "author", "name": text}
