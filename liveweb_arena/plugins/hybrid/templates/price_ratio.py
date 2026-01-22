"""Cross-site price ratio template - requires both CoinGecko and Stooq"""

import csv
import io
import random
from typing import Any, Dict, Optional

import aiohttp

from liveweb_arena.core.validators.base import (
    QuestionTemplate, GeneratedQuestion, ValidationResult, register_template,
)
from liveweb_arena.core.ground_truth_trigger import (
    UrlPatternTrigger, FetchStrategy, TriggerConfig, GroundTruthResult,
)
from liveweb_arena.plugins.coingecko.api_client import CoinGeckoClient
from .variables import CryptoVariable, StockVariable, CryptoSpec, StockSpec


@register_template("hybrid_price_ratio")
class HybridPriceRatioTemplate(QuestionTemplate):
    """
    Cross-site template requiring data from both CoinGecko and Stooq.

    This template asks questions like:
    - "How many shares of Apple could you buy with 1 Bitcoin?"
    - "If you sold 1 Ethereum, how many shares of Tesla could you afford?"

    This CANNOT be answered from memory because:
    1. Both crypto and stock prices change in real-time
    2. The specific pair combination varies
    3. Requires visiting TWO different websites and doing calculation
    """

    PATTERNS = [
        "How many shares of {stock} could you buy with 1 {crypto}?",
        "If you sold 1 {crypto}, how many shares of {stock} could you afford?",
        "How many {stock} shares equal the value of 1 {crypto}?",
        "With 1 {crypto}, how many {stock} shares could you purchase?",
    ]

    STOOQ_CSV_URL = "https://stooq.com/q/d/l/"

    def __init__(self):
        super().__init__("hybrid_price_ratio")
        self._crypto_var = CryptoVariable()
        self._stock_var = StockVariable()

    def generate(self, seed: int, variant: Optional[int] = None) -> GeneratedQuestion:
        """Generate a cross-site price ratio question."""
        rng = random.Random(seed)

        crypto = self._crypto_var.sample(rng)
        stock = self._stock_var.sample(rng)

        pattern = rng.choice(self.PATTERNS)
        question_text = pattern.format(
            crypto=crypto.name,
            stock=stock.name,
        )

        # Start at CoinGecko (crypto price first, then navigate to Stooq)
        start_url = f"https://www.coingecko.com/en/coins/{crypto.coin_id}"

        validation_info = {
            "crypto_id": crypto.coin_id,
            "crypto_name": crypto.name,
            "crypto_symbol": crypto.symbol,
            "stock_symbol": stock.symbol,
            "stock_ticker": stock.ticker,
            "stock_name": stock.name,
        }

        return GeneratedQuestion(
            question_text=question_text,
            start_url=start_url,
            variables={"crypto": crypto, "stock": stock},
            validation_info=validation_info,
            template_name=self.name,
            expected_steps=10,  # Need to visit 2 sites + do calculation
        )

    def get_validation_rules(self, validation_info: Dict[str, Any]) -> str:
        crypto_name = validation_info.get("crypto_name", "the crypto")
        stock_name = validation_info.get("stock_name", "the stock")

        return f"""Task-Specific Rules (Hybrid - Price Ratio Calculation):
- Calculate how many {stock_name} shares can be bought with 1 {crypto_name}
- Requires getting {crypto_name} price from CoinGecko
- Requires getting {stock_name} price from Stooq
- Score 1.0: Result within 10% tolerance (accounts for price fluctuation during task)
- Score 0.0: Result differs by more than 10%
- Accept integer or decimal answers (e.g., 4, 4.5, "about 4 shares")"""

    async def get_ground_truth(self, validation_info: Dict[str, Any]) -> GroundTruthResult:
        """Fetch prices from both CoinGecko and Stooq, calculate ratio."""
        crypto_id = validation_info.get("crypto_id", "")
        stock_symbol = validation_info.get("stock_symbol", "")

        if not crypto_id or not stock_symbol:
            return GroundTruthResult.fail("Missing crypto_id or stock_symbol")

        # Fetch crypto price from CoinGecko
        crypto_price = await self._get_crypto_price(crypto_id)
        if crypto_price is None:
            return GroundTruthResult.retry("Could not fetch crypto price")

        # Fetch stock price from Stooq
        stock_price = await self._get_stock_price(stock_symbol)
        if stock_price is None:
            return GroundTruthResult.retry("Could not fetch stock price")

        # Calculate ratio
        if stock_price <= 0:
            return GroundTruthResult.fail("Invalid stock price")

        ratio = crypto_price / stock_price

        return GroundTruthResult.ok(
            f"{ratio:.2f} shares (${crypto_price:.2f} / ${stock_price:.2f})"
        )

    async def _get_crypto_price(self, coin_id: str) -> Optional[float]:
        """Get crypto price in USD from CoinGecko."""
        try:
            data = await CoinGeckoClient.get_coin_market_data(coin_id)
            if data and len(data) > 0:
                return data[0].get("current_price")
        except Exception:
            pass
        return None

    async def _get_stock_price(self, symbol: str) -> Optional[float]:
        """Get stock price in USD from Stooq."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"s": symbol, "i": "d"}
                async with session.get(
                    self.STOOQ_CSV_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        return None
                    csv_text = await response.text()

            reader = csv.DictReader(io.StringIO(csv_text))
            rows = list(reader)

            if not rows:
                return None

            latest = rows[-1]
            close = latest.get("Close")
            if close:
                return float(close)
        except Exception:
            pass
        return None

    async def validate_answer(
        self,
        answer: str,
        validation_info: Dict[str, Any]
    ) -> ValidationResult:
        """Validate the price ratio answer."""
        import re

        result = await self.get_ground_truth(validation_info)

        if not result.success:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=None,
                actual=answer,
                details=f"Ground truth unavailable: {result.error}",
            )

        ground_truth = result.value

        # Parse expected ratio from ground truth (format: "X.XX shares ($Y / $Z)")
        exp_match = re.search(r"(\d+\.?\d*)\s*shares", ground_truth)
        if not exp_match:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Could not parse expected ratio",
            )
        expected_ratio = float(exp_match.group(1))

        # Parse answer - look for a number
        answer_clean = answer.replace(",", "")
        num_match = re.search(r"(\d+\.?\d*)", answer_clean)

        if not num_match:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Could not find numeric value in answer",
            )

        actual_ratio = float(num_match.group(1))

        # Calculate percentage difference
        if expected_ratio == 0:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details="Expected ratio is zero",
            )

        diff_pct = abs(actual_ratio - expected_ratio) / expected_ratio * 100

        # 10% tolerance accounts for price fluctuation during task execution
        if diff_pct <= 10:
            return ValidationResult(
                score=1.0,
                is_correct=True,
                expected=ground_truth,
                actual=answer,
                details=f"Within 10% tolerance (diff: {diff_pct:.1f}%)",
            )
        else:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=ground_truth,
                actual=answer,
                details=f"Outside tolerance (diff: {diff_pct:.1f}%)",
            )

    def get_ground_truth_trigger(
        self,
        validation_info: Dict[str, Any]
    ) -> TriggerConfig:
        """
        Trigger ground truth fetch when agent visits Stooq.

        Since this is a cross-site query, we trigger on the second site
        (Stooq) which should be visited after getting the crypto price.
        """
        stock_symbol = validation_info.get("stock_symbol", "")
        trigger = UrlPatternTrigger(
            domains=["stooq.com"],
            url_contains=stock_symbol if stock_symbol else None,
        )
        return TriggerConfig(trigger=trigger, strategy=FetchStrategy.FIRST)
