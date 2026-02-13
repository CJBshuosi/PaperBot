#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from paperbot.application.services.anchor_service import AnchorService
from paperbot.application.services.author_backfill_service import run_author_backfill
from paperbot.infrastructure.stores.author_store import AuthorStore
from paperbot.infrastructure.stores.models import Base, PaperFeedbackModel, ResearchTrackModel
from paperbot.infrastructure.stores.paper_store import PaperStore
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url


REQUIRED_TABLES = {
    "authors",
    "paper_authors",
    "user_anchor_scores",
    "user_anchor_actions",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Anchor Author MVP end-to-end on local DB"
    )
    parser.add_argument("--db-url", default=os.getenv("PAPERBOT_DB_URL") or get_db_url())
    parser.add_argument("--user-id", default="anchor-validator")
    return parser.parse_args()


def ensure_tables(db_url: str) -> list[str]:
    provider = SessionProvider(db_url)
    Base.metadata.create_all(provider.engine)
    tables = set(inspect(provider.engine).get_table_names())
    missing = sorted(REQUIRED_TABLES - tables)
    return missing


def seed_minimal_data(db_url: str, user_id: str) -> tuple[int, int]:
    provider = SessionProvider(db_url)
    paper_store = PaperStore(db_url=db_url)
    author_store = AuthorStore(db_url=db_url)

    with provider.session() as session:
        track = ResearchTrackModel(
            user_id=user_id,
            name="anchor-mvp-track",
            description="validation track",
            keywords_json=json.dumps(["attention", "transformer"]),
            venues_json="[]",
            methods_json="[]",
            is_active=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(track)
        session.commit()
        session.refresh(track)
        track_id = int(track.id)

    paper = paper_store.upsert_paper(
        paper={
            "title": "Attention Validation Paper",
            "abstract": "A transformer attention benchmark.",
            "paper_id": "2502.99999",
            "url": "https://arxiv.org/abs/2502.99999",
            "year": 2025,
            "citation_count": 123,
            "authors": ["Alice Smith", "Bob Lee"],
        },
        source_hint="arxiv",
    )
    paper_id = int(paper["id"])
    author_store.replace_paper_authors(paper_id=paper_id, authors=["Alice Smith", "Bob Lee"])

    with provider.session() as session:
        session.add(
            PaperFeedbackModel(
                user_id=user_id,
                track_id=track_id,
                paper_id=str(paper_id),
                paper_ref_id=paper_id,
                canonical_paper_id=paper_id,
                action="like",
                weight=1.0,
                ts=datetime.now(timezone.utc),
                metadata_json="{}",
            )
        )
        session.commit()

    return track_id, paper_id


def main() -> int:
    args = parse_args()
    missing = ensure_tables(args.db_url)
    if missing:
        print(json.dumps({"ok": False, "error": "missing_tables", "tables": missing}, indent=2))
        return 1

    backfill_stats = run_author_backfill(db_url=args.db_url, limit=50)
    track_id, _paper_id = seed_minimal_data(args.db_url, args.user_id)

    service = AnchorService(db_url=args.db_url)
    personalized = service.discover(
        track_id=track_id,
        user_id=args.user_id,
        limit=5,
        window_years=5,
        personalized=True,
    )
    global_rows = service.discover(
        track_id=track_id,
        user_id=args.user_id,
        limit=5,
        window_years=5,
        personalized=False,
    )

    if not personalized:
        print(json.dumps({"ok": False, "error": "discover_empty"}, indent=2))
        return 2

    first_author_id = int(personalized[0]["author_id"])
    action_payload = service.set_user_anchor_action(
        user_id=args.user_id,
        track_id=track_id,
        author_id=first_author_id,
        action="follow",
    )
    actions = service.get_user_anchor_actions(user_id=args.user_id, track_id=track_id)

    print(
        json.dumps(
            {
                "ok": True,
                "db_url": args.db_url,
                "track_id": track_id,
                "backfill": backfill_stats,
                "personalized_top": personalized[0],
                "global_top": global_rows[0] if global_rows else None,
                "action_payload": action_payload,
                "actions_count": len(actions),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
