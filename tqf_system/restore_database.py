"""
restore_database.py
-------------------
วิธีใช้: รันไฟล์นี้จาก Windows เพื่อแทนที่ฐานข้อมูลที่เสียหาย

ปัญหา: ไฟล์ tqf_database.db มี journal file ค้างอยู่ทำให้ Python
       ไม่สามารถเปิดฐานข้อมูลได้จาก Linux sandbox

วิธีแก้: แทนที่ด้วย tqf_database_fixed.db ที่มีข้อมูลถูกต้องแล้ว
"""

import os
import shutil
from pathlib import Path

THIS_DIR = Path(__file__).parent.parent  # tqf_system folder

src = THIS_DIR / "TQF_system" / "tqf_database_fixed.db"
dst = THIS_DIR / "tqf_database.db"
journal = THIS_DIR / "tqf_database.db-journal"

print(f"Source:      {src}")
print(f"Destination: {dst}")
print(f"Journal:     {journal}")
print()

if not src.exists():
    print("ERROR: ไม่พบไฟล์ tqf_database_fixed.db")
    raise SystemExit(1)

# Remove journal file if exists
if journal.exists():
    journal.unlink()
    print("ลบ journal file แล้ว")

# Replace database
shutil.copy2(src, dst)
print("แทนที่ฐานข้อมูลเรียบร้อย!")

# Verify
import sqlite3
conn = sqlite3.connect(str(dst))
rows = conn.execute("SELECT COUNT(*) FROM tqf3_staff").fetchone()[0]
print(f"ตรวจสอบ: tqf3_staff มี {rows} rows — OK")
conn.close()
