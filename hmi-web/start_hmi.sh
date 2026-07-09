#!/bin/bash

echo "=================================================="
echo " 🌐 KHỞI CHẠY ĐỘC LẬP SCADA WEB HMI DASHBOARD"
echo "=================================================="

# 1. Dọn dẹp container hmi-web cũ (nếu có) để tránh lỗi trùng tên
echo "🧹 1. Đang dọn dẹp container hmi-web cũ..."
docker rm -f hmi-web 2>/dev/null || true

# 2. Kiểm tra mạng substation-net
echo "🌐 2. Kiểm tra mạng substation-net..."
docker network create --subnet=172.20.0.0/16 substation-net 2>/dev/null || echo " -> Mạng substation-net đã sẵn sàng!"

# 3. Build Docker Image cho Web HMI
echo "📦 3. Đang đóng gói (Build) Docker Image hmi-web:latest..."
docker build -t hmi-web:latest ~/thesis-scada-iec61850/hmi-web/

# 4. Khởi chạy container Web HMI tại IP 172.20.0.22 và mở cổng 9090
echo "⚡ 4. Đang khởi chạy Web HMI tại IP 172.20.0.22 (Cổng 9090)..."
docker run -d --name hmi-web \
  --network substation-net --ip 172.20.0.22 \
  -p 9090:80 \
  hmi-web:latest

echo "=================================================="
echo " 🎉 HOÀN TẤT! WEB HMI ĐÃ SẴN SÀNG HOẠT ĐỘNG!"
echo " 👉 Truy cập giao diện từ Windows: http://192.168.56.10:9090"
echo "=================================================="
# Hiển thị trạng thái container vừa bật
docker ps | grep hmi-web
