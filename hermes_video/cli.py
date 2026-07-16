from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .applescript_generator import build_applescript, open_in_fcp
from .benchmark import evaluate, init_benchmark, record_baseline
from .batch_processor import process_all_projects
from .config import load_config
from .fcpxml_generator import export_timeline_fcpxml
from .folder_watcher import watch_projects
from .marketing_editor import render_marketing_edits
from .pipeline import analyze_local, create_shorts, ingest_project, plan_project, prepare, transcribe_words
from .project_scaffold import init_project, init_projects_root
from .review import serve_review
from .style import learn_edit, list_styles, rebuild_style, show_style
from .video_renderer import render_project


def _project(parser: argparse.ArgumentParser, required: bool = True) -> None:
    parser.add_argument("--project", required=required, default=".")


def _deprecated(name: str, replacement: str) -> None:
    print(f"DEPRECATED: '{name}' is retained for compatibility; use '{replacement}'.", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="Hermes Assistant Editor V2", description="Local-first assistant-editor rough cuts for Final Cut Pro")
    parser.add_argument("--config", default=None, help="JSON or TOML configuration")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("setup-root"); p.add_argument("--projects-root", required=True)
    p = sub.add_parser("init"); _project(p); p.add_argument("--raw-subfolders", action="store_true")
    p = sub.add_parser("ingest"); _project(p)
    p = sub.add_parser("analyze"); _project(p); p.add_argument("--engine")
    p = sub.add_parser("plan"); _project(p); p.add_argument("--format", default=None); p.add_argument("--target-duration", type=float); p.add_argument("--style", default="chandler_default")
    p = sub.add_parser("prepare"); _project(p); p.add_argument("--format", default=None); p.add_argument("--target-duration", type=float); p.add_argument("--style", default="chandler_default"); p.add_argument("--engine")
    p = sub.add_parser("review"); _project(p); p.add_argument("--host"); p.add_argument("--port", type=int)
    p = sub.add_parser("export-fcpxml"); _project(p); p.add_argument("--timeline", choices=["conservative", "aggressive", "approved"], default="conservative"); p.add_argument("--orientation", choices=["horizontal", "vertical"], default="horizontal")
    p = sub.add_parser("open-in-fcp"); _project(p); p.add_argument("--timeline", default="approved")
    p = sub.add_parser("render"); _project(p); p.add_argument("--timeline", default="conservative"); p.add_argument("--horizontal-only", action="store_true"); p.add_argument("--vertical-only", action="store_true")
    p = sub.add_parser("legacy-marketing-montage"); _project(p)
    for name in ("edit", "full"):
        p = sub.add_parser(name); _project(p); p.add_argument("--format", default=None); p.add_argument("--engine")
    p = sub.add_parser("scan"); _project(p)
    p = sub.add_parser("transcribe"); _project(p); p.add_argument("--engine")
    p = sub.add_parser("build-edit"); _project(p); p.add_argument("--format", default=None)
    p = sub.add_parser("build-fcpxml"); _project(p); p.add_argument("--timeline", default="conservative")
    p = sub.add_parser("marketing-edit"); _project(p)
    p = sub.add_parser("watch"); p.add_argument("--projects-root", required=True)
    p = sub.add_parser("process-all"); p.add_argument("--projects-root", required=True); p.add_argument("--format", default=None); p.add_argument("--engine")

    p = sub.add_parser("learn-edit"); _project(p)
    p.add_argument("--automated-xml", "--automated", dest="automated", required=True)
    p.add_argument("--final-xml", "--final", dest="final", required=True)
    p.add_argument("--style", default="chandler_default")

    p = sub.add_parser("style"); p.add_argument("action", choices=["list", "show", "rebuild"]); _project(p, required=False); p.add_argument("name", nargs="?", default="chandler_default")

    p = sub.add_parser("benchmark"); p.add_argument("action", choices=["init", "record-baseline", "evaluate"]); _project(p)
    p.add_argument("--minutes", type=float); p.add_argument("--cost", type=float, default=0); p.add_argument("--structure-units", type=int); p.add_argument("--retained-units", type=int); p.add_argument("--errors", type=int, default=0); p.add_argument("--final-xml")

    args = parser.parse_args(argv)
    config = load_config(args.config)
    if getattr(args, "engine", None):
        config.transcription_engine = args.engine
    cmd, result = args.command, None

    if cmd == "setup-root":
        result = str(init_projects_root(args.projects_root))
    elif cmd == "init":
        result = str(init_project(args.project, raw_subfolders=args.raw_subfolders))
    elif cmd in {"ingest", "scan"}:
        if cmd == "scan": _deprecated("scan", "ingest")
        result = ingest_project(args.project, config)
    elif cmd == "analyze":
        ingest_project(args.project, config)
        result = {"transcription": transcribe_words(args.project, config), "local": analyze_local(args.project)}
    elif cmd == "transcribe":
        _deprecated("transcribe", "analyze"); result = transcribe_words(args.project, config)
    elif cmd in {"plan", "build-edit"}:
        if cmd == "build-edit": _deprecated("build-edit", "plan")
        result = {k: v.model_dump() for k, v in plan_project(args.project, args.format or config.default_edit_format, getattr(args, "target_duration", None), getattr(args, "style", config.default_style)).items()}
        create_shorts(args.project)
    elif cmd in {"prepare", "edit", "full"}:
        if cmd != "prepare": _deprecated(cmd, "prepare")
        result = prepare(args.project, config, args.format or config.default_edit_format, getattr(args, "target_duration", None), getattr(args, "style", config.default_style))
    elif cmd == "review":
        host, port = args.host or config.review_host, args.port or config.review_port
        print(f"Review server: http://{host}:{port}")
        serve_review(args.project, host, port); return
    elif cmd in {"export-fcpxml", "build-fcpxml"}:
        if cmd == "build-fcpxml": _deprecated("build-fcpxml", "export-fcpxml")
        result = str(export_timeline_fcpxml(args.project, args.timeline, getattr(args, "orientation", "horizontal")))
        build_applescript(args.project, config)
    elif cmd == "open-in-fcp":
        open_in_fcp(args.project, config); return
    elif cmd == "render":
        if args.horizontal_only and args.vertical_only:
            parser.error("--horizontal-only and --vertical-only cannot be combined")
        timeline = Path(args.project) / "05_EDIT_DECISIONS" / f"timeline_{args.timeline}.json"
        result = render_project(args.project, timeline, render_horizontal=not args.vertical_only, render_vertical=not args.horizontal_only)
    elif cmd in {"legacy-marketing-montage", "marketing-edit"}:
        if cmd == "marketing-edit": _deprecated("marketing-edit", "legacy-marketing-montage")
        result = render_marketing_edits(args.project, config)
    elif cmd == "watch":
        watch_projects(args.projects_root, config); return
    elif cmd == "process-all":
        result = process_all_projects(args.projects_root, config, args.format or config.default_edit_format)
    elif cmd == "learn-edit":
        result = str(learn_edit(args.project, args.automated, args.final, args.style))
    elif cmd == "style":
        if args.action == "list": result = list_styles(args.project)
        elif args.action == "show": result = show_style(args.project, args.name)
        else: result = str(rebuild_style(args.project, args.name))
    elif cmd == "benchmark":
        if args.action == "init": result = str(init_benchmark(args.project))
        elif args.action == "record-baseline": result = str(record_baseline(args.project, args.minutes, args.cost, args.structure_units, args.errors))
        else: result = evaluate(args.project, args.minutes, args.cost, args.retained_units, args.errors, args.final_xml)

    if result is not None:
        print(json.dumps(result, indent=2, default=str))
