#!/usr/bin/env python3
"""
SCADA RTU / GATEWAY MODULE (Mô phỏng IEC 60870-5-104)
- Thu thập dữ liệu thời gian thực từ SCADA Data Server (172.20.0.20:8080/api/data)
- Chuyển đổi định dạng sang mô hình bản tin viễn thám IEC 60870-5-104 (ASDU / IOA)
- Mô phỏng phát dữ liệu chuyển tiếp lên Trung tâm Điều độ (A0 / A2 / B1)
"""
import time, json, logging, requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [GATEWAY-104] %(message)s')
log = logging.getLogger("RTU_GATEWAY")

# ── Cấu hình kết nối ──────────────────────────────────────
SCADA_SERVER_URL = "http://172.20.0.20:8080/api/data"
POLL_INTERVAL    = 5  # Tần suất lấy dữ liệu (giây)

# Mô phỏng các Trung tâm Điều độ nhận dữ liệu
DISPATCH_CENTERS = [
    {"name": "Trung tâm Điều độ Hệ thống điện Miền (A2)", "ip": "10.100.0.1", "status": "CONNECTED"},
    {"name": "Trung tâm Điều khiển Lưới điện 110kV (B1)",   "ip": "10.100.0.2", "status": "CONNECTED"}
]

def map_to_iec104_asdu(ied_name, data):
    """
    Mô phỏng đóng gói dữ liệu sang chuẩn IEC 60870-5-104
    - Type 13/36 (M_ME_NC_1 / M_ME_TF_1): Giá trị đo lường số thực (Float telemetry)
    - Type 1/30  (M_SP_NA_1 / M_SP_TB_1): Trạng thái điểm đơn (Single-point status)
    """
    m = data["measurements"]
    asdu_payload = {
        "common_address": 1, # Địa chỉ trạm (Station Common Address)
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "telemetry_floats_type36": [
            {"ioa": 101, "name": f"{ied_name}_Voltage", "value": m["voltage_kv"], "unit": "kV"},
            {"ioa": 102, "name": f"{ied_name}_Current", "value": m["current_a"],  "unit": "A"},
            {"ioa": 103, "name": f"{ied_name}_ActiveP", "value": m["active_power_mw"], "unit": "MW"},
            {"ioa": 104, "name": f"{ied_name}_Freq",    "value": m["freq_hz"],    "unit": "Hz"}
        ],
        "status_points_type30": [
            {"ioa": 201, "name": f"{ied_name}_MC_89",  "state": "CLOSED" if m["mc_closed"] else "OPEN"},
            {"ioa": 202, "name": f"{ied_name}_DCL_17", "state": "CLOSED" if m["dcl_closed"] else "OPEN"}
        ]
    }
    return asdu_payload

def main():
    log.info("=== SCADA GATEWAY (IEC 60870-5-104 FORWARDER) KHỞI ĐỘNG ===")
    log.info(f"Đang kết nối trạm máy chủ SCADA tại: {SCADA_SERVER_URL}")
    for dc in DISPATCH_CENTERS:
        log.info(f" -> Đã thiết lập kênh kết nối WAN tới: {dc['name']} ({dc['ip']})")

    while True:
        try:
            # 1. Hút dữ liệu từ SCADA Server nội bộ trạm
            resp = requests.get(SCADA_SERVER_URL, timeout=3)
            if resp.status_code == 200:
                scada_data = resp.json()
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📡 ĐANG CHUYỂN TIẾP GÓI TIN IEC 104 LÊN TRUNG TÂM ĐIỀU ĐỘ...")
                
                # 2. Xử lý và chuyển tiếp cho từng Ngăn lộ
                for ied_name, bay_data in scada_data.items():
                    asdu = map_to_iec104_asdu(ied_name, bay_data)
                    
                    # In tóm tắt gói tin chuyển tiếp ra màn hình console
                    v_val = asdu["telemetry_floats_type36"][0]["value"]
                    i_val = asdu["telemetry_floats_type36"][1]["value"]
                    mc_st = asdu["status_points_type30"][0]["state"]
                    
                    print(f"  ⚡ [ASDU-104] {ied_name:<6} (IOA:101-202) -> U: {v_val:>6} kV | I: {i_val:>6} A | MC: [{mc_st}] -> 🟢 SENT OK")
            else:
                log.warning(f"SCADA Server trả về mã lỗi HTTP: {resp.status_code}")
                
        except requests.exceptions.RequestException:
            log.error("❌ Mất kết nối đến SCADA Data Server (172.20.0.20)! Đang thử lại...")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
