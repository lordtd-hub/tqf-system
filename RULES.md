# กฎการทำงานของ AI ในโปรเจค TQF System

## 1. เมื่อสรุปสิ่งที่ต้องทำ → บันทึกเป็น .md ทันที

**ชื่อไฟล์** ต้องสื่อถึงเนื้อหา เช่น:
- `สิ่งที่ต้องแก้_db_schema.md`
- `สิ่งที่ต้องทำ_gui_improvements.md`
- `สิ่งที่ต้องแก้_import_bugs.md`

**โครงสร้างไฟล์บังคับ:**
```
# [หัวเรื่อง]
วันที่พบ: YYYY-MM-DD

## สิ่งที่ต้องทำ
- [ ] งาน 1 — อธิบายรายละเอียด
- [ ] งาน 2 — อธิบายรายละเอียด

## สาเหตุ / บริบท
อธิบายว่าทำไมถึงต้องทำ

## ไฟล์ที่เกี่ยวข้อง
- `database.py` — บรรทัด X
- `import_tqf3.py` — ฟังก์ชัน Y
```

---

## 2. เมื่อแก้เสร็จ → กลับมาอัปเดตไฟล์ .md นั้น

เปลี่ยน `- [ ]` เป็น `- [x]` พร้อมเพิ่มบรรทัด:
```
- [x] งาน 1 — ✅ แก้แล้ว (YYYY-MM-DD): อธิบายว่าแก้อย่างไร
```

เพิ่มหมวด `## สิ่งที่ทำไปแล้ว` ท้ายไฟล์:
```
## สิ่งที่ทำไปแล้ว
- แก้ไข X โดย Y
- เพิ่ม Z ใน function W
```

---

## 3. กฎเพิ่มเติมสำหรับโปรเจคนี้

### DB / Schema
- **ห้าม** ใช้ `ALTER TABLE RENAME` โดยตรงในโค้ด production — ต้องสร้าง DB ใหม่จาก SCHEMA แล้ว copy data แทน
- ทุกครั้งที่แก้ schema ใน `database.py` ต้อง rebuild DB ใน /tmp แล้ว backup ด้วย `conn.backup()` (ไม่ใช่ `iterdump()`)
- ตรวจ FK integrity ด้วย `PRAGMA integrity_check` ทุกครั้งหลัง migration

### ไฟล์ .db
- แก้ทุกอย่างใน `/tmp/` ก่อนเสมอ (sandbox mount ไม่รองรับ SQLite file lock)
- copy กลับด้วย `conn.backup()` เท่านั้น — ไม่ใช้ `cp` โดยตรงหลังทำ write operation
- ตรวจด้วย DB Browser for SQLite บน Windows ก่อน deploy

### import_tqf3.py
- ไม่ส่ง `curriculum_id` ไปใน `upsert_course` → `upsert_course` จะหา existing record แทนอัตโนมัติ (logic อยู่ใน `database.py`)
- CLO ที่ได้น้อยผิดปกติ (เช่น seminar ได้แค่ 1 ข้อ) → ตรวจว่าไฟล์ docx ใช้ heading format ตรงกับ parser ไหม

### import_grades.py
- รองรับ `.doc` / `.rtf` ด้วย `parse_rtf_tables()` (ไม่ต้อง LibreOffice)
- ถ้าหาวิชาไม่เจอใน DB → สร้าง empty record ไว้ก่อน (แจ้งเตือนใน log)
- ชื่อวิชาที่ได้จากไฟล์เกรดอาจไม่ตรงกับ curriculum — ให้ยึด curriculum เป็น master

### GUI (input_gui.py)
- ทุก DB operation ใน GUI ต้องรันใน background thread (`threading.Thread`)
- `db.init_db()` ต้องเรียกก่อน operation อื่นเสมอ
- Error ต้องแสดงใน log box ไม่ใช่ popup (ยกเว้น export สำเร็จ)

---

## 4. Workflow มาตรฐาน

```
พบ bug / งานใหม่
    ↓
สร้างไฟล์ สิ่งที่ต้องแก้_XXXX.md
    ↓
แก้โค้ด / rebuild DB
    ↓
ทดสอบ runtime จริง (ไม่ใช่แค่ syntax check)
    ↓
อัปเดต .md → เปลี่ยน [ ] เป็น [x]
    ↓
อัปเดต PROJECT_REFERENCE.md ถ้า schema หรือ behavior เปลี่ยน
    ↓
อัปเดต HANDOFF.md (สถานะล่าสุด + งานต่อไป)
    ↓
git commit + push (ถ้า setup git แล้ว)
```

---

## 5. Multi-Device / Multi-AI Workflow

โปรเจคนี้ทำงานบน 3 environment:

| Environment | เครื่องมือ | ใช้เมื่อ |
|-------------|-----------|---------|
| PC (หลัก) | Cowork | งานหลัก, GUI, DB, วิเคราะห์ซับซ้อน |
| PC (fallback) | Codex | โทเคน Cowork หมด, งาน coding ตรงๆ |
| MacBook | Cowork หรือ Codex | ออกนอกสถานที่ |

### กฎ: เริ่ม session ทุกครั้ง
1. **อ่าน `HANDOFF.md` ก่อนเสมอ** — รู้ว่างานค้างอยู่ตรงไหน
2. ถ้าใช้ git: `git pull` ก่อนทำงาน
3. ถ้า DB อาจเปลี่ยน (ทำงานคนละเครื่องมาก่อน): ตรวจสอบไฟล์ DB

### กฎ: จบ session ทุกครั้ง
1. **อัพเดท `HANDOFF.md`** — เขียนว่าทำอะไรไป และงานต่อไปคืออะไร
2. ถ้าแก้ schema: อัพเดท `PROJECT_REFERENCE.md`
3. ถ้าใช้ git: `git add *.py *.md .gitignore` → `git commit` → `git push`
4. **ห้าม commit** ไฟล์ .db, __pycache__, .xlsx (ดู .gitignore)

### วิธีส่งงานให้ Codex
```
บอก Codex ว่า:
"อ่านไฟล์เหล่านี้ก่อน: CODEX_CONTEXT.md, HANDOFF.md
แล้วทำงานต่อตาม HANDOFF.md section งานต่อไป"
```

### วิธีตั้ง Git (ทำครั้งแรกครั้งเดียว)
```bash
cd "path/to/tqf gen/tqf_system"
git init
git add *.py *.md *.bat *.txt .gitignore requirements.txt
git commit -m "initial: TQF system"
git remote add origin https://github.com/YOUR_USERNAME/tqf-system.git
git push -u origin main
```

### Sync DB ระหว่างเครื่อง
- **DB ไม่ใส่ใน git** (binary เปลี่ยนบ่อย)
- ใช้ **cloud folder** (OneDrive/Google Drive) sync โฟลเดอร์ทั้งหมดแทน
- ถ้าใช้ git เสริม: export Excel ก็พอสำหรับดูข้อมูลบน MacBook
