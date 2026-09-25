"""
Pluggable LLM backend for the natural-language reporting assistant.

Configure via Django settings, e.g. OpenRouter (hosts free-tier models):

    SLICK_REPORTING_SETTINGS = {
        "LLM_BACKEND": "slick_reporting.llm.backends.OpenRouterBackend",
        "LLM_BACKEND_OPTIONS": {
            "model": "nex-agi/nex-n2.5-mini:free",  # any OpenRouter model id
            # The API key is read from the OPENROUTER_API_KEY env var.
        },
    }

or any OpenAI-compatible endpoint (OpenAI, Groq, a local llama.cpp server, ...):

    SLICK_REPORTING_SETTINGS = {
        "LLM_BACKEND": "slick_reporting.llm.backends.OpenAICompatibleBackend",
        "LLM_BACKEND_OPTIONS": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4o-mini",
            "temperature": 0.2,
        },
    }

If ``LLM_BACKEND`` is not set, :func:`get_llm_backend` auto-detects from the
environment: ``OPENROUTER_API_KEY`` selects the OpenRouter backend with its
default free model, ``OPENAI_API_KEY`` selects the OpenAI backend, otherwise
the no-op ``EchoBackend`` is used.

The configured backend class is instantiated once and must implement::

    def complete(self, prompt: str) -> str:
        ...

A prompt is the full system+user text; the backend returns the assistant's
content string.  Implementations are encouraged to raise on failure rather
than returning an empty string.
"""

import json
import logging
import os
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

    def get_last_usage(self) -> dict:
        """Token usage reported by the provider for the last ``complete()`` call.

        Returns a dict with ``prompt_tokens`` / ``completion_tokens`` /
        ``total_tokens`` keys, or an empty dict when the provider does not
        report usage (or no call has been made yet).
        """
        return {}

    def get_last_model(self):
        """Model identifier the provider reports for the last ``complete()`` call, if any."""
        return None


class EchoBackend(LLMBackend):
    """A backend useful for tests: returns exactly what was sent as the prompt."""

    def complete(self, prompt: str) -> str:
        return prompt


class OpenAICompatibleBackend(LLMBackend):
    """
    OpenAI-compatible chat completions backend using only the standard library.

    Expected ``options`` keys:
    * ``api_url``  full chat-completions URL, e.g. ``https://api.openai.com/v1/chat/completions``,
      or ``base_url`` an OpenAI-style base URL (``/chat/completions`` is appended).
    * ``api_key``  the literal API key, or ``api_key_env`` naming an environment
      variable to read it from.
    * ``model``    model identifier (falls back to the class ``default_model`` if any).
    * ``temperature`` (optional, default 0.2), ``max_tokens``, ``timeout`` (default 600).
    * ``extra_headers`` optional dict merged into the request headers.
    * ``extra_payload`` optional dict merged into every request payload. Use it
      for provider-specific knobs, e.g. OpenRouter reasoning controls
      ``{"reasoning": {"effort": "low"}}``.
    * ``enable_thinking`` / ``reasoning_budget``: llama.cpp reasoning controls.

    Supports any provider exposing the same JSON schema: OpenAI, OpenRouter,
    Groq, llama.cpp, etc.
    """

    #: Subclasses may provide defaults so instances need no options at all.
    default_base_url = None
    default_api_key_env = None
    default_model = None

    def __init__(self, **options):
        self.options = options
        base_url = (options.get("base_url") or self.default_base_url or "").rstrip("/")
        self.api_url = options.get("api_url") or (f"{base_url}/chat/completions" if base_url else "")
        if not self.api_url:
            raise ValueError(f"{self.__class__.__name__} requires 'api_url' or 'base_url' in LLM_BACKEND_OPTIONS.")
        api_key_env = options.get("api_key_env") or self.default_api_key_env
        self.api_key = options.get("api_key") or (os.environ.get(api_key_env, "") if api_key_env else "")
        if not self.api_key and api_key_env:
            logger.warning(
                "%s has no API key: set the %s environment variable or pass 'api_key'.",
                self.__class__.__name__,
                api_key_env,
            )
        self.model = options.get("model") or self.default_model
        if not self.model:
            raise ValueError(f"{self.__class__.__name__} requires 'model' in LLM_BACKEND_OPTIONS.")
        self.temperature = float(options.get("temperature", 0.2))
        self.max_tokens = options.get("max_tokens")
        self.enable_thinking = options.get("enable_thinking")
        self.reasoning_budget = options.get("reasoning_budget")
        self.extra_headers = dict(options.get("extra_headers") or {})
        self.extra_payload = dict(options.get("extra_payload") or {})

    def complete(self, prompt: str) -> str:
        import urllib.request

        messages = self._messages_from_prompt(prompt)
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            **self.extra_payload,
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        if self.enable_thinking is not None:
            payload["enable_thinking"] = bool(self.enable_thinking)

        # llama.cpp reasoning controls. enable_thinking=False and a zero budget both
        # mean "no thinking", and the reliable off switch across templates is
        # chat_template_kwargs (qwen ignores the top-level enable_thinking flag).
        thinking_off = self.enable_thinking is False or self.reasoning_budget == 0
        if thinking_off:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        if self.reasoning_budget is not None and self.reasoning_budget > 0:
            payload["reasoning_budget"] = int(self.reasoning_budget)

        logger.debug(
            "LLM request to %s (model=%s, temperature=%s, messages=%d)\n%s",
            self.api_url,
            self.model,
            self.temperature,
            len(messages),
            json.dumps(payload, indent=2),
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        timeout = self.options.get("timeout", 600)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        message = result["choices"][0].get("message", {})
        content = message.get("content") or ""
        # Preserve the provider's token accounting and served-model identity
        # so evaluations can compare prompt sizes across prompt formats.
        usage = result.get("usage") or {}
        self._last_usage = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
        self._last_model = result.get("model")
        logger.debug("LLM response status=%s\n%s", response.status, content)
        return content

    def get_last_usage(self) -> dict:
        """Token usage reported by the provider for the last ``complete()`` call."""
        return dict(getattr(self, "_last_usage", None) or {})

    def get_last_model(self):
        """Model identifier the provider reports for the last ``complete()`` call."""
        return getattr(self, "_last_model", None)

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


#: Model used by ``OpenRouterBackend`` when no explicit model is configured.
#: A free-tier model so the assistant works out of the box; this one verified
#: best against the demo evaluation set (2026-09). Free-model rosters and
#: availability change often — browse https://openrouter.ai/models?q=free
OPENROUTER_DEFAULT_MODEL = "nex-agi/nex-n2.5-mini:free"


class OpenRouterBackend(OpenAICompatibleBackend):
    """
    `OpenRouter <https://openrouter.ai>`_ backend (OpenAI-compatible API).

    Defaults: base URL ``https://openrouter.ai/api/v1``, API key read from the
    ``OPENROUTER_API_KEY`` environment variable, and the free-tier
    ``OPENROUTER_DEFAULT_MODEL``. All ``OpenAICompatibleBackend`` options
    apply; additionally ``site_url`` and ``app_name`` set OpenRouter's
    optional ``HTTP-Referer`` / ``X-Title`` attribution headers, and
    ``extra_payload`` can carry OpenRouter reasoning controls, e.g.
    ``{"reasoning": {"effort": "low"}}``.
    """

    default_base_url = "https://openrouter.ai/api/v1"
    default_api_key_env = "OPENROUTER_API_KEY"
    default_model = OPENROUTER_DEFAULT_MODEL

    def __init__(self, **options):
        extra_headers = dict(options.get("extra_headers") or {})
        if options.get("site_url"):
            extra_headers.setdefault("HTTP-Referer", options["site_url"])
        if options.get("app_name"):
            extra_headers.setdefault("X-Title", options["app_name"])
        options["extra_headers"] = extra_headers
        super().__init__(**options)


def _default_backend_options():
    """Return default options using well-known environment variables."""
    return {
        "base_url": "https://api.openai.com/v1",
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
    }


def get_llm_backend():
    """Load the configured LLM backend class and instantiate it once."""
    backend_path = SLICK_REPORTING_SETTINGS.get("LLM_BACKEND")
    options = SLICK_REPORTING_SETTINGS.get("LLM_BACKEND_OPTIONS")

    if backend_path is None:
        # Auto-detect a backend from well-known environment variables.
        if os.environ.get("OPENROUTER_API_KEY"):
            backend_path = "slick_reporting.llm.backends.OpenRouterBackend"
            options = options or {}
        elif os.environ.get("OPENAI_API_KEY"):
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
