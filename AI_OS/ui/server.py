import os
import sys
import json
import uvicorn
import psutil
import asyncio
import threading
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import HUD_HOST, HUD_PORT, GROQ_API_KEY, GROQ_MODEL

app = FastAPI(title="YALI AI OS")
static_dir = os.path.join(os.path.dirname(__file__), 'hud_dashboard')
app.mount('/static', StaticFiles(directory=static_dir), name='static')

# Global queues
task_queue = asyncio.Queue()
mind_clients = set()   # YALI MIND WebSocket connections
clients = set()         # general WS connections

# Conversation history for YALI MIND context
_mind_conversation: list = []


# ─── Core Routes ───────────────────────────────────────────────────────────────

@app.get('/')
async def index():
    return FileResponse(os.path.join(static_dir, 'index.html'))


@app.post('/submit-task')
async def submit_task(request: Request):
    data = await request.json()
    task = data.get('task', '').strip()
    if task:
        await task_queue.put(task)
        return {"status": "ok", "message": f"Task queued: {task}"}
    return {"status": "error", "message": "Empty task"}


# ─── YALI MIND REST API ────────────────────────────────────────────────────────

@app.post('/mind/answer')
async def mind_answer(request: Request):
    """Generate structured answer for an interview question."""
    data = await request.json()
    question = data.get('question', '').strip()
    if not question:
        return JSONResponse({"error": "No question provided"}, status_code=400)

    from modules.cognitive.answer_engine import generate_answer_sync
    from modules.cognitive.intent_classifier import classify_intent, get_response_framework

    intent, conf, label = classify_intent(question)
    framework = get_response_framework(intent)

    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: generate_answer_sync(question, _mind_conversation)
    )

    # Add to conversation history
    _mind_conversation.append({"role": "user", "content": question})
    _mind_conversation.append({"role": "assistant", "content": result.get("full_text", "")})
    if len(_mind_conversation) > 20:
        _mind_conversation.pop(0)
        _mind_conversation.pop(0)

    # Broadcast to MIND WebSocket clients
    await _broadcast_mind({
        "type": "answer",
        "question": question,
        "intent": label,
        "framework": framework,
        "opening": result.get("opening", ""),
        "bullets": result.get("bullets", []),
        "example": result.get("example", ""),
        "keywords": result.get("keywords", []),
    })

    return JSONResponse(result)


@app.post('/mind/analyze')
async def mind_analyze(request: Request):
    """Analyze a transcript for speech quality metrics."""
    data = await request.json()
    transcript = data.get('transcript', '').strip()
    duration = data.get('duration', 0)
    question = data.get('question', '')

    if not transcript:
        return JSONResponse({"error": "No transcript provided"}, status_code=400)

    from modules.cognitive.speech_analyzer import analyze_transcript
    metrics = analyze_transcript(transcript, duration_seconds=duration)

    result = metrics.to_dict()
    result["question"] = question

    await _broadcast_mind({"type": "analysis", **result})
    return JSONResponse(result)


@app.get('/mind/questions')
async def mind_questions(area: str = "all", count: int = 10):
    """Get practice questions for a given area."""
    from modules.cognitive.practice_mode import PracticeSession
    session = PracticeSession()
    areas = None if area == "all" else [area]
    questions = session.get_question_list(areas=areas, count=count)
    return JSONResponse({"questions": questions})


@app.post('/mind/parse-resume')
async def mind_parse_resume(request: Request):
    """Parse an uploaded resume and build user profile."""
    from modules.cognitive.resume_parser import parse_resume, USER_PROFILE_PATH
    import tempfile

    form = await request.form()
    if 'resume' not in form:
        # Try to parse existing resume at default path
        profile = await asyncio.get_event_loop().run_in_executor(None, parse_resume)
        if profile:
            return JSONResponse({"status": "ok", "profile": profile})
        return JSONResponse({"error": "No resume file. Upload a PDF."}, status_code=400)

    file = form['resume']
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    profile = await asyncio.get_event_loop().run_in_executor(
        None, lambda: parse_resume(tmp_path)
    )
    tmp_path.unlink(missing_ok=True)

    if not profile:
        return JSONResponse({"error": "Could not parse resume"}, status_code=422)

    return JSONResponse({"status": "ok", "profile": profile})


@app.get('/mind/profile')
async def mind_profile():
    """Get the current user profile."""
    from modules.cognitive.resume_parser import load_profile
    profile = load_profile()
    if not profile:
        return JSONResponse({"error": "No profile loaded. Upload your resume first."}, status_code=404)
    return JSONResponse(profile)


@app.get('/mind/status')
async def mind_status():
    """Health check for YALI MIND."""
    return JSONResponse({
        "status": "ok",
        "groq_configured": bool(GROQ_API_KEY),
        "conversation_turns": len(_mind_conversation) // 2,
        "model": GROQ_MODEL,
    })


# ─── YALI MIND WebSocket ────────────────────────────────────────────────────────

@app.websocket('/mind/ws')
async def mind_websocket(websocket: WebSocket):
    """WebSocket for real-time YALI MIND streaming."""
    await websocket.accept()
    mind_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "question":
                question = msg.get("question", "").strip()
                if question:
                    asyncio.create_task(_stream_answer_to_ws(question, websocket))

            elif msg.get("type") == "clear_history":
                _mind_conversation.clear()
                await websocket.send_json({"type": "history_cleared"})

    except Exception:
        mind_clients.discard(websocket)


async def _stream_answer_to_ws(question: str, websocket: WebSocket):
    """Stream answer tokens to a specific WebSocket client."""
    from modules.cognitive.answer_engine import generate_answer_streaming
    from modules.cognitive.intent_classifier import classify_intent, get_response_framework

    intent, conf, label = classify_intent(question)
    framework = get_response_framework(intent)

    await websocket.send_json({
        "type": "answer_start",
        "question": question,
        "intent": label,
        "framework": framework,
    })

    collected = []

    def on_chunk(text, section):
        collected.append(text)
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({"type": "answer_chunk", "text": text, "section": section}),
            asyncio.get_event_loop()
        )

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: generate_answer_streaming(question, on_chunk, _mind_conversation)
    )

    await websocket.send_json({"type": "answer_end"})


async def _broadcast_mind(data: dict):
    dead = []
    for ws in list(mind_clients):
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for d in dead:
        mind_clients.discard(d)


# ─── General WebSocket ─────────────────────────────────────────────────────────

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)
    except Exception:
        clients.discard(websocket)


async def broadcast_status(status):
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(status)
        except Exception:
            dead.append(ws)
    for d in dead:
        clients.discard(d)


# ─── Background Tasks ──────────────────────────────────────────────────────────

_ticker_tick = 0

async def _system_broadcaster():
    global _ticker_tick
    while True:
        try:
            status = {
                "type": "system",
                "cpu": psutil.cpu_percent(interval=None),
                "mem": psutil.virtual_memory().percent,
                "agents": "-",
                "clients": len(clients),
                "mind_clients": len(mind_clients),
            }
            await broadcast_status(status)

            # Push ticker every 5 min (150 × 2s ticks)
            _ticker_tick += 1
            if _ticker_tick >= 150:
                _ticker_tick = 0
                try:
                    from tools.finance_tool import get_market_overview
                    overview = get_market_overview()
                    await broadcast_status({"type": "ticker", "data": overview})
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(2)


# ─── JOB ENGINE API ───────────────────────────────────────────────────────────

@app.post('/jobs/search')
async def jobs_search(request: Request):
    data = await request.json()
    query = data.get('query', '').strip()
    location = data.get('location', '')
    sources = data.get('sources', ['indeed', 'linkedin', 'naukri'])
    max_per = data.get('max_per_source', 10)
    min_score = data.get('min_score', 60)

    if not query:
        return JSONResponse({"error": "No query provided"}, status_code=400)

    from modules.job.job_scraper import search_jobs
    from modules.job.job_scorer import score_jobs_batch

    jobs = await search_jobs(query, location, sources, max_per)
    job_dicts = [j.to_dict() for j in jobs]
    scored = score_jobs_batch(job_dicts, min_score=min_score)

    await _broadcast_mind({"type": "jobs_found", "count": len(scored), "query": query})
    return JSONResponse({"jobs": scored, "total": len(scored)})


@app.get('/jobs/cached')
async def jobs_cached(min_score: int = 0):
    from modules.job.job_scraper import load_cached_jobs
    from modules.job.job_scorer import score_jobs_batch
    jobs = load_cached_jobs()
    if min_score > 0:
        jobs = score_jobs_batch(jobs, min_score=min_score)
    return JSONResponse({"jobs": jobs, "total": len(jobs)})


@app.post('/jobs/tailor')
async def jobs_tailor(request: Request):
    data = await request.json()
    jd_text = data.get('jd_text', '')
    company = data.get('company', 'Company')
    role = data.get('role', 'Role')

    if not jd_text:
        return JSONResponse({"error": "No JD text"}, status_code=400)

    from modules.job.resume_tailorer import tailor_for_job
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: tailor_for_job(jd_text, company, role)
    )
    return JSONResponse(result)


@app.post('/jobs/apply')
async def jobs_apply(request: Request):
    data = await request.json()
    job = data.get('job', {})
    resume_pdf = data.get('resume_pdf_path', None)

    if not job:
        return JSONResponse({"error": "No job provided"}, status_code=400)

    from modules.job.auto_applier import apply_linkedin_easy_apply, apply_indeed_quick_apply
    source = job.get('source', '')
    url = job.get('apply_url', '')
    job_id = job.get('job_id', str(hash(url)))
    company = job.get('company', 'Unknown')
    role = job.get('title', 'Unknown')

    if source == 'linkedin':
        result = await apply_linkedin_easy_apply(url, job_id, company, role, resume_pdf)
    elif source == 'indeed':
        result = await apply_indeed_quick_apply(url, job_id, company, role, resume_pdf)
    else:
        result = {"status": "skipped", "message": f"Auto-apply not supported for {source}"}

    return JSONResponse(result)


@app.get('/jobs/tracker')
async def jobs_tracker_list(status: str = ""):
    from modules.job.tracker import get_tracker
    tracker = get_tracker()
    apps = tracker.get_all(status=status if status else None)
    stats = tracker.get_stats()
    return JSONResponse({"applications": apps, "stats": stats})


@app.patch('/jobs/tracker/{job_id}')
async def jobs_tracker_update(job_id: str, request: Request):
    data = await request.json()
    status = data.get('status', '')
    notes = data.get('notes', '')
    from modules.job.tracker import get_tracker
    tracker = get_tracker()
    ok = tracker.update_status(job_id, status, notes)
    return JSONResponse({"ok": ok})


@app.post('/jobs/followup')
async def jobs_followup(request: Request):
    data = await request.json()
    dry_run = data.get('dry_run', True)
    from modules.job.followup import run_followup_check
    results = await asyncio.get_event_loop().run_in_executor(
        None, lambda: run_followup_check(dry_run=dry_run)
    )
    return JSONResponse({"followups": results, "count": len(results)})


@app.get('/jobs/followup/draft/{job_id}')
async def jobs_followup_draft(job_id: str):
    from modules.job.tracker import get_tracker
    from modules.job.followup import draft_followup_email
    tracker = get_tracker()
    apps = tracker.search(job_id)
    if not apps:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    app = apps[0]
    draft = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: draft_followup_email(
            app['company'], app['title'],
            app['applied_date'], app['follow_up_count']
        )
    )
    return JSONResponse({"draft": draft, "job": app})


# ─── FINANCE API ──────────────────────────────────────────────────────────────

@app.get('/finance/overview')
async def finance_overview():
    from tools.finance_tool import get_market_overview
    data = get_market_overview()
    return JSONResponse(data)


@app.get('/finance/news')
async def finance_news(q: str = "Indian stock market NSE Nifty", n: int = 5):
    from tools.finance_tool import get_news
    news = get_news(query=q, n=n)
    return JSONResponse({"news": news})


@app.post('/finance/brief')
async def finance_brief():
    from core.agents.finance_agent import FinanceAgent
    agent = FinanceAgent()
    result = await agent.handle("market brief")
    return JSONResponse({"brief": result})


@app.post('/finance/predict')
async def finance_predict(request: Request):
    data = await request.json()
    question = data.get('question', '').strip()
    if not question:
        return JSONResponse({"error": "No question provided"}, status_code=400)
    from core.agents.finance_agent import FinanceAgent
    agent = FinanceAgent()
    result = await agent.handle(question)
    return JSONResponse({"prediction": result})


@app.get('/finance/predictions')
async def finance_predictions():
    from core.memory import recall_all
    mem = recall_all()
    preds = mem.get("predictions", [])
    return JSONResponse({"predictions": list(reversed(preds[-10:]))})


@app.post('/chat')
async def chat(request: Request):
    """Direct LLM chat — returns answer immediately. Used by Assistant panel."""
    data = await request.json()
    cmd = data.get('message', '').strip()
    if not cmd:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    from core.llm_client import ask
    from core.memory import get_context, write, auto_tag

    # Route finance queries through finance agent
    finance_kw = ['market','stock','nifty','sensex','predict','forecast','invest','price','trading','bse','nse']
    if any(k in cmd.lower() for k in finance_kw):
        from core.agents.finance_agent import FinanceAgent
        agent = FinanceAgent()
        result = await agent.handle(cmd)
    else:
        ctx = get_context()
        result = ask(user_prompt=cmd, memory_context=ctx, max_tokens=600)
        if not result:
            result = "I couldn't process that command. Try again."

    write(cmd, result, agent="assistant")
    auto_tag(cmd, result)
    return JSONResponse({"reply": result})


@app.get('/memory/recall')
async def memory_recall():
    from core.memory import recall_all, _load
    lt = recall_all()
    data = _load()
    return JSONResponse({**lt, "mid_term": data.get("mid_term", [])[-20:]})


@app.get('/finance/price/{symbol}')
async def finance_price(symbol: str):
    from tools.finance_tool import get_price
    data = get_price(symbol.upper())
    return JSONResponse(data)


# ─── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup():
    asyncio.create_task(_system_broadcaster())

    # Start follow-up scheduler
    try:
        from modules.job.followup import start_scheduler
        start_scheduler()
    except Exception:
        pass

    print("[YALI] Server started. YALI MIND + Job Engine ready.")
    print(f"[YALI] Groq API: {'configured' if GROQ_API_KEY else 'NOT configured - add GROQ_API_KEY to .env (free at console.groq.com)'}")


def run_server():
    uvicorn.run('ui.server:app', host=HUD_HOST, port=HUD_PORT, log_level='info', reload=False)


if __name__ == '__main__':
    run_server()
