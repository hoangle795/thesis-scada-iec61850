#!/usr/bin/env python3
"""
MÔ PHỎNG TRUNG TÂM ĐIỀU ĐỘ HỆ THỐNG ĐIỆN (EVN DISPATCH CENTER - A2 / B1)
- Lắng nghe kết nối viễn thám WAN trên cổng tiêu chuẩn IEC 60870-5-104
- Tiếp nhận, giải mã bản tin ASDU từ Gateway
- Giám sát tổng thể thông số lưới điện và xử lý cảnh báo
- Cung cấp API (Port 9000) để phát lệnh Điều khiển (Cắt/Đóng MC) xuyên DMZ
"""
import time
import socket
import threading
import logging
import json
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [DISPATCH-A0/A2] %(message)s')
log = logging.getLogger("DISPATCH_CENTER")

# ── Cấu hình Điều độ ──────────────────────────────────────
TCP_PORT            = 2404
GATEWAY_WAN_IP      = "172.21.0.30"
SCADA_API_BACKUP    = "http://172.20.0.20:8080/api/data"
GATEWAY_CONTROL_URL = "http://172.21.0.30:8081/control"
POLL_RATE           = 3  # Chu kỳ cập nhật màn hình (3 giây)

# ── 1. Cụm API Server nhận lệnh từ Điều độ viên ───────────
class DispatchControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/send_control":
            cmd = {"ied": "IED131", "action": "open_mc", "user": "dispatcher"}
            try:
                log.info(f"⚡ Đang phát lệnh điều khiển qua Gateway DMZ: {cmd}")
                r = requests.post(GATEWAY_CONTROL_URL, json=cmd, timeout=5)
                result = r.json()
                log.info(f"✅ Phản hồi từ hạ tầng Trạm: {result}")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
            except Exception as e:
                log.error(f"❌ Lỗi gửi lệnh: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args): pass

def run_control_server():
    server = HTTPServer(("0.0.0.0", 9000), DispatchControlHandler)
    log.info("🌐 API Cổng Điều Khiển sẵn sàng tại: http://0.0.0.0:9000/send_control")
    server.serve_forever()

# ── 2. Hàm chạy TCP Server lắng nghe cổng 2404 ────────────
def start_iec104_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(("0.0.0.0", TCP_PORT))
        server_socket.listen(5)
        log.info(f"🟢 [TCP SERVER] Đã mở cổng viễn thám {TCP_PORT} (IEC 104).")
        while True:
            client_sock, addr = server_socket.accept()
            log.info(f"🔗 [WAN CONNECTED] Kết nối viễn thông mới từ: {addr[0]}:{addr[1]}")
            client_sock.close()
    except Exception as e:
        log.warning(f"TCP Socket Server cảnh báo: {e}")

# ── 3. Luồng chính: Giám sát & Hiển thị Màn hình ──────────
def main():
    print("==================================================================")
    print(" 🏛️  HỆ THỐNG SCADA - TRUNG TÂM ĐIỀU ĐỘ HỆ THỐNG ĐIỆN MIỀN (A2)")
    print("==================================================================")
    
    # Kích hoạt 2 luồng ngầm: TCP thu thập và API điều khiển
    threading.Thread(target=start_iec104_server, daemon=True).start()
    threading.Thread(target=run_control_server, daemon=True).start()
    time.sleep(1)

    while True:
        try:
            resp = requests.get(SCADA_API_BACKUP, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                
                print(f"\n──────────────────────────────────────────────────────────────────")
                print(f"📊 [MÀN HÌNH ĐIỀU ĐỘ A2] CẬP NHẬT TÌNH TRẠNG LƯỚI ĐIỆN - {datetime.now().strftime('%H:%M:%S')}")
                print(f"──────────────────────────────────────────────────────────────────")
                print(f"  {'NGĂN LỘ':<14} | {'ĐIỆN ÁP (kV)':<13} | {'DÒNG ĐIỆN (A)':<14} | {'P (MW)':<10} | {'TRẠNG THÁI MC':<14}")
                print(f"──────────────────────────────────────────────────────────────────")
                
                total_p = 0
                for ied, d in data.items():
                    m = d["measurements"]
                    v_val  = f"{m['voltage_kv']:>6.2f}"
                    i_val  = f"{m['current_a']:>6.2f}"
                    p_val  = f"{m['active_power_mw']:>5.2f}"
                    mc_st  = "🟢 ĐÓNG (CLOSED)" if m["mc_closed"] else "🔴 CẮT (OPEN)"
                    
                    total_p += m["active_power_mw"]
                    
                    status_flag = ""
                    if m["voltage_kv"] >= 121.0 or m["temp_oil_c"] >= 85.0:
                        status_flag = " ⚠️ [ALARM QĐ-1603]"
                        
                    print(f"  {ied:<14} | {v_val:<13} | {i_val:<14} | {p_val:<10} | {mc_st}{status_flag}")
                
                print(f"──────────────────────────────────────────────────────────────────")
                print(f" 🌐 TỔNG CÔNG SUẤT TRUYỀN TẢI TBA 110kV: {total_p:.2f} MW | TẦN SỐ LƯỚI: 50.00 Hz | KÊNH WAN: ONLINE 🟢")
                print(f"──────────────────────────────────────────────────────────────────")
            else:
                log.warning("Chưa nhận được bản tin viễn thám từ Gateway...")
        except Exception:
            log.warning(f"🔄 Đang chờ kết nối đường truyền WAN tới Gateway trạm 110kV ({GATEWAY_WAN_IP})...")
            
        time.sleep(POLL_RATE)

if __name__ == "__main__":
    main()
