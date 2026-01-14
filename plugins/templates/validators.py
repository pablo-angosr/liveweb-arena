"""Answer validators for different validation strategies"""

import re
from typing import Any, Optional, Tuple

from .base import Validator, ValidationResult


class NumericToleranceValidator(Validator):
    """
    Validates numeric answers with tolerance bands.

    Supports:
    - Full score within tight tolerance
    - Partial score within loose tolerance
    - Zero score outside tolerance
    """

    def __init__(
        self,
        full_tolerance: float,
        partial_tolerance: float,
        unit: str = "",
        partial_score: float = 0.5,
    ):
        """
        Initialize numeric validator.

        Args:
            full_tolerance: Tolerance for full score (e.g., 2 for ±2°C)
            partial_tolerance: Tolerance for partial score (e.g., 5 for ±5°C)
            unit: Unit string for display (e.g., "°C", "%", "km/h")
            partial_score: Score to award for partial match (default 0.5)
        """
        self.full_tolerance = full_tolerance
        self.partial_tolerance = partial_tolerance
        self.unit = unit
        self.partial_score = partial_score

    def extract_value(self, answer: str) -> Optional[float]:
        """Extract numeric value from answer string"""
        if not answer:
            return None

        # Patterns to match various numeric formats
        patterns = [
            r"(-?\d+\.?\d*)\s*°?[CF]?",  # Temperature
            r"(-?\d+\.?\d*)\s*%",  # Percentage
            r"(-?\d+\.?\d*)\s*(?:km/?h|mph|m/s)",  # Speed
            r"(-?\d+\.?\d*)\s*(?:mm|cm|inches?)",  # Precipitation
            r"(-?\d+\.?\d*)",  # Plain number
        ]

        for pattern in patterns:
            match = re.search(pattern, answer, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return None

    def validate(self, answer: str, ground_truth: Any) -> ValidationResult:
        """Validate answer against ground truth with tolerance"""
        actual = self.extract_value(answer)

        if actual is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Could not extract numeric value from answer",
            )

        if ground_truth is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=None,
                actual=actual,
                details="Ground truth not available",
            )

        expected = float(ground_truth)
        diff = abs(actual - expected)

        if diff <= self.full_tolerance:
            return ValidationResult(
                score=1.0,
                is_correct=True,
                expected=expected,
                actual=actual,
                details=f"Exact match within ±{self.full_tolerance}{self.unit} (diff: {diff:.1f})",
            )
        elif diff <= self.partial_tolerance:
            return ValidationResult(
                score=self.partial_score,
                is_correct=False,
                expected=expected,
                actual=actual,
                details=f"Partial match within ±{self.partial_tolerance}{self.unit} (diff: {diff:.1f})",
            )
        else:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=expected,
                actual=actual,
                details=f"Outside tolerance ±{self.partial_tolerance}{self.unit} (diff: {diff:.1f})",
            )


class ExactMatchValidator(Validator):
    """
    Validates answers requiring exact string match.

    Supports case-insensitive matching and normalization.
    """

    def __init__(self, case_sensitive: bool = False, normalize: bool = True):
        """
        Initialize exact match validator.

        Args:
            case_sensitive: Whether to do case-sensitive comparison
            normalize: Whether to normalize whitespace
        """
        self.case_sensitive = case_sensitive
        self.normalize = normalize

    def extract_value(self, answer: str) -> Optional[str]:
        """Extract and normalize answer string"""
        if not answer:
            return None

        value = answer.strip()
        if self.normalize:
            value = " ".join(value.split())
        if not self.case_sensitive:
            value = value.lower()

        return value

    def validate(self, answer: str, ground_truth: Any) -> ValidationResult:
        """Validate answer against ground truth with exact match"""
        actual = self.extract_value(answer)
        expected = self.extract_value(str(ground_truth)) if ground_truth else None

        if actual is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Empty or invalid answer",
            )

        if expected is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=None,
                actual=actual,
                details="Ground truth not available",
            )

        is_match = actual == expected
        return ValidationResult(
            score=1.0 if is_match else 0.0,
            is_correct=is_match,
            expected=ground_truth,
            actual=answer,
            details="Exact match" if is_match else "No match",
        )


class BooleanValidator(Validator):
    """
    Validates yes/no or true/false questions.

    Handles various ways of expressing boolean answers.
    """

    # Keywords indicating positive/negative answers
    POSITIVE_KEYWORDS = {
        "yes", "true", "correct", "right", "affirmative",
        "会", "有", "是", "对", "正确",
        "will", "does", "is", "are", "can",
    }
    NEGATIVE_KEYWORDS = {
        "no", "false", "incorrect", "wrong", "negative",
        "不会", "没有", "不是", "不对", "错误", "不",
        "won't", "doesn't", "isn't", "aren't", "can't", "cannot",
    }

    def extract_value(self, answer: str) -> Optional[bool]:
        """Extract boolean value from answer string"""
        if not answer:
            return None

        answer_lower = answer.lower().strip()

        # Check for positive keywords
        for keyword in self.POSITIVE_KEYWORDS:
            if keyword in answer_lower:
                return True

        # Check for negative keywords
        for keyword in self.NEGATIVE_KEYWORDS:
            if keyword in answer_lower:
                return False

        return None

    def validate(self, answer: str, ground_truth: Any) -> ValidationResult:
        """Validate boolean answer"""
        actual = self.extract_value(answer)

        if actual is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Could not determine yes/no from answer",
            )

        expected = bool(ground_truth) if ground_truth is not None else None
        if expected is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=None,
                actual=actual,
                details="Ground truth not available",
            )

        is_correct = actual == expected
        return ValidationResult(
            score=1.0 if is_correct else 0.0,
            is_correct=is_correct,
            expected=expected,
            actual=actual,
            details="Correct" if is_correct else "Incorrect",
        )


class ContainsValidator(Validator):
    """
    Validates that the answer contains expected keywords or patterns.

    Useful for descriptive answers or condition checks.
    """

    def __init__(
        self,
        required_patterns: list = None,
        forbidden_patterns: list = None,
        case_sensitive: bool = False,
    ):
        """
        Initialize contains validator.

        Args:
            required_patterns: Patterns that must appear in answer
            forbidden_patterns: Patterns that must NOT appear
            case_sensitive: Whether pattern matching is case-sensitive
        """
        self.required_patterns = required_patterns or []
        self.forbidden_patterns = forbidden_patterns or []
        self.case_sensitive = case_sensitive

    def extract_value(self, answer: str) -> Optional[str]:
        """Extract normalized answer"""
        if not answer:
            return None
        return answer if self.case_sensitive else answer.lower()

    def validate(self, answer: str, ground_truth: Any) -> ValidationResult:
        """Validate answer contains/excludes expected patterns"""
        actual = self.extract_value(answer)

        if actual is None:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Empty answer",
            )

        # Check required patterns
        missing = []
        for pattern in self.required_patterns:
            check_pattern = pattern if self.case_sensitive else pattern.lower()
            if check_pattern not in actual:
                missing.append(pattern)

        # Check forbidden patterns
        found_forbidden = []
        for pattern in self.forbidden_patterns:
            check_pattern = pattern if self.case_sensitive else pattern.lower()
            if check_pattern in actual:
                found_forbidden.append(pattern)

        # Calculate score
        total_checks = len(self.required_patterns) + len(self.forbidden_patterns)
        if total_checks == 0:
            score = 1.0
        else:
            passed = (
                len(self.required_patterns) - len(missing) +
                len(self.forbidden_patterns) - len(found_forbidden)
            )
            score = passed / total_checks

        is_correct = score >= 1.0
        details_parts = []
        if missing:
            details_parts.append(f"Missing: {missing}")
        if found_forbidden:
            details_parts.append(f"Forbidden found: {found_forbidden}")
        if not details_parts:
            details_parts.append("All patterns matched")

        return ValidationResult(
            score=score,
            is_correct=is_correct,
            expected=ground_truth,
            actual=answer,
            details="; ".join(details_parts),
        )
