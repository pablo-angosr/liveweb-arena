# LiveWeb Arena API Reference

## Actor

Main class for running evaluations.

### Constructor

```python
Actor(api_key: str = None)
```

**Parameters:**
- `api_key`: API key for LLM service. Falls back to `CHUTES_API_KEY` environment variable.

### Methods

#### evaluate()

```python
async def evaluate(
    model: str,
    base_url: str,
    api_key: Optional[str] = None,
    seed: Optional[int] = None,
    num_subtasks: int = 2,
    plugins: Optional[List[str]] = None,
    max_steps: int = 30,
    timeout: int = 600,
    temperature: float = 0.7,
    max_concurrency: int = 2,
    validation_model: Optional[str] = None,
) -> dict
```

Run a single evaluation.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | str | required | LLM model name for the agent |
| `base_url` | str | required | OpenAI-compatible API base URL |
| `api_key` | str | None | Override API key for this evaluation |
| `seed` | int | random | Task generation seed for reproducibility |
| `num_subtasks` | int | 2 | Number of sub-tasks (1-4) |
| `plugins` | list | None | Plugin list; None = random selection |
| `max_steps` | int | 30 | Maximum browser interaction steps |
| `timeout` | int | 600 | Total timeout in seconds |
| `temperature` | float | 0.7 | LLM temperature |
| `max_concurrency` | int | 2 | Container-local concurrency limit |
| `validation_model` | str | gpt-oss-120b-TEE | Model for answer validation |

**Returns:**
```python
{
    "task_name": str,        # e.g., "liveweb_arena:2tasks"
    "score": float,          # 0.0 - 1.0
    "success": bool,         # True if score >= 0.8
    "time_taken": float,     # Seconds
    "extra": {
        "seed": int,
        "num_subtasks": int,
        "final_url": str,
        "output_format": str,
        "json_repair_count": int,
        "usage": {
            "prompt_tokens": int,
            "completion_tokens": int,
            "total_tokens": int,
        },
        "answer_details": List[AnswerDetail],
        "conversation": List[ConversationTurn],
    },
    "error": str,            # Only if error occurred
    "error_trace": str,      # Only if error occurred
}
```

#### shutdown()

```python
async def shutdown()
```

Shutdown browser and cleanup resources.

---

## Answer Detail

Each answer validation result.

```python
{
    "question": str,      # Original question
    "answer_tag": str,    # e.g., "answer1"
    "expected": Any,      # Ground truth from API
    "actual": Any,        # Answer from agent
    "score": float,       # 0.0 - 1.0
    "is_correct": bool,   # True if score >= 0.8
    "reasoning": str,     # LLM's reasoning (max 50 words)
}
```

---

## Conversation Turn

Each turn in the conversation history.

### System Turn
```python
{
    "role": "system",
    "content": str,       # Task description
    "metadata": {
        "type": "task_description",
        "num_subtasks": int,
    }
}
```

### Environment Turn
```python
{
    "role": "environment",
    "content": str,       # URL + Title + Accessibility Tree
    "metadata": {
        "type": "observation",
        "step": int,
        "url": str,
    }
}
```

### Agent Turn
```python
{
    "role": "agent",
    "content": str,       # Thought + Action
    "metadata": {
        "type": "action",
        "step": int,
        "action_type": str,
        "action_result": str,
    }
}
```

---

## Plugin Interface

Base class for plugins.

```python
class BasePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier (e.g., 'weather')"""

    @property
    @abstractmethod
    def supported_sites(self) -> List[str]:
        """List of supported website domains"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description for system prompt"""

    @property
    @abstractmethod
    def usage_hint(self) -> str:
        """Detailed usage instructions for agent"""

    @abstractmethod
    async def generate_task(self, seed: int) -> SubTask:
        """Generate a task using the given seed"""

    @abstractmethod
    async def validate_answer(
        self, answer: str, validation_info: dict
    ) -> ValidationResult:
        """Validate answer against ground truth"""

    @abstractmethod
    async def get_ground_truth(self, validation_info: dict) -> Any:
        """Get ground truth value from API"""
```

---

## SubTask

A single task within a composite task.

```python
@dataclass
class SubTask:
    plugin_name: str      # Which plugin generated this
    intent: str           # Natural language description
    validation_info: dict # Parameters for validation
    answer_tag: str       # Answer identifier
```

---

## Browser Actions

Supported actions the agent can take.

| Action | Parameters | Example |
|--------|------------|---------|
| `goto` | `{url: string}` | `{"action": "goto", "url": "https://wttr.in/Tokyo"}` |
| `click` | `{selector: string}` | `{"action": "click", "selector": "#search-btn"}` |
| `type` | `{selector: string, text: string}` | `{"action": "type", "selector": "#input", "text": "hello"}` |
| `scroll` | `{direction: string, amount: int}` | `{"action": "scroll", "direction": "down", "amount": 500}` |
| `wait` | `{seconds: float}` | `{"action": "wait", "seconds": 1.5}` |
| `stop` | `{final: {answers: {...}}}` | `{"action": "stop", "final": {"answers": {"answer1": "28°C"}}}` |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CHUTES_API_KEY` | Yes | API key for LLM service |
