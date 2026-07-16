from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .models import TimelineVersion
from .store import ProjectStore


class ReviewAction(BaseModel):
    id: str
    action: str
    notes: str = ""
    mode: str = "conservative"


class PreferredTimeline(BaseModel):
    mode: str

HTML = """<!doctype html><meta charset='utf-8'><title>Hermes Review</title>
<style>body{font:15px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}nav,article{border:1px solid #ddd;padding:1rem;margin:.6rem 0;border-radius:8px}.removed{opacity:.55}button,select{margin:.2rem;padding:.35rem}audio,video{max-width:100%;width:520px}.text{font-size:1.05rem;margin:.5rem 0}</style>
<h1>Assistant-editor rough-cut review</h1><p>This is a paper edit, not a finished professional edit.</p>
<nav><label>Timeline <select id='mode' onchange='load()'><option>conservative</option><option>aggressive</option><option>approved</option></select></label><button onclick="preferred()">Select as preferred/approved</button><button onclick="showTranscript()">Transcript</button></nav>
<div id='notice'></div><div id='items'></div>
<script>
async function load(){let r=await fetch('/api/timeline?mode='+mode.value);if(!r.ok){notice.textContent=await r.text();items.innerHTML='';return}let d=await r.json();notice.textContent=`${d.mode} · ${d.status} · ${d.total_duration||0}s`;items.innerHTML=d.decisions.map((x,i)=>`<article class='${x.action==='remove'?'removed':''}'><b>${i+1}. ${x.action}</b> <code>${x.editorial_unit_id}</code><div>${x.in_seconds.toFixed(3)}–${x.out_seconds.toFixed(3)} · confidence ${x.confidence}</div><div class='text'>${x.transcript_text||''}</div><div>${x.reason}</div>${x.media_url?`<video controls preload='metadata' src='${x.media_url}#t=${x.in_seconds},${x.out_seconds}'></video>`:''}<br><button onclick="act('${x.id}','approve')">Approve</button><button onclick="act('${x.id}','reject')">Reject</button><button onclick="act('${x.id}','restore')">Restore</button><button onclick="act('${x.id}','alternate')">Alternate take</button><button onclick="act('${x.id}','move_up')">Move up</button><button onclick="act('${x.id}','move_down')">Move down</button><button onclick="act('${x.id}','broll')">B-roll note</button></article>`).join('')}
async function act(id,action){let notes=prompt('Notes (optional)')||'';await fetch('/api/decision',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id,action,notes,mode:mode.value})});load()}
async function preferred(){await fetch('/api/preferred',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({mode:mode.value})});mode.value='approved';load()}
async function showTranscript(){let d=await(await fetch('/api/transcript')).json();items.innerHTML=d.sentences.map(x=>`<article><code>${x.start_seconds.toFixed(3)}–${x.end_seconds.toFixed(3)}</code><div class='text'>${x.text}</div></article>`).join('')}
load()</script>"""


def create_app(project: str | Path):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import FileResponse, HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Review UI requires fastapi and uvicorn") from exc

    path = Path(project).expanduser().resolve()
    store = ProjectStore(path)
    app = FastAPI(title="Hermes Assistant Editor Review")

    def timeline_row(mode: str) -> dict[str, Any]:
        rows = store.rows("timeline_version", "mode=?", (mode,))
        if not rows and mode == "approved":
            rows = store.rows("timeline_version", "status='approved'")
        if not rows:
            raise HTTPException(404, f"No {mode} timeline; run plan first")
        return rows[-1]

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTML

    @app.get("/api/timeline")
    def timeline(mode: str = "conservative"):
        row = timeline_row(mode)
        payload = row["payload"]
        units = {r["id"]: r["payload"] for r in store.rows("editorial_unit")}
        assets = {r["id"]: r["payload"] for r in store.rows("media_asset")}
        decisions = []
        for decision in payload["decisions"]:
            item = dict(decision)
            item["transcript_text"] = units.get(item["editorial_unit_id"], {}).get("text", "")
            if item.get("media_asset_id") in assets:
                item["media_url"] = f"/api/media/{item['media_asset_id']}"
            decisions.append(item)
        return {**payload, "decisions": decisions}

    @app.get("/api/transcript")
    def transcript():
        return {"sentences": [r["payload"] for r in store.rows("transcript_sentence")]}

    @app.get("/api/media/{asset_id}")
    def media(asset_id: str):
        rows = store.rows("media_asset", "id=?", (asset_id,))
        if not rows:
            raise HTTPException(404, "Unknown media")
        source = Path(rows[0]["payload"]["source_path"])
        if not source.exists():
            raise HTTPException(404, "Media is missing")
        return FileResponse(source)

    @app.post("/api/decision")
    def decision(action: ReviewAction):
        allowed = {"approve", "reject", "alternate", "restore", "move_up", "move_down", "note", "broll"}
        if action.action not in allowed:
            raise HTTPException(400, "Invalid action")
        row = timeline_row(action.mode)
        project_id = row["project_id"]
        store.upsert("approval", {"id": f"{row['id']}:{action.id}", "project_id": project_id, "timeline_id": row["id"], "decision_id": action.id, "action": action.action, "notes": action.notes, "payload": action.model_dump()})
        payload = row["payload"]
        decisions = payload["decisions"]
        index = next((i for i, item in enumerate(decisions) if item["id"] == action.id), None)
        if index is None:
            raise HTTPException(404, "Unknown decision")
        if action.action == "reject": decisions[index]["action"] = "remove"
        elif action.action in {"restore", "approve"}: decisions[index]["action"] = "keep"; decisions[index]["approved"] = True
        elif action.action == "alternate" and decisions[index].get("alternate_unit_ids"): decisions[index]["editorial_unit_id"] = decisions[index]["alternate_unit_ids"][0]
        elif action.action == "broll": decisions[index]["notes"] = (decisions[index].get("notes", "") + "; B-roll required: " + action.notes).strip("; ")
        elif action.action == "move_up" and index > 0: decisions[index - 1], decisions[index] = decisions[index], decisions[index - 1]
        elif action.action == "move_down" and index < len(decisions) - 1: decisions[index + 1], decisions[index] = decisions[index], decisions[index + 1]
        store.upsert("timeline_version", {"id": row["id"], "project_id": project_id, "mode": payload["mode"], "status": payload["status"], "payload": payload})
        return {"saved": True}

    @app.post("/api/preferred")
    def preferred(request: PreferredTimeline):
        row = timeline_row(request.mode)
        payload = dict(row["payload"])
        payload.update({"id": f"{row['project_id']}_approved", "mode": "human_final", "status": "approved", "version_name": "approved_v2"})
        approved = TimelineVersion.model_validate(payload)
        store.upsert("timeline_version", {"id": approved.id, "project_id": approved.project_id, "mode": approved.mode, "status": approved.status, "payload": approved.model_dump()})
        return {"saved": True, "timeline": approved.id}

    return app


def serve_review(project: str | Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Review UI requires fastapi and uvicorn") from exc
    uvicorn.run(create_app(project), host=host, port=port)
