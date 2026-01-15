"""Subnet ranking query template for Taostats"""

import random
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from liveweb_arena.core.validators.base import (
    QuestionTemplate, GeneratedQuestion, ValidationResult, register_template,
    Variable, VariableType
)


class RankingMetric(Enum):
    """Metrics used for ranking subnets on taostats.io/subnets"""
    MARKET_CAP = "market_cap"  # Default ranking by market cap
    PRICE = "price"  # Alpha price
    EMISSION = "emission"  # Emission percentage


@dataclass
class RankingMetricSpec:
    """Specification for a ranking metric"""
    metric: RankingMetric
    display_name: str
    url_param: str  # URL parameter for sorting on taostats


@dataclass
class SubnetNameSpec:
    """Specification for a subnet identified by name"""
    subnet_id: int
    subnet_name: str


# Well-known subnets with stable names (manually curated for reliability)
# These are popular subnets that are unlikely to be renamed or removed
KNOWN_SUBNETS: Dict[int, str] = {
    1: "Apex",
    2: "Omron",
    3: "Templar",
    4: "Targon",
    5: "Kaito",
    6: "Infinite Games",
    7: "Subvortex",
    8: "Taoshi",
    9: "Pretraining",
    10: "Sturdy",
    11: "Dippy",
    12: "Horde",
    13: "Dataverse",
    14: "Sybil",
    15: "Deval",
    16: "BitAgent",
    17: "404 - Gen",
    18: "Cortex.t",
    19: "Namorai",
    20: "BitMind",
    21: "Any-Any",
    22: "Datura",
    23: "NicheImage",
    24: "Omega",
    25: "Protein Folding",
    26: "Proprietary Trading Network",
    27: "Nodexo",
    32: "ItsAI",
    33: "Ready Player Me",
    37: "Finetuning",
    42: "Masa",
    47: "Condense AI",
    53: "Yogabyte",
    61: "RedPill",
    64: "SocialTensor",
}


class SubnetNameVariable(Variable):
    """Variable for subnet selection by name (for ranking questions)"""

    def __init__(self):
        super().__init__("subnet_name", VariableType.TEXT)

    @property
    def subnet_names(self) -> Dict[int, str]:
        return KNOWN_SUBNETS

    def sample(self, rng: random.Random) -> SubnetNameSpec:
        subnet_id = rng.choice(list(KNOWN_SUBNETS.keys()))
        return SubnetNameSpec(
            subnet_id=subnet_id,
            subnet_name=KNOWN_SUBNETS[subnet_id]
        )

    def get_display_value(self, value: SubnetNameSpec) -> str:
        return value.subnet_name

    def get_api_value(self, value: SubnetNameSpec) -> str:
        return str(value.subnet_id)


class RankingMetricVariable(Variable):
    """Variable for ranking metric selection"""

    METRICS: Dict[RankingMetric, RankingMetricSpec] = {
        RankingMetric.MARKET_CAP: RankingMetricSpec(
            RankingMetric.MARKET_CAP, "market cap", "mc"
        ),
        RankingMetric.PRICE: RankingMetricSpec(
            RankingMetric.PRICE, "price", "price"
        ),
        RankingMetric.EMISSION: RankingMetricSpec(
            RankingMetric.EMISSION, "emission", "emission"
        ),
    }

    def __init__(self, allowed_metrics: List[RankingMetric] = None):
        super().__init__("ranking_metric", VariableType.TEXT)
        self.allowed_metrics = allowed_metrics or list(self.METRICS.keys())

    def sample(self, rng: random.Random) -> RankingMetricSpec:
        metric_type = rng.choice(self.allowed_metrics)
        return self.METRICS[metric_type]

    def get_display_value(self, value: RankingMetricSpec) -> str:
        return value.display_name

    def get_api_value(self, value: RankingMetricSpec) -> str:
        return value.metric.value


@register_template("taostats_subnet_ranking")
class SubnetRankingTemplate(QuestionTemplate):
    """
    Template for querying subnet rankings on Taostats.

    Generates questions like:
    - "What is Apex's current ranking on taostats?"
    - "What rank is Nodexo by market cap?"
    - "Where does ItsAI rank by emission?"

    Note: Rankings are dynamic. Validation allows ±2 rank tolerance.
    """

    PATTERNS: List[str] = [
        "What is subnet {subnet_name}'s ranking by {metric} on taostats.io/subnets?",
        "On the taostats subnets page, what rank is {subnet_name} by {metric}?",
        "Where does the {subnet_name} subnet rank by {metric} on taostats?",
        "Find {subnet_name}'s subnet ranking by {metric} on taostats.io/subnets.",
    ]

    # Patterns without metric specification (default to market cap)
    PATTERNS_DEFAULT: List[str] = [
        "What is the {subnet_name} subnet's ranking on taostats.io/subnets?",
        "On taostats.io/subnets, what rank is the {subnet_name} subnet?",
        "Find the ranking of {subnet_name} subnet on taostats subnets page.",
    ]

    def __init__(self):
        super().__init__("taostats_subnet_ranking")
        self.register_variable(SubnetNameVariable())
        self.register_variable(RankingMetricVariable())
        # Note: No validators registered - using LLM validation for dynamic rankings

    def generate(self, seed: int) -> GeneratedQuestion:
        rng = random.Random(seed)

        subnet: SubnetNameSpec = self._variables["subnet_name"].sample(rng)
        metric: RankingMetricSpec = self._variables["ranking_metric"].sample(rng)

        # 50% chance to use default patterns (no metric specified)
        use_default = rng.random() < 0.5

        if use_default:
            pattern = rng.choice(self.PATTERNS_DEFAULT)
            question_text = pattern.format(subnet_name=subnet.subnet_name)
            # Default to market cap when not specified
            metric = RankingMetricVariable.METRICS[RankingMetric.MARKET_CAP]
        else:
            pattern = rng.choice(self.PATTERNS)
            question_text = pattern.format(
                subnet_name=subnet.subnet_name,
                metric=metric.display_name
            )

        validation_info = {
            "subnet_id": subnet.subnet_id,
            "subnet_name": subnet.subnet_name,
            "ranking_metric": metric.metric.value,
            "url_param": metric.url_param,
        }

        return GeneratedQuestion(
            question_text=question_text,
            start_url="https://taostats.io/subnets",
            variables={"subnet": subnet, "metric": metric},
            validation_info=validation_info,
            template_name=self.name,
        )

    def get_validation_rules(self, validation_info: Dict[str, Any]) -> str:
        return """Task-Specific Rules (Subnet Ranking):
- Score 1.0: Rank matches within ±2 positions
- Score 0.5: Rank matches within ±5 positions
- Score 0.0: Rank differs by more than 5 positions"""

    async def get_ground_truth(self, validation_info: Dict[str, Any]) -> Optional[Any]:
        """
        Get ground truth ranking.

        Returns None to trigger LLM validation, since:
        1. Ranking can be directly read from taostats.io/subnets webpage
        2. Fetching all subnets via API is too slow for real-time validation
        3. LLM validation can compare agent's answer with webpage content
        """
        # Return None to use LLM validation based on webpage content
        return None

    async def validate_answer(
        self, answer: str, validation_info: Dict[str, Any]
    ) -> ValidationResult:
        """Validate ranking answer - delegates to LLM validation"""
        # Rankings are dynamic and best validated by LLM comparing
        # agent's answer with what's shown on taostats.io/subnets
        return ValidationResult(
            score=0.0,
            is_correct=False,
            expected=None,
            actual=answer,
            details="Ranking validation requires LLM to compare with webpage content",
        )
