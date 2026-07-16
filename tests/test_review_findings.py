import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi.testclient import TestClient

from hermes_video.applescript_generator import build_applescript, latest_fcpxml
from hermes_video.config import AppConfig
from hermes_video.fcpxml_generator import export_timeline_fcpxml
from hermes_video.pipeline import ingest_project, plan_project, prepare
from hermes_video.review import create_app
from hermes_video.store import ProjectStore
from hermes_video.video_renderer import render_project


def test_fcpxml_does_not_export_unselected_alternates(media_project):
    prepare(media_project, AppConfig(transcription_engine="none"), "generic_rough_cut")
    store = ProjectStore(media_project)
    row = store.rows("timeline_version", "mode='aggressive'")[0]
    payload = row["payload"]
    keep = dict(payload["decisions"][0])
    alternate = dict(keep, id="alternate_take", action="alternate", timeline_position_seconds=payload["total_duration"], timeline_out=payload["total_duration"])
    payload["decisions"].append(alternate)
    store.upsert("timeline_version", {"id": row["id"], "project_id": row["project_id"], "mode": "aggressive", "status": "draft", "payload": payload})

    xml_path = export_timeline_fcpxml(media_project, "aggressive")
    root = ET.parse(xml_path).getroot()
    assert len(root.findall(".//spine/asset-clip")) == 1
    assert float(__import__("fractions").Fraction(root.find(".//sequence").get("duration").removesuffix("s"))) == payload["total_duration"]


def test_review_keeps_db_json_and_approved_timeline_consistent(media_project):
    prepare(media_project, AppConfig(transcription_engine="none"), "generic_rough_cut")
    store = ProjectStore(media_project)
    row = store.rows("timeline_version", "mode='conservative'")[0]
    payload = row["payload"]
    first = dict(payload["decisions"][0], id="first", in_seconds=0.0, out_seconds=0.4)
    second = dict(payload["decisions"][0], id="second", in_seconds=0.4, out_seconds=1.0)
    payload["decisions"] = [first, second]
    payload["total_duration"] = 1.0
    store.upsert("timeline_version", {"id": row["id"], "project_id": row["project_id"], "mode": "conservative", "status": "draft", "payload": payload})

    client = TestClient(create_app(media_project))
    assert client.post("/api/decision", json={"id": "first", "action": "move_down", "mode": "conservative"}).status_code == 200
    updated = store.rows("timeline_version", "mode='conservative'")[0]["payload"]
    assert [d["id"] for d in updated["decisions"]] == ["second", "first"]
    assert [d["timeline_position_seconds"] for d in updated["decisions"]] == [0.0, 0.6]
    assert updated["total_duration"] == 1.0
    exported_json = json.loads((media_project / "05_EDIT_DECISIONS/timeline_conservative.json").read_text())
    assert exported_json["decisions"] == updated["decisions"]

    assert client.post("/api/preferred", json={"mode": "conservative"}).status_code == 200
    approved_path = media_project / "05_EDIT_DECISIONS/timeline_approved.json"
    assert approved_path.exists()
    approved = json.loads(approved_path.read_text())
    assert approved["status"] == "approved"
    assert approved["total_duration"] == 1.0


def test_review_alternate_selection_replaces_full_source_range(media_project):
    prepare(media_project, AppConfig(transcription_engine="none"), "generic_rough_cut")
    store = ProjectStore(media_project)
    unit = store.rows("editorial_unit")[0]
    alternate = dict(unit["payload"], id="alternate_unit", start_seconds=0.25, end_seconds=0.75)
    store.upsert("editorial_unit", {"id": alternate["id"], "project_id": unit["project_id"], "media_asset_id": unit["media_asset_id"], "start": 0.25, "end": 0.75, "payload": alternate})
    row = store.rows("timeline_version", "mode='conservative'")[0]
    payload = row["payload"]
    payload["decisions"][0]["alternate_unit_ids"] = ["alternate_unit"]
    store.upsert("timeline_version", {"id": row["id"], "project_id": row["project_id"], "mode": "conservative", "status": "draft", "payload": payload})

    client = TestClient(create_app(media_project))
    decision_id = payload["decisions"][0]["id"]
    assert client.post("/api/decision", json={"id": decision_id, "action": "alternate", "mode": "conservative"}).status_code == 200
    selected = store.rows("timeline_version", "mode='conservative'")[0]["payload"]["decisions"][0]
    assert selected["editorial_unit_id"] == "alternate_unit"
    assert selected["in_seconds"] == 0.25
    assert selected["out_seconds"] == 0.75
    assert selected["media_asset_id"] == alternate["media_asset_id"]


def test_reingest_removes_deleted_assets_and_invalidates_replaced_transcript(media_project):
    cfg = AppConfig(transcription_engine="none")
    ingest_project(media_project, cfg)
    store = ProjectStore(media_project)
    asset = store.rows("media_asset")[0]
    store.upsert("transcript_word", {"id": "stale", "project_id": asset["project_id"], "media_asset_id": asset["id"], "start": 0.0, "end": 0.1, "payload": {"id": "stale"}})

    with (media_project / "clip.mp4").open("ab") as handle:
        handle.write(b"replacement-marker")
    ingest_project(media_project, cfg)
    assert store.rows("transcript_word", "media_asset_id=?", (asset["id"],)) == []

    (media_project / "clip.mp4").unlink()
    ingest_project(media_project, cfg)
    assert store.rows("media_asset") == []


def test_planning_uses_configured_budget_and_style_profile(media_project, monkeypatch):
    ingest_project(media_project, AppConfig(transcription_engine="none"))
    style_dir = media_project / ".hermes/style_profiles"
    style_dir.mkdir(parents=True)
    (style_dir / "custom.json").write_text(json.dumps({"name": "custom", "rules": {"target_average_clip_seconds": 4.2}, "source_comparisons": [{"automated": "a", "human_final": "b"}]}))
    captured = {}

    from hermes_video import pipeline
    original = pipeline.cached_analyze
    def capture(store, model, units, budget):
        captured["budget"] = budget
        return original(store, model, units, budget)
    monkeypatch.setattr(pipeline, "cached_analyze", capture)
    cfg = AppConfig(maximum_model_calls=7, maximum_project_tokens=321, maximum_project_cost_usd=2.5, maximum_retries=1)
    timelines = plan_project(media_project, "generic_rough_cut", style="custom", config=cfg)
    assert captured["budget"].max_calls == 7
    assert captured["budget"].max_tokens == 321
    assert captured["budget"].max_cost_usd == 2.5
    assert timelines["conservative"].model_metadata["style_rules"]["target_average_clip_seconds"] == 4.2
    assert timelines["conservative"].model_metadata["style_examples"][0]["automated"] == "a"


def test_applescript_selects_requested_timeline_not_newest(media_project):
    out = media_project / "06_FCPXML"
    out.mkdir(parents=True)
    approved = out / "project_approved_horizontal.fcpxml"
    aggressive = out / "project_aggressive_vertical.fcpxml"
    approved.write_text("<fcpxml/>")
    time.sleep(0.01)
    aggressive.write_text("<fcpxml/>")
    assert latest_fcpxml(media_project, "approved") == approved
    script = build_applescript(media_project, AppConfig(), "approved")
    assert str(approved) in script.read_text()


def test_optional_preview_renderer_accepts_v2_timeline_json(media_project):
    prepare(media_project, AppConfig(transcription_engine="none"), "generic_rough_cut")
    timeline = media_project / "05_EDIT_DECISIONS/timeline_conservative.json"
    outputs = render_project(media_project, timeline, render_horizontal=True, render_vertical=False)
    rendered = Path(outputs["horizontal"])
    assert rendered.exists() and rendered.stat().st_size > 0
