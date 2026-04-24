package com.example.docxmath;

import com.example.docxmath.word.DocxMathPatchMain;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class DocxToHtmlCliPatchSummaryJsonlTest {
    @Test
    void omitsDriftFieldsFromJsonRecordWhenNoDriftExists() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only")
        );

        String record = DocxToHtmlCli.buildPatchSummaryJsonRecord(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary
        );

        assertTrue(record.contains("\"omml_preservation\":\"preserved\""));
        assertTrue(record.contains("\"omml_before\":\"eq:1,inline:1,block:0,shape:inline_only\""));
        assertTrue(record.contains("\"omml_after\":\"eq:1,inline:1,block:0,shape:inline_only\""));
        assertFalse(record.contains("\"omml_drift_warning\""));
        assertFalse(record.contains("\"omml_drift_class\""));
        assertFalse(record.contains("\"omml_drift_pair\""));
        assertFalse(record.contains("\"omml_drift_bundle\""));
    }

    @Test
    void includesStableDriftFieldsInJsonRecordWhenDriftExists() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(0, 0, 0, "no_omml"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 0, 1, "block_only")
        );

        String record = DocxToHtmlCli.buildPatchSummaryJsonRecord(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                Path.of("/tmp/manifest.tsv"),
                summary
        );

        assertTrue(record.contains("\"mathml_manifest\":\"/tmp/manifest.tsv\""));
        assertTrue(record.contains("\"omml_preservation\":\"drift_expected:eq|block|shape\""));
        assertTrue(record.contains("\"omml_drift_warning\":\"eq|block|shape\""));
        assertTrue(record.contains("\"omml_drift_class\":\"expected_patch_drift\""));
        assertTrue(record.contains("\"omml_drift_pair\":\"before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)\""));
        assertTrue(record.contains("\"omml_drift_bundle\":\"warn:eq|block|shape;class:expected_patch_drift;pair:before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)\""));
    }

    @Test
    void rendersNoDriftStdoutJsonlRecord() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only")
        );

        String rendered = DocxToHtmlCli.renderPatchSummaryOutput(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary,
                true
        );

        assertTrue(rendered.startsWith("{"));
        assertTrue(rendered.endsWith(System.lineSeparator()));
        assertTrue(rendered.contains("\"omml_preservation\":\"preserved\""));
        assertTrue(rendered.contains("\"omml_before\":\"eq:1,inline:1,block:0,shape:inline_only\""));
        assertFalse(rendered.contains("\"omml_drift_warning\""));
        assertFalse(rendered.contains("Patch summary:"));
    }

    @Test
    void rendersDriftStdoutJsonlRecord() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(0, 0, 0, "no_omml"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 0, 1, "block_only")
        );

        String rendered = DocxToHtmlCli.renderPatchSummaryOutput(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary,
                true
        );

        assertTrue(rendered.contains("\"omml_preservation\":\"drift_expected:eq|block|shape\""));
        assertTrue(rendered.contains("\"omml_drift_warning\":\"eq|block|shape\""));
        assertTrue(rendered.contains("\"omml_drift_class\":\"expected_patch_drift\""));
        assertTrue(rendered.contains("\"omml_drift_pair\":\"before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)\""));
        assertTrue(rendered.contains("\"omml_drift_bundle\":\"warn:eq|block|shape;class:expected_patch_drift;pair:before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)\""));
    }

    @Test
    void rendersHumanSummaryWithStableOmmlPreservationToken() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only")
        );

        String rendered = DocxToHtmlCli.renderPatchSummaryOutput(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary,
                false
        );

        assertTrue(rendered.contains("Patch summary:"));
        assertTrue(rendered.contains(" omml_preservation=preserved "));
    }

    @Test
    void rendersHumanSummaryWithDeterministicExpectedDriftOmmlPreservationToken() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(0, 0, 0, "no_omml"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 0, 1, "block_only")
        );

        String rendered = DocxToHtmlCli.renderPatchSummaryOutput(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary,
                false
        );

        assertTrue(rendered.contains("Patch summary:"));
        assertTrue(rendered.contains(" omml_preservation=drift_expected:eq|block|shape "));
    }

    @Test
    void rendersHumanSummaryWithDeterministicUnexpectedDriftOmmlPreservationToken() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only"),
                new DocxMathPatchMain.OmmlStructureSnapshot(2, 1, 1, "mixed_inline_block")
        );

        String rendered = DocxToHtmlCli.renderPatchSummaryOutput(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary,
                false
        );

        assertTrue(rendered.contains("Patch summary:"));
        assertTrue(rendered.contains(" omml_preservation=drift_unexpected:eq|block|shape "));
    }

    @Test
    void keepsStableHumanSummaryFieldOrderingAroundOmmlPreservation() throws Exception {
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain.PatchSummary(
                1,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                java.util.List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only"),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only")
        );

        String rendered = DocxToHtmlCli.renderPatchSummaryOutput(
                Path.of("/tmp/in.docx"),
                Path.of("/tmp/out.docx"),
                null,
                summary,
                false
        );

        String summaryLine = Arrays.stream(rendered.split("\\R"))
                .filter(line -> line.startsWith("Patch summary: "))
                .findFirst()
                .orElse("");
        assertTrue(summaryLine.contains(" multi_skipped_ambiguous=0"));
        assertTrue(summaryLine.contains(" omml_preservation=preserved"));
        assertTrue(summaryLine.contains(" omml_before=eq:1,inline:1,block:0,shape:inline_only"));
        assertTrue(
                summaryLine.indexOf(" multi_skipped_ambiguous=0")
                        < summaryLine.indexOf(" omml_preservation=preserved")
                        && summaryLine.indexOf(" omml_preservation=preserved")
                        < summaryLine.indexOf(" omml_before=eq:1,inline:1,block:0,shape:inline_only")
        );
    }
}
