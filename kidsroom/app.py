from __future__ import annotations

import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pywintypes
from PySide6.QtCore import QLockFile, QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QStyle,
    QSystemTrayIcon, QVBoxLayout, QWidget,
)

from kidsroom.core import MAX_EXERCISE_ATTEMPTS, Store
from kidsroom.exams import BUNDLED_EXAMS
from kidsroom.runtime import external_dll_search
from kidsroom.theme import apply_theme
from kidsroom.vision import VisionWorker, foreground_region, load_template
from kidsroom.widgets import (
    ExerciseDialog, ParentDialog, button, guarded, new_password,
)


LOG = logging.getLogger(__name__)
WINDOW_FLAGS = (
    Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint
)


class Shield(QWidget):
    def __init__(self):
        super().__init__(None, WINDOW_FLAGS)
        layout = QVBoxLayout(self)
        label = QLabel("Kidsroom\nHãy làm bài trên màn hình chính để nhận thời gian thưởng.")
        label.setObjectName("sectionTitle")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def closeEvent(self, event):
        event.ignore()


class StatusPanel(QWidget):
    def __init__(self, owner):
        super().__init__(None, Qt.WindowType.Window)
        self.owner = owner
        self.setWindowTitle("Kidsroom")
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        row = QHBoxLayout()
        button("Cha mẹ", owner.open_parent, row)
        button("Quay lại màn hình học", owner.return_to_learning, row)
        layout.addLayout(row)
        self.resize(480, 170)

    def closeEvent(self, event):
        if self.owner.parent_open:
            event.ignore()
            return
        self.owner.return_to_learning()
        event.accept()


class LearningWindow(QMainWindow):
    def __init__(self, store: Store, data_dir: Path):
        super().__init__(None, WINDOW_FLAGS)
        self.store = store
        self.data_dir = data_dir
        self.worker = None
        self.typing_process = None
        self.typing_executable = ""
        self.parent_open = False
        self.shutting_down = False
        self.using_reward_time = False
        self.shields = []
        self.setWindowTitle("Kidsroom")
        content = QWidget()
        content.setObjectName("learningPage")
        self.setCentralWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        top = QHBoxLayout()
        brand = QLabel("KIDSROOM  /  GÓC HỌC TẬP")
        brand.setObjectName("eyebrow")
        top.addWidget(brand)
        top.addStretch()
        button("Cha mẹ · Quản lý", self.open_parent, top)
        layout.addLayout(top)
        hero = QWidget()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 22, 28, 22)
        hero_layout.setSpacing(10)
        heading = QLabel("Học một chút, khám phá thật nhiều")
        heading.setObjectName("heading")
        heading.setWordWrap(True)
        hero_layout.addWidget(heading)
        intro = QLabel(
            "Chọn một nhiệm vụ em thích và hoàn thành để nhận thời gian sử dụng máy tính.\n"
            "Mỗi đề có tối đa 2 lượt nộp trong một vòng; chưa đạt 50% thì hãy chọn đề khác. "
            "Câu tự luận cần để đạt 50% sẽ được cha mẹ duyệt."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        hero_layout.addWidget(intro)
        layout.addWidget(hero)
        self.current_reward_label = QLabel()
        self.current_reward_label.setObjectName("rewardSummary")
        self.current_reward_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_reward_label)
        self.reward_summary = QLabel()
        self.reward_summary.setObjectName("rewardSummary")
        self.reward_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.reward_summary)
        section = QLabel("Nhiệm vụ hôm nay")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)
        self.message = QLabel()
        self.message.setObjectName("hint")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message)
        self.exercise_list = QListWidget()
        self.exercise_list.setObjectName("missions")
        self.exercise_list.setWordWrap(True)
        self.exercise_list.setSpacing(4)
        self.exercise_list.itemDoubleClicked.connect(lambda _: self.start_exercise())
        layout.addWidget(self.exercise_list, 1)
        actions = QHBoxLayout()
        self.start_button = button("Bắt đầu nhiệm vụ", self.start_exercise, actions)
        self.start_button.setObjectName("primary")
        self.use_computer_button = button("Sử dụng máy tính", self.use_computer, actions)
        self.typing_button = button("Luyện đánh máy", self.start_typing, actions)
        self.cancel_typing_button = button("Dừng bài đánh máy", self.return_to_learning, actions)
        layout.addLayout(actions)
        self.panel = StatusPanel(self)
        self.tray = QSystemTrayIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self
        )
        menu = QMenu(self)
        manage_action = QAction("Quản lý của cha mẹ", self)
        manage_action.triggered.connect(self.open_parent)
        menu.addAction(manage_action)
        lock_action = QAction("Quay lại màn hình học", self)
        lock_action.triggered.connect(self.return_to_learning)
        menu.addAction(lock_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Kidsroom")
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        app = QApplication.instance()
        app.screenAdded.connect(self.screen_added)
        app.screenRemoved.connect(self.rebuild_shields)
        app.primaryScreenChanged.connect(self.rebuild_shields)
        for screen in app.screens():
            screen.geometryChanged.connect(self.rebuild_shields)
        self.rebuild_shields()
        self.refresh()

    def screen_added(self, screen):
        screen.geometryChanged.connect(self.rebuild_shields)
        self.rebuild_shields()

    def rebuild_shields(self, *_):
        was_visible = self.isVisible()
        for shield in self.shields:
            shield.hide()
            shield.deleteLater()
        self.shields = []
        app = QApplication.instance()
        primary = app.primaryScreen()
        self.setGeometry(primary.geometry())
        for screen in app.screens():
            if screen is primary:
                continue
            shield = Shield()
            shield.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, not self.parent_open)
            shield.setGeometry(screen.geometry())
            if was_visible:
                shield.show()
            self.shields.append(shield)

    def set_topmost(self, enabled: bool):
        windows = [self, *self.shields]
        for window in windows:
            window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)

    def begin(self):
        self.lock_screen()
        if not self.store.get("password"):
            QTimer.singleShot(0, self.setup_password)
        else:
            self.timer.start()
            self.tick()

    @guarded
    def setup_password(self):
        QMessageBox.information(
            self, "Thiết lập lần đầu",
            "Cha mẹ hãy đặt mật khẩu và thêm đề bài/phần mềm đánh máy.\n"
            "Chỉ hoàn tất thiết lập khi cha mẹ đang trực tiếp sử dụng máy.",
        )
        password = new_password(self)
        if password is None:
            self.shutdown()
            return
        self.store.set_password(password)
        self.timer.start()
        self.open_parent()

    def refresh(self):
        selected = self.exercise_list.currentRow()
        self.progress_day = self.store.day(time.time())
        progress = self.store.reward_progress()
        reward_time = self.store.reward_time()
        self.update_reward_display(reward_time)
        self.reward_summary.setText(
            f"Lượt thưởng hôm nay: {progress['used']} / {progress['limit']}  ·  Vòng {progress['round']}"
        )
        self.exercises = self.store.exercises(True)
        self.exercise_list.clear()
        for exercise in self.exercises:
            task = progress["tasks"][f"exercise:{exercise['id']}"]
            if task["reason"]:
                state = (
                    "Hết lượt hôm nay" if progress["used"] >= progress["limit"]
                    else f"Đã làm {MAX_EXERCISE_ATTEMPTS} lần · Hãy chọn đề khác"
                )
            elif task["pending"]:
                state = (
                    f"Chờ cha mẹ duyệt · Đã làm "
                    f"{task['attempts']}/{MAX_EXERCISE_ATTEMPTS} lần"
                )
            else:
                state = (
                    f"+{self.store.reward_minutes(exercise['minutes'])} phút"
                    f" · Đã làm {task['attempts']}/{MAX_EXERCISE_ATTEMPTS} lần"
                )
            self.exercise_list.addItem(f"{exercise['title']}\n{exercise['subject']}  ·  {state}")
        if self.exercises:
            self.exercise_list.setCurrentRow(max(0, min(selected, len(self.exercises) - 1)))
        if reward_time:
            self.message.setText(
                "Em đang có thời gian thưởng. Bấm 'Sử dụng máy tính' để bắt đầu dùng nhé!"
            )
        else:
            self.message.setText(
                "Chọn một nhiệm vụ bên dưới để bắt đầu nhé!" if self.exercises else
                "Chưa có đề bài hiển thị. Hãy nhờ cha mẹ thêm đề trong phần Quản lý."
            )
        self.typing_button.setText(
            "Quay lại bài đánh máy" if self.worker else "Luyện đánh máy"
        )
        typing = progress["tasks"].get("typing")
        if not self.worker and typing:
            if typing["reason"]:
                state = "Hết lượt hôm nay" if progress["used"] >= progress["limit"] else "Chờ vòng sau"
                self.typing_button.setText(f"Đánh máy · {state}")
        self.typing_button.setEnabled(
            self.worker is not None or (typing is not None and not typing["reason"])
        )
        self.start_button.setEnabled(any(
            not task["reason"] and not task["pending"]
            for name, task in progress["tasks"].items() if name.startswith("exercise:")
        ))
        if progress["used"] >= progress["limit"] and not reward_time:
            self.message.setText("Đã hết lượt thưởng hôm nay. Hẹn em ngày mai!")
        self.cancel_typing_button.setEnabled(self.worker is not None)

    def update_reward_display(self, seconds: int | None = None):
        seconds = self.store.reward_time() if seconds is None else seconds
        self.current_reward_label.setText(
            f"Thời gian thưởng hiện tại: {seconds // 60:02d}:{seconds % 60:02d}"
        )

    def lock_screen(self):
        self.panel.hide()
        for shield in self.shields:
            if shield.isMinimized():
                shield.showNormal()
            else:
                shield.show()
        if self.isMinimized():
            self.showNormal()
            self.raise_()
            self.activateWindow()
        elif not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()

    def hide_screen(self):
        self.hide()
        for shield in self.shields:
            shield.hide()
        self.panel.show()

    def tick(self):
        if self.parent_open or self.shutting_down:
            return
        try:
            if self.progress_day != self.store.day(time.time()):
                self.refresh()
            remaining = self.store.remaining()
            self.update_reward_display(self.store.reward_time())
            if remaining and self.using_reward_time:
                self.hide_screen()
                self.panel.label.setText(
                    f"Giờ khám phá của em! Còn {remaining // 60:02d}:{remaining % 60:02d}."
                )
            elif self.worker:
                # Switching away from typing restores the learning screen.
                if foreground_region(self.typing_executable) is not None:
                    self.hide_screen()
                else:
                    self.lock_screen()
                    self.message.setText("Hãy bấm 'Quay lại bài đánh máy' để tiếp tục.")
            else:
                was_using_reward_time = self.using_reward_time
                self.using_reward_time = False
                self.lock_screen()
                if was_using_reward_time:
                    self.message.setText(
                        "Em đã dùng hết thời gian thưởng. Hãy làm bài tập để có thời gian thưởng."
                    )
            if not self.timer.isActive():
                self.timer.start()
        except (ValueError, OSError, sqlite3.Error, pywintypes.error, RuntimeError) as error:
            self.timer.stop()
            self.lock_screen()
            LOG.exception("Screen-time monitoring failed")
            QMessageBox.warning(
                self, "Lỗi theo dõi thời gian",
                f"{error}\nMàn hình học được giữ lại. Hãy vào Quản lý để kiểm tra và thử lại.",
            )

    @guarded
    def start_exercise(self):
        if not self.store.get("password"):
            self.setup_password()
            return
        self.stop_worker()
        index = self.exercise_list.currentRow()
        if index < 0:
            raise ValueError("Chưa chọn đề bài. Cha mẹ có thể thêm đề trong Quản lý.")
        exercise = self.exercises[index]
        self.store.require_reward(f"exercise:{exercise['id']}")
        dialog = ExerciseDialog(self, self.store, exercise)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.outcome["status"] == "rewarded":
                self.announce_reward(dialog.outcome["minutes"])
        self.refresh()
        self.tick()

    @guarded
    def use_computer(self):
        seconds = self.store.start_reward_time()
        if not seconds:
            QMessageBox.information(
                self, "Không còn thời gian thưởng",
                "Em không còn thời gian thưởng. Hãy làm bài tập để có thời gian thưởng.",
            )
            return
        self.using_reward_time = True
        self.panel.label.setText(
            f"Giờ khám phá của em! Còn {seconds // 60:02d}:{seconds % 60:02d}."
        )
        self.update_reward_display(self.store.reward_time())
        self.hide_screen()
        if not self.timer.isActive():
            self.timer.start()

    @guarded
    def start_typing(self):
        if not self.store.get("password"):
            self.setup_password()
            return
        if self.worker:
            self.focus_typing()
            return
        self.store.require_reward("typing")
        settings = self.store.settings()
        executable = Path(settings["typing_exe"])
        if not settings["typing_exe"] or not executable.is_file():
            raise ValueError("Cha mẹ cần cấu hình phần mềm đánh máy trước.")
        load_template(settings["typing_template"])
        self.typing_executable = str(executable)
        with external_dll_search() as environment:
            self.typing_process = subprocess.Popen(
                [str(executable)], cwd=str(executable.parent), env=environment
            )
        worker = VisionWorker(str(executable), settings["typing_template"],
                              settings["match_threshold"])
        worker.completed.connect(self.typing_completed)
        worker.failed.connect(self.typing_failed)
        worker.progress.connect(self.panel.label.setText)
        self.worker = worker
        worker.start()
        self.refresh()
        self.hide_screen()
        self.panel.label.setText("Đang mở phần mềm đánh máy...")

    def focus_typing(self):
        import win32con
        import win32gui
        import win32process

        candidates = []

        def find(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if self.typing_process and pid == self.typing_process.pid:
                    candidates.append(hwnd)
        win32gui.EnumWindows(find, None)
        if not candidates:
            raise ValueError("Không tìm thấy cửa sổ. Hãy quay lại màn hình học và mở bài lại; "
                             "cần chọn .exe thực sự, không phải launcher.")
        self.hide_screen()
        win32gui.ShowWindow(candidates[0], win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(candidates[0])

    def stop_worker(self):
        if self.worker:
            worker = self.worker
            worker.requestInterruption()
            if not worker.wait(10_000):
                raise RuntimeError("Bộ nhận diện chưa dừng được. Hãy thử lại sau.")
            self.worker = None
            worker.deleteLater()
        self.typing_process = None

    @guarded
    def typing_completed(self):
        if self.worker is None or self.sender() is not self.worker:
            return
        self.stop_worker()
        minutes = self.store.reward_typing()
        self.announce_reward(minutes)
        self.refresh()
        self.tick()

    @guarded
    def typing_failed(self, error):
        if self.worker is None or self.sender() is not self.worker:
            return
        LOG.error("Image detection failed: %s", error)
        self.stop_worker()
        self.lock_screen()
        QMessageBox.warning(self, "Lỗi nhận diện", error + "\nChưa cấp thời gian thưởng.")
        self.refresh()
        self.tick()

    def announce_reward(self, minutes):
        self.lock_screen()
        remaining = self.store.reward_time()
        self.update_reward_display(remaining)
        self.message.setText(
            f"Chúc mừng! Em được thưởng thêm {minutes} phút. "
            "Bấm 'Sử dụng máy tính' để bắt đầu dùng thời gian thưởng."
        )
        self.tray.showMessage("Hoàn thành bài tập", f"Em được thưởng thêm {minutes} phút!",
                              QSystemTrayIcon.MessageIcon.Information, 6000)

    @guarded
    def return_to_learning(self):
        if self.parent_open:
            return
        self.stop_worker()
        self.using_reward_time = False
        paused = self.store.pause_reward_time()
        self.lock_screen()
        self.refresh()
        if paused:
            self.message.setText(
                f"Đã dừng đếm giờ khám phá. Còn {paused // 60:02d}:{paused % 60:02d}; "
                "thời gian này sẽ được cộng vào lần thưởng tiếp theo khi em hoàn thành đề."
            )

    @guarded
    def open_parent(self):
        if self.parent_open:
            return
        if not self.store.get("password"):
            self.setup_password()
            return
        self.parent_open = True
        try:
            self.lock_screen()
            password, accepted = QInputDialog.getText(
                self, "Cha mẹ", "Mật khẩu quản lý:", QLineEdit.EchoMode.Password
            )
            if not accepted:
                return
            if not self.store.authenticate(password):
                raise ValueError("Mật khẩu không đúng. Sai 5 lần sẽ tạm khóa 60 giây.")
            self.set_topmost(False)
            self.hide()
            self.panel.hide()
            for shield in self.shields:
                shield.hide()
            self.stop_worker()
            dialog = ParentDialog(self, self.store, self.data_dir)
            dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            dialog.exec()
            if dialog.exit_requested:
                self.shutdown()
        finally:
            self.parent_open = False
            if not self.shutting_down:
                self.set_topmost(True)
                self.refresh()
                self.tick()

    def shutdown(self):
        self.stop_worker()
        self.shutting_down = True
        self.timer.stop()
        self.tray.hide()
        self.panel.hide()
        for shield in self.shields:
            shield.hide()
            shield.close()
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def closeEvent(self, event):
        if self.shutting_down:
            event.accept()
        else:
            event.ignore()


def main():
    if sys.platform != "win32":
        raise SystemExit("Kidsroom yêu cầu Windows 10 trở lên.")
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kidsroom.Learning")
    data_dir = Path(os.environ["LOCALAPPDATA"]) / "Kidsroom"
    data_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(data_dir / "app.log", maxBytes=1_000_000,
                                  backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("Kidsroom")
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)

    def report_error(error_type, error, traceback):
        LOG.critical("Unhandled application error", exc_info=(error_type, error, traceback))
        QMessageBox.critical(None, "Kidsroom - Lỗi", f"{error_type.__name__}: {error}")
    sys.excepthook = report_error
    lock = QLockFile(str(data_dir / "agent.lock"))
    lock.setStaleLockTime(0)
    # A service-launched agent may wait behind a manually started copy.
    # It takes over if that copy exits, instead of creating duplicate windows.
    waiting_logged = False
    while not lock.tryLock(0):
        if lock.error() != QLockFile.LockError.LockFailedError:
            QMessageBox.critical(None, "Kidsroom", "Không thể tạo khóa phiên trong thư mục dữ liệu.")
            return
        if not waiting_logged:
            LOG.info("Another GUI owns this user session; waiting for its lock.")
            waiting_logged = True
        time.sleep(2)
    store = None
    try:
        store = Store(data_dir / "data.sqlite3")
        try:
            imported = store.seed_exams(BUNDLED_EXAMS)
            if imported:
                LOG.info("Imported %d bundled exams.", len(imported))
        except (ValueError, sqlite3.Error):
            LOG.exception("Could not import bundled exams.")
        window = LearningWindow(store, data_dir)
        window.begin()
        app.exec()
        window.stop_worker()
    finally:
        if store:
            store.close()
        lock.unlock()


if __name__ == "__main__":
    main()
