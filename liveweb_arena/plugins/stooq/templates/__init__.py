"""Stooq question templates"""

from .price import StooqPriceTemplate
from .comparison import StooqComparisonTemplate
from .historical import StooqHistoricalTemplate
from .market_summary import StooqMarketSummaryTemplate
from .currency import StooqCurrencyTemplate
from .week52 import Stooq52WeekTemplate
from .variables import (
    StockVariable, IndexVariable, CurrencyVariable, CommodityVariable,
    PriceMetricVariable, StockSpec, IndexSpec, CurrencySpec, CommoditySpec,
    MetricSpec, PriceMetric, InstrumentType,
    US_STOCKS, INDICES, CURRENCIES, COMMODITIES,
)

__all__ = [
    "StooqPriceTemplate",
    "StooqComparisonTemplate",
    "StooqHistoricalTemplate",
    "StooqMarketSummaryTemplate",
    "StooqCurrencyTemplate",
    "Stooq52WeekTemplate",
    "StockVariable",
    "IndexVariable",
    "CurrencyVariable",
    "CommodityVariable",
    "PriceMetricVariable",
    "StockSpec",
    "IndexSpec",
    "CurrencySpec",
    "CommoditySpec",
    "MetricSpec",
    "PriceMetric",
    "InstrumentType",
    "US_STOCKS",
    "INDICES",
    "CURRENCIES",
    "COMMODITIES",
]
