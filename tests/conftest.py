import subprocess
from pathlib import Path
import pytest

@pytest.fixture
def media_project(tmp_path: Path) -> Path:
    p=tmp_path/"project"; p.mkdir()
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","testsrc=size=320x180:rate=30000/1001","-f","lavfi","-i","sine=frequency=440:duration=1","-t","1","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",str(p/"clip.mp4")],check=True,capture_output=True)
    return p
