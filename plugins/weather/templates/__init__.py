"""Weather-specific question templates"""

from plugins.weather.templates.templates import (
    LocationNameWeatherTemplate,
    MultiDayWeatherTemplate,
)
from plugins.weather.templates.variables import (
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
