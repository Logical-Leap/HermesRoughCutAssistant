from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from hermes_video.config import AppConfig
from hermes_video.fcpxml_generator import export_timeline_fcpxml, frame_duration, validate_fcpxml
from hermes_video.pipeline import prepare

def test_supported_rational_timebases():
    expected={23.976:"1001/24000s",24:"1/24s",25:"1/25s",29.97:"1001/30000s",30:"1/30s",50:"1/50s",59.94:"1001/60000s",60:"1/60s"}
    assert {fps:frame_duration(fps) for fps in expected}==expected
    with pytest.raises(ValueError): frame_duration(27)

def test_horizontal_vertical_resources_and_validation(media_project):
    prepare(media_project,AppConfig(transcription_engine="none"),"generic_rough_cut")
    for orientation,dims in (("horizontal",("1920","1080")),("vertical",("1080","1920"))):
        out=export_timeline_fcpxml(media_project,"conservative",orientation)
        validate_fcpxml(out)
        fmt=ET.parse(out).getroot().find("resources/format")
        assert (fmt.get("width"),fmt.get("height"))==dims
        assert ET.parse(out).find(".//spine/asset-clip") is not None

def test_missing_media_is_not_hidden(media_project):
    prepare(media_project,AppConfig(transcription_engine="none"),"generic_rough_cut")
    (media_project/"clip.mp4").unlink()
    with pytest.raises(FileNotFoundError,match="Missing media"):
        export_timeline_fcpxml(media_project,"conservative")
