# HANDOFF — TQF System
> ไฟล์นี้คือ "กระดานข่าว" ของโปรเจค
> **อ่านก่อนทำงานทุกครั้ง — อัพเดทหลังทำงานทุก session**
> ทั้ง Cowork, Codex, และทุกเครื่องใช้ไฟล์นี้เป็น source of truth

---

## 🟢 สถานะล่าสุด
อัพเดท: 2026-04-10  |  เครื่อง: PC  |  เครื่องมือ: Cowork

### งานที่เสร็จแล้วใน session นี้
- [x] เพิ่ม `is_special` column ใน `tqf3` + migration + upsert_tqf3
- [x] import_grades.py: auto-detect P0x section, รับ `is_special` param
- [x] input_gui.py: แสดง ★ วิชาพิเศษ, radio ปกติ/พิเศษ ใน GradeInfoDialog + CourseEditDialog
- [x] input_gui.py: เพิ่ม `course_id` hidden column + `btn_edit` + `CourseEditDialog`
- [x] ROADMAP_v2.md: วางแผน 3-layer architecture ใหม่ (PLOs + course_clos + course_assessments)
- [x] ออกแบบ multi-device / multi-AI workflow (ไฟล์นี้ + CODEX_CONTEXT.md)
- [x] Initialized local Git repository on branch `main` for source tracking
- [x] database.py: เพิ่ม 3 ตารางใหม่ (`plos`, `course_clos`, `course_assessments`) + CRUD functions
- [x] database.py: เพิ่ม `copy_course_template_to_tqf3()` — snapshot CLO/assessment template ไป tqf3
- [x] input_gui.py: เพิ่ม Tab 3 "ฐานข้อมูลหลักสูตร" — PanedWindow, course treeview, detail panel
- [x] input_gui.py: `CourseAddDialog`, `PLOManagerDialog`, `PLOEditRowDialog` — CRUD PLO/วิชา
- [x] input_gui.py: `CourseCLOEditor` (CLO tab + Assessment tab), `CLOEditRowDialog`, `AsmtEditRowDialog`
- [x] Syntax check input_gui.py ✅ OK

---

## 🔵 งานที่ค้างอยู่ (In Progress)
_ไม่มีงานค้าง — พร้อมเริ่ม Phase ถัดไป_

---

## 🟡 งานต่อไป (Next Up)
**รอก่อน:**
- [ ] ผู้ใช้ให้ template มคอ.3 แบบละเอียด → วิเคราะห์ fields → อัพเดท schema
- [ ] ผู้ใช้ให้รายชื่อ PLO ของหลักสูตร 65 และ 69

**ทำได้เลย (ไม่รอ template):**
- [ ] `import_courses_excel.py` — bulk import วิชาจาก Excel (template + parser)
- [ ] `TQF3GenerateDialog` — UI เลือกวิชา/ปี/เทอม → `copy_course_template_to_tqf3()` → สร้าง tqf3 ใหม่
- [ ] Tab 3: ทดสอบ + polish UI (ปุ่ม enable/disable, error handling)
- [ ] Sync course_clos เมื่อ import มคอ.3 ใหม่ (opt-in อัพเดท template)
- [ ] `generate_tqf5.py` — ทดสอบกับ DB จริง

---

## 🔴 ข้อควรระวัง / Known Issues
- **DB path มีช่องว่าง**: `tqf gen/` → SQLite ใน sandbox เปิดไม่ได้ตรงๆ ต้อง copy ไป `/tmp/` ก่อนทดสอบ บน Windows production ใช้ได้ปกติ
- **LibreOffice**: import_tqf3.py ต้องใช้ LibreOffice แปลง .doc → .docx ถ้าไม่มีจะ error (import_grades.py มี native RTF parser ของตัวเอง)
- **tqf3 UNIQUE**: `(course_id, semester, year, is_special)` — วิชาพิเศษ (P0x) กับปกติ (N0x) เก็บแยก record

---

## 📁 ไฟล์ Reference สำคัญ
| ไฟล์ | ใช้ทำอะไร |
|------|-----------|
| `PROJECT_REFERENCE.md` | Schema ทั้งหมด, ERD, function list |
| `ROADMAP_v2.md` | แผนพัฒนา v2 (3-layer architecture) |
| `RULES.md` | กฎการทำงานสำหรับ AI ทุกตัว |
| `CODEX_CONTEXT.md` | Context สำหรับ Codex โดยเฉพาะ |
| `HANDOFF.md` | ไฟล์นี้ — สถานะปัจจุบัน |

---

## 📋 Template อัพเดทไฟล์นี้ (ทำทุกครั้งหลังทำงาน)

```markdown
## 🟢 สถานะล่าสุด
อัพเดท: YYYY-MM-DD  |  เครื่อง: PC/MacBook  |  เครื่องมือ: Cowork/Codex

### งานที่เสร็จแล้วใน session นี้
- [x] ...

## 🔵 งานที่ค้างอยู่
- [ ] (ถ้ามี) อธิบายว่าหยุดตรงไหน และไฟล์/