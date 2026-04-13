# generate_tqf3.py — Template Analysis & Fix Log
Date found: 2026-04-10
Last updated: 2026-04-12

---

## Tasks

- [x] Design/add `course_teaching_plan` or extend `teaching_plan` with detailed weekly plan fields: week range, LLO, topic, activities, media, assessment tools, hours — ✅ Done (2026-04-10): Added `course_teaching_plan` table with all required columns
- [x] Design/add `course_resources` for section 8 (textbooks, articles, websites, media) — ✅ Done (2026-04-10): Added `course_resources` table with `resource_type`, `citation_text`, `url`, `note`
- [x] Design/add `tqf3_staff` for section 9 (personnel roles: committee, instructor) — ✅ Done (2026-04-10): Added `tqf3_staff` table with `role`, `seq`, `name`
- [x] Extend `assessments` with `full_score`, `assessment_period`, `eval_criteria`, `pass_threshold` — ✅ Done (2026-04-10)
- [x] Implement `generate_tqf3.py` to fill the existing Word template instead of creating from scratch — ✅ Done (2026-04-11): Opens `แบบฟอร์ม มคอ. 3.docx`, fills tables and paragraphs in place
- [x] Fix CLO insertion — CLOs must appear between intro paragraph and "5.2 ผลการเรียนรู้..." — ✅ Done (2026-04-11): `_replace_block_between()` with correct anchor logic
- [x] Fix section 8 resources — must not delete section 9 and appendix — ✅ Done (2026-04-11): Scoped between "(เว็บไซต์...)" and "9. คณะกรรมการ..."
- [x] Fix section 9 (committee + instructors) — must replace correctly — ✅ Done (2026-04-11): Two `_replace_block_between()` calls for 9.1 and 9.2
- [x] Fix corrupt `instructors_json` for SMA7005 (tqf3_id=19) — appendix items mistakenly stored as instructor names — ✅ Done (2026-04-11): Cleaned data, added `_is_valid_instructor_name()` filter
- [x] Populate `tqf3_staff` for existing records (tqf3_id 1, 2, 3, 4, 19) — ✅ Done (2026-04-11)

---

## Reason / Context

The original `generate_tqf3.py` was building documents programmatically from scratch, which lost the original Word template formatting. The requirement was to open the existing template and fill in data from the DB.

Key technical discoveries during implementation:
- `doc.paragraphs` in python-docx returns **only body-level paragraphs** (not table cell paragraphs) — 69 body paragraphs in the template
- `addprevious()` on a target element is unreliable in Word XML — causes elements to appear in wrong positions
- `addnext()` from the intro paragraph (chained) works correctly
- Python `.pyc` bytecode cache: Python 3.10 loads `.pyc` if mtime matches source — if Edit/Write tool changes content but not mtime on the Linux mount, Python loads stale bytecode. Fix: `touch <file>.py`

---

## Related Files
- `generate_tqf3.py` — main file
- `database.py` — `get_tqf3_staff()`, `get_course_resources()`, `get_course_teaching_plan()`
- `templates/แบบฟอร์ม มคอ. 3.docx` — Word template (69 body paragraphs, 6 tables)
- `TQF_system/tqf_database_fixed.db` — fixed DB (tqf3_staff populated, corrupt data cleaned)
- `TQF_system/restore_database.py` — Windows script to replace broken DB+journal

---

## Completed

- Added `course_teaching_plan`, `course_resources`, `tqf3_staff` tables to `database.py`
- Extended `assessments`/`course_assessments` with additional fields
- Rewrote `generate_tqf3.py` to use template-fill approach
- Implemented `_replace_block_between()` using `addnext` chain strategy
- Added `_is_valid_instructor_name()` to filter garbage from `instructors_json`
- Fixed corrupt data in tqf3_id=19 and populated `tqf3_staff` for records 1, 2, 3, 4, 19
- Verified output for SMAC001 (tqf3_id=2) and SMA7005 (tqf3_id=19) — structure correct

---

## Remaining / Future

- [ ] `hours_theory`/`hours_practice`/`hours_self` in teaching_plan not yet populated for most records → Table 3 (hours summary) shows 0. Need data entry UI or import logic.
- [ ] PLO mapping for curricula 65 and 69 not yet entered → Table 1 (PLO/CLO mapping) shows "ไม่ระบุ". Need PLO data from user.
- [ ] Semester offering manager not yet implemented; TQF3 creation is still ad hoc from the course catalog
- [ ] Dynamic section choices should come from declared offerings instead of the fixed `N01-N09` / `P01-P09` list
