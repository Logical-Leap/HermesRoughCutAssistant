from __future__ import annotations

import argparse
from .config import load_config
from .project_scaffold import init_project
from .metadata_extractor import scan_project
from .transcription import transcribe_project
from .transcript_analyzer import analyze_project
from .edit_decision_builder import build_edit_decisions
from .fcpxml_generator import build_fcpxml
from .applescript_generator import build_applescript, open_in_fcp
from .folder_watcher import watch_projects


def _project_arg(parser):
    parser.add_argument("--project", required=True, help="Absolute or relative project folder path")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="Hermes Rough Cut Assistant")
    parser.add_argument("--config", help="Path to config JSON", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); _project_arg(p)
    p = sub.add_parser("scan"); _project_arg(p)
    p = sub.add_parser("transcribe"); _project_arg(p); p.add_argument("--engine", help="Override transcription engine")
    p = sub.add_parser("analyze"); _project_arg(p)
    p = sub.add_parser("build-edit"); _project_arg(p); p.add_argument("--format", default=None)
    p = sub.add_parser("build-fcpxml"); _project_arg(p); p.add_argument("--edl", default=None)
    p = sub.add_parser("build-applescript"); _project_arg(p)
    p = sub.add_parser("open-in-fcp"); _project_arg(p)
    p = sub.add_parser("full"); _project_arg(p); p.add_argument("--format", default=None); p.add_argument("--engine", help="Override transcription engine")
    p = sub.add_parser("watch"); p.add_argument("--projects-root", required=True)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if getattr(args, "engine", None):
        config.transcription_engine = args.engine
    if args.command == "init":
        init_project(args.project)
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
    elif args.command == "open-in-fcp":
        open_in_fcp(args.project, config)
    elif args.command == "full":
        init_project(args.project)
        scan_project(args.project, config)
        transcribe_project(args.project, config)
        analyze_project(args.project, config)
        build_edit_decisions(args.project, args.format or config.default_edit_format, config)
        build_fcpxml(args.project)
        build_applescript(args.project, config)
    elif args.command == "watch":
        watch_projects(args.projects_root, config)


if __name__ == "__main__":
    main()
