"""Question template framework for dynamic task generation

This module provides the generic base classes and validators for building
question templates. Plugin-specific variables and templates should be
defined in their respective plugin directories.

Example:
    plugins/weather/templates/ - Weather-specific templates and variables
    plugins/stock/templates/ - Stock-specific templates and variables
"""

from .base import (
    QuestionTemplate,
    Variable,
    VariableType,
    Validator,
    ValidationResult,
    GeneratedQuestion,
    CompositeQuestion,
)
from .validators import (
    NumericToleranceValidator,
    ExactMatchValidator,
    BooleanValidator,
    ContainsValidator,
)
from .llm_validator import (
    LLMValidator,
    LLMValidationResult,
    validate_answers_with_llm,
)

__all__ = [
    # Base classes
    "QuestionTemplate",
    "Variable",
    "VariableType",
    "Validator",
    "ValidationResult",
    "GeneratedQuestion",
    "CompositeQuestion",
    # Generic validators
    "NumericToleranceValidator",
    "ExactMatchValidator",
    "BooleanValidator",
    "ContainsValidator",
    # LLM-based validator
    "LLMValidator",
    "LLMValidationResult",
    "validate_answers_with_llm",
]
