#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from paperbot.application.services.author_backfill_service import run_author_backfill
from paperbot.infrastructure.stores.sqlalchemy_db import get_db_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill authors / paper_authors from papers.authors_json"
    )
    parser.add_argument("--db-url", default=os.getenv("PAPERBOT_DB_URL") or get_db_url())
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--paper-id", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats = run_author_backfill(db_url=args.db_url, limit=args.limit, paper_id=args.paper_id)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
