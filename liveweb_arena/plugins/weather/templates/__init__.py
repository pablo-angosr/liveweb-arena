"""Weather-specific question templates"""

from .templates import (
    LocationNameWeatherTemplate,
    MultiDayWeatherTemplate,
)
from .variables import (
    LocationVariable,
    DateVariable,
    WeatherMetricVariable,
    LocationType,
    DateType,
    MetricType,
    LocationSpec,
    DateSpec,
    MetricSpec,
)

__all__ = [
    "LocationNameWeatherTemplate",
    "MultiDayWeatherTemplate",
    "LocationVariable",
    "DateVariable",
    "WeatherMetricVariable",
    "LocationType",
    "DateType",
    "MetricType",
    "LocationSpec",
    "DateSpec",
    "MetricSpec",
]
