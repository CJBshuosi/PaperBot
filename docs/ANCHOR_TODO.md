# Anchor Author MVP TODO

## P0 Data Foundation

- [x] `authors` / `paper_authors` schema + migration
- [x] author backfill service + CLI
- [x] dual-track anchor scoring service (intrinsic + relevance)
- [x] discover API route
- [x] Research UI uses real anchor data

## P1 Explainability

- [x] structured `score_breakdown`
- [x] evidence backlink fields (`evidence_papers`)
- [x] no-evidence unified copy (`evidence_note`)

## P2 Ranking Enhancements

- [x] network propagation score (`network_score`)
- [x] offline recompute script (`scripts/recompute_anchor_scores.py`)
- [x] personalized score storage (`user_anchor_scores`)
- [x] personalized/global switch in API + UI

## P3 Interaction Loop

- [x] follow/ignore action storage (`user_anchor_actions`)
- [x] action APIs
- [x] Research anchor card actions
- [x] workflow metric logging (`workflow=anchor_action`)

## P4 Validation and Release

- [x] MVP validation script (`scripts/validate_anchor_author_mvp.py`)
- [x] implementation/ops docs (`docs/anchor_author_implementation.md`)
- [x] feature flag and rollback path (`PAPERBOT_ENABLE_ANCHOR_AUTHORS`)

## Release Checklist

- [ ] staging migration dry run
- [ ] production migration window confirmation
- [ ] flip feature flag to `true` in production
- [ ] monitor anchor_action metrics for 48h
- [ ] collect first round user feedback
