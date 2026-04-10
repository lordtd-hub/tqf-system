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
        self.tab_import  = tk.Frame(nb, bg=BG)
        nb.add(self.tab_courses, text="  📋  รายวิชาในระบบ  ")
        nb.add(self.tab_import,  text="  📥  นำเข้าข้อมูล  ")

        self._build_tab_courses()
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
    # TAB 2: นำเข้าข้อมูล
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
