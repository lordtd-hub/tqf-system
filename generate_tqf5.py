"""
generate_tqf5.py — สร้าง มคอ.5 โดยเติมข้อมูลลงใน template แบบฟอร์ม มคอ. 5.docx
ใช้วิธี XML manipulation เพื่อรักษา layout และ formatting เดิมของ template ทุกอย่าง

วิธีการ:
  1. copy template → output
  2. แทรกข้อมูลจาก DB ลงใน placeholder ใน XML โดยตรง
"""

import os
import sys
import re
import copy
import shutil
from pathlib import Path
from docx import Document

import database as db

NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# ── หา template ──────────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).parent
TEMPLATE_CANDIDATES = [
    _THIS_DIR / "templates" / "แบบฟอร์ม มคอ. 5.docx",   # ← ที่อยู่มาตรฐาน
    _THIS_DIR / "แบบฟอร์ม มคอ. 5.docx",                  # ← fallback (เวอร์ชันเก่า)
    _THIS_DIR.parent / "แบบฟอร์ม มคอ. 5.docx",           # ← fallback root
]

def find_template() -> Path:
    for p in TEMPLATE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        "ไม่พบไฟล์ 'แบบฟอร์ม มคอ. 5.docx' — "
        f"กรุณาวางไว้ในโฟลเดอร์ {_THIS_DIR / 'templates'}"
    )


# ════════════════════════════════════════════════
# XML HELPERS (เหมือน tqf3_to_tqf5.py เป๊ะ)
# ════════════════════════════════════════════════

def get_para_text(para_elem) -> str:
    return ''.join(t.text or '' for t in para_elem.iter(f'{{{NS}}}t'))


def replace_plain_text(para_elem, old: str, new: str) -> bool:
    """แทนที่ข้อความที่อาจกระจายอยู่ใน run หลายตัว"""
    all_t = list(para_elem.iter(f'{{{NS}}}t'))
    if not all_t:
        return False
    full = ''.join(t.text or '' for t in all_t)
    if old not in full:
        return False
    new_full = full.replace(old, new)
    all_t[0].text = new_full
    for t in all_t[1:]:
        t.text = ''
    return True


def replace_formfield_value(para_elem, new_value: str, field_index: int = 0) -> bool:
    """แทรกค่าลง form field (FORMTEXT) ตัวที่ field_index"""
    defaults = list(para_elem.iter(f'{{{NS}}}default'))
    if field_index < len(defaults):
        defaults[field_index].set(f'{{{NS}}}val', new_value)

    count = 0
    in_field = False
    for child in para_elem.iter(f'{{{NS}}}fldChar', f'{{{NS}}}t'):
        tag = child.tag.split('}')[1]
        if tag == 'fldChar':
            ftype = child.get(f'{{{NS}}}fldCharType', '')
            if ftype == 'separate':
                in_field = True
            elif ftype == 'end':
                if in_field:
                    count += 1
                in_field = False
        elif tag == 't' and in_field:
            if count == field_index:
                child.text = new_value
                return True
    return False


def clear_and_set_cell_text(tc, text: str):
    """เซ็ตข้อความใน cell โดย clear ทุกอย่างก่อน"""
    paras = tc.findall(f'{{{NS}}}p')
    if not paras:
        return
    p = paras[0]
    for t_elem in p.iter(f'{{{NS}}}t'):
        t_elem.text = ''

    in_field = False
    for child in p.iter(f'{{{NS}}}fldChar', f'{{{NS}}}t'):
        tag = child.tag.split('}')[1]
        if tag == 'fldChar':
            ftype = child.get(f'{{{NS}}}fldCharType', '')
            if ftype == 'separate':
                in_field = True
            elif ftype == 'end':
                in_field = False
        elif tag == 't' and in_field:
            child.text = text
            return

    all_t = list(p.iter(f'{{{NS}}}t'))
    if all_t:
        all_t[0].text = text


def find_tables(body):
    return body.findall(f'.//{{{NS}}}tbl')


def get_rows(tbl):
    return tbl.findall(f'{{{NS}}}tr')


def get_cells(tr):
    return tr.findall(f'{{{NS}}}tc')


def get_paras(tc):
    return tc.findall(f'{{{NS}}}p')


def deep_copy_row(tr):
    return copy.deepcopy(tr)


# ════════════════════════════════════════════════
# DATA LOADER FROM DB
# ════════════════════════════════════════════════

def load_data_for_tqf5(tqf3_id: int) -> dict:
    """โหลดข้อมูลทั้งหมดจาก DB แล้วจัดรูปแบบให้ตรงกับที่ fill_tqf5 ต้องการ"""
    tqf3   = db.get_tqf3(tqf3_id)
    course = db.get_course_by_code(tqf3["code"])
    clos   = db.get_clos(tqf3_id)
    plan   = db.get_teaching_plan(tqf3_id)
    tqf5   = db.get_tqf5(tqf3_id) or {}
    grades_list = db.get_student_grades(tqf5["id"]) if tqf5.get("id") else []
    actual = db.get_teaching_actual(tqf5["id"]) if tqf5.get("id") else []

    # ── Grade stats ──────────────────────────────
    GRADE_ORDER = ['A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'E', 'I', 'P', 'U']
    dist = tqf5.get("grade_dist", {}) or {}
    total = tqf5.get("registered_count", 0) or len(grades_list)
    withdrawn = tqf5.get("withdrawn_count", dist.get("W", 0))
    remaining = tqf5.get("remaining_count", total - withdrawn)

    grades = {}
    for g in GRADE_ORDER:
        display = g
        if g == "I":  display = "ไม่สมบูรณ์ (I)"
        if g in ("P", "S"): display = "ผ่าน (P,S)"
        if g == "U":  display = "ไม่ผ่าน (U)"
        cnt = dist.get(display, dist.get(g, 0))
        pct = round(cnt / total * 100, 2) if total > 0 else 0.0
        grades[g] = {"count": cnt, "percent": f"{pct:.2f}"}

    # ── Teaching plan: ใช้ actual ถ้ามี ──────────
    teaching_plan = []
    if actual:
        for a in actual:
            teaching_plan.append({
                "topic": a["topic"],
                "planned_hours": str(a["hours_planned"]),
                "actual_hours":  str(a["hours_actual"]),
                "deviation":     a["deviation_reason"] or "-",
            })
    elif plan:
        for p in plan:
            teaching_plan.append({
                "topic": p["topic"],
                "planned_hours": str(p["hours_planned"]),
                "actual_hours":  str(p["hours_planned"]),   # default = ตามแผน
                "deviation": "-",
            })

    # ── CLOs ──────────────────────────────────────
    clo_results = tqf5.get("clo_results", []) or []
    clo_result_map = {r.get("clo"): r for r in clo_results}

    clos_data = []
    for c in clos:
        n = c["clo_number"]
        res = clo_result_map.get(n, {})
        clos_data.append({
            "num": n,
            "text": c["description"],
            "teaching_strategy": c.get("teaching_strategy", ""),
            "assessment_method": c.get("assessment_method", ""),
            "indicator": c.get("indicator", f"ร้อยละ {c['target_pct']} ของนักศึกษา"),
            "achieved": "บรรลุ" if res.get("achieved") else "[บรรลุ/ไม่บรรลุ]",
            "note": res.get("note", ""),
            "improvement": "[ระบุแนวทางปรับปรุง]",
        })

    return {
        # หมวด 1
        "faculty":                  f"{course.get('faculty','')} {course.get('department','')}".strip(),
        "course_code":              tqf3["code"],
        "course_name_th":           tqf3["name_th"],
        "course_name_en":           course.get("name_en", ""),
        "credits":                  course.get("credits_text", ""),
        "semester":                 str(tqf3["semester"]),
        "semester_year":            str(tqf3["year"]),
        "prerequisite":             course.get("prerequisite", "ไม่มี"),
        "instructor_responsible":   tqf3.get("instructor_main", ""),
        "instructors":              tqf3.get("instructors", []) or [tqf3.get("instructor_main", "")],
        "location":                 tqf3.get("location", "คณะวิทยาศาสตร์และเทคโนโลยี มหาวิทยาลัยราชภัฏสุราษฎร์ธานี"),
        # หมวด 2
        "teaching_plan":            teaching_plan,
        "clos":                     clos_data,
        # หมวด 3
        "grade_data": {
            "total":     total,
            "withdrawn": withdrawn,
            "remaining": remaining,
            "grades":    grades,
        },
        # หมวด 4-6 (อาจารย์กรอก)
        "tqf5_extra": tqf5,
    }


# ════════════════════════════════════════════════
# FILL TEMPLATE
# ════════════════════════════════════════════════

def fill_tqf5(template_path: str, data: dict, output_path: str):
    doc = Document(template_path)
    body = doc.element.find(f'.//{{{NS}}}body')

    # ══ Title paragraphs ══════════════════════════
    for p in body.findall(f'{{{NS}}}p'):
        ptxt = get_para_text(p)
        if '[รหัสวิชา]' in ptxt and '[ชื่อรายวิชา]' in ptxt:
            replace_plain_text(p, '[รหัสวิชา]', data['course_code'])
            replace_plain_text(p, '[ชื่อรายวิชา]', data['course_name_th'])
        elif 'ภาคเรียนที่' in ptxt and ('25xx' in ptxt or '[' in ptxt):
            # ต้อง formfield ก่อน แล้วค่อย plain text (ไม่งั้นจะ render ซ้ำ)
            replace_formfield_value(p, data['semester'])
            replace_plain_text(p, '25xx', data['semester_year'])
            replace_plain_text(p, ' 25xx', ' ' + data['semester_year'])

    tables = find_tables(body)

    # ══ Table 0: Header info ══════════════════════
    t0 = tables[0]
    for tr in get_rows(t0):
        tc = get_cells(tr)[0]
        row_text = ''.join(get_para_text(p) for p in get_paras(tc))

        if 'คณะ/สาขา/วิชาเอก' in row_text:
            for p in get_paras(tc):
                if 'คณะ' in get_para_text(p):
                    replace_formfield_value(p, data['faculty'])
                    replace_plain_text(p, '[..............................]', data['faculty'])

        elif 'รหัสวิชาและชื่อรายวิชา' in row_text:
            for p in get_paras(tc):
                pt = get_para_text(p)
                if 'รหัสวิชา' in pt and 'ชื่อวิชา (ไทย)' in pt:
                    replace_formfield_value(p, data['course_code'], 0)
                    replace_formfield_value(p, data['course_name_th'], 1)
                elif 'รหัสวิชา' in pt and '[' in pt:
                    replace_formfield_value(p, data['course_code'], 0)
                elif 'ชื่อวิชา (ไทย)' in pt and '[' in pt:
                    replace_formfield_value(p, data['course_name_th'], 0)
                elif 'ชื่อวิชา (อังกฤษ)' in pt and '[' in pt:
                    replace_formfield_value(p, data['course_name_en'], 0)

        elif 'จำนวนหน่วยกิต' in row_text:
            for p in get_paras(tc):
                if 'น(ท-ป-ศ)' in get_para_text(p):
                    replace_plain_text(p, 'น(ท-ป-ศ)', data['credits'])

        elif 'ต้องเรียนก่อนรายวิชา' in row_text:
            for p in get_paras(tc):
                pt = get_para_text(p)
                if '[รหัสวิชา]' in pt:
                    replace_plain_text(p, '[รหัสวิชา] [ชื่อวิชาภาษาไทย] น(ท-ป-ศ)', data['prerequisite'])
                    replace_plain_text(p, '[รหัสวิชา]', '')
                    replace_plain_text(p, '[ชื่อวิชาภาษาไทย]', '')
                    replace_plain_text(p, 'น(ท-ป-ศ)', '')

        elif 'อาจารย์ผู้รับผิดชอบ' in row_text:
            for p in get_paras(tc):
                pt = get_para_text(p)
                if 'อาจารย์ผู้รับผิดชอบ' in pt and '[' in pt:
                    replace_formfield_value(p, data['instructor_responsible'])
                    replace_plain_text(p, '[..............................]', data['instructor_responsible'])
                elif 'ระบุชื่ออาจารย์ประจำกลุ่มเรียน' in pt:
                    if data['instructors']:
                        replace_plain_text(p, '[ระบุชื่ออาจารย์ประจำกลุ่มเรียน]', data['instructors'][0])
                        replace_plain_text(p, '[..............................]', '')

        elif 'ภาคการศึกษา' in row_text:
            for p in get_paras(tc):
                if '[' in get_para_text(p):
                    val = f"{data['semester']}/{data['semester_year']}"
                    replace_formfield_value(p, val)
                    replace_plain_text(p, '[..............................]', val)

        elif 'สถานที่เรียน' in row_text:
            for p in get_paras(tc):
                if '[' in get_para_text(p):
                    replace_formfield_value(p, data['location'])
                    replace_plain_text(p, '[..............................]', data['location'])

    # ══ Table 1: Teaching hours ══════════════════
    if len(tables) > 1:
        t1 = tables[1]
        rows1 = get_rows(t1)
        if len(rows1) > 1:
            template_data_row = rows1[1]
            for tr in rows1[1:]:
                t1.remove(tr)

            for tp in data['teaching_plan']:
                new_tr = deep_copy_row(template_data_row)
                t1.append(new_tr)
                cells = get_cells(new_tr)
                if len(cells) >= 4:
                    clear_and_set_cell_text(cells[0], tp['topic'])
                    clear_and_set_cell_text(cells[1], tp['planned_hours'])
                    clear_and_set_cell_text(cells[2], tp.get('actual_hours', tp['planned_hours']))
                    clear_and_set_cell_text(cells[3], tp.get('deviation', '-'))

    # ══ Table 3: CLO table ══════════════════════
    if len(tables) > 3:
        t3 = tables[3]
        rows3 = get_rows(t3)
        if len(rows3) > 1:
            template_clo_row = rows3[1]
            for tr in rows3[2:]:
                t3.remove(tr)

            clos = data['clos']
            if clos:
                # Fill row 1 with CLO1
                cells3 = get_cells(rows3[1])
                clo1_text = f"CLO{clos[0]['num']} {clos[0]['text']}"
                for p in get_paras(cells3[0]):
                    replaced = replace_plain_text(p, '1.สามารถอธิบาย....ได้อย่างถูกต้อง', clo1_text)
                    if not replaced:
                        for t_elem in p.iter(f'{{{NS}}}t'):
                            if t_elem.text and ('สามารถ' in t_elem.text or 'CLO' in t_elem.text
                                                or 'อธิบาย' in t_elem.text):
                                t_elem.text = clo1_text
                                break
                # Fill columns 2-6 for CLO1
                _fill_clo_row_extra(cells3, clos[0])

                # Add CLO 2+
                for clo in clos[1:]:
                    new_tr = deep_copy_row(template_clo_row)
                    t3.append(new_tr)
                    cells = get_cells(new_tr)
                    clo_text = f"CLO{clo['num']} {clo['text']}"
                    for p in get_paras(cells[0]):
                        for t_elem in p.iter(f'{{{NS}}}t'):
                            t_elem.text = ''
                        all_t = list(p.iter(f'{{{NS}}}t'))
                        if all_t:
                            all_t[0].text = clo_text
                    _fill_clo_row_extra(cells, clo)

    # ══ Section 3: Grade counts ═══════════════════
    _fill_section3(body, tables, data['grade_data'])

    doc.save(output_path)
    print(f"[TQF5] Saved: {output_path}")


def _fill_clo_row_extra(cells, clo: dict):
    """เติม column กลยุทธ์, ตัวชี้วัด, วิธีประเมิน, ผล, แนวทาง ของแต่ละ CLO"""
    # cells: [CLO, กลยุทธ์, ตัวชี้วัด, วิธีประเมิน, ผลตามตัวชี้วัด, แนวทาง]
    col_data = [
        clo.get("teaching_strategy", ""),
        clo.get("indicator", ""),
        clo.get("assessment_method", ""),
        clo.get("note", "") or clo.get("achieved", ""),
        clo.get("improvement", ""),
    ]
    for i, val in enumerate(col_data):
        ci = i + 1
        if ci < len(cells) and val:
            for p in get_paras(cells[ci]):
                all_t = list(p.iter(f'{{{NS}}}t'))
                if all_t:
                    # ถ้ามี placeholder ให้แทน ถ้าไม่มีให้ set ตรง
                    full = ''.join(t.text or '' for t in all_t)
                    if not full.strip() or '[' in full:
                        all_t[0].text = val
                        for t in all_t[1:]:
                            t.text = ''


def _fill_section3(body, tables, grade_data: dict):
    """เติมจำนวนนักศึกษาและตารางเกรด (หมวด 3)"""
    total     = str(grade_data['total'])
    remaining = str(grade_data['remaining'])
    withdrawn = str(grade_data['withdrawn'])

    for p in body.iter(f'{{{NS}}}p'):
        txt = ''.join(t.text or '' for t in p.iter(f'{{{NS}}}t'))
        if 'ลงทะเบียนเรียน' in txt and '[xx]' in txt:
            replace_plain_text(p, '[xx]', total)
        elif 'คงอยู่เมื่อสิ้นสุดภาคการศึกษา' in txt and '[xx]' in txt:
            replace_plain_text(p, '[xx]', remaining)
        elif 'ถอน (W)' in txt and '[xx]' in txt:
            replace_plain_text(p, '[xx]', withdrawn)

    # ตาราง grade distribution (table[4] ใน template)
    if len(tables) > 4:
        t4 = tables[4]
        rows4 = get_rows(t4)
        grade_order = ['A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'E', 'I', 'P', 'U']

        for tr in rows4[1:]:
            cells = get_cells(tr)
            if not cells:
                continue
            row_label = ''.join(t.text or '' for t in cells[0].iter(f'{{{NS}}}t')).strip()

            matched = None
            for g in grade_order:
                if g in row_label:
                    matched = g
                    break

            if matched and matched in grade_data['grades']:
                info = grade_data['grades'][matched]
                cnt = str(info['count'])
                pct = info['percent']
                if len(cells) >= 3:
                    for p in get_paras(cells[1]):
                        replace_plain_text(p, '[xx]', cnt)
                    for p in get_paras(cells[2]):
                        replace_plain_text(p, '[xx]', pct)


# ════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════

def generate_tqf5_docx(tqf3_id: int, output_path: str = None) -> str:
    """
    สร้างไฟล์ มคอ.5 .docx โดยเติมข้อมูลจาก DB ลงใน template
    คืน path ของไฟล์ที่สร้าง
    """
    template = find_template()

    tqf3 = db.get_tqf3(tqf3_id)
    if not tqf3:
        raise ValueError(f"ไม่พบ TQF3 id={tqf3_id}")

    if not output_path:
        fname = f"มคอ5_{tqf3['code']}_{tqf3['semester']}_{tqf3['year']}.docx"
        output_path = str(_THIS_DIR / fname)

    print(f"[TQF5] Template: {template}")
    data = load_data_for_tqf5(tqf3_id)
    fill_tqf5(str(template), data, output_path)
    return output_path


# ════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_tqf5.py <tqf3_id> [output_path]")
        sys.exit(1)
    db.init_db()
    tqf3_id = int(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    result = generate_tqf5_docx(tqf3_id, out)
    print(f"Generated: {result}")
