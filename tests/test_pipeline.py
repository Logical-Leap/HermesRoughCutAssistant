from hermes_video.config import AppConfig
from hermes_video.pipeline import ingest_project, prepare
from hermes_video.store import TABLES

def test_scan_and_checksum_cache(media_project):
    cfg=AppConfig(transcription_engine="none")
    first=ingest_project(media_project,cfg); second=ingest_project(media_project,cfg)
    assert first["asset_count"]==1
    assert second["cache_hits"]==1
    assert len(first["assets"][0]["checksum"])==64
    assert (media_project/".hermes/project.db").exists()
    assert {"project","media_asset","transcript_word","transcript_sentence","scene","audio_region","retake_group","editorial_unit","edit_decision","timeline_version"} <= set(TABLES)

def test_prepare_end_to_end_is_not_final_or_montage(media_project):
    result=prepare(media_project,AppConfig(transcription_engine="none"),"generic_rough_cut")
    assert result["status"]=="prepared_for_review" and result["final"] is False
    assert result["timelines"]==["conservative","aggressive"]
    assert not list((media_project/"08_EXPORTS").glob("*marketing*"))
    assert (media_project/"04_ANALYSIS/paper_edit.md").exists()
    assert (media_project/"04_ANALYSIS/continuity_report.md").exists()
