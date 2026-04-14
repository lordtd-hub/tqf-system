-- 001_baseline.sql
-- Baseline schema: all tables that existed before the versioned migration
-- runner was introduced. This file is marked as pre-applied on legacy DBs.
-- For fresh installs it creates the complete initial schema.

CREATE TABLE IF NOT EXISTS curricula (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT    NOT NULL UNIQUE,
    name_th         TEXT    DEFAULT '',
    effective_year  INTEGER DEFAULT 0,
    graduation_req  TEXT    DEFAULT '',
    created_at      TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS courses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_id       INTEGER REFERENCES curricula(id),
    code                TEXT    NOT NULL,
    name_th             TEXT    NOT NULL,
    name_en             TEXT    NOT NULL DEFAULT '',
    credits_text        TEXT    DEFAULT '',
    credit_lecture      INTEGER DEFAULT 0,
    credit_lab          INTEGER DEFAULT 0,
    credit_self         INTEGER DEFAULT 0,
    prerequisite        TEXT    DEFAULT 'ไม่มี',
    course_type         TEXT    DEFAULT '',
    description_th      TEXT    DEFAULT '',
    description_en      TEXT    DEFAULT '',
    faculty             TEXT    DEFAULT '',
    department          TEXT    DEFAULT '',
    created_at          TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(code, curriculum_id)
);

CREATE TABLE IF NOT EXISTS course_offerings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    curriculum_id       INTEGER NOT NULL REFERENCES curricula(id) ON DELETE CASCADE,
    semester            INTEGER NOT NULL,
    year                INTEGER NOT NULL,
    section_code        TEXT    NOT NULL,
    is_special          INTEGER NOT NULL DEFAULT 0,
    status              TEXT    NOT NULL DEFAULT 'active',
    source_type         TEXT    NOT NULL DEFAULT 'catalog',
    created_at          TEXT    DEFAULT (datetime('now','localtime')),
    updated_at          TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(course_id, semester, year, section_code)
);

CREATE TABLE IF NOT EXISTS tqf3 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    offering_id         INTEGER REFERENCES course_offerings(id) ON DELETE SET NULL,
    semester            INTEGER NOT NULL,
    year                INTEGER NOT NULL,
    instructor_main     TEXT    DEFAULT '',
    instructors_json    TEXT    DEFAULT '[]',
    location            TEXT    DEFAULT '',
    objectives          TEXT    DEFAULT '',
    source_file         TEXT    DEFAULT '',
    source_type         TEXT    DEFAULT 'imported',
    is_special          INTEGER NOT NULL DEFAULT 0,
    imported_at         TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(course_id, semester, year, is_special)
);

CREATE TABLE IF NOT EXISTS clos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    clo_number          INTEGER NOT NULL,
    description         TEXT    NOT NULL,
    teaching_strategy   TEXT    DEFAULT '',
    assessment_method   TEXT    DEFAULT '',
    indicator           TEXT    DEFAULT '',
    target_pct          REAL    DEFAULT 50.0,
    UNIQUE(tqf3_id, clo_number)
);

CREATE TABLE IF NOT EXISTS teaching_plan (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    week                INTEGER NOT NULL,
    week_label          TEXT    DEFAULT '',
    llo_text            TEXT    DEFAULT '',
    topic               TEXT    NOT NULL,
    activities          TEXT    DEFAULT '',
    media               TEXT    DEFAULT '',
    assessment_tools    TEXT    DEFAULT '',
    hours_planned       REAL    NOT NULL DEFAULT 0,
    hours_theory        REAL    DEFAULT 0,
    hours_practice      REAL    DEFAULT 0,
    hours_self          REAL    DEFAULT 0,
    teaching_method     TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS assessments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    name                TEXT    NOT NULL,
    full_score          REAL    DEFAULT 100,
    weight_pct          REAL    NOT NULL DEFAULT 0,
    clo_mapping         TEXT    DEFAULT '[]',
    assessment_period   TEXT    DEFAULT '',
    eval_criteria       TEXT    DEFAULT '',
    pass_threshold      REAL    DEFAULT 50.0
);

CREATE TABLE IF NOT EXISTS tqf5 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL UNIQUE REFERENCES tqf3(id) ON DELETE CASCADE,
    registered_count    INTEGER DEFAULT 0,
    remaining_count     INTEGER DEFAULT 0,
    withdrawn_count     INTEGER DEFAULT 0,
    grade_dist_json     TEXT    DEFAULT '{}',
    abnormal_factors    TEXT    DEFAULT '',
    deviation_time      TEXT    DEFAULT '',
    deviation_method    TEXT    DEFAULT '',
    clo_results_json    TEXT    DEFAULT '[]',
    verification_method TEXT    DEFAULT '',
    resource_issues     TEXT    DEFAULT '',
    admin_issues        TEXT    DEFAULT '',
    student_eval_notes  TEXT    DEFAULT '',
    teacher_response    TEXT    DEFAULT '',
    improvement_prev    TEXT    DEFAULT '',
    improvement_next    TEXT    DEFAULT '',
    improvement_resp    TEXT    DEFAULT '',
    suggestions         TEXT    DEFAULT '',
    last_updated        TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS student_grades (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf5_id             INTEGER NOT NULL REFERENCES tqf5(id) ON DELETE CASCADE,
    student_id          TEXT    NOT NULL,
    student_name        TEXT    NOT NULL,
    section             TEXT    DEFAULT '',
    score_components    TEXT    DEFAULT '{}',
    total_score         REAL    DEFAULT 0,
    grade               TEXT    NOT NULL,
    UNIQUE(tqf5_id, student_id)
);

CREATE TABLE IF NOT EXISTS teaching_actual (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf5_id             INTEGER NOT NULL REFERENCES tqf5(id) ON DELETE CASCADE,
    topic               TEXT    NOT NULL,
    hours_planned       REAL    DEFAULT 0,
    hours_actual        REAL    DEFAULT 0,
    deviation_reason    TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS plos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_id   INTEGER NOT NULL REFERENCES curricula(id) ON DELETE CASCADE,
    plo_number      INTEGER NOT NULL,
    plo_code        TEXT    DEFAULT '',
    category        TEXT    DEFAULT '',
    description     TEXT    NOT NULL DEFAULT '',
    UNIQUE(curriculum_id, plo_number)
);

CREATE TABLE IF NOT EXISTS ylos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_id       INTEGER NOT NULL REFERENCES curricula(id) ON DELETE CASCADE,
    year_number         INTEGER NOT NULL,
    title               TEXT    NOT NULL DEFAULT '',
    indicators          TEXT    DEFAULT '',
    assessment_methods  TEXT    DEFAULT '',
    plo_mapping         TEXT    DEFAULT '[]',
    UNIQUE(curriculum_id, year_number)
);

CREATE TABLE IF NOT EXISTS course_clos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    clo_number          INTEGER NOT NULL,
    description         TEXT    NOT NULL DEFAULT '',
    domain              TEXT    DEFAULT '',
    teaching_strategy   TEXT    DEFAULT '',
    assessment_method   TEXT    DEFAULT '',
    pass_threshold_pct  REAL    DEFAULT 50.0,
    plo_mapping         TEXT    DEFAULT '[]',
    UNIQUE(course_id, clo_number)
);

CREATE TABLE IF NOT EXISTS course_teaching_plan (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    seq                 INTEGER DEFAULT 0,
    week                INTEGER NOT NULL DEFAULT 0,
    week_label          TEXT    DEFAULT '',
    llo_text            TEXT    DEFAULT '',
    topic               TEXT    NOT NULL DEFAULT '',
    activities          TEXT    DEFAULT '',
    teaching_method     TEXT    DEFAULT '',
    media               TEXT    DEFAULT '',
    assessment_tools    TEXT    DEFAULT '',
    hours_planned       REAL    DEFAULT 0,
    hours_theory        REAL    DEFAULT 0,
    hours_practice      REAL    DEFAULT 0,
    hours_self          REAL    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS course_assessments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    seq                 INTEGER DEFAULT 0,
    name                TEXT    NOT NULL,
    full_score          REAL    DEFAULT 100,
    weight_pct          REAL    NOT NULL DEFAULT 0,
    clo_mapping         TEXT    DEFAULT '[]',
    assessment_period   TEXT    DEFAULT '',
    eval_criteria       TEXT    DEFAULT '',
    pass_threshold      REAL    DEFAULT 50.0
);

CREATE TABLE IF NOT EXISTS course_resources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    seq             INTEGER DEFAULT 0,
    resource_type   TEXT    DEFAULT '',
    citation_text   TEXT    NOT NULL DEFAULT '',
    url             TEXT    DEFAULT '',
    note            TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tqf3_staff (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id         INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    role            TEXT    NOT NULL DEFAULT '',
    seq             INTEGER DEFAULT 0,
    name            TEXT    NOT NULL DEFAULT ''
);

-- schema_migrations is created by runner.py before this file is applied
-- included here so fresh installs via executescript() also have it
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now','localtime'))
);
