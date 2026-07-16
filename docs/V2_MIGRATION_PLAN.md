# V2 Migration Plan

## Milestone 1 — correctness foundation

- [x] Audit V1 and record commands, runtimes, routing, dead code, and documentation drift.
- [x] Add pytest and regression coverage.
- [x] Add `<project>/.hermes/project.db` with indexed entities and readable exports.
- [x] Add checksum-aware ingest caching.
- [x] Add word-timestamp transcription and sentence construction.
- [x] Route `prepare`, deprecated `edit`/`full`, watcher, and `process-all` through V2.
- [x] Quarantine montage behind `legacy-marketing-montage`.

## Milestone 2 — assistant-editor intelligence

- [x] Deterministic scene, audio, silence, loudness, and clipping analysis.
- [x] Retake grouping with preserved alternates.
- [x] Complete editorial units.
- [x] Provider-neutral deterministic/OpenAI-compatible model abstraction with caching and budgets.
- [x] Conservative/aggressive paper edits and short timelines.
- [x] Boundary and continuity validation reports.

## Milestone 3 — review and handoff

- [x] Local transcript/timeline/media review UI and persistent approval state.
- [x] Approved timeline creation.
- [x] Rational-time FCPXML resources, roles, markers, B-roll gaps, horizontal/vertical formats, backups, and validation.
- [ ] Manual import validation in Final Cut Pro on a real spoken project (manual/environment gate).

## Milestone 4 — personalization

- [x] Automated-versus-final FCPXML comparison.
- [x] Descriptive style profiles and rebuild command.
- [x] Style-conditioned planning metadata.
- [ ] Expand comparison beyond exact resource/start/duration matching after real completed-edit fixtures accumulate.

## Milestone 5 — evaluation

- [x] Benchmark initialization, baseline, evaluation, threshold failures, and report.
- [x] Synthetic single-camera fixture in automated tests.
- [ ] Collect measured podcast and vlog projects. The repository does not fabricate human-time savings.

Migration is additive. Raw media is never deleted, V1 artifacts remain readable, and ambiguous legacy commands emit deprecation notices. No unreviewed timeline is labeled final.
