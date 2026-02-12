#!/usr/bin/env python3
"""Backfill paper_identifiers from papers table columns and
canonical_paper_id from paper_feedback.

Usage:
    python scripts/backfill_identifiers.py [--db-url sqlite:///...]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure src/ is importable
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlalchemy import select  # noqa: E402
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


def backfill_canonical_paper_id(provider: SessionProvider) -> dict:
    """Populate paper_feedback.canonical_paper_id from paper_ref_id."""
    updated = 0
    with provider.session() as session:
        rows = (
            session.execute(
                select(PaperFeedbackModel).where(
                    PaperFeedbackModel.canonical_paper_id.is_(None),
                    PaperFeedbackModel.paper_ref_id.is_not(None),
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            row.canonical_paper_id = row.paper_ref_id
            updated += 1
        session.commit()

    return {"feedback_rows_updated": updated}


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
    result2 = backfill_canonical_paper_id(provider)
    print(result2)

    print("Done.")


if __name__ == "__main__":
    main()
