"""Scoring logic for WebArena Dynamic evaluations"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import CompositeTask
from ..plugins.base import BasePlugin, ValidationResult


@dataclass
class SubtaskScore:
    """Score for a single subtask"""
    answer_tag: str
    plugin_name: str
    score: float
    is_correct: bool
    expected: Any
    actual: Any
    details: str


@dataclass
class EvaluationResult:
    """Complete evaluation result"""
    task_name: str
    score: float  # 0.0 - 1.0 (aggregated)
    success: bool
    time_taken: float
    subtask_scores: List[SubtaskScore] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class Scorer:
    """
    Scores agent answers against ground truth via plugin validation.

    Each subtask is validated independently via its plugin's validate_answer,
    then scores are aggregated (mean by default).
    """

    def __init__(self, success_threshold: float = 0.8):
        """
        Initialize scorer.

        Args:
            success_threshold: Score threshold for success (default 0.8)
        """
        self._success_threshold = success_threshold

    async def score(
        self,
        task: CompositeTask,
        parsed_answers: Dict[str, Optional[str]],
        plugins: Dict[str, BasePlugin],
    ) -> EvaluationResult:
        """
        Score parsed answers against ground truth.

        Args:
            task: The composite task
            parsed_answers: Parsed answers {"answer1": "...", ...}
            plugins: Plugin instances for validation

        Returns:
            EvaluationResult with per-subtask and aggregate scores
        """
        subtask_scores: List[SubtaskScore] = []

        for subtask in task.subtasks:
            answer_tag = subtask.answer_tag
            answer = parsed_answers.get(answer_tag)

            if answer is None:
                # No answer provided
                subtask_scores.append(SubtaskScore(
                    answer_tag=answer_tag,
                    plugin_name=subtask.plugin_name,
                    score=0.0,
                    is_correct=False,
                    expected=None,
                    actual=None,
                    details="No answer provided",
                ))
                continue

            # Get plugin for validation
            plugin = plugins.get(subtask.plugin_name)
            if plugin is None:
                subtask_scores.append(SubtaskScore(
                    answer_tag=answer_tag,
                    plugin_name=subtask.plugin_name,
                    score=0.0,
                    is_correct=False,
                    expected=None,
                    actual=answer,
                    details=f"Plugin '{subtask.plugin_name}' not found",
                ))
                continue

            # Validate answer
            try:
                result: ValidationResult = await plugin.validate_answer(
                    answer=answer,
                    validation_info=subtask.validation_info,
                )
                subtask_scores.append(SubtaskScore(
                    answer_tag=answer_tag,
                    plugin_name=subtask.plugin_name,
                    score=result.score,
                    is_correct=result.is_correct,
                    expected=result.expected,
                    actual=result.actual,
                    details=result.details,
                ))
            except Exception as e:
                subtask_scores.append(SubtaskScore(
                    answer_tag=answer_tag,
                    plugin_name=subtask.plugin_name,
                    score=0.0,
                    is_correct=False,
                    expected=None,
                    actual=answer,
                    details=f"Validation error: {e}",
                ))

        # Aggregate scores
        if subtask_scores:
            total_score = sum(s.score for s in subtask_scores) / len(subtask_scores)
        else:
            total_score = 0.0

        success = total_score >= self._success_threshold

        return EvaluationResult(
            task_name=f"webarena_dynamic:{len(task.subtasks)}tasks",
            score=total_score,
            success=success,
            time_taken=0.0,  # To be set by caller
            subtask_scores=subtask_scores,
        )
