from __future__ import annotations

import argparse
from pathlib import Path
from .config import load_config
from .project_scaffold import init_project, init_projects_root
from .metadata_extractor import scan_project
from .transcription import transcribe_project
from .transcript_analyzer import analyze_project
from .edit_decision_builder import build_edit_decisions
from .fcpxml_generator import build_fcpxml
from .applescript_generator import build_applescript, open_in_fcp
from .video_renderer import render_project
from .marketing_editor import render_marketing_edits
from .batch_processor import process_project, process_all_projects
from .folder_watcher import watch_projects


def _project_arg(parser):
    parser.add_argument("--project", required=True, help="Project folder path. You can drop clips/music directly into this folder.")


def _run_edit(project: str, edit_format: str, config) -> None:
    process_project(project, config, edit_format)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="Hermes Rough Cut Assistant")
    parser.add_argument("--config", help="Path to config JSON", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("setup-root", help="Create the folder that will contain all video projects")
    p.add_argument("--projects-root", required=True)

    p = sub.add_parser("init", help="Create one project folder. Drop clips/music directly into it.")
    _project_arg(p)
    p.add_argument("--raw-subfolders", action="store_true", help="Also create legacy 01_RAW/A_CAM/B_CAM/IPHONE/AUDIO folders")

    p = sub.add_parser("scan"); _project_arg(p)
    p = sub.add_parser("transcribe"); _project_arg(p); p.add_argument("--engine", help="Override transcription engine")
    p = sub.add_parser("analyze"); _project_arg(p)
    p = sub.add_parser("build-edit"); _project_arg(p); p.add_argument("--format", default=None)
    p = sub.add_parser("build-fcpxml"); _project_arg(p); p.add_argument("--edl", default=None)
    p = sub.add_parser("build-applescript"); _project_arg(p)
    p = sub.add_parser("render", help="Render horizontal and vertical MP4 exports from the edit decision list")
    _project_arg(p)
    p.add_argument("--edl", default=None)
    p.add_argument("--horizontal-only", action="store_true")
    p.add_argument("--vertical-only", action="store_true")
    p = sub.add_parser("marketing-edit", help="Render an actually edited short-form marketing cut from source video highlights")
    _project_arg(p)
    p = sub.add_parser("open-in-fcp"); _project_arg(p)

    p = sub.add_parser("edit", help="One-command workflow: scan, transcribe, analyze, build FCPXML, render horizontal + vertical MP4s")
    _project_arg(p)
    p.add_argument("--format", default=None)
    p.add_argument("--engine", help="Override transcription engine")

    p = sub.add_parser("full", help="Alias for edit")
    _project_arg(p)
    p.add_argument("--format", default=None)
    p.add_argument("--engine", help="Override transcription engine")

    p = sub.add_parser("watch")
    p.add_argument("--projects-root", required=True)

    p = sub.add_parser("process-all", help="Process every project folder under the projects root that contains media")
    p.add_argument("--projects-root", required=True)
    p.add_argument("--format", default=None)
    p.add_argument("--engine", help="Override transcription engine")

    args = parser.parse_args(argv)
    config = load_config(args.config)
    if getattr(args, "engine", None):
        config.transcription_engine = args.engine

    if args.command == "setup-root":
        init_projects_root(args.projects_root)
    elif args.command == "init":
        init_project(args.project, raw_subfolders=args.raw_subfolders)
    elif args.command == "scan":
        scan_project(args.project, config)
    elif args.command == "transcribe":
        transcribe_project(args.project, config)
    elif args.command == "analyze":
        analyze_project(args.project, config)
    elif args.command == "build-edit":
        build_edit_decisions(args.project, args.format or config.default_edit_format, config)
    elif args.command == "build-fcpxml":
        build_fcpxml(args.project, args.edl)
    elif args.command == "build-applescript":
        build_applescript(args.project, config)
    elif args.command == "render":
        render_project(
            args.project,
            args.edl,
            render_horizontal=not args.vertical_only,
            render_vertical=not args.horizontal_only,
        )
    elif args.command == "marketing-edit":
        render_marketing_edits(args.project)
    elif args.command == "open-in-fcp":
        open_in_fcp(args.project, config)
    elif args.command in {"edit", "full"}:
        _run_edit(args.project, args.format or config.default_edit_format, config)
    elif args.command == "watch":
        watch_projects(args.projects_root, config)
    elif args.command == "process-all":
        process_all_projects(args.projects_root, config, args.format or config.default_edit_format)


if __name__ == "__main__":
    main()
