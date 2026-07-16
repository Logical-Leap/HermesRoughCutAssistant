# Editorial Pipeline

`ingest` inventories supported media and writes database/project state. `analyze` transcribes speech to words, groups words into complete sentences using punctuation and pauses, and extracts deterministic technical signals. Whisper segments are transport containers only; they are never final cut units.

Editorial units preserve source IDs, sentence IDs, ranges, context, confidence, scenes, and audio regions. Retake detection combines normalized wording and delivery confidence. Every alternate remains in the database and paper edit.

The semantic layer receives structured text and summaries, not full-resolution video. The deterministic model is the no-cost fallback. OpenAI-compatible endpoints receive a bounded structured request and must return Pydantic-valid JSON. Cached calls record provenance and estimates.

The conservative plan preserves chronology and complete units, removing only known alternates or material beyond an explicit target. The aggressive plan can omit weaker duplicate takes and tighten the assembly but records every action. No passage is selected by fixed temporal percentage or score-only sorting.

Continuity checks detect missing media, invalid or duplicate ranges, impossible offsets, and over-duration selections, and warn about backwards source jumps, unresolved-reference openings, and unanswered terminal questions. `paper_edit.md` explains keeps, removals, and alternatives. Human review remains authoritative.
