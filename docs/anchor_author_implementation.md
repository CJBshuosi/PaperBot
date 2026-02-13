# 锚点作者系统 — 实施设计

> 从理论模型到可运行代码的落地方案。
> 理论基础见 `anchor_source_authority_model.md`。

---

## 0. 核心问题

arXiv 每天 ~500 篇 CS 论文，用户不可能全读。锚点作者系统的目标：

1. **自动发现**用户应该关注的高质量作者（不依赖手动订阅）
2. **搜索增强**：每次搜索后标注哪些结果命中了锚点作者
3. **防过拟合**：不盲信用户品味，用客观质量校准主观偏好
4. **合作网络**：揭示作者间的合作关系和机构聚类

---

## 1. 数据层：authors + paper_authors

### 1.1 为什么不继续用 authors_json

当前 `PaperModel.authors_json` 存的是 `["John Smith", "Jane Doe"]`，存在：
- 同一人多种写法（"Yann LeCun" / "Y. LeCun"）
- 无法跨论文聚合统计
- 无法关联 Semantic Scholar author ID

### 1.2 新表设计

```sql
-- 作者实体表
CREATE TABLE authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_normalized TEXT NOT NULL,        -- 小写去空格，用于去重
    display_name TEXT NOT NULL,           -- 展示用原名
    semantic_scholar_id TEXT,             -- S2 author ID（延迟解析）
    affiliation TEXT,                     -- 机构（延迟解析）
    h_index INTEGER,
    citation_count INTEGER DEFAULT 0,
    paper_count INTEGER DEFAULT 0,
    resolved_at DATETIME,                 -- S2 API 解析时间
    created_at DATETIME NOT NULL,
    UNIQUE(name_normalized)
);
CREATE INDEX idx_authors_s2id ON authors(semantic_scholar_id);
CREATE INDEX idx_authors_name ON authors(name_normalized);

-- 论文-作者多对多关联
CREATE TABLE paper_authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,  -- 0-based，0=一作
    UNIQUE(paper_id, author_id)
);
CREATE INDEX idx_paper_authors_author ON paper_authors(author_id);
CREATE INDEX idx_paper_authors_paper ON paper_authors(paper_id);
```

### 1.3 Name Normalization

```python
def normalize_author_name(name: str) -> str:
    """轻量级姓名归一化，不依赖外部服务。"""
    name = name.strip().lower()
    name = re.sub(r'\s+', ' ', name)
    # 去掉中间名缩写: "yann a. lecun" → "yann lecun"
    name = re.sub(r'\b[a-z]\.\s*', '', name)
    # 去掉尾部逗号格式: "lecun, yann" → "yann lecun"
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        name = f"{parts[1]} {parts[0]}"
    return name.strip()
```

精确去重靠 `name_normalized` UNIQUE 约束。后续对 top 作者调 S2 Author Search API 补全 `semantic_scholar_id`，实现跨写法合并。

### 1.4 回填策略

迁移后一次性扫描 `papers.authors_json`：

```python
for paper in all_papers:
    for i, name in enumerate(paper.get_authors()):
        norm = normalize_author_name(name)
        author = get_or_create_author(norm, display_name=name)
        link_paper_author(paper.id, author.id, position=i)
```

后续每次 `paper_store.upsert_paper()` 时同步写入 `paper_authors`。

---

## 2. 双轨评分：防过拟合

### 2.1 问题

纯靠用户 save 行为推荐 = 信息茧房。初学者可能 save 质量一般的论文。

### 2.2 解法：Subjective + Objective 自适应混合

```
anchor_score = α × subjective_score + (1 - α) × objective_score
```

α 随用户成熟度动态调整：

```python
import math

def compute_alpha(user_total_saves: int, calibration: float) -> float:
    """
    α ∈ [0.1, 0.7]，永远不会完全忽略客观分。
    calibration: 用户 save 与 judge score 的相关性 (0~1)
    """
    raw = 1 / (1 + math.exp(-(user_total_saves - 20) / 8))
    return 0.1 + 0.6 * raw * calibration
```

- 新用户 (saves < 10): α ≈ 0.1 → 客观质量主导
- 成熟用户 (saves > 30) + 高校准: α ≈ 0.5 → 主观客观各半
- α 上限 0.7 → 客观分永远至少占 30%

### 2.3 Objective Score（不依赖用户行为）

针对每个 author，从系统全局数据计算：

| 信号 | 权重 | 来源 |
|------|------|------|
| `judge_score_avg` | 0.35 | 该作者所有论文的 `paper_judge_scores.overall` 平均值 |
| `citation_velocity` | 0.25 | `papers.citation_count / age_years`（log scale） |
| `venue_tier_avg` | 0.20 | 论文发表 venue 的平均 tier（T1=1.0, T2=0.6, other=0.2） |
| `h_index_norm` | 0.20 | `log(1 + h_index) / log(1 + field_median_h)`（领域归一化） |

```python
def objective_score(author_id: int) -> float:
    papers = get_author_papers(author_id)
    if not papers:
        return 0.0

    judge_avg = mean([p.judge_overall for p in papers if p.judge_overall]) or 0
    cite_vel = mean([p.citation_count / max(age_years(p), 0.5) for p in papers])
    venue_avg = mean([venue_tier_score(p.venue) for p in papers])
    h_norm = math.log(1 + (author.h_index or 0)) / math.log(1 + 30)  # 30 as field median

    return (0.35 * min(judge_avg / 5.0, 1.0) +
            0.25 * min(math.log(1 + cite_vel) / 5.0, 1.0) +
            0.20 * venue_avg +
            0.20 * min(h_norm, 1.0))
```

### 2.4 Subjective Score（来自用户行为）

针对特定 user，从 `paper_feedback(action=save)` 聚合：

| 信号 | 权重 | 说明 |
|------|------|------|
| `save_count` | 0.40 | 出现在多少篇 saved paper 上 |
| `recency` | 0.25 | 最近 save 的时间衰减（半衰期 90 天） |
| `track_spread` | 0.20 | 跨多少个 research track |
| `first_author_ratio` | 0.15 | 一作比例 |

### 2.5 用户校准（Calibration）

追踪用户 save 的论文的 judge score 分布：

```python
def compute_calibration(user_id: str) -> float:
    """用户品味与客观质量的一致性，0~1。"""
    saved_papers = get_user_saved_papers(user_id)
    if len(saved_papers) < 5:
        return 0.3  # 数据不足，保守值

    judge_scores = [p.judge_overall for p in saved_papers if p.judge_overall]
    if not judge_scores:
        return 0.3

    avg = mean(judge_scores)
    # judge overall 满分 5.0，avg >= 3.5 说明用户品味靠谱
    return min(max((avg - 2.0) / 2.0, 0.0), 1.0)
```

### 2.6 锚点分层

| 层级 | anchor_score | 标签 | 系统行为 |
|------|-------------|------|---------|
| Core Anchor | >= 0.7 | `anchor` | 新论文自动高优先级，搜索结果置顶 |
| Rising | 0.4 ~ 0.7 | `rising` | 值得关注，搜索结果标注 |
| Background | < 0.4 | — | 不展示 |

---

## 3. Search Hit Overlay — 搜索结果锚点命中

### 3.1 数据流

```
用户搜索 → Context Engine 返回 papers
    → 提取所有 paper 的 author_ids (via paper_authors)
    → 查询 user 的 anchor authors
    → 交叉匹配 → 生成 anchor_hits overlay
    → 返回给前端
```

### 3.2 后端响应扩展

在现有搜索响应中新增 `anchor_hits` 字段：

```json
{
  "papers": [...],
  "anchor_hits": {
    "summary": {
      "total_results": 20,
      "anchor_hit_count": 4,
      "hit_rate": 0.20
    },
    "by_author": [
      {
        "author_name": "Yann LeCun",
        "author_id": 42,
        "tier": "anchor",
        "anchor_score": 0.92,
        "hit_paper_ids": [101, 205],
        "track_stats": {
          "track_name": "self-supervised-learning",
          "saved_in_track": 5,
          "this_is_nth": [6, 7]
        }
      }
    ]
  }
}
```

### 3.3 前端展示

- PaperCard 作者名旁：`⚓ Anchor · 该 track 第 6 篇`
- 搜索结果顶部统计栏：`4/20 results from your anchor authors (20%)`
- Rising 作者用不同颜色 badge

### 3.4 Track 计数逻辑

"这是该作者在这个 track 的第 N 篇" 的计算：

```sql
SELECT COUNT(*) + 1 as nth
FROM paper_feedback pf
JOIN paper_authors pa ON pa.paper_id = pf.paper_ref_id
WHERE pf.user_id = :user_id
  AND pf.track_id = :track_id
  AND pf.action = 'save'
  AND pa.author_id = :author_id
```

---

## 4. 合作网络 + 机构关系

### 4.1 Co-author 共现图

从 `paper_authors` 构建：同一篇论文的两个作者之间建立 edge。

```python
def build_coauthor_edges(user_id: str) -> list[dict]:
    """从用户 saved papers 构建共现边。"""
    saved_paper_ids = get_saved_paper_ids(user_id)
    edges = defaultdict(int)

    for paper_id in saved_paper_ids:
        authors = get_paper_author_ids(paper_id)
        for a, b in combinations(authors, 2):
            key = (min(a, b), max(a, b))
            edges[key] += 1

    return [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edges.items()
        if w >= 2  # 至少合作 2 篇才建边
    ]
```

### 4.2 机构聚类

按 `authors.affiliation` 分组（需 S2 API 解析后才有数据）：

```json
{
  "clusters": [
    {
      "institution": "UC Berkeley",
      "author_count": 5,
      "total_saved_papers": 12,
      "top_authors": ["Dawn Song", "Pieter Abbeel"]
    },
    {
      "institution": "Google DeepMind",
      "author_count": 8,
      "total_saved_papers": 15,
      "top_authors": ["Demis Hassabis", "Oriol Vinyals"]
    }
  ]
}
```

### 4.3 后端端点

```
GET /research/scholars/network?user_id=default&min_edge_weight=2
```

返回 `{ nodes: [...], edges: [...], clusters: [...] }`

---

## 5. 探索机制 — 打破信息茧房

### 5.1 Community Picks

不依赖任何用户行为，纯客观质量推荐：

```python
def community_picks(track_id: int, limit: int = 10) -> list:
    """在 track 领域内，judge 分数 top 的作者（排除用户已有锚点）。"""
    track = get_track(track_id)
    keywords = track.get_keywords()

    # 找到该领域论文
    papers = search_papers(keywords=keywords, min_judge_score=3.5)

    # 按作者聚合 judge 分数
    author_scores = defaultdict(list)
    for p in papers:
        for author_id in get_paper_author_ids(p.id):
            author_scores[author_id].append(p.judge_overall)

    # 排序：平均 judge score × 论文数权重
    ranked = sorted(
        author_scores.items(),
        key=lambda x: mean(x[1]) * math.log(1 + len(x[1])),
        reverse=True
    )
    return ranked[:limit]
```

### 5.2 Blind Spot Detection

检测用户哪些 track 缺少锚点覆盖：

```python
def detect_blind_spots(user_id: str) -> list[dict]:
    tracks = get_user_tracks(user_id)
    anchors = get_user_anchors(user_id)

    blind_spots = []
    for track in tracks:
        track_anchor_count = count_anchors_in_track(anchors, track.id)
        if track_anchor_count == 0:
            community = community_picks(track.id, limit=5)
            blind_spots.append({
                "track": track.name,
                "message": f"No anchors in '{track.name}' yet",
                "suggested_authors": community
            })
    return blind_spots
```

### 5.3 Serendipity Injection

搜索结果中混入 10-15% 的非锚点但客观质量高的论文，让用户有机会发现新作者。在 Context Engine 的结果排序中实现。

---

## 6. API 端点设计

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/research/scholars/discover` | 锚点发现：返回双轨评分排序的作者列表 |
| `GET` | `/research/scholars/community` | Community Picks：纯客观质量推荐 |
| `GET` | `/research/scholars/network` | 合作网络图：nodes + edges + clusters |
| `GET` | `/research/scholars/blind-spots` | 盲区检测：缺少锚点的 track |
| `POST` | `/research/scholars/{author_id}/resolve` | 触发 S2 API 解析补全 |

### 6.1 Discover 端点详细

```
GET /research/scholars/discover?user_id=default&limit=30&include_community=true
```

响应：

```json
{
  "anchors": [
    {
      "author_id": 42,
      "name": "Yann LeCun",
      "tier": "anchor",
      "anchor_score": 0.92,
      "objective_score": 0.88,
      "subjective_score": 0.95,
      "save_count": 8,
      "avg_judge_score": 4.2,
      "avg_citations": 1250,
      "tracks": ["deep-learning", "self-supervised"],
      "recent_papers": ["A Path Towards Autonomous AI"],
      "affiliation": "Meta AI / NYU",
      "h_index": 180,
      "semantic_scholar_id": "1688681"
    }
  ],
  "community_picks": [...],
  "blind_spots": [...],
  "user_calibration": 0.72,
  "alpha": 0.45
}
```

---

## 7. 前端 Scholars 页面改造

### 7.1 页面结构

```
/scholars
├── Tab: Discovered (默认)
│   ├── 统计栏: "12 anchors · 8 rising · calibration: 72%"
│   ├── Your Anchors (双轨评分 top N)
│   │   └── AuthorCard: name, tier badge, score, save_count, tracks, affiliation
│   ├── Community Picks (纯客观推荐)
│   │   └── AuthorCard + "Community Recommended" badge
│   └── Blind Spots (缺少锚点的 track)
│       └── "No anchors in 'CV' track — suggested: ..."
├── Tab: Network
│   └── 力导向图 / 简单列表展示合作网络
└── Tab: Subscribed
    └── 现有手动订阅学者（保留）
```

### 7.2 AuthorCard 组件

```
┌─────────────────────────────────────────────────┐
│ [Avatar]  Yann LeCun          ⚓ Anchor (0.92)  │
│           Meta AI / NYU · h-index: 180          │
│                                                  │
│  📊 Obj: 0.88  👤 Subj: 0.95  📄 8 saved       │
│  Tracks: deep-learning, self-supervised          │
│                                                  │
│  Recent: "A Path Towards Autonomous AI" (2025)   │
│                                                  │
│  [Resolve Profile]  [View Details]  [Follow]     │
└─────────────────────────────────────────────────┘
```

---

## 8. Search Hit Overlay 前端

### 8.1 搜索结果顶部

```
┌─────────────────────────────────────────────────┐
│ 🎯 Anchor Coverage: 4/20 results (20%)          │
│    LeCun: 2 hits · He: 1 hit · Bengio: 1 hit   │
└─────────────────────────────────────────────────┘
```

### 8.2 PaperCard 内嵌标注

在现有 PaperCard 的作者行中，锚点作者名字后追加：

```
Authors: Yann LeCun ⚓, Kaiming He 📈, ...
         └─ Anchor · self-supervised track 第 6 篇
```

---

## 9. 实施顺序

详见 `ANCHOR_TODO.md`。

P0（最小闭环）: 建表 → 回填 → discover 端点 → 前端替换 mock
P1（搜索增强）: search hit overlay → PaperCard 标注
P2（网络 + 解析）: 合作网络 → S2 API 解析 → 机构聚类
P3（智能推荐）: anchor boost in Context Engine → blind spot → serendipity
