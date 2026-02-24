from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import json
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
async def get_status(request: Request):

    filters = {
        "status": request.query_params.get("status"),
        "level": request.query_params.get("level"),
        "latencyGt": request.query_params.get("latencyGt"),
        "dateFrom": request.query_params.get("dateFrom")
    }

    if filters["status"]:
        filters["status"] = int(filters["status"])
    if filters["latencyGt"]:
        filters["latencyGt"] = float(filters["latencyGt"]) 
    
    try:
        logs = r.zrevrange("orchestrator_telemetry", 0, -1)
        logs_decoded = []

        for raw in logs:
            log = parse_log(raw)

            if apply_filters(log, filters):
                logs_decoded.append(log)

        data = build_dashboard_data(logs_decoded)

        accept = request.headers.get("accept", "")

        if "text/html" not in accept:
            return JSONResponse(content=data)
        
        return HTMLResponse(content=render_dashboard(logs_decoded, data, filters))
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

def build_dashboard_data(logs):
    return {
        "status": "online",
        "project": "Ephyphonic",
        "owner": "Angelo Araya",
        "retention": "7_days",
        "total_logs": len(logs),
        "last_events": [
            f"{l['timestamp']} | Status: {l['status']} | {l['latency']}ms"
            if l["timestamp"] else l["raw"]
            for l in logs
        ]
    }

def parse_log(raw: bytes):
    raw_str = raw.decode("utf-8")

    try:
        parsed = json.loads(raw_str)
        return {
            "timestamp": parsed.get("timestamp"),
            "status": parsed.get("status"),
            "latency": parsed.get("latency"),
            "raw": raw_str
        }
    except:
        try:
            parts = raw_str.split("|")
            return {
                "timestamp": parts[0].strip(),
                "status": int(parts[1].split(":")[1].strip()),
                "latency": float(parts[2].replace("ms", "").strip()),
                "raw": raw_str
            }
        except:
            return {
                "timestamp": None,
                "status": None,
                "latency": None,
                "raw": raw_str
            }
        
def apply_filters(log, filters):
    # If no filters, include every log
    if not filters:
        return True

    level = filters.get("level")
    status_filter = filters.get("status")
    slow = filters.get("latencyGt")
    date_from = filters.get("dateFrom")

    # Filter by error level all bigger than or equal to 400
    if level == "error":
        if log["status"] is None or log["status"] < 400:
            return False

    # Filter by exact status if provided
    if status_filter is not None:
        if log["status"] != status_filter:
            return False

    # Filter by latency greater than specified
    if slow is not None:
        if log["latency"] is None or log["latency"] >= slow:
            return False
    
    # Filter by date
    if date_from:
        try:
            log_date = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")
            filter_date = datetime.strptime(date_from, "%Y-%m-%d")
            if log_date < filter_date:
                return False
        except Exception:
            # If timestamp is missing or invalid, exclude the log
            return False

    # If all filters pass, we include the log
    return True

def render_dashboard(logs_decoded, data, filters):
    log_items = ""

    for log in logs_decoded:
        if log["timestamp"]:
            display = f"{log['timestamp']} | Status: {log['status']} | {log['latency']}ms"
            status_code = log["status"]
        else:
            display = log["raw"]
            status_code = None

        color = "text-blue-300"

        if status_code and status_code >= 500:
            color = "text-red-400"
        elif status_code and status_code >= 400:
            color = "text-yellow-400"

        log_items += f"<li class='border-b border-slate-700 py-2 font-mono text-sm {color}'>{display}</li>"
    
    status_val = filters.get("status") or ""
    level_val = filters.get("level") or ""
    latency_val = filters.get("latencyGt") or ""
    date_from_val = filters.get("dateFrom") or ""

    level_any_selected = "selected" if level_val == "" else ""
    level_error_selected = "selected" if level_val == "error" else ""

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
                        <a href="/api/worker" class="flex items-center gap-2 text-xs px-3 py-1.5 rounded-xl border border-emerald-500/50 bg-slate-700 hover:bg-slate-600 text-emerald-400 font-medium transition-all shadow-sm shadow-emerald-500/30">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 stroke-emerald-400" fill="none" viewBox="0 0 24 24" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M12 5l7 7-7 7"/>
                            </svg>
                            Run Worker
                        </a>
                        <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-sm border border-emerald-500/50">System Online</span>
                    </div>
                </header>

                <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 mb-6">
                    <form id="searchForm" method="GET" action="/api" class="flex flex-wrap gap-4 items-end">
                        <div>
                            <label class="text-slate-400 text-xs">Status</label>
                            <input type="number" name="status" placeholder="200" value="{status_val}" class="px-2 py-1 rounded border border-slate-600 bg-slate-900 text-white text-sm">
                        </div>
                        <div>
                            <label class="text-slate-400 text-xs">Level</label>
                            <select name="level" class="px-2 py-1 rounded border border-slate-600 bg-slate-900 text-white text-sm">
                                <option value="" {level_any_selected}>Any</option>
                                <option value="error" {level_error_selected}>Error (>=400)</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-slate-400 text-xs">Min Latency (ms)</label>
                            <input type="number" name="latencyGt" placeholder="100" value="{latency_val}" class="px-2 py-1 rounded border border-slate-600 bg-slate-900 text-white text-sm">
                        </div>
                        <div>
                            <label class="text-slate-400 text-xs">Date From</label>
                            <input type="date" name="dateFrom" value="{date_from_val}" class="px-2 py-1 rounded border border-slate-600 bg-slate-900 text-white text-sm">
                        </div>
                        <div>
                            <button class="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-emerald-400 px-4 py-2 rounded-xl border border-emerald-500/50 text-sm font-medium transition-colors transition-transform hover:scale-105 active:scale-95 shadow-sm">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 stroke-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                                    <path d="M10 18a8 8 0 100-16 8 8 0 000 16z" />
                                    <path d="M15 15l5 5" />
                                </svg>
                                Search
                            </button>
                        </div>
                    </form>
                </div>

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
    return html_content


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
        log_entry = {
            "timestamp": now_str,
            "status": response.status_code,
            "latency": latency
        }

        r.zadd("orchestrator_telemetry", {json.dumps(log_entry): now_ts})
        
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