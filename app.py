"""
app.py — TQF System Web Interface (Streamlit)
รันด้วย: streamlit run app.py

ต้องการ: pip install streamlit pandas plotly python-docx
"""

import os
import sys
import json
import tempfile
import subprocess
from datetime import datetime

import streamlit as st
import pandas as pd

# เพิ่ม path ของโฟลเดอร์นี้
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
import import_tqf3
import import_grades
import generate_tqf5

# ════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════

st.set_page_config(
    page_title="ระบบ TQF | มคอ.3 → มคอ.5",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════
# INIT DB
# ════════════════════════════════════════════════

db.init_db()

# ════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ════════════════════════════════════════════════

st.sidebar.title("📚 ระบบ TQF")
st.sidebar.caption("มคอ.3 → ฐานข้อมูล → มคอ.5")
st.sidebar.divider()

PAGE = st.sidebar.radio(
    "เลือกหน้า",
    options=[
        "🏠 Dashboard",
        "📥 นำเข้า มคอ.3",
        "📊 นำเข้าเกรด",
        "📝 สร้าง มคอ.5",
        "🔍 ดูข้อมูลรายวิชา",
        "📈 ประวัติย้อนหลัง",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption(f"DB: {os.path.basename(db.DB_PATH)}")

# ════════════════════════════════════════════════
# HELPER
# ════════════════════════════════════════════════

def success(msg): st.success(f"✅ {msg}")
def error(msg):   st.error(f"❌ {msg}")
def warn(msg):    st.warning(f"⚠️ {msg}")
def info(msg):    st.info(f"ℹ️ {msg}")


def format_sem_year(s, y):
    return f"ภาค {s}/{y}"


# ════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════

if PAGE == "🏠 Dashboard":
    st.title("🏠 Dashboard — ภาพรวมทั้งสาขา")

    summary = db.get_dashboard_summary()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("รายวิชาในระบบ",  summary["total_courses"],  "วิชา")
    col2.metric("มคอ.3 ที่นำเข้า", summary["total_tqf3"],    "รายการ")
    col3.metric("มคอ.5 ที่สร้าง",  summary["total_tqf5"],    "รายการ")
    col4.metric("นักศึกษา (รวม)", summary["total_students"], "คน")

    st.divider()
    st.subheader("รายวิชาล่าสุด")

    if summary["recent"]:
        rows = []
        for r in summary["recent"]:
            dist = json.loads(r.get("grade_dist_json") or "{}")
            total = sum(dist.values()) if dist else 0
            a_pct = round(dist.get("A", 0) / total * 100, 1) if total else 0
            rows.append({
                "รหัสวิชา": r["code"],
                "ชื่อวิชา": r["name_th"],
                "ภาค/ปี": format_sem_year(r["semester"], r["year"]),
                "ลงทะเบียน": r.get("registered_count") or total,
                "A (%)": f"{a_pct:.1f}%",
                "มคอ.5": "✅" if r.get("registered_count") else "⏳",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        info("ยังไม่มีข้อมูล — เริ่มด้วยการนำเข้า มคอ.3")

    # Grade distribution chart (รวมทุกวิชา)
    if summary["total_students"] > 0:
        st.divider()
        st.subheader("การกระจายเกรดรวมทุกวิชา")

        with db.get_conn() as conn:
            rows = conn.execute(
                "SELECT grade, COUNT(*) as cnt FROM student_grades GROUP BY grade ORDER BY grade"
            ).fetchall()

        if rows:
            df_g = pd.DataFrame(rows, columns=["เกรด", "จำนวน"])
            grade_order = ["A","B+","B","C+","C","D+","D","E","W","I","P","S","U"]
            df_g["sort"] = df_g["เกรด"].apply(
                lambda g: grade_order.index(g) if g in grade_order else 99)
            df_g = df_g.sort_values("sort").drop(columns="sort")
            st.bar_chart(df_g.set_index("เกรด"))


# ════════════════════════════════════════════════
# PAGE: IMPORT TQF3
# ════════════════════════════════════════════════

elif PAGE == "📥 นำเข้า มคอ.3":
    st.title("📥 นำเข้า มคอ.3")
    st.caption("อัปโหลดไฟล์ มคอ.3 .docx หรือ .doc เพื่อบันทึกข้อมูลลงฐานข้อมูล")

    uploaded = st.file_uploader(
        "เลือกไฟล์ มคอ.3",
        type=["docx", "doc"],
        accept_multiple_files=True,
        help="รองรับหลายไฟล์พร้อมกัน"
    )

    if uploaded:
        if st.button("🚀 นำเข้าไฟล์ที่เลือก", type="primary"):
            results = []
            prog = st.progress(0)
            for i, f in enumerate(uploaded):
                prog.progress((i + 1) / len(uploaded))
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                    tmp.write(f.read())
                    tmp_path = tmp.name
                try:
                    # ถ้าเป็น .doc ให้แปลงก่อน
                    if f.name.lower().endswith(".doc"):
                        soffice = os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            "..", ".claude", "skills", "docx",
                            "scripts", "office", "soffice.py")
                        if os.path.exists(soffice):
                            subprocess.run(
                                [sys.executable, soffice,
                                 "--headless", "--convert-to", "docx", tmp_path],
                                capture_output=True)
                            tmp_path = tmp_path.replace(".docx", "") + ".docx"

                    result = import_tqf3.import_tqf3(tmp_path)
                    results.append({"ไฟล์": f.name, "สถานะ": "✅ สำเร็จ",
                                    "รหัสวิชา": result["code"],
                                    "ชื่อวิชา": result["name_th"],
                                    "CLOs": result["clos_count"],
                                    "แผนการสอน": f"{result['plan_weeks']} สัปดาห์"})
                except Exception as e:
                    results.append({"ไฟล์": f.name, "สถานะ": f"❌ {e}",
                                    "รหัสวิชา": "", "ชื่อวิชา": "", "CLOs": "", "แผนการสอน": ""})
                finally:
                    os.unlink(tmp_path) if os.path.exists(tmp_path) else None

            prog.empty()
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            success(f"นำเข้าแล้ว {len([r for r in results if '✅' in r['สถานะ']])} ไฟล์")

    st.divider()
    st.subheader("หรือกรอกข้อมูลด้วยตนเอง")
    with st.expander("➕ เพิ่มรายวิชาใหม่ / แก้ไข"):
        col1, col2 = st.columns(2)
        with col1:
            code     = st.text_input("รหัสวิชา *", placeholder="เช่น SMA0901")
            name_th  = st.text_input("ชื่อวิชา (ไทย) *", placeholder="สัมมนาคณิตศาสตร์")
            name_en  = st.text_input("ชื่อวิชา (อังกฤษ)", placeholder="Seminar in Mathematics")
            credits  = st.text_input("หน่วยกิต", placeholder="1(0-1-2)")
        with col2:
            sem    = st.selectbox("ภาคการศึกษา", [1, 2])
            year   = st.number_input("ปีการศึกษา", min_value=2560, max_value=2580, value=2568)
            instr  = st.text_input("อาจารย์ผู้รับผิดชอบ")
            loc    = st.text_input("สถานที่เรียน")
            prereq = st.text_input("วิชาที่ต้องเรียนก่อน", value="ไม่มี")

        if st.button("บันทึก", type="primary"):
            if not code or not name_th:
                error("กรุณากรอกรหัสวิชาและชื่อวิชา")
            else:
                try:
                    # parse credits
                    import re
                    m = re.search(r"(\d+)\((\d+)-(\d+)-(\d+)\)", credits)
                    cl, cb, cs = (int(m.group(i)) for i in [2,3,4]) if m else (0,0,0)

                    cid = db.upsert_course(code, name_th, name_en,
                                           credits, cl, cb, cs, prereq)
                    tid = db.upsert_tqf3(cid, sem, year, instr,
                                          location=loc, source_file="manual")
                    success(f"บันทึกแล้ว: {code} {name_th} ภาค {sem}/{year}")
                except Exception as e:
                    error(str(e))


# ════════════════════════════════════════════════
# PAGE: IMPORT GRADES
# ════════════════════════════════════════════════

elif PAGE == "📊 นำเข้าเกรด":
    st.title("📊 นำเข้าไฟล์เกรด")

    # เลือกวิชา
    courses = db.get_all_courses()
    if not courses:
        warn("ยังไม่มีรายวิชา — นำเข้า มคอ.3 ก่อน")
        st.stop()

    course_options = {f"{c['code']} — {c['name_th']}": c["code"] for c in courses}
    selected_label = st.selectbox("เลือกรายวิชา", list(course_options.keys()))
    selected_code  = course_options[selected_label]

    # เลือก ภาค/ปี
    tqf3_list = db.get_all_tqf3()
    course = db.get_course_by_code(selected_code)
    tqf3_for_course = [t for t in tqf3_list if t["code"] == selected_code]

    if not tqf3_for_course:
        warn("ยังไม่มี มคอ.3 สำหรับวิชานี้")
        st.stop()

    sem_year_options = {
        format_sem_year(t["semester"], t["year"]): (t["semester"], t["year"])
        for t in tqf3_for_course
    }
    sel_sem_year = st.selectbox("เลือกภาค/ปีการศึกษา", list(sem_year_options.keys()))
    sem, year    = sem_year_options[sel_sem_year]

    uploaded = st.file_uploader(
        "อัปโหลดไฟล์เกรด (.docx หรือ .doc)",
        type=["docx", "doc"],
        help=f"ไฟล์เกรดสำหรับ {selected_code} ภาค {sem}/{year}"
    )

    if uploaded:
        st.caption(f"ไฟล์: {uploaded.name}  ({uploaded.size:,} bytes)")

        # Preview
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        try:
            if uploaded.name.lower().endswith(".doc"):
                soffice = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", ".claude", "skills", "docx",
                    "scripts", "office", "soffice.py")
                if os.path.exists(soffice):
                    subprocess.run(
                        [sys.executable, soffice,
                         "--headless", "--convert-to", "docx", tmp_path],
                        capture_output=True)
                    tmp_path_new = tmp_path.replace(
                        os.path.splitext(tmp_path)[1], ".docx")
                    if os.path.exists(tmp_path_new):
                        tmp_path = tmp_path_new

            data = import_grades.parse_grade_docx(tmp_path)
            students = data["students"]

            if students:
                st.subheader(f"Preview — {len(students)} นักศึกษา")
                df = pd.DataFrame([{
                    "รหัส": s["student_id"],
                    "ชื่อ-สกุล": s["student_name"],
                    "คะแนนรวม": s["total_score"],
                    "เกรด": s["grade"],
                } for s in students])
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Grade dist
                dist = data["grade_dist"]
                if dist:
                    st.subheader("การกระจายเกรด")
                    df_d = pd.DataFrame(
                        [(g, n) for g, n in dist.items()],
                        columns=["เกรด", "จำนวน"]
                    )
                    st.bar_chart(df_d.set_index("เกรด"))
            else:
                warn("ไม่พบข้อมูลนักศึกษาในไฟล์ — ตรวจสอบรูปแบบไฟล์")

        except Exception as e:
            error(f"อ่านไฟล์ไม่ได้: {e}")
            st.stop()

        if students and st.button("✅ บันทึกลงฐานข้อมูล", type="primary"):
            try:
                result = import_grades.import_grades(
                    tmp_path, selected_code, sem, year)
                success(f"บันทึกแล้ว {result['students_count']} คน | "
                        f"ลงทะเบียน {result['stats']['registered']} | "
                        f"ถอน {result['stats']['withdrawn']}")
            except Exception as e:
                error(str(e))

        os.unlink(tmp_path) if os.path.exists(tmp_path) else None


# ════════════════════════════════════════════════
# PAGE: GENERATE TQF5
# ════════════════════════════════════════════════

elif PAGE == "📝 สร้าง มคอ.5":
    st.title("📝 สร้าง มคอ.5 อัตโนมัติ")

    tqf3_all = db.get_all_tqf3()
    if not tqf3_all:
        warn("ยังไม่มีข้อมูล มคอ.3 — นำเข้าก่อน")
        st.stop()

    options = {
        f"{t['code']} {t['name_th']} ({format_sem_year(t['semester'], t['year'])})": t["id"]
        for t in tqf3_all
    }
    sel = st.selectbox("เลือกรายวิชาและภาคการศึกษา", list(options.keys()))
    tqf3_id = options[sel]

    tqf3 = db.get_tqf3(tqf3_id)
    tqf5 = db.get_tqf5(tqf3_id)
    clos = db.get_clos(tqf3_id)

    # แสดงสถานะข้อมูล
    col1, col2, col3 = st.columns(3)
    col1.metric("CLOs", len(clos))
    col2.metric("นักศึกษา", tqf5["registered_count"] if tqf5 else "ยังไม่มีเกรด")
    col3.metric("สถานะเกรด", "✅ มีข้อมูล" if tqf5 and tqf5.get("registered_count") else "⏳ รอนำเข้า")

    st.divider()

    # ── กรอกข้อมูลที่ต้องใส่เพิ่ม ────────────────
    st.subheader("✏️ กรอกข้อมูลเพิ่มเติม (อาจารย์กรอก)")
    st.caption("ฟิลด์ที่มี * ต้องกรอก — ที่เหลือระบบจะ auto-fill จาก มคอ.3 และเกรด")

    tqf5_id = db.get_or_create_tqf5(tqf3_id)
    current = db.get_tqf5(tqf3_id) or {}

    with st.form("tqf5_form"):
        st.markdown("**หมวด 2 — CLOs**")
        clo_results = []
        if clos:
            for clo in clos:
                n = clo["clo_number"]
                existing = next(
                    (r for r in (current.get("clo_results") or []) if r.get("clo") == n),
                    {}
                )
                c1, c2 = st.columns([1, 3])
                achieved = c1.checkbox(f"CLO {n} บรรลุ", value=existing.get("achieved", False))
                note = c2.text_input(
                    f"CLO {n} — ผลตามตัวชี้วัด",
                    value=existing.get("note", ""),
                    placeholder="เช่น นักศึกษา 10/13 คน (76.9%) บรรลุเป้าหมาย"
                )
                clo_results.append({"clo": n, "achieved": achieved, "note": note})

        st.divider()
        st.markdown("**หมวด 2 — ชั่วโมงสอนจริง**")
        teach_actual_data = db.get_teaching_actual(tqf5_id)
        updated_actual = []
        if teach_actual_data:
            for i, a in enumerate(teach_actual_data):
                c1, c2, c3 = st.columns([5, 2, 2])
                c1.text(a["topic"][:60])
                h_actual = c2.number_input(
                    f"ชั่วโมงจริง ({i})",
                    value=float(a["hours_actual"]),
                    min_value=0.0, step=0.5,
                    label_visibility="collapsed"
                )
                reason = c3.text_input(
                    f"สาเหตุ ({i})",
                    value=a["deviation_reason"],
                    label_visibility="collapsed",
                    placeholder="สาเหตุ (ถ้าต่างจากแผน >25%)"
                )
                updated_actual.append({
                    "topic": a["topic"],
                    "hours_planned": a["hours_planned"],
                    "hours_actual": h_actual,
                    "deviation_reason": reason,
                })

        st.divider()
        st.markdown("**หมวด 3 — ข้อสังเกตเกรด**")
        abnormal = st.text_area(
            "ปัจจัยที่ทำคะแนนผิดปกติ (ถ้ามี)",
            value=current.get("abnormal_factors", "") or "",
            placeholder="เช่น จำนวนนักศึกษาถอนสูง เนื่องจาก..."
        )
        dev_time = st.text_area(
            "ความคลาดเคลื่อนด้านเวลา (ถ้ามี)",
            value=current.get("deviation_time", "") or "",
            placeholder="ไม่มี"
        )
        dev_method = st.text_area(
            "ความคลาดเคลื่อนด้านวิธีประเมิน (ถ้ามี)",
            value=current.get("deviation_method", "") or "",
            placeholder="ไม่มี"
        )

        st.divider()
        st.markdown("**หมวด 4 — ปัญหา**")
        res_issues   = st.text_area("ปัญหาด้านทรัพยากร", value=current.get("resource_issues", "") or "", placeholder="ไม่มี")
        admin_issues = st.text_area("ปัญหาด้านบริหาร",   value=current.get("admin_issues", "") or "",   placeholder="ไม่มี")

        st.divider()
        st.markdown("**หมวด 5 — ประเมินรายวิชา**")
        eval_notes    = st.text_area("ข้อวิพากษ์จากนักศึกษา",  value=current.get("student_eval_notes", "") or "", placeholder="จุดแข็ง/จุดอ่อนจากผลประเมิน")
        teacher_resp  = st.text_area("ความเห็นอาจารย์",         value=current.get("teacher_response", "") or "",   placeholder="ความเห็นต่อข้อวิพากษ์")

        st.divider()
        st.markdown("**หมวด 6 — แผนปรับปรุง**")
        imp_prev = st.text_area("แผนปรับปรุงจากภาคที่แล้ว + ผล", value=current.get("improvement_prev", "") or "", placeholder="ระบุแผนที่เคยเสนอและผลดำเนินการ")
        imp_next = st.text_area("ข้อเสนอแผนปรับปรุงครั้งต่อไป",  value=current.get("improvement_next", "") or "", placeholder="เช่น ปรับวิธีการสอน...")
        imp_resp = st.text_input("ผู้รับผิดชอบ", value=current.get("improvement_resp", tqf3.get("instructor_main", "")) or "")
        suggestions = st.text_area("ข้อเสนอแนะต่ออาจารย์ผู้รับผิดชอบหลักสูตร", value=current.get("suggestions", "") or "")

        submitted = st.form_submit_button("💾 บันทึก", type="primary")

    if submitted:
        db.update_tqf5(tqf5_id,
            clo_results=clo_results,
            abnormal_factors=abnormal,
            deviation_time=dev_time,
            deviation_method=dev_method,
            resource_issues=res_issues,
            admin_issues=admin_issues,
            student_eval_notes=eval_notes,
            teacher_response=teacher_resp,
            improvement_prev=imp_prev,
            improvement_next=imp_next,
            improvement_resp=imp_resp,
            suggestions=suggestions,
        )
        if updated_actual:
            db.replace_teaching_actual(tqf5_id, updated_actual)
        success("บันทึกข้อมูลแล้ว")

    st.divider()
    if st.button("📄 สร้างไฟล์ มคอ.5 (.docx)", type="primary", use_container_width=True):
        try:
            out_dir = os.path.dirname(os.path.abspath(__file__))
            fname = f"มคอ5_{tqf3['code']}_{tqf3['semester']}_{tqf3['year']}.docx"
            out_path = os.path.join(out_dir, fname)
            generate_tqf5.generate_tqf5_docx(tqf3_id, out_path)

            with open(out_path, "rb") as f:
                st.download_button(
                    label=f"⬇️ ดาวน์โหลด {fname}",
                    data=f.read(),
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            success(f"สร้างไฟล์สำเร็จ: {fname}")
        except Exception as e:
            error(f"สร้างไฟล์ไม่ได้: {e}")
            st.exception(e)


# ════════════════════════════════════════════════
# PAGE: VIEW COURSE
# ════════════════════════════════════════════════

elif PAGE == "🔍 ดูข้อมูลรายวิชา":
    st.title("🔍 ดูข้อมูลรายวิชา")

    courses = db.get_all_courses()
    if not courses:
        warn("ยังไม่มีข้อมูล")
        st.stop()

    course_opts = {f"{c['code']} — {c['name_th']}": c["code"] for c in courses}
    sel = st.selectbox("เลือกรายวิชา", list(course_opts.keys()))
    code = course_opts[sel]
    course = db.get_course_by_code(code)

    # Info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**รหัส:** {course['code']}")
        st.markdown(f"**ชื่อ (ไทย):** {course['name_th']}")
        st.markdown(f"**ชื่อ (อังกฤษ):** {course['name_en']}")
        st.markdown(f"**หน่วยกิต:** {course['credits_text']}")
    with col2:
        st.markdown(f"**คณะ:** {course['faculty']}")
        st.markdown(f"**สาขา:** {course['department']}")
        st.markdown(f"**ประเภท:** {course['course_type']}")
        st.markdown(f"**วิชาก่อนเรียน:** {course['prerequisite']}")

    st.divider()

    # TQF3 sessions
    tqf3_list = db.get_all_tqf3(course["id"])
    if tqf3_list:
        sel_sem = st.selectbox(
            "เลือกภาค/ปี",
            [format_sem_year(t["semester"], t["year"]) for t in tqf3_list]
        )
        tqf3 = next(t for t in tqf3_list
                    if format_sem_year(t["semester"], t["year"]) == sel_sem)

        tab1, tab2, tab3, tab4 = st.tabs(["📋 CLOs", "📅 แผนการสอน", "📊 เกรด", "ℹ️ รายละเอียด"])

        with tab1:
            clos = db.get_clos(tqf3["id"])
            if clos:
                df_c = pd.DataFrame([{
                    "CLO": f"CLO{c['clo_number']}",
                    "ผลลัพธ์การเรียนรู้": c["description"],
                    "กลยุทธ์การสอน": c["teaching_strategy"],
                    "วิธีประเมิน": c["assessment_method"],
                    "เป้าหมาย (%)": c["target_pct"],
                } for c in clos])
                st.dataframe(df_c, use_container_width=True, hide_index=True)
            else:
                info("ยังไม่มีข้อมูล CLOs")

        with tab2:
            plan = db.get_teaching_plan(tqf3["id"])
            if plan:
                df_p = pd.DataFrame([{
                    "สัปดาห์": p["week"],
                    "หัวข้อ": p["topic"],
                    "ชั่วโมง": p["hours_planned"],
                    "วิธีสอน": p["teaching_method"],
                } for p in plan])
                st.dataframe(df_p, use_container_width=True, hide_index=True)
                total_h = sum(p["hours_planned"] for p in plan)
                st.caption(f"รวม {total_h:.0f} ชั่วโมง")
            else:
                info("ยังไม่มีแผนการสอน")

        with tab3:
            tqf5 = db.get_tqf5(tqf3["id"])
            if tqf5 and tqf5.get("registered_count"):
                col1, col2, col3 = st.columns(3)
                col1.metric("ลงทะเบียน",  tqf5["registered_count"])
                col2.metric("คงอยู่",      tqf5["remaining_count"])
                col3.metric("ถอน (W)",     tqf5["withdrawn_count"])

                dist = tqf5.get("grade_dist", {})
                if dist:
                    grade_order = ["A","B+","B","C+","C","D+","D","E","W","ไม่สมบูรณ์ (I)","ผ่าน (P,S)","ไม่ผ่าน (U)"]
                    total = tqf5["registered_count"]
                    rows = []
                    for g in grade_order:
                        n = dist.get(g, 0)
                        rows.append({"เกรด": g, "จำนวน": n,
                                     "%": f"{n/total*100:.2f}" if total else "0.00"})
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    df_chart = pd.DataFrame(
                        [(g, dist.get(g, 0)) for g in grade_order if dist.get(g, 0) > 0],
                        columns=["เกรด", "จำนวน"])
                    if not df_chart.empty:
                        st.bar_chart(df_chart.set_index("เกรด"))
            else:
                info("ยังไม่มีข้อมูลเกรด — นำเข้าไฟล์เกรดก่อน")

        with tab4:
            assess = db.get_assessments(tqf3["id"])
            if assess:
                st.markdown("**การประเมิน:**")
                df_a = pd.DataFrame([{
                    "รูปแบบ": a["name"],
                    "สัดส่วน (%)": a["weight_pct"],
                } for a in assess])
                st.dataframe(df_a, use_container_width=True, hide_index=True)
            st.markdown(f"**อาจารย์ผู้รับผิดชอบ:** {tqf3.get('instructor_main','')}")
            st.markdown(f"**สถานที่เรียน:** {tqf3.get('location','')}")


# ════════════════════════════════════════════════
# PAGE: HISTORY
# ════════════════════════════════════════════════

elif PAGE == "📈 ประวัติย้อนหลัง":
    st.title("📈 ประวัติผลการเรียนรายวิชา")

    courses = db.get_all_courses()
    if not courses:
        warn("ยังไม่มีข้อมูล")
        st.stop()

    course_opts = {f"{c['code']} — {c['name_th']}": c["code"] for c in courses}
    sel = st.selectbox("เลือกรายวิชา", list(course_opts.keys()))
    code = course_opts[sel]

    history = db.get_course_history(code)
    if not history:
        info("ยังไม่มีประวัติผลการเรียน")
        st.stop()

    # Timeline table
    rows = []
    for h in history:
        dist = h.get("grade_dist", {})
        total = sum(dist.values()) if dist else 0
        pass_count = sum(dist.get(g, 0) for g in ["A","B+","B","C+","C","D+","D"])
        rows.append({
            "ภาค/ปี": format_sem_year(h["semester"], h["year"]),
            "ลงทะเบียน": h.get("registered_count") or total,
            "ผ่าน": pass_count,
            "ตก (E)": dist.get("E", 0),
            "ถอน (W)": h.get("withdrawn_count", dist.get("W", 0)),
            "% A": f"{dist.get('A',0)/total*100:.1f}%" if total else "-",
            "อัปเดตล่าสุด": (h.get("last_updated") or "")[:10],
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Trend chart
    if len(history) > 1:
        st.subheader("แนวโน้มการกระจายเกรด")
        trend_data = {}
        labels = []
        for h in reversed(history):
            label = format_sem_year(h["semester"], h["year"])
            labels.append(label)
            dist = h.get("grade_dist", {})
            total = sum(dist.values()) if dist else 1
            for g in ["A", "B+", "B", "C+", "C", "D+", "D", "E"]:
                if g not in trend_data:
                    trend_data[g] = []
                trend_data[g].append(round(dist.get(g, 0) / total * 100, 1))

        df_trend = pd.DataFrame(trend_data, index=labels)
        st.line_chart(df_trend[["A", "B+", "B", "C+", "E"]])
