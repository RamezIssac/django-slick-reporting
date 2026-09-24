"""
Discovery shim for the LLM assistant tests.

``runtests.py`` uses Django's test runner with the default ``test*.py``
pattern, which does not match ``llm_tests.py``. Re-export the test cases
here so a plain ``python runtests.py`` covers them. The tests themselves
live in ``tests/llm_tests.py``.
"""

from tests.llm_tests import (  # noqa: F401
    AskLLMViewOpenRouterTests,
    AskLLMViewTests,
    BackendTests,
    CatalogTests,
    ExecutorUnitTests,
    ReportConfigExecutionTests,
)
