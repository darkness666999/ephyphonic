import os
import redis
import time
import requests
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

try:
    r = redis.from_url(
        os.getenv("REDIS_URL"), 
        decode_responses=True,
        socket_connect_timeout=5,
        ssl_cert_reqs=None 
    )
except Exception:
    r = None

@app.get("/api/cron/worker")
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