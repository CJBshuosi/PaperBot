# 信息源锚点模型：形式化建模与系统设计

> 从噪声信息流中发现高质量锚点，建模信息源之间的权威性传播关系，并个性化标定锚点价值。

---

## 1. 本质问题

这是一个**异构信息网络中的权威性发现与传播问题**（Authority Discovery in Heterogeneous Information Networks）。

它结合了三个经典问题：

1. **信号检测**（Signal Detection）— 从噪声中识别高质量信号
2. **权威性传播**（Authority Propagation）— PageRank/HITS 的核心思想：权威性不是孤立的属性，而是通过关系网络传播的
3. **锚点标定**（Anchor Calibration）— 锚点不是绝对的，是相对于观察者（用户研究方向）和时间的

### 1.1 信号检测：从噪声中找锚点

每天面对的信息流本质是一个**低信噪比信道**。arXiv 每天 ~500 篇 CS 论文，绝大多数是噪声（对特定研究方向而言）。锚点就是这个信道中的**高信噪比节点** — 它们不只是自身有价值，而且它们的存在能帮你**校准其他信号的价值**。

**一个好的锚点的本质特征是：它能减少你评估其他信息时的不确定性。**

例：当你知道 Dawn Song 在做 AI Safety，她的新论文就是一个锚点 — 不只因为这篇论文好，而是因为它帮你快速判断：
- 这个方向是活跃的
- 这些合作者值得关注
- 这些 venue 是相关的
- 这些被引论文可能是基础工作

锚点的信息论定义：**锚点是观测到后能最大程度降低你对信息空间不确定性的节点**。

```
H(信息空间 | 观测到锚点) << H(信息空间)

其中 H 是信息熵。锚点的质量 ∝ 互信息 I(锚点; 信息空间)
```

### 1.2 权威传播：锚点之间的关系

这就是 PageRank 的核心洞察：**权威性不是孤立属性，而是通过关系网络传播的**。

```
锚点学者 ──发表于──→ 锚点 venue
    │                    │
    └──引用──→ 锚点论文 ──被引用──→ 新论文（被锚点网络"背书"）
    │
    └──合作──→ 新学者（通过合作关系获得"锚点传播"）
```

**关键：锚点不是单个实体的属性，是整个网络中相对位置的函数。**

一篇论文被 3 个核心锚点学者引用 vs 被 30 个普通论文引用 — 这两个事件传达的信号完全不同。前者是领域顶级专家的"背书"，后者可能只是普通的文献综述。现有的引用计数无法区分这种差异，但基于网络传播的权威评分可以。

### 1.3 个性化标定：锚点是相对的

同一个学者，对研究 NLP 的人和研究 Systems 的人是完全不同的锚点。同一个会议在 2020 年是锚点，2026 年可能影响力已经转移。所以锚点评分实际上是一个**四元函数**：

```
anchor_score(source, domain, time, observer) → [0, 1]
```

- **source**: 信息源实体（学者/venue/网站/repo）
- **domain**: 领域上下文（安全/ML/系统/SE）
- **time**: 时间窗口（最近 6 个月 vs 历史全量）
- **observer**: 用户的研究方向和偏好

---

## 2. 形式化建模

### 2.1 异构信息网络定义

定义异构信息网络 $G = (V, E, \phi, \psi)$，其中：

- $V$ 是节点集合
- $E \subseteq V \times V$ 是边集合
- $\phi: V \rightarrow T_V$ 是节点类型映射函数
- $\psi: E \rightarrow T_E$ 是边类型映射函数
- $|T_V| + |T_E| > 2$（异构性条件）

#### 节点类型 $T_V$

```
T_V = {Scholar, Paper, Venue, Website, Topic, Repo}
```

| 节点类型 | 属性集 | 内在质量信号 |
|---------|--------|------------|
| **Scholar** | id, name, h_index, citation_count, paper_count, fields, affiliations | h-index, 总引用, 论文产出率 |
| **Paper** | id, title, year, citations, venue, judge_scores, abstract | 引用数, Judge 综合分, venue tier |
| **Venue** | name, domain, tier, acceptance_rate, impact_factor | 领域排名, 接收率, 影响因子 |
| **Website** | url, type, freshness, coverage | 覆盖率, 更新频率, 数据质量 |
| **Topic** | keyword, field, trending_score | 论文量增速, 引用集中度 |
| **Repo** | url, stars, forks, language, last_commit, contributors | stars, 活跃度, 贡献者数 |

#### 边类型 $T_E$

```
T_E = {authors, published_at, cites, coauthors, belongs_to, listed_on, has_repo, researches}
```

| 边类型 | 源节点 → 目标节点 | 权威传播含义 | 权重来源 |
|--------|------------------|------------|---------|
| **authors** | Scholar → Paper | 学者为论文背书 | 作者排序位置 |
| **published_at** | Paper → Venue | Venue 为论文背书（接收=认可） | 接收年份 |
| **cites** | Paper → Paper | 被引论文获得引用方的传播 | 引用上下文（正/负/中性） |
| **coauthors** | Scholar ↔ Scholar | 合作者之间的信任传递 | 合作频次, 合作年限 |
| **belongs_to** | Paper → Topic | 论文质量反哺主题热度 | 主题匹配置信度 |
| **listed_on** | Paper → Website | 数据源的覆盖质量 | 上线时间 |
| **has_repo** | Paper → Repo | 代码实现增强论文可信度 | 代码与论文匹配度 |
| **researches** | Scholar → Topic | 学者定义研究方向的权威性 | 该方向的论文数占比 |

#### 元路径（Meta-path）

元路径是异构图上连接两个节点的语义路径模式，用于定义"什么样的关系链构成有意义的权威传播"。

关键元路径定义：

```
Scholar Authority Paths:
  P1: Scholar ──authors──→ Paper ──published_at──→ Venue
      含义：学者通过在高质量 venue 发表论文获得权威

  P2: Scholar ──authors──→ Paper ──cites──→ Paper ──authors──→ Scholar
      含义：学者 A 引用学者 B 的论文 → B 获得 A 传播的权威

  P3: Scholar ──coauthors──→ Scholar ──authors──→ Paper
      含义：合作者的论文质量反映到当前学者

Venue Authority Paths:
  P4: Venue ←──published_at── Paper ──cites──→ Paper ──published_at──→ Venue
      含义：Venue A 的论文引用 Venue B 的论文 → B 获得 A 的传播

Topic Authority Paths:
  P5: Topic ←──belongs_to── Paper ──authors──→ Scholar ──researches──→ Topic
      含义：Topic 间通过学者的跨领域工作产生关联

Emerging Source Detection:
  P6: Scholar ──coauthors──→ Scholar(anchor) ──researches──→ Topic
      含义：与锚点学者合作且进入新方向 → 潜力信号
```

### 2.2 锚点评分公式

对一个 source 节点 $s$，其锚点评分是四个分量的组合：

$$
\text{AnchorScore}(s) = Q(s) \cdot N(s) \cdot T(s) \cdot R(s, o)
$$

或者采用加权加法形式（避免任何一项为零导致整体为零）：

$$
\text{AnchorScore}(s) = \alpha \cdot Q(s) + \beta \cdot N(s) + \gamma \cdot T(s) + \delta \cdot R(s, o)
$$

其中 $\alpha + \beta + \gamma + \delta = 1$，建议初始权重：

| 分量 | 权重 | 说明 |
|------|------|------|
| $\alpha$ (内在质量) | 0.30 | 基础门槛，但不应主导 |
| $\beta$ (网络位置) | 0.35 | 最重要的信号 — 网络效应 |
| $\gamma$ (时间动态) | 0.15 | 区分活跃 vs 历史锚点 |
| $\delta$ (观察者相关) | 0.20 | 个性化校准 |

#### 2.2.1 Q(s) — 内在质量

内在质量是 source 自身的客观属性评分，不依赖网络关系。

**Scholar 内在质量：**

```
Q_scholar(s) = normalize(
    w_h · log(1 + h_index) +
    w_c · log(1 + citation_count) +
    w_p · min(paper_count / 50, 1.0) +
    w_v · avg_venue_tier
)

其中:
  w_h = 0.40  (h-index 权重，对数缩放)
  w_c = 0.25  (总引用权重)
  w_p = 0.10  (论文数量，上限 50 篇后饱和)
  w_v = 0.25  (平均发表 venue tier)
```

h-index 使用对数缩放是因为它的分布是重尾的（h=50 和 h=100 的差距远小于 h=5 和 h=10 的差距）。

**Paper 内在质量：**

```
Q_paper(s) = normalize(
    w_cite · citation_score(citations) +     # 引用分（分段映射）
    w_venue · venue_tier_score(venue) +       # venue tier 分
    w_judge · judge_overall / 5.0 +           # Judge 综合分（如有）
    w_code · has_code_score                   # 代码可用性
)

其中:
  w_cite  = 0.35
  w_venue = 0.25
  w_judge = 0.25
  w_code  = 0.15
```

这里 `citation_score()` 复用现有的 `CITATION_SCORE_RANGES` 分段映射（`domain/influence/weights.py`）。

**Venue 内在质量：**

```
Q_venue(s) = tier_score(tier) · domain_relevance(domain)

其中:
  tier_score(tier1) = 1.0
  tier_score(tier2) = 0.6
  tier_score(other) = 0.2
```

**Repo 内在质量：**

```
Q_repo(s) = normalize(
    w_stars · stars_score(stars) +
    w_activity · activity_score(last_commit) +
    w_contrib · min(contributors / 10, 1.0)
)
```

**归一化**：所有 Q(s) 在同类型节点内做 min-max 归一化到 [0, 1]。不同类型之间不直接比较 Q 值。

#### 2.2.2 N(s) — 网络位置（异构 PageRank）

N(s) 度量的是节点在异构网络中的结构重要性。这是锚点评分中最关键的分量 — 它捕获了"被谁引用/合作/发表"的信息。

**基础算法：异构阻尼 PageRank**

传统 PageRank 在同构图上定义：

$$
PR(v) = \frac{1 - d}{|V|} + d \sum_{u \in \text{in}(v)} \frac{PR(u)}{|\text{out}(u)|}
$$

在异构图上，需要对不同边类型赋予不同的传播权重：

$$
N(v) = \frac{1 - d}{|V|} + d \sum_{u \in \text{in}(v)} \frac{w_{\psi(u,v)} \cdot N(u)}{Z(u)}
$$

其中：
- $d = 0.85$（阻尼因子）
- $w_{\psi(u,v)}$ 是边类型 $\psi(u,v)$ 的传播权重
- $Z(u) = \sum_{v' \in \text{out}(u)} w_{\psi(u,v')}$ 是归一化因子

**边类型传播权重：**

```python
EDGE_PROPAGATION_WEIGHTS = {
    "cites":        0.30,   # 引用传播最强 — "我认可你的工作"
    "coauthors":    0.25,   # 合作关系 — "我信任你足以共同署名"
    "published_at": 0.20,   # venue 背书 — "这个会议认可了这篇论文"
    "has_repo":     0.15,   # 代码关联 — 实现增强可信度
    "belongs_to":   0.10,   # 主题归属 — 最弱的关联
}
```

**算法伪代码：**

```python
def heterogeneous_pagerank(graph, edge_weights, d=0.85, iterations=20, epsilon=1e-6):
    """
    异构 PageRank — 不同边类型有不同传播权重。

    Args:
        graph: 异构信息网络
        edge_weights: Dict[edge_type, float] — 边类型传播权重
        d: 阻尼因子
        iterations: 最大迭代次数
        epsilon: 收敛阈值

    Returns:
        Dict[node_id, float] — 每个节点的网络权威分数
    """
    n = len(graph.nodes)

    # 初始化：用内在质量 Q(s) 作为先验
    authority = {
        node.id: node.intrinsic_quality / n
        for node in graph.nodes
    }

    for iteration in range(iterations):
        new_authority = {}
        max_delta = 0

        for node in graph.nodes:
            # 从所有入边收集权威性
            incoming_authority = 0.0
            for neighbor, edge_type in graph.in_edges(node):
                w = edge_weights.get(edge_type, 0.1)
                out_degree = sum(
                    edge_weights.get(et, 0.1)
                    for _, et in graph.out_edges(neighbor)
                )
                if out_degree > 0:
                    incoming_authority += w * authority[neighbor.id] / out_degree

            new_score = (1 - d) / n + d * incoming_authority
            max_delta = max(max_delta, abs(new_score - authority[node.id]))
            new_authority[node.id] = new_score

        authority = new_authority

        # 收敛检测
        if max_delta < epsilon:
            break

    # 归一化到 [0, 1]
    max_auth = max(authority.values()) or 1
    return {nid: score / max_auth for nid, score in authority.items()}
```

**HITS 变体（可选增强）：Hub-Authority 双角色**

HITS 算法区分了两种角色：
- **Authority**：被高质量 hub 指向的节点（好论文 = 被好综述引用的论文）
- **Hub**：指向很多高质量 authority 的节点（好综述 = 引用了很多好论文的综述）

在 PaperBot 语境下：
- Survey 论文是典型的 **Hub**（引用大量论文）
- 被 survey 引用的论文是 **Authority**
- 学者同时扮演两种角色：作为 Hub（引用他人），作为 Authority（被引用）

```
authority(v) = ∑_{u → v} hub(u)
hub(v) = ∑_{v → u} authority(u)
```

HITS 比 PageRank 能更好地区分"综述型学者"（hub 分高）和"原创型学者"（authority 分高），但计算复杂度略高。建议 Phase 1 用 PageRank，Phase 2 考虑 HITS。

#### 2.2.3 T(s) — 时间动态

时间动态捕获 source 的**当前活跃度**和**趋势方向**。一个 h-index=80 但 5 年没发过论文的学者，和一个 h-index=15 但近 6 个月有 3 篇顶会的新学者，后者的时间动态分数应该更高。

**Scholar 时间动态：**

```
T_scholar(s) = w_rec · recency(s) + w_vel · velocity(s) + w_trend · trend(s)

其中:
  recency(s) = exp(-λ · months_since_last_paper)
      λ = 0.693 / 12  (半衰期 12 个月)

  velocity(s) = min(papers_last_12_months / 5, 1.0)
      (年产 5 篇以上饱和)

  trend(s) = citation_velocity_trend  (来自 DynamicPIS)
      accelerating → 1.0
      stable       → 0.5
      declining    → 0.1

权重:
  w_rec = 0.40, w_vel = 0.35, w_trend = 0.25
```

**Paper 时间动态：**

```
T_paper(s) = recency_decay(days_since_publish)
           = exp(-0.693 · days / half_life)

half_life:
  - 对于 trending 类场景: 30 天 (快速衰减，关注最新)
  - 对于 foundational 类场景: 365 天 (慢速衰减，经典论文保留)
```

**Venue 时间动态：**

```
T_venue(s) = w_accept · normalized_acceptance_rate_trend +
             w_submit · normalized_submission_growth +
             w_cite   · venue_citation_velocity

(Venue 的时间动态变化较慢，可每年更新一次)
```

**Repo 时间动态：**

```
T_repo(s) = w_commit · commit_recency +
            w_stars  · star_velocity +
            w_issue  · issue_resolution_rate

commit_recency = exp(-0.693 · days_since_last_commit / 30)
star_velocity  = stars_last_30_days / max(total_stars, 1)
```

#### 2.2.4 R(s, o) — 观察者相关性

观察者相关性将全局的权威性投射到特定用户的研究方向上。

**基于 embedding 的语义相似度：**

```
R(s, o) = cosine_similarity(embed(source_profile), embed(observer_profile))

source_profile = 拼接(
    source.keywords,
    source.fields,
    source.recent_paper_titles[:5],  # 最近 5 篇论文标题
    source.venue_names[:3]           # 常发 venue
)

observer_profile = 拼接(
    observer.track_keywords,
    observer.track_methods,
    observer.liked_paper_titles[:10],  # 最近 like 的 10 篇论文
    observer.search_queries[:5]        # 最近 5 次搜索
)
```

这里复用现有的 `EmbeddingProvider`（`context_engine/embeddings.py`），使用 `text-embedding-3-small` 计算。

**领域归一化**：

相同 h-index 在不同领域代表不同含义。ML 领域 h-index=30 是中等水平，而理论 CS h-index=30 是顶级。

```
Q_normalized(s) = Q_raw(s) / Q_median(s.domain)

其中 Q_median(domain) 是该领域所有已知 source 的 Q 中位数。
```

这需要按领域维护 Q 的分布统计，可以在 `top_venues.yaml` 中按 domain 扩展。

### 2.3 锚点层级判定

锚点不是二元分类，而是一个**连续光谱**。为了实用，划分四个层级：

| 层级 | AnchorScore 区间 | 含义 | 系统行为 |
|------|-----------------|------|---------|
| **核心锚点** (Core Anchor) | ≥ 0.8 | 领域奠基者/顶会常客/关键 venue | 主动追踪，新论文自动推送，搜索结果置顶加权 |
| **活跃锚点** (Active Anchor) | 0.5 ~ 0.8 | 当前产出高、引用增速快、重要 repo | 纳入 DailyPaper 优先排序，Judge 上下文注入 |
| **潜力锚点** (Emerging Anchor) | 0.3 ~ 0.5 | 新兴学者/新 repo/新趋势 | 标记关注，定期复查，Trending 候选 |
| **普通源** (Background) | < 0.3 | 背景噪声 | 仅在搜索命中时展示，不主动推荐 |

### 2.4 潜力锚点检测

潜力锚点的识别特别关键 — 这是"有潜力的源头"的核心。

**特征定义：内在质量不高，但动态信号异常强**

```python
def classify_emerging_anchor(source, window_months=6):
    """
    识别潜力锚点：内在质量一般，但增速异常。

    核心思想：
      - 核心锚点 = 高 Q + 高 N（已经很强了）
      - 潜力锚点 = 中低 Q + 异常高 ΔN 或 ΔT（正在变强）
    """
    q = intrinsic_quality(source)
    t = temporal_momentum(source)

    # 网络位置变化量：最近 window 内的 N(s) 增速
    n_current = network_authority(source, time=now)
    n_previous = network_authority(source, time=now - window)
    delta_n = (n_current - n_previous) / max(n_previous, 0.01)

    # 异常检测：增速是否超过同层级 source 的 2σ
    peers = get_peers(source, q_range=(q - 0.1, q + 0.1))
    peer_delta_mean = mean([delta_n_of(p) for p in peers])
    peer_delta_std = std([delta_n_of(p) for p in peers])

    z_score = (delta_n - peer_delta_mean) / max(peer_delta_std, 0.01)

    if q < 0.5 and z_score > 2.0:
        return "emerging_anchor"
    elif q >= 0.8:
        return "core_anchor"
    elif q >= 0.5:
        return "active_anchor"
    else:
        return "background"
```

**Scholar 潜力信号：**

| 信号 | 检测方法 | 示例 |
|------|---------|------|
| **顶会突破** | 首次在 tier1 venue 发表 | 博士生的第一篇 NeurIPS |
| **锚点合作** | 首次与核心锚点合作 | 新学者与 Dawn Song 合著 |
| **引用爆发** | 近 6 个月引用增速 > 同年龄段 2σ | 一篇论文突然被广泛引用 |
| **跨领域迁移** | 原本在 A 领域，开始在 B 领域发表 | Systems 学者开始做 ML Security |
| **代码影响力** | 关联 repo stars 快速增长 | 论文 repo 一月内 1000+ stars |

**Topic 潜力信号：**

| 信号 | 检测方法 |
|------|---------|
| **论文聚集** | 近 3 个月该 topic 论文数量异常增长 |
| **锚点学者进入** | 核心锚点开始在该 topic 发表 |
| **跨域引用** | 多个不同领域的论文开始引用该 topic 的论文 |
| **Industry 关注** | 关联 repo 出现企业贡献者/sponsor |

---

## 3. 与经典算法的关系

### 3.1 vs. PageRank

PageRank 是同构有向图上的全局权威评分。本模型的 N(s) 分量是 PageRank 在异构图上的扩展，增加了：
- 边类型权重（不同关系传播不同强度）
- 节点类型感知（Scholar 和 Paper 的权威含义不同）
- Q(s) 先验（初始化不是均匀的，而是用内在质量）

### 3.2 vs. HITS

HITS 区分 Hub（指向好东西的节点）和 Authority（被好东西指向的节点）。在本模型中：
- Survey 论文是 Hub，被 survey 引用的原创论文是 Authority
- 数据源网站（papers.cool、arXiv）是 Hub，被它们列出的论文是 Authority
- HITS 可以作为 N(s) 的替代算法，提供更精细的角色区分

### 3.3 vs. TrustRank

TrustRank 从一组已知可信的种子节点（"白名单"）开始，沿链接传播信任。在本模型中：
- Scholar 订阅列表（`scholar_subscriptions.yaml`）是天然的种子锚点
- `top_venues.yaml` 的 tier1 venue 是天然的种子锚点
- 可以用 TrustRank 的思路：从种子集出发做有限跳数的权威传播

### 3.4 vs. Metapath2Vec / HAN

Metapath2Vec 和 HAN（Heterogeneous Attention Network）是异构图上的表征学习方法。它们通过元路径引导的随机游走或注意力机制学习节点嵌入。

对于 PaperBot 的规模（数千到数万节点），显式的 PageRank 计算比深度图模型更实用。但如果未来需要更精细的语义相似度（如"找到和 X 学者研究风格相似的学者"），图嵌入方法值得考虑。

---

## 4. 与 PaperBot 现有基础的对接

### 4.1 已有基础设施

| 已有组件 | 对应锚点模型分量 | 当前限制 |
|---------|-----------------|---------|
| `InfluenceCalculator` (PIS) | Q(s) — Paper 内在质量 | 仅评估 Paper，未扩展到 Scholar/Venue |
| `DynamicPISCalculator` | T(s) — 时间动态 | 仅估算引用速度，无真实引用历史 |
| `top_venues.yaml` (tier1/tier2) | Q(s) — Venue 内在质量 | 静态配置，无自动发现新 venue |
| `Scholar` domain model | Q(s) — Scholar 内在质量 | h-index 无领域归一化 |
| Scholar Network API (coauthor graph) | N(s) — 网络位置输入 | 已有 coauthor 数据，但未计算传播分数 |
| Judge 5 维评分 | Q(s) — Paper 细粒度质量 | 独立评分，未反哺 source 权威 |
| `TrackRouter` (keyword matching) | R(s,o) — 观察者相关性 | 基于 keyword overlap，非语义嵌入 |
| `EmbeddingProvider` (OpenAI) | R(s,o) — 语义计算 | 已有基础设施，但未用于 source 评分 |
| `INFLUENCE_WEIGHTS` | 权重配置 | 现有权重结构可复用 |
| `_score_record()` in topic search | 搜索排序 | 仅用 token 匹配，未考虑 source 权威 |

### 4.2 关键缺口

1. **无 Source 统一注册** — Scholar/Venue/Repo 是独立的，没有统一的 `Source` 抽象
2. **无网络级评分** — 所有评分都是实体级的，没有权威传播
3. **无 Source 间关系建模** — coauthor 数据已有但未用于评分
4. **Judge 评分单向流** — Judge 评完论文后分数不反哺到学者/venue 的权威
5. **搜索排序忽略 source** — `_score_record()` 不考虑论文作者/venue 的锚点地位

### 4.3 反哺回路

锚点模型一旦建立，可以反哺现有的多个模块：

```
Source Authority Layer
    │
    ├──→ DailyPaper: global_top 排序时加入 anchor_boost
    │    anchor_boost = 0.2 * max(author_anchor_scores)
    │    final_score = base_score + anchor_boost
    │
    ├──→ Topic Search: _score_record() 中加入 source_authority_factor
    │    source_factor = avg(author_anchors) * venue_anchor
    │    score *= (1 + 0.3 * source_factor)
    │
    ├──→ Judge: 评分上下文中注入 "This paper is by [anchor_level] scholar X"
    │    帮助 LLM Judge 更好地评估 impact 维度
    │
    ├──→ Scholar Tracking: 自动发现潜力锚点，建议订阅
    │    "New emerging anchor detected: Y (z_score=2.5, 3 ICML papers in 6 months)"
    │
    ├──→ Trending: trending_score 中加入 source_authority 权重
    │    trending_score += 0.15 * avg_author_anchor_score
    │
    └──→ 推荐系统: 基于用户锚点偏好推荐新论文
         "Based on your core anchors, you might find this relevant..."
```

---

## 5. 实施架构

### 5.1 系统架构

```
                    ┌─────────────────────────────────┐
                    │     Source Authority Layer        │
                    │                                   │
  ┌─────────┐      │  ┌───────────────────────────┐   │
  │ S2 API  │──────│──│ 1. Source Registry         │   │
  │ (引用/  │      │  │    统一 Scholar/Venue/Repo  │   │
  │  合作)  │      │  │    为 Source 实体           │   │
  └─────────┘      │  └─────────────┬───────────────┘   │
                    │               │                    │
  ┌─────────┐      │  ┌────────────▼────────────────┐  │
  │ PIS /   │──────│──│ 2. Relation Graph           │  │
  │ Judge / │      │  │    Source 间关系网络         │  │
  │ Venues  │      │  │    (引用/合作/发表/主题)     │  │
  └─────────┘      │  └─────────────┬───────────────┘  │
                    │               │                    │
  ┌─────────┐      │  ┌────────────▼────────────────┐  │
  │ Track   │──────│──│ 3. Authority Propagation    │  │
  │ Router  │      │  │    异构 PageRank 迭代计算    │  │
  │ (用户   │      │  │    Q(s) + N(s) + T(s)       │  │
  │  偏好)  │      │  └─────────────┬───────────────┘  │
  └─────────┘      │               │                    │
                    │  ┌────────────▼────────────────┐  │
                    │  │ 4. Anchor Classifier        │  │
                    │  │    锚点层级判定              │  │
                    │  │    + 潜力锚点异常检测        │  │
                    │  └─────────────┬───────────────┘  │
                    │               │                    │
                    │  ┌────────────▼────────────────┐  │
                    │  │ 5. Observer Projection      │  │
                    │  │    R(s,o) 个性化投影         │  │
                    │  │    基于 Track + Embedding    │  │
                    │  └────────────────────────────┘   │
                    └─────────────────┬─────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        DailyPaper              Scholar Tracking        推荐系统
        排序加权               自动锚点发现            个性化推荐
```

### 5.2 数据模型

```sql
-- Source 统一注册表
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,          -- 'scholar' | 'venue' | 'website' | 'repo' | 'topic'
    name TEXT NOT NULL,
    external_id TEXT,                   -- S2 author ID / venue name / repo URL
    intrinsic_score REAL DEFAULT 0,     -- Q(s)
    network_authority REAL DEFAULT 0,   -- N(s)
    temporal_momentum REAL DEFAULT 0,   -- T(s)
    anchor_score REAL DEFAULT 0,        -- AnchorScore(s) 全局版
    anchor_level TEXT DEFAULT 'background', -- core/active/emerging/background
    attributes_json TEXT,               -- 类型特定属性 (h_index, stars, tier, ...)
    first_seen_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    UNIQUE(source_type, external_id)
);

-- Source 间关系表
CREATE TABLE source_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,         -- 'cites' | 'coauthors' | 'published_at' | ...
    weight REAL DEFAULT 1.0,            -- 边权重（合作频次/引用次数/...）
    evidence_json TEXT,                 -- 关系证据 (论文ID列表/时间跨度/...)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, target_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (target_id) REFERENCES sources(id)
);

-- 用户个性化锚点评分
CREATE TABLE user_anchor_scores (
    user_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    observer_relevance REAL DEFAULT 0,  -- R(s, o)
    personalized_anchor_score REAL DEFAULT 0,
    last_computed_at TEXT NOT NULL,
    PRIMARY KEY (user_id, source_id),
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- 锚点变化历史（用于潜力检测）
CREATE TABLE anchor_score_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    score_type TEXT NOT NULL,            -- 'intrinsic' | 'network' | 'temporal' | 'anchor'
    score_value REAL NOT NULL,
    computed_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
CREATE INDEX idx_anchor_history_source_time ON anchor_score_history(source_id, computed_at);
```

### 5.3 计算调度

锚点评分不需要实时计算（与搜索不同），可以按不同频率批量更新：

| 计算任务 | 频率 | 触发方式 | 说明 |
|---------|------|---------|------|
| Q(s) 更新 | 每周 | ARQ Cron | 重新计算内在质量（新引用/新论文/新 stars） |
| N(s) PageRank | 每周 | Q(s) 更新后 | 在关系图上运行 20 次迭代 |
| T(s) 动态 | 每日 | DailyPaper 后 | 更新时间衰减和速度指标 |
| R(s,o) 投影 | 每次 Track 变更 | 用户操作触发 | 重算与当前 Track 的语义相似度 |
| 潜力检测 | 每周 | N(s) 更新后 | Z-score 异常检测 |
| 锚点层级判定 | 每周 | 所有分量更新后 | 重新分类 core/active/emerging/background |

### 5.4 冷启动策略

新系统没有足够的关系数据来运行 PageRank。冷启动方案：

1. **种子锚点**：`scholar_subscriptions.yaml` 中的学者 + `top_venues.yaml` 中的 tier1 venue 作为初始核心锚点
2. **反向填充**：对种子锚点调用 S2 API 获取 coauthor 和 cited papers，构建初始关系图
3. **Bootstrap PageRank**：在初始图上运行 PageRank，产生第一批 N(s) 分数
4. **DailyPaper 持续积累**：每次 DailyPaper 运行时，新论文的 authors/venues/citations 持续充实关系图
5. **Judge 反哺**：高分论文的 authors 获得 Q(s) boost，逐步建立更多数据

---

## 6. 与记忆模块的关系

锚点模型和记忆模块（见 `memory_module_complete_proposal.md`）是互补的两个系统：

| 维度 | 锚点模型 | 记忆模块 |
|------|---------|---------|
| **关注对象** | 信息源（外部世界的客观属性） | 用户知识（内部世界的主观积累） |
| **数据来源** | S2 API, 引用网络, venue 配置 | 用户交互, feedback, 聊天记录 |
| **时间特征** | 周级更新，变化缓慢 | 实时写入，变化快速 |
| **个性化方式** | R(s,o) 投影 — 全局权威的个人视角 | scope/track — 用户自己的知识结构 |
| **协作点** | 记忆中的 "interest" 类型记忆 → 提供 observer_profile | 锚点评分 → 影响记忆中的 "insight" 提取优先级 |

**数据流：**

```
用户行为 ──→ 记忆模块（提取 interest/preference）
                │
                └──→ 锚点模型 R(s,o)（用 interest 计算观察者相关性）
                        │
                        └──→ DailyPaper/Search（锚点加权排序）
                                │
                                └──→ 记忆模块（高分论文写入 episode/insight）
```

---

## 7. 参考文献

### 算法基础

- Page, L., Brin, S., Motwani, R., & Winograd, T. (1999). The PageRank Citation Ranking: Bringing Order to the Web.
- Kleinberg, J. M. (1999). Authoritative Sources in a Hyperlinked Environment. JACM.
- Gyöngyi, Z., Garcia-Molina, H., & Pedersen, J. (2004). Combating Web Spam with TrustRank. VLDB.
- Sun, Y., Han, J., Yan, X., Yu, P. S., & Wu, T. (2011). PathSim: Meta Path-Based Top-K Similarity Search in Heterogeneous Information Networks. VLDB.
- Dong, Y., Chawla, N. V., & Swami, A. (2017). metapath2vec: Scalable Representation Learning for Heterogeneous Networks. KDD.
- Wang, X., Ji, H., Shi, C., Wang, B., et al. (2019). Heterogeneous Graph Attention Network. WWW.

### 学术影响力度量

- Hirsch, J. E. (2005). An index to quantify an individual's scientific research output. PNAS.
- Radicchi, F., Fortunato, S., & Castellano, C. (2008). Universality of citation distributions: Toward an objective measure of scientific impact. PNAS.
- Wang, D., Song, C., & Barabási, A. L. (2013). Quantifying Long-Term Scientific Impact. Science.

### PaperBot 现有实现

- `src/paperbot/domain/influence/calculator.py` — PIS 评分计算器
- `src/paperbot/domain/influence/analyzers/dynamic_pis.py` — 引用速度分析
- `src/paperbot/domain/influence/weights.py` — 评分权重配置
- `src/paperbot/domain/scholar.py` — Scholar 领域模型
- `config/top_venues.yaml` — Venue tier 配置
- `config/scholar_subscriptions.yaml` — 种子锚点配置
