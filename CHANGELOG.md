# Changelog

## Unreleased — Personalized Assistant Editor V2

- Replaced the default video montage route with a local-first assistant-editor pipeline.
- Added SQLite project state, checksum-aware ingest, word-level transcription, sentence construction, technical media analysis, retake grouping, and complete editorial units.
- Added deterministic and OpenAI-compatible semantic analysis with validation, caching, and budget controls.
- Added conservative, aggressive, horizontal-short, and vertical-short paper-edit timelines with continuity and rationale reports.
- Added the local review/approval interface and approved-timeline persistence.
- Added rational-time horizontal/vertical FCPXML export with source metadata, markers, roles, placeholders, backups, and validation.
- Added completed-edit comparison, style profiles, benchmark reporting, V2 tests, updated demo, accurate README, and architecture/workflow documentation.
- Quarantined the old montage renderer behind `legacy-marketing-montage`; deprecated ambiguous V1 commands.

### Known limitations

- Final Cut Pro import still requires manual integration validation on a real spoken project.
- Real time-saving claims require measured commentary, podcast, and vlog benchmark projects.
- FCPXML style comparison currently uses conservative exact-range matching.
