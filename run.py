#!/usr/bin/env python3
"""
LiveWeb Arena - Standalone Evaluation Script

Usage:
    python run.py [options]

Examples:
    # Basic evaluation
    python run.py --model "deepseek-ai/DeepSeek-V3" --seed 42

    # With custom settings
    python run.py --model "gpt-4" --base-url "https://api.openai.com/v1" --num-tasks 2
"""

import argparse
import asyncio
import json
import os
import sys

from liveweb_arena.env import Actor


async def main():
    parser = argparse.ArgumentParser(
        description="LiveWeb Arena - Real-time web evaluation for LLM browser agents"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="zai-org/GLM-4.7-TEE",
        help="LLM model name (default: zai-org/GLM-4.7-TEE)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="https://llm.chutes.ai/v1",
        help="OpenAI-compatible API base URL (default: https://llm.chutes.ai/v1)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key (default: from CHUTES_API_KEY env var)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: random)",
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=1,
        help="Number of sub-tasks (1-4, default: 1)",
    )
    parser.add_argument(
        "--plugins",
        type=str,
        nargs="+",
        default=["weather"],
        help="Plugins to use (default: weather)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum browser interaction steps (default: 20)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Total timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="LLM temperature (default: 0.7)",
    )
    parser.add_argument(
        "--validation-model",
        type=str,
        default="openai/gpt-oss-120b-TEE",
        help="Model for answer validation (default: openai/gpt-oss-120b-TEE)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (default: print to stdout)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output",
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("CHUTES_API_KEY")
    if not api_key:
        print("Error: API key required. Set CHUTES_API_KEY or use --api-key")
        sys.exit(1)

    if args.verbose:
        print(f"Model: {args.model}")
        print(f"Base URL: {args.base_url}")
        print(f"Seed: {args.seed or 'random'}")
        print(f"Tasks: {args.num_tasks}")
        print(f"Plugins: {args.plugins}")
        print()

    # Initialize actor
    actor = Actor(api_key=api_key)

    try:
        print("Starting evaluation...")
        print("-" * 50)

        result = await actor.evaluate(
            model=args.model,
            base_url=args.base_url,
            seed=args.seed,
            num_subtasks=args.num_tasks,
            plugins=args.plugins,
            max_steps=args.max_steps,
            timeout=args.timeout,
            temperature=args.temperature,
            validation_model=args.validation_model,
        )

        # Print results
        print()
        print("=" * 50)
        print("EVALUATION RESULT")
        print("=" * 50)
        print(f"Task: {result['task_name']}")
        print(f"Score: {result['score']:.2f}")
        print(f"Success: {result['success']}")
        print(f"Time: {result['time_taken']:.2f}s")

        if result.get("error"):
            print(f"Error: {result['error']}")

        # Print answer details
        extra = result.get("extra", {})
        answer_details = extra.get("answer_details", [])
        if answer_details:
            print()
            print("--- Answer Details ---")
            for detail in answer_details:
                print(f"\nQuestion: {detail['question']}")
                print(f"Expected: {detail['expected']}")
                print(f"Actual: {detail['actual']}")
                print(f"Score: {detail['score']:.2f}")
                print(f"Reasoning: {detail['reasoning']}")

        # Print usage
        usage = extra.get("usage")
        if usage:
            print()
            print("--- Token Usage ---")
            print(f"Prompt: {usage.get('prompt_tokens', 0)}")
            print(f"Completion: {usage.get('completion_tokens', 0)}")
            print(f"Total: {usage.get('total_tokens', 0)}")

        # Save to file if requested
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {args.output}")

        # Return exit code based on success
        return 0 if result["success"] else 1

    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
        return 130

    except Exception as e:
        import traceback
        print(f"\nError: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

    finally:
        await actor.shutdown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
