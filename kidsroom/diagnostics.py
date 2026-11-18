"""Opt-in deployment check that never uses the real desktop or user database."""

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import traceback


def self_test(report_path: str) -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    report = {"status": "failed", "frozen": bool(getattr(sys, "frozen", False))}
    try:
        import cv2
        import mss
        import numpy as np
        import win32api
        import win32gui
        import win32process
        from PySide6.QtWidgets import QApplication

        from kidsroom.app import LearningWindow
        from kidsroom.core import Store
        from kidsroom.runtime import external_dll_search
        from kidsroom.theme import apply_theme
        from kidsroom.vision import CompletionGate, match_score
        from kidsroom.widgets import ParentDialog, QuestionEditor

        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        apply_theme(app)
        with tempfile.TemporaryDirectory(prefix="Kidsroom-check-") as directory:
            root = Path(directory)
            store = Store(root / "test.sqlite3")
            try:
                store.set_password("diagnostic-only-password")
                if not store.authenticate("diagnostic-only-password"):
                    raise RuntimeError("Password authentication failed.")
                exercise = store.save_exercise("Check", "Math", True, 1, [
                    {"kind": "short", "prompt": "2 + 2?", "accepted": ["4"]},
                ])
                store.configure({"daily_reward_limit": 1})
                store.submit(exercise, ["4"])
                if store.reward_progress()["used"] != 1 or store.reward_time() < 55:
                    raise RuntimeError("Reward persistence check failed.")
                window = LearningWindow(store, root)
                parent = ParentDialog(window, store, root)
                editor = QuestionEditor(parent, store.exercise(exercise))
                if not parent.daily_reward_limit.value() == 1 or window.start_button.isEnabled():
                    raise RuntimeError("Qt widget and daily-limit check failed.")
                rng = np.random.default_rng(42)
                frame = rng.integers(0, 256, (100, 120), dtype=np.uint8)
                if match_score(frame, frame[10:30, 20:50].copy()) < 0.99:
                    raise RuntimeError("OpenCV template matching check failed.")
                gate = CompletionGate(0.9)
                if any(gate.observe(score) for score in [0.0, 1.0, 1.0]):
                    raise RuntimeError("Premature recognition.")
                if not gate.observe(1.0):
                    raise RuntimeError("Completion recognition failed.")
                with external_dll_search():
                    pass
                editor.hide()
                parent.hide()
                window.tray.hide()
                window.timer.stop()
                window.panel.hide()
                for shield in window.shields:
                    shield.hide()
                app.processEvents()
                report.update({
                    "status": "passed", "python": sys.version.split()[0],
                    "opencv": cv2.__version__, "mss": mss.__version__,
                    "checks": ["Qt offscreen widgets", "SQLite rewards", "password hashing",
                               "daily reward cap", "OpenCV", "Windows imports", "DLL search reset"],
                })
            finally:
                store.close()
    except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error):
        report["error"] = traceback.format_exc()
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["status"] == "passed" else 1
