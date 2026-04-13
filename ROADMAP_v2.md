# ROADMAP v2 - TQF System Architecture Redesign
Updated: 2026-04-12

---

## Goal

Redesign the system around a clear separation between:

1. Curriculum-level data
2. Course template data
3. Term offering data

This keeps long-lived academic structure separate from semester-specific teaching records.

---

## Core Architecture

```text
Layer 1: CURRICULUM
  - curricula
  - plos

Layer 2: COURSE CATALOG (template layer)
  - courses
  - course_clos
  - course_assessments
  - course_teaching_plan
  - course_resources

Layer 3: COURSE OFFERING (term layer)
  - course_offerings
  - tqf3
  - clos
  - assessments
  - teaching_plan
  - tqf3_staff
  - tqf5
  - student_grades
```

Rule of thumb:
- Layer 2 is reused across years
- Layer 3 represents a real opened course in a specific semester/year/section

---

## Agreed GUI Direction

This is the agreed UX direction as of 2026-04-12.

### Tab 1: Curriculum Catalog

Purpose:
- Manage master/template data only

Scope:
- curricula
- courses
- PLOs
- default CLOs
- default assessment templates
- default teaching plan
- default resources

### Tab 2: Term Offerings

Purpose:
- Manage courses actually opened in a selected semester/year

Scope:
- offering records
- section/special-section data
- generate/open TQF3
- TQF3 staff
- later grades and TQF5

### Key UX Rules

- Term-specific actions should live in Tab 2, not in the catalog tab
- `times offered` should be counted from `course_offerings`
- section choices should eventually come from offering records, not a fixed N01-N09 / P01-P09 picker
- Tab 2 should support a "create offerings from catalog" flow:
  - choose curriculum
  - choose semester
  - choose academic year
  - choose which catalog courses are opened that term

### Recommended Tab 2 layout

Use a 3-zone layout:

1. Top control panel
- semester
- academic year
- quick search
- primary `open offering from catalog` action

2. Main data view
- offering table on the left
- selected offering detail panel on the right

3. Contextual action panel
- all term-specific actions depend on the currently selected offering
- keep these disabled until a row is selected

Design notes:
- keep the table compact for scanning
- move rich details to the right-side panel
- use zebra striping for readability
- double-click should open a safe edit/detail action

---

## Schema Direction

### Existing tables to keep

- `curricula`
- `courses`
- `tqf3`
- `clos`
- `teaching_plan`
- `assessments`
- `tqf5`
- `student_grades`

### Template-layer tables already added

- `plos`
- `course_clos`
- `course_assessments`
- `course_teaching_plan`
- `course_resources`
- `tqf3_staff`

### Next required table

#### `course_offerings`

Recommended shape:

```sql
CREATE TABLE IF NOT EXISTS course_offerings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id     INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    curriculum_id INTEGER NOT NULL REFERENCES curricula(id) ON DELETE CASCADE,
    semester      INTEGER NOT NULL,
    year          INTEGER NOT NULL,
    section_code  TEXT    NOT NULL,
    is_special    INTEGER NOT NULL DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'planned',
    source_type   TEXT    NOT NULL DEFAULT 'catalog',
    created_at    TEXT    DEFAULT (datetime('now','localtime')),
    updated_at    TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(course_id, semester, year, section_code)
);
```

Notes:
- Prefer one row per actual section/offering
- This fits TQF3, grades, and TQF5 better than grouping many sections into one row

---

## Data Relationship Summary

```text
curricula
  -> plos
  -> courses
       -> course_clos
       -> course_assessments
       -> course_teaching_plan
       -> course_resources
       -> course_offerings
            -> tqf3
                 -> clos
                 -> assessments
                 -> teaching_plan
                 -> tqf3_staff
                 -> tqf5
                      -> student_grades
```

Important distinction:
- `course_*` tables are defaults/templates
- `tqf3`-side tables are offering-specific snapshots or overrides

---

## Workflow Direction

### Workflow A: Maintain curriculum/catalog data

1. Select curriculum
2. Add or edit course master data
3. Maintain PLOs
4. Maintain default CLOs and PLO mapping
5. Maintain default assessments
6. Maintain default teaching plan
7. Maintain default resources

### Workflow B: Manage a teaching term

1. Choose curriculum
2. Choose semester
3. Choose academic year
4. Search/filter existing offerings for that term
5. Add offerings from the catalog if missing
6. Select one offering
7. Use contextual actions for TQF3 / staff / term-specific work

---

## Implementation Order

### Phase 2A - Tab 2 layout cleanup
- [x] rebuild Tab 2 into top controls + offering list + detail panel + contextual actions
- [ ] remove crowded mixed-purpose buttons from the old toolbar completely

### Phase 2B - Selection-state behavior
- [x] disable actions until an offering is selected
- [x] bind selected-offering summary into the action panel
- [ ] add safe double-click behavior

### Phase 2C - Search and readability
- [x] add quick filter
- [x] add zebra striping
- [ ] keep the visible table columns compact

### Phase 2D - Offering-first actions
- make selected offering the default context for:
  - TQF3 generation/open
  - TQF3 staff
  - later TQF5 / grades

### Phase 2E - Bulk creation from catalog
- add `open offerings from catalog`
- support selecting multiple catalog courses to create term offerings

### Phase 2F - Section source-of-truth cleanup
- switch section choice logic to offering-backed records
- keep fixed section lists only as backward-compatible fallback during transition

Output:
- reusable course template for future offerings

### Workflow B: Create real offerings for a term

1. Go to Tab 2
2. Select curriculum, semester, academic year
3. Create offerings from catalog
4. Select which courses are actually opened
5. Create one or more section records

Output:
- official offering rows in `course_offerings`

### Workflow C: Work on a selected offering

1. Open offering detail
2. Generate TQF3 from template data or open an imported record
3. Edit TQF3-specific staff or section details
4. Import grades later
5. Generate TQF5 later

Output:
- full semester-specific teaching record

---

## Snapshot Strategy

Recommended behavior:

- Before TQF3 exists:
  - offering reads defaults from `course_*` tables
- When TQF3 is generated:
  - snapshot template data into offering-specific tables
- After TQF3 exists:
  - edits affect the offering snapshot, not the master template

This keeps:
- catalog data reusable
- historical TQF3 records stable

---

## Risks and Design Notes

### 1. Snapshot drift

If `course_clos` changes after a TQF3 record already exists, the old TQF3 should not silently change.

Recommendation:
- keep TQF3 as a snapshot
- show a warning in GUI when template data changed after a TQF3 was created

### 2. Many-to-many mapping storage

Current JSON-based mappings such as `plo_mapping` are acceptable for current scale.

Tradeoff:
- simple to store
- not ideal for complex SQL analytics

### 3. Assessment weights

`course_assessments.weight_pct` and offering-level `assessments.weight_pct` should validate to 100%.

### 4. Dynamic section picker

The current fixed N01-N09 / P01-P09 picker is only a temporary solution.

Future rule:
- section choices come from `course_offerings`

### 5. Source of "times offered"

Use:
- count of `course_offerings`

Do not use:
- count of generated TQF3 rows

Reason:
- offering records are the business truth

---

## Implementation Priority

Current status:
- Step 1 is done in the DB layer: `course_offerings` exists, legacy `tqf3` rows are backfilled, and `tqf3.offering_id` is linked
- Step 2 is partially landed in the GUI: Tab 2 has term filters, an offering list, and offering-scoped actions
- Step 3 is the next active slice: bulk "create offerings from catalog"

1. Add `course_offerings` table and migration
   Status: done in `database.py`
2. Refactor Tab 1 / Tab 2 responsibilities
   Status: partially landed in `input_gui.py`
3. Build "create offerings from catalog" flow
   Status: next active implementation slice
4. Move term-specific actions to Tab 2
5. Replace fixed section picker with offering-backed sections
6. Recompute "times offered" from offerings
7. Add later reports that aggregate by offering history

---

## Open Inputs Still Needed

- Final decision on whether every section gets its own offering row
- Real PLO data for curricula 65 and 69
- Continued edge-case testing for long TQF3 content and template layout behavior
