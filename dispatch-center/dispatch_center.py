#!/usr/bin/env python3
"""
MÔ PHỎNG TRUNG TÂM ĐIỀU ĐỘ HỆ THỐNG ĐIỆN (EVN DISPATCH CENTER - A2 / B1)
- Lắng nghe kết nối viễn thám WAN trên cổng tiêu chuẩn IEC 60870-5-104 (Port 2404)
- Tiếp nhận, giải mã bản tin ASDU từ Gateway Trạm biến áp 110kV (172.20.0.30)
- Giám sát tổng thể thông số lưới điện, tần số hệ thống và xử lý cảnh báo mức Điều độ
"""
import time, socket, threading, logging, json, requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [DISPATCH-A0/A2] %(message)s')
log = logging.getLogger("DISPATCH_CENTER")

# ── Cấu hình Điều độ ──────────────────────────────────────
TCP_PORT         = 2404  # Cổng tiêu chuẩn giao thức IEC 60870-5-104
GATEWAY_WAN_IP   = "172.20.0.30"
SCADA_API_BACKUP = "http://172.20.0.20:8080/api/data"
POLL_RATE        = 6     # Chu kỳ cập nhật màn hình Điều độ (giây)

# ── Hàm chạy TCP Server lắng nghe cổng 2404 ─────────────────
def start_iec104_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(("0.0.0.0", TCP_PORT))
        server_socket.listen(5)
        log.info(f"🟢 [TCP SERVER] Đã mở cổng viễn thám {TCP_PORT} (IEC 60870-5-104). Sẵn sàng nhận dữ liệu từ Gateway...")
        while True:
            client_sock, addr = server_socket.accept()
            log.info(f"🔗 [WAN CONNECTED] Phát hiện kết nối viễn thông mới từ Gateway Trạm: {addr[0]}:{addr[1]}")
            client_sock.close()
    except Exception as e:
        log.warning(f"TCP Socket Server cảnh báo: {e}")

# ── Luồng chính: Giám sát & Hiển thị log Điều độ ──────────
def main():
    print("==================================================================")
    print(" 🏛️  HỆ THỐNG SCADA - TRUNG TÂM ĐIỀU ĐỘ HỆ THỐNG ĐIỆN MIỀN (A2)")
    print("==================================================================")
    log.info("Khởi động Module giám sát Điều độ lưới điện 110kV...")
    
    # Khởi chạy luồng TCP Server cổng 2404 ngầm bên dưới
    threading.Thread(target=start_iec104_server, daemon=True).start()
    time.sleep(2)

    while True:
        try:
            # Mô phỏng việc thu thập gói tin ASDU đã được Gateway chuyển tiếp
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
                    
                    # Kiểm tra cảnh báo mức hệ thống
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
            log.warning("🔄 Đang chờ kết nối đường truyền WAN tới Gateway trạm 110kV (172.20.0.30)...")
            
        time.sleep(POLL_RATE)

if __name__ == "__main__":
    main()
