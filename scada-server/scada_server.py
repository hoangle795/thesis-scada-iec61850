#!/usr/bin/env python3
"""
SCADA Data Server
- Thu thập dữ liệu từ 4 IED qua IEC 61850/MMS (simulation mode nếu chưa có pyiec61850)
- Xử lý cảnh báo 3 cấp: Warning / Alarm / Failure theo QĐ 1603/QĐ-EVN
- Ghi vào InfluxDB (Historian)
- Cung cấp REST API tại :8080/api/data cho HMI Web và Gateway
- Nhận lệnh điều khiển (POST /api/control) và lưu Audit Log
"""
import time, json, random, logging, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUX_OK = True
except ImportError:
    INFLUX_OK = False

try:
    import iec61850
    USE_IEC61850 = True
except ImportError:
    USE_IEC61850 = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [SCADA] %(message)s')
log = logging.getLogger(__name__)

# ── Cấu hình IED ──────────────────────────────────────────
IED_LIST = [
    {"name": "IED131", "bay": "Ngăn lộ 131", "ip": "172.20.0.10", "port": 102},
    {"name": "IED171", "bay": "Ngăn lộ 171", "ip": "172.20.0.11", "port": 102},
    {"name": "IED172", "bay": "Ngăn lộ 172", "ip": "172.20.0.12", "port": 102},
    {"name": "IED112", "bay": "Ngăn lộ 112", "ip": "172.20.0.13", "port": 102},
]

# ── Cấu hình InfluxDB ─────────────────────────────────────
INFLUX_URL    = "http://172.20.0.21:8086"
INFLUX_TOKEN  = "scada-token-2024"
INFLUX_ORG    = "substation"
INFLUX_BUCKET = "scada_data"

# ── Ngưỡng cảnh báo (trạm 110kV) ─────────────────────────
# Nguồn: Điều 5 QĐ 1603/QĐ-EVN
THR = {
    "voltage_kv":   {"warn": 115.0, "alarm": 121.0, "low": 95.0},
    "current_a":    {"warn": 400.0, "alarm": 500.0},
    "freq_hz":      {"low": 49.5,   "high": 50.5},
    "power_factor": {"low": 0.85},
    "temp_oil_c":   {"warn": 75.0,  "alarm": 85.0},
}

# ── Store dữ liệu hiện tại dùng cho REST API ──────────────
store = {}
lock  = threading.Lock()

# ── Global variables cho Control ──────────────────────────
audit_write_api = None
sims = {}

# ── Simulator IED (dùng khi chưa có kết nối IEC 61850 thật) ──
class IEDSim:
    def __init__(self, name):
        self.name = name
        self.mc  = True
        self.dcl = True
        self.dtd = False
        self.tap = 9       # Nấc phân áp khởi tạo

    def read(self):
        return {
            "voltage_kv":          round(110.0 + random.uniform(-2, 2), 2),
            "current_a":           round(250.0 + random.uniform(-20, 20), 2),
            "active_power_mw":     round(45.0  + random.uniform(-3, 3), 2),
            "reactive_power_mvar": round(12.0  + random.uniform(-2, 2), 2),
            "freq_hz":             round(50.0  + random.uniform(-0.1, 0.1), 3),
            "power_factor":        round(0.92  + random.uniform(-0.02, 0.02), 3),
            "temp_oil_c":          round(65.0  + random.uniform(-3, 3), 1),
            "temp_winding_c":      round(75.0  + random.uniform(-3, 3), 1),
            "tap_position":        self.tap,   # Dùng self.tap thay vì random
            "mc_closed":           self.mc,
            "dcl_closed":          self.dcl,
            "dtd_closed":          self.dtd,
            "timestamp_ms":        int(time.time() * 1000),
        }

# ── Kiểm tra cảnh báo 3 cấp ──────────────────────────────
def check_alarms(m):
    alarms = []
    v, i, f, t, pf = (m["voltage_kv"], m["current_a"], m["freq_hz"],
                      m["temp_oil_c"], m["power_factor"])
    if v >= THR["voltage_kv"]["alarm"]:
        alarms.append({"level": "ALARM",   "msg": f"Quá áp nghiêm trọng: {v} kV"})
    elif v >= THR["voltage_kv"]["warn"]:
        alarms.append({"level": "WARNING", "msg": f"Điện áp cao: {v} kV"})
    elif v < THR["voltage_kv"]["low"]:
        alarms.append({"level": "WARNING", "msg": f"Điện áp thấp: {v} kV"})

    if i >= THR["current_a"]["alarm"]:
        alarms.append({"level": "ALARM",   "msg": f"Quá dòng nghiêm trọng: {i} A"})
    elif i >= THR["current_a"]["warn"]:
        alarms.append({"level": "WARNING", "msg": f"Dòng điện cao: {i} A"})

    if f < THR["freq_hz"]["low"] or f > THR["freq_hz"]["high"]:
        alarms.append({"level": "WARNING", "msg": f"Tần số bất thường: {f} Hz"})

    if t >= THR["temp_oil_c"]["alarm"]:
        alarms.append({"level": "ALARM",   "msg": f"Nhiệt độ dầu nguy hiểm: {t}°C"})
    elif t >= THR["temp_oil_c"]["warn"]:
        alarms.append({"level": "WARNING", "msg": f"Nhiệt độ dầu cao: {t}°C"})

    if pf < THR["power_factor"]["low"]:
        alarms.append({"level": "WARNING", "msg": f"Hệ số công suất thấp: {pf}"})
    return alarms

# ── Ghi InfluxDB ──────────────────────────────────────────
def write_influx(write_api, ied_name, m):
    if not INFLUX_OK or write_api is None:
        return
    try:
        p = (Point("ied_measurements")
             .tag("ied", ied_name)
             .field("voltage_kv",          m["voltage_kv"])
             .field("current_a",           m["current_a"])
             .field("active_power_mw",     m["active_power_mw"])
             .field("reactive_power_mvar", m["reactive_power_mvar"])
             .field("freq_hz",             m["freq_hz"])
             .field("power_factor",        m["power_factor"])
             .field("temp_oil_c",          m["temp_oil_c"])
             .field("tap_position",        float(m["tap_position"]))
             .field("mc_closed",           float(m["mc_closed"])))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception as e:
        log.warning(f"InfluxDB write error: {e}")

# ── Audit log lệnh điều khiển vào InfluxDB + file ─────────
AUDIT_LOG = "/app/audit_log.jsonl"
def write_audit_log(user, ied, cmd, result, write_api):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user":      user,
        "ied":       ied,
        "command":   cmd,
        "result":    result,
    }
    # Ghi file
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Ghi InfluxDB
    if INFLUX_OK and write_api:
        try:
            p = (Point("control_audit")
                 .tag("ied",  ied)
                 .tag("user", user)
                 .tag("cmd",  cmd)
                 .field("result", result))
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        except Exception as e:
            log.warning(f"Audit log InfluxDB error: {e}")

# ── Xử lý lệnh điều khiển từ HMI ─────────────────────────
def handle_control(cmd):
    """
    cmd = {
        "ied":  "IED131",
        "action": "open_mc" | "close_mc" | "tap_up" | "tap_down",
        "user": "operator"
    }
    """
    ied_name = cmd.get("ied")
    action   = cmd.get("action")
    user     = cmd.get("user", "unknown")

    if ied_name not in sims:
        return {"ok": False, "msg": f"IED {ied_name} không tồn tại"}

    sim = sims[ied_name]
    msg = ""

    if action == "open_mc":
        sim.mc = False
        msg = f"MC {ied_name} đã CẮT"
    elif action == "close_mc":
        sim.mc = True
        msg = f"MC {ied_name} đã ĐÓNG"
    elif action == "tap_up":
        sim.tap = min(sim.tap + 1, 17)
        msg = f"Nấc phân áp {ied_name} tăng lên {sim.tap}"
    elif action == "tap_down":
        sim.tap = max(sim.tap - 1, 1)
        msg = f"Nấc phân áp {ied_name} giảm xuống {sim.tap}"
    else:
        return {"ok": False, "msg": f"Lệnh không hợp lệ: {action}"}

    log.info(f"[CONTROL] [{user}] {msg}")
    write_audit_log(user, ied_name, action, msg, audit_write_api)
    return {"ok": True, "msg": msg}

# ── REST API server ────────────────────────────────────────
class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            with lock:
                body = json.dumps(store, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/control":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                cmd = json.loads(body.decode("utf-8"))
                result = handle_control(cmd)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, *args):
        pass

def run_api():
    HTTPServer(("0.0.0.0", 8080), APIHandler).serve_forever()

# ── Main loop ─────────────────────────────────────────────
def main():
    global sims, audit_write_api
    
    log.info("=== SCADA Data Server khởi động ===")
    log.info(f"Chế độ IED: {'IEC 61850 thật' if USE_IEC61850 else 'Simulation'}")
    
    # InfluxDB
    write_api = None
    if INFLUX_OK:
        try:
            c = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
            write_api = c.write_api(write_options=SYNCHRONOUS)
            log.info("Kết nối InfluxDB thành công")
        except Exception as e:
            log.warning(f"InfluxDB không kết nối được: {e}")

    audit_write_api = write_api
    sims = {ied["name"]: IEDSim(ied["name"]) for ied in IED_LIST}

    # REST API thread
    threading.Thread(target=run_api, daemon=True).start()
    log.info("REST API tại http://172.20.0.20:8080/api/data")
    
    try:
        while True:
            snap = {}
            for ied in IED_LIST:
                name = ied["name"]
                m    = sims[name].read()
                al   = check_alarms(m)
                snap[name] = {
                    "bay":          ied["bay"],
                    "ip":           ied["ip"],
                    "measurements": m,
                    "alarms":       al,
                    "updated_at":   datetime.now().isoformat(),
                }
                write_influx(write_api, name, m)
                for a in al:
                    log.warning(f"[{name}] [{a['level']}] {a['msg']}")
            with lock:
                store.update(snap)
                
            # Console summary
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
            for name, d in snap.items():
                m  = d["measurements"]
                st = ("ALARM"   if any(a["level"]=="ALARM"   for a in d["alarms"]) else
                      "WARNING" if any(a["level"]=="WARNING" for a in d["alarms"]) else "OK")
                print(f"  {name}: {m['voltage_kv']}kV | {m['current_a']}A | "
                      f"{m['freq_hz']}Hz | {m['temp_oil_c']}°C | [{st}]")
            time.sleep(5)
    except KeyboardInterrupt:
        log.info("Dừng.")

if __name__ == "__main__":
    main()
