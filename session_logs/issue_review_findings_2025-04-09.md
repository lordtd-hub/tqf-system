# สิ่งที่ต้องแก้ — จากการตรวจโปรเจค
วันที่พบ: 2026-04-09

---

## สิ่งที่ต้องทำ

### DB / Schema
- [x] FK ใน `tqf3` ยังชี้ไปที่ `courses_old` แทน `courses` — ✅ แก้แล้ว (2026-04-09): rebuild DB ทั้งหมดด้วย schema ใหม่, copy data ด้วย `conn.backup()`
- [x] FK ใน `clos`, `teaching_plan`, `assessments`, `tqf5` ชี้ไปที่ `tqf3_old` — ✅ แก้แล้ว (2026-04-09): rebuild DB พร้อมกัน
- [x] `UNIQUE(code)` แบบ global ทำให้วิชาเดียวกันข้ามหลักสูตรไม่ได้ — ✅ แก้แล้ว (2026-04-09): เปลี่ยนเป็น `UNIQUE(code, curriculum_id)`
- [x] `upsert_course(curriculum_id=None)` สร้าง record ซ้ำ เพราะ NULL != NULL ใน SQLite — ✅ แก้แล้ว (2026-04-09): เพิ่ม logic ค้นหา existing record ก่อนใน `database.py`

### import_tqf3.py
- [x] `assessments` ดึงไม่ได้เลย (0 รายการ) ทุกไฟล์ — ✅ แก้แล้ว (2026-04-09): เพิ่ม keyword `ร้อยละ`, `รายการ` ใน `extract_assessments()` ผลลัพธ์: SMAC001=5, SMA2301=3, SMA3004=4, SMA0901=3 รายการ
- [x] `SMA0901 (seminar)` plan ได้แค่ 2 สัปดาห์ — ✅ ถูกต้องแล้ว ไฟล์ seminar มีแค่ 2 แถว (สัปดาห์ 1 และ 2-16) ตรงตาม format จริง
- [x] `SMA2301 (complex)` CLO ได้แค่ 1 ข้อ — ✅ แก้แล้ว (2026-04-09): `extract_clos()` รองรับ CLO ที่ไม่มีเลขนำหน้าแล้ว ผลลัพธ์: SMA2301=5 CLOs

### ข้อมูล
- [ ] `SMA2301` ชื่อในไฟล์ TQF3 คือ "ตัวแปรเชิงซ้อน" แต่ใน curriculum 65 คือ "การวิเคราะห์เชิงคณิตศาสตร์" — รอตรวจสอบกับอาจารย์
- [ ] หลักสูตร 65 ยังขาด "วิชาเลือก" — รอผู้ใช้ให้ข้อมูล
- [x] `get_course_by_code()` คืน record แรกโดยไม่ filter `curriculum_id` — ✅ แก้แล้ว (2026-04-09): เพิ่ม parameter `curriculum_id=None`, default คืน record ที่มี curriculum_id ก่อน

### GUI
- [x] Tab 1 ใช้ INNER JOIN ทำให้วิชาที่ยังไม่มี มคอ.3 ไม่แสดง — ✅ แก้แล้ว (2026-04-09): เปลี่ยนเป็น LEFT JOIN, แสดงวิชาทุกวิชา
- [x] ไม่มี filter หลักสูตร — ✅ เพิ่มแล้ว (2026-04-09): Dropdown filter "ทั้งหมด / หลักสูตร 65 / หลักสูตร 69" + คอลัมน์ "หลักสูตร" ใน Treeview

---

## สาเหตุ / บริบท

Bug ทั้งหมดเกิดจากการทำ `ALTER TABLE RENAME TO xxx_old` แล้ว recreate table ระหว่าง session ก่อนหน้า SQLite เก็บ FK reference ตามชื่อตารางเดิม ทำให้ตารางลูก (clos, tqf5 ฯลฯ) ยังชี้ไปที่ตารางที่ถูกลบแล้ว

---

## ไฟล์ที่เกี่ยวข้อง
- `database.py` — `upsert_course()`, SCHEMA definition, `UNIQUE(code, curriculum_id)`
- `import_tqf3.py` — `extract_assessments()`, `extract_teaching_plan()`, `extract_clos()`
- `input_gui.py` — `_refresh_courses()` query (ใช้ INNER JOIN กับ tqf3)
- `tqf_database.db` — rebuild แล้ว integrity=ok ✅

---

## สิ่งที่ทำไปแล้ว (2026-04-09)

- Rebuild `tqf_database.db` ด้วย schema ที่ถูกต้องทั้งหมด — FK ครบ, integrity=ok
- แก้ `database.py`: `upsert_course()` ไม่สร้าง duplicate เมื่อ `curriculum_id=None`
- แก้ `database.py`: SCHEMA ใช้ `UNIQUE(code, curriculum_id)` แทน `UNIQUE(code)`
- ทดสอบ `import_tqf3` ทั้ง 4 ไฟล์ → ✅ ทั้งหมด
- ทดสอบ `import_grades` ทั้ง 5 ไฟล์ (.doc) → ✅ ทั้งหมด (119 นักศึกษา)
- ทดสอบ `export_to_excel` → ✅ 4 sheets สมบูรณ์
- เพิ่ม `RULES.md` — กฎการทำงานสำหรับ AI
- เพิ่ม `PROJECT_REFERENCE.md` — โครงสร้างโปรเจคสำหรับอ้างอิง
