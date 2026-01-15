# LiveWeb Arena - Design Document

## Overview

LiveWeb Arena is a real-time web interaction evaluation framework for LLM browser agents. Unlike static benchmarks, it evaluates agents against live websites with dynamically generated tasks and real-time API validation.

### Key Features

- **Real-time Evaluation**: Tasks are validated against live website data, not static snapshots
- **Dynamic Task Generation**: Reproducible task generation using seeds
- **Plugin Architecture**: Extensible system for adding new task types (weather, stocks, flights, etc.)
- **LLM-based Validation**: Flexible answer validation using LLM judgment
- **Agent-driven Navigation**: Agents decide which websites to visit based on task hints

## Architecture

```
liveweb-arena/
├── env.py                 # Main Actor class - evaluation entry point
├── core/
│   ├── browser.py         # Playwright browser automation
│   ├── agent_loop.py      # Main agent interaction loop
│   ├── agent_policy.py    # Prompt building and response parsing
│   ├── task_manager.py    # Task generation and plugin coordination
│   ├── models.py          # Data models (SubTask, TrajectoryStep, etc.)
│   └── parser.py          # Answer parsing from agent responses
├── plugins/
│   ├── base.py            # BasePlugin abstract class
│   ├── templates/         # Template framework for question generation
│   │   ├── base.py        # QuestionTemplate, Variable, Validator
│   │   ├── validators.py  # NumericTolerance, ExactMatch, Boolean validators
│   │   └── llm_validator.py  # LLM-based flexible validation
│   └── weather/           # Weather plugin (wttr.in)
│       ├── weather.py     # WeatherPlugin implementation
│       └── templates/     # Weather-specific templates and variables
└── utils/
    └── llm_client.py      # OpenAI-compatible LLM client
```

## Core Components

### 1. Actor (env.py)

The main entry point for evaluations.

```python
from liveweb_arena import Actor

actor = Actor(api_key="your-api-key")
result = await actor.evaluate(
    model="gpt-4",
    base_url="https://api.openai.com/v1",
    seed=42,
    num_subtasks=2,
    plugins=["weather"],
    max_steps=20,
    timeout=300,
)
```

**Evaluation Flow:**
1. Generate composite task from plugins using seed
2. Create isolated browser session
3. Build system prompt with plugin hints
4. Run agent loop (observe → think → act)
5. Parse answers from final response
6. Fetch real-time ground truth from APIs
7. Validate answers using LLM
8. Return scored results with conversation history

### 2. Plugin System

Plugins provide domain-specific task generation and validation.

```python
class BasePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def usage_hint(self) -> str: ...

    @abstractmethod
    async def generate_task(self, seed: int) -> SubTask: ...

    @abstractmethod
    async def get_ground_truth(self, validation_info: dict) -> Any: ...
```

**Current Plugins:**
- `weather`: Weather queries using wttr.in

**Planned Plugins:**
- `stock`: Stock prices and market data
- `flight`: Flight status and pricing
- `paper`: Academic paper searches
- `news`: News article queries

### 3. Template Framework

Flexible question generation with variable sampling.

```python
class QuestionTemplate:
    def register_variable(self, var: Variable): ...
    def register_validator(self, name: str, validator: Validator): ...
    def generate(self, seed: int) -> GeneratedQuestion: ...
    async def validate_answer(self, answer: str, info: dict) -> ValidationResult: ...
```

**Variable Types:**
- Discrete: Categorical choices (cities, metrics)
- Continuous: Numeric ranges (dates, values)
- Dependent: Values depending on other variables

### 4. Agent Loop

Manages the observe-think-act cycle.

```
┌─────────────────────────────────────────────────────┐
│                    Agent Loop                        │
├─────────────────────────────────────────────────────┤
│  1. Start from about:blank                          │
│  2. Get observation (URL, title, accessibility tree)│
│  3. Build prompt with system + observation          │
│  4. Call LLM for thought + action                   │
│  5. Execute action (goto, click, type, scroll, etc.)│
│  6. Record trajectory step                          │
│  7. Repeat until stop action or max_steps           │
└─────────────────────────────────────────────────────┘
```

### 5. Browser Actions

Supported browser actions:

| Action | Parameters | Description |
|--------|------------|-------------|
| `goto` | `{url: string}` | Navigate to URL |
| `click` | `{selector: string}` | Click element |
| `type` | `{selector: string, text: string}` | Type text |
| `scroll` | `{direction: up/down, amount: int}` | Scroll page |
| `wait` | `{seconds: float}` | Wait |
| `stop` | `{final: {answers: {...}}}` | Complete task |

### 6. LLM Validation

Flexible answer validation using LLM judgment.

```python
# Validation prompt includes:
# - Original question
# - Expected answer (ground truth from API)
# - Actual answer (from agent)
# - Instructions for flexible matching

result = await validator.validate(
    question="What is the temperature in Tokyo?",
    expected=28.5,
    actual="The temperature is around 28-29°C",
)
# Returns: score=1.0, reasoning="Answer matches within tolerance"
```

## Data Models

### SubTask
```python
@dataclass
class SubTask:
    plugin_name: str      # Which plugin generated this
    intent: str           # Natural language task description
    validation_info: dict # Parameters for validation
    answer_tag: str       # e.g., "answer1", "answer2"
```

### CompositeTask
```python
@dataclass
class CompositeTask:
    subtasks: List[SubTask]
    combined_intent: str     # Full task description for agent
    plugin_hints: Dict[str, str]  # Usage hints for each plugin
    seed: int
```

### TrajectoryStep
```python
@dataclass
class TrajectoryStep:
    step_num: int
    observation: BrowserObservation
    thought: str
    action: BrowserAction
    action_result: str
```

## Output Format

Evaluation results include:

```json
{
  "task_name": "liveweb_arena:2tasks",
  "score": 0.85,
  "success": true,
  "time_taken": 45.2,
  "extra": {
    "seed": 42,
    "num_subtasks": 2,
    "final_url": "https://wttr.in/Tokyo",
    "usage": {"prompt_tokens": 1500, "completion_tokens": 300},
    "answer_details": [
      {
        "question": "What is the temperature in Tokyo?",
        "answer_tag": "answer1",
        "expected": 28.5,
        "actual": "28°C",
        "score": 1.0,
        "reasoning": "Answer matches expected temperature within tolerance"
      }
    ],
    "conversation": [
      {"role": "system", "content": "...", "metadata": {...}},
      {"role": "environment", "content": "...", "metadata": {...}},
      {"role": "agent", "content": "...", "metadata": {...}}
    ]
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHUTES_API_KEY` | API key for LLM service | Required |

### Evaluation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | str | - | LLM model name |
| `base_url` | str | - | OpenAI-compatible API URL |
| `seed` | int | random | Reproducibility seed |
| `num_subtasks` | int | 2 | Number of sub-tasks (1-4) |
| `plugins` | list | None | Plugin list (None = random) |
| `max_steps` | int | 30 | Max browser interaction steps |
| `timeout` | int | 600 | Total timeout in seconds |
| `temperature` | float | 0.7 | LLM temperature |
| `validation_model` | str | gpt-oss-120b-TEE | Model for answer validation |

## Extending with New Plugins

1. Create plugin directory: `plugins/your_plugin/`
2. Implement plugin class extending `BasePlugin`
3. Create templates in `plugins/your_plugin/templates/`
4. Register plugin in `Actor.PLUGINS`

Example:
```python
class StockPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "stock"

    @property
    def description(self) -> str:
        return "Query real-time stock prices and market data"

    @property
    def usage_hint(self) -> str:
        return """## Stock Tool (Yahoo Finance)

        **Website**: https://finance.yahoo.com
        **URL Pattern**: https://finance.yahoo.com/quote/AAPL
        ...
        """

    async def generate_task(self, seed: int) -> SubTask:
        # Generate stock-related question
        ...

    async def get_ground_truth(self, validation_info: dict) -> Any:
        # Fetch real-time stock price from API
        ...
```

## Roadmap

### Phase 1: Core Framework (Complete)
- [x] Browser automation with Playwright
- [x] Plugin architecture
- [x] Template-based question generation
- [x] LLM-based answer validation
- [x] Conversation history tracking
- [x] Parallel answer validation
- [x] Ground truth fetch with retry mechanism
- [x] Browser session isolation modes (shared/strict)

### Phase 2: Plugin Expansion
- [ ] Stock plugin (Yahoo Finance, Google Finance)
- [ ] Flight plugin (flight status, prices)
- [ ] Paper plugin (arXiv, Google Scholar)
- [ ] News plugin (Google News, Hacker News)

### Phase 3: Advanced Features
- [ ] Multi-step reasoning tasks
- [ ] Cross-plugin composite tasks
- [ ] Human evaluation integration
- [ ] Leaderboard and benchmark suite

### Phase 4: Optimization
- [ ] Parallel evaluation (multiple tasks concurrently)
- [ ] Caching for ground truth
- [ ] Reduced token usage
- [ ] Faster validation models

## License

MIT License
