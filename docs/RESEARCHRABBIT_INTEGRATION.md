# ResearchRabbit-style Integration Plan

Date: 2026-02-14
Branch: `feat/researchrabbit-core-bridge`

## Scope (compliance-first)

We do **not** scrape or reverse-engineer ResearchRabbit internals.  
Interoperability is built through stable export/import channels:

1. BibTeX bridge (MVP)
2. Zotero connector (enhanced bridge)

## Implemented in this branch

### 1) BibTeX bridge (Issue #129)

- Import endpoint: `POST /api/research/papers/import/bibtex`
  - Parses BibTeX entries
  - Upserts papers into PaperBot registry
  - Saves papers into a selected/active/new track
- Export endpoint already existed:
  - `GET /api/research/papers/export?format=bibtex`
- Web entrypoint:
  - Saved Papers page now has **Import BibTeX** dialog (paste-in workflow)

### 2) Zotero connector (Issue #130)

- New connector: `src/paperbot/infrastructure/connectors/zotero_connector.py`
  - Read library items (`user` or `group`)
  - Create library items
  - PaperBot<->Zotero mapping + dedupe key generation
- Pull endpoint: `POST /api/research/integrations/zotero/pull`
  - Pull Zotero items -> PaperBot registry -> save to track
- Push endpoint: `POST /api/research/integrations/zotero/push`
  - Push PaperBot saved papers -> Zotero (supports `dry_run`)
- Web entrypoint:
  - Saved Papers page now has **Zotero Sync** dialog (pull/push)

## Issue mapping

- Epic: #124
- Discovery core:
  - #125 seed-based discovery API
  - #126 graph + timeline view
  - #127 collections workspace
  - #128 recommendation loop
- Bridges:
  - #129 BibTeX bridge
  - #130 Zotero connector

## Notes

- For now, Zotero API key is request-scoped and not persisted.
- Next step can add encrypted per-user integration settings.
