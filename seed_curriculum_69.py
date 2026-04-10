"""
seed_curriculum_69.py — ใส่ข้อมูลหลักสูตร 69 (วท.บ. คณิตศาสตร์ ปรับปรุง พ.ศ. 2569)
รัน: python seed_curriculum_69.py

ข้อมูล:
  - PLOs 6 ข้อ (รวม PLO 4.3)
  - YLOs 4 ชั้นปี พร้อม indicators, เครื่องมือประเมิน และ plo_mapping
  - เกณฑ์จบการศึกษาพิเศษ (คะแนนดิจิทัล + ภาษาอังกฤษ)

Script นี้ idempotent — รันซ้ำได้โดยไม่เกิดข้อมูลซ้ำ
"""

import json
import database as db

db.init_db()

# ── 1. หลักสูตร 69 ────────────────────────────────────────────────────────────
graduation_req = json.dumps({
    "digital_score_min_pct": 50,
    "english_req": "ผ่านเกณฑ์ภาษาอังกฤษตามที่มหาวิทยาลัยกำหนด",
    "rubric_required": True,
    "marking_scheme_required": True,
    "notes": (
        "ทุกรายวิชาต้องใช้ Rubric Score และมี Marking Scheme ที่ชัดเจน "
        "เพื่อความโปร่งใสในการประเมิน PLOs "
        "หลักสูตรมีคณะกรรมการทวนสอบตรวจสอบเครื่องมือให้สอดคล้องกับ PLOs/YLOs"
    ),
}, ensure_ascii=False)

with db.get_conn() as conn:
    conn.execute(
        """
        INSERT INTO curricula (version, name_th, effective_year, graduation_req)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(version) DO UPDATE SET
            name_th=excluded.name_th,
            effective_year=excluded.effective_year,
            graduation_req=excluded.graduation_req
        """,
        ("69",
         "หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาคณิตศาสตร์ (ปรับปรุง พ.ศ. 2569)",
         2569,
         graduation_req),
    )
    cur = conn.execute("SELECT id FROM curricula WHERE version='69'").fetchone()
    curriculum_id = cur["id"]

print(f"[Seed] Curriculum 69 → id={curriculum_id}")

# ── 2. PLOs ────────────────────────────────────────────────────────────────────
plos = [
    dict(plo_number=1, plo_code="1",
         description="อธิบายความรู้เชิงทฤษฎีพื้นฐานทางเคมี ชีววิทยา และคณิตศาสตร์ได้"),
    dict(plo_number=2, plo_code="2",
         description="ประยุกต์ความรู้เพื่อพัฒนางานหรือแก้ปัญหาได้"),
    dict(plo_number=3, plo_code="3",
         description="ใช้เครื่องมือพื้นฐานทางวิทยาศาสตร์และคณิตศาสตร์ได้"),
    dict(plo_number=4, plo_code="4.3",
         description="ใช้หลักการทางคณิตศาสตร์ พัฒนาแบบจำลองหรือทฤษฎีเพื่อแก้ปัญหา"),
    dict(plo_number=5, plo_code="5",
         description="แสดงออกถึงคุณธรรม จริยธรรม จรรยาบรรณ และจิตสาธารณะ"),
    dict(plo_number=6, plo_code="6",
         description="ใฝ่รู้ มีเหตุผล คิดสร้างสรรค์ ใช้เทคโนโลยีในยุคดิจิทัล"),
]
db.replace_plos(curriculum_id, plos)
print(f"[Seed] PLOs: {len(plos)} รายการ")

# ── 3. YLOs ────────────────────────────────────────────────────────────────────
# plo_mapping = plo_number (int) ของ PLO ที่ YLO นี้ส่งเสริม
ylos = [
    dict(
        year_number=1,
        title="พื้นฐานทางทฤษฎีและการใช้เครื่องมือเบื้องต้น",
        indicators="\n".join([
            "อธิบายทฤษฎีพื้นฐานได้ถูกต้อง",
            "ใช้เครื่องมือตามหลักการได้",
            "มีความรับผิดชอบและตรงต่อเวลา",
        ]),
        assessment_methods="\n".join([
            "1. การสอบ (ปรนัย/อัตนัย/ปากเปล่า/ปฏิบัติ)",
            "2. ประเมินแบบฝึกหัด รายงาน และการนำเสนองาน",
            "3. การสังเกตพฤติกรรมและการมีส่วนร่วมในชั้นเรียน",
        ]),
        plo_mapping=[1, 3, 5, 6],
    ),
    dict(
        year_number=2,
        title="การแก้ปัญหาสถานการณ์โดยใช้คณิตศาสตร์และสถิติ",
        indicators="\n".join([
            "ใช้ความรู้และเครื่องมือแก้ปัญหาที่กำหนดได้",
            "แสดงออกถึงจิตสาธารณะและเหตุผล",
            "ใช้เทคโนโลยีดิจิทัลอย่างเหมาะสม",
        ]),
        assessment_methods="\n".join([
            "1. การประเมินผลงาน (ชิ้นงาน/รายงาน/กลุ่ม)",
            "2. การทดสอบวัดความรู้และทักษะประยุกต์",
            "3. การสังเกตการทำงานเป็นทีมและพฤติกรรม",
        ]),
        plo_mapping=[2, 3, 5, 6],
    ),
    dict(
        year_number=3,
        title="การสร้างแบบจำลองและการประยุกต์ใช้เทคโนโลยี",
        indicators="\n".join([
            "พัฒนาแบบจำลองหรือทฤษฎีคณิตศาสตร์ได้",
            "คะแนนดิจิทัล ≥ 50%",
            "ผ่านเกณฑ์ภาษาอังกฤษของมหาวิทยาลัย",
        ]),
        assessment_methods="\n".join([
            "1. การประเมินโครงงาน (Project) และเล่มรายงาน",
            "2. การทดสอบทักษะดิจิทัลและภาษาอังกฤษ",
            "3. ระบบตรวจสอบการคัดลอกผลงาน",
        ]),
        plo_mapping=[2, 4, 6],     # 4 = PLO 4.3
    ),
    dict(
        year_number=4,
        title="การปฏิบัติงานจริงและสหกิจศึกษา",
        indicators="\n".join([
            "ประยุกต์ความรู้ในงานจริง ณ สถานประกอบการได้",
            "มีจรรยาบรรณวิชาชีพ",
            "ปรับตัวทำงานร่วมกับผู้อื่นได้ดี",
        ]),
        assessment_methods="\n".join([
            "1. การประเมินโดยสถานประกอบการ (พี่เลี้ยง)",
            "2. การประเมินโดยอาจารย์นิเทศก์",
            "3. รายงานสหกิจศึกษาและการนำเสนอผลงาน",
        ]),
        plo_mapping=[2, 3, 5],
    ),
]
db.replace_ylos(curriculum_id, ylos)
print(f"[Seed] YLOs: {len(ylos)} ชั้นปี")

# ── 4. ตรวจสอบผลลัพธ์ ─────────────────────────────────────────────────────────
print("\n── PLOs ──────────────────────────────────────────────")
plo_list = db.get_plos(curriculum_id)
for p in plo_list:
    print(f"  PLO {p['plo_code']}: {p['description'][:60]}")

print("\n── YLOs ──────────────────────────────────────────────")
plo_code_map = {p["plo_number"]: p["plo_code"] for p in plo_list}
for y in db.get_ylos(curriculum_id):
    codes = [plo_code_map.get(n, str(n)) for n in y["plo_mapping"]]
    print(f"  ชั้นปีที่ {y['year_number']}: {y['title']}")
    print(f"    PLOs ที่ส่งเสริม: {', '.join(codes)}")

print("\n── เกณฑ์จบการศึกษา ───────────────────────────────────")
with db.get_conn() as conn:
    row = conn.execute(
        "SELECT graduation_req FROM curricula WHERE id=?", (curriculum_id,)
    ).fetchone()
    req = json.loads(row["graduation_req"] or "{}")
    print(f"  คะแนนดิจิทัลขั้นต่ำ : {req.get('digital_score_min_pct', '-')}%")
    print(f"  ภาษาอังกฤษ         : {req.get('english_req', '-')}")
    print(f"  Rubric required    : {req.get('rubric_required', False)}")

print("\n[Seed] เสร็จสมบูรณ์ ✓")
