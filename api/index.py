from fastapi import FastAPI
import os
import redis

app = FastAPI()

# Conexión a Redis
REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL)

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