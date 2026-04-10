# ROADMAP v2 — TQF System Architecture Redesign
อัพเดท: 2026-04-10

---

## แนวคิดหลัก (3-Layer Architecture)

ระบบแบ่งเป็น 3 ชั้น ชัดเจน:

```
Layer 1: CURRICULUM (หลักสูตร)
   └── มี PLOs (Program Learning Outcomes) ของหลักสูตร

Layer 2: COURSE CATALOG (ฐานข้อมูลรายวิชา — "template")
   └── วิชาแต่ละวิชา มี CLOs มาตรฐาน, การประเมิน, โยง PLO
       → ข้อมูลนี้คงอยู่ข้ามปี/เทอม เปลี่ยนเมื่อปรับปรุงหลักสูตร

Layer 3: COURSE OFFERING (การเปิดสอนแต่ละปี/เทอม)
   └── มคอ.3  ← สร้างจาก template หรือ import ใหม่
   └── เกรด   ← import แบบเดิม
   └── มคอ.5  ← generate จาก มคอ.3 + เกรด
```

---

## Schema ใหม่ที่ต้องเพิ่ม

### ตารางที่มีอยู่แล้ว (คงไว้/แก้เล็กน้อย)

| ตาราง | สถานะ | หมายเหตุ |
|-------|--------|----------|
| `curricula` | ✅ ใช้ได้ | เพิ่มแค่ column เล็กน้อยถ้าจำเป็น |
| `courses` | ✅ ใช้ได้ | โครงสร้างครบแล้ว |
| `tqf3` | ✅ ใช้ได้ | เพิ่ม `source_type` ('imported' / 'generated') |
| `clos` | ✅ ใช้ได้ | ยังผูกกับ tqf3 เหมือนเดิม — คือ CLO "จริง" ของแต่ละเทอม |
| `teaching_plan` | ✅ ใช้ได้ | คงไว้ |
| `assessments` | ✅ ใช้ได้ | คงไว้ + เพิ่ม column |
| `tqf5` | ✅ ใช้ได้ | คงไว้ |
| `student_grades` | ✅ ใช้ได้ | คงไว้ |

---

### ตารางใหม่ที่ต้องสร้าง

#### 1. `plos` — PLO ของแต่ละหลักสูตร

```sql
CREATE TABLE IF NOT EXISTS plos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_id   INTEGER NOT NULL REFERENCES curricula(id) ON DELETE CASCADE,
    plo_number      INTEGER NOT NULL,
    category        TEXT    DEFAULT '',   -- ด้านความรู้ / ด้านทักษะทางปัญญา /
                                          -- ด้านทักษะความสัมพันธ์ / ด้านการวิเคราะห์ตัวเลข
    description     TEXT    NOT NULL,
    UNIQUE(curriculum_id, plo_number)
);
```

#### 2. `course_clos` — CLO มาตรฐานของวิชา (template)

```sql
CREATE TABLE IF NOT EXISTS course_clos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    clo_number          INTEGER NOT NULL,
    description         TEXT    NOT NULL,
    domain              TEXT    DEFAULT '',   -- ด้านความรู้ / ทักษะ / จริยธรรม ฯลฯ
    teaching_strategy   TEXT    DEFAULT '',   -- วิธีการสอน (บรรยาย, สัมมนา, ปฏิบัติ)
    assessment_method   TEXT    DEFAULT '',   -- วิธีวัด (สอบ, รายงาน, สังเกต)
    pass_threshold_pct  REAL    DEFAULT 50.0, -- เกณฑ์ผ่าน % (ผ่านต้องได้กี่ %)
    plo_mapping         TEXT    DEFAULT '[]', -- JSON: [1, 3, 4] → PLO number ที่สอดคล้อง
    UNIQUE(course_id, clo_number)
);
```

#### 3. `course_assessments` — แผนการประเมินมาตรฐานของวิชา (template)

```sql
CREATE TABLE IF NOT EXISTS course_assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,         -- สอบกลางภาค / สอบปลายภาค / งาน / ฯลฯ
    full_score      REAL    DEFAULT 100,      -- คะแนนเต็มของรายการนี้
    weight_pct      REAL    NOT NULL DEFAULT 0, -- น้ำหนัก % รวมทุกรายการต้องได้ 100
    clo_mapping     TEXT    DEFAULT '[]',     -- JSON: [clo_number, ...] CLO ที่วัดผ่านนี้
    eval_criteria   TEXT    DEFAULT '',       -- เกณฑ์การให้คะแนน/รายละเอียดกิจกรรม
    pass_threshold  REAL    DEFAULT 50.0      -- เกณฑ์ผ่านของรายการนี้ %
);
```

---

## ความสัมพันธ์ตาราง (ERD ฉบับใหม่)

```
curricula
│   └── plos (curriculum_id)          ← ใหม่
│
└── courses (curriculum_id)
    │
    ├── course_clos (course_id)        ← ใหม่: CLO มาตรฐาน + โยง PLO
    │       plo_mapping → plos
    │
    ├── course_assessments (course_id) ← ใหม่: แผนประเมินมาตรฐาน
    │       clo_mapping → course_clos
    │
    └── tqf3 (course_id)              ← "การเปิดสอน" แต่ละปี/เทอม
         │    source_type: 'generated' | 'imported'
         │
         ├── clos (tqf3_id)           ← CLO จริงของเทอมนี้ (copy จาก course_clos หรือ import ใหม่)
         │       plo_mapping → JSON
         │
         ├── assessments (tqf3_id)    ← การประเมินจริงของเทอมนี้
         ├── teaching_plan (tqf3_id)
         │
         └── tqf5 (tqf3_id)
               ├── student_grades (tqf5_id)
               └── teaching_actual (tqf5_id)
```

---

## Workflow การทำงานใหม่

### Workflow A: เพิ่มวิชาใหม่ในหลักสูตร
```
1. เลือกหลักสูตร (curricula)
2. กรอกข้อมูลวิชา (courses)
3. กรอก CLO มาตรฐาน (course_clos) + โยง PLO
4. กรอกแผนการประเมิน (course_assessments)
→ วิชาพร้อมสำหรับเปิดสอนได้ทุกปี
```

### Workflow B: เปิดสอนวิชา (แต่ละปี/เทอม)
```
เลือกวิชาจาก Catalog
    ↓
[ตัวเลือก] เลือกวิธีสร้าง มคอ.3:
   Option 1: "สร้างจาก template" → copy course_clos → clos, เปลี่ยนแค่ ปี/เทอม
   Option 2: "Import ไฟล์ มคอ.3" → parse docx/pdf แบบเดิม (override clos)
    ↓
import เกรด (แบบเดิม)
    ↓
สร้าง มคอ.5 (generate จาก มคอ.3 + เกรด)
```

### Workflow C: ดูผล PLO Achievement (อนาคต)
```
เลือกหลักสูตร + ปีการศึกษา
→ รวม clo_results ของทุกวิชา + plo_mapping
→ แสดง % นักศึกษาที่ผ่านแต่ละ PLO
```

---

## การเปลี่ยนแปลงที่ต้องทำในโค้ด

### database.py
- เพิ่ม 3 ตาราง: `plos`, `course_clos`, `course_assessments`
- เพิ่ม column ใน `tqf3`: `source_type TEXT DEFAULT 'imported'`
- เพิ่ม migration สำหรับ DB เก่า
- เพิ่ม CRUD functions: `upsert_plo()`, `upsert_course_clo()`, `get_course_clos()`, `copy_course_clos_to_tqf3()`, `get_plos()`

### import_tqf3.py
- หลัง import สำเร็จ: sync CLO ที่ parse ได้ → `course_clos` ด้วย (ถ้ายังไม่มี)
- บันทึก `plo_mapping` ถ้า parse ได้จากไฟล์

### input_gui.py — Tab ใหม่และ Dialog ใหม่

| Component | คำอธิบาย |
|-----------|----------|
| **Tab 3: หลักสูตร & รายวิชา** | ซ้าย=dropdown หลักสูตร + ตารางวิชา, ขวา=รายละเอียดวิชา + CLO มาตรฐาน |
| **CourseAddDialog** | form เพิ่มวิชาใหม่ (code, ชื่อ, หน่วยกิต, ประเภท, คำอธิบาย, prerequisite) |
| **CourseCLOEditor** | กรอก/แก้ไข CLO มาตรฐาน + PLO mapping + เกณฑ์ผ่าน (embedded table หรือ popup) |
| **TQF3GenerateDialog** | เลือกปี/เทอม/อาจารย์ + เลือก mode (จาก template / import ใหม่) |
| **PLOManagerDialog** | จัดการ PLO ของแต่ละหลักสูตร (add/edit/delete) |

### generate_tqf3.py (ไฟล์ใหม่)
- `generate_tqf3_docx(course_id, semester, year, output_path)`
- อ่านข้อมูลจาก `courses`, `course_clos`, `course_assessments`, `plos`
- เติมลง template Word ที่ผู้ใช้ให้

### import_courses_excel.py (ไฟล์ใหม่)
- อ่าน Excel template → bulk insert `courses` + `course_clos`

---

## จุดที่น่าระวัง / ข้อแนะนำ

### ✅ สิ่งที่ออกแบบได้ดี

1. **แยก Layer ชัดเจน** — course template vs tqf3 offering ทำให้ไม่ต้องกรอก CLO ซ้ำทุกปี
2. **backward compatible** — ตาราง `clos` ยังผูกกับ `tqf3` เหมือนเดิม ไม่ต้อง migrate data เก่า
3. **PLO tracking** — เมื่อมีข้อมูล `plo_mapping` ใน clos + ผล `clo_results` ใน tqf5 สามารถคำนวณ PLO achievement ได้ในอนาคต

### ⚠️ จุดที่ต้องระวัง

**1. CLO "ล็อค" เมื่อสร้าง มคอ.3**
เมื่อ generate มคอ.3 จาก template ระบบ copy `course_clos` → `clos` (ผูกกับ tqf3)
หากภายหลังอัพเดท `course_clos` ตาราง clos ของ tqf3 เก่า**ไม่เปลี่ยน** (เพราะเป็น snapshot)
→ แนะนำ: แสดง warning ใน GUI ถ้า course_clos ถูกแก้ไขหลัง tqf3 สร้างไปแล้ว

**2. PLO mapping เก็บเป็น JSON**
`plo_mapping TEXT DEFAULT '[]'` → ใช้ JSON เพราะ mapping เป็น many-to-many แบบง่าย
ข้อดี: ง่าย ข้อเสีย: query เพื่อ filter "วิชาที่ตอบสนอง PLO X" ต้องใช้ Python ไม่ใช่ SQL
→ ยอมรับได้สำหรับขนาดข้อมูลนี้ (ไม่ใหญ่)

**3. `course_assessments.weight_pct` ต้องรวมกัน 100%**
ระบบควรตรวจสอบว่าผลรวม weight_pct ของทุกรายการในวิชาเดียวกัน = 100
→ ต้องมี validation ใน GUI และ/หรือ database layer

**4. เมื่อ import มคอ.3 → sync course_clos?**
ถ้า import TQF3 ไฟล์ใหม่แล้ว CLO เปลี่ยนจาก course_clos เดิม — ควรทำอย่างไร?
→ แนะนำ: **ถามผู้ใช้** ว่าจะ "อัพเดท CLO มาตรฐาน" ด้วยหรือไม่
   เพราะบางทีเปลี่ยนเฉพาะปีนั้น ไม่ได้เปลี่ยน template จริงๆ

**5. `course_assessments` vs `assessments` (tqf3)**
มี 2 ระดับ: template (course) และ จริง (tqf3)
→ เมื่อ generate มคอ.3 ต้อง copy `course_assessments` → `assessments` เหมือนกัน
→ แต่ถ้า import มคอ.3 ใหม่ทับ ให้ใช้ assessments ที่ parse ได้จากไฟล์แทน

---

## ลำดับการพัฒนาที่แนะนำ

| ลำดับ | งาน | ขึ้นอยู่กับ |
|-------|-----|------------|
| 1 | เพิ่ม `plos`, `course_clos`, `course_assessments` ใน schema + migration | — |
| 2 | Tab 3 Course Catalog + PLO Manager + CourseAddDialog | schema ใหม่ |
| 3 | CourseCLOEditor (กรอก CLO + PLO mapping + เกณฑ์ผ่าน) | schema ใหม่ |
| 4 | Sync course_clos เมื่อ import มคอ.3 (opt-in) | Tab 3 |
| 5 | TQF3GenerateDialog + copy_course_clos_to_tqf3() | Course Catalog |
| 6 | generate_tqf3.py + template Word | **รอ template จากผู้ใช้** |
| 7 | import_courses_excel.py (bulk add) | schema ใหม่ |
| 8 | PLO Achievement report (ระยะยาว) | clo_results ใน tqf5 |

---

## สิ่งที่รอผู้ใช้

| รายการ | ใช้สำหรับ | บล็อกลำดับ |
|--------|-----------|------------|
| Template มคอ.3 (.docx) แบบละเอียด | ออกแบบ generate_tqf3.py, ยืนยัน fields ที่ต้องเก็บ | ลำดับ 6 |
| รายชื่อ PLO ของหลักสูตร 65 และ 69 | กรอกข้อมูล plos table | ลำดับ 1-2 |
| รายวิชาเลือก หลักสูตร 65 | ความครบถ้วนของ catalog | ลำดับ 2 |
