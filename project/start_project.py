"""Start the local project from its root, reuse healthy services, keep logs."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / '.runtime'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def read(url, timeout=3):
    with OPENER.open(url, timeout=timeout) as response:
        return response.read().decode('utf-8')


def healthy(kind):
    try:
        if kind == 'backend':
            return json.loads(read('http://127.0.0.1:8000/api/health')).get('status') == 'ok'
        return '/@vite/client' in read('http://127.0.0.1:5173/') and json.loads(read('http://127.0.0.1:5173/api/health')).get('status') == 'ok'
    except (OSError, ValueError, urllib.error.URLError):
        return False


def occupied(port):
    try:
        with socket.create_connection(('localhost', port), timeout=1):
            return True
    except OSError:
        return False


def ensure(kind, command, directory, port):
    if healthy(kind):
        print(f'{kind}: already running.', flush=True)
        return
    if occupied(port):
        raise RuntimeError(f'Port {port} is occupied but {kind} did not pass its health check. Check the existing service before restarting it.')
    LOGS.mkdir(exist_ok=True)
    logfile = LOGS / f'{kind}.log'
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with logfile.open('ab') as output:
        process = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT, creationflags=flags,
                                   start_new_session=os.name != 'nt')
    (LOGS / f'{kind}.pid').write_text(str(process.pid), encoding='ascii')
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if healthy(kind):
            print(f'{kind}: started (PID {process.pid}). Log: {logfile}', flush=True)
            return
        if process.poll() is not None:
            raise RuntimeError(f'{kind} exited with code {process.returncode}. Read {logfile}')
        time.sleep(.5)
    raise RuntimeError(f'{kind} did not become ready. Read {logfile}')


def main():
    python = ROOT / 'backend/.venv/Scripts/python.exe'
    vite = ROOT / 'frontend/node_modules/vite/bin/vite.js'
    node = shutil.which('node')
    if not python.exists():
        raise RuntimeError('backend/.venv is missing. Install backend dependencies first.')
    if not vite.exists() or not node:
        raise RuntimeError('Node.js or frontend dependencies are missing. Run npm install in frontend first.')
    ensure('backend', [str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], ROOT / 'backend', 8000)
    ensure('frontend', [node, str(vite), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], ROOT / 'frontend', 5173)
    read('http://127.0.0.1:5173/api/regulation/overview', timeout=20)
    print('Ready: http://127.0.0.1:5173/  |  http://127.0.0.1:5173/regulation', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Startup failed: {exc}', file=sys.stderr)
        sys.exit(1)
