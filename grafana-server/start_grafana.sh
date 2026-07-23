#!/bin/bash
echo "=== KHỞI CHẠY GRAFANA TỰ ĐỘNG (PROVISIONING) ==="

# 1. Tạo cấu trúc thư mục provisioning
mkdir -p provisioning/datasources
mkdir -p provisioning/dashboards

# 2. Sinh file cấu hình tự động kết nối InfluxDB
cat > provisioning/datasources/influxdb.yaml << 'EOF'
apiVersion: 1
datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://172.20.0.21:8086
    jsonData:
      version: Flux
      organization: substation
      defaultBucket: scada_data
    secureJsonData:
      token: scada-token-2024
    isDefault: true
EOF

# 3. Sinh file cấu hình tự động trỏ tới Dashboard JSON
cat > provisioning/dashboards/dashboards.yaml << 'EOF'
apiVersion: 1
providers:
  - name: 'SCADA Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# 4. Sinh file Dashboard JSON
cat > provisioning/dashboards/scada-dashboard.json << 'EOF'
{
  "title": "SCADA Trạm Biến Áp 110kV",
  "tags": ["scada", "iec61850"],
  "timezone": "Asia/Ho_Chi_Minh",
  "panels": [
    {
      "id": 1, "title": "Điện áp các ngăn lộ (kV)", "type": "timeseries", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
      "targets": [{"datasource": {"type": "influxdb"}, "query": "from(bucket: \"scada_data\")\n  |> range(start: -15m)\n  |> filter(fn: (r) => r._measurement == \"ied_measurements\")\n  |> filter(fn: (r) => r._field == \"voltage_kv\")\n  |> aggregateWindow(every: 10s, fn: mean)"}],
      "fieldConfig": {"defaults": {"thresholds": {"steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 115}, {"color": "red", "value": 121}]}}}
    },
    {
      "id": 2, "title": "Dòng điện các ngăn lộ (A)", "type": "timeseries", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
      "targets": [{"datasource": {"type": "influxdb"}, "query": "from(bucket: \"scada_data\")\n  |> range(start: -15m)\n  |> filter(fn: (r) => r._measurement == \"ied_measurements\")\n  |> filter(fn: (r) => r._field == \"current_a\")\n  |> aggregateWindow(every: 10s, fn: mean)"}]
    },
    {
      "id": 3, "title": "Tần số hệ thống (Hz)", "type": "timeseries", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
      "targets": [{"datasource": {"type": "influxdb"}, "query": "from(bucket: \"scada_data\")\n  |> range(start: -15m)\n  |> filter(fn: (r) => r._measurement == \"ied_measurements\")\n  |> filter(fn: (r) => r._field == \"freq_hz\")\n  |> aggregateWindow(every: 10s, fn: mean)"}],
      "fieldConfig": {"defaults": {"thresholds": {"steps": [{"color": "red", "value": null}, {"color": "green", "value": 49.5}, {"color": "red", "value": 50.5}]}}}
    },
    {
      "id": 4, "title": "Nhiệt độ dầu MBA (°C)", "type": "timeseries", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
      "targets": [{"datasource": {"type": "influxdb"}, "query": "from(bucket: \"scada_data\")\n  |> range(start: -15m)\n  |> filter(fn: (r) => r._measurement == \"ied_measurements\")\n  |> filter(fn: (r) => r._field == \"temp_oil_c\")\n  |> aggregateWindow(every: 10s, fn: mean)"}],
      "fieldConfig": {"defaults": {"thresholds": {"steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 75}, {"color": "red", "value": 85}]}}}
    },
    {
      "id": 5, "title": "Công suất tác dụng (MW)", "type": "timeseries", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
      "targets": [{"datasource": {"type": "influxdb"}, "query": "from(bucket: \"scada_data\")\n  |> range(start: -15m)\n  |> filter(fn: (r) => r._measurement == \"ied_measurements\")\n  |> filter(fn: (r) => r._field == \"active_power_mw\")\n  |> aggregateWindow(every: 10s, fn: mean)"}]
    },
    {
      "id": 6, "title": "Trạng thái MC (1=ĐÓNG, 0=CẮT)", "type": "timeseries", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
      "targets": [{"datasource": {"type": "influxdb"}, "query": "from(bucket: \"scada_data\")\n  |> range(start: -15m)\n  |> filter(fn: (r) => r._measurement == \"ied_measurements\")\n  |> filter(fn: (r) => r._field == \"mc_closed\")\n  |> aggregateWindow(every: 10s, fn: last)"}],
      "fieldConfig": {"defaults": {"min": 0, "max": 1, "thresholds": {"steps": [{"color": "red", "value": 0}, {"color": "green", "value": 1}]}}}
    }
  ],
  "refresh": "5s",
  "schemaVersion": 38,
  "version": 1
}
EOF

# 5. Xóa container cũ (nếu có) để chạy bản sạch
docker rm -f grafana 2>/dev/null

# 6. Khởi chạy Grafana (Map chính xác thư mục provisioning)
echo "Đang đóng gói và khởi chạy Docker Container..."
docker run -d --name grafana \
  --network substation-net --ip 172.20.0.23 \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_USER=admin \
  -e GF_SECURITY_ADMIN_PASSWORD=scada2024 \
  -e GF_USERS_ALLOW_SIGN_UP=false \
  -v $(pwd)/provisioning:/etc/grafana/provisioning \
  -v grafana-data:/var/lib/grafana \
  grafana/grafana:latest

echo "======================================================"
echo "🎉 HOÀN TẤT! GRAFANA ĐÃ SẴN SÀNG VỚI ĐẦY ĐỦ BẢNG ĐIỀU KHIỂN"
echo "👉 Truy cập: http://192.168.57.10:3000 (Tài khoản: admin / scada2024)"
echo "======================================================"
