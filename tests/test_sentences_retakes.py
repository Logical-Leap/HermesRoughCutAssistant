from hermes_video.sentences import refine_boundary, words_to_sentences
from hermes_video.retakes import group_retakes

def _w(i,start,end,text): return {"id":f"w{i}","media_asset_id":"a","start_seconds":start,"end_seconds":end,"text":text,"confidence":.9}

def test_words_to_sentences_uses_punctuation_and_pauses():
    words=[_w(1,0,.2,"Hello"),_w(2,.2,.5,"world."),_w(3,2,2.3,"Next"),_w(4,2.3,2.6,"clause")]
    sentences=words_to_sentences(words)
    assert [s["text"] for s in sentences]==["Hello world.","Next clause"]
    assert sentences[0]["end_seconds"]==.5

def test_boundary_refinement_never_mid_word():
    words=[_w(1,0,.4,"one"),_w(2,.6,1,"two")]
    assert refine_boundary(.25,words,"start") in {0,.6}
    assert refine_boundary(.8,words,"end") in {.4,1}

def test_duplicate_retakes_preserve_alternates():
    units=[{"id":"u1","text":"This is the complete answer","confidence":.8},{"id":"u2","text":"this is the complete answer","confidence":.9}]
    groups=group_retakes(units)
    assert groups[0]["preferred_unit_id"]=="u2"
    assert groups[0]["alternate_unit_ids"]==["u1"]
