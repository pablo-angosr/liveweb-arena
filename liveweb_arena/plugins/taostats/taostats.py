"""Taostats plugin for Bittensor network data queries"""

import random
from typing import Dict, List, Type

from liveweb_arena.plugins.base import BasePlugin, SubTask, ValidationResult
from liveweb_arena.core.validators.base import QuestionTemplate, GeneratedQuestion, get_registered_templates

# Import templates to trigger registration
from . import templates as _  # noqa: F401


class TaostatsPlugin(BasePlugin):
    """
    Plugin for querying Bittensor network data from taostats.io.

    Taostats is a blockchain explorer and analytics platform for Bittensor,
    providing subnet data, validator info, and network statistics.

    Key pages:
    - /subnets - List of all subnets
    - /subnets/{id} - Subnet details
    - /validators - Validator list and stats
    """

    def __init__(self, templates: List[str] = None):
        self._template_instances: Dict[str, QuestionTemplate] = {}

        # Get taostats templates from global registry
        registered = get_registered_templates()
        taostats_templates = {
            k: v for k, v in registered.items()
            if k.startswith("taostats_")
        }

        template_names = templates or list(taostats_templates.keys())
        for name in template_names:
            if name in taostats_templates:
                self._template_instances[name] = taostats_templates[name]()

    @property
    def name(self) -> str:
        return "taostats"

    @property
    def supported_sites(self) -> List[str]:
        return ["taostats.io"]

    @property
    def description(self) -> str:
        return "Query Bittensor network data including subnets, validators, and network statistics"

    @property
    def usage_hint(self) -> str:
        return """## Taostats (taostats.io)

**Website**: https://taostats.io

**Main Pages**:
- /subnets - Complete list of all Bittensor subnets with key metrics
- /subnets/{id} - Detailed information for a specific subnet
- /validators - List of validators with stake and performance data

**Subnet Page Content**:
Each subnet page shows:
- Name and description
- Owner address
- Registration cost (in TAO)
- Number of validators and miners
- Emission rate
- Tempo and other parameters

**Tips**:
- Subnet IDs are numeric (0 = root network, 1+ = application subnets)
- TAO amounts shown with τ symbol
- Look for data tables and statistics cards on the page
"""

    async def generate_task(self, seed: int) -> SubTask:
        """Generate a Taostats query task"""
        rng = random.Random(seed)

        if not self._template_instances:
            raise ValueError("No templates available")

        template_name = rng.choice(list(self._template_instances.keys()))
        template = self._template_instances[template_name]

        question: GeneratedQuestion = template.generate(seed)

        return SubTask(
            plugin_name=self.name,
            intent=question.question_text,
            validation_info={
                "template_name": template_name,
                **question.validation_info,
            },
            answer_tag="",
        )

    async def validate_answer(
        self, answer: str, validation_info: dict
    ) -> ValidationResult:
        """Validate answer - uses LLM validation for Taostats"""
        template_name = validation_info.get("template_name")
        template = self._template_instances.get(template_name)

        if template is None:
            template = list(self._template_instances.values())[0]

        result = await template.validate_answer(answer, validation_info)

        return ValidationResult(
            score=result.score,
            is_correct=result.is_correct,
            expected=result.expected,
            actual=result.actual,
            details=result.details,
        )

    async def get_ground_truth(self, validation_info: dict):
        """Get ground truth - returns None for LLM validation"""
        template_name = validation_info.get("template_name")
        template = self._template_instances.get(template_name)

        if template is None:
            return None

        return await template.get_ground_truth(validation_info)

    def get_validation_rules(self, validation_info: dict) -> str:
        """Get validation rules from template"""
        template_name = validation_info.get("template_name")
        template = self._template_instances.get(template_name)

        if template is None:
            return ""

        return template.get_validation_rules(validation_info)
