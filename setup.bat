@echo off
chcp 65001 > nul
title ติดตั้งส่วนเสริม Meeting Summarizer

cd /d "%~dp0"

echo =================================================================
echo         🛠️ กำลังติดตั้งไลบรารีที่จำเป็น (Setup Dependencies)
echo =================================================================
echo.

WHERE uv >nul 2>nul
IF %ERRORLEVEL% EQU 0 (
    echo พบเครื่องมือ uv ในระบบ กำลังติดตั้งด้วย uv...
    IF NOT EXIST ".venv" (
        uv venv .venv
    )
    uv pip install -r requirements.txt
) ELSE (
    echo กำลังติดตั้งด้วย python...
    IF NOT EXIST ".venv" (
        python -m venv .venv
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo =================================================================
echo  ✅ ติดตั้งไลบรารีเรียบร้อยแล้ว! 
echo  กรุณาเปิดไฟล์ .env เพื่อใส่ GEMINI_API_KEY ก่อนเริ่มใช้งาน
echo =================================================================
echo.
pause
