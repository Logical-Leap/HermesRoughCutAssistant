from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MediaAsset(BaseModel):
    id: str
    source_path: str
    relative_path: str
    file_name: str
    file_extension: str
    media_type: Literal["video", "audio", "image", "unknown"]
    duration_seconds: float
    frame_rate: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_stream_count: int = 0
    has_audio: bool = False
    creation_time: Optional[str] = None
    camera_group: Optional[str] = None
    checksum: str


class TranscriptSegment(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float = 0.0
    speaker_label: Optional[str] = None


class Transcript(BaseModel):
    media_asset_id: str
    source_path: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    language: str = "en"
    created_at: str = Field(default_factory=now_iso)


class HighlightCandidate(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    title: str
    reason: str
    score: float
    transcript_excerpt: str


class AnalysisReport(BaseModel):
    project_name: str
    created_at: str = Field(default_factory=now_iso)
    highlight_candidates: list[HighlightCandidate] = Field(default_factory=list)
    weak_sections: list[dict] = Field(default_factory=list)
    repeated_phrases: list[dict] = Field(default_factory=list)
    likely_hook_moments: list[HighlightCandidate] = Field(default_factory=list)
    suggested_structure: list[str] = Field(default_factory=list)
    suggested_clip_titles: list[str] = Field(default_factory=list)
    notes_for_broll: list[str] = Field(default_factory=list)
    recommended_rough_cut_sections: list[HighlightCandidate] = Field(default_factory=list)


class EditDecision(BaseModel):
    id: str
    media_asset_id: str
    source_path: str
    in_seconds: float
    out_seconds: float
    timeline_position_seconds: float
    decision_type: str
    reason: str
    title: str
    notes: str


class EditDecisionList(BaseModel):
    project_name: str
    format: str
    timeline_name: str
    decisions: list[EditDecision]
    total_estimated_duration_seconds: float
    created_at: str = Field(default_factory=now_iso)


class FinalCutProject(BaseModel):
    project_name: str
    timeline_name: str
    fcpxml_path: str
    edit_decision_list_path: str
    generated_at: str = Field(default_factory=now_iso)
