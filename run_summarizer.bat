@echo off
chcp 65001 > nul
title Meeting Summarizer - สรุปบันทึกการประชุมอัตโนมัติ

cd /d "%~dp0"

echo =================================================================
echo        🎙️ กำลังเริ่มระบบสรุปเสียงบันทึกการประชุม...
echo =================================================================
echo.

IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" summarizer.py
) ELSE (
    python summarizer.py
)

echo.
echo กดปุ่มใดๆ เพื่อปิดหน้าต่างนี้...
pause > nul
