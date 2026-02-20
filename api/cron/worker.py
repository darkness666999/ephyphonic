from http.server import BaseHTTPRequestHandler
import os
import requests
import redis
import time
from datetime import datetime, timedelta

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        r = redis.from_url(os.getenv("REDIS_URL"))
        target = os.getenv("TARGET_URL")
        
        try:
            start_time = time.time()
            response = requests.get(target, timeout=10)
            latency = round((time.time() - start_time) * 1000, 2)
            
            now_ts = time.time()
            ahora_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            log_msg = f"{ahora_str} | Status: {response.status_code} | {latency}ms"
            r.zadd("orchestrator_telemetry", {log_msg: now_ts})

            week = now_ts - (7 * 24 * 60 * 60)
            
            num_del = r.zremrangebyscore("orchestrator_telemetry", "-inf", week)

            system_keys = r.keys("celery-task-meta-*")
            if system_keys:
                r.delete(*system_keys)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"OK. Log saved. Deleted {num_del} old entries.".encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode()) 
