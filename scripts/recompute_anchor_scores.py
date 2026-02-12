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

from paperbot.application.services.anchor_service import AnchorService
from paperbot.infrastructure.stores.models import Base
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recompute anchor author network scores")
    parser.add_argument("--db-url", default=os.getenv("PAPERBOT_DB_URL") or get_db_url())
    parser.add_argument("--window-years", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider = SessionProvider(args.db_url)
    Base.metadata.create_all(provider.engine)

    service = AnchorService(db_url=args.db_url)
    stats = service.recompute_author_network_scores(window_years=args.window_years)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
