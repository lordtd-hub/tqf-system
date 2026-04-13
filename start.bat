@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ===================================
echo  ระบบ TQF — มคอ.3 to มคอ.5
echo ===================================

:: ตรวจสอบ streamlit
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo กำลังติดตั้ง dependencies...
    pip install -r requirements.txt
)

echo กำลังเปิดระบบ...
echo เปิด browser ที่: http://localhost:8501
streamlit run app.py --server.port 8501 --server.headless false

pause
