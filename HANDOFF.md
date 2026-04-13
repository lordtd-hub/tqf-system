# HANDOFF — TQF System
> This file is the project "bulletin board".
> **Read before every session — update after every session.**
> Used by Cowork, Codex, and all tools as the source of truth.

---

## 🟢 Latest Status
Updated: 2026-04-13 (session 2)  |  Machine: PC  |  Tool: Codex

### Completed this session
- [x] Tab 2 offering UI cleanup: added live offering search (`code/name/section`) and zebra striping in the offering table
- [x] Moved offering-specific actions out of the crowded left list area into a right-side contextual action box
- [x] Added selected-offering summary text in the action box and kept all offering actions disabled until a row is selected
- [x] Promoted `เปิดสอนวิชาที่เลือก` into the top term-control row so the primary add-offering action is easier to reach
- [x] Added regression coverage for offering search matching in `tests/test_regressions.py`
- [x] Verified `py_compile` and `tests.test_regressions` -> OK (16 tests)
- [x] Standardized the new Tab 2 offering UI text to Thai (`รายวิชาที่เปิดสอน`, `ภาคเรียน`, `ปีการศึกษา`, `แสดงข้อมูล`, Thai offering action labels)
- [x] Fixed the live Tab 2 opening-history display path so `การเปิดสอน` now renders Thai text like `ภาค 1/2569 N01 ... มี มคอ.3` instead of the garbled `เธ...` string
- [x] Verified `input_gui.py`, `database.py`, and `tests/test_regressions.py` with `py_compile` -> OK
- [x] Re-ran `tests.test_regressions` -> OK (15 tests)
- [ ] Separate unrelated issue discovered: `generate_tqf3.py` still has an `IndentationError` at line 631 and needs a follow-up fix
- [x] Roadmap step 2 started in the GUI: Tab 2 now has a term filter row (`semester` + `year`) and a dedicated `Term Offerings` list
- [x] Added offering-scoped actions in Tab 2: `Open In Term`, `Generate TQF3`, `TQF3 Staff`, `Delete Offering`
- [x] Added `CourseOfferingDialog` and wired it to `upsert_course_offering()`
- [x] Tab 2 offering actions now prefer the selected offering record instead of only using the old ad-hoc TQF3 path
- [x] Moved the crowded term-specific buttons off the main Tab 2 toolbar and into the offering panel
- [x] Added regression coverage for `CourseOfferingDialog._confirm()`
- [x] Re-ran `py_compile` and `tests.test_regressions` -> OK (15 tests)
- [x] Roadmap step 1 landed: added first-class `course_offerings` to `database.py`
- [x] Added `tqf3.offering_id` plus migration-safe backfill from legacy `tqf3` rows
- [x] Added DB helpers `upsert_course_offering()` and `get_course_offerings()`
- [x] Updated `upsert_tqf3()` to create/link a real offering record automatically
- [x] Updated Tab 2 course detail history to read from `course_offerings`
- [x] Added regression coverage for offering migration + `upsert_tqf3()` offering linkage
- [x] Verified `py_compile` and `tests.test_regressions` -> OK
- [x] Agreed next UI architecture: `Tab 1 = Curriculum Catalog` (master/template data), `Tab 2 = Term Offerings` (courses actually opened by semester/year)
- [x] Agreed that deep term-specific actions should move to Tab 2: TQF3 generation, TQF3 staff, section/special-section data, and later grades/TQF5
- [x] Agreed that opening history / "times offered" should be counted from `course_offerings`, not from ad-hoc TQF3 rows
- [x] Rewrote `ROADMAP_v2.md` in clean English to remove the old encoding-corrupted content and align it with the agreed architecture
- [x] Tab 2 GUI: added `course_teaching_plan` editor via new button `แผนการสอน`
- [x] Added `CourseTeachingPlanDialog` and `_TeachingPlanRowDialog` for weekly plan rows (add/edit/delete/reorder)
- [x] Added teaching plan summary block to the course detail panel in Tab 2
- [x] Fixed mojibake/garbled text in the Tab 2 `แผนการสอนรายสัปดาห์` detail panel by replacing the renderer with clean UTF-8 strings
- [x] Added editable dropdown suggestions to high-friction form fields (credits, prerequisite, CLO strategy/method, assessment name/period, teaching-plan week label)
- [x] Added regression tests for teaching plan dialogs in `tests/test_regressions.py`
- [x] Renamed `สิ่งที่ต้องแก้_generate_tqf3_schema.md` -> `issue_generate_tqf3_schema.md`
- [x] `input_gui.py` and regression tests verified -> OK

### Previous session (2026-04-12 session 3)
- [x] **BUG FIX**: `CourseResourcesDialog` add-row broken + `TQF3StaffDialog` blank page — root cause: `FG` constant missing from module. Added `FG = "#1a1a1a"` to style block. Both dialogs now functional. See `issue_gui_dialog_bugs.md`.
- [x] `input_gui.py` syntax verified — OK

### Previous session (2026-04-11 session 2)
- [x] Added `[low token used]` keyword to RULES.md and CODEX_CONTEXT.md — all MD files are now English-only
- [x] Fixed DB journal file via truncation — live `tqf_database.db` is now accessible from Linux sandbox
- [x] Verified all 8 TQF3 records generate correctly (`generate_tqf3_docx` OK for tqf3_id 1–4, 9, 18, 19, 20)
- [x] **Tab 2 GUI**: added "ทรัพยากร" button → `CourseResourcesDialog` (Add/Edit/Delete/Reorder `course_resources`)
- [x] **Tab 2 GUI**: added "บุคลากร มคอ.3" button → `TQF3StaffDialog` (manage committee + instructors per TQF3 record)
- [x] New helper dialogs: `_ResourceRowDialog`, `_PersonRowDialog`
- [x] `input_gui.py` syntax verified — 14 classes, 3102 lines

### Previous session (2026-04-11 session 1)
- [x] `generate_tqf3.py`: switched from code-built document to filling existing Word template (`templates/แบบฟอร์ม มคอ. 3.docx`)
- [x] Fixed CLO insertion position — CLOs now appear correctly between intro paragraph and "5.2 ผลการเรียนรู้..."
- [x] Fixed resources section (section 8) — no longer deletes section 9 and appendix
- [x] Fixed section 9 (committee + instructors) — replaced correctly via `_replace_block_between()`
- [x] Added `_replace_block_between()` helper — safe paragraph replacement using `addnext` (avoids `addprevious` XML bug in python-docx)
- [x] Added `_is_valid_instructor_name()` — filters garbage appendix items mistakenly stored in `instructors_json`
- [x] Fixed corrupt `instructors_json` in tqf3 id=19 (SMA7005) — was importing appendix headings as instructor names
- [x] Populated `tqf3_staff` table for tqf3_id 1, 2, 3, 4, 19 from existing `instructors_json`/`instructor_main`
- [x] Diagnosed `.pyc` bytecode cache issue on Linux sandbox — after Edit/Write tool changes, run `touch generate_tqf3.py` to force Python to recompile
- [x] Created `TQF_system/tqf_database_fixed.db` — fixed version of DB with correct staff data
- [x] Created `TQF_system/restore_database.py` — Windows-side script to replace broken DB
- [x] Converted all MD files to English to reduce LLM token usage

### Known issue: DB journal file on Linux mount
`tqf_database.db-journal` exists on the mounted Windows filesystem and cannot be removed from the Linux sandbox. This causes `sqlite3.OperationalError: disk I/O error` when Python accesses the DB via bash.

**Fix (run from Windows once):**
```

---

## 2026-04-12 Agreed UX Direction

- `Tab 1 = Curriculum Catalog`
- Purpose: master/template data only (`courses`, PLOs, default CLOs, default assessments, default teaching plan, default resources)
- `Tab 2 = Term Offerings`
- Purpose: courses actually opened in a selected semester/year
- Add `course_offerings` as a first-class table and use it as the source of truth for real openings
- Add a "create offerings from catalog" flow in Tab 2: choose curriculum + semester + academic year, then select courses from the catalog to open that term
- Move deep term-specific actions to Tab 2: TQF3 generation/open, TQF3 staff, section/special-section info, later grades and TQF5
- Count opening history / `times offered` from `course_offerings`, not from ad-hoc generated TQF3 rows
- Replace the fixed N01–N09 / P01–P09 picker with offering-backed section records in a later step

## Ordered Next Steps For Tab 2

Follow this order unless a blocking bug forces a detour.

### Step 1: Restructure Tab 2 layout
- [x] Added top term-control row with semester, year, search, and primary `เปิดสอนวิชาที่เลือก`
- [x] Added right-side contextual offering action box
- [ ] Full split between catalog actions and term actions is still incomplete

### Step 2: Enforce selection-state UX
- All offering actions stay disabled until one offering row is selected
- Header text in the action area should reflect the selected offering
- Double-click on an offering row should open a safe edit/detail action

### Step 3: Add quick filter and table readability
- [x] Added live search by course code / Thai name / section
- [x] Added zebra striping in the offering table
- [ ] Keep the table scan-friendly:
  - code
  - course name
  - section
  - offering status
  - TQF3 status

### Step 4: Finish offering-first action flow
- Move term-specific actions fully into the selected-offering context:
  - edit offering
  - generate/open TQF3
  - manage TQF3 staff
  - later grades / TQF5
- Keep instructor detail in the side panel rather than widening the table

### Step 5: Build the real creation flow
- Add `open offerings from catalog`
- Flow:
  - choose curriculum
  - choose semester
  - choose academic year
  - choose catalog courses to open
  - create one or more offering rows

### Step 6: Replace fixed section assumptions
- Stop treating `N01-N09 / P01-P09` as the long-term source of truth
- Read section choices from `course_offerings`
- Keep the old fixed picker only as a temporary compatibility fallback
cd "tqf gen\tqf_system\TQF_system"
python restore_database.py
```
This deletes the journal file and replaces `tqf_database.db` with the fixed version.

---

## 🔵 In Progress
- [ ] Roadmap step 2 is partially landed: Tab 2 now has an initial offering manager, but bulk "create offerings from catalog" and deeper offering-first detail views are still pending.

---

## 🟡 Next Up

- [x] **BUG FIX**: `CourseResourcesDialog` + `TQF3StaffDialog` — fixed 2026-04-12 (missing `FG` constant)
- [ ] **FEATURE**: Semester offering manager — a dedicated UI (Tab 1 or new Tab) to declare which courses are offered in a given semester/year, with section count that can be updated later. TQF3 generation should be tied to a declared offering record, not created ad-hoc. This prevents accidental "test" TQF3 entries from being treated as real offerings. Likely needs a new table `course_offerings(id, course_id, semester, year, is_special, sections, status)` and a picker before "สร้าง มคอ.3" to select an existing offering or create a new one.
- [ ] **FEATURE (related)**: In the "สร้าง มคอ.3" dialog, section codes N01–N09 (normal) and P01–P09 (พิเศษ) are shown as a fixed ordered list. Once the semester offering manager exists, these section slots should come from the declared offering (how many sections were registered) rather than being a free-pick dropdown. For now the ordering N01→N09, P01→P09 is correct as-is.
- [ ] `import_courses_excel.py` — bulk import courses from Excel
- [ ] `generate_tqf5.py` — test with real DB
- [ ] Test edge cases: TQF3 generation with very long CLO text, merge cells in template
- [ ] Supply PLO data for curricula 65 and 69

---

## 🔴 Warnings / Known Issues

| Issue | Detail |
|-------|--------|
| ~~**CourseResourcesDialog: cannot add**~~ | ✅ Fixed 2026-04-12 — `FG` constant was missing; see `issue_gui_dialog_bugs.md` |
| ~~**TQF3StaffDialog: blank page**~~ | ✅ Fixed 2026-04-12 — same root cause (`FG` undefined → silent NameError) |
| **DB path has spaces** | `tqf gen/` → SQLite in Linux sandbox cannot open directly; copy to `/tmp/` first for testing. Production on Windows works fine. |
| **DB journal file** | `tqf_database.db-journal` blocks all Linux-side DB writes. Run `restore_database.py` on Windows. See `TQF_system/restore_database.py`. |
| **LibreOffice dependency** | `import_tqf3.py` requires LibreOffice to convert `.doc` → `.docx`. `import_grades.py` has its own native RTF parser (no dependency). |
| **tqf3 UNIQUE** | `(course_id, semester, year, is_special)` — special-section (P0x) and regular (N0x) stored as separate records. |
| **generate_tqf3 template mapping** | If `แบบฟอร์ม มคอ. 3.docx` is ever modified, re-verify paragraph indices and cell mapping in `generate_tqf3.py`. |
| **Linux mount / .pyc cache** | Edit/Write tool writes to Windows path; Linux mount may lag. After edits always run `touch <file>.py` to invalidate `.pyc` cache before testing. |
| **Never use `cp` to replace DB on mount** | Use `conn.backup()` API or run the replacement script on Windows. Raw `cp` + existing journal = corrupted DB. |

---

## 📁 Key Reference Files

| File | Purpose |
|------|---------|
| `PROJECT_REFERENCE.md` | Full schema, ERD, function list |
| `ROADMAP_v2.md` | v2 development plan (3-layer architecture) |
| `RULES.md` | Rules for all AI tools |
| `CODEX_CONTEXT.md` | Context specifically for Codex |
| `HANDOFF.md` | This file — current status |

---

## 📋 Update Template (fill in after every session)

```markdown
## 🟢 Latest Status
Updated: YYYY-MM-DD  |  Machine: PC/MacBook  |  Tool: Cowork/Codex

### Completed this session
- [x] ...

## 🔵 In Progress
- [ ] (if any) describe exactly where you stopped and which file/function
```
