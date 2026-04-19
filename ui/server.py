import os
import uvicorn
import psutil
import asyncio
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config.settings import HUD_HOST, HUD_PORT

app = FastAPI()
static_dir = os.path.join(os.path.dirname(__file__), 'hud_dashboard')
app.mount('/static', StaticFiles(directory=static_dir), name='static')

# Global task queue for communication with orchestrator
task_queue = asyncio.Queue()

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

clients = set()

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # echo for now
            await websocket.send_text(data)
    except Exception:
        clients.remove(websocket)

async def broadcast_status(status):
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(status)
        except Exception:
            dead.append(ws)
    for d in dead:
        clients.discard(d)


async def _system_broadcaster():
    """Background task: periodically broadcast CPU/MEM and client count."""
    while True:
        try:
            status = {
                "cpu": psutil.cpu_percent(interval=None),
                "mem": psutil.virtual_memory().percent,
                "agents": "-",
                "clients": len(clients)
            }
            await broadcast_status(status)
        except Exception:
            pass
        await asyncio.sleep(2)


@app.on_event("startup")
async def _startup_broadcaster():
    asyncio.create_task(_system_broadcaster())

def run_server():
    uvicorn.run('ui.server:app', host=HUD_HOST, port=HUD_PORT, log_level='info')

if __name__ == '__main__':
    run_server()
