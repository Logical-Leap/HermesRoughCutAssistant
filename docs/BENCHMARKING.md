# Benchmarking

Benchmarks measure rather than market. Initialize after ingest, record the editor's normal active-time baseline, then evaluate with actual review/correction time and final FCPXML.

Metrics include raw duration, automated processing placeholders, model usage/cost, human review/correction time, total active editing time, structure retention, restored passages, incorrect removals, mid-sentence errors, missing keepers, and final duration.

Spoken-content thresholds are at least 40% active-time reduction, zero unflagged mid-word/mid-sentence errors, and at least 70% rough-cut structure retained. The report prints `FAIL` and every failed threshold. Missing podcast/vlog measurements remain an explicit limitation; synthetic fixtures cannot prove real human time savings.
