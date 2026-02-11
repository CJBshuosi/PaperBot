"""Tests for newsletter subscription system."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from paperbot.infrastructure.stores.subscriber_store import SubscriberStore


@pytest.fixture()
def store(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    return SubscriberStore(db_url=db_url, auto_create_schema=True)


class TestSubscriberStore:
    def test_add_subscriber(self, store: SubscriberStore):
        result = store.add_subscriber("alice@example.com")
        assert result["email"] == "alice@example.com"
        assert result["status"] == "active"
        assert result["unsub_token"]

    def test_add_subscriber_idempotent(self, store: SubscriberStore):
        r1 = store.add_subscriber("bob@example.com")
        r2 = store.add_subscriber("bob@example.com")
        assert r1["email"] == r2["email"]
        assert r1["unsub_token"] == r2["unsub_token"]

    def test_add_subscriber_normalizes_email(self, store: SubscriberStore):
        result = store.add_subscriber("  Alice@Example.COM  ")
        assert result["email"] == "alice@example.com"

    def test_remove_subscriber(self, store: SubscriberStore):
        sub = store.add_subscriber("charlie@example.com")
        ok = store.remove_subscriber(sub["unsub_token"])
        assert ok is True
        info = store.get_subscriber_by_email("charlie@example.com")
        assert info is not None
        assert info["status"] == "unsubscribed"

    def test_remove_subscriber_invalid_token(self, store: SubscriberStore):
        ok = store.remove_subscriber("nonexistent_token")
        assert ok is False

    def test_remove_subscriber_idempotent(self, store: SubscriberStore):
        sub = store.add_subscriber("dave@example.com")
        store.remove_subscriber(sub["unsub_token"])
        ok = store.remove_subscriber(sub["unsub_token"])
        assert ok is True

    def test_resubscribe_after_unsubscribe(self, store: SubscriberStore):
        sub = store.add_subscriber("eve@example.com")
        store.remove_subscriber(sub["unsub_token"])
        resub = store.add_subscriber("eve@example.com")
        assert resub["status"] == "active"
        assert resub["unsub_at"] is None

    def test_get_active_subscribers(self, store: SubscriberStore):
        store.add_subscriber("a@example.com")
        store.add_subscriber("b@example.com")
        sub_c = store.add_subscriber("c@example.com")
        store.remove_subscriber(sub_c["unsub_token"])

        active = store.get_active_subscribers()
        assert sorted(active) == ["a@example.com", "b@example.com"]

    def test_get_active_subscribers_with_tokens(self, store: SubscriberStore):
        store.add_subscriber("x@example.com")
        store.add_subscriber("y@example.com")
        tokens = store.get_active_subscribers_with_tokens()
        assert len(tokens) == 2
        assert "x@example.com" in tokens
        assert "y@example.com" in tokens

    def test_get_subscriber_count(self, store: SubscriberStore):
        store.add_subscriber("one@example.com")
        sub = store.add_subscriber("two@example.com")
        store.remove_subscriber(sub["unsub_token"])

        counts = store.get_subscriber_count()
        assert counts["active"] == 1
        assert counts["total"] == 2

    def test_get_subscriber_by_email_not_found(self, store: SubscriberStore):
        assert store.get_subscriber_by_email("nobody@example.com") is None


class TestResendEmailService:
    def test_from_env_returns_none_without_key(self):
        from paperbot.application.services.resend_service import ResendEmailService

        with patch.dict("os.environ", {}, clear=True):
            svc = ResendEmailService.from_env()
            assert svc is None

    def test_from_env_returns_instance_with_key(self):
        from paperbot.application.services.resend_service import ResendEmailService

        env = {"PAPERBOT_RESEND_API_KEY": "re_test_key"}
        with patch.dict("os.environ", env, clear=True):
            svc = ResendEmailService.from_env()
            assert svc is not None
            assert svc.api_key == "re_test_key"

    def test_render_text(self):
        from paperbot.application.services.resend_service import ResendEmailService

        svc = ResendEmailService(
            api_key="test", from_email="test@test.com", unsub_base_url="https://example.com"
        )
        report = {
            "title": "Test Digest",
            "date": "2026-02-11",
            "stats": {"unique_items": 3},
            "global_top": [
                {"title": "Paper A", "url": "https://arxiv.org/abs/1", "score": 9.5},
                {"title": "Paper B", "url": "", "score": 8.0},
            ],
        }
        text = svc._render_text(report, "", "https://example.com/unsub/abc")
        assert "Test Digest" in text
        assert "Paper A" in text
        assert "Unsubscribe" in text

    def test_render_html(self):
        from paperbot.application.services.resend_service import ResendEmailService

        svc = ResendEmailService(
            api_key="test", from_email="test@test.com", unsub_base_url="https://example.com"
        )
        report = {
            "title": "Test Digest",
            "date": "2026-02-11",
            "stats": {"unique_items": 1, "total_query_hits": 5},
            "global_top": [
                {
                    "title": "Paper X",
                    "url": "https://arxiv.org/abs/2",
                    "score": 7.0,
                    "judge": {"recommendation": "must_read", "one_line_summary": "Great paper"},
                },
            ],
        }
        html = svc._render_html(report, "", "https://example.com/unsub/xyz")
        assert "PaperBot" in html
        assert "Paper X" in html
        assert "Must Read" in html
        assert "Unsubscribe" in html


class TestNewsletterRoutes:
    @pytest.fixture()
    def client(self, tmp_path):
        import os
        os.environ["PAPERBOT_DB_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
        from fastapi.testclient import TestClient
        from paperbot.api.main import app
        return TestClient(app)

    def test_subscribe(self, client):
        resp = client.post("/api/newsletter/subscribe", json={"email": "test@example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["email"] == "test@example.com"

    def test_subscribe_invalid_email(self, client):
        resp = client.post("/api/newsletter/subscribe", json={"email": "not-an-email"})
        assert resp.status_code == 400

    def test_subscribers_count(self, client):
        client.post("/api/newsletter/subscribe", json={"email": "a@example.com"})
        client.post("/api/newsletter/subscribe", json={"email": "b@example.com"})
        resp = client.get("/api/newsletter/subscribers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] >= 2

    def test_unsubscribe_invalid_token(self, client):
        resp = client.get("/api/newsletter/unsubscribe/invalid_token_123")
        assert resp.status_code == 404
