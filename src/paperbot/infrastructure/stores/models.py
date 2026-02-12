from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow: Mapped[str] = mapped_column(String(64), default="", index=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")

    # Sandbox-specific fields
    executor_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # e2b/docker/local
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paper_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    paper_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    events = relationship("AgentEventModel", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("ExecutionLogModel", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship(
        "ResourceMetricModel", back_populates="run", cascade="all, delete-orphan"
    )
    runbook_steps = relationship(
        "RunbookStepModel", back_populates="run", cascade="all, delete-orphan"
    )
    artifacts = relationship("ArtifactModel", back_populates="run", cascade="all, delete-orphan")

    def set_metadata(self, data: Dict[str, Any]) -> None:
        self.metadata_json = json.dumps(data or {}, ensure_ascii=False)

    def get_metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}


class AgentEventModel(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.run_id"), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), default="", index=True)

    span_id: Mapped[str] = mapped_column(String(32), default="")
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    workflow: Mapped[str] = mapped_column(String(64), default="")
    stage: Mapped[str] = mapped_column(String(64), default="")
    attempt: Mapped[int] = mapped_column(Integer, default=0)

    agent_name: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(32), default="")
    type: Mapped[str] = mapped_column(String(64), default="")

    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    tags_json: Mapped[str] = mapped_column(Text, default="{}")

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    run = relationship("AgentRunModel", back_populates="events")

    def set_payload(self, payload: Dict[str, Any]) -> None:
        self.payload_json = json.dumps(payload or {}, ensure_ascii=False)

    def get_payload(self) -> Dict[str, Any]:
        try:
            return json.loads(self.payload_json or "{}")
        except Exception:
            return {}

    def set_metrics(self, metrics: Dict[str, Any]) -> None:
        self.metrics_json = json.dumps(metrics or {}, ensure_ascii=False)

    def get_metrics(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metrics_json or "{}")
        except Exception:
            return {}

    def set_tags(self, tags: Dict[str, Any]) -> None:
        self.tags_json = json.dumps(tags or {}, ensure_ascii=False)

    def get_tags(self) -> Dict[str, Any]:
        try:
            return json.loads(self.tags_json or "{}")
        except Exception:
            return {}


class ExecutionLogModel(Base):
    """Execution log entries for sandbox runs"""

    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.run_id"), index=True)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    level: Mapped[str] = mapped_column(String(16), default="info")  # debug/info/warning/error
    message: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(
        String(32), default="system"
    )  # stdout/stderr/executor/system

    run = relationship("AgentRunModel", back_populates="logs")


class ResourceMetricModel(Base):
    """Resource usage metrics for sandbox runs"""

    __tablename__ = "resource_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.run_id"), index=True)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_mb: Mapped[float] = mapped_column(Float, default=0.0)
    memory_limit_mb: Mapped[float] = mapped_column(Float, default=4096.0)

    run = relationship("AgentRunModel", back_populates="metrics")


class RunbookStepModel(Base):
    """
    Structured Runbook step records.

    Logs and metrics are stored separately (execution_logs/resource_metrics) keyed by run_id.
    This table provides step-level lifecycle and configuration for long-term evidence tracking.
    """

    __tablename__ = "runbook_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.run_id"), index=True)

    step_name: Mapped[str] = mapped_column(
        String(64), index=True
    )  # smoke/install/data/train/eval/report/...
    status: Mapped[str] = mapped_column(
        String(32), default="running"
    )  # running/success/failed/error
    executor_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # docker/e2b/ssh_docker/...

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    command: Mapped[str] = mapped_column(Text, default="")
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    run = relationship("AgentRunModel", back_populates="runbook_steps")


class ArtifactModel(Base):
    """
    Artifact index for evidence tracking.

    This table stores references (paths/URIs) to outputs produced during a run/step:
    - logs (raw/filtered), metrics snapshots, reports, figures, exported evidence packs, etc.
    """

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.run_id"), index=True)
    step_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("runbook_steps.id"), nullable=True, index=True
    )

    type: Mapped[str] = mapped_column(String(32), index=True)  # log/metric/report/file/zip/...
    path_or_uri: Mapped[str] = mapped_column(Text, default="")
    mime: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    run = relationship("AgentRunModel", back_populates="artifacts")
    step = relationship("RunbookStepModel")


class MemorySourceModel(Base):
    """
    Imported chat-log sources (e.g., ChatGPT export, Gemini transcript).

    Stores provenance so memory items can be traced back to an import batch.
    """

    __tablename__ = "memory_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    filename: Mapped[str] = mapped_column(String(256), default="")
    sha256: Mapped[str] = mapped_column(String(64), index=True)

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    conversation_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    memories = relationship(
        "MemoryItemModel", back_populates="source", cascade="all, delete-orphan"
    )


class MemoryItemModel(Base):
    """
    Long-term memory items extracted from chats.

    Content is stored as plain text; retrieval can be keyword-based.
    """

    __tablename__ = "memory_items"
    __table_args__ = (UniqueConstraint("user_id", "content_hash", name="uq_memory_user_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    scope_type: Mapped[str] = mapped_column(
        String(16), default="global", index=True
    )  # global/track/project/paper
    scope_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="fact", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.6)

    status: Mapped[str] = mapped_column(
        String(16), default="approved", index=True
    )  # pending/approved/rejected/superseded
    supersedes_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("memory_items.id"), nullable=True, index=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    pii_risk: Mapped[int] = mapped_column(Integer, default=0)  # 0=unknown/low,1=maybe,2=high

    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    deleted_reason: Mapped[str] = mapped_column(Text, default="")

    source_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("memory_sources.id"), nullable=True, index=True
    )
    source = relationship("MemorySourceModel", back_populates="memories")

    supersedes = relationship("MemoryItemModel", remote_side="MemoryItemModel.id")


class MemoryAuditLogModel(Base):
    """
    Audit log for memory governance (create/edit/approve/delete).
    """

    __tablename__ = "memory_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    actor_id: Mapped[str] = mapped_column(String(64), default="", index=True)  # user/admin/service
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    action: Mapped[str] = mapped_column(
        String(32), index=True
    )  # create/update/approve/reject/delete/hard_delete/use
    item_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("memory_items.id"), nullable=True, index=True
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("memory_sources.id"), nullable=True, index=True
    )

    detail_json: Mapped[str] = mapped_column(Text, default="{}")


class MemoryEvalMetricModel(Base):
    """
    Evaluation metrics for memory system quality (acceptance criteria).

    Stores periodic measurements of:
    - extraction_precision: % of extracted items that are correct
    - false_positive_rate: % of approved items that are incorrect
    - retrieval_hit_rate: % of relevant memories retrieved when needed
    - injection_pollution_rate: % of responses negatively affected by wrong memory
    - deletion_compliance: deleted items never retrieved (should be 1.0)

    See docs/memory_types.md for metric definitions.
    """

    __tablename__ = "memory_eval_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    metric_name: Mapped[str] = mapped_column(String(64), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evaluator_id: Mapped[str] = mapped_column(String(64), default="system")

    detail_json: Mapped[str] = mapped_column(Text, default="{}")


class ResearchTrackModel(Base):
    """
    User research direction / track.

    Scope boundary for domain memories and paper recommendations.
    """

    __tablename__ = "research_tracks"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_research_tracks_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)

    name: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    venues_json: Mapped[str] = mapped_column(Text, default="[]")
    methods_json: Mapped[str] = mapped_column(Text, default="[]")

    is_active: Mapped[int] = mapped_column(Integer, default=0, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    tasks = relationship("ResearchTaskModel", back_populates="track", cascade="all, delete-orphan")
    milestones = relationship(
        "ResearchMilestoneModel", back_populates="track", cascade="all, delete-orphan"
    )
    paper_feedback = relationship(
        "PaperFeedbackModel", back_populates="track", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "ResearchTrackEmbeddingModel", back_populates="track", cascade="all, delete-orphan"
    )


class ResearchTaskModel(Base):
    """Track-scoped TODO / progress item."""

    __tablename__ = "research_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_tracks.id"), index=True)

    title: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(16), default="todo", index=True
    )  # todo/in_progress/done/blocked
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)

    paper_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    paper_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    done_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    track = relationship("ResearchTrackModel", back_populates="tasks")


class ResearchMilestoneModel(Base):
    """Track-scoped milestone (proposal/survey/experiments/writing/...)."""

    __tablename__ = "research_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_tracks.id"), index=True)

    name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(
        String(16), default="todo", index=True
    )  # todo/in_progress/done
    notes: Mapped[str] = mapped_column(Text, default="")

    due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    track = relationship("ResearchTrackModel", back_populates="milestones")


class PaperFeedbackModel(Base):
    """User feedback on recommended/seen papers (track-scoped)."""

    __tablename__ = "paper_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), index=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_tracks.id"), index=True)

    paper_id: Mapped[str] = mapped_column(String(64), index=True)
    paper_ref_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("papers.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(16), index=True)  # like/dislike/skip/save/cite

    weight: Mapped[float] = mapped_column(Float, default=0.0)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    track = relationship("ResearchTrackModel", back_populates="paper_feedback")
    paper = relationship("PaperModel", back_populates="feedback_rows")


class PaperJudgeScoreModel(Base):
    """Structured LLM-as-Judge scores linked to canonical papers."""

    __tablename__ = "paper_judge_scores"
    __table_args__ = (
        UniqueConstraint("paper_id", "query", name="uq_paper_judge_scores_paper_query"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), index=True)
    query: Mapped[str] = mapped_column(String(256), default="", index=True)

    overall: Mapped[float] = mapped_column(Float, default=0.0)
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    novelty: Mapped[float] = mapped_column(Float, default=0.0)
    rigor: Mapped[float] = mapped_column(Float, default=0.0)
    impact: Mapped[float] = mapped_column(Float, default=0.0)
    clarity: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation: Mapped[str] = mapped_column(String(32), default="", index=True)
    one_line_summary: Mapped[str] = mapped_column(Text, default="")
    judge_model: Mapped[str] = mapped_column(String(128), default="")
    judge_cost_tier: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    paper = relationship("PaperModel", back_populates="judge_scores")


class PaperRepoModel(Base):
    """Repository enrichment metadata linked to canonical papers."""

    __tablename__ = "paper_repos"
    __table_args__ = (UniqueConstraint("paper_id", "repo_url", name="uq_paper_repos_paper_repo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), index=True)

    repo_url: Mapped[str] = mapped_column(String(512), default="", index=True)
    full_name: Mapped[str] = mapped_column(String(256), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    stars: Mapped[int] = mapped_column(Integer, default=0, index=True)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    watchers: Mapped[int] = mapped_column(Integer, default=0)

    language: Mapped[str] = mapped_column(String(64), default="")
    license: Mapped[str] = mapped_column(String(64), default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    html_url: Mapped[str] = mapped_column(String(512), default="")
    topics_json: Mapped[str] = mapped_column(Text, default="[]")

    updated_at_remote: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    pushed_at_remote: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    query: Mapped[str] = mapped_column(String(256), default="", index=True)
    source: Mapped[str] = mapped_column(String(32), default="paperscool_repo_enrich", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    paper = relationship("PaperModel", back_populates="repo_rows")

    def set_topics(self, values: Optional[list[str]]) -> None:
        self.topics_json = json.dumps(
            [str(v) for v in (values or []) if str(v).strip()],
            ensure_ascii=False,
        )

    def get_topics(self) -> list[str]:
        try:
            data = json.loads(self.topics_json or "[]")
            if isinstance(data, list):
                return [str(v) for v in data if str(v).strip()]
        except Exception:
            pass
        return []


class PaperReadingStatusModel(Base):
    """Per-user reading lifecycle state for a paper."""

    __tablename__ = "paper_reading_status"
    __table_args__ = (
        UniqueConstraint("user_id", "paper_id", name="uq_paper_reading_status_user_paper"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), index=True)

    status: Mapped[str] = mapped_column(String(16), default="unread", index=True)
    saved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    paper = relationship("PaperModel", back_populates="reading_status_rows")


class ResearchTrackEmbeddingModel(Base):
    """Cached embedding for a track profile (to improve routing)."""

    __tablename__ = "research_track_embeddings"
    __table_args__ = (UniqueConstraint("track_id", "model", name="uq_track_embedding_track_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_tracks.id"), index=True)

    model: Mapped[str] = mapped_column(String(64), default="text-embedding-3-small", index=True)
    text_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")
    dim: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    track = relationship("ResearchTrackModel", back_populates="embeddings")


class NewsletterSubscriberModel(Base):
    """Email newsletter subscriber for DailyPaper digest delivery.

    TODO(GDPR): email stored as plaintext — consider encryption-at-rest or
    hashing. Add a hard-delete method for GDPR/CCPA right-to-erasure (current
    unsubscribe only sets status='unsubscribed', no row purge).
    """

    __tablename__ = "newsletter_subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    unsub_token: Mapped[str] = mapped_column(String(64), unique=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    unsub_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class ResearchContextRunModel(Base):
    """
    One context build event (routing + recommendations), used for replay/eval.
    """

    __tablename__ = "research_context_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), index=True)
    track_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("research_tracks.id"), nullable=True, index=True
    )

    query: Mapped[str] = mapped_column(Text, default="")
    merged_query: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(String(16), default="auto", index=True)

    exploration_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    diversity_strength: Mapped[float] = mapped_column(Float, default=0.0)

    routing_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    impressions = relationship(
        "PaperImpressionModel", back_populates="run", cascade="all, delete-orphan"
    )
    track = relationship("ResearchTrackModel")


class PaperImpressionModel(Base):
    """
    A paper shown to the user as part of a recommendation list.
    """

    __tablename__ = "paper_impressions"
    __table_args__ = (UniqueConstraint("run_id", "paper_id", name="uq_paper_impression_run_paper"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_context_runs.id"), index=True)

    user_id: Mapped[str] = mapped_column(String(64), index=True)
    track_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("research_tracks.id"), nullable=True, index=True
    )

    paper_id: Mapped[str] = mapped_column(String(64), index=True)
    rank: Mapped[int] = mapped_column(Integer, default=0, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    run = relationship("ResearchContextRunModel", back_populates="impressions")
    track = relationship("ResearchTrackModel")


class PaperModel(Base):
    """Harvested paper metadata from multiple sources."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Canonical identifiers (for deduplication)
    doi: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    semantic_scholar_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    openalex_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    title_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA256 of normalized title

    # Core metadata
    title: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    authors_json: Mapped[str] = mapped_column(Text, default="[]")
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    publication_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # URLs (no PDF download, just references)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Classification
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    fields_of_study_json: Mapped[str] = mapped_column(Text, default="[]")

    # Source tracking
    primary_source: Mapped[str] = mapped_column(
        String(32), default=""
    )  # First source that found this paper
    sources_json: Mapped[str] = mapped_column(
        Text, default="[]"
    )  # All sources that returned this paper

    # Timestamps
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Soft delete

    # Relationships
    feedback_rows = relationship("PaperFeedbackModel", back_populates="paper")
    judge_scores = relationship("PaperJudgeScoreModel", back_populates="paper")
    reading_status_rows = relationship("PaperReadingStatusModel", back_populates="paper")
    repo_rows = relationship("PaperRepoModel", back_populates="paper")

    def get_authors(self) -> list:
        try:
            return json.loads(self.authors_json or "[]")
        except Exception:
            return []

    def get_keywords(self) -> list:
        try:
            return json.loads(self.keywords_json or "[]")
        except Exception:
            return []

    def get_fields_of_study(self) -> list:
        try:
            return json.loads(self.fields_of_study_json or "[]")
        except Exception:
            return []

    def get_sources(self) -> list:
        try:
            return json.loads(self.sources_json or "[]")
        except Exception:
            return []

    def set_keywords(self, keywords: list) -> None:
        self.keywords_json = json.dumps(keywords or [], ensure_ascii=False)

    def set_fields_of_study(self, fields: list) -> None:
        self.fields_of_study_json = json.dumps(fields or [], ensure_ascii=False)

    def set_sources(self, sources: list) -> None:
        self.sources_json = json.dumps(sources or [], ensure_ascii=False)


class HarvestRunModel(Base):
    """Harvest execution tracking."""

    __tablename__ = "harvest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Input
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    venues_json: Mapped[str] = mapped_column(Text, default="[]")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    max_results_per_source: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Results
    status: Mapped[Optional[str]] = mapped_column(
        String(32), default="running", index=True
    )  # running/success/partial/failed
    papers_found: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    papers_new: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    papers_deduplicated: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    error_json: Mapped[str] = mapped_column(Text, default="{}")

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def get_keywords(self) -> list:
        try:
            return json.loads(self.keywords_json or "[]")
        except Exception:
            return []

    def get_venues(self) -> list:
        try:
            return json.loads(self.venues_json or "[]")
        except Exception:
            return []

    def get_sources(self) -> list:
        try:
            return json.loads(self.sources_json or "[]")
        except Exception:
            return []

    def get_errors(self) -> dict:
        try:
            return json.loads(self.error_json or "{}")
        except Exception:
            return {}

    def set_errors(self, errors: dict) -> None:
        self.error_json = json.dumps(errors or {}, ensure_ascii=False)
