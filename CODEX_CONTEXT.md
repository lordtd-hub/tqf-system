# Codex Context — TQF System
> วาง content ไฟล์นี้ใน System Prompt ของ Codex ก่อนเริ่มงานทุกครั้ง
> หรือบอก Codex ว่า: "อ่าน CODEX_CONTEXT.md, HANDOFF.md, PROJECT_REFERENCE.md ก่อนเริ่มทำงาน"

---

## โปรเจคนี้คืออะไร

ระบบจัดการ TQF (มคอ.) สำหรับสาขาวิชาคณิตศาสตร์ มหาวิทยาลัยราชภัฏสุราษฎร์ธานี
เขียนด้วย Python (tkinter GUI + SQLite) ทำงานบน Windows

**stack:** Python 3, tkinter, sqlite3, python-docx, pdfplumber, openpyxl

---

## โครงสร้างไฟล์

```
tqf_system/
├── database.py        ← DB layer ทั้งหมด (schema + CRUD)
├── import_tqf3.py     ← Parse มคอ.3 .docx/.pdf → DB
├── import_grades.py   ← Parse ไฟล์เกรด .doc/.rtf/.docx/.pdf → DB
├── input_gui.py       ← GUI หลัก (tkinter) — เปิดด้วย นำเข้าข้อมูล.bat
├── generate_tqf5.py   ← สร้างไฟล์ Word มคอ.5
├── app.py             ← Streamlit web app (ทางเลือก)
├── tqf_database.db    ← SQLite DB (อย่า commit ลง git)
├── HANDOFF.md         ← *** อ่านก่อนทำงานทุกครั้ง ***
├── PROJECT_REFERENCE.md ← Schema ทั้งหมด + function list
├── ROADMAP_v2.md      ← แผนพัฒนา v2
└── RULES.md           ← กฎการทำงาน (อ่าน!)
```

---

## กฎสำคัญที่ต้องปฏิบัติ (Codex MUST follow)

### 1. อ่านก่อนเสมอ
- `HANDOFF.md` — สถานะปัจจุบัน งานค้าง งานต่อไป
- `PROJECT_REFERENCE.md` — Schema DB และ function signatures
- `RULES.md` — กฎทั้งหมด

### 2. DB Rules
- **ห้าม** `ALTER TABLE RENAME TO` — ถ้า schema เปลี่ยน ต้องเขียน migration ใน `init_db()`
- Migration pattern: `ALTER TABLE xxx ADD COLUMN yyy` (ถ้า column ไม่มีใน PRAGMA table_info)
- ทดสอบ SQLite ต้องใช้ path ไม่มีช่องว่าง (copy ไป `/tmp/` ก่อนถ้าจำเป็น)

### 3. Coding Rules
- ทุก DB operation ใน GUI ต้องรันใน `threading.Thread` (ไม่ block UI)
- `db.init_db()` เรียกก่อนทุก operation
- ไม่ commit .db, __pycache__, *.xlsx ลง git (ดู .gitignore)

### 4. อัพเดทเมื่อเสร็จ
- อัพเดท `HANDOFF.md` ทุกครั้งหลังทำงาน (section "สถานะล่าสุด")
- ถ้าแก้ schema ให้อัพเดท `PROJECT_REFERENCE.md` ด้วย

---

## Schema หลัก (ย่อ)

```
curricula(id, version, name_th, effective_year)
    └── courses(id, curriculum_id, code, name_th, credits_text, course_type, ...)
            └── tqf3(id, course_id, semester, year, is_special, source_type, ...)
                    ├── clos(tqf3_id, clo_number, description, plo_mapping, ...)
                    ├── teaching_plan(tqf3_id, week, topic, hours_planned)
                    ├── assessments(tqf3_id, name, weight_pct, clo_mapping)
                    └── tqf5(tqf3_id → UNIQUE)
                            ├── student_grades(tqf5_id, student_id, grade, ...)
                            └── teaching_actual(tqf5_id, ...)

-- ตาราง v2 (จะเพิ่มใน ROADMAP_v2.md)
plos(curriculum_id, plo_number, category, description)
course_clos(course_id, clo_number, description, plo_mapping, pass_threshold_pct)
course_assessments(course_id, name, full_score, weight_pct, clo_mapping)
```

UNIQUE constraints สำคัญ:
- `courses`: `UNIQUE(code, curriculum_id)`
- `tqf3`: `UNIQUE(course_id, semester, year, is_special)`
- `clos`: `UNIQUE(tqf3_id, clo_number)`

---

## งานปัจจุบัน

**ดู `HANDOFF.md` สำหรับ task ที่ต้องทำต่อ**

---

## วิธีรัน/ทดสอบ

```bash
# เปิด GUI
cd tqf_system
python input_gui.py

# ทดสอบ syntax
python -c "import ast; ast.parse(open('input_gui.py').read()); print('OK')"

# ทดสอบ DB (ถ้า path มีช่องว่าง)
cp tqf_database.db /tmp/test.db
python -c "import sqlite3; conn=sqlite3.connect('/tmp/test.db'); ..."
```

---

## ข้อมูลที่ Codex ควรรู้

- **ภาษา**: โค้ดเป็นภาษาอังกฤษ, comment/ชื่อตัวแปรบางอันเป็นไทย, ผู้ใช้สื่อสารภาษาไทย
- **Windows**: path separator `\`, encoding cp874 สำหรับไฟล์เกรด .doc เก่า
- **is_special**: 0=เปิดปกติ (N0x section), 1=เปิดพิเศษ (P0x section)
- **หลักสูตร**: มี 2 หลักสูตร — 65 (curriculum_id=2) และ 69 (curriculum_id=1)
