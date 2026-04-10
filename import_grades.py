"""
import_grades.py — Parse ไฟล์เกรด (.doc/.docx/.pdf) แล้ว import เข้า database
รองรับรูปแบบ: "seminar สิทธิโชค.docx", "calculus สิทธิโชค.docx", *.pdf ฯลฯ
"""

import re
import os
import sys
import subprocess
import tempfile
import shutil
from docx import Document
import database as db


# ════════════════════════════════════════════════
# FILE CONVERSION: .doc / .rtf → .docx
# ════════════════════════════════════════════════

def parse_rtf_tables(filepath: str) -> list:
    """
    Parse ตารางจากไฟล์ RTF/.doc โดยตรง ไม่ต้องพึ่ง LibreOffice
    คืน list ของ rows, แต่ละ row คือ list ของ cell text
    """
    with open(filepath, "rb") as f:
        raw = f.read()

    # decode — ไฟล์ไทยมักเป็น cp874
    for enc in ("cp874", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            text = raw.decode("latin-1", errors="ignore")

    # ── strip RTF control words ──────────────────────────────────
    def rtf_to_text(s):
        # ลบ Unicode escape \uN
        s = re.sub(r'\\u-?\d+\??', '', s)
        # ลบ binary data \binN
        s = re.sub(r'\\bin\d+\s?', '', s)
        # ลบ hex escape \'XX แต่แปลงเป็น char ก่อน
        def hex_to_char(m):
            try:
                return bytes([int(m.group(1), 16)]).decode("cp874", errors="ignore")
            except Exception:
                return ""
        s = re.sub(r"\\'([0-9a-fA-F]{2})", hex_to_char, s)
        # ลบ control words
        s = re.sub(r'\\[a-zA-Z]+\-?\d*\s?', '', s)
        # ลบ group markers
        s = re.sub(r'[{}]', '', s)
        return s.strip()

    # ── แยก cell โดยใช้ \cell เป็น delimiter ────────────────────
    # normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    rows = []
    current_row = []

    # split ด้วย \cell และ \row
    parts = re.split(r'(\\cell\b|\\row\b)', text)
    for i, part in enumerate(parts):
        if part == r'\cell':
            # เนื้อหาของ cell คือ part ก่อนหน้า
            if i > 0:
                cell_text = rtf_to_text(parts[i-1])
                cell_text = " ".join(cell_text.split())
                current_row.append(cell_text)
        elif part == r'\row':
            if current_row:
                rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    return rows


def ensure_docx(filepath: str) -> str:
    """
    ถ้าเป็น .docx คืน path เดิม
    ถ้าเป็น .doc/.rtf: ลอง LibreOffice ก่อน ถ้าไม่มีให้ใช้ parse_rtf_tables แทน
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".docx":
        return filepath

    # ลอง LibreOffice (ถ้ามี)
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    # Windows path fallbacks
    if not lo:
        for candidate in [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]:
            if os.path.exists(candidate):
                lo = candidate
                break

    if lo:
        try:
            out_dir = tempfile.mkdtemp()
            result = subprocess.run(
                [lo, "--headless", "--convert-to", "docx", filepath, "--outdir", out_dir],
                capture_output=True, text=True, timeout=60
            )
            basename = os.path.splitext(os.path.basename(filepath))[0] + ".docx"
            converted = os.path.join(out_dir, basename)
            if result.returncode == 0 and os.path.exists(converted):
                return converted
        except Exception:
            pass  # fallback ด้านล่าง

    # ถ้าไม่มี LibreOffice — return None เพื่อให้ parse RTF โดยตรง
    return None


# ════════════════════════════════════════════════
# GRADE CONFIG
# ════════════════════════════════════════════════

VALID_GRADES = {"A", "B+", "B", "C+", "C", "D+", "D", "E", "W", "I", "P", "S", "U"}

GRADE_THRESHOLDS_DEFAULT = {
    "A":  (80, 101),
    "B+": (75, 80),
    "B":  (70, 75),
    "C+": (65, 70),
    "C":  (60, 65),
    "D+": (55, 60),
    "D":  (50, 55),
    "E":  (0,  50),
}


def clean(text: str) -> str:
    return " ".join(str(text).split()).strip()


def is_student_id(text: str) -> bool:
    """รหัสนักศึกษา — ตัวเลข 10-13 หลัก"""
    return bool(re.match(r"^\d{10,13}$", clean(text)))


def parse_score(text: str):
    """แปลง text เป็น float, คืน None ถ้าไม่ใช่ตัวเลข"""
    t = clean(text).replace(",", "")
    if not t or t in ("-", "–", "—", "\\-"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


# ════════════════════════════════════════════════
# PARSE GRADE FILE
# ════════════════════════════════════════════════

def _extract_text_from_pdf(filepath: str) -> str:
    """ดึง text ดิบจาก PDF ใช้ pdfplumber"""
    try:
        import pdfplumber
        lines = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages[:5]:  # อ่านแค่ 5 หน้าแรกพอสำหรับหาข้อมูลวิชา
                txt = page.extract_text() or ""
                lines.append(txt)
                # ดึง text จาก tables ด้วย
                for tbl in (page.extract_tables() or []):
                    for row in tbl:
                        lines.append(" ".join(str(c) for c in row if c))
        return "\n".join(lines)
    except Exception:
        return ""


def _extract_pdf_grade_tables(filepath: str) -> list:
    """
    ดึงตารางทั้งหมดจาก PDF
    คืน list ของ rows (เหมือนที่ parse_grade_docx ใช้)
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("ต้องติดตั้ง pdfplumber: pip install pdfplumber")

    all_rows = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            # ลอง lines strategy ก่อน
            tbl_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_tolerance": 5,
            }
            tables = page.extract_tables(tbl_settings)
            # fallback: text strategy
            if not tables:
                tables = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "min_words_vertical": 3,
                })

            for tbl in (tables or []):
                cleaned = []
                for row in tbl:
                    cr = [" ".join(str(c).split()) if c else "" for c in row]
                    if any(cr):
                        cleaned.append(cr)
                if len(cleaned) >= 2:
                    all_rows.append(cleaned)
    return all_rows


def extract_course_info_from_file(filepath: str) -> dict:
    """
    ดึงรหัสวิชา / ภาคเรียน / ปีการศึกษา จากไฟล์เกรด
    รองรับ .doc/.rtf (อ่าน raw text), .docx (python-docx), .pdf (pdfplumber)
    คืน dict: {code, semester, year}  — ค่าอาจเป็น None ถ้าหาไม่เจอ
    """
    info = {"code": None, "semester": None, "year": None}
    ext = os.path.splitext(filepath)[1].lower()

    # อ่าน text ดิบ
    raw = ""
    if ext == ".pdf":
        raw = _extract_text_from_pdf(filepath)
    elif ext in (".doc", ".rtf"):
        try:
            with open(filepath, "rb") as f:
                raw = f.read().decode("cp874", errors="ignore")
        except Exception:
            pass
    else:
        # .docx — อ่าน paragraph ทั้งหมด
        try:
            doc = Document(filepath)
            raw = "\n".join(p.text for p in doc.paragraphs)
            # รวม text จากตารางหัวด้วย
            for table in doc.tables[:3]:
                for row in table.rows[:5]:
                    raw += " ".join(c.text for c in row.cells) + "\n"
        except Exception:
            pass

    # ── หารหัสวิชา เช่น SMAC001, SMA0901 ────────────────
    m = re.search(r'\b([A-Z]{2,6}\d{3,6}[A-Z]?)', raw)
    if m:
        info["code"] = m.group(1)

    # ── หาภาค/ปี เช่น "2/2568" หรือ "ภาคการศึกษาที่ 2/2568" ─
    m2 = re.search(r'(\d)/(\d{4})', raw)
    if m2:
        info["semester"] = int(m2.group(1))
        info["year"]     = int(m2.group(2))
    else:
        m3 = re.search(r'ภาค(?:การศึกษา)?(?:ที่)?\s*(\d).*?(\d{4})', raw)
        if m3:
            info["semester"] = int(m3.group(1))
            info["year"]     = int(m3.group(2))

    return info


def parse_grade_docx(filepath: str) -> dict:
    """
    Parse ไฟล์เกรด docx
    คืน dict:
      {
        students: [{student_id, student_name, section, score_components, total_score, grade}, ...],
        grade_dist: {A:n, B+:n, ...},
        thresholds: {A:(80,101), ...},
        section: "66045.041"
      }
    """
    ext = os.path.splitext(filepath)[1].lower()
    students = []
    grade_dist = {}
    thresholds = {}
    section = ""

    # ── เลือกวิธีอ่านตาราง ───────────────────────────────────────
    if ext == ".pdf":
        # PDF — ใช้ pdfplumber
        all_rows = _extract_pdf_grade_tables(filepath)
    elif ext == ".docx":
        doc = Document(filepath)
        all_rows = []
        for table in doc.tables:
            all_rows.append([[clean(c.text) for c in row.cells] for row in table.rows])
    else:
        # .doc / .rtf — parse RTF โดยตรง (ไม่ต้อง LibreOffice)
        docx_path = ensure_docx(filepath)
        if docx_path:
            doc = Document(docx_path)
            all_rows = []
            for table in doc.tables:
                all_rows.append([[clean(c.text) for c in row.cells] for row in table.rows])
        else:
            # fallback: parse RTF table
            rtf_rows = parse_rtf_tables(filepath)
            # de-duplicate adjacent identical cells (merged cells)
            cleaned = []
            for row in rtf_rows:
                dedup = list(dict.fromkeys(c for c in row if c))
                if dedup:
                    cleaned.append(dedup)
            all_rows = [cleaned]  # treat as single table

    for rows in all_rows:
        if not rows:
            continue

        # ── ตรวจว่าเป็นตารางรายชื่อนักศึกษา ────────────────────
        # ต้องมีรหัสนักศึกษา (10+ หลัก) ในคอลัมน์ใดคอลัมน์หนึ่ง
        has_student_rows = any(
            any(is_student_id(cell) for cell in row)
            for row in rows[1:6]
        )

        if has_student_rows:
            # หา column index สำหรับ: รหัส, ชื่อ, คะแนน..., เกรด, section
            header = rows[0] if rows else []
            id_col = name_col = grade_col = section_col = -1
            score_cols = []

            for i, h in enumerate(header):
                hl = h.lower()
                if is_student_id(h) or "รหัส" in h:
                    id_col = i
                elif any(kw in h for kw in ["ชื่อ", "name"]):
                    name_col = i
                elif h in VALID_GRADES or any(kw in hl for kw in ["เกรด", "grade", "ระดับ"]):
                    grade_col = i
                elif any(kw in hl for kw in ["section", "กลุ่ม", "สาขา", "คณะ"]):
                    section_col = i
                elif any(kw in hl for kw in ["คะแนน", "score", "รวม"]):
                    score_cols.append(i)

            # fallback: detect by content
            for row in rows[1:5]:
                for i, cell in enumerate(row):
                    if is_student_id(cell) and id_col < 0:
                        id_col = i
                    if grade_col < 0 and cell in VALID_GRADES:
                        grade_col = i

            if id_col < 0:
                continue  # ไม่ใช่ตารางนักศึกษา

            # ถ้ายังไม่รู้ column ให้ลอง auto-detect
            if name_col < 0:
                name_col = id_col + 1
            if grade_col < 0:
                # เกรดมักอยู่ก่อน column สุดท้าย
                grade_col = len(rows[0]) - 2 if len(rows[0]) > 2 else len(rows[0]) - 1

            for row in rows:
                if len(row) <= id_col:
                    continue
                sid = row[id_col]
                if not is_student_id(sid):
                    continue

                name = row[name_col] if name_col < len(row) else ""
                grade = row[grade_col] if grade_col < len(row) else ""
                grade = clean(grade).upper()
                if grade not in VALID_GRADES:
                    # ลองหาเกรดใน row
                    for cell in row:
                        if clean(cell).upper() in VALID_GRADES:
                            grade = clean(cell).upper()
                            break

                # section
                if section_col >= 0 and section_col < len(row):
                    s = row[section_col]
                    if s and len(s) > 3:
                        section = s

                # คะแนน
                scores = {}
                numeric_cols = []
                for i, cell in enumerate(row):
                    if i in (id_col, name_col, grade_col, section_col):
                        continue
                    v = parse_score(cell)
                    if v is not None and v >= 0:
                        numeric_cols.append((i, v))

                # assign parts
                if len(numeric_cols) >= 3:
                    # สมมติ: ส่วน1, ส่วน2, รวม
                    scores["part1"] = numeric_cols[0][1]
                    scores["part2"] = numeric_cols[1][1]
                    total = numeric_cols[-1][1]
                elif len(numeric_cols) == 2:
                    scores["part1"] = numeric_cols[0][1]
                    total = numeric_cols[-1][1]
                elif len(numeric_cols) == 1:
                    total = numeric_cols[0][1]
                else:
                    total = 0

                students.append({
                    "student_id": sid,
                    "student_name": name,
                    "section": section,
                    "score_components": scores,
                    "total_score": total,
                    "grade": grade,
                })

        # ── ตาราง grade distribution (สรุปด้านล่าง) ─────────────
        # มักมีรูปแบบ: เกรด | ช่วงเกรด | จำนวน | %
        is_dist_table = any(
            any(g in cell for cell in row for g in ["A", "B+", "B"])
            and any(kw in " ".join(row) for kw in ["จำนวน", "รวม", "%"])
            for row in rows
        )
        if is_dist_table and not students:  # เป็นตาราง summary
            for row in rows:
                if len(row) < 2:
                    continue
                grade_cell = clean(row[0])
                if grade_cell in VALID_GRADES:
                    count = None
                    for cell in row[1:]:
                        v = parse_score(cell)
                        if v is not None and v == int(v):
                            count = int(v)
                            break
                    if count is not None:
                        grade_dist[grade_cell] = count

                    # threshold
                    for cell in row[1:]:
                        m = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*[>]?\s*(\d+(?:\.\d+)?)", cell)
                        if m:
                            lo, hi = float(m.group(1)), float(m.group(2))
                            thresholds[grade_cell] = (lo, hi)
                            break
                        m2 = re.search(r"(\d+(?:\.\d+)?)\s*->>", cell)
                        if m2:
                            thresholds[grade_cell] = (float(m2.group(1)), 101)
                            break

    # คำนวณ grade_dist จาก students ถ้าไม่มีตาราง summary
    if not grade_dist and students:
        for s in students:
            g = s["grade"]
            grade_dist[g] = grade_dist.get(g, 0) + 1

    course_info = extract_course_info_from_file(filepath)

    # ── auto-detect section type จากรายชื่อนักศึกษา ─────────────────────────
    # section code ที่ขึ้นต้นด้วย P (เช่น P01, P02) = เปิดพิเศษ
    # section code ที่ขึ้นต้นด้วย N (เช่น N01, N02) = เปิดปกติ
    detected_special = False
    for s in students:
        sec = (s.get("section") or "").strip().upper()
        # จับ pattern: P0x, P1, P01, หรือ section code ที่มีตัว P นำ
        if re.match(r"^P\d", sec):
            detected_special = True
            break
        elif re.match(r"^N\d", sec):
            detected_special = False
            break

    return {
        "students": students,
        "grade_dist": grade_dist,
        "thresholds": thresholds or GRADE_THRESHOLDS_DEFAULT,
        "section": section,
        "course_info": course_info,
        "is_special_detected": detected_special,
    }


# ════════════════════════════════════════════════
# IMPORT TO DATABASE
# ════════════════════════════════════════════════

def import_grades(filepath: str, course_code: str,
                  semester: int, year: int, is_special: bool = False) -> dict:
    """
    Import ไฟล์เกรดเข้า database
    - course_code: รหัสวิชา e.g. "SMA0901"
    - semester: 1 หรือ 2
    - year: ปีการศึกษา e.g. 2568
    - is_special: True = เปิดพิเศษ (P0x), False = เปิดปกติ (N0x)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ไม่พบไฟล์: {filepath}")

    print(f"[GRADE] Reading: {filepath}")
    data = parse_grade_docx(filepath)
    students = data["students"]
    grade_dist = data["grade_dist"]

    print(f"  นักศึกษา   : {len(students)} คน")
    print(f"  Grade dist : {grade_dist}")

    db.init_db()

    # หา course — ถ้ายังไม่มีให้สร้าง record เปล่าไว้ก่อน
    course = db.get_course_by_code(course_code)
    if not course:
        print(f"  [INFO] ไม่พบ {course_code} ในระบบ — สร้าง record เปล่าไว้ก่อน (import มคอ.3 ทีหลังเพื่อเติมข้อมูล)")
        course_id = db.upsert_course(
            code=course_code,
            name_th="", name_en="", credits_text="",
            credit_lecture=0, credit_lab=0, credit_self=0,
            prerequisite="", course_type="",
            description_th="", description_en="",
            faculty="", department="",
        )
    else:
        course_id = course["id"]

    # หา tqf3 — ถ้ายังไม่มีให้สร้าง record เปล่าไว้ก่อน
    is_special_int = int(bool(is_special))
    tqf3_list = db.get_all_tqf3(course_id)
    tqf3 = next(
        (t for t in tqf3_list
         if t["semester"] == semester and t["year"] == year
         and int(t.get("is_special", 0)) == is_special_int),
        None
    )
    if not tqf3:
        label = "พิเศษ" if is_special else "ปกติ"
        print(f"  [INFO] ไม่พบ มคอ.3 ภาค {semester}/{year} ({label}) — สร้าง record เปล่าไว้ก่อน")
        tqf3_id = db.upsert_tqf3(
            course_id=course_id,
            semester=semester, year=year,
            instructor_main="", instructors=[],
            location="", objectives="",
            source_file="", is_special=is_special_int,
        )
    else:
        tqf3_id = tqf3["id"]

    # สร้าง TQF5 ถ้ายังไม่มี
    tqf5_id = db.get_or_create_tqf5(tqf3_id)

    # บันทึกเกรดรายคน
    db.replace_student_grades(tqf5_id, students)

    # คำนวณสถิติแล้วบันทึก
    stats = db.compute_grade_stats(tqf5_id)
    db.update_tqf5(tqf5_id,
        registered_count=stats["registered"],
        remaining_count=stats["remaining"],
        withdrawn_count=stats["withdrawn"],
        grade_dist=stats["dist"],
    )

    # สร้าง teaching_actual จาก teaching_plan (hours_actual = 0 ให้อาจารย์กรอกทีหลัง)
    plan = db.get_teaching_plan(tqf3_id)
    if plan:
        actual = [{"topic": p["topic"],
                   "hours_planned": p["hours_planned"],
                   "hours_actual": p["hours_planned"],  # default = ตามแผน
                   "deviation_reason": ""} for p in plan]
        db.replace_teaching_actual(tqf5_id, actual)

    print(f"[GRADE] Saved → tqf5_id={tqf5_id}")
    print(f"  ลงทะเบียน {stats['registered']} | คงอยู่ {stats['remaining']} | ถอน {stats['withdrawn']}")

    return {
        "success": True,
        "tqf5_id": tqf5_id,
        "students_count": len(students),
        "stats": stats,
    }


# ════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python import_grades.py <grade_file.docx> <course_code> <semester> <year>")
        print("Example: python import_grades.py 'seminar สิทธิโชค.docx' SMA0901 2 2568")
        sys.exit(1)
    result = import_grades(
        filepath=sys.argv[1],
        course_code=sys.argv[2],
        semester=int(sys.argv[3]),
        year=int(sys.argv[4]),
    )
    print("\nResult:", result)
