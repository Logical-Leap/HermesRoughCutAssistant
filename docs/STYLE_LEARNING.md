# Style Learning

`learn-edit` compares automated FCPXML with the editor's completed export. V2 records selection retention, human clip duration, total duration, and source-comparison references. Profiles live at `<project>/.hermes/style_profiles/<name>.json` and contain descriptive statistics plus explicit deterministic rules.

`style rebuild` recomputes aggregate statistics from recorded comparison files. Planning receives the selected profile name and records it in timeline metadata. Future retrieval can select prior examples with similar formats and topics.

V2 does not fine-tune a model. Adaptation uses statistics, explicit rules, relevant example retrieval, and prompt conditioning. Exact FCPXML matching is deliberately conservative; trim tolerance, reordering, hooks/endings, filler tolerance, B-roll, and pacing features should expand only with verified fixtures.
