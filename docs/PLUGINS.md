# Plugin Development Guide

This guide explains how to create new plugins for LiveWeb Arena.

## Plugin Structure

Each plugin has its own directory under `plugins/`:

```
plugins/
├── base.py                 # BasePlugin abstract class
├── templates/              # Shared template framework
│   ├── base.py
│   ├── validators.py
│   └── llm_validator.py
└── your_plugin/            # Your new plugin
    ├── __init__.py
    ├── your_plugin.py      # Main plugin class
    └── templates/          # Plugin-specific templates
        ├── __init__.py
        ├── templates.py    # Question templates
        └── variables.py    # Variable definitions
```

## Step 1: Create Plugin Directory

```bash
mkdir -p plugins/stock/templates
touch plugins/stock/__init__.py
touch plugins/stock/stock.py
touch plugins/stock/templates/__init__.py
```

## Step 2: Implement Plugin Class

```python
# plugins/stock/stock.py

from typing import Any, Dict, List, Type
from plugins.base import BasePlugin, SubTask, ValidationResult
from plugins.templates.base import QuestionTemplate, GeneratedQuestion


class StockPlugin(BasePlugin):
    """Stock market plugin using Yahoo Finance"""

    def __init__(self):
        self._template_instances = {}
        # Initialize templates...

    @property
    def name(self) -> str:
        return "stock"

    @property
    def supported_sites(self) -> List[str]:
        return ["finance.yahoo.com", "google.com/finance"]

    @property
    def description(self) -> str:
        return "Query real-time stock prices and market data"

    @property
    def usage_hint(self) -> str:
        return """## Stock Tool (Yahoo Finance)

**Website**: https://finance.yahoo.com

**URL Patterns**:
- Stock quote: https://finance.yahoo.com/quote/AAPL
- Stock chart: https://finance.yahoo.com/quote/AAPL/chart

**Page Content**:
- Current price displayed prominently
- Price change and percentage
- Market cap, volume, P/E ratio
- Historical chart

**Tips**:
- Look for the large price number at the top
- Green indicates price up, red indicates price down
"""

    async def generate_task(self, seed: int) -> SubTask:
        import random
        rng = random.Random(seed)

        # Sample a stock and question type
        stocks = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        stock = rng.choice(stocks)

        return SubTask(
            plugin_name=self.name,
            intent=f"What is the current stock price of {stock}?",
            validation_info={
                "symbol": stock,
                "metric": "price",
            },
            answer_tag="",  # Will be set by TaskManager
        )

    async def get_ground_truth(self, validation_info: dict) -> Any:
        """Fetch real-time stock price from API"""
        import httpx

        symbol = validation_info["symbol"]

        # Use a free stock API (example)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.example.com/stock/{symbol}"
            )
            data = response.json()
            return data["price"]

    async def validate_answer(
        self, answer: str, validation_info: dict
    ) -> ValidationResult:
        """Validate using template validators"""
        # Implementation...
        pass
```

## Step 3: Define Question Templates

```python
# plugins/stock/templates/templates.py

import random
from typing import Any, Dict
from plugins.templates.base import (
    QuestionTemplate,
    GeneratedQuestion,
    ValidationResult,
)
from plugins.templates.validators import NumericToleranceValidator


class StockPriceTemplate(QuestionTemplate):
    """Template for stock price questions"""

    STOCKS = {
        "AAPL": "Apple Inc.",
        "GOOGL": "Alphabet Inc.",
        "MSFT": "Microsoft Corporation",
        "AMZN": "Amazon.com Inc.",
        "TSLA": "Tesla Inc.",
    }

    QUESTION_PATTERNS = [
        "What is the current stock price of {company} ({symbol})?",
        "How much is {symbol} trading at right now?",
        "What is {company}'s current share price?",
    ]

    def __init__(self):
        super().__init__("stock_price")
        self.register_validator(
            "price",
            NumericToleranceValidator(
                full_tolerance=1.0,      # $1 tolerance for full score
                partial_tolerance=5.0,   # $5 tolerance for partial
                unit="$",
            )
        )

    def generate(self, seed: int) -> GeneratedQuestion:
        rng = random.Random(seed)

        symbol = rng.choice(list(self.STOCKS.keys()))
        company = self.STOCKS[symbol]
        pattern = rng.choice(self.QUESTION_PATTERNS)

        question_text = pattern.format(symbol=symbol, company=company)

        return GeneratedQuestion(
            question_text=question_text,
            start_url=f"https://finance.yahoo.com/quote/{symbol}",
            variables={"symbol": symbol, "company": company},
            validation_info={
                "symbol": symbol,
                "metric": "price",
            },
            template_name=self.name,
        )

    async def get_ground_truth(self, validation_info: Dict[str, Any]) -> Any:
        # Fetch from API...
        pass

    async def validate_answer(
        self, answer: str, validation_info: Dict[str, Any]
    ) -> ValidationResult:
        ground_truth = await self.get_ground_truth(validation_info)
        validator = self._validators["price"]
        return validator.validate(answer, ground_truth)
```

## Step 4: Define Variables

```python
# plugins/stock/templates/variables.py

import random
from dataclasses import dataclass
from typing import List
from plugins.templates.base import Variable, VariableType


@dataclass
class StockSpec:
    """Specification for a stock"""
    symbol: str
    company: str
    exchange: str


class StockVariable(Variable):
    """Variable for stock selection"""

    STOCKS = [
        StockSpec("AAPL", "Apple Inc.", "NASDAQ"),
        StockSpec("GOOGL", "Alphabet Inc.", "NASDAQ"),
        StockSpec("MSFT", "Microsoft Corporation", "NASDAQ"),
        # Add more...
    ]

    def __init__(self, allowed_exchanges: List[str] = None):
        super().__init__(
            name="stock",
            var_type=VariableType.DISCRETE,
            description="Stock symbol selection",
        )
        self.allowed_exchanges = allowed_exchanges

    def sample(self, rng: random.Random) -> StockSpec:
        stocks = self.STOCKS
        if self.allowed_exchanges:
            stocks = [
                s for s in stocks
                if s.exchange in self.allowed_exchanges
            ]
        return rng.choice(stocks)
```

## Step 5: Register Plugin

Add your plugin to the registry in `env.py`:

```python
# env.py

from plugins.stock import StockPlugin

class Actor:
    PLUGINS: Dict[str, Type[BasePlugin]] = {
        "weather": WeatherPlugin,
        "stock": StockPlugin,  # Add this
    }
```

## Step 6: Export from Package

```python
# plugins/stock/__init__.py

from .stock import StockPlugin

__all__ = ["StockPlugin"]
```

## Best Practices

### 1. Ground Truth APIs

- Use reliable, fast APIs for ground truth
- Handle API errors gracefully
- Cache responses when appropriate
- Set reasonable timeouts

### 2. Usage Hints

- Provide clear URL patterns
- Explain page structure
- Give tips for finding information
- Include examples

### 3. Question Templates

- Use natural language variations
- Include different difficulty levels
- Test edge cases
- Ensure reproducibility with seeds

### 4. Validators

- Use appropriate tolerances
- Handle format variations
- Provide clear error messages
- Support partial credit

## Testing Your Plugin

```python
import asyncio
from plugins.stock import StockPlugin

async def test_plugin():
    plugin = StockPlugin()

    # Test task generation
    task = await plugin.generate_task(seed=42)
    print(f"Generated task: {task.intent}")

    # Test ground truth
    ground_truth = await plugin.get_ground_truth(task.validation_info)
    print(f"Ground truth: {ground_truth}")

    # Test validation
    result = await plugin.validate_answer("$150.25", task.validation_info)
    print(f"Score: {result.score}")

asyncio.run(test_plugin())
```
