import time
import json
import threading
import requests
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("Gateway")

SCADA_CONTROL_URL = "http://172.20.0.20:8080/api/control"

class GatewayControlHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/control":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                cmd = json.loads(body.decode())
                log.info(f"[GW←DISPATCH] Nhan lenh tu Dieu do: {cmd}")
                
                # Forward xuong SCADA Server
                r = requests.post(SCADA_CONTROL_URL, json=cmd, timeout=5)
                result = r.json()
                
                log.info(f"[GW→SCADA] Forward thanh cong: {result}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                log.error(f"Loi xu ly lenh: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args): pass

def run_gw_control():
    server = HTTPServer(("0.0.0.0", 8081), GatewayControlHandler)
    log.info("Gateway Control Listener san sang tai port 8081")
    server.serve_forever()

def main():
    threading.Thread(target=run_gw_control, daemon=True).start()
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
