from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class ResendEmailService:
    """Send emails via the Resend REST API (no SDK dependency)."""

    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, from_email: str, unsub_base_url: str):
        self.api_key = api_key
        self.from_email = from_email
        self.unsub_base_url = unsub_base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> Optional["ResendEmailService"]:
        api_key = os.getenv("PAPERBOT_RESEND_API_KEY", "").strip()
        if not api_key:
            return None
        from_email = os.getenv(
            "PAPERBOT_RESEND_FROM", "PaperBot <noreply@paperbot.dev>"
        )
        unsub_base_url = os.getenv(
            "PAPERBOT_RESEND_UNSUB_URL", "http://localhost:3000"
        )
        return cls(
            api_key=api_key,
            from_email=from_email,
            unsub_base_url=unsub_base_url,
        )

    def send(
        self, *, to: List[str], subject: str, html_body: str, text: str
    ) -> Dict[str, Any]:
        resp = requests.post(
            self.API_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "from": self.from_email,
                "to": to,
                "subject": subject,
                "html": html_body,
                "text": text,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def send_digest(
        self,
        *,
        to: List[str],
        report: Dict[str, Any],
        markdown: str,
        unsub_tokens: Dict[str, str],
    ) -> Dict[str, Any]:
        """Send DailyPaper digest to subscribers, each with their own unsubscribe link."""
        results: Dict[str, Any] = {}
        date_str = report.get("date", "")
        subject = f"[PaperBot] {report.get('title', 'DailyPaper Digest')}"
        if date_str:
            subject += f" - {date_str}"

        for email_addr in to:
            token = unsub_tokens.get(email_addr, "")
            unsub_link = f"{self.unsub_base_url}/api/newsletter/unsubscribe/{token}"
            html_body = self._render_html(report, markdown, unsub_link)
            text = self._render_text(report, markdown, unsub_link)
            try:
                r = self.send(
                    to=[email_addr], subject=subject, html_body=html_body, text=text
                )
                results[email_addr] = {"ok": True, "id": r.get("id")}
            except Exception as e:
                logger.warning("Resend failed for %s: %s", email_addr, e)
                results[email_addr] = {"ok": False, "error": str(e)}
        return results

    def _render_html(
        self, report: Dict[str, Any], markdown: str, unsub_link: str
    ) -> str:
        from paperbot.application.services.email_template import build_digest_html

        return build_digest_html(report, unsub_link=unsub_link)

    def _render_text(
        self, report: Dict[str, Any], markdown: str, unsub_link: str
    ) -> str:
        from paperbot.application.services.email_template import build_digest_text

        return build_digest_text(report, unsub_link=unsub_link)
