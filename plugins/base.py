"""Base plugin interface and data structures"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ValidationResult:
    """Result of answer validation against ground truth"""
    score: float  # 0.0 - 1.0
    is_correct: bool
    expected: Any
    actual: Any
    details: str


@dataclass
class SubTask:
    """A single sub-task within a composite task"""
    plugin_name: str
    intent: str
    validation_info: dict
    answer_tag: str  # "answer1"..."answer4"
    # Note: start_url removed - Agent should decide which URL to visit


class BasePlugin(ABC):
    """
    Base class for all website plugins.

    Each plugin is responsible for:
    1. Providing description and usage hints for the Agent
    2. generate_task(): Generate a sub-task with deterministic seed
    3. validate_answer(): Validate answer against real-time API ground truth
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name (e.g., 'weather', 'stock')"""
        pass

    @property
    @abstractmethod
    def supported_sites(self) -> List[str]:
        """List of supported website domains"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Short description of what this plugin provides.
        Used in system prompt to help Agent understand available tools.
        """
        pass

    @property
    @abstractmethod
    def usage_hint(self) -> str:
        """
        Detailed usage instructions for the Agent.
        Should include:
        - Website URL patterns
        - How to navigate and find information
        - Data format on the website
        """
        pass

    @abstractmethod
    async def generate_task(self, seed: int) -> SubTask:
        """
        Generate a sub-task deterministically based on seed.

        Args:
            seed: Random seed for deterministic generation

        Returns:
            SubTask with intent and validation_info
            Note: Does NOT include start_url - Agent decides navigation
        """
        pass

    @abstractmethod
    async def validate_answer(
        self, answer: str, validation_info: dict
    ) -> ValidationResult:
        """
        Validate answer against real-time API ground truth.

        Args:
            answer: The answer string from the agent
            validation_info: Parameters for validation (from SubTask)

        Returns:
            ValidationResult with score and details
        """
        pass

    @abstractmethod
    async def get_ground_truth(self, validation_info: dict) -> Any:
        """
        Get ground truth value for LLM-based validation.

        Args:
            validation_info: Parameters for fetching ground truth (from SubTask)

        Returns:
            Ground truth value (type depends on question type)
        """
        pass
