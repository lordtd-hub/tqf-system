# TQF System — Project Reference
Mathematics Department TQF Database System, Suratthani Rajabhat University

---

## File Structure

```
tqf_system/
├── database.py            ← DB layer: schema + all CRUD helpers
├── import_tqf3.py         ← Parser: TQF3 (.docx) → DB
├── import_grades.py       ← Parser: grade files (.doc/.rtf/.docx) → DB
├── input_gui.py           ← Main GUI (tkinter)
├── app.py                 ← Streamlit web app (alternative)
├── generate_tqf3.py       ← Generate TQF3 .docx from DB
├── generate_tqf5.py       ← Generate TQF5 .docx from DB
├── tqf_database.db        ← SQLite database (main)
├── tqf_database_view.xlsx ← Latest Excel export
├── requirements.txt       ← Python dependencies
├── นำเข้าข้อมูล.bat       ← Double-click to open GUI
├── export_excel.bat        ← Double-click to export Excel
└── start.bat              ← Open Streamlit app (port 8501)
```

---

## Schema Update Log

### 2026-04-10
- Added `course_teaching_plan` — weekly teaching plan template per course
- Added `course_resources` — section 8 textbooks/articles/web resources per course
- Added `tqf3_staff` — personnel and roles for section 9 per TQF3 record
- Extended `teaching_plan`: added `week_label`, `llo_text`, `activities`, `media`, `assessment_tools`, `hours_theory`, `hours_practice`, `hours_self`
- Extended `assessments` and `course_assessments`: added `full_score`, `assessment_period`, `eval_criteria`, `pass_threshold`
- Updated `copy_course_template_to_tqf3()` to copy `course_clos`, `course_teaching_plan`, and detailed `course_assessments` into the tqf3 snapshot
- Added `source_type` to `tqf3` to distinguish imported vs generated records

### 2026-04-11
- Fixed `instructors_json` corruption in tqf3 id=19 (SMA7005) — appendix headings were mistakenly stored as instructor names
- Populated `tqf3_staff` for tqf3_id 1, 2, 3, 4, 19 from existing `instructors_json`/`instructor_main`
- `generate_tqf3.py`: switched to template-fill approach (opens `แบบฟอร์ม มคอ. 3.docx`, fills in place)

### 2026-04-13
- Standardized the new Tab 2 offering manager UI text to Thai
- Fixed the Tab 2 opening-history display path to render Thai offering labels cleanly instead of the garbled `เธ...` fallback

---

## Database Schema

### `curricula` — Curricula
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| version | TEXT UNIQUE | "65", "69" |
| name_th | TEXT | Thai curriculum name |
| effective_year | INTEGER | Year adopted (2565, 2569) |

Current data: id=1 (curriculum 69), id=2 (curriculum 65)

---

### `courses` — Courses
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| curriculum_id | INTEGER FK | → curricula.id |
| code | TEXT | Course code e.g. SMAC001 |
| name_th / name_en | TEXT | Course name |
| credits_text | TEXT | e.g. "3(3-0-6)" |
| credit_lecture/lab/self | INTEGER | Credit components |
| course_type | TEXT | Core / Required / Elective / Co-op |
| description_th / description_en | TEXT | Course description |
| faculty | TEXT | Faculty name |
| department | TEXT | Department name |
| UNIQUE | | (code, curriculum_id) |

**Current data:**
- Curriculum 65 (curriculum_id=2): 26 courses (7 core + 16 required + 3 co-op)
- Curriculum 69 (curriculum_id=1): 40 courses (7 core + 14 required + 16 elective + 3 co-op)

### `course_offerings` โ€” Real Course Offerings
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| course_id | INTEGER FK | -> courses.id |
| curriculum_id | INTEGER FK | -> curricula.id |
| offering_id | INTEGER FK | -> course_offerings.id |
| semester | INTEGER | 1 or 2 |
| year | INTEGER | Academic year e.g. 2569 |
| section_code | TEXT | Section code such as `N01` or `P01` |
| is_special | INTEGER | 0=regular, 1=special |
| status | TEXT | `active`, `planned`, or later workflow states |
| source_type | TEXT | `catalog`, `generated`, `imported` |
| UNIQUE | | (course_id, semester, year, section_code) |

Purpose:
- Source of truth for real openings
- Basis for the future Tab 2 `Term Offerings` UI
- Used to compute `times offered`

---

### `plos` — Program Learning Outcomes
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| curriculum_id | INTEGER FK | → curricula.id |
| plo_number | TEXT | e.g. "1", "2" |
| plo_code | TEXT | e.g. "PLO1" |
| category | TEXT | Knowledge / Skill / Ethics / Personal |
| description | TEXT | |
| pass_threshold_pct | REAL | Default 50.0 |

---

### `tqf3` — TQF3 Records (per semester/year)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| course_id | INTEGER FK | → courses.id |
| semester | INTEGER | 1 or 2 |
| year | INTEGER | Academic year e.g. 2568 |
| instructor_main | TEXT | Primary responsible instructor |
| instructors_json | TEXT | JSON array of all instructors (may contain garbage — always filter) |
| objectives | TEXT | Course objectives |
| source_file | TEXT | Path to source file |
| source_type | TEXT | `imported` or `generated` |
| is_special | INTEGER | 0=regular (N0x), 1=special section (P0x) |
| UNIQUE | | (course_id, semester, year, is_special) |

---

### `tqf3_staff` — Personnel for TQF3 Section 9
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| tqf3_id | INTEGER FK | → tqf3.id |
| role | TEXT | `committee` or `instructor` |
| seq | INTEGER | Display order |
| name | TEXT | Person's name |

---

### `clos` — Course Learning Outcomes (TQF3 snapshot)
| Column | Type | Description |
|--------|------|-------------|
| tqf3_id | INTEGER FK | → tqf3.id |
| clo_number | INTEGER | CLO index |
| description | TEXT | |
| plo_mapping | TEXT | JSON array of PLO numbers/codes |
| teaching_strategy | TEXT | |
| assessment_method | TEXT | |
| pass_threshold_pct | REAL | Default 50.0 |
| UNIQUE | | (tqf3_id, clo_number) |

---

### `course_clos` — CLO Templates per Course
| Column | Type | Description |
|--------|------|-------------|
| course_id | INTEGER FK | → courses.id |
| clo_number | INTEGER | |
| description | TEXT | |
| plo_mapping | TEXT | JSON array |
| pass_threshold_pct | REAL | |
| teaching_strategy / assessment_method | TEXT | |

---

### `assessments` — Assessment Plans (TQF3 snapshot)
| Column | Description |
|--------|-------------|
| tqf3_id FK | |
| name | Assessment name (midterm, final, etc.) |
| full_score | Maximum score |
| weight_pct | Weight percentage |
| clo_mapping | JSON list of CLO numbers |
| assessment_period | Time period |
| eval_criteria | Criteria / rubric details |
| pass_threshold | Pass threshold % |

### `course_assessments` — Assessment Templates per Course
Same columns as `assessments` but with `course_id` instead of `tqf3_id`.

---

### `teaching_plan` — Weekly Teaching Plan (TQF3 snapshot)
| Column | Description |
|--------|-------------|
| tqf3_id FK | |
| week | Week number |
| week_label | Display label (e.g. "1-2") |
| llo_text | Lesson-level learning outcome |
| topic | Topic |
| activities | Learning activities |
| media | Teaching media/tools |
| assessment_tools | Assessment evidence/method |
| hours_planned | Planned hours |
| hours_theory / hours_practice / hours_self | Detailed hour breakdown |
| teaching_method | Teaching method |

### `course_teaching_plan` — Teaching Plan Template per Course
Same columns as `teaching_plan` but with `course_id` instead of `tqf3_id`.

---

### `course_resources` — Section 8 Resources per Course
| Column | Description |
|--------|-------------|
| id | INTEGER PK |
| course_id | INTEGER FK → courses.id |
| resource_type | `textbook` / `article` / `website` / `media` |
| citation_text | Full citation |
| url | URL (if applicable) |
| note | Additional note |

---

### `tqf5` — TQF5 Records (Teaching Results)
| Column | Type | Description |
|--------|------|-------------|
| tqf3_id | INTEGER FK UNIQUE | → tqf3.id |
| registered_count | INTEGER | |
| remaining_count | INTEGER | |
| withdrawn_count | INTEGER | |
| grade_dist_json | TEXT | JSON {"A":4, "B+":3, ...} |
| clo_results_json | TEXT | JSON CLO assessment results |
| improvement_next | TEXT | Improvement plan for next semester |

---

### `student_grades` — Student Grade Records
| Column | Type | Description |
|--------|------|-------------|
| tqf5_id | INTEGER FK | → tqf5.id |
| student_id | TEXT | |
| student_name | TEXT | |
| section | TEXT | Class section |
| total_score | REAL | |
| grade | TEXT | A/B+/B/C+/C/D+/D/E/W/I/P/U |
| UNIQUE | | (tqf5_id, student_id) |

---

## ERD (abbreviated)

```
curricula
   └── courses (curriculum_id)
         ├── plos (curriculum_id)
         ├── course_clos (course_id)
         ├── course_assessments (course_id)
         ├── course_teaching_plan (course_id)
         ├── course_resources (course_id)
         └── tqf3 (course_id)
               ├── clos (tqf3_id)
               ├── teaching_plan (tqf3_id)
               ├── assessments (tqf3_id)
               ├── tqf3_staff (tqf3_id)
               └── tqf5 (tqf3_id)
                     ├── student_grades (tqf5_id)
                     └── teaching_actual (tqf5_id)
```

---

## Key Files

### `database.py`
Central DB layer — all other files do `import database as db`.

**Key functions:**
```python
db.init_db()                          # Create/migrate schema
db.upsert_curriculum(version, ...)
db.upsert_course(code, name_th, ..., curriculum_id)
db.upsert_course_offering(course_id, semester, year, ...)
db.get_course_offerings(course_id=None, curriculum_id=None, semester=None, year=None)
db.upsert_tqf3(course_id, semester, year, ...)
db.replace_clos(tqf3_id, clos_list)
db.get_or_create_tqf5(tqf3_id)
db.replace_student_grades(tqf5_id, grades_list)
db.compute_grade_stats(tqf5_id)
db.get_dashboard_summary()
db.export_to_excel(output_path)

# v2 additions
db.get_plos(curriculum_id)
db.get_course_clos(course_id) / db.replace_course_clos(course_id, clos)
db.get_course_assessments(course_id) / db.replace_course_assessments(...)
db.get_course_teaching_plan(course_id) / db.replace_course_teaching_plan(...)
db.get_course_resources(course_id) / db.replace_course_resources(...)
db.get_tqf3_staff(tqf3_id) / db.replace_tqf3_staff(tqf3_id, staff_list)
db.copy_course_template_to_tqf3(course_id, tqf3_id)
```

---

### `generate_tqf3.py`
Generates TQF3 `.docx` by filling the Word template `templates/แบบฟอร์ม มคอ. 3.docx`.

**Key functions:**
```python
load_data_for_tqf3(course_id=None, semester=None, year=None, tqf3_id=None) -> dict
fill_tqf3(template_path, data, output_path) -> str
generate_tqf3_docx(course_id=None, semester=None, year=None, output_path=None, tqf3_id=None) -> str
```

**Helper functions:**
```python
_replace_block_between(doc, intro_predicate, end_predicate, lines)
    # Finds paragraph range by predicate, removes existing, inserts new lines via addnext
_find_paragraph_index(doc, predicate) -> int
_is_valid_instructor_name(name) -> bool
    # Returns False if name starts with appendix keywords (ภาคผนวก, แบบประเมิน, เกณฑ์การให้คะแนน, ...)
_build_objective_lines(clos, plo_lookup) -> list[str]
_build_plo_rows(plos, clos, assessments) -> list[tuple]
_hours_summary(course, teaching_plan) -> list[str]
```

**Data loading priority:**
1. `tqf3_staff` table → if empty, fall back to `instructors_json`/`instructor_main` from tqf3 row (filtered)
2. `clos` table for tqf3_id → if empty, fall back to `course_clos`
3. `assessments` table for tqf3_id → if empty, fall back to `course_assessments`
4. `teaching_plan` table for tqf3_id → if empty, fall back to `course_teaching_plan`
5. `course_resources` always loaded from course level

**Template structure (แบบฟอร์ม มคอ. 3.docx):**
- 69 body-level paragraphs, 6 tables
- Tables filled: Table0=header, Table1=PLO/CLO mapping, Table2=teaching plan, Table3=hours summary, Table4=assessments, Table5=grade scale
- Paragraph blocks replaced: CLOs (section 5.1), resources (section 8), staff (sections 9.1, 9.2)

---

### `import_tqf3.py`
Parses TQF3 `.docx` files and inserts into DB.

Steps:
1. `ensure_docx()` — convert `.doc`/`.rtf` → `.docx` via LibreOffice if needed
2. Read sections from Word document headings
3. Extract: course name, code, semester/year, CLOs (section 5), instructors (section 9.2)
4. Call `db.upsert_course()` + `db.upsert_tqf3()` + `db.replace_clos()`

---

### `import_grades.py`
Parses grade files `.doc`/`.rtf`/`.docx` and inserts into DB.

Steps:
1. `extract_course_info_from_file()` — regex-extract course code + semester/year from header
   - Course code pattern: `[A-Z]{2,6}\d{3,6}` e.g. SMAC001, SMA0901
   - Semester/year pattern: `\d/\d{4}` e.g. 1/2567
2. `parse_rtf_tables()` — native RTF table parser (no LibreOffice needed)
   - Splits on `\cell` and `\row` markers, decodes hex escapes `\'XX` as cp874 (Thai)
3. `parse_grade_docx()` — reads grade table, extracts student_id, name, score, grade
4. If course not found in DB → create empty course + tqf3 record automatically
5. Call `db.replace_student_grades()` + `db.update_tqf5()`

---

### `input_gui.py`
Main tkinter GUI.

**Structure:**
```
TQFApp (tk.Tk)
├── Header bar (system name + Export Excel button)
├── Tab 1: "รายวิชาในระบบ" (Courses in system)
│    └── Treeview: code, name, semester/year, TQF3, grades, students, status
│         color tags: complete=green, partial=yellow, gradeonly=orange
├── Tab 2: "ฐานข้อมูลหลักสูตร" (Curriculum database)
│    ├── Manage courses / PLOs / CLOs / Assessment templates / Teaching plan / Resources
│    └── Button "สร้าง มคอ.3" → opens TQF3GenerateDialog
└── Tab 3: "นำเข้าข้อมูล" (Import data)
     ├── Card: Import TQF3 (.docx)
     ├── Card: Import grades (.doc/.rtf/.docx)
     └── Log box (dark bg, shows output)
```

---

### `generate_tqf5.py`
Generates TQF5 `.docx` from template.

```python
generate_tqf5(tqf3_id, output_path)
```

Reads tqf3 + tqf5 + student_grades from DB and fills `แบบฟอร์ม มคอ. 5.docx`.

---

## How to Use

### Open GUI (recommended)
```
Double-click: นำเข้าข้อมูล.bat
```

### Export Excel
```
Double-click: export_excel.bat
→ Creates tqf_database_view.xlsx (4 sheets):
   - Course overview
   - CLOs
   - Grade distribution
   - Student list
```

### Open Streamlit web app
```
Double-click: start.bat
→ Opens browser at http://localhost:8501
```

### Install dependencies (first time)
```bash
pip install python-docx openpyxl streamlit pandas plotly
```

---

## Curriculum Data in System

### Curriculum 65 (curriculum_id=2) — 26 courses
| Group | Courses |
|-------|---------|
| Core (7) | SPHC001, SCHC005, SBIC005, SMAC001, SMAC002, SMAC006, SMA2102 |
| Required (16) | SMA1003, SMA1004, SMA2101, SMA2201, SMA2202, SMA2301, SMA2302, SMA2303, SMA3004, SMA3005, SMA3007, SMA4001, SMA6001, SMA6002, SMA7001, SMA0901 |
| Co-op (3) | SMA5001, SMA5002, SMA5003 |

### Curriculum 69 (curriculum_id=1) — 40 courses
| Group | Courses |
|-------|---------|
| Core (7) | SCI0001, SCI0002, SCI0003, SMA0001, SMA0002, SMA0003, SMA0004 |
| Required (14) | (see DB) |
| Elective (16) | (see DB) |
| Co-op (3) | (see DB) |

---

## Known Issues / TODO

## Agreed Next UI Refactor (2026-04-12)

This is the agreed direction for the next implementation step. It is partially implemented now: the DB layer has `course_offerings`, and Tab 2 now has an initial term/offering panel, but the full offering-first refactor is still pending.

- `Tab 1 = Curriculum Catalog`
- Holds long-lived master/template data: curricula, courses, PLOs, default CLOs, default assessment templates, default teaching plan, default resources
- `Tab 2 = Term Offerings`
- Holds courses actually opened in a selected semester/year, backed by `course_offerings`
- Term-specific actions should move to Tab 2: generate/open TQF3, edit TQF3 staff, section/special-section data, and later grades/TQF5
- `times offered` should be counted from offering records, not from ad-hoc TQF3 generation rows
- Tab 2 should support a "create offerings from catalog" flow: choose curriculum + semester + year, then select courses from the catalog to open for that term


- [ ] If the TQF3 Word template is modified in the future, re-verify paragraph indices and table cell mapping in `generate_tqf3.py`
- [ ] Elective courses for curriculum 65 not yet imported (user has not provided data)
- [ ] `import_tqf3.py` requires LibreOffice for `.doc` — `import_grades.py` has native RTF parser (no dependency)
- [ ] Semester offering manager UI is only partially implemented; Tab 2 has term filters + offering actions now, but the bulk "create offerings from catalog" flow is still missing
- [ ] Dynamic section picker from declared offerings not yet implemented (`N01-N09` / `P01-P09` still fixed-order choices)
- [ ] The next agreed refactor slice is to finish turning the current mixed Tab 2 into `Term Offerings`, backed by `course_offerings`

---

## Development Plan v2 (see ROADMAP_v2.md)
Current roadmap status:
- `F1` through `F5` are done
- `F6` (`course_offerings` DB foundation) is now done
- `F7` (Tab 2 offering manager UI) is partially landed and remains the active next step

### F1: Course Catalog Tab ✅ Done
### F2: Add courses without TQF3 ✅ Done
### F3: Generate TQF3 from DB ✅ Done (template-fill approach)
### F4: Teaching plan + resources editors — Done
### F5: TQF3 staff editor — Done
