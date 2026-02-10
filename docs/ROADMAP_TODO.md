# PaperBot Roadmap & TODO

> 对标 HuggingFace Daily Papers / AlphaXiv 的完整功能规划。
> 本文件同时作为迭代清单使用：完成一项请将 `[ ]` 更新为 `[x]`。

---

## 对标结论

| 维度 | PaperBot 现状 | 差距 |
|------|--------------|------|
| AI 分析 | **领先**（5 维 Judge + Trend + Insight + Relevance） | — |
| 学者追踪 | **领先**（多 Agent + PIS 评分） | — |
| 深度评审 | **独有**（模拟同行评审） | — |
| Paper2Code | **独有**（论文→代码骨架） | — |
| 多通道推送 | **领先**（Email/Slack/钉钉） | 内容为纯文本，需富文本 |
| 论文持久化 | **缺失** | HF/AlphaXiv 都有完整论文 DB |
| 社区/交互 | 仅 feedback | HF 有 upvote/评论，AlphaXiv 有逐行批注 |
| 论文详情页 | 无 | HF 每篇论文有独立页面 |
| AI 问答 | 无 | AlphaXiv 核心卖点 |
| 个性化推荐 | Track + Memory 骨架 | 未形成推荐闭环 |
| 资源关联 | 无 | HF 关联 Models/Datasets/Demos |
| 学者网络 | S2 客户端已有 | 未暴露 coauthor/引用网络 API |

---

## Phase 1 — 数据根基

> 不做这一步，后续所有功能（Trending/推荐/详情页/收藏）都没有数据基础。

### 1.1 Paper Registry（论文持久化）

- [ ] 新增 `PaperModel` 表
  - 字段：`id`（自增）、`arxiv_id`（唯一索引）、`doi`、`title`、`authors_json`、`abstract`、`url`、`external_url`、`pdf_url`、`source`（papers_cool / arxiv_api / semantic_scholar）、`venue`、`published_at`、`first_seen_at`、`keywords_json`、`metadata_json`
  - 唯一约束：`(arxiv_id)` 或 `(doi)` 去重
  - 文件：`src/paperbot/infrastructure/stores/models.py`
- [ ] 新增 Alembic 迁移
- [ ] 新增 `PaperStore`（CRUD + upsert + 按 arxiv_id/doi 查重）
  - 文件：`src/paperbot/infrastructure/stores/paper_store.py`
- [ ] `build_daily_paper_report()` 完成后自动入库
  - 文件：`src/paperbot/application/workflows/dailypaper.py`
  - 逻辑：遍历 `report["queries"][*]["top_items"]`，逐条 upsert
- [ ] Judge 评分写入 `PaperModel` 或关联表 `paper_judge_scores`
  - 字段：`paper_id`、`query`、`overall`、`relevance`、`novelty`、`rigor`、`impact`、`clarity`、`recommendation`、`one_line_summary`、`scored_at`
- [ ] `PaperFeedbackModel` 的 `paper_id` 关联到 `PaperModel.id`（目前 paper_id 是自由文本）
- [ ] 论文 ID 归一化工具函数 `normalize_paper_id(url_or_id) -> arxiv_id | doi`
  - 文件：`src/paperbot/domain/paper_identity.py`

### 1.2 收藏 / 阅读列表

- [ ] 新增 `PaperReadingStatusModel` 表（或扩展 `PaperFeedbackModel`）
  - 字段：`user_id`、`paper_id`、`status`（unread/reading/read/archived）、`saved_at`、`read_at`
- [ ] API：`GET /api/research/papers/saved`（用户收藏列表，支持排序：judge_score / saved_at / published_at）
- [ ] API：`POST /api/research/papers/{paper_id}/status`（更新阅读状态）
- [ ] API：`GET /api/research/papers/{paper_id}`（论文详情，聚合 judge + feedback + summary）
- [ ] 前端：收藏列表页面组件
  - 文件：`web/src/components/research/SavedPapersList.tsx`

### 1.3 GitHub Repo 关联（Repo Enrichment）

- [ ] 新增 `PaperRepoModel` 表
  - 字段：`paper_id`、`repo_url`、`owner`、`name`、`stars`、`forks`、`last_commit_at`、`language`、`description`、`fetched_at`
- [ ] Enrichment 服务：从论文 abstract/url/external_url 中正则提取 GitHub 链接
  - 文件：`src/paperbot/application/services/repo_enrichment.py`
  - 正则：`github\.com/[\w\-]+/[\w\-]+`
  - 调用 GitHub API 补元数据（stars/forks/language/last_commit）
- [ ] DailyPaper 生成后异步调用 repo enrichment
- [ ] API：`GET /api/research/papers/{paper_id}/repos`
- [ ] API：`GET /api/research/paperscool/repos`（批量，含 stars/活跃度）

---

## Phase 2 — 体验提升

### 2.1 论文详情页

- [ ] 前端页面：`web/src/app/papers/[id]/page.tsx`
  - 基本信息卡片（标题/作者/venue/日期/链接）
  - AI Summary 区块
  - Judge 雷达图（复用现有 `JudgeRadarCard` 组件）
  - Trend 关联（该论文所属 query 的趋势分析）
  - Feedback 操作栏（like/save/cite/dislike）
  - 关联 GitHub Repo 卡片（stars/活跃度/语言）
  - 相似论文列表（Phase 3 实现后接入）
- [ ] API：`GET /api/research/papers/{paper_id}` 聚合返回上述所有数据

### 2.2 AI Chat with Paper

- [ ] API：`POST /api/research/papers/{paper_id}/ask`
  - 请求：`{ "question": "...", "user_id": "..." }`
  - 上下文构建：title + abstract + judge scores + ai_summary + keywords
  - 调用 `LLMService`（task_type=chat）
  - 返回：`{ "answer": "...", "context_used": [...] }`
  - 文件：`src/paperbot/api/routes/paper_qa.py`
- [ ] 前端：论文卡片/详情页的 "Ask AI" 按钮 → 对话弹窗
  - 文件：`web/src/components/research/PaperQADialog.tsx`
- [ ] 可选增强：如果有 PDF URL，抽取全文作为上下文（Phase 3）

### 2.3 富文本推送

- [ ] HTML 邮件模板
  - 文件：`src/paperbot/application/services/templates/daily_email.html`
  - 内容：Top 5 论文卡片（标题+摘要+Judge 评分徽章+链接）、趋势摘要、统计数据
  - 使用 Jinja2 渲染
  - `_send_email()` 发送 `multipart/alternative`（text + html）
- [ ] Slack Block Kit 消息
  - 将 `_send_slack()` 的 `text` payload 替换为 `blocks` 结构
  - 包含 Header Block + Section Blocks（论文卡片）+ Divider
- [ ] 钉钉 Markdown 优化
  - 优化 `_send_dingtalk()` 的 markdown 格式
  - 添加论文链接、评分标签

### 2.4 RSS / Atom Feed

- [ ] API：`GET /api/feed/rss`（最近 N 天的 DailyPaper 聚合为 RSS 2.0）
  - 参数：`days`（默认 7）、`query`（可选过滤）、`track_id`（可选）
  - 文件：`src/paperbot/api/routes/feed.py`
  - 依赖 Paper Registry（从 DB 读取论文列表）
- [ ] API：`GET /api/feed/atom`（Atom 1.0 格式）
- [ ] DailyPaper 生成后同时输出静态 RSS 文件到 `reports/feed.xml`

---

## Phase 3 — 智能推荐与学者网络

### 3.1 学者合作网络（Coauthor Graph）

- [ ] API：`GET /api/research/scholar/network`
  - 参数：`scholar_id`（S2 author ID）、`depth`（默认 1，最大 2）
  - 返回：`{ "nodes": [...], "edges": [...] }`
    - node：`{ "id", "name", "affiliation", "h_index", "paper_count", "citation_count" }`
    - edge：`{ "source", "target", "coauthor_count", "recent_paper_titles" }`
  - 实现：调用 `SemanticScholarClient.get_author()` + `get_author_papers()` → 提取 coauthor → 递归
  - 文件：`src/paperbot/api/routes/scholar.py`
  - 基础设施：`src/paperbot/infrastructure/api_clients/semantic_scholar.py`（已有 `get_author` / `get_author_papers`）
- [ ] 前端：学者关系图可视化（复用 xyflow / d3-force）
  - 文件：`web/src/components/research/ScholarNetworkGraph.tsx`

### 3.2 学者趋势分析

- [ ] API：`GET /api/research/scholar/trends`
  - 参数：`scholar_id`、`years`（默认 5）
  - 返回：
    - `yearly_stats`：`[{ "year", "paper_count", "citation_count", "top_venues" }]`
    - `topic_migration`：`[{ "period", "keywords", "shift_direction" }]`（LLM 生成）
    - `citation_velocity`：`{ "recent_3y_avg", "historical_avg", "trend" }`
    - `collaboration_trend`：`{ "unique_coauthors_per_year", "new_collaborators" }`
  - 实现：
    - 基础统计：从 S2 author papers 聚合
    - 主题迁移：复用 `TrendAnalyzer`（`analysis/trend_analyzer.py`），输入学者各年代表论文
  - 文件：`src/paperbot/application/services/scholar_trends.py`
- [ ] 前端：学者趋势图表（年度发表量/引用趋势/主题变迁时间线）
  - 文件：`web/src/components/research/ScholarTrendsChart.tsx`

### 3.3 个性化推荐（Re-rank）

- [ ] 兴趣向量提取
  - 从用户 feedback（like/save 的论文 title+abstract）+ Track keywords 构建兴趣 embedding
  - 文件：`src/paperbot/application/services/interest_profile.py`
  - 复用 `ResearchTrackEmbeddingModel` 的 embedding 能力
- [ ] DailyPaper re-rank
  - 在 `build_daily_paper_report()` 之后、输出之前，用兴趣向量对 `global_top` 重排序
  - `personalized_score = base_score * 0.5 + interest_similarity * 0.3 + judge_overall * 0.2`
- [ ] API：`GET /api/research/recommended`（为你推荐，基于 Track + Feedback）
- [ ] 前端："为你推荐" 区块（DailyPaper 页面或独立页面）

### 3.4 论文 Trending

- [ ] Trending 评分公式
  - `trending_score = judge_overall * 0.4 + feedback_likes * 0.3 + recency_decay * 0.2 + repo_stars * 0.1`
  - `recency_decay = exp(-days_since_publish / 14)`
- [ ] API：`GET /api/research/trending`
  - 参数：`days`（默认 7）、`limit`（默认 20）、`track_id`（可选）
  - 依赖 Paper Registry + Judge 分数 + Feedback 数据
- [ ] 前端：Trending 页面
  - 文件：`web/src/app/trending/page.tsx`

### 3.5 相似论文推荐

- [ ] 论文 Embedding 存储
  - 新增 `PaperEmbeddingModel` 表（paper_id、model、embedding_json、dim）
  - DailyPaper 入库后异步计算 title+abstract embedding
- [ ] 相似度检索
  - 给定 paper_id → 取其 embedding → cosine similarity top-K
  - 文件：`src/paperbot/application/services/paper_similarity.py`
- [ ] API：`GET /api/research/papers/{paper_id}/similar`
- [ ] 前端：论文详情页 "Related Papers" 区块

### 3.6 订阅管理（Per-Topic / Per-Author）

- [ ] 新增 `SubscriptionModel` 表
  - 字段：`user_id`、`type`（keyword/author/venue）、`value`（具体关键词/作者 ID/venue 名）、`notify_channels`（email/slack/dingtalk）、`enabled`、`created_at`
- [ ] API：`POST /api/research/subscriptions`（创建订阅）
- [ ] API：`GET /api/research/subscriptions`（列出订阅）
- [ ] API：`DELETE /api/research/subscriptions/{id}`
- [ ] ARQ Cron：按订阅配置生成个性化 DailyPaper
  - 每个订阅独立生成搜索结果 → 合并 → 推送
  - 文件：`src/paperbot/infrastructure/queue/arq_worker.py`
- [ ] 有新匹配论文时触发推送（增量检测：对比上次推送的论文 ID 列表）

---

## Phase 4 — 平台化能力（远期）

> 以下功能视需求和资源情况推进，不急于落地。

### 4.1 多用户体系

- [ ] 用户注册/登录（JWT / OAuth2）
- [ ] API Key 管理
- [ ] 用户隔离（所有查询带 user_id scope）

### 4.2 社区交互

- [ ] 论文评论系统（评论表 + API）
- [ ] Upvote 系统（基于 `PaperFeedbackModel.action = "upvote"`）
- [ ] 作者 Claiming（关联 S2 author ID 到用户账户）

### 4.3 浏览器集成

- [ ] Chrome 插件：arXiv 页面注入 PaperBot Judge 评分 + AI Summary
- [ ] URL 替换：`arxiv.org` → `paperbot.xxx/papers/arxiv_id`

### 4.4 全文 PDF 处理

- [ ] PDF 下载 + 文本提取
- [ ] 全文索引（用于 AI Chat with Paper 的深度问答）
- [ ] 逐段批注（类 AlphaXiv）

---

## 实现依赖关系

```
Phase 1.1 (Paper Registry)
  ├── Phase 1.2 (收藏/阅读列表)
  ├── Phase 1.3 (Repo Enrichment)
  ├── Phase 2.1 (论文详情页)
  ├── Phase 2.2 (AI Chat with Paper)
  ├── Phase 2.4 (RSS Feed)
  ├── Phase 3.4 (Trending)
  └── Phase 3.5 (相似论文)

Phase 3.1 (学者网络) ── 独立，仅依赖 S2 客户端（已有）
Phase 3.2 (学者趋势) ── 独立，仅依赖 S2 客户端 + TrendAnalyzer（已有）
Phase 2.3 (富文本推送) ── 独立，仅依赖现有 DailyPushService
Phase 3.3 (个性化推荐) ── 依赖 Paper Registry + Embedding
Phase 3.6 (订阅管理) ── 依赖 Paper Registry + DailyPushService
```

## 涉及文件索引

| 文件 | 改动类型 | 关联 Phase |
|------|---------|-----------|
| `src/paperbot/infrastructure/stores/models.py` | 新增 Model | 1.1, 1.2, 1.3, 3.5, 3.6 |
| `src/paperbot/infrastructure/stores/paper_store.py` | **新建** | 1.1 |
| `src/paperbot/domain/paper_identity.py` | **新建** | 1.1 |
| `src/paperbot/application/workflows/dailypaper.py` | 修改 | 1.1, 3.3 |
| `src/paperbot/application/services/repo_enrichment.py` | **新建** | 1.3 |
| `src/paperbot/application/services/scholar_trends.py` | **新建** | 3.2 |
| `src/paperbot/application/services/interest_profile.py` | **新建** | 3.3 |
| `src/paperbot/application/services/paper_similarity.py` | **新建** | 3.5 |
| `src/paperbot/application/services/daily_push_service.py` | 修改 | 2.3 |
| `src/paperbot/application/services/templates/daily_email.html` | **新建** | 2.3 |
| `src/paperbot/api/routes/paper_qa.py` | **新建** | 2.2 |
| `src/paperbot/api/routes/scholar.py` | **新建** | 3.1, 3.2 |
| `src/paperbot/api/routes/feed.py` | **新建** | 2.4 |
| `src/paperbot/api/routes/paperscool.py` | 修改 | 1.1, 1.3 |
| `src/paperbot/api/routes/research.py` | 修改 | 1.2, 3.4 |
| `src/paperbot/infrastructure/api_clients/semantic_scholar.py` | 修改 | 3.1 |
| `src/paperbot/infrastructure/queue/arq_worker.py` | 修改 | 3.6 |
| `web/src/app/papers/[id]/page.tsx` | **新建** | 2.1 |
| `web/src/app/trending/page.tsx` | **新建** | 3.4 |
| `web/src/components/research/PaperQADialog.tsx` | **新建** | 2.2 |
| `web/src/components/research/SavedPapersList.tsx` | **新建** | 1.2 |
| `web/src/components/research/ScholarNetworkGraph.tsx` | **新建** | 3.1 |
| `web/src/components/research/ScholarTrendsChart.tsx` | **新建** | 3.2 |

---

## 现有可复用基础

| 已有能力 | 文件 | 可用于 |
|---------|------|-------|
| S2 作者/论文/引用 API | `infrastructure/api_clients/semantic_scholar.py` | 学者网络、学者趋势 |
| LLM Trend Analyzer | `application/workflows/analysis/trend_analyzer.py` | 学者主题迁移分析 |
| Paper Judge（5 维评分） | `application/workflows/analysis/paper_judge.py` | Trending 评分、详情页 |
| Track + Memory + Feedback | `api/routes/research.py` + stores | 个性化推荐 |
| Track Embedding | `infrastructure/stores/models.py:ResearchTrackEmbeddingModel` | 兴趣向量、相似论文 |
| DailyPushService | `application/services/daily_push_service.py` | 富文本推送 |
| LLMService | `application/services/llm_service.py` | AI Chat with Paper |
| XYFlow DAG | `web/src/components/research/TopicWorkflowDashboard.tsx` | 学者网络图 |

---

## Progress Log

> 每次完成请追加一行：日期 + 简述 + 关联文件

- 2025-02-10: 创建 ROADMAP_TODO.md，完成对标分析与功能规划
