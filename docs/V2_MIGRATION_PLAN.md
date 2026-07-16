# V2 migration plan

## Delivery order

1. **Correctness foundation** — introduce typed domain models, SQLite state/migrations, checksum metadata cache, word-level transcription abstraction, sentence/clause construction, JSON/Markdown exports, and make `prepare`/legacy `edit` route through the assistant pipeline.
2. **Assistant intelligence** — deterministic FFprobe/FFmpeg analyzers, audio and scene regions, retake/duplicate grouping, complete editorial units, provider-neutral schema-validated semantic model with deterministic fallback and strict call/token/cost/retry budgets, topic map, conservative/aggressive plans, safe boundaries, continuity and paper-edit reports.
3. **Review and FCP handoff** — persistent approvals and a local FastAPI UI; modular rational FCPXML for common source rates and horizontal/vertical timelines, roles/markers/placeholders/external audio, backup plus validation. FCP is never automated beyond opening XML.
4. **Personalization** — compare machine and human-final FCPXML, store descriptive style profiles, condition planning prompts/rules; no fine-tuning.
5. **Shorts and benchmarks** — create explainable horizontal/vertical candidates and benchmark records with honest threshold failures.

## Module boundaries

- `store.py`, `ingest.py`, `transcription.py`, `local_analysis.py`: deterministic local media analysis and durable facts.
- `editorial_model.py`, `semantic.py`: provider-neutral semantic analysis only; cached and budgeted.
- `planning.py`, `continuity.py`, `shorts.py`: editorial planning and evaluation.
- `fcpxml_generator.py`, optional `video_renderer.py`: timeline construction/handoff.
- `review.py`, `style.py`, `benchmark.py`: personalization and human evaluation.
- `pipeline.py`, `cli.py`: orchestration and explicit commands; no hidden montage selection.

## Compatibility

`scan`, `transcribe`, `build-edit`, and `build-fcpxml` remain as deprecated aliases with warnings. Ambiguous `edit` and `full` become deprecated aliases for `prepare` and never render or montage. `marketing-edit` becomes a deprecated alias for explicit `legacy-marketing-montage`. Existing numbered output folders remain. SQLite is authoritative; portable JSON/Markdown exports remain reviewable.

## Verification gates

Each subsystem receives unit tests. End-to-end tests use synthetic FFmpeg fixtures, deterministic/mock editorial models, and no Final Cut dependency. FCPXML is XML/reference/duration validated locally; actual Final Cut import remains a separately reported manual validation. The final demo must ingest, analyze, plan, produce shorts, and export conservative/aggressive FCPXML without a paid API; optional MP4 render is separate.
