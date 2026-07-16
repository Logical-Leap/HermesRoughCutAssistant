# FCPXML Handoff

FCPXML is the primary editable handoff. Hermes never edits a Final Cut library or creates a native `.fcpbundle`.

The exporter derives source formats from metadata and supports rational frame durations for 23.976, 24, 25, 29.97, 30, 50, 59.94, and 60 fps. Horizontal projects use 1920×1080 and vertical projects use 1080×1920. Resources preserve file URLs and stream capability flags. The primary storyline contains selected ranges, dialogue/video roles, editorial markers, and B-roll placeholder gaps.

Before success, the exporter parses XML and checks resource references, positive durations, and local source existence. Existing XML is backed up. Automated tests use fixtures and do not require Final Cut Pro.

Import manually with **File → Import → XML** or use `open-in-fcp`, which only opens generated XML with AppleScript. Successful XML validation is not a claim that a specific Final Cut version imported it; manual import is a separate integration gate.
