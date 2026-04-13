# Codex Context — TQF System
> Paste this file into Codex System Prompt before starting work.
> Or tell Codex: "Read CODEX_CONTEXT.md, HANDOFF.md, PROJECT_REFERENCE.md before starting."

---

## What is this project?

TQF (มคอ.) management system for the Mathematics Department, Suratthani Rajabhat University.
Written in Python (tkinter GUI + SQLite), runs on Windows.

**Stack:** Python 3, tkinter, sqlite3, python-docx, pdfplumber, openpyxl

---

## File Structure

```
tqf_system/
├── database.py          ← DB layer: schema + all CRUD helpers
├── import_tqf3.py       ← Parse TQF3 .docx/.pdf → DB
├── import_grades.py     ← Parse grade files .doc/.rtf/.docx/.pdf → DB
├── input_gui.py         ← Main GUI (tkinter) — open via นำเข้าข้อมูล.bat
├── generate_tqf3.py     ← Generate TQF3 .docx by filling Word template
├── generate_tqf5.py     ← Generate TQF5 .docx from DB data
├── app.py               ← Streamlit web app (alternative)
├── tqf_database.db      ← SQLite DB (never commit to git)
├── templates/
│   ├── แบบฟอร์ม มคอ. 3.docx   ← TQF3 Word template (fill in place, don't recreate)
│   └── แบบฟอร์ม มคอ. 5.docx   ← TQF5 Word template
├── HANDOFF.md           ← *** Read before every session ***
├── PROJECT_REFERENCE.md ← Full DB schema + function list
├── ROADMAP_v2.md        ← v2 development plan
└── RULES.md             ← AI rules (read this!)
```

---

## Critical Rules (Codex MUST follow)

### 1. Always read first
- `HANDOFF.md` — current status, blocked tasks, what's next
- `PROJECT_REFERENCE.md` — DB schema and function signatures
- `RULES.md` — all rules

### 2. DB Rules
- **Never** use `ALTER TABLE RENAME TO` — write migrations using `ALTER TABLE xxx ADD COLUMN yyy` inside `init_db()`
- Test SQLite using paths without spaces (copy to `/tmp/` if needed)
- **Never** use `cp` to replace the DB file on the Linux mount — use `conn.backup()` API or run replacement on Windows
- If a `.db-journal` file exists on the mount, it blocks all writes — remove on Windows side only

### 3. Coding Rules  `[low token used]`
- All DB operations inside GUI must run in `threading.Thread` (don't block UI)
- Call `db.init_db()` before any DB operation
- Don't commit .db, `__pycache__`, `*.xlsx` to git
- **All MD files must be written in English** to reduce LLM token usage
- **Keep responses concise** — show code directly, skip verbose narration, no restating of context already in HANDOFF.md

### 4. generate_tqf3.py — how it works
- Opens `templates/แบบฟอร์ม มคอ. 3.docx` and fills in data — does **not** create a new document
- `_replace_block_between(doc, intro_pred, end_pred, lines)` — removes paragraphs in range then inserts new ones
- Uses `addnext` (not `addprevious`) to insert paragraphs — `addprevious` has XML ordering bugs in python-docx
- `_is_valid_instructor_name(name)` — filters garbage entries from `instructors_json` (e.g., appendix headings mistakenly imported)
- After editing via Write/Edit tool on Windows, always `touch generate_tqf3.py` in bash to invalidate `.pyc` cache

### 5. Update when done
- Update `HANDOFF.md` after every session
- If schema changed, also update `PROJECT_REFERENCE.md`
- If git is part of the task, use this command order:
  - `git status --short --branch`
  - `git diff`
  - `git add -- <intended files>`
  - `git commit -m "type: summary"`
  - `git push origin main`
- Prefer targeted staging over `git add -A` when the worktree is already dirty
- After push, check `git status --short --branch` again and note any leftover changes in `HANDOFF.md`

---

## Schema Summary (abbreviated)

```
curricula(id, version, name_th, effective_year)
    └── courses(id, curriculum_id, code, name_th, credits_text, course_type, ...)
            ├── plos(curriculum_id, plo_number, plo_code, category, description, pass_threshold_pct)
            ├── course_clos(course_id, clo_number, description, plo_mapping, pass_threshold_pct, ...)
            ├── course_assessments(course_id, name, full_score, weight_pct, clo_mapping, ...)
            ├── course_teaching_plan(course_id, week, week_label, topic, ...)
            ├── course_resources(course_id, resource_type, citation_text, url, note)
            └── tqf3(id, course_id, semester, year, is_special, source_type, ...)
                    ├── clos(tqf3_id, clo_number, description, plo_mapping, ...)
                    ├── teaching_plan(tqf3_id, week, topic, ...)
                    ├── assessments(tqf3_id, name, weight_pct, clo_mapping, ...)
                    ├── tqf3_staff(tqf3_id, role, seq, name)
                    └── tqf5(tqf3_id UNIQUE)
                            ├── student_grades(tqf5_id, student_id, grade, ...)
                            └── teaching_actual(tqf5_id, ...)
```

Key UNIQUE constraints:
- `courses`: `UNIQUE(code, curriculum_id)`
- `tqf3`: `UNIQUE(course_id, semester, year, is_special)`
- `clos`: `UNIQUE(tqf3_id, clo_number)`

---

## How to Run / Test

```bash
# Open GUI
cd tqf_system
python input_gui.py

# Syntax check
python -c "import ast; ast.parse(open('generate_tqf3.py').read()); print('OK')"

# Test DB (path has spaces — copy first)
cp tqf_database.db /tmp/test.db
python -c "import sqlite3; conn=sqlite3.connect('/tmp/test.db'); print(conn.execute('SELECT COUNT(*) FROM tqf3').fetchone())"

# Generate TQF3 document
python -c "from generate_tqf3 import generate_tqf3_docx; print(generate_tqf3_docx(tqf3_id=2))"

# After editing generate_tqf3.py — invalidate .pyc cache:
touch generate_tqf3.py
```

---

## Notes for Codex

- **Language**: Code in English; some comments/variable names in Thai; user communicates in Thai
- **Windows paths**: use `\` separator; Thai `.doc` grade files use cp874 encoding
- **is_special**: 0 = regular section (N0x), 1 = special section (P0x)
- **Curricula**: 65 (curriculum_id=2) and 69 (curriculum_id=1)
- **tqf3_staff roles**: `"committee"` = course management committee, `"instructor"` = teaching instructor
- **instructors_json**: may contain garbage if imported from poorly-structured Word docs; always filter via `_is_valid_instructor_name()`
- **TQF_system/ folder**: `tqf_database_fixed.db` = clean DB; `restore_database.py` = Windows script to fix broken DB+journal
