# Data-format evaluation: results and recommendation

Evidence artifact: `benchmark_20261014_103338.json` (full per-call records,
untruncated raw plan/answer responses, token counts, per-stage latencies,
failures). Every number below is quoted from that artifact; re-quote from
there, not from this summary.

## Setup (from the artifact `meta`)

- Endpoint: `http://192.168.178.100:8080/v1/chat/completions` (local, OpenAI-compatible)
- Served model: `Qwen3.6-35B-A3B-UD-Q5_K_XL.gguf`
- Sampling: temperature 0.2, identical across formats
- Workload: the 5 deterministic fixture questions x 3 formats (JSON / plain
  text / TOON) x 3 paired repetitions = 15 calls per format, on a hermetic,
  freshly seeded SQLite fixture pinned in Q1 2026
- TOON serialization: `toon-format==1.1.0`

## Results

| Metric                          | JSON   | Plain text | TOON   |
| ------------------------------- | ------ | ---------- | ------ |
| Avg total tokens per question   | 4536.9 | 2699.7     | 3122.9 |
| Plan correctness rate           | 0.87   | 0.60       | 0.80   |
| Parse success rate              | 1.00   | 1.00       | 0.93   |
| Report execution rate           | 1.00   | 0.93       | 0.93   |
| Exact result values/labels rate | 1.00   | 0.93       | 0.93   |
| Answer correctness rate         | 1.00   | 0.93       | 0.93   |

## Recommendation

At this fixture size, serializing prompt data as TOON uses ~31% fewer total
tokens per question than JSON (3122.9 vs 4536.9), but still trails plain
text (2699.7). JSON leads on plan correctness (0.87) and answer correctness
(1.00) in this run. The evidence is one 5-question fixture on a single local
model, so these findings are directional — they are not grounds for changing
the production default, which stays JSON.

## Known limitations

- **Answer-binder phrasing classes.** The answer scorer binds numbers to
  labels only within the same phrasing class: a grouped answer whose numbers
  do not appear in the same sentence/run pattern as their labels can be
  mis-bound — including total-first breakdown phrasing ("The US and EG sold
  $2,750 in total: $1,250 for the US and $1,500 for EG."). Answers that carry
  label-matching structured `key_numbers` are unaffected. Parked as a
  documented limitation, not patched.
- **Strict `group_by` plan scoring.** Plan correctness requires an exact
  `group_by` match: a plan grouping by a different-but-related field scores
  as incorrect even when the report would still answer the question.
