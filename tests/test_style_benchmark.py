import json
from pathlib import Path
from hermes_video.benchmark import evaluate, init_benchmark, record_baseline
from hermes_video.style import compare_timelines, learn_edit, list_styles

XML='''<?xml version="1.0"?><fcpxml><resources/><library><event><project><sequence><spine><asset-clip ref="r1" start="0s" duration="10s" offset="0s"/></spine></sequence></project></event></library></fcpxml>'''
def test_style_timeline_comparison_and_generation(tmp_path):
    project=tmp_path/"p"; project.mkdir(); a=tmp_path/"a.fcpxml"; h=tmp_path/"h.fcpxml"; a.write_text(XML); h.write_text(XML)
    assert compare_timelines(a,h)["exact_select_retention"]==1
    profile=learn_edit(project,a,h)
    assert profile.exists() and list_styles(project)==["chandler_default"]

def test_benchmark_thresholds_fail_honestly(tmp_path):
    p=tmp_path/"p"; p.mkdir(); init_benchmark(p); record_baseline(p,100,10,10)
    failed=evaluate(p,70,1,6,1)
    assert failed["passed"] is False
    assert len(failed["failures"])==3
    passed=evaluate(p,50,1,8,0)
    assert passed["passed"] is True
