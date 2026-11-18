from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import re
import secrets
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


DEFAULT_SETTINGS = {
    "typing_exe": "",
    "typing_template": "",
    "typing_minutes": 15,
    "match_threshold": 0.9,
    "daily_reward_limit": 4,
    "reward_minutes": None,
}
MAX_EXERCISE_ATTEMPTS = 2

SUPERSCRIPT_MAP = {
    # Digits
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    # Signs & symbols
    "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
    # Lowercase letters
    "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ",
    "f": "ᶠ", "g": "ᵍ", "h": "ʰ", "i": "ⁱ", "j": "ʲ",
    "k": "ᵏ", "l": "ˡ", "m": "ᵐ", "n": "ⁿ", "o": "ᵒ",
    "p": "ᵖ", "r": "ʳ", "s": "ˢ", "t": "ᵗ", "u": "ᵘ",
    "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ", "z": "ᶻ",
    # Uppercase letters
    "A": "ᴬ", "B": "ᴮ", "D": "ᴰ", "E": "ᴱ", "G": "ᴳ",
    "H": "ᴴ", "I": "ᴵ", "J": "ᴶ", "K": "ᴷ", "L": "ᴸ",
    "M": "ᴹ", "N": "ᴺ", "O": "ᴼ", "P": "ᴾ", "R": "ᴿ",
    "T": "ᵀ", "U": "ᵁ", "W": "ᵂ",
}

EXPONENT_PATTERN = re.compile(
    r"\s*\^\s*\{([^{}]+)\}|\s*\^\s*\(([^()]+)\)|\s*\^([+\-]?[0-9]+|[0-9]*[a-zA-Z]{1,3})(?![0-9a-zA-Z])"
)


def to_superscript(text: str) -> str | None:
    chars = []
    for ch in text:
        if ch.isspace():
            continue
        if ch not in SUPERSCRIPT_MAP:
            return None
        chars.append(SUPERSCRIPT_MAP[ch])
    return "".join(chars) if chars else None


def replace_superscripts(text: str) -> str:
    if not isinstance(text, str) or "^" not in text:
        return text

    def _sub(match: re.Match) -> str:
        content = match.group(1) or match.group(2) or match.group(3)
        if not content:
            return match.group(0)
        converted = to_superscript(content)
        if converted is None:
            return match.group(0)
        return converted

    return EXPONENT_PATTERN.sub(_sub, text)


def normalize_superscripts_in_exam(data: object) -> object:
    if isinstance(data, str):
        return replace_superscripts(data)
    if isinstance(data, list):
        return [normalize_superscripts_in_exam(item) for item in data]
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key == "accepted" and isinstance(value, list):
                new_accepted = []
                for item in value:
                    if isinstance(item, str):
                        converted = replace_superscripts(item)
                        if converted not in new_accepted:
                            new_accepted.append(converted)
                        if item not in new_accepted:
                            new_accepted.append(item)
                    else:
                        new_accepted.append(item)
                result[key] = new_accepted
            else:
                result[key] = normalize_superscripts_in_exam(value)
        return result
    return data


def minutes_value(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 240:
        raise ValueError("Thời gian thưởng phải là số nguyên từ 1 đến 240 phút.")
    return value


def normalize_answer(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def validate_questions(questions: object) -> list[dict]:
    if not isinstance(questions, list) or not questions:
        raise ValueError("Đề bài phải có ít nhất một câu hỏi.")
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Câu hỏi không hợp lệ.")
        if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
            raise ValueError("Mỗi câu hỏi cần có nội dung.")
        kind = question.get("kind")
        if kind == "choice":
            choices = question.get("choices")
            if (
                not isinstance(choices, list)
                or not 2 <= len(choices) <= 10
                or any(not isinstance(c, str) or not c.strip() for c in choices)
            ):
                raise ValueError("Trắc nghiệm cần từ 2 đến 10 lựa chọn không rỗng.")
            if type(question.get("correct")) is not int or not 0 <= question["correct"] < len(choices):
                raise ValueError("Vị trí đáp án đúng không hợp lệ.")
        elif kind == "short":
            answers = question.get("accepted")
            if not isinstance(answers, list) or not answers or any(
                not isinstance(a, str) or not normalize_answer(a) for a in answers
            ):
                raise ValueError("Câu trả lời ngắn cần ít nhất một đáp án.")
        elif kind != "essay":
            raise ValueError("Loại câu hỏi không được hỗ trợ.")
        solution = question.get("solution")
        if solution is not None and not isinstance(solution, str):
            raise ValueError("Lời giải phải là chuỗi văn bản.")
    return questions


EXAM_FIELDS = {"title", "subject", "minutes", "visible", "questions"}


def parse_exam(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Tệp đề thi phải chứa một đối tượng JSON.")
    data = normalize_superscripts_in_exam(data)
    unknown = set(data) - EXAM_FIELDS
    if unknown:
        raise ValueError("Tệp đề thi có trường không hỗ trợ: " + ", ".join(sorted(unknown)))
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Tệp đề thi cần tên đề (title) không rỗng.")
    subject = data.get("subject", "")
    if not isinstance(subject, str):
        raise ValueError("Môn học (subject) phải là chuỗi văn bản.")
    minutes = data.get("minutes", 15)
    minutes_value(minutes)
    visible = data.get("visible", True)
    if not isinstance(visible, bool):
        raise ValueError("Trường visible phải là true hoặc false.")
    questions = validate_questions(data.get("questions"))
    return {"title": title, "subject": subject, "minutes": minutes,
            "visible": visible, "questions": questions}


def load_exam_file(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Không đọc được tệp đề thi: {error}") from None
    return parse_exam(data)


def _grade_details(
    questions: list[dict], answers: object
) -> tuple[bool, bool, list[int], int, int]:
    validate_questions(questions)
    if not isinstance(answers, list) or len(answers) != len(questions):
        raise ValueError("Cần trả lời đủ tất cả câu hỏi.")
    wrong = []
    objective_correct = 0
    essays_answered = 0
    has_essay = False
    for index, (question, answer) in enumerate(zip(questions, answers)):
        if question["kind"] == "choice":
            correct = type(answer) is int and answer == question["correct"]
        elif question["kind"] == "short":
            correct = isinstance(answer, str) and normalize_answer(answer) in {
                normalize_answer(a) for a in question["accepted"]
            }
        elif question["kind"] == "essay":
            has_essay = True
            correct = isinstance(answer, str) and bool(answer.strip())
            essays_answered += int(correct)
        else:
            raise ValueError("Loại câu hỏi không được hỗ trợ.")
        if not correct:
            wrong.append(index + 1)
        elif question["kind"] != "essay":
            objective_correct += 1
    threshold = (len(questions) + 1) // 2
    passed = objective_correct + essays_answered >= threshold
    manual = has_essay and objective_correct < threshold
    return passed, manual, wrong, objective_correct, essays_answered


def grade(questions: list[dict], answers: object) -> tuple[bool, bool, list[int]]:
    passed, manual, wrong, _, _ = _grade_details(questions, answers)
    return passed, manual, wrong


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Mật khẩu cần ít nhất 8 ký tự.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"600000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def check_password(password: str, encoded: str) -> bool:
    rounds, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), base64.b64decode(salt), int(rounds)
    )
    return hmac.compare_digest(actual, base64.b64decode(expected))


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, subject TEXT NOT NULL,
                visible INTEGER NOT NULL, minutes INTEGER NOT NULL, questions TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY, task TEXT NOT NULL, day TEXT NOT NULL,
                granted REAL NOT NULL, minutes INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY, exercise_id INTEGER NOT NULL,
                title TEXT NOT NULL, questions TEXT NOT NULL, answers TEXT NOT NULL,
                minutes INTEGER NOT NULL, day TEXT NOT NULL, status TEXT NOT NULL,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exercise_attempts (
                exercise_id INTEGER PRIMARY KEY, attempts INTEGER NOT NULL
            );
        """)
        self.db.commit()
        if self.db.execute("PRAGMA user_version").fetchone()[0] < 1:
            with self.transaction():
                self.db.execute("""
                    CREATE TABLE rewards_updated (
                        id INTEGER PRIMARY KEY, task TEXT NOT NULL, day TEXT NOT NULL,
                        granted REAL NOT NULL, minutes INTEGER NOT NULL
                    )
                """)
                self.db.execute("""
                    INSERT INTO rewards_updated
                    SELECT id, task, date(granted, 'unixepoch', 'localtime'), granted, minutes
                    FROM rewards
                """)
                self.db.execute("DROP TABLE rewards")
                self.db.execute("ALTER TABLE rewards_updated RENAME TO rewards")
                self.db.execute("CREATE INDEX rewards_day_task ON rewards(day, task)")
                self.db.execute("PRAGMA user_version = 1")
        with self.transaction():
            self._complete_exam_round_if_ready()

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def get(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def _set(self, key: str, value):
        self.db.execute(
            "INSERT INTO settings(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )

    def configure(self, settings: dict):
        if set(settings) - DEFAULT_SETTINGS.keys():
            raise ValueError("Tùy chọn không hợp lệ.")
        if "typing_minutes" in settings:
            minutes_value(settings["typing_minutes"])
        if "reward_minutes" in settings:
            minutes_value(settings["reward_minutes"])
        if "daily_reward_limit" in settings:
            limit = settings["daily_reward_limit"]
            if type(limit) is not int or not 0 <= limit <= 100:
                raise ValueError("Số lần thưởng mỗi ngày phải là số nguyên từ 0 đến 100.")
        if "match_threshold" in settings:
            threshold = settings["match_threshold"]
            if type(threshold) not in (int, float) or not 0.7 <= threshold <= 0.99:
                raise ValueError("Ngưỡng nhận diện phải từ 0.70 đến 0.99.")
        with self.transaction():
            for key, value in settings.items():
                self._set(key, value)

    def settings(self) -> dict:
        return {key: self.get(key, value) for key, value in DEFAULT_SETTINGS.items()}

    def reward_minutes(self, individual_minutes: int) -> int:
        shared = self.get("reward_minutes")
        return individual_minutes if shared is None else shared

    def set_password(self, password: str):
        encoded = hash_password(password)
        with self.transaction():
            self._set("password", encoded)
            self._set("auth_failures", 0)
            self._set("auth_locked_until", 0)

    def authenticate(self, password: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self.transaction():
            locked = self.get("auth_locked_until", 0)
            if now < locked:
                raise ValueError(f"Hãy thử lại sau {math.ceil(locked - now)} giây.")
            encoded = self.get("password")
            valid = bool(encoded) and check_password(password, encoded)
            failures = 0 if valid else self.get("auth_failures", 0) + 1
            self._set("auth_failures", failures)
            if failures >= 5:
                self._set("auth_locked_until", now + 60)
                self._set("auth_failures", 0)
            elif valid:
                self._set("auth_locked_until", 0)
        return valid

    def exercises(self, visible_only=False) -> list[dict]:
        sql = "SELECT * FROM exercises"
        if visible_only:
            sql += " WHERE visible=1"
        return [self._exercise(row) for row in self.db.execute(sql + " ORDER BY id")]

    @staticmethod
    def _exercise(row) -> dict:
        result = dict(row)
        result["questions"] = json.loads(result["questions"])
        result["visible"] = bool(result["visible"])
        return result

    def exercise(self, exercise_id: int) -> dict:
        row = self.db.execute("SELECT * FROM exercises WHERE id=?", (exercise_id,)).fetchone()
        if not row:
            raise ValueError("Đề bài không còn tồn tại.")
        return self._exercise(row)

    def save_exercise(self, title: str, subject: str, visible: bool, minutes: int,
                      questions: list[dict], exercise_id: int | None = None) -> int:
        title = replace_superscripts(title) if isinstance(title, str) else title
        subject = replace_superscripts(subject) if isinstance(subject, str) else subject
        if questions is not None:
            questions = normalize_superscripts_in_exam(questions)
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Cần nhập tên đề bài.")
        minutes_value(minutes)
        validate_questions(questions)
        values = (title.strip(), subject.strip(), int(visible), minutes,
                  json.dumps(questions, ensure_ascii=False))
        with self.transaction():
            if exercise_id is None:
                cursor = self.db.execute(
                    "INSERT INTO exercises(title,subject,visible,minutes,questions) VALUES (?,?,?,?,?)",
                    values,
                )
                saved_id = cursor.lastrowid
            else:
                cursor = self.db.execute(
                    "UPDATE exercises SET title=?,subject=?,visible=?,minutes=?,questions=? WHERE id=?",
                    (*values, exercise_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("Không tìm thấy đề bài.")
                saved_id = exercise_id
            self._complete_exam_round_if_ready()
        return saved_id

    def set_visible(self, exercise_id: int, visible: bool):
        with self.transaction():
            cursor = self.db.execute(
                "UPDATE exercises SET visible=? WHERE id=?", (int(visible), exercise_id)
            )
            if cursor.rowcount != 1:
                raise ValueError("Không tìm thấy đề bài.")
            self._complete_exam_round_if_ready()

    def _exam_attempt_count(self, exercise_id: int) -> int:
        row = self.db.execute(
            "SELECT attempts FROM exercise_attempts WHERE exercise_id=?", (exercise_id,)
        ).fetchone()
        return row["attempts"] if row else 0

    def _complete_exam_round_if_ready(self) -> bool:
        exercise_ids = [
            row["id"] for row in self.db.execute(
                "SELECT id FROM exercises WHERE visible=1"
            )
        ]
        if not exercise_ids or any(
            self._exam_attempt_count(exercise_id) < MAX_EXERCISE_ATTEMPTS
            for exercise_id in exercise_ids
        ):
            return False
        self.db.execute("UPDATE exercise_attempts SET attempts=0")
        self._set("exam_round", self.get("exam_round", 1) + 1)
        return True

    def _record_exam_attempt(self, exercise_id: int) -> tuple[int, bool]:
        self.db.execute(
            "INSERT INTO exercise_attempts(exercise_id,attempts) VALUES (?,1) "
            "ON CONFLICT(exercise_id) DO UPDATE SET attempts=attempts+1",
            (exercise_id,),
        )
        attempts = self._exam_attempt_count(exercise_id)
        return attempts, self._complete_exam_round_if_ready()

    def import_exam_file(self, path: Path) -> int:
        return self.save_exercise(**load_exam_file(path))

    def import_exam_json(self, text: str) -> list[int]:
        if not text.strip():
            raise ValueError("Hãy nhập hoặc dán nội dung JSON của đề thi.")
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"Định dạng JSON không hợp lệ: {error}") from None
        if isinstance(data, list):
            if not data:
                raise ValueError("Danh sách đề thi rỗng.")
            exams = [parse_exam(item) for item in data]
        elif isinstance(data, dict):
            exams = [parse_exam(data)]
        else:
            raise ValueError("Nội dung JSON phải là một đối tượng đề thi hoặc danh sách đề thi.")
        return [self.save_exercise(**exam) for exam in exams]

    def export_exam_file(self, exercise_id: int, path: Path) -> None:
        exercise = self.exercise(exercise_id)
        exam = parse_exam({
            "title": exercise["title"],
            "subject": exercise["subject"],
            "minutes": exercise["minutes"],
            "visible": exercise["visible"],
            "questions": exercise["questions"],
        })
        Path(path).write_text(
            json.dumps(exam, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def seed_exams(self, exams: list[tuple[str, dict]]) -> list[int]:
        imported = []
        seeded = self.get("seeded_exams", [])
        for slug, exam in exams:
            if slug in seeded:
                continue
            imported.append(self.save_exercise(**parse_exam(exam)))
            seeded.append(slug)
            with self.transaction():
                self._set("seeded_exams", seeded)
        return imported

    @staticmethod
    def day(now: float) -> str:
        return datetime.fromtimestamp(now).date().isoformat()

    def reward_progress(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        settings = self.settings()
        counts = {
            row["task"]: row["count"] for row in self.db.execute(
                "SELECT task, COUNT(*) AS count FROM rewards WHERE day=? GROUP BY task",
                (self.day(now),),
            )
        }
        tasks = {
            f"exercise:{row['id']}" for row in self.db.execute(
                "SELECT id FROM exercises WHERE visible=1"
            )
        }
        if settings["typing_exe"] and settings["typing_template"]:
            tasks.add("typing")
        pending = {
            f"exercise:{row['exercise_id']}" for row in self.db.execute(
                "SELECT DISTINCT exercise_id FROM submissions WHERE status='pending'"
            )
        }
        used = sum(counts.values())
        limit = settings["daily_reward_limit"]
        completed_reward_rounds = min((counts.get(task, 0) for task in tasks), default=0)
        task_states = {}
        for task in tasks:
            reason = ""
            exercise_attempts = (
                self._exam_attempt_count(int(task.split(":")[1]))
                if task.startswith("exercise:") else 0
            )
            attempt_limit_reached = (
                task.startswith("exercise:")
                and exercise_attempts >= MAX_EXERCISE_ATTEMPTS
            )
            daily_limit_reached = used >= limit
            if daily_limit_reached:
                reason = "Đã hết lượt thưởng hôm nay. Hãy quay lại vào ngày mai."
            elif attempt_limit_reached:
                reason = (
                    f"Đã làm đề này {MAX_EXERCISE_ATTEMPTS} lần. "
                    "Hãy hoàn thành các đề còn lại trước khi làm lại."
                )
            elif task == "typing" and counts.get(task, 0) > completed_reward_rounds:
                reason = "Hãy hoàn thành các bài còn lại trong vòng này trước khi làm lại."
            task_states[task] = {
                "completed": counts.get(task, 0), "attempts": exercise_attempts,
                "attempt_limit_reached": attempt_limit_reached,
                "daily_limit_reached": daily_limit_reached,
                "reason": reason, "pending": task in pending,
            }
        return {
            "used": used, "limit": limit, "round": self.get("exam_round", 1),
            "tasks": task_states,
        }

    def require_reward(self, task: str, now: float | None = None, *, reviewing=False):
        state = self.reward_progress(now)["tasks"].get(task)
        if state is None:
            raise ValueError("Bài tập không nằm trong danh sách đang hiển thị.")
        if state["reason"] and not (
            reviewing and state["attempt_limit_reached"] and not state["daily_limit_reached"]
        ):
            raise ValueError(state["reason"])
        if state["pending"] and not reviewing:
            raise ValueError("Đề này đã được nộp và đang chờ cha mẹ duyệt.")

    def _grant(self, task: str, minutes: int, now: float):
        minutes_value(minutes)
        self.require_reward(task, now, reviewing=True)
        paused_seconds = max(0, self.get("paused_reward_seconds", 0))
        available_seconds = max(0, self.get("available_reward_seconds", 0))
        free_until = self.get("free_until", 0)
        self.db.execute(
            "INSERT INTO rewards(task,day,granted,minutes) VALUES (?,?,?,?)",
            (task, self.day(now), now, minutes),
        )
        if free_until > now:
            self._set(
                "free_until",
                free_until + paused_seconds + available_seconds + minutes * 60,
            )
            self._set("available_reward_seconds", 0)
        else:
            self._set("free_until", 0)
            self._set(
                "available_reward_seconds",
                available_seconds + paused_seconds + minutes * 60,
            )
        self._set("paused_reward_seconds", 0)

    def reward_typing(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.transaction():
            minutes = self.reward_minutes(self.settings()["typing_minutes"])
            self._grant("typing", minutes, now)
        return minutes

    def submit(self, exercise_id: int, answers: list, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        with self.transaction():
            exercise = self.exercise(exercise_id)
            if not exercise["visible"]:
                raise ValueError("Đề bài đang được ẩn.")
            task = f"exercise:{exercise_id}"
            self.require_reward(task, now)
            questions = exercise["questions"]
            passed, manual, wrong, objective_correct, essays_answered = _grade_details(
                questions, answers
            )
            score = {
                "correct_count": objective_correct,
                "essay_answered_count": essays_answered,
                "total_questions": len(questions),
            }
            attempt, round_reset = self._record_exam_attempt(exercise_id)
            if not passed:
                if not round_reset:
                    self.db.execute(
                        "UPDATE exercise_attempts SET attempts=? WHERE exercise_id=?",
                        (MAX_EXERCISE_ATTEMPTS, exercise_id),
                    )
                    attempt = MAX_EXERCISE_ATTEMPTS
                    round_reset = self._complete_exam_round_if_ready()
                return {
                    "status": "incorrect", "wrong": wrong, "attempt": attempt,
                    "attempt_limit": MAX_EXERCISE_ATTEMPTS, "round_reset": round_reset,
                    **score,
                }
            minutes = self.reward_minutes(exercise["minutes"])
            if manual:
                self.db.execute(
                    "INSERT INTO submissions(exercise_id,title,questions,answers,minutes,day,status,created)"
                    " VALUES (?,?,?,?,?,?,'pending',?)",
                    (exercise_id, exercise["title"], json.dumps(exercise["questions"], ensure_ascii=False),
                     json.dumps(answers, ensure_ascii=False), minutes, self.day(now), now),
                )
                return {"status": "pending", "attempt": attempt, **score}
            self._grant(task, minutes, now)
            return {"status": "rewarded", "minutes": minutes, **score}

    def pending(self) -> list[dict]:
        result = []
        for row in self.db.execute("SELECT * FROM submissions WHERE status='pending' ORDER BY id"):
            item = dict(row)
            item["questions"] = json.loads(item["questions"])
            item["answers"] = json.loads(item["answers"])
            result.append(item)
        return result

    def review(self, submission_id: int, approve: bool, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.transaction():
            row = self.db.execute(
                "SELECT * FROM submissions WHERE id=? AND status='pending'", (submission_id,)
            ).fetchone()
            if not row:
                raise ValueError("Bài nộp không còn chờ duyệt.")
            if approve:
                self._grant(f"exercise:{row['exercise_id']}", row["minutes"], now)
            else:
                self.db.execute(
                    "UPDATE exercise_attempts SET attempts=MAX(0, attempts-1) WHERE exercise_id=?",
                    (row["exercise_id"],),
                )
            self.db.execute(
                "UPDATE submissions SET status=? WHERE id=?",
                ("approved" if approve else "rejected", submission_id),
            )
            return row["minutes"] if approve else 0

    def remaining(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        return max(0, math.ceil(self.get("free_until", 0) - now))

    def reward_time(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        return self.remaining(now) + max(0, self.get("available_reward_seconds", 0))

    def start_reward_time(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.transaction():
            remaining = max(0, math.ceil(self.get("free_until", 0) - now))
            if remaining:
                return remaining
            available = max(0, self.get("available_reward_seconds", 0))
            if available:
                self._set("free_until", now + available)
                self._set("available_reward_seconds", 0)
            return available

    def pause_reward_time(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.transaction():
            remaining = max(0, math.ceil(self.get("free_until", 0) - now))
            if remaining:
                paused = self.get("paused_reward_seconds", 0)
                self._set("paused_reward_seconds", paused + remaining)
                self._set("free_until", 0)
        return remaining

    def revoke_time(self):
        with self.transaction():
            self._set("free_until", 0)
            self._set("paused_reward_seconds", 0)
            self._set("available_reward_seconds", 0)
