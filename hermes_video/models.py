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
    rotation_degrees: int = 0
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


class Project(BaseModel):
    id: str
    name: str
    path: str
    created_at: str = Field(default_factory=now_iso)


class TranscriptWord(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float = 0.0
    speaker_label: Optional[str] = None


class TranscriptSentence(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    text: str
    word_ids: list[str] = Field(default_factory=list)
    speaker_label: Optional[str] = None


class Scene(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    confidence: float = 0.0


class AudioRegion(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    kind: Literal["speech", "silence", "music", "clipping", "noise", "applause", "unknown"]


class RetakeGroup(BaseModel):
    id: str
    unit_ids: list[str]
    preferred_unit_id: str
    alternate_unit_ids: list[str] = Field(default_factory=list)
    reason: str


class EditorialUnit(BaseModel):
    id: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    text: str = ""
    transcript_sentence_ids: list[str] = Field(default_factory=list)
    scene_ids: list[str] = Field(default_factory=list)
    audio_region_ids: list[str] = Field(default_factory=list)
    topic: str = "general"
    purpose: str = "support"
    confidence: float = 0.0
    complete: bool = True


DecisionAction = Literal["keep", "trim", "remove", "reorder", "alternate", "short_candidate", "broll_placeholder"]
TimelineMode = Literal["conservative", "aggressive", "short_vertical", "short_horizontal", "human_final"]


class V2EditDecision(BaseModel):
    id: str
    editorial_unit_id: str
    action: DecisionAction
    reason: str
    source_path: str = ""
    media_asset_id: str = ""
    in_seconds: float = 0.0
    out_seconds: float = 0.0
    timeline_position_seconds: float = 0.0
    alternate_unit_ids: list[str] = Field(default_factory=list)
    approved: Optional[bool] = None
    notes: str = ""


class TimelineVersion(BaseModel):
    id: str
    project_id: str
    mode: TimelineMode
    status: Literal["draft", "preferred", "approved", "exported"] = "draft"
    format: str = "youtube_longform"
    target_duration_seconds: Optional[float] = None
    decisions: list[V2EditDecision] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class ShortCandidate(BaseModel):
    id: str
    orientation: Literal["vertical", "horizontal"]
    title: str
    hook: str
    caption: str
    description: str
    media_asset_id: str
    start_seconds: float
    end_seconds: float
    confidence: float = Field(ge=0, le=1)
    context_warning: str = ""
    reframe_notes: str = "Center crop is a preview; verify subject framing manually."
