"""
Django settings for the LLM format benchmark (``run_benchmark.py``).

Identical to the test settings except the database: a dedicated SQLite file
so the benchmark is hermetic -- no pre-existing rows can shift the fixture's
expected values, and the benchmark never touches the development database.

Set the ``SLICK_EVAL_DB`` environment variable to choose the database file;
the default is a file in the system temp directory.  ``run_benchmark.py``
deletes the file before seeding so every run starts from a known-empty
database.
"""

import os
import tempfile

from tests.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SLICK_EVAL_DB") or os.path.join(tempfile.gettempdir(), "slick_llm_eval.sqlite3"),
    }
}
