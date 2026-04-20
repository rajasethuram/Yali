import threading
import asyncio
import logging
import time
from core.wakeword_engine import WakeWordEngine
from core.orchestrator import Orchestrator
from core.text_to_speech import speak
from ui.server import run_server, task_queue

logging.basicConfig(filename='logs/system.log', level=logging.INFO)
logger = logging.getLogger('yali')

orc = Orchestrator()

async def task_processor():
    """Background task that processes tasks from the web interface queue"""
    while True:
        try:
            task = await asyncio.wait_for(task_queue.get(), timeout=1.0)
            if task:
                logger.info(f"Processing task from queue: {task}")
                await orc.handle_task(task)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Task processor error: {e}")
            await asyncio.sleep(0.5)

def start_ui_and_task_processor():
    """Run UI server and task processor in the event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_all():
        # Start task processor
        task_proc = asyncio.create_task(task_processor())
        
        # Run the server (this will block)
        await asyncio.gather(task_proc)
    
    loop.run_until_complete(run_all())

def start_ui():
    run_server()

def main():
    # start UI server in a thread (it runs with uvicorn)
    t = threading.Thread(target=start_ui, daemon=True)
    t.start()
    
    # Give server time to start
    time.sleep(2)
    
    # Start background task processor in another thread
    t2 = threading.Thread(target=lambda: asyncio.run(task_processor()), daemon=True)
    t2.start()

    logger.info("YALI AI_OS started - listening for tasks from web UI")
    print("YALI AI_OS started - submit tasks from http://localhost:8000")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down')

if __name__ == '__main__':
    main()

