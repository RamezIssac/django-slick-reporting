#!/usr/bin/env python
"""
Deterministic benchmark: JSON vs plain-text vs TOON data serialization in
the prompts of the LLM reporting assistant.

    pip install "toon-format==0.9.0b1"   # needed for the TOON arm only
    python run_benchmark.py

Runs the 5 fixture questions x 3 data formats x 3 paired repetitions
(identical sampling, one backend instance, rep -> format -> question order)
against the local OpenAI-compatible endpoint
(http://192.168.178.100:8080/v1/chat/completions), on a hermetic, freshly
created SQLite database (see tests/eval_settings.py), and writes the full
evidence artifact -- untruncated raw responses, per-call token counts,
per-stage latencies, failures -- to eval_evidence/benchmark_<timestamp>.json.
"""

import datetime
import json
import os
import sys
import time
import urllib.request

ENDPOINT = "http://192.168.178.100:8080/v1/chat/completions"

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.eval_settings"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

from slick_reporting.llm.backends import OpenAICompatibleBackend  # noqa: E402
from slick_reporting.llm.evaluator import (  # noqa: E402
    EvaluationFixture,
    create_fixture_data,
    run_evaluation,
)

FORMATS = ["json", "plain", "toon"]
REPETITIONS = 3


def query_served_models():
    """Return the model list the endpoint currently serves (for pinning)."""
    url = ENDPOINT.rsplit("/chat/completions", 1)[0] + "/models"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [m.get("id") or m.get("name") for m in payload.get("data") or payload.get("models") or []]
    except Exception as exc:
        print(f"WARNING: could not query served models from {url}: {exc}")
        return []


def prepare_database():
    """Create a fresh, hermetic evaluation database."""
    db_path = settings.DATABASES["default"]["NAME"]
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed stale evaluation database: {db_path}")
    call_command("migrate", "--run-syncdb", verbosity=0)
    create_fixture_data()
    print(f"Seeded hermetic fixture database: {db_path}")


def main():
    served = query_served_models()
    backend = OpenAICompatibleBackend(
        api_url=ENDPOINT,
        model="local",  # llama.cpp serves a single model; the served name is recorded per response
        temperature=0.2,
        timeout=300,
        enable_thinking=False,
        reasoning_budget=0,
    )

    print("=" * 70)
    print("LLM PROMPT DATA-FORMAT COMPARISON BENCHMARK")
    print("=" * 70)
    print(f"Endpoint:    {ENDPOINT}")
    print(f"Served:      {', '.join(served) or 'unknown'}")
    print(f"Formats:     {', '.join(FORMATS)}")
    print(f"Repetitions: {REPETITIONS} (paired, identical sampling)")
    print()
    print(EvaluationFixture.get_summary())
    print()

    prepare_database()

    start = time.perf_counter()
    result = run_evaluation(backend=backend, formats=FORMATS, repetitions=REPETITIONS)
    elapsed = time.perf_counter() - start

    result["meta"]["elapsed_seconds"] = round(elapsed, 2)
    result["meta"]["wall_clock_start_utc"] = datetime.datetime.now(datetime.UTC).isoformat()
    result["meta"]["served_models_endpoint"] = served

    scores = result.get("scores", {})
    print("\n" + "=" * 70)
    print("AGGREGATED RESULTS BY FORMAT")
    print("=" * 70)
    for fmt in FORMATS:
        s = scores.get(fmt, {})
        print(f"\n  [{fmt.upper()}]")
        print(f"    Plan success rate:        {s.get('plan_success_rate', 0) * 100:.0f}%")
        print(f"    Parse success rate:       {s.get('parse_success_rate', 0) * 100:.0f}%")
        print(f"    Report execution rate:    {s.get('report_execution_rate', 0) * 100:.0f}%")
        print(f"    Exact value match rate:   {s.get('exact_value_match_rate', 0) * 100:.0f}%")
        print(f"    Answer correctness rate:  {s.get('answer_correctness_rate', 0) * 100:.0f}%")
        print(f"    Avg normalized plan:      {s.get('avg_normalized_plan_score', 0):.2f}")
        print(f"    Plan correctness stddev:  {s.get('plan_correctness_stddev', 0):.4f}")
        print(f"    Avg plan prompt tokens:   {s.get('avg_plan_prompt_tokens', 0):.0f}")
        print(f"    Avg answer prompt tokens: {s.get('avg_answer_prompt_tokens', 0):.0f}")
        print(f"    Avg total tokens/quest.:  {s.get('avg_total_tokens_per_question', 0):.0f}")
        print(f"    Avg plan latency (s):     {s.get('avg_plan_latency_seconds', 0):.2f}")
        print(f"    Avg answer latency (s):   {s.get('avg_answer_latency_seconds', 0):.2f}")
        print(f"    Avg total latency (s):    {s.get('avg_total_latency_seconds', 0):.2f}")

    evidence_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(evidence_dir, f"benchmark_{timestamp}.json")

    artifact = {
        "meta": result["meta"],
        "scores": scores,
        "results": {fmt: [r.to_dict() for r in result["results"][fmt]] for fmt in FORMATS},
    }
    with open(output_path, "w") as f:
        json.dump(artifact, f, indent=2, default=str)

    print(f"\n  Evidence artifact: {output_path}")
    print(f"  Total wall clock: {elapsed:.1f}s")
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
