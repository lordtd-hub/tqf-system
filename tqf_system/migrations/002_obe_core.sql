-- 002_obe_core.sql
-- OBE core entities: students master, enrollments, LLOs, CLO<->LLO mapping

-- Students master registry (one record per real person)
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code    TEXT    NOT NULL UNIQUE,
    full_name_th    TEXT    NOT NULL DEFAULT '',
    full_name_en    TEXT    DEFAULT '',
    curriculum_id   INTEGER REFERENCES curricula(id),
    entry_year      INTEGER,
    status          TEXT    NOT NULL DEFAULT 'active',  -- active|graduated|withdrawn
    created_at      TEXT    DEFAULT (datetime('now','localtime'))
);

-- Enrollment: links student to a specific course offering + stores grade
CREATE TABLE IF NOT EXISTS enrollments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    offering_id     INTEGER NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    section         TEXT    DEFAULT '',
    midterm_score   REAL,
    final_score     REAL,
    total_score     REAL,
    final_grade     TEXT    DEFAULT '',   -- A|B+|B|C+|C|D+|D|E|W|I|P|S|U
    grade_points    REAL,
    imported_at     TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(offering_id, student_id)
);

-- LLO (Lesson-Level Learning Outcome) as first-class entity, scoped to course template
CREATE TABLE IF NOT EXISTS llos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    llo_number      INTEGER NOT NULL,
    description_th  TEXT    NOT NULL DEFAULT '',
    description_en  TEXT    DEFAULT '',
    UNIQUE(course_id, llo_number)
);

-- CLO <-> LLO mapping (many-to-many, course template level)
CREATE TABLE IF NOT EXISTS clo_llo_map (
    clo_id  INTEGER NOT NULL REFERENCES course_clos(id) ON DELETE CASCADE,
    llo_id  INTEGER NOT NULL REFERENCES llos(id) ON DELETE CASCADE,
    weight  REAL    NOT NULL DEFAULT 1.0,
    PRIMARY KEY (clo_id, llo_id)
);

-- Link teaching_plan rows to LLO entity (nullable FK, backward-compat with llo_text)
-- SQLite ALTER TABLE ADD COLUMN is idempotent only when migration runs once (tracked in schema_migrations)
ALTER TABLE teaching_plan ADD COLUMN llo_id INTEGER REFERENCES llos(id) ON DELETE SET NULL;
