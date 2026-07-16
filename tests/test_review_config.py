from pathlib import Path

from fastapi.testclient import TestClient

from hermes_video.config import AppConfig, load_config
from hermes_video.pipeline import prepare
from hermes_video.review import create_app
from hermes_video.store import ProjectStore


def test_prepare_creates_short_timelines_and_review_approval(media_project):
    prepare(media_project, AppConfig(transcription_engine="none"), "generic_rough_cut")
    store = ProjectStore(media_project)
    modes = {row["mode"] for row in store.rows("timeline_version")}
    assert {"conservative", "aggressive", "short_vertical", "short_horizontal"} <= modes

    client = TestClient(create_app(media_project))
    timeline = client.get("/api/timeline?mode=conservative")
    assert timeline.status_code == 200
    decision = timeline.json()["decisions"][0]
    assert decision["media_url"].startswith("/api/media/")
    assert client.get(decision["media_url"]).status_code == 200
    assert client.post("/api/decision", json={"id": decision["id"], "action": "approve", "mode": "conservative"}).status_code == 200
    approved = client.post("/api/preferred", json={"mode": "conservative"})
    assert approved.status_code == 200
    payload = client.get("/api/timeline?mode=approved").json()
    assert payload["status"] == "approved"


def test_toml_loads_budget_and_safe_defaults(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("""
[transcription]
engine = "none"
model = "tiny"
[editorial]
maximum_project_tokens = 321
maximum_total_model_calls = 7
maximum_project_cost_usd = 2.5
[rendering]
enabled_by_default = false
""")
    loaded = load_config(config)
    assert loaded.transcription_engine == "none"
    assert loaded.whisper_model == "tiny"
    assert loaded.maximum_project_tokens == 321
    assert loaded.maximum_model_calls == 7
    assert loaded.maximum_project_cost_usd == 2.5
    assert loaded.rendering_enabled_by_default is False
