from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from paperbot.context_engine import ContextEngine, ContextEngineConfig
from paperbot.context_engine.track_router import TrackRouter
from paperbot.infrastructure.api_clients.semantic_scholar import SemanticScholarClient
from paperbot.infrastructure.stores.memory_store import SqlAlchemyMemoryStore
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore
from paperbot.memory.eval.collector import MemoryMetricCollector
from paperbot.memory.extractor import extract_memories
from paperbot.memory.schema import MemoryCandidate, NormalizedMessage
from paperbot.utils.logging_config import LogFiles, Logger, set_trace_id

router = APIRouter()

_research_store = SqlAlchemyResearchStore()
_memory_store = SqlAlchemyMemoryStore()
_track_router = TrackRouter(research_store=_research_store, memory_store=_memory_store)
_metric_collector: Optional[MemoryMetricCollector] = None
_paper_store: Optional["PaperStore"] = None


def _get_metric_collector() -> MemoryMetricCollector:
    """Lazy initialization of metric collector."""
    global _metric_collector
    if _metric_collector is None:
        _metric_collector = MemoryMetricCollector()
    return _metric_collector


def _get_paper_store() -> "PaperStore":
    """Lazy initialization of paper store."""
    from paperbot.infrastructure.stores.paper_store import PaperStore

    global _paper_store
    if _paper_store is None:
        _paper_store = PaperStore()
    return _paper_store


def _schedule_embedding_precompute(
    background_tasks: Optional[BackgroundTasks],
    *,
    user_id: str,
    track_ids: List[int],
) -> None:
    if background_tasks is None:
        return

    ids = sorted({int(x) for x in track_ids if int(x) > 0})
    if not ids:
        return

    def _run() -> None:
        try:
            _track_router.precompute_track_embeddings(user_id=user_id, track_ids=ids)
        except Exception:
            return

    background_tasks.add_task(_run)


class TrackCreateRequest(BaseModel):
    user_id: str = "default"
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    keywords: List[str] = []
    venues: List[str] = []
    methods: List[str] = []
    activate: bool = True


class TrackUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    venues: Optional[List[str]] = None
    methods: Optional[List[str]] = None


class TrackResponse(BaseModel):
    track: Dict[str, Any]


@router.post("/research/tracks", response_model=TrackResponse)
def create_track(req: TrackCreateRequest, background_tasks: BackgroundTasks):
    track = _research_store.create_track(
        user_id=req.user_id,
        name=req.name,
        description=req.description,
        keywords=req.keywords,
        venues=req.venues,
        methods=req.methods,
        activate=req.activate,
    )
    _schedule_embedding_precompute(
        background_tasks, user_id=req.user_id, track_ids=[int(track.get("id") or 0)]
    )
    return TrackResponse(track=track)


class TrackListResponse(BaseModel):
    user_id: str
    tracks: List[Dict[str, Any]]


@router.get("/research/tracks", response_model=TrackListResponse)
def list_tracks(
    user_id: str = "default",
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    tracks = _research_store.list_tracks(
        user_id=user_id, include_archived=include_archived, limit=limit
    )
    return TrackListResponse(user_id=user_id, tracks=tracks)


@router.get("/research/tracks/active", response_model=TrackResponse)
def get_active_track(user_id: str = "default"):
    track = _research_store.get_active_track(user_id=user_id)
    if not track:
        raise HTTPException(status_code=404, detail="No active track for user")
    return TrackResponse(track=track)


@router.patch("/research/tracks/{track_id}", response_model=TrackResponse)
def update_track(
    track_id: int,
    req: TrackUpdateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = "default",
):
    update_data = req.model_dump(exclude_unset=True, exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        track = _research_store.update_track(user_id=user_id, track_id=track_id, **update_data)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Track name already exists") from None
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    _schedule_embedding_precompute(background_tasks, user_id=user_id, track_ids=[track_id])
    return TrackResponse(track=track)


@router.post("/research/tracks/{track_id}/activate", response_model=TrackResponse)
def activate_track(track_id: int, background_tasks: BackgroundTasks, user_id: str = "default"):
    track = _research_store.activate_track(user_id=user_id, track_id=track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    _schedule_embedding_precompute(background_tasks, user_id=user_id, track_ids=[track_id])
    return TrackResponse(track=track)


class TaskCreateRequest(BaseModel):
    user_id: str = "default"
    title: str = Field(..., min_length=1)
    status: str = "todo"
    priority: int = 0
    paper_id: Optional[str] = None
    paper_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    task: Dict[str, Any]


@router.post("/research/tracks/{track_id}/tasks", response_model=TaskResponse)
def add_task(track_id: int, req: TaskCreateRequest, background_tasks: BackgroundTasks):
    task = _research_store.add_task(
        user_id=req.user_id,
        track_id=track_id,
        title=req.title,
        status=req.status,
        priority=req.priority,
        paper_id=req.paper_id,
        paper_url=req.paper_url,
        metadata=req.metadata,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Track not found")
    _schedule_embedding_precompute(background_tasks, user_id=req.user_id, track_ids=[track_id])
    return TaskResponse(task=task)


class TaskListResponse(BaseModel):
    user_id: str
    track_id: int
    tasks: List[Dict[str, Any]]


@router.get("/research/tracks/{track_id}/tasks", response_model=TaskListResponse)
def list_tasks(
    track_id: int,
    user_id: str = "default",
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    tasks = _research_store.list_tasks(
        user_id=user_id, track_id=track_id, status=status, limit=limit
    )
    return TaskListResponse(user_id=user_id, track_id=track_id, tasks=tasks)


class MemoryItemCreateRequest(BaseModel):
    user_id: str = "default"
    scope_type: str = "track"  # global/track
    scope_id: Optional[str] = None
    kind: str = Field("note", min_length=1, max_length=32)
    content: str = Field(..., min_length=1)
    tags: List[str] = []
    status: str = "approved"
    confidence: float = 0.8
    evidence: Dict[str, Any] = {}


class MemoryItemResponse(BaseModel):
    item: Dict[str, Any]


def _resolve_track_scope_id(
    user_id: str, scope_type: str, scope_id: Optional[str]
) -> Optional[str]:
    if scope_type != "track":
        return scope_id
    if scope_id:
        return scope_id
    active = _research_store.get_active_track(user_id=user_id)
    if not active:
        return None
    return str(active["id"])


@router.post("/research/memory/items", response_model=MemoryItemResponse)
def create_memory_item(req: MemoryItemCreateRequest, background_tasks: BackgroundTasks):
    scope_type = (req.scope_type or "global").strip() or "global"
    scope_id = _resolve_track_scope_id(req.user_id, scope_type, req.scope_id)
    if scope_type == "track" and not scope_id:
        raise HTTPException(status_code=400, detail="scope_id missing and no active track")

    cand = MemoryCandidate(
        kind=req.kind,  # type: ignore[arg-type]
        content=req.content,
        confidence=float(req.confidence),
        tags=req.tags,
        evidence=req.evidence,
        scope_type=scope_type,
        scope_id=scope_id,
        status=req.status,
    )
    created, _, rows = _memory_store.add_memories(user_id=req.user_id, memories=[cand])
    if created <= 0 or not rows:
        raise HTTPException(
            status_code=409, detail="Duplicate memory item (same scope/kind/content)"
        )
    if scope_type == "track":
        _schedule_embedding_precompute(
            background_tasks, user_id=req.user_id, track_ids=[int(scope_id or 0)]
        )
    return MemoryItemResponse(item=SqlAlchemyMemoryStore._row_to_dict(rows[0]))


class MemoryItemListResponse(BaseModel):
    user_id: str
    items: List[Dict[str, Any]]


@router.get("/research/memory/items", response_model=MemoryItemListResponse)
def list_memory_items(
    user_id: str = "default",
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    include_pending: bool = False,
    limit: int = Query(100, ge=1, le=500),
):
    items = _memory_store.list_memories(
        user_id=user_id,
        limit=limit,
        kind=kind,
        scope_type=scope_type,
        scope_id=scope_id,
        include_pending=include_pending,
        status=status,
    )
    return MemoryItemListResponse(user_id=user_id, items=items)


@router.get("/research/memory/inbox", response_model=MemoryItemListResponse)
def list_memory_inbox(
    user_id: str = "default",
    track_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
):
    if track_id is None:
        active = _research_store.get_active_track(user_id=user_id)
        if not active:
            raise HTTPException(status_code=404, detail="No active track for user")
        track_id = int(active["id"])

    items = _memory_store.list_memories(
        user_id=user_id,
        limit=limit,
        scope_type="track",
        scope_id=str(track_id),
        status="pending",
        include_deleted=False,
        include_pending=True,
    )
    return MemoryItemListResponse(user_id=user_id, items=items)


class MemorySuggestRequest(BaseModel):
    user_id: str = "default"
    text: str = Field(..., min_length=1)
    scope_type: str = "track"
    scope_id: Optional[str] = None
    use_llm: bool = False
    redact: bool = True
    language_hint: Optional[str] = None


class MemorySuggestResponse(BaseModel):
    user_id: str
    created: int
    skipped: int
    candidates: List[Dict[str, Any]]


@router.post("/research/memory/suggest", response_model=MemorySuggestResponse)
def suggest_memories(req: MemorySuggestRequest, background_tasks: BackgroundTasks):
    scope_type = (req.scope_type or "global").strip() or "global"
    scope_id = _resolve_track_scope_id(req.user_id, scope_type, req.scope_id)
    if scope_type == "track" and not scope_id:
        raise HTTPException(status_code=400, detail="scope_id missing and no active track")

    msgs = [NormalizedMessage(role="user", content=req.text)]
    extracted = extract_memories(
        msgs, use_llm=req.use_llm, redact=req.redact, language_hint=req.language_hint
    )
    pending = [
        MemoryCandidate(
            kind=m.kind,
            content=m.content,
            confidence=m.confidence,
            tags=m.tags,
            evidence=m.evidence,
            scope_type=scope_type,
            scope_id=scope_id,
            status="pending",
        )
        for m in extracted
    ]
    created, skipped, rows = _memory_store.add_memories(user_id=req.user_id, memories=pending)
    if scope_type == "track":
        _schedule_embedding_precompute(
            background_tasks, user_id=req.user_id, track_ids=[int(scope_id or 0)]
        )
    return MemorySuggestResponse(
        user_id=req.user_id,
        created=created,
        skipped=skipped,
        candidates=[SqlAlchemyMemoryStore._row_to_dict(r) for r in rows],
    )


class MemoryModerateRequest(BaseModel):
    user_id: str = "default"
    status: str = Field(..., min_length=1)  # approved/rejected/pending/superseded
    content: Optional[str] = None
    kind: Optional[str] = None
    tags: Optional[List[str]] = None
    scope_type: Optional[str] = None
    scope_id: Optional[str] = None


@router.post("/research/memory/items/{item_id}/moderate", response_model=MemoryItemResponse)
def moderate_memory_item(item_id: int, req: MemoryModerateRequest):
    updated = _memory_store.update_item(
        user_id=req.user_id,
        item_id=item_id,
        status=req.status,
        content=req.content,
        kind=req.kind,
        tags=req.tags,
        scope_type=req.scope_type,
        scope_id=req.scope_id,
        actor_id="user",
    )
    if not updated:
        raise HTTPException(status_code=409, detail="Memory item not found or update conflict")
    return MemoryItemResponse(item=updated)


class BulkModerateRequest(BaseModel):
    user_id: str = "default"
    item_ids: List[int] = Field(default_factory=list)
    status: str = Field(..., min_length=1)


class BulkModerateResponse(BaseModel):
    user_id: str
    updated: List[Dict[str, Any]]


@router.post("/research/memory/bulk_moderate", response_model=BulkModerateResponse)
def bulk_moderate(req: BulkModerateRequest, background_tasks: BackgroundTasks):
    # Get items before update to check their confidence for P0 metrics
    items_before = _memory_store.get_items_by_ids(user_id=req.user_id, item_ids=req.item_ids)

    updated = _memory_store.bulk_update_items(
        user_id=req.user_id,
        item_ids=req.item_ids,
        status=req.status,
        actor_id="user",
    )
    affected_tracks = [
        int(i.get("scope_id") or 0)
        for i in updated
        if i.get("scope_type") == "track" and i.get("scope_id")
    ]
    _schedule_embedding_precompute(background_tasks, user_id=req.user_id, track_ids=affected_tracks)

    # P0 Hook: Record false positive rate when user rejects high-confidence items
    # A rejection of an auto-approved (confidence >= 0.60) item is a false positive
    if req.status == "rejected" and items_before:
        high_confidence_rejected = sum(
            1
            for item in items_before
            if item.get("confidence", 0) >= 0.60 and item.get("status") == "approved"
        )
        if high_confidence_rejected > 0:
            collector = _get_metric_collector()
            collector.record_false_positive_rate(
                false_positive_count=high_confidence_rejected,
                total_approved_count=len(items_before),
                evaluator_id=f"user:{req.user_id}",
                detail={
                    "item_ids": req.item_ids,
                    "action": "bulk_moderate_reject",
                },
            )

    return BulkModerateResponse(user_id=req.user_id, updated=updated)


class BulkMoveRequest(BaseModel):
    user_id: str = "default"
    item_ids: List[int] = Field(default_factory=list)
    scope_type: str = Field(..., min_length=1)
    scope_id: Optional[str] = None


class BulkMoveResponse(BaseModel):
    user_id: str
    updated: List[Dict[str, Any]]


@router.post("/research/memory/bulk_move", response_model=BulkMoveResponse)
def bulk_move(req: BulkMoveRequest, background_tasks: BackgroundTasks):
    scope_type = (req.scope_type or "global").strip() or "global"
    scope_id = _resolve_track_scope_id(req.user_id, scope_type, req.scope_id)
    if scope_type == "track" and not scope_id:
        raise HTTPException(status_code=400, detail="scope_id missing and no active track")
    updated = _memory_store.bulk_update_items(
        user_id=req.user_id,
        item_ids=req.item_ids,
        scope_type=scope_type,
        scope_id=scope_id,
        actor_id="user",
    )
    affected_tracks = [
        int(i.get("scope_id") or 0)
        for i in updated
        if i.get("scope_type") == "track" and i.get("scope_id")
    ]
    _schedule_embedding_precompute(background_tasks, user_id=req.user_id, track_ids=affected_tracks)
    return BulkMoveResponse(user_id=req.user_id, updated=updated)


class MemoryFeedbackRequest(BaseModel):
    """Request to record feedback on retrieved memories."""

    user_id: str = "default"
    memory_ids: List[int] = Field(..., min_length=1, description="IDs of memories being rated")
    helpful_ids: List[int] = Field(
        default_factory=list, description="IDs of memories that were helpful"
    )
    not_helpful_ids: List[int] = Field(
        default_factory=list, description="IDs of memories that were not helpful"
    )
    context_run_id: Optional[int] = None
    query: Optional[str] = None


class MemoryFeedbackResponse(BaseModel):
    user_id: str
    total_rated: int
    helpful_count: int
    not_helpful_count: int
    hit_rate: float


@router.post("/research/memory/feedback", response_model=MemoryFeedbackResponse)
def record_memory_feedback(req: MemoryFeedbackRequest):
    """
    Record user feedback on retrieved memories.

    This endpoint allows users to indicate which memories were helpful vs not helpful
    when they were retrieved for a query. This data feeds into the P0 retrieval_hit_rate metric.

    Usage:
    - After building context, frontend shows retrieved memories
    - User marks which memories were helpful
    - Frontend calls this endpoint with the feedback
    """
    helpful_set = set(req.helpful_ids)
    not_helpful_set = set(req.not_helpful_ids)

    # Count hits (helpful) and misses (not helpful)
    hits = len(helpful_set)
    total = len(req.memory_ids)

    if total > 0:
        hit_rate = hits / total
        collector = _get_metric_collector()
        collector.record_retrieval_hit_rate(
            hits=hits,
            expected=total,
            evaluator_id=f"user:{req.user_id}",
            detail={
                "memory_ids": req.memory_ids,
                "helpful_ids": list(helpful_set),
                "not_helpful_ids": list(not_helpful_set),
                "context_run_id": req.context_run_id,
                "query": req.query,
                "action": "memory_feedback",
            },
        )
    else:
        hit_rate = 0.0

    return MemoryFeedbackResponse(
        user_id=req.user_id,
        total_rated=total,
        helpful_count=hits,
        not_helpful_count=len(not_helpful_set),
        hit_rate=hit_rate,
    )


class ClearTrackMemoryResponse(BaseModel):
    user_id: str
    track_id: int
    deleted_count: int


@router.post("/research/tracks/{track_id}/memory/clear", response_model=ClearTrackMemoryResponse)
def clear_track_memory(
    track_id: int,
    background_tasks: BackgroundTasks,
    user_id: str = "default",
    confirm: bool = Query(False),
):
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true required")
    deleted = _memory_store.soft_delete_by_scope(
        user_id=user_id,
        scope_type="track",
        scope_id=str(track_id),
        actor_id="user",
        reason="clear_track_memory",
    )
    _schedule_embedding_precompute(background_tasks, user_id=user_id, track_ids=[track_id])

    # P0 Hook: Verify deletion compliance - deleted items should not be retrievable
    if deleted > 0:
        # Try to retrieve items from the cleared scope (should return empty)
        retrieved_after_delete = _memory_store.list_memories(
            user_id=user_id,
            scope_type="track",
            scope_id=str(track_id),
            include_deleted=False,
            include_pending=True,
            limit=100,
        )
        # Also try searching
        search_results = _memory_store.search_memories(
            user_id=user_id,
            query="*",  # broad query
            scope_type="track",
            scope_id=str(track_id),
            limit=100,
        )
        retrieved_count = len(retrieved_after_delete) + len(search_results)

        collector = _get_metric_collector()
        collector.record_deletion_compliance(
            deleted_retrieved_count=retrieved_count,
            deleted_total_count=deleted,
            evaluator_id=f"user:{user_id}",
            detail={
                "track_id": track_id,
                "deleted_count": deleted,
                "retrieved_after_delete": retrieved_count,
                "action": "clear_track_memory",
            },
        )

    return ClearTrackMemoryResponse(user_id=user_id, track_id=track_id, deleted_count=deleted)


class PrecomputeEmbeddingsRequest(BaseModel):
    user_id: str = "default"
    track_ids: Optional[List[int]] = None


class PrecomputeEmbeddingsResponse(BaseModel):
    user_id: str
    result: Dict[str, int]


@router.post("/research/embeddings/precompute", response_model=PrecomputeEmbeddingsResponse)
def precompute_embeddings(req: PrecomputeEmbeddingsRequest):
    result = _track_router.precompute_track_embeddings(
        user_id=req.user_id, track_ids=req.track_ids or None
    )
    return PrecomputeEmbeddingsResponse(user_id=req.user_id, result=result)


class EvalSummaryResponse(BaseModel):
    user_id: str
    track_id: Optional[int] = None
    summary: Dict[str, Any]


@router.get("/research/evals/summary", response_model=EvalSummaryResponse)
def eval_summary(
    user_id: str = "default",
    track_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
):
    summary = _research_store.summarize_eval(user_id=user_id, track_id=track_id, days=days)
    return EvalSummaryResponse(user_id=user_id, track_id=track_id, summary=summary)


class PaperFeedbackRequest(BaseModel):
    user_id: str = "default"
    track_id: Optional[int] = None
    paper_id: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)  # like/dislike/skip/save/cite
    weight: float = 0.0
    metadata: Dict[str, Any] = {}
    context_run_id: Optional[int] = None
    context_rank: Optional[int] = None
    # Paper metadata (optional, used when saving to library)
    paper_title: Optional[str] = None
    paper_abstract: Optional[str] = None
    paper_authors: Optional[List[str]] = None
    paper_year: Optional[int] = None
    paper_venue: Optional[str] = None
    paper_citation_count: Optional[int] = None
    paper_url: Optional[str] = None
    paper_source: Optional[str] = None  # arxiv, semantic_scholar, openalex


class PaperFeedbackResponse(BaseModel):
    feedback: Dict[str, Any]
    library_paper_id: Optional[int] = None  # ID in papers table if saved


@router.post("/research/papers/feedback", response_model=PaperFeedbackResponse)
def add_paper_feedback(req: PaperFeedbackRequest):
    set_trace_id()  # Initialize trace_id for this request
    Logger.info(f"Received paper feedback request, action={req.action}", file=LogFiles.HARVEST)

    track_id = req.track_id
    if track_id is None:
        Logger.info("No track specified, getting active track", file=LogFiles.HARVEST)
        active = _research_store.get_active_track(user_id=req.user_id)
        if not active:
            Logger.error("No active track found", file=LogFiles.HARVEST)
            raise HTTPException(status_code=400, detail="track_id missing and no active track")
        track_id = int(active["id"])

    meta: Dict[str, Any] = dict(req.metadata or {})
    if req.context_run_id is not None:
        meta["context_run_id"] = int(req.context_run_id)
    if req.context_rank is not None:
        meta["context_rank"] = int(req.context_rank)

    library_paper_id: Optional[int] = None

    # If action is "save" and we have paper metadata, insert into papers table
    if req.action == "save" and req.paper_title:
        Logger.info(
            "Save action detected, inserting paper into papers table", file=LogFiles.HARVEST
        )
        try:
            from paperbot.domain.harvest import HarvestedPaper, HarvestSource

            paper_store = _get_paper_store()

            # Determine source from request or default to semantic_scholar
            source_str = (req.paper_source or "semantic_scholar").lower()
            source_map = {
                "arxiv": HarvestSource.ARXIV,
                "semantic_scholar": HarvestSource.SEMANTIC_SCHOLAR,
                "openalex": HarvestSource.OPENALEX,
            }
            source = source_map.get(source_str, HarvestSource.SEMANTIC_SCHOLAR)

            paper = HarvestedPaper(
                title=req.paper_title,
                source=source,
                abstract=req.paper_abstract or "",
                authors=req.paper_authors or [],
                semantic_scholar_id=(
                    req.paper_id if source == HarvestSource.SEMANTIC_SCHOLAR else None
                ),
                arxiv_id=req.paper_id if source == HarvestSource.ARXIV else None,
                openalex_id=req.paper_id if source == HarvestSource.OPENALEX else None,
                year=req.paper_year,
                venue=req.paper_venue,
                citation_count=req.paper_citation_count or 0,
                url=req.paper_url,
            )
            Logger.info("Calling paper store to upsert paper", file=LogFiles.HARVEST)
            new_count, _ = paper_store.upsert_papers_batch([paper])

            # Get the paper ID from database using store method
            result = paper_store.get_paper_by_source_id(source, req.paper_id)
            if result:
                library_paper_id = result.id
                # Store library_paper_id in metadata for joins, keep paper_id as external ID
                meta["library_paper_id"] = library_paper_id
                Logger.info(
                    f"Paper saved to library with id={library_paper_id}", file=LogFiles.HARVEST
                )
        except Exception as e:
            Logger.warning(f"Failed to save paper to library: {e}", file=LogFiles.HARVEST)

    Logger.info("Recording paper feedback to research store", file=LogFiles.HARVEST)
    fb = _research_store.add_paper_feedback(
        user_id=req.user_id,
        track_id=track_id,
        paper_id=req.paper_id,  # Always use external ID for consistency
        action=req.action,
        weight=req.weight,
        metadata=meta,
    )
    if not fb:
        Logger.error("Failed to record feedback - track not found", file=LogFiles.HARVEST)
        raise HTTPException(status_code=404, detail="Track not found")
    Logger.info("Paper feedback recorded successfully", file=LogFiles.HARVEST)
    return PaperFeedbackResponse(feedback=fb, library_paper_id=library_paper_id)


class PaperFeedbackListResponse(BaseModel):
    user_id: str
    track_id: int
    items: List[Dict[str, Any]]


@router.get("/research/tracks/{track_id}/papers/feedback", response_model=PaperFeedbackListResponse)
def list_paper_feedback(
    track_id: int,
    user_id: str = "default",
    action: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
):
    items = _research_store.list_paper_feedback(
        user_id=user_id, track_id=track_id, action=action, limit=limit
    )
    return PaperFeedbackListResponse(user_id=user_id, track_id=track_id, items=items)


class PaperReadingStatusRequest(BaseModel):
    user_id: str = "default"
    status: str = Field(..., min_length=1)  # unread/reading/read/archived
    mark_saved: Optional[bool] = None
    metadata: Dict[str, Any] = {}


class PaperReadingStatusResponse(BaseModel):
    status: Dict[str, Any]


class SavedPapersResponse(BaseModel):
    user_id: str
    items: List[Dict[str, Any]]


class PaperDetailResponse(BaseModel):
    detail: Dict[str, Any]


class PaperRepoListResponse(BaseModel):
    paper_id: str
    repos: List[Dict[str, Any]]


@router.post("/research/papers/{paper_id}/status", response_model=PaperReadingStatusResponse)
def update_paper_status(paper_id: str, req: PaperReadingStatusRequest):
    status = _research_store.set_paper_reading_status(
        user_id=req.user_id,
        paper_id=paper_id,
        status=req.status,
        metadata=req.metadata,
        mark_saved=req.mark_saved,
    )
    if not status:
        raise HTTPException(status_code=404, detail="Paper not found in registry")
    return PaperReadingStatusResponse(status=status)


@router.get("/research/papers/saved", response_model=SavedPapersResponse)
def list_saved_papers(
    user_id: str = "default",
    sort_by: str = Query("saved_at"),
    limit: int = Query(200, ge=1, le=1000),
):
    items = _research_store.list_saved_papers(user_id=user_id, sort_by=sort_by, limit=limit)
    return SavedPapersResponse(user_id=user_id, items=items)


@router.get("/research/papers/{paper_id}", response_model=PaperDetailResponse)
def get_paper_detail(paper_id: str, user_id: str = "default"):
    detail = _research_store.get_paper_detail(paper_id=paper_id, user_id=user_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Paper not found in registry")
    return PaperDetailResponse(detail=detail)


@router.get("/research/papers/{paper_id}/repos", response_model=PaperRepoListResponse)
def get_paper_repos(paper_id: str):
    repos = _research_store.list_paper_repos(paper_id=paper_id)
    if repos is None:
        raise HTTPException(status_code=404, detail="Paper not found in registry")
    return PaperRepoListResponse(paper_id=paper_id, repos=repos)


class RouterSuggestRequest(BaseModel):
    user_id: str = "default"
    query: str = Field(..., min_length=1)


class RouterSuggestResponse(BaseModel):
    suggestion: Optional[Dict[str, Any]]


@router.post("/research/router/suggest", response_model=RouterSuggestResponse)
def suggest_track(req: RouterSuggestRequest):
    active = _research_store.get_active_track(user_id=req.user_id)
    if not active:
        return RouterSuggestResponse(suggestion=None)
    suggestion = _track_router.suggest_track(
        user_id=req.user_id, query=req.query, active_track_id=int(active["id"])
    )
    return RouterSuggestResponse(suggestion=suggestion)


class ContextRequest(BaseModel):
    user_id: str = "default"
    query: str = Field(..., min_length=1)
    track_id: Optional[int] = None
    activate_track_id: Optional[int] = None  # confirm switch: activates then uses it
    memory_limit: int = Field(8, ge=1, le=50)
    paper_limit: int = Field(8, ge=0, le=50)
    offline: bool = False
    include_cross_track: bool = False
    stage: str = "auto"  # auto/survey/writing/rebuttal
    exploration_ratio: Optional[float] = Field(default=None, ge=0.0, le=0.5)
    diversity_strength: Optional[float] = Field(default=None, ge=0.0, le=2.0)


class ContextResponse(BaseModel):
    context_pack: Dict[str, Any]


@router.post("/research/context", response_model=ContextResponse)
async def build_context(req: ContextRequest):
    set_trace_id()  # Initialize trace_id for this request
    Logger.info("Received build context request", file=LogFiles.HARVEST)

    if req.activate_track_id is not None:
        Logger.info("Activating research track", file=LogFiles.HARVEST)
        activated = _research_store.activate_track(
            user_id=req.user_id, track_id=req.activate_track_id
        )
        if not activated:
            Logger.error("Research track not found", file=LogFiles.HARVEST)
            raise HTTPException(status_code=404, detail="Track not found")

    Logger.info("Initializing context engine", file=LogFiles.HARVEST)
    engine = ContextEngine(
        research_store=_research_store,
        memory_store=_memory_store,
        track_router=_track_router,
        config=ContextEngineConfig(
            memory_limit=req.memory_limit,
            paper_limit=req.paper_limit,
            offline=req.offline,
            stage=req.stage,
            exploration_ratio=(
                float(req.exploration_ratio) if req.exploration_ratio is not None else None
            ),
            diversity_strength=(
                float(req.diversity_strength) if req.diversity_strength is not None else None
            ),
        ),
    )
    try:
        Logger.info("Building context pack with paper recommendations", file=LogFiles.HARVEST)
        pack = await engine.build_context_pack(
            user_id=req.user_id,
            query=req.query,
            track_id=req.track_id,
            include_cross_track=req.include_cross_track,
        )
        paper_count = len(pack.get("paper_recommendations", []))
        Logger.info(
            f"Context pack built successfully, found {paper_count} papers", file=LogFiles.HARVEST
        )
        return ContextResponse(context_pack=pack)
    finally:
        await engine.close()


class ScholarNetworkRequest(BaseModel):
    scholar_id: Optional[str] = None
    scholar_name: Optional[str] = None
    max_papers: int = Field(100, ge=1, le=500)
    recent_years: int = Field(5, ge=0, le=30)
    max_nodes: int = Field(40, ge=5, le=200)


class ScholarNetworkResponse(BaseModel):
    scholar: Dict[str, Any]
    stats: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class ScholarTrendsRequest(BaseModel):
    scholar_id: Optional[str] = None
    scholar_name: Optional[str] = None
    max_papers: int = Field(200, ge=1, le=1000)
    year_window: int = Field(10, ge=3, le=30)


class ScholarTrendsResponse(BaseModel):
    scholar: Dict[str, Any]
    stats: Dict[str, Any]
    publication_velocity: List[Dict[str, Any]]
    topic_distribution: List[Dict[str, Any]]
    venue_distribution: List[Dict[str, Any]]
    recent_papers: List[Dict[str, Any]]
    trend_summary: Dict[str, Any]


def _resolve_scholar_identity(
    *, scholar_id: Optional[str], scholar_name: Optional[str]
) -> Tuple[str, Optional[str]]:
    if scholar_id and scholar_id.strip():
        return scholar_id.strip(), None

    if not scholar_name or not scholar_name.strip():
        raise HTTPException(status_code=400, detail="scholar_id or scholar_name is required")

    from paperbot.agents.scholar_tracking.scholar_profile_agent import ScholarProfileAgent

    name_key = scholar_name.strip().lower()
    try:
        profile = ScholarProfileAgent()
        for scholar in profile.list_tracked_scholars():
            if (scholar.name or "").strip().lower() != name_key:
                continue
            if not scholar.semantic_scholar_id:
                break
            return scholar.semantic_scholar_id, scholar.name
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"failed to load scholar profile: {exc}"
        ) from exc

    raise HTTPException(
        status_code=404,
        detail="Scholar not found in subscriptions. Provide scholar_id directly or add scholar to subscriptions.",
    )


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _extract_year_from_paper(paper: Dict[str, Any]) -> Optional[int]:
    year = _safe_int(paper.get("year"), 0)
    if year > 0:
        return year

    date_value = str(paper.get("publicationDate") or paper.get("publication_date") or "")
    match = re.search(r"(20\d{2}|19\d{2})", date_value)
    if match:
        return _safe_int(match.group(1), 0) or None
    return None


def _unwrap_author_paper_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(row.get("paper"), dict):
        return row["paper"]
    return row


def _trend_direction(values: List[float]) -> str:
    if len(values) < 2:
        return "flat"
    pivot = max(1, len(values) // 2)
    older = sum(values[:pivot]) / max(1, len(values[:pivot]))
    recent = sum(values[pivot:]) / max(1, len(values[pivot:]))
    if recent > older * 1.15:
        return "up"
    if recent < older * 0.85:
        return "down"
    return "flat"


@router.post("/research/scholar/network", response_model=ScholarNetworkResponse)
async def scholar_network(req: ScholarNetworkRequest):
    scholar_id, resolved_name = _resolve_scholar_identity(
        scholar_id=req.scholar_id,
        scholar_name=req.scholar_name,
    )

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or os.getenv("S2_API_KEY")
    client = SemanticScholarClient(api_key=api_key)
    try:
        author = await client.get_author(
            scholar_id,
            fields=["name", "affiliations", "paperCount", "citationCount", "hIndex"],
        )
        paper_rows = await client.get_author_papers(
            scholar_id,
            limit=max(1, int(req.max_papers)),
            fields=["title", "year", "citationCount", "authors", "url", "publicationDate"],
        )
    finally:
        await client.close()

    target_name = (author or {}).get("name") or resolved_name or req.scholar_name or scholar_id
    target_key = str(scholar_id)
    min_year: Optional[int] = None
    if req.recent_years > 0:
        min_year = datetime.now(timezone.utc).year - int(req.recent_years) + 1

    collaborators: Dict[str, Dict[str, Any]] = {}
    papers_used = 0

    for raw_row in paper_rows:
        paper = _unwrap_author_paper_row(raw_row)
        year = _extract_year_from_paper(paper)
        if min_year and year and year < min_year:
            continue

        parsed_authors: List[Tuple[str, str]] = []
        has_target_author = False
        for author_row in paper.get("authors") or []:
            if isinstance(author_row, dict):
                author_id = str(author_row.get("authorId") or "")
                author_name = str(author_row.get("name") or "").strip()
            else:
                author_id = ""
                author_name = str(author_row or "").strip()
            if not author_name:
                continue
            parsed_authors.append((author_id, author_name))
            if author_id and author_id == target_key:
                has_target_author = True
            elif not author_id and author_name.lower() == str(target_name).lower():
                has_target_author = True

        if not parsed_authors or not has_target_author:
            continue

        papers_used += 1
        paper_title = str(paper.get("title") or "Untitled")
        citation_count = _safe_int(paper.get("citationCount"), 0)

        for author_id, author_name in parsed_authors:
            if (author_id and author_id == target_key) or (
                not author_id and author_name.lower() == str(target_name).lower()
            ):
                continue

            node_id = f"author:{author_id}" if author_id else f"name:{author_name.lower()}"
            item = collaborators.setdefault(
                node_id,
                {
                    "id": node_id,
                    "author_id": author_id or None,
                    "name": author_name,
                    "collab_papers": 0,
                    "citation_sum": 0,
                    "recent_year": year,
                    "sample_titles": [],
                },
            )
            item["collab_papers"] += 1
            item["citation_sum"] += citation_count
            if year and (not item.get("recent_year") or year > int(item.get("recent_year") or 0)):
                item["recent_year"] = year
            if len(item["sample_titles"]) < 3:
                item["sample_titles"].append(paper_title)

    ranked = sorted(
        collaborators.values(),
        key=lambda row: (int(row["collab_papers"]), int(row["citation_sum"])),
        reverse=True,
    )
    ranked = ranked[: max(0, int(req.max_nodes) - 1)]

    nodes = [
        {
            "id": f"author:{target_key}",
            "author_id": target_key,
            "name": target_name,
            "type": "target",
            "collab_papers": papers_used,
            "citation_sum": _safe_int((author or {}).get("citationCount"), 0),
        }
    ]
    nodes.extend(
        [
            {
                "id": row["id"],
                "author_id": row["author_id"],
                "name": row["name"],
                "type": "coauthor",
                "collab_papers": row["collab_papers"],
                "citation_sum": row["citation_sum"],
                "recent_year": row.get("recent_year"),
            }
            for row in ranked
        ]
    )

    edges = [
        {
            "source": f"author:{target_key}",
            "target": row["id"],
            "weight": row["collab_papers"],
            "citation_sum": row["citation_sum"],
            "sample_titles": row["sample_titles"],
        }
        for row in ranked
    ]

    scholar_payload = {
        "scholar_id": target_key,
        "name": target_name,
        "affiliations": (author or {}).get("affiliations") or [],
        "paper_count": _safe_int((author or {}).get("paperCount"), 0),
        "citation_count": _safe_int((author or {}).get("citationCount"), 0),
        "h_index": _safe_int((author or {}).get("hIndex"), 0),
    }

    return ScholarNetworkResponse(
        scholar=scholar_payload,
        stats={
            "papers_fetched": len(paper_rows),
            "papers_used": papers_used,
            "coauthor_count": len(ranked),
            "recent_years": int(req.recent_years),
        },
        nodes=nodes,
        edges=edges,
    )


@router.post("/research/scholar/trends", response_model=ScholarTrendsResponse)
async def scholar_trends(req: ScholarTrendsRequest):
    scholar_id, resolved_name = _resolve_scholar_identity(
        scholar_id=req.scholar_id,
        scholar_name=req.scholar_name,
    )

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or os.getenv("S2_API_KEY")
    client = SemanticScholarClient(api_key=api_key)
    try:
        author = await client.get_author(
            scholar_id,
            fields=["name", "affiliations", "paperCount", "citationCount", "hIndex"],
        )
        paper_rows = await client.get_author_papers(
            scholar_id,
            limit=max(1, int(req.max_papers)),
            fields=[
                "title",
                "year",
                "citationCount",
                "venue",
                "fieldsOfStudy",
                "publicationDate",
                "url",
            ],
        )
    finally:
        await client.close()

    current_year = datetime.now(timezone.utc).year
    min_year = current_year - int(req.year_window) + 1

    year_buckets: Dict[int, Dict[str, int]] = {}
    topic_counter: Counter[str] = Counter()
    venue_counter: Counter[str] = Counter()
    recent_papers: List[Dict[str, Any]] = []

    for raw_row in paper_rows:
        paper = _unwrap_author_paper_row(raw_row)
        year = _extract_year_from_paper(paper)
        if year is None or year < min_year:
            continue

        citation_count = _safe_int(paper.get("citationCount"), 0)
        bucket = year_buckets.setdefault(year, {"papers": 0, "citations": 0})
        bucket["papers"] += 1
        bucket["citations"] += citation_count

        for topic in paper.get("fieldsOfStudy") or paper.get("fields_of_study") or []:
            topic_name = str(topic).strip()
            if topic_name:
                topic_counter[topic_name] += 1

        venue = str(
            paper.get("venue")
            or (
                (paper.get("publicationVenue") or {}).get("name")
                if isinstance(paper.get("publicationVenue"), dict)
                else ""
            )
            or ""
        ).strip()
        if venue:
            venue_counter[venue] += 1

        recent_papers.append(
            {
                "title": paper.get("title") or "Untitled",
                "year": year,
                "citation_count": citation_count,
                "venue": venue,
                "url": paper.get("url") or "",
            }
        )

    yearly = [
        {
            "year": year,
            "papers": stats["papers"],
            "citations": stats["citations"],
        }
        for year, stats in sorted(year_buckets.items())
    ]

    recent_papers.sort(
        key=lambda row: (int(row.get("year") or 0), int(row.get("citation_count") or 0)),
        reverse=True,
    )

    paper_series = [float(row["papers"]) for row in yearly]
    citation_series = [float(row["citations"]) for row in yearly]

    trend_summary = {
        "publication_trend": _trend_direction(paper_series),
        "citation_trend": _trend_direction(citation_series),
        "active_years": len(yearly),
        "window": int(req.year_window),
    }

    scholar_payload = {
        "scholar_id": str(scholar_id),
        "name": (author or {}).get("name") or resolved_name or req.scholar_name or str(scholar_id),
        "affiliations": (author or {}).get("affiliations") or [],
        "paper_count": _safe_int((author or {}).get("paperCount"), 0),
        "citation_count": _safe_int((author or {}).get("citationCount"), 0),
        "h_index": _safe_int((author or {}).get("hIndex"), 0),
    }

    return ScholarTrendsResponse(
        scholar=scholar_payload,
        stats={
            "papers_fetched": len(paper_rows),
            "papers_in_window": sum(item["papers"] for item in yearly),
            "year_window": int(req.year_window),
        },
        publication_velocity=yearly,
        topic_distribution=[
            {"topic": topic, "count": count} for topic, count in topic_counter.most_common(15)
        ],
        venue_distribution=[
            {"venue": venue, "count": count} for venue, count in venue_counter.most_common(15)
        ],
        recent_papers=recent_papers[:10],
        trend_summary=trend_summary,
    )
