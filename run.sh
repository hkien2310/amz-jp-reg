#!/bin/bash

# Di chuyển vào thư mục chứa script
cd "$(dirname "$0")"

echo "=== KHI KHOI DONG BOT DANG KY AMAZON JP ==="

# Kiểm tra xem .venv đã tồn tại chưa
if [ ! -d ".venv" ]; then
    echo "Dang khoi tao moi truong ao (.venv)..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Loi: Khong the khoi tao .venv. Vui long kiem tra xem python3 da duoc cai dat chua."
        exit 1
    fi
    
    echo "Dang cai dat cac thu vien can thiet..."
    .venv/bin/pip install customtkinter playwright openpyxl PySocks
    if [ $? -ne 0 ]; then
        echo "Loi: Khong the cai dat thu vien."
        exit 1
    fi
fi

# Chạy ứng dụng GUI
echo "Dang khoi chay ung dung..."
.venv/bin/python main.py
