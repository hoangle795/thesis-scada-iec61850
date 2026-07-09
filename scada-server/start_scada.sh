#!/bin/bash

echo "=================================================="
echo " 🖥️  KHỞI CHẠY ĐỘC LẬP SCADA DATA SERVER"
echo "=================================================="

# 1. Dọn dẹp container cũ nếu đang chạy để tránh lỗi trùng tên
echo "🧹 1. Đang dọn dẹp container scada-server cũ (nếu có)..."
docker rm -f scada-server 2>/dev/null || true

# 2. Kiểm tra và tự động tạo mạng ảo substation-net nếu chưa có
echo "🌐 2. Kiểm tra mạng substation-net..."
docker network create --subnet=172.20.0.0/16 substation-net 2>/dev/null || echo " -> Mạng substation-net đã sẵn sàng!"

# 3. Build Docker Image (Nhờ Docker Cache nên từ lần 2 sẽ chỉ mất 1 giây!)
echo "📦 3. Đang đóng gói (Build) Docker Image scada-server:latest..."
docker build -t scada-server:latest ~/thesis-scada-iec61850/scada-server/

# 4. Khởi chạy container SCADA Server tại IP 172.20.0.20 và mở cổng 8080
echo "⚡ 4. Đang khởi chạy SCADA Server tại IP 172.20.0.20 (Cổng 8080)..."
docker run -d --name scada-server \
  --network substation-net --ip 172.20.0.20 \
  -p 8080:8080 \
  scada-server:latest

echo "=================================================="
echo " 🎉 HOÀN TẤT! SCADA SERVER ĐANG THU THẬP DỮ LIỆU!"
echo " 👉 REST API:          http://localhost:8080/api/data"
echo " 👉 Lệnh xem log live: docker logs -f scada-server"
echo "=================================================="
# Hiển thị trạng thái container vừa bật
docker ps | grep scada-server
