@echo off
chcp 65001 > nul
cd /d "%~dp0"
python -c "import database as db; db.export_to_excel()"
echo.
echo เสร็จแล้ว! เปิดไฟล์ tqf_database_view.xlsx ได้เลยครับ
pause
