from __future__ import annotations
from pathlib import Path
from .store import ProjectStore

HTML = """<!doctype html><meta charset='utf-8'><title>Hermes Review</title><style>body{font:16px system-ui;max-width:960px;margin:2rem auto}article{border:1px solid #ddd;padding:1rem;margin:.5rem}button{margin:.2rem}</style><h1>Assistant rough-cut review</h1><p>This is not a final professional edit.</p><div id='items'></div><script>async function load(){let d=await(await fetch('/api/timeline')).json();items.innerHTML=d.decisions.map(x=>`<article><b>${x.action}</b> ${x.editorial_unit_id}<br>${x.reason}<br><button onclick="act('${x.id}','approve')">Approve</button><button onclick="act('${x.id}','reject')">Reject</button><button onclick="act('${x.id}','restore')">Restore</button></article>`).join('')}async function act(id,action){let notes=prompt('Notes (optional)')||'';await fetch('/api/decision',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id,action,notes})});load()}load()</script>"""

def create_app(project: str | Path):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse
        from pydantic import BaseModel
    except ImportError as exc:
        raise RuntimeError("Review UI requires optional dependencies: pip install fastapi uvicorn") from exc
    path = Path(project).expanduser().resolve(); store = ProjectStore(path)
    app = FastAPI(title="Hermes Assistant Editor Review")
    class Action(BaseModel):
        id: str; action: str; notes: str = ""
    @app.get("/", response_class=HTMLResponse)
    def index(): return HTML
    @app.get("/api/timeline")
    def timeline():
        rows = store.rows("timeline_version", "mode='conservative'")
        if not rows: raise HTTPException(404, "Run plan first")
        return rows[-1]["payload"]
    @app.post("/api/decision")
    def decision(action: Action):
        if action.action not in {"approve", "reject", "alternate", "restore", "reorder", "note", "broll", "preferred_timeline", "export"}: raise HTTPException(400, "Invalid action")
        timeline = store.rows("timeline_version", "mode='conservative'")[-1]
        project_id = timeline["project_id"]
        store.upsert("approval", {"id": f"{timeline['id']}:{action.id}", "project_id": project_id, "timeline_id": timeline["id"], "decision_id": action.id, "action": action.action, "notes": action.notes, "payload": action.model_dump()})
        return {"saved": True}
    return app

def serve_review(project: str | Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    try: import uvicorn
    except ImportError as exc: raise RuntimeError("Review UI requires optional dependencies: pip install fastapi uvicorn") from exc
    uvicorn.run(create_app(project), host=host, port=port)
