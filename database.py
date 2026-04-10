"""
database.py — TQF System Database Layer
SQLite schema + CRUD helpers
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager

# ────────────────────────────────────────────────
# Path to DB file — placed next to this script
# ────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tqf_database.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ════════════════════════════════════════════════
# SCHEMA CREATION
# ════════════════════════════════════════════════

SCHEMA = """
-- ─── หลักสูตร (เช่น 65, 69) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS curricula (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT    NOT NULL UNIQUE,   -- "65", "69"
    name_th         TEXT    DEFAULT '',        -- ชื่อหลักสูตรภาษาไทย
    effective_year  INTEGER DEFAULT 0,         -- ปีที่เริ่มใช้
    created_at      TEXT    DEFAULT (datetime('now','localtime'))
);

-- ─── ตารางหลักสูตรรายวิชา ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS courses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_id       INTEGER REFERENCES curricula(id),   -- หลักสูตรที่สังกัด
    code                TEXT    NOT NULL,              -- รหัสวิชา e.g. SMA0901
    name_th             TEXT    NOT NULL,
    name_en             TEXT    NOT NULL DEFAULT '',
    credits_text        TEXT    DEFAULT '',            -- e.g. 1(0-1-2)
    credit_lecture      INTEGER DEFAULT 0,
    credit_lab          INTEGER DEFAULT 0,
    credit_self         INTEGER DEFAULT 0,
    prerequisite        TEXT    DEFAULT 'ไม่มี',
    course_type         TEXT    DEFAULT '',            -- วิชาแกน/วิชาบังคับ/ฯลฯ
    description_th      TEXT    DEFAULT '',
    description_en      TEXT    DEFAULT '',
    faculty             TEXT    DEFAULT '',
    department          TEXT    DEFAULT '',
    created_at          TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(code, curriculum_id)
);

-- ─── มคอ.3 แต่ละภาคการศึกษา ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tqf3 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    semester            INTEGER NOT NULL,              -- 1 หรือ 2
    year                INTEGER NOT NULL,              -- ปีการศึกษา เช่น 2568
    instructor_main     TEXT    DEFAULT '',            -- อาจารย์ผู้รับผิดชอบ
    instructors_json    TEXT    DEFAULT '[]',          -- JSON array ชื่ออาจารย์+กลุ่ม
    location            TEXT    DEFAULT '',
    objectives          TEXT    DEFAULT '',
    source_file         TEXT    DEFAULT '',            -- path ไฟล์ต้นฉบับ
    is_special          INTEGER NOT NULL DEFAULT 0,   -- 0=ปกติ (N0x), 1=พิเศษ (P0x)
    imported_at         TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(course_id, semester, year, is_special)
);

-- ─── CLOs ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    clo_number          INTEGER NOT NULL,
    description         TEXT    NOT NULL,
    teaching_strategy   TEXT    DEFAULT '',
    assessment_method   TEXT    DEFAULT '',
    indicator           TEXT    DEFAULT '',            -- ตัวชี้วัด
    target_pct          REAL    DEFAULT 50.0,          -- ค่าเป้าหมาย %
    UNIQUE(tqf3_id, clo_number)
);

-- ─── แผนการสอนรายสัปดาห์ ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teaching_plan (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    week                INTEGER NOT NULL,
    topic               TEXT    NOT NULL,
    hours_planned       REAL    NOT NULL DEFAULT 0,
    teaching_method     TEXT    DEFAULT ''
);

-- ─── แผนการประเมิน ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS assessments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL REFERENCES tqf3(id) ON DELETE CASCADE,
    name                TEXT    NOT NULL,              -- สอบกลางภาค / งาน / ฯลฯ
    weight_pct          REAL    NOT NULL DEFAULT 0,
    clo_mapping         TEXT    DEFAULT '[]'           -- JSON list of CLO numbers
);

-- ─── มคอ.5 ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tqf5 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf3_id             INTEGER NOT NULL UNIQUE REFERENCES tqf3(id) ON DELETE CASCADE,
    registered_count    INTEGER DEFAULT 0,
    remaining_count     INTEGER DEFAULT 0,
    withdrawn_count     INTEGER DEFAULT 0,
    grade_dist_json     TEXT    DEFAULT '{}',          -- {A:4, B+:3, ...}
    abnormal_factors    TEXT    DEFAULT '',
    deviation_time      TEXT    DEFAULT '',            -- ความคลาดเคลื่อนด้านเวลา
    deviation_method    TEXT    DEFAULT '',            -- ความคลาดเคลื่อนด้านวิธี
    clo_results_json    TEXT    DEFAULT '[]',          -- [{clo:1, achieved:true, note:...}]
    verification_method TEXT    DEFAULT '',
    resource_issues     TEXT    DEFAULT '',
    admin_issues        TEXT    DEFAULT '',
    student_eval_notes  TEXT    DEFAULT '',
    teacher_response    TEXT    DEFAULT '',
    improvement_prev    TEXT    DEFAULT '',            -- แผนปรับปรุงจากภาคที่แล้ว
    improvement_next    TEXT    DEFAULT '',            -- ข้อเสนอแผนต่อไป
    improvement_resp    TEXT    DEFAULT '',            -- ผู้รับผิดชอบ
    suggestions         TEXT    DEFAULT '',
    last_updated        TEXT    DEFAULT (datetime('now','localtime'))
);

-- ─── ผลการเรียนรายคน ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS student_grades (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf5_id             INTEGER NOT NULL REFERENCES tqf5(id) ON DELETE CASCADE,
    student_id          TEXT    NOT NULL,
    student_name        TEXT    NOT NULL,
    section             TEXT    DEFAULT '',
    score_components    TEXT    DEFAULT '{}',          -- JSON {part1:40, part2:50}
    total_score         REAL    DEFAULT 0,
    grade               TEXT    NOT NULL,              -- A/B+/B/C+/C/D+/D/E/W/I/P/U
    UNIQUE(tqf5_id, student_id)
);

-- ─── ชั่วโมงสอนจริง vs แผน ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teaching_actual (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tqf5_id             INTEGER NOT NULL REFERENCES tqf5(id) ON DELETE CASCADE,
    topic               TEXT    NOT NULL,
    hours_planned       REAL    DEFAULT 0,
    hours_actual        REAL    DEFAULT 0,
    deviation_reason    TEXT    DEFAULT ''
);
"""


def init_db():
    """สร้าง schema ถ้ายังไม่มี + migrate คอลัมน์ใหม่"""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # ── Migration: เพิ่ม is_special ถ้า DB เก่ายังไม่มี ──────────────────
        cols = [r[1] for r in conn.execute("PRAGMA table_info(tqf3)").fetchall()]
        if "is_special" not in cols:
            conn.execute(
                "ALTER TABLE tqf3 ADD COLUMN is_special INTEGER NOT NULL DEFAULT 0")
            print("[DB] Migration: added tqf3.is_special column")
    print(f"[DB] Initialized: {DB_PATH}")


# ════════════════════════════════════════════════
# COURSE helpers
# ════════════════════════════════════════════════

def upsert_course(code, name_th, name_en="", credits_text="",
                  credit_lecture=0, credit_lab=0, credit_self=0,
                  prerequisite="ไม่มี", course_type="",
                  description_th="", description_en="",
                  faculty="", department="",
                  curriculum_id=None) -> int:
    with get_conn() as conn:
        # ถ้าไม่ระบุ curriculum_id → ดูว่า code นี้มีอยู่ใน curriculum ไหนแล้วหรือไม่
        # เพื่อป้องกันการสร้าง record ซ้ำด้วย curriculum_id=NULL
        if curriculum_id is None:
            existing = conn.execute(
                "SELECT id, curriculum_id FROM courses WHERE code=? ORDER BY curriculum_id DESC LIMIT 1",
                (code,)).fetchone()
            if existing:
                # อัปเดต record ที่มีอยู่แล้วแทนการสร้างใหม่
                conn.execute("""
                    UPDATE courses SET
                        name_th=CASE WHEN ?!='' THEN ? ELSE name_th END,
                        name_en=CASE WHEN ?!='' THEN ? ELSE name_en END,
                        credits_text=CASE WHEN ?!='' THEN ? ELSE credits_text END,
                        credit_lecture=CASE WHEN ?>0 THEN ? ELSE credit_lecture END,
                        credit_lab=CASE WHEN ?>0 THEN ? ELSE credit_lab END,
                        credit_self=CASE WHEN ?>0 THEN ? ELSE credit_self END,
                        faculty=CASE WHEN ?!='' THEN ? ELSE faculty END,
                        department=CASE WHEN ?!='' THEN ? ELSE department END
                    WHERE id=?
                """, (name_th, name_th, name_en, name_en, credits_text, credits_text,
                      credit_lecture, credit_lecture, credit_lab, credit_lab,
                      credit_self, credit_self, faculty, faculty, department, department,
                      existing["id"]))
                return existing["id"]

        conn.execute("""
            INSERT INTO courses (code, name_th, name_en, credits_text,
                credit_lecture, credit_lab, credit_self, prerequisite,
                course_type, description_th, description_en,
                faculty, department, curriculum_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(code, curriculum_id) DO UPDATE SET
                name_th=excluded.name_th, name_en=excluded.name_en,
                credits_text=excluded.credits_text,
                credit_lecture=excluded.credit_lecture,
                credit_lab=excluded.credit_lab,
                credit_self=excluded.credit_self,
                prerequisite=excluded.prerequisite,
                course_type=excluded.course_type,
                description_th=excluded.description_th,
                description_en=excluded.description_en,
                faculty=excluded.faculty, department=excluded.department
        """, (code, name_th, name_en, credits_text,
              credit_lecture, credit_lab, credit_self, prerequisite,
              course_type, description_th, description_en,
              faculty, department, curriculum_id))
        row = conn.execute("SELECT id FROM courses WHERE code=? AND curriculum_id IS ?", (code, curriculum_id)).fetchone()
        if not row:
            row = conn.execute("SELECT id FROM courses WHERE code=?", (code,)).fetchone()
        return row["id"]


def get_all_courses():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM courses ORDER BY code").fetchall()]


def get_course_by_code(code, curriculum_id=None):
    with get_conn() as conn:
        if curriculum_id is not None:
            row = conn.execute(
                "SELECT * FROM courses WHERE code=? AND curriculum_id=?",
                (code, curriculum_id)).fetchone()
        else:
            # ถ้าไม่ระบุ curriculum ให้คืน record ที่มี curriculum_id (ไม่ใช่ NULL) ก่อน
            row = conn.execute(
                "SELECT * FROM courses WHERE code=? ORDER BY curriculum_id DESC LIMIT 1",
                (code,)).fetchone()
        return dict(row) if row else None


# ════════════════════════════════════════════════
# TQF3 helpers
# ════════════════════════════════════════════════

def upsert_tqf3(course_id, semester, year, instructor_main="",
                instructors=None, location="", objectives="",
                source_file="", is_special=0) -> int:
    instructors_json = json.dumps(instructors or [], ensure_ascii=False)
    is_special = int(bool(is_special))
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO tqf3 (course_id, semester, year, instructor_main,
                instructors_json, location, objectives, source_file, is_special)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(course_id, semester, year, is_special) DO UPDATE SET
                instructor_main=excluded.instructor_main,
                instructors_json=excluded.instructors_json,
                location=excluded.location,
                objectives=excluded.objectives,
                source_file=excluded.source_file,
                imported_at=datetime('now','localtime')
        """, (course_id, semester, year, instructor_main,
              instructors_json, location, objectives, source_file, is_special))
        row = conn.execute(
            "SELECT id FROM tqf3 WHERE course_id=? AND semester=? AND year=? AND is_special=?",
            (course_id, semester, year, is_special)).fetchone()
        return row["id"]


def get_tqf3(tqf3_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT t.*, c.code, c.name_th FROM tqf3 t JOIN courses c ON c.id=t.course_id WHERE t.id=?",
            (tqf3_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["instructors"] = json.loads(d.get("instructors_json", "[]"))
        return d


def get_all_tqf3(course_id=None):
    with get_conn() as conn:
        if course_id:
            rows = conn.execute(
                "SELECT t.*, c.code, c.name_th FROM tqf3 t JOIN courses c ON c.id=t.course_id WHERE t.course_id=? ORDER BY t.year DESC, t.semester DESC",
                (course_id,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT t.*, c.code, c.name_th FROM tqf3 t JOIN courses c ON c.id=t.course_id ORDER BY t.year DESC, t.semester DESC"
            ).fetchall()
        return [dict(r) for r in rows]


# ════════════════════════════════════════════════
# CLO helpers
# ════════════════════════════════════════════════

def replace_clos(tqf3_id, clos_list):
    """clos_list = [{"clo_number":1, "description":"...", ...}, ...]"""
    with get_conn() as conn:
        conn.execute("DELETE FROM clos WHERE tqf3_id=?", (tqf3_id,))
        for c in clos_list:
            conn.execute("""
                INSERT INTO clos (tqf3_id, clo_number, description,
                    teaching_strategy, assessment_method, indicator, target_pct)
                VALUES (?,?,?,?,?,?,?)
            """, (tqf3_id, c.get("clo_number", 0), c.get("description", ""),
                  c.get("teaching_strategy", ""), c.get("assessment_method", ""),
                  c.get("indicator", ""), c.get("target_pct", 50.0)))


def get_clos(tqf3_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM clos WHERE tqf3_id=? ORDER BY clo_number",
            (tqf3_id,)).fetchall()]


# ════════════════════════════════════════════════
# Teaching Plan helpers
# ════════════════════════════════════════════════

def replace_teaching_plan(tqf3_id, plan_list):
    """plan_list = [{"week":1, "topic":"...", "hours_planned":2, ...}, ...]"""
    with get_conn() as conn:
        conn.execute("DELETE FROM teaching_plan WHERE tqf3_id=?", (tqf3_id,))
        for p in plan_list:
            conn.execute("""
                INSERT INTO teaching_plan (tqf3_id, week, topic, hours_planned, teaching_method)
                VALUES (?,?,?,?,?)
            """, (tqf3_id, p.get("week", 0), p.get("topic", ""),
                  p.get("hours_planned", 0), p.get("teaching_method", "")))


def get_teaching_plan(tqf3_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM teaching_plan WHERE tqf3_id=? ORDER BY week",
            (tqf3_id,)).fetchall()]


# ════════════════════════════════════════════════
# Assessment helpers
# ════════════════════════════════════════════════

def replace_assessments(tqf3_id, assessments_list):
    with get_conn() as conn:
        conn.execute("DELETE FROM assessments WHERE tqf3_id=?", (tqf3_id,))
        for a in assessments_list:
            conn.execute("""
                INSERT INTO assessments (tqf3_id, name, weight_pct, clo_mapping)
                VALUES (?,?,?,?)
            """, (tqf3_id, a.get("name", ""),
                  a.get("weight_pct", 0),
                  json.dumps(a.get("clo_mapping", []), ensure_ascii=False)))


def get_assessments(tqf3_id):
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM assessments WHERE tqf3_id=? ORDER BY id",
            (tqf3_id,)).fetchall()]
        for r in rows:
            r["clo_mapping"] = json.loads(r.get("clo_mapping", "[]"))
        return rows


# ════════════════════════════════════════════════
# TQF5 helpers
# ════════════════════════════════════════════════

def get_or_create_tqf5(tqf3_id) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM tqf5 WHERE tqf3_id=?", (tqf3_id,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO tqf5 (tqf3_id) VALUES (?)", (tqf3_id,))
        return cur.lastrowid


def get_tqf5(tqf3_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tqf5 WHERE tqf3_id=?", (tqf3_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["grade_dist"] = json.loads(d.get("grade_dist_json", "{}"))
        d["clo_results"] = json.loads(d.get("clo_results_json", "[]"))
        return d


def update_tqf5(tqf5_id, **kwargs):
    if "grade_dist" in kwargs:
        kwargs["grade_dist_json"] = json.dumps(kwargs.pop("grade_dist"), ensure_ascii=False)
    if "clo_results" in kwargs:
        kwargs["clo_results_json"] = json.dumps(kwargs.pop("clo_results"), ensure_ascii=False)
    kwargs["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [tqf5_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE tqf5 SET {cols} WHERE id=?", vals)


# ════════════════════════════════════════════════
# Student Grade helpers
# ════════════════════════════════════════════════

def replace_student_grades(tqf5_id, grades_list):
    """grades_list = [{"student_id":"...", "student_name":"...", "grade":"A", ...}]"""
    with get_conn() as conn:
        conn.execute("DELETE FROM student_grades WHERE tqf5_id=?", (tqf5_id,))
        for g in grades_list:
            conn.execute("""
                INSERT INTO student_grades
                    (tqf5_id, student_id, student_name, section,
                     score_components, total_score, grade)
                VALUES (?,?,?,?,?,?,?)
            """, (tqf5_id, g.get("student_id", ""), g.get("student_name", ""),
                  g.get("section", ""),
                  json.dumps(g.get("score_components", {}), ensure_ascii=False),
                  g.get("total_score", 0), g.get("grade", "")))


def get_student_grades(tqf5_id):
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM student_grades WHERE tqf5_id=? ORDER BY student_id",
            (tqf5_id,)).fetchall()]
        for r in rows:
            r["score_components"] = json.loads(r.get("score_components", "{}"))
        return rows


def compute_grade_stats(tqf5_id) -> dict:
    """คำนวณสถิติเกรดจากตาราง student_grades"""
    grades = get_student_grades(tqf5_id)
    GRADE_ORDER = ["A", "B+", "B", "C+", "C", "D+", "D", "E",
                   "ไม่สมบูรณ์ (I)", "ผ่าน (P,S)", "ไม่ผ่าน (U)", "W"]
    dist = {g: 0 for g in GRADE_ORDER}
    for s in grades:
        g = s["grade"]
        if g in dist:
            dist[g] += 1
        elif g == "I":
            dist["ไม่สมบูรณ์ (I)"] += 1
        elif g in ("P", "S"):
            dist["ผ่าน (P,S)"] += 1
        elif g == "U":
            dist["ไม่ผ่าน (U)"] += 1
    total = len(grades)
    registered = total
    withdrawn = dist.get("W", 0)
    remaining = total - withdrawn
    pct = {g: round(n / total * 100, 2) if total > 0 else 0.0
           for g, n in dist.items()}
    return {
        "registered": registered,
        "withdrawn": withdrawn,
        "remaining": remaining,
        "dist": dist,
        "pct": pct,
        "total": total,
    }


# ════════════════════════════════════════════════
# Teaching Actual helpers
# ════════════════════════════════════════════════

def replace_teaching_actual(tqf5_id, actual_list):
    with get_conn() as conn:
        conn.execute("DELETE FROM teaching_actual WHERE tqf5_id=?", (tqf5_id,))
        for a in actual_list:
            conn.execute("""
                INSERT INTO teaching_actual
                    (tqf5_id, topic, hours_planned, hours_actual, deviation_reason)
                VALUES (?,?,?,?,?)
            """, (tqf5_id, a.get("topic", ""),
                  a.get("hours_planned", 0), a.get("hours_actual", 0),
                  a.get("deviation_reason", "")))


def get_teaching_actual(tqf5_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM teaching_actual WHERE tqf5_id=? ORDER BY id",
            (tqf5_id,)).fetchall()]


# ════════════════════════════════════════════════
# Dashboard / Summary queries
# ════════════════════════════════════════════════

def get_dashboard_summary():
    """ข้อมูลสรุปสำหรับหน้า Dashboard"""
    with get_conn() as conn:
        total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        total_tqf3   = conn.execute("SELECT COUNT(*) FROM tqf3").fetchone()[0]
        total_tqf5   = conn.execute("SELECT COUNT(*) FROM tqf5").fetchone()[0]
        total_students = conn.execute("SELECT COUNT(*) FROM student_grades").fetchone()[0]

        # รายวิชาล่าสุด
        recent = conn.execute("""
            SELECT c.code, c.name_th, t.semester, t.year,
                   t5.registered_count, t5.grade_dist_json
            FROM tqf3 t
            JOIN courses c ON c.id = t.course_id
            LEFT JOIN tqf5 t5 ON t5.tqf3_id = t.id
            ORDER BY t.year DESC, t.semester DESC
            LIMIT 10
        """).fetchall()

        return {
            "total_courses": total_courses,
            "total_tqf3": total_tqf3,
            "total_tqf5": total_tqf5,
            "total_students": total_students,
            "recent": [dict(r) for r in recent],
        }


def get_course_history(course_code):
    """ประวัติผลการเรียนของรายวิชาข้ามภาค"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT t.semester, t.year, t5.registered_count, t5.remaining_count,
                   t5.withdrawn_count, t5.grade_dist_json, t5.last_updated
            FROM tqf3 t
            JOIN courses c ON c.id = t.course_id
            LEFT JOIN tqf5 t5 ON t5.tqf3_id = t.id
            WHERE c.code = ?
            ORDER BY t.year DESC, t.semester DESC
        """, (course_code,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["grade_dist"] = json.loads(d.get("grade_dist_json") or "{}")
            result.append(d)
        return result


def upsert_curriculum(version: str, name_th: str = "", effective_year: int = 0) -> int:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO curricula (version, name_th, effective_year)
            VALUES (?, ?, ?)
            ON CONFLICT(version) DO UPDATE SET
                name_th=excluded.name_th,
                effective_year=excluded.effective_year
        """, (version, name_th, effective_year))
        row = conn.execute("SELECT id FROM curricula WHERE version=?", (version,)).fetchone()
        return row["id"]


def get_curriculum_by_version(version: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM curricula WHERE version=?", (version,)).fetchone()


def export_to_excel(output_path: str = None):
    """Export ข้อมูลทั้งหมดออกเป็น Excel เพื่อแชร์ให้คนอื่นดู"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    if output_path is None:
        output_path = os.path.join(os.path.dirname(DB_PATH), "tqf_database_view.xlsx")

    HEADER_FILL = PatternFill("solid", start_color="1F4E79")
    HEADER_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    ROW_A = PatternFill("solid", start_color="DEEAF1")
    ROW_B = PatternFill("solid", start_color="FFFFFF")
    NORMAL = Font(name="Arial", size=10)

    def write_sheet(ws, headers, rows, col_widths):
        ws.append(headers)
        for ci in range(1, len(headers)+1):
            c = ws.cell(1, ci)
            c.fill = HEADER_FILL
            c.font = HEADER_FONT
            c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 22
        for ri, row in enumerate(rows, 2):
            ws.append(list(row))
            fill = ROW_A if ri % 2 == 0 else ROW_B
            for ci in range(1, len(headers)+1):
                c = ws.cell(ri, ci)
                c.fill = fill
                c.font = NORMAL
                c.alignment = Alignment(vertical="center", wrap_text=True)
            ws.row_dimensions[ri].height = 20
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

    wb = Workbook()
    with get_conn() as conn:

        # ── Sheet 1: ภาพรวมรายวิชา ──────────────────────────────
        ws1 = wb.active
        ws1.title = "ภาพรวมรายวิชา"
        rows1 = conn.execute("""
            SELECT c.code, c.name_th, c.credits_text,
                   t.semester||'/'||t.year,
                   t.instructor_main,
                   (SELECT COUNT(*) FROM clos cl WHERE cl.tqf3_id=t.id),
                   COALESCE(t5.registered_count, '-'),
                   COALESCE(t5.remaining_count, '-'),
                   COALESCE(t5.withdrawn_count, '-')
            FROM courses c
            JOIN tqf3 t ON t.course_id = c.id
            LEFT JOIN tqf5 t5 ON t5.tqf3_id = t.id
            ORDER BY c.code
        """).fetchall()
        write_sheet(ws1,
            ["รหัสวิชา","ชื่อวิชา","หน่วยกิต","ภาค/ปี","อาจารย์ผู้รับผิดชอบ","CLOs","ลงทะเบียน","คงอยู่","ถอน"],
            rows1, [12, 30, 10, 8, 28, 7, 10, 8, 8])

        # ── Sheet 2: CLOs ────────────────────────────────────────
        ws2 = wb.create_sheet("CLOs")
        rows2 = conn.execute("""
            SELECT c.code, c.name_th, cl.clo_number, cl.description
            FROM clos cl
            JOIN tqf3 t ON t.id = cl.tqf3_id
            JOIN courses c ON c.id = t.course_id
            ORDER BY c.code, cl.clo_number
        """).fetchall()
        write_sheet(ws2,
            ["รหัสวิชา","ชื่อวิชา","CLO#","คำอธิบาย"],
            rows2, [12, 24, 6, 70])

        # ── Sheet 3: การกระจายเกรด ───────────────────────────────
        ws3 = wb.create_sheet("การกระจายเกรด")
        grade_keys = ["A","B+","B","C+","C","D+","D","E","W"]
        rows3 = conn.execute("""
            SELECT c.code, c.name_th,
                   t5.registered_count, t5.remaining_count, t5.withdrawn_count,
                   t5.grade_dist_json
            FROM tqf5 t5
            JOIN tqf3 t ON t.id = t5.tqf3_id
            JOIN courses c ON c.id = t.course_id
            ORDER BY c.code
        """).fetchall()
        data3 = []
        for r in rows3:
            dist = json.loads(r[5]) if r[5] else {}
            data3.append(list(r[:5]) + [dist.get(g, 0) for g in grade_keys])
        write_sheet(ws3,
            ["รหัสวิชา","ชื่อวิชา","ลงทะเบียน","คงอยู่","ถอน"] + grade_keys,
            data3, [12, 28, 10, 8, 8] + [6]*len(grade_keys))

        # ── Sheet 4: รายชื่อนักศึกษา ─────────────────────────────
        ws4 = wb.create_sheet("รายชื่อนักศึกษา")
        rows4 = conn.execute("""
            SELECT c.code, sg.student_id, sg.student_name, sg.total_score, sg.grade
            FROM student_grades sg
            JOIN tqf5 t5 ON t5.id = sg.tqf5_id
            JOIN tqf3 t ON t.id = t5.tqf3_id
            JOIN courses c ON c.id = t.course_id
            ORDER BY c.code, sg.student_id
        """).fetchall()
        write_sheet(ws4,
            ["รหัสวิชา","รหัสนักศึกษา","ชื่อ-สกุล","คะแนนรวม","เกรด"],
            rows4, [12, 18, 36, 12, 8])

    wb.save(output_path)
    print(f"[Excel] Export → {output_path}")
    return output_path


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
