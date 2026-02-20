from fastapi import FastAPI
import os
import redis

app = FastAPI()

REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL)

@app.get("/api")
def get_status():
    try:
        logs = r.lrange("system_logs", 0, 10)
        logs_decoded = [log.decode('utf-8') for log in logs]
        
        return {
            "status": "online",
            "project": "Serverless Orquestrator",
            "owner": "Angelo Araya",
            "last_events": logs_decoded
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}