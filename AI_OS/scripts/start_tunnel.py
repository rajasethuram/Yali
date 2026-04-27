"""
YALI Launcher with Cloudflare Tunnel
Starts uvicorn server + cloudflared tunnel, prints public URL.
Usage: python scripts/start_tunnel.py
"""
import subprocess
import sys
import time
import re
import os
import signal
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYTHON = sys.executable
CLOUDFLARED = Path(__file__).parent / "cloudflared.exe"

# Load .env manually (dotenv may not be installed in PATH Python)
env_path = ROOT / ".env"
env = os.environ.copy()
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

TUNNEL_TOKEN = env.get("CLOUDFLARE_TUNNEL_TOKEN", "")

server_proc = None
tunnel_proc = None


def cleanup(*_):
    print("\n[YALI] Shutting down...")
    if tunnel_proc:
        tunnel_proc.terminate()
    if server_proc:
        server_proc.terminate()
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def main():
    global server_proc, tunnel_proc

    print("[YALI] Starting YALI server on http://localhost:8000 ...")
    server_proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "ui.server:app",
         "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
        cwd=str(ROOT),
        env=env,
    )

    # Wait for server to bind
    time.sleep(3)
    if server_proc.poll() is not None:
        print("[YALI] ERROR: Server failed to start. Check your .env and imports.")
        sys.exit(1)

    print("[YALI] Server running. Starting Cloudflare Tunnel...")

    if TUNNEL_TOKEN:
        # Mode B: persistent tunnel with token
        tunnel_cmd = [str(CLOUDFLARED), "tunnel", "run", "--token", TUNNEL_TOKEN]
        print("[YALI] Mode: Persistent tunnel (token)")
    else:
        # Mode A: quick tunnel, random trycloudflare.com URL
        tunnel_cmd = [str(CLOUDFLARED), "tunnel", "--url", "http://localhost:8000"]
        print("[YALI] Mode: Quick tunnel (random URL) — add CLOUDFLARE_TUNNEL_TOKEN to .env for a fixed URL")

    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(ROOT),
        env=env,
    )

    print("[YALI] Waiting for tunnel URL...")
    url_found = False
    for line in tunnel_proc.stdout:
        line = line.rstrip()

        # Extract public URL from cloudflared output
        match = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
        if match and not url_found:
            url = match.group(0)
            url_found = True
            print("\n" + "=" * 55)
            print(f"  YALI PUBLIC URL: {url}")
            print(f"  Open on any device, share with anyone")
            print("=" * 55 + "\n")
            continue

        # Also catch named tunnel URLs
        match2 = re.search(r'https://[a-zA-Z0-9\-\.]+\.(com|net|org|io)', line)
        if match2 and not url_found and "cloudflare" not in line.lower():
            url = match2.group(0)
            url_found = True
            print(f"\n[YALI] PUBLIC URL: {url}\n")

        # Show useful cloudflared status lines
        if any(kw in line for kw in ["INF", "ERR", "Registered", "Connection"]):
            print(f"[cloudflared] {line}")

    # If tunnel exits, clean up server too
    cleanup()


if __name__ == "__main__":
    main()
