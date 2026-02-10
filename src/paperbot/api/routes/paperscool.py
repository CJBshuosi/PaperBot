from __future__ import annotations

import copy
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from paperbot.api.streaming import StreamEvent, wrap_generator
from paperbot.application.services.daily_push_service import DailyPushService
from paperbot.application.services.llm_service import get_llm_service
from paperbot.application.workflows.analysis.paper_judge import PaperJudge
from paperbot.application.workflows.dailypaper import (
    DailyPaperReporter,
    apply_judge_scores_to_report,
    build_daily_paper_report,
    enrich_daily_paper_report,
    ingest_daily_report_to_registry,
    normalize_llm_features,
    normalize_output_formats,
    persist_judge_scores_to_registry,
    render_daily_paper_markdown,
    select_judge_candidates,
)
from paperbot.application.workflows.paperscool_topic_search import PapersCoolTopicSearchWorkflow
from paperbot.utils.text_processing import extract_github_url

router = APIRouter()


class PapersCoolSearchRequest(BaseModel):
    queries: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=lambda: ["papers_cool"])
    branches: List[str] = Field(default_factory=lambda: ["arxiv", "venue"])
    top_k_per_query: int = Field(5, ge=1, le=50)
    show_per_branch: int = Field(25, ge=1, le=200)
    min_score: float = Field(0.0, ge=0.0, description="Drop papers scoring below this threshold")


class PapersCoolSearchResponse(BaseModel):
    source: str
    fetched_at: str
    sources: List[str]
    queries: List[Dict[str, Any]]
    items: List[Dict[str, Any]]
    summary: Dict[str, Any]


class DailyPaperRequest(BaseModel):
    queries: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=lambda: ["papers_cool"])
    branches: List[str] = Field(default_factory=lambda: ["arxiv", "venue"])
    top_k_per_query: int = Field(5, ge=1, le=50)
    show_per_branch: int = Field(25, ge=1, le=200)
    min_score: float = Field(0.0, ge=0.0, description="Drop papers scoring below this threshold")
    title: str = "DailyPaper Digest"
    top_n: int = Field(10, ge=1, le=200)
    formats: List[str] = Field(default_factory=lambda: ["both"])
    save: bool = False
    output_dir: str = "./reports/dailypaper"
    enable_llm_analysis: bool = False
    llm_features: List[str] = Field(default_factory=lambda: ["summary"])
    enable_judge: bool = False
    judge_runs: int = Field(1, ge=1, le=5)
    judge_max_items_per_query: int = Field(5, ge=1, le=200)
    judge_token_budget: int = Field(0, ge=0, le=2_000_000)
    notify: bool = False
    notify_channels: List[str] = Field(default_factory=list)
    notify_email_to: List[str] = Field(default_factory=list)


class DailyPaperResponse(BaseModel):
    report: Dict[str, Any]
    markdown: str
    markdown_path: Optional[str] = None
    json_path: Optional[str] = None
    notify_result: Optional[Dict[str, Any]] = None


class PapersCoolAnalyzeRequest(BaseModel):
    report: Dict[str, Any]
    run_judge: bool = False
    run_trends: bool = False
    run_insight: bool = False
    judge_runs: int = Field(1, ge=1, le=5)
    judge_max_items_per_query: int = Field(5, ge=1, le=200)
    judge_token_budget: int = Field(0, ge=0, le=2_000_000)
    trend_max_items_per_query: int = Field(3, ge=1, le=20)


class PapersCoolReposRequest(BaseModel):
    report: Optional[Dict[str, Any]] = None
    papers: List[Dict[str, Any]] = Field(default_factory=list)
    max_items: int = Field(100, ge=1, le=1000)
    include_github_api: bool = True


class PapersCoolReposResponse(BaseModel):
    total_candidates: int
    matched_repos: int
    github_api_used: bool
    repos: List[Dict[str, Any]]


@router.post("/research/paperscool/search", response_model=PapersCoolSearchResponse)
def topic_search(req: PapersCoolSearchRequest):
    cleaned_queries = [q.strip() for q in req.queries if (q or "").strip()]
    if not cleaned_queries:
        raise HTTPException(status_code=400, detail="queries is required")

    workflow = PapersCoolTopicSearchWorkflow()
    try:
        result = workflow.run(
            queries=cleaned_queries,
            sources=req.sources,
            branches=req.branches,
            top_k_per_query=req.top_k_per_query,
            show_per_branch=req.show_per_branch,
            min_score=req.min_score,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"topic search failed: {exc}") from exc
    return PapersCoolSearchResponse(**result)


async def _dailypaper_stream(req: DailyPaperRequest):
    """SSE generator for the full DailyPaper pipeline."""
    cleaned_queries = [q.strip() for q in req.queries if (q or "").strip()]

    # Phase 1 — Search
    yield StreamEvent(type="progress", data={"phase": "search", "message": "Searching papers..."})
    workflow = PapersCoolTopicSearchWorkflow()
    effective_top_k = max(int(req.top_k_per_query), int(req.top_n), 1)
    search_result = workflow.run(
        queries=cleaned_queries,
        sources=req.sources,
        branches=req.branches,
        top_k_per_query=effective_top_k,
        show_per_branch=req.show_per_branch,
        min_score=req.min_score,
    )
    summary = search_result.get("summary") or {}
    yield StreamEvent(
        type="search_done",
        data={
            "items_count": len(search_result.get("items") or []),
            "queries_count": len(search_result.get("queries") or []),
            "unique_items": int(summary.get("unique_items") or 0),
        },
    )

    # Phase 2 — Build Report
    yield StreamEvent(type="progress", data={"phase": "build", "message": "Building report..."})
    report = build_daily_paper_report(search_result=search_result, title=req.title, top_n=req.top_n)
    yield StreamEvent(
        type="report_built",
        data={
            "queries_count": len(report.get("queries") or []),
            "global_top_count": len(report.get("global_top") or []),
            "report": report,
        },
    )

    # Phase 3 — LLM Enrichment
    if req.enable_llm_analysis:
        features = normalize_llm_features(req.llm_features)
        if features:
            llm_service = get_llm_service()
            llm_block: Dict[str, Any] = {
                "enabled": True,
                "features": features,
                "query_trends": [],
                "daily_insight": "",
            }

            summary_done = 0
            summary_total = 0
            if "summary" in features or "relevance" in features:
                for query in report.get("queries") or []:
                    summary_total += len((query.get("top_items") or [])[:3])

            yield StreamEvent(
                type="progress",
                data={"phase": "llm", "message": "Starting LLM enrichment...", "total": summary_total},
            )

            for query in report.get("queries") or []:
                query_name = query.get("normalized_query") or query.get("raw_query") or ""
                top_items = (query.get("top_items") or [])[:3]

                if "summary" in features:
                    for item in top_items:
                        item["ai_summary"] = llm_service.summarize_paper(
                            title=item.get("title") or "",
                            abstract=item.get("snippet") or item.get("abstract") or "",
                        )
                        summary_done += 1
                        yield StreamEvent(
                            type="llm_summary",
                            data={
                                "title": item.get("title") or "Untitled",
                                "query": query_name,
                                "ai_summary": item["ai_summary"],
                                "done": summary_done,
                                "total": summary_total,
                            },
                        )

                if "relevance" in features:
                    for item in top_items:
                        item["relevance"] = llm_service.assess_relevance(paper=item, query=query_name)
                        if "summary" not in features:
                            summary_done += 1

                if "trends" in features and top_items:
                    trend_text = llm_service.analyze_trends(topic=query_name, papers=top_items)
                    llm_block["query_trends"].append({"query": query_name, "analysis": trend_text})
                    yield StreamEvent(
                        type="trend",
                        data={
                            "query": query_name,
                            "analysis": trend_text,
                            "done": len(llm_block["query_trends"]),
                            "total": len(report.get("queries") or []),
                        },
                    )

            if "insight" in features:
                yield StreamEvent(type="progress", data={"phase": "insight", "message": "Generating daily insight..."})
                llm_block["daily_insight"] = llm_service.generate_daily_insight(report)
                yield StreamEvent(type="insight", data={"analysis": llm_block["daily_insight"]})

            report["llm_analysis"] = llm_block
            yield StreamEvent(
                type="llm_done",
                data={
                    "summaries_count": summary_done,
                    "trends_count": len(llm_block["query_trends"]),
                },
            )

    # Phase 4 — Judge
    if req.enable_judge:
        llm_service_j = get_llm_service()
        judge = PaperJudge(llm_service=llm_service_j)
        selection = select_judge_candidates(
            report,
            max_items_per_query=req.judge_max_items_per_query,
            n_runs=req.judge_runs,
            token_budget=req.judge_token_budget,
        )
        selected = list(selection.get("selected") or [])
        recommendation_count: Dict[str, int] = {
            "must_read": 0,
            "worth_reading": 0,
            "skim": 0,
            "skip": 0,
        }

        yield StreamEvent(
            type="progress",
            data={
                "phase": "judge",
                "message": "Starting judge scoring",
                "total": len(selected),
                "budget": selection.get("budget") or {},
            },
        )

        for idx, row in enumerate(selected, start=1):
            query_index = int(row.get("query_index") or 0)
            item_index = int(row.get("item_index") or 0)

            queries = list(report.get("queries") or [])
            if query_index >= len(queries):
                continue

            query = queries[query_index]
            query_name = query.get("normalized_query") or query.get("raw_query") or ""
            top_items = list(query.get("top_items") or [])
            if item_index >= len(top_items):
                continue

            item = top_items[item_index]
            if req.judge_runs > 1:
                judgment = judge.judge_with_calibration(
                    paper=item,
                    query=query_name,
                    n_runs=max(1, int(req.judge_runs)),
                )
            else:
                judgment = judge.judge_single(paper=item, query=query_name)

            j_payload = judgment.to_dict()
            item["judge"] = j_payload
            rec = j_payload.get("recommendation")
            if rec in recommendation_count:
                recommendation_count[rec] += 1

            yield StreamEvent(
                type="judge",
                data={
                    "query": query_name,
                    "title": item.get("title") or "Untitled",
                    "judge": j_payload,
                    "done": idx,
                    "total": len(selected),
                },
            )

        for query in report.get("queries") or []:
            top_items = list(query.get("top_items") or [])
            if not top_items:
                continue
            capped_count = min(len(top_items), max(1, int(req.judge_max_items_per_query)))
            capped = top_items[:capped_count]
            capped.sort(
                key=lambda it: float((it.get("judge") or {}).get("overall") or -1), reverse=True
            )
            query["top_items"] = capped + top_items[capped_count:]

        report["judge"] = {
            "enabled": True,
            "max_items_per_query": int(req.judge_max_items_per_query),
            "n_runs": int(max(1, int(req.judge_runs))),
            "recommendation_count": recommendation_count,
            "budget": selection.get("budget") or {},
        }
        yield StreamEvent(type="judge_done", data=report["judge"])

        # Phase 4b — Filter: remove papers below "worth_reading"
        KEEP_RECOMMENDATIONS = {"must_read", "worth_reading"}
        yield StreamEvent(
            type="progress",
            data={"phase": "filter", "message": "Filtering papers by judge recommendation..."},
        )
        filter_log: List[Dict[str, Any]] = []
        total_before = 0
        total_after = 0
        for query in report.get("queries") or []:
            query_name = query.get("normalized_query") or query.get("raw_query") or ""
            items_before = list(query.get("top_items") or [])
            total_before += len(items_before)
            kept: List[Dict[str, Any]] = []
            removed: List[Dict[str, Any]] = []
            for item in items_before:
                j = item.get("judge")
                if isinstance(j, dict):
                    rec = j.get("recommendation", "")
                    if rec in KEEP_RECOMMENDATIONS:
                        kept.append(item)
                    else:
                        removed.append(item)
                        filter_log.append({
                            "query": query_name,
                            "title": item.get("title") or "Untitled",
                            "recommendation": rec,
                            "overall": j.get("overall"),
                            "action": "removed",
                        })
                else:
                    # No judge score — keep by default (unjudged papers)
                    kept.append(item)
            total_after += len(kept)
            query["top_items"] = kept

        # Also filter global_top
        global_before = list(report.get("global_top") or [])
        global_kept = []
        for item in global_before:
            j = item.get("judge")
            if isinstance(j, dict):
                rec = j.get("recommendation", "")
                if rec in KEEP_RECOMMENDATIONS:
                    global_kept.append(item)
            else:
                global_kept.append(item)
        report["global_top"] = global_kept

        report["filter"] = {
            "enabled": True,
            "keep_recommendations": list(KEEP_RECOMMENDATIONS),
            "total_before": total_before,
            "total_after": total_after,
            "removed_count": total_before - total_after,
            "log": filter_log,
        }
        yield StreamEvent(
            type="filter_done",
            data={
                "total_before": total_before,
                "total_after": total_after,
                "removed_count": total_before - total_after,
                "log": filter_log,
            },
        )

    # Phase 5 — Persist + Notify
    yield StreamEvent(type="progress", data={"phase": "save", "message": "Saving to registry..."})
    try:
        ingest_summary = ingest_daily_report_to_registry(report)
        report["registry_ingest"] = ingest_summary
    except Exception as exc:
        report["registry_ingest"] = {"error": str(exc)}

    if req.enable_judge:
        try:
            report["judge_registry_ingest"] = persist_judge_scores_to_registry(report)
        except Exception as exc:
            report["judge_registry_ingest"] = {"error": str(exc)}

    markdown = render_daily_paper_markdown(report)

    markdown_path = None
    json_path = None
    notify_result: Optional[Dict[str, Any]] = None
    if req.save:
        reporter = DailyPaperReporter(output_dir=req.output_dir)
        artifacts = reporter.write(
            report=report,
            markdown=markdown,
            formats=normalize_output_formats(req.formats),
            slug=req.title,
        )
        markdown_path = artifacts.markdown_path
        json_path = artifacts.json_path

    if req.notify:
        yield StreamEvent(type="progress", data={"phase": "notify", "message": "Sending notifications..."})
        notify_service = DailyPushService.from_env()
        notify_result = notify_service.push_dailypaper(
            report=report,
            markdown=markdown,
            markdown_path=markdown_path,
            json_path=json_path,
            channels_override=req.notify_channels or None,
            email_to_override=req.notify_email_to or None,
        )

    yield StreamEvent(
        type="result",
        data={
            "report": report,
            "markdown": markdown,
            "markdown_path": markdown_path,
            "json_path": json_path,
            "notify_result": notify_result,
        },
    )


@router.post("/research/paperscool/daily")
async def generate_daily_report(req: DailyPaperRequest):
    cleaned_queries = [q.strip() for q in req.queries if (q or "").strip()]
    if not cleaned_queries:
        raise HTTPException(status_code=400, detail="queries is required")

    # Fast sync path when no LLM/Judge — avoids SSE overhead
    if not req.enable_llm_analysis and not req.enable_judge:
        return _sync_daily_report(req, cleaned_queries)

    # SSE streaming path for long-running operations
    return StreamingResponse(
        wrap_generator(_dailypaper_stream(req)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _sync_daily_report(req: DailyPaperRequest, cleaned_queries: List[str]):
    """Original synchronous path for fast requests (no LLM/Judge)."""
    workflow = PapersCoolTopicSearchWorkflow()
    effective_top_k = max(int(req.top_k_per_query), int(req.top_n), 1)
    try:
        search_result = workflow.run(
            queries=cleaned_queries,
            sources=req.sources,
            branches=req.branches,
            top_k_per_query=effective_top_k,
            show_per_branch=req.show_per_branch,
            min_score=req.min_score,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"daily search failed: {exc}") from exc
    report = build_daily_paper_report(search_result=search_result, title=req.title, top_n=req.top_n)

    try:
        ingest_summary = ingest_daily_report_to_registry(report)
        report["registry_ingest"] = ingest_summary
    except Exception as exc:
        report["registry_ingest"] = {"error": str(exc)}

    markdown = render_daily_paper_markdown(report)

    markdown_path = None
    json_path = None
    notify_result: Optional[Dict[str, Any]] = None
    if req.save:
        reporter = DailyPaperReporter(output_dir=req.output_dir)
        artifacts = reporter.write(
            report=report,
            markdown=markdown,
            formats=normalize_output_formats(req.formats),
            slug=req.title,
        )
        markdown_path = artifacts.markdown_path
        json_path = artifacts.json_path

    if req.notify:
        notify_service = DailyPushService.from_env()
        notify_result = notify_service.push_dailypaper(
            report=report,
            markdown=markdown,
            markdown_path=markdown_path,
            json_path=json_path,
            channels_override=req.notify_channels or None,
            email_to_override=req.notify_email_to or None,
        )

    return DailyPaperResponse(
        report=report,
        markdown=markdown,
        markdown_path=markdown_path,
        json_path=json_path,
        notify_result=notify_result,
    )


_GITHUB_REPO_RE = re.compile(r"https?://github\.com/([\w.-]+)/([\w.-]+)", re.IGNORECASE)


def _normalize_github_repo_url(raw_url: str | None) -> Optional[str]:
    if not raw_url:
        return None
    candidate = (raw_url or "").strip()
    if not candidate:
        return None
    if "github.com" not in candidate.lower():
        return None
    if not candidate.startswith("http"):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if "github.com" not in (parsed.netloc or "").lower():
        return None

    match = _GITHUB_REPO_RE.search(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
    if not match:
        return None

    owner, repo = match.group(1), match.group(2)
    repo = repo.removesuffix(".git")
    return f"https://github.com/{owner}/{repo}"


def _extract_repo_url_from_paper(paper: Dict[str, Any]) -> Optional[str]:
    candidates: List[str] = []
    for key in ("github_url", "external_url", "url", "pdf_url"):
        value = paper.get(key)
        if isinstance(value, str) and value:
            candidates.append(value)

    for alt in paper.get("alternative_urls") or []:
        if isinstance(alt, str) and alt:
            candidates.append(alt)

    for candidate in candidates:
        normalized = _normalize_github_repo_url(candidate)
        if normalized:
            return normalized

    text_blob_parts = [
        str(paper.get("title") or ""),
        str(paper.get("snippet") or paper.get("abstract") or ""),
        " ".join(str(k) for k in (paper.get("keywords") or [])),
    ]
    extracted = extract_github_url("\n".join(text_blob_parts))
    return _normalize_github_repo_url(extracted)


def _flatten_report_papers(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for query in report.get("queries") or []:
        query_name = query.get("normalized_query") or query.get("raw_query") or ""
        for item in query.get("top_items") or []:
            row = dict(item)
            row.setdefault("_query", query_name)
            rows.append(row)

    for item in report.get("global_top") or []:
        row = dict(item)
        if "_query" not in row:
            matched = row.get("matched_queries") or []
            row["_query"] = matched[0] if matched else ""
        rows.append(row)

    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in rows:
        key = f"{item.get('url') or ''}|{item.get('title') or ''}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _fetch_github_repo_metadata(repo_url: str, token: Optional[str]) -> Dict[str, Any]:
    normalized = _normalize_github_repo_url(repo_url)
    if not normalized:
        return {"ok": False, "error": "invalid_repo_url"}

    match = _GITHUB_REPO_RE.search(normalized)
    if not match:
        return {"ok": False, "error": "invalid_repo_url"}

    owner, repo = match.group(1), match.group(2)
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "PaperBot/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {
                "ok": False,
                "status": resp.status_code,
                "error": "github_api_error",
                "repo_url": normalized,
            }

        payload = resp.json()
        return {
            "ok": True,
            "status": resp.status_code,
            "repo_url": normalized,
            "full_name": payload.get("full_name") or f"{owner}/{repo}",
            "description": payload.get("description") or "",
            "stars": int(payload.get("stargazers_count") or 0),
            "forks": int(payload.get("forks_count") or 0),
            "open_issues": int(payload.get("open_issues_count") or 0),
            "watchers": int(payload.get("subscribers_count") or payload.get("watchers_count") or 0),
            "language": payload.get("language") or "",
            "license": (payload.get("license") or {}).get("spdx_id") or "",
            "updated_at": payload.get("updated_at"),
            "pushed_at": payload.get("pushed_at"),
            "archived": bool(payload.get("archived")),
            "topics": payload.get("topics") or [],
            "html_url": payload.get("html_url") or normalized,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"github_api_exception: {exc}",
            "repo_url": normalized,
        }


@router.post("/research/paperscool/repos", response_model=PapersCoolReposResponse)
def enrich_papers_with_repo_data(req: PapersCoolReposRequest):
    papers: List[Dict[str, Any]] = []
    if isinstance(req.report, dict):
        papers.extend(_flatten_report_papers(req.report))
    papers.extend(list(req.papers or []))

    if not papers:
        raise HTTPException(status_code=400, detail="report or papers is required")

    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in papers:
        key = f"{item.get('url') or ''}|{item.get('title') or ''}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    selected = deduped[: max(1, int(req.max_items))]
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    repos: List[Dict[str, Any]] = []
    for item in selected:
        repo_url = _extract_repo_url_from_paper(item)
        if not repo_url:
            continue

        row: Dict[str, Any] = {
            "title": item.get("title") or "Untitled",
            "query": item.get("_query") or ", ".join(item.get("matched_queries") or []),
            "paper_url": item.get("url") or item.get("external_url") or "",
            "repo_url": repo_url,
        }
        if req.include_github_api:
            row["github"] = _fetch_github_repo_metadata(repo_url=repo_url, token=token)
        repos.append(row)

    if req.include_github_api:
        repos.sort(
            key=lambda row: int(((row.get("github") or {}).get("stars") or -1)),
            reverse=True,
        )

    return PapersCoolReposResponse(
        total_candidates=len(selected),
        matched_repos=len(repos),
        github_api_used=bool(req.include_github_api),
        repos=repos,
    )


async def _paperscool_analyze_stream(req: PapersCoolAnalyzeRequest):
    report = copy.deepcopy(req.report)
    llm_service = get_llm_service()

    llm_block: Optional[Dict[str, Any]] = None
    if req.run_trends or req.run_insight:
        llm_block = report.get("llm_analysis")
        if not isinstance(llm_block, dict):
            llm_block = {}

        features = list(llm_block.get("features") or [])
        if req.run_trends and "trends" not in features:
            features.append("trends")
        if req.run_insight and "insight" not in features:
            features.append("insight")

        llm_block["enabled"] = True
        llm_block["features"] = features
        llm_block.setdefault("daily_insight", "")
        if req.run_trends:
            llm_block["query_trends"] = []

    if req.run_trends and llm_block is not None:

        queries = list(report.get("queries") or [])
        trend_total = sum(1 for query in queries if query.get("top_items"))
        trend_done = 0
        yield StreamEvent(
            type="progress",
            data={"phase": "trends", "message": "Starting trend analysis", "total": trend_total},
        )
        for query in queries:
            query_name = query.get("normalized_query") or query.get("raw_query") or ""
            top_items = list(query.get("top_items") or [])[
                : max(1, int(req.trend_max_items_per_query))
            ]
            if not top_items:
                continue

            trend_done += 1
            analysis = llm_service.analyze_trends(topic=query_name, papers=top_items)
            llm_block["query_trends"].append({"query": query_name, "analysis": analysis})

            yield StreamEvent(
                type="trend",
                data={
                    "query": query_name,
                    "analysis": analysis,
                    "done": trend_done,
                    "total": trend_total,
                },
            )

        report["llm_analysis"] = llm_block
        yield StreamEvent(type="trend_done", data={"count": trend_done})

    if req.run_insight and llm_block is not None:
        yield StreamEvent(
            type="progress",
            data={"phase": "insight", "message": "Generating daily insight"},
        )
        daily_insight = llm_service.generate_daily_insight(report)
        llm_block["daily_insight"] = daily_insight
        report["llm_analysis"] = llm_block
        yield StreamEvent(type="insight", data={"analysis": daily_insight})

    if req.run_judge:
        judge = PaperJudge(llm_service=llm_service)
        selection = select_judge_candidates(
            report,
            max_items_per_query=req.judge_max_items_per_query,
            n_runs=req.judge_runs,
            token_budget=req.judge_token_budget,
        )
        selected = list(selection.get("selected") or [])
        recommendation_count = {
            "must_read": 0,
            "worth_reading": 0,
            "skim": 0,
            "skip": 0,
        }

        yield StreamEvent(
            type="progress",
            data={
                "phase": "judge",
                "message": "Starting judge scoring",
                "total": len(selected),
                "budget": selection.get("budget") or {},
            },
        )

        for idx, row in enumerate(selected, start=1):
            query_index = int(row.get("query_index") or 0)
            item_index = int(row.get("item_index") or 0)

            queries = list(report.get("queries") or [])
            if query_index >= len(queries):
                continue

            query = queries[query_index]
            query_name = query.get("normalized_query") or query.get("raw_query") or ""
            top_items = list(query.get("top_items") or [])
            if item_index >= len(top_items):
                continue

            item = top_items[item_index]
            if req.judge_runs > 1:
                judgment = judge.judge_with_calibration(
                    paper=item,
                    query=query_name,
                    n_runs=max(1, int(req.judge_runs)),
                )
            else:
                judgment = judge.judge_single(paper=item, query=query_name)

            j_payload = judgment.to_dict()
            item["judge"] = j_payload
            rec = j_payload.get("recommendation")
            if rec in recommendation_count:
                recommendation_count[rec] += 1

            yield StreamEvent(
                type="judge",
                data={
                    "query": query_name,
                    "title": item.get("title") or "Untitled",
                    "judge": j_payload,
                    "done": idx,
                    "total": len(selected),
                },
            )

        for query in report.get("queries") or []:
            top_items = list(query.get("top_items") or [])
            if not top_items:
                continue
            capped_count = min(len(top_items), max(1, int(req.judge_max_items_per_query)))
            capped = top_items[:capped_count]
            capped.sort(
                key=lambda it: float((it.get("judge") or {}).get("overall") or -1), reverse=True
            )
            query["top_items"] = capped + top_items[capped_count:]

        report["judge"] = {
            "enabled": True,
            "max_items_per_query": int(req.judge_max_items_per_query),
            "n_runs": int(max(1, int(req.judge_runs))),
            "recommendation_count": recommendation_count,
            "budget": selection.get("budget") or {},
        }
        try:
            report["judge_registry_ingest"] = persist_judge_scores_to_registry(report)
        except Exception as exc:
            report["judge_registry_ingest"] = {"error": str(exc)}
        yield StreamEvent(type="judge_done", data=report["judge"])

    markdown = render_daily_paper_markdown(report)
    yield StreamEvent(type="result", data={"report": report, "markdown": markdown})


@router.post("/research/paperscool/analyze")
async def analyze_daily_report(req: PapersCoolAnalyzeRequest):
    if not req.run_judge and not req.run_trends and not req.run_insight:
        raise HTTPException(
            status_code=400,
            detail="run_judge or run_trends or run_insight must be true",
        )
    if not isinstance(req.report, dict) or not req.report.get("queries"):
        raise HTTPException(status_code=400, detail="report with queries is required")

    return StreamingResponse(
        wrap_generator(_paperscool_analyze_stream(req)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
