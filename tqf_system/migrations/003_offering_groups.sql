-- 003_offering_groups.sql
-- Multi-instructor support + group/section detail on course_offerings

-- Multi-instructor per offering (replaces flat instructors_json in tqf3)
CREATE TABLE IF NOT EXISTS offering_instructors (
    offering_id     INTEGER NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    instructor_name TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'co',   -- main|co
    section         TEXT    DEFAULT '',
    ordering        INTEGER DEFAULT 0,
    PRIMARY KEY (offering_id, instructor_name, section)
);

-- Extra detail columns on course_offerings
-- (ALTER TABLE ADD COLUMN; safe to run once since tracked in schema_migrations)
ALTER TABLE course_offerings ADD COLUMN section_label  TEXT    DEFAULT '';
ALTER TABLE course_offerings ADD COLUMN group_code     TEXT    DEFAULT '';
ALTER TABLE course_offerings ADD COLUMN enrollment_cap INTEGER DEFAULT 0;
