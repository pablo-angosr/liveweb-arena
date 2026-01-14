"""Agent loop for browser-based task execution"""

from typing import Any, List, Optional, Tuple

from core.browser import BrowserSession
from core.models import BrowserAction, BrowserObservation, CompositeTask, TrajectoryStep
from core.agent_policy import AgentPolicy
from utils.llm_client import LLMClient


class AgentLoop:
    """
    Main agent loop that drives browser interaction via LLM.

    Responsibilities:
    - Navigate to start URL
    - Loop: observe -> think -> act until stop or max_steps
    - Return trajectory and final answer
    """

    def __init__(
        self,
        session: BrowserSession,
        llm_client: LLMClient,
        policy: AgentPolicy,
        max_steps: int = 30,
    ):
        """
        Initialize agent loop.

        Args:
            session: Browser session to control
            llm_client: LLM client for generating actions
            policy: Agent policy for prompt building and parsing
            max_steps: Maximum number of interaction steps
        """
        self._session = session
        self._llm_client = llm_client
        self._policy = policy
        self._max_steps = max_steps

    async def run(
        self,
        task: CompositeTask,
        model: str,
        temperature: float = 0.7,
        seed: Optional[int] = None,
    ) -> Tuple[List[TrajectoryStep], Any, Optional[dict]]:
        """
        Run the agent loop until completion or max_steps.

        Args:
            task: Composite task to complete
            model: LLM model name
            temperature: LLM temperature
            seed: LLM seed for reproducibility

        Returns:
            Tuple of (trajectory, final_answer, usage)
            - trajectory: List of TrajectoryStep
            - final_answer: The final answer dict from stop action, or None
            - usage: Aggregated LLM usage dict
        """
        trajectory: List[TrajectoryStep] = []
        final_answer = None
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Reset policy repair count
        self._policy.reset_repair_count()

        # Build system prompt once
        system_prompt = self._policy.build_system_prompt(task)

        # Start from about:blank - Agent decides which URL to visit
        obs = await self._session.goto("about:blank")

        for step_num in range(self._max_steps):
            # Build step prompt
            user_prompt = self._policy.build_step_prompt(obs, trajectory)

            # Call LLM
            try:
                raw_response, usage = await self._llm_client.chat(
                    system=system_prompt,
                    user=user_prompt,
                    model=model,
                    temperature=temperature,
                    seed=seed,
                )

                # Aggregate usage
                if usage:
                    for key in total_usage:
                        total_usage[key] += usage.get(key, 0)

            except Exception as e:
                # LLM error - record and continue with wait action
                raw_response = ""
                thought = f"LLM error: {e}"
                action = BrowserAction(action_type="wait", params={"seconds": 1})
                action_result = "LLM call failed"

                trajectory.append(TrajectoryStep(
                    step_num=step_num,
                    observation=obs,
                    thought=thought,
                    action=action,
                    action_result=action_result,
                ))
                obs = await self._session.execute_action(action)
                continue

            # Parse response
            thought, action = self._policy.parse_response(raw_response)

            # Save observation before action execution (what Agent saw when making decision)
            obs_before_action = obs

            if action is None:
                # Parse failed - default to wait
                action = BrowserAction(action_type="wait", params={"seconds": 0.5})
                action_result = "Parse failed, waiting"
            elif action.action_type == "stop":
                # Extract final answer and finish
                final_params = action.params.get("final", {})
                final_answer = final_params if final_params else action.params
                action_result = "Task completed"

                trajectory.append(TrajectoryStep(
                    step_num=step_num,
                    observation=obs_before_action,
                    thought=thought,
                    action=action,
                    action_result=action_result,
                ))
                break
            else:
                # Execute action
                try:
                    new_obs = await self._session.execute_action(action)
                    action_result = "Success"
                    obs = new_obs
                except Exception as e:
                    action_result = f"Action failed: {e}"

            # Record step with observation BEFORE action (what Agent saw)
            trajectory.append(TrajectoryStep(
                step_num=step_num,
                observation=obs_before_action,
                thought=thought,
                action=action,
                action_result=action_result,
            ))

        return trajectory, final_answer, total_usage if any(total_usage.values()) else None
