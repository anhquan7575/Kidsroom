import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QMessageBox, QPushButton, QScrollArea,
    QTabWidget,
)

from kidsroom.app import LearningWindow, Shield
from kidsroom.core import Store
from kidsroom.theme import apply_theme
from kidsroom.vision import VisionWorker
from kidsroom.widgets import ExerciseDialog, ParentDialog, QuestionEditor


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        apply_theme(cls.app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "test.sqlite3")
        self.questions = [{"kind": "short", "prompt": "2+2?", "accepted": ["4"]}]
        self.exercise_id = self.store.save_exercise("Math", "Math", True, 15, self.questions)
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            if isinstance(widget, LearningWindow):
                widget.timer.stop()
                widget.tray.hide()
                widget.panel.hide()
                widget.shutting_down = True
                for shield in widget.shields:
                    shield.hide()
                    shield.deleteLater()
                widget.panel.deleteLater()
            widget.hide()
            widget.deleteLater()
        self.app.processEvents()
        self.store.close()
        self.temp.cleanup()

    def keep(self, widget):
        self.widgets.append(widget)
        return widget

    def test_themed_editor_fits_small_screen_and_keeps_actions_accessible(self):
        editor = self.keep(QuestionEditor(None))
        editor.resize(1024, 700)
        editor.show()
        self.app.processEvents()
        self.assertLessEqual(editor.height(), 700)
        buttons = editor.findChild(QDialogButtonBox)
        self.assertEqual(buttons.button(QDialogButtonBox.StandardButton.Save).text(), "Lưu")
        self.assertEqual(buttons.button(QDialogButtonBox.StandardButton.Cancel).text(), "Hủy")
        self.assertTrue(editor.rect().contains(buttons.geometry()))
        scroll = editor.findChild(QScrollArea)
        scroll.ensureWidgetVisible(editor.solution)
        self.app.processEvents()
        position = editor.solution.mapTo(scroll.viewport(), editor.solution.rect().center())
        self.assertTrue(scroll.viewport().rect().contains(position))

    def test_editor_preserves_questions_when_switching_and_saves(self):
        editor = self.keep(QuestionEditor(None))
        editor.title_edit.setText("My quiz")
        editor.prompt.setPlainText("First question")
        editor.accepted.setPlainText("one\nONE!")
        editor.add_question()
        editor.kind.setCurrentIndex(editor.kind.findData("choice"))
        editor.prompt.setPlainText("Second question")
        editor.choices.setPlainText("a\nb")
        editor.correct.setValue(2)
        editor.question_list.setCurrentRow(0)
        self.assertEqual(editor.prompt.toPlainText(), "First question")
        self.assertEqual(editor.accepted.toPlainText(), "one\nONE!")
        editor.save()
        self.assertEqual(editor.result(), QDialog.DialogCode.Accepted)
        saved = self.store.save_exercise(**editor.result_data)
        self.assertEqual(self.store.exercise(saved)["questions"][1]["correct"], 1)

    def test_editor_removal_does_not_overwrite_adjacent_question(self):
        exercise = {"title": "Test", "subject": "", "minutes": 15, "visible": True,
                    "questions": self.questions + [
                        {"kind": "essay", "prompt": "Keep this"},
                        {"kind": "short", "prompt": "Third", "accepted": ["3"]},
                    ]}
        editor = self.keep(QuestionEditor(None, exercise))
        editor.remove_question()
        self.assertEqual(editor.prompt.toPlainText(), "Keep this")
        editor.save()
        self.assertEqual(editor.result_data["questions"][1]["prompt"], "Third")

    def test_student_submission_grants_configured_time(self):
        dialog = self.keep(ExerciseDialog(None, self.store, self.store.exercise(self.exercise_id)))
        dialog.inputs[0].setText("4")
        with patch("kidsroom.widgets.QMessageBox.information") as message:
            dialog.submit()
        self.assertEqual(dialog.outcome, {
            "status": "rewarded", "minutes": 15, "correct_count": 1,
            "essay_answered_count": 0, "total_questions": 1,
        })
        self.assertIn("1/1", message.call_args.args[2])
        self.assertGreater(self.store.reward_time(), 895)
        self.assertEqual(self.store.remaining(), 0)

    def test_wrong_submission_reports_score_and_requires_another_exam(self):
        self.store.save_exercise("Other", "Math", True, 15, self.questions)
        dialog = self.keep(ExerciseDialog(None, self.store, self.store.exercise(self.exercise_id)))
        dialog.inputs[0].setText("3")
        with patch("kidsroom.widgets.QMessageBox.information") as message:
            dialog.submit()
        self.assertEqual(dialog.outcome["status"], "incorrect")
        self.assertEqual(dialog.outcome["attempt"], 2)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertIn("0/1", message.call_args.args[2])
        self.assertIn("chưa được thưởng", message.call_args.args[2])
        self.assertIn("chọn đề khác", message.call_args.args[2])
        self.assertEqual(message.call_count, 1)
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, ["4"])
        self.assertEqual(self.store.remaining(), 0)

    def test_parent_visibility_and_essay_review(self):
        essay = self.store.save_exercise(
            "Essay", "Writing", True, 20, [{"kind": "essay", "prompt": "Write"}]
        )
        self.store.submit(essay, ["My text"])
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        tabs = dialog.findChild(QTabWidget)
        self.assertEqual(tabs.tabText(3), "Duyệt bài")
        self.assertIn("1 bài đang chờ", dialog.review_status.text())
        self.assertFalse(dialog.approve_review_button.isEnabled())
        dialog.exercise_list.setCurrentRow(0)
        dialog.toggle_exercise()
        self.assertFalse(self.store.exercise(self.exercise_id)["visible"])
        dialog.pending_list.setCurrentRow(0)
        self.assertTrue(dialog.approve_review_button.isEnabled())
        self.assertIn("My text", dialog.submission_text.toPlainText())
        with patch("kidsroom.widgets.QMessageBox.information"):
            dialog.review(True)
        self.assertEqual(dialog.pending_list.count(), 0)
        self.assertIn("Chưa có bài chờ duyệt", dialog.review_status.text())
        self.assertFalse(dialog.approve_review_button.isEnabled())
        self.assertGreater(self.store.reward_time(), 1195)

    def test_parent_can_stop_service_with_admin_elevation(self):
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        dialog.resize(1000, 700)
        dialog.show()
        self.app.processEvents()
        stop_button = next(
            item for item in dialog.findChildren(QPushButton)
            if item.text().startswith("Dừng Kidsroom Service")
        )
        self.assertTrue(dialog.rect().contains(stop_button.geometry()))
        with patch(
            "kidsroom.widgets.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ), patch("kidsroom.widgets.win32api.ShellExecute") as launch:
            dialog.stop_service()
        launch.assert_not_called()
        with patch(
            "kidsroom.widgets.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ), patch("kidsroom.widgets.win32api.ShellExecute", return_value=33) as launch, \
                patch("kidsroom.widgets.QMessageBox.information") as message:
            dialog.stop_service()
        self.assertEqual(launch.call_args.args[1], "runas")
        self.assertEqual(launch.call_args.args[2], sys.executable)
        self.assertEqual(launch.call_args.args[3], "-I -m kidsroom.service stop")
        message.assert_called_once()
        self.assertTrue(dialog.exit_requested)

    def test_parent_uses_bundled_service_executable_when_frozen(self):
        executable = self.root / "Kidsroom.exe"
        service_executable = self.root / "KidsroomService.exe"
        executable.touch()
        service_executable.touch()
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "executable", str(executable)), \
                patch(
                    "kidsroom.widgets.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.Yes,
                ), patch("kidsroom.widgets.win32api.ShellExecute", return_value=33) as launch, \
                patch("kidsroom.widgets.QMessageBox.information"):
            dialog.stop_service()
        self.assertEqual(launch.call_args.args[2], str(service_executable))
        self.assertEqual(launch.call_args.args[3], "stop")
        self.assertTrue(dialog.exit_requested)

    def test_parent_imports_exam_from_pasted_json(self):
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        exam_json = json.dumps({
            "title": "Pasted Exam 2^2",
            "subject": "Toán 6",
            "minutes": 20,
            "visible": True,
            "questions": [
                {
                    "kind": "short",
                    "prompt": "Tính 3^5?",
                    "accepted": ["243", "3^5"],
                }
            ],
        })
        dialog.json_paste_box.setPlainText(exam_json)
        with patch("kidsroom.widgets.QMessageBox.information") as message:
            dialog.import_exam_from_text()
        message.assert_called_once()
        self.assertEqual(dialog.json_paste_box.toPlainText(), "")
        all_exams = self.store.exercises()
        titles = [e["title"] for e in all_exams]
        self.assertIn("Pasted Exam 2²", titles)
        pasted = next(e for e in all_exams if e["title"] == "Pasted Exam 2²")
        self.assertEqual(pasted["questions"][0]["prompt"], "Tính 3⁵?")
        self.assertIn("3⁵", pasted["questions"][0]["accepted"])
        self.assertIn("3^5", pasted["questions"][0]["accepted"])

    def test_parent_close_application_button_and_shutdown(self):
        parent_window = MagicMock()
        dialog = self.keep(ParentDialog(parent_window, self.store, self.root))
        dialog.resize(1000, 700)
        dialog.show()
        self.app.processEvents()

        close_btn = next(
            item for item in dialog.findChildren(QPushButton)
            if item.text() == "Đóng chương trình"
        )
        self.assertIsNotNone(close_btn)

        with patch(
            "kidsroom.widgets.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ):
            close_btn.click()
        self.assertFalse(dialog.exit_requested)
        parent_window.shutdown.assert_not_called()

        with patch(
            "kidsroom.widgets.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            close_btn.click()
        self.assertTrue(dialog.exit_requested)
        parent_window.shutdown.assert_called_once()

    def test_parent_import_pasted_json_rejects_empty(self):
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        dialog.json_paste_box.setPlainText("   ")
        with patch("kidsroom.widgets.QMessageBox.warning") as warning:
            dialog.import_exam_from_text()
        warning.assert_called_once()

    def test_exercise_table_structure_and_columns(self):
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        table = dialog.exercise_list
        self.assertEqual(table.columnCount(), 5)
        headers = [table.horizontalHeaderItem(i).text() for i in range(5)]
        self.assertEqual(headers, ["STT", "Hiển thị", "Môn học", "Tên đề bài", "Thời gian"])
        self.assertTrue(table.showGrid())
        self.assertEqual(table.item(0, 0).text(), "1")
        self.assertEqual(table.item(0, 1).text(), "Hiện")
        self.assertEqual(table.item(0, 2).text(), "Math")
        self.assertEqual(table.item(0, 3).text(), "Math")
        self.assertEqual(table.item(0, 4).text(), "15 phút")
        dialog.toggle_exercise()
        self.assertEqual(table.item(0, 1).text(), "Ẩn")

    def test_parent_exports_selected_exam_as_json(self):
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        dialog.exercise_list.setCurrentRow(0)
        export_path = self.root / "exported.json"
        with patch(
            "kidsroom.widgets.QFileDialog.getSaveFileName",
            return_value=(str(export_path), "Đề thi JSON (*.json)"),
        ), patch("kidsroom.widgets.QMessageBox.information") as message:
            dialog.export_exam()
        exported = json.loads(export_path.read_text("utf-8"))
        self.assertEqual(exported, {
            "title": "Math", "subject": "Math", "minutes": 15,
            "visible": True, "questions": self.questions,
        })
        message.assert_called_once()

    def test_reward_time_starts_only_after_child_uses_it_and_expires(self):
        window = self.keep(LearningWindow(self.store, self.root))
        now = time.time()
        self.store.configure({
            "typing_minutes": 1, "typing_exe": "typing.exe", "typing_template": "sample.png",
        })
        self.store.reward_typing(now)
        with patch("kidsroom.core.time.time", return_value=now + 59):
            window.tick()
        self.assertTrue(window.isVisible())
        self.assertFalse(window.panel.isVisible())
        self.assertIn("01:00", window.current_reward_label.text())
        with patch("kidsroom.core.time.time", return_value=now + 59):
            window.use_computer_button.click()
        self.assertFalse(window.isVisible())
        self.assertTrue(window.panel.isVisible())
        with patch("kidsroom.core.time.time", return_value=now + 118):
            window.tick()
        self.assertTrue(window.panel.isVisible())
        self.assertIn("00:01", window.panel.label.text())
        with patch("kidsroom.core.time.time", return_value=now + 119):
            window.tick()
        self.assertTrue(window.isVisible())
        self.assertFalse(window.panel.isVisible())
        self.assertTrue(window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertFalse(window.panel.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(window.panel.windowFlags() & Qt.WindowType.Window)
        with patch("kidsroom.core.time.time", return_value=now + 119):
            window.close()
        self.assertTrue(window.isVisible())

    def test_use_computer_without_reward_explains_how_to_earn_time(self):
        window = self.keep(LearningWindow(self.store, self.root))
        window.show()
        with patch("kidsroom.app.QMessageBox.information") as message:
            window.use_computer_button.click()
        self.assertEqual(message.call_args.args[1], "Không còn thời gian thưởng")
        self.assertIn(
            "Hãy làm bài tập để có thời gian thưởng",
            message.call_args.args[2],
        )
        self.assertTrue(window.isVisible())
        self.assertFalse(window.panel.isVisible())

    def test_return_to_learning_pauses_time_and_next_reward_adds_remainder(self):
        second = self.store.save_exercise("English", "English", True, 15, self.questions)
        now = time.time()
        self.store.submit(self.exercise_id, ["4"], now)
        self.store.start_reward_time(now)
        window = self.keep(LearningWindow(self.store, self.root))
        with patch("kidsroom.core.time.time", return_value=now + 120):
            window.return_to_learning()
        self.assertEqual(self.store.remaining(now + 120), 0)
        self.assertEqual(self.store.get("paused_reward_seconds"), 780)
        self.assertIn("đã dừng đếm giờ khám phá", window.message.text().lower())
        self.store.submit(second, ["4"], now + 600)
        self.assertEqual(self.store.reward_time(now + 600), 1680)
        self.store.start_reward_time(now + 600)
        self.assertEqual(self.store.remaining(now + 600), 1680)

    def test_parent_management_releases_desktop_and_restores_topmost(self):
        window = self.keep(LearningWindow(self.store, self.root))
        window.show()
        shield = Shield()
        window.shields.append(shield)
        shield.show()
        self.store.set_password("parent123")

        def verify_password_prompt(parent, *_):
            topmost = Qt.WindowType.WindowStaysOnTopHint
            self.assertIs(parent, window)
            self.assertTrue(window.windowFlags() & topmost)
            self.assertTrue(shield.windowFlags() & topmost)
            self.assertTrue(window.isVisible())
            self.assertTrue(shield.isVisible())
            return "parent123", True

        def verify_management_mode(dialog):
            topmost = Qt.WindowType.WindowStaysOnTopHint
            self.assertFalse(window.windowFlags() & topmost)
            self.assertFalse(window.panel.windowFlags() & topmost)
            self.assertFalse(dialog.windowFlags() & topmost)
            self.assertFalse(window.isVisible())
            self.assertFalse(window.panel.isVisible())
            self.assertFalse(shield.isVisible())
            return QDialog.DialogCode.Rejected

        with patch(
            "kidsroom.app.QInputDialog.getText", side_effect=verify_password_prompt
        ), patch.object(self.store, "authenticate", return_value=True), \
                patch("kidsroom.app.ParentDialog.exec", new=verify_management_mode):
            window.open_parent()

        topmost = Qt.WindowType.WindowStaysOnTopHint
        self.assertTrue(window.windowFlags() & topmost)
        self.assertFalse(window.panel.windowFlags() & topmost)
        self.assertTrue(shield.windowFlags() & topmost)
        self.assertTrue(window.isVisible())
        self.assertTrue(shield.isVisible())

    def test_monitor_error_locks_screen_and_stops_repeating_dialogs(self):
        window = self.keep(LearningWindow(self.store, self.root))
        window.hide_screen()
        window.timer.start()
        with patch.object(self.store, "remaining", side_effect=sqlite3.DatabaseError("test error")), \
                patch("kidsroom.app.QMessageBox.warning") as message, \
                self.assertLogs("kidsroom.app", level="ERROR"):
            window.tick()
        self.assertTrue(window.isVisible())
        self.assertFalse(window.timer.isActive())
        message.assert_called_once()

    def test_only_current_recognition_worker_can_grant_reward(self):
        self.store.configure({"typing_exe": "typing.exe", "typing_template": "sample.png"})
        window = self.keep(LearningWindow(self.store, self.root))
        old = VisionWorker("unused.exe", "unused.png", 0.9)
        current = VisionWorker("unused.exe", "unused.png", 0.9)
        old.completed.connect(window.typing_completed)
        current.completed.connect(window.typing_completed)
        window.worker = current
        old.completed.emit()
        self.assertEqual(self.store.remaining(), 0)
        self.assertIs(window.worker, current)
        with patch.object(window.tray, "showMessage"):
            current.completed.emit()
        self.assertIsNone(window.worker)
        self.assertGreater(self.store.reward_time(), 895)
        self.assertEqual(self.store.remaining(), 0)
        old.deleteLater()

    def test_parent_can_save_daily_cap_and_see_existing_usage(self):
        self.store.submit(self.exercise_id, ["4"])
        dialog = self.keep(ParentDialog(None, self.store, self.root))
        dialog.daily_reward_limit.setValue(2)
        dialog.reward_minutes.setValue(9)
        with patch("kidsroom.widgets.QMessageBox.information"):
            dialog.save_reward_settings()
        self.assertEqual(self.store.settings()["daily_reward_limit"], 2)
        self.assertEqual(self.store.settings()["reward_minutes"], 9)
        self.assertFalse(dialog.typing_minutes.isEnabled())
        self.assertIn("9 phút", dialog.exercise_list.item(0).text())
        self.assertIn("1 / 2", dialog.reward_summary.text())
        reopened = self.keep(ParentDialog(None, self.store, self.root))
        reopened.resize(1024, 700)
        reopened.show()
        self.app.processEvents()
        self.assertLessEqual(reopened.height(), 700)
        self.assertEqual(reopened.daily_reward_limit.value(), 2)
        self.assertEqual(reopened.reward_minutes.value(), 9)
        window = self.keep(LearningWindow(self.store, self.root))
        window.refresh()
        self.assertIn("+9 phút", window.exercise_list.item(0).text())
        exercise = self.keep(ExerciseDialog(None, self.store, self.store.exercise(self.exercise_id)))
        self.assertTrue(any("Thưởng 9 phút" in label.text()
                            for label in exercise.findChildren(QLabel)))
        editor = self.keep(QuestionEditor(
            None, self.store.exercise(self.exercise_id), shared_reward=True
        ))
        self.assertFalse(editor.minutes.isEnabled())
        editor.save()
        self.assertEqual(editor.result_data["minutes"], 15)

    def test_child_must_attempt_other_exam_after_failing(self):
        second = self.store.save_exercise("English", "English", True, 15, self.questions)
        self.store.submit(self.exercise_id, ["wrong"])
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, ["4"])
        window = self.keep(LearningWindow(self.store, self.root))
        self.assertIn("Đã làm 2 lần", window.exercise_list.item(0).text())
        self.assertTrue(window.start_button.isEnabled())
        self.store.submit(second, ["wrong"])
        window.refresh()
        self.assertIn("Vòng 2", window.reward_summary.text())
        self.assertIn("Đã làm 0/2 lần", window.exercise_list.item(0).text())
        self.assertIn("Đã làm 0/2 lần", window.exercise_list.item(1).text())

    def test_midnight_resets_daily_limit_without_restarting_gui(self):
        now = 1_800_000_000
        self.store.configure({"daily_reward_limit": 1})
        self.store.submit(self.exercise_id, ["4"], now)
        with patch("kidsroom.core.time.time", return_value=now):
            window = self.keep(LearningWindow(self.store, self.root))
        self.assertFalse(window.start_button.isEnabled())
        with patch("kidsroom.core.time.time", return_value=now + 86400):
            window.tick()
        self.assertTrue(window.start_button.isEnabled())
        self.assertIn("0 / 1", window.reward_summary.text())


if __name__ == "__main__":
    unittest.main()
