"""Variables for Taostats question templates"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from liveweb_arena.core.validators.base import Variable, VariableType


class SubnetMetric(Enum):
    """Metrics that can be queried for a subnet - only those reliably visible on taostats.io"""
    NAME = "name"
    OWNER = "owner"
    EMISSION = "emission"
    REGISTRATION_COST = "registration_cost"
    PRICE = "price"  # Alpha token price
    TEMPO = "tempo"  # Block interval
    GITHUB_REPO = "github_repo"  # GitHub repository URL


@dataclass
class SubnetSpec:
    """Specification for a subnet"""
    subnet_id: int
    display_name: str


@dataclass
class MetricSpec:
    """Specification for a subnet metric"""
    metric: SubnetMetric
    display_name: str
    unit: str = ""
    is_numeric: bool = False
    tolerance_pct: float = 10.0  # Percentage tolerance for numeric validation


# Cache for subnet IDs to avoid repeated network calls
_subnet_ids_cache: Optional[List[int]] = None


def _fetch_active_subnet_ids() -> List[int]:
    """Fetch active subnet IDs from Bittensor network."""
    global _subnet_ids_cache
    if _subnet_ids_cache is not None:
        return _subnet_ids_cache

    try:
        import bittensor as bt
        subtensor = bt.Subtensor(network="finney")
        # Get all subnet netuids (max 128 possible)
        netuids = subtensor.get_subnets()
        # Filter out root network (0) and return as list
        _subnet_ids_cache = [n for n in netuids if n > 0]
        return _subnet_ids_cache
    except Exception:
        # Fallback: use range 1-128 (max possible subnets)
        return list(range(1, 129))


class SubnetVariable(Variable):
    """
    Variable for Bittensor subnet selection.

    Dynamically fetches active subnets from the Bittensor network.
    Bittensor supports up to 128 subnets (netuid 0-127, where 0 is root).
    """

    def __init__(self, subnet_ids: List[int] = None):
        """
        Initialize subnet variable.

        Args:
            subnet_ids: Specific subnet IDs to sample from (if None, fetches from network)
        """
        super().__init__("subnet", VariableType.NUMERIC)
        if subnet_ids:
            self.subnet_ids = subnet_ids
        else:
            # Dynamically fetch active subnets from network
            self.subnet_ids = _fetch_active_subnet_ids()

    def sample(self, rng: random.Random) -> SubnetSpec:
        subnet_id = rng.choice(self.subnet_ids)
        # Vary display format
        formats = [f"subnet {subnet_id}", f"SN{subnet_id}", f"Subnet {subnet_id}"]
        display = rng.choice(formats)
        return SubnetSpec(subnet_id=subnet_id, display_name=display)

    def get_display_value(self, value: SubnetSpec) -> str:
        return value.display_name

    def get_api_value(self, value: SubnetSpec) -> str:
        return str(value.subnet_id)


class MetricVariable(Variable):
    """Variable for subnet metrics - focused on reliable, visible data"""

    METRICS: Dict[SubnetMetric, MetricSpec] = {
        SubnetMetric.NAME: MetricSpec(
            SubnetMetric.NAME, "name", is_numeric=False
        ),
        SubnetMetric.OWNER: MetricSpec(
            SubnetMetric.OWNER, "owner", is_numeric=False
        ),
        SubnetMetric.EMISSION: MetricSpec(
            SubnetMetric.EMISSION, "emission", unit="τ/day", is_numeric=True,
            tolerance_pct=15.0  # Emissions fluctuate
        ),
        SubnetMetric.REGISTRATION_COST: MetricSpec(
            SubnetMetric.REGISTRATION_COST, "registration cost", unit="τ",
            is_numeric=True, tolerance_pct=20.0  # Dynamic pricing
        ),
        SubnetMetric.PRICE: MetricSpec(
            SubnetMetric.PRICE, "alpha price", unit="τ", is_numeric=True,
            tolerance_pct=10.0
        ),
        SubnetMetric.TEMPO: MetricSpec(
            SubnetMetric.TEMPO, "tempo", unit="blocks", is_numeric=True,
            tolerance_pct=0.0  # Tempo is exact, no tolerance needed
        ),
        SubnetMetric.GITHUB_REPO: MetricSpec(
            SubnetMetric.GITHUB_REPO, "GitHub repository", is_numeric=False
        ),
    }

    def __init__(self, allowed_metrics: List[SubnetMetric] = None):
        super().__init__("metric", VariableType.TEXT)
        self.allowed_metrics = allowed_metrics or list(self.METRICS.keys())

    def sample(self, rng: random.Random) -> MetricSpec:
        metric_type = rng.choice(self.allowed_metrics)
        return self.METRICS[metric_type]

    def get_display_value(self, value: MetricSpec) -> str:
        return value.display_name

    def get_api_value(self, value: MetricSpec) -> str:
        return value.metric.value
