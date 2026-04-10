"""
input_gui.py — ระบบจัดการ TQF สาขาคณิตศาสตร์ มรส.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys, os, sqlite3, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ══════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════
BG        = "#F4F6F9"
BLUE_DARK = "#1F4E79"
BLUE      = "#2E75B6"
BLUE_LITE = "#DEEAF1"
GREEN     = "#107C10"
RED       = "#C50F1F"
GRAY      = "#6B7280"
WHITE     = "#FFFFFF"

FONT      = ("Arial", 10)
FONT_B    = ("Arial", 10, "bold")
FONT_SM   = ("Arial", 9)
FONT_H    = ("Arial", 12, "bold")


# ══════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════
class TQFApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ระบบ TQF — สาขาคณิตศาสตร์ มรส.")
        self.geometry("860x620")
        self.minsize(760, 500)
        self.configure(bg=BG)
        self._build_ui()
        self.after(300, self._refresh_courses)

    # ── UI skeleton ─────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BLUE_DARK, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="ระบบ TQF — สาขาวิชาคณิตศาสตร์  มหาวิทยาลัยราชภัฏสุราษฎร์ธานี",
                 bg=BLUE_DARK, fg=WHITE, font=("Arial", 12, "bold")).pack(side="left", padx=18, pady=14)
        tk.Button(hdr, text="⬇  Export Excel", bg="#107C10", fg=WHITE,
                  font=FONT_B, relief="flat", padx=14, pady=6,
                  cursor="hand2", activebackground="#0B5E0B", activeforeground=WHITE,
                  command=self._export_excel).pack(side="right", padx=14, pady=10)

        # Tabs
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=FONT_B, padding=[16, 8],
                        background="#D1DBE8", foreground=BLUE_DARK)
        style.map("TNotebook.Tab",
                  background=[("selected", WHITE)],
                  foreground=[("selected", BLUE_DARK)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_courses = tk.Frame(nb, bg=BG)
        self.tab_catalog = tk.Frame(nb, bg=BG)
        self.tab_import  = tk.Frame(nb, bg=BG)
        nb.add(self.tab_courses, text="  📋  รายวิชาในระบบ  ")
        nb.add(self.tab_catalog, text="  📚  ฐานข้อมูลหลักสูตร  ")
        nb.add(self.tab_import,  text="  📥  นำเข้าข้อมูล  ")

        self._build_tab_courses()
        self._build_tab_catalog()
        self._build_tab_import()

    # ══════════════════════════════════════════════════
    # TAB 1: รายวิชาในระบบ
    # ══════════════════════════════════════════════════
    def _build_tab_courses(self):
        tab = self.tab_courses

        # ── Toolbar ──────────────────────────────────
        bar = tk.Frame(tab, bg=BG)
        bar.pack(fill="x", padx=16, pady=(12, 6))
        tk.Label(bar, text="รายวิชาทั้งหมดในฐานข้อมูล",
                 bg=BG, font=FONT_H, fg=BLUE_DARK).pack(side="left")

        self.curriculum_var = tk.StringVar(value="ทั้งหมด")
        filter_frame = tk.Frame(bar, bg=BG)
        filter_frame.pack(side="right", padx=(0, 8))
        tk.Label(filter_frame, text="หลักสูตร:", bg=BG, font=FONT_SM).pack(side="left")
        self.curriculum_combo = ttk.Combobox(
            filter_frame, textvariable=self.curriculum_var,
            values=["ทั้งหมด"], width=8, state="readonly")
        self.curriculum_combo.pack(side="left", padx=(4, 8))
        self.curriculum_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_courses())
        tk.Button(bar, text="🔄  รีเฟรช", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=12, pady=4,
                  cursor="hand2", activebackground=BLUE_DARK, activeforeground=WHITE,
                  command=self._refresh_courses).pack(side="right")
        self.btn_gen = tk.Button(
            bar, text="📄  สร้าง มคอ.5", bg="#6C3483", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4,
            cursor="hand2", activebackground="#4A235A", activeforeground=WHITE,
            state="disabled", command=self._generate_tqf5)
        self.btn_gen.pack(side="right", padx=(0, 8))

        # ปุ่มแก้ไขข้อมูล
        self.btn_edit = tk.Button(
            bar, text="✏️  แก้ไขข้อมูล", bg="#2E7D32", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4,
            cursor="hand2", activebackground="#1B5E20", activeforeground=WHITE,
            state="disabled", command=self._edit_course)
        self.btn_edit.pack(side="right", padx=(0, 6))

        # ── PanedWindow แบ่งบน (ตาราง) / ล่าง (รายละเอียด) ──
        paned = tk.PanedWindow(tab, orient="vertical", bg=BG,
                               sashwidth=6, sashrelief="flat",
                               sashpad=2, opaqueresize=True)
        paned.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        # ── บน: Treeview ─────────────────────────────
        top_frame = tk.Frame(paned, bg=BG)
        paned.add(top_frame, minsize=180, stretch="always")

        style = ttk.Style()
        style.configure("Treeview", font=FONT_SM, rowheight=26,
                        background=WHITE, fieldbackground=WHITE)
        style.configure("Treeview.Heading", font=FONT_B,
                        background=BLUE_LITE, foreground=BLUE_DARK)
        style.map("Treeview", background=[("selected", BLUE_LITE)],
                  foreground=[("selected", BLUE_DARK)])

        cols = ("code","name","curriculum","sem_year","tqf3","grade","students","status","tqf3_id","course_id")
        self.tree = ttk.Treeview(top_frame, columns=cols, show="headings",
                                 selectmode="browse", height=10)
        heads = {
            "code":      ("รหัสวิชา",  90, "center"),
            "name":      ("ชื่อวิชา", 200, "w"),
            "curriculum":("หลักสูตร",  70, "center"),
            "sem_year":  ("ภาค/ปี",    70, "center"),
            "tqf3":      ("มคอ.3",     60, "center"),
            "grade":     ("เกรด",      60, "center"),
            "students":  ("นักศึกษา",  75, "center"),
            "status":    ("สถานะ",    130, "center"),
            "tqf3_id":   ("",           0, "center"),
            "course_id": ("",           0, "center"),
        }
        hidden = {"tqf3_id", "course_id"}
        for col, (heading, width, anchor) in heads.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor=anchor,
                             minwidth=0 if col in hidden else 50)
        self.tree.tag_configure("complete",  background="#E8F5E9")
        self.tree.tag_configure("partial",   background="#FFF8E1")
        self.tree.tag_configure("gradeonly", background="#FFF3E0")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        vsb = ttk.Scrollbar(top_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ── ล่าง: Detail Panel ───────────────────────
        bot_frame = tk.Frame(paned, bg=WHITE,
                             highlightbackground="#D1DBE8", highlightthickness=1)
        paned.add(bot_frame, minsize=120, stretch="never")

        # header ของ detail panel
        det_hdr = tk.Frame(bot_frame, bg=BLUE_LITE)
        det_hdr.pack(fill="x")
        self.detail_title = tk.Label(
            det_hdr, text="  เลือกวิชาในตารางเพื่อดูรายละเอียด",
            bg=BLUE_LITE, fg=BLUE_DARK, font=FONT_B, anchor="w")
        self.detail_title.pack(side="left", fill="x", expand=True, padx=8, pady=4)

        # แท็บ CLO / นักศึกษา ด้วย Radiobutton
        self.detail_tab_var = tk.StringVar(value="clo")
        tab_bar = tk.Frame(det_hdr, bg=BLUE_LITE)
        tab_bar.pack(side="right", padx=8)
        for text, val in [("📌 CLOs", "clo"), ("👥 นักศึกษา", "students")]:
            tk.Radiobutton(tab_bar, text=text, variable=self.detail_tab_var,
                           value=val, bg=BLUE_LITE, fg=BLUE_DARK,
                           font=FONT_SM, activebackground=BLUE_LITE,
                           selectcolor=WHITE, cursor="hand2",
                           command=self._switch_detail_tab).pack(side="left", padx=4)

        # กรอบ content
        det_content = tk.Frame(bot_frame, bg=WHITE)
        det_content.pack(fill="both", expand=True)

        # CLO Text
        self.clo_text = tk.Text(
            det_content, font=("Consolas", 9), bg=WHITE, fg="#212121",
            relief="flat", padx=10, pady=6, wrap="word",
            state="disabled", height=6)
        self.clo_vsb = ttk.Scrollbar(det_content, orient="vertical",
                                     command=self.clo_text.yview)
        self.clo_text.configure(yscrollcommand=self.clo_vsb.set)
        self.clo_text.tag_config("header", foreground=BLUE_DARK,
                                 font=("Arial", 9, "bold"))
        self.clo_text.tag_config("dim", foreground=GRAY)

        # Student Text
        self.stu_text = tk.Text(
            det_content, font=("Consolas", 9), bg=WHITE, fg="#212121",
            relief="flat", padx=10, pady=6, wrap="word",
            state="disabled", height=6)
        self.stu_vsb = ttk.Scrollbar(det_content, orient="vertical",
                                     command=self.stu_text.yview)
        self.stu_text.configure(yscrollcommand=self.stu_vsb.set)
        self.stu_text.tag_config("header", foreground=BLUE_DARK,
                                 font=("Arial", 9, "bold"))
        self.stu_text.tag_config("pass_a",  foreground="#1B5E20")
        self.stu_text.tag_config("pass_b",  foreground="#2E7D32")
        self.stu_text.tag_config("pass_c",  foreground="#E65100")
        self.stu_text.tag_config("fail",    foreground="#B71C1C")
        self.stu_text.tag_config("special", foreground="#6A1B9A")

        # เริ่มต้นแสดง CLO pane
        self._switch_detail_tab()

        # ── Status bar ───────────────────────────────
        self.status_var = tk.StringVar(value="กำลังโหลด...")
        tk.Label(tab, textvariable=self.status_var,
                 bg=BG, fg=GRAY, font=FONT_SM, anchor="w").pack(
                 fill="x", padx=18, pady=(0, 6))

    def _switch_detail_tab(self):
        """สลับระหว่างแท็บ CLO และนักศึกษา"""
        tab = self.detail_tab_var.get()
        # ซ่อนทั้งสอง
        self.clo_text.pack_forget()
        self.clo_vsb.pack_forget()
        self.stu_text.pack_forget()
        self.stu_vsb.pack_forget()
        # แสดงอันที่เลือก
        if tab == "clo":
            self.clo_vsb.pack(side="right", fill="y")
            self.clo_text.pack(side="left", fill="both", expand=True)
        else:
            self.stu_vsb.pack(side="right", fill="y")
            self.stu_text.pack(side="left", fill="both", expand=True)

    def _refresh_courses(self):
        """โหลดข้อมูลรายวิชาจาก DB มาแสดงใน Treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            import database as db
            db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row

            # อัปเดต dropdown หลักสูตร
            curricula = conn.execute("SELECT version, name_th FROM curricula ORDER BY version").fetchall()
            curr_labels = ["ทั้งหมด"] + [f"หลักสูตร {r['version']}" for r in curricula]
            self.curriculum_combo["values"] = curr_labels

            # filter condition
            cur_filter = self.curriculum_var.get()
            where_clause = ""
            if cur_filter != "ทั้งหมด":
                ver = cur_filter.replace("หลักสูตร ", "").strip()
                where_clause = f"AND cu.version = '{ver}'"

            # LEFT JOIN tqf3 → แสดงวิชาทุกวิชา แม้ยังไม่มี มคอ.3
            rows = conn.execute(f"""
                SELECT c.id AS course_id, c.code, c.name_th,
                       c.course_type,
                       COALESCE(cu.version, '?') AS cur_ver,
                       t.semester, t.year,
                       t.source_file,
                       t.id AS tqf3_id,
                       COALESCE(t.is_special, 0) AS is_special,
                       COALESCE(t5.registered_count, 0) AS students,
                       COALESCE(t5.remaining_count, 0)  AS remaining,
                       COALESCE(t5.withdrawn_count, 0)  AS withdrawn,
                       COALESCE((SELECT COUNT(*) FROM clos cl WHERE cl.tqf3_id=t.id), 0) AS clo_count,
                       CASE WHEN t5.id IS NOT NULL THEN 1 ELSE 0 END AS has_grade
                FROM courses c
                LEFT JOIN curricula cu ON cu.id = c.curriculum_id
                LEFT JOIN tqf3 t ON t.course_id = c.id
                LEFT JOIN tqf5 t5 ON t5.tqf3_id = t.id
                WHERE 1=1 {where_clause}
                ORDER BY cu.version, c.course_type, c.code, t.year DESC, t.semester DESC
            """).fetchall()
            conn.close()

            for r in rows:
                has_tqf3  = bool(r["source_file"] and r["clo_count"] > 0)
                has_grade = bool(r["has_grade"] and r["students"] > 0)

                tqf3_icon  = "✅" if has_tqf3  else "—"
                grade_icon = "✅" if has_grade else "—"
                is_special = bool(r["is_special"])
                sem_year_base = f"{r['semester']}/{r['year']}" if r["semester"] else "—"
                sem_year = f"★{sem_year_base}" if is_special else sem_year_base

                sp_label = "  [พิเศษ]" if is_special else ""
                if has_tqf3 and has_grade:
                    status, tag = f"✅ พร้อมสร้าง มคอ.5{sp_label}", "complete"
                elif has_tqf3:
                    status, tag = f"⏳ รอนำเข้าเกรด{sp_label}", "partial"
                elif has_grade:
                    status, tag = f"⏳ รอนำเข้า มคอ.3{sp_label}", "gradeonly"
                else:
                    status, tag = "— ยังไม่มีข้อมูล", ""

                self.tree.insert("", "end", tags=(tag,), values=(
                    r["code"],
                    r["name_th"] or "(ยังไม่มีชื่อ)",
                    r["cur_ver"],
                    sem_year,
                    tqf3_icon,
                    grade_icon,
                    f"{r['students']} คน" if r["students"] else "—",
                    status,
                    r["tqf3_id"] or "",   # hidden tqf3_id  [index 8]
                    r["course_id"] or "",  # hidden course_id [index 9]
                ))

            total = len(rows)
            has_data = sum(1 for r in rows if r["source_file"])
            ready    = sum(1 for r in rows
                           if r["source_file"] and r["clo_count"] > 0
                           and r["has_grade"] and r["students"] > 0)
            self.status_var.set(
                f"รายวิชา {total} วิชา  |  มีข้อมูล มคอ.3: {has_data}  |  พร้อมสร้าง มคอ.5: {ready}")

        except Exception as e:
            self.status_var.set(f"❌ โหลดข้อมูลไม่ได้: {e}")

    def _on_tree_select(self, event=None):
        """คลิกเลือกแถว → โหลดรายละเอียดใน panel ล่าง"""
        sel = self.tree.selection()
        if not sel:
            self.btn_gen.config(state="disabled")
            self.btn_edit.config(state="disabled")
            self._clear_detail()
            return
        vals = self.tree.item(sel[0], "values")
        tqf3_id  = vals[8] if len(vals) > 8 else ""
        course_id = vals[9] if len(vals) > 9 else ""
        self.btn_gen.config(state="normal" if tqf3_id else "disabled")
        self.btn_edit.config(state="normal" if course_id else "disabled")
        if tqf3_id:
            self._load_detail(int(tqf3_id), vals)
        else:
            self._clear_detail()

    def _on_tree_double_click(self, event=None):
        """Double-click → สลับไปแท็บ นักศึกษา"""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if vals[8] if len(vals) > 8 else "":
            self.detail_tab_var.set("students")
            self._switch_detail_tab()

    def _clear_detail(self):
        for txt in (self.clo_text, self.stu_text):
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.configure(state="disabled")
        self.detail_title.config(text="  เลือกวิชาในตารางเพื่อดูรายละเอียด")

    def _load_detail(self, tqf3_id: int, vals):
        """โหลด CLO + เกรดนักศึกษาจาก DB แสดงใน panel ล่าง"""
        code, name = vals[0], vals[1]
        sem_year   = vals[3]
        self.detail_title.config(
            text=f"  {code}  {name}  —  ภาค {sem_year}")

        try:
            import database as db
            db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row

            clos = conn.execute("""
                SELECT clo_number, description, teaching_strategy,
                       assessment_method, target_pct
                FROM clos WHERE tqf3_id=? ORDER BY clo_number
            """, (tqf3_id,)).fetchall()

            t5 = conn.execute(
                "SELECT id, registered_count, remaining_count, "
                "withdrawn_count, grade_dist_json "
                "FROM tqf5 WHERE tqf3_id=?", (tqf3_id,)).fetchone()

            students = []
            dist = {}
            if t5:
                students = conn.execute(
                    "SELECT student_id, grade FROM student_grades "
                    "WHERE tqf5_id=? ORDER BY student_id",
                    (t5["id"],)).fetchall()
                try:
                    dist = json.loads(t5["grade_dist_json"] or "{}")
                except Exception:
                    dist = {}
            conn.close()
        except Exception as e:
            self._set_text(self.clo_text, f"❌ โหลดข้อมูลไม่ได้: {e}")
            return

        # ── เติม CLO text ────────────────────────────
        self.clo_text.configure(state="normal")
        self.clo_text.delete("1.0", "end")
        if clos:
            self.clo_text.insert("end",
                f"{'ข้อ':<5}  {'ผลลัพธ์การเรียนรู้ (CLO)':<62}  {'วิธีสอน':<22}  {'ประเมิน':<22}  เป้า\n",
                "header")
            self.clo_text.insert("end", "─"*130 + "\n", "dim")
            for r in clos:
                tgt = f"{r['target_pct']:.0f}%" if r["target_pct"] else "—"
                self.clo_text.insert("end",
                    f"CLO{r['clo_number']:<3}  "
                    f"{(r['description'] or '—')[:62]:<62}  "
                    f"{(r['teaching_strategy'] or '—')[:22]:<22}  "
                    f"{(r['assessment_method'] or '—')[:22]:<22}  {tgt}\n")
        else:
            self.clo_text.insert("end", "ยังไม่มีข้อมูล CLO\n", "dim")
        self.clo_text.configure(state="disabled")

        # ── เติม Student text ────────────────────────
        self.stu_text.configure(state="normal")
        self.stu_text.delete("1.0", "end")
        if t5:
            dist_str = "   ".join(
                f"{g}={v}" for g, v in dist.items() if v and int(v) > 0)
            self.stu_text.insert("end",
                f"ลงทะเบียน {t5['registered_count']} คน  |  "
                f"คงอยู่ {t5['remaining_count']}  |  "
                f"ถอน {t5['withdrawn_count']}  |  {dist_str}\n",
                "header")
            self.stu_text.insert("end", "─"*80 + "\n", "dim")
        if students:
            grade_tag = {
                "A": "pass_a", "B+": "pass_a", "B": "pass_b",
                "C+": "pass_b", "C": "pass_c",
                "D+": "fail", "D": "fail", "E": "fail", "F": "fail",
                "W": "special", "I": "special",
            }
            for i, r in enumerate(students, 1):
                g = (r["grade"] or "").strip()
                tag = grade_tag.get(g, "")
                self.stu_text.insert("end",
                    f"{i:>4}.  {r['student_id']}    {g or '—'}\n", tag)
        elif t5:
            self.stu_text.insert("end", "ไม่มีข้อมูลรายชื่อนักศึกษา\n", "dim")
        else:
            self.stu_text.insert("end", "ยังไม่มีข้อมูลเกรด\n", "dim")
        self.stu_text.configure(state="disabled")

    def _edit_course(self):
        """เปิด dialog แก้ไขข้อมูลวิชาที่เลือก"""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        course_id = vals[9] if len(vals) > 9 else ""
        tqf3_id   = vals[8] if len(vals) > 8 else ""
        if not course_id:
            return
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT c.id, c.code, c.name_th, c.course_type, c.curriculum_id, "
                "       cu.version AS cur_ver "
                "FROM courses c "
                "LEFT JOIN curricula cu ON cu.id = c.curriculum_id "
                "WHERE c.id = ?", (int(course_id),)).fetchone()
            curricula = conn.execute(
                "SELECT id, version, name_th FROM curricula ORDER BY version"
            ).fetchall()
            tqf3_row = None
            if tqf3_id:
                tqf3_row = conn.execute(
                    "SELECT id, semester, year FROM tqf3 WHERE id=?",
                    (int(tqf3_id),)).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดข้อมูลไม่ได้: {e}", parent=self)
            return

        if not course:
            messagebox.showerror("ข้อผิดพลาด", "ไม่พบข้อมูลวิชา", parent=self)
            return

        dlg = CourseEditDialog(self, course, curricula, tqf3_row)
        if dlg.result:
            # บันทึก courses
            try:
                import database as db; db.init_db()
                conn = sqlite3.connect(db.DB_PATH)
                conn.execute(
                    "UPDATE courses SET curriculum_id=?, course_type=? WHERE id=?",
                    (dlg.result["curriculum_id"], dlg.result["course_type"], int(course_id)))
                # บันทึก tqf3 (ถ้ามี)
                if tqf3_id and dlg.result.get("semester") and dlg.result.get("year"):
                    conn.execute(
                        "UPDATE tqf3 SET semester=?, year=?, is_special=? WHERE id=?",
                        (dlg.result["semester"], dlg.result["year"],
                         int(bool(dlg.result.get("is_special", False))),
                         int(tqf3_id)))
                conn.commit()
                conn.close()
                messagebox.showinfo("สำเร็จ",
                    f"บันทึกข้อมูล {course['code']} เรียบร้อย", parent=self)
                self._refresh_courses()
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _generate_tqf5(self):
        """สร้างไฟล์ มคอ.5 จากวิชาที่เลือกใน Treeview"""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        tqf3_id = vals[8] if len(vals) > 8 else ""
        course_code = vals[0]
        if not tqf3_id:
            messagebox.showwarning("ไม่มีข้อมูล", "ไม่พบ มคอ.3 สำหรับวิชานี้", parent=self)
            return

        out_path = filedialog.asksaveasfilename(
            title=f"บันทึก มคอ.5 — {course_code}",
            defaultextension=".docx",
            initialfile=f"มคอ5_{course_code}.docx",
            filetypes=[("Word Document", "*.docx")]
        )
        if not out_path:
            return

        def do():
            try:
                import database as db; db.init_db()
                from generate_tqf5 import generate_tqf5_docx
                result = generate_tqf5_docx(int(tqf3_id), out_path)
                self.after(0, lambda: messagebox.showinfo(
                    "สำเร็จ",
                    f"สร้าง มคอ.5 เสร็จแล้ว\n{out_path}",
                    parent=self))
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror(
                    "เกิดข้อผิดพลาด",
                    f"สร้าง มคอ.5 ไม่สำเร็จ:\n{e}", parent=self))

        threading.Thread(target=do, daemon=True).start()

    # ══════════════════════════════════════════════════
    # TAB 2: ฐานข้อมูลหลักสูตร (Course Catalog)
    # ══════════════════════════════════════════════════
    def _build_tab_catalog(self):
        tab = self.tab_catalog

        # ── Toolbar ──────────────────────────────────
        bar = tk.Frame(tab, bg=BG)
        bar.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(bar, text="หลักสูตร:", bg=BG, font=FONT_B).pack(side="left")
        self.cat_cur_var = tk.StringVar(value="ทั้งหมด")
        self.cat_cur_combo = ttk.Combobox(
            bar, textvariable=self.cat_cur_var, values=["ทั้งหมด"],
            width=10, state="readonly")
        self.cat_cur_combo.pack(side="left", padx=(4, 12))
        self.cat_cur_combo.bind("<<ComboboxSelected>>",
                                lambda e: self._refresh_catalog())

        # ปุ่มขวา
        tk.Button(bar, text="📚  PLO", bg="#5C4033", fg=WHITE,
                  font=FONT_B, relief="flat", padx=12, pady=4,
                  cursor="hand2", activebackground="#3E2723", activeforeground=WHITE,
                  command=self._manage_plos).pack(side="right", padx=(0, 6))
        self.btn_cat_del = tk.Button(
            bar, text="🗑  ลบวิชา", bg=RED, fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", state="disabled", command=self._delete_catalog_course)
        self.btn_cat_del.pack(side="right", padx=(0, 6))
        self.btn_cat_clo = tk.Button(
            bar, text="📝  แก้ไข CLO", bg="#1565C0", fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", state="disabled", command=self._edit_course_clos)
        self.btn_cat_clo.pack(side="right", padx=(0, 6))
        self.btn_cat_edit = tk.Button(
            bar, text="✏️  แก้ไขวิชา", bg=BLUE, fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", state="disabled", command=self._edit_catalog_course)
        self.btn_cat_edit.pack(side="right", padx=(0, 6))
        tk.Button(bar, text="＋  เพิ่มวิชา", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=14, pady=4,
                  cursor="hand2", activebackground="#0B5E0B", activeforeground=WHITE,
                  command=self._add_catalog_course).pack(side="right", padx=(0, 6))

        # ── PanedWindow ──────────────────────────────
        paned = tk.PanedWindow(tab, orient="horizontal", bg=BG,
                               sashwidth=6, sashrelief="flat", opaqueresize=True)
        paned.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        # ── ซ้าย: ตารางวิชา ──────────────────────────
        left = tk.Frame(paned, bg=BG)
        paned.add(left, minsize=300, stretch="never")

        cat_cols = ("code", "name", "credits", "type", "clo_count", "course_id")
        self.cat_tree = ttk.Treeview(
            left, columns=cat_cols, show="headings",
            selectmode="browse", height=20)
        cat_heads = {
            "code":      ("รหัสวิชา",  90, "center"),
            "name":      ("ชื่อวิชา", 180, "w"),
            "credits":   ("หน่วยกิต",  70, "center"),
            "type":      ("ประเภท",   100, "w"),
            "clo_count": ("CLO",       45, "center"),
            "course_id": ("",           0, "center"),
        }
        for col, (heading, width, anchor) in cat_heads.items():
            self.cat_tree.heading(col, text=heading)
            self.cat_tree.column(col, width=width, anchor=anchor,
                                 minwidth=0 if col == "course_id" else 40)
        self.cat_tree.bind("<<TreeviewSelect>>", self._on_catalog_select)
        cat_vsb = ttk.Scrollbar(left, orient="vertical", command=self.cat_tree.yview)
        self.cat_tree.configure(yscrollcommand=cat_vsb.set)
        self.cat_tree.pack(side="left", fill="both", expand=True)
        cat_vsb.pack(side="right", fill="y")

        # ── ขวา: รายละเอียด ──────────────────────────
        right = tk.Frame(paned, bg=WHITE,
                         highlightbackground="#D1DBE8", highlightthickness=1)
        paned.add(right, minsize=320, stretch="always")

        det_hdr = tk.Frame(right, bg=BLUE_LITE)
        det_hdr.pack(fill="x")
        self.cat_detail_title = tk.Label(
            det_hdr, text="  เลือกวิชาในตารางเพื่อดูรายละเอียด",
            bg=BLUE_LITE, fg=BLUE_DARK, font=FONT_B, anchor="w")
        self.cat_detail_title.pack(fill="x", padx=8, pady=4)

        self.cat_detail_text = tk.Text(
            right, font=("Consolas", 9), bg=WHITE, fg="#212121",
            relief="flat", padx=10, pady=6, wrap="word",
            state="disabled")
        cat_vsb2 = ttk.Scrollbar(right, orient="vertical",
                                  command=self.cat_detail_text.yview)
        self.cat_detail_text.configure(yscrollcommand=cat_vsb2.set)
        self.cat_detail_text.tag_config("h1", foreground=BLUE_DARK,
                                        font=("Arial", 10, "bold"))
        self.cat_detail_text.tag_config("h2", foreground=BLUE,
                                        font=("Arial", 9, "bold"))
        self.cat_detail_text.tag_config("dim", foreground=GRAY)
        self.cat_detail_text.tag_config("ok",  foreground="#1B5E20")
        self.cat_detail_text.tag_config("warn", foreground="#E65100")
        cat_vsb2.pack(side="right", fill="y")
        self.cat_detail_text.pack(side="left", fill="both", expand=True)

        # status bar
        self.cat_status_var = tk.StringVar(value="")
        tk.Label(tab, textvariable=self.cat_status_var,
                 bg=BG, fg=GRAY, font=FONT_SM, anchor="w").pack(
                 fill="x", padx=18, pady=(0, 6))

        self.after(350, self._refresh_catalog)

    def _refresh_catalog(self):
        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row

            curricula = conn.execute(
                "SELECT id, version FROM curricula ORDER BY version").fetchall()
            cur_labels = ["ทั้งหมด"] + [f"หลักสูตร {r['version']}" for r in curricula]
            self.cat_cur_combo["values"] = cur_labels

            where = ""
            filt = self.cat_cur_var.get()
            if filt != "ทั้งหมด":
                ver = filt.replace("หลักสูตร ", "").strip()
                where = f"AND cu.version='{ver}'"

            rows = conn.execute(f"""
                SELECT c.id, c.code, c.name_th, c.credits_text, c.course_type,
                       COALESCE(cu.version,'?') AS cur_ver,
                       (SELECT COUNT(*) FROM course_clos cc WHERE cc.course_id=c.id) AS clo_cnt
                FROM courses c
                LEFT JOIN curricula cu ON cu.id = c.curriculum_id
                WHERE 1=1 {where}
                ORDER BY cu.version, c.course_type, c.code
            """).fetchall()
            conn.close()

            for r in rows:
                self.cat_tree.insert("", "end", values=(
                    r["code"], r["name_th"] or "(ไม่มีชื่อ)",
                    r["credits_text"] or "—",
                    r["course_type"] or "—",
                    r["clo_cnt"] if r["clo_cnt"] else "—",
                    r["id"],
                ))

            n = len(rows)
            has_clo = sum(1 for r in rows if r["clo_cnt"] > 0)
            self.cat_status_var.set(
                f"รายวิชา {n} วิชา  |  มี CLO มาตรฐาน {has_clo} วิชา")
        except Exception as e:
            self.cat_status_var.set(f"❌ โหลดไม่ได้: {e}")

    def _on_catalog_select(self, event=None):
        sel = self.cat_tree.selection()
        state = "normal" if sel else "disabled"
        self.btn_cat_edit.config(state=state)
        self.btn_cat_del.config(state=state)
        self.btn_cat_clo.config(state=state)
        if not sel:
            self._clear_cat_detail(); return

        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        self._load_cat_detail(course_id, vals)

    def _clear_cat_detail(self):
        self.cat_detail_text.configure(state="normal")
        self.cat_detail_text.delete("1.0", "end")
        self.cat_detail_text.configure(state="disabled")
        self.cat_detail_title.config(
            text="  เลือกวิชาในตารางเพื่อดูรายละเอียด")

    def _load_cat_detail(self, course_id: int, vals):
        self.cat_detail_title.config(
            text=f"  {vals[0]}  {vals[1]}")
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT c.*, cu.version AS cur_ver "
                "FROM courses c LEFT JOIN curricula cu ON cu.id=c.curriculum_id "
                "WHERE c.id=?", (course_id,)).fetchone()
            clos = conn.execute(
                "SELECT * FROM course_clos WHERE course_id=? ORDER BY clo_number",
                (course_id,)).fetchall()
            asmt = conn.execute(
                "SELECT * FROM course_assessments WHERE course_id=? ORDER BY seq,id",
                (course_id,)).fetchall()
            # ดึง plos สำหรับ mapping
            plo_map = {}
            if course and course["curriculum_id"]:
                plos = conn.execute(
                    "SELECT plo_number, description FROM plos WHERE curriculum_id=?",
                    (course["curriculum_id"],)).fetchall()
                plo_map = {r["plo_number"]: r["description"] for r in plos}
            # นับการเปิดสอน
            offerings = conn.execute(
                "SELECT semester, year, is_special, source_type FROM tqf3 "
                "WHERE course_id=? ORDER BY year DESC, semester DESC",
                (course_id,)).fetchall()
            conn.close()
        except Exception as e:
            self._set_cat_detail(f"❌ โหลดไม่ได้: {e}"); return

        t = self.cat_detail_text
        t.configure(state="normal")
        t.delete("1.0", "end")

        # ── ข้อมูลทั่วไป ──
        t.insert("end", "ข้อมูลทั่วไป\n", "h1")
        t.insert("end", "─" * 60 + "\n", "dim")
        cr = dict(course) if course else {}
        t.insert("end", f"หลักสูตร  : {cr.get('cur_ver','?')}\n")
        t.insert("end", f"รหัสวิชา  : {cr.get('code','')}\n")
        t.insert("end", f"ชื่อไทย   : {cr.get('name_th','')}\n")
        t.insert("end", f"ชื่ออังกฤษ: {cr.get('name_en','') or '—'}\n")
        t.insert("end", f"หน่วยกิต  : {cr.get('credits_text','') or '—'}"
                 f"  (บรรยาย-ปฏิบัติ-ค้นคว้า: "
                 f"{cr.get('credit_lecture',0)}-{cr.get('credit_lab',0)}-{cr.get('credit_self',0)})\n")
        t.insert("end", f"ประเภท    : {cr.get('course_type','') or '—'}\n")
        t.insert("end", f"บังคับก่อน: {cr.get('prerequisite','') or 'ไม่มี'}\n")
        if cr.get("description_th"):
            t.insert("end", f"คำอธิบาย  : {cr['description_th']}\n")

        # ── การเปิดสอน ──
        t.insert("end", f"\nการเปิดสอน ({len(offerings)} ครั้ง)\n", "h1")
        t.insert("end", "─" * 60 + "\n", "dim")
        if offerings:
            for o in offerings:
                sp = " [พิเศษ]" if o["is_special"] else ""
                src = " ★generated" if o["source_type"] == "generated" else ""
                t.insert("end", f"  ภาค {o['semester']}/{o['year']}{sp}{src}\n", "ok")
        else:
            t.insert("end", "  ยังไม่เคยเปิดสอน\n", "dim")

        # ── CLO มาตรฐาน ──
        t.insert("end", f"\nCLO มาตรฐาน ({len(clos)} ข้อ)\n", "h1")
        t.insert("end", "─" * 60 + "\n", "dim")
        if clos:
            for c in clos:
                plo_nums = json.loads(c["plo_mapping"] if c["plo_mapping"] else "[]")
                plo_str = ", ".join(f"PLO{p}" for p in plo_nums) if plo_nums else "—"
                t.insert("end", f"CLO{c['clo_number']}  ", "h2")
                t.insert("end", f"{c['description'] or '(ยังไม่มีคำอธิบาย)'}\n")
                t.insert("end",
                    f"       ตอบสนอง: {plo_str}  |  "
                    f"เกณฑ์ผ่าน: {c['pass_threshold_pct']:.0f}%  |  "
                    f"วิธีสอน: {c['teaching_strategy'] or '—'}\n", "dim")
        else:
            t.insert("end", "  ยังไม่มี CLO มาตรฐาน — กด 📝 แก้ไข CLO เพื่อเพิ่ม\n", "warn")

        # ── แผนการประเมิน ──
        total_w = sum(a["weight_pct"] for a in asmt)
        t.insert("end", f"\nแผนการประเมิน ({len(asmt)} รายการ  รวม {total_w:.0f}%)\n", "h1")
        t.insert("end", "─" * 60 + "\n", "dim")
        if asmt:
            for a in asmt:
                t.insert("end", f"  {a['name']:<20}", "h2")
                t.insert("end",
                    f"  คะแนนเต็ม {a['full_score']:.0f}  |  "
                    f"น้ำหนัก {a['weight_pct']:.0f}%  |  "
                    f"ผ่าน {a['pass_threshold']:.0f}%\n")
            if abs(total_w - 100) > 0.5:
                t.insert("end",
                    f"  ⚠ รวม {total_w:.0f}% (ควรได้ 100%)\n", "warn")
        else:
            t.insert("end", "  ยังไม่มีแผนการประเมิน\n", "dim")

        t.configure(state="disabled")

    def _set_cat_detail(self, msg: str):
        self.cat_detail_text.configure(state="normal")
        self.cat_detail_text.delete("1.0", "end")
        self.cat_detail_text.insert("end", msg)
        self.cat_detail_text.configure(state="disabled")

    def _add_catalog_course(self):
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            curricula = conn.execute(
                "SELECT id, version, name_th FROM curricula ORDER BY version"
            ).fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดข้อมูลไม่ได้: {e}", parent=self)
            return
        dlg = CourseAddDialog(self, curricula)
        if dlg.result:
            try:
                import database as db; db.init_db()
                db.upsert_course(**dlg.result)
                self._refresh_catalog()
                self._refresh_courses()
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _edit_catalog_course(self):
        sel = self.cat_tree.selection()
        if not sel: return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
            curricula = conn.execute(
                "SELECT id, version, name_th FROM curricula ORDER BY version"
            ).fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self); return

        dlg = CourseAddDialog(self, curricula, existing=course)
        if dlg.result:
            try:
                import database as db; db.init_db()
                conn = sqlite3.connect(db.DB_PATH)
                conn.execute("""
                    UPDATE courses SET
                        name_th=?, name_en=?, credits_text=?,
                        credit_lecture=?, credit_lab=?, credit_self=?,
                        course_type=?, prerequisite=?,
                        description_th=?, curriculum_id=?
                    WHERE id=?
                """, (dlg.result["name_th"], dlg.result.get("name_en",""),
                      dlg.result.get("credits_text",""),
                      dlg.result.get("credit_lecture",0), dlg.result.get("credit_lab",0),
                      dlg.result.get("credit_self",0),
                      dlg.result.get("course_type",""), dlg.result.get("prerequisite","ไม่มี"),
                      dlg.result.get("description_th",""), dlg.result["curriculum_id"],
                      course_id))
                conn.commit(); conn.close()
                self._refresh_catalog(); self._refresh_courses()
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _delete_catalog_course(self):
        sel = self.cat_tree.selection()
        if not sel: return
        vals = self.cat_tree.item(sel[0], "values")
        course_id, code = int(vals[5]), vals[0]
        if not messagebox.askyesno("ยืนยันการลบ",
                f"ลบวิชา {code} ออกจากฐานข้อมูล?\n"
                "(ข้อมูล มคอ.3, เกรด, มคอ.5 ที่เกี่ยวข้องจะถูกลบด้วย)",
                parent=self): return
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
            conn.commit(); conn.close()
            self._refresh_catalog(); self._refresh_courses()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ลบไม่สำเร็จ: {e}", parent=self)

    def _edit_course_clos(self):
        sel = self.cat_tree.selection()
        if not sel: return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT c.*, cu.version AS cur_ver, cu.id AS cur_id "
                "FROM courses c LEFT JOIN curricula cu ON cu.id=c.curriculum_id "
                "WHERE c.id=?", (course_id,)).fetchone()
            clos  = db.get_course_clos(course_id)
            asmt  = db.get_course_assessments(course_id)
            plos  = db.get_plos(course["cur_id"]) if course and course["cur_id"] else []
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self); return

        dlg = CourseCLOEditor(self, course, clos, asmt, plos)
        if dlg.result:
            try:
                import database as db; db.init_db()
                db.replace_course_clos(course_id, dlg.result["clos"])
                db.replace_course_assessments(course_id, dlg.result["assessments"])
                self._refresh_catalog()
                self._load_cat_detail(course_id, vals)
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _manage_plos(self):
        filt = self.cat_cur_var.get()
        if filt == "ทั้งหมด":
            messagebox.showinfo("แจ้งเตือน",
                "กรุณาเลือกหลักสูตรก่อน แล้วกด 📚 PLO", parent=self)
            return
        ver = filt.replace("หลักสูตร ", "").strip()
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            curr = conn.execute(
                "SELECT * FROM curricula WHERE version=?", (ver,)).fetchone()
            plos = db.get_plos(curr["id"]) if curr else []
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self); return

        dlg = PLOManagerDialog(self, curr, plos)
        if dlg.result is not None:
            try:
                import database as db; db.init_db()
                db.replace_plos(curr["id"], dlg.result)
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    # ══════════════════════════════════════════════════
    # TAB 3: นำเข้าข้อมูล
    # ══════════════════════════════════════════════════
    def _build_tab_import(self):
        tab = self.tab_import

        tk.Label(tab, text="นำเข้าข้อมูลเข้าสู่ระบบ",
                 bg=BG, font=FONT_H, fg=BLUE_DARK).pack(anchor="w", padx=18, pady=(14, 8))

        cards = tk.Frame(tab, bg=BG)
        cards.pack(fill="x", padx=16)

        self._card(cards,
            icon="📄",
            title="นำเข้า มคอ.3",
            desc="รองรับ .doc, .rtf, .docx\nระบบดึงข้อมูลรายวิชา, CLOs และแผนการสอนอัตโนมัติ",
            btn="เลือกไฟล์ มคอ.3",
            cmd=self._import_tqf3, col=0)

        self._card(cards,
            icon="📊",
            title="นำเข้าไฟล์เกรด",
            desc="รองรับ .doc, .rtf, .docx\nนำเข้าได้ก่อนหรือหลัง มคอ.3 ก็ได้",
            btn="เลือกไฟล์เกรด",
            cmd=self._import_grades, col=1)

        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        # Log
        tk.Label(tab, text="ผลการดำเนินการ",
                 bg=BG, fg=BLUE_DARK, font=FONT_B).pack(anchor="w", padx=18, pady=(12, 4))

        log_wrap = tk.Frame(tab, bg=BG)
        log_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.log = tk.Text(log_wrap, font=("Consolas", 9),
                           bg="#1E1E1E", fg="#D4D4D4",
                           relief="flat", padx=8, pady=6,
                           wrap="word", state="disabled")
        sb = ttk.Scrollbar(log_wrap, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.log.tag_config("ok",  foreground="#4EC9B0")
        self.log.tag_config("err", foreground="#F44747")
        self.log.tag_config("hdr", foreground="#569CD6")
        self._log("ℹ  ระบบพร้อมใช้งาน — เลือกไฟล์เพื่อนำเข้าข้อมูล", "hdr")

    def _card(self, parent, icon, title, desc, btn, cmd, col):
        f = tk.Frame(parent, bg=WHITE, relief="flat",
                     highlightbackground="#D1DBE8", highlightthickness=1)
        f.grid(row=0, column=col, sticky="nsew",
               padx=(0 if col else 0, 6 if col == 0 else 0), pady=4, ipady=8, ipadx=10)

        tk.Label(f, text=f"{icon}  {title}", bg=WHITE, fg=BLUE_DARK,
                 font=FONT_B).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(f, text=desc, bg=WHITE, fg=GRAY,
                 font=FONT_SM, justify="left").pack(anchor="w", padx=12)
        tk.Button(f, text=btn, bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=14, pady=5, cursor="hand2",
                  activebackground=BLUE_DARK, activeforeground=WHITE,
                  command=cmd).pack(anchor="e", padx=12, pady=(8, 6))

    # ── Log ─────────────────────────────────────────
    def _log(self, msg, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", tag or "")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ══════════════════════════════════════════════════
    # IMPORT มคอ.3
    # ══════════════════════════════════════════════════
    def _import_tqf3(self):
        files = filedialog.askopenfilenames(
            title="เลือกไฟล์ มคอ.3",
            filetypes=[("Word / PDF", "*.docx *.doc *.rtf *.pdf"), ("ทุกไฟล์", "*.*")]
        )
        if files:
            threading.Thread(target=self._do_import_tqf3, args=(files,), daemon=True).start()

    def _do_import_tqf3(self, files):
        try:
            import database as db; db.init_db()
            from import_tqf3 import import_tqf3
        except Exception as e:
            self._log(f"❌ โหลด module ไม่ได้: {e}", "err"); return

        self._log(f"\n── นำเข้า มคอ.3 ({len(files)} ไฟล์) ──────────────", "hdr")
        ok = 0
        for f in files:
            try:
                r = import_tqf3(f)
                self._log(f"✅  {r['code']}  {r['name_th']}", "ok")
                self._log(f"    ภาค {r['semester']}/{r['year']}  |  CLOs {r['clos_count']} ข้อ  |  แผนการสอน {r['plan_weeks']} สัปดาห์")
                ok += 1
            except Exception as e:
                self._log(f"❌  {os.path.basename(f)}: {e}", "err")

        self._log(f"เสร็จ {ok}/{len(files)} ไฟล์", "ok" if ok == len(files) else "err")
        self.after(0, self._refresh_courses)

    # ══════════════════════════════════════════════════
    # IMPORT เกรด
    # ══════════════════════════════════════════════════
    def _import_grades(self):
        files = filedialog.askopenfilenames(
            title="เลือกไฟล์เกรด",
            filetypes=[("Word / PDF", "*.docx *.doc *.rtf *.pdf"), ("ทุกไฟล์", "*.*")]
        )
        if files:
            threading.Thread(target=self._do_import_grades, args=(files,), daemon=True).start()

    def _do_import_grades(self, files):
        try:
            import database as db; db.init_db()
            from import_grades import import_grades, parse_grade_docx
        except Exception as e:
            self._log(f"❌ โหลด module ไม่ได้: {e}", "err"); return

        self._log(f"\n── นำเข้าเกรด ({len(files)} ไฟล์) ──────────────", "hdr")

        for f in files:
            fname = os.path.basename(f)
            try:
                parsed = parse_grade_docx(f)
                auto        = parsed.get("course_info", {})
                dist        = parsed.get("grade_dist", {})
                n           = len(parsed.get("students", []))
                sp_detected = parsed.get("is_special_detected", False)

                result = {}
                event  = threading.Event()
                def ask(a=auto, sp=sp_detected):
                    dlg = GradeInfoDialog(self, fname, dist, n, a,
                                          is_special_detected=sp)
                    result["data"] = dlg.result
                    event.set()
                self.after(0, ask)
                event.wait()

                info = result.get("data")
                if not info:
                    self._log(f"⚠  {fname}: ยกเลิก", "err"); continue

                r = import_grades(f, course_code=info["code"],
                                  semester=info["semester"], year=info["year"],
                                  is_special=info.get("is_special", False))
                s = r["stats"]
                self._log(f"✅  {info['code']}  ภาค {info['semester']}/{info['year']}", "ok")
                self._log(f"    นักศึกษา {s['registered']} คน  |  คงอยู่ {s['remaining']}  |  ถอน {s['withdrawn']}")
                top = {g: v for g, v in s["dist"].items() if v > 0}
                self._log(f"    เกรด: {top}")
            except Exception as e:
                self._log(f"❌  {fname}: {e}", "err")

        self.after(0, self._refresh_courses)

    # ══════════════════════════════════════════════════
    # EXPORT EXCEL
    # ══════════════════════════════════════════════════
    def _export_excel(self):
        path = filedialog.asksaveasfilename(
            title="บันทึก Excel",
            defaultextension=".xlsx",
            initialfile="tqf_database_view.xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return
        def do():
            try:
                import database as db
                db.export_to_excel(path)
                self.after(0, lambda: messagebox.showinfo(
                    "สำเร็จ", f"Export เสร็จแล้ว\n{path}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("ผิดพลาด", str(e)))
        threading.Thread(target=do, daemon=True).start()



# ══════════════════════════════════════════════════════
# DIALOG ยืนยันข้อมูลวิชาก่อน import เกรด
# ══════════════════════════════════════════════════════
class GradeInfoDialog(tk.Toplevel):
    def __init__(self, parent, filename, grade_dist, student_count,
                 auto_info=None, is_special_detected=False):
        super().__init__(parent)
        self.title("ยืนยันข้อมูลรายวิชา")
        self.geometry("400x390")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        auto     = auto_info or {}
        detected = bool(auto.get("code") and auto.get("semester") and auto.get("year"))

        tk.Label(self, text=f"ไฟล์: {filename}", bg=BG, fg="#333",
                 font=FONT_SM, wraplength=360).pack(pady=(14,2), padx=16, anchor="w")

        dist_str = "  ".join(f"{g}:{v}" for g, v in grade_dist.items() if v > 0)
        tk.Label(self, text=f"นักศึกษา {student_count} คน  |  {dist_str}",
                 bg=BG, fg=GRAY, font=FONT_SM).pack(padx=16, anchor="w")

        status_text  = ("✅  ตรวจพบข้อมูลอัตโนมัติ — กรุณาตรวจสอบ"
                        if detected else "⚠️  ตรวจไม่พบข้อมูลวิชา — กรุณากรอกเอง")
        status_color = GREEN if detected else RED
        tk.Label(self, text=status_text, bg=BG, fg=status_color,
                 font=("Arial", 9, "bold")).pack(padx=16, pady=(6,0), anchor="w")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=10)

        form = tk.Frame(self, bg=BG)
        form.pack(padx=16, fill="x")

        fields = [
            ("รหัสวิชา *",    "code_var",  tk.StringVar(value=auto.get("code") or ""),     "entry", None),
            ("ภาคเรียนที่ *", "sem_var",   tk.StringVar(value=str(auto.get("semester") or "2")), "combo", ["1","2","3"]),
            ("ปีการศึกษา *",  "year_var",  tk.StringVar(value=str(auto.get("year") or "2568")), "entry", None),
        ]
        for i, (label, attr, var, kind, opts) in enumerate(fields):
            setattr(self, attr, var)
            tk.Label(form, text=label, bg=BG, font=FONT_B).grid(row=i, column=0, sticky="w", pady=7)
            if kind == "combo":
                w = ttk.Combobox(form, textvariable=var, values=opts, width=6, state="readonly")
            else:
                w = tk.Entry(form, textvariable=var, width=20, font=("Arial", 11))
            w.grid(row=i, column=1, sticky="w", padx=10)

        # ── ประเภทการเปิด: ปกติ / พิเศษ ─────────────────────────────────────
        ttk.Separator(form, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        tk.Label(form, text="ประเภทเปิด :", bg=BG, font=FONT_B).grid(
            row=4, column=0, sticky="w", pady=6)
        sec_frame = tk.Frame(form, bg=BG)
        sec_frame.grid(row=4, column=1, sticky="w", padx=10)
        self.special_var = tk.BooleanVar(value=is_special_detected)
        tk.Radiobutton(sec_frame, text="ปกติ (N0x)", variable=self.special_var,
                       value=False, bg=BG, font=FONT_SM, cursor="hand2",
                       activebackground=BG).pack(side="left", padx=(0,10))
        tk.Radiobutton(sec_frame, text="★ พิเศษ (P0x)", variable=self.special_var,
                       value=True, bg=BG, font=FONT_SM, cursor="hand2",
                       fg="#C75000", activebackground=BG,
                       selectcolor=WHITE).pack(side="left")
        # แสดง label auto-detect ถ้าตรวจพบ
        if is_special_detected:
            tk.Label(form, text="(ตรวจพบ section P0x อัตโนมัติ)",
                     bg=BG, fg=GRAY, font=("Arial", 8, "italic")).grid(
                row=5, column=1, sticky="w", padx=10)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=16)
        tk.Button(btn_frame, text="ยืนยัน", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=20, pady=6, command=self._confirm).pack(side="left", padx=6)
        tk.Button(btn_frame, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=6, command=self.destroy).pack(side="left", padx=6)
        self.wait_window()

    def _confirm(self):
        code = self.code_var.get().strip().upper()
        if not code:
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอกรหัสวิชา", parent=self); return
        try:
            year = int(self.year_var.get())
            sem  = int(self.sem_var.get())
        except ValueError:
            messagebox.showwarning("ข้อมูลไม่ถูกต้อง", "ปีการศึกษาต้องเป็นตัวเลข", parent=self); return
        self.result = {
            "code": code, "semester": sem, "year": year,
            "is_special": bool(self.special_var.get()),
        }
        self.destroy()


# ══════════════════════════════════════════════════════
# DIALOG เพิ่ม/แก้ไขวิชาใหม่
# ══════════════════════════════════════════════════════
class CourseAddDialog(tk.Toplevel):
    """Dialog สำหรับเพิ่มวิชาใหม่ หรือแก้ไขข้อมูลพื้นฐานวิชา"""
    TYPES = ["วิชาแกน (Core)", "วิชาบังคับ (Required)",
             "วิชาเลือก (Elective)", "วิชาปฏิบัติการ (Practicum)",
             "วิชาเลือกเสรี (Free Elective)", "สหกิจศึกษา", "อื่นๆ"]

    def __init__(self, parent, curricula, existing=None):
        super().__init__(parent)
        is_edit = existing is not None
        self.title("แก้ไขข้อมูลวิชา" if is_edit else "เพิ่มวิชาใหม่")
        self.geometry("520x560")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        ex = dict(existing) if existing else {}
        self._cur_map = {f"หลักสูตร {r['version']}  ({r['name_th']})": r["id"]
                         for r in curricula}

        # Header
        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x")
        title_text = (f"✏️  {ex.get('code','')}  {ex.get('name_th','')}"
                      if is_edit else "＋  เพิ่มวิชาใหม่")
        tk.Label(hdr, text=title_text, bg=BLUE_DARK, fg=WHITE,
                 font=FONT_B, wraplength=480, anchor="w").pack(padx=14, pady=10)

        # Form
        frm = tk.Frame(self, bg=BG)
        frm.pack(fill="both", expand=True, padx=20, pady=12)
        frm.columnconfigure(1, weight=1)

        def row_label(r, text):
            tk.Label(frm, text=text, bg=BG, font=FONT_B,
                     anchor="e").grid(row=r, column=0, sticky="e",
                                      pady=5, padx=(0, 10))

        def entry(r, var, width=30, state="normal"):
            e = tk.Entry(frm, textvariable=var, width=width,
                         font=("Arial", 10), state=state)
            e.grid(row=r, column=1, sticky="w")
            return e

        # หลักสูตร
        row_label(0, "หลักสูตร *")
        cur_default = ""
        for lbl, cid in self._cur_map.items():
            if cid == ex.get("curriculum_id"):
                cur_default = lbl; break
        self.cur_var = tk.StringVar(value=cur_default)
        ttk.Combobox(frm, textvariable=self.cur_var,
                     values=list(self._cur_map.keys()),
                     width=36, state="readonly").grid(row=0, column=1, sticky="w")

        # รหัสวิชา
        row_label(1, "รหัสวิชา *")
        self.code_var = tk.StringVar(value=ex.get("code", ""))
        entry(1, self.code_var, state="normal" if not is_edit else "readonly")

        # ชื่อไทย
        row_label(2, "ชื่อไทย *")
        self.nameth_var = tk.StringVar(value=ex.get("name_th", ""))
        entry(2, self.nameth_var, 36)

        # ชื่ออังกฤษ
        row_label(3, "ชื่ออังกฤษ")
        self.nameen_var = tk.StringVar(value=ex.get("name_en", ""))
        entry(3, self.nameen_var, 36)

        # หน่วยกิต
        row_label(4, "หน่วยกิต")
        cr_frame = tk.Frame(frm, bg=BG)
        cr_frame.grid(row=4, column=1, sticky="w")
        self.credits_var = tk.StringVar(value=ex.get("credits_text", ""))
        tk.Entry(cr_frame, textvariable=self.credits_var,
                 width=12, font=("Arial", 10)).pack(side="left")
        tk.Label(cr_frame, text="  บรรยาย:", bg=BG, font=FONT_SM).pack(side="left")
        self.lec_var = tk.StringVar(value=str(ex.get("credit_lecture", 0)))
        tk.Entry(cr_frame, textvariable=self.lec_var, width=3,
                 font=("Arial", 10)).pack(side="left")
        tk.Label(cr_frame, text=" ปฏิบัติ:", bg=BG, font=FONT_SM).pack(side="left")
        self.lab_var = tk.StringVar(value=str(ex.get("credit_lab", 0)))
        tk.Entry(cr_frame, textvariable=self.lab_var, width=3,
                 font=("Arial", 10)).pack(side="left")
        tk.Label(cr_frame, text=" ค้นคว้า:", bg=BG, font=FONT_SM).pack(side="left")
        self.slf_var = tk.StringVar(value=str(ex.get("credit_self", 0)))
        tk.Entry(cr_frame, textvariable=self.slf_var, width=3,
                 font=("Arial", 10)).pack(side="left")

        # ประเภทวิชา
        row_label(5, "ประเภทวิชา")
        ct_default = ex.get("course_type", "")
        if ct_default not in self.TYPES:
            for t in self.TYPES:
                if ct_default and ct_default[:4] in t:
                    ct_default = t; break
        self.type_var = tk.StringVar(value=ct_default)
        ttk.Combobox(frm, textvariable=self.type_var,
                     values=self.TYPES, width=30, state="readonly"
                     ).grid(row=5, column=1, sticky="w")

        # วิชาบังคับก่อน
        row_label(6, "บังคับก่อน")
        self.prereq_var = tk.StringVar(value=ex.get("prerequisite", "ไม่มี"))
        entry(6, self.prereq_var, 30)

        # คำอธิบาย
        row_label(7, "คำอธิบาย")
        self.desc_text = tk.Text(frm, width=36, height=3,
                                  font=("Arial", 9), wrap="word")
        self.desc_text.insert("1.0", ex.get("description_th", ""))
        self.desc_text.grid(row=7, column=1, sticky="w", pady=4)

        # Buttons
        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=14)
        tk.Button(btn_f, text="💾  บันทึก", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=22, pady=7, cursor="hand2",
                  command=self._save).pack(side="left", padx=8)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=7,
                  command=self.destroy).pack(side="left", padx=4)
        self.wait_window()

    def _save(self):
        cur_label = self.cur_var.get()
        curriculum_id = self._cur_map.get(cur_label)
        if not curriculum_id:
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณาเลือกหลักสูตร", parent=self)
            return
        code = self.code_var.get().strip().upper()
        name_th = self.nameth_var.get().strip()
        if not code or not name_th:
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอกรหัสวิชาและชื่อไทย", parent=self)
            return
        try:
            lec = int(self.lec_var.get() or 0)
            lab = int(self.lab_var.get() or 0)
            slf = int(self.slf_var.get() or 0)
        except ValueError:
            lec = lab = slf = 0
        self.result = {
            "code": code, "name_th": name_th,
            "name_en": self.nameen_var.get().strip(),
            "credits_text": self.credits_var.get().strip(),
            "credit_lecture": lec, "credit_lab": lab, "credit_self": slf,
            "course_type": self.type_var.get(),
            "prerequisite": self.prereq_var.get().strip() or "ไม่มี",
            "description_th": self.desc_text.get("1.0", "end").strip(),
            "curriculum_id": curriculum_id,
        }
        self.destroy()


# ══════════════════════════════════════════════════════
# DIALOG จัดการ PLO ของหลักสูตร
# ══════════════════════════════════════════════════════
class PLOManagerDialog(tk.Toplevel):
    """Dialog เพิ่ม/แก้ไข/ลบ PLO ของหลักสูตร"""
    PLO_CATS = ["ด้านความรู้", "ด้านทักษะทางปัญญา",
                "ด้านทักษะความสัมพันธ์ระหว่างบุคคล",
                "ด้านการวิเคราะห์เชิงตัวเลข", "ด้านจริยธรรม", "อื่นๆ"]

    def __init__(self, parent, curriculum, plos):
        super().__init__(parent)
        cur_ver = curriculum["version"] if curriculum else "?"
        self.title(f"จัดการ PLO — หลักสูตร {cur_ver}")
        self.geometry("700x500")
        self.resizable(True, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._rows = [dict(p) for p in plos]   # working copy

        # Header
        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"📚  PLO — หลักสูตร {cur_ver}",
                 bg=BLUE_DARK, fg=WHITE, font=FONT_B).pack(
                 side="left", padx=14, pady=10)
        tk.Label(hdr, text="(Program Learning Outcomes)",
                 bg=BLUE_DARK, fg="#90CAF9", font=FONT_SM).pack(
                 side="left", padx=4, pady=10)

        # Toolbar
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=12, pady=(8, 4))
        tk.Button(bar, text="＋ เพิ่ม PLO", bg=GREEN, fg=WHITE, font=FONT_B,
                  relief="flat", padx=10, pady=3, cursor="hand2",
                  command=self._add_row).pack(side="left", padx=(0, 6))
        self.btn_del_plo = tk.Button(
            bar, text="🗑 ลบ", bg=RED, fg=WHITE, font=FONT_B,
            relief="flat", padx=10, pady=3, cursor="hand2",
            state="disabled", command=self._del_row)
        self.btn_del_plo.pack(side="left")

        # Treeview
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)
        tcols = ("num", "cat", "desc")
        self.plo_tree = ttk.Treeview(
            tree_frame, columns=tcols, show="headings",
            selectmode="browse", height=12)
        self.plo_tree.heading("num",  text="PLO#")
        self.plo_tree.heading("cat",  text="ด้าน")
        self.plo_tree.heading("desc", text="คำอธิบาย")
        self.plo_tree.column("num",  width=50,  anchor="center", minwidth=40)
        self.plo_tree.column("cat",  width=180, anchor="w")
        self.plo_tree.column("desc", width=400, anchor="w")
        self.plo_tree.bind("<<TreeviewSelect>>",
                           lambda e: self.btn_del_plo.config(
                               state="normal" if self.plo_tree.selection() else "disabled"))
        self.plo_tree.bind("<Double-1>", self._edit_row)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.plo_tree.yview)
        self.plo_tree.configure(yscrollcommand=vsb.set)
        self.plo_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        tk.Label(self, text="ดับเบิลคลิกที่แถวเพื่อแก้ไข",
                 bg=BG, fg=GRAY, font=("Arial", 8, "italic")).pack(pady=(0, 2))

        # Buttons
        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="💾  บันทึก PLO ทั้งหมด", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=22, pady=7, cursor="hand2",
                  command=self._save).pack(side="left", padx=8)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=7, command=self.destroy
                  ).pack(side="left", padx=4)

        self._render_tree()
        self.wait_window()

    def _render_tree(self):
        for item in self.plo_tree.get_children():
            self.plo_tree.delete(item)
        for r in self._rows:
            self.plo_tree.insert("", "end", values=(
                r["plo_number"], r.get("category",""), r.get("description","")))

    def _add_row(self):
        next_num = max((r["plo_number"] for r in self._rows), default=0) + 1
        dlg = PLOEditRowDialog(self, next_num, "", "", self.PLO_CATS)
        if dlg.result:
            self._rows.append(dlg.result)
            self._rows.sort(key=lambda x: x["plo_number"])
            self._render_tree()

    def _edit_row(self, event=None):
        sel = self.plo_tree.selection()
        if not sel: return
        vals = self.plo_tree.item(sel[0], "values")
        idx = next((i for i, r in enumerate(self._rows)
                    if r["plo_number"] == int(vals[0])), None)
        if idx is None: return
        r = self._rows[idx]
        dlg = PLOEditRowDialog(self, r["plo_number"],
                               r.get("category",""), r.get("description",""),
                               self.PLO_CATS)
        if dlg.result:
            self._rows[idx] = dlg.result
            self._render_tree()

    def _del_row(self):
        sel = self.plo_tree.selection()
        if not sel: return
        vals = self.plo_tree.item(sel[0], "values")
        num = int(vals[0])
        self._rows = [r for r in self._rows if r["plo_number"] != num]
        self._render_tree()

    def _save(self):
        self.result = self._rows
        self.destroy()


class PLOEditRowDialog(tk.Toplevel):
    def __init__(self, parent, plo_number, category, description, cats):
        super().__init__(parent)
        self.title(f"PLO {plo_number}")
        self.geometry("460x240")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        frm = tk.Frame(self, bg=BG)
        frm.pack(fill="both", expand=True, padx=20, pady=16)
        frm.columnconfigure(1, weight=1)

        tk.Label(frm, text="PLO#:", bg=BG, font=FONT_B).grid(
            row=0, column=0, sticky="e", pady=6, padx=(0,10))
        self.num_var = tk.StringVar(value=str(plo_number))
        tk.Entry(frm, textvariable=self.num_var, width=6,
                 font=("Arial",10)).grid(row=0, column=1, sticky="w")

        tk.Label(frm, text="ด้าน:", bg=BG, font=FONT_B).grid(
            row=1, column=0, sticky="e", pady=6, padx=(0,10))
        self.cat_var = tk.StringVar(value=category)
        ttk.Combobox(frm, textvariable=self.cat_var,
                     values=cats, width=32, state="normal").grid(
            row=1, column=1, sticky="w")

        tk.Label(frm, text="คำอธิบาย:", bg=BG, font=FONT_B).grid(
            row=2, column=0, sticky="ne", pady=6, padx=(0,10))
        self.desc_text = tk.Text(frm, width=34, height=3,
                                  font=("Arial",9), wrap="word")
        self.desc_text.insert("1.0", description)
        self.desc_text.grid(row=2, column=1, sticky="w")

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=12)
        tk.Button(btn_f, text="ตกลง", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=16, pady=5, command=self._ok
                  ).pack(side="left", padx=6)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=12, pady=5, command=self.destroy
                  ).pack(side="left")
        self.wait_window()

    def _ok(self):
        try:
            num = int(self.num_var.get())
        except ValueError:
            messagebox.showwarning("ข้อมูลไม่ถูกต้อง", "PLO# ต้องเป็นตัวเลข", parent=self)
            return
        self.result = {
            "plo_number": num,
            "category": self.cat_var.get().strip(),
            "description": self.desc_text.get("1.0","end").strip(),
        }
        self.destroy()


# ══════════════════════════════════════════════════════
# DIALOG แก้ไข CLO + Assessment ของวิชา (course template)
# ══════════════════════════════════════════════════════
class CourseCLOEditor(tk.Toplevel):
    """แก้ไข course_clos และ course_assessments"""

    DOMAINS = ["ด้านความรู้", "ด้านทักษะทางปัญญา",
               "ด้านทักษะความสัมพันธ์ระหว่างบุคคล",
               "ด้านการวิเคราะห์เชิงตัวเลข", "ด้านจริยธรรม", ""]

    def __init__(self, parent, course, clos, assessments, plos):
        super().__init__(parent)
        code = course["code"] if course else "?"
        self.title(f"แก้ไข CLO & การประเมิน — {code}")
        self.geometry("780x600")
        self.resizable(True, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._clos  = [dict(c) for c in clos]
        self._asmt  = [dict(a) for a in assessments]
        self._plos  = plos   # [{plo_number, description}]

        # Header
        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x")
        tk.Label(hdr,
                 text=f"📝  CLO & การประเมินมาตรฐาน — {code}  {course.get('name_th','')}",
                 bg=BLUE_DARK, fg=WHITE, font=FONT_B,
                 wraplength=720, anchor="w").pack(padx=14, pady=9)

        # Notebook สลับ CLO / Assessment
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=6)
        self.tab_clo  = tk.Frame(nb, bg=BG)
        self.tab_asmt = tk.Frame(nb, bg=BG)
        nb.add(self.tab_clo,  text="  📌 CLO มาตรฐาน  ")
        nb.add(self.tab_asmt, text="  📊 แผนการประเมิน  ")
        self._build_clo_tab()
        self._build_asmt_tab()

        # Buttons
        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="💾  บันทึกทั้งหมด", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=22, pady=7, cursor="hand2",
                  command=self._save).pack(side="left", padx=8)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=7, command=self.destroy
                  ).pack(side="left", padx=4)
        self.wait_window()

    # ── CLO tab ─────────────────────────────────────
    def _build_clo_tab(self):
        bar = tk.Frame(self.tab_clo, bg=BG)
        bar.pack(fill="x", padx=8, pady=(8,4))
        tk.Button(bar, text="＋ เพิ่ม CLO", bg=GREEN, fg=WHITE, font=FONT_B,
                  relief="flat", padx=10, pady=3, cursor="hand2",
                  command=self._add_clo).pack(side="left", padx=(0,6))
        self.btn_del_clo = tk.Button(
            bar, text="🗑 ลบ", bg=RED, fg=WHITE, font=FONT_B,
            relief="flat", padx=10, pady=3, cursor="hand2",
            state="disabled", command=self._del_clo)
        self.btn_del_clo.pack(side="left")
        tk.Label(bar, text="(ดับเบิลคลิกเพื่อแก้ไข)",
                 bg=BG, fg=GRAY, font=("Arial",8,"italic")).pack(side="left", padx=8)

        tf = tk.Frame(self.tab_clo, bg=BG)
        tf.pack(fill="both", expand=True, padx=8, pady=4)
        cc = ("num","desc","plo","pass_pct")
        self.clo_tree = ttk.Treeview(tf, columns=cc, show="headings",
                                      selectmode="browse", height=14)
        self.clo_tree.heading("num",     text="CLO#")
        self.clo_tree.heading("desc",    text="คำอธิบาย")
        self.clo_tree.heading("plo",     text="PLO")
        self.clo_tree.heading("pass_pct",text="เกณฑ์ผ่าน")
        self.clo_tree.column("num",      width=50,  anchor="center")
        self.clo_tree.column("desc",     width=400, anchor="w")
        self.clo_tree.column("plo",      width=80,  anchor="center")
        self.clo_tree.column("pass_pct", width=70,  anchor="center")
        self.clo_tree.bind("<<TreeviewSelect>>",
                           lambda e: self.btn_del_clo.config(
                               state="normal" if self.clo_tree.selection() else "disabled"))
        self.clo_tree.bind("<Double-1>", self._edit_clo)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.clo_tree.yview)
        self.clo_tree.configure(yscrollcommand=vsb.set)
        self.clo_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._render_clo_tree()

    def _render_clo_tree(self):
        for item in self.clo_tree.get_children():
            self.clo_tree.delete(item)
        for c in self._clos:
            plo_nums = c.get("plo_mapping", [])
            if isinstance(plo_nums, str):
                plo_nums = json.loads(plo_nums)
            plo_str = ",".join(str(p) for p in plo_nums) if plo_nums else "—"
            self.clo_tree.insert("", "end", values=(
                c["clo_number"],
                (c.get("description") or "")[:70],
                plo_str,
                f"{c.get('pass_threshold_pct',50):.0f}%",
            ))

    def _add_clo(self):
        next_num = max((c["clo_number"] for c in self._clos), default=0) + 1
        dlg = CLOEditRowDialog(self, {
            "clo_number": next_num, "description": "",
            "domain": "", "teaching_strategy": "",
            "assessment_method": "", "pass_threshold_pct": 50.0,
            "plo_mapping": [],
        }, self._plos, self.DOMAINS)
        if dlg.result:
            self._clos.append(dlg.result)
            self._clos.sort(key=lambda x: x["clo_number"])
            self._render_clo_tree()

    def _edit_clo(self, event=None):
        sel = self.clo_tree.selection()
        if not sel: return
        vals = self.clo_tree.item(sel[0], "values")
        idx = next((i for i, c in enumerate(self._clos)
                    if c["clo_number"] == int(vals[0])), None)
        if idx is None: return
        dlg = CLOEditRowDialog(self, self._clos[idx], self._plos, self.DOMAINS)
        if dlg.result:
            self._clos[idx] = dlg.result
            self._render_clo_tree()

    def _del_clo(self):
        sel = self.clo_tree.selection()
        if not sel: return
        vals = self.clo_tree.item(sel[0], "values")
        num = int(vals[0])
        self._clos = [c for c in self._clos if c["clo_number"] != num]
        self._render_clo_tree()

    # ── Assessment tab ───────────────────────────────
    def _build_asmt_tab(self):
        bar = tk.Frame(self.tab_asmt, bg=BG)
        bar.pack(fill="x", padx=8, pady=(8,4))
        tk.Button(bar, text="＋ เพิ่มรายการ", bg=GREEN, fg=WHITE, font=FONT_B,
                  relief="flat", padx=10, pady=3, cursor="hand2",
                  command=self._add_asmt).pack(side="left", padx=(0,6))
        self.btn_del_asmt = tk.Button(
            bar, text="🗑 ลบ", bg=RED, fg=WHITE, font=FONT_B,
            relief="flat", padx=10, pady=3, cursor="hand2",
            state="disabled", command=self._del_asmt)
        self.btn_del_asmt.pack(side="left")
        self.asmt_total_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self.asmt_total_var,
                 bg=BG, fg=GRAY, font=FONT_SM).pack(side="left", padx=12)

        tf = tk.Frame(self.tab_asmt, bg=BG)
        tf.pack(fill="both", expand=True, padx=8, pady=4)
        ac = ("name","full_score","weight","pass_t","clos")
        self.asmt_tree = ttk.Treeview(tf, columns=ac, show="headings",
                                       selectmode="browse", height=14)
        self.asmt_tree.heading("name",      text="รายการประเมิน")
        self.asmt_tree.heading("full_score",text="คะแนนเต็ม")
        self.asmt_tree.heading("weight",    text="น้ำหนัก %")
        self.asmt_tree.heading("pass_t",    text="เกณฑ์ผ่าน %")
        self.asmt_tree.heading("clos",      text="CLOs")
        self.asmt_tree.column("name",       width=200, anchor="w")
        self.asmt_tree.column("full_score", width=80,  anchor="center")
        self.asmt_tree.column("weight",     width=80,  anchor="center")
        self.asmt_tree.column("pass_t",     width=80,  anchor="center")
        self.asmt_tree.column("clos",       width=120, anchor="center")
        self.asmt_tree.bind("<<TreeviewSelect>>",
                            lambda e: self.btn_del_asmt.config(
                                state="normal" if self.asmt_tree.selection() else "disabled"))
        self.asmt_tree.bind("<Double-1>", self._edit_asmt)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.asmt_tree.yview)
        self.asmt_tree.configure(yscrollcommand=vsb.set)
        self.asmt_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._render_asmt_tree()

    def _render_asmt_tree(self):
        for item in self.asmt_tree.get_children():
            self.asmt_tree.delete(item)
        total = 0
        for a in self._asmt:
            w = a.get("weight_pct", 0)
            total += w
            clom = a.get("clo_mapping", [])
            if isinstance(clom, str):
                clom = json.loads(clom)
            clos_str = ",".join(f"CLO{c}" for c in clom) if clom else "—"
            self.asmt_tree.insert("", "end", values=(
                a.get("name",""),
                f"{a.get('full_score',100):.0f}",
                f"{w:.0f}%",
                f"{a.get('pass_threshold',50):.0f}%",
                clos_str,
            ))
        color = "ok" if abs(total-100) < 0.5 else "warn"
        label = f"รวม {total:.0f}% {'✅' if abs(total-100)<0.5 else '⚠ ควรได้ 100%'}"
        self.asmt_total_var.set(label)

    def _add_asmt(self):
        dlg = AsmtEditRowDialog(self, {}, self._clos)
        if dlg.result:
            self._asmt.append(dlg.result)
            self._render_asmt_tree()

    def _edit_asmt(self, event=None):
        sel = self.asmt_tree.selection()
        if not sel: return
        vals = self.asmt_tree.item(sel[0], "values")
        idx = next((i for i, a in enumerate(self._asmt)
                    if a.get("name") == vals[0]), None)
        if idx is None: return
        dlg = AsmtEditRowDialog(self, self._asmt[idx], self._clos)
        if dlg.result:
            self._asmt[idx] = dlg.result
            self._render_asmt_tree()

    def _del_asmt(self):
        sel = self.asmt_tree.selection()
        if not sel: return
        vals = self.asmt_tree.item(sel[0], "values")
        self._asmt = [a for a in self._asmt if a.get("name") != vals[0]]
        self._render_asmt_tree()

    def _save(self):
        self.result = {"clos": self._clos, "assessments": self._asmt}
        self.destroy()


class CLOEditRowDialog(tk.Toplevel):
    def __init__(self, parent, clo, plos, domains):
        super().__init__(parent)
        self.title(f"CLO {clo.get('clo_number','')}")
        self.geometry("500x380")
        self.resizable(False, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._plos = plos

        frm = tk.Frame(self, bg=BG)
        frm.pack(fill="both", expand=True, padx=16, pady=12)
        frm.columnconfigure(1, weight=1)

        def lbl(r, t):
            tk.Label(frm, text=t, bg=BG, font=FONT_B, anchor="e").grid(
                row=r, column=0, sticky="e", pady=5, padx=(0,8))

        lbl(0, "CLO#:")
        self.num_var = tk.StringVar(value=str(clo.get("clo_number",1)))
        tk.Entry(frm, textvariable=self.num_var, width=6,
                 font=("Arial",10)).grid(row=0, column=1, sticky="w")

        lbl(1, "คำอธิบาย:")
        self.desc = tk.Text(frm, width=38, height=3, font=("Arial",9), wrap="word")
        self.desc.insert("1.0", clo.get("description",""))
        self.desc.grid(row=1, column=1, sticky="w", pady=4)

        lbl(2, "ด้าน:")
        self.dom_var = tk.StringVar(value=clo.get("domain",""))
        ttk.Combobox(frm, textvariable=self.dom_var,
                     values=domains, width=32, state="normal").grid(
            row=2, column=1, sticky="w")

        lbl(3, "วิธีสอน:")
        self.strat_var = tk.StringVar(value=clo.get("teaching_strategy",""))
        tk.Entry(frm, textvariable=self.strat_var, width=38,
                 font=("Arial",9)).grid(row=3, column=1, sticky="w")

        lbl(4, "วิธีวัด:")
        self.asmth_var = tk.StringVar(value=clo.get("assessment_method",""))
        tk.Entry(frm, textvariable=self.asmth_var, width=38,
                 font=("Arial",9)).grid(row=4, column=1, sticky="w")

        lbl(5, "เกณฑ์ผ่าน %:")
        self.pass_var = tk.StringVar(value=str(clo.get("pass_threshold_pct",50)))
        tk.Entry(frm, textvariable=self.pass_var, width=8,
                 font=("Arial",10)).grid(row=5, column=1, sticky="w")

        lbl(6, "PLO ที่ตอบสนอง:")
        plo_frame = tk.Frame(frm, bg=BG)
        plo_frame.grid(row=6, column=1, sticky="w", pady=4)
        cur_mapping = clo.get("plo_mapping", [])
        if isinstance(cur_mapping, str):
            cur_mapping = json.loads(cur_mapping)
        self._plo_vars = {}
        for p in plos:
            var = tk.BooleanVar(value=(p["plo_number"] in cur_mapping))
            self._plo_vars[p["plo_number"]] = var
            tk.Checkbutton(
                plo_frame, text=f"PLO{p['plo_number']}",
                variable=var, bg=BG, font=FONT_SM, cursor="hand2",
                activebackground=BG).pack(side="left", padx=4)
        if not plos:
            tk.Label(plo_frame, text="(ยังไม่มี PLO — กด 📚 PLO ก่อน)",
                     bg=BG, fg=GRAY, font=FONT_SM).pack(side="left")

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="ตกลง", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=16, pady=5, command=self._ok
                  ).pack(side="left", padx=6)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=12, pady=5, command=self.destroy
                  ).pack(side="left")
        self.wait_window()

    def _ok(self):
        try:
            num = int(self.num_var.get())
            pct = float(self.pass_var.get())
        except ValueError:
            messagebox.showwarning("ข้อมูลผิด", "CLO# และเกณฑ์ผ่านต้องเป็นตัวเลข", parent=self)
            return
        self.result = {
            "clo_number": num,
            "description": self.desc.get("1.0","end").strip(),
            "domain": self.dom_var.get().strip(),
            "teaching_strategy": self.strat_var.get().strip(),
            "assessment_method": self.asmth_var.get().strip(),
            "pass_threshold_pct": pct,
            "plo_mapping": [n for n, v in self._plo_vars.items() if v.get()],
        }
        self.destroy()


class AsmtEditRowDialog(tk.Toplevel):
    def __init__(self, parent, asmt, clos):
        super().__init__(parent)
        self.title("รายการประเมิน")
        self.geometry("440x320")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        frm = tk.Frame(self, bg=BG)
        frm.pack(fill="both", expand=True, padx=16, pady=12)
        frm.columnconfigure(1, weight=1)

        def lbl(r, t):
            tk.Label(frm, text=t, bg=BG, font=FONT_B, anchor="e").grid(
                row=r, column=0, sticky="e", pady=5, padx=(0,8))

        lbl(0, "ชื่อรายการ:")
        self.name_var = tk.StringVar(value=asmt.get("name",""))
        tk.Entry(frm, textvariable=self.name_var, width=30,
                 font=("Arial",10)).grid(row=0, column=1, sticky="w")

        lbl(1, "คะแนนเต็ม:")
        self.full_var = tk.StringVar(value=str(asmt.get("full_score",100)))
        tk.Entry(frm, textvariable=self.full_var, width=8,
                 font=("Arial",10)).grid(row=1, column=1, sticky="w")

        lbl(2, "น้ำหนัก %:")
        self.wt_var = tk.StringVar(value=str(asmt.get("weight_pct",0)))
        tk.Entry(frm, textvariable=self.wt_var, width=8,
                 font=("Arial",10)).grid(row=2, column=1, sticky="w")

        lbl(3, "เกณฑ์ผ่าน %:")
        self.pass_var = tk.StringVar(value=str(asmt.get("pass_threshold",50)))
        tk.Entry(frm, textvariable=self.pass_var, width=8,
                 font=("Arial",10)).grid(row=3, column=1, sticky="w")

        lbl(4, "CLOs ที่วัด:")
        clo_frame = tk.Frame(frm, bg=BG)
        clo_frame.grid(row=4, column=1, sticky="w", pady=4)
        cur_mapping = asmt.get("clo_mapping", [])
        if isinstance(cur_mapping, str):
            cur_mapping = json.loads(cur_mapping)
        self._clo_vars = {}
        for c in clos:
            num = c["clo_number"]
            var = tk.BooleanVar(value=(num in cur_mapping))
            self._clo_vars[num] = var
            tk.Checkbutton(clo_frame, text=f"CLO{num}",
                           variable=var, bg=BG, font=FONT_SM,
                           activebackground=BG).pack(side="left", padx=3)
        if not clos:
            tk.Label(clo_frame, text="(ยังไม่มี CLO)",
                     bg=BG, fg=GRAY, font=FONT_SM).pack(side="left")

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=12)
        tk.Button(btn_f, text="ตกลง", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=16, pady=5, command=self._ok
                  ).pack(side="left", padx=6)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=12, pady=5, command=self.destroy
                  ).pack(side="left")
        self.wait_window()

    def _ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("ข้อมูลไม่ครบ","กรุณากรอกชื่อรายการ",parent=self)
            return
        try:
            full = float(self.full_var.get())
            wt   = float(self.wt_var.get())
            pt   = float(self.pass_var.get())
        except ValueError:
            messagebox.showwarning("ข้อมูลผิด","ตัวเลขไม่ถูกต้อง",parent=self)
            return
        self.result = {
            "name": name, "full_score": full,
            "weight_pct": wt, "pass_threshold": pt,
            "clo_mapping": [n for n, v in self._clo_vars.items() if v.get()],
            "eval_criteria": "",
        }
        self.destroy()


# ══════════════════════════════════════════════════════
# DIALOG แก้ไขข้อมูลวิชา
# ══════════════════════════════════════════════════════
class CourseEditDialog(tk.Toplevel):
    """Dialog แก้ไข: หลักสูตร, ประเภทวิชา, ภาคเรียน, ปีการศึกษา"""

    COURSE_TYPES = [
        "วิชาแกน (Core)", "วิชาบังคับ (Required)",
        "วิชาเลือก (Elective)", "วิชาปฏิบัติการ (Practicum)",
        "วิชาเลือกเสรี (Free Elective)", "อื่นๆ",
    ]

    def __init__(self, parent, course, curricula, tqf3_row=None):
        super().__init__(parent)
        self.title(f"แก้ไขข้อมูล — {course['code']}")
        self.geometry("440x380")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        self._curricula = curricula   # list of Row (id, version, name_th)
        self._cur_map   = {f"หลักสูตร {r['version']}  ({r['name_th']})": r["id"]
                           for r in curricula}
        self._has_tqf3  = tqf3_row is not None

        # ── Header ──────────────────────────────────
        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x")
        tk.Label(hdr,
                 text=f"✏️  {course['code']}  —  {course['name_th']}",
                 bg=BLUE_DARK, fg=WHITE, font=FONT_B,
                 wraplength=400, anchor="w").pack(padx=14, pady=10, anchor="w")

        # ── Form ────────────────────────────────────
        form = tk.Frame(self, bg=BG)
        form.pack(fill="both", expand=True, padx=20, pady=14)
        form.columnconfigure(1, weight=1)

        row = 0

        # หลักสูตร
        tk.Label(form, text="หลักสูตร :", bg=BG, font=FONT_B,
                 anchor="e").grid(row=row, column=0, sticky="e", pady=8, padx=(0,10))
        cur_labels = list(self._cur_map.keys())
        # หาค่าปัจจุบัน
        cur_default = ""
        for label, cid in self._cur_map.items():
            if cid == course["curriculum_id"]:
                cur_default = label; break
        self.cur_var = tk.StringVar(value=cur_default)
        ttk.Combobox(form, textvariable=self.cur_var,
                     values=cur_labels, width=34, state="readonly"
                     ).grid(row=row, column=1, sticky="w")
        row += 1

        # ประเภทวิชา
        tk.Label(form, text="ประเภทวิชา :", bg=BG, font=FONT_B,
                 anchor="e").grid(row=row, column=0, sticky="e", pady=8, padx=(0,10))
        # normalise course_type ให้ตรงกับ COURSE_TYPES ถ้าทำได้
        ct_default = course["course_type"] or ""
        if ct_default not in self.COURSE_TYPES:
            # ลองจับคู่แบบ partial
            for ct in self.COURSE_TYPES:
                if ct_default and (ct_default in ct or ct_default[:4] in ct):
                    ct_default = ct; break
        self.type_var = tk.StringVar(value=ct_default)
        ttk.Combobox(form, textvariable=self.type_var,
                     values=self.COURSE_TYPES, width=34, state="readonly"
                     ).grid(row=row, column=1, sticky="w")
        row += 1

        # ── ภาคเรียน / ปีการศึกษา / ประเภทเปิด (แสดงเฉพาะถ้ามี tqf3) ──
        if self._has_tqf3:
            ttk.Separator(form, orient="horizontal").grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(6, 2))
            row += 1
            tk.Label(form, text="(ข้อมูลจาก มคอ.3)", bg=BG, fg=GRAY,
                     font=("Arial", 8, "italic")).grid(
                row=row, column=0, columnspan=2, pady=(0, 6))
            row += 1

            # ภาคเรียน
            tk.Label(form, text="ภาคเรียนที่ :", bg=BG, font=FONT_B,
                     anchor="e").grid(row=row, column=0, sticky="e", pady=8, padx=(0,10))
            self.sem_var = tk.StringVar(
                value=str(tqf3_row["semester"]) if tqf3_row["semester"] else "1")
            ttk.Combobox(form, textvariable=self.sem_var,
                         values=["1", "2", "3"], width=6, state="readonly"
                         ).grid(row=row, column=1, sticky="w")
            row += 1

            # ปีการศึกษา
            tk.Label(form, text="ปีการศึกษา :", bg=BG, font=FONT_B,
                     anchor="e").grid(row=row, column=0, sticky="e", pady=8, padx=(0,10))
            self.year_var = tk.StringVar(
                value=str(tqf3_row["year"]) if tqf3_row["year"] else "2567")
            tk.Entry(form, textvariable=self.year_var, width=10,
                     font=("Arial", 11)).grid(row=row, column=1, sticky="w")
            row += 1

            # ประเภทการเปิด
            tk.Label(form, text="ประเภทเปิด :", bg=BG, font=FONT_B,
                     anchor="e").grid(row=row, column=0, sticky="e", pady=8, padx=(0,10))
            sec_frame = tk.Frame(form, bg=BG)
            sec_frame.grid(row=row, column=1, sticky="w")
            try:
                _is_sp = int(tqf3_row["is_special"]) if tqf3_row else 0
            except (IndexError, KeyError, TypeError):
                _is_sp = 0
            self.special_var = tk.BooleanVar(value=bool(_is_sp))
            tk.Radiobutton(sec_frame, text="ปกติ (N0x)",
                           variable=self.special_var, value=False,
                           bg=BG, font=FONT_SM, cursor="hand2",
                           activebackground=BG).pack(side="left", padx=(0,10))
            tk.Radiobutton(sec_frame, text="★ พิเศษ (P0x)",
                           variable=self.special_var, value=True,
                           bg=BG, font=FONT_SM, cursor="hand2",
                           fg="#C75000", activebackground=BG,
                           selectcolor=WHITE).pack(side="left")
            row += 1
        else:
            self.sem_var     = None
            self.year_var    = None
            self.special_var = None

        # ── Buttons ─────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=16)
        tk.Button(btn_frame, text="💾  บันทึก", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=22, pady=7,
                  cursor="hand2", activebackground=BLUE_DARK, activeforeground=WHITE,
                  command=self._save).pack(side="left", padx=8)
        tk.Button(btn_frame, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=7,
                  command=self.destroy).pack(side="left", padx=4)

        self.wait_window()

    def _save(self):
        cur_label = self.cur_var.get()
        curriculum_id = self._cur_map.get(cur_label)
        if not curriculum_id:
            messagebox.showwarning("ข้อมูลไม่ครบ",
                "กรุณาเลือกหลักสูตร", parent=self); return
        course_type = self.type_var.get().strip()

        self.result = {
            "curriculum_id": curriculum_id,
            "course_type":   course_type,
            "semester": None,
            "year":     None,
        }
        if self._has_tqf3 and self.sem_var and self.year_var:
            try:
                year = int(self.year_var.get())
                sem  = int(self.sem_var.get())
            except ValueError:
                messagebox.showwarning("ข้อมูลไม่ถูกต้อง",
                    "ปีการศึกษาต้องเป็นตัวเลข", parent=self); return
            self.result["semester"]   = sem
            self.result["year"]       = year
            self.result["is_special"] = bool(self.special_var.get()) if self.special_var else False
        self.destroy()


# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    app = TQFApp()
    app.mainloop()
