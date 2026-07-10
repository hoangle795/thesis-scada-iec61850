#!/bin/bash

echo "=================================================="
echo " 🏛️  KHỞI CHẠY TRUNG TÂM ĐIỀU ĐỘ MÔ PHỎNG (EVN A2/B1)"
echo "=================================================="

# 1. Dọn dẹp container cũ
echo "🧹 1. Đang dọn dẹp container dispatch-center cũ (nếu có)..."
docker rm -f dispatch-center 2>/dev/null || true

# 2. Kiểm tra mạng
echo "🌐 2. Kiểm tra mạng substation-net..."
docker network create --subnet=172.20.0.0/16 substation-net 2>/dev/null || echo " -> Mạng substation-net đã sẵn sàng!"

# 3. Build Docker Image
echo "📦 3. Đang đóng gói (Build) Docker Image dispatch-center:latest..."
docker build -t dispatch-center:latest ~/thesis-scada-iec61850/dispatch-center/

# 4. Khởi chạy container
echo "⚡ 4. Đang khởi chạy Dispatch Center tại IP 172.20.0.31 (Cổng viễn thám 2404)..."
docker run -d --name dispatch-center \
  --network substation-net --ip 172.20.0.31 \
  -p 2404:2404 \
  dispatch-center:latest

echo "=================================================="
echo " 🎉 HOÀN TẤT! TRUNG TÂM ĐIỀU ĐỘ ĐANG GIÁM SÁT LƯỚI!"
echo " 👉 Lệnh xem bảng điều khiển: docker logs -f dispatch-center"
echo "=================================================="
docker ps | grep dispatch-center
