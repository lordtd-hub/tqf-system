"""
seed_curriculum_69.py — ใส่ข้อมูลหลักสูตร 69 (วท.บ. คณิตศาสตร์ ปรับปรุง พ.ศ. 2569)
รัน: python seed_curriculum_69.py

ข้อมูล: PLOs 6 ข้อ + YLOs 4 ชั้นปี พร้อม mapping ระหว่าง PLO↔YLO
"""

import database as db

db.init_db()

# ── 1. สร้าง/อัพเดทหลักสูตร 69 ───────────────────────────────────────────────
with db.get_conn() as conn:
    conn.execute(
        """
        INSERT INTO curricula (version, name_th, effective_year)
        VALUES (?, ?, ?)
        ON CONFLICT(version) DO UPDATE SET
            name_th=excluded.name_th,
            effective_year=excluded.effective_year
        """,
        ("69", "หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาคณิตศาสตร์ (ปรับปรุง พ.ศ. 2569)", 2569),
    )
    cur = conn.execute("SELECT id FROM curricula WHERE version='69'").fetchone()
    curriculum_id = cur["id"]

print(f"[Seed] Curriculum 69 → id={curriculum_id}")

# ── 2. PLOs หลักสูตร 69 ───────────────────────────────────────────────────────
# หมายเหตุ: PLO 4.3 ใช้ plo_number=4, plo_code='4.3'
plos = [
    dict(plo_number=1, plo_code="1",
         description="อธิบายความรู้เชิงทฤษฎีพื้นฐานทางเคมี ชีววิทยา และคณิตศาสตร์ได้"),
    dict(plo_number=2, plo_code="2",
         description="ประยุกต์ความรู้เพื่อพัฒนางานหรือแก้ปัญหาได้"),
    dict(plo_number=3, plo_code="3",
         description="ใช้เครื่องมือพื้นฐานทางวิทยาศาสตร์และคณิตศาสตร์ได้"),
    dict(plo_number=4, plo_code="4.3",
         description="ใช้หลักการทางคณิตศาสตร์พัฒนาแบบจำลองหรือทฤษฎีเพื่อแก้ปัญหา"),
    dict(plo_number=5, plo_code="5",
         description="แสดงออกถึงคุณธรรม จริยธรรม จรรยาบรรณ และจิตสาธารณะ"),
    dict(plo_number=6, plo_code="6",
         description="ใฝ่รู้ มีเหตุผล คิดสร้างสรรค์ ใช้เทคโนโลยีสื่อสารในยุคดิจิทัล"),
]
db.replace_plos(curriculum_id, plos)
print(f"[Seed] PLOs: {len(plos)} รายการ")

# ── 3. YLOs หลักสูตร 69 (4 ชั้นปี) ──────────────────────────────────────────
# plo_mapping = รายการ plo_number (integer) ที่ YLO นี้ส่งเสริม
ylos = [
    dict(
        year_number=1,
        title="ปรับพื้นฐานและเครื่องมือเบื้องต้น",
        indicators="\n".join([
            "สามารถอธิบายหลักการพื้นฐานได้ถูกต้อง",
            "ใช้เครื่องมือพื้นฐานตามขั้นตอนได้",
            "มีความซื่อสัตย์และตรงต่อเวลา",
        ]),
        assessment_methods="\n".join([
            "การสอบ (ข้อเขียน/ปากเปล่า/ปฏิบัติ)",
            "ประเมินจากแบบฝึกหัด รายงานชิ้นงาน และการนำเสนอ",
            "การสังเกตพฤติกรรมการมีส่วนร่วมในชั้นเรียน",
        ]),
        plo_mapping=[1, 3, 5, 6],   # PLO ที่ชั้นปี 1 ส่งเสริม
    ),
    dict(
        year_number=2,
        title="การใช้ความรู้แก้ปัญหาและสถานการณ์",
        indicators="\n".join([
            "ใช้ความรู้คณิตศาสตร์และสถิติแก้โจทย์ปัญหาที่กำหนดได้",
            "แสดงออกถึงการมีจิตสาธารณะและใฝ่รู้",
        ]),
        assessment_methods="\n".join([
            "การสอบทุกรูปแบบ (เน้นการประยุกต์โจทย์ปัญหา)",
            "ประเมินผลงาน (แบบฝึกหัด/รายงาน/ชิ้นงาน)",
            "การประเมินการทำงานเป็นทีมและการสังเกตพฤติกรรม",
        ]),
        plo_mapping=[2, 3, 5, 6],   # PLO ที่ชั้นปี 2 ส่งเสริม
    ),
    dict(
        year_number=3,
        title="การสร้างแบบจำลองและการคิดสร้างสรรค์",
        indicators="\n".join([
            "พัฒนาแบบจำลองหรือทฤษฎีทางคณิตศาสตร์เพื่อแก้ปัญหาสถานการณ์จริงได้",
            "ผ่านเกณฑ์ดิจิทัล (ไม่ต่ำกว่าร้อยละ 50)",
            "ผ่านเกณฑ์ภาษาอังกฤษของมหาวิทยาลัย",
        ]),
        assessment_methods="\n".join([
            "การประเมินโครงงาน (Project) และเล่มรายงาน",
            "การทดสอบความรู้ความสามารถด้านดิจิทัลและภาษาอังกฤษ",
            "ระบบตรวจสอบการคัดลอกผลงาน เพื่อรักษาจรรยาบรรณทางวิชาการ",
        ]),
        plo_mapping=[2, 4, 6],      # PLO ที่ชั้นปี 3 ส่งเสริม (4=PLO4.3)
    ),
    dict(
        year_number=4,
        title="การปฏิบัติจริงในโลกการทำงาน",
        indicators="\n".join([
            "ประยุกต์ความรู้ในงานสหกิจศึกษาได้จริง",
            "ปรับตัวเข้ากับสถานประกอบการได้ดี",
            "แสดงออกถึงจรรยาบรรณนักวิทยาศาสตร์",
        ]),
        assessment_methods="\n".join([
            "การประเมินโดยสถานประกอบการ (พี่เลี้ยง)",
            "การประเมินโดยอาจารย์นิเทศก์",
            "เล่มรายงานผลการปฏิบัติงานและการนำเสนอผลงานสหกิจศึกษา",
        ]),
        plo_mapping=[2, 3, 5],      # PLO ที่ชั้นปี 4 ส่งเสริม
    ),
]
db.replace_ylos(curriculum_id, ylos)
print(f"[Seed] YLOs: {len(ylos)} ชั้นปี")

# ── 4. ตรวจสอบ ───────────────────────────────────────────────────────────────
print("\n── ข้อมูลที่บันทึก ──────────────────────────────────")
for plo in db.get_plos(curriculum_id):
    print(f"  PLO {plo['plo_code']}: {plo['description'][:60]}")

print()
for ylo in db.get_ylos(curriculum_id):
    plo_codes = [
        next((p["plo_code"] for p in db.get_plos(curriculum_id)
              if p["plo_number"] == n), str(n))
        for n in ylo["plo_mapping"]
    ]
    print(f"  ชั้นปีที่ {ylo['year_number']} — {ylo['title']}")
    print(f"    → PLOs: {', '.join(plo_codes)}")

print("\n[Seed] เสร็จสมบูรณ์ ✓")
