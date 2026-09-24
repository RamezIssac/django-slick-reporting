#!/usr/bin/env python
"""
Run the deterministic LLM evaluation benchmark against the local Qwen model via Ollama.

Usage:
    python run_benchmark.py

This runs all 5 fixture questions across 3 formats (json, plain, toonn) with
3 repetitions each, preserving raw outputs and generating a comparison report.
"""

import datetime
import json
import os
import sys
import time

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
import django
django.setup()

from slick_reporting.llm.evaluator import run_evaluation, EvaluationFixture


def main():
    # Configured local Qwen endpoint
    backend_class = "slick_reporting.llm.backends.OpenAICompatibleBackend"
    backend_options = {
        "api_url": "http://192.168.178.100:8080/v1/chat/completions",
        "model": "local",
        "temperature": 0.2,
        "timeout": 300,
        "enable_thinking": False,
        "reasoning_budget": 0,
    }

    formats = ["json", "plain", "toonn"]
    repetitions = 3

    print("=" * 70)
    print("LLM FORMAT COMPARISON BENCHMARK")
    print("=" * 70)
    print(f"Backend: {backend_class}")
    print(f"Model:   {backend_options['model']}")
    print(f"Endpoint: {backend_options['api_url']}")
    print(f"Formats: {', '.join(formats)}")
    print(f"Repetitions: {repetitions}")
    EvaluationFixture.setup()
    print(f"Fixture: {len(EvaluationFixture.get_all_question_ids())} questions")
    print("=" * 70)

    EvaluationFixture.setup()
    print()
    print(EvaluationFixture.get_summary())
    print()

    
    
    
    

    start = time.perf_counter()
    result = run_evaluation(
        backend_class=backend_class,
        backend_options=backend_options,
        formats=formats,
        repetitions=repetitions,
    )
    elapsed = time.perf_counter() - start

    result["meta"]["elapsed_seconds"] = round(elapsed, 2)
    result["meta"]["wall_clock_start"] = datetime.datetime.now(datetime.UTC).isoformat() + "Z"

    # Build a human-readable comparison summary
    scores = result.get("scores", {})
    print("\n" + "=" * 70)
    print("AGGREGATED RESULTS BY FORMAT")
    print("=" * 70)

    for fmt in formats:
        s = scores.get(fmt, {})
        print(f"\n  [{fmt.upper()}]")
        print(f"    Plan success rate:        {s.get('plan_success_rate', 0)*100:.0f}%")
        print(f"    Parse success rate:       {s.get('parse_success_rate', 0)*100:.0f}%")
        print(f"    Report execution rate:    {s.get('report_execution_rate', 0)*100:.0f}%")
        print(f"    Exact value match rate:   {s.get('exact_value_match_rate', 0)*100:.0f}%")
        print(f"    Answer correctness rate:  {s.get('answer_correctness_rate', 0)*100:.0f}%")
        print(f"    Avg normalized plan:      {s.get('avg_normalized_plan_score', 0):.2f}")
        print(f"    Plan correctness stddev:  {s.get('plan_correctness_stddev', 0):.4f}")
        print(f"    Avg total latency (s):    {s.get('avg_total_latency_seconds', 0):.3f}")
        print(f"    Avg plan tokens:          {s.get('avg_plan_tokens', 0):.0f}")
        print(f"    Avg answer tokens:        {s.get('avg_answer_tokens', 0):.0f}")

    # Variability comparison
    print("\n" + "=" * 70)
    print("VARIABILITY COMPARISON (across repetitions)")
    print("=" * 70)
    for fmt in formats:
        s = scores.get(fmt, {})
        sd = s.get("plan_correctness_stddev", 0)
        bar = "█" * int(sd * 20) + "░" * (20 - int(sd * 20))
        print(f"  {fmt:8s}: {sd:.4f}  [{bar}]")

    # Save raw results to eval_evidence/ (not gitignored)
    evidence_dir = os.path.join(
        os.path.dirname(__file__), "eval_evidence"
    )
    os.makedirs(evidence_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(evidence_dir, f"benchmark_{timestamp}.json")

    # Convert EvaluationResult objects to dicts for serialization
    raw_results = result.get("results", {})
    serializable_results = {}
    for fmt, results_list in raw_results.items():
        serializable_results[fmt] = []
        for r in results_list:
            serializable_results[fmt].append({
                "question_id": r.question_id,
                "question_text": r.question_text,
                "format_name": r.format_name,
                "plan_success": r.plan_success,
                "parse_success": r.parse_success,
                "report_executed": r.report_executed,
                "error": r.error,
                "raw_plan": r.raw_plan,
                "raw_answer": r.raw_answer,
                "report_config": r.report_config,
                "report_data": r.report_data,
                "answer": r.answer,
                "timings": r.timings,
                "scores": {k: (list(v) if isinstance(v, tuple) else v) for k, v in r.scores.items()},
            "token_counts": r.token_counts,
            "timings": r.timings,
            })

    result["results"] = serializable_results

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Full results saved to: {output_path}")

    # Save a compact summary
    summary_path = output_path.replace(".json", "_summary.json")
    summary = {
        "meta": result["meta"],
        "scores": scores,
        "variability": {
            fmt: scores.get(fmt, {}).get("plan_correctness_stddev", 0)
            for fmt in formats
        },
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary saved to: {summary_path}")

    print(f"\n  Total wall clock: {elapsed:.1f}s")
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()
