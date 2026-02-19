#!/usr/bin/env python3
"""Backfill paper_identifiers from papers table columns and
canonical_paper_id from paper_feedback.

Usage:
    python scripts/backfill_identifiers.py [--db-url sqlite:///...]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure src/ is importable
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlalchemy import select  # noqa: E402
from paperbot.application.services.identity_resolver import IdentityResolver  # noqa: E402
from paperbot.infrastructure.stores.models import (  # noqa: E402
    Base,
    PaperFeedbackModel,
    PaperIdentifierModel,
    PaperModel,
)
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url  # noqa: E402


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def backfill_identifiers(provider: SessionProvider) -> dict:
    """Populate paper_identifiers from papers columns."""
    now = _utcnow()
    created = 0
    skipped = 0

    with provider.session() as session:
        papers = session.execute(select(PaperModel)).scalars().all()
        for paper in papers:
            pairs: list[tuple[str, str]] = []
            if paper.semantic_scholar_id:
                pairs.append(("semantic_scholar", paper.semantic_scholar_id))
            if paper.arxiv_id:
                pairs.append(("arxiv", paper.arxiv_id))
            if paper.openalex_id:
                pairs.append(("openalex", paper.openalex_id))
            if paper.doi:
                pairs.append(("doi", paper.doi))

            for source, eid in pairs:
                existing = session.execute(
                    select(PaperIdentifierModel).where(
                        PaperIdentifierModel.source == source,
                        PaperIdentifierModel.external_id == eid,
                    )
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        PaperIdentifierModel(
                            paper_id=paper.id,
                            source=source,
                            external_id=eid,
                            created_at=now,
                        )
                    )
                    created += 1
                else:
                    skipped += 1

        session.commit()

    return {"identifiers_created": created, "identifiers_skipped": skipped}


def backfill_canonical_paper_id(provider: SessionProvider, db_url: str) -> dict:
    """Populate paper_feedback.canonical_paper_id from paper_ref_id / IdentityResolver."""
    resolver = IdentityResolver(db_url=db_url)
    updated = 0
    resolved_from_ref = 0
    resolved_from_identity = 0
    unresolved = 0
    with provider.session() as session:
        rows = (
            session.execute(
                select(PaperFeedbackModel).where(
                    PaperFeedbackModel.canonical_paper_id.is_(None),
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            resolved_id = int(row.paper_ref_id) if row.paper_ref_id is not None else None
            if resolved_id is None:
                try:
                    metadata = json.loads(row.metadata_json or "{}")
                    if not isinstance(metadata, dict):
                        metadata = {}
                except Exception:
                    metadata = {}
                resolved_id = resolver.resolve(str(row.paper_id or "").strip(), hints=metadata)

            if resolved_id is not None:
                row.canonical_paper_id = int(resolved_id)
                updated += 1
                if row.paper_ref_id is not None:
                    resolved_from_ref += 1
                else:
                    resolved_from_identity += 1
            else:
                unresolved += 1
        session.commit()

    return {
        "feedback_rows_updated": updated,
        "resolved_from_paper_ref_id": resolved_from_ref,
        "resolved_from_identity_resolver": resolved_from_identity,
        "feedback_rows_unresolved": unresolved,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill paper_identifiers")
    parser.add_argument("--db-url", default=None, help="Database URL override")
    args = parser.parse_args()

    db_url = args.db_url or get_db_url()
    provider = SessionProvider(db_url)
    Base.metadata.create_all(provider.engine)

    print("=== Backfilling paper_identifiers ===")
    result1 = backfill_identifiers(provider)
    print(result1)

    print("=== Backfilling canonical_paper_id ===")
    result2 = backfill_canonical_paper_id(provider, db_url)
    print(result2)

    print("Done.")


if __name__ == "__main__":
    main()
