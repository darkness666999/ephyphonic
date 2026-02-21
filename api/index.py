from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import os
import redis
import time
import requests
from datetime import datetime

app = FastAPI()

REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL)

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <head>
            <title>Ephyphonic Orchestrator</title>
            <link rel="icon" type="image/svg+xml" href="/favicon.svg">
        </head>
        <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0f172a; color: white;">
            <div style="text-align: center; border: 1px solid #334155; padding: 2rem; border-radius: 1rem; background: #1e293b;">
                <h1>🚀 Ephyphonic System</h1>
                <p>Status: <span style="color: #10b981;">Online</span></p>
                <a href="/api" style="color: #38bdf8; text-decoration: none;">View API Dashboard →</a>
            </div>
        </body>
    </html>
    """

@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse("api/ephyphonic.svg", media_type="image/svg+xml")

@app.get("/api")
def get_status(request: Request):
    try:
        logs = r.zrevrange("orchestrator_telemetry", 0, -1)
        logs_decoded = [log.decode('utf-8') for log in logs]
        
        data = {
            "status": "online",
            "project": "Ephyphonic",
            "owner": "Angelo Araya",
            "retention": "7_days",
            "total_logs": len(logs_decoded),
            "last_events": logs_decoded
        }

        accept = request.headers.get("accept", "")
        if "text/html" not in accept:
            return JSONResponse(content=data)

        log_items = "".join([f"<li class='border-b border-slate-700 py-2 font-mono text-sm text-blue-300'>{log}</li>" for log in logs_decoded])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ephyphonic Dashboard</title>
            <link rel="icon" type="image/svg+xml" href="/favicon.svg">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-900 text-slate-200 min-h-screen p-8">
            <div class="max-w-4xl mx-auto">
                <header class="flex justify-between items-center mb-8 border-b border-slate-700 pb-4">
                    <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                        Ephyphonic Orchestrator
                    </h1>
                    <div class="flex items-center gap-4">
                        <a href="/api/worker" class="text-xs bg-blue-600 hover:bg-blue-500 text-white py-1.5 px-3 rounded-lg transition-colors font-medium">
                            ▶ Run Worker
                        </a>
                        <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-sm border border-emerald-500/50">System Online</span>
                    </div>
                </header>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div class="bg-slate-800 p-4 rounded-xl border border-slate-700">
                        <p class="text-slate-400 text-sm">Owner</p>
                        <p class="text-xl font-semibold">{data['owner']}</p>
                    </div>
                    <div class="bg-slate-800 p-4 rounded-xl border border-slate-700">
                        <p class="text-slate-400 text-sm">Retention Policy</p>
                        <p class="text-xl font-semibold text-blue-400">7 Days</p>
                    </div>
                    <div class="bg-slate-800 p-4 rounded-xl border border-slate-700">
                        <p class="text-slate-400 text-sm">Total Logs</p>
                        <p class="text-xl font-semibold text-emerald-400">{data['total_logs']}</p>
                    </div>
                </div>

                <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                    <div class="bg-slate-700/50 p-4 border-b border-slate-700">
                        <h2 class="font-semibold">Recent Telemetry (7d window)</h2>
                    </div>
                    <ul class="p-4 max-h-[500px] overflow-y-auto italic">
                        {log_items if logs_decoded else "<p class='text-slate-500 text-center py-4'>No logs available yet. Waiting for GitHub Action...</p>"}
                    </ul>
                </div>
                
                <footer class="mt-8 text-center text-slate-500 text-xs">
                    Powered by FastAPI, Redis & Vercel Serverless
                </footer>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
    
@app.get("/api/worker")
def do_worker(request: Request):
    if r is None:
        return JSONResponse(content={"status": "error", "message": "Redis not initialized."}, status_code=500)
    
    target = os.getenv("TARGET_URL")
    if not target:
        return JSONResponse(content={"status": "error", "message": "TARGET_URL not configured."}, status_code=500)
    
    try:
        start_time = time.time()
        response = requests.get(target, timeout=10)
        latency = round((time.time() - start_time) * 1000, 2)
        
        now_ts = time.time()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"{now_str} | Status: {response.status_code} | {latency}ms"
        
        r.zadd("orchestrator_telemetry", {log_msg: now_ts})
        
        week_ago = now_ts - (7 * 24 * 60 * 60)
        num_del = r.zremrangebyscore("orchestrator_telemetry", "-inf", week_ago)

        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>                
                <title>Worker Execution</title>
                <link rel="icon" type="image/svg+xml" href="/favicon.svg">
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-slate-900 text-slate-200 flex items-center justify-center min-h-screen p-4">
                <div class="bg-slate-800 border border-emerald-500/30 p-8 rounded-2xl shadow-2xl max-w-md w-full text-center">
                    <div class="mb-4 inline-flex items-center justify-center w-16 h-16 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/50">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold text-white mb-2">Worker Executed</h1>
                    <p class="text-slate-400 mb-6 italic text-sm">"{log_msg}"</p>
                    <div class="flex flex-col gap-3">
                        <a href="/api" class="bg-blue-600 hover:bg-blue-500 text-white py-3 px-4 rounded-xl font-bold transition-all shadow-lg shadow-blue-900/20 active:scale-95">
                            ← Back to Dashboard
                        </a>
                        <span class="text-xs text-slate-500">Deleted {num_del} expired logs</span>
                    </div>
                </div>
            </body>
            </html>
            """)

        return {
            "status": "success",
            "entry": log_msg,
            "deleted_old": num_del
        }

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)