"""LiveWeb Arena - Main evaluation entry point"""

import asyncio
import os
import random
import time
from typing import Dict, List, Optional, Type

from .core.browser import BrowserEngine
from .core.task_manager import TaskManager
from .core.agent_policy import AgentPolicy
from .core.agent_loop import AgentLoop
from .core.parser import AnswerParser
from .plugins.base import BasePlugin
from .plugins.weather import WeatherPlugin
from .plugins.templates.llm_validator import validate_answers_with_llm
from .utils.llm_client import LLMClient


class Actor:
    """
    LiveWeb Arena evaluation actor.

    Evaluates LLM browser agents on real-world web interaction tasks.
    Features:
    - Dynamic task generation using seeds for reproducibility
    - Real-time API validation against live websites
    - Plugin-based architecture for extensible task types
    - LLM-based flexible answer validation
    """

    # Plugin registry
    PLUGINS: Dict[str, Type[BasePlugin]] = {
        "weather": WeatherPlugin,
        # Future plugins:
        # "stock": StockPlugin,
        # "paper": PaperPlugin,
        # "flight": FlightPlugin,
        # "news": NewsPlugin,
    }

    def __init__(self, api_key: str = None):
        """
        Initialize Actor.

        Args:
            api_key: API key for LLM service. Falls back to CHUTES_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("CHUTES_API_KEY")
        self.browser: Optional[BrowserEngine] = None
        self.task_manager = TaskManager(self.PLUGINS)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._lock = asyncio.Lock()

    async def evaluate(
        self,
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
    ) -> dict:
        """
        Run a single evaluation.

        Args:
            model: Model name for the LLM agent
            base_url: OpenAI-compatible API base URL
            api_key: Override API key for this evaluation
            seed: Deterministic task generation seed (random if None)
            num_subtasks: Number of sub-tasks (1-4)
            plugins: Explicit plugin list; None = random selection
            max_steps: Max browser interaction steps
            timeout: Total wall-clock budget in seconds
            temperature: LLM temperature
            max_concurrency: Container-local concurrency limit
            validation_model: Model for answer validation (default: same as model)

        Returns:
            Evaluation result dict with scores and metadata
        """
        start_time = time.time()

        # Generate seed if not provided
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        # Allow per-call API key override
        current_api_key = api_key or self.api_key

        # Initialize semaphore for concurrency control
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(max_concurrency)

        async with self._semaphore:
            try:
                result = await self._run_evaluation(
                    model=model,
                    base_url=base_url,
                    api_key=current_api_key,
                    seed=seed,
                    num_subtasks=num_subtasks,
                    plugins=plugins,
                    max_steps=max_steps,
                    timeout=timeout,
                    temperature=temperature,
                    validation_model=validation_model,
                )
            except Exception as e:
                import traceback
                result = {
                    "task_name": f"liveweb_arena:{num_subtasks}tasks",
                    "score": 0.0,
                    "success": False,
                    "time_taken": time.time() - start_time,
                    "extra": {
                        "seed": seed,
                        "num_subtasks": num_subtasks,
                        "conversation": [],
                    },
                    "error": f"{type(e).__name__}: {str(e)}",
                    "error_trace": traceback.format_exc(),
                }

        result["time_taken"] = time.time() - start_time
        return result

    async def _run_evaluation(
        self,
        model: str,
        base_url: str,
        api_key: str,
        seed: int,
        num_subtasks: int,
        plugins: Optional[List[str]],
        max_steps: int,
        timeout: int,
        temperature: float,
        validation_model: Optional[str] = None,
    ) -> dict:
        """Internal evaluation logic"""
        # Ensure browser is started
        await self._ensure_browser()

        # Generate composite task
        task = await self.task_manager.generate_composite_task(
            seed=seed,
            num_subtasks=num_subtasks,
            plugin_names=plugins,
        )

        # Create isolated browser session
        session = await self.browser.new_session()

        try:
            # Initialize components
            llm_client = LLMClient(base_url=base_url, api_key=api_key)
            policy = AgentPolicy()
            agent_loop = AgentLoop(
                session=session,
                llm_client=llm_client,
                policy=policy,
                max_steps=max_steps,
            )

            # Run agent loop with timeout
            try:
                trajectory, final_answer, usage = await asyncio.wait_for(
                    agent_loop.run(
                        task=task,
                        model=model,
                        temperature=temperature,
                        seed=seed,
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                trajectory, final_answer, usage = [], None, None

            # Parse answers
            parser = AnswerParser()
            parsed_answers = parser.parse_answers(final_answer, num_subtasks)
            output_format = parser.get_output_format(final_answer)

            # Collect ground truths from plugins
            ground_truths = {}
            for subtask in task.subtasks:
                plugin = self.task_manager.get_plugin(subtask.plugin_name)
                try:
                    gt_result = await plugin.get_ground_truth(subtask.validation_info)
                    ground_truths[subtask.answer_tag] = gt_result
                except Exception as e:
                    ground_truths[subtask.answer_tag] = None

            # Use LLM to validate answers
            # Default validation model: openai/gpt-oss-120b-TEE (fast and reliable)
            actual_validation_model = validation_model or "openai/gpt-oss-120b-TEE"
            answer_validations = await validate_answers_with_llm(
                llm_client=llm_client,
                subtasks=task.subtasks,
                answers=parsed_answers,
                ground_truths=ground_truths,
                model=model,
                validation_model=actual_validation_model,
            )

            # Calculate overall score
            if answer_validations:
                total_score = sum(v["score"] for v in answer_validations) / len(answer_validations)
            else:
                total_score = 0.0

            success = total_score >= 0.8

            # Get final URL
            final_url = None
            if trajectory:
                final_url = trajectory[-1].observation.url

            # Build conversation history
            conversation = self._build_conversation(task, trajectory)

            # Build result with answer details array in metadata
            return {
                "task_name": f"liveweb_arena:{num_subtasks}tasks",
                "score": total_score,
                "success": success,
                "time_taken": 0.0,  # Will be set by caller
                "extra": {
                    "seed": seed,
                    "num_subtasks": num_subtasks,
                    "final_url": final_url,
                    "output_format": output_format,
                    "json_repair_count": policy.json_repair_count,
                    "usage": usage,
                    "answer_details": answer_validations,
                    "conversation": conversation,
                },
            }

        finally:
            # Always close the session
            await session.close()

    async def _ensure_browser(self):
        """Ensure browser is started (lazy initialization)"""
        async with self._lock:
            if self.browser is None:
                self.browser = BrowserEngine(headless=True)
                await self.browser.start()

    async def shutdown(self):
        """Shutdown browser and cleanup resources"""
        if self.browser:
            await self.browser.stop()
            self.browser = None

    def _build_conversation(
        self,
        task: "CompositeTask",
        trajectory: List["TrajectoryStep"],
    ) -> List[dict]:
        """
        Build conversation history from task and trajectory.

        Args:
            task: The composite task
            trajectory: List of trajectory steps

        Returns:
            List of conversation turns with role, content, and metadata
        """
        from .core.models import CompositeTask, TrajectoryStep

        conversation = []

        # Add initial task as system message
        conversation.append({
            "role": "system",
            "content": task.combined_intent,
            "metadata": {
                "type": "task_description",
                "num_subtasks": len(task.subtasks),
            }
        })

        # Add each trajectory step
        for step in trajectory:
            # Observation (environment state)
            obs_content = (
                f"URL: {step.observation.url}\n"
                f"Title: {step.observation.title}\n"
                f"Accessibility Tree:\n{step.observation.accessibility_tree[:2000]}"
            )
            if len(step.observation.accessibility_tree) > 2000:
                obs_content += "\n... (truncated)"

            conversation.append({
                "role": "environment",
                "content": obs_content,
                "metadata": {
                    "type": "observation",
                    "step": step.step_num,
                    "url": step.observation.url,
                }
            })

            # Agent's thought and action
            if step.thought or step.action:
                action_str = ""
                if step.action:
                    action_str = f"Action: {step.action.action_type}"
                    if step.action.params:
                        action_str += f" {step.action.params}"

                agent_content = ""
                if step.thought:
                    agent_content += f"Thought: {step.thought}\n"
                if action_str:
                    agent_content += action_str

                conversation.append({
                    "role": "agent",
                    "content": agent_content.strip(),
                    "metadata": {
                        "type": "action",
                        "step": step.step_num,
                        "action_type": step.action.action_type if step.action else None,
                        "action_result": step.action_result,
                    }
                })

        return conversation
