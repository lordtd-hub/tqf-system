# วิเคราะห์ template มคอ.3 สำหรับ generate_tqf3
วันที่พบ: 2026-04-10

## สิ่งที่ต้องทำ
- [ ] เพิ่ม/ออกแบบ `course_teaching_plan` หรือขยาย `teaching_plan` ให้เก็บแผนสอนรายสัปดาห์แบบละเอียด: ช่วงสัปดาห์, LLO, หัวข้อ, กิจกรรม, สื่อ, วิธีประเมิน, ชั่วโมง
- [ ] ขยาย snapshot ระดับ `tqf3` ให้เก็บรายละเอียดการประเมินมากกว่า `name + weight_pct + clo_mapping` เช่น `full_score`, `assessment_period`, `eval_criteria`
- [ ] เพิ่มตาราง `course_resources` สำหรับหมวด 8 (หนังสือ/บทความ/เว็บไซต์/สื่อ) พร้อมรองรับรูปแบบ APA
- [ ] ตัดสินใจโครงสร้างหมวด 9 ว่าจะใช้ `instructors_json` แบบมี role หรือเพิ่มตารางใหม่ เช่น `tqf3_staff`
- [ ] แยก field ให้ชัดว่าอะไรเป็น "template ระดับวิชา" และอะไรเป็น "offering รายเทอม" ก่อนเริ่ม `generate_tqf3.py`

## สาเหตุ / บริบท
ตรวจไฟล์ `templates_ref/tqf3 Intro to AI.docx` เพื่อดูว่า template มคอ.3 แบบละเอียดต้องใช้ข้อมูลอะไรบ้างในการ generate เอกสารจากฐานข้อมูล

จาก template ตัวอย่าง พบว่าระบบปัจจุบันครอบคลุมเฉพาะหมวดหลักบางส่วนแล้ว (`courses`, `tqf3`, `course_clos`, `course_assessments`, `plos`) แต่ยังไม่พอสำหรับหมวด 6-9 และภาคผนวกในรูปแบบละเอียด

## สิ่งที่พบจาก template
- [x] หมวด 1: รหัสวิชา + ชื่อวิชาไทย/อังกฤษ
- [x] หมวด 2: หน่วยกิต เช่น `3(2-2-5)`
- [x] หมวด 3: ชื่อหลักสูตร + ประเภทรายวิชา
- [x] หมวด 4: คำอธิบายรายวิชาภาษาไทย/อังกฤษ และข้อความกำกับเรื่อง Active learning / CLO / PLO
- [x] หมวด 5: CLO รายข้อ + mapping ไป PLO โดยในตัวอย่างมีการอ้าง `PLO4.2`, `PLO6.1`, `PLO6.3`
- [x] หมวด 6: แผนการสอนรายสัปดาห์แบบละเอียด มี LLO, topic/content, learning activities, media/tools, assessment/evidence, ชั่วโมง และสรุป theory/practice/self-study รวม
- [x] หมวด 7: การวัดและประเมินผลระดับ CLO มีชื่อการประเมิน, ช่วงเวลาประเมิน, น้ำหนัก และเกณฑ์ตัดเกรด
- [x] หมวด 8: ทรัพยากรประกอบการเรียนรู้แบบอ้างอิง APA (หนังสือ เว็บไซต์ เครื่องมือ online)
- [x] หมวด 9: แยก "คณะกรรมการบริหารรายวิชา" ออกจาก "อาจารย์ผู้สอนรายวิชา"
- [x] ภาคผนวก: มีแบบฟอร์ม rubric / marking scheme / self & peer evaluation / แบบประเมิน CLO

## เชื่อมกับ schema ปัจจุบัน
- `courses` ครอบคลุม code, ชื่อไทย/อังกฤษ, หน่วยกิต, course_type, description_th, description_en ได้แล้ว
- `course_clos` + `plos` ครอบคลุมหมวด 5 ได้ในระดับหนึ่ง
- `course_assessments` มี `full_score`, `weight_pct`, `eval_criteria`, `pass_threshold` ซึ่งเหมาะกับ template ระดับวิชา
- `tqf3` + `clos` + `assessments` ใช้เป็น snapshot รายเทอมได้

## จุดที่ยังไม่พอ
- `teaching_plan` ปัจจุบันเก็บแค่ `week`, `topic`, `hours_planned`, `teaching_method` ซึ่งไม่พอสำหรับหมวด 6 แบบละเอียด
- `copy_course_template_to_tqf3()` ตอนนี้ copy แค่ `course_clos -> clos` และ `course_assessments -> assessments` ยังไม่ copy แผนการสอนรายสัปดาห์
- `assessments` ระดับ `tqf3` ยังไม่มี `full_score`, `assessment_period`, `eval_criteria`
- ยังไม่มีตารางเก็บ resources/textbooks/links สำหรับหมวด 8
- หมวด 9 ยังไม่มีโครงสร้าง role-based staff/member ชัดเจน

## ข้อเสนอ schema / implementation
- [ ] เพิ่ม `course_teaching_plan` เป็น template ระดับวิชา แล้ว copy ไป `teaching_plan` ตอน generate มคอ.3
- [ ] ขยาย `teaching_plan` ให้เก็บ `week_label`, `llo_text`, `activities`, `media`, `assessment_tools`, `hours_theory`, `hours_practice`, `hours_self`
- [ ] เพิ่ม `assessment_period` ใน `course_assessments` และ `assessments`
- [ ] เพิ่ม `course_resources(id, course_id, seq, resource_type, citation_text, url, note)`
- [ ] ตัดสินใจว่าจะเพิ่ม `tqf3_staff(id, tqf3_id, role, seq, name)` หรือใช้ JSON เดียวที่มี role

## ข้อสรุปเบื้องต้น
- [x] Template มคอ.3 ตัวอย่างยืนยันแล้วว่า `generate_tqf3.py` ไม่ควรเริ่มจาก `course_clos` + `course_assessments` อย่างเดียว
- [x] หมวด 6 เป็นช่องว่างใหญ่ที่สุดของ schema ปัจจุบัน
- [x] หมวด 8 และหมวด 9 ควรถูกออกแบบก่อนลงมือ generate เอกสารจริง
- [x] ภาคผนวกส่วนใหญ่สามารถเก็บเป็น static template ได้ก่อน ยังไม่จำเป็นต้อง normalize เป็น DB ทันที

## ไฟล์ที่เกี่ยวข้อง
- `templates_ref/tqf3 Intro to AI.docx` — template ตัวอย่างที่ใช้วิเคราะห์
- `database.py` — schema ปัจจุบัน และ `copy_course_template_to_tqf3()`
- `ROADMAP_v2.md` — แผน generate มคอ.3 เดิม
- `PROJECT_REFERENCE.md` — เอกสาร schema ปัจจุบัน
## อัปเดตการทำจริงใน `database.py` (2026-04-10)

- [x] เพิ่ม `course_teaching_plan`
- [x] ขยาย `teaching_plan` ให้เก็บ `week_label`, `llo_text`, `activities`, `media`, `assessment_tools`, `hours_theory`, `hours_practice`, `hours_self`
- [x] เพิ่ม `assessment_period` ใน `course_assessments` และ `assessments`
- [x] เพิ่ม `course_resources`
- [x] เพิ่ม `tqf3_staff`
- [x] เพิ่ม migration สำหรับคอลัมน์ใหม่ในฐานข้อมูลเก่า
- [x] เพิ่ม CRUD helper สำหรับ `course_teaching_plan`, `course_resources`, `tqf3_staff`
- [x] ปรับ `copy_course_template_to_tqf3()` ให้ copy detailed teaching plan และ detailed assessments

## งานที่ยังเหลือหลัง schema

- [ ] เชื่อม UI สำหรับกรอก/แก้ `course_teaching_plan`
- [ ] เชื่อม UI สำหรับกรอก/แก้ `course_resources`
- [ ] เชื่อม UI หรือ import flow สำหรับ `tqf3_staff`
- [ ] ใช้ข้อมูลใหม่เหล่านี้ใน `generate_tqf3.py`
