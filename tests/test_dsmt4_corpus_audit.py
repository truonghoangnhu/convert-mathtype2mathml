from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "audit_dsmt4_corpus.py"
SPEC = importlib.util.spec_from_file_location("audit_dsmt4_corpus", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Dsmt4CorpusAuditTest(unittest.TestCase):
    def test_normalize_key(self) -> None:
        self.assertEqual(MODULE.normalize_key("Vat_Ly_Le_Khiet"), "vatlylekhiet")
        self.assertEqual(MODULE.base_family_name("toan-2026-big--3457e9e43ced"), "toan-2026-big")

    def test_metadata_only_pattern_detects_full_end_only(self) -> None:
        payload_class = {
            "deep_audit": {
                "bin_mtef_summary": {"tail_after_eqn_prefs": ["full", "end"]},
                "preview_mtef_summary": {"tail_after_eqn_prefs": ["full", "end"]},
            }
        }

        pattern = MODULE.metadata_only_pattern(payload_class)

        self.assertEqual(pattern, "FULL_END_ONLY_AFTER_EQN_PREFS")

    def test_classify_pattern_class_distinguishes_metadata_vs_empty_sidecar(self) -> None:
        metadata_pattern = MODULE.classify_pattern_class(
            assessment={"result": "TOP_LEVEL_FULL_END_ONLY"},
            bin_summary={"metadata_only": True},
            preview_summary={"metadata_only": True},
            bin_parser={"status": "ok"},
            preview_parser={"status": "ok"},
            bin_sidecar_status="empty_math",
            preview_sidecar_status="empty_math",
        )
        empty_sidecar_pattern = MODULE.classify_pattern_class(
            assessment={"result": "BODY_PRESENT_BUT_EMPTY_MATHML"},
            bin_summary={"metadata_only": False},
            preview_summary={"metadata_only": False},
            bin_parser={"status": "ok"},
            preview_parser={"status": "ok"},
            bin_sidecar_status="empty_math",
            preview_sidecar_status="empty_math",
        )

        self.assertEqual(metadata_pattern, "METADATA_ONLY_FULL_END_ONLY")
        self.assertEqual(empty_sidecar_pattern, "EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY")

    def test_decide_corpus_label_requires_more_than_one_class_to_confirm(self) -> None:
        aggregate = {
            "dsmt4_metadata_only_classes_total_combined": 1,
            "dsmt4_metadata_only_sources_total_combined": 1,
            "dsmt4_empty_generated_sidecar_classes": 0,
            "dsmt4_other_parser_pattern_classes": 0,
        }

        decision = MODULE.decide_corpus_label(aggregate)

        self.assertEqual(decision, "INSUFFICIENT_EVIDENCE_NEED_MORE_CORPUS")

    def test_decide_corpus_label_confirms_repeated_metadata_only_pattern(self) -> None:
        aggregate = {
            "dsmt4_metadata_only_classes_total_combined": 2,
            "dsmt4_metadata_only_sources_total_combined": 1,
            "dsmt4_empty_generated_sidecar_classes": 0,
            "dsmt4_other_parser_pattern_classes": 0,
        }

        decision = MODULE.decide_corpus_label(aggregate)

        self.assertEqual(decision, "CONFIRMED_UNSUPPORTED_OR_DEGENERATE_PAYLOAD_CLASS")

    def test_sort_docx_candidates_prefers_underscore_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plain = root / "Toan_2026_Big.docx"
            underscore = root / "_Toan_2026_Big.docx"
            another = root / "_Hoa_2026_Big.docx"
            for path in [plain, underscore, another]:
                path.write_bytes(b"docx")

            ordered = MODULE.sort_docx_candidates([plain, underscore, another], prefer_underscore_first=True)

            self.assertEqual([path.name for path in ordered], ["_Hoa_2026_Big.docx", "_Toan_2026_Big.docx", "Toan_2026_Big.docx"])

    def test_aggregate_payload_classes_counts_buckets(self) -> None:
        payload_classes = [
            {
                "class_key": "bin-a|wmf-a",
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "pattern_stage": "GENERATED_SIDECAR",
                "pattern_signature": {"pattern_class": "RENDERABLE_BODY_PRESENT"},
                "pattern_signature_key": "sig-renderable",
                "occurrence_count": 3,
                "source_names": ["math-1202"],
                "preset_names": ["math-1202"],
                "source_group": "registry",
                "source_kind": "registry",
                "registry_source_names": ["math-1202"],
                "external_source_names": [],
                "source_families": ["math-1202"],
                "deep_audit": None,
            },
            {
                "class_key": "bin-b|wmf-b",
                "bucket": "METADATA_ONLY_PAYLOAD",
                "pattern_class": "METADATA_ONLY_FULL_END_ONLY",
                "pattern_stage": "PARSER_INPUT_PAYLOAD",
                "pattern_signature": {"pattern_class": "METADATA_ONLY_FULL_END_ONLY"},
                "pattern_signature_key": "sig-full-end",
                "occurrence_count": 2,
                "source_names": ["math-deso-11-tb"],
                "preset_names": ["math-deso-11-tb"],
                "source_group": "registry",
                "source_kind": "registry",
                "registry_source_names": ["math-deso-11-tb"],
                "external_source_names": [],
                "source_families": ["math-deso-11-tb"],
                "deep_audit": {
                    "payload_comparison": {"same_effective_payload": True},
                    "bin_mtef_summary": {"tail_after_eqn_prefs": ["full", "end"]},
                    "preview_mtef_summary": {"tail_after_eqn_prefs": ["full", "end"]},
                },
            },
        ]

        aggregate = MODULE.aggregate_payload_classes(
            payload_classes,
            registry_sources=[{"name": "math-1202"}, {"name": "math-deso-11-tb"}],
            external_sources=[],
        )

        self.assertEqual(aggregate["dsmt4_payload_classes_total"], 2)
        self.assertEqual(aggregate["dsmt4_occurrences_total"], 5)
        self.assertEqual(aggregate["dsmt4_registry_occurrences_total"], 5)
        self.assertEqual(aggregate["dsmt4_renderable_classes"], 1)
        self.assertEqual(aggregate["dsmt4_metadata_only_classes"], 1)
        self.assertEqual(aggregate["dsmt4_same_effective_payload_classes"], 1)
        self.assertEqual(aggregate["dsmt4_pattern_classes_total"], 2)
        self.assertEqual(aggregate["dsmt4_pattern_metadata_only_full_end_only_classes"], 1)
        self.assertEqual(aggregate["metadata_only_patterns"], {"FULL_END_ONLY_AFTER_EQN_PREFS": 1})
        self.assertEqual(aggregate["top_degenerate_pattern_classes"][0]["pattern_class"], "METADATA_ONLY_FULL_END_ONLY")

    def test_aggregate_payload_classes_counts_external_new_vs_existing(self) -> None:
        payload_classes = [
            {
                "class_key": "shared|preview-shared",
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "pattern_stage": "GENERATED_SIDECAR",
                "pattern_signature": {"pattern_class": "RENDERABLE_BODY_PRESENT"},
                "pattern_signature_key": "sig-shared-renderable",
                "occurrence_count": 3,
                "source_names": ["physics-le-khiet"],
                "preset_names": ["physics-le-khiet"],
                "source_group": "registry",
                "source_kind": "registry",
                "registry_source_names": ["physics-le-khiet"],
                "external_source_names": [],
                "source_families": ["physics-le-khiet"],
                "deep_audit": None,
            },
            {
                "class_key": "shared|preview-shared",
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "pattern_stage": "GENERATED_SIDECAR",
                "pattern_signature": {"pattern_class": "RENDERABLE_BODY_PRESENT"},
                "pattern_signature_key": "sig-shared-renderable",
                "occurrence_count": 2,
                "source_names": ["external-workdir:work/batches/other/Vat_Ly_Le_Khiet"],
                "preset_names": ["external-workdir:work/batches/other/Vat_Ly_Le_Khiet"],
                "source_group": "external",
                "source_kind": "external_workdir",
                "registry_source_names": [],
                "external_source_names": ["external-workdir:work/batches/other/Vat_Ly_Le_Khiet"],
                "source_families": ["Vat_Ly_Le_Khiet"],
                "deep_audit": None,
            },
            {
                "class_key": "new|preview-new",
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "pattern_stage": "GENERATED_SIDECAR",
                "pattern_signature": {"pattern_class": "RENDERABLE_BODY_PRESENT"},
                "pattern_signature_key": "sig-new-renderable",
                "occurrence_count": 1,
                "source_names": ["external-docx:/tmp/new.docx"],
                "preset_names": ["external-docx:/tmp/new.docx"],
                "source_group": "external",
                "source_kind": "external_docx",
                "registry_source_names": [],
                "external_source_names": ["external-docx:/tmp/new.docx"],
                "source_families": ["new"],
                "deep_audit": None,
            },
        ]

        aggregate = MODULE.aggregate_payload_classes(
            payload_classes,
            registry_sources=[{"name": "physics-le-khiet"}],
            external_sources=[{"name": "external-workdir:work/batches/other/Vat_Ly_Le_Khiet", "source_kind": "external_workdir"}, {"name": "external-docx:/tmp/new.docx", "source_kind": "external_docx"}],
        )

        self.assertEqual(aggregate["dsmt4_registry_payload_classes_total"], 1)
        self.assertEqual(aggregate["dsmt4_external_payload_classes_total"], 2)
        self.assertEqual(aggregate["dsmt4_external_existing_payload_classes_total"], 1)
        self.assertEqual(aggregate["dsmt4_external_new_payload_classes_total"], 1)
        self.assertEqual(aggregate["dsmt4_payload_classes_total"], 2)
        self.assertEqual(aggregate["external_files_scanned"], 1)

    def test_summarize_external_sources_counts_new_classes_so_far(self) -> None:
        payload_classes = [
            {
                "class_key": "shared|preview-shared",
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "occurrence_count": 3,
                "source_names": ["physics-le-khiet"],
                "source_group": "registry",
            },
            {
                "class_key": "shared|preview-shared",
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "occurrence_count": 2,
                "source_names": ["external-workdir:work/batches/other/Vat_Ly_Le_Khiet"],
                "source_group": "external",
                "deep_audit": None,
            },
            {
                "class_key": "new|preview-new",
                "bucket": "METADATA_ONLY_PAYLOAD",
                "pattern_class": "METADATA_ONLY_FULL_END_ONLY",
                "occurrence_count": 1,
                "source_names": ["external-docx:/tmp/_Toan_2026_Big.docx"],
                "source_group": "external",
                "deep_audit": {
                    "bin_mtef_summary": {"tail_after_eqn_prefs": ["full", "end"]},
                    "preview_mtef_summary": {"tail_after_eqn_prefs": ["full", "end"]},
                },
            },
        ]

        summaries = MODULE.summarize_external_sources(
            payload_classes=payload_classes,
            registry_sources=[{"name": "physics-le-khiet"}],
            external_sources=[
                {"name": "external-workdir:work/batches/other/Vat_Ly_Le_Khiet", "source_kind": "external_workdir", "workdir": "/tmp/a", "docx_path": None},
                {"name": "external-docx:/tmp/_Toan_2026_Big.docx", "source_kind": "external_docx", "workdir": "/tmp/b", "docx_path": "/tmp/_Toan_2026_Big.docx"},
            ],
        )

        self.assertEqual(summaries[0]["dsmt4_new_payload_classes_so_far"], 0)
        self.assertEqual(summaries[1]["dsmt4_new_payload_classes_so_far"], 1)
        self.assertTrue(summaries[1]["full_end_only_present"])
        self.assertEqual(summaries[1]["top_pattern_classes"][0]["pattern_class"], "METADATA_ONLY_FULL_END_ONLY")


if __name__ == "__main__":
    unittest.main()
