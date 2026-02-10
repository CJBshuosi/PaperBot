# Project Issue Backlog (From ROADMAP_TODO)

This file splits unfinished items in `docs/ROADMAP_TODO.md` into issue-ready cards for GitHub Projects.

## Suggested Labels

- `roadmap`
- `phase-1`, `phase-2`, `phase-3`, `phase-4`
- `backend`, `frontend`, `data-model`, `workflow`, `infra`
- `priority-p0`, `priority-p1`, `priority-p2`

## Issue 1 - Saved Papers Frontend Page

- Title: `[Feature] Saved papers list page and actions`
- Labels: `roadmap`, `phase-1`, `frontend`, `priority-p1`
- Source TODO:
  - `前端：收藏列表页面组件`
- Scope:
  - Implement `web/src/components/research/SavedPapersList.tsx`
  - Consume `GET /api/research/papers/saved`
  - Support sort `judge_score | saved_at | published_at`
  - Add open-detail and status action entry points
- Acceptance:
  - Saved papers render with pagination/limit
  - Sorting works and is testable
  - Empty and loading states are handled

## Issue 2 - Repo Persistence Model and Per-Paper Repo API

- Title: `[Feature] Persist repo enrichment and expose paper repo detail API`
- Labels: `roadmap`, `phase-1`, `backend`, `data-model`, `priority-p1`
- Source TODO:
  - `新增 PaperRepoModel 表`
  - `DailyPaper 生成后异步调用 repo enrichment`
  - `API：GET /api/research/papers/{paper_id}/repos`
- Scope:
  - Add `PaperRepoModel` + migration
  - Persist enrichment output from `/paperscool/repos`
  - Add read API for single paper repos
  - Add async hook after daily generation
- Acceptance:
  - Repo metadata is queryable by paper id
  - Async job does not block daily response latency

## Issue 3 - Paper Detail Page (UI)

- Title: `[Feature] Paper detail page UI aggregation`
- Labels: `roadmap`, `phase-2`, `frontend`, `priority-p1`
- Source TODO:
  - `前端页面：web/src/app/papers/[id]/page.tsx`
- Scope:
  - Render paper base info, judge radar, feedback, repo panel
  - Render trend-related context and related papers placeholder
- Acceptance:
  - Page works from deep link `/papers/{id}`
  - Works with empty fields and fallback states

## Issue 4 - Paper Detail Aggregation API Hardening

- Title: `[Feature] Harden GET /api/research/papers/{paper_id} aggregation contract`
- Labels: `roadmap`, `phase-2`, `backend`, `priority-p1`
- Source TODO:
  - `API：GET /api/research/papers/{paper_id} 聚合返回上述所有数据`
- Scope:
  - Finalize response schema for detail page
  - Include stable sections: paper, reading_status, judge_scores, feedback_summary, repos
  - Add API tests for not-found, partial-data, complete-data
- Acceptance:
  - Frontend can render without shape ambiguity
  - Backward-compatible fields documented

## Issue 5 - Chat with Paper API + Dialog

- Title: `[Feature] Chat with Paper end-to-end`
- Labels: `roadmap`, `phase-2`, `backend`, `frontend`, `priority-p1`
- Source TODO:
  - `API：POST /api/research/papers/{paper_id}/ask`
  - `前端 Ask AI 按钮 + 对话弹窗`
- Scope:
  - Implement ask API using title+abstract+judge context
  - Add dialog UI from list/detail pages
  - Add error budget and timeout handling
- Acceptance:
  - Chat responses are grounded in paper context
  - UI supports retries and failure messaging

## Issue 6 - Full-Text Context for Ask (Optional Advanced)

- Title: `[Enhancement] Add PDF full-text context path for Ask API`
- Labels: `roadmap`, `phase-2`, `backend`, `priority-p2`
- Source TODO:
  - `可选增强：如果有 PDF URL，抽取全文作为上下文`
- Scope:
  - PDF fetch and extraction pipeline
  - Chunking + retrieval for ask endpoint
- Acceptance:
  - Ask quality improves for methods/experiment questions
  - Falls back cleanly when PDF unavailable

## Issue 7 - Rich Push Channels (Email/Slack/DingTalk)

- Title: `[Feature] Rich push formatting for daily digest`
- Labels: `roadmap`, `phase-2`, `backend`, `priority-p1`
- Source TODO:
  - `HTML 邮件模板`
  - `Slack Block Kit 消息`
  - `钉钉 Markdown 优化`
- Scope:
  - Implement HTML email template
  - Implement Slack blocks payload
  - Improve DingTalk markdown layout
- Acceptance:
  - Push output is structured and readable across channels

## Issue 8 - RSS/Atom Feed Export

- Title: `[Feature] RSS and Atom feed endpoints for DailyPaper`
- Labels: `roadmap`, `phase-2`, `backend`, `priority-p1`
- Source TODO:
  - `GET /api/feed/rss`
  - `GET /api/feed/atom`
  - `输出静态 RSS 文件`
- Scope:
  - Feed generation service + endpoints
  - Optional static `reports/feed.xml`
- Acceptance:
  - Valid RSS 2.0 and Atom 1.0 output
  - Supports recent-N and optional filters

## Issue 9 - Scholar Graph/Trend Frontend Visualization

- Title: `[Feature] Scholar network and trend visualization UI`
- Labels: `roadmap`, `phase-3`, `frontend`, `priority-p1`
- Source TODO:
  - `前端：学者关系图可视化`
  - `前端：学者趋势图表`
- Scope:
  - `ScholarNetworkGraph.tsx`
  - `ScholarTrendsChart.tsx`
  - Integrate with existing `/scholar/network|trends` APIs
- Acceptance:
  - Interactive graph + trend charts are stable with 10-200 nodes

## Issue 10 - Personalized Recommendation Pipeline

- Title: `[Feature] Personalized re-rank and recommendation endpoint`
- Labels: `roadmap`, `phase-3`, `backend`, `workflow`, `priority-p1`
- Source TODO:
  - `兴趣向量提取`
  - `DailyPaper re-rank`
  - `GET /api/research/recommended`
  - `前端 为你推荐 区块`
- Scope:
  - Interest profile service from feedback + track
  - Re-rank formula in daily workflow
  - Recommendation API + minimal UI block
- Acceptance:
  - Recommendations differ by user behavior
  - Score composition is observable/debuggable

## Issue 11 - Trending Papers Feature

- Title: `[Feature] Trending papers API and page`
- Labels: `roadmap`, `phase-3`, `backend`, `frontend`, `priority-p1`
- Source TODO:
  - `Trending 评分公式`
  - `GET /api/research/trending`
  - `前端 Trending 页面`
- Scope:
  - Implement trending score blend and endpoint
  - Add frontend page with filters
- Acceptance:
  - Trending list updates over time and is explainable

## Issue 12 - Similar Papers Retrieval

- Title: `[Feature] Similar paper retrieval via embeddings`
- Labels: `roadmap`, `phase-3`, `backend`, `priority-p1`
- Source TODO:
  - `论文 Embedding 存储`
  - `相似度检索`
  - `GET /api/research/papers/{paper_id}/similar`
  - `详情页 Related Papers`
- Scope:
  - Embedding model/table + async generation
  - Similarity service and endpoint
  - UI integration in paper detail page
- Acceptance:
  - Related papers are semantically relevant and deterministic

## Issue 13 - Subscription System and Scheduled Delivery

- Title: `[Feature] Per-topic/per-author subscriptions with scheduled digests`
- Labels: `roadmap`, `phase-3`, `backend`, `workflow`, `priority-p1`
- Source TODO:
  - `SubscriptionModel`
  - CRUD APIs for subscriptions
  - ARQ cron generation
  - Incremental new-paper detection
- Scope:
  - Model + migration + APIs
  - Scheduler and job execution path
  - Dedup/new-match logic
- Acceptance:
  - User receives only new matching results per subscription

## Issue 14 - OpenClaw Integration Package

- Title: `[Feature] OpenClaw skill integration for PaperBot workflows`
- Labels: `roadmap`, `opclaw`, `integration`, `priority-p2`
- Source TODO:
  - `OpenClaw Skill 包装层`
  - `Skill 调用 PaperBot API`
  - `推送渠道对接`
  - `OpenClaw Cron`
- Scope:
  - Provide OpenClaw-compatible wrappers
  - Connect existing PaperBot APIs and push system
- Acceptance:
  - Daily flow runnable from OpenClaw with end-to-end logs

## Issue 15 - Multi-Agent Framework Upgrade Evaluation

- Title: `[Research] Orchestration framework upgrade plan`
- Labels: `roadmap`, `research`, `priority-p2`
- Source TODO:
  - `评估 LangGraph / CrewAI / AutoGen`
  - `统一 Agent 抽象层`
  - `可观测性增强`
- Scope:
  - Benchmark matrix and migration recommendation
  - RFC for unified agent interface
- Acceptance:
  - Decision doc with measurable tradeoffs and migration steps

## Issue 16 - Platformization Foundation (Multi-user + Community + Extension + PDF)

- Title: `[Epic] Platformization foundation`
- Labels: `roadmap`, `phase-4`, `epic`, `priority-p2`
- Source TODO:
  - Multi-user auth/API key/isolation
  - Community interaction (comment/upvote/claim)
  - Browser extension + URL rewrite
  - PDF full-text indexing/annotation
- Scope:
  - Break into child issues before implementation
- Acceptance:
  - Child issue tree created and scheduled by quarter

---

## Project Board Setup Suggestion

Columns:

1. `Backlog`
2. `Ready`
3. `In Progress`
4. `Review`
5. `Done`

Custom fields:

- `Phase` (P1/P2/P3/P4)
- `Priority` (P0/P1/P2)
- `Area` (Backend/Frontend/Data/Workflow)
- `Size` (S/M/L/XL)
