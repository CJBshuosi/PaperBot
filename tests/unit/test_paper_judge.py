import json

from paperbot.application.workflows.analysis.paper_judge import PaperJudge


class _FakeLLMService:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, **kwargs):
        return json.dumps(self.payload)

    def describe_task_provider(self, task_type="default"):
        return {"provider_name": "fake", "model_name": "judge-model", "cost_tier": 2}


def test_paper_judge_single_parses_scores_and_overall():
    payload = {
        "relevance": {"score": 5, "rationale": "direct"},
        "novelty": {"score": 4, "rationale": "new"},
        "rigor": {"score": 4, "rationale": "solid"},
        "impact": {"score": 3, "rationale": "good"},
        "clarity": {"score": 5, "rationale": "clear"},
        "overall": 4.2,
        "one_line_summary": "strong paper",
        "recommendation": "must_read",
    }
    judge = PaperJudge(llm_service=_FakeLLMService(payload))

    result = judge.judge_single(paper={"title": "x", "snippet": "y"}, query="icl compression")

    assert result.relevance.score == 5
    assert result.overall == 4.2
    assert result.recommendation == "must_read"
    assert result.judge_model == "judge-model"
    assert result.evidence_quotes == []


def test_paper_judge_parses_evidence_quotes():
    payload = {
        "relevance": {"score": 4, "rationale": "related"},
        "novelty": {"score": 3, "rationale": "ok"},
        "rigor": {"score": 4, "rationale": "solid"},
        "impact": {"score": 3, "rationale": "moderate"},
        "clarity": {"score": 4, "rationale": "clear"},
        "overall": 3.6,
        "one_line_summary": "decent paper",
        "recommendation": "worth_reading",
        "evidence_quotes": [
            {"text": "We propose a novel method", "source_url": "https://arxiv.org/abs/1234", "page_hint": "Section 3"},
            {"text": "Results show 20% improvement", "source_url": "", "page_hint": "Table 2"},
        ],
    }
    judge = PaperJudge(llm_service=_FakeLLMService(payload))
    result = judge.judge_single(paper={"title": "x", "snippet": "y"}, query="methods")

    assert len(result.evidence_quotes) == 2
    assert result.evidence_quotes[0]["text"] == "We propose a novel method"
    assert result.evidence_quotes[0]["source_url"] == "https://arxiv.org/abs/1234"
    assert result.evidence_quotes[1]["page_hint"] == "Table 2"

    d = result.to_dict()
    assert "evidence_quotes" in d
    assert len(d["evidence_quotes"]) == 2


def test_paper_judge_evidence_quotes_defaults_empty_on_missing():
    payload = {
        "relevance": {"score": 3, "rationale": "ok"},
        "novelty": {"score": 3, "rationale": "ok"},
        "rigor": {"score": 3, "rationale": "ok"},
        "impact": {"score": 3, "rationale": "ok"},
        "clarity": {"score": 3, "rationale": "ok"},
        "overall": 3.0,
        "one_line_summary": "average",
        "recommendation": "skim",
    }
    judge = PaperJudge(llm_service=_FakeLLMService(payload))
    result = judge.judge_single(paper={"title": "x", "snippet": "y"}, query="q")

    assert result.evidence_quotes == []
    assert result.to_dict()["evidence_quotes"] == []


def test_paper_judge_evidence_quotes_skips_invalid_entries():
    payload = {
        "relevance": {"score": 3, "rationale": "ok"},
        "novelty": {"score": 3, "rationale": "ok"},
        "rigor": {"score": 3, "rationale": "ok"},
        "impact": {"score": 3, "rationale": "ok"},
        "clarity": {"score": 3, "rationale": "ok"},
        "overall": 3.0,
        "one_line_summary": "test",
        "recommendation": "skim",
        "evidence_quotes": [
            {"text": "valid quote", "source_url": "", "page_hint": ""},
            "not a dict",
            {"text": "", "source_url": "url"},
            {"no_text_key": "value"},
        ],
    }
    judge = PaperJudge(llm_service=_FakeLLMService(payload))
    result = judge.judge_single(paper={"title": "x", "snippet": "y"}, query="q")

    assert len(result.evidence_quotes) == 1
    assert result.evidence_quotes[0]["text"] == "valid quote"


def test_paper_judge_calibration_uses_median():
    class _SwitchingLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, **kwargs):
            self.calls += 1
            score = 3 if self.calls == 1 else (5 if self.calls == 2 else 4)
            payload = {
                "relevance": {"score": score, "rationale": ""},
                "novelty": {"score": 4, "rationale": ""},
                "rigor": {"score": 4, "rationale": ""},
                "impact": {"score": 4, "rationale": ""},
                "clarity": {"score": 4, "rationale": ""},
                "one_line_summary": "x",
                "recommendation": "worth_reading",
            }
            return json.dumps(payload)

        def describe_task_provider(self, task_type="default"):
            return {"provider_name": "fake", "model_name": "judge-model", "cost_tier": 1}

    judge = PaperJudge(llm_service=_SwitchingLLM())
    result = judge.judge_with_calibration(paper={"title": "x", "snippet": "y"}, query="icl", n_runs=3)

    assert result.relevance.score == 4
    assert result.recommendation in {"must_read", "worth_reading", "skim", "skip"}
