import unittest
from pathlib import Path

from scripts.batch.run_subject_batch import safe_artifact_part, safe_artifact_stem


class BatchArtifactPathTests(unittest.TestCase):
    def test_safe_artifact_part_preserves_existing_safe_name(self) -> None:
        self.assertEqual(safe_artifact_part("Hoa_2026_Big"), "Hoa_2026_Big")

    def test_safe_artifact_part_rewrites_spacey_name(self) -> None:
        value = safe_artifact_part("de 1202")
        self.assertTrue(value.startswith("de-1202--"))
        self.assertNotIn(" ", value)

    def test_safe_artifact_part_rewrites_unicode_decorative_name(self) -> None:
        value = safe_artifact_part(" Câu 1")
        self.assertTrue(value.startswith("Cau-1--"))
        self.assertNotIn(" ", value)

    def test_safe_artifact_stem_rewrites_each_path_part(self) -> None:
        stem = safe_artifact_stem(Path("2026-04-14/Pham Nghia"))
        self.assertEqual(stem.parts[0], "2026-04-14")
        self.assertTrue(stem.parts[1].startswith("Pham-Nghia--"))
        self.assertNotIn(" ", str(stem))


if __name__ == "__main__":
    unittest.main()
