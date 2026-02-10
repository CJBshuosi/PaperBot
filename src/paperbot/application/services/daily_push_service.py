from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

import requests

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_list(name: str, default: str = "") -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class DailyPushConfig:
    enabled: bool = False
    channels: List[str] = field(default_factory=list)

    # email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    email_from: str = ""
    email_to: List[str] = field(default_factory=list)

    # slack
    slack_webhook_url: str = ""

    # dingtalk
    dingtalk_webhook_url: str = ""
    dingtalk_secret: str = ""

    # shared
    timeout_seconds: float = 15.0
    subject_prefix: str = "[PaperBot Daily]"


class DailyPushService:
    """Push DailyPaper digest to email/slack/dingtalk."""

    def __init__(self, config: DailyPushConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "DailyPushService":
        config = DailyPushConfig(
            enabled=_env_bool("PAPERBOT_NOTIFY_ENABLED", False),
            channels=_env_list("PAPERBOT_NOTIFY_CHANNELS", ""),
            smtp_host=os.getenv("PAPERBOT_NOTIFY_SMTP_HOST", "").strip(),
            smtp_port=int(os.getenv("PAPERBOT_NOTIFY_SMTP_PORT", "587")),
            smtp_username=os.getenv("PAPERBOT_NOTIFY_SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("PAPERBOT_NOTIFY_SMTP_PASSWORD", "").strip(),
            smtp_use_tls=_env_bool("PAPERBOT_NOTIFY_SMTP_USE_TLS", True),
            smtp_use_ssl=_env_bool("PAPERBOT_NOTIFY_SMTP_USE_SSL", False),
            email_from=os.getenv("PAPERBOT_NOTIFY_EMAIL_FROM", "").strip(),
            email_to=_env_list("PAPERBOT_NOTIFY_EMAIL_TO", ""),
            slack_webhook_url=os.getenv("PAPERBOT_NOTIFY_SLACK_WEBHOOK_URL", "").strip(),
            dingtalk_webhook_url=os.getenv("PAPERBOT_NOTIFY_DINGTALK_WEBHOOK_URL", "").strip(),
            dingtalk_secret=os.getenv("PAPERBOT_NOTIFY_DINGTALK_SECRET", "").strip(),
            timeout_seconds=float(os.getenv("PAPERBOT_NOTIFY_TIMEOUT_SECONDS", "15")),
            subject_prefix=os.getenv("PAPERBOT_NOTIFY_SUBJECT_PREFIX", "[PaperBot Daily]").strip()
            or "[PaperBot Daily]",
        )
        return cls(config=config)

    def push_dailypaper(
        self,
        *,
        report: Dict[str, Any],
        markdown: str = "",
        markdown_path: Optional[str] = None,
        json_path: Optional[str] = None,
        channels_override: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        channels = channels_override or self.config.channels
        channels = [c.strip().lower() for c in channels if c and c.strip()]

        if not self.config.enabled:
            return {"sent": False, "reason": "notify disabled", "channels": channels}
        if not channels:
            return {"sent": False, "reason": "no channels configured", "channels": channels}

        subject = self._build_subject(report)
        text = self._build_text(
            report, markdown=markdown, markdown_path=markdown_path, json_path=json_path
        )

        results: Dict[str, Any] = {"sent": False, "channels": channels, "results": {}}
        any_success = False
        for channel in channels:
            try:
                if channel == "email":
                    self._send_email(subject=subject, body=text)
                elif channel == "slack":
                    self._send_slack(subject=subject, body=text)
                elif channel in {"dingtalk", "dingding"}:
                    self._send_dingtalk(subject=subject, body=text)
                else:
                    raise ValueError(f"unsupported channel: {channel}")
                results["results"][channel] = {"ok": True}
                any_success = True
            except Exception as exc:  # pragma: no cover - runtime specific
                logger.warning("Daily push failed channel=%s err=%s", channel, exc)
                results["results"][channel] = {"ok": False, "error": str(exc)}

        results["sent"] = any_success
        return results

    def _build_subject(self, report: Dict[str, Any]) -> str:
        title = str(report.get("title") or "DailyPaper Digest").strip()
        date = str(report.get("date") or "").strip()
        if date:
            return f"{self.config.subject_prefix} {title} - {date}"
        return f"{self.config.subject_prefix} {title}"

    def _build_text(
        self,
        report: Dict[str, Any],
        *,
        markdown: str,
        markdown_path: Optional[str],
        json_path: Optional[str],
    ) -> str:
        stats = report.get("stats") or {}
        lines: List[str] = []
        lines.append(str(report.get("title") or "DailyPaper Digest"))
        lines.append("Date: " + str(report.get("date") or "-"))
        lines.append("Unique Items: " + str(stats.get("unique_items", 0)))
        lines.append("Total Query Hits: " + str(stats.get("total_query_hits", 0)))
        lines.append("")

        global_top = list(report.get("global_top") or [])[:5]
        if global_top:
            lines.append("Top 5 Papers:")
            for idx, item in enumerate(global_top, start=1):
                title = item.get("title") or "Untitled"
                score = float(item.get("score") or 0)
                url = item.get("url") or ""
                if url:
                    lines.append(f"{idx}. {title} (score={score:.4f})\n   {url}")
                else:
                    lines.append(f"{idx}. {title} (score={score:.4f})")
            lines.append("")

        if markdown_path:
            lines.append(f"Markdown: {markdown_path}")
        if json_path:
            lines.append(f"JSON: {json_path}")

        if markdown and not markdown_path:
            lines.append("")
            lines.append("---")
            lines.append(markdown[:3000])

        return "\n".join(lines).strip()

    def _send_email(self, *, subject: str, body: str) -> None:
        if not self.config.smtp_host:
            raise ValueError("PAPERBOT_NOTIFY_SMTP_HOST is required for email notifications")
        if not self.config.email_to:
            raise ValueError("PAPERBOT_NOTIFY_EMAIL_TO is required for email notifications")

        from_addr = self.config.email_from or self.config.smtp_username
        if not from_addr:
            raise ValueError("PAPERBOT_NOTIFY_EMAIL_FROM or SMTP username is required")

        msg = MIMEText(body, _subtype="plain", _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr(("PaperBot", from_addr))
        msg["To"] = ", ".join(self.config.email_to)

        if self.config.smtp_use_ssl:
            server = smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=self.config.timeout_seconds,
            )
        else:
            server = smtplib.SMTP(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=self.config.timeout_seconds,
            )

        with server:
            server.ehlo()
            if self.config.smtp_use_tls and not self.config.smtp_use_ssl:
                server.starttls()
                server.ehlo()
            if self.config.smtp_username:
                server.login(self.config.smtp_username, self.config.smtp_password)
            server.sendmail(from_addr, self.config.email_to, msg.as_string())

    def _send_slack(self, *, subject: str, body: str) -> None:
        url = self.config.slack_webhook_url
        if not url:
            raise ValueError(
                "PAPERBOT_NOTIFY_SLACK_WEBHOOK_URL is required for slack notifications"
            )

        # Keep payload compact to avoid webhook payload limits.
        text = f"*{subject}*\n```{body[:3500]}```"
        resp = requests.post(
            url,
            json={"text": text},
            timeout=self.config.timeout_seconds,
        )
        resp.raise_for_status()

    def _send_dingtalk(self, *, subject: str, body: str) -> None:
        url = self.config.dingtalk_webhook_url
        if not url:
            raise ValueError(
                "PAPERBOT_NOTIFY_DINGTALK_WEBHOOK_URL is required for dingtalk notifications"
            )

        signed_url = self._dingtalk_signed_url(url)
        text = f"### {subject}\n\n{body[:3500]}"
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": subject,
                "text": text,
            },
        }
        resp = requests.post(signed_url, json=payload, timeout=self.config.timeout_seconds)
        resp.raise_for_status()

        # DingTalk webhook returns JSON with errcode=0 on success.
        data = resp.json() if resp.content else {}
        if isinstance(data, dict) and int(data.get("errcode", 0)) != 0:
            raise RuntimeError(f"dingtalk error: {data}")

    def _dingtalk_signed_url(self, webhook_url: str) -> str:
        secret = self.config.dingtalk_secret
        if not secret:
            return webhook_url

        timestamp = str(int(time.time() * 1000))
        sign_str = f"{timestamp}\n{secret}".encode("utf-8")
        sign = base64.b64encode(
            hmac.new(secret.encode("utf-8"), sign_str, digestmod=hashlib.sha256).digest()
        )
        sign_qs = quote_plus(sign)

        parsed = urlparse(webhook_url)
        sep = "&" if parsed.query else "?"
        return f"{webhook_url}{sep}timestamp={timestamp}&sign={sign_qs}"
