"""OpenAI-compatible LLM client with retry and streaming support"""

import asyncio
import random
from typing import Optional, Tuple

import httpx
import openai


class LLMClient:
    """
    OpenAI-compatible LLM client.

    Features:
    - Streaming support with usage tracking
    - Exponential backoff retry for recoverable errors
    - Configurable timeouts
    """

    # Recoverable error status codes
    RETRY_STATUS_CODES = {429, 503, 502, 500}

    # Default retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 8.0  # seconds

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize LLM client.

        Args:
            base_url: OpenAI-compatible API base URL
            api_key: API key for authentication
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def chat(
        self,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.7,
        seed: Optional[int] = None,
        timeout_s: int = 30,
    ) -> Tuple[str, Optional[dict]]:
        """
        Make a chat completion request.

        Args:
            system: System prompt
            user: User message
            model: Model name
            temperature: Sampling temperature
            seed: Random seed for reproducibility
            timeout_s: Request timeout in seconds

        Returns:
            Tuple of (response content, usage dict or None)
        """
        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                content, usage = await self._make_request(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    seed=seed,
                    timeout_s=timeout_s,
                )
                return content, usage

            except openai.RateLimitError as e:
                last_error = e
                await self._backoff(attempt)

            except openai.APIStatusError as e:
                if e.status_code in self.RETRY_STATUS_CODES:
                    last_error = e
                    await self._backoff(attempt)
                else:
                    raise

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                await self._backoff(attempt)

        # All retries exhausted
        raise last_error or Exception("LLM request failed after all retries")

    async def _make_request(
        self,
        messages: list,
        model: str,
        temperature: float,
        seed: Optional[int],
        timeout_s: int,
    ) -> Tuple[str, Optional[dict]]:
        """Make a single API request with streaming"""
        client = openai.AsyncOpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=httpx.Timeout(timeout_s),
            max_retries=0,  # We handle retries ourselves
        )

        # Build request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if seed is not None:
            params["seed"] = seed

        # Make streaming request
        stream = await client.chat.completions.create(**params)

        # Collect streamed content and usage
        content_parts = []
        usage = None

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content_parts.append(chunk.choices[0].delta.content)
            if chunk.usage:
                usage = chunk.usage.model_dump()

        content = "".join(content_parts)
        if not content:
            raise ValueError("LLM returned empty response")

        return content.strip(), usage

    async def _backoff(self, attempt: int):
        """Exponential backoff with jitter"""
        delay = min(
            self.BASE_DELAY * (2 ** attempt) + random.uniform(0, 1),
            self.MAX_DELAY
        )
        await asyncio.sleep(delay)
