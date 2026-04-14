"""
input_gui.py — ระบบจัดการ TQF สาขาคณิตศาสตร์ มรส.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys, os, sqlite3, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Windows DPI awareness (ต้องทำก่อน tk.Tk() เสมอ) ──────────────
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ── Global fix: ทุก Toplevel dialog auto-size ตาม content ──────────
_orig_wait_window = tk.Toplevel.wait_window


def _autosize_wait_window(self, window=None):
    """Auto-expand dialog height to fit content before blocking."""
    try:
        self.update_idletasks()
        req_h = self.winfo_reqheight()
        cur_h = self.winfo_height()
        if req_h > cur_h:
            cur_w = self.winfo_width() or self.winfo_reqwidth()
            self.geometry(f"{cur_w}x{req_h}")
            self.update_idletasks()
    except Exception:
        pass
    _orig_wait_window(self, window)


tk.Toplevel.wait_window = _autosize_wait_window

# ── Global fix: Escape ปิด dialog ทุก Toplevel อัตโนมัติ ───────────
_orig_toplevel_init = tk.Toplevel.__init__


def _patched_toplevel_init(self, master=None, **kw):
    _orig_toplevel_init(self, master, **kw)
    self.bind("<Escape>", lambda e: self.destroy())


tk.Toplevel.__init__ = _patched_toplevel_init

# ── Global fix: Ctrl+A เลือกทั้งหมดใน Entry ───────────────────────
_orig_entry_init = tk.Entry.__init__


def _patched_entry_init(self, master=None, **kw):
    _orig_entry_init(self, master, **kw)
    self.bind("<Control-a>", lambda e: (e.widget.select_range(0, "end"), "break")[1])
    self.bind("<Control-A>", lambda e: (e.widget.select_range(0, "end"), "break")[1])


tk.Entry.__init__ = _patched_entry_init

# ══════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════
BG        = "#F4F6F9"
FG        = "#1a1a1a"
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
# SCROLLABLE BODY — ใช้ใน dialog ที่มี content เยอะ
# ══════════════════════════════════════════════════════
class _ScrollableBody(tk.Frame):
    """
    Frame ที่มี Canvas + Scrollbar แนวตั้ง พร้อม mousewheel support.
    ใส่ widget ลงใน self.inner แทน parent โดยตรง
    ปุ่ม OK/Cancel ควร pack ลงใน Toplevel โดยตรง (ไม่ใช่ใน _ScrollableBody)
    เพื่อให้ปุ่มอยู่ด้านล่างเสมอและไม่ถูก scroll ไป
    """

    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self._vsb = ttk.Scrollbar(self, orient="vertical",
                                   command=self._canvas.yview)
        self.inner = tk.Frame(self._canvas, bg=bg)

        self._win_id = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_config)
        self._canvas.bind("<Configure>", self._on_canvas_config)
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._vsb.pack(side="right", fill="y")

        # mousewheel บน canvas และ inner frame
        for w in (self._canvas, self.inner):
            w.bind("<MouseWheel>", self._on_wheel)
            w.bind("<Button-4>", self._on_wheel)   # Linux scroll up
            w.bind("<Button-5>", self._on_wheel)   # Linux scroll down

    def _on_inner_config(self, _e=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_config(self, e):
        self._canvas.itemconfigure(self._win_id, width=e.width)

    def _on_wheel(self, e):
        if e.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif e.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(-1 * (e.delta // 120), "units")

    def bind_mousewheel(self, widget):
        """ผูก mousewheel event กับ widget ภายใน inner (เช่น Text, Combobox)."""
        widget.bind("<MouseWheel>", self._on_wheel)


def _dialog_btn_bar(parent, on_save, on_cancel,
                    save_text="💾  บันทึก", cancel_text="ยกเลิก"):
    """
    สร้าง button bar ด้านล่าง dialog — pack side=bottom ก่อน content เสมอ
    เพื่อให้ปุ่มไม่หายเมื่อ content ยาวเกิน window
    """
    bar = tk.Frame(parent, bg=BG, bd=0, relief="flat")
    bar.pack(side="bottom", fill="x", pady=(8, 14), padx=16)
    sep = tk.Frame(bar, bg="#D1D5DB", height=1)
    sep.pack(fill="x", pady=(0, 10))
    btn_row = tk.Frame(bar, bg=BG)
    btn_row.pack()
    tk.Button(btn_row, text=save_text, bg=BLUE, fg=WHITE, font=FONT_B,
              relief="flat", padx=22, pady=7, cursor="hand2",
              command=on_save).pack(side="left", padx=8)
    tk.Button(btn_row, text=cancel_text, bg="#9CA3AF", fg=WHITE, font=FONT,
              relief="flat", padx=16, pady=7, cursor="hand2",
              command=on_cancel).pack(side="left", padx=4)
    return bar


def _build_wrapped_checklist(
    parent,
    *,
    items,
    selected_values,
    text_fn,
    value_fn,
    empty_text,
    columns=4,
    height=96,
):
    """Render a multi-column checklist that wraps and scrolls vertically."""
    if not items:
        tk.Label(parent, text=empty_text, bg=BG, fg=GRAY, font=FONT_SM).pack(
            anchor="w"
        )
        return {}

    selected = set(selected_values or [])
    shell = tk.Frame(parent, bg=BG)
    shell.pack(fill="both", expand=True)

    canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, bd=0, height=height)
    vsb = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    inner = tk.Frame(canvas, bg=BG)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _sync_scroll_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(window_id, width=canvas.winfo_width())

    inner.bind("<Configure>", _sync_scroll_region)
    canvas.bind("<Configure>", _sync_scroll_region)

    vars_map = {}
    for idx, item in enumerate(items):
        value = value_fn(item)
        var = tk.BooleanVar(value=(value in selected))
        vars_map[value] = var
        col = idx % columns
        row = idx // columns
        tk.Checkbutton(
            inner,
            text=text_fn(item),
            variable=var,
            bg=BG,
            font=FONT_SM,
            cursor="hand2",
            activebackground=BG,
            anchor="w",
        ).grid(row=row, column=col, sticky="w", padx=(0, 12), pady=2)
        inner.grid_columnconfigure(col, weight=1)
    return vars_map


def _build_wrapped_action_bar(parent, *, buttons, bg=BG, columns=3, pack_kwargs=None):
    """Render a compact multi-row button bar for crowded popup actions."""
    frame = tk.Frame(parent, bg=bg)
    frame.pack(fill="x", **(pack_kwargs or {}))
    created = {}
    for idx, spec in enumerate(buttons):
        row = idx // columns
        col = idx % columns
        btn = tk.Button(
            frame,
            text=spec["text"],
            bg=spec.get("bg", BLUE),
            fg=spec.get("fg", WHITE),
            font=spec.get("font", FONT_B),
            relief="flat",
            padx=spec.get("padx", 10),
            pady=spec.get("pady", 3),
            cursor=spec.get("cursor", "hand2"),
            state=spec.get("state", "normal"),
            command=spec.get("command"),
        )
        btn.grid(row=row, column=col, sticky="ew", padx=4, pady=3)
        frame.grid_columnconfigure(col, weight=1)
        key = spec.get("key")
        if key:
            created[key] = btn
    return frame, created


def _offering_matches_search(row, raw_query):
    query = (raw_query or "").strip().lower()
    if not query:
        return True
    haystack = " ".join(
        [
            str(row.get("code", "")),
            str(row.get("name_th", "")),
            str(row.get("section_code", "")),
            str(row.get("status", "")),
            str(row.get("source_type", "")),
        ]
    ).lower()
    return query in haystack


# ══════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════
class TQFApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ระบบ TQF — สาขาคณิตศาสตร์ มรส.")
        self.geometry("960x680")
        self.minsize(840, 540)
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

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_catalog = tk.Frame(self.nb, bg=BG)
        self.tab_courses = tk.Frame(self.nb, bg=BG)
        self.tab_import  = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_catalog, text="  📚  ฐานข้อมูลหลักสูตร  ")
        self.nb.add(self.tab_courses, text="  📋  รายวิชาในระบบ  ")
        self.nb.add(self.tab_import,  text="  📥  นำเข้าข้อมูล  ")

        self._build_tab_courses()
        self._build_tab_catalog()
        self._build_tab_import()

    # ══════════════════════════════════════════════════
    # TAB 1: รายวิชาในระบบ
    # ══════════════════════════════════════════════════
    # ── state chip colors ─────────────────────────────────
    _STATE_BG: dict = {
        "not_started":     "#F5F5F5",
        "in_progress":     "#E3F2FD",
        "ready_for_tqf3":  "#E1F5FE",
        "tqf3_generated":  "#E8F5E9",
        "teaching":        "#FFF3E0",
        "grades_imported": "#F3E5F5",
        "ready_for_tqf5":  "#E0F7FA",
        "tqf5_generated":  "#DCEDC8",
        "term_closed":     "#ECEFF1",
    }
    _STATE_CHIP: dict = {
        "not_started":     "—  ยังไม่เริ่ม",
        "in_progress":     "🔵  กำลังดำเนินการ",
        "ready_for_tqf3":  "🔷  พร้อม มคอ.3",
        "tqf3_generated":  "🟢  มคอ.3 สร้างแล้ว",
        "teaching":        "🟡  กำลังสอน",
        "grades_imported": "🟣  นำเข้าเกรดแล้ว",
        "ready_for_tqf5":  "🔷  พร้อม มคอ.5",
        "tqf5_generated":  "✅  มคอ.5 สร้างแล้ว",
        "term_closed":     "🔒  ปิดภาคเรียน",
    }

    def _build_tab_courses(self):
        tab = self.tab_courses

        # shared vars (also used by Tab 2 offering filter)
        self.curriculum_var    = tk.StringVar(value="ทั้งหมด")
        self.cat_term_sem_var  = tk.StringVar(value="1")
        self.cat_term_year_var = tk.StringVar(value="2569")
        self.t1_sem_var  = tk.StringVar(value="1")
        self.t1_year_var = tk.StringVar(value="2568")

        toolbar = tk.Frame(tab, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(12, 4))

        # ── แถว 1: ชื่อ + filter ภาค/ปี + รีเฟรช ──────
        top_row = tk.Frame(toolbar, bg=BG)
        top_row.pack(fill="x")
        tk.Label(top_row, text="แดชบอร์ดภาคการศึกษา",
                 bg=BG, font=FONT_H, fg=BLUE_DARK).pack(side="left")

        right_filter = tk.Frame(top_row, bg=BG)
        right_filter.pack(side="right")
        tk.Label(right_filter, text="ภาคเรียน:", bg=BG, font=FONT_SM).pack(side="left")
        t1_sem_cb = ttk.Combobox(right_filter, textvariable=self.t1_sem_var,
                                  values=["ทั้งหมด", "1", "2", "3"],
                                  width=6, state="readonly")
        t1_sem_cb.pack(side="left", padx=(4, 10))
        t1_sem_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_courses())

        tk.Label(right_filter, text="ปีการศึกษา:", bg=BG, font=FONT_SM).pack(side="left")
        t1_year_ent = tk.Entry(right_filter, textvariable=self.t1_year_var,
                                width=8, font=FONT, relief="solid", bd=1)
        t1_year_ent.pack(side="left", padx=(4, 10))
        t1_year_ent.bind("<Return>",   lambda e: self._refresh_courses())
        t1_year_ent.bind("<FocusOut>", lambda e: self._refresh_courses())

        tk.Button(right_filter, text="รีเฟรช", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=12, pady=4, cursor="hand2",
                  activebackground=BLUE_DARK, activeforeground=WHITE,
                  command=self._refresh_courses).pack(side="left")

        # ── แถว 2: ปุ่มหลัก + ปุ่มบริบท ───────────────
        action_row = tk.Frame(toolbar, bg=BG)
        action_row.pack(fill="x", pady=(8, 0))

        tk.Button(action_row, text="➕  เปิดรายวิชา", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=14, pady=4, cursor="hand2",
                  activebackground="#0B5E0B", activeforeground=WHITE,
                  command=self._open_bulk_dialog).pack(side="left", padx=(0, 6))

        self.btn_change_state = tk.Button(
            action_row, text="🔄  เปลี่ยนสถานะ", bg="#546E7A", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4, cursor="hand2",
            state="disabled", command=self._transition_state_dialog)
        self.btn_change_state.pack(side="left", padx=(0, 12))

        # separator
        tk.Frame(action_row, bg="#D1D5DB", width=1, height=22).pack(
            side="left", padx=(0, 12), fill="y")

        self.btn_tqf3_new = tk.Button(
            action_row, text="📝  กรอก มคอ.3", bg="#0277BD", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4, cursor="hand2",
            state="disabled", command=self._goto_tqf3)
        self.btn_tqf3_new.pack(side="left", padx=(0, 6))

        self.btn_import_grade = tk.Button(
            action_row, text="📊  นำเข้าเกรด", bg="#00695C", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4, cursor="hand2",
            state="disabled", command=self._goto_import)
        self.btn_import_grade.pack(side="left", padx=(0, 6))

        self.btn_gen = tk.Button(
            action_row, text="📄  สร้าง มคอ.5", bg="#6C3483", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4, cursor="hand2",
            activebackground="#4A235A", activeforeground=WHITE,
            state="disabled", command=self._generate_tqf5)
        self.btn_gen.pack(side="left", padx=(0, 6))

        self.btn_edit = tk.Button(
            action_row, text="✏️  แก้ไข", bg="#2E7D32", fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4, cursor="hand2",
            activebackground="#1B5E20", activeforeground=WHITE,
            state="disabled", command=self._edit_course)
        self.btn_edit.pack(side="left", padx=(0, 8))

        self.t1_hint = tk.Label(
            action_row, text="← เลือกรายวิชาจากตารางเพื่อดูตัวเลือก",
            bg=BG, fg=GRAY, font=FONT_SM, anchor="w")
        self.t1_hint.pack(side="left")

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

        # columns: visible + 3 hidden (offering_id, course_id, tqf3_id, state)
        cols = ("code","name","instructor","sem_year","status",
                "tqf3","students","curriculum",
                "offering_id","course_id","tqf3_id","state")
        self.tree = ttk.Treeview(top_frame, columns=cols, show="headings",
                                 selectmode="browse", height=10)
        heads = {
            "code":        ("รหัสวิชา",  90,  "center"),
            "name":        ("ชื่อวิชา", 200,  "w"),
            "instructor":  ("ผู้สอน",   110,  "w"),
            "sem_year":    ("ภาค/ปี",    70,  "center"),
            "status":      ("สถานะ",    160,  "w"),
            "tqf3":        ("มคอ.3",     60,  "center"),
            "students":    ("นศ.",        55,  "center"),
            "curriculum":  ("หลักสูตร",  70,  "center"),
            "offering_id": ("",           0,  "center"),
            "course_id":   ("",           0,  "center"),
            "tqf3_id":     ("",           0,  "center"),
            "state":       ("",           0,  "center"),
        }
        hidden = {"offering_id", "course_id", "tqf3_id", "state"}
        for col, (heading, width, anchor) in heads.items():
            if col not in hidden:
                self.tree.heading(
                    col, text=heading,
                    command=lambda c=col: self._sort_tree(self.tree, c))
            else:
                self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor=anchor,
                             minwidth=0 if col in hidden else 40)
        for state, bg in self._STATE_BG.items():
            self.tree.tag_configure(f"s_{state}", background=bg)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._ctx_menu_dashboard)
        self.tree.bind("<Return>",   lambda e: self._on_tree_double_click())

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
        """โหลด offerings จาก DB ผ่าน get_term_dashboard() แสดงพร้อม state chip"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            import database as db
            db.init_db()

            sem_val  = self.t1_sem_var.get()
            year_val = self.t1_year_var.get()
            sem  = int(sem_val)  if sem_val  not in ("ทั้งหมด", "") else None
            try:
                year = int(year_val) if year_val not in ("ทั้งหมด", "") else None
            except ValueError:
                year = None

            rows = db.get_term_dashboard(semester=sem, year=year)

            # counter for status bar
            total   = len(rows)
            done3   = sum(1 for r in rows if r["has_tqf3"])
            done5   = sum(1 for r in rows if r["has_tqf5"])
            closed  = sum(1 for r in rows if r["state"] == "term_closed")

            for r in rows:
                state     = r["state"] or "not_started"
                chip      = self._STATE_CHIP.get(state, state)
                tqf3_icon = "✅" if r["has_tqf3"] and r["clo_count"] > 0 else (
                            "⏳" if r["has_tqf3"] else "—")
                stu_label = str(r["enrolled_count"]) if r["enrolled_count"] else "—"
                sem_year  = f"{r['semester']}/{r['year']}"
                if r["is_special"]:
                    sem_year = f"★{sem_year}"
                instructor = r["instructor_main"] or "—"

                self.tree.insert("", "end", tags=(f"s_{state}",), values=(
                    r["course_code"],
                    r["course_name"] or "(ยังไม่มีชื่อ)",
                    instructor,
                    sem_year,
                    chip,               # status column
                    tqf3_icon,          # มคอ.3 column
                    stu_label,          # นศ. column
                    r["curriculum_version"] or "—",
                    r["offering_id"],   # hidden [index 8]
                    r["course_id"],     # hidden [index 9]
                    r["tqf3_id"] or "", # hidden [index 10]
                    state,              # hidden [index 11]
                ))

            sem_txt  = f"ภาค {sem}"  if sem  else "ทุกภาค"
            year_txt = f"ปี {year}"  if year else "ทุกปี"
            self.status_var.set(
                f"{sem_txt} {year_txt}  |  offering {total}  |  "
                f"มคอ.3: {done3}  |  มคอ.5: {done5}  |  ปิดแล้ว: {closed}")

        except Exception as e:
            import traceback
            self.status_var.set(f"❌ โหลดข้อมูลไม่ได้: {e}")
            print(traceback.format_exc())

    def _on_tree_select(self, event=None):
        """คลิกเลือกแถว → แสดงปุ่มตามสถานะ + โหลดรายละเอียด"""
        sel = self.tree.selection()
        if not sel:
            for b in (self.btn_change_state, self.btn_tqf3_new,
                      self.btn_import_grade, self.btn_gen, self.btn_edit):
                b.config(state="disabled")
            self.t1_hint.config(text="← เลือกรายวิชาจากตารางเพื่อดูตัวเลือก")
            self._clear_detail()
            return

        vals        = self.tree.item(sel[0], "values")
        offering_id = vals[8]  if len(vals) > 8  else ""
        course_id   = vals[9]  if len(vals) > 9  else ""
        tqf3_id     = vals[10] if len(vals) > 10 else ""
        state       = vals[11] if len(vals) > 11 else "not_started"
        tqf3_icon   = vals[5]  if len(vals) > 5  else ""

        has_tqf3    = bool(tqf3_id)
        has_grade   = bool(tqf3_id)  # TQF5 inferred from state
        from tqf_system.core.state_machine import allowed_next, TRANSITIONS
        can_transition = bool(allowed_next(state))

        # ── เปลี่ยนสถานะ ──────────────────────────────────────────────
        self.btn_change_state.config(state="normal" if can_transition and offering_id else "disabled")

        # ── ปุ่มบริบทตามสถานะ ─────────────────────────────────────────
        self.btn_tqf3_new.config(state="normal" if offering_id else "disabled")
        self.btn_import_grade.config(
            state="normal" if has_tqf3 and state not in (
                "grades_imported","ready_for_tqf5","tqf5_generated","term_closed") else "disabled")
        self.btn_gen.config(
            state="normal" if state in (
                "grades_imported","ready_for_tqf5","tqf5_generated") else "disabled")
        self.btn_edit.config(state="normal" if course_id else "disabled")

        # hint ตาม state
        from tqf_system.core.state_machine import STATE_LABELS_TH
        hint_map = {
            "not_started":     "กด 'กรอก มคอ.3' เพื่อเริ่มกรอกข้อมูล หรือ 'เปลี่ยนสถานะ' เป็น กำลังดำเนินการ",
            "in_progress":     "กำลังกรอกข้อมูล — เปลี่ยนสถานะเป็น 'พร้อม มคอ.3' เมื่อพร้อม",
            "ready_for_tqf3":  "พร้อมสร้าง มคอ.3 — ไปที่ Tab ฐานข้อมูลหลักสูตร แล้วกด 'สร้าง มคอ.3'",
            "tqf3_generated":  "มคอ.3 สร้างแล้ว — เปลี่ยนสถานะเป็น 'กำลังสอน' เมื่อเริ่มสอน",
            "teaching":        "กำลังสอน — กด 'นำเข้าเกรด' หลังจบภาคการศึกษา",
            "grades_imported": "นำเข้าเกรดแล้ว — กด 'สร้าง มคอ.5' หรือเปลี่ยนสถานะ",
            "ready_for_tqf5":  "พร้อมสร้าง มคอ.5 — กด 'สร้าง มคอ.5' ได้เลย",
            "tqf5_generated":  "มคอ.5 สร้างแล้ว — เปลี่ยนสถานะเป็น 'ปิดภาคเรียน' เมื่อเสร็จสิ้น",
            "term_closed":     "ปิดภาคเรียนแล้ว (สถานะสุดท้าย)",
        }
        self.t1_hint.config(text=hint_map.get(state, ""))

        if tqf3_id:
            self._load_detail(int(tqf3_id), vals)
        else:
            self._clear_detail()

    def _goto_tqf3(self):
        """ไปที่ Tab ฐานข้อมูลเพื่อจัดการ มคอ.3"""
        self.nb.select(self.tab_catalog)

    def _goto_import(self):
        """ไปที่ Tab นำเข้าข้อมูล"""
        self.nb.select(self.tab_import)

    def _on_tree_double_click(self, event=None):
        """Double-click → สลับไปแท็บ นักศึกษา (ถ้ามี tqf3_id)"""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if vals[10] if len(vals) > 10 else "":   # tqf3_id at index 10
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
        course_id = vals[9]  if len(vals) > 9  else ""   # index updated
        tqf3_id   = vals[10] if len(vals) > 10 else ""   # index updated
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

    # ── Phase 3: State-transition dialog ─────────────────────────────
    def _transition_state_dialog(self):
        """เปิด dialog เปลี่ยนสถานะของ offering ที่เลือก"""
        sel = self.tree.selection()
        if not sel:
            return
        vals        = self.tree.item(sel[0], "values")
        offering_id = vals[8]  if len(vals) > 8  else ""
        course_code = vals[0]
        state       = vals[11] if len(vals) > 11 else "not_started"
        if not offering_id:
            return

        from tqf_system.core.state_machine import (
            allowed_next, STATE_LABELS_TH, IllegalTransition)

        next_states = allowed_next(state)
        if not next_states:
            messagebox.showinfo("สถานะสุดท้าย",
                f"รายวิชา {course_code} อยู่ในสถานะ '{STATE_LABELS_TH.get(state, state)}'\n"
                "ซึ่งเป็นสถานะสุดท้าย ไม่สามารถเปลี่ยนต่อไปได้อีก", parent=self)
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"เปลี่ยนสถานะ — {course_code}")
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.grab_set()
        dlg.minsize(400, 0)

        tk.Label(dlg, text=f"สถานะปัจจุบัน: {STATE_LABELS_TH.get(state, state)}",
                 bg=BG, font=FONT_B, fg=BLUE_DARK).pack(padx=20, pady=(16, 8), anchor="w")
        tk.Label(dlg, text="เลือกสถานะถัดไป:",
                 bg=BG, font=FONT_SM).pack(padx=20, anchor="w")

        to_var = tk.StringVar(value=next_states[0])
        for ns in next_states:
            tk.Radiobutton(dlg, text=STATE_LABELS_TH.get(ns, ns),
                           variable=to_var, value=ns,
                           bg=BG, font=FONT, activebackground=BG,
                           selectcolor=WHITE).pack(padx=30, anchor="w", pady=2)

        tk.Label(dlg, text="บันทึกเหตุผล (ไม่บังคับ):",
                 bg=BG, font=FONT_SM).pack(padx=20, pady=(12, 4), anchor="w")
        note_var = tk.StringVar()
        tk.Entry(dlg, textvariable=note_var, font=FONT,
                 relief="solid", bd=1).pack(padx=20, fill="x")

        def do_save():
            import database as db; db.init_db()
            try:
                db.transition_offering_state(
                    int(offering_id), to_var.get(), note_var.get())
                dlg.destroy()
                self._refresh_courses()
            except Exception as e:
                messagebox.showerror("เกิดข้อผิดพลาด", str(e), parent=dlg)

        _dialog_btn_bar(dlg, do_save, dlg.destroy)
        dlg.wait_window()

    # ── Phase 3: Bulk open-offerings dialog ──────────────────────────
    def _open_bulk_dialog(self):
        """Dialog เลือกวิชาจากหลักสูตรแล้วเปิดการสอนพร้อมกัน"""
        import database as db; db.init_db()
        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        curricula = conn.execute(
            "SELECT id, version, name_th FROM curricula ORDER BY version"
        ).fetchall()
        conn.close()

        if not curricula:
            messagebox.showinfo("ไม่มีข้อมูล",
                "ยังไม่มีหลักสูตรในระบบ — กรุณาเพิ่มหลักสูตรก่อน", parent=self)
            return

        dlg = tk.Toplevel(self)
        dlg.title("เปิดรายวิชาจากหลักสูตร")
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.grab_set()
        dlg.minsize(520, 0)

        # ── form ──────────────────────────────────────
        form = tk.Frame(dlg, bg=BG)
        form.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(form, text="หลักสูตร:", bg=BG, font=FONT_SM).grid(
            row=0, column=0, sticky="w", pady=4)
        cur_var = tk.StringVar(value=curricula[0]["version"])
        cur_cb  = ttk.Combobox(form, textvariable=cur_var,
                                values=[f"{c['version']} — {c['name_th']}" for c in curricula],
                                width=28, state="readonly")
        cur_cb.grid(row=0, column=1, sticky="w", padx=8)

        tk.Label(form, text="ภาคเรียน:", bg=BG, font=FONT_SM).grid(
            row=1, column=0, sticky="w", pady=4)
        sem_var = tk.StringVar(value=self.t1_sem_var.get()
                               if self.t1_sem_var.get() not in ("ทั้งหมด","") else "1")
        sem_cb  = ttk.Combobox(form, textvariable=sem_var,
                                values=["1","2","3"], width=5, state="readonly")
        sem_cb.grid(row=1, column=1, sticky="w", padx=8)

        tk.Label(form, text="ปีการศึกษา:", bg=BG, font=FONT_SM).grid(
            row=2, column=0, sticky="w", pady=4)
        year_var = tk.StringVar(value=self.t1_year_var.get()
                                if self.t1_year_var.get() not in ("ทั้งหมด","") else "2568")
        tk.Entry(form, textvariable=year_var, width=10,
                 font=FONT, relief="solid", bd=1).grid(row=2, column=1, sticky="w", padx=8)

        tk.Label(form, text="กลุ่มเรียน:", bg=BG, font=FONT_SM).grid(
            row=3, column=0, sticky="w", pady=4)
        sec_var = tk.StringVar(value="01")
        tk.Entry(form, textvariable=sec_var, width=10,
                 font=FONT, relief="solid", bd=1).grid(row=3, column=1, sticky="w", padx=8)

        # ── course checklist ──────────────────────────
        tk.Label(dlg, text="รายวิชาที่จะเปิด (เลือกทั้งหมดที่ต้องการ):",
                 bg=BG, font=FONT_B, fg=BLUE_DARK).pack(padx=20, anchor="w", pady=(4, 2))

        list_frame  = _ScrollableBody(dlg)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 4))
        list_frame.configure(height=200)

        check_vars: dict[int, tk.BooleanVar] = {}

        def _reload_courses(*_):
            for w in list_frame.inner.winfo_children():
                w.destroy()
            check_vars.clear()
            ver = cur_var.get().split(" — ")[0].strip()
            try:
                conn2 = sqlite3.connect(db.DB_PATH)
                conn2.row_factory = sqlite3.Row
                cur_row = conn2.execute(
                    "SELECT id FROM curricula WHERE version=?", (ver,)
                ).fetchone()
                if not cur_row:
                    conn2.close()
                    return
                courses = conn2.execute(
                    "SELECT id, code, name_th FROM courses "
                    "WHERE curriculum_id=? ORDER BY code", (cur_row["id"],)
                ).fetchall()
                conn2.close()
            except Exception:
                return
            all_var = tk.BooleanVar(value=True)

            def toggle_all():
                v = all_var.get()
                for bv in check_vars.values():
                    bv.set(v)

            tk.Checkbutton(list_frame.inner, text="เลือกทั้งหมด",
                           variable=all_var, command=toggle_all,
                           bg=BG, font=FONT_B, activebackground=BG).pack(anchor="w")
            tk.Frame(list_frame.inner, bg="#D1D5DB", height=1).pack(fill="x", pady=4)
            for crs in courses:
                bv = tk.BooleanVar(value=True)
                check_vars[crs["id"]] = bv
                tk.Checkbutton(list_frame.inner,
                               text=f"{crs['code']}  {crs['name_th']}",
                               variable=bv, bg=BG, font=FONT,
                               activebackground=BG).pack(anchor="w")

        cur_cb.bind("<<ComboboxSelected>>", _reload_courses)
        _reload_courses()

        # ── action buttons ────────────────────────────
        def do_open():
            ver = cur_var.get().split(" — ")[0].strip()
            try:
                sem  = int(sem_var.get())
                year = int(year_var.get())
            except ValueError:
                messagebox.showerror("ข้อผิดพลาด",
                    "ภาคเรียน/ปีการศึกษาต้องเป็นตัวเลข", parent=dlg)
                return
            sec = sec_var.get().strip() or "01"
            selected_ids = [cid for cid, bv in check_vars.items() if bv.get()]
            if not selected_ids:
                messagebox.showwarning("ไม่มีรายวิชา",
                    "กรุณาเลือกอย่างน้อย 1 รายวิชา", parent=dlg)
                return
            try:
                conn3 = sqlite3.connect(db.DB_PATH)
                conn3.row_factory = sqlite3.Row
                cur_row = conn3.execute(
                    "SELECT id FROM curricula WHERE version=?", (ver,)
                ).fetchone()
                conn3.close()
                if not cur_row:
                    messagebox.showerror("ข้อผิดพลาด", "ไม่พบหลักสูตร", parent=dlg)
                    return
                created = db.bulk_open_offerings(
                    cur_row["id"], selected_ids, sem, year, sec)
                messagebox.showinfo("สำเร็จ",
                    f"เปิดรายวิชาใหม่ {created} วิชา\n"
                    f"(ที่มีอยู่แล้วถูกข้ามไป {len(selected_ids)-created} วิชา)",
                    parent=dlg)
                dlg.destroy()
                self._refresh_courses()
            except Exception as e:
                messagebox.showerror("เกิดข้อผิดพลาด", str(e), parent=dlg)

        _dialog_btn_bar(dlg, do_open, dlg.destroy, save_text="➕  เปิดรายวิชาที่เลือก")
        dlg.wait_window()

    def _generate_tqf5(self):
        """สร้างไฟล์ มคอ.5 จากวิชาที่เลือกใน Treeview"""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        tqf3_id = vals[10] if len(vals) > 10 else ""   # index updated
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
                success_msg = f"สร้าง มคอ.5 เสร็จแล้ว\n{out_path}"
                self.after(0, lambda msg=success_msg: messagebox.showinfo(
                    "สำเร็จ",
                    msg,
                    parent=self))
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                error_msg = f"สร้าง มคอ.5 ไม่สำเร็จ:\n{e}"
                self.after(0, lambda msg=error_msg: messagebox.showerror(
                    "เกิดข้อผิดพลาด",
                    msg, parent=self))

        threading.Thread(target=do, daemon=True).start()

    # ── UX helpers ───────────────────────────────────────────────────

    _tree_sort_state: dict = {}   # {tree_id: (col, reverse)}

    def _sort_tree(self, tree: ttk.Treeview, col: str) -> None:
        """คลิก heading → เรียงข้อมูลใน Treeview แบบ toggle asc/desc"""
        key = id(tree)
        prev_col, prev_rev = self._tree_sort_state.get(key, (None, False))
        reverse = (not prev_rev) if col == prev_col else False
        self._tree_sort_state[key] = (col, reverse)

        items = [(tree.set(iid, col), iid) for iid in tree.get_children("")]
        try:
            items.sort(key=lambda t: (t[0] == "", t[0].lower()), reverse=reverse)
        except Exception:
            items.sort(reverse=reverse)
        for idx, (_, iid) in enumerate(items):
            tree.move(iid, "", idx)

        # ── indicator arrow in heading ─────────────────
        for c in tree["columns"]:
            text = tree.heading(c, "text").rstrip(" ▲▼")
            tree.heading(c, text=text)
        cur_text = tree.heading(col, "text").rstrip(" ▲▼")
        tree.heading(col, text=cur_text + (" ▲" if not reverse else " ▼"))

    def _ctx_menu_dashboard(self, event) -> None:
        """Right-click เมนูบริบทบน TAB1 (แดชบอร์ดภาคการศึกษา)"""
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.tree.focus(row)
        sel = self.tree.selection()
        if not sel:
            return
        vals      = self.tree.item(sel[0], "values")
        state     = vals[11] if len(vals) > 11 else "not_started"
        tqf3_id   = vals[10] if len(vals) > 10 else ""
        offering_id = vals[8] if len(vals) > 8 else ""

        from tqf_system.core.state_machine import allowed_next, STATE_LABELS_TH

        menu = tk.Menu(self, tearoff=0, bg=WHITE, fg="#212121",
                       activebackground=BLUE, activeforeground=WHITE, font=FONT)
        menu.add_command(label="✏️  แก้ไขข้อมูล",
                         command=self._edit_course,
                         state="normal" if offering_id else "disabled")
        menu.add_command(label="📝  กรอก มคอ.3",
                         command=self._goto_tqf3,
                         state="normal" if offering_id else "disabled")
        menu.add_command(label="📊  นำเข้าเกรด",
                         command=self._goto_import,
                         state="normal" if tqf3_id else "disabled")
        menu.add_command(label="📄  สร้าง มคอ.5",
                         command=self._generate_tqf5,
                         state="normal" if state in (
                             "grades_imported","ready_for_tqf5","tqf5_generated") else "disabled")
        next_states = allowed_next(state)
        if next_states and offering_id:
            menu.add_separator()
            menu.add_command(label="🔄  เปลี่ยนสถานะ…",
                             command=self._transition_state_dialog)
        menu.tk_popup(event.x_root, event.y_root)

    # ══════════════════════════════════════════════════
    # TAB 2: ฐานข้อมูลหลักสูตร (Course Catalog)
    # ══════════════════════════════════════════════════
    def _build_tab_catalog(self):
        tab = self.tab_catalog

        # ── Toolbar ──────────────────────────────────
        self.cat_cur_var = tk.StringVar(value="ทั้งหมด")
        toolbar = tk.Frame(tab, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(12, 6))

        top_row = tk.Frame(toolbar, bg=BG)
        top_row.pack(fill="x")
        tk.Label(top_row, text="ฐานข้อมูลหลักสูตร / รายวิชา",
                 bg=BG, font=FONT_H, fg=BLUE_DARK).pack(side="left")

        filter_frame = tk.Frame(top_row, bg=BG)
        filter_frame.pack(side="right")
        tk.Label(filter_frame, text="หลักสูตร:", bg=BG, font=FONT_SM).pack(side="left")
        self.cat_cur_combo = ttk.Combobox(
            filter_frame, textvariable=self.cat_cur_var, values=["ทั้งหมด"],
            width=10, state="readonly")
        self.cat_cur_combo.pack(side="left", padx=(4, 8))
        self.cat_cur_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: (self._refresh_catalog(), self._refresh_catalog_offerings()),
        )
        tk.Button(filter_frame, text="รีเฟรช", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=12, pady=4,
                  cursor="hand2", activebackground=BLUE_DARK, activeforeground=WHITE,
                  command=self._refresh_catalog).pack(side="left")

        self.cat_offering_search_var = tk.StringVar(value="")
        offering_filter_row = tk.Frame(toolbar, bg=BG)
        offering_filter_row.pack(fill="x", pady=(8, 0))
        tk.Label(offering_filter_row, text="รายวิชาที่เปิดสอน:", bg=BG,
                 fg=BLUE_DARK, font=FONT_B).pack(side="left")
        tk.Label(offering_filter_row, text="ภาคเรียน", bg=BG,
                 font=FONT_SM).pack(side="left", padx=(12, 4))
        sem_combo = ttk.Combobox(
            offering_filter_row,
            textvariable=self.cat_term_sem_var,
            values=["1", "2", "3"],
            width=4,
            state="readonly",
        )
        sem_combo.pack(side="left")
        sem_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_catalog_offerings())
        tk.Label(offering_filter_row, text="ปีการศึกษา", bg=BG,
                 font=FONT_SM).pack(side="left", padx=(12, 4))
        year_ent = tk.Entry(
            offering_filter_row,
            textvariable=self.cat_term_year_var,
            width=8, font=FONT, relief="solid", bd=1,
        )
        year_ent.pack(side="left")
        year_ent.bind("<Return>", lambda e: self._refresh_catalog_offerings())
        year_ent.bind("<FocusOut>", lambda e: self._refresh_catalog_offerings())
        tk.Button(
            offering_filter_row, text="แสดงข้อมูล", bg="#455A64", fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", command=self._refresh_catalog_offerings
        ).pack(side="left", padx=(8, 0))
        tk.Label(offering_filter_row, text="ค้นหา", bg=BG,
                 font=FONT_SM).pack(side="left", padx=(12, 4))
        self.cat_offering_search_entry = tk.Entry(
            offering_filter_row,
            textvariable=self.cat_offering_search_var,
            width=24,
            font=FONT,
            relief="solid",
            bd=1,
        )
        self.cat_offering_search_entry.pack(side="left")
        self.cat_offering_search_entry.bind(
            "<KeyRelease>", lambda e: self._refresh_catalog_offerings()
        )
        self.btn_cat_add_offering = tk.Button(
            offering_filter_row, text="เปิดสอนวิชาที่เลือก", bg=GREEN, fg=WHITE,
            font=FONT_B, relief="flat", padx=14, pady=4,
            cursor="hand2", state="disabled", command=self._add_course_offering
        )
        self.btn_cat_add_offering.pack(side="right")
        tk.Label(
            offering_filter_row,
            text="ใช้ตัวกรองนี้เพื่อจัดการรายวิชาที่เปิดสอนจริงในแต่ละภาคเรียน",
            bg=BG, fg=GRAY, font=FONT_SM, anchor="w",
        ).pack(side="left", padx=(12, 0))

        action_row = tk.Frame(toolbar, bg=BG)
        action_row.pack(fill="x", pady=(8, 0))

        # ── ปุ่มหลัก (เสมอมองเห็น) ─────────────────────
        tk.Button(action_row, text="เพิ่มวิชา", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=14, pady=4,
                  cursor="hand2", activebackground="#0B5E0B", activeforeground=WHITE,
                  command=self._add_catalog_course).pack(side="left", padx=(0, 6))
        self.btn_cat_edit = tk.Button(
            action_row, text="แก้ไขวิชา", bg=BLUE, fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", state="disabled", command=self._edit_catalog_course)
        self.btn_cat_edit.pack(side="left", padx=(0, 6))
        self.btn_cat_gen3 = tk.Button(
            action_row, text="สร้าง มคอ.3", bg="#6C3483", fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", state="disabled", command=self._generate_tqf3)
        self.btn_cat_gen3.pack(side="left", padx=(0, 6))
        self.btn_cat_del = tk.Button(
            action_row, text="ลบวิชา", bg=RED, fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", state="disabled", command=self._delete_catalog_course)
        self.btn_cat_del.pack(side="left", padx=(0, 6))

        # ── ปุ่มรอง — เก็บเป็น attr เพื่อ state management แต่ไม่ pack ในแถบ ──
        self.btn_cat_clo = tk.Button(
            action_row, text="แก้ไข CLO", bg="#1565C0", fg=WHITE,
            font=FONT_B, relief="flat", cursor="hand2",
            state="disabled", command=self._edit_course_clos)
        self.btn_cat_llo = tk.Button(
            action_row, text="LLO", bg="#0277BD", fg=WHITE,
            font=FONT_B, relief="flat", cursor="hand2",
            state="disabled", command=self._edit_course_llos)
        self.btn_cat_plan = tk.Button(
            action_row, text="แผนการสอน", bg="#00838F", fg=WHITE,
            font=FONT_B, relief="flat", cursor="hand2",
            state="disabled", command=self._edit_course_teaching_plan)
        self.btn_cat_res = tk.Button(
            action_row, text="ทรัพยากร", bg="#00695C", fg=WHITE,
            font=FONT_B, relief="flat", cursor="hand2",
            state="disabled", command=self._edit_course_resources)
        self.btn_cat_staff = tk.Button(
            action_row, text="บุคลากร มคอ.3", bg="#4527A0", fg=WHITE,
            font=FONT_B, relief="flat", cursor="hand2",
            state="disabled", command=self._edit_course_staff)

        # ── "เพิ่มเติม ▼" dropdown ──────────────────────
        self.cat_more_menu = tk.Menu(
            action_row, tearoff=0, bg=WHITE, fg="#212121",
            activebackground=BLUE, activeforeground=WHITE, font=FONT)
        # รายการที่ขึ้นกับ selection (5 รายการแรก)
        _sel_entries = [
            ("แก้ไข CLO",      self._edit_course_clos),
            ("LLO",            self._edit_course_llos),
            ("แผนการสอน",     self._edit_course_teaching_plan),
            ("ทรัพยากร",      self._edit_course_resources),
            ("บุคลากร มคอ.3", self._edit_course_staff),
        ]
        for label, cmd in _sel_entries:
            self.cat_more_menu.add_command(label=label, command=cmd, state="disabled")
        self.cat_more_menu.add_separator()
        self.cat_more_menu.add_command(label="PLO",
                                       command=self._manage_plos)
        self.cat_more_menu.add_command(label="ข้อมูลหลักสูตร",
                                       command=self._show_curriculum_overview)
        self._cat_more_sel_count = len(_sel_entries)  # how many entries need selection

        self.btn_cat_more = tk.Menubutton(
            action_row, text="เพิ่มเติม ▼", bg="#546E7A", fg=WHITE,
            font=FONT_B, relief="flat", padx=12, pady=4,
            cursor="hand2", menu=self.cat_more_menu,
            activebackground="#37474F", activeforeground=WHITE)
        self.btn_cat_more.pack(side="left", padx=(8, 0))

        paned = tk.PanedWindow(tab, orient="horizontal", bg=BG,
                               sashwidth=6, sashrelief="flat", opaqueresize=True)
        paned.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        # ── ซ้าย: ตารางวิชา ──────────────────────────
        left = tk.Frame(paned, bg=BG)
        paned.add(left, minsize=300, stretch="never")

        left_split = tk.PanedWindow(
            left, orient="vertical", bg=BG,
            sashwidth=6, sashrelief="flat", opaqueresize=True
        )
        left_split.pack(fill="both", expand=True)

        course_frame = tk.Frame(left, bg=BG)
        left_split.add(course_frame, minsize=180, stretch="always")

        cat_cols = ("code", "name", "credits", "type", "clo_count", "course_id")
        self.cat_tree = ttk.Treeview(
            course_frame, columns=cat_cols, show="headings",
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
        self.cat_tree.bind("<Double-1>",  self._edit_catalog_course)
        self.cat_tree.bind("<Return>",    self._edit_catalog_course)
        self.cat_tree.bind("<Button-3>",  self._ctx_menu_catalog_course)
        cat_vsb = ttk.Scrollbar(course_frame, orient="vertical", command=self.cat_tree.yview)
        self.cat_tree.configure(yscrollcommand=cat_vsb.set)
        self.cat_tree.pack(side="left", fill="both", expand=True)
        cat_vsb.pack(side="right", fill="y")

        offering_frame = tk.Frame(left, bg=BG)
        left_split.add(offering_frame, minsize=170, stretch="always")

        offering_action_row = tk.Frame(offering_frame, bg=BG)
        offering_action_row.pack(fill="x", pady=(0, 4))
        self.btn_cat_add_offering_visible = tk.Button(
            offering_action_row,
            text="เพิ่มวิชาจากหลักสูตรไปยังเทอมนี้",
            bg=GREEN,
            fg=WHITE,
            font=FONT_B,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._add_course_offering,
        )
        self.btn_cat_add_offering_visible.pack(side="right")

        tk.Label(
            offering_frame, text="รายวิชาที่เปิดสอน", bg=BG,
            fg=BLUE_DARK, font=FONT_B, anchor="w"
        ).pack(fill="x", pady=(0, 4))

        tk.Label(
            offering_frame,
            text="เลือกแถวในตาราง แล้วใช้ปุ่มจัดการทางด้านขวา",
            bg=BG,
            fg=GRAY,
            font=FONT_SM,
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        offering_cols = ("code", "name", "section", "kind", "tqf3", "status", "offering_id", "course_id", "tqf3_id")
        self.cat_offering_tree = ttk.Treeview(
            offering_frame, columns=offering_cols, show="headings",
            selectmode="browse", height=8
        )
        offering_heads = {
            "code": ("รหัส", 80, "center"),
            "name": ("รายวิชา", 145, "w"),
            "section": ("ตอนเรียน", 62, "center"),
            "kind": ("ประเภท", 58, "center"),
            "tqf3": ("TQF3", 48, "center"),
            "status": ("สถานะ", 90, "w"),
            "offering_id": ("", 0, "center"),
            "course_id": ("", 0, "center"),
            "tqf3_id": ("", 0, "center"),
        }
        hidden_cols = {"offering_id", "course_id", "tqf3_id"}
        for col, (heading, width, anchor) in offering_heads.items():
            if col not in hidden_cols:
                self.cat_offering_tree.heading(
                    col, text=heading,
                    command=lambda c=col: self._sort_tree(self.cat_offering_tree, c))
            else:
                self.cat_offering_tree.heading(col, text=heading)
            self.cat_offering_tree.column(
                col, width=width, anchor=anchor,
                minwidth=0 if col in hidden_cols else 40
            )
        self.cat_offering_tree.bind("<<TreeviewSelect>>", self._on_catalog_offering_select)
        self.cat_offering_tree.bind("<Double-1>",  self._on_catalog_offering_dbl_click)
        self.cat_offering_tree.bind("<Button-3>",  self._ctx_menu_offering)
        self.cat_offering_tree.bind("<Return>",    self._on_catalog_offering_dbl_click)
        self.cat_offering_tree.bind("<Delete>",    lambda e: self._delete_course_offering_v2())
        self.cat_offering_tree.tag_configure("odd", background=WHITE)
        self.cat_offering_tree.tag_configure("even", background="#F7FAFC")
        offering_vsb = ttk.Scrollbar(
            offering_frame, orient="vertical", command=self.cat_offering_tree.yview
        )
        self.cat_offering_tree.configure(yscrollcommand=offering_vsb.set)
        self.cat_offering_tree.pack(side="left", fill="both", expand=True)
        offering_vsb.pack(side="right", fill="y")

        self.cat_offering_status_var = tk.StringVar(value="")
        tk.Label(
            offering_frame, textvariable=self.cat_offering_status_var,
            bg=BG, fg=GRAY, font=FONT_SM, anchor="w"
        ).pack(fill="x", pady=(4, 0))

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

        context_frame = tk.LabelFrame(
            right,
            text="จัดการการเปิดสอนที่เลือก",
            bg=WHITE,
            fg=BLUE_DARK,
            font=FONT_B,
            padx=10,
            pady=8,
        )
        context_frame.pack(fill="x", padx=10, pady=(10, 6))
        self.cat_offering_context_var = tk.StringVar(
            value="เลือกการเปิดสอนในตารางเพื่อสร้าง มคอ.3 หรือจัดการข้อมูลรายเทอม"
        )
        tk.Label(
            context_frame,
            textvariable=self.cat_offering_context_var,
            bg=WHITE,
            fg=GRAY,
            font=FONT_SM,
            anchor="w",
            justify="left",
        ).pack(fill="x")
        context_buttons = tk.Frame(context_frame, bg=WHITE)
        context_buttons.pack(fill="x", pady=(8, 0))
        self.btn_cat_offering_gen3 = tk.Button(
            context_buttons, text="สร้าง มคอ.3", bg="#6C3483", fg=WHITE,
            font=FONT_B, relief="flat", padx=10, pady=4,
            cursor="hand2", state="disabled", command=self._generate_selected_offering_tqf3
        )
        self.btn_cat_offering_gen3.pack(side="left", padx=(0, 6))
        self.btn_cat_offering_staff = tk.Button(
            context_buttons, text="บุคลากร มคอ.3", bg="#4527A0", fg=WHITE,
            font=FONT_B, relief="flat", padx=10, pady=4,
            cursor="hand2", state="disabled", command=self._edit_selected_offering_staff
        )
        self.btn_cat_offering_staff.pack(side="left", padx=(0, 6))
        self.btn_cat_offering_instructors = tk.Button(
            context_buttons, text="ผู้สอน", bg="#00838F", fg=WHITE,
            font=FONT_B, relief="flat", padx=10, pady=4,
            cursor="hand2", state="disabled", command=self._edit_offering_instructors
        )
        self.btn_cat_offering_instructors.pack(side="left", padx=(0, 6))
        self.btn_cat_del_offering = tk.Button(
            context_buttons, text="ลบการเปิดสอน", bg=RED, fg=WHITE,
            font=FONT_B, relief="flat", padx=10, pady=4,
            cursor="hand2", state="disabled", command=self._delete_course_offering_v2
        )
        self.btn_cat_del_offering.pack(side="left")

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
        self.cat_detail_text.tag_config("plo_num", foreground="#1565C0",
                                        font=("Arial", 9, "bold"))
        self.cat_detail_text.tag_config("ylo_num", foreground="#4A148C",
                                        font=("Arial", 9, "bold"))
        self.cat_detail_text.tag_config("sub",  foreground="#546E7A")
        cat_vsb2.pack(side="right", fill="y")
        self.cat_detail_text.pack(side="left", fill="both", expand=True)

        # status bar
        self.cat_status_var = tk.StringVar(value="")
        tk.Label(tab, textvariable=self.cat_status_var,
                 bg=BG, fg=GRAY, font=FONT_SM, anchor="w").pack(
                 fill="x", padx=18, pady=(0, 6))

        self.after(350, self._refresh_catalog)
        self.after(450, self._refresh_catalog_offerings)

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

            # auto-show curriculum overview เมื่อเลือกหลักสูตรเฉพาะ
            if filt != "ทั้งหมด":
                curr_row = next(
                    (r for r in curricula
                     if str(r["version"]) == filt.replace("หลักสูตร ", "").strip()),
                    None)
                if curr_row:
                    self._load_curriculum_overview(curr_row["id"])
                    return
            self._clear_cat_detail()
        except Exception as e:
            self.cat_status_var.set(f"❌ โหลดไม่ได้: {e}")

    def _catalog_term_context(self):
        curriculum_id = None
        filt = self.cat_cur_var.get()
        try:
            import database as db; db.init_db()
            with sqlite3.connect(db.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                if filt != "เธ—เธฑเนเธเธซเธกเธ”":
                    ver = filt.replace("เธซเธฅเธฑเธเธชเธนเธ•เธฃ ", "").strip()
                    row = conn.execute(
                        "SELECT id FROM curricula WHERE version=?",
                        (ver,),
                    ).fetchone()
                    if row:
                        curriculum_id = row["id"]
        except Exception:
            curriculum_id = None

        try:
            semester = int(self.cat_term_sem_var.get())
        except Exception:
            semester = None
        try:
            year = int(self.cat_term_year_var.get())
        except Exception:
            year = None
        return curriculum_id, semester, year

    def _refresh_catalog_offerings(self, preserve_offering_id=None):
        for item in self.cat_offering_tree.get_children():
            self.cat_offering_tree.delete(item)

        curriculum_id, semester, year = self._catalog_term_context()
        if semester is None or year is None:
            self.cat_offering_status_var.set("กรุณาระบุภาคเรียนและปีการศึกษาให้ถูกต้อง")
            return

        try:
            import database as db; db.init_db()
            offerings = db.get_course_offerings(
                curriculum_id=curriculum_id,
                semester=semester,
                year=year,
            )
        except Exception as e:
            self.cat_offering_status_var.set(f"โหลด offerings ไม่ได้: {e}")
            return

        selected_item = None
        search_query = self.cat_offering_search_var.get().strip()
        visible_count = 0
        for row in offerings:
            if not _offering_matches_search(row, search_query):
                continue
            tqf3_flag = "มี" if row.get("tqf3_id") else "-"
            kind = "พิเศษ" if row.get("is_special") else "ปกติ"
            status_map = {
                "generated": "สร้างจากระบบ",
                "imported": "นำเข้า",
                "catalog": "จากแม่แบบ",
                "active": "เปิดสอน",
                "planned": "วางแผน",
            }
            status = status_map.get(row.get("source_type") or row.get("status"), row.get("source_type") or row.get("status") or "-")
            item_id = str(row["id"])
            row_tag = "even" if visible_count % 2 == 0 else "odd"
            self.cat_offering_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    row.get("code", ""),
                    row.get("name_th", "") or "-",
                    row.get("section_code", "") or "-",
                    kind,
                    tqf3_flag,
                    status,
                    row["id"],
                    row.get("course_id", ""),
                    row.get("tqf3_id", "") or "",
                ),
                tags=(row_tag,),
            )
            visible_count += 1
            if preserve_offering_id and row["id"] == preserve_offering_id:
                selected_item = item_id

        self.cat_offering_status_var.set(
            f"การเปิดสอน {len(offerings)} รายวิชา ในภาค {semester}/{year}"
        )
        if search_query:
            self.cat_offering_status_var.set(
                f"พบ {visible_count} / {len(offerings)} รายการ ในภาค {semester}/{year}"
            )
        if selected_item:
            self.cat_offering_tree.selection_set(selected_item)
            self.cat_offering_tree.focus(selected_item)
            self.cat_offering_tree.see(selected_item)
        self._on_catalog_offering_select()

    def _focus_catalog_course(self, course_id: int):
        target = str(course_id)
        for item in self.cat_tree.get_children():
            vals = self.cat_tree.item(item, "values")
            if len(vals) >= 6 and str(vals[5]) == target:
                self.cat_tree.selection_set(item)
                self.cat_tree.focus(item)
                self.cat_tree.see(item)
                return vals
        return None

    def _selected_catalog_offering(self):
        sel = self.cat_offering_tree.selection()
        if not sel:
            return None
        vals = self.cat_offering_tree.item(sel[0], "values")
        if len(vals) < 9:
            return None
        return {
            "code": vals[0],
            "name": vals[1],
            "section_code": vals[2],
            "kind": vals[3],
            "tqf3_flag": vals[4],
            "status": vals[5],
            "offering_id": int(vals[6]),
            "course_id": int(vals[7]),
            "tqf3_id": int(vals[8]) if str(vals[8]).strip() else None,
        }

    def _on_catalog_select(self, event=None):
        sel = self.cat_tree.selection()
        state = "normal" if sel else "disabled"
        self.btn_cat_edit.config(state=state)
        self.btn_cat_del.config(state=state)
        self.btn_cat_gen3.config(state=state)
        # hidden button attrs — keep state in sync even though not packed in toolbar
        self.btn_cat_clo.config(state=state)
        self.btn_cat_llo.config(state=state)
        self.btn_cat_plan.config(state=state)
        self.btn_cat_res.config(state=state)
        self.btn_cat_staff.config(state=state)
        # dropdown menu entries
        for idx in range(self._cat_more_sel_count):
            self.cat_more_menu.entryconfigure(idx, state=state)
        self.btn_cat_add_offering.config(state=state)
        if hasattr(self, "btn_cat_add_offering_visible"):
            self.btn_cat_add_offering_visible.config(state=state)
        if not sel:
            self._clear_cat_detail()
            return

        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        self._load_cat_detail(course_id, vals)

    def _on_catalog_offering_select(self, event=None):
        offering = self._selected_catalog_offering()
        has_offering = offering is not None
        self.btn_cat_offering_gen3.config(state="normal" if has_offering else "disabled")
        self.btn_cat_offering_staff.config(
            state="normal" if has_offering and offering.get("tqf3_id") else "disabled"
        )
        self.btn_cat_offering_instructors.config(
            state="normal" if has_offering else "disabled"
        )
        self.btn_cat_del_offering.config(
            state="normal" if has_offering else "disabled"
        )
        if not offering:
            if hasattr(self, "cat_offering_context_var"):
                self.cat_offering_context_var.set(
                    "เลือกการเปิดสอนในตารางเพื่อสร้าง มคอ.3 หรือจัดการข้อมูลรายเทอม"
                )
            return

        if hasattr(self, "cat_offering_context_var"):
            tqf3_text = "มี มคอ.3 แล้ว" if offering.get("tqf3_id") else "ยังไม่มี มคอ.3"
            self.cat_offering_context_var.set(
                f"{offering['code']} {offering['section_code']} | {offering['status']} | {tqf3_text}"
            )

        vals = self._focus_catalog_course(offering["course_id"])
        if vals:
            self._load_cat_detail(offering["course_id"], vals)

    def _on_catalog_offering_dbl_click(self, event=None) -> None:
        """Double-click หรือ Enter บน offering tree → เปิด dialog แก้ไขการเปิดสอน"""
        offering = self._selected_catalog_offering()
        if not offering:
            return
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT id, code, name_th, curriculum_id FROM courses WHERE id=?",
                (offering["course_id"],),
            ).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", str(e), parent=self)
            return
        if not course:
            return
        dlg = CourseOfferingDialog(
            self, course,
            semester_default=str(offering["semester"]),
            year_default=str(offering["year"]),
            existing=offering,          # pre-fill existing values
        )
        if not dlg.result:
            return
        try:
            import database as db; db.init_db()
            oid = db.upsert_course_offering(
                offering["course_id"],
                dlg.result["semester"],
                dlg.result["year"],
                curriculum_id=course["curriculum_id"],
                section_code=dlg.result["section_code"],
                is_special=dlg.result["is_special"],
                status=dlg.result["status"],
                source_type="catalog",
            )
            self._refresh_catalog_offerings(preserve_offering_id=oid)
            self._refresh_courses()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _ctx_menu_offering(self, event) -> None:
        """Right-click เมนูบริบทบน catalog offering tree"""
        row = self.cat_offering_tree.identify_row(event.y)
        if row:
            self.cat_offering_tree.selection_set(row)
            self.cat_offering_tree.focus(row)
        offering = self._selected_catalog_offering()
        if not offering:
            return
        has_tqf3 = bool(offering.get("tqf3_id"))
        menu = tk.Menu(self, tearoff=0, bg=WHITE, fg="#212121",
                       activebackground=BLUE, activeforeground=WHITE, font=FONT)
        menu.add_command(label="✏️  แก้ไขการเปิดสอน",
                         command=self._on_catalog_offering_dbl_click)
        menu.add_command(label="📋  สร้าง มคอ.3",
                         command=self._generate_tqf3,
                         state="normal")
        menu.add_command(label="👥  จัดการผู้สอน",
                         command=self._edit_offering_instructors,
                         state="normal")
        menu.add_separator()
        menu.add_command(label="🗑️  ลบการเปิดสอน",
                         command=self._delete_course_offering_v2,
                         state="normal")
        menu.tk_popup(event.x_root, event.y_root)

    def _ctx_menu_catalog_course(self, event) -> None:
        """Right-click เมนูบริบทบน course list ใน Tab 2"""
        row = self.cat_tree.identify_row(event.y)
        if row:
            self.cat_tree.selection_set(row)
            self.cat_tree.focus(row)
        sel = self.cat_tree.selection()
        if not sel:
            return
        menu = tk.Menu(self, tearoff=0, bg=WHITE, fg="#212121",
                       activebackground=BLUE, activeforeground=WHITE, font=FONT)
        menu.add_command(label="✏️  แก้ไขข้อมูลวิชา",  command=self._edit_catalog_course)
        menu.add_command(label="⚙️  แก้ไข CLO",         command=self._edit_course_clos)
        menu.add_command(label="📋  แผนการสอน",          command=self._edit_course_teaching_plan)
        menu.add_separator()
        menu.add_command(label="📂  เปิดสอนวิชานี้",     command=self._add_course_offering)
        menu.add_separator()
        menu.add_command(label="🗑️  ลบวิชา",             command=self._delete_catalog_course)
        menu.tk_popup(event.x_root, event.y_root)

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
            plan_rows = conn.execute(
                "SELECT * FROM course_teaching_plan WHERE course_id=? ORDER BY seq, week, id",
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
        total_hours = sum((r["hours_planned"] or 0) for r in plan_rows)
        t.insert("end", f"\nแผนการสอนรายสัปดาห์ ({len(plan_rows)} แถว  รวม {total_hours:.0f} ชม.)\n", "h1")
        t.insert("end", "โ”€" * 60 + "\n", "dim")
        if plan_rows:
            for row in plan_rows[:8]:
                label = row["week_label"] or row["week"] or "โ€”"
                topic = row["topic"] or "(ยังไม่ระบุหัวข้อ)"
                llo = row["llo_text"] or "โ€”"
                method = row["teaching_method"] or row["activities"] or "โ€”"
                t.insert("end", f"  {label:<10}", "h2")
                t.insert("end", f"{topic}\n")
                t.insert(
                    "end",
                    f"       LLO: {llo}  |  สอน: {method}"
                    f"  |  ชั่วโมง: {(row['hours_planned'] or 0):.0f}\n",
                    "dim",
                )
            if len(plan_rows) > 8:
                t.insert("end", f"  ... และอีก {len(plan_rows) - 8} แถว\n", "dim")
        else:
            t.insert("end", "  ยังไม่มีแผนการสอน โ€” กด แผนการสอน เพื่อเพิ่ม\n", "warn")

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

    def _load_cat_detail(self, course_id: int, vals):
        self.cat_detail_title.config(text=f"  {vals[0]}  {vals[1]}")
        try:
            import database as db

            db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT c.*, cu.version AS cur_ver "
                "FROM courses c LEFT JOIN curricula cu ON cu.id=c.curriculum_id "
                "WHERE c.id=?",
                (course_id,),
            ).fetchone()
            clos = conn.execute(
                "SELECT * FROM course_clos WHERE course_id=? ORDER BY clo_number",
                (course_id,),
            ).fetchall()
            asmt = conn.execute(
                "SELECT * FROM course_assessments WHERE course_id=? ORDER BY seq,id",
                (course_id,),
            ).fetchall()
            plan_rows = conn.execute(
                "SELECT * FROM course_teaching_plan WHERE course_id=? ORDER BY seq, week, id",
                (course_id,),
            ).fetchall()
            offerings = conn.execute(
                """
                SELECT
                    o.semester,
                    o.year,
                    o.section_code,
                    o.is_special,
                    o.status,
                    o.source_type,
                    t.id AS tqf3_id
                FROM course_offerings o
                LEFT JOIN tqf3 t ON t.offering_id = o.id
                WHERE o.course_id=?
                ORDER BY o.year DESC, o.semester DESC, o.section_code
                """,
                (course_id,),
            ).fetchall()
            conn.close()
        except Exception as e:
            self._set_cat_detail(f"โหลดไม่ได้: {e}")
            return

        t = self.cat_detail_text
        t.configure(state="normal")
        t.delete("1.0", "end")

        divider = "-" * 60 + "\n"
        cr = dict(course) if course else {}

        t.insert("end", "ข้อมูลทั่วไป\n", "h1")
        t.insert("end", divider, "dim")
        t.insert("end", f"หลักสูตร  : {cr.get('cur_ver', '?')}\n")
        t.insert("end", f"รหัสวิชา  : {cr.get('code', '')}\n")
        t.insert("end", f"ชื่อไทย   : {cr.get('name_th', '')}\n")
        t.insert("end", f"ชื่ออังกฤษ: {cr.get('name_en', '') or '-'}\n")
        t.insert(
            "end",
            f"หน่วยกิต  : {cr.get('credits_text', '') or '-'}"
            f"  (บรรยาย-ปฏิบัติ-ค้นคว้า: "
            f"{cr.get('credit_lecture', 0)}-{cr.get('credit_lab', 0)}-{cr.get('credit_self', 0)})\n",
        )
        t.insert("end", f"ประเภท    : {cr.get('course_type', '') or '-'}\n")
        t.insert("end", f"บังคับก่อน: {cr.get('prerequisite', '') or 'ไม่มี'}\n")
        if cr.get("description_th"):
            t.insert("end", f"คำอธิบาย  : {cr['description_th']}\n")

        t.insert("end", f"\nการเปิดสอน ({len(offerings)} ครั้ง)\n", "h1")
        t.insert("end", divider, "dim")
        if offerings:
            for row in offerings:
                special = " [พิเศษ]" if row["is_special"] else ""
                section = f" {row['section_code']}" if row["section_code"] else ""
                source_map = {
                    "generated": "สร้างจากระบบ",
                    "imported": "นำเข้า",
                    "catalog": "จากแม่แบบ",
                }
                source_label = source_map.get(row["source_type"], row["source_type"] or "")
                source = f" ({source_label})" if source_label else ""
                tqf3_mark = " มี มคอ.3" if row["tqf3_id"] else ""
                special = " [พิเศษ]" if row["is_special"] else ""
                display_line = f"  ภาค {row['semester']}/{row['year']}{section}{special}{source}{tqf3_mark}\n"
                t.insert("end", display_line, "ok")
                continue
                t.insert(
                    "end",
                    f"  เธ เธฒเธ {row['semester']}/{row['year']}{section}{special}{source}{tqf3_mark}\n",
                    "ok",
                )
                continue
                t.insert("end", f"  ภาค {row['semester']}/{row['year']}{special}{source}\n", "ok")
        else:
            t.insert("end", "  ยังไม่เคยเปิดสอน\n", "dim")

        t.insert("end", f"\nCLO มาตรฐาน ({len(clos)} ข้อ)\n", "h1")
        t.insert("end", divider, "dim")
        if clos:
            for row in clos:
                plo_nums = json.loads(row["plo_mapping"] if row["plo_mapping"] else "[]")
                plo_str = ", ".join(f"PLO{p}" for p in plo_nums) if plo_nums else "-"
                t.insert("end", f"CLO{row['clo_number']}  ", "h2")
                t.insert("end", f"{row['description'] or '(ยังไม่มีคำอธิบาย)'}\n")
                t.insert(
                    "end",
                    f"       ตอบสนอง: {plo_str}  |  "
                    f"เกณฑ์ผ่าน: {row['pass_threshold_pct']:.0f}%  |  "
                    f"วิธีสอน: {row['teaching_strategy'] or '-'}\n",
                    "dim",
                )
        else:
            t.insert("end", "  ยังไม่มี CLO มาตรฐาน - กด แก้ไข CLO เพื่อเพิ่ม\n", "warn")

        total_hours = sum((row["hours_planned"] or 0) for row in plan_rows)
        t.insert("end", f"\nแผนการสอนรายสัปดาห์ ({len(plan_rows)} แถว  รวม {total_hours:.0f} ชม.)\n", "h1")
        t.insert("end", divider, "dim")
        if plan_rows:
            for row in plan_rows[:8]:
                label = row["week_label"] or row["week"] or "-"
                topic = row["topic"] or "(ยังไม่ระบุหัวข้อ)"
                llo = row["llo_text"] or "-"
                method = row["teaching_method"] or row["activities"] or "-"
                t.insert("end", f"  {label:<10}", "h2")
                t.insert("end", f"{topic}\n")
                t.insert(
                    "end",
                    f"       LLO: {llo}  |  สอน: {method}"
                    f"  |  ชั่วโมง: {(row['hours_planned'] or 0):.0f}\n",
                    "dim",
                )
            if len(plan_rows) > 8:
                t.insert("end", f"  ... และอีก {len(plan_rows) - 8} แถว\n", "dim")
        else:
            t.insert("end", "  ยังไม่มีแผนการสอน - กด แผนการสอน เพื่อเพิ่ม\n", "warn")

        total_w = sum(row["weight_pct"] for row in asmt)
        t.insert("end", f"\nแผนการประเมิน ({len(asmt)} รายการ  รวม {total_w:.0f}%)\n", "h1")
        t.insert("end", divider, "dim")
        if asmt:
            for row in asmt:
                t.insert("end", f"  {row['name']:<20}", "h2")
                t.insert(
                    "end",
                    f"  คะแนนเต็ม {row['full_score']:.0f}  |  "
                    f"น้ำหนัก {row['weight_pct']:.0f}%  |  "
                    f"ผ่าน {row['pass_threshold']:.0f}%\n",
                )
            if abs(total_w - 100) > 0.5:
                t.insert("end", f"  รวม {total_w:.0f}% (ควรได้ 100%)\n", "warn")
        else:
            t.insert("end", "  ยังไม่มีแผนการประเมิน\n", "dim")

        t.configure(state="disabled")

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
                self._refresh_catalog_offerings()
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
                self._refresh_catalog()
                self._refresh_catalog_offerings()
                self._refresh_courses()
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
            self._refresh_catalog()
            self._refresh_catalog_offerings()
            self._refresh_courses()
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

    def _edit_course_llos(self):
        sel = self.cat_tree.selection()
        if not sel: return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        try:
            import database as db; db.init_db()
            course = dict(sqlite3.connect(db.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
                          .execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
                          or {})
            llos = db.get_llos(course_id)
            clos = db.get_course_clos(course_id)
            mapping = db.get_clo_llo_map(course_id)
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self); return

        dlg = LLOEditorDialog(self, course, llos, clos, mapping)
        if dlg.result:
            try:
                import database as db; db.init_db()
                db.replace_llos(course_id, dlg.result["llos"])
                db.replace_clo_llo_map(course_id, dlg.result["mapping"])
                self._load_cat_detail(course_id, vals)
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _edit_offering_instructors(self):
        offering = self._selected_catalog_offering()
        if not offering: return
        try:
            import database as db; db.init_db()
            instructors = db.get_offering_instructors(offering["offering_id"])
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self); return

        dlg = OfferingInstructorsDialog(self, offering, instructors)
        if dlg.result is not None:
            try:
                import database as db; db.init_db()
                db.replace_offering_instructors(offering["offering_id"], dlg.result)
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _edit_course_teaching_plan(self):
        sel = self.cat_tree.selection()
        if not sel:
            return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        try:
            import database as db; db.init_db()
            plan_rows = db.get_course_teaching_plan(course_id)
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT code, name_th FROM courses WHERE id=?", (course_id,)
            ).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”", f"เนเธซเธฅเธ”เนเธกเนเนเธ”เน: {e}", parent=self)
            return

        dlg = CourseTeachingPlanDialog(self, course, [dict(r) for r in plan_rows])
        if dlg.result is not None:
            try:
                import database as db; db.init_db()
                db.replace_course_teaching_plan(course_id, dlg.result)
                self._load_cat_detail(course_id, vals)
            except Exception as e:
                messagebox.showerror("เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”", f"เธเธฑเธเธ—เธถเธเนเธกเนเธชเธณเน€เธฃเนเธ: {e}", parent=self)

    def _add_course_offering(self):
        sel = self.cat_tree.selection()
        if not sel:
            return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])

        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT id, code, name_th, curriculum_id FROM courses WHERE id=?",
                (course_id,),
            ).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดข้อมูลรายวิชาไม่สำเร็จ: {e}", parent=self)
            return

        if not course:
            return

        dlg = CourseOfferingDialog(
            self,
            course,
            semester_default=self.cat_term_sem_var.get(),
            year_default=self.cat_term_year_var.get(),
        )
        if not dlg.result:
            return

        try:
            import database as db; db.init_db()
            offering_id = db.upsert_course_offering(
                course_id,
                dlg.result["semester"],
                dlg.result["year"],
                curriculum_id=course["curriculum_id"],
                section_code=dlg.result["section_code"],
                is_special=dlg.result["is_special"],
                status=dlg.result["status"],
                source_type="catalog",
            )
            self.cat_term_sem_var.set(str(dlg.result["semester"]))
            self.cat_term_year_var.set(str(dlg.result["year"]))
            self._refresh_catalog_offerings(preserve_offering_id=offering_id)
            self._refresh_courses()
            self._load_cat_detail(course_id, vals)
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"บันทึกการเปิดสอนไม่สำเร็จ: {e}", parent=self)

    def _delete_course_offering(self):
        offering = self._selected_catalog_offering()
        if not offering:
            return
        if offering.get("tqf3_id"):
            messagebox.showinfo(
                "ไม่สามารถลบได้",
                "การเปิดสอนนี้มีข้อมูล มคอ.3 แล้ว จึงยังลบไม่ได้ในขั้นตอนนี้",
                parent=self,
            )
            return
        if not messagebox.askyesno(
            "ยืนยันการลบ",
            f"ต้องการลบการเปิดสอน {offering['code']} {offering['section_code']} ใช่หรือไม่?",
            parent=self,
        ):
            return
        try:
            import database as db; db.init_db()
            with sqlite3.connect(db.DB_PATH) as conn:
                conn.execute("DELETE FROM course_offerings WHERE id=?", (offering["offering_id"],))
            self._refresh_catalog_offerings()
            self._refresh_courses()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ลบการเปิดสอนไม่สำเร็จ: {e}", parent=self)

    def _delete_course_offering_v2(self):
        offering = self._selected_catalog_offering()
        if not offering:
            return

        has_tqf3 = bool(offering.get("tqf3_id"))
        if has_tqf3:
            confirm_title = "ยืนยันการลบการเปิดสอนและ มคอ.3"
            confirm_message = (
                f"ต้องการลบการเปิดสอน {offering['code']} {offering['section_code']} ใช่หรือไม่?\n\n"
                "รายการนี้มีข้อมูล มคอ.3 แล้ว หากยืนยัน ระบบจะลบข้อมูล มคอ.3 และข้อมูลที่เกี่ยวข้องของการเปิดสอนนี้ด้วย"
            )
        else:
            confirm_title = "ยืนยันการลบการเปิดสอน"
            confirm_message = (
                f"ต้องการลบการเปิดสอน {offering['code']} {offering['section_code']} ใช่หรือไม่?"
            )

        if not messagebox.askyesno(confirm_title, confirm_message, parent=self):
            return

        try:
            import database as db; db.init_db()
            db.delete_course_offering(
                offering["offering_id"],
                delete_linked_tqf3=has_tqf3,
            )
            self._refresh_catalog_offerings()
            self._refresh_courses()
            self._clear_catalog_offering_selection()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ลบการเปิดสอนไม่สำเร็จ: {e}", parent=self)

    def _generate_selected_offering_tqf3(self):
        offering = self._selected_catalog_offering()
        if not offering:
            return

        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT o.*, c.code, c.name_th, c.curriculum_id
                FROM course_offerings o
                JOIN courses c ON c.id=o.course_id
                WHERE o.id=?
                """,
                (offering["offering_id"],),
            ).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดข้อมูลการเปิดสอนไม่สำเร็จ: {e}", parent=self)
            return

        if not row:
            messagebox.showerror("ข้อผิดพลาด", "ไม่พบข้อมูลการเปิดสอน", parent=self)
            return

        suffix = f"_{row['section_code']}" if row["section_code"] else ""
        out_path = filedialog.asksaveasfilename(
            title=f"บันทึก มคอ.3 - {row['code']}",
            defaultextension=".docx",
            initialfile=f"มคอ3_{row['code']}_{row['semester']}_{row['year']}{suffix}.docx",
            filetypes=[("Word Document", "*.docx")],
        )
        if not out_path:
            return

        def do():
            try:
                import database as db; db.init_db()
                from generate_tqf3 import generate_tqf3_docx

                tqf3_id = offering.get("tqf3_id")
                if not tqf3_id:
                    tqf3_id = db.upsert_tqf3(
                        row["course_id"],
                        row["semester"],
                        row["year"],
                        is_special=bool(row["is_special"]),
                        offering_id=row["id"],
                        section_code=row["section_code"],
                    )
                    db.copy_course_template_to_tqf3(row["course_id"], tqf3_id)

                generate_tqf3_docx(tqf3_id=tqf3_id, output_path=out_path)
                success_msg = f"สร้าง มคอ.3 สำเร็จ\n{out_path}"
                self.after(0, lambda msg=success_msg: messagebox.showinfo("สำเร็จ", msg, parent=self))
                self.after(0, self._refresh_catalog)
                self.after(0, lambda oid=row["id"]: self._refresh_catalog_offerings(preserve_offering_id=oid))
                self.after(0, self._refresh_courses)
                vals = self._focus_catalog_course(row["course_id"])
                if vals:
                    self.after(0, lambda v=vals, cid=row["course_id"]: self._load_cat_detail(cid, v))
            except Exception as e:
                error_msg = f"สร้าง มคอ.3 ไม่สำเร็จ:\n{e}"
                self.after(0, lambda msg=error_msg: messagebox.showerror("ข้อผิดพลาด", msg, parent=self))

        threading.Thread(target=do, daemon=True).start()

    def _edit_selected_offering_staff(self):
        offering = self._selected_catalog_offering()
        if not offering:
            return
        if not offering.get("tqf3_id"):
            messagebox.showinfo(
                "ยังไม่มี มคอ.3",
                "กรุณาสร้าง มคอ.3 ของการเปิดสอนนี้ก่อน แล้วจึงแก้ไขข้อมูลบุคลากร",
                parent=self,
            )
            return

        try:
            import database as db; db.init_db()
            with sqlite3.connect(db.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                course = conn.execute(
                    "SELECT code, name_th FROM courses WHERE id=?",
                    (offering["course_id"],),
                ).fetchone()
                tqf3_row = conn.execute(
                    "SELECT id, semester, year, is_special FROM tqf3 WHERE id=?",
                    (offering["tqf3_id"],),
                ).fetchone()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดข้อมูลบุคลากรไม่สำเร็จ: {e}", parent=self)
            return

        dlg = TQF3StaffDialog(self, course, [dict(tqf3_row)])
        if dlg.result is not None:
            try:
                import database as db; db.init_db()
                db.replace_tqf3_staff(dlg.result["tqf3_id"], dlg.result["staff"])
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกข้อมูลบุคลากรไม่สำเร็จ: {e}", parent=self)

    def _generate_tqf3(self):
        offering = self._selected_catalog_offering()
        if offering:
            self._generate_selected_offering_tqf3()
            return

        sel = self.cat_tree.selection()
        if not sel:
            return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])

        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT code, name_th FROM courses WHERE id=?", (course_id,)
            ).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดข้อมูลวิชาไม่ได้: {e}", parent=self)
            return

        if not course:
            messagebox.showerror("ข้อผิดพลาด", "ไม่พบข้อมูลวิชาที่เลือก", parent=self)
            return

        dlg = TQF3GenerateDialog(self, course)
        if not dlg.result:
            return

        sem = dlg.result["semester"]
        year = dlg.result["year"]
        is_special = dlg.result["is_special"]
        suffix = "_P" if is_special else ""
        out_path = filedialog.asksaveasfilename(
            title=f"บันทึก มคอ.3 — {course['code']}",
            defaultextension=".docx",
            initialfile=f"มคอ3_{course['code']}_{sem}_{year}{suffix}.docx",
            filetypes=[("Word Document", "*.docx")],
        )
        if not out_path:
            return

        def do():
            try:
                import database as db; db.init_db()
                from generate_tqf3 import generate_tqf3_docx

                conn = sqlite3.connect(db.DB_PATH)
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """
                    SELECT id FROM tqf3
                    WHERE course_id=? AND semester=? AND year=? AND is_special=?
                    """,
                    (course_id, sem, year, int(is_special)),
                ).fetchone()
                if row:
                    tqf3_id = row["id"]
                else:
                    tqf3_id = db.upsert_tqf3(
                        course_id,
                        sem,
                        year,
                        is_special=is_special,
                    )
                conn.close()

                db.copy_course_template_to_tqf3(course_id, tqf3_id)
                generate_tqf3_docx(tqf3_id=tqf3_id, output_path=out_path)
                success_msg = f"สร้าง มคอ.3 เสร็จแล้ว\n{out_path}"
                self.after(0, lambda msg=success_msg: messagebox.showinfo(
                    "สำเร็จ",
                    msg,
                    parent=self))
                self.after(0, self._refresh_catalog)
                self.after(0, self._refresh_courses)
                self.after(0, lambda: self._load_cat_detail(course_id, vals))
            except Exception as e:
                error_msg = f"สร้าง มคอ.3 ไม่สำเร็จ:\n{e}"
                self.after(0, lambda msg=error_msg: messagebox.showerror(
                    "เกิดข้อผิดพลาด",
                    msg,
                    parent=self))

        threading.Thread(target=do, daemon=True).start()

    def _edit_course_resources(self):
        sel = self.cat_tree.selection()
        if not sel:
            return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        try:
            import database as db; db.init_db()
            resources = db.get_course_resources(course_id)
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT code, name_th FROM courses WHERE id=?", (course_id,)
            ).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self)
            return
        dlg = CourseResourcesDialog(self, course, [dict(r) for r in resources])
        if dlg.result is not None:
            try:
                import database as db; db.init_db()
                db.replace_course_resources(course_id, dlg.result)
                self._load_cat_detail(course_id, vals)
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"บันทึกไม่สำเร็จ: {e}", parent=self)

    def _edit_course_staff(self):
        offering = self._selected_catalog_offering()
        if offering:
            self._edit_selected_offering_staff()
            return

        sel = self.cat_tree.selection()
        if not sel:
            return
        vals = self.cat_tree.item(sel[0], "values")
        course_id = int(vals[5])
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT code, name_th FROM courses WHERE id=?", (course_id,)
            ).fetchone()
            tqf3_records = conn.execute(
                "SELECT id, semester, year, is_special FROM tqf3 WHERE course_id=? ORDER BY year DESC, semester DESC",
                (course_id,)
            ).fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"โหลดไม่ได้: {e}", parent=self)
            return
        if not tqf3_records:
            messagebox.showinfo("แจ้งเตือน",
                f"ยังไม่มีข้อมูล มคอ.3 ของวิชา {vals[0]}\nกรุณาสร้าง มคอ.3 ก่อน",
                parent=self)
            return
        dlg = TQF3StaffDialog(self, course, [dict(r) for r in tqf3_records])
        if dlg.result is not None:
            try:
                import database as db; db.init_db()
                db.replace_tqf3_staff(dlg.result["tqf3_id"], dlg.result["staff"])
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

    def _show_curriculum_overview(self):
        """โหลดและแสดงข้อมูลหลักสูตรที่เลือกใน detail panel"""
        filt = self.cat_cur_var.get()
        if filt == "ทั้งหมด":
            messagebox.showinfo("แจ้งเตือน",
                "กรุณาเลือกหลักสูตรก่อน\nแล้วกด 📊 ข้อมูลหลักสูตร", parent=self)
            return
        ver = filt.replace("หลักสูตร ", "").strip()
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            curr = conn.execute(
                "SELECT * FROM curricula WHERE version=?", (ver,)).fetchone()
            conn.close()
        except Exception as e:
            self._set_cat_detail(f"❌ โหลดไม่ได้: {e}"); return
        if not curr:
            self._set_cat_detail("ไม่พบข้อมูลหลักสูตร"); return
        # ล้าง selection ในตาราง
        for item in self.cat_tree.selection():
            self.cat_tree.selection_remove(item)
        self.btn_cat_edit.config(state="disabled")
        self.btn_cat_del.config(state="disabled")
        self.btn_cat_gen3.config(state="disabled")
        self.btn_cat_clo.config(state="disabled")
        self.btn_cat_llo.config(state="disabled")
        self.btn_cat_plan.config(state="disabled")
        self.btn_cat_res.config(state="disabled")
        self.btn_cat_staff.config(state="disabled")
        for idx in range(self._cat_more_sel_count):
            self.cat_more_menu.entryconfigure(idx, state="disabled")
        self.btn_cat_add_offering.config(state="disabled")
        self.btn_cat_offering_gen3.config(state="disabled")
        self.btn_cat_offering_staff.config(state="disabled")
        self.btn_cat_del_offering.config(state="disabled")
        self._load_curriculum_overview(curr["id"])

    def _load_curriculum_overview(self, curriculum_id: int):
        """แสดง PLO / YLO / เกณฑ์จบ ของหลักสูตรใน detail panel"""
        try:
            import database as db; db.init_db()
            conn = sqlite3.connect(db.DB_PATH)
            conn.row_factory = sqlite3.Row
            curr = conn.execute(
                "SELECT * FROM curricula WHERE id=?", (curriculum_id,)).fetchone()
            plos = db.get_plos(curriculum_id)
            ylos = db.get_ylos(curriculum_id)
            conn.close()
        except Exception as e:
            self._set_cat_detail(f"❌ โหลดไม่ได้: {e}"); return

        if not curr:
            self._set_cat_detail("ไม่พบข้อมูลหลักสูตร"); return

        cr = dict(curr)
        self.cat_detail_title.config(
            text=f"  📊  หลักสูตรที่ {cr['version']}  —  {cr.get('name_th','')}")

        t = self.cat_detail_text
        t.configure(state="normal")
        t.delete("1.0", "end")

        # ── ข้อมูลทั่วไป ──
        t.insert("end", "ข้อมูลหลักสูตร\n", "h1")
        t.insert("end", "─" * 62 + "\n", "dim")
        t.insert("end", f"หลักสูตร  : {cr.get('version','')}\n")
        t.insert("end", f"ชื่อ      : {cr.get('name_th','') or '—'}\n")
        t.insert("end", f"ปีที่เริ่ม : {cr.get('effective_year','') or '—'}\n")

        # ── PLOs ──
        t.insert("end", f"\nผลลัพธ์การเรียนรู้ของหลักสูตร (PLOs)  —  {len(plos)} ข้อ\n", "h1")
        t.insert("end", "─" * 62 + "\n", "dim")
        if plos:
            for p in plos:
                p = dict(p)
                plo_label = f"PLO {p.get('plo_code') or p['plo_number']}"
                cat = f"  [{p['category']}]" if p.get("category") else ""
                t.insert("end", f"  {plo_label:<9}", "plo_num")
                t.insert("end", f"{p.get('description','') or '(ยังไม่มีคำอธิบาย)'}")
                if cat:
                    t.insert("end", cat, "dim")
                t.insert("end", "\n")
        else:
            t.insert("end", "  ยังไม่มีข้อมูล PLO — กด 📚 PLO เพื่อเพิ่ม\n", "warn")

        # ── YLOs ──
        t.insert("end", f"\nผลลัพธ์การเรียนรู้รายชั้นปี (YLOs)  —  {len(ylos)} ชั้นปี\n", "h1")
        t.insert("end", "─" * 62 + "\n", "dim")
        if ylos:
            for y in ylos:
                y = dict(y)
                t.insert("end", f"  ชั้นปีที่ {y['year_number']}  ", "ylo_num")
                t.insert("end", f"{y.get('title','')}\n")
                # PLO mapping
                plo_map_raw = y.get("plo_mapping") or "[]"
                try:
                    plo_map = json.loads(plo_map_raw) if isinstance(plo_map_raw, str) else plo_map_raw
                except Exception:
                    plo_map = []
                if plo_map:
                    plo_str = ", ".join(f"PLO {p}" for p in plo_map)
                    t.insert("end", f"     PLOs: {plo_str}\n", "dim")
                # Indicators (แสดงสูงสุด 3 บรรทัด)
                indicators = y.get("indicators") or ""
                if indicators:
                    lines = [ln.strip() for ln in indicators.split("\n") if ln.strip()]
                    for line in lines[:3]:
                        t.insert("end", f"     • {line}\n", "sub")
                    if len(lines) > 3:
                        t.insert("end", f"     … (+{len(lines)-3} รายการ)\n", "dim")
                # Assessment methods
                asmt = y.get("assessment_methods") or ""
                if asmt:
                    t.insert("end", f"     ประเมิน: {asmt[:80]}\n", "sub")
                t.insert("end", "\n")
        else:
            t.insert("end", "  ยังไม่มีข้อมูล YLO\n", "dim")

        # ── เกณฑ์จบการศึกษา ──
        t.insert("end", "เกณฑ์จบการศึกษา\n", "h1")
        t.insert("end", "─" * 62 + "\n", "dim")
        grad_raw = cr.get("graduation_req") or "{}"
        try:
            grad = json.loads(grad_raw) if grad_raw else {}
        except Exception:
            grad = {}
        if grad:
            if "digital_score_min_pct" in grad:
                t.insert("end",
                    f"  คะแนนดิจิทัลขั้นต่ำ  : {grad['digital_score_min_pct']}%\n")
            if "english_req" in grad:
                t.insert("end",
                    f"  ภาษาอังกฤษ          : {grad['english_req']}\n")
            if "rubric_required" in grad:
                val = "ต้องผ่าน ✅" if grad["rubric_required"] else "ไม่บังคับ"
                t.insert("end", f"  Rubric             : {val}\n")
        else:
            t.insert("end", "  ยังไม่มีข้อมูลเกณฑ์จบ\n", "dim")

        t.configure(state="disabled")

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
                success_msg = f"Export เสร็จแล้ว\n{path}"
                self.after(0, lambda msg=success_msg: messagebox.showinfo(
                    "สำเร็จ", msg))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: messagebox.showerror("ผิดพลาด", msg))
        threading.Thread(target=do, daemon=True).start()



# ══════════════════════════════════════════════════════
# DIALOG ยืนยันข้อมูลวิชาก่อน import เกรด
# ══════════════════════════════════════════════════════
class GradeInfoDialog(tk.Toplevel):
    def __init__(self, parent, filename, grade_dist, student_count,
                 auto_info=None, is_special_detected=False):
        super().__init__(parent)
        self.title("ยืนยันข้อมูลรายวิชา")
        self.minsize(400, 0)
        self.resizable(False, True)
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


class CourseOfferingDialog(tk.Toplevel):
    SECTION_CHOICES = ["N01", "P01"]
    STATUS_LABELS = {"เปิดสอน": "active", "วางแผน": "planned"}

    def __init__(self, parent, course, semester_default="1", year_default="2569",
                 existing=None):
        """existing = dict from _selected_catalog_offering() for pre-fill (edit mode)."""
        super().__init__(parent)
        is_edit = existing is not None
        self.title("แก้ไขการเปิดสอน" if is_edit else "เพิ่มการเปิดสอน")
        self.resizable(False, True)
        self.minsize(420, 100)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        code = course["code"] if course else "?"
        name = course["name_th"] if course else ""

        # ── pre-fill values from existing offering (edit mode) ──────
        if is_edit:
            sem_init     = str(existing.get("semester", semester_default))
            year_init    = str(existing.get("year",     year_default))
            section_init = str(existing.get("section_code", "N01"))
            status_raw   = existing.get("status", "active")
            # reverse-map to Thai label
            rev_status   = {v: k for k, v in self.STATUS_LABELS.items()}
            status_init  = rev_status.get(status_raw, "เปิดสอน")
        else:
            sem_init, year_init, section_init, status_init = (
                str(semester_default or "1"), str(year_default or "2569"), "N01", "เปิดสอน")

        # Buttons first (side=bottom)
        _dialog_btn_bar(self, self._confirm, self.destroy,
                        save_text="💾  บันทึก", cancel_text="ยกเลิก")

        # Header
        tk.Label(
            self, text=f"{code}  {name}", bg=BG, fg=BLUE_DARK,
            font=FONT_B, wraplength=380
        ).pack(padx=16, pady=(16, 4), anchor="w")
        tk.Label(
            self,
            text="แก้ไขข้อมูลการเปิดสอน" if is_edit else "กำหนดข้อมูลการเปิดสอนจริงของรายวิชานี้",
            bg=BG, fg=GRAY, font=FONT_SM
        ).pack(padx=16, anchor="w")

        form = tk.Frame(self, bg=BG)
        form.pack(padx=16, pady=12, fill="x")

        tk.Label(form, text="ภาคเรียน *", bg=BG, font=FONT_B).grid(row=0, column=0, sticky="w", pady=7)
        self.sem_var = tk.StringVar(value=sem_init)
        ttk.Combobox(
            form, textvariable=self.sem_var, values=["1", "2", "3"],
            width=6, state="readonly"
        ).grid(row=0, column=1, sticky="w", padx=10)

        tk.Label(form, text="ปีการศึกษา *", bg=BG, font=FONT_B).grid(row=1, column=0, sticky="w", pady=7)
        self.year_var = tk.StringVar(value=year_init)
        tk.Entry(form, textvariable=self.year_var,
                 width=10, font=FONT, relief="solid", bd=1
                 ).grid(row=1, column=1, sticky="w", padx=10)

        tk.Label(form, text="ตอนเรียน *", bg=BG, font=FONT_B).grid(row=2, column=0, sticky="w", pady=7)
        self.section_var = tk.StringVar(value=section_init)
        ttk.Combobox(
            form, textvariable=self.section_var,
            values=self.SECTION_CHOICES,
            width=8, state="readonly"
        ).grid(row=2, column=1, sticky="w", padx=10)

        tk.Label(form, text="สถานะ", bg=BG, font=FONT_B).grid(row=3, column=0, sticky="w", pady=7)
        self.status_var = tk.StringVar(value=status_init)
        ttk.Combobox(
            form, textvariable=self.status_var,
            values=list(self.STATUS_LABELS.keys()),
            width=10, state="readonly"
        ).grid(row=3, column=1, sticky="w", padx=10)

        tk.Label(
            form,
            text="รองรับ 1 ตอนปกติ (N01) และ 1 ตอนพิเศษ (P01) ต่อภาคเรียน",
            bg=BG, fg=GRAY, font=FONT_SM, wraplength=360, justify="left"
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 4))

        self.wait_window()

    def _confirm(self):
        try:
            semester = int(self.sem_var.get())
            year = int(self.year_var.get())
        except ValueError:
            messagebox.showwarning("ข้อมูลไม่ถูกต้อง", "ภาคเรียนและปีการศึกษาต้องเป็นตัวเลข", parent=self)
            return

        section_code = self.section_var.get().strip().upper()
        if section_code not in self.SECTION_CHOICES:
            messagebox.showwarning("ข้อมูลไม่ถูกต้อง", "กรุณาเลือกตอนเรียนที่รองรับ", parent=self)
            return

        self.result = {
            "semester": semester,
            "year": year,
            "section_code": section_code,
            "is_special": section_code.startswith("P"),
            "status": self.STATUS_LABELS.get(self.status_var.get(), "active"),
        }
        self.destroy()


class TQF3GenerateDialog(tk.Toplevel):
    def __init__(self, parent, course):
        super().__init__(parent)
        self.title("สร้าง มคอ.3")
        self.minsize(420, 0)
        self.resizable(False, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        code = course["code"] if course else "?"
        name = course["name_th"] if course else ""

        tk.Label(self, text=f"{code}  {name}", bg=BG, fg=BLUE_DARK,
                 font=FONT_B, wraplength=380).pack(padx=16, pady=(16, 6), anchor="w")
        tk.Label(self, text="ระบุข้อมูลการเปิดสอนก่อนสร้างไฟล์ มคอ.3",
                 bg=BG, fg=GRAY, font=FONT_SM).pack(padx=16, anchor="w")

        form = tk.Frame(self, bg=BG)
        form.pack(padx=16, pady=14, fill="x")

        tk.Label(form, text="ภาคเรียนที่ *", bg=BG, font=FONT_B).grid(row=0, column=0, sticky="w", pady=7)
        self.sem_var = tk.StringVar(value="1")
        ttk.Combobox(
            form, textvariable=self.sem_var, values=["1", "2", "3"],
            width=6, state="readonly"
        ).grid(row=0, column=1, sticky="w", padx=10)

        tk.Label(form, text="ปีการศึกษา *", bg=BG, font=FONT_B).grid(row=1, column=0, sticky="w", pady=7)
        self.year_var = tk.StringVar(value="2569")
        tk.Entry(form, textvariable=self.year_var, width=12, font=("Arial", 11)).grid(
            row=1, column=1, sticky="w", padx=10
        )

        tk.Label(form, text="ประเภทเปิด", bg=BG, font=FONT_B).grid(row=2, column=0, sticky="w", pady=7)
        sec_frame = tk.Frame(form, bg=BG)
        sec_frame.grid(row=2, column=1, sticky="w", padx=10)
        self.special_var = tk.BooleanVar(value=False)
        tk.Radiobutton(sec_frame, text="ปกติ (N0x)", variable=self.special_var,
                       value=False, bg=BG, font=FONT_SM,
                       activebackground=BG).pack(side="left", padx=(0, 10))
        tk.Radiobutton(sec_frame, text="พิเศษ (P0x)", variable=self.special_var,
                       value=True, bg=BG, font=FONT_SM,
                       activebackground=BG).pack(side="left")

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text="สร้าง", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=20, pady=6, command=self._confirm).pack(side="left", padx=6)
        tk.Button(btn_frame, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=6, command=self.destroy).pack(side="left", padx=6)
        self.wait_window()

    def _confirm(self):
        try:
            semester = int(self.sem_var.get())
            year = int(self.year_var.get())
        except ValueError:
            messagebox.showwarning("ข้อมูลไม่ถูกต้อง", "ภาคเรียนและปีการศึกษาต้องเป็นตัวเลข", parent=self)
            return
        self.result = {
            "semester": semester,
            "year": year,
            "is_special": bool(self.special_var.get()),
        }
        self.destroy()


# ══════════════════════════════════════════════════════
# DIALOG เพิ่ม/แก้ไขวิชาใหม่
# ══════════════════════════════════════════════════════
class CourseAddDialog(tk.Toplevel):
    CREDIT_EXAMPLES = ["3(3-0-6)", "3(2-2-5)", "3(0-6-3)", "2(1-2-3)", "1(0-2-1)"]
    PREREQUISITE_EXAMPLES = ["ไม่มี", "ตามแผนหลักสูตร", "SMA1001", "SMA1002 และ SMA1003"]
    """Dialog สำหรับเพิ่มวิชาใหม่ หรือแก้ไขข้อมูลพื้นฐานวิชา"""
    TYPES = ["วิชาแกน (Core)", "วิชาบังคับ (Required)",
             "วิชาเลือก (Elective)", "วิชาปฏิบัติการ (Practicum)",
             "วิชาเลือกเสรี (Free Elective)", "สหกิจศึกษา", "อื่นๆ"]

    def __init__(self, parent, curricula, existing=None):
        super().__init__(parent)
        is_edit = existing is not None
        self.title("แก้ไขข้อมูลวิชา" if is_edit else "เพิ่มวิชาใหม่")
        self.minsize(520, 400)
        self.resizable(False, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        ex = dict(existing) if existing else {}
        self._cur_map = {f"หลักสูตร {r['version']}  ({r['name_th']})": r["id"]
                         for r in curricula}

        # Header (fixed — ไม่ scroll)
        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x", side="top")
        title_text = (f"✏️  {ex.get('code','')}  {ex.get('name_th','')}"
                      if is_edit else "＋  เพิ่มวิชาใหม่")
        tk.Label(hdr, text=title_text, bg=BLUE_DARK, fg=WHITE,
                 font=FONT_B, wraplength=480, anchor="w").pack(padx=14, pady=10)

        # Buttons (pack side=bottom ก่อน — ปุ่มไม่หายเด็ดขาด)
        _dialog_btn_bar(self, self._save, self.destroy)

        # Scrollable form body
        body = _ScrollableBody(self)
        body.pack(fill="both", expand=True)
        frm = body.inner
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
        ttk.Combobox(
            cr_frame,
            textvariable=self.credits_var,
            values=self.CREDIT_EXAMPLES,
            width=12,
            state="normal",
        ).pack(side="left")
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
        ttk.Combobox(frm, textvariable=self.prereq_var,
                     values=self.PREREQUISITE_EXAMPLES,
                     width=30, state="normal").grid(row=6, column=1, sticky="w")

        # คำอธิบาย
        row_label(7, "คำอธิบาย")
        self.desc_text = tk.Text(frm, width=36, height=3,
                                  font=("Arial", 9), wrap="word")
        self.desc_text.insert("1.0", ex.get("description_th", ""))
        self.desc_text.grid(row=7, column=1, sticky="w", pady=(4, 12))
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
        self.minsize(700, 0)
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
        _, plo_buttons = _build_wrapped_action_bar(
            self,
            buttons=[
                {"text": "＋ เพิ่ม PLO", "bg": GREEN, "command": self._add_row},
                {"key": "delete", "text": "🗑 ลบ", "bg": RED, "state": "disabled", "command": self._del_row},
            ],
            columns=2,
            pack_kwargs={"padx": 12, "pady": (8, 4)},
        )
        self.btn_del_plo = plo_buttons["delete"]

        # Treeview
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)
        tcols = ("num", "code", "cat", "desc")
        self.plo_tree = ttk.Treeview(
            tree_frame, columns=tcols, show="headings",
            selectmode="browse", height=12)
        self.plo_tree.heading("num",  text="PLO#")
        self.plo_tree.heading("code", text="Code")
        self.plo_tree.heading("cat",  text="ด้าน")
        self.plo_tree.heading("desc", text="คำอธิบาย")
        self.plo_tree.column("num",  width=50,  anchor="center", minwidth=40)
        self.plo_tree.column("code", width=70,  anchor="center")
        self.plo_tree.column("cat",  width=180, anchor="w")
        self.plo_tree.column("desc", width=330, anchor="w")
        self.plo_tree.bind("<<TreeviewSelect>>",
                           lambda e: self.btn_del_plo.config(
                               state="normal" if self.plo_tree.selection() else "disabled"))
        self.plo_tree.bind("<Double-1>", self._edit_row)
        self.plo_tree.bind("<Return>",   self._edit_row)
        self.plo_tree.bind("<Delete>",   lambda e: self._del_row())
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
                r["plo_number"],
                r.get("plo_code", "") or str(r["plo_number"]),
                r.get("category",""),
                r.get("description",""),
            ))

    def _add_row(self):
        next_num = max((r["plo_number"] for r in self._rows), default=0) + 1
        dlg = PLOEditRowDialog(self, next_num, str(next_num), "", "", self.PLO_CATS)
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
                               r.get("plo_code", "") or str(r["plo_number"]),
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
    def __init__(self, parent, plo_number, plo_code, category, description, cats):
        super().__init__(parent)
        self.title(f"PLO {plo_number}")
        self.minsize(460, 0)
        self.resizable(False, True)
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

        tk.Label(frm, text="Code:", bg=BG, font=FONT_B).grid(
            row=1, column=0, sticky="e", pady=6, padx=(0,10))
        self.code_var = tk.StringVar(value=plo_code or str(plo_number))
        tk.Entry(frm, textvariable=self.code_var, width=12,
                 font=("Arial",10)).grid(row=1, column=1, sticky="w")

        tk.Label(frm, text="ด้าน:", bg=BG, font=FONT_B).grid(
            row=2, column=0, sticky="e", pady=6, padx=(0,10))
        self.cat_var = tk.StringVar(value=category)
        ttk.Combobox(frm, textvariable=self.cat_var,
                     values=cats, width=32, state="normal").grid(
            row=2, column=1, sticky="w")

        tk.Label(frm, text="คำอธิบาย:", bg=BG, font=FONT_B).grid(
            row=3, column=0, sticky="ne", pady=6, padx=(0,10))
        self.desc_text = tk.Text(frm, width=34, height=3,
                                  font=("Arial",9), wrap="word")
        self.desc_text.insert("1.0", description)
        self.desc_text.grid(row=3, column=1, sticky="w")

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
            "plo_code": self.code_var.get().strip() or str(num),
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
        course = dict(course) if course else {}
        code = course["code"] if course else "?"
        self.title(f"แก้ไข CLO & การประเมิน — {code}")
        self.minsize(780, 0)
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
        _, clo_buttons = _build_wrapped_action_bar(
            self.tab_clo,
            buttons=[
                {"text": "＋ เพิ่ม CLO", "bg": GREEN, "command": self._add_clo},
                {"key": "delete", "text": "🗑 ลบ", "bg": RED, "state": "disabled", "command": self._del_clo},
            ],
            columns=2,
            pack_kwargs={"padx": 8, "pady": (8, 2)},
        )
        self.btn_del_clo = clo_buttons["delete"]
        tk.Label(self.tab_clo, text="(ดับเบิลคลิกเพื่อแก้ไข)",
                 bg=BG, fg=GRAY, font=("Arial",8,"italic")).pack(anchor="w", padx=12, pady=(0, 4))

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
        self.clo_tree.bind("<Return>",   self._edit_clo)
        self.clo_tree.bind("<Delete>",   lambda e: self._del_clo())
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
        _, asmt_buttons = _build_wrapped_action_bar(
            self.tab_asmt,
            buttons=[
                {"text": "＋ เพิ่มรายการ", "bg": GREEN, "command": self._add_asmt},
                {"key": "delete", "text": "🗑 ลบ", "bg": RED, "state": "disabled", "command": self._del_asmt},
            ],
            columns=2,
            pack_kwargs={"padx": 8, "pady": (8, 2)},
        )
        self.btn_del_asmt = asmt_buttons["delete"]
        self.asmt_total_var = tk.StringVar(value="")
        tk.Label(self.tab_asmt, textvariable=self.asmt_total_var,
                 bg=BG, fg=GRAY, font=FONT_SM).pack(anchor="w", padx=12, pady=(0, 4))

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
        self.asmt_tree.bind("<Return>",   self._edit_asmt)
        self.asmt_tree.bind("<Delete>",   lambda e: self._del_asmt())
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
    TEACHING_STRATEGY_EXAMPLES = [
        "บรรยาย",
        "บรรยายและอภิปราย",
        "อภิปรายกลุ่ม",
        "problem-based learning",
        "project-based learning",
        "ปฏิบัติการ",
        "กรณีศึกษา",
        "flipped classroom",
    ]
    ASSESSMENT_METHOD_EXAMPLES = [
        "แบบฝึกหัด",
        "งานเดี่ยว",
        "งานกลุ่ม",
        "สอบย่อย",
        "สอบกลางภาค",
        "สอบปลายภาค",
        "นำเสนอ",
        "โครงงาน",
        "รายงาน",
    ]
    def __init__(self, parent, clo, plos, domains):
        super().__init__(parent)
        self.title(f"CLO {clo.get('clo_number','')}")
        self.minsize(580, 420)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._plos = plos

        frm = tk.Frame(self, bg=BG)
        frm.pack(fill="both", expand=True, padx=16, pady=12)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(6, weight=1)

        def lbl(r, t):
            tk.Label(frm, text=t, bg=BG, font=FONT_B, anchor="e").grid(
                row=r, column=0, sticky="e", pady=5, padx=(0,8))

        lbl(0, "CLO#:")
        self.num_var = tk.StringVar(value=str(clo.get("clo_number",1)))
        tk.Entry(frm, textvariable=self.num_var, width=6,
                 font=("Arial",10)).grid(row=0, column=1, sticky="w")

        lbl(1, "คำอธิบาย:")
        self.desc = tk.Text(frm, width=48, height=4, font=("Arial",9), wrap="word")
        self.desc.insert("1.0", clo.get("description",""))
        self.desc.grid(row=1, column=1, sticky="ew", pady=4)

        lbl(2, "ด้าน:")
        self.dom_var = tk.StringVar(value=clo.get("domain",""))
        ttk.Combobox(frm, textvariable=self.dom_var,
                     values=domains, width=42, state="normal").grid(
            row=2, column=1, sticky="ew")

        lbl(3, "วิธีสอน:")
        self.strat_var = tk.StringVar(value=clo.get("teaching_strategy",""))
        ttk.Combobox(frm, textvariable=self.strat_var,
                     values=self.TEACHING_STRATEGY_EXAMPLES,
                     width=46, state="normal").grid(row=3, column=1, sticky="ew")

        lbl(4, "วิธีวัด:")
        self.asmth_var = tk.StringVar(value=clo.get("assessment_method",""))
        ttk.Combobox(frm, textvariable=self.asmth_var,
                     values=self.ASSESSMENT_METHOD_EXAMPLES,
                     width=46, state="normal").grid(row=4, column=1, sticky="ew")

        lbl(5, "เกณฑ์ผ่าน %:")
        self.pass_var = tk.StringVar(value=str(clo.get("pass_threshold_pct",50)))
        tk.Entry(frm, textvariable=self.pass_var, width=8,
                 font=("Arial",10)).grid(row=5, column=1, sticky="w")

        lbl(6, "PLO ที่ตอบสนอง:")
        plo_frame = tk.LabelFrame(
            frm,
            text="เลือก PLO ที่สอดคล้อง",
            bg=BG,
            fg=BLUE_DARK,
            font=FONT_SM,
            padx=8,
            pady=6,
        )
        plo_frame.grid(row=6, column=1, sticky="nsew", pady=4)
        cur_mapping = clo.get("plo_mapping", [])
        if isinstance(cur_mapping, str):
            cur_mapping = json.loads(cur_mapping)
        self._plo_vars = _build_wrapped_checklist(
            plo_frame,
            items=plos,
            selected_values=cur_mapping,
            text_fn=lambda p: f"PLO {p.get('plo_code') or p['plo_number']}",
            value_fn=lambda p: p["plo_number"],
            empty_text="(ยังไม่มี PLO — กด 📚 PLO ก่อน)",
            columns=4,
            height=110,
        )

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
    NAME_EXAMPLES = [
        "Quiz",
        "Assignment",
        "Report",
        "Presentation",
        "Midterm exam",
        "Final exam",
        "Project",
        "Lab",
    ]
    PERIOD_EXAMPLES = [
        "Week 1-4",
        "Before midterm",
        "Week 8",
        "Midterm",
        "After midterm",
        "Final",
        "Whole semester",
    ]
    def __init__(self, parent, asmt, clos):
        super().__init__(parent)
        self.title("รายการประเมิน")
        self.minsize(520, 380)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._asmt = dict(asmt)

        frm = tk.Frame(self, bg=BG)
        frm.pack(fill="both", expand=True, padx=16, pady=12)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(5, weight=1)

        def lbl(r, t):
            tk.Label(frm, text=t, bg=BG, font=FONT_B, anchor="e").grid(
                row=r, column=0, sticky="e", pady=5, padx=(0,8))

        lbl(0, "ชื่อรายการ:")
        self.name_var = tk.StringVar(value=asmt.get("name",""))
        ttk.Combobox(frm, textvariable=self.name_var,
                     values=self.NAME_EXAMPLES,
                     width=30, state="normal").grid(row=0, column=1, sticky="w")

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
        tk.Label(frm, text="Assessment period:", bg=BG, font=FONT_B, anchor="e").grid(
            row=4, column=0, sticky="e", pady=5, padx=(0,8))
        self.period_var = tk.StringVar(value=asmt.get("assessment_period", ""))
        ttk.Combobox(frm, textvariable=self.period_var,
                     values=self.PERIOD_EXAMPLES,
                     width=30, state="normal").grid(row=4, column=1, sticky="w")

        tk.Label(frm, text="CLOs:", bg=BG, font=FONT_B, anchor="e").grid(
            row=5, column=0, sticky="e", pady=5, padx=(0,8))
        clo_frame = tk.LabelFrame(
            frm,
            text="เลือก CLO ที่ถูกวัด",
            bg=BG,
            fg=BLUE_DARK,
            font=FONT_SM,
            padx=8,
            pady=6,
        )
        clo_frame.grid(row=5, column=1, sticky="nsew", pady=4)
        cur_mapping = asmt.get("clo_mapping", [])
        if isinstance(cur_mapping, str):
            cur_mapping = json.loads(cur_mapping)
        self._clo_vars = _build_wrapped_checklist(
            clo_frame,
            items=clos,
            selected_values=cur_mapping,
            text_fn=lambda c: f"CLO {c['clo_number']}",
            value_fn=lambda c: c["clo_number"],
            empty_text="(ยังไม่มี CLO)",
            columns=5,
            height=90,
        )

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
        self.result = dict(self._asmt)
        self.result.update({
            "name": name,
            "full_score": full,
            "weight_pct": wt,
            "pass_threshold": pt,
            "assessment_period": self.period_var.get().strip() if getattr(self, "period_var", None) else self._asmt.get("assessment_period", ""),
            "clo_mapping": [n for n, v in self._clo_vars.items() if v.get()],
        })
        self.result.setdefault("assessment_period", "")
        self.result.setdefault("eval_criteria", "")
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
        self.minsize(440, 0)
        self.resizable(False, True)
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

        # ── bottom buttons ──
        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=16)
        tk.Button(btn_row, text="บันทึก", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self._save).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self.destroy).pack(side="right")

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
class CourseTeachingPlanDialog(tk.Toplevel):
    """Edit course_teaching_plan rows for a course."""

    def __init__(self, parent, course, plan_rows: list):
        super().__init__(parent)
        self.title(f"แผนการสอน — {course['code']} {course['name_th'] or ''}")
        self.resizable(True, True)
        self.minsize(860, 0)
        self.grab_set()
        self.result = None
        self._rows = [dict(r) for r in plan_rows]

        tb = tk.Frame(self, bg=BG, pady=6)
        tb.pack(fill="x", padx=10)
        tk.Button(tb, text="+ เพิ่มแถว", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._add_row).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="แก้ไข", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._edit_row).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="ลบ", bg=RED, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._del_row).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="โ‘", font=FONT_B, relief="flat", padx=8, pady=3,
                  command=self._move_up).pack(side="left", padx=(0, 2))
        tk.Button(tb, text="โ“", font=FONT_B, relief="flat", padx=8, pady=3,
                  command=self._move_down).pack(side="left")

        _build_wrapped_action_bar(
            self,
            buttons=[
                {"text": "+ เพิ่มแถว", "bg": GREEN, "command": self._add_row},
                {"text": "แก้ไข", "bg": BLUE, "command": self._edit_row},
                {"text": "ลบ", "bg": RED, "command": self._del_row},
                {"text": "↑", "bg": WHITE, "fg": FG, "command": self._move_up},
                {"text": "↓", "bg": WHITE, "fg": FG, "command": self._move_down},
            ],
            columns=3,
            pack_kwargs={"padx": 10, "pady": (6, 2)},
        )
        tb.destroy()

        cols = ("no", "week", "llo", "topic", "hours")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                 selectmode="browse", height=15)
        self.tree.heading("no", text="#")
        self.tree.heading("week", text="สัปดาห์")
        self.tree.heading("llo", text="LLO")
        self.tree.heading("topic", text="หัวข้อ")
        self.tree.heading("hours", text="ชม.")
        self.tree.column("no", width=36, anchor="center", stretch=False)
        self.tree.column("week", width=90, anchor="center", stretch=False)
        self.tree.column("llo", width=220, anchor="w")
        self.tree.column("topic", width=360, anchor="w")
        self.tree.column("hours", width=60, anchor="center", stretch=False)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 4))
        vsb.pack(side="left", fill="y", pady=(0, 4))
        self.tree.bind("<Double-1>", lambda e: self._edit_row())
        self.tree.bind("<Return>",   lambda e: self._edit_row())
        self.tree.bind("<Delete>",   lambda e: self._del_row())

        hint = tk.Label(
            self,
            text="แก้ได้ทั้ง week_label, LLO, หัวข้อ, กิจกรรม, วิธีสอน, สื่อ, วิธีประเมิน และจำนวนชั่วโมง",
            bg=BG,
            fg=GRAY,
            font=FONT_SM,
            anchor="w",
        )
        hint.pack(fill="x", padx=12, pady=(0, 4))

        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=10)
        tk.Button(btn_row, text="บันทึก", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self._save).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self.destroy).pack(side="right")

        self._refresh_tree()
        self.wait_window()

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, row in enumerate(self._rows, 1):
            label = row.get("week_label") or row.get("week") or "-"
            llo = (row.get("llo_text") or "").replace("\n", " ").strip()
            topic = (row.get("topic") or "").replace("\n", " ").strip()
            hours = row.get("hours_planned", 0) or 0
            self.tree.insert("", "end", iid=str(i - 1), values=(
                i,
                label,
                llo[:48] if llo else "-",
                topic[:72] if topic else "-",
                f"{float(hours):.0f}",
            ))

    def _selected_idx(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add_row(self):
        dlg = _TeachingPlanRowDialog(self)
        if dlg.result:
            self._rows.append(dlg.result)
            self._refresh_tree()

    def _edit_row(self):
        idx = self._selected_idx()
        if idx is None:
            return
        dlg = _TeachingPlanRowDialog(self, self._rows[idx])
        if dlg.result:
            self._rows[idx] = dlg.result
            self._refresh_tree()
            self.tree.selection_set(str(idx))

    def _del_row(self):
        idx = self._selected_idx()
        if idx is None:
            return
        self._rows.pop(idx)
        self._refresh_tree()

    def _move_up(self):
        idx = self._selected_idx()
        if idx is None or idx == 0:
            return
        self._rows[idx - 1], self._rows[idx] = self._rows[idx], self._rows[idx - 1]
        self._refresh_tree()
        self.tree.selection_set(str(idx - 1))

    def _move_down(self):
        idx = self._selected_idx()
        if idx is None or idx >= len(self._rows) - 1:
            return
        self._rows[idx], self._rows[idx + 1] = self._rows[idx + 1], self._rows[idx]
        self._refresh_tree()
        self.tree.selection_set(str(idx + 1))

    def _save(self):
        normalized = []
        for idx, row in enumerate(self._rows):
            item = dict(row)
            item["seq"] = idx
            planned = item.get("hours_planned", 0) or 0
            if not planned:
                planned = (item.get("hours_theory", 0) or 0) + (item.get("hours_practice", 0) or 0)
            item["hours_planned"] = planned
            normalized.append(item)
        self.result = normalized
        self.destroy()


class _TeachingPlanRowDialog(tk.Toplevel):
    WEEK_LABEL_EXAMPLES = [
        "1", "2", "3", "4", "5", "6", "7", "8",
        "9", "10", "11", "12", "13", "14", "15",
        "16", "1-2", "3-4", "Midterm", "Final", "Review",
    ]
    """Sub-dialog: add or edit a single teaching plan row."""

    def __init__(self, parent, row: dict = None):
        super().__init__(parent)
        self.title("แก้ไขแผนการสอน" if row else "เพิ่มแผนการสอน")
        self.resizable(True, True)
        self.minsize(680, 560)
        self.grab_set()
        self.result = None
        row = row or {}

        self.week_var = tk.StringVar(value=str(row.get("week", "") or ""))
        self.week_label_var = tk.StringVar(value=row.get("week_label", "") or "")
        self.hours_planned_var = tk.StringVar(value=str(row.get("hours_planned", "") or ""))
        self.hours_theory_var = tk.StringVar(value=str(row.get("hours_theory", "") or ""))
        self.hours_practice_var = tk.StringVar(value=str(row.get("hours_practice", "") or ""))
        self.hours_self_var = tk.StringVar(value=str(row.get("hours_self", "") or ""))

        frm = tk.Frame(self, bg=BG, padx=16, pady=12)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="สัปดาห์:", bg=BG, fg=FG, font=FONT_B).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(frm, textvariable=self.week_var, width=8, font=FONT).grid(row=0, column=1, sticky="w", pady=4)
        tk.Label(frm, text="ป้ายแสดงผล:", bg=BG, fg=FG, font=FONT_B).grid(row=0, column=2, sticky="w", padx=(12, 0), pady=4)
        ttk.Combobox(frm, textvariable=self.week_label_var,
                     values=self.WEEK_LABEL_EXAMPLES,
                     width=14, state="normal").grid(row=0, column=3, sticky="w", pady=4)

        tk.Label(frm, text="ชั่วโมงรวม:", bg=BG, fg=FG, font=FONT_B).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(frm, textvariable=self.hours_planned_var, width=8, font=FONT).grid(row=1, column=1, sticky="w", pady=4)
        tk.Label(frm, text="ทฤษฎี:", bg=BG, fg=FG, font=FONT_B).grid(row=1, column=2, sticky="w", padx=(12, 0), pady=4)
        tk.Entry(frm, textvariable=self.hours_theory_var, width=8, font=FONT).grid(row=1, column=3, sticky="w", pady=4)
        tk.Label(frm, text="ปฏิบัติ:", bg=BG, fg=FG, font=FONT_B).grid(row=1, column=4, sticky="w", padx=(12, 0), pady=4)
        tk.Entry(frm, textvariable=self.hours_practice_var, width=8, font=FONT).grid(row=1, column=5, sticky="w", pady=4)
        tk.Label(frm, text="ศึกษาด้วยตนเอง:", bg=BG, fg=FG, font=FONT_B).grid(row=1, column=6, sticky="w", padx=(12, 0), pady=4)
        tk.Entry(frm, textvariable=self.hours_self_var, width=8, font=FONT).grid(row=1, column=7, sticky="w", pady=4)

        def add_text_field(row_no, label, value):
            tk.Label(frm, text=label, bg=BG, fg=FG, font=FONT_B,
                     anchor="w").grid(row=row_no, column=0, sticky="nw", pady=4)
            widget = tk.Text(frm, width=74, height=3, font=FONT, wrap="word")
            widget.grid(row=row_no, column=1, columnspan=7, sticky="nsew", pady=4)
            if value:
                widget.insert("1.0", value)
            return widget

        self.llo_text = add_text_field(2, "LLO:", row.get("llo_text", "") or "")
        self.topic_text = add_text_field(3, "หัวข้อ:", row.get("topic", "") or "")
        self.activities_text = add_text_field(4, "กิจกรรม:", row.get("activities", "") or "")
        self.method_text = add_text_field(5, "วิธีสอน:", row.get("teaching_method", "") or "")
        self.media_text = add_text_field(6, "สื่อ/เครื่องมือ:", row.get("media", "") or "")
        self.assessment_text = add_text_field(7, "การประเมิน/หลักฐาน:", row.get("assessment_tools", "") or "")

        for idx in range(1, 8):
            frm.grid_columnconfigure(idx, weight=1)
        for row_no in range(2, 8):
            frm.grid_rowconfigure(row_no, weight=1)

        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=16)
        tk.Button(btn_row, text="ตกลง", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=4,
                  command=self._ok).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=4,
                  command=self.destroy).pack(side="right")
        self.wait_window()

    @staticmethod
    def _read_text(widget):
        return widget.get("1.0", "end").strip()

    @staticmethod
    def _to_float(raw):
        text = str(raw).strip()
        if not text:
            return 0.0
        return float(text)

    def _ok(self):
        try:
            week_text = self.week_var.get().strip()
            week = int(week_text) if week_text else 0
            hours_planned = self._to_float(self.hours_planned_var.get())
            hours_theory = self._to_float(self.hours_theory_var.get())
            hours_practice = self._to_float(self.hours_practice_var.get())
            hours_self = self._to_float(self.hours_self_var.get())
        except ValueError:
            messagebox.showwarning(
                "ข้อมูลไม่ถูกต้อง",
                "สัปดาห์และชั่วโมงต้องเป็นตัวเลข",
                parent=self,
            )
            return

        topic = self._read_text(self.topic_text)
        if not topic:
            messagebox.showwarning(
                "ข้อมูลไม่ครบ",
                "กรุณากรอกหัวข้อการสอน",
                parent=self,
            )
            return

        week_label = self.week_label_var.get().strip() or (str(week) if week else "")
        if not hours_planned:
            hours_planned = hours_theory + hours_practice

        self.result = {
            "week": week,
            "week_label": week_label,
            "llo_text": self._read_text(self.llo_text),
            "topic": topic,
            "activities": self._read_text(self.activities_text),
            "teaching_method": self._read_text(self.method_text),
            "media": self._read_text(self.media_text),
            "assessment_tools": self._read_text(self.assessment_text),
            "hours_planned": hours_planned,
            "hours_theory": hours_theory,
            "hours_practice": hours_practice,
            "hours_self": hours_self,
        }
        self.destroy()


class CourseResourcesDialog(tk.Toplevel):
    """Edit course_resources (section 8: textbooks, articles, websites, media)."""

    TYPES = ["textbook", "article", "website", "media", "other"]

    def __init__(self, parent, course, resources: list):
        super().__init__(parent)
        self.title(f"ทรัพยากรการสอน — {course['code']} {course['name_th'] or ''}")
        self.resizable(True, True)
        self.minsize(720, 0)
        self.grab_set()
        self.result = None
        self._rows = [dict(r) for r in resources]

        tb = tk.Frame(self, bg=BG, pady=6)
        tb.pack(fill="x", padx=10)
        tk.Button(tb, text="+ เพิ่มรายการ", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._add_row).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="แก้ไข", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._edit_row).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="ลบ", bg=RED, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._del_row).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="↑", font=FONT_B, relief="flat", padx=8, pady=3,
                  command=self._move_up).pack(side="left", padx=(0, 2))
        tk.Button(tb, text="↓", font=FONT_B, relief="flat", padx=8, pady=3,
                  command=self._move_down).pack(side="left")

        _build_wrapped_action_bar(
            self,
            buttons=[
                {"text": "+ เพิ่มรายการ", "bg": GREEN, "command": self._add_row},
                {"text": "แก้ไข", "bg": BLUE, "command": self._edit_row},
                {"text": "ลบ", "bg": RED, "command": self._del_row},
                {"text": "↑", "bg": WHITE, "fg": FG, "command": self._move_up},
                {"text": "↓", "bg": WHITE, "fg": FG, "command": self._move_down},
            ],
            columns=3,
            pack_kwargs={"padx": 10, "pady": (6, 2)},
        )
        tb.destroy()

        cols = ("no", "type", "citation", "url")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                 selectmode="browse", height=14)
        self.tree.heading("no",       text="#")
        self.tree.heading("type",     text="ประเภท")
        self.tree.heading("citation", text="รายการอ้างอิง / ชื่อ")
        self.tree.heading("url",      text="URL")
        self.tree.column("no",       width=30,  anchor="center", stretch=False)
        self.tree.column("type",     width=80,  anchor="center", stretch=False)
        self.tree.column("citation", width=360, anchor="w")
        self.tree.column("url",      width=200, anchor="w")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 4))
        vsb.pack(side="left", fill="y", pady=(0, 4))
        self.tree.bind("<Double-1>", lambda e: self._edit_row())
        self.tree.bind("<Return>",   lambda e: self._edit_row())
        self.tree.bind("<Delete>",   lambda e: self._del_row())

        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=10)
        tk.Button(btn_row, text="บันทึก", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self._save).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self.destroy).pack(side="right")

        self._refresh_tree()
        self.wait_window()

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, r in enumerate(self._rows, 1):
            self.tree.insert("", "end", iid=str(i - 1), values=(
                i,
                r.get("resource_type", "other"),
                r.get("citation_text", "")[:80],
                r.get("url", "") or "",
            ))

    def _selected_idx(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add_row(self):
        dlg = _ResourceRowDialog(self)
        if dlg.result:
            self._rows.append(dlg.result)
            self._refresh_tree()

    def _edit_row(self):
        idx = self._selected_idx()
        if idx is None:
            return
        dlg = _ResourceRowDialog(self, self._rows[idx])
        if dlg.result:
            self._rows[idx] = dlg.result
            self._refresh_tree()
            self.tree.selection_set(str(idx))

    def _del_row(self):
        idx = self._selected_idx()
        if idx is None:
            return
        self._rows.pop(idx)
        self._refresh_tree()

    def _move_up(self):
        idx = self._selected_idx()
        if idx is None or idx == 0:
            return
        self._rows[idx - 1], self._rows[idx] = self._rows[idx], self._rows[idx - 1]
        self._refresh_tree()
        self.tree.selection_set(str(idx - 1))

    def _move_down(self):
        idx = self._selected_idx()
        if idx is None or idx >= len(self._rows) - 1:
            return
        self._rows[idx], self._rows[idx + 1] = self._rows[idx + 1], self._rows[idx]
        self._refresh_tree()
        self.tree.selection_set(str(idx + 1))

    def _save(self):
        self.result = self._rows
        self.destroy()


class _ResourceRowDialog(tk.Toplevel):
    """Sub-dialog: add or edit a single resource row."""
    TYPES = ["textbook", "article", "website", "media", "other"]

    def __init__(self, parent, row: dict = None):
        super().__init__(parent)
        self.title("แก้ไขทรัพยากร" if row else "เพิ่มทรัพยากร")
        self.resizable(False, True)
        self.minsize(560, 0)
        self.grab_set()
        self.result = None
        row = row or {}

        frm = tk.Frame(self, bg=BG, padx=16, pady=12)
        frm.pack(fill="both", expand=True)

        def lbl(text, r):
            tk.Label(frm, text=text, bg=BG, fg=FG, font=FONT_B,
                     anchor="w").grid(row=r, column=0, sticky="w", pady=3)

        lbl("ประเภท:", 0)
        self.type_var = tk.StringVar(value=row.get("resource_type", "textbook"))
        ttk.Combobox(frm, textvariable=self.type_var,
                     values=self.TYPES, state="readonly", width=16
                     ).grid(row=0, column=1, sticky="w", pady=3)

        lbl("รายการอ้างอิง / ชื่อ:", 1)
        self.cite_var = tk.StringVar(value=row.get("citation_text", ""))
        tk.Entry(frm, textvariable=self.cite_var, width=52,
                 font=FONT).grid(row=1, column=1, sticky="ew", pady=3)

        lbl("URL:", 2)
        self.url_var = tk.StringVar(value=row.get("url", "") or "")
        tk.Entry(frm, textvariable=self.url_var, width=52,
                 font=FONT).grid(row=2, column=1, sticky="ew", pady=3)

        lbl("หมายเหตุ:", 3)
        self.note_var = tk.StringVar(value=row.get("note", "") or "")
        tk.Entry(frm, textvariable=self.note_var, width=52,
                 font=FONT).grid(row=3, column=1, sticky="ew", pady=3)

        frm.columnconfigure(1, weight=1)
        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=16)
        tk.Button(btn_row, text="ตกลง", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=4,
                  command=self._ok).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=4,
                  command=self.destroy).pack(side="right")
        self.wait_window()

    def _ok(self):
        cite = self.cite_var.get().strip()
        if not cite:
            messagebox.showwarning("ข้อมูลไม่ครบ",
                "กรุณากรอกรายการอ้างอิงหรือชื่อทรัพยากร", parent=self); return
        self.result = {
            "resource_type": self.type_var.get(),
            "citation_text": cite,
            "url":  self.url_var.get().strip() or None,
            "note": self.note_var.get().strip() or None,
        }
        self.destroy()


# ══════════════════════════════════════════════════════
class TQF3StaffDialog(tk.Toplevel):
    """Edit tqf3_staff (section 9: committee + instructors) for a TQF3 record."""
    ROLE_LABELS = {"committee": "คณะกรรมการบริหารรายวิชา", "instructor": "ผู้สอนรายวิชา"}

    def __init__(self, parent, course, tqf3_records: list):
        super().__init__(parent)
        self.title(f"บุคลากร มคอ.3 — {course['code']} {course['name_th'] or ''}")
        self.resizable(True, True)
        self.minsize(680, 0)
        self.grab_set()
        self.result = None
        self._tqf3_records = tqf3_records
        self._staff = []
        self._current_tqf3_id = None

        hdr = tk.Frame(self, bg=BG, padx=10, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="เลือก มคอ.3:", bg=BG, fg=FG,
                 font=FONT_B).pack(side="left", padx=(0, 8))
        self.rec_var = tk.StringVar()
        rec_labels = [
            f"ภาค {r['semester']} / {r['year']}" + (" (พิเศษ)" if r.get("is_special") else "")
            for r in tqf3_records
        ]
        self.rec_combo = ttk.Combobox(hdr, textvariable=self.rec_var,
                                      values=rec_labels, state="readonly", width=28)
        self.rec_combo.pack(side="left")
        self.rec_combo.bind("<<ComboboxSelected>>", self._on_rec_select)
        if rec_labels:
            self.rec_combo.current(0)
            self.after(100, self._on_rec_select)

        tb = tk.Frame(self, bg=BG, pady=4, padx=10)
        tb.pack(fill="x")
        tk.Button(tb, text="+ เพิ่มบุคลากร", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._add_person).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="แก้ไข", bg=BLUE, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._edit_person).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="ลบ", bg=RED, fg=WHITE,
                  font=FONT_B, relief="flat", padx=10, pady=3,
                  command=self._del_person).pack(side="left", padx=(0, 6))
        tk.Button(tb, text="↑", font=FONT_B, relief="flat", padx=8, pady=3,
                  command=self._move_up).pack(side="left", padx=(0, 2))
        tk.Button(tb, text="↓", font=FONT_B, relief="flat", padx=8, pady=3,
                  command=self._move_down).pack(side="left")

        _build_wrapped_action_bar(
            self,
            buttons=[
                {"text": "+ เพิ่มบุคลากร", "bg": GREEN, "command": self._add_person},
                {"text": "แก้ไข", "bg": BLUE, "command": self._edit_person},
                {"text": "ลบ", "bg": RED, "command": self._del_person},
                {"text": "↑", "bg": WHITE, "fg": FG, "command": self._move_up},
                {"text": "↓", "bg": WHITE, "fg": FG, "command": self._move_down},
            ],
            columns=3,
            pack_kwargs={"padx": 10, "pady": (4, 2)},
        )
        tb.destroy()

        cols = ("seq", "role", "name")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                 selectmode="browse", height=14)
        self.tree.heading("seq",  text="#")
        self.tree.heading("role", text="บทบาท")
        self.tree.heading("name", text="ชื่อ-สกุล")
        self.tree.column("seq",  width=35,  anchor="center", stretch=False)
        self.tree.column("role", width=130, anchor="center", stretch=False)
        self.tree.column("name", width=420, anchor="w")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 4))
        vsb.pack(side="left", fill="y", pady=(0, 4))
        self.tree.bind("<Double-1>", lambda e: self._edit_person())
        self.tree.bind("<Return>",   lambda e: self._edit_person())
        self.tree.bind("<Delete>",   lambda e: self._del_person())

        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=10)
        tk.Button(btn_row, text="บันทึก", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self._save).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=5,
                  command=self.destroy).pack(side="right")
        self.wait_window()

    def _on_rec_select(self, event=None):
        idx = self.rec_combo.current()
        if idx < 0:
            return
        rec = self._tqf3_records[idx]
        self._current_tqf3_id = rec["id"]
        try:
            import database as db; db.init_db()
            staff = db.get_tqf3_staff(rec["id"])
            self._staff = [dict(s) for s in staff]
        except Exception:
            self._staff = []
        if not self._staff:
            try:
                import database as db, sqlite3 as _sq, json as _json
                conn = _sq.connect(db.DB_PATH)
                conn.row_factory = _sq.Row
                row = conn.execute(
                    "SELECT instructor_main, instructors_json FROM tqf3 WHERE id=?",
                    (rec["id"],)).fetchone()
                conn.close()
                if row and row["instructor_main"]:
                    self._staff.append({"role": "committee", "seq": 0, "name": row["instructor_main"]})
                for i, n in enumerate(_json.loads(row["instructors_json"] or "[]"), 1):
                    if n and not any(n.startswith(kw) for kw in ("ภาคผนวก", "แบบประเมิน", "เกณฑ์")):
                        self._staff.append({"role": "instructor", "seq": i, "name": n})
            except Exception:
                pass
        self._refresh_tree()

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, s in enumerate(self._staff):
            role_label = self.ROLE_LABELS.get(s.get("role", "instructor"), s.get("role", ""))
            self.tree.insert("", "end", iid=str(i), values=(i + 1, role_label, s.get("name", "")))

    def _selected_idx(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add_person(self):
        dlg = _PersonRowDialog(self)
        if dlg.result:
            self._staff.append(dlg.result)
            self._refresh_tree()

    def _edit_person(self):
        idx = self._selected_idx()
        if idx is None:
            return
        dlg = _PersonRowDialog(self, self._staff[idx])
        if dlg.result:
            self._staff[idx] = dlg.result
            self._refresh_tree()
            self.tree.selection_set(str(idx))

    def _del_person(self):
        idx = self._selected_idx()
        if idx is None:
            return
        self._staff.pop(idx)
        self._refresh_tree()

    def _move_up(self):
        idx = self._selected_idx()
        if idx is None or idx == 0:
            return
        self._staff[idx - 1], self._staff[idx] = self._staff[idx], self._staff[idx - 1]
        self._refresh_tree()
        self.tree.selection_set(str(idx - 1))

    def _move_down(self):
        idx = self._selected_idx()
        if idx is None or idx >= len(self._staff) - 1:
            return
        self._staff[idx], self._staff[idx + 1] = self._staff[idx + 1], self._staff[idx]
        self._refresh_tree()
        self.tree.selection_set(str(idx + 1))

    def _save(self):
        if self._current_tqf3_id is None:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือก มคอ.3 ก่อน", parent=self); return
        for i, s in enumerate(self._staff):
            s["seq"] = i
        self.result = {"tqf3_id": self._current_tqf3_id, "staff": self._staff}
        self.destroy()


class _PersonRowDialog(tk.Toplevel):
    """Sub-dialog: add or edit a single staff person."""
    ROLE_LABELS = {"committee": "คณะกรรมการบริหารรายวิชา", "instructor": "ผู้สอนรายวิชา"}

    def __init__(self, parent, row: dict = None):
        super().__init__(parent)
        self.title("แก้ไขบุคลากร" if row else "เพิ่มบุคลากร")
        self.resizable(False, True)
        self.minsize(440, 0)
        self.grab_set()
        self.result = None
        row = row or {}

        frm = tk.Frame(self, bg=BG, padx=16, pady=12)
        frm.pack(fill="both", expand=True)
        tk.Label(frm, text="บทบาท:", bg=BG, fg=FG, font=FONT_B,
                 anchor="w").grid(row=0, column=0, sticky="w", pady=6)
        self.role_var = tk.StringVar(value=row.get("role", "instructor"))
        self._role_cb = ttk.Combobox(
            frm, textvariable=self.role_var,
            values=list(self.ROLE_LABELS.values()), state="readonly", width=32)
        self._role_cb.set(self.ROLE_LABELS.get(row.get("role", "instructor"), "ผู้สอนรายวิชา"))
        self._role_cb.grid(row=0, column=1, sticky="ew", pady=6)

        tk.Label(frm, text="ชื่อ-สกุล:", bg=BG, fg=FG, font=FONT_B,
                 anchor="w").grid(row=1, column=0, sticky="w", pady=6)
        self.name_var = tk.StringVar(value=row.get("name", ""))
        tk.Entry(frm, textvariable=self.name_var, width=36,
                 font=FONT).grid(row=1, column=1, sticky="ew", pady=6)
        frm.columnconfigure(1, weight=1)

        btn_row = tk.Frame(self, bg=BG, pady=8)
        btn_row.pack(fill="x", padx=16)
        tk.Button(btn_row, text="ตกลง", bg=GREEN, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=4,
                  command=self._ok).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="ยกเลิก", bg=GRAY, fg=WHITE,
                  font=FONT_B, relief="flat", padx=18, pady=4,
                  command=self.destroy).pack(side="right")
        self.wait_window()

    def _ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอกชื่อ-สกุล", parent=self); return
        label = self._role_cb.get()
        role = next((k for k, v in self.ROLE_LABELS.items() if v == label), "instructor")
        self.result = {"role": role, "name": name}
        self.destroy()


# ══════════════════════════════════════════════════════
# Phase 2: LLO Editor + Offering Instructors Dialog
# ══════════════════════════════════════════════════════

class LLOEditorDialog(tk.Toplevel):
    """Edit LLOs for a course + manage CLO<->LLO mapping."""

    def __init__(self, parent, course, llos, clos, mapping):
        super().__init__(parent)
        course = dict(course) if course else {}
        code = course.get("code", "?")
        self.title(f"จัดการ LLO — {code}")
        self.minsize(720, 0)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._llos = [dict(l) for l in llos]
        self._clos = [dict(c) for c in clos]
        # mapping rows: {clo_id, llo_id, clo_number, llo_number, weight}
        self._mapping = {(m["clo_id"], m["llo_id"]): m["weight"]
                         for m in mapping}

        # Header
        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"LLO & CLO-LLO Mapping — {code} {course.get('name_th', '')}",
                 bg=BLUE_DARK, fg=WHITE, font=FONT_B,
                 wraplength=680, anchor="w").pack(padx=14, pady=9)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=6)
        self._tab_llo = tk.Frame(nb, bg=BG)
        self._tab_map = tk.Frame(nb, bg=BG)
        nb.add(self._tab_llo, text="  LLO  ")
        nb.add(self._tab_map, text="  CLO ↔ LLO  ")
        self._build_llo_tab()
        self._build_map_tab()

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="บันทึก", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=22, pady=7, command=self._save).pack(side="left", padx=8)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=7, command=self.destroy).pack(side="left", padx=4)
        self.wait_window()

    # ── LLO Tab ───────────────────────────────────────

    def _build_llo_tab(self):
        t = self._tab_llo
        bar = tk.Frame(t, bg=BG)
        bar.pack(fill="x", pady=(8, 4), padx=8)
        tk.Button(bar, text="+ เพิ่ม LLO", bg=GREEN, fg=WHITE, font=FONT_B,
                  relief="flat", padx=10, pady=4, command=self._add_llo).pack(side="left", padx=(0, 6))
        self._btn_del_llo = tk.Button(bar, text="ลบ", bg=RED, fg=WHITE, font=FONT_B,
                                      relief="flat", padx=10, pady=4, state="disabled",
                                      command=self._del_llo)
        self._btn_del_llo.pack(side="left")
        tk.Label(t, text="LLO = ผลลัพธ์การเรียนรู้ระดับชั้นเรียน (Lesson-Level Learning Outcome)",
                 bg=BG, fg=GRAY, font=FONT_SM).pack(anchor="w", padx=8)

        cols = ("no", "desc_th", "desc_en")
        self._llo_tree = ttk.Treeview(t, columns=cols, show="headings",
                                       selectmode="browse", height=12)
        self._llo_tree.heading("no", text="LLO#")
        self._llo_tree.heading("desc_th", text="คำอธิบาย (ไทย)")
        self._llo_tree.heading("desc_en", text="คำอธิบาย (Eng)")
        self._llo_tree.column("no", width=50, anchor="center")
        self._llo_tree.column("desc_th", width=300, anchor="w")
        self._llo_tree.column("desc_en", width=280, anchor="w")
        vsb = ttk.Scrollbar(t, orient="vertical", command=self._llo_tree.yview)
        self._llo_tree.configure(yscrollcommand=vsb.set)
        self._llo_tree.pack(side="left", fill="both", expand=True, padx=8, pady=4)
        vsb.pack(side="right", fill="y", pady=4)
        self._llo_tree.bind("<<TreeviewSelect>>",
                             lambda e: self._btn_del_llo.config(
                                 state="normal" if self._llo_tree.selection() else "disabled"))
        self._llo_tree.bind("<Double-1>", lambda e: self._edit_llo())
        self._llo_tree.bind("<Return>",   lambda e: self._edit_llo())
        self._llo_tree.bind("<Delete>",   lambda e: self._del_llo())
        self._refresh_llo_tree()

    def _refresh_llo_tree(self):
        for row in self._llo_tree.get_children():
            self._llo_tree.delete(row)
        for item in self._llos:
            self._llo_tree.insert("", "end", values=(
                item.get("llo_number", ""),
                item.get("description_th", ""),
                item.get("description_en", ""),
            ))

    def _add_llo(self):
        next_no = max((l.get("llo_number", 0) for l in self._llos), default=0) + 1
        dlg = _LLORowDialog(self, {"llo_number": next_no})
        if dlg.result:
            self._llos.append(dlg.result)
            self._llos.sort(key=lambda x: x.get("llo_number", 0))
            self._refresh_llo_tree()

    def _edit_llo(self):
        sel = self._llo_tree.selection()
        if not sel: return
        idx = self._llo_tree.index(sel[0])
        dlg = _LLORowDialog(self, self._llos[idx])
        if dlg.result:
            self._llos[idx] = dlg.result
            self._refresh_llo_tree()

    def _del_llo(self):
        sel = self._llo_tree.selection()
        if not sel: return
        idx = self._llo_tree.index(sel[0])
        if messagebox.askyesno("ยืนยัน", "ลบ LLO นี้ใช่ไหม?", parent=self):
            self._llos.pop(idx)
            self._refresh_llo_tree()

    # ── Map Tab ───────────────────────────────────────

    def _build_map_tab(self):
        t = self._tab_map
        tk.Label(t, text="ทำเครื่องหมาย CLO ที่เกี่ยวข้องกับแต่ละ LLO",
                 bg=BG, fg=GRAY, font=FONT_SM).pack(anchor="w", padx=8, pady=(8, 4))

        frame = tk.Frame(t, bg=BG)
        frame.pack(fill="both", expand=True, padx=8, pady=4)

        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        h_sb = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        v_sb = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=h_sb.set, yscrollcommand=v_sb.set)

        h_sb.pack(side="bottom", fill="x")
        v_sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        self._check_vars: dict[tuple, tk.IntVar] = {}

        # Header row: CLOs
        tk.Label(inner, text="LLO \\ CLO", bg=BG, font=FONT_B,
                 width=30, anchor="w").grid(row=0, column=0, padx=4, pady=2)
        for j, clo in enumerate(self._clos):
            tk.Label(inner, text=f"CLO{clo.get('clo_number', j+1)}",
                     bg=BG, font=FONT_SM, width=6, anchor="center",
                     wraplength=60).grid(row=0, column=j + 1, padx=2)

        # Data rows: LLOs × CLOs
        for i, llo in enumerate(self._llos):
            desc = (llo.get("description_th") or "")[:35]
            tk.Label(inner, text=f"LLO{llo.get('llo_number','?')} {desc}",
                     bg=BG, font=FONT_SM, width=30, anchor="w").grid(
                row=i + 1, column=0, padx=4, pady=2)
            for j, clo in enumerate(self._clos):
                key = (clo.get("id", clo.get("clo_id")), llo.get("id", llo.get("llo_id")))
                var = tk.IntVar(value=1 if key in self._mapping else 0)
                self._check_vars[key] = var
                tk.Checkbutton(inner, variable=var, bg=BG).grid(
                    row=i + 1, column=j + 1, padx=2)

        if not self._llos:
            tk.Label(inner, text="ยังไม่มี LLO — ไปเพิ่มใน tab LLO ก่อน",
                     bg=BG, fg=GRAY, font=FONT_SM).grid(row=1, column=0, columnspan=10)
        if not self._clos:
            tk.Label(inner, text="ยังไม่มี CLO มาตรฐาน — ไปเพิ่มใน แก้ไข CLO ก่อน",
                     bg=BG, fg=GRAY, font=FONT_SM).grid(row=2, column=0, columnspan=10)

    # ── Save ─────────────────────────────────────────

    def _save(self):
        mappings = []
        for (clo_id, llo_id), var in self._check_vars.items():
            if var.get():
                mappings.append({"clo_id": clo_id, "llo_id": llo_id, "weight": 1.0})
        self.result = {"llos": self._llos, "mapping": mappings}
        self.destroy()


class _LLORowDialog(tk.Toplevel):
    """Add / edit a single LLO row."""

    def __init__(self, parent, row: dict):
        super().__init__(parent)
        self.title("แก้ไข LLO" if row.get("id") else "เพิ่ม LLO")
        self.minsize(480, 0)
        self.resizable(False, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        form = tk.Frame(self, bg=BG)
        form.pack(padx=16, pady=14, fill="x")

        tk.Label(form, text="LLO#", bg=BG, font=FONT_B).grid(row=0, column=0, sticky="w", pady=6)
        self._no_var = tk.StringVar(value=str(row.get("llo_number", "")))
        tk.Entry(form, textvariable=self._no_var, width=8, font=FONT).grid(
            row=0, column=1, sticky="w", padx=10)

        tk.Label(form, text="คำอธิบาย (ไทย)", bg=BG, font=FONT_B).grid(
            row=1, column=0, sticky="nw", pady=6)
        self._desc_th = tk.Text(form, width=40, height=3, font=FONT, wrap="word")
        self._desc_th.grid(row=1, column=1, padx=10)
        self._desc_th.insert("1.0", row.get("description_th", "") or "")

        tk.Label(form, text="คำอธิบาย (Eng)", bg=BG, font=FONT_B).grid(
            row=2, column=0, sticky="nw", pady=6)
        self._desc_en = tk.Text(form, width=40, height=2, font=FONT, wrap="word")
        self._desc_en.grid(row=2, column=1, padx=10)
        self._desc_en.insert("1.0", row.get("description_en", "") or "")

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=8)
        tk.Button(btn_f, text="บันทึก", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=18, pady=6, command=self._confirm).pack(side="left", padx=6)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=14, pady=6, command=self.destroy).pack(side="left", padx=4)
        self.wait_window()

    def _confirm(self):
        try:
            no = int(self._no_var.get().strip())
        except ValueError:
            messagebox.showwarning("ข้อมูลผิด", "LLO# ต้องเป็นตัวเลข", parent=self); return
        desc_th = self._desc_th.get("1.0", "end").strip()
        if not desc_th:
            messagebox.showwarning("ข้อมูลผิด", "กรุณากรอกคำอธิบาย (ไทย)", parent=self); return
        self.result = {
            "llo_number": no,
            "description_th": desc_th,
            "description_en": self._desc_en.get("1.0", "end").strip(),
        }
        self.destroy()


class OfferingInstructorsDialog(tk.Toplevel):
    """Manage multi-instructor list for a course offering."""

    ROLE_LABELS = {"main": "ผู้สอนหลัก", "co": "ผู้สอนร่วม"}

    def __init__(self, parent, offering: dict, instructors: list):
        super().__init__(parent)
        code = offering.get("code", "?")
        sec = offering.get("section_code", "")
        self.title(f"ผู้สอน — {code} {sec}")
        self.minsize(560, 0)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self._instructors = [dict(i) for i in instructors]

        hdr = tk.Frame(self, bg=BLUE_DARK)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"ผู้สอน — {code} ตอนเรียน {sec}",
                 bg=BLUE_DARK, fg=WHITE, font=FONT_B).pack(padx=14, pady=9, anchor="w")

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=10, pady=(10, 4))
        tk.Button(bar, text="+ เพิ่มผู้สอน", bg=GREEN, fg=WHITE, font=FONT_B,
                  relief="flat", padx=10, pady=4, command=self._add).pack(side="left", padx=(0, 6))
        self._btn_edit = tk.Button(bar, text="แก้ไข", bg=BLUE, fg=WHITE, font=FONT_B,
                                    relief="flat", padx=10, pady=4, state="disabled",
                                    command=self._edit)
        self._btn_edit.pack(side="left", padx=(0, 6))
        self._btn_del = tk.Button(bar, text="ลบ", bg=RED, fg=WHITE, font=FONT_B,
                                   relief="flat", padx=10, pady=4, state="disabled",
                                   command=self._del)
        self._btn_del.pack(side="left")

        cols = ("role", "name", "section")
        self._tree = ttk.Treeview(self, columns=cols, show="headings",
                                   selectmode="browse", height=12)
        self._tree.heading("role", text="บทบาท")
        self._tree.heading("name", text="ชื่อ-สกุล")
        self._tree.heading("section", text="ตอนที่สอน")
        self._tree.column("role", width=110, anchor="center")
        self._tree.column("name", width=280, anchor="w")
        self._tree.column("section", width=90, anchor="center")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=4)
        vsb.pack(side="right", fill="y", pady=4, padx=(0, 4))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._edit())
        self._tree.bind("<Return>",   lambda e: self._edit())
        self._tree.bind("<Delete>",   lambda e: self._del())
        self._refresh_tree()

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="บันทึก", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=22, pady=7, command=self._save).pack(side="left", padx=8)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=16, pady=7, command=self.destroy).pack(side="left", padx=4)
        self.wait_window()

    def _refresh_tree(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for i, item in enumerate(self._instructors):
            role_lbl = self.ROLE_LABELS.get(item.get("role", "co"), item.get("role", "co"))
            tag = "odd" if i % 2 == 0 else "even"
            self._tree.insert("", "end", values=(
                role_lbl,
                item.get("instructor_name", ""),
                item.get("section", ""),
            ), tags=(tag,))
        self._tree.tag_configure("odd", background=WHITE)
        self._tree.tag_configure("even", background="#F7FAFC")

    def _on_select(self, event=None):
        has_sel = bool(self._tree.selection())
        state = "normal" if has_sel else "disabled"
        self._btn_edit.config(state=state)
        self._btn_del.config(state=state)

    def _add(self):
        dlg = _InstructorRowDialog(self, {})
        if dlg.result:
            dlg.result["ordering"] = len(self._instructors)
            self._instructors.append(dlg.result)
            self._refresh_tree()

    def _edit(self):
        sel = self._tree.selection()
        if not sel: return
        idx = self._tree.index(sel[0])
        dlg = _InstructorRowDialog(self, self._instructors[idx])
        if dlg.result:
            self._instructors[idx] = dlg.result
            self._refresh_tree()

    def _del(self):
        sel = self._tree.selection()
        if not sel: return
        idx = self._tree.index(sel[0])
        if messagebox.askyesno("ยืนยัน", "ลบผู้สอนนี้ใช่ไหม?", parent=self):
            self._instructors.pop(idx)
            self._refresh_tree()

    def _save(self):
        for i, item in enumerate(self._instructors):
            item["ordering"] = i
        self.result = self._instructors
        self.destroy()


class _InstructorRowDialog(tk.Toplevel):
    """Add / edit a single instructor row."""

    def __init__(self, parent, row: dict):
        super().__init__(parent)
        self.title("แก้ไขผู้สอน" if row.get("instructor_name") else "เพิ่มผู้สอน")
        self.minsize(420, 0)
        self.resizable(False, True)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None

        form = tk.Frame(self, bg=BG)
        form.pack(padx=16, pady=14, fill="x")

        tk.Label(form, text="ชื่อ-สกุล *", bg=BG, font=FONT_B).grid(
            row=0, column=0, sticky="w", pady=6)
        self._name_var = tk.StringVar(value=row.get("instructor_name", ""))
        tk.Entry(form, textvariable=self._name_var, width=32, font=FONT).grid(
            row=0, column=1, sticky="w", padx=10)

        tk.Label(form, text="บทบาท", bg=BG, font=FONT_B).grid(
            row=1, column=0, sticky="w", pady=6)
        self._role_var = tk.StringVar(
            value=self.ROLE_LABELS.get(row.get("role", "co"), "ผู้สอนร่วม"))
        role_cb = ttk.Combobox(form, textvariable=self._role_var,
                                values=list(self.ROLE_LABELS.values()),
                                width=12, state="readonly")
        role_cb.grid(row=1, column=1, sticky="w", padx=10)

        tk.Label(form, text="ตอนที่สอน", bg=BG, font=FONT_B).grid(
            row=2, column=0, sticky="w", pady=6)
        self._section_var = tk.StringVar(value=row.get("section", ""))
        tk.Entry(form, textvariable=self._section_var, width=10, font=FONT).grid(
            row=2, column=1, sticky="w", padx=10)

        btn_f = tk.Frame(self, bg=BG)
        btn_f.pack(pady=8)
        tk.Button(btn_f, text="บันทึก", bg=BLUE, fg=WHITE, font=FONT_B,
                  relief="flat", padx=18, pady=6, command=self._confirm).pack(side="left", padx=6)
        tk.Button(btn_f, text="ยกเลิก", bg="#9CA3AF", fg=WHITE, font=FONT,
                  relief="flat", padx=14, pady=6, command=self.destroy).pack(side="left", padx=4)
        self.wait_window()

    def _confirm(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("ข้อมูลผิด", "กรุณากรอกชื่อ-สกุล", parent=self); return
        role_map = {v: k for k, v in self.ROLE_LABELS.items()}
        self.result = {
            "instructor_name": name,
            "role": role_map.get(self._role_var.get(), "co"),
            "section": self._section_var.get().strip(),
        }
        self.destroy()


# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    app = TQFApp()
    app.mainloop()
