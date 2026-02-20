from fastapi import FastAPI
import os
import redis
from fastapi.responses import HTMLResponse

app = FastAPI()

# Conexión a Redis
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
def get_status():
    try:
        logs = r.zrevrange("orchestrator_telemetry", 0, -1)
        
        logs_decoded = [log.decode('utf-8') for log in logs]
        
        return {
            "status": "online",
            "project": "Ephyphonic",
            "owner": "Angelo Araya",
            "retention_policy": "7_days_dynamic",
            "total_logs": len(logs_decoded),
            "last_events": logs_decoded
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}