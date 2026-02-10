# PaperBot

论文检索、LLM 评审、学者追踪与 Paper2Code 的研究工作流工具链。

**后端** Python + FastAPI（SSE 流式） · **前端** Next.js Web + Ink CLI · **数据源** papers.cool / arXiv API / Semantic Scholar

## 核心功能

| 模块 | 说明 |
|------|------|
| **Topic Search** | 多主题聚合检索，支持 papers.cool + arXiv API 双数据源，跨 query/branch 去重与评分排序，`min_score` 质量过滤 |
| **DailyPaper** | 日报生成（Markdown/JSON），可选 LLM 增强（摘要/趋势/洞察/相关性），支持定时推送（Email/Slack/钉钉） |
| **LLM-as-Judge** | 5 维评分（Relevance/Novelty/Rigor/Impact/Clarity）+ 推荐分级（must_read/worth_reading/skim/skip），Token Budget 控制，多轮校准 |
| **Analyze SSE** | Judge + Trend 分析通过 SSE 实时流式推送，前端增量渲染（逐张 Judge 卡片 / 逐条 Trend 分析） |
| **学者追踪** | 定期监测学者论文，多 Agent 协作（Research/Code/Quality/Reviewer），PIS 影响力评分（引用速度、趋势动量） |
| **深度评审** | 模拟同行评审（初筛→深度批评→决策），输出 Summary/Strengths/Weaknesses/Novelty Score |
| **Paper2Code** | 论文到代码骨架（Planning→Analysis→Generation→Verification），自愈调试，Docker/E2B 沙箱执行 |
| **个性化研究** | Research Track 管理、记忆 Inbox（LLM/规则抽取）、Context Engine 路由与推荐 |
| **每日推送** | DailyPaper 生成后自动推送摘要到 Email/Slack/钉钉，支持 API 手动触发和 ARQ Cron 定时推送 |

## 模块成熟度

| 模块 | 状态 | API | CLI | 说明 |
|------|------|-----|-----|------|
| Topic Search | ✅ 可用 | `/research/paperscool/search` | `topic-search` | 双数据源（papers.cool + arXiv API），评分/去重/min_score 过滤均已落地 |
| DailyPaper | ✅ 可用 | `/research/paperscool/daily` | `daily-paper` | 报告生成 + LLM 增强 + Judge + 保存，完整可用 |
| LLM-as-Judge | ✅ 可用 | `/research/paperscool/analyze` | `--with-judge` | 5 维评分 + 多轮校准 + 推荐分级 + Token Budget，SSE 增量推送 |
| Analyze SSE | ✅ 可用 | `/research/paperscool/analyze` | — | Judge / Trend / Insight 三通道 SSE 流式，前端逐卡片渲染 |
| Push/Notify | ✅ 可用 | `/research/paperscool/daily` | `--notify` | Email（SMTP）/ Slack（Webhook）/ 钉钉（签名），ARQ Cron 定时推送 |
| 学者追踪 | 🟡 基本可用 | `/track` | `track` | 多 Agent 管线 + PIS 评分完整；依赖 Semantic Scholar API Key |
| 深度评审 | 🟡 基本可用 | `/review` | `review` | 模拟同行评审流程完整；输出质量取决于 LLM 后端配置 |
| Paper2Code | 🟡 基本可用 | `/gen-code` | `gen-code` | 编排 + RAG + CodeMemory 完整；需配置 Docker 或 E2B 沙箱运行验证 |
| 记忆系统 | 🔴 早期 | `/research/memory/*` | — | Schema + Extractor + Parsers 骨架已搭建；LLM 抽取与检索回路待完善 |
| Context Engine | 🔴 早期 | `/research/context` | — | Track Router + Engine 框架已有；推荐策略与 Embedding 集成待落地 |

> ✅ 可用 = 核心功能完整、API/CLI 已接通、可直接使用
> 🟡 基本可用 = 实现完整但有外部依赖或配置要求
> 🔴 早期 = 骨架已搭建，核心流程待完善

## 架构

> 完整架构图（可编辑）：[Excalidraw](asset/architecture.excalidraw) · [drawio](asset/architecture.drawio)

```
┌─────────────────────────────────────────────────────────────────┐
│  Clients:  Web (Next.js)  ·  CLI (Ink)  ·  ARQ Cron  ·  Push  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────── FastAPI Gateway (SSE) ───────────────────────┐
│  /search  /daily  /analyze  /track  /review  /gen-code  /chat  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─ Application ──────────────────────────────────────────────────┐
│  TopicSearch · DailyPaper · ScholarPipeline · Paper2Code       │
│  LLM-as-Judge · TrendAnalyzer · Summarizer · ReviewerAgent     │
│  ContextEngine · PushService · VerificationAgent               │
└────────────────────────────┬───────────────────────────────────┘
                             ▼
┌─ Infrastructure ───────────────────────────────────────────────┐
│  ModelRouter (OpenAI/NIM/OR)  ·  SQLite  ·  ARQ  ·  Docker/E2B│
└────────────────────────────┬───────────────────────────────────┘
                             ▼
┌─ External Sources ─────────────────────────────────────────────┐
│  papers.cool  ·  arXiv API  ·  Semantic Scholar  ·  GitHub     │
│  HuggingFace  ·  OpenReview                                    │
└────────────────────────────────────────────────────────────────┘
```

### 数据流

```
                   ┌─── papers.cool (arxiv/venue branch)
Input Queries ──→  ├─── arXiv API (relevance sort)
                   └─── (extensible: TopicSearchSource protocol)
                              │
                    Normalize → Dedup → Score → min_score Filter
                              │
                   ┌── DailyPaper Report (Markdown / JSON)
                   ├── LLM Enrichment (summary / trends / insight)
                   ├── LLM-as-Judge (5-dim scoring, SSE stream)
                   ├── Save to disk / Push to channels
                   └── Web UI (DAG + Tabs: Papers / Insights / Judge)
```

## 界面预览

### Terminal UI（Ink）

![PaperBot CLI Demo](asset/ui/paperbot%20cli%20demo.jpg)

### Web Dashboard（Next.js）

![Dashboard](asset/ui/dashboard.jpg)

| 论文分析 | 学者画像 |
|----------|----------|
| ![Paper](asset/ui/paper.jpg) | ![Scholar](asset/ui/scholar2.jpg) |

| Wiki 知识库 | DeepCode Studio |
|-------------|-----------------|
| ![Wiki](asset/ui/wiki.jpg) | ![Studio](asset/ui/deepcode.jpg) |

### Topic Workflow

| DAG + 配置面板 | DailyPaper 报告 |
|---------------|----------------|
| ![DAG](asset/ui/9-3.png) | ![Report](asset/ui/9-1.png) |

| 论文卡片 | Insights + Trends |
|---------|-------------------|
| ![Cards](asset/ui/9-2.png) | ![Insights](asset/ui/9-4.png) |

| Judge 评分卡片 | Judge 雷达图详情 |
|---------------|-----------------|
| ![Judge Cards](asset/ui/9-4.png) | ![Judge Radar](asset/ui/9-5.png) |

## 快速开始

### 1) 安装

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 可选
pip install jinja2 openreview-py huggingface_hub
```

### 2) 配置

```bash
cp env.example .env
```

至少配置一个 LLM Key（如 `OPENAI_API_KEY`），否则 LLM 相关功能不可用。

<details>
<summary>LLM 后端配置（点击展开）</summary>

支持多种 LLM 后端，由 `ModelRouter` 按任务类型自动路由：

| 任务类型 | 路由目标 | 典型模型 |
|---------|---------|---------|
| default / extraction / summary / chat | default | MiniMax M2.1 / gpt-4o-mini |
| analysis / reasoning / review / judge | reasoning | GLM 4.7 / DeepSeek R1 |
| code | code | gpt-4o |

```bash
# OpenAI（默认）
OPENAI_API_KEY=sk-...

# NVIDIA NIM（OpenAI-compatible）
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MINIMAX_API_KEY=nvapi-...
NVIDIA_GLM_API_KEY=nvapi-...

# OpenRouter（DeepSeek R1 等 thinking model）
OPENROUTER_API_KEY=sk-or-v1-...

# 显式覆盖（优先级最高）
LLM_DEFAULT_MODEL=...
LLM_REASONING_MODEL=...
```

</details>

<details>
<summary>每日推送配置（点击展开）</summary>

```bash
# 通知渠道
PAPERBOT_NOTIFY_ENABLED=true
PAPERBOT_NOTIFY_CHANNELS=email,slack,dingding

# Email (SMTP)
PAPERBOT_NOTIFY_SMTP_HOST=smtp.example.com
PAPERBOT_NOTIFY_SMTP_USERNAME=...
PAPERBOT_NOTIFY_SMTP_PASSWORD=...
PAPERBOT_NOTIFY_EMAIL_FROM=bot@example.com
PAPERBOT_NOTIFY_EMAIL_TO=you@example.com

# Slack
PAPERBOT_NOTIFY_SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# 钉钉（支持签名验证）
PAPERBOT_NOTIFY_DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=...
PAPERBOT_NOTIFY_DINGTALK_SECRET=SEC...

# DailyPaper 定时任务
PAPERBOT_DAILYPAPER_ENABLED=true
PAPERBOT_DAILYPAPER_CRON_HOUR=8
PAPERBOT_DAILYPAPER_CRON_MINUTE=30
PAPERBOT_DAILYPAPER_NOTIFY_ENABLED=true
PAPERBOT_DAILYPAPER_NOTIFY_CHANNELS=email,slack
```

</details>

### 3) 启动

```bash
# DB 迁移（首次）
alembic upgrade head

# API 服务器
python -m uvicorn src.paperbot.api.main:app --reload --port 8000

# Web（另一个终端）
cd web && npm install && npm run dev

# CLI（可选）
cd cli && npm install && npm run build && npm start

# ARQ Worker — 定时任务（可选）
arq paperbot.infrastructure.queue.arq_worker.WorkerSettings
```

后端非默认地址时：
- CLI：`PAPERBOT_API_URL=http://<host>:8000`
- Web：`PAPERBOT_API_BASE_URL=http://<host>:8000`

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/track` | GET | 学者追踪（SSE） |
| `/api/analyze` | POST | 论文分析（SSE） |
| `/api/gen-code` | POST | Paper2Code（SSE） |
| `/api/review` | POST | 深度评审（SSE） |
| `/api/chat` | POST | AI 对话（SSE） |
| `/api/research/paperscool/search` | POST | 主题检索（多源聚合，支持 `min_score` 过滤） |
| `/api/research/paperscool/daily` | POST | DailyPaper 日报（支持 `notify` 推送） |
| `/api/research/paperscool/analyze` | POST | Judge + Trend 流式分析（SSE） |
| `/api/research/tracks` | GET/POST | 研究方向管理 |
| `/api/research/memory/*` | GET/POST | 记忆系统（Inbox/审核/检索） |
| `/api/research/papers/feedback` | POST | 论文反馈（like/dislike/save） |
| `/api/research/context` | POST | ContextPack 构建（含 Track Router） |
| `/api/sandbox/*` | GET/POST | 沙箱执行与日志 |
| `/api/runbook/*` | GET/POST | Workspace 文件操作与 Diff |

## CLI 命令

```bash
# 学者追踪
python main.py track --summary
python main.py track --scholar-id 1741101

# 顶会论文下载（IEEE S&P / NDSS / ACM CCS / USENIX Security）
python main.py --conference ccs --year 23

# 深度评审
python main.py review --title "..." --abstract "..."

# 声明验证
python main.py verify --title "..." --abstract "..." --num-claims 5

# Paper2Code
python main.py gen-code --title "..." --abstract "..." --output-dir ./output

# 主题检索
python -m paperbot.presentation.cli.main topic-search \
  -q "ICL压缩" -q "KV Cache加速" \
  --source papers_cool --source arxiv_api --branch arxiv --branch venue

# DailyPaper（含 LLM + Judge + 推送）
python -m paperbot.presentation.cli.main daily-paper \
  -q "ICL压缩" -q "KV Cache加速" \
  --with-llm --llm-feature summary --llm-feature trends --llm-feature insight \
  --with-judge --judge-runs 2 --judge-max-items 5 \
  --save --notify --notify-channel email
```

## 目录结构

```text
PaperBot/
├── src/paperbot/
│   ├── agents/                        # Agents（研究/代码/评审/验证/追踪）
│   ├── api/                           # FastAPI 后端（SSE 流式）
│   │   └── routes/                    # 业务路由（track/analyze/paperscool/sandbox/...）
│   ├── application/
│   │   ├── services/                  # 统一服务（LLM/Push/...）
│   │   └── workflows/
│   │       ├── paperscool_topic_search.py  # 主题检索（多源聚合 + min_score）
│   │       ├── topic_search_sources.py     # 数据源注册（papers_cool / arxiv_api）
│   │       ├── dailypaper.py               # 日报生成、LLM 增强、Judge 评分
│   │       └── analysis/                   # Judge / Trend / Summarizer / Relevance
│   ├── core/                          # 核心抽象（pipeline/errors/DI）
│   ├── domain/                        # 领域模型（paper/scholar/influence/PIS）
│   ├── infrastructure/
│   │   ├── connectors/                # 外部数据源连接器（papers.cool / arXiv / S2）
│   │   ├── stores/                    # SQLAlchemy 模型 + Alembic 迁移
│   │   └── queue/                     # ARQ Worker（定时任务 + DailyPaper Cron）
│   ├── memory/                        # 记忆中间件（导入/抽取/检索）
│   ├── context_engine/                # Context Engine（Track Router / 推荐）
│   ├── presentation/                  # CLI 入口与 Markdown 报告渲染
│   └── repro/                         # Paper2Code（Blueprint/CodeMemory/RAG/Debugger）
├── web/                               # Next.js Web Dashboard
├── cli/                               # Ink/React Terminal UI
├── docs/                              # 项目文档
├── config/                            # 配置（models/venues/subscriptions）
├── tests/                             # 测试
├── asset/                             # 截图 + 架构图（drawio / excalidraw）
├── main.py                            # Python CLI 入口
└── env.example                        # 环境变量模板
```

## Roadmap

> 详细评估与可执行计划见 [`docs/PLAN.md`](docs/PLAN.md)

### Phase 1 — 稳定性与一致性（P0）

收敛重复实现（下载/抓取统一）、统一网络请求层（退避/限速/熔断）、补齐解析契约测试、日志从 `print` 迁移到结构化 JSON、统一多智能体 `run_id/trace_id` 与消息 envelope。

### Phase 2 — 数据与运营能力（P1）

DB 持久化（统一主数据模型 Paper/Scholar/Event/Run）、任务队列/调度（幂等/重试/死信）、指标与告警（抓取成功率/LLM 失败率/成本）、长期记忆 MVP（Run/Episodic + Semantic Memory）。

### Phase 3 — 平台化与企业级治理（P2/P3）

Source Registry 与插件化（配置驱动注册）、MCP 工具互操作、多租户/权限/审计/配额、OpenTelemetry 可观测性、密钥管理与合规审计。

## 文档索引

| 文档 | 说明 |
|------|------|
| [`docs/PLAN.md`](docs/PLAN.md) | 总体路线图与详细评估 |
| [`docs/PAPERSCOOL_WORKFLOW.md`](docs/PAPERSCOOL_WORKFLOW.md) | Topic Workflow 端到端流程与配置 |
| [`docs/DEEPCODE_TODO.md`](docs/DEEPCODE_TODO.md) | Paper2Code 迭代清单 |
| [`docs/memory.md`](docs/memory.md) | 记忆系统设计文档 |
| [`docs/TOPIC_SOURCE_TEMPLATE.md`](docs/TOPIC_SOURCE_TEMPLATE.md) | 数据源开发模板 |

## 测试

```bash
pytest -q
```

## 致谢

- [Qc-TX](https://github.com/Qc-TX) 对爬虫脚本的贡献
- 多 Agent 协作参考了 [BettaFish](https://github.com/666ghj/BettaFish) InsightEngine 的公开实现

## License

MIT
