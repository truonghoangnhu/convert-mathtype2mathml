import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "contracts" / "generate_output_contract.py"
SPEC = importlib.util.spec_from_file_location("generate_output_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def parse_questions(html_text: str):
    parsed = MODULE.parse_html_structure(html_text)
    return parsed["questions"]


class QuestionHeaderNormalizationTests(unittest.TestCase):
    def test_standard_cau_marker_still_detected(self):
        questions = parse_questions("<p>Câu 1. Nội dung câu hỏi.</p>")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_number, 1)

    def test_decorative_right_angle_quote_prefix_detected(self):
        questions = parse_questions("<p>\u00bb Câu 1. Nội dung câu hỏi.</p>")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_number, 1)

    def test_decorative_bullet_prefix_detected(self):
        questions = parse_questions("<p>\u2022 Câu 1. Nội dung câu hỏi.</p>")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_number, 1)

    def test_decorative_prefix_with_weird_spacing_detected(self):
        questions = parse_questions("<p>\uf040   Câu   1. Nội dung câu hỏi.</p>")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_number, 1)

    def test_decorative_prefix_preserves_existing_english_question_detection(self):
        questions = parse_questions("<p>\u00bb Question 1. Choose the correct answer.</p>")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_number, 1)

    def test_plain_bullet_paragraph_does_not_become_question(self):
        questions = parse_questions("<p>\u2022 Ghi chú ôn tập trước khi làm bài.</p>")
        self.assertEqual(len(questions), 0)

    def test_answer_choices_do_not_become_question_starts(self):
        html_text = (
            "<p>\u2022 Câu 1. Chọn đáp án đúng.</p>"
            "<p>A. Phương án A.</p>"
            "<p>B. Phương án B.</p>"
            "<p>C. Phương án C.</p>"
            "<p>D. Phương án D.</p>"
        )
        questions = parse_questions(html_text)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_number, 1)

    def test_true_false_markers_still_parse_as_true_false(self):
        html_text = (
            "<p>\u00bb Câu 1. Xét các phát biểu sau đây đúng sai.</p>"
            "<p>(a) Mệnh đề 1.</p>"
            "<p>(b) Mệnh đề 2.</p>"
            "<p>(c) Mệnh đề 3.</p>"
            "<p>(d) Mệnh đề 4.</p>"
        )
        questions = parse_questions(html_text)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_type, "true_false")


if __name__ == "__main__":
    unittest.main()
