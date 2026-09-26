"""Regression coverage for false positive LLM judgments of empty answers."""
from unittest.mock import Mock

import pytest

from core.config import load_settings
from evaluation import metrics


@pytest.mark.parametrize("prediction", ["", " \t\r\n\u2003"])
def test_empty_answer_is_incorrect_without_calling_llm(tmp_path, monkeypatch, prediction):
    build = Mock(side_effect=AssertionError("Empty answers must not reach the LLM"))
    monkeypatch.setattr(metrics, "build_llm", build)

    verdict = metrics._judge_answer(
        load_settings(tmp_path), "What categories?", "Information Retrieval", prediction,
    )

    assert verdict.correct is False
    assert verdict.score == 1
    build.assert_not_called()


def test_nonempty_answer_preserves_llm_verdict(tmp_path, monkeypatch):
    expected = metrics.JudgeVerdict(score=3, correct=False, reasoning="Incomplete answer.")
    judge = Mock()
    judge.invoke.return_value = expected
    llm = Mock()
    llm.with_structured_output.return_value = judge
    monkeypatch.setattr(metrics, "build_llm", Mock(return_value=llm))

    verdict = metrics._judge_answer(
        load_settings(tmp_path), "What categories?", "Information Retrieval, NLP", "NLP",
    )

    assert verdict == expected
    judge.invoke.assert_called_once()
