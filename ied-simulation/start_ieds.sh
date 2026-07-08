#!/bin/bash

echo "=================================================="
echo " 🚀 BẮT ĐẦU KHỞI TẠO HỆ THỐNG IED GIẢ LẬP"
echo "=================================================="

# 1. Dọn dẹp các container cũ nếu đang chạy để tránh lỗi trùng tên
echo "🧹 1. Đang dọn dẹp các container IED cũ (nếu có)..."
docker rm -f ied131 ied171 ied172 ied112 2>/dev/null || true

# 2. Kiểm tra và tạo mạng ảo substation-net nếu chưa có
echo "🌐 2. Kiểm tra mạng substation-net..."
docker network create --subnet=172.20.0.0/16 substation-net 2>/dev/null || echo " -> Mạng substation-net đã sẵn sàng!"

# 3. Build Docker Image từ Dockerfile
echo "📦 3. Đang đóng gói (Build) Docker Image ied-simulator:latest..."
docker build -t ied-simulator:latest ~/thesis-scada-iec61850/ied-simulation/

# 4. Khởi chạy 4 IED containers
echo "⚡ 4. Đang khởi chạy 4 container IED cho các Ngăn lộ..."
docker run -d --name ied131 --network substation-net --ip 172.20.0.10 -e IED_NAME="IED131_NganLo131" ied-simulator:latest
docker run -d --name ied171 --network substation-net --ip 172.20.0.11 -e IED_NAME="IED171_NganLo171" ied-simulator:latest
docker run -d --name ied172 --network substation-net --ip 172.20.0.12 -e IED_NAME="IED172_NganLo172" ied-simulator:latest
docker run -d --name ied112 --network substation-net --ip 172.20.0.13 -e IED_NAME="IED112_NganLo112" ied-simulator:latest

echo "=================================================="
echo " 🎉 HOÀN TẤT! DANH SÁCH CÁC IED ĐANG HOẠT ĐỘNG:"
echo "=================================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|ied"
