"""
Prompt-side serialization of report data and catalogs for the LLM assistant.

Three data formats are supported for embedding the reporting catalog and
report results into prompts:

* ``json``  — the default: ``json.dumps(..., indent=2, default=str)``.
* ``plain`` — a deterministic line-oriented plain-text rendering.
* ``toon``  — `TOON (Token-Oriented Object Notation) <https://toonformat.dev>`_,
  a compact serialization aimed at LLM prompts, via the official
  `toon-format <https://pypi.org/project/toon-format/>`_ package.

Only the *prompt-side* data serialization changes between formats; the
response-side instructions live in :mod:`slick_reporting.llm.prompts`.
"""

import datetime
import json
from decimal import Decimal

__all__ = [
    "DATA_FORMATS",
    "serialize_for_prompt",
    "dumps_json",
    "dumps_plain",
    "dumps_toon",
    "normalize_jsonable",
]

#: Prompt-side data serialization formats that can be compared.
DATA_FORMATS = ("json", "plain", "toon")

#: Minimum toon-format release with a working encoder (0.1.0 cannot encode).
TOON_PACKAGE = "toon-format"
TOON_PACKAGE_PIN = "toon-format==0.9.0b1"


def normalize_jsonable(obj):
    """
    Convert ``obj`` into JSON-safe primitives.

    ``Decimal`` becomes ``float``, dates/times become ISO strings, unknown
    objects fall back to ``str()``.  Dictionaries and sequences are
    converted recursively.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): normalize_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalize_jsonable(v) for v in obj]
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def dumps_json(obj):
    """Serialize with the base-branch default JSON rendering."""
    return json.dumps(obj, indent=2, default=str)


def dumps_toon(obj):
    """
    Serialize to TOON (Token-Oriented Object Notation).

    Requires the official ``toon-format`` package (``pip install
    toon-format==0.9.0b1``); a clear error is raised when it is missing.
    """
    try:
        import toon_format
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            f"TOON serialization requires the '{TOON_PACKAGE}' package. "
            f"Install the pinned working release: pip install {TOON_PACKAGE_PIN}"
        ) from exc
    return toon_format.encode(normalize_jsonable(obj))


def dumps_plain(obj):
    """
    Serialize to a deterministic line-oriented plain-text rendering.

    Dictionaries become ``key: value`` lines; uniform lists of flat
    dictionaries become aligned tables using `` | `` separators; other
    lists become ``- item`` lines; nesting is shown by two-space indents.
    """
    lines = []
    _render_plain(normalize_jsonable(obj), lines, 0)
    return "\n".join(lines)


def _render_plain(obj, lines, level):
    pad = "  " * level
    if isinstance(obj, dict):
        if not obj:
            lines.append(f"{pad}(empty)")
            return
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                _render_plain_member(str(key), value, lines, level)
            else:
                lines.append(f"{pad}{key}: {value}")
    elif isinstance(obj, list):
        _render_plain_member(None, obj, lines, level)
    else:
        lines.append(f"{pad}{obj}")


def _render_plain_member(key, value, lines, level):
    """Render one dict member (or a bare list when ``key`` is None)."""
    pad = "  " * level
    header = f"{pad}{key}" if key else f"{pad}items"
    if isinstance(value, dict):
        lines.append(f"{header}:")
        _render_plain(value, lines, level + 1)
        return
    # value is a list
    if not value:
        lines.append(f"{header}: (none)")
        return
    if all(not isinstance(v, (dict, list)) for v in value):
        lines.append(f"{header}: " + ", ".join(str(v) for v in value))
        return
    if all(isinstance(v, dict) for v in value) and all(
        all(not isinstance(vv, (dict, list)) for vv in row.values()) for row in value
    ):
        # Uniform flat records -> table.
        columns = []
        for row in value:
            for k in row:
                if k not in columns:
                    columns.append(k)
        lines.append(f"{header} ({len(value)} rows):")
        lines.append(f"{pad}  " + " | ".join(columns))
        for row in value:
            lines.append(f"{pad}  " + " | ".join(str(row.get(k, "")) for k in columns))
        return
    lines.append(f"{header}:")
    for i, item in enumerate(value, 1):
        lines.append(f"{pad}  #{i}")
        _render_plain(item, lines, level + 2)


def serialize_for_prompt(obj, data_format="json"):
    """Serialize ``obj`` for embedding in a prompt in ``data_format``."""
    if data_format == "json":
        return dumps_json(obj)
    if data_format == "plain":
        return dumps_plain(obj)
    if data_format == "toon":
        return dumps_toon(obj)
    raise ValueError(f"Unknown data_format {data_format!r}; expected one of {DATA_FORMATS}")
