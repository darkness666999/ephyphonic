import time
import network
import gc
import ntptime
import usocket as socket


WIFI_SSID = "NETWORK__SSID"
WIFI_PASSWORD = "NETWORK_PASS"

TARGET_HOST = "SIGNALER_ADDRESS_NO_HTTPS"
TARGET_PATH = "/swagger-ui/index.html"
INTERVAL = 600

REDIS_HOST = "REDIS_HOST"  
REDIS_PORT = 17222
REDIS_AUTH = "REDIS_PASS"  
REDIS_KEY  = "REDIS_DB"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        try:
            ntptime.settime()
        except:
            pass
        return True
    return False

def get_timestamp():
    t = time.localtime()
    return str(t[0]) + "-" + "{:02d}".format(t[1]) + "-" + "{:02d}".format(t[2]) + " " + "{:02d}".format(t[3]) + ":" + "{:02d}".format(t[4]) + ":" + "{:02d}".format(t[5])

def log_to_redis(status_code, latency_ms):
    now_str = get_timestamp()
    current_epoch = int(time.time())
    
    # 30-year Unix synchronization offset calculation to sort correctly on dashboard
    unix_epoch = current_epoch + 946684800
    score_str = str(unix_epoch)
    max_old_score = str(unix_epoch - 604800)  # 7 days retention math
    
    log_string = '{"timestamp": "' + now_str + '", "status": ' + str(status_code) + ', "latency": ' + str(latency_ms) + '}'
    
    print("⚡ Syncing telemetry payload directly to Redis... Score: " + score_str)
    
    try:
        addr_info = socket.getaddrinfo(REDIS_HOST, REDIS_PORT)
        target_addr = addr_info[0][4]
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(target_addr)
        
        if REDIS_AUTH:
            auth_cmd = "*2\r\n$4\r\nAUTH\r\n$" + str(len(REDIS_AUTH)) + "\r\n" + REDIS_AUTH + "\r\n"
            s.send(auth_cmd.encode())
            s.recv(1024)

        zadd_cmd = "*4\r\n$4\r\nZADD\r\n$" + str(len(REDIS_KEY)) + "\r\n" + REDIS_KEY + "\r\n$" + str(len(score_str)) + "\r\n" + score_str + "\r\n$" + str(len(log_string)) + "\r\n" + log_string + "\r\n"
        s.send(zadd_cmd.encode())
        zadd_reply = s.recv(1024).decode()
        
        zrem_cmd = "*4\r\n$15\r\nZREMRANGEBYSCORE\r\n$" + str(len(REDIS_KEY)) + "\r\n" + REDIS_KEY + "\r\n$4\r\n-inf\r\n$" + str(len(max_old_score)) + "\r\n" + max_old_score + "\r\n"
        s.send(zrem_cmd.encode())
        zrem_reply = s.recv(1024).decode()
        
        s.close()
        print("📊 Telemetry synced. Redis Response: " + zadd_reply.strip() + " | Cleanup code: " + zrem_reply.strip())
        
    except Exception as redis_err:
        print("🚨 Direct database transmission failed: " + str(redis_err))

def execute_ping():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected() and not connect_wifi():
        return

    now = get_timestamp()
    start_time = time.ticks_ms()
    try:
        addr_info = socket.getaddrinfo(TARGET_HOST, 80)
        target_addr = addr_info[0][4]
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15)
        s.connect(target_addr)
        
        http_req = (
            "GET " + TARGET_PATH + " HTTP/1.1\r\n"
            "Host: " + TARGET_HOST + "\r\n"
            "User-Agent: ESP32-Trigger\r\n"
            "Connection: close\r\n\r\n"
        )
        s.send(http_req.encode())
        
        http_response = s.recv(128).decode()
        s.close()
        
        # Calculate real hardware connection latency
        latency = round(float(time.ticks_diff(time.ticks_ms(), start_time)), 2)
        
        # Render endpoints allow unencrypted 200 OK or a clean 301/302 routing redirect page
        if "200 OK" in http_response or "301" in http_response or "302" in http_response:
            print("[" + now + "] ✅ Target App Responsive! Latency: " + str(latency) + "ms")
            log_to_redis(200, latency)
        else:
            first_line = http_response.split("\r\n") if http_response else "Empty Response"
            print("[" + now + "] ⚠️ Target App returned bad header status: " + first_line)
            log_to_redis(400, 0.00)
            
    except Exception as e:
        print("[" + now + "] ❌ Target App Down or Unreachable: " + str(e))
        log_to_redis(500, 0.00)
        
    gc.collect()
        
if __name__ == "__main__":
    if connect_wifi():
        print("🚀 System Online. Monitoring via Crash-Proof Raw Sockets...")
        while True:
            execute_ping()
            time.sleep(INTERVAL)
