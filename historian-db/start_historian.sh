#!/bin/bash

echo "=================================================="
echo " 🗄️  KHỞI TẠO CƠ SỞ DỮ LIỆU SCADA HISTORIAN (INFLUXDB)"
echo "=================================================="

# 1. Dọn dẹp container cũ nếu đang chạy để tránh lỗi trùng tên
echo "🧹 1. Đang dọn dẹp container influxdb cũ (nếu có)..."
docker rm -f influxdb 2>/dev/null || true

# 2. Kiểm tra và tạo mạng ảo substation-net nếu chưa có
echo "🌐 2. Kiểm tra mạng substation-net..."
docker network create --subnet=172.20.0.0/16 substation-net 2>/dev/null || echo " -> Mạng substation-net đã sẵn sàng!"

# 3. Build image (hoặc pull từ Docker Hub)
echo "📦 3. Đang chuẩn bị Docker Image cho Historian DB..."
docker build -t scada-historian:latest ~/thesis-scada-iec61850/historian-db/

# 4. Khởi chạy container InfluxDB
echo "⚡ 4. Đang khởi chạy InfluxDB tại IP 172.20.0.21..."
docker run -d --name influxdb \
  --network substation-net --ip 172.20.0.21 \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=scada2024 \
  -e DOCKER_INFLUXDB_INIT_ORG=substation \
  -e DOCKER_INFLUXDB_INIT_BUCKET=scada_data \
  -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=scada-token-2024 \
  -v influxdb-data:/var/lib/influxdb2 \
  scada-historian:latest

echo "=================================================="
echo " 🎉 HOÀN TẤT! INFLUXDB HISTORIAN ĐANG HOẠT ĐỘNG!"
echo " 👉 Truy cập giao diện quản lý tại: http://192.168.57.10:8086"
echo "=================================================="
