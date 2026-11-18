from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path

import cv2
import mss
import numpy as np
from PySide6.QtCore import QThread, Signal


def load_template(path: str) -> np.ndarray:
    data = np.frombuffer(Path(path).read_bytes(), dtype=np.uint8)
    if not data.size:
        raise ValueError("Ảnh mẫu rỗng.")
    image = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Không đọc được ảnh mẫu. Hãy dùng PNG hoặc JPG.")
    if min(image.shape) < 12 or image.size > 8_000_000 or image.std() < 5:
        raise ValueError("Ảnh mẫu cần ít nhất 12×12 pixel, có chi tiết và không quá 8 triệu pixel.")
    return image


def match_score(frame: np.ndarray, template: np.ndarray) -> float:
    if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
        return 0.0
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    score = float(cv2.minMaxLoc(result)[1])
    return score if math.isfinite(score) else 0.0


class CompletionGate:
    """Require an absent-to-present transition, then three stable samples."""

    def __init__(self, threshold: float):
        self.threshold = threshold
        self.saw_absent = False
        self.hits = 0

    def observe(self, score: float | None) -> bool:
        if score is None:
            self.hits = 0
            return False
        if score < self.threshold:
            self.saw_absent = True
            self.hits = 0
        else:
            self.hits += 1
        return self.saw_absent and self.hits >= 3


def foreground_region(executable: str) -> dict | None:
    import win32api
    import win32con
    import win32gui
    import win32process

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd or win32gui.IsIconic(hwnd):
        return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.c_ulong(len(buffer))
        query = ctypes.windll.kernel32.QueryFullProcessImageNameW
        query.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
                          ctypes.POINTER(ctypes.c_ulong)]
        query.restype = ctypes.c_int
        if not query(int(handle), 0, buffer, ctypes.byref(length)):
            raise ctypes.WinError()
        if os.path.normcase(os.path.realpath(buffer.value)) != os.path.normcase(
            os.path.realpath(executable)
        ):
            return None
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        x, y = win32gui.ClientToScreen(hwnd, (left, top))
        return {"left": x, "top": y, "width": right - left, "height": bottom - top}
    finally:
        handle.Close()


class VisionWorker(QThread):
    completed = Signal()
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, executable: str, template_path: str, threshold: float):
        super().__init__()
        self.executable = executable
        self.template_path = template_path
        self.threshold = threshold

    def run(self):
        # All capture objects belong to this worker thread, never the Qt UI thread.
        try:
            template = load_template(self.template_path)
            gate = CompletionGate(self.threshold)
            with mss.mss() as capture:
                while not self.isInterruptionRequested():
                    region = foreground_region(self.executable)
                    if not region or region["width"] <= 0 or region["height"] <= 0:
                        gate.observe(None)
                        self.progress.emit("Hãy chuyển sang cửa sổ phần mềm đánh máy.")
                    else:
                        desktop = capture.monitors[0]
                        left = max(region["left"], desktop["left"])
                        top = max(region["top"], desktop["top"])
                        right = min(region["left"] + region["width"],
                                    desktop["left"] + desktop["width"])
                        bottom = min(region["top"] + region["height"],
                                     desktop["top"] + desktop["height"])
                        if right <= left or bottom <= top:
                            gate.observe(None)
                            self.msleep(800)
                            continue
                        frame = np.array(capture.grab(
                            {"left": left, "top": top, "width": right - left, "height": bottom - top}
                        ))
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                        if gate.observe(match_score(gray, template)):
                            self.completed.emit()
                            return
                        self.progress.emit(
                            "Đang theo dõi kết quả bài tập."
                            if gate.saw_absent else
                            "Hãy bắt đầu bài mới để màn hình kết quả cũ biến mất trước."
                        )
                    self.msleep(800)
        except Exception as error:
            # A worker cannot propagate to the UI; the receiver logs and displays the failure.
            self.failed.emit(f"{type(error).__name__}: {error}")
