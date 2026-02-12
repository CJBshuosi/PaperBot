# Anchor Author MVP Implementation Guide

## 1. Scope

Anchor Author MVP covers a track-scoped author discovery loop:

1. Canonical author modeling (`authors`, `paper_authors`)
2. Backfill from existing `papers.authors_json`
3. Anchor discovery API (`/api/research/tracks/{track_id}/anchors/discover`)
4. Personalized/global scoring toggle
5. User interaction loop (`follow` / `ignore`) and metric logging

## 2. Data Model

Core tables:

- `authors`
  - canonical author entity + latest aggregate stats
- `paper_authors`
  - many-to-many paper-author relationship
- `user_anchor_scores`
  - per-user per-track personalized score snapshots
- `user_anchor_actions`
  - per-user per-track author action (`follow` / `ignore`)

Migration chain:

- `0016_anchor_author_schema`
- `0017_user_anchor_scores`
- `0018_user_anchor_actions`

## 3. Scoring

`AnchorService.discover()` uses weighted scoring:

- intrinsic: paper volume + citation density
- relevance: keyword match against track profile
- network: coauthor propagation score
- personalization: feedback-derived signal (only in personalized mode)

Current total formula:

`total = 0.45*intrinsic + 0.30*relevance + 0.15*network + 0.10*personalization`

Output fields include:

- `score_breakdown`
- `evidence_papers`
- `evidence_status` / `evidence_note`
- `user_action`

## 4. API Surface

### Discover

`GET /api/research/tracks/{track_id}/anchors/discover`

Query params:

- `user_id`
- `limit`
- `window_days`
- `personalized` (`true` / `false`)

### Actions

- `POST /api/research/tracks/{track_id}/anchors/{author_id}/action`
  - body: `{ user_id, action: follow|ignore }`
- `GET /api/research/tracks/{track_id}/anchors/actions?user_id=...`

## 5. Feature Flag and Rollback

Feature flag:

- `PAPERBOT_ENABLE_ANCHOR_AUTHORS=true|false`
- when set to `false`, anchor APIs return `503`

Rollback strategy:

1. set `PAPERBOT_ENABLE_ANCHOR_AUTHORS=false`
2. redeploy API
3. keep schema as-is (non-destructive rollback)
4. re-enable after fix and replay validations

## 6. Operational Validation

Recommended local validation:

```bash
# 1) migrate
PAPERBOT_DB_URL=sqlite:////tmp/paperbot_anchor_mvp.db alembic upgrade head

# 2) backfill existing papers -> authors
PAPERBOT_DB_URL=sqlite:////tmp/paperbot_anchor_mvp.db python scripts/backfill_paper_authors.py

# 3) run mvp validator
PAPERBOT_DB_URL=sqlite:////tmp/paperbot_anchor_mvp.db python scripts/validate_anchor_author_mvp.py
```

Expected:

- validator exits `0`
- discover returns non-empty anchors
- follow/ignore action persists
- personalized/global both available
