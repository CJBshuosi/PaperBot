# Paper Collection & Resource Pool v1 - Technical Design Document

> **Status**: Draft
> **Author**: Claude Code
> **Date**: 2026-02-03
> **Estimated Effort**: 5-7 days (~40h)

---

## 0. Architecture Context: Where v1 Fits

v1 spans **three layers** of the PaperBot architecture, focusing on **Paper Harvesting, Storage, and Search capabilities**.

### 0.1 PaperBot Architecture with Harvest Layer

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PaperBot Standard Architecture                           │
│         (Offline Ingestion → Storage → Online Retrieval → Generation → Feedback)│
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 1 · Ingestion (Async) - HARVEST LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ ╔════════════════════════════════════════════════════════════════════╗   │   │
│  │ ║  v1: Paper Harvesters                                              ║   │   │
│  │ ║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 ║   │   │
│  │ ║  │   arXiv     │  │ Semantic    │  │  OpenAlex   │                 ║   │   │
│  │ ║  │  Harvester  │  │  Scholar    │  │  Harvester  │                 ║   │   │
│  │ ║  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 ║   │   │
│  │ ║         └─────────────────┼─────────────────┘                      ║   │   │
│  │ ║                           ▼                                        ║   │   │
│  │ ║               ┌───────────────────────┐                            ║   │   │
│  │ ║               │  PaperDeduplicator    │                            ║   │   │
│  │ ║               │  (DOI/Title/ID match) │                            ║   │   │
│  │ ║               └───────────┬───────────┘                            ║   │   │
│  │ ╚═══════════════════════════╪════════════════════════════════════════╝   │   │
│  └─────────────────────────────┼────────────────────────────────────────────┘   │
│                                ▼                                                 │
└────────────────────────────────┼─────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────────────┐
│  Layer 2 · Storage                                                               │
│  ┌─────────────────────────────▼────────────────────────────────────────────┐   │
│  │  SQL 主库 (SQLite/Postgres)                                               │   │
│  │  ╔═══════════════════════════════════════════════════════════════════╗   │   │
│  │  ║  v1: papers table (NEW)                                           ║   │   │
│  │  ║  - doi, arxiv_id, semantic_scholar_id, openalex_id               ║   │   │
│  │  ║  - title, abstract, authors, year, venue, citations               ║   │   │
│  │  ║  - title_hash (dedup), primary_source, sources_json              ║   │   │
│  │  ╠═══════════════════════════════════════════════════════════════════╣   │   │
│  │  ║  v1: harvest_runs table (NEW)                                     ║   │   │
│  │  ║  - run_id, keywords, venues, status, papers_found/new/deduped    ║   │   │
│  │  ╚═══════════════════════════════════════════════════════════════════╝   │   │
│  │    research_tracks / tasks / paper_feedback (existing)                   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┼─────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────────────┐
│  Layer 3 · Retrieval (Online)                                                    │
│  ┌─────────────────────────────▼────────────────────────────────────────────┐   │
│  │  ╔═══════════════════════════════════════════════════════════════════╗   │   │
│  │  ║  v1: PaperStore.search_papers() (NEW)                             ║   │   │
│  │  ║  - Full-text search in title/abstract                             ║   │   │
│  │  ║  - Filter by: keywords, venues, year range, citations, sources   ║   │   │
│  │  ║  - Sort by: citation_count, year, created_at                     ║   │   │
│  │  ║  - Pagination with limit/offset (TopN)                           ║   │   │
│  │  ╚═══════════════════════════════════════════════════════════════════╝   │   │
│  │  ContextEngine / TrackRouter / Paper Searcher (existing)                 │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┼─────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────────────┐
│  Layer 4-5 · Generation & Feedback (Existing - No Changes)                       │
│  ┌─────────────────────────────▼────────────────────────────────────────────┐   │
│  │  PromptComposer → LLM → Output Parser → Paper Feedback                   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘

Legend:
  ╔═══╗  v1 Focus Area (Paper Harvest & Storage)
  ╚═══╝
  ───▶   Data Flow
```

### 0.2 v1 Components Mapped to Architecture Layers

| Layer | Component | v1 Deliverable |
|-------|-----------|----------------|
| **Layer 1: Ingestion** | Harvesters | ArxivHarvester, SemanticScholarHarvester, OpenAlexHarvester |
| | Query Services | VenueRecommender, QueryRewriter |
| | Deduplication | PaperDeduplicator (multi-strategy) |
| **Layer 2: Storage** | `papers` table | Paper metadata with multi-source IDs |
| | `harvest_runs` table | Harvest execution tracking |
| | PaperStore | SQLAlchemy repository implementation |
| **Layer 3: Retrieval** | Search API | Filter-based TopN retrieval |

### 0.3 v1 Focus: Harvest Pipeline

```
                    ┌─────────────────────────────────────────┐
                    │         v1: Harvest Pipeline            │
                    └─────────────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  Query Services     │   │  Harvesters         │   │  Storage & Search   │
│                     │   │                     │   │                     │
│  - VenueRecommender │   │  - ArxivHarvester   │   │  - PaperStore       │
│    keyword→venues   │   │  - S2Harvester      │   │    upsert/search    │
│  - QueryRewriter    │   │  - OpenAlexHarvester│   │  - Deduplication    │
│    expand/synonyms  │   │                     │   │    DOI/title/ID     │
│                     │   │                     │   │                     │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────────┐
                    │        Implementation Artifacts         │
                    │                                         │
                    │  src/paperbot/domain/harvest.py         │
                    │  src/paperbot/infrastructure/harvesters/│
                    │  src/paperbot/infrastructure/stores/    │
                    │  src/paperbot/application/services/     │
                    │  src/paperbot/api/routes/harvest.py     │
                    └─────────────────────────────────────────┘
```

### 0.4 Data Flow with v1 Touch Points

```
                              USER INPUT
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  POST /api/harvest                                  │  │
    │  │  keywords: ["ransomware", "machine learning"]       │  │
    │  │  venues: ["USENIX Security", "CCS"] (optional)      │  │
    │  │  year_from: 2020, year_to: 2024 (optional)          │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                             │                             │
    └─────────────────────────────┼─────────────────────────────┘
                                  │
                            QUERY SERVICES
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  VenueRecommender.recommend()                       │  │
    │  │  ╔═══════════════════════════════════════════════╗  │  │
    │  │  ║ v1: keyword→venue mapping from config         ║  │  │
    │  │  ║ "ransomware" → security: [CCS, S&P, USENIX]   ║  │  │
    │  │  ╚═══════════════════════════════════════════════╝  │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                             │                             │
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  QueryRewriter.rewrite()                            │  │
    │  │  ╔═══════════════════════════════════════════════╗  │  │
    │  │  ║ v1: abbreviation expansion + synonyms         ║  │  │
    │  │  ║ "ML" → "machine learning"                     ║  │  │
    │  │  ║ "LLM" → "large language model"                ║  │  │
    │  │  ╚═══════════════════════════════════════════════╝  │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                           │
    └─────────────────────────────┼─────────────────────────────┘
                                  │
                         PARALLEL HARVEST
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │              ┌──────────────┼──────────────┐              │
    │              ▼              ▼              ▼              │
    │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │
    │  │ ArxivHarvester │ │  S2Harvester   │ │OpenAlexHarvest │ │
    │  │ ╔════════════╗ │ │ ╔════════════╗ │ │ ╔════════════╗ │ │
    │  │ ║ v1: Atom   ║ │ │ ║ v1: REST   ║ │ │ ║ v1: REST   ║ │ │
    │  │ ║ XML API    ║ │ │ ║ API wrap   ║ │ │ ║ API (new)  ║ │ │
    │  │ ╚════════════╝ │ │ ╚════════════╝ │ │ ╚════════════╝ │ │
    │  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘ │
    │          └──────────────────┼──────────────────┘          │
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  List[HarvestedPaper] (unified format)              │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                           │
    └─────────────────────────────┼─────────────────────────────┘
                                  │
                           DEDUPLICATION
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  PaperDeduplicator.deduplicate()                    │  │
    │  │  ╔═══════════════════════════════════════════════╗  │  │
    │  │  ║ v1: Multi-strategy matching (priority order): ║  │  │
    │  │  ║ 1. DOI (canonical, most reliable)             ║  │  │
    │  │  ║ 2. arXiv ID                                   ║  │  │
    │  │  ║ 3. Semantic Scholar ID                        ║  │  │
    │  │  ║ 4. OpenAlex ID                                ║  │  │
    │  │  ║ 5. Normalized title hash (fallback)          ║  │  │
    │  │  ╚═══════════════════════════════════════════════╝  │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                           │
    └─────────────────────────────┼─────────────────────────────┘
                                  │
                              STORAGE
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  PaperStore.upsert_papers_batch()                   │  │
    │  │  ╔═══════════════════════════════════════════════╗  │  │
    │  │  ║ v1: Atomic upsert with dedup at DB level      ║  │  │
    │  │  ║ - Unique constraints on DOI, arxiv_id, etc.   ║  │  │
    │  │  ║ - Merge metadata from duplicates              ║  │  │
    │  │  ║ - Track sources that returned each paper      ║  │  │
    │  │  ╚═══════════════════════════════════════════════╝  │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                           │
    └─────────────────────────────┼─────────────────────────────┘
                                  │
                             RETRIEVAL
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             ▼                             │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  POST /api/papers/search                            │  │
    │  │  ╔═══════════════════════════════════════════════╗  │  │
    │  │  ║ v1: Filter-based search with TopN             ║  │  │
    │  │  ║ - Full-text: title LIKE '%query%'             ║  │  │
    │  │  ║ - Filters: year, venue, citations, source     ║  │  │
    │  │  ║ - Sort: citation_count DESC (default)         ║  │  │
    │  │  ║ - Pagination: limit=50, offset=0              ║  │  │
    │  │  ╚═══════════════════════════════════════════════╝  │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                           │
    └───────────────────────────────────────────────────────────┘
```

---

## 1. Executive Summary

**Objective**: Build a stable pipeline for "keywords → recommend venues → pull papers → store → search", enabling paper collection from 3 open sources with deduplication and filter-based retrieval.

**Current State**:
- ArxivConnector exists (XML parsing only, no search)
- SemanticScholarClient exists (async API wrapper)
- No unified harvester interface
- No persistent paper storage
- No deduplication across sources

**Scope**: This document covers the v1 deliverables:
1. Unified harvester interface and 3 implementations
2. Paper storage with multi-strategy deduplication
3. Query services (VenueRecommender, QueryRewriter)
4. API endpoints for harvest and search

**Non-Goals (deferred to v2)**:
- PDF downloading and parsing
- Full-text search (FTS5/Elasticsearch)
- Embedding-based semantic search
- Authenticated sources (IEEE, ACM)

---

## 2. Technical Solution Design

### 2.1 Domain Models

#### 2.1.1 HarvestedPaper (Unified Format)

**File**: `src/paperbot/domain/harvest.py`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | str | Yes | Paper title |
| `abstract` | str | No | Paper abstract |
| `authors` | List[str] | No | Author names |
| `doi` | str | No | Digital Object Identifier |
| `arxiv_id` | str | No | arXiv identifier (e.g., 2301.12345) |
| `semantic_scholar_id` | str | No | S2 paper ID |
| `openalex_id` | str | No | OpenAlex work ID |
| `year` | int | No | Publication year |
| `venue` | str | No | Conference/journal name |
| `publication_date` | str | No | ISO date string |
| `citation_count` | int | No | Number of citations |
| `url` | str | No | Paper URL |
| `pdf_url` | str | No | PDF URL (metadata only, no download) |
| `keywords` | List[str] | No | Author keywords |
| `fields_of_study` | List[str] | No | Research fields |
| `source` | HarvestSource | Yes | Which harvester found this |
| `source_rank` | int | No | Position in source results |

```python
@dataclass
class HarvestedPaper:
    title: str
    source: HarvestSource
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    openalex_id: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    publication_date: Optional[str] = None
    citation_count: int = 0
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    fields_of_study: List[str] = field(default_factory=list)
    source_rank: Optional[int] = None
```

#### 2.1.2 HarvestSource Enum

```python
class HarvestSource(str, Enum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
```

#### 2.1.3 HarvestResult

```python
@dataclass
class HarvestResult:
    """Result from a single harvester."""
    source: HarvestSource
    papers: List[HarvestedPaper]
    total_found: int
    error: Optional[str] = None

@dataclass
class HarvestRunResult:
    """Aggregated result from all harvesters."""
    run_id: str
    status: str  # running/success/partial/failed
    papers_found: int
    papers_new: int
    papers_deduplicated: int
    source_results: Dict[HarvestSource, HarvestResult]
    started_at: datetime
    ended_at: Optional[datetime] = None
```

### 2.2 Database Schema

#### 2.2.1 papers Table (NEW)

**File**: `alembic/versions/0003_paper_harvest_tables.py`

```sql
CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Canonical identifiers (for deduplication)
    doi TEXT UNIQUE,
    arxiv_id TEXT UNIQUE,
    semantic_scholar_id TEXT UNIQUE,
    openalex_id TEXT UNIQUE,
    title_hash TEXT NOT NULL,  -- SHA256 of normalized title

    -- Core metadata
    title TEXT NOT NULL,
    abstract TEXT DEFAULT '',
    authors_json TEXT DEFAULT '[]',
    year INTEGER,
    venue TEXT,
    publication_date TEXT,
    citation_count INTEGER DEFAULT 0,

    -- URLs (no PDF download, just references)
    url TEXT,
    pdf_url TEXT,

    -- Classification
    keywords_json TEXT DEFAULT '[]',
    fields_of_study_json TEXT DEFAULT '[]',

    -- Source tracking
    primary_source TEXT NOT NULL,  -- First source that found this paper
    sources_json TEXT DEFAULT '[]',  -- All sources that returned this paper

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP  -- Soft delete
);

-- Indexes
CREATE INDEX idx_papers_doi ON papers(doi);
CREATE INDEX idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX idx_papers_title_hash ON papers(title_hash);
CREATE INDEX idx_papers_year ON papers(year);
CREATE INDEX idx_papers_venue ON papers(venue);
CREATE INDEX idx_papers_citation_count ON papers(citation_count);
CREATE INDEX idx_papers_created_at ON papers(created_at);
```

#### 2.2.2 harvest_runs Table (NEW)

```sql
CREATE TABLE harvest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,

    -- Input
    keywords_json TEXT DEFAULT '[]',
    venues_json TEXT DEFAULT '[]',
    sources_json TEXT DEFAULT '[]',
    max_results_per_source INTEGER DEFAULT 100,

    -- Results
    status TEXT DEFAULT 'running',  -- running/success/partial/failed
    papers_found INTEGER DEFAULT 0,
    papers_new INTEGER DEFAULT 0,
    papers_deduplicated INTEGER DEFAULT 0,
    error_json TEXT DEFAULT '{}',

    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE INDEX idx_harvest_runs_run_id ON harvest_runs(run_id);
CREATE INDEX idx_harvest_runs_status ON harvest_runs(status);
CREATE INDEX idx_harvest_runs_started_at ON harvest_runs(started_at);
```

#### 2.2.3 SQLAlchemy Models

**File**: `src/paperbot/infrastructure/stores/models.py` (additions)

```python
class PaperModel(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Canonical identifiers
    doi: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    semantic_scholar_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    openalex_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Core metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, default="")
    authors_json: Mapped[str] = mapped_column(Text, default="[]")
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    publication_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # URLs
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Classification
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    fields_of_study_json: Mapped[str] = mapped_column(Text, default="[]")

    # Source tracking
    primary_source: Mapped[str] = mapped_column(String(32), nullable=False)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")

    # Timestamps
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class HarvestRunModel(Base):
    __tablename__ = "harvest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Input
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    venues_json: Mapped[str] = mapped_column(Text, default="[]")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    max_results_per_source: Mapped[int] = mapped_column(Integer, default=100)

    # Results
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    papers_found: Mapped[int] = mapped_column(Integer, default=0)
    papers_new: Mapped[int] = mapped_column(Integer, default=0)
    papers_deduplicated: Mapped[int] = mapped_column(Integer, default=0)
    error_json: Mapped[str] = mapped_column(Text, default="{}")

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 2.3 Harvester Interface

**File**: `src/paperbot/application/ports/harvester_port.py`

```python
from typing import Protocol, runtime_checkable, Optional, List
from paperbot.domain.harvest import HarvestSource, HarvestResult

@runtime_checkable
class HarvesterPort(Protocol):
    """Abstract interface for all paper harvesters."""

    @property
    def source(self) -> HarvestSource:
        """Return the harvest source identifier."""
        ...

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,
    ) -> HarvestResult:
        """
        Search for papers matching the query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            year_from: Filter papers published on or after this year
            year_to: Filter papers published on or before this year
            venues: Filter papers from these venues (if supported)

        Returns:
            HarvestResult with papers and metadata
        """
        ...

    async def close(self) -> None:
        """Release resources (HTTP sessions, etc.)."""
        ...
```

### 2.4 Harvester Implementations

#### 2.4.1 ArxivHarvester

**File**: `src/paperbot/infrastructure/harvesters/arxiv_harvester.py`

```python
class ArxivHarvester:
    """
    arXiv paper harvester using the Atom API.

    API: https://export.arxiv.org/api/query
    Rate limit: 1 request per 3 seconds (be conservative)
    """

    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    REQUEST_INTERVAL = 3.0  # seconds between requests

    def __init__(self, connector: ArxivConnector):
        self.connector = connector
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def source(self) -> HarvestSource:
        return HarvestSource.ARXIV

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,  # Not supported by arXiv
    ) -> HarvestResult:
        """
        Search arXiv using the Atom API.

        Query syntax: https://arxiv.org/help/api/user-manual#query_details
        """
        # Build query with year filters if provided
        search_query = self._build_query(query, year_from, year_to)

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            async with self._get_session().get(self.ARXIV_API_URL, params=params) as resp:
                xml_text = await resp.text()

            records = self.connector.parse_atom(xml_text)
            papers = [self._record_to_paper(r, rank=i) for i, r in enumerate(records)]

            return HarvestResult(
                source=self.source,
                papers=papers,
                total_found=len(papers),
            )
        except Exception as e:
            return HarvestResult(
                source=self.source,
                papers=[],
                total_found=0,
                error=str(e),
            )

    def _record_to_paper(self, record: ArxivRecord, rank: int) -> HarvestedPaper:
        """Convert ArxivRecord to HarvestedPaper."""
        # Extract arxiv_id from full URL (e.g., "http://arxiv.org/abs/2301.12345v1")
        arxiv_id = record.arxiv_id.split("/")[-1].split("v")[0]

        # Extract year from published date
        year = None
        if record.published:
            try:
                year = int(record.published[:4])
            except ValueError:
                pass

        return HarvestedPaper(
            title=record.title,
            source=HarvestSource.ARXIV,
            abstract=record.summary,
            authors=record.authors,
            arxiv_id=arxiv_id,
            year=year,
            publication_date=record.published,
            url=record.abs_url,
            pdf_url=record.pdf_url,
            source_rank=rank,
        )
```

#### 2.4.2 SemanticScholarHarvester

**File**: `src/paperbot/infrastructure/harvesters/semantic_scholar_harvester.py`

```python
class SemanticScholarHarvester:
    """
    Semantic Scholar paper harvester.

    API: https://api.semanticscholar.org/graph/v1/paper/search
    Rate limit: 100 req/min (with API key), 5000/day without key
    """

    FIELDS = [
        "paperId", "title", "abstract", "year", "venue",
        "citationCount", "authors", "publicationDate",
        "externalIds", "fieldsOfStudy", "url", "openAccessPdf"
    ]

    def __init__(self, client: SemanticScholarClient):
        self.client = client

    @property
    def source(self) -> HarvestSource:
        return HarvestSource.SEMANTIC_SCHOLAR

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,
    ) -> HarvestResult:
        """Search Semantic Scholar API."""
        try:
            # S2 API supports year filter in query
            year_filter = ""
            if year_from and year_to:
                year_filter = f" year:{year_from}-{year_to}"
            elif year_from:
                year_filter = f" year:{year_from}-"
            elif year_to:
                year_filter = f" year:-{year_to}"

            results = await self.client.search_papers(
                query=query + year_filter,
                limit=max_results,
                fields=self.FIELDS,
            )

            papers = [self._to_paper(r, rank=i) for i, r in enumerate(results)]

            # Filter by venue if specified
            if venues:
                venue_set = {v.lower() for v in venues}
                papers = [p for p in papers if p.venue and p.venue.lower() in venue_set]

            return HarvestResult(
                source=self.source,
                papers=papers,
                total_found=len(papers),
            )
        except Exception as e:
            return HarvestResult(
                source=self.source,
                papers=[],
                total_found=0,
                error=str(e),
            )

    def _to_paper(self, data: Dict[str, Any], rank: int) -> HarvestedPaper:
        """Convert S2 API response to HarvestedPaper."""
        authors = [a.get("name", "") for a in data.get("authors", [])]
        external_ids = data.get("externalIds", {}) or {}

        pdf_url = None
        if data.get("openAccessPdf"):
            pdf_url = data["openAccessPdf"].get("url")

        return HarvestedPaper(
            title=data.get("title", ""),
            source=HarvestSource.SEMANTIC_SCHOLAR,
            abstract=data.get("abstract") or "",
            authors=authors,
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            semantic_scholar_id=data.get("paperId"),
            year=data.get("year"),
            venue=data.get("venue"),
            publication_date=data.get("publicationDate"),
            citation_count=data.get("citationCount", 0),
            url=data.get("url"),
            pdf_url=pdf_url,
            fields_of_study=data.get("fieldsOfStudy") or [],
            source_rank=rank,
        )
```

#### 2.4.3 OpenAlexHarvester

**File**: `src/paperbot/infrastructure/harvesters/openalex_harvester.py`

```python
class OpenAlexHarvester:
    """
    OpenAlex paper harvester.

    API: https://docs.openalex.org/api-entities/works
    Rate limit: 10 req/s (polite pool with email), 100K/day
    """

    OPENALEX_API_URL = "https://api.openalex.org/works"
    REQUEST_INTERVAL = 0.1  # 10 req/s

    def __init__(self, email: Optional[str] = None):
        self.email = email  # For polite pool
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def source(self) -> HarvestSource:
        return HarvestSource.OPENALEX

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,
    ) -> HarvestResult:
        """Search OpenAlex API."""
        params = {
            "search": query,
            "per_page": min(max_results, 200),  # API max is 200
            "sort": "cited_by_count:desc",
        }

        # Add email for polite pool
        if self.email:
            params["mailto"] = self.email

        # Build filter string
        filters = []
        if year_from:
            filters.append(f"publication_year:>={year_from}")
        if year_to:
            filters.append(f"publication_year:<={year_to}")
        if filters:
            params["filter"] = ",".join(filters)

        try:
            async with self._get_session().get(self.OPENALEX_API_URL, params=params) as resp:
                data = await resp.json()

            results = data.get("results", [])
            papers = [self._to_paper(r, rank=i) for i, r in enumerate(results)]

            # Filter by venue if specified
            if venues:
                venue_set = {v.lower() for v in venues}
                papers = [p for p in papers if p.venue and p.venue.lower() in venue_set]

            return HarvestResult(
                source=self.source,
                papers=papers,
                total_found=data.get("meta", {}).get("count", len(papers)),
            )
        except Exception as e:
            return HarvestResult(
                source=self.source,
                papers=[],
                total_found=0,
                error=str(e),
            )

    def _to_paper(self, data: Dict[str, Any], rank: int) -> HarvestedPaper:
        """Convert OpenAlex API response to HarvestedPaper."""
        # Extract authors
        authors = []
        for authorship in data.get("authorships", []):
            author = authorship.get("author", {})
            if author.get("display_name"):
                authors.append(author["display_name"])

        # Extract identifiers
        ids = data.get("ids", {})
        doi = ids.get("doi", "").replace("https://doi.org/", "") if ids.get("doi") else None
        openalex_id = ids.get("openalex", "").replace("https://openalex.org/", "")

        # Extract venue
        venue = None
        if data.get("primary_location"):
            source = data["primary_location"].get("source") or {}
            venue = source.get("display_name")

        # Extract PDF URL
        pdf_url = None
        if data.get("open_access", {}).get("oa_url"):
            pdf_url = data["open_access"]["oa_url"]

        return HarvestedPaper(
            title=data.get("title", ""),
            source=HarvestSource.OPENALEX,
            abstract=self._get_abstract(data),
            authors=authors,
            doi=doi,
            openalex_id=openalex_id,
            year=data.get("publication_year"),
            venue=venue,
            publication_date=data.get("publication_date"),
            citation_count=data.get("cited_by_count", 0),
            url=data.get("doi") or ids.get("openalex"),
            pdf_url=pdf_url,
            keywords=self._extract_keywords(data),
            fields_of_study=[c.get("display_name", "") for c in data.get("concepts", [])[:5]],
            source_rank=rank,
        )

    def _get_abstract(self, data: Dict[str, Any]) -> str:
        """Reconstruct abstract from inverted index."""
        abstract_index = data.get("abstract_inverted_index")
        if not abstract_index:
            return ""

        # OpenAlex stores abstract as inverted index: {"word": [positions]}
        words = []
        for word, positions in abstract_index.items():
            for pos in positions:
                words.append((pos, word))
        words.sort(key=lambda x: x[0])
        return " ".join(w[1] for w in words)
```

### 2.5 Query Services

#### 2.5.1 VenueRecommender

**File**: `src/paperbot/application/services/venue_recommender.py`

```python
class VenueRecommender:
    """
    Recommend relevant venues based on keywords.

    Uses a static mapping from keywords/domains to top venues.
    Configuration loaded from config/venue_mappings.yaml.
    """

    # Default keyword→venue mappings (can be overridden by config)
    DEFAULT_MAPPINGS = {
        # Security
        "security": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "ransomware": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "malware": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "cryptography": ["CRYPTO", "EUROCRYPT", "CCS"],
        "privacy": ["S&P", "PETS", "CCS", "USENIX Security"],

        # ML/AI
        "machine learning": ["NeurIPS", "ICML", "ICLR"],
        "deep learning": ["NeurIPS", "ICML", "ICLR", "CVPR"],
        "llm": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "large language model": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "transformer": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "nlp": ["ACL", "EMNLP", "NAACL", "NeurIPS"],
        "computer vision": ["CVPR", "ICCV", "ECCV", "NeurIPS"],

        # Systems
        "database": ["SIGMOD", "VLDB", "ICDE"],
        "systems": ["OSDI", "SOSP", "EuroSys", "ATC"],
        "networking": ["SIGCOMM", "NSDI", "MobiCom"],

        # Software Engineering
        "software engineering": ["ICSE", "FSE", "ASE"],
        "testing": ["ICSE", "ISSTA", "FSE"],
        "program analysis": ["PLDI", "POPL", "OOPSLA"],
    }

    def __init__(self, config_path: Optional[str] = None):
        self.mappings = self.DEFAULT_MAPPINGS.copy()
        if config_path:
            self._load_config(config_path)

    def recommend(
        self,
        keywords: List[str],
        *,
        max_venues: int = 5,
    ) -> List[str]:
        """
        Recommend venues based on keywords.

        Args:
            keywords: List of search keywords
            max_venues: Maximum number of venues to recommend

        Returns:
            List of recommended venue names, ordered by relevance
        """
        venue_scores: Dict[str, int] = {}

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Exact match
            if keyword_lower in self.mappings:
                for venue in self.mappings[keyword_lower]:
                    venue_scores[venue] = venue_scores.get(venue, 0) + 2

            # Partial match
            for mapped_kw, venues in self.mappings.items():
                if keyword_lower in mapped_kw or mapped_kw in keyword_lower:
                    for venue in venues:
                        venue_scores[venue] = venue_scores.get(venue, 0) + 1

        # Sort by score descending
        sorted_venues = sorted(venue_scores.items(), key=lambda x: -x[1])
        return [v[0] for v in sorted_venues[:max_venues]]
```

#### 2.5.2 QueryRewriter

**File**: `src/paperbot/application/services/query_rewriter.py`

```python
class QueryRewriter:
    """
    Expand and rewrite queries for better search coverage.

    Handles:
    - Abbreviation expansion (LLM → large language model)
    - Synonym addition (ML → machine learning)
    - Query normalization
    """

    # Abbreviation → full form mappings
    ABBREVIATIONS = {
        "llm": "large language model",
        "llms": "large language models",
        "ml": "machine learning",
        "dl": "deep learning",
        "nlp": "natural language processing",
        "cv": "computer vision",
        "rl": "reinforcement learning",
        "gan": "generative adversarial network",
        "gans": "generative adversarial networks",
        "cnn": "convolutional neural network",
        "cnns": "convolutional neural networks",
        "rnn": "recurrent neural network",
        "rnns": "recurrent neural networks",
        "lstm": "long short-term memory",
        "bert": "bidirectional encoder representations from transformers",
        "gpt": "generative pre-trained transformer",
        "rag": "retrieval augmented generation",
        "vae": "variational autoencoder",
        "asr": "automatic speech recognition",
        "tts": "text to speech",
        "ocr": "optical character recognition",
        "sql": "structured query language",
        "api": "application programming interface",
    }

    def __init__(self, abbreviations: Optional[Dict[str, str]] = None):
        self.abbreviations = {**self.ABBREVIATIONS}
        if abbreviations:
            self.abbreviations.update(abbreviations)

    def rewrite(self, query: str) -> List[str]:
        """
        Rewrite query to produce expanded variations.

        Args:
            query: Original search query

        Returns:
            List of query variations (original + expanded)
        """
        queries = [query]

        # Tokenize and expand abbreviations
        words = query.lower().split()
        expanded_words = []
        has_expansion = False

        for word in words:
            # Remove punctuation for matching
            clean_word = word.strip(".,;:!?()[]{}\"'")

            if clean_word in self.abbreviations:
                expanded_words.append(self.abbreviations[clean_word])
                has_expansion = True
            else:
                expanded_words.append(word)

        if has_expansion:
            expanded_query = " ".join(expanded_words)
            if expanded_query != query.lower():
                queries.append(expanded_query)

        return queries

    def normalize(self, query: str) -> str:
        """
        Normalize query for consistent matching.

        - Lowercase
        - Remove extra whitespace
        - Remove special characters (except alphanumeric and space)
        """
        import re
        normalized = query.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized
```

### 2.6 Deduplication Service

**File**: `src/paperbot/application/services/paper_deduplicator.py`

```python
class PaperDeduplicator:
    """
    Multi-strategy paper deduplication.

    Priority order:
    1. DOI (most reliable)
    2. arXiv ID
    3. Semantic Scholar ID
    4. OpenAlex ID
    5. Normalized title hash (fallback)
    """

    def __init__(self):
        self._doi_index: Dict[str, int] = {}
        self._arxiv_index: Dict[str, int] = {}
        self._s2_index: Dict[str, int] = {}
        self._openalex_index: Dict[str, int] = {}
        self._title_hash_index: Dict[str, int] = {}

    def deduplicate(
        self,
        papers: List[HarvestedPaper],
    ) -> Tuple[List[HarvestedPaper], int]:
        """
        Deduplicate papers in-memory.

        Args:
            papers: List of papers from all sources

        Returns:
            Tuple of (deduplicated papers, count of duplicates removed)
        """
        unique_papers: List[HarvestedPaper] = []
        duplicates_count = 0

        for paper in papers:
            existing_idx = self._find_duplicate(paper)

            if existing_idx is not None:
                # Merge metadata into existing paper
                self._merge_paper(unique_papers[existing_idx], paper)
                duplicates_count += 1
            else:
                # Add new paper
                idx = len(unique_papers)
                self._index_paper(paper, idx)
                unique_papers.append(paper)

        return unique_papers, duplicates_count

    def _find_duplicate(self, paper: HarvestedPaper) -> Optional[int]:
        """Find existing paper index if duplicate exists."""
        # 1. DOI match
        if paper.doi:
            doi_lower = paper.doi.lower()
            if doi_lower in self._doi_index:
                return self._doi_index[doi_lower]

        # 2. arXiv ID match
        if paper.arxiv_id:
            arxiv_lower = paper.arxiv_id.lower()
            if arxiv_lower in self._arxiv_index:
                return self._arxiv_index[arxiv_lower]

        # 3. Semantic Scholar ID match
        if paper.semantic_scholar_id:
            s2_lower = paper.semantic_scholar_id.lower()
            if s2_lower in self._s2_index:
                return self._s2_index[s2_lower]

        # 4. OpenAlex ID match
        if paper.openalex_id:
            openalex_lower = paper.openalex_id.lower()
            if openalex_lower in self._openalex_index:
                return self._openalex_index[openalex_lower]

        # 5. Title hash match (fallback)
        title_hash = self._compute_title_hash(paper.title)
        if title_hash in self._title_hash_index:
            return self._title_hash_index[title_hash]

        return None

    def _index_paper(self, paper: HarvestedPaper, idx: int) -> None:
        """Add paper to all relevant indexes."""
        if paper.doi:
            self._doi_index[paper.doi.lower()] = idx
        if paper.arxiv_id:
            self._arxiv_index[paper.arxiv_id.lower()] = idx
        if paper.semantic_scholar_id:
            self._s2_index[paper.semantic_scholar_id.lower()] = idx
        if paper.openalex_id:
            self._openalex_index[paper.openalex_id.lower()] = idx

        title_hash = self._compute_title_hash(paper.title)
        self._title_hash_index[title_hash] = idx

    def _merge_paper(self, existing: HarvestedPaper, new: HarvestedPaper) -> None:
        """Merge metadata from new paper into existing."""
        # Fill in missing identifiers
        if not existing.doi and new.doi:
            existing.doi = new.doi
        if not existing.arxiv_id and new.arxiv_id:
            existing.arxiv_id = new.arxiv_id
        if not existing.semantic_scholar_id and new.semantic_scholar_id:
            existing.semantic_scholar_id = new.semantic_scholar_id
        if not existing.openalex_id and new.openalex_id:
            existing.openalex_id = new.openalex_id

        # Prefer longer abstract
        if len(new.abstract) > len(existing.abstract):
            existing.abstract = new.abstract

        # Prefer higher citation count
        if new.citation_count > existing.citation_count:
            existing.citation_count = new.citation_count

        # Merge keywords and fields
        existing.keywords = list(set(existing.keywords + new.keywords))
        existing.fields_of_study = list(set(existing.fields_of_study + new.fields_of_study))

    @staticmethod
    def _compute_title_hash(title: str) -> str:
        """Compute normalized title hash for deduplication."""
        import hashlib
        import re

        # Normalize: lowercase, remove punctuation, collapse whitespace
        normalized = title.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return hashlib.sha256(normalized.encode()).hexdigest()
```

### 2.7 PaperStore Repository

**File**: `src/paperbot/infrastructure/stores/paper_store.py`

```python
class PaperStore:
    """
    Paper storage repository.

    Handles:
    - Batch upsert with DB-level deduplication
    - Filter-based search with pagination
    - Source tracking
    """

    def __init__(self, session_provider: SessionProvider):
        self.session_provider = session_provider

    async def upsert_papers_batch(
        self,
        papers: List[HarvestedPaper],
    ) -> Tuple[int, int]:
        """
        Upsert papers with deduplication.

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0

        with self.session_provider() as session:
            for paper in papers:
                existing = self._find_existing(session, paper)

                if existing:
                    self._update_paper(existing, paper)
                    updated_count += 1
                else:
                    model = self._create_model(paper)
                    session.add(model)
                    new_count += 1

            session.commit()

        return new_count, updated_count

    async def search_papers(
        self,
        *,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        venues: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_citations: Optional[int] = None,
        sources: Optional[List[str]] = None,
        sort_by: str = "citation_count",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PaperModel], int]:
        """
        Search papers with filters and pagination.

        Returns:
            Tuple of (papers, total_count)
        """
        with self.session_provider() as session:
            stmt = select(PaperModel).where(PaperModel.deleted_at.is_(None))

            # Full-text search (LIKE for v1)
            if query:
                pattern = f"%{query}%"
                stmt = stmt.where(
                    or_(
                        PaperModel.title.ilike(pattern),
                        PaperModel.abstract.ilike(pattern),
                    )
                )

            # Filters
            if year_from:
                stmt = stmt.where(PaperModel.year >= year_from)
            if year_to:
                stmt = stmt.where(PaperModel.year <= year_to)
            if min_citations:
                stmt = stmt.where(PaperModel.citation_count >= min_citations)
            if venues:
                stmt = stmt.where(PaperModel.venue.in_(venues))
            if sources:
                stmt = stmt.where(PaperModel.primary_source.in_(sources))

            # Count total
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_count = session.execute(count_stmt).scalar() or 0

            # Sort
            sort_col = getattr(PaperModel, sort_by, PaperModel.citation_count)
            if sort_order == "desc":
                stmt = stmt.order_by(sort_col.desc())
            else:
                stmt = stmt.order_by(sort_col.asc())

            # Pagination
            stmt = stmt.offset(offset).limit(limit)

            papers = session.execute(stmt).scalars().all()

            return list(papers), total_count
```

### 2.8 Harvest Pipeline Orchestrator

**File**: `src/paperbot/application/workflows/harvest_pipeline.py`

```python
class HarvestPipeline:
    """
    Orchestrates the paper harvest pipeline.

    Stages:
    1. Query expansion (QueryRewriter)
    2. Venue recommendation (VenueRecommender)
    3. Parallel harvesting (all harvesters)
    4. Deduplication (PaperDeduplicator)
    5. Storage (PaperStore)
    """

    def __init__(
        self,
        harvesters: List[HarvesterPort],
        paper_store: PaperStore,
        query_rewriter: QueryRewriter,
        venue_recommender: VenueRecommender,
        deduplicator: PaperDeduplicator,
    ):
        self.harvesters = harvesters
        self.paper_store = paper_store
        self.query_rewriter = query_rewriter
        self.venue_recommender = venue_recommender
        self.deduplicator = deduplicator

    async def run(
        self,
        keywords: List[str],
        *,
        venues: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        max_results_per_source: int = 50,
        sources: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> HarvestRunResult:
        """
        Run the full harvest pipeline.

        Args:
            keywords: Search keywords
            venues: Venue filter (optional, will recommend if not provided)
            year_from: Publication year lower bound
            year_to: Publication year upper bound
            max_results_per_source: Max papers per source
            sources: Which sources to use (default: all)
            progress_callback: Optional callback for progress updates

        Returns:
            HarvestRunResult with all papers and statistics
        """
        run_id = f"harvest-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
        started_at = datetime.now(timezone.utc)

        def emit(phase: str, message: str):
            if progress_callback:
                progress_callback(phase, message)

        # Stage 1: Query expansion
        emit("Expanding", "Expanding keywords...")
        expanded_queries = []
        for kw in keywords:
            expanded_queries.extend(self.query_rewriter.rewrite(kw))
        combined_query = " ".join(expanded_queries)

        # Stage 2: Venue recommendation
        if not venues:
            emit("Recommending", "Recommending venues...")
            venues = self.venue_recommender.recommend(keywords)

        # Stage 3: Parallel harvesting
        emit("Harvesting", "Fetching from sources...")

        selected_harvesters = self.harvesters
        if sources:
            source_set = {HarvestSource(s) for s in sources}
            selected_harvesters = [h for h in self.harvesters if h.source in source_set]

        # Run all harvesters in parallel
        tasks = [
            h.search(
                combined_query,
                max_results=max_results_per_source,
                year_from=year_from,
                year_to=year_to,
                venues=venues,
            )
            for h in selected_harvesters
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        source_results: Dict[HarvestSource, HarvestResult] = {}
        all_papers: List[HarvestedPaper] = []

        for harvester, result in zip(selected_harvesters, results):
            if isinstance(result, Exception):
                source_results[harvester.source] = HarvestResult(
                    source=harvester.source,
                    papers=[],
                    total_found=0,
                    error=str(result),
                )
            else:
                source_results[harvester.source] = result
                all_papers.extend(result.papers)
                emit("Harvesting", f"Found {result.total_found} from {harvester.source.value}")

        papers_found = len(all_papers)

        # Stage 4: Deduplication
        emit("Deduplicating", "Removing duplicates...")
        unique_papers, duplicates_count = self.deduplicator.deduplicate(all_papers)

        # Stage 5: Storage
        emit("Storing", "Saving to database...")
        new_count, updated_count = await self.paper_store.upsert_papers_batch(unique_papers)

        # Determine final status
        has_errors = any(r.error for r in source_results.values())
        has_results = any(r.papers for r in source_results.values())

        if has_errors and not has_results:
            status = "failed"
        elif has_errors:
            status = "partial"
        else:
            status = "success"

        return HarvestRunResult(
            run_id=run_id,
            status=status,
            papers_found=papers_found,
            papers_new=new_count,
            papers_deduplicated=duplicates_count,
            source_results=source_results,
            started_at=started_at,
            ended_at=datetime.now(timezone.utc),
        )
```

### 2.9 API Endpoints

**File**: `src/paperbot/api/routes/harvest.py`

```python
router = APIRouter(prefix="/api", tags=["harvest"])


class HarvestRequest(BaseModel):
    keywords: List[str]
    venues: Optional[List[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_results_per_source: int = Field(default=50, ge=1, le=200)
    sources: Optional[List[str]] = None


class PaperSearchRequest(BaseModel):
    query: Optional[str] = None
    keywords: Optional[List[str]] = None
    venues: Optional[List[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    min_citations: Optional[int] = None
    sources: Optional[List[str]] = None
    sort_by: str = Field(default="citation_count")
    sort_order: str = Field(default="desc")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


@router.post("/harvest")
async def harvest_papers(request: HarvestRequest):
    """
    Start paper harvesting pipeline.

    Returns SSE stream with progress updates and final result.
    """
    async def generate():
        pipeline = get_harvest_pipeline()  # From DI container

        async def on_progress(phase: str, message: str):
            yield sse_event("progress", {"phase": phase, "message": message})

        result = await pipeline.run(
            keywords=request.keywords,
            venues=request.venues,
            year_from=request.year_from,
            year_to=request.year_to,
            max_results_per_source=request.max_results_per_source,
            sources=request.sources,
            progress_callback=on_progress,
        )

        yield sse_event("result", {
            "run_id": result.run_id,
            "status": result.status,
            "papers_found": result.papers_found,
            "papers_new": result.papers_new,
            "papers_deduplicated": result.papers_deduplicated,
            "sources": {
                source.value: {
                    "papers": len(r.papers),
                    "error": r.error,
                }
                for source, r in result.source_results.items()
            },
        })
        yield sse_event("done", {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@router.post("/papers/search")
async def search_papers(request: PaperSearchRequest):
    """
    Search harvested papers with filters.
    """
    store = get_paper_store()  # From DI container

    papers, total = await store.search_papers(
        query=request.query,
        venues=request.venues,
        year_from=request.year_from,
        year_to=request.year_to,
        min_citations=request.min_citations,
        sources=request.sources,
        sort_by=request.sort_by,
        sort_order=request.sort_order,
        limit=request.limit,
        offset=request.offset,
    )

    return {
        "papers": [paper_to_dict(p) for p in papers],
        "total": total,
        "limit": request.limit,
        "offset": request.offset,
    }
```

### 2.10 Papers Library Integration

The **Papers Library** (web UI at `/papers`) displays the user's personal paper collection. When a user clicks "Save" on a paper from search results or recommendations, that paper should appear in their Papers Library.

#### 2.10.1 Data Flow: Save → Papers Library

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Save Action → Papers Library Flow                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Research Page / Recommendations                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │  Paper: "Attention Is All You Need"                             │    │  │
│  │  │  [Like]  [Save]  [Dislike]                                      │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────┬──────────────────────────────────────┘  │
│                                      │ User clicks "Save"                       │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  POST /api/research/feedback                                             │  │
│  │  {                                                                       │  │
│  │    "user_id": "user123",                                                 │  │
│  │    "track_id": 1,                                                        │  │
│  │    "paper_id": 42,              ← papers.id from paper_store             │  │
│  │    "action": "save"                                                      │  │
│  │  }                                                                       │  │
│  └───────────────────────────────────┬──────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  paper_feedback table (existing in research_store)                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │  id: 1                                                          │    │  │
│  │  │  user_id: "user123"                                             │    │  │
│  │  │  track_id: 1                                                    │    │  │
│  │  │  paper_id: "42"               ← Reference to papers.id          │    │  │
│  │  │  action: "save"                                                 │    │  │
│  │  │  ts: 2026-02-06T10:30:00Z                                       │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────┬──────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  GET /api/papers/library                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │  SELECT p.*, pf.action, pf.ts AS saved_at                       │    │  │
│  │  │  FROM papers p                                                  │    │  │
│  │  │  JOIN paper_feedback pf ON p.id = CAST(pf.paper_id AS INTEGER)  │    │  │
│  │  │  WHERE pf.user_id = ? AND pf.action = 'save'                    │    │  │
│  │  │  ORDER BY pf.ts DESC                                            │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────┬──────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Papers Library Page (/papers)                                           │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │  📄 Attention Is All You Need    [Transformer] [NLP]            │    │  │
│  │  │     NeurIPS 2017 · Vaswani et al. · 100k+ citations             │    │  │
│  │  │     Saved: Feb 6, 2026                         [Analyze] [Remove]│    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 2.10.2 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Use `paper_feedback.paper_id` to reference `papers.id`** | Links user actions to the local paper pool |
| **Papers Library = papers WHERE action='save'** | Simple query, no new table needed |
| **Store `papers.id` (integer) not external IDs** | Consistent internal reference, supports papers from any source |
| **Keep track_id in feedback** | Papers can be saved in context of a research track |

#### 2.10.3 New API Endpoint: GET /api/papers/library

**File**: `src/paperbot/api/routes/harvest.py` (addition)

```python
class PaperLibraryRequest(BaseModel):
    user_id: str
    track_id: Optional[int] = None  # Filter by track, or all if None
    include_actions: List[str] = Field(default=["save"])  # "save", "like", "cite"
    sort_by: str = Field(default="saved_at")  # saved_at, title, citation_count
    sort_order: str = Field(default="desc")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


@router.get("/papers/library")
async def get_user_library(
    user_id: str,
    track_id: Optional[int] = None,
    sort_by: str = "saved_at",
    limit: int = 50,
    offset: int = 0,
):
    """
    Get user's saved papers (Papers Library).

    Joins paper_feedback (action='save') with papers table to return
    full paper metadata for the user's personal collection.
    """
    store = get_paper_store()

    papers, total = await store.get_user_library(
        user_id=user_id,
        track_id=track_id,
        actions=["save"],
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )

    return {
        "papers": [
            {
                **paper_to_dict(p.paper),
                "saved_at": p.saved_at.isoformat() if p.saved_at else None,
                "track_id": p.track_id,
                "action": p.action,
            }
            for p in papers
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/papers/library/{paper_id}")
async def remove_from_library(paper_id: int, user_id: str):
    """
    Remove a paper from user's library (soft-delete the 'save' feedback).
    """
    store = get_paper_store()
    success = await store.remove_from_library(user_id=user_id, paper_id=paper_id)
    return {"success": success}
```

#### 2.10.4 PaperStore Addition: get_user_library()

**File**: `src/paperbot/infrastructure/stores/paper_store.py` (addition)

```python
@dataclass
class LibraryPaper:
    """Paper with library metadata."""
    paper: PaperModel
    saved_at: datetime
    track_id: Optional[int]
    action: str


class PaperStore:
    # ... existing methods ...

    async def get_user_library(
        self,
        user_id: str,
        *,
        track_id: Optional[int] = None,
        actions: List[str] = ["save"],
        sort_by: str = "saved_at",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[LibraryPaper], int]:
        """
        Get papers in user's library (saved papers).

        Joins papers table with paper_feedback where action in actions.
        """
        with self.session_provider() as session:
            # Build query joining papers with paper_feedback
            stmt = (
                select(PaperModel, PaperFeedbackModel)
                .join(
                    PaperFeedbackModel,
                    PaperModel.id == cast(PaperFeedbackModel.paper_id, Integer)
                )
                .where(
                    PaperFeedbackModel.user_id == user_id,
                    PaperFeedbackModel.action.in_(actions),
                    PaperModel.deleted_at.is_(None),
                )
            )

            if track_id is not None:
                stmt = stmt.where(PaperFeedbackModel.track_id == track_id)

            # Count total
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = session.execute(count_stmt).scalar() or 0

            # Sort
            if sort_by == "saved_at":
                stmt = stmt.order_by(PaperFeedbackModel.ts.desc())
            elif sort_by == "title":
                stmt = stmt.order_by(PaperModel.title.asc())
            elif sort_by == "citation_count":
                stmt = stmt.order_by(PaperModel.citation_count.desc())
            else:
                stmt = stmt.order_by(PaperFeedbackModel.ts.desc())

            # Pagination
            stmt = stmt.offset(offset).limit(limit)

            results = session.execute(stmt).all()

            return [
                LibraryPaper(
                    paper=row[0],
                    saved_at=row[1].ts,
                    track_id=row[1].track_id,
                    action=row[1].action,
                )
                for row in results
            ], total

    async def remove_from_library(
        self,
        user_id: str,
        paper_id: int,
    ) -> bool:
        """Remove paper from user's library by deleting 'save' feedback."""
        with self.session_provider() as session:
            stmt = (
                PaperFeedbackModel.__table__.delete()
                .where(
                    PaperFeedbackModel.user_id == user_id,
                    PaperFeedbackModel.paper_id == str(paper_id),
                    PaperFeedbackModel.action == "save",
                )
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0
```

#### 2.10.5 Frontend Update: Connect Papers Library to API

**File**: `web/src/lib/api.ts` (update)

```typescript
// Replace mock fetchPapers with real API call
export async function fetchPapers(userId: string): Promise<Paper[]> {
    const res = await fetch(`${API_BASE}/api/papers/library?user_id=${userId}`);
    if (!res.ok) {
        throw new Error('Failed to fetch papers library');
    }
    const data = await res.json();
    return data.papers.map((p: any) => ({
        id: p.id.toString(),
        title: p.title,
        venue: p.venue || 'Unknown',
        authors: p.authors?.join(', ') || 'Unknown',
        citations: p.citation_count?.toString() || '0',
        status: p.status || 'Saved',  // Could track analysis status separately
        tags: p.keywords || p.fields_of_study || [],
        savedAt: p.saved_at,
    }));
}
```

#### 2.10.6 Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     Papers Library Data Relationships                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────┐         ┌─────────────────────┐                       │
│  │    papers (v1 NEW)  │         │   paper_feedback    │                       │
│  │                     │         │     (existing)      │                       │
│  ├─────────────────────┤         ├─────────────────────┤                       │
│  │ id (PK)             │◄────────│ paper_id (FK)       │                       │
│  │ doi                 │         │ user_id             │                       │
│  │ arxiv_id            │         │ track_id (FK)       │──────┐                │
│  │ title               │         │ action              │      │                │
│  │ abstract            │         │ ts                  │      │                │
│  │ authors_json        │         │ weight              │      │                │
│  │ year                │         └─────────────────────┘      │                │
│  │ venue               │                                      │                │
│  │ citation_count      │         ┌─────────────────────┐      │                │
│  │ ...                 │         │  research_tracks    │      │                │
│  └─────────────────────┘         │    (existing)       │◄─────┘                │
│                                  ├─────────────────────┤                       │
│                                  │ id (PK)             │                       │
│                                  │ user_id             │                       │
│                                  │ name                │                       │
│                                  │ keywords_json       │                       │
│                                  │ venues_json         │                       │
│                                  └─────────────────────┘                       │
│                                                                                 │
│  Query: Papers Library for User                                                 │
│  ───────────────────────────────                                                │
│  SELECT p.*, pf.ts AS saved_at, pf.track_id                                     │
│  FROM papers p                                                                  │
│  JOIN paper_feedback pf ON p.id = CAST(pf.paper_id AS INTEGER)                  │
│  WHERE pf.user_id = :user_id AND pf.action = 'save'                             │
│  ORDER BY pf.ts DESC                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Principles

### 3.1 Core Design Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Open Sources First** | Prioritize free, no-auth APIs | arXiv, S2, OpenAlex (no IEEE/ACM) |
| **Metadata Only** | No PDF download or parsing | Store URLs only, defer PDF to v2 |
| **Graceful Degradation** | Partial results if some sources fail | Continue pipeline, report errors |
| **Idempotent Upserts** | Same paper → same record | Multi-strategy deduplication |
| **Audit Trail** | Track all harvest runs | harvest_runs table with timing/counts |

### 3.2 Deduplication Strategy (Priority Order)

```
┌─────────────────────────────────────────────────────────────┐
│                  Paper Arrives from Source                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. DOI Match? (most reliable)                              │
│     doi.lower() in doi_index → DUPLICATE                    │
└─────────────────────────────────────────────────────────────┘
                              │ No
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. arXiv ID Match?                                         │
│     arxiv_id.lower() in arxiv_index → DUPLICATE             │
└─────────────────────────────────────────────────────────────┘
                              │ No
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Semantic Scholar ID Match?                              │
│     s2_id.lower() in s2_index → DUPLICATE                   │
└─────────────────────────────────────────────────────────────┘
                              │ No
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. OpenAlex ID Match?                                      │
│     openalex_id.lower() in openalex_index → DUPLICATE       │
└─────────────────────────────────────────────────────────────┘
                              │ No
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Title Hash Match? (fallback)                            │
│     sha256(normalize(title)) in title_hash_index → DUPLICATE│
└─────────────────────────────────────────────────────────────┘
                              │ No
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    NEW PAPER → Insert                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Component Responsibilities

| Component | Responsibility | Should NOT Do |
|-----------|----------------|---------------|
| **Harvester** | Fetch papers from source, normalize to HarvestedPaper | Deduplicate, store, apply business rules |
| **QueryRewriter** | Expand/transform keywords | Fetch papers, access database |
| **VenueRecommender** | Map keywords to venues | Fetch papers, access database |
| **Deduplicator** | Find duplicates in memory, merge metadata | Access database, make API calls |
| **PaperStore** | Persist papers, DB-level dedup, search | Fetch from external APIs |
| **HarvestPipeline** | Orchestrate all stages | Implement stage logic |

---

## 4. Technology Selection Rationale

### 4.1 Third Source: OpenAlex

| Criterion | OpenAlex | CrossRef | PubMed |
|-----------|----------|----------|--------|
| Coverage | 240M+ works | 140M+ | 35M+ (biomedical only) |
| API Cost | Free | Free | Free |
| Rate Limit | 10 req/s | 50 req/s | 3 req/s |
| Auth Required | No | No (polite pool) | No |
| DOI Support | Yes | Yes | Limited |
| CS Coverage | Excellent | Good | Poor |

**Decision**: OpenAlex (best coverage, generous rate limit, no auth)

### 4.2 Storage: SQLite

| Criterion | SQLite | PostgreSQL |
|-----------|--------|------------|
| Consistency with stack | Same DB | New infra |
| Deployment simplicity | Single file | Server required |
| Full-text search | FTS5 (v2) | pg_trgm |
| Scale limit | ~10M rows | Unlimited |

**Decision**: SQLite (consistent with existing stack, sufficient for v1)

### 4.3 Search: LIKE Queries (v1)

| Criterion | LIKE | FTS5 | Elasticsearch |
|-----------|------|------|---------------|
| Setup complexity | None | Index creation | New infra |
| Query speed | Slow | Fast | Fastest |
| Relevance ranking | None | BM25 | Full control |

**Decision**: LIKE queries for v1 (simple, sufficient for TopN), defer FTS5 to v2

---

## 5. Best Practices and References

### 5.1 API Documentation

| Source | API Docs | Key Endpoints |
|--------|----------|---------------|
| **arXiv** | https://arxiv.org/help/api | `export.arxiv.org/api/query` |
| **Semantic Scholar** | https://api.semanticscholar.org/api-docs/ | `/graph/v1/paper/search` |
| **OpenAlex** | https://docs.openalex.org/ | `/works?search=...` |

### 5.2 Open Source References

| Project | Relevance |
|---------|-----------|
| **semanticscholar** (PyPI) | Python client for S2 API |
| **arxiv-sanity-lite** | Query handling patterns |
| **paperetl** | Metadata extraction + dedup patterns |

### 5.3 Internal Documents

| Document | Content |
|----------|---------|
| `config/top_venues.yaml` | Venue tier rankings |
| `src/paperbot/infrastructure/connectors/arxiv_connector.py` | Existing arXiv XML parsing |
| `src/paperbot/infrastructure/api_clients/semantic_scholar.py` | Existing S2 client |

---

## 6. Risks and Mitigations

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API rate limiting | High | Medium | Respect rate limits, exponential backoff |
| Source API changes | Low | High | Version harvesters, monitor for changes |
| Dedup misses duplicates | Medium | Low | Multiple strategies, title hash fallback |
| Large result sets slow DB | Medium | Medium | Pagination, indexes, defer FTS to v2 |

### 6.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenAlex API unreliable | Low | Medium | Continue with other sources |
| Stale venue mappings | Medium | Low | Config-driven, easy to update |
| Disk space from paper storage | Low | Low | Metadata only, no PDFs |

---

## 7. Workload Estimation

### 7.1 Task Breakdown

| Task | Effort | Dependencies |
|------|--------|--------------|
| **Infrastructure** | | |
| Domain models (`domain/harvest.py`) | 2h | None |
| Database migration (papers, harvest_runs) | 2h | Models |
| PaperStore implementation | 4h | Migration |
| **Harvesters** | | |
| HarvesterPort interface | 1h | Models |
| ArxivHarvester | 3h | Interface |
| SemanticScholarHarvester | 2h | Interface |
| OpenAlexHarvester | 4h | Interface |
| **Services** | | |
| VenueRecommender | 2h | Config |
| QueryRewriter | 2h | None |
| PaperDeduplicator | 3h | Models |
| **Pipeline & API** | | |
| HarvestPipeline orchestrator | 4h | All above |
| API routes (harvest, search) | 3h | Pipeline, Store |
| **Papers Library Integration** | | |
| PaperStore.get_user_library() | 2h | PaperStore |
| API route (/api/papers/library) | 1h | PaperStore |
| Frontend update (web/src/lib/api.ts) | 1h | API |
| **Testing** | | |
| Unit tests (dedup, rewriter, recommender) | 3h | Services |
| Integration tests (harvesters, store) | 3h | Harvesters |
| E2E test (full pipeline) | 2h | API |

### 7.2 Summary

| Category | Hours |
|----------|-------|
| Infrastructure | 8h |
| Harvesters | 10h |
| Services | 7h |
| Pipeline & API | 7h |
| Papers Library Integration | 4h |
| Testing | 8h |
| **Total** | **44h (~6-7 days)** |

### 7.3 Suggested Timeline

```
Day 1:    Infrastructure
          - Domain models
          - Database migration
          - PaperStore (partial)

Day 2:    Infrastructure + Harvesters
          - PaperStore completion
          - HarvesterPort interface
          - ArxivHarvester

Day 3:    Harvesters
          - SemanticScholarHarvester
          - OpenAlexHarvester
          - Unit tests for harvesters

Day 4:    Services
          - VenueRecommender
          - QueryRewriter
          - PaperDeduplicator
          - Unit tests

Day 5:    Pipeline & API
          - HarvestPipeline orchestrator
          - API routes
          - Integration tests

Day 6:    Testing & Polish
          - E2E tests
          - Error handling improvements
          - Documentation

Day 7:    Buffer / Review
          - Code review
          - Bug fixes
          - Update docs
```

---

## 8. Deliverables Checklist

### 8.1 Domain Models
- [ ] `src/paperbot/domain/harvest.py` - HarvestedPaper, HarvestSource, HarvestResult

### 8.2 Database
- [ ] `alembic/versions/0003_paper_harvest_tables.py` - Migration
- [ ] `src/paperbot/infrastructure/stores/models.py` - PaperModel, HarvestRunModel

### 8.3 Harvesters
- [ ] `src/paperbot/application/ports/harvester_port.py` - HarvesterPort interface
- [ ] `src/paperbot/infrastructure/harvesters/__init__.py`
- [ ] `src/paperbot/infrastructure/harvesters/arxiv_harvester.py`
- [ ] `src/paperbot/infrastructure/harvesters/semantic_scholar_harvester.py`
- [ ] `src/paperbot/infrastructure/harvesters/openalex_harvester.py`

### 8.4 Services
- [ ] `src/paperbot/application/services/venue_recommender.py`
- [ ] `src/paperbot/application/services/query_rewriter.py`
- [ ] `src/paperbot/application/services/paper_deduplicator.py`

### 8.5 Pipeline & Storage
- [ ] `src/paperbot/application/workflows/harvest_pipeline.py`
- [ ] `src/paperbot/infrastructure/stores/paper_store.py`

### 8.6 API
- [ ] `src/paperbot/api/routes/harvest.py` - POST /api/harvest, POST /api/papers/search, GET /api/papers/library
- [ ] `src/paperbot/api/main.py` - Register router

### 8.7 Papers Library Integration
- [ ] `src/paperbot/infrastructure/stores/paper_store.py` - Add `get_user_library()`, `remove_from_library()` methods
- [ ] `web/src/lib/api.ts` - Update `fetchPapers()` to call real API
- [ ] `web/src/app/papers/page.tsx` - Connect to `/api/papers/library` endpoint

### 8.8 Tests
- [ ] `tests/unit/test_paper_deduplicator.py`
- [ ] `tests/unit/test_query_rewriter.py`
- [ ] `tests/unit/test_venue_recommender.py`
- [ ] `tests/integration/test_paper_store.py`
- [ ] `tests/integration/test_harvesters.py`
- [ ] `tests/e2e/test_harvest_api.py`
- [ ] `tests/e2e/test_papers_library.py` - Papers Library integration test

### 8.9 Documentation
- [ ] `docs/paper_harvest_v1.md` - User guide

---

## 9. Open Questions

The following questions require user input before implementation:

1. **Venue configuration format**: Should VenueRecommender use existing `config/top_venues.yaml` or a separate config file with keyword→venue mappings?

2. **Rate limiting strategy**: Should we implement global rate limiting across all harvesters, or per-harvester limits?

3. **Search scope**: Should `/api/papers/search` search only harvested papers, or also query external APIs in real-time?

4. **Frontend integration**: Should harvest progress be shown on a new page, or integrated into the existing Research page?

5. **Retention policy**: Should old harvest_runs records be automatically cleaned up after N days?

---

## Appendix A: Existing Implementation Summary

### A.1 Existing Connectors

| Connector | Status | Reusable? |
|-----------|--------|-----------|
| ArxivConnector | XML parsing only | Use for response parsing |
| SemanticScholarClient | Async API wrapper | Wrap with harvester |
| RedditConnector | RSS parsing | Not relevant |

### A.2 Existing Infrastructure

| Component | Status |
|-----------|--------|
| SessionProvider | Ready |
| SQLAlchemy Base | Ready |
| Alembic migrations | Ready |
| FastAPI streaming | Ready |
| EventLogPort | Ready |

### A.3 API Patterns to Follow

| Pattern | Example File |
|---------|--------------|
| SSE streaming | `src/paperbot/api/routes/track.py` |
| Pydantic models | `src/paperbot/api/routes/research.py` |
| Store initialization | `src/paperbot/infrastructure/stores/research_store.py` |
