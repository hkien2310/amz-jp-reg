@echo off
title Amazon JP Auto Register Bot
cd /d "%~dp0"

echo === KHOI DONG BOT DANG KY AMAZON JP (WINDOWS) ===

:: Kiem tra xem Python da co trong PATH chua
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo LOI: Khong tim thay Python trong PATH. Vui long cai dat Python va tick chon 'Add Python to PATH'.
    pause
    exit /b 1
)

:: Khoi tao moi truong ao neu chua co
if not exist .venv (
    echo Dang tao moi truong ao .venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo LOI: Khong the tao moi truong ao.
        pause
        exit /b 1
    )
    
    echo Dang kich hoat moi truong ao va cai dat thu vien...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install customtkinter playwright openpyxl PySocks
    if %errorlevel% neq 0 (
        echo LOI: Khong the cai dat cac thu vien can thiet.
        pause
        exit /b 1
    )
) else (
    call .venv\Scripts\activate.bat
)

echo Dang khoi chay ung dung...
python main.py
if %errorlevel% neq 0 (
    echo Co loi xay ra trong khi chay ung dung.
    pause
)
