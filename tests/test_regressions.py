import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import database as db
import input_gui


class _FakeVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _FakeText:
    def __init__(self, value):
        self._value = value

    def get(self, *_args):
        return self._value


class _FakeButton:
    def __init__(self):
        self.state = None

    def config(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]


class _DummyDialog:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


class RegressionTests(unittest.TestCase):
    def test_init_db_migrates_course_assessments_detail_columns(self):
        tmpdir = tempfile.mkdtemp()
        temp_db = os.path.join(tmpdir, "legacy.db")
        try:
            conn = sqlite3.connect(temp_db)
            conn.execute(
                """
                CREATE TABLE course_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    seq INTEGER DEFAULT 0,
                    name TEXT NOT NULL,
                    weight_pct REAL NOT NULL DEFAULT 0,
                    clo_mapping TEXT DEFAULT '[]'
                )
                """
            )
            conn.commit()
            conn.close()

            original_path = db.DB_PATH
            try:
                db.DB_PATH = temp_db
                db.init_db()
                with sqlite3.connect(temp_db) as verify_conn:
                    cols = {
                        row[1]: row[2]
                        for row in verify_conn.execute("PRAGMA table_info(course_assessments)")
                    }
            finally:
                db.DB_PATH = original_path
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.assertIn("full_score", cols)
        self.assertIn("assessment_period", cols)
        self.assertIn("eval_criteria", cols)
        self.assertIn("pass_threshold", cols)

    def test_init_db_rebuilds_tqf3_unique_constraint_to_include_is_special(self):
        tmpdir = tempfile.mkdtemp()
        temp_db = os.path.join(tmpdir, "legacy_tqf3.db")
        try:
            conn = sqlite3.connect(temp_db)
            conn.execute(
                """
                CREATE TABLE courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    name_th TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE tqf3 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    semester INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    instructor_main TEXT DEFAULT '',
                    instructors_json TEXT DEFAULT '[]',
                    location TEXT DEFAULT '',
                    objectives TEXT DEFAULT '',
                    source_file TEXT DEFAULT '',
                    imported_at TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(course_id, semester, year)
                )
                """
            )
            conn.commit()
            conn.close()

            original_path = db.DB_PATH
            try:
                db.DB_PATH = temp_db
                db.init_db()
                with sqlite3.connect(temp_db) as verify_conn:
                    indexes = list(verify_conn.execute("PRAGMA index_list('tqf3')"))
                    index_cols = []
                    for row in indexes:
                        if row[2]:
                            index_cols.append(
                                [info[2] for info in verify_conn.execute(f"PRAGMA index_info('{row[1]}')")]
                            )
            finally:
                db.DB_PATH = original_path
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.assertIn(["course_id", "semester", "year", "is_special"], index_cols)

    def test_init_db_backfills_course_offerings_from_tqf3(self):
        tmpdir = tempfile.mkdtemp()
        temp_db = os.path.join(tmpdir, "legacy_offerings.db")
        try:
            conn = sqlite3.connect(temp_db)
            conn.execute(
                """
                CREATE TABLE curricula (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    curriculum_id INTEGER,
                    code TEXT NOT NULL,
                    name_th TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE tqf3 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    semester INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    instructor_main TEXT DEFAULT '',
                    instructors_json TEXT DEFAULT '[]',
                    location TEXT DEFAULT '',
                    objectives TEXT DEFAULT '',
                    source_file TEXT DEFAULT '',
                    source_type TEXT DEFAULT 'generated',
                    is_special INTEGER NOT NULL DEFAULT 0,
                    imported_at TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(course_id, semester, year, is_special)
                )
                """
            )
            conn.execute("INSERT INTO curricula (id, version) VALUES (1, '69')")
            conn.execute(
                "INSERT INTO courses (id, curriculum_id, code, name_th) VALUES (1, 1, 'SMA1001', 'Test Course')"
            )
            conn.execute(
                """
                INSERT INTO tqf3 (course_id, semester, year, source_type, is_special)
                VALUES (1, 1, 2569, 'generated', 0)
                """
            )
            conn.commit()
            conn.close()

            original_path = db.DB_PATH
            try:
                db.DB_PATH = temp_db
                db.init_db()
                with sqlite3.connect(temp_db) as verify_conn:
                    verify_conn.row_factory = sqlite3.Row
                    offering = verify_conn.execute(
                        "SELECT * FROM course_offerings WHERE course_id=1"
                    ).fetchone()
                    tqf3_row = verify_conn.execute(
                        "SELECT offering_id FROM tqf3 WHERE course_id=1"
                    ).fetchone()
            finally:
                db.DB_PATH = original_path
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.assertIsNotNone(offering)
        self.assertEqual(offering["section_code"], "N01")
        self.assertEqual(offering["source_type"], "generated")
        self.assertEqual(tqf3_row["offering_id"], offering["id"])

    def test_upsert_tqf3_creates_linked_course_offering(self):
        tmpdir = tempfile.mkdtemp()
        temp_db = os.path.join(tmpdir, "offering_upsert.db")
        try:
            original_path = db.DB_PATH
            try:
                db.DB_PATH = temp_db
                db.init_db()
                curriculum_id = db.upsert_curriculum("69", "Test Curriculum", 2569)
                course_id = db.upsert_course("SMA1002", "Another Course", curriculum_id=curriculum_id)
                tqf3_id = db.upsert_tqf3(course_id, 2, 2569, is_special=True)
                with sqlite3.connect(temp_db) as verify_conn:
                    verify_conn.row_factory = sqlite3.Row
                    tqf3_row = verify_conn.execute(
                        "SELECT offering_id, is_special FROM tqf3 WHERE id=?",
                        (tqf3_id,),
                    ).fetchone()
                    offering = verify_conn.execute(
                        "SELECT * FROM course_offerings WHERE id=?",
                        (tqf3_row["offering_id"],),
                    ).fetchone()
            finally:
                db.DB_PATH = original_path
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.assertIsNotNone(offering)
        self.assertEqual(offering["section_code"], "P01")
        self.assertEqual(offering["is_special"], 1)

    def test_delete_course_offering_can_remove_linked_tqf3_snapshot(self):
        tmpdir = tempfile.mkdtemp()
        temp_db = os.path.join(tmpdir, "offering_delete.db")
        try:
            original_path = db.DB_PATH
            try:
                db.DB_PATH = temp_db
                db.init_db()
                curriculum_id = db.upsert_curriculum("69", "Test Curriculum", 2569)
                course_id = db.upsert_course("SMA1001", "Calculus 1", curriculum_id=curriculum_id)
                offering_id = db.upsert_course_offering(course_id, 1, 2569, curriculum_id=curriculum_id)
                tqf3_id = db.upsert_tqf3(course_id, 1, 2569, offering_id=offering_id)
                db.replace_clos(
                    tqf3_id,
                    [
                        {
                            "clo_number": 1,
                            "description": "Test CLO",
                            "plo_mapping": [1],
                        }
                    ],
                )
                db.delete_course_offering(offering_id, delete_linked_tqf3=True)
                with sqlite3.connect(temp_db) as verify_conn:
                    offering = verify_conn.execute(
                        "SELECT id FROM course_offerings WHERE id=?",
                        (offering_id,),
                    ).fetchone()
                    tqf3_row = verify_conn.execute(
                        "SELECT id FROM tqf3 WHERE id=?",
                        (tqf3_id,),
                    ).fetchone()
                    clo_count = verify_conn.execute(
                        "SELECT COUNT(*) FROM clos WHERE tqf3_id=?",
                        (tqf3_id,),
                    ).fetchone()[0]
            finally:
                db.DB_PATH = original_path
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.assertIsNone(offering)
        self.assertIsNone(tqf3_row)
        self.assertEqual(clo_count, 0)

    def test_course_offering_dialog_confirm_builds_normalized_result(self):
        dialog = _DummyDialog()
        dialog.sem_var = _FakeVar("2")
        dialog.year_var = _FakeVar("2569")
        dialog.section_var = _FakeVar("P01")
        dialog.status_var = _FakeVar("active")
        dialog.SECTION_CHOICES = ["N01", "P01"]
        dialog.result = None

        input_gui.CourseOfferingDialog._confirm(dialog)

        self.assertTrue(dialog.destroyed)
        self.assertEqual(
            dialog.result,
            {
                "semester": 2,
                "year": 2569,
                "section_code": "P01",
                "is_special": True,
                "status": "active",
            },
        )

    def test_offering_search_matches_code_name_and_section(self):
        row = {
            "code": "SMA1001",
            "name_th": "แคลคูลัส 1",
            "section_code": "N01",
            "status": "active",
            "source_type": "catalog",
        }

        self.assertTrue(input_gui._offering_matches_search(row, "SMA1"))
        self.assertTrue(input_gui._offering_matches_search(row, "แคล"))
        self.assertTrue(input_gui._offering_matches_search(row, "N01"))
        self.assertFalse(input_gui._offering_matches_search(row, "P01"))

    def test_catalog_select_updates_visible_add_offering_button(self):
        class _CatalogStub:
            def __init__(self):
                self.btn_cat_edit = _FakeButton()
                self.btn_cat_del = _FakeButton()
                self.btn_cat_clo = _FakeButton()
                self.btn_cat_plan = _FakeButton()
                self.btn_cat_gen3 = _FakeButton()
                self.btn_cat_res = _FakeButton()
                self.btn_cat_staff = _FakeButton()
                self.btn_cat_add_offering = _FakeButton()
                self.btn_cat_add_offering_visible = _FakeButton()
                self.cat_tree = self
                self.cleared = False

            def selection(self):
                return []

            def _clear_cat_detail(self):
                self.cleared = True

        stub = _CatalogStub()
        input_gui.TQFApp._on_catalog_select(stub)

        self.assertEqual(stub.btn_cat_add_offering.state, "disabled")
        self.assertEqual(stub.btn_cat_add_offering_visible.state, "disabled")
        self.assertTrue(stub.cleared)

    def test_plo_editor_ok_preserves_custom_plo_code(self):
        dialog = _DummyDialog()
        dialog.num_var = _FakeVar("4")
        dialog.code_var = _FakeVar("4.3")
        dialog.cat_var = _FakeVar("ด้านความรู้")
        dialog.desc_text = _FakeText("ทดสอบคำอธิบาย")
        dialog.result = None

        input_gui.PLOEditRowDialog._ok(dialog)

        self.assertTrue(dialog.destroyed)
        self.assertEqual(dialog.result["plo_number"], 4)
        self.assertEqual(dialog.result["plo_code"], "4.3")
        self.assertEqual(dialog.result["category"], "ด้านความรู้")

    def test_assessment_editor_ok_preserves_detail_metadata(self):
        dialog = _DummyDialog()
        dialog._asmt = {
            "name": "สอบกลางภาค",
            "full_score": 100,
            "weight_pct": 30,
            "pass_threshold": 50,
            "assessment_period": "สัปดาห์ที่ 8",
            "eval_criteria": "ต้องได้อย่างน้อยครึ่งหนึ่ง",
            "clo_mapping": [1],
        }
        dialog.name_var = _FakeVar("สอบกลางภาค")
        dialog.full_var = _FakeVar("80")
        dialog.wt_var = _FakeVar("40")
        dialog.pass_var = _FakeVar("60")
        dialog._clo_vars = {1: _FakeVar(False), 2: _FakeVar(True)}
        dialog.result = None

        input_gui.AsmtEditRowDialog._ok(dialog)

        self.assertTrue(dialog.destroyed)
        self.assertEqual(dialog.result["full_score"], 80.0)
        self.assertEqual(dialog.result["weight_pct"], 40.0)
        self.assertEqual(dialog.result["pass_threshold"], 60.0)
        self.assertEqual(dialog.result["clo_mapping"], [2])
        self.assertEqual(dialog.result["assessment_period"], "สัปดาห์ที่ 8")
        self.assertEqual(dialog.result["eval_criteria"], "ต้องได้อย่างน้อยครึ่งหนึ่ง")

    def test_assessment_editor_ok_uses_selected_period(self):
        dialog = _DummyDialog()
        dialog._asmt = {
            "name": "Quiz",
            "full_score": 10,
            "weight_pct": 10,
            "pass_threshold": 50,
            "assessment_period": "",
            "eval_criteria": "",
            "clo_mapping": [1],
        }
        dialog.name_var = _FakeVar("Quiz")
        dialog.full_var = _FakeVar("10")
        dialog.wt_var = _FakeVar("15")
        dialog.pass_var = _FakeVar("50")
        dialog.period_var = _FakeVar("Week 8")
        dialog._clo_vars = {1: _FakeVar(True)}
        dialog.result = None

        input_gui.AsmtEditRowDialog._ok(dialog)

        self.assertTrue(dialog.destroyed)
        self.assertEqual(dialog.result["assessment_period"], "Week 8")

    def test_clo_dialog_can_be_constructed(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        try:
            with patch.object(input_gui.CLOEditRowDialog, "wait_window", lambda self: None):
                dialog = input_gui.CLOEditRowDialog(
                    root,
                    {
                        "clo_number": 1,
                        "description": "",
                        "domain": "",
                        "teaching_strategy": "",
                        "assessment_method": "",
                        "pass_threshold_pct": 50.0,
                        "plo_mapping": [],
                    },
                    [],
                    ["ด้านความรู้"],
                )
                dialog.destroy()
        finally:
            root.destroy()

    def test_clo_dialog_wraps_many_plo_checkboxes(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        plos = [
            {"plo_number": i, "plo_code": f"{i}.1" if i % 2 == 0 else str(i)}
            for i in range(1, 10)
        ]
        try:
            with patch.object(input_gui.CLOEditRowDialog, "wait_window", lambda self: None):
                dialog = input_gui.CLOEditRowDialog(
                    root,
                    {
                        "clo_number": 1,
                        "description": "",
                        "domain": "",
                        "teaching_strategy": "",
                        "assessment_method": "",
                        "pass_threshold_pct": 50.0,
                        "plo_mapping": [2, 4],
                    },
                    plos,
                    ["ด้านความรู้"],
                )
                self.assertEqual(len(dialog._plo_vars), len(plos))
                dialog.destroy()
        finally:
            root.destroy()

    def test_asmt_dialog_wraps_many_clo_checkboxes(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        clos = [{"clo_number": i} for i in range(1, 13)]
        try:
            with patch.object(input_gui.AsmtEditRowDialog, "wait_window", lambda self: None):
                dialog = input_gui.AsmtEditRowDialog(
                    root,
                    {
                        "name": "สอบย่อย",
                        "full_score": 20,
                        "weight_pct": 10,
                        "pass_threshold": 50,
                        "clo_mapping": [1, 3, 5],
                    },
                    clos,
                )
                self.assertEqual(len(dialog._clo_vars), len(clos))
                dialog.destroy()
        finally:
            root.destroy()

    def test_tqf3_generate_dialog_can_be_constructed(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        try:
            with patch.object(input_gui.TQF3GenerateDialog, "wait_window", lambda self: None):
                dialog = input_gui.TQF3GenerateDialog(
                    root,
                    {"code": "MAT999", "name_th": "วิชาทดสอบ"},
                )
                self.assertEqual(dialog.sem_var.get(), "1")
                dialog.destroy()
        finally:
            root.destroy()

    def test_teaching_plan_row_dialog_ok_builds_normalized_result(self):
        dialog = _DummyDialog()
        dialog.week_var = _FakeVar("3")
        dialog.week_label_var = _FakeVar("")
        dialog.hours_planned_var = _FakeVar("")
        dialog.hours_theory_var = _FakeVar("2")
        dialog.hours_practice_var = _FakeVar("1")
        dialog.hours_self_var = _FakeVar("4")
        dialog.llo_text = _FakeText("LLO 3")
        dialog.topic_text = _FakeText("หัวข้อทดสอบ")
        dialog.activities_text = _FakeText("กิจกรรม")
        dialog.method_text = _FakeText("บรรยาย")
        dialog.media_text = _FakeText("สไลด์")
        dialog.assessment_text = _FakeText("quiz")
        dialog.result = None
        dialog._to_float = input_gui._TeachingPlanRowDialog._to_float
        dialog._read_text = input_gui._TeachingPlanRowDialog._read_text

        input_gui._TeachingPlanRowDialog._ok(dialog)

        self.assertTrue(dialog.destroyed)
        self.assertEqual(dialog.result["week"], 3)
        self.assertEqual(dialog.result["week_label"], "3")
        self.assertEqual(dialog.result["hours_planned"], 3.0)
        self.assertEqual(dialog.result["hours_theory"], 2.0)
        self.assertEqual(dialog.result["hours_practice"], 1.0)
        self.assertEqual(dialog.result["hours_self"], 4.0)
        self.assertEqual(dialog.result["topic"], "หัวข้อทดสอบ")

    def test_teaching_plan_dialog_can_be_constructed(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        try:
            with patch.object(input_gui.CourseTeachingPlanDialog, "wait_window", lambda self: None):
                dialog = input_gui.CourseTeachingPlanDialog(
                    root,
                    {"code": "MAT999", "name_th": "วิชาทดสอบ"},
                    [{
                        "week": 1,
                        "week_label": "1(3)",
                        "llo_text": "LLO1",
                        "topic": "บทนำ",
                        "teaching_method": "บรรยาย",
                        "hours_planned": 3,
                    }],
                )
                self.assertEqual(len(dialog._rows), 1)
                dialog.destroy()
        finally:
            root.destroy()

    def test_course_resources_dialog_can_be_constructed(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        try:
            with patch.object(input_gui.CourseResourcesDialog, "wait_window", lambda self: None):
                dialog = input_gui.CourseResourcesDialog(
                    root,
                    {"code": "MAT999", "name_th": "วิชาทดสอบ"},
                    [],
                )
                dialog.destroy()
        finally:
            root.destroy()

    def test_tqf3_staff_dialog_can_be_constructed(self):
        root = input_gui.tk.Tk()
        root.withdraw()
        try:
            with patch.object(input_gui.TQF3StaffDialog, "wait_window", lambda self: None):
                dialog = input_gui.TQF3StaffDialog(
                    root,
                    {"code": "MAT999", "name_th": "วิชาทดสอบ"},
                    [{"id": 1, "semester": 1, "year": 2569, "is_special": 0}],
                )
                dialog.destroy()
        finally:
            root.destroy()

    def test_course_clo_editor_accepts_sqlite_row_course(self):
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory = sqlite3.Row
            course = conn.execute(
                "SELECT 'TEST101' AS code, 'Test Course' AS name_th"
            ).fetchone()

        root = input_gui.tk.Tk()
        root.withdraw()
        try:
            with patch.object(input_gui.CourseCLOEditor, "wait_window", lambda self: None):
                dialog = input_gui.CourseCLOEditor(root, course, [], [], [])
                dialog.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
