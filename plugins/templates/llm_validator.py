"""LLM-based answer validator for flexible answer matching"""

from dataclasses import dataclass
from typing import Any, Optional
import json
import re

from .base import ValidationResult


@dataclass
class LLMValidationResult:
    """Result from LLM validation"""
    score: float  # 0.0 - 1.0
    is_correct: bool
    expected: Any
    actual: Any
    reasoning: str  # LLM's reasoning (max 50 words)


VALIDATION_PROMPT = """You are an answer validator. Compare the expected answer with the actual answer and determine if they match.

Question: {question}
Expected Answer: {expected}
Actual Answer: {actual}

Instructions:
1. Determine if the actual answer correctly answers the question based on the expected answer
2. Be flexible with formatting differences (e.g., "28°C" vs "28 degrees" vs "28")
3. For numeric values, allow small differences due to timing (e.g., temperature may vary by 1-2 degrees)
4. If the question asks about multiple days and the actual answer provides individual daily values that match or are close to the expected average, consider it correct
5. Focus on whether the actual answer provides the information requested in the question
6. Output a score from 0.0 to 1.0 (1.0 = fully correct, 0.5 = partially correct, 0.0 = incorrect)
7. Provide a brief reasoning (max 50 words)

Output ONLY a JSON object in this format:
{{"score": <float>, "reasoning": "<brief explanation>"}}
"""


class LLMValidator:
    """
    LLM-based validator for flexible answer matching.

    Uses an LLM to judge if the actual answer matches the expected answer,
    allowing for format variations and minor differences.
    """

    def __init__(self, llm_client):
        """
        Initialize LLM validator.

        Args:
            llm_client: LLM client for making validation calls
        """
        self._llm_client = llm_client

    async def validate(
        self,
        question: str,
        expected: Any,
        actual: Any,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ) -> LLMValidationResult:
        """
        Validate answer using LLM.

        Args:
            question: The original question/task
            expected: Expected answer (ground truth)
            actual: Actual answer from the agent
            model: LLM model to use for validation
            temperature: LLM temperature (0 for deterministic)

        Returns:
            LLMValidationResult with score and reasoning
        """
        # Handle None values
        if actual is None or actual == "":
            return LLMValidationResult(
                score=0.0,
                is_correct=False,
                expected=expected,
                actual=actual,
                reasoning="No answer provided by the agent.",
            )

        if expected is None:
            return LLMValidationResult(
                score=0.0,
                is_correct=False,
                expected=expected,
                actual=actual,
                reasoning="Ground truth not available for validation.",
            )

        # Build validation prompt
        prompt = VALIDATION_PROMPT.format(
            question=question,
            expected=str(expected),
            actual=str(actual),
        )

        try:
            # Call LLM for validation
            response, _ = await self._llm_client.chat(
                system="You are a precise answer validator. Output only valid JSON.",
                user=prompt,
                model=model,
                temperature=temperature,
            )

            # Parse response
            result = self._parse_response(response)

            return LLMValidationResult(
                score=result["score"],
                is_correct=result["score"] >= 0.8,
                expected=expected,
                actual=actual,
                reasoning=result["reasoning"],
            )

        except Exception as e:
            # Fallback to simple string comparison on LLM error
            is_match = str(expected).lower().strip() in str(actual).lower().strip()
            return LLMValidationResult(
                score=1.0 if is_match else 0.0,
                is_correct=is_match,
                expected=expected,
                actual=actual,
                reasoning=f"LLM validation failed ({e}), used string match fallback.",
            )

    def _parse_response(self, response: str) -> dict:
        """Parse LLM response to extract score and reasoning"""
        # Try direct JSON parse
        try:
            data = json.loads(response.strip())
            return self._validate_result(data)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_result(data)
            except json.JSONDecodeError:
                pass

        # Fallback: try to extract score and reasoning manually
        score_match = re.search(r'"?score"?\s*:\s*([0-9.]+)', response)
        reasoning_match = re.search(r'"?reasoning"?\s*:\s*"([^"]+)"', response)

        score = float(score_match.group(1)) if score_match else 0.0
        reasoning = reasoning_match.group(1) if reasoning_match else "Could not parse LLM response"

        return {"score": min(1.0, max(0.0, score)), "reasoning": reasoning}

    def _validate_result(self, data: dict) -> dict:
        """Validate and normalize parsed result"""
        score = float(data.get("score", 0.0))
        score = min(1.0, max(0.0, score))  # Clamp to [0, 1]

        reasoning = str(data.get("reasoning", "No reasoning provided"))
        # Truncate reasoning to ~50 words
        words = reasoning.split()
        if len(words) > 50:
            reasoning = " ".join(words[:50]) + "..."

        return {"score": score, "reasoning": reasoning}


async def validate_answers_with_llm(
    llm_client,
    subtasks: list,
    answers: dict,
    ground_truths: dict,
    model: str = "gpt-4o-mini",
    validation_model: str = None,
) -> list:
    """
    Validate multiple answers using LLM.

    Args:
        llm_client: LLM client for validation calls
        subtasks: List of SubTask objects
        answers: Dict of answer_tag -> answer from agent
        ground_truths: Dict of answer_tag -> ground truth value
        model: Default LLM model (fallback if validation_model not set)
        validation_model: Specific model for validation (recommended: fast model)

    Returns:
        List of validation result dicts with expected, actual, score, reasoning
    """
    validator = LLMValidator(llm_client)
    results = []

    # Use validation_model if provided, otherwise fall back to model
    actual_model = validation_model or model

    for subtask in subtasks:
        tag = subtask.answer_tag
        question = subtask.intent
        expected = ground_truths.get(tag)
        actual = answers.get(tag)

        result = await validator.validate(
            question=question,
            expected=expected,
            actual=actual,
            model=actual_model,
        )

        results.append({
            "question": question,
            "answer_tag": tag,
            "expected": result.expected,
            "actual": result.actual,
            "score": result.score,
            "is_correct": result.is_correct,
            "reasoning": result.reasoning,
        })

    return results
