# LiveWeb Arena

Real-time web interaction evaluation framework for LLM browser agents.

## Features

- **Real-time Evaluation**: Validate against live websites, not static snapshots
- **Dynamic Tasks**: Reproducible task generation with seeds
- **Plugin Architecture**: Extensible task types (weather, stocks, flights, etc.)
- **LLM Validation**: Flexible answer validation with reasoning
- **Agent-driven**: Agents decide which websites to visit

## Quick Start

```python
import asyncio
from liveweb_arena import Actor

async def main():
    actor = Actor(api_key="your-api-key")

    result = await actor.evaluate(
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        seed=42,
        num_subtasks=1,
        plugins=["weather"],
    )

    print(f"Score: {result['score']}")
    print(f"Success: {result['success']}")

    await actor.shutdown()

asyncio.run(main())
```

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Documentation

See [docs/DESIGN.md](docs/DESIGN.md) for detailed architecture and API documentation.

## Current Plugins

- **weather**: Weather queries using wttr.in

## Evaluation Output

```json
{
  "task_name": "liveweb_arena:1tasks",
  "score": 1.0,
  "success": true,
  "time_taken": 45.2,
  "extra": {
    "seed": 42,
    "answer_details": [
      {
        "question": "What is the temperature in Tokyo?",
        "expected": 28.5,
        "actual": "28°C",
        "score": 1.0,
        "reasoning": "Answer matches within tolerance"
      }
    ],
    "conversation": [...]
  }
}
```

## License

MIT
