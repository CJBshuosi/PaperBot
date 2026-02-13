# 锚点作者系统 — TODO

> 对应设计文档：`anchor_author_implementation.md`
> 理论基础：`anchor_source_authority_model.md`

---

## P0 — 最小闭环：建表 → 回填 → 发现 → 展示

### 数据层

- [ ] `models.py`: 新增 `AuthorModel` (id, name_normalized, display_name, semantic_scholar_id, affiliation, h_index, citation_count, paper_count, resolved_at, created_at)
- [ ] `models.py`: 新增 `PaperAuthorModel` (id, paper_id FK, author_id FK, position)
- [ ] `alembic/versions/0017_authors_tables.py`: 迁移脚本，创建 authors + paper_authors 表
- [ ] `paper_store.py`: 新增 `normalize_author_name()` 函数
- [ ] `paper_store.py`: 新增 `get_or_create_author(name) -> AuthorModel`
- [ ] `paper_store.py`: 新增 `link_paper_authors(paper_id, authors: list[str])` — upsert paper_authors
- [ ] `paper_store.py`: 修改 `upsert_paper()` — 在写入 authors_json 的同时调用 `link_paper_authors()`
- [ ] 回填脚本: `scripts/backfill_paper_authors.py` — 扫描所有 papers.authors_json，填充 authors + paper_authors

### 评分服务

- [ ] `src/paperbot/application/services/anchor_service.py`: 新建锚点评分服务
  - [ ] `objective_score(author_id) -> float` — judge_avg + citation_velocity + venue_tier + h_index
  - [ ] `subjective_score(user_id, author_id) -> float` — save_count + recency + track_spread + first_author_ratio
  - [ ] `compute_calibration(user_id) -> float` — 用户 save 与 judge score 的相关性
  - [ ] `compute_alpha(user_total_saves, calibration) -> float` — 自适应混合权重
  - [ ] `anchor_score(user_id, author_id) -> float` — α × subjective + (1-α) × objective
  - [ ] `discover_anchors(user_id, limit) -> list[dict]` — 返回排序后的锚点作者列表
  - [ ] `community_picks(track_id, limit) -> list[dict]` — 纯客观质量推荐

### API 端点

- [ ] `research.py`: 新增 `GET /research/scholars/discover` — 锚点发现
  - query params: user_id, limit, include_community
  - 返回: anchors + community_picks + blind_spots + user_calibration + alpha

### 前端

- [ ] `web/src/app/api/research/scholars/discover/route.ts`: proxy route
- [ ] `web/src/lib/api.ts`: 替换 `fetchScholars()` — 调用 discover 端点
- [ ] `web/src/app/scholars/page.tsx`: 替换 mock 数据 → 真实锚点列表
  - [ ] Discovered / Subscribed 两个 tab
  - [ ] AuthorCard 组件：name, tier badge, score, save_count, tracks
  - [ ] Community Picks 区域
  - [ ] Blind Spots 提示

### 验证

- [ ] `alembic upgrade head` 无报错
- [ ] `python scripts/backfill_paper_authors.py` 回填成功
- [ ] `pytest -q` 现有测试不破
- [ ] `cd web && npx next build` 前端构建通过
- [ ] 手动验证：/scholars 页面展示真实锚点数据

---

## P1 — 搜索增强：Search Hit Overlay

### 后端

- [ ] `anchor_service.py`: 新增 `compute_anchor_hits(user_id, paper_ids, track_id) -> dict`
  - 交叉匹配搜索结果作者 vs 用户锚点
  - 计算 track 内第 N 篇
  - 返回 summary + by_author 结构
- [ ] `research.py`: 修改搜索端点 — 在返回 papers 的同时附加 `anchor_hits`

### 前端

- [ ] `web/src/components/research/PaperCard.tsx`: 作者名旁显示锚点 badge + track 计数
- [ ] 搜索结果顶部: 新增 AnchorCoverageBanner 组件 — "4/20 results from your anchors"

### 验证

- [ ] 搜索 "transformer" → 结果中锚点作者有 badge 标注
- [ ] 顶部统计栏显示命中率

---

## P2 — 合作网络 + S2 解析

### 后端

- [ ] `anchor_service.py`: 新增 `build_coauthor_network(user_id) -> dict`
  - nodes (authors) + edges (co-author weight) + clusters (institutions)
- [ ] `anchor_service.py`: 新增 `resolve_author_profile(author_id)` — 调 S2 Author Search API
  - 补全 semantic_scholar_id, affiliation, h_index, citation_count
  - 写入 authors 表 + 更新 resolved_at
- [ ] `research.py`: 新增 `GET /research/scholars/network` — 合作网络
- [ ] `research.py`: 新增 `POST /research/scholars/{author_id}/resolve` — 触发解析

### 前端

- [ ] `web/src/app/api/research/scholars/network/route.ts`: proxy route
- [ ] `web/src/app/scholars/page.tsx`: Network tab — 合作网络展示
  - 可选：力导向图（用 d3-force 或简单列表）
  - 机构聚类卡片

### 验证

- [ ] Network tab 展示合作关系
- [ ] Resolve 按钮点击后补全 affiliation/h-index

---

## P3 — 智能推荐 + Context Engine 集成

### 后端

- [ ] `enrichment_pipeline.py`: 新增 `AnchorBoostStep` — 锚点作者论文 judge score boost
- [ ] `anchor_service.py`: 新增 `detect_blind_spots(user_id) -> list[dict]`
- [ ] `anchor_service.py`: 新增 `serendipity_injection(papers, ratio=0.15) -> list`
  - 在搜索结果中混入非锚点但客观质量高的论文
- [ ] Context Engine: 搜索排序中加入 anchor_boost 权重

### 前端

- [ ] Blind Spots 区域: "No anchors in 'CV' track — suggested: ..."
- [ ] 搜索结果中标注 serendipity 论文: "Discover" badge

### 验证

- [ ] 锚点作者新论文在搜索结果中排名靠前
- [ ] Blind spots 正确检测无锚点覆盖的 track

---

## P4 — 高级功能（远期）

- [ ] Author Momentum: 追踪锚点分数随时间变化，检测 rising/cooling
- [ ] Citation Chain Discovery: 锚点作者频繁引用的作者 → 潜在新锚点
- [ ] Track-Author Matrix: 每个 track 的 top 作者排行
- [ ] Institutional Heatmap: 按机构聚合 saved papers 统计
- [ ] Anchor Alert: 锚点作者发布新论文时自动推送
- [ ] Diversity Warning: 锚点过于集中时提醒用户
