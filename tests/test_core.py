import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from kidsroom.core import Store, grade, load_exam_file, parse_exam, validate_questions
from kidsroom.exams import BUNDLED_EXAMS


QUESTIONS = [
    {"kind": "choice", "prompt": "2 + 2?", "choices": ["3", "4"], "correct": 1},
    {"kind": "short", "prompt": "Capital?", "accepted": ["Ha Noi", "Hanoi"]},
]


class GradingTests(unittest.TestCase):
    def test_exact_choice_and_normalized_short(self):
        self.assertEqual(grade(QUESTIONS, [1, "  HA   NOI "]), (True, False, []))
        self.assertEqual(grade(QUESTIONS, [True, "wrong"]), (False, False, [1, 2]))

    def test_half_correct_completes_exam_and_odd_question_count_rounds_up(self):
        self.assertEqual(grade(QUESTIONS, [1, "wrong"]), (True, False, [2]))
        self.assertEqual(grade(QUESTIONS, [0, "wrong"]), (False, False, [1, 2]))
        three_questions = QUESTIONS + [
            {"kind": "short", "prompt": "Color?", "accepted": ["blue"]}
        ]
        self.assertTrue(grade(three_questions, [1, "wrong", "blue"])[0])
        self.assertFalse(grade(three_questions, [0, "wrong", "blue"])[0])

    def test_vietnamese_unicode_normalization_keeps_accents(self):
        questions = [{"kind": "short", "prompt": "?", "accepted": ["H\u00e0 N\u1ed9i"]}]
        self.assertTrue(grade(questions, ["Ha\u0300 No\u0323\u0302i"])[0])
        self.assertFalse(grade(questions, ["Ha Noi"])[0])

    def test_essay_needs_manual_review_and_nonempty_answer(self):
        questions = [{"kind": "essay", "prompt": "Write"}]
        self.assertEqual(grade(questions, ["Text"]), (True, True, []))
        self.assertEqual(grade(questions, ["  "]), (False, True, [1]))

    def test_invalid_quiz_and_missing_answers(self):
        for questions in ([], [{"kind": "short", "prompt": "?", "accepted": [" "]}],
                          [{"kind": "choice", "prompt": "?", "choices": ["a", "b"], "correct": 2}]):
            with self.assertRaises(ValueError):
                validate_questions(questions)
        with self.assertRaises(ValueError):
            grade(QUESTIONS, [1])


class ExamImportTests(unittest.TestCase):
    def test_solution_must_be_text_when_present(self):
        question = {"kind": "essay", "prompt": "Explain", "solution": "Because"}
        self.assertEqual(validate_questions([question]), [question])
        with self.assertRaises(ValueError):
            validate_questions([{"kind": "essay", "prompt": "Explain", "solution": 5}])

    def test_parse_exam_defaults_and_rejections(self):
        exam = parse_exam({"title": "Exam", "questions": QUESTIONS})
        self.assertEqual((exam["subject"], exam["minutes"], exam["visible"]), ("", 15, True))
        for bad in ([], {"questions": QUESTIONS}, {"title": " ", "questions": QUESTIONS},
                    {"title": "Exam", "questions": []},
                    {"title": "Exam", "questions": QUESTIONS, "extra": 1},
                    {"title": "Exam", "questions": QUESTIONS, "minutes": 0},
                    {"title": "Exam", "questions": QUESTIONS, "visible": "yes"}):
            with self.assertRaises(ValueError):
                parse_exam(bad)

    def test_import_exam_file_and_seed_bundled_exams_once(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / "data.sqlite3")
            try:
                exam_path = Path(temp) / "exam.json"
                exam_path.write_text(json.dumps({
                    "title": "De mau", "subject": "Toan", "minutes": 20,
                    "questions": QUESTIONS,
                }, ensure_ascii=False), "utf-8")
                store.import_exam_file(exam_path)
                self.assertEqual(store.exercises()[0]["title"], "De mau")
                exam_path.write_text("not json", "utf-8")
                with self.assertRaises(ValueError):
                    store.import_exam_file(exam_path)
                self.assertEqual(len(store.seed_exams(BUNDLED_EXAMS)), 2)
                self.assertEqual(store.seed_exams(BUNDLED_EXAMS), [])
                titles = [exercise["title"] for exercise in store.exercises()]
                self.assertEqual(len(titles), 3)
                self.assertTrue(any("Học kì I" in title for title in titles))
                self.assertTrue(any("Giữa học kì I" in title for title in titles))
            finally:
                store.close()

    def test_export_exam_file_round_trips_supported_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / "data.sqlite3")
            try:
                exercise_id = store.save_exercise(
                    "Đề Toán", "Toán 6", False, 20, QUESTIONS
                )
                exam_path = Path(temp) / "exported.json"
                store.export_exam_file(exercise_id, exam_path)
                self.assertEqual(load_exam_file(exam_path), {
                    "title": "Đề Toán", "subject": "Toán 6", "minutes": 20,
                    "visible": False, "questions": QUESTIONS,
                })
            finally:
                store.close()

    def test_bundled_exams_grade_with_answer_key(self):
        for slug, exam in BUNDLED_EXAMS:
            parsed = parse_exam(exam)
            answers = [question.get("correct", "Bai lam cua con")
                       for question in parsed["questions"]]
            passed, manual, wrong = grade(parsed["questions"], answers)
            self.assertTrue(passed, slug)
            self.assertFalse(manual, slug)
            self.assertEqual(wrong, [], slug)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "data.sqlite3"
        self.store = Store(self.path)
        self.now = datetime(2026, 11, 15, 12).timestamp()
        self.exercise_id = self.store.save_exercise("Quiz", "Math", True, 15, QUESTIONS)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_reward_survives_restart_and_expires_at_exact_deadline(self):
        self.store.configure({"daily_reward_limit": 1})
        result = self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(result["status"], "rewarded")
        self.assertEqual(self.store.start_reward_time(self.now), 900)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.remaining(self.now + 899), 1)
        self.assertEqual(self.store.remaining(self.now + 900), 0)
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now + 901)
        self.assertEqual(self.store.remaining(self.now + 901), 0)

    def test_unstarted_reward_survives_restart_without_counting_down(self):
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.reward_time(self.now + 3600), 900)
        self.assertEqual(self.store.remaining(self.now + 3600), 0)
        self.assertEqual(self.store.start_reward_time(self.now + 3600), 900)
        self.assertEqual(self.store.remaining(self.now + 3600), 900)

    def test_daily_reward_resets_and_failed_answers_grant_nothing(self):
        self.store.configure({"daily_reward_limit": 1})
        self.assertEqual(
            self.store.submit(self.exercise_id, [0, "wrong"], self.now)["wrong"], [1, 2]
        )
        self.assertEqual(self.store.remaining(self.now), 0)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.submit(self.exercise_id, [1, "Hanoi"], self.now + 86400)["status"],
                         "rewarded")

    def test_half_correct_submission_grants_configured_time(self):
        result = self.store.submit(self.exercise_id, [1, "wrong"], self.now)
        self.assertEqual(result, {
            "status": "rewarded", "minutes": 15, "correct_count": 1,
            "essay_answered_count": 0, "total_questions": 2,
        })
        self.assertGreater(self.store.reward_time(self.now), 895)
        self.assertEqual(self.store.remaining(self.now), 0)

    def test_half_objective_score_skips_essay_review_and_rewards_immediately(self):
        questions = [
            {"kind": "choice", "prompt": "A?", "choices": ["no", "yes"], "correct": 1},
            {"kind": "choice", "prompt": "B?", "choices": ["no", "yes"], "correct": 1},
            {"kind": "essay", "prompt": "Explain A"},
            {"kind": "essay", "prompt": "Explain B"},
        ]
        exercise = self.store.save_exercise("Mixed", "Math", True, 15, questions)
        outcome = self.store.submit(exercise, [1, 1, "", ""], self.now)
        self.assertEqual(outcome["status"], "rewarded")
        self.assertEqual(outcome["correct_count"], 2)
        self.assertEqual(outcome["essay_answered_count"], 0)
        self.assertEqual(self.store.pending(), [])
        self.assertGreater(self.store.reward_time(self.now), 895)
        self.assertEqual(self.store.remaining(self.now), 0)

    def test_essay_answers_can_reach_half_but_wait_for_parent_review(self):
        questions = [
            {"kind": "choice", "prompt": "A?", "choices": ["no", "yes"], "correct": 1},
            {"kind": "choice", "prompt": "B?", "choices": ["no", "yes"], "correct": 1},
            {"kind": "essay", "prompt": "Explain A"},
            {"kind": "essay", "prompt": "Explain B"},
        ]
        exercise = self.store.save_exercise("Mixed", "Math", True, 15, questions)
        outcome = self.store.submit(exercise, [1, 0, "Answer A", ""], self.now)
        self.assertEqual(outcome["status"], "pending")
        self.assertEqual(outcome["correct_count"], 1)
        self.assertEqual(outcome["essay_answered_count"], 1)
        self.assertEqual(len(self.store.pending()), 1)

    def test_less_than_half_even_counting_submitted_essays_does_not_get_review(self):
        questions = [
            {"kind": "choice", "prompt": "A?", "choices": ["no", "yes"], "correct": 1},
            {"kind": "choice", "prompt": "B?", "choices": ["no", "yes"], "correct": 1},
            {"kind": "essay", "prompt": "Explain A"},
            {"kind": "essay", "prompt": "Explain B"},
        ]
        exercise = self.store.save_exercise("Mixed", "Math", True, 15, questions)
        outcome = self.store.submit(exercise, [0, 0, "Answer A", ""], self.now)
        self.assertEqual(outcome["status"], "incorrect")
        self.assertEqual(outcome["correct_count"], 0)
        self.assertEqual(outcome["essay_answered_count"], 1)
        self.assertEqual(self.store.pending(), [])

    def test_paused_reward_survives_restart_and_is_added_to_next_reward(self):
        second = self.store.save_exercise("English", "English", True, 10, QUESTIONS)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.start_reward_time(self.now), 900)
        self.assertEqual(self.store.pause_reward_time(self.now + 120), 780)
        self.assertEqual(self.store.remaining(self.now + 120), 0)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.get("paused_reward_seconds"), 780)
        self.store.submit(second, [1, "Hanoi"], self.now + 600)
        self.assertEqual(self.store.reward_time(self.now + 600), 1380)
        self.assertEqual(self.store.start_reward_time(self.now + 600), 1380)
        self.assertEqual(self.store.remaining(self.now + 600), 1380)
        self.assertEqual(self.store.get("paused_reward_seconds"), 0)

    def test_hidden_exercise_cannot_be_submitted(self):
        self.store.set_visible(self.exercise_id, False)
        self.assertEqual(self.store.exercises(True), [])
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)

    def test_manual_review_uses_snapshot_and_cannot_pay_twice(self):
        questions = QUESTIONS + [{"kind": "essay", "prompt": "Explain"}]
        self.store.save_exercise("Essay", "Math", True, 20, questions, self.exercise_id)
        self.assertEqual(self.store.submit(self.exercise_id, [1, "wrong", "Because"], self.now)["status"],
                         "pending")
        self.assertEqual(self.store.remaining(self.now), 0)
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "wrong", "Again"], self.now)
        self.store.save_exercise("Edited", "Math", True, 1, QUESTIONS, self.exercise_id)
        submission = self.store.pending()[0]
        self.assertEqual(submission["title"], "Essay")
        self.assertEqual(self.store.review(submission["id"], True, self.now + 100), 20)
        with self.assertRaises(ValueError):
            self.store.review(submission["id"], True, self.now + 101)
        self.assertEqual(self.store.reward_time(self.now + 100), 1200)
        self.assertEqual(self.store.start_reward_time(self.now + 100), 1200)
        self.assertEqual(self.store.remaining(self.now + 100), 1200)

    def test_rejection_allows_resubmission(self):
        questions = [{"kind": "essay", "prompt": "Explain"}]
        exercise = self.store.save_exercise("Essay", "Writing", True, 15, questions)
        self.store.submit(exercise, ["First"], self.now)
        self.store.review(self.store.pending()[0]["id"], False, self.now)
        self.assertEqual(self.store.submit(exercise, ["Second"], self.now)["status"], "pending")

    def test_typing_shares_rotation_and_extends_reward(self):
        self.store.configure({
            "typing_minutes": 20, "typing_exe": "typing.exe", "typing_template": "sample.png",
        })
        self.assertEqual(self.store.reward_typing(self.now), 20)
        self.assertEqual(self.store.start_reward_time(self.now), 20 * 60)
        with self.assertRaises(ValueError):
            self.store.reward_typing(self.now + 1)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now + 60)
        self.assertEqual(self.store.remaining(self.now + 60), 2040)
        self.assertEqual(self.store.reward_typing(self.now + 120), 20)
        self.assertEqual(self.store.reward_progress(self.now + 120)["used"], 3)

    def test_shared_reward_applies_to_exercise_and_typing_after_restart(self):
        self.store.configure({
            "typing_minutes": 20, "typing_exe": "typing.exe", "typing_template": "sample.png",
            "reward_minutes": 7, "daily_reward_limit": 3,
        })
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)["minutes"], 7)
        self.assertEqual(self.store.reward_typing(self.now), 7)
        self.assertEqual(self.store.reward_time(self.now), 14 * 60)
        self.assertEqual(self.store.start_reward_time(self.now), 14 * 60)
        self.assertEqual(self.store.remaining(self.now), 14 * 60)
        self.assertEqual(self.store.exercise(self.exercise_id)["minutes"], 15)

    def test_shared_reward_preserves_essay_snapshot_when_settings_change(self):
        essay = self.store.save_exercise(
            "Essay", "Writing", True, 20, [{"kind": "essay", "prompt": "Explain"}]
        )
        self.store.submit(essay, ["Earlier"], self.now)
        previous = self.store.pending()[0]["id"]
        self.store.configure({"reward_minutes": 8})
        self.assertEqual(self.store.review(previous, True, self.now), 20)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.submit(essay, ["Later"], self.now)
        current = self.store.pending()[0]
        self.assertEqual(current["minutes"], 8)
        self.store.configure({"reward_minutes": 12})
        self.assertEqual(self.store.review(current["id"], True, self.now), 8)

    def test_password_lockout_persists(self):
        self.store.set_password("parent123")
        for _ in range(5):
            self.assertFalse(self.store.authenticate("bad", self.now))
        self.store.close()
        self.store = Store(self.path)
        with self.assertRaises(ValueError):
            self.store.authenticate("parent123", self.now + 59)
        self.assertTrue(self.store.authenticate("parent123", self.now + 60))
        self.assertFalse(self.store.authenticate("bad", self.now + 61))

    def test_password_hash_and_configuration_validation(self):
        with self.assertRaises(ValueError):
            self.store.set_password("short")
        self.store.set_password("parent123")
        self.assertNotIn("parent123", self.store.get("password"))
        for bad in (0, 241, True, 1.5):
            with self.assertRaises(ValueError):
                self.store.configure({"typing_minutes": bad})
            with self.assertRaises(ValueError):
                self.store.configure({"reward_minutes": bad})
        for bad in (0.69, 1, float("nan")):
            with self.assertRaises(ValueError):
                self.store.configure({"match_threshold": bad})
        for bad in (-1, 101, True, 1.5):
            with self.assertRaises(ValueError):
                self.store.configure({"daily_reward_limit": bad})

    def test_atomic_grant_rolls_back_on_failure(self):
        self.store.db.execute("""
            CREATE TRIGGER reject_settings BEFORE INSERT ON settings
            BEGIN SELECT RAISE(ABORT, 'test write failure'); END
        """)
        self.store.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 0)

    def test_failed_attempt_uses_remaining_lives_then_resets_after_all_visible_exams(self):
        second = self.store.save_exercise("English", "English", True, 20, QUESTIONS)
        self.store.configure({"daily_reward_limit": 4})
        result = self.store.submit(self.exercise_id, [0, "wrong"], self.now)
        self.assertEqual(result["status"], "incorrect")
        self.assertEqual(result["attempt"], 2)
        self.assertEqual((result["correct_count"], result["total_questions"]), (0, 2))
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(
            self.store.reward_progress(self.now)["tasks"][f"exercise:{self.exercise_id}"]["attempts"],
            2,
        )
        self.store.submit(second, [0, "wrong"], self.now)
        progress = self.store.reward_progress(self.now)
        self.assertEqual(progress["round"], 2)
        self.assertEqual(progress["tasks"][f"exercise:{self.exercise_id}"]["attempts"], 0)
        self.assertEqual(progress["tasks"][f"exercise:{second}"]["attempts"], 0)
        self.store.submit(self.exercise_id, [0, "wrong"], self.now)

    def test_successful_attempts_still_obey_global_daily_reward_cap(self):
        second = self.store.save_exercise("English", "English", True, 20, QUESTIONS)
        self.store.configure({"daily_reward_limit": 3})
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.submit(second, [1, "Hanoi"], self.now)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        with self.assertRaises(ValueError):
            self.store.submit(second, [1, "Hanoi"], self.now)
        progress = self.store.reward_progress(self.now)
        self.assertEqual(progress["used"], 3)
        self.assertEqual(self.store.reward_time(self.now), 50 * 60)

    def test_single_task_can_repeat_until_cap_and_cap_changes_preserve_usage(self):
        self.store.configure({"daily_reward_limit": 2})
        for _ in range(2):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.configure({"daily_reward_limit": 1})
        self.store.revoke_time()
        self.assertEqual(self.store.reward_progress(self.now)["used"], 2)
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.configure({"daily_reward_limit": 3})
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 3)
        self.assertEqual(self.store.reward_time(self.now), 900)

    def test_zero_cap_and_unconfigured_typing_cannot_grant(self):
        with self.assertRaises(ValueError):
            self.store.reward_typing(self.now)
        self.store.configure({"daily_reward_limit": 0})
        with self.assertRaises(ValueError):
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 0)

    def test_hiding_and_reshowing_tasks_does_not_clear_daily_usage(self):
        second = self.store.save_exercise("English", "English", True, 20, QUESTIONS)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.set_visible(second, False)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.set_visible(second, True)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 2)
        self.store.submit(second, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 3)

    def test_essay_approval_counts_on_grant_day_and_obeys_daily_cap(self):
        essay = self.store.save_exercise(
            "Essay", "Writing", True, 20, [{"kind": "essay", "prompt": "Explain"}]
        )
        self.store.configure({"daily_reward_limit": 1})
        self.store.submit(essay, ["My answer"], self.now)
        submission = self.store.pending()[0]["id"]
        tomorrow = self.now + 86400
        with self.assertRaises(ValueError):
            self.store.submit(essay, ["Duplicate"], tomorrow)
        self.store.submit(self.exercise_id, [1, "Hanoi"], tomorrow)
        with self.assertRaises(ValueError):
            self.store.review(submission, True, tomorrow)
        self.assertEqual(len(self.store.pending()), 1)
        self.store.configure({"daily_reward_limit": 2})
        self.assertEqual(self.store.review(submission, True, tomorrow), 20)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 0)
        self.assertEqual(self.store.reward_progress(tomorrow)["used"], 2)
        self.assertEqual(self.store.reward_time(tomorrow), 35 * 60)

    def test_second_connection_cannot_use_stale_daily_allowance(self):
        self.store.configure({"daily_reward_limit": 1})
        other = Store(self.path)
        try:
            other.require_reward(f"exercise:{self.exercise_id}", self.now)
            self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
            with self.assertRaises(ValueError):
                other.submit(self.exercise_id, [1, "Hanoi"], self.now)
            self.assertEqual(other.reward_progress(self.now)["used"], 1)
        finally:
            other.close()

    def test_legacy_unique_reward_history_migrates_without_losing_time_or_counts(self):
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.store.db.executescript("""
            ALTER TABLE rewards RENAME TO rewards_unrestricted;
            CREATE TABLE rewards (
                id INTEGER PRIMARY KEY, task TEXT NOT NULL, day TEXT NOT NULL,
                granted REAL NOT NULL, minutes INTEGER NOT NULL, UNIQUE(task, day)
            );
            INSERT INTO rewards SELECT * FROM rewards_unrestricted;
            DROP TABLE rewards_unrestricted;
            PRAGMA user_version = 0;
        """)
        with self.store.transaction():
            self.store.db.execute("UPDATE rewards SET day=?", (self.store.day(self.now - 86400),))
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.reward_time(self.now), 900)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 1)
        self.store.submit(self.exercise_id, [1, "Hanoi"], self.now)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 2)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.reward_progress(self.now)["used"], 2)
        self.assertEqual(self.store.reward_time(self.now), 1800)

    def test_import_exam_json_supports_single_object_and_list(self):
        single = json.dumps({
            "title": "Single JSON Exam",
            "subject": "Physics",
            "minutes": 15,
            "visible": True,
            "questions": [{"kind": "short", "prompt": "Speed of light?", "accepted": ["c"]}],
        })
        ids = self.store.import_exam_json(single)
        self.assertEqual(len(ids), 1)
        self.assertEqual(self.store.exercise(ids[0])["title"], "Single JSON Exam")

        multiple = json.dumps([
            {
                "title": "Exam A", "subject": "Bio", "minutes": 10, "visible": True,
                "questions": [{"kind": "choice", "prompt": "Cell?", "choices": ["Yes", "No"], "correct": 0}],
            },
            {
                "title": "Exam B", "subject": "Chem", "minutes": 15, "visible": True,
                "questions": [{"kind": "short", "prompt": "Water?", "accepted": ["H2O"]}],
            },
        ])
        batch_ids = self.store.import_exam_json(multiple)
        self.assertEqual(len(batch_ids), 2)

        with self.assertRaises(ValueError):
            self.store.import_exam_json("")
        with self.assertRaises(ValueError):
            self.store.import_exam_json("not valid json")
        with self.assertRaises(ValueError):
            self.store.import_exam_json("[]")

    def test_superscript_exponent_replacement_in_exam_import(self):
        from kidsroom.core import replace_superscripts

        self.assertEqual(replace_superscripts("2^2"), "2²")
        self.assertEqual(replace_superscripts("3^2"), "3²")
        self.assertEqual(replace_superscripts("3^5"), "3⁵")
        self.assertEqual(replace_superscripts("10^4"), "10⁴")
        self.assertEqual(replace_superscripts("2^(x+1)"), "2ˣ⁺¹")
        self.assertEqual(replace_superscripts("2^{x+1}"), "2ˣ⁺¹")
        self.assertEqual(replace_superscripts("2^-3"), "2⁻³")
        self.assertEqual(replace_superscripts("(a + b)^2"), "(a + b)²")
        self.assertEqual(replace_superscripts("2 ^ 2"), "2²")

        exam_payload = json.dumps({
            "title": "Đề thi luỹ thừa 2^2 và 3^5",
            "subject": "Toán 6",
            "minutes": 15,
            "visible": True,
            "questions": [
                {
                    "kind": "choice",
                    "prompt": "Tính giá trị 2^3 + 3^2:",
                    "choices": ["15", "17", "2^3", "3^2"],
                    "correct": 1,
                    "solution": "Ta có 2^3 = 8 và 3^2 = 9 nên 8 + 9 = 17",
                },
                {
                    "kind": "short",
                    "prompt": "Viết gọn 2 . 2 dưới dạng luỹ thừa:",
                    "accepted": ["2^2"],
                    "solution": "2^2",
                },
            ],
        })
        ids = self.store.import_exam_json(exam_payload)
        saved = self.store.exercise(ids[0])
        self.assertEqual(saved["title"], "Đề thi luỹ thừa 2² và 3⁵")
        q1 = saved["questions"][0]
        self.assertEqual(q1["prompt"], "Tính giá trị 2³ + 3²:")
        self.assertEqual(q1["choices"], ["15", "17", "2³", "3²"])
        self.assertEqual(q1["solution"], "Ta có 2³ = 8 và 3² = 9 nên 8 + 9 = 17")

        q2 = saved["questions"][1]
        self.assertEqual(q2["prompt"], "Viết gọn 2 . 2 dưới dạng luỹ thừa:")
        self.assertIn("2²", q2["accepted"])
        self.assertIn("2^2", q2["accepted"])
        self.assertEqual(q2["solution"], "2²")

        # Test answering with physical keyboard '2^2'
        outcome_ascii = self.store.submit(ids[0], [1, "2^2"], self.now)
        self.assertEqual(outcome_ascii["status"], "rewarded")

        # Test answering with unicode '2²'
        outcome_unicode = self.store.submit(ids[0], [1, "2²"], self.now + 10)
        self.assertEqual(outcome_unicode["status"], "rewarded")


if __name__ == "__main__":
    unittest.main()
