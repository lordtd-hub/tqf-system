-- 004_offering_status.sql
-- State machine tables for course offering lifecycle

-- Current state per offering (one-to-one with course_offerings)
CREATE TABLE IF NOT EXISTS offering_status (
    offering_id INTEGER PRIMARY KEY REFERENCES course_offerings(id) ON DELETE CASCADE,
    state       TEXT    NOT NULL DEFAULT 'not_started',
    updated_at  TEXT    DEFAULT (datetime('now','localtime')),
    updated_by  TEXT    DEFAULT ''
);

-- Full audit trail of every state transition
CREATE TABLE IF NOT EXISTS offering_status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    offering_id INTEGER NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    from_state  TEXT    DEFAULT '',
    to_state    TEXT    NOT NULL,
    changed_at  TEXT    DEFAULT (datetime('now','localtime')),
    changed_by  TEXT    DEFAULT '',
    note        TEXT    DEFAULT ''
);

-- Backfill: create offering_status rows for all existing offerings.
-- Infer initial state from existing tqf3 / clos / tqf5 data.
INSERT OR IGNORE INTO offering_status (offering_id, state)
SELECT co.id,
    CASE
        WHEN t5.id IS NOT NULL THEN 'tqf5_generated'
        WHEN t3.id IS NOT NULL
             AND (SELECT COUNT(*) FROM clos cl WHERE cl.tqf3_id = t3.id) > 0
             THEN 'tqf3_generated'
        WHEN t3.id IS NOT NULL THEN 'in_progress'
        ELSE 'not_started'
    END
FROM course_offerings co
LEFT JOIN tqf3 t3 ON t3.offering_id = co.id
LEFT JOIN tqf5 t5 ON t5.tqf3_id = t3.id;
