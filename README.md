# LiveWeb Arena

Real-time web interaction evaluation framework for LLM browser agents.

## Features

- **Real-time Evaluation**: Validate against live websites, not static snapshots
- **Reproducible Tasks**: Deterministic task generation with seeds and task IDs
- **Plugin Architecture**: Extensible task types (weather, stocks, crypto, etc.)
- **Ground Truth Validation**: Fetch real-time data from APIs for accurate scoring
- **Agent-driven Navigation**: Agents decide which websites to visit

## Quick Start

### Installation

```bash
# Install as editable package
pip install -e .

# Install Playwright browsers
playwright install chromium
```

### Run Evaluation

**Recommended: Use `eval.py` for all evaluations.**

```bash
# Basic evaluation with random task
python eval.py --model "gpt-4" --base-url "https://api.openai.com/v1" --api-key "sk-xxx"

# Reproducible evaluation with task_id
python eval.py --task-id 100001 --seed 42

# Specific template evaluation
python eval.py --templates weather/current_weather --verbose

# Show all available templates
python eval.py --show-registry
```

## eval.py Usage

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | LLM model name | `zai-org/GLM-4.7-TEE` |
| `--base-url` | OpenAI-compatible API URL | `https://llm.chutes.ai/v1` |
| `--api-key` | API key (or set `CHUTES_API_KEY`) | - |
| `--seed` | Random seed for reproducibility | random |
| `--task-id` | Deterministic task ID (1 to max) | - |
| `--num-tasks` | Number of sub-tasks (1-4) | 1 |
| `--templates` | Specific templates to use | random |
| `--verbose` | Print detailed output | false |

### Advanced Options

| Option | Description | Default |
|--------|-------------|---------|
| `--max-steps` | Maximum browser steps | auto |
| `--timeout` | Total timeout (seconds) | 3600 |
| `--temperature` | LLM temperature | 0.0 |
| `--validation-model` | Model for answer validation | `openai/gpt-oss-120b-TEE` |
| `--output` | Output file path | `eval/timestamp.json` |

### Examples

```bash
# 1. Random single task
python eval.py --seed 42 --verbose

# 2. Specific template with variant
python eval.py --templates stooq/stooq_price/0 --seed 100 --verbose

# 3. Multi-task evaluation
python eval.py --num-tasks 3 --templates weather/current_weather coingecko/coingecko_price --verbose

# 4. Deterministic task by ID (reproducible across runs)
python eval.py --task-id 300001 --seed 12345 --verbose

# 5. View task registry
python eval.py --show-registry
```

### Template Format

Templates are specified as `plugin/template_name` or `plugin/template_name/variant`:

```bash
--templates weather/current_weather          # Random variant
--templates stooq/stooq_price/0              # Specific variant (0-indexed)
--templates weather/multi_day coingecko/coingecko_rank  # Multiple templates
```

## Available Plugins & Templates

### Weather (wttr.in)
| Template | Description |
|----------|-------------|
| `weather/location_name` | Location-based weather queries |
| `weather/current_weather` | Current temperature, humidity, wind |
| `weather/multi_day` | Multi-day forecast comparison |
| `weather/time_of_day` | Morning/afternoon/evening weather |
| `weather/astronomy` | Sunrise, sunset, moon phase |
| `weather/weather_comparison` | Compare weather between cities |

### Stooq (stooq.com) - Financial Data
| Template | Description |
|----------|-------------|
| `stooq/stooq_price` | Stock/index current price |
| `stooq/stooq_comparison` | Compare multiple instruments |
| `stooq/stooq_ranking` | Rank instruments by metric |
| `stooq/stooq_sector_analysis` | Sector performance analysis |
| `stooq/stooq_52week` | 52-week high/low queries |
| `stooq/stooq_currency` | Currency exchange rates |

### CoinGecko (coingecko.com) - Cryptocurrency
| Template | Description |
|----------|-------------|
| `coingecko/coingecko_price` | Crypto price, market cap |
| `coingecko/coingecko_volume` | 24h trading volume |
| `coingecko/coingecko_comparison` | Compare two cryptos |
| `coingecko/coingecko_rank` | Market cap ranking |
| `coingecko/coingecko_top_movers` | Top gainers/losers |
| `coingecko/coingecko_supply` | Circulating/total supply |
| `coingecko/coingecko_ath` | All-time high queries |
| `coingecko/coingecko_performance` | Performance metrics |

### Taostats (taostats.io) - Bittensor Network
| Template | Description |
|----------|-------------|
| `taostats/taostats_subnet_info` | Subnet details |
| `taostats/taostats_network` | Network statistics |
| `taostats/taostats_price` | TAO token price |

## Task ID System

Task IDs provide fully deterministic, reproducible evaluations:

```
task_id = combo_id * 10000 + variation_seed

Example: task_id = 300001
  - combo_id = 30 (specific template combination)
  - variation_seed = 1 (question variation within that combo)
```

Use `--show-registry` to see all available combinations and their IDs.

## Output Format

Results are saved as JSON:

```json
{
  "task_name": "liveweb_arena:1tasks",
  "score": 1.0,
  "success": true,
  "time_taken": 45.2,
  "extra": {
    "seed": 42,
    "task_id": 100001,
    "answer_details": [
      {
        "question": "What is the current temperature in Tokyo?",
        "expected": "15°C",
        "actual": "15 degrees Celsius",
        "score": 1.0,
        "reasoning": "Answer matches within tolerance"
      }
    ],
    "usage": {
      "prompt_tokens": 1234,
      "completion_tokens": 567,
      "total_tokens": 1801
    }
  }
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CHUTES_API_KEY` | Default API key for LLM calls |
| `COINGECKO_API_KEY` | CoinGecko Pro API key (optional) |
| `TMDB_API_KEY` | TMDB API key for movie templates |

## Architecture

```
liveweb_arena/
├── core/
│   ├── actor.py           # Main evaluation orchestrator
│   ├── task_registry.py   # Task ID management
│   ├── ground_truth_trigger.py  # Ground truth fetching
│   └── validators/        # Answer validation
├── plugins/
│   ├── base.py            # Plugin interface
│   ├── weather/           # Weather plugin
│   ├── stooq/             # Financial data plugin
│   ├── coingecko/         # Cryptocurrency plugin
│   ├── taostats/          # Bittensor plugin
│   └── tmdb/              # Movie database plugin
└── browser/               # Playwright browser control
```

## License

MIT
