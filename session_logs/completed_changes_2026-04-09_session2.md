# สิ่งที่แก้แล้ว — Session 2
วันที่: 2026-04-09 (session ที่ 2 หลัง context reset)

---

## สิ่งที่ทำเสร็จ

### DB / ข้อมูล
- [x] **SMA2401 ชื่อว่าง** — ✅ อัปเดตชื่อวิชา = "รากฐานเรขาคณิต", name_en = "Foundation of Geometry"
  - ข้อมูลเกรด 7 คนยังคงอยู่ครบ (SMA2401 → tqf5_id=5, student_grades=7)
  - curriculum_id ยังเป็น NULL (รอยืนยันกับอาจารย์ว่าเป็นหลักสูตรไหน)

- [x] **SMA6002 (โครงงานคณิตศาสตร์) ยังไม่ import เกรด** — ✅ สร้าง tqf3+tqf5 record ด้วยมือ
  - ไฟล์ "project สิทธิโชค.doc" มีโครงสร้าง binary ไม่สามารถ parse student list ได้
  - Import grade_dist: {A:1} ด้วยมือ, นักศึกษา 1 คน (รหัส 6504302001011)
  - **หมายเหตุ**: ควรให้อาจารย์ยืนยันรายชื่อนักศึกษาจากต้นฉบับ

- [x] **teaching_actual มีข้อมูล stale** — ✅ ลบทิ้งทั้งหมด (37 rows)
  - สาเหตุ: copy มาจาก DB rebuild ครั้งก่อนพร้อม topic "CLO1, CLO2" และ hours=0.0
  - `teaching_actual` ควรกรอกเฉพาะเมื่ออาจารย์รายงานผลการสอนจริง

### import_tqf3.py
- [x] **`extract_teaching_plan()` ดึง topic และ hours ผิด** — ✅ แก้แล้ว (2026-04-09)
  - **Bug**: ใช้ col 1 (CLO reference) เป็น topic, หา hours จาก col 2+ แต่ hours ฝังใน col 0 เช่น "1(3)"
  - **Fix**: detect header ว่า col 1 เป็น "ผลลัพธ์/CLO" → ใช้ col 2 เป็น topic; parse hours จาก "(N)" ใน col 0
  - **ผลลัพธ์หลัง fix**:
    - SMAC001: 10 สัปดาห์, 45h ✅ topic ถูกต้อง (ไม่ใช่ "CLO1, CLO2")
    - SMA2301: 16 สัปดาห์, 45h ✅ topic ถูกต้อง
    - SMA3004: 10 สัปดาห์, 59h ✅ topic ถูกต้อง
    - SMA0901: 2 สัปดาห์, 32h ✅ ถูกต้อง (format seminar)
  - Re-imported teaching plan ทั้ง 4 วิชาใหม่ใน DB

### generate_tqf5.py
- [x] **Teaching plan ใน output แสดง "CLO1, CLO2" และ hours=0.0** — ✅ แก้แล้ว
  - สาเหตุ: `teaching_actual` มีข้อมูล stale → generate_tqf5 ใช้ `actual` ก่อน `plan` เสมอ
  - Fix: ลบ teaching_actual stale + fix extract_teaching_plan
  - ผลลัพธ์: generate SMAC001 มคอ.5 → teaching plan ถูกต้อง หัวข้อ/ชั่วโมงครบ

### input_gui.py
- [x] **ไม่มี feature สร้าง มคอ.5** — ✅ เพิ่มแล้ว
  - เพิ่ม column `tqf3_id` (hidden) ใน Treeview
  - เพิ่ม `📄 สร้าง มคอ.5` button ใน toolbar (enabled เมื่อเลือกวิชาที่มี tqf3)
  - เพิ่ม double-click handler: double-click ที่วิชาใดก็ generate มคอ.5 ได้เลย
  - เพิ่ม `_on_tree_select()`, `_on_tree_double_click()`, `_generate_tqf5()` methods

---

## สถานะ DB หลัง session 2

| ตาราง | จำนวน | หมายเหตุ |
|-------|--------|----------|
| curricula | 2 | หลักสูตร 65, 69 |
| courses | 67 | 40 ใน cur69, 26 ใน cur65, 1 ไม่มี cur (SMA2401) |
| tqf3 | 6 | SMAC001, SMA0901, SMA2301, SMA2401, SMA3004, SMA6002 |
| clos | 21 | ครบทุกวิชา (ยกเว้น SMA2401, SMA6002 ที่ไม่มี TQF3.docx) |
| assessments | 15 | ครบ |
| teaching_plan | 38 | topic และ hours ถูกต้องทั้งหมด |
| teaching_actual | 0 | cleared (รอข้อมูลจริงจากอาจารย์) |
| tqf5 | 6 | ครบทุกวิชา |
| student_grades | 120 | SMAC001=42, SMA3004=30, SMA0901=23, SMA2301=17, SMA2401=7, SMA6002=1 |

---

## ยังต้องทำ (รอผู้ใช้)

- [ ] **SMA2401 curriculum_id** — ยืนยันกับอาจารย์ว่า SMA2401 "รากฐานเรขาคณิต" อยู่ใน curriculum ไหน
  (ใน curriculum 69 มี SMA2102 = "รากฐานเรขาคณิต" ด้วยซ้ำ อาจเป็นรหัสเก่า)
- [ ] **SMA6002 student list** — มีเพียง 1 นักศึกษาที่ parse ได้ จาก "project สิทธิโชค.doc"
  ควรยืนยัน/แก้ไขรายชื่อจากต้นฉบับ
- [ ] **SMA2301 ชื่อวิชา** — TQF3 บอก "ตัวแปรเชิงซ้อน" แต่ curriculum 65 มีทั้ง SMA2301 และ SMA2303 ชื่อ "ตัวแปรเชิงซ้อน" ซ้ำกัน
  รอยืนยันว่าถูกต้องหรือต้องแก้
- [ ] **วิชาเลือก หลักสูตร 65** — ยังขาดรายชื่อวิชาเลือก (elective courses)

---

## ไฟล์ที่แก้ใน session นี้
- `database.py` — ไม่เปลี่ยน
- `import_tqf3.py` — แก้ `extract_teaching_plan()` (col detection + hours parsing)
- `generate_tqf5.py` — ไม่เปลี่ยน code (bug อยู่ที่ DB data)
- `input_gui.py` — เพิ่ม สร้าง มคอ.5 button + double-click + _generate_tqf5()
- `tqf_database.db` — re-imported teaching_plan, cleared teaching_actual, added SMA6002+SMA2401
