"""
Pluggable LLM backend for the natural-language reporting assistant.

Configure via Django settings, e.g.

    SLICK_REPORTING_SETTINGS = {
        "LLM_BACKEND": "slick_reporting.llm.backends.OpenAICompatibleBackend",
        "LLM_BACKEND_OPTIONS": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "model": "gpt-4o-mini",
            "temperature": 0.2,
        },
    }

The configured backend class is instantiated once and must implement::

    def complete(self, prompt: str) -> str:
        ...

A prompt is the full system+user text; the backend returns the assistant's
content string.  Implementations are encouraged to raise on failure rather
than returning an empty string.
"""

import json
import logging
from abc import ABC, abstractmethod

from django.utils.module_loading import import_string

from ..app_settings import SLICK_REPORTING_SETTINGS

logger = logging.getLogger(__name__)


class LLMBackend(ABC):
    """Abstract LLM client."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send ``prompt`` to the LLM and return the raw text response."""
        raise NotImplementedError


class EchoBackend(LLMBackend):
    """A backend useful for tests: returns exactly what was sent as the prompt."""

    def complete(self, prompt: str) -> str:
        return prompt


class OpenAICompatibleBackend(LLMBackend):
    """
    OpenAI-compatible chat completions backend using only the standard library.

    Expected ``options`` keys:
    * api_url  (required) e.g. ``https://api.openai.com/v1/chat/completions``
    * api_key  (required)
    * model    (required)
    * temperature (optional, default 0.2)
    * max_tokens  (optional)

    Supports any provider exposing the same JSON schema: OpenAI, Groq, etc.
    """

    def __init__(self, **options):
        self.options = options
        self.api_url = options["api_url"]
        self.api_key = options["api_key"]
        self.model = options["model"]
        self.temperature = float(options.get("temperature", 0.2))
        self.max_tokens = options.get("max_tokens")
        self.enable_thinking = options.get("enable_thinking")
        self.reasoning_budget = options.get("reasoning_budget")

    def complete(self, prompt: str) -> str:
        import urllib.request

        messages = self._messages_from_prompt(prompt)
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        if self.enable_thinking is not None:
            payload["enable_thinking"] = bool(self.enable_thinking)

        # llama.cpp reasoning controls. enable_thinking=False goes through
        # chat_template_kwargs (the real off switch for qwen); a budget caps tokens.
        if self.enable_thinking is False:
            payload.setdefault("chat_template_kwargs", {})["enable_thinking"] = False
        if self.reasoning_budget is not None:
            payload["reasoning_budget"] = int(self.reasoning_budget)

        logger.debug(
            "LLM request to %s (model=%s, temperature=%s, messages=%d)\n%s",
            self.api_url,
            self.model,
            self.temperature,
            len(messages),
            json.dumps(payload, indent=2),
        )

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        timeout = self.options.get("timeout", 600)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        message = result["choices"][0].get("message", {})
        content = message.get("content", "")
        logger.debug("LLM response status=%s\n%s", response.status, content)
        return content

    def _messages_from_prompt(self, prompt: str):
        """
        Allow callers to pass a pre-structured JSON message list in the
        prompt by trying to decode it; otherwise treat the whole value as
        the user message.
        """
        try:
            parsed = json.loads(prompt)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return None


def _default_backend_options():
    """Return default options using well-known environment variables."""
    import os

    return {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
    }


def get_llm_backend():
    """Load the configured LLM backend class and instantiate it once."""
    backend_path = SLICK_REPORTING_SETTINGS.get("LLM_BACKEND")
    options = SLICK_REPORTING_SETTINGS.get("LLM_BACKEND_OPTIONS")

    if backend_path is None:
        # Try to fall back to environment-backed defaults if an API key is set.
        import os

        if os.environ.get("OPENAI_API_KEY"):
            backend_path = "slick_reporting.llm.backends.OpenAICompatibleBackend"
            options = options or _default_backend_options()
        else:
            backend_path = "slick_reporting.llm.backends.EchoBackend"
            options = {}

    if isinstance(backend_path, str):
        backend_class = import_string(backend_path)
    else:
        backend_class = backend_path

    options = options or {}
    return backend_class(**options)
