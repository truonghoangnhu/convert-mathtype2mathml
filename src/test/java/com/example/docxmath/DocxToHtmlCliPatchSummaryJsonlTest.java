package com.example.docxmath;

import com.example.docxmath.word.DocxMathPatchMain;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;

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

        assertTrue(rendered.contains("\"omml_drift_warning\":\"eq|block|shape\""));
        assertTrue(rendered.contains("\"omml_drift_class\":\"expected_patch_drift\""));
        assertTrue(rendered.contains("\"omml_drift_pair\":\"before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)\""));
        assertTrue(rendered.contains("\"omml_drift_bundle\":\"warn:eq|block|shape;class:expected_patch_drift;pair:before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)\""));
    }
}
