"""Loopback-first web service and privacy-minimised operational telemetry."""
import json
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from agent import build_agent
from trained_router import TrainedRouter
from sources import ROOT, SourceStore


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=600)
    nation: Literal["England", "Wales", "Scotland", "Northern Ireland"] = "England"


class Feedback(BaseModel):
    request_id: uuid.UUID
    helpful: bool


class Telemetry:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False); self.lock = threading.Lock()
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, at TEXT, status TEXT, latency_ms REAL, model_mode TEXT, source_errors INTEGER)")
            self.db.execute("CREATE TABLE IF NOT EXISTS feedback (request_id TEXT PRIMARY KEY REFERENCES requests(id), helpful INTEGER)")
    def record(self, ref, status, ms, mode, errors):
        with self.lock, self.db:
            self.db.execute("INSERT INTO requests VALUES (?,?,?,?,?,?)", (ref, datetime.now(timezone.utc).isoformat(), status, ms, mode, errors))
            # Bounded, local 30-day retention. No question, response, IP or identifiers.
            self.db.execute("DELETE FROM feedback WHERE request_id IN (SELECT id FROM requests WHERE julianday(at) < julianday('now','-30 days'))")
            self.db.execute("DELETE FROM requests WHERE julianday(at) < julianday('now','-30 days')")
    def feedback(self, ref, helpful):
        with self.lock, self.db:
            if not self.db.execute("SELECT 1 FROM requests WHERE id=?", (ref,)).fetchone(): return False
            self.db.execute("INSERT OR REPLACE INTO feedback VALUES (?,?)", (ref, int(helpful))); return True
    def metrics(self):
        with self.lock:
            count, errors, latency, failures = self.db.execute("SELECT COUNT(*),SUM(status IN ('source_problem','internal_error')),SUM(latency_ms),SUM(source_errors) FROM requests").fetchone()
            return {"requests_total": count, "problem_responses_total": errors or 0, "request_duration_ms_sum": latency or 0, "source_failures_total": failures or 0,
                    "feedback_total": self.db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]}


def create_app(store=None, router=None, db_path=None, rate_limit=20):
    store = store or SourceStore(os.getenv("DATA_MODE", "live"))
    # Explicit model opt-out is visible in every response, never advertised as LLM.
    router = router or TrainedRouter(enabled=os.getenv("LLM_ENABLED", "1") == "1")
    telemetry = Telemetry(db_path or os.getenv("TELEMETRY_DB", str(ROOT / "telemetry.sqlite3")))
    graph = build_agent(store, router)
    app = FastAPI(title="UK Student Copilot", docs_url="/docs")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
    app.state.telemetry = telemetry; app.state.router = router; app.state.store = store
    hits = defaultdict(deque); limiter_lock = threading.Lock()

    @app.middleware("http")
    async def protect(request: Request, call_next):
        from fastapi.responses import JSONResponse
        origin = request.headers.get("origin")
        if origin and origin not in ("http://localhost:8000", "http://127.0.0.1:8000", "http://testserver"):
            return JSONResponse({"detail": "Cross-origin request blocked"}, status_code=403)
        if request.method == "POST":
            # Read with a hard bound; Content-Length alone is not trusted.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 8192: return JSONResponse({"detail": "Request body too large"}, status_code=413)
            request._body = bytes(body)
            with limiter_lock:
                key = request.client.host if request.client else "unknown"; now = time.monotonic()
                for old in list(hits):
                    if not hits[old] or now-hits[old][-1] > 60: del hits[old]
                while hits[key] and now-hits[key][0] > 60: hits[key].popleft()
                if len(hits[key]) >= rate_limit: return JSONResponse({"detail": "Please wait before trying again"}, status_code=429, headers={"Retry-After": "60"})
                hits[key].append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index(): return FileResponse(ROOT / "static/index.html")

    @app.post("/api/ask")
    def ask(payload: Question):
        start = time.perf_counter(); ref = str(uuid.uuid4())
        try:
            state = graph.invoke({"question": payload.question.strip(), "nation": payload.nation})
            result = state["answer"]; mode = result.get("routing", {}).get("mode", "not_called")
            failures = sum(c["source"]["status"] != "verified" for c in result["cards"])
            elapsed = round((time.perf_counter()-start)*1000, 2)
            telemetry.record(ref, result["status"], elapsed, mode, failures)
            return {**result, "request_id": ref, "latency_ms": elapsed, "data_mode": store.mode}
        except Exception:
            telemetry.record(ref, "internal_error", round((time.perf_counter()-start)*1000, 2), "unknown", 0)
            raise HTTPException(503, {"message": "The assistant is temporarily unavailable. Contact your university support team.", "request_id": ref})

    @app.post("/api/feedback")
    def feedback(payload: Feedback):
        if not telemetry.feedback(str(payload.request_id), payload.helpful): raise HTTPException(404, "Unknown support reference")
        return {"saved": True}

    @app.get("/healthz")
    def health(): return {"status": "ok", "data_mode": store.mode, "llm_enabled": router.enabled, "llm_loaded": router.model is not None, "scope": "local prototype; not public production"}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics(): return "\n".join(f"student_copilot_{k} {v}" for k, v in telemetry.metrics().items()) + "\n"

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    return app


app = create_app()
