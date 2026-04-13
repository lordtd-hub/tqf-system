"""
Generate TQF3 documents by filling the existing Word template.
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
import sys
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_THIS_DIR = Path(__file__).parent
TEMPLATE_CANDIDATES = [
    _THIS_DIR / "templates" / "เนเธเธเธเธญเธฃเนเธก เธกเธเธญ. 3.docx",
    _THIS_DIR / "เนเธเธเธเธญเธฃเนเธก เธกเธเธญ. 3.docx",
    _THIS_DIR.parent / "เนเธเธเธเธญเธฃเนเธก เธกเธเธญ. 3.docx",
]


def find_template() -> Path:
    for path in TEMPLATE_CANDIDATES:
        if path.exists():
            return path
    for base_dir in (_THIS_DIR / "templates", _THIS_DIR, _THIS_DIR.parent):
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.glob("*.docx")):
            name = path.name.lower()
            if "3" in name and ("tqf" in name or "template" in name or "มคอ" in path.name):
                return path
    raise FileNotFoundError(
        "เนเธกเนเธเธเนเธเธฅเน 'เนเธเธเธเธญเธฃเนเธก เธกเธเธญ. 3.docx' เนเธเนเธเธฅเน€เธ”เธญเธฃเน templates เธเธญเธเนเธเธฃเน€เธเนเธเธ•เน"
    )


def _ensure_list(value):
    if value in (None, "", "[]"):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except Exception:
            return []
        return loaded if isinstance(loaded, list) else []
    return []


def _safe_text(value, fallback=""):
    text = "" if value is None else str(value).strip()
    return text or fallback


def _format_pct(value, default=50.0):
    try:
        return f"{float(value):.0f}%"
    except Exception:
        return f"{float(default):.0f}%"


def _paragraph_text(paragraph) -> str:
    return (paragraph.text or "").strip()


def _remove_paragraph(paragraph):
    element = paragraph._p
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def _set_paragraph_text(paragraph, text: str):
    if not paragraph.runs:
        paragraph.add_run("")
    paragraph.runs[0].text = text
    for run in paragraph.runs[1:]:
        run.text = ""


def _set_cell_text(cell, text: str):
    if not cell.paragraphs:
        cell.add_paragraph("")
    _set_paragraph_text(cell.paragraphs[0], text)
    for para in cell.paragraphs[1:]:
        _set_paragraph_text(para, "")


def _insert_paragraph_after(paragraph, text: str) -> Paragraph:
    new_element = copy.deepcopy(paragraph._p)
    paragraph._p.addnext(new_element)
    new_paragraph = Paragraph(new_element, paragraph._parent)
    _set_paragraph_text(new_paragraph, text)
    return new_paragraph


def _append_row_from_template(table, row_template):
    table._tbl.append(copy.deepcopy(row_template))
    return table.rows[-1]


def _clear_rows(table, keep_rows: int):
    for idx in range(len(table.rows) - 1, keep_rows - 1, -1):
        table._tbl.remove(table.rows[idx]._tr)


def _find_paragraph_index(doc, predicate) -> int:
    for idx, paragraph in enumerate(doc.paragraphs):
        if predicate(_paragraph_text(paragraph)):
            return idx
    raise ValueError("เนเธกเนเธเธ paragraph เธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเนเธ template เธกเธเธญ.3")


def _replace_block_between(doc, intro_predicate, end_predicate, lines):
    intro_idx = _find_paragraph_index(doc, intro_predicate)
    end_idx = _find_paragraph_index(doc, end_predicate)
    existing = doc.paragraphs[intro_idx + 1:end_idx]

    # เธเธณ intro paragraph เธเนเธญเธ remove เน€เธเธทเนเธญเนเธเน addnext เนเธ—เธ addprevious
    # (addprevious เธกเธตเธเธฑเธเธซเธฒเธเธฑเธ Word XML เธเธฒเธเนเธเธฃเธเธชเธฃเนเธฒเธ)
    intro_para = doc.paragraphs[intro_idx]

    if existing:
        template_element = copy.deepcopy(existing[0]._p)
        for paragraph in reversed(existing):
            _remove_paragraph(paragraph)
    else:
        template_element = copy.deepcopy(doc.paragraphs[intro_idx]._p)

    # เนเธ—เธฃเธ lines เธ—เธตเธฅเธฐเธเธฃเธฃเธ—เธฑเธ” เธ•เนเธญเธเธฒเธ intro เนเธ”เธขเนเธเน addnext
    current = intro_para._p
    for line in lines:
        new_element = copy.deepcopy(template_element)
        current.addnext(new_element)
        new_paragraph = Paragraph(new_element, intro_para._parent)
        _set_paragraph_text(new_paragraph, line)
        current = new_element


_GARBAGE_INSTRUCTOR_PREFIXES = (
    "เธ เธฒเธเธเธเธงเธ", "เนเธเธเธเธฃเธฐเน€เธกเธดเธ", "เน€เธเธ“เธ‘เนเธเธฒเธฃเนเธซเนเธเธฐเนเธเธ",
    "เธซเธกเธฒเธขเน€เธซเธ•เธธ", "เธ•เธฑเธงเธญเธขเนเธฒเธ", "เธเธฅเธเธฒเธฃเน€เธฃเธตเธขเธ",
)


def _is_valid_instructor_name(name: str) -> bool:
    """เธเธฃเธญเธเธเธทเนเธญเธญเธฒเธเธฒเธฃเธขเนเธ—เธตเนเนเธกเนเธ–เธนเธเธ•เนเธญเธ (เน€เธเนเธ เธซเธฑเธงเธเนเธญเธ เธฒเธเธเธเธงเธเธ—เธตเนเธ–เธนเธ import เธเธดเธ”)"""
    name = _safe_text(name)
    if not name:
        return False
    return not any(name.startswith(prefix) for prefix in _GARBAGE_INSTRUCTOR_PREFIXES)


def _clean_numbering_prefix(text: str) -> str:
    stripped = _safe_text(text)
    if not stripped:
        return ""
    parts = stripped.split(". ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1].strip()
    return stripped


def _get_plo_code(plo) -> str:
    return _safe_text(plo.get("plo_code") or plo.get("plo_number"))


def _build_plo_lookup(plos):
    lookup = {}
    for plo in plos:
        code = _get_plo_code(plo)
        number = _safe_text(plo.get("plo_number"))
        if code:
            lookup[code] = plo
        if number:
            lookup[number] = plo
    return lookup


def _mapped_plos_for_clo(clo, plo_lookup):
    mapped = []
    for raw in _ensure_list(clo.get("plo_mapping")):
        key = _safe_text(raw)
        plo = plo_lookup.get(key)
        if plo is not None:
            mapped.append(plo)
        elif key:
            mapped.append({"plo_number": key, "plo_code": key, "description": ""})
    return mapped


def _join_unique(values, fallback="-"):
    seen = set()
    ordered = []
    for value in values:
        text = _safe_text(value)
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return "\n".join(ordered) if ordered else fallback


def _related_assessments(assessments, clo_numbers):
    target = {int(num) for num in clo_numbers if str(num).isdigit()}
    matched = []
    for assessment in assessments:
        mapped = {int(num) for num in _ensure_list(assessment.get("clo_mapping")) if str(num).isdigit()}
        if not target or not mapped or target.intersection(mapped):
            matched.append(assessment)
    return matched


def _build_objective_lines(clos, plo_lookup):
    if not clos:
        return ["5.1.1 เธขเธฑเธเนเธกเนเธกเธตเธเนเธญเธกเธนเธฅเธเธฅเธฅเธฑเธเธเนเธเธฒเธฃเน€เธฃเธตเธขเธเธฃเธนเนเธฃเธฒเธขเธงเธดเธเธฒ"]

    lines = []
    for idx, clo in enumerate(clos, start=1):
        clo_number = _safe_text(clo.get("clo_number"), str(idx))
        mapped_plos = _mapped_plos_for_clo(clo, plo_lookup)
        suffix_bits = []
        if mapped_plos:
            suffix_bits.append(", ".join(f"PLO {_get_plo_code(plo)}" for plo in mapped_plos))
        suffix_bits.append(f"เธชเธฑเธกเธเธฑเธเธเนเธเธฑเธ CLO{clo_number}")
        suffix = f" ({'; '.join(suffix_bits)})" if suffix_bits else ""
        lines.append(f"5.1.{idx} {_safe_text(clo.get('description'), '-')}{suffix}")
    return lines


def _build_plo_rows(plos, clos, assessments):
    plo_lookup = _build_plo_lookup(plos)
    grouped = []

    for plo in plos:
        code = _get_plo_code(plo)
        related = [
            clo for clo in clos
            if any(_get_plo_code(mapped) == code for mapped in _mapped_plos_for_clo(clo, plo_lookup))
        ]
        if related:
            grouped.append((code, related))

    unmapped = [clo for clo in clos if not _mapped_plos_for_clo(clo, plo_lookup)]
    if unmapped:
        grouped.append(("เนเธกเนเธฃเธฐเธเธธ", unmapped))

    if not grouped and clos:
        grouped.append(("เธขเธฑเธเนเธกเน map", clos))

    rows = []
    for plo_code, related_clos in grouped:
        clo_numbers = [clo.get("clo_number") for clo in related_clos]
        related_assessments = _related_assessments(assessments, clo_numbers)
        criteria = []
        for clo in related_clos:
            criteria.append(f"เธเนเธฒเธ {_format_pct(clo.get('pass_threshold_pct', 50.0))}")
        for assessment in related_assessments:
            criteria.append(_safe_text(assessment.get("eval_criteria")))
            if not assessment.get("eval_criteria"):
                criteria.append(f"เธเนเธฒเธ {_format_pct(assessment.get('pass_threshold', 50.0))}")

        rows.append((
            f"PLO{plo_code}" if plo_code not in {"เนเธกเนเธฃเธฐเธเธธ", "เธขเธฑเธเนเธกเน map"} else plo_code,
            _join_unique(
                f"CLO{_safe_text(clo.get('clo_number'))} {_safe_text(clo.get('description'), '-')}"
                for clo in related_clos
            ),
            _join_unique(clo.get("teaching_strategy") for clo in related_clos),
            _join_unique(clo.get("assessment_method") for clo in related_clos),
            _join_unique(assessment.get("name") for assessment in related_assessments),
            _join_unique(criteria),
        ))
    return rows or [("เธขเธฑเธเนเธกเนเธกเธตเธเนเธญเธกเธนเธฅ", "-", "-", "-", "-", "-")]


def _build_clo_label_map(clos):
    return {
        int(clo["clo_number"]): f"CLO{clo['clo_number']} {_safe_text(clo.get('description'), '-')}"
        for clo in clos
        if str(clo.get("clo_number", "")).isdigit()
    }


def _format_assessment_label(assessment):
    name = _safe_text(assessment.get("name"), "-")
    score = assessment.get("full_score")
    score_text = ""
    try:
        if score is not None:
            score_text = f" ({float(score):.0f} เธเธฐเนเธเธ)"
    except Exception:
        score_text = ""
    criteria = _safe_text(assessment.get("eval_criteria"))
    return f"{name}{score_text}" if not criteria else f"{name}{score_text}\n{criteria}"


def _course_faculty_text(course, fallback):
    parts = [_safe_text(course.get("faculty")), _safe_text(course.get("department"))]
    joined = " ".join(part for part in parts if part)
    return joined or fallback


def _hours_summary(course, teaching_plan):
    if teaching_plan:
        theory = sum(float(item.get("hours_theory", 0) or 0) for item in teaching_plan)
        practice = sum(float(item.get("hours_practice", 0) or 0) for item in teaching_plan)
        self_study = sum(float(item.get("hours_self", 0) or 0) for item in teaching_plan)
    else:
        theory = float(course.get("credit_lecture", 0) or 0) * 15
        practice = float(course.get("credit_lab", 0) or 0) * 15
        self_study = float(course.get("credit_self", 0) or 0) * 15
    total = theory + practice + self_study
    return [str(int(theory)), str(int(practice)), str(int(self_study)), str(int(total))]


def load_data_for_tqf3(
    course_id: int = None,
    semester: int = None,
    year: int = None,
    tqf3_id: int = None,
) -> dict:
    import database as db

    db.init_db()
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row

    if tqf3_id is not None:
        row = conn.execute(
            """
            SELECT t.*, c.*, cu.version AS cur_ver, cu.name_th AS cur_name
            FROM tqf3 t
            JOIN courses c ON c.id = t.course_id
            LEFT JOIN curricula cu ON cu.id = c.curriculum_id
            WHERE t.id = ?
            """,
            (tqf3_id,),
        ).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"เนเธกเนเธเธ tqf3 id={tqf3_id}")

        course = dict(row)
        course_id = row["course_id"]
        semester = row["semester"]
        year = row["year"]
        curriculum_id = row["curriculum_id"]

        clos = db.get_clos(tqf3_id) or db.get_course_clos(course_id)
        assessments = db.get_assessments(tqf3_id) or db.get_course_assessments(course_id)
        teaching_plan = db.get_teaching_plan(tqf3_id) or db.get_course_teaching_plan(course_id)
        staff = db.get_tqf3_staff(tqf3_id)
        if not staff:
            if course.get("instructor_main"):
                staff.append({"role": "committee", "seq": 0, "name": course["instructor_main"]})
            for idx, name in enumerate(_ensure_list(course.get("instructors_json")), 1):
                if _is_valid_instructor_name(name):
                    staff.append({"role": "instructor", "seq": idx, "name": name})
    else:
        if course_id is None or semester is None or year is None:
            conn.close()
            raise ValueError("เธ•เนเธญเธเธฃเธฐเธเธธ course_id, semester, year เธซเธฃเธทเธญ tqf3_id")

        row = conn.execute(
            """
            SELECT c.*, cu.version AS cur_ver, cu.name_th AS cur_name
            FROM courses c
            LEFT JOIN curricula cu ON cu.id = c.curriculum_id
            WHERE c.id = ?
            """,
            (course_id,),
        ).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"เนเธกเนเธเธเธงเธดเธเธฒ id={course_id}")

        course = dict(row)
        curriculum_id = row["curriculum_id"]
        clos = db.get_course_clos(course_id)
        assessments = db.get_course_assessments(course_id)
        teaching_plan = db.get_course_teaching_plan(course_id)
        staff = []

    plos = db.get_plos(curriculum_id) if curriculum_id else []
    resources = db.get_course_resources(course_id)
    conn.close()

    return {
        "course": course,
        "semester": semester,
        "year": year,
        "plos": [dict(p) for p in plos],
        "clos": [dict(c) for c in clos],
        "assessments": [dict(a) for a in assessments],
        "teaching_plan": [dict(t) for t in teaching_plan],
        "resources": [dict(r) for r in resources],
        "staff": [dict(s) for s in staff],
        "tqf3_id": tqf3_id,
    }


def fill_tqf3(template_path: str, data: dict, output_path: str) -> str:
    doc = Document(template_path)

    course = data["course"]
    code = _safe_text(course.get("code"), "UNKNOWN")
    name_th = _safe_text(course.get("name_th"), "-")
    name_en = _safe_text(course.get("name_en"), "-")
    credits = _safe_text(
        course.get("credits_text"),
        f"{course.get('credit_lecture', 0)}({course.get('credit_lecture', 0)}-"
        f"{course.get('credit_lab', 0)}-{course.get('credit_self', 0)})",
    )
    desc_th = _safe_text(course.get("description_th"), "-")
    desc_en = _safe_text(course.get("description_en"), name_en)
    curriculum_name = _safe_text(course.get("cur_name"), "-")
    course_type = _safe_text(course.get("course_type"), "-")

    if len(doc.paragraphs) >= 5:
        _set_paragraph_text(doc.paragraphs[3], f"{code} {name_th}".strip())
        _set_paragraph_text(
            doc.paragraphs[4],
            f"ภาคเรียนที่ {data['semester']} ปีการศึกษา {data['year']}",
        )

    table0 = doc.tables[0]
    faculty_fallback = _safe_text(table0.cell(1, 0).text, "-")
    _set_cell_text(table0.cell(1, 0), f"เธเธ“เธฐ/เธชเธฒเธเธฒ/เธงเธดเธเธฒเน€เธญเธ {_course_faculty_text(course, faculty_fallback)}")
    _set_cell_text(
        table0.cell(2, 0),
        f"1. เธฃเธซเธฑเธชเธงเธดเธเธฒเนเธฅเธฐเธเธทเนเธญเธฃเธฒเธขเธงเธดเธเธฒ เธฃเธซเธฑเธชเธงเธดเธเธฒ {code} เธเธทเนเธญเธงเธดเธเธฒ (เนเธ—เธข) {name_th} "
        f"เธเธทเนเธญเธงเธดเธเธฒ (เธญเธฑเธเธเธคเธฉ) {name_en}",
    )
    _set_cell_text(table0.cell(3, 0), f"2. เธเธณเธเธงเธเธซเธเนเธงเธขเธเธดเธ• {credits}")
    _set_cell_text(
        table0.cell(4, 0),
        f"3.เธเธทเนเธญเธซเธฅเธฑเธเธชเธนเธ•เธฃเนเธฅเธฐเธเธฃเธฐเน€เธ เธ—เธเธญเธเธฃเธฒเธขเธงเธดเธเธฒ เธเธทเนเธญเธซเธฅเธฑเธเธชเธนเธ•เธฃ {curriculum_name} "
        f"เธเธฃเธฐเน€เธ เธ—เธเธญเธเธฃเธฒเธขเธงเธดเธเธฒ {course_type}",
    )
    _set_cell_text(
        table0.cell(5, 0),
        f"4. เธเธณเธญเธเธดเธเธฒเธขเธฃเธฒเธขเธงเธดเธเธฒ เธ เธฒเธฉเธฒเนเธ—เธข {desc_th} เธ เธฒเธฉเธฒเธญเธฑเธเธเธคเธฉ {desc_en}",
    )

    plo_lookup = _build_plo_lookup(data["plos"])
    _replace_block_between(
        doc,
        lambda text: text.startswith("เมื่อสิ้นสุดการเรียนการสอนแล้วนักศึกษา"),
        lambda text: text.startswith("5.2 "),
        _build_objective_lines(data["clos"], plo_lookup),
    )

    table1 = doc.tables[1]
    table1_template = copy.deepcopy(table1.rows[1]._tr)
    _clear_rows(table1, 1)
    for values in _build_plo_rows(data["plos"], data["clos"], data["assessments"]):
        row = _append_row_from_template(table1, table1_template)
        for idx, value in enumerate(values):
            if idx < len(row.cells):
                _set_cell_text(row.cells[idx], value)

    table2 = doc.tables[2]
    table2_template = copy.deepcopy(table2.rows[1]._tr)
    _clear_rows(table2, 1)
    teaching_plan = data["teaching_plan"] or [{
        "week_label": "-",
        "llo_text": "-",
        "topic": "-",
        "teaching_method": "-",
        "media": "-",
        "assessment_tools": "-",
    }]
    for item in teaching_plan:
        row = _append_row_from_template(table2, table2_template)
        values = [
            _safe_text(item.get("week_label") or item.get("week"), "-"),
            _safe_text(item.get("llo_text"), "-"),
            _safe_text(item.get("topic"), "-"),
            _safe_text(item.get("teaching_method") or item.get("activities"), "-"),
            _safe_text(item.get("media"), "-"),
            _safe_text(item.get("assessment_tools"), "-"),
        ]
        for idx, value in enumerate(values):
            if idx < len(row.cells):
                _set_cell_text(row.cells[idx], value)

    table3 = doc.tables[3]
    for idx, value in enumerate(_hours_summary(course, data["teaching_plan"])):
        if idx < len(table3.rows[1].cells):
            _set_cell_text(table3.rows[1].cells[idx], value)

    clo_label_map = _build_clo_label_map(data["clos"])
    table4 = doc.tables[4]
    assessment_row_template = copy.deepcopy(table4.rows[1]._tr)
    total_row_template = copy.deepcopy(table4.rows[-1]._tr)
    _clear_rows(table4, 1)
    assessments = data["assessments"] or [{
        "name": "-",
        "assessment_period": "-",
        "weight_pct": 0,
        "clo_mapping": [],
        "eval_criteria": "",
        "pass_threshold": 50.0,
    }]
    total_weight = 0.0
    for assessment in assessments:
        row = _append_row_from_template(table4, assessment_row_template)
        clo_numbers = [int(num) for num in _ensure_list(assessment.get("clo_mapping")) if str(num).isdigit()]
        clo_text = _join_unique(clo_label_map.get(num, f"CLO{num}") for num in clo_numbers)
        period = _safe_text(assessment.get("assessment_period"), "-")
        weight = assessment.get("weight_pct", 0) or 0
        total_weight += float(weight)
        values = [
            clo_text,
            _format_assessment_label(assessment),
            period,
            period,
            _format_pct(weight, default=0),
            _format_pct(weight, default=0),
        ]
        for idx, value in enumerate(values):
            if idx < len(row.cells):
                _set_cell_text(row.cells[idx], value)

    total_row = _append_row_from_template(table4, total_row_template)
    for cell in total_row.cells:
        _set_cell_text(cell, "")
    if len(total_row.cells) >= 1:
        _set_cell_text(total_row.cells[0], "เธฃเธงเธก")
    if len(total_row.cells) >= 2:
        _set_cell_text(total_row.cells[1], "เธฃเธงเธก")
    if len(total_row.cells) >= 3:
        _set_cell_text(total_row.cells[2], "เธฃเธงเธก")
    if len(total_row.cells) >= 2:
        _set_cell_text(total_row.cells[-2], _format_pct(total_weight, default=0))
        _set_cell_text(total_row.cells[-1], _format_pct(total_weight, default=0))

    # --- เธซเธกเธงเธ” 8: เธ—เธฃเธฑเธเธขเธฒเธเธฃเธเธฃเธฐเธเธญเธเธเธฒเธฃเน€เธฃเธตเธขเธเธเธฒเธฃเธชเธญเธ ---
    resources = data["resources"]
    resource_lines = []
    for idx, resource in enumerate(resources, start=1):
        citation = _clean_numbering_prefix(resource.get("citation_text", ""))
        url = _safe_text(resource.get("url"))
        note = _safe_text(resource.get("note"))
        tail = " ".join(bit for bit in [url, note] if bit and bit not in citation)
        text = citation if not tail else f"{citation} {tail}".strip()
        resource_lines.append(f"{idx}. {text}".strip())
    if not resource_lines:
        resource_lines = ["1. -"]

    # เนเธเน _replace_block_between เน€เธเธทเนเธญเนเธ—เธเธ—เธตเนเน€เธเธเธฒเธฐเธฃเธฒเธขเธเธฒเธฃ resources
    # เธฃเธฐเธซเธงเนเธฒเธเธขเนเธญเธซเธเนเธฒเธซเธกเธฒเธขเน€เธซเธ•เธธ "(เน€เธงเนเธเนเธเธ•เน...)" เธเธฑเธ "9. เธเธ“เธฐเธเธฃเธฃเธกเธเธฒเธฃ..."
    # เนเธกเนเนเธซเนเธเธดเธเนเธเธ–เธถเธ section 9 เธซเธฃเธทเธญ เธ เธฒเธเธเธเธงเธ
    _replace_block_between(
        doc,
        lambda text: text.startswith("(เว็บไซต์"),
        lambda text: text.startswith("9."),
        resource_lines,
    )

    # --- เธซเธกเธงเธ” 9: เธเธ“เธฐเธเธฃเธฃเธกเธเธฒเธฃเธเธฃเธดเธซเธฒเธฃเธฃเธฒเธขเธงเธดเธเธฒ / เธญเธฒเธเธฒเธฃเธขเนเธเธนเนเธชเธญเธ ---
    staff = data.get("staff", [])
    committee = [s for s in staff if s.get("role") == "committee"]
    instructors = [s for s in staff if s.get("role") == "instructor"]

    # fallback: เธ–เนเธฒเนเธกเนเธกเธต tqf3_staff เนเธซเนเนเธเน instructor_main / instructors_json
    if not committee and not instructors:
        instructor_main = _safe_text(course.get("instructor_main"))
        instructors_json = _ensure_list(course.get("instructors_json"))
        if instructor_main:
            committee = [{"name": instructor_main}]
        if instructors_json:
            instructors = [{"name": n} for n in instructors_json]
        elif instructor_main:
            instructors = [{"name": instructor_main}]

    committee_lines = [
        f"{i + 1}. {_safe_text(s.get('name'), '-')}"
        for i, s in enumerate(committee or [{"name": "-"}])
    ]
    instructor_lines = [
        f"{i + 1}. {_safe_text(s.get('name'), '-')}"
        for i, s in enumerate(instructors or [{"name": "-"}])
    ]

    _replace_block_between(
        doc,
        lambda text: text.startswith("9.1"),
        lambda text: text.startswith("9.2"),
        committee_lines,
    )
    _replace_block_between(
        doc,
        lambda text: text.startswith("9.2"),
        lambda text: text.startswith("ภาคผนวก"),
        instructor_lines,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    return str(output)


def generate_tqf3_docx(
    course_id: int = None,
    semester: int = None,
    year: int = None,
    output_path: str = None,
    tqf3_id: int = None,
) -> str:
    data = load_data_for_tqf3(
        course_id=course_id,
        semester=semester,
        year=year,
        tqf3_id=tqf3_id,
    )
    if output_path is None:
        code = data["course"].get("code", "unknown")
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"เธกเธเธญ3_{code}_{data['semester']}_{data['year']}.docx",
        )
    return fill_tqf3(str(find_template()), data, output_path)


if __name__ == "__main__":
    print(generate_tqf3_docx())
