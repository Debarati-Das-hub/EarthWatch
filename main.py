from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime
import os, asyncio, json

import pipeline
from config import MAPBOX_TOKEN

app = FastAPI(title="EarthWatch India", version="2.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

from fastapi import WebSocket, WebSocketDisconnect
ws_clients = []


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


@app.get("/api/incidents")
async def get_incidents():
    incidents = pipeline.get_incidents()
    return {
        "count":     len(incidents),
        "last_run":  pipeline.get_last_run(),
        "incidents": incidents,
    }


@app.get("/api/stats")
async def get_stats():
    incidents = pipeline.get_incidents()
    by_type   = {}
    for inc in incidents:
        t = inc.get("type", "other")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total":     len(incidents),
        "critical":  sum(1 for i in incidents if i.get("severity", 0) >= 7),
        "by_type":   by_type,
        "last_run":  pipeline.get_last_run(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/run")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_and_broadcast)
    return {"message": "Pipeline started", "status": "running"}


async def run_and_broadcast():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, pipeline.run)
    msg = json.dumps({"type": "refresh"})
    for ws in ws_clients[:]:
        try:
            await ws.send_text(msg)
        except:
            ws_clients.remove(ws)


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in ws_clients:
            ws_clients.remove(ws)


@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "incidents": len(pipeline.get_incidents()),
        "last_run":  pipeline.get_last_run(),
        "time":      datetime.utcnow().isoformat()
    }


@app.on_event("startup")
async def startup():
    print("\n🚀 EarthWatch India starting...")
    pipeline.start_auto_refresh(interval_minutes=5)
