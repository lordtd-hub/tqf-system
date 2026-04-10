# TQF System — Project Reference
ระบบฐานข้อมูล มคอ. สาขาวิชาคณิตศาสตร์ มหาวิทยาลัยราชภัฏสุราษฎร์ธานี

---

## โครงสร้างไฟล์

```
tqf_system/
├── database.py          ← DB layer: schema + CRUD helpers ทั้งหมด
├── import_tqf3.py       ← Parser มคอ.3 (.docx) → ฐานข้อมูล
├── import_grades.py     ← Parser ไฟล์เกรด (.doc/.rtf/.docx) → ฐานข้อมูล
├── input_gui.py         ← GUI หลัก (tkinter) สำหรับดูข้อมูลและนำเข้าไฟล์
├── app.py               ← Streamlit web app (ทางเลือก)
├── generate_tqf5.py     ← สร้างไฟล์มคอ.5 .docx จากข้อมูลในฐานข้อมูล
├── tqf_database.db      ← SQLite database (ไฟล์หลัก)
├── tqf_database_view.xlsx ← Excel export ล่าสุด
├── requirements.txt     ← Python dependencies
├── นำเข้าข้อมูล.bat     ← ดับเบิลคลิกเปิด GUI
├── export_excel.bat     ← ดับเบิลคลิก export Excel
└── start.bat            ← เปิด Streamlit app (port 8501)
```

---

## Database Schema

### ตาราง `curricula` — หลักสูตร
| column | type | คำอธิบาย |
|--------|------|-----------|
| id | INTEGER PK | |
| version | TEXT UNIQUE | "65", "69" |
| name_th | TEXT | ชื่อหลักสูตรภาษาไทย |
| effective_year | INTEGER | ปีที่เริ่มใช้ (2565, 2569) |

ข้อมูลปัจจุบัน: id=1 (หลักสูตร 69), id=2 (หลักสูตร 65)

---

### ตาราง `courses` — รายวิชา
| column | type | คำอธิบาย |
|--------|------|-----------|
| id | INTEGER PK | |
| curriculum_id | INTEGER FK | → curricula.id |
| code | TEXT | รหัสวิชา เช่น SMAC001 |
| name_th / name_en | TEXT | ชื่อวิชา |
| credits_text | TEXT | เช่น "3(3-0-6)" |
| credit_lecture/lab/self | INTEGER | หน่วยกิตแยกส่วน |
| course_type | TEXT | วิชาแกน / วิชาบังคับ / วิชาเลือก / สหกิจศึกษา |
| description_th | TEXT | คำอธิบายรายวิชา |
| UNIQUE | | (code, curriculum_id) |

**ข้อมูลปัจจุบัน:**
- หลักสูตร 65 (curriculum_id=2): 26 วิชา (7 แกน + 16 บังคับ + 3 สหกิจ)
- หลักสูตร 69 (curriculum_id=1): 40 วิชา (7 แกน + 14 บังคับ + 16 เลือก + 3 สหกิจ)

---

### ตาราง `tqf3` — มคอ.3 แต่ละภาค/ปี
| column | type | คำอธิบาย |
|--------|------|-----------|
| id | INTEGER PK | |
| course_id | INTEGER FK | → courses.id |
| semester | INTEGER | 1 หรือ 2 |
| year | INTEGER | ปีการศึกษา เช่น 2568 |
| instructor_main | TEXT | อาจารย์ผู้รับผิดชอบหลัก |
| instructors_json | TEXT | JSON array รายชื่ออาจารย์ทั้งหมด |
| objectives | TEXT | วัตถุประสงค์รายวิชา |
| source_file | TEXT | path ไฟล์ต้นฉบับ |
| UNIQUE | | (course_id, semester, year) |

---

### ตาราง `clos` — CLOs (Course Learning Outcomes)
| column | type | คำอธิบาย |
|--------|------|-----------|
| tqf3_id | INTEGER FK | → tqf3.id |
| clo_number | INTEGER | ลำดับ CLO |
| description | TEXT | |
| teaching_strategy | TEXT | วิธีสอน |
| assessment_method | TEXT | วิธีวัดผล |
| target_pct | REAL | ค่าเป้าหมาย % (default 50) |
| UNIQUE | | (tqf3_id, clo_number) |

---

### ตาราง `tqf5` — มคอ.5 (ผลการสอน)
| column | type | คำอธิบาย |
|--------|------|-----------|
| tqf3_id | INTEGER FK UNIQUE | → tqf3.id |
| registered_count | INTEGER | จำนวนนักศึกษาที่ลงทะเบียน |
| remaining_count | INTEGER | คงอยู่ |
| withdrawn_count | INTEGER | ถอน |
| grade_dist_json | TEXT | JSON {"A":4, "B+":3, ...} |
| clo_results_json | TEXT | JSON ผลการประเมิน CLOs |
| improvement_next | TEXT | แผนปรับปรุงรอบต่อไป |

---

### ตาราง `student_grades` — รายชื่อนักศึกษา
| column | type | คำอธิบาย |
|--------|------|-----------|
| tqf5_id | INTEGER FK | → tqf5.id |
| student_id | TEXT | รหัสนักศึกษา |
| student_name | TEXT | |
| section | TEXT | กลุ่มเรียน |
| total_score | REAL | คะแนนรวม |
| grade | TEXT | A/B+/B/C+/C/D+/D/E/W/I/P/U |
| UNIQUE | | (tqf5_id, student_id) |

---

### ตาราง `teaching_plan` — แผนการสอนรายสัปดาห์
| column | คำอธิบาย |
|--------|-----------|
| tqf3_id FK | |
| week | สัปดาห์ที่ |
| topic | หัวข้อ |
| hours_planned | ชั่วโมงตามแผน |

### ตาราง `assessments` — แผนการประเมิน
| column | คำอธิบาย |
|--------|-----------|
| tqf3_id FK | |
| name | ชื่อการประเมิน (สอบกลางภาค ฯลฯ) |
| weight_pct | น้ำหนัก % |
| clo_mapping | JSON list of CLO numbers |

### ตาราง `teaching_actual` — ชั่วโมงสอนจริง
| column | คำอธิบาย |
|--------|-----------|
| tqf5_id FK | |
| hours_planned / hours_actual | แผน vs จริง |
| deviation_reason | เหตุผลที่เบี่ยงเบน |

---

## ความสัมพันธ์ตาราง (ERD แบบย่อ)

```
curricula
   └── courses (curriculum_id)
         └── tqf3 (course_id)
               ├── clos (tqf3_id)
               ├── teaching_plan (tqf3_id)
               ├── assessments (tqf3_id)
               └── tqf5 (tqf3_id)
                     ├── student_grades (tqf5_id)
                     └── teaching_actual (tqf5_id)
```

---

## ไฟล์หลักแต่ละตัว

### `database.py`
DB layer รวมศูนย์ ทุกไฟล์ `import database as db`

**Functions สำคัญ:**
```python
db.init_db()                          # สร้าง schema
db.upsert_curriculum(version, ...)    # เพิ่ม/อัปเดตหลักสูตร
db.upsert_course(code, name_th, ..., curriculum_id)  # เพิ่ม/อัปเดตวิชา
db.upsert_tqf3(course_id, semester, year, ...)       # เพิ่ม/อัปเดต มคอ.3
db.replace_clos(tqf3_id, clos_list)   # บันทึก CLOs (ลบเก่า→เพิ่มใหม่)
db.get_or_create_tqf5(tqf3_id)       # สร้าง มคอ.5 record
db.replace_student_grades(tqf5_id, grades_list)      # บันทึกเกรดทั้งหมด
db.compute_grade_stats(tqf5_id)       # คำนวณสถิติการกระจายเกรด
db.get_dashboard_summary()            # ข้อมูลภาพรวมสำหรับ GUI
db.export_to_excel(output_path)       # export → .xlsx (4 sheets)
```

---

### `import_tqf3.py`
Parse ไฟล์มคอ.3 (.docx) แล้ว insert เข้า DB

**ขั้นตอน:**
1. `ensure_docx()` — แปลง .doc/.rtf → .docx ผ่าน LibreOffice (ถ้าจำเป็น)
2. อ่าน sections จาก heading ของ Word document
3. ดึงข้อมูล: ชื่อวิชา, รหัส, ภาค/ปี, CLOs (ส่วนที่ 4), อาจารย์ (ส่วนที่ 9.2)
4. เรียก `db.upsert_course()` + `db.upsert_tqf3()` + `db.replace_clos()`

**รูปแบบชื่อไฟล์ที่รองรับ:**
- `tqf3 calculus1.docx`, `tqf3 complex 60.docx`, ฯลฯ

---

### `import_grades.py`
Parse ไฟล์เกรด (.doc/.rtf/.docx) แล้ว insert เข้า DB

**ขั้นตอน:**
1. `extract_course_info_from_file()` — อ่าน header หารหัสวิชา + ภาค/ปี ด้วย regex
   - รหัสวิชา: pattern `[A-Z]{2,6}\d{3,6}` เช่น SMAC001, SMA0901
   - ภาค/ปี: pattern `\d/\d{4}` เช่น 1/2567
2. `parse_rtf_tables()` — parse ตารางจาก .doc/.rtf แบบ native (ไม่ต้อง LibreOffice)
   - split ด้วย `\cell` และ `\row` markers
   - decode hex escape `\'XX` เป็น cp874 (Thai encoding)
3. `parse_grade_docx()` — อ่านตารางเกรด หา student_id, ชื่อ, คะแนน, เกรด
4. ถ้าไม่พบวิชาใน DB → สร้าง empty course + tqf3 record อัตโนมัติ
5. เรียก `db.replace_student_grades()` + `db.update_tqf5()`

**รูปแบบตารางเกรดที่รองรับ:**
- คอลัมน์: ลำดับ | รหัสนักศึกษา | ชื่อ-สกุล | [คะแนนต่างๆ] | เกรด

---

### `input_gui.py`
GUI หลักด้วย tkinter

**โครงสร้าง:**
```
TQFApp (tk.Tk)
├── Header bar (ชื่อระบบ + ปุ่ม Export Excel)
├── Tab 1: "รายวิชาในระบบ"
│    └── Treeview ตารางวิชา (code, ชื่อ, ภาค/ปี, มคอ.3, เกรด, นักศึกษา, สถานะ)
│         color tags: complete=เขียว, partial=เหลือง, gradeonly=ส้ม
└── Tab 2: "นำเข้าข้อมูล"
     ├── Card: นำเข้า มคอ.3 (รับ .docx)
     ├── Card: นำเข้าเกรด (รับ .doc/.rtf/.docx)
     └── Log box (dark bg, แสดง output)
```

**GradeInfoDialog:** dialog ยืนยัน/แก้ไข course_code + semester/year
- ✅ = ตรวจพบอัตโนมัติ, ⚠️ = ตรวจไม่พบ (ให้กรอกเอง)

---

### `generate_tqf5.py`
สร้างไฟล์มคอ.5 .docx จาก template

**ฟังก์ชัน:**
```python
generate_tqf5(tqf3_id, output_path)
```
- อ่านข้อมูล tqf3 + tqf5 + student_grades จาก DB
- เติมข้อมูลลง template Word (`แบบฟอร์ม มคอ. 5.docx`)
- ส่งออกเป็นไฟล์ใหม่

---

## วิธีใช้งาน

### เปิด GUI (แนะนำ)
```
ดับเบิลคลิก: นำเข้าข้อมูล.bat
```

### Export Excel
```
ดับเบิลคลิก: export_excel.bat
→ สร้าง tqf_database_view.xlsx (4 sheets)
   - ภาพรวมรายวิชา
   - CLOs
   - การกระจายเกรด
   - รายชื่อนักศึกษา
```

### เปิด Streamlit web app
```
ดับเบิลคลิก: start.bat
→ เปิด browser ที่ http://localhost:8501
```

### ติดตั้ง dependencies (ครั้งแรก)
```bash
pip install python-docx openpyxl streamlit pandas plotly
```

---

## ข้อมูลหลักสูตรในระบบ

### หลักสูตร 65 (curriculum_id=2) — 26 วิชา
| กลุ่ม | วิชา |
|-------|------|
| วิชาแกน (7) | SPHC001, SCHC005, SBIC005, SMAC001, SMAC002, SMAC006, SMA2102 |
| วิชาบังคับ (16) | SMA1003, SMA1004, SMA2101, SMA2201, SMA2202, SMA2301, SMA2302, SMA2303, SMA3004, SMA3005, SMA3007, SMA4001, SMA6001, SMA6002, SMA7001 + SMA0901 |
| สหกิจศึกษา (3) | SMA5001, SMA5002, SMA5003 |

### หลักสูตร 69 (curriculum_id=1) — 40 วิชา
| กลุ่ม | วิชา |
|-------|------|
| วิชาแกน (7) | SCI0001, SCI0002, SCI0003, SMA0001, SMA0002, SMA0003, SMA0004 |
| วิชาบังคับ (14) | ... |
| วิชาเลือก (16) | ... |
| สหกิจศึกษา (3) | ... |

---

## Known Issues / TODO

- [ ] วิชาเลือกของหลักสูตร 65 ยังไม่ได้ import (ผู้ใช้ยังไม่ได้ให้ข้อมูล)
- [ ] import_tqf3.py ใช้ LibreOffice สำหรับ .doc — ถ้าไม่มี LibreOffice จะ error (ต่างจาก import_grades.py ที่มี native RTF parser)

---

## แผนพัฒนา v2 (ROADMAP_v2.md)

ดูรายละเอียดทั้งหมดใน `ROADMAP_v2.md` — สรุปย่อ:

### F1: Course Catalog Tab
- เพิ่ม Tab 3 "หลักสูตร & รายวิชา" ใน GUI
- แสดงรายวิชาทั้งหมดของหลักสูตร พร้อมรายละเอียดเต็ม
- รองรับ add/edit/delete วิชาจาก GUI

### F2: เพิ่มวิชาโดยไม่ต้องใช้มคอ.3
- `CourseAddDialog` — form กรอกข้อมูลวิชาใหม่
- `import_courses_excel.py` — bulk import จาก Excel template
- เพิ่มตาราง **`course_clos`** — CLO มาตรฐานระดับวิชา (แยกจาก CLO ใน tqf3 แต่ละปี)

### F3: สร้างมคอ.3 จาก DB (เลือกปีได้)
- `generate_tqf3.py` — สร้างไฟล์ Word มคอ.3 จาก template
- `TQF3GenerateDialog` — เลือกวิชา/ปี/ภาค/อาจารย์ แล้ว pre-fill CLO จาก DB
- **รอ template มคอ.3 แบบละเอียด** ก่อนพัฒนา (อาจต้องเพิ่ม schema: textbooks, plo_definitions, graduate_attributes)

### Schema ที่จะเพิ่ม (ยืนยันบางส่วน รอ template)
| ตาราง | สถานะ |
|-------|--------|
| `course_clos` | ✅ ยืนยันแล้ว — จำเป็นสำหรับ F2+F3 |
| `textbooks` | ⏳ รอดู template หมวด 6 |
| `plo_definitions` | ⏳ รอดู template หมวด 4 |
| `graduate_attributes` | ⏳ รอดู template หมวด 4 |

---

## Notes สำคัญ

- **DB path**: `database.py` ใช้ `os.path.dirname(__file__)` → DB อยู่ข้างๆ script เสมอ
- **UNIQUE constraint**: `courses` ใช้ `UNIQUE(code, curriculum_id)` → วิชาเดียวกันอยู่ได้หลายหลักสูตร
- **JSON fields**: `instructors_json`, `grade_dist_json`, `clo_results_json` เก็บเป็น TEXT ต้อง `json.loads()` ก่อนใช้
- **Encoding**: ไฟล์เกรด .doc/.rtf ไทยใช้ cp874 → `parse_rtf_tables()` decode ด้วย cp874 ก่อน
