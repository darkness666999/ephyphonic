from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
        <head><title>Ephyphonic Orchestrator</title></head>
        <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0f172a; color: white;">
            <div style="text-align: center; border: 1px solid #334155; padding: 2rem; border-radius: 1rem; background: #1e293b;">
                <h1>🚀 Ephyphonic System</h1>
                <p>Status: <span style="color: #10b981;">Online</span></p>
                <a href="/api" style="color: #38bdf8; text-decoration: none;">View API Dashboard →</a>
            </div>
        </body>
    </html>
    """

@app.get("/api")
def get_status(request: Request):
    try:
        # 1. Obtener datos de Redis
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

        # 2. Verificar si el usuario pide JSON (API) o HTML (Navegador)
        accept = request.headers.get("accept", "")
        if "text/html" not in accept:
            return JSONResponse(content=data)

        # 3. HTML "Beautified" para el Dashboard
        log_items = "".join([f"<li class='border-b border-slate-700 py-2 font-mono text-sm text-blue-300'>{log}</li>" for log in logs_decoded])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ephyphonic Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-900 text-slate-200 min-h-screen p-8">
            <div class="max-w-4xl mx-auto">
                <header class="flex justify-between items-center mb-8 border-b border-slate-700 pb-4">
                    <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                        Ephyphonic Orchestrator
                    </h1>
                    <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-sm border border-emerald-500/50">System Online</span>
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
def do_worker():
    if r is None:
        return {"status": "error", "message": "Redis not initialized. Check REDIS_URL."}
    
    target = os.getenv("TARGET_URL")
    if not target:
        return {"status": "error", "message": "TARGET_URL not configured."}
    
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

        return {
            "status": "success",
            "message": "Log guardado",
            "entry": log_msg,
            "deleted_old": num_del
        }

    except Exception as e:
        return {"status": "error", "message": f"Execution failure: {str(e)}"}