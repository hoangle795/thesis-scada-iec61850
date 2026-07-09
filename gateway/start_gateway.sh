#!/bin/bash
echo "=================================================="
echo " 📡 KHỞI CHẠY ĐỘC LẬP SCADA GATEWAY (IEC 104)"
echo "=================================================="

echo "🧹 1. Đang dọn dẹp container gateway cũ..."
docker rm -f gateway 2>/dev/null || true

echo "🌐 2. Kiểm tra mạng substation-net..."
docker network create --subnet=172.20.0.0/16 substation-net 2>/dev/null || echo " -> Mạng substation-net đã sẵn sàng!"

echo "📦 3. Đang đóng gói (Build) Docker Image gateway:latest..."
docker build -t gateway:latest ~/thesis-scada-iec61850/gateway/

echo "⚡ 4. Đang khởi chạy Gateway tại IP 172.20.0.30..."
docker run -d --name gateway \
  --network substation-net --ip 172.20.0.30 \
  gateway:latest

echo "=================================================="
echo " 🎉 HOÀN TẤT! GATEWAY ĐANG CHUYỂN TIẾP DỮ LIỆU WAN!"
echo " 👉 Lệnh xem log live: docker logs -f gateway"
echo "=================================================="
docker ps | grep gateway
