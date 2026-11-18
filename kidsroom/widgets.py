from __future__ import annotations

from functools import wraps
import hashlib
import logging
from pathlib import Path
import shutil
import sqlite3
import sys

import cv2
import pywintypes
import win32api
import win32con
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)

from kidsroom.core import MAX_EXERCISE_ATTEMPTS, Store, validate_questions
from kidsroom.vision import load_template


LOG = logging.getLogger(__name__)


def guarded(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except (ValueError, OSError, sqlite3.Error, cv2.error, pywintypes.error, RuntimeError) as error:
            LOG.exception("User action failed: %s", function.__name__)
            QMessageBox.warning(self, "Không thể thực hiện", str(error))
    return wrapped


def button(text, callback, layout):
    result = QPushButton(text)
    result.clicked.connect(callback)
    layout.addWidget(result)
    return result


def minute_spin(value=15):
    result = QSpinBox()
    result.setRange(1, 240)
    result.setSuffix(" phút")
    result.setValue(value)
    return result


class QuestionEditor(QDialog):
    def __init__(self, parent, exercise=None, *, shared_reward=False):
        super().__init__(parent)
        self.setWindowTitle("Biên soạn đề bài")
        self.resize(1000, 700)
        self.result_data = None
        self.questions = [dict(q) for q in exercise["questions"]] if exercise else []
        self.selected = -1
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        heading = QLabel("Thiết kế nhiệm vụ học tập")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        form = QFormLayout()
        self.title_edit = QLineEdit(exercise["title"] if exercise else "")
        self.subject_edit = QLineEdit(exercise["subject"] if exercise else "")
        self.minutes = minute_spin(exercise["minutes"] if exercise else 15)
        self.minutes.setEnabled(not shared_reward)
        if shared_reward:
            self.minutes.setToolTip("Đang sử dụng thời gian thưởng chung.")
        self.visible = QCheckBox("Hiển thị cho con")
        self.visible.setChecked(exercise["visible"] if exercise else True)
        self.title_edit.setPlaceholderText("Ví dụ: Khám phá phân số")
        self.subject_edit.setPlaceholderText("Ví dụ: Toán 6")
        form.addRow("Tên đề", self.title_edit)
        form.addRow("Môn học", self.subject_edit)
        form.addRow("Thưởng riêng của đề" if not shared_reward else
                    "Thưởng riêng (đang dùng mức chung)", self.minutes)
        form.addRow(self.visible)
        layout.addLayout(form)
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.question_list = QListWidget()
        left.addWidget(self.question_list)
        button("Thêm câu", self.add_question, left)
        button("Xóa câu đang chọn", self.remove_question, left).setObjectName("danger")
        body.addLayout(left, 1)
        fields = QWidget()
        right = QFormLayout(fields)
        self.kind = QComboBox()
        self.kind.addItem("Trắc nghiệm", "choice")
        self.kind.addItem("Trả lời ngắn", "short")
        self.kind.addItem("Tự luận · cha mẹ duyệt", "essay")
        self.prompt = QTextEdit()
        self.choices = QTextEdit()
        self.choices.setPlaceholderText("Mỗi lựa chọn một dòng (2–10 dòng)")
        self.correct = QSpinBox()
        self.correct.setRange(1, 10)
        self.accepted = QTextEdit()
        self.accepted.setPlaceholderText("Mỗi đáp án chấp nhận một dòng; không phân biệt hoa thường.")
        self.solution = QTextEdit()
        self.solution.setPlaceholderText(
            "Lời giải / đáp án mẫu (tùy chọn). Chỉ cha mẹ thấy khi duyệt bài, con không thấy."
        )
        right.addRow("Loại câu hỏi", self.kind)
        right.addRow("Nội dung", self.prompt)
        right.addRow("Lựa chọn (trắc nghiệm)", self.choices)
        right.addRow("Số thứ tự đáp án đúng", self.correct)
        right.addRow("Đáp án (trả lời ngắn)", self.accepted)
        right.addRow("Lời giải (tùy chọn)", self.solution)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(fields)
        body.addWidget(scroll, 3)
        layout.addLayout(body)
        self.kind.currentIndexChanged.connect(self.update_fields)
        self.question_list.currentRowChanged.connect(self.select_question)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if not self.questions:
            self.questions.append({"kind": "short", "prompt": "", "accepted": []})
        self.rebuild_list(0)

    def update_fields(self):
        kind = self.kind.currentData()
        self.choices.setEnabled(kind == "choice")
        self.correct.setEnabled(kind == "choice")
        self.accepted.setEnabled(kind == "short")

    def collect_current(self):
        if self.selected < 0:
            return
        question = {"kind": self.kind.currentData(), "prompt": self.prompt.toPlainText().strip()}
        if question["kind"] == "choice":
            question["choices"] = self.choices.toPlainText().splitlines()
            question["correct"] = self.correct.value() - 1
        elif question["kind"] == "short":
            question["accepted"] = self.accepted.toPlainText().splitlines()
        solution = self.solution.toPlainText().strip()
        if solution:
            question["solution"] = solution
        self.questions[self.selected] = question

    def select_question(self, index):
        self.collect_current()
        self.selected = index
        if index < 0:
            return
        question = self.questions[index]
        self.kind.setCurrentIndex(self.kind.findData(question["kind"]))
        self.prompt.setPlainText(question["prompt"])
        self.choices.setPlainText("\n".join(question.get("choices", [])))
        self.correct.setValue(question.get("correct", 0) + 1)
        self.accepted.setPlainText("\n".join(question.get("accepted", [])))
        self.solution.setPlainText(question.get("solution", ""))
        self.update_fields()

    def rebuild_list(self, index):
        self.selected = -1
        self.question_list.blockSignals(True)
        self.question_list.clear()
        self.question_list.addItems([f"Câu {i + 1}" for i in range(len(self.questions))])
        self.question_list.blockSignals(False)
        self.question_list.setCurrentRow(index)

    def add_question(self):
        self.collect_current()
        self.questions.append({"kind": "short", "prompt": "", "accepted": []})
        self.rebuild_list(len(self.questions) - 1)

    @guarded
    def remove_question(self):
        if len(self.questions) <= 1:
            raise ValueError("Đề bài phải có ít nhất một câu.")
        index = self.question_list.currentRow()
        if index < 0:
            raise ValueError("Hãy chọn câu hỏi.")
        self.questions.pop(index)
        self.rebuild_list(min(index, len(self.questions) - 1))

    @guarded
    def save(self):
        self.collect_current()
        if not self.title_edit.text().strip():
            raise ValueError("Cần nhập tên đề bài.")
        validate_questions(self.questions)
        self.result_data = {
            "title": self.title_edit.text(), "subject": self.subject_edit.text(),
            "visible": self.visible.isChecked(), "minutes": self.minutes.value(),
            "questions": self.questions,
        }
        self.accept()


class ExerciseDialog(QDialog):
    def __init__(self, parent, store: Store, exercise: dict):
        super().__init__(parent)
        self.setWindowTitle(exercise["title"])
        self.resize(850, 700)
        self.store = store
        self.exercise = exercise
        self.outcome = None
        self.inputs = []
        attempts = store.reward_progress()["tasks"][f"exercise:{exercise['id']}"]["attempts"]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        intro = QLabel(
            f"{exercise['title']} · Thưởng {store.reward_minutes(exercise['minutes'])} phút\n"
            f"Em còn {MAX_EXERCISE_ATTEMPTS - attempts} lần nộp đề này. "
            "Cần đúng ít nhất một nửa số câu để hoàn thành. Tự luận sẽ chờ cha mẹ duyệt."
        )
        intro.setObjectName("sectionTitle")
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(intro)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        questions_layout = QVBoxLayout(content)
        questions_layout.setSpacing(16)
        for index, question in enumerate(exercise["questions"]):
            card = QFrame()
            card.setObjectName("questionCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            card_layout.setSpacing(12)
            label = QLabel(f"Câu {index + 1}. {question['prompt']}")
            label.setStyleSheet("font-weight: 700;color: orange")
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            card_layout.addWidget(label)
            if question["kind"] == "choice":
                widget = QComboBox()
                widget.addItem("— Chọn đáp án —", -1)
                for number, choice in enumerate(question["choices"]):
                    widget.addItem(choice, number)
            elif question["kind"] == "short":
                widget = QLineEdit()
                widget.setPlaceholderText("Nhập câu trả lời của em...")
            else:
                widget = QTextEdit()
                widget.setPlaceholderText("Trình bày bài làm của em tại đây...")
                widget.setMaximumHeight(180)
            card_layout.addWidget(widget)
            questions_layout.addWidget(card)
            self.inputs.append(widget)
        questions_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        actions = QHBoxLayout()
        button("Nộp bài", self.submit, actions).setObjectName("primary")
        button("Quay lại", self.reject, actions)
        layout.addLayout(actions)

    @guarded
    def submit(self):
        answers = []
        for widget in self.inputs:
            if isinstance(widget, QComboBox):
                answers.append(widget.currentData())
            elif isinstance(widget, QLineEdit):
                answers.append(widget.text())
            else:
                answers.append(widget.toPlainText())
        outcome = self.store.submit(self.exercise["id"], answers)
        score = (
            f"Số câu được chấm tự động đúng: "
            f"{outcome['correct_count']}/{outcome['total_questions']} câu trong đề."
        )
        essay_note = (
            f" Em đã trả lời {outcome['essay_answered_count']} câu tự luận."
            if outcome["essay_answered_count"] else ""
        )
        if outcome["status"] == "incorrect":
            QMessageBox.information(
                self, "Chưa đạt 50%",
                f"{score}{essay_note}\nEm chưa được thưởng vì chưa đạt 50% tổng số câu. "
                "Hãy chọn đề khác để làm.",
            )
        elif outcome["status"] == "pending":
            QMessageBox.information(
                self, "Đã nộp bài",
                f"{score}{essay_note}\nBài có câu tự luận đang chờ cha mẹ duyệt; "
                "thời gian thưởng sẽ được cộng sau khi duyệt.",
            )
        else:
            QMessageBox.information(
                self, "Hoàn thành đề",
                f"{score}\nĐã đạt ngưỡng 50% bằng câu được chấm tự động, "
                "không cần cha mẹ duyệt. Em được thưởng thêm "
                f"{outcome['minutes']} phút.",
            )
        self.outcome = outcome
        self.accept()


class ExerciseTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["STT", "Hiển thị", "Môn học", "Tên đề bài", "Thời gian"])
        self.setShowGrid(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setHighlightSections(False)
        self.setColumnWidth(0, 55)
        self.setColumnWidth(1, 90)
        self.setColumnWidth(2, 120)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(4, 110)

    def item(self, row: int, column: int | None = None):
        if column is None:
            texts = []
            for col in range(self.columnCount()):
                cell = super().item(row, col)
                if cell:
                    texts.append(cell.text())
            return QTableWidgetItem(" | ".join(texts))
        return super().item(row, column)

    def setCurrentRow(self, row: int):
        if 0 <= row < self.rowCount():
            self.setCurrentCell(row, 0)
            self.selectRow(row)
        else:
            self.clearSelection()

    def clear(self):
        self.setRowCount(0)


class ParentDialog(QDialog):
    def __init__(self, parent, store: Store, data_dir: Path):
        super().__init__(parent)
        self.setWindowTitle("Quản lý của cha mẹ")
        self.resize(1000, 700)
        self.store = store
        self.data_dir = data_dir
        self.exit_requested = False
        self.submissions = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        heading = QLabel("Đồng hành cùng con")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        subtitle = QLabel("Quản lý nhiệm vụ, duyệt bài và xây dựng thói quen học tập mỗi ngày.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.build_reward_settings(tabs)
        self.build_settings(tabs)
        self.build_exercises(tabs)
        self.build_review(tabs)
        service_actions = QHBoxLayout()
        button(
            "Dừng Kidsroom Service (cần quyền quản trị)", self.stop_service, service_actions
        ).setObjectName("danger")
        service_actions.addStretch()
        layout.addLayout(service_actions)
        bottom = QHBoxLayout()
        button("Thu hồi thời gian thưởng", self.revoke, bottom).setObjectName("danger")
        button("Đổi mật khẩu", self.change_password, bottom)
        button("Đóng chương trình", self.close_application, bottom).setObjectName("danger")
        button("Đóng quản lý", self.accept, bottom).setObjectName("primary")
        layout.addLayout(bottom)
        self.refresh_exercises()
        self.refresh_pending()

    def build_reward_settings(self, tabs):
        page = QWidget()
        form = QFormLayout(page)
        self.daily_reward_limit = QSpinBox()
        self.daily_reward_limit.setRange(0, 100)
        settings = self.store.settings()
        self.daily_reward_limit.setValue(settings["daily_reward_limit"])
        self.daily_reward_limit.setSuffix(" lần / ngày")
        form.addRow("Tổng số lần thưởng tối đa", self.daily_reward_limit)
        self.reward_minutes = minute_spin(settings["reward_minutes"] or 15)
        form.addRow("Thời gian mỗi lần thưởng", self.reward_minutes)
        self.reward_summary = QLabel()
        self.reward_summary.setObjectName("rewardSummary")
        form.addRow("Hôm nay", self.reward_summary)
        notes = QLabel(
            "Giới hạn này tính chung cho tất cả môn học và bài đánh máy.\n"
            "Mỗi đề có tối đa 2 lượt nộp; bài dưới 50% phải chuyển sang đề khác.\n"
            "Hoàn thành 2 lượt ở mọi đề đang hiển thị sẽ bắt đầu vòng mới.\n"
            "Đề ẩn không tính vào vòng làm đề; bài đánh máy vẫn tính trong giới hạn thưởng chung.\n"
            "Nhấn Lưu để dùng cùng một thời gian thưởng cho mọi đề và bài đánh máy.\n"
            "Trước khi lưu lần đầu, mỗi đề và bài đánh máy vẫn dùng số phút riêng.\n"
            "Bài tự luận đã nộp giữ số phút tại thời điểm nộp.\n"
            "Đặt 0 lượt để không cấp thêm thưởng. Thay đổi không xóa lượt hay giờ đã cấp."
        )
        notes.setWordWrap(True)
        notes.setObjectName("hint")
        form.addRow(notes)
        save = QPushButton("Lưu thiết lập thưởng")
        save.setObjectName("primary")
        save.clicked.connect(self.save_reward_settings)
        form.addRow(save)
        tabs.addTab(page, "Thời gian và lượt thưởng")
        self.refresh_reward_summary()

    def refresh_reward_summary(self):
        progress = self.store.reward_progress()
        self.reward_summary.setText(
            f"Đã nhận {progress['used']} / {progress['limit']} lần · Vòng {progress['round']}."
        )

    @guarded
    def save_reward_settings(self):
        self.store.configure({
            "daily_reward_limit": self.daily_reward_limit.value(),
            "reward_minutes": self.reward_minutes.value(),
        })
        self.typing_minutes.setEnabled(False)
        self.refresh_exercises()
        self.refresh_reward_summary()
        QMessageBox.information(self, "Đã lưu", "Thiết lập thưởng đã được lưu.")

    def build_settings(self, tabs):
        page = QWidget()
        form = QFormLayout(page)
        settings = self.store.settings()
        self.exe = QLineEdit(settings["typing_exe"])
        exe_row = QHBoxLayout()
        exe_row.addWidget(self.exe)
        button("Chọn .exe", self.choose_exe, exe_row)
        form.addRow("Phần mềm đánh máy", exe_row)
        self.template = QLineEdit(settings["typing_template"])
        template_row = QHBoxLayout()
        template_row.addWidget(self.template)
        button("Chọn ảnh mẫu", self.choose_template, template_row)
        form.addRow("Ảnh nhận diện hoàn thành", template_row)
        self.typing_minutes = minute_spin(settings["typing_minutes"])
        self.typing_minutes.setEnabled(settings["reward_minutes"] is None)
        self.typing_minutes.setToolTip("Khi đã lưu mức thưởng chung, ô này không được áp dụng.")
        form.addRow("Thưởng riêng (nếu chưa đặt mức chung)", self.typing_minutes)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.7, 0.99)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(settings["match_threshold"])
        form.addRow("Ngưỡng khớp ảnh", self.threshold)
        notes = QLabel(
            "Cắt ảnh chỉ giữ thông báo hoàn thành đặc trưng, không gồm điểm số thay đổi.\n"
            "Giữ nguyên DPI/zoom. Chỉ nhận diện cửa sổ .exe được chọn đang ở phía trước.\n"
            "Ảnh kết quả phải biến mất rồi xuất hiện lại trong 3 lần quét liên tiếp.\n"
            "Đánh máy cũng tính vào giới hạn lượt thưởng và mỗi vòng bài tập.\n"
            "Dữ liệu lưu cục bộ; không chụp ảnh lưu trữ hay gửi dữ liệu lên mạng."
        )
        notes.setWordWrap(True)
        notes.setObjectName("hint")
        form.addRow(notes)
        save = QPushButton("Lưu cấu hình")
        save.setObjectName("primary")
        save.clicked.connect(self.save_settings)
        form.addRow(save)
        tabs.addTab(page, "Đánh máy")

    def choose_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn phần mềm đánh máy", "", "Windows (*.exe)")
        if path:
            self.exe.setText(path)

    def choose_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh hoàn thành", "",
                                             "Ảnh (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.template.setText(path)

    @guarded
    def save_settings(self):
        executable = self.exe.text().strip()
        template = self.template.text().strip()
        if bool(executable) != bool(template):
            raise ValueError("Cần chọn cả phần mềm và ảnh mẫu, hoặc để trống cả hai.")
        if executable:
            exe_path = Path(executable).resolve()
            if not exe_path.is_file() or exe_path.suffix.lower() != ".exe":
                raise ValueError("Hãy chọn tệp thực thi .exe hợp lệ.")
            executable = str(exe_path)
            load_template(template)
            source = Path(template).resolve()
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
            destination = self.data_dir / "templates" / f"{digest}{source.suffix.lower()}"
            destination.parent.mkdir(exist_ok=True)
            if source != destination:
                shutil.copyfile(source, destination)
            template = str(destination)
        self.store.configure({
            "typing_exe": executable, "typing_template": template,
            "typing_minutes": self.typing_minutes.value(), "match_threshold": self.threshold.value(),
        })
        self.exe.setText(executable)
        self.template.setText(template)
        self.refresh_reward_summary()
        QMessageBox.information(self, "Đã lưu", "Cấu hình đã được lưu.")

    def build_exercises(self, tabs):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.exercise_list = ExerciseTableWidget()
        self.exercise_list.cellDoubleClicked.connect(lambda row, col: self.edit_exercise())
        layout.addWidget(self.exercise_list, 1)
        actions = QHBoxLayout()
        button("Tạo đề", self.create_exercise, actions).setObjectName("primary")
        button("Sửa đề", self.edit_exercise, actions)
        button("Hiện / Ẩn đề", self.toggle_exercise, actions)
        button("Nhập đề từ JSON", self.import_exam, actions)
        button("Xuất đề ra JSON", self.export_exam, actions)
        layout.addLayout(actions)
        note = QLabel(
            "Đề thi là JSON gồm title, subject, minutes, visible và questions; "
            "mỗi câu có thể kèm lời giải (solution) để đối chiếu khi duyệt."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        layout.addWidget(note)

        paste_label = QLabel("Dán nội dung JSON đề thi:")
        layout.addWidget(paste_label)
        self.json_paste_box = QTextEdit()
        self.json_paste_box.setPlaceholderText(
            'Dán nội dung JSON đề thi tại đây (hỗ trợ cả đối tượng {...} hoặc danh sách [{...}, ...])...\n'
            'Ví dụ: {"title": "Đề 15 phút", "subject": "Toán 6", "minutes": 15, "visible": true, "questions": [...]}'
        )
        self.json_paste_box.setMaximumHeight(110)
        layout.addWidget(self.json_paste_box)

        paste_actions = QHBoxLayout()
        button("Thêm đề từ nội dung JSON", self.import_exam_from_text, paste_actions).setObjectName("primary")
        button("Xóa ô nhập JSON", self.json_paste_box.clear, paste_actions)
        paste_actions.addStretch()
        layout.addLayout(paste_actions)

        tabs.addTab(page, "Kho đề bài")

    def refresh_exercises(self):
        selected = self.exercise_list.currentRow()
        self.all_exercises = self.store.exercises()
        self.exercise_list.clear()
        self.exercise_list.setRowCount(len(self.all_exercises))
        for row, exercise in enumerate(self.all_exercises):
            stt_item = QTableWidgetItem(str(row + 1))
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.exercise_list.setItem(row, 0, stt_item)

            is_visible = exercise["visible"]
            vis_item = QTableWidgetItem("Hiện" if is_visible else "Ẩn")
            vis_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            vis_item.setForeground(QColor("#4eedc4") if is_visible else QColor("#8390a6"))
            self.exercise_list.setItem(row, 1, vis_item)

            subj_item = QTableWidgetItem(exercise["subject"])
            subj_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.exercise_list.setItem(row, 2, subj_item)

            title_item = QTableWidgetItem(exercise["title"])
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.exercise_list.setItem(row, 3, title_item)

            time_item = QTableWidgetItem(f"{self.store.reward_minutes(exercise['minutes'])} phút")
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.exercise_list.setItem(row, 4, time_item)

        if self.all_exercises:
            target_row = max(0, min(selected, len(self.all_exercises) - 1)) if selected >= 0 else 0
            self.exercise_list.setCurrentRow(target_row)
        self.refresh_reward_summary()

    def selected_exercise(self):
        index = self.exercise_list.currentRow()
        if index < 0 or index >= len(self.all_exercises):
            raise ValueError("Hãy chọn một đề bài.")
        return self.all_exercises[index]

    @guarded
    def create_exercise(self):
        dialog = QuestionEditor(self, shared_reward=self.store.settings()["reward_minutes"] is not None)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.save_exercise(**dialog.result_data)
            self.refresh_exercises()

    @guarded
    def edit_exercise(self):
        exercise = self.selected_exercise()
        dialog = QuestionEditor(
            self, exercise, shared_reward=self.store.settings()["reward_minutes"] is not None
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.save_exercise(**dialog.result_data, exercise_id=exercise["id"])
            self.refresh_exercises()

    @guarded
    def toggle_exercise(self):
        exercise = self.selected_exercise()
        self.store.set_visible(exercise["id"], not exercise["visible"])
        self.refresh_exercises()

    @guarded
    def import_exam(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn tệp đề thi", "", "Đề thi JSON (*.json)")
        if not path:
            return
        self.store.import_exam_file(Path(path))
        self.refresh_exercises()
        QMessageBox.information(self, "Đã nhập đề", "Đề thi đã được thêm vào kho đề bài.")

    @guarded
    def import_exam_from_text(self):
        text = self.json_paste_box.toPlainText().strip()
        if not text:
            raise ValueError("Hãy dán nội dung JSON của đề thi vào ô văn bản.")
        saved_ids = self.store.import_exam_json(text)
        self.refresh_exercises()
        self.json_paste_box.clear()
        QMessageBox.information(
            self, "Đã thêm đề",
            f"Đã thêm thành công {len(saved_ids)} đề thi từ nội dung JSON."
        )

    @guarded
    def export_exam(self):
        exercise = self.selected_exercise()
        filename = "".join(
            "_" if char in '<>:"/\\|?*' else char for char in exercise["title"]
        ).strip(" .") or "de-thi"
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất đề thi", f"{filename}.json", "Đề thi JSON (*.json)"
        )
        if not path:
            return
        if Path(path).suffix.lower() != ".json":
            path = f"{path}.json"
        self.store.export_exam_file(exercise["id"], Path(path))
        QMessageBox.information(self, "Đã xuất đề", "Đề thi đã được xuất ra tệp JSON.")

    def build_review(self, tabs):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.review_status = QLabel()
        self.review_status.setWordWrap(True)
        self.review_status.setObjectName("hint")
        layout.addWidget(self.review_status)
        self.pending_list = QListWidget()
        self.pending_list.currentRowChanged.connect(self.show_submission)
        self.pending_list.currentRowChanged.connect(self.update_review_actions)
        layout.addWidget(self.pending_list, 1)
        self.submission_text = QTextEdit()
        self.submission_text.setReadOnly(True)
        layout.addWidget(self.submission_text, 3)
        actions = QHBoxLayout()
        self.approve_review_button = button(
            "Duyệt bài và thưởng", lambda: self.review(True), actions
        )
        self.approve_review_button.setObjectName("primary")
        self.reject_review_button = button("Yêu cầu làm lại", lambda: self.review(False), actions)
        layout.addLayout(actions)
        tabs.addTab(page, "Duyệt bài")
        self.update_review_actions()

    def refresh_pending(self):
        self.submissions = self.store.pending()
        self.pending_list.clear()
        self.submission_text.clear()
        for submission in self.submissions:
            self.pending_list.addItem(f"{submission['day']} | {submission['title']}")
        if self.submissions:
            self.review_status.setText(
                f"Có {len(self.submissions)} bài đang chờ cha mẹ duyệt. "
                "Chọn một bài để xem câu trả lời và duyệt thưởng hoặc yêu cầu làm lại."
            )
        else:
            self.review_status.setText(
                "Chưa có bài chờ duyệt. Bài có câu tự luận sẽ xuất hiện tại đây nếu cần "
                "câu tự luận để đạt ngưỡng; nếu câu trắc nghiệm/trả lời ngắn đã đạt "
                "50%, bài được thưởng ngay mà không cần duyệt."
            )
        self.update_review_actions()

    def update_review_actions(self, *_):
        selected = 0 <= self.pending_list.currentRow() < len(self.submissions)
        self.approve_review_button.setEnabled(selected)
        self.reject_review_button.setEnabled(selected)

    def show_submission(self, index):
        if not 0 <= index < len(self.submissions):
            self.submission_text.clear()
            return
        submission = self.submissions[index]
        lines = []
        for number, (question, answer) in enumerate(zip(
            submission["questions"], submission["answers"]
        )):
            if question["kind"] == "choice":
                answer = question["choices"][answer]
            entry = f"Câu {number + 1}: {question['prompt']}\nTrả lời: {answer}\n"
            if question.get("solution"):
                entry += f"Lời giải gợi ý: {question['solution']}\n"
            lines.append(entry)
        self.submission_text.setPlainText("\n".join(lines))

    @guarded
    def review(self, approve):
        index = self.pending_list.currentRow()
        if index < 0:
            raise ValueError("Hãy chọn bài cần duyệt.")
        minutes = self.store.review(self.submissions[index]["id"], approve)
        self.refresh_pending()
        self.refresh_reward_summary()
        QMessageBox.information(
            self, "Đã duyệt", f"Đã cộng {minutes} phút." if approve else "Con có thể làm lại đề này."
        )

    @guarded
    def revoke(self):
        self.store.revoke_time()
        QMessageBox.information(self, "Đã thu hồi", "Thời gian thưởng đã được thu hồi.")

    @guarded
    def change_password(self):
        password = new_password(self)
        if password is not None:
            self.store.set_password(password)
            QMessageBox.information(self, "Đã lưu", "Mật khẩu đã được thay đổi.")

    @guarded
    def stop_service(self):
        if QMessageBox.question(
            self, "Dừng Kidsroom Service",
            "Windows sẽ yêu cầu quyền quản trị để dừng service và tắt toàn bộ chương trình Kidsroom.\n"
            "Tiếp tục?",
        ) != QMessageBox.StandardButton.Yes:
            return

        if getattr(sys, "frozen", False):
            executable = Path(sys.executable).with_name("KidsroomService.exe")
            arguments = "stop"
        else:
            executable = Path(sys.executable)
            if executable.name.casefold() == "pythonw.exe":
                executable = executable.with_name("python.exe")
            arguments = "-I -m kidsroom.service stop"
        if not executable.is_file():
            raise FileNotFoundError(f"Không tìm thấy chương trình điều khiển service: {executable}")

        result = win32api.ShellExecute(
            0, "runas", str(executable), arguments, str(executable.parent),
            win32con.SW_SHOWNORMAL,
        )
        if result <= 32:
            raise OSError(f"Windows không thể khởi chạy lệnh dừng service (mã lỗi {result}).")
        QMessageBox.information(
            self, "Đã gửi yêu cầu",
            "Windows đã mở lệnh dừng service với quyền quản trị.\n"
            "Chương trình Kidsroom sẽ đóng ngay bây giờ.",
        )
        self.exit_requested = True
        if self.parent() and hasattr(self.parent(), "shutdown"):
            self.parent().shutdown()
        self.accept()

    def close_application(self):
        if QMessageBox.question(
            self, "Đóng chương trình",
            "Bạn có chắc chắn muốn đóng hoàn toàn chương trình Kidsroom không?\n"
            "Tiến trình Kidsroom.exe sẽ bị đóng lại.",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.exit_requested = True
        if self.parent() and hasattr(self.parent(), "shutdown"):
            self.parent().shutdown()
        self.accept()

    def request_exit(self):
        self.close_application()


def new_password(parent) -> str | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Đặt mật khẩu cha mẹ")
    layout = QFormLayout(dialog)
    password = QLineEdit()
    confirm = QLineEdit()
    password.setEchoMode(QLineEdit.EchoMode.Password)
    confirm.setEchoMode(QLineEdit.EchoMode.Password)
    layout.addRow("Mật khẩu (ít nhất 8 ký tự)", password)
    layout.addRow("Nhập lại", confirm)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                               QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    if password.text() != confirm.text():
        raise ValueError("Hai mật khẩu không trùng nhau.")
    if len(password.text()) < 8:
        raise ValueError("Mật khẩu cần ít nhất 8 ký tự.")
    return password.text()
