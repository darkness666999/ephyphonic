import time
import requests
import os
from datetime import datetime
#This file is to tregger the Ephyphonic API every 10 minutes, and log the results in Windows Event Log for monitoring.
URL = "https://ephyphonic-hybu.vercel.app/api/worker"
INTERVAL = 600 # 10 minutes
APP_NAME = "EphyphonicTrigger"

def log_event(message, error=False):
    etype = "Error" if error else "Information"
    msg_final = f"[Ephyphonic] {message}"
    
    command_for_log = f'powershell -Command "Write-EventLog -LogName Application -Source \'Application Error\' -EventId 1 -EntryType {etype} -Message \'{msg_final}\'"'
    os.system(command_for_log)

def ejecute_ping():
    now = datetime.now().strftime('%H:%M:%S')
    try:
        response = requests.get(URL, headers={"Accept": "application/json"}, timeout=15)
        if response.status_code == 200:
            info = response.json().get('entry', 'No detail')
            log_event(f"Ping exitoso [{now}]: {info}")
            print(f"[{now}] ✅ Sent")
        else:
            log_event(f"Error Status {response.status_code} [{now}]", error=True)
            print(f"[{now}] ⚠️ Status {response.status_code}")
    except Exception as e:
        print(f"[{now}] ❌ Network failiure: {e}")

if __name__ == "__main__":
    print(f"🚀 Trigger initiated. Every {INTERVAL/60} min.")
    log_event("Service to Trigger Ephyphonic initiated.")
    
    while True:
        ejecute_ping()
        time.sleep(INTERVAL)