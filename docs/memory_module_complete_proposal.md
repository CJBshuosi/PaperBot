# PaperBot 记忆模块架构设计提案

> 基于 Manus 上下文工程、EverMemOS/Mem0/Zep/Letta 等主流实现、以及 15 篇近期顶会论文的综合调研。

## 1. 调研综述

### 1.1 外部系统调研

| 系统 | 架构 | LoCoMo | LongMemEval-S | 核心思想 |
|------|------|--------|---------------|---------|
| **EverMemOS** | 4 层仿脑架构（engram 启发式） | 92.3% | 82% | 前额叶皮层+大脑皮层网络类比，当前 SOTA |
| **Zep/Graphiti** | 时序知识图谱（Neo4j） | 85.2% | — | 双时态模型，P95 延迟 300ms，检索无需 LLM |
| **Letta** | 文件系统即记忆 | 74.0% | — | 迭代文件搜索优于专用记忆工具 |
| **Mem0** | 向量+图双存储 | 64.2% | — | 生产级 SaaS，自动记忆提取管线 |
| **memU** | 基于文件的 Agent 记忆 | 66.7% | — | 面向 24/7 主动式 Agent |

### 1.2 Manus 上下文工程核心原则

1. **KV-Cache 命中率是第一指标** — 缓存 vs 非缓存 token 成本差 10x
2. **上下文即 RAM** — LLM 是 CPU，上下文窗口是 RAM，需要"操作系统"管理
3. **Raw > Compaction > Summarization** — 可逆压缩优先，不可逆摘要最后手段
4. **文件系统是无限记忆** — 上下文只保留引用，全量数据在外部存储
5. **上下文隔离** — "Share memory by communicating, don't communicate by sharing memory"
6. **渐进式披露（Skills）** — 三级加载：元数据(100 tokens) → 指令(<5k) → 资源(按需)
7. **工具掩码而非移除** — 保持 prompt 前缀稳定以最大化 KV-cache
8. **todo.md 注意力管理** — 将计划写到上下文尾部，利用 transformer 近因偏差

### 1.3 关键论文发现

| 论文 | 会议 | 关键贡献 |
|------|------|---------|
| A-MEM | NeurIPS 2025 | Zettelkasten 式自组织互联笔记网络 |
| HiMem | arXiv 2026.01 | Episode Memory + Note Memory 两层层级 + 冲突感知重整合 |
| Agent Workflow Memory | ICML 2025 | 从历史轨迹归纳可复用工作流模板 |
| RMM (Reflective Memory) | ACL 2025 | 前瞻/回顾双向反思 + RL 精化检索 |
| Memoria | arXiv 2025.12 | SQL + KG + 向量三存储混合，87.1% 准确率 |
| ACE | arXiv 2025.10 | Agent 通过重写上下文自我改进，无需权重更新 |
| TiMem | arXiv 2026.01 | 认知科学启发的时间层级记忆整合 |
| Collaborative Memory | ICML 2025 | 多用户记忆共享 + 动态访问控制 |
| Survey of Context Engineering | arXiv 2025.07 | 165 页综述，1400+ 论文，上下文工程形式化框架 |

---

## 2. PaperBot 现状分析

### 2.1 现有记忆架构

```
src/paperbot/memory/
├── schema.py           # NormalizedMessage, MemoryCandidate, MemoryKind (11种)
├── extractor.py        # 双策略提取：LLM (ModelRouter) + 启发式 (中文正则)
├── __init__.py         # 公共 API
├── eval/collector.py   # 5 个 P0 指标（precision≥85%, FP≤5%, ...）
└── parsers/
    ├── common.py       # 多格式聊天记录解析
    └── types.py        # ParsedChatLog

src/paperbot/context_engine/
├── engine.py           # ContextEngine — build_context_pack() 632 行
├── track_router.py     # TrackRouter — 多特征 track 评分 356 行
└── embeddings.py       # EmbeddingProvider (OpenAI text-embedding-3-small)

src/paperbot/infrastructure/stores/
├── memory_store.py     # SqlAlchemyMemoryStore 658 行（CRUD + 粗粒度搜索）
└── models.py           # MemoryItemModel, MemorySourceModel, MemoryAuditLogModel
```

### 2.2 现有问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **无向量检索** | 🔴 高 | `search_memories()` 使用 SQL `CONTAINS` + 内存 token 评分，无语义匹配 |
| **无时间感知** | 🔴 高 | 记忆无衰减机制，无时序推理能力 |
| **无记忆整合** | 🟡 中 | 记忆只有 CRUD，无 consolidation/forgetting/reconsolidation |
| **层级耦合** | 🟡 中 | ContextEngine 直接依赖 SqlAlchemyMemoryStore，混合 infra 和业务逻辑 |
| **提取策略单一** | 🟡 中 | 启发式仅支持中文正则，LLM 提取依赖 ModelRouter 可用性 |
| **无跨记忆关联** | 🟡 中 | 记忆项之间无链接关系（vs A-MEM 的双向链接） |
| **Scope 隔离不完整** | 🟢 低 | scope_type 有 global/track/project/paper，但 track/paper scope 实际使用有限 |

### 2.3 现有优势（可复用）

- ✅ 完整的 schema 设计（MemoryKind 11 种、scope、confidence、status lifecycle）
- ✅ 审计日志（MemoryAuditLogModel 全量变更记录）
- ✅ PII 检测与脱敏（email/phone 正则）
- ✅ 基于 confidence 的自动审核（≥0.60 自动 approved）
- ✅ 使用量追踪（last_used_at, use_count）
- ✅ 评估指标框架（5 个 P0 指标 + MemoryEvalMetricModel）

---

## 3. 架构设计

### 3.1 设计原则

基于调研结论，采用以下原则：

1. **记忆即基础设施** — 记忆模块是独立的 infra 层服务，不依赖任何业务模块（DailyPaper/Judge/Track）
2. **混合存储** — 结合向量存储（语义）+ 结构化存储（关系/时间）+ 文件存储（全文）
3. **层级记忆** — 参考 HiMem，区分 Episode Memory（具体事件）和 Note Memory（抽象知识）
4. **时间感知** — 参考 Zep/Graphiti 的双时态模型（事件时间 + 录入时间）
5. **渐进式上下文** — 参考 Manus Skills，三级加载控制 token 消耗
6. **自组织链接** — 参考 A-MEM Zettelkasten，记忆项之间建立双向关联
7. **上下文工程 > Prompt 工程** — 整个 context payload（记忆/工具/检索结果）作为工程系统设计

### 3.2 分层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  Application Layer（业务消费者，不属于记忆模块）                        │
│                                                                     │
│  DailyPaper · Judge · TopicSearch · ScholarPipeline · Paper2Code   │
│        ↓                    ↓                    ↓                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Context Assembly Service（上下文装配，属于 application 层）     │   │
│  │  - build_context_pack() 从记忆层获取原料                       │   │
│  │  - 按 task/stage 组装成 prompt-ready 上下文                    │   │
│  │  - 实施 token budget 控制和渐进式披露                          │   │
│  └────────────────────────┬─────────────────────────────────────┘   │
└───────────────────────────│─────────────────────────────────────────┘
                            │ MemoryService Protocol (接口契约)
┌───────────────────────────│─────────────────────────────────────────┐
│  Memory Infrastructure Layer（记忆基础设施，独立模块）                 │
│                            │                                        │
│  ┌─────────────────────────┴──────────────────────────────────┐     │
│  │              MemoryService (Facade)                         │     │
│  │  - write(items)    读写入口                                  │     │
│  │  - recall(query, scope, k)  检索入口                        │     │
│  │  - forget(item_id, reason)  删除/过期                       │     │
│  │  - consolidate()   定期整合                                  │     │
│  │  - link(a, b, relation)   建立关联                          │     │
│  └────────┬───────────┬──────────────┬────────────────────────┘     │
│           │           │              │                              │
│  ┌────────▼───┐ ┌─────▼──────┐ ┌────▼─────────┐                   │
│  │ Extractor  │ │ Retriever  │ │ Consolidator │                   │
│  │ (Write)    │ │ (Read)     │ │ (Maintain)   │                   │
│  ├────────────┤ ├────────────┤ ├──────────────┤                   │
│  │ LLM 提取   │ │ 向量检索    │ │ 记忆衰减      │                   │
│  │ 规则提取   │ │ 关键词匹配  │ │ 冲突检测      │                   │
│  │ 结构化导入 │ │ 图遍历     │ │ Episode→Note │                   │
│  │ 自动标签   │ │ 时间过滤   │ │ 链接维护      │                   │
│  │ PII 检测   │ │ scope 过滤 │ │ 过期清理      │                   │
│  └────────┬───┘ └─────┬──────┘ └──────┬───────┘                   │
│           │           │               │                            │
│  ┌────────▼───────────▼───────────────▼───────────────────────┐    │
│  │                  Storage Backends                           │    │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐              │    │
│  │  │ SQLite   │  │ Vector    │  │ File       │              │    │
│  │  │ (结构化)  │  │ (语义)    │  │ (全文/导出) │              │    │
│  │  │          │  │           │  │            │              │    │
│  │  │ items    │  │ embeddings│  │ episodes   │              │    │
│  │  │ links    │  │ (dim=1536)│  │ exports    │              │    │
│  │  │ audit    │  │           │  │ snapshots  │              │    │
│  │  │ sources  │  │           │  │            │              │    │
│  │  └──────────┘  └───────────┘  └────────────┘              │    │
│  └────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
```

### 3.3 核心抽象（Protocol 层）

记忆模块对外暴露的接口契约，所有业务模块通过此协议消费记忆服务：

```python
# src/paperbot/memory/protocol.py

from typing import Protocol, Optional, Sequence
from dataclasses import dataclass

@dataclass(frozen=True)
class MemoryItem:
    """一条记忆项（infrastructure 不关心业务含义）"""
    id: str
    kind: str                    # profile/preference/fact/note/episode/...
    content: str                 # 记忆内容文本
    scope_type: str              # global/track/project/paper
    scope_id: Optional[str]
    confidence: float            # 0.0~1.0
    tags: tuple[str, ...]
    created_at: str              # ISO 8601
    event_at: Optional[str]      # 事件发生时间（双时态）
    use_count: int
    last_used_at: Optional[str]
    linked_ids: tuple[str, ...]  # 关联的其他记忆 ID

@dataclass(frozen=True)
class RecallResult:
    """检索结果"""
    items: Sequence[MemoryItem]
    scores: Sequence[float]      # 与 items 一一对应的相关性分数
    token_count: int             # 估算的 token 消耗

class MemoryService(Protocol):
    """记忆服务的接口契约 — 业务层只依赖此协议"""

    def write(
        self,
        user_id: str,
        items: Sequence[dict],       # kind, content, scope_type, ...
        source: str = "api",         # 来源标识
    ) -> Sequence[str]:              # 返回写入的 item IDs
        ...

    def recall(
        self,
        user_id: str,
        query: str,
        *,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        kinds: Optional[Sequence[str]] = None,
        top_k: int = 10,
        max_tokens: int = 2000,
        recency_weight: float = 0.2,
    ) -> RecallResult:
        ...

    def forget(
        self,
        user_id: str,
        item_id: str,
        reason: str = "user_request",
    ) -> bool:
        ...

    def consolidate(
        self,
        user_id: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> int:                       # 返回整合/清理的记忆条数
        ...

    def link(
        self,
        item_a_id: str,
        item_b_id: str,
        relation: str = "related",  # related/supports/contradicts/supersedes
    ) -> bool:
        ...

    def build_context_block(
        self,
        user_id: str,
        query: str,
        *,
        max_tokens: int = 1500,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> str:
        """便捷方法：recall + 格式化为 prompt-ready 文本块"""
        ...
```

### 3.4 记忆类型体系

参考 HiMem（Episode + Note）和 A-MEM（Zettelkasten）设计两层记忆：

```
Memory Types
├── Episode Memory（具体事件记忆）
│   ├── paper_read:    用户阅读了某篇论文
│   ├── search_query:  用户执行的搜索查询
│   ├── feedback:      用户对论文的 like/dislike/save
│   ├── workflow_run:  执行了 DailyPaper/Judge/Analyze 流程
│   └── interaction:   用户与系统的对话片段
│
└── Note Memory（抽象知识记忆）
    ├── profile:       用户身份信息（姓名/机构/职称）
    ├── preference:    用户偏好（语言/格式/模型选择）
    ├── interest:      研究兴趣（主题/方法/venue）
    ├── fact:          用户陈述的事实
    ├── goal:          研究目标
    ├── constraint:    约束条件（deadline/scope）
    ├── decision:      用户做出的决定
    └── insight:       从论文中提炼的洞察
```

**Episode → Note 整合规则**（Consolidator 负责）：

| Episode 类型 | 整合目标 | 触发条件 |
|-------------|---------|---------|
| 多次 `paper_read` 同领域 | → `interest` Note | ≥3 篇同 keyword 论文 |
| 多次 `feedback` like | → `preference` Note | ≥5 次 like 同 venue/method |
| `search_query` 重复模式 | → `interest` Note | ≥3 次相似查询 |
| `workflow_run` 常用配置 | → `preference` Note | ≥3 次相同 workflow 参数 |

### 3.5 存储层设计

#### 3.5.1 SQLite 结构化存储（主存储）

扩展现有 `MemoryItemModel`，新增字段：

```sql
-- 记忆项（扩展现有表）
ALTER TABLE memory_items ADD COLUMN memory_layer TEXT DEFAULT 'note';
  -- 'episode' | 'note'
ALTER TABLE memory_items ADD COLUMN event_at TEXT;
  -- 双时态：事件发生时间（vs 已有的 created_at 录入时间）
ALTER TABLE memory_items ADD COLUMN embedding_id TEXT;
  -- 关联到 memory_embeddings 表
ALTER TABLE memory_items ADD COLUMN decay_factor REAL DEFAULT 1.0;
  -- 衰减因子，定期更新

-- 记忆关联（新表）
CREATE TABLE memory_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL DEFAULT 'related',
      -- related | supports | contradicts | supersedes | derived_from
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    UNIQUE(source_id, target_id, relation),
    FOREIGN KEY (source_id) REFERENCES memory_items(id),
    FOREIGN KEY (target_id) REFERENCES memory_items(id)
);

-- 记忆向量（新表）
CREATE TABLE memory_embeddings (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
    embedding BLOB NOT NULL,  -- numpy float32 序列化
    dim INTEGER NOT NULL DEFAULT 1536,
    created_at TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES memory_items(id)
);
```

#### 3.5.2 向量检索策略

考虑到 PaperBot 是单用户/小团队工具，不需要大规模向量数据库：

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| **SQLite + numpy cosine** | 零依赖，现有技术栈 | 线性扫描，>10K 条时变慢 | ✅ Phase 1 |
| **sqlite-vec** | SQLite 扩展，原生向量 | 需编译安装 | Phase 2 |
| **Qdrant (本地模式)** | 高性能 ANN | 新增依赖 | Phase 3 (可选) |
| **FAISS** | 成熟高效 | C++ 编译依赖 | Phase 3 (可选) |

**Phase 1 实现**：在 `memory_embeddings` 表中存储 embedding blob，检索时加载到内存做 cosine similarity。对于 < 5000 条记忆，延迟可控在 50ms 以内。

```python
# src/paperbot/memory/retriever.py (核心检索逻辑)

import numpy as np

def vector_search(
    query_embedding: np.ndarray,
    candidate_embeddings: list[tuple[str, np.ndarray]],  # (item_id, embedding)
    top_k: int = 10,
) -> list[tuple[str, float]]:
    """余弦相似度检索"""
    if not candidate_embeddings:
        return []
    ids = [c[0] for c in candidate_embeddings]
    matrix = np.stack([c[1] for c in candidate_embeddings])
    # 归一化
    query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
    matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    scores = matrix_norm @ query_norm
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(ids[i], float(scores[i])) for i in top_indices]
```

#### 3.5.3 检索管线（Hybrid Recall）

参考 Zep 的混合检索策略，组合三路信号：

```
Query → ┌── 向量检索（语义匹配） ─── weight: 0.50
        ├── 关键词匹配（BM25/token）── weight: 0.25
        └── scope/tag 精确过滤    ── weight: 0.25
                    │
             Merge & Re-rank
                    │
             Time Decay × Score
                    │
             Token Budget Trim
                    │
             RecallResult
```

**时间衰减公式**（参考 Trending 评分公式）：

```python
import math

def time_decay(days_since_event: float, half_life: float = 30.0) -> float:
    """记忆时间衰减 — 半衰期默认 30 天"""
    return math.exp(-0.693 * days_since_event / half_life)

def recall_score(
    semantic_sim: float,
    keyword_score: float,
    scope_match: float,
    days_old: float,
    use_count: int,
    recency_weight: float = 0.2,
) -> float:
    """综合检索评分"""
    base = semantic_sim * 0.50 + keyword_score * 0.25 + scope_match * 0.25
    decay = time_decay(days_old)
    usage_boost = min(math.log1p(use_count) * 0.05, 0.2)  # 使用频率加成，上限 0.2
    return base * (1 - recency_weight + recency_weight * decay) + usage_boost
```

### 3.6 记忆整合（Consolidator）

定期运行的后台任务，负责：

1. **Episode → Note 升级**：将频繁出现的 Episode 模式提炼为 Note
2. **冲突检测**：检查新记忆与旧记忆的矛盾（参考 HiMem 冲突感知重整合）
3. **衰减清理**：`decay_factor` 低于阈值的记忆标记为 superseded
4. **链接维护**：自动发现相似记忆并建立关联

```python
# src/paperbot/memory/consolidator.py (简化示意)

class MemoryConsolidator:
    """记忆整合器 — 定期运行"""

    def __init__(self, store, embedding_provider, llm_service=None):
        self.store = store
        self.embedder = embedding_provider
        self.llm = llm_service

    async def run(self, user_id: str) -> ConsolidationReport:
        report = ConsolidationReport()

        # 1. 衰减更新
        report.decayed = await self._update_decay_factors(user_id)

        # 2. Episode → Note 整合
        report.consolidated = await self._consolidate_episodes(user_id)

        # 3. 自动链接发现
        report.links_created = await self._discover_links(user_id)

        # 4. 过期清理
        report.expired = await self._cleanup_expired(user_id)

        return report

    async def _consolidate_episodes(self, user_id: str) -> int:
        """将相似 episode 聚类并提炼为 note"""
        episodes = self.store.list_memories(
            user_id=user_id,
            memory_layer="episode",
            status="approved",
            min_count=3,  # 至少 3 个相似 episode 才整合
        )
        # 按 embedding 聚类 → 每个簇生成一条 Note
        # 如果 LLM 可用，用 LLM 生成摘要；否则用模板
        ...

    async def _discover_links(self, user_id: str) -> int:
        """基于 embedding 相似度自动发现关联"""
        items = self.store.list_memories(user_id=user_id, status="approved")
        # 对所有 items 的 embedding 做 pairwise cosine
        # similarity > 0.85 → 建立 'related' 链接
        ...
```

### 3.7 上下文装配（与 Manus 原则对齐）

现有的 `ContextEngine.build_context_pack()` 重构为 **上下文装配服务**，位于 application 层（不属于记忆 infra）：

```python
# src/paperbot/application/services/context_assembly.py

class ContextAssemblyService:
    """上下文装配 — 从记忆层获取原料，按 task/stage 组装"""

    def __init__(self, memory: MemoryService, track_router: TrackRouter):
        self.memory = memory
        self.router = track_router

    def build_context(
        self,
        user_id: str,
        task_type: str,           # "judge" | "daily" | "search" | "chat"
        query: str,
        *,
        track_id: Optional[str] = None,
        max_tokens: int = 3000,
    ) -> ContextPack:
        # 1. 路由到 track
        track = self.router.suggest_track(query, user_id) if not track_id else ...

        # 2. 按优先级和 token budget 分配
        budget = TokenBudget(total=max_tokens)

        # Level 1: 用户画像（profile/preference）— 始终包含
        profile_block = self.memory.build_context_block(
            user_id, query="user profile",
            max_tokens=budget.allocate("profile", 300),
            kinds=["profile", "preference"],
        )

        # Level 2: 任务相关记忆 — 按 scope 和 query 检索
        task_block = self.memory.build_context_block(
            user_id, query=query,
            max_tokens=budget.allocate("task", 1200),
            scope_type="track" if track else None,
            scope_id=track.id if track else None,
        )

        # Level 3: 历史洞察 — 仅在 budget 允许时包含
        insight_block = ""
        remaining = budget.remaining()
        if remaining > 200:
            insight_block = self.memory.build_context_block(
                user_id, query=query,
                max_tokens=remaining,
                kinds=["insight", "decision"],
            )

        return ContextPack(
            profile=profile_block,
            task_memories=task_block,
            insights=insight_block,
            track=track,
            token_usage=budget.used(),
        )
```

### 3.8 渐进式上下文管理（三级加载）

参考 Manus Skills 的 Progressive Disclosure：

| 级别 | 何时加载 | 内容 | Token 消耗 |
|------|---------|------|-----------|
| **L0: 元数据** | 每次 LLM 调用 | 用户名 + 当前 track 名 + "has N memories" | ~50 tokens |
| **L1: 画像** | task 开始时 | profile + preferences + goals | ~300 tokens |
| **L2: 任务记忆** | query 确定后 | recall(query) 结果的 top-k | ~1200 tokens |
| **L3: 深度上下文** | 仅在需要时 | 完整 insights + linked items + episode 详情 | 按需分配 |

```python
# 实际使用示例（在 DailyPaper workflow 中）

# L0: 始终包含
system_prompt = f"User: {user_name}. Research track: {track_name}."

# L1: workflow 开始时获取
profile = memory.build_context_block(user_id, "user profile", max_tokens=300)

# L2: 每个 query 的 judge 评分时获取
for query in queries:
    task_ctx = memory.build_context_block(
        user_id, query, max_tokens=1200, scope_type="track"
    )
    judge_prompt = f"{system_prompt}\n\n{profile}\n\n{task_ctx}\n\n{paper_abstract}"
```

---

## 4. 迁移计划

### Phase 0: 接口定义 + 向量化（无破坏性变更）

**目标**：在不修改现有功能的前提下，为记忆系统添加向量检索能力。

- [ ] 新建 `src/paperbot/memory/protocol.py`（MemoryService Protocol 定义）
- [ ] 新建 `src/paperbot/memory/retriever.py`（向量检索 + 混合检索实现）
- [ ] 新增 `memory_embeddings` 表 + Alembic 迁移
- [ ] 新增 `memory_links` 表 + Alembic 迁移
- [ ] 扩展 `MemoryItemModel`：添加 `memory_layer`、`event_at`、`embedding_id`、`decay_factor` 字段
- [ ] 在现有 `SqlAlchemyMemoryStore.add_memories()` 中异步计算 embedding
- [ ] 在现有 `SqlAlchemyMemoryStore.search_memories()` 中加入向量检索分支

### Phase 1: 分离 Facade + Consolidator

**目标**：建立 MemoryService Facade，实现 Protocol 契约，使业务层通过 Protocol 消费。

- [ ] 新建 `src/paperbot/memory/service.py`（MemoryServiceImpl，实现 MemoryService Protocol）
- [ ] 新建 `src/paperbot/memory/consolidator.py`（MemoryConsolidator）
- [ ] Episode/Note 双层记忆类型支持（memory_layer 字段实际使用）
- [ ] `recall()` 方法实现混合检索管线
- [ ] `link()` 方法实现记忆关联
- [ ] 将 `ContextEngine` 中的记忆相关逻辑迁移到 `ContextAssemblyService`
- [ ] DI 容器注册 `MemoryService`

### Phase 2: 业务集成 + 自动记忆生成

**目标**：让各 workflow 自动产生和消费记忆。

- [ ] `dailypaper.py` 完成后自动写入 Episode（search_query + workflow_run）
- [ ] `paper_judge.py` 评分后将高分论文洞察写入 Note（insight）
- [ ] `feedback` 路由处理后写入 Episode（feedback）
- [ ] Judge prompt 注入用户画像和研究偏好记忆
- [ ] Track Router 使用向量化记忆提升路由准确度
- [ ] Consolidator 注册到 ARQ Worker 定期执行

### Phase 3: 高级功能

- [ ] 时间衰减调度（decay_factor 定期更新）
- [ ] 冲突检测（新记忆 vs 旧记忆的语义矛盾检查）
- [ ] 自动链接发现（embedding 相似度 > 阈值自动建立关联）
- [ ] 记忆导出/快照（备份到文件系统，参考 Manus 文件即记忆模式）
- [ ] 可选升级到 sqlite-vec 或 Qdrant

---

## 5. 文件清单

| 文件 | 类型 | Phase | 说明 |
|------|------|-------|------|
| `src/paperbot/memory/protocol.py` | **新建** | 0 | MemoryService Protocol 接口定义 |
| `src/paperbot/memory/retriever.py` | **新建** | 0 | 向量检索 + 混合检索 |
| `src/paperbot/memory/service.py` | **新建** | 1 | MemoryServiceImpl (Facade) |
| `src/paperbot/memory/consolidator.py` | **新建** | 1 | 记忆整合器 |
| `src/paperbot/memory/types.py` | **新建** | 0 | MemoryItem, RecallResult 等数据类 |
| `src/paperbot/infrastructure/stores/models.py` | 修改 | 0 | 扩展 MemoryItemModel + 新增 MemoryLinkModel/MemoryEmbeddingModel |
| `src/paperbot/infrastructure/stores/memory_store.py` | 修改 | 0-1 | 添加向量检索/链接 CRUD |
| `src/paperbot/context_engine/engine.py` | 修改 | 1 | 迁移记忆逻辑到 ContextAssemblyService |
| `src/paperbot/application/services/context_assembly.py` | **新建** | 1 | 上下文装配服务 |
| `src/paperbot/memory/extractor.py` | 修改 | 1 | 适配新的 MemoryService 写入接口 |
| `src/paperbot/application/workflows/dailypaper.py` | 修改 | 2 | 自动写入 Episode 记忆 |
| `src/paperbot/application/workflows/analysis/paper_judge.py` | 修改 | 2 | 注入记忆上下文 |
| `src/paperbot/infrastructure/queue/arq_worker.py` | 修改 | 2 | 注册 Consolidator 定时任务 |
| `alembic/versions/xxx_add_memory_vectors.py` | **新建** | 0 | 数据库迁移 |

---

## 6. 与上下文工程的关系

### 6.1 关键定位

```
┌──────────────────────────────────────────────────────────────┐
│                    Context Engineering                        │
│                                                              │
│  ┌───────────┐  ┌─────────────┐  ┌────────────────────────┐ │
│  │  Memory   │  │  Retrieval  │  │  Context Management    │ │
│  │  (本模块)  │  │  (RAG/搜索)  │  │  (token budget/压缩)  │ │
│  │           │  │             │  │                        │ │
│  │ 用户画像   │  │ 论文检索     │  │ 渐进式加载 (L0-L3)    │ │
│  │ 研究偏好   │  │ 学者数据     │  │ Compaction (引用替代)  │ │
│  │ 交互历史   │  │ 代码仓库     │  │ Summarization (摘要)   │ │
│  │ 知识积累   │  │             │  │ Scope isolation        │ │
│  └─────┬─────┘  └──────┬──────┘  └───────────┬────────────┘ │
│        │               │                      │              │
│        └───────────────┼──────────────────────┘              │
│                        ▼                                     │
│              Context Assembly Service                        │
│              (组装 prompt payload)                           │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 对齐 Manus 原则

| Manus 原则 | PaperBot 对应设计 |
|-----------|-----------------|
| 文件系统即无限记忆 | Episode 全文存文件系统，DB 只存引用和元数据 |
| Raw > Compaction > Summarization | L2 检索返回原文；L1 返回 profile 摘要；L0 返回元数据 |
| 上下文隔离 | scope_type 隔离：每个 Track 的记忆互不干扰 |
| KV-Cache 稳定性 | Profile 块（L1）放 prompt 前部，很少变化，利于缓存 |
| 工具掩码而非移除 | 记忆 recall 按 scope/kinds 过滤，而非修改 prompt 模板 |
| todo.md 注意力引导 | 将当前 research goal 放到 prompt 末尾 |
| 保留错误上下文 | 记忆中保留 "contradiction" 和 "superseded" 标记 |

---

## 7. 参考文献

### 系统与框架

- [Manus Context Engineering](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [LangChain × Manus Webinar](https://blog.langchain.com/context-engineering-for-agents/)
- [Manus Skills Standard](https://manus.im/blog/manus-skills)
- [EverMemOS](https://github.com/EverMind-AI/EverMemOS) — 92.3% LoCoMo
- [Zep/Graphiti](https://github.com/getzep/graphiti) — 时序知识图谱
- [Mem0](https://github.com/mem0ai/mem0) — 生产级记忆层
- [Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory) — 文件系统即记忆
- [memU](https://github.com/NevaMind-AI/memU) — 主动式 Agent 记忆

### 学术论文

1. A-MEM: Agentic Memory for LLM Agents — NeurIPS 2025 ([arXiv:2502.12110](https://arxiv.org/abs/2502.12110))
2. HiMem: Hierarchical Long-Term Memory — arXiv 2026 ([arXiv:2601.06377](https://arxiv.org/abs/2601.06377))
3. Agent Workflow Memory — ICML 2025 ([arXiv:2409.07429](https://arxiv.org/abs/2409.07429))
4. RMM: Reflective Memory Management — ACL 2025 ([arXiv:2503.08026](https://arxiv.org/abs/2503.08026))
5. Memoria: Scalable Agentic Memory — arXiv 2025 ([arXiv:2512.12686](https://arxiv.org/abs/2512.12686))
6. ACE: Agentic Context Engineering — arXiv 2025 ([arXiv:2510.04618](https://arxiv.org/abs/2510.04618))
7. TiMem: Temporal-Hierarchical Memory — arXiv 2026 ([arXiv:2601.02845](https://arxiv.org/abs/2601.02845))
8. Collaborative Memory — ICML 2025 ([arXiv:2505.18279](https://arxiv.org/abs/2505.18279))
9. Memory in the Age of AI Agents: Survey — arXiv 2025 ([arXiv:2512.13564](https://arxiv.org/abs/2512.13564))
10. Survey of Context Engineering — arXiv 2025 ([arXiv:2507.13334](https://arxiv.org/abs/2507.13334))
11. M+: Extending MemoryLLM — ICML 2025 ([arXiv:2502.00592](https://arxiv.org/abs/2502.00592))
12. Mem0 Paper — arXiv 2025 ([arXiv:2504.19413](https://arxiv.org/abs/2504.19413))
13. Episodic Memory Risks — SaTML 2025 ([arXiv:2501.11739](https://arxiv.org/abs/2501.11739))
14. Episodic Memory: Suggesting Next Tasks — arXiv 2025 ([arXiv:2511.17775](https://arxiv.org/abs/2511.17775))
15. Zep: Temporal KG Architecture — arXiv 2025 ([arXiv:2501.13956](https://arxiv.org/abs/2501.13956))

### Benchmark

- [LoCoMo](https://snap-research.github.io/locomo/) — 300-turn 长对话记忆评估
- [LongMemEval](https://arxiv.org/abs/2410.10813) — 500 问题，5 核心记忆能力 (ICLR 2025)
- [MemAgents Workshop Proposal](https://openreview.net/pdf?id=U51WxL382H) — ICLR 2026 Workshop
