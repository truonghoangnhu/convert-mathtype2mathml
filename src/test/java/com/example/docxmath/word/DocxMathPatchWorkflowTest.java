package com.example.docxmath.word;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;

final class DocxMathPatchWorkflowTest {
    @Test
    void leavesNativeOmmlUntouched() throws Exception {
        Path tempDir = Files.createTempDirectory("docx-patch-native");
        Path input = tempDir.resolve("native.docx");
        Path output = tempDir.resolve("native-out.docx");
        writeMinimalDocx(input, nativeOmmlDocumentXml(), List.of());

        DocxMathPatchMain.PatchSummary summary =
                new DocxMathPatchMain(ManifestMathSidecarRepository.empty()).patch(input, output);

        String xml = readDocumentXml(output);
        assertEquals(1, summary.totalOccurrences());
        assertEquals(1, summary.nativeOmmlUntouched());
        assertEquals(0, summary.patchedBlocks());
        assertEquals(0, summary.patchedInline());
        assertEquals(1, summary.structureBeforePatch().equationCount());
        assertEquals(1, summary.structureBeforePatch().inlineEquationCount());
        assertEquals(0, summary.structureBeforePatch().blockEquationCount());
        assertEquals("inline_only", summary.structureBeforePatch().shapeSummary());
        assertEquals(summary.structureBeforePatch(), summary.structureAfterPatch());
        assertEquals("", summary.ommlDriftWarningToken());
        assertEquals("", summary.ommlDriftClass());
        assertEquals("", summary.ommlDriftPair());
        assertEquals("", summary.ommlDriftBundle());
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
        assertTrue(xml.contains("oMath"));
        assertFalse(xml.contains("<w:object"));
    }

    @Test
    void patchesStandaloneOleObjectWhenManifestMatches() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        PatchRunResult result = runPatch(oleObjectDocumentXml(object), List.of(object), List.of(object));

        assertEquals(1, result.summary.patchedBlocks());
        assertEquals(0, result.summary.patchedInline());
        assertEquals(0, result.summary.unresolved());
        assertEquals(0, result.summary.structureBeforePatch().equationCount());
        assertEquals("no_omml", result.summary.structureBeforePatch().shapeSummary());
        assertEquals(1, result.summary.structureAfterPatch().equationCount());
        assertEquals(0, result.summary.structureAfterPatch().inlineEquationCount());
        assertEquals(1, result.summary.structureAfterPatch().blockEquationCount());
        assertEquals("block_only", result.summary.structureAfterPatch().shapeSummary());
        assertEquals("eq|block|shape", result.summary.ommlDriftWarningToken());
        assertEquals("expected_patch_drift", result.summary.ommlDriftClass());
        assertEquals(
                "before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)",
                result.summary.ommlDriftPair()
        );
        assertEquals(
                "warn:eq|block|shape;class:expected_patch_drift;pair:before(eq:0,inline:0,block:0,shape:no_omml)->after(eq:1,inline:0,block:1,shape:block_only)",
                result.summary.ommlDriftBundle()
        );
        assertTrue(result.xml.contains("oMathPara"));
        assertTrue(result.xml.contains("x+1"));
        assertFalse(result.xml.contains("<w:object"));
    }

    @Test
    void classifiesUnexpectedNativeDriftWhenStructureChangesWithoutPatchingWork() {
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
                List.of(),
                new DocxMathPatchMain.OmmlStructureSnapshot(1, 1, 0, "inline_only"),
                new DocxMathPatchMain.OmmlStructureSnapshot(2, 1, 1, "mixed_inline_block")
        );

        assertEquals("eq|block|shape", summary.ommlDriftWarningToken());
        assertEquals("unexpected_native_drift", summary.ommlDriftClass());
        assertEquals(
                "before(eq:1,inline:1,block:0,shape:inline_only)->after(eq:2,inline:1,block:1,shape:mixed_inline_block)",
                summary.ommlDriftPair()
        );
    }

    @Test
    void patchesSafeInlineObjectBetweenText() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml("", List.of(textRunXml("Alpha "), objectRunXml(object), textRunXml(" omega."))),
                List.of(object),
                List.of(object)
        );

        assertEquals(0, result.summary.patchedBlocks());
        assertEquals(1, result.summary.patchedInline());
        assertEquals(0, result.summary.structureBeforePatch().equationCount());
        assertEquals("no_omml", result.summary.structureBeforePatch().shapeSummary());
        assertEquals(1, result.summary.structureAfterPatch().equationCount());
        assertEquals(1, result.summary.structureAfterPatch().inlineEquationCount());
        assertEquals(0, result.summary.structureAfterPatch().blockEquationCount());
        assertEquals("inline_only", result.summary.structureAfterPatch().shapeSummary());
        assertTrue(result.xml.contains("Alpha "));
        assertTrue(result.xml.contains("omega."));
        assertTrue(result.xml.contains("oMath"));
        assertFalse(result.xml.contains("<w:object"));
    }

    @Test
    void patchesTier3aParagraphWithTwoSeparatedInlineObjects() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(
                                textRunXml("Alpha "),
                                objectRunXml(first),
                                textRunXml(" and "),
                                objectRunXml(second),
                                textRunXml(" omega")
                        )
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(2, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertFalse(result.xml.contains("<w:object"));
        assertContainsInOrder(result.xml, List.of("Alpha ", "a+1", " and ", "b-2", " omega"));
    }

    @Test
    void patchesTier3aParagraphWithThreeSequentialInlineObjects() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "+", "2"));
        MathObjectRef third = mathObjectRef(3, wmfMathml("c", "+", "3"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(
                                textRunXml("Before "),
                                objectRunXml(first),
                                textRunXml(", "),
                                objectRunXml(second),
                                textRunXml(", "),
                                objectRunXml(third),
                                textRunXml(" after")
                        )
                ),
                List.of(first, second, third),
                List.of(first, second, third)
        );

        assertEquals(3, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertContainsInOrder(result.xml, List.of("Before ", "a+1", ", ", "b+2", ", ", "c+3", " after"));
    }

    @Test
    void patchesTier3aParagraphWithObjectAtStartMiddleAndEnd() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("s", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("m", "+", "2"));
        MathObjectRef third = mathObjectRef(3, wmfMathml("e", "+", "3"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(
                                objectRunXml(first),
                                textRunXml(" start "),
                                objectRunXml(second),
                                textRunXml(" end "),
                                objectRunXml(third)
                        )
                ),
                List.of(first, second, third),
                List.of(first, second, third)
        );

        assertEquals(3, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertContainsInOrder(result.xml, List.of("s+1", " start ", "m+2", " end ", "e+3"));
    }

    @Test
    void skipsMultiObjectParagraphWhenAnyManifestEntryIsMissing() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), objectRunXml(first), textRunXml(" B "), objectRunXml(second))
                ),
                List.of(first, second),
                List.of(first)
        );

        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.unresolved());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.multiObjectSkippedUnsafeParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.UNRESOLVED_MANIFEST));
        assertTrue(result.xml.contains("<w:object"));
    }

    @Test
    void skipsMultiObjectParagraphWithNativeOmml() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                nativeOmmlAndMultiObjectDocumentXml(List.of(first, second)),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(1, result.summary.nativeOmmlUntouched());
        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.multiObjectSkippedUnsafeParagraphs());
        assertTrue(result.xml.contains("oMath"));
        assertTrue(result.xml.contains("<w:object"));
    }

    @Test
    void copiesInputBytesWhenMixedNativeOmmlCaseSkipsPatchWork() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        Path tempDir = Files.createTempDirectory("docx-patch-mixed-copy");
        Path input = tempDir.resolve("input.docx");
        Path output = tempDir.resolve("output.docx");
        writeMinimalDocx(input, nativeOmmlAndMultiObjectDocumentXml(List.of(first, second)), List.of(first, second));

        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(
                ManifestMathSidecarRepository.load(writeManifest(tempDir, List.of(first, second)))
        ).patch(input, output);

        assertEquals(1, summary.nativeOmmlUntouched());
        assertEquals(0, summary.patchedBlocks());
        assertEquals(0, summary.patchedInline());
        assertEquals(0, summary.unresolved());
        assertEquals(1, summary.skippedMultiObjectParagraphs());
        assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.NATIVE_OMML_PRESENT));
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
    }

    @Test
    void skipsMultiObjectParagraphWhenOneObjectHasUnknownSourceType() throws Exception {
        MathObjectRef known = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef unknown = new MathObjectRef(
                2,
                "rIdOle2",
                "rIdPreview2",
                "/word/embeddings/oleObject2.dat",
                "/word/media/image2.png",
                wmfMathml("u", "+", "9")
        );
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), objectRunXml(known), textRunXml(" B "), objectRunXml(unknown))
                ),
                List.of(known, unknown),
                List.of(known, unknown)
        );

        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.multiObjectSkippedAmbiguousParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.UNKNOWN_SOURCE_KIND));
        assertTrue(result.xml.contains("<w:object"));
    }

    @Test
    void skipsMultiObjectParagraphWithUnsafeRunStructure() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), unsafeMixedRunXml(first), textRunXml(" B "), objectRunXml(second))
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.multiObjectSkippedUnsafeParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.DRAWING_IN_RUN));
        assertEquals(0, result.summary.skipBreakdownCount(PatchSkipReason.LAST_RENDERED_PAGE_BREAK_IN_RUN));
        assertEquals(PatchSkipReason.values().length, result.summary.skipBreakdown().size());
        assertTrue(result.xml.contains("<w:object"));
    }

    @Test
    void patchesMultiObjectParagraphWithBenignStandaloneDrawingRun() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(
                                textRunXml(" C."),
                                textRunXml(" "),
                                standaloneDrawingRunXml(),
                                textRunXml(" D."),
                                textRunXml(" Cl - Cl "),
                                objectRunXml(first),
                                textRunXml(" "),
                                objectRunXml(second)
                        )
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(2, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertEquals(0, result.summary.skipBreakdownCount(PatchSkipReason.DRAWING_IN_RUN));
        assertTrue(result.xml.contains("<w:drawing>"));
        assertContainsInOrder(result.xml, List.of(" C.", " D.", " Cl - Cl ", "a+1", " ", "b-2"));
    }

    @Test
    void keepsOleObjectWhenManifestIsUnresolved() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        PatchRunResult result = runPatch(oleObjectDocumentXml(object), List.of(object), List.of());

        assertEquals(1, result.summary.unresolved());
        assertEquals(0, result.summary.patchedBlocks());
        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.UNRESOLVED_MANIFEST));
        assertTrue(result.xml.contains("<w:object"));
    }

    @Test
    void copiesInputBytesWhenUnresolvedObjectSkipsAllPatchWork() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        Path tempDir = Files.createTempDirectory("docx-patch-unresolved-copy");
        Path input = tempDir.resolve("input.docx");
        Path output = tempDir.resolve("output.docx");
        writeMinimalDocx(input, oleObjectDocumentXml(object), List.of(object));

        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(
                ManifestMathSidecarRepository.load(writeManifest(tempDir, List.of()))
        ).patch(input, output);

        assertEquals(1, summary.unresolved());
        assertEquals(0, summary.patchedBlocks());
        assertEquals(0, summary.patchedInline());
        assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.UNRESOLVED_MANIFEST));
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
    }

    @Test
    void patchesMultiObjectParagraphWithBenignLastRenderedPageBreak() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), pageBreakRunXml(first), textRunXml(" B "), objectRunXml(second))
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(2, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertEquals(0, result.summary.skipBreakdownCount(PatchSkipReason.LAST_RENDERED_PAGE_BREAK_IN_RUN));
        assertContainsInOrder(result.xml, List.of("A ", "a+1", " B ", "b-2"));
    }

    @Test
    void skipsLastRenderedPageBreakCaseWhenRunStillMixesObjectAndText() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), pageBreakAndTextRunXml(first, " inline "), objectRunXml(second))
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.MIXED_OBJECT_AND_TEXT_IN_RUN));
        assertEquals(0, result.summary.skipBreakdownCount(PatchSkipReason.LAST_RENDERED_PAGE_BREAK_IN_RUN));
        assertEquals(0, result.summary.skipBreakdownCount(PatchSkipReason.DRAWING_IN_RUN));
    }

    @Test
    void skipsDrawingCaseWhenRunStillMixesDrawingAndText() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), drawingAndTextRunXml(" helper "), objectRunXml(first), objectRunXml(second))
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.DRAWING_IN_RUN));
    }

    @Test
    void skipBreakdownKeepsStableEnumOrder() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("A "), unsafeMixedRunXml(first), textRunXml(" B "), objectRunXml(second))
                ),
                List.of(first, second),
                List.of(first, second)
        );

        assertEquals(
                Arrays.stream(PatchSkipReason.values()).toList(),
                result.summary.skipBreakdown().stream().map(DocxMathPatchMain.SkipBreakdownEntry::reason).toList()
        );
    }

    private PatchRunResult runPatch(
            String documentXml,
            List<MathObjectRef> documentObjects,
            List<MathObjectRef> manifestObjects
    ) throws Exception {
        Path tempDir = Files.createTempDirectory("docx-patch-workflow");
        Path input = tempDir.resolve("input.docx");
        Path output = tempDir.resolve("output.docx");
        writeMinimalDocx(input, documentXml, documentObjects);
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(
                ManifestMathSidecarRepository.load(writeManifest(tempDir, manifestObjects))
        ).patch(input, output);
        return new PatchRunResult(summary, readDocumentXml(output));
    }

    private static Path writeManifest(Path tempDir, List<MathObjectRef> objects) throws IOException {
        Path manifestDir = tempDir.resolve("sidecars");
        Files.createDirectories(manifestDir.resolve("mathml"));
        Path manifest = manifestDir.resolve("manifest.tsv");
        StringBuilder manifestText = new StringBuilder();
        int index = 1;
        for (MathObjectRef object : objects) {
            String fileName = "eq" + index + ".mathml";
            manifestText.append(object.olePartName()).append('\t').append("mathml/").append(fileName).append('\n');
            Files.writeString(manifestDir.resolve("mathml").resolve(fileName), object.mathml(), StandardCharsets.UTF_8);
            index++;
        }
        Files.writeString(manifest, manifestText.toString(), StandardCharsets.UTF_8);
        return manifest;
    }

    private static void writeMinimalDocx(Path path, String documentXml, List<MathObjectRef> objects) throws IOException {
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(path))) {
            put(zip, "[Content_Types].xml", contentTypesXml());
            put(zip, "_rels/.rels", packageRelationshipsXml());
            put(zip, "word/document.xml", documentXml);
            put(zip, "word/_rels/document.xml.rels", documentRelationshipsXml(objects));
            for (MathObjectRef object : objects) {
                put(zip, object.olePartName().substring(1), "dummy");
                put(zip, object.previewPartName().substring(1), "dummy");
            }
        }
    }

    private static void put(ZipOutputStream zip, String entryName, String text) throws IOException {
        zip.putNextEntry(new ZipEntry(entryName));
        zip.write(text.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }

    private static String readDocumentXml(Path docx) throws IOException {
        try (var zip = new java.util.zip.ZipFile(docx.toFile())) {
            return new String(zip.getInputStream(zip.getEntry("word/document.xml")).readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static String contentTypesXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                  <Default Extension="xml" ContentType="application/xml"/>
                  <Default Extension="bin" ContentType="application/vnd.openxmlformats-officedocument.oleObject"/>
                  <Default Extension="dat" ContentType="application/octet-stream"/>
                  <Default Extension="wmf" ContentType="image/x-wmf"/>
                  <Default Extension="png" ContentType="image/png"/>
                  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                </Types>
                """;
    }

    private static String packageRelationshipsXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                </Relationships>
                """;
    }

    private static String documentRelationshipsXml(List<MathObjectRef> objects) {
        String relationships = objects.stream()
                .flatMap(object -> List.of(
                        "<Relationship Id=\"" + object.oleRelId() + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject\" Target=\"" + object.oleTarget() + "\"/>",
                        "<Relationship Id=\"" + object.previewRelId() + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"" + object.previewTarget() + "\"/>"
                ).stream())
                .collect(Collectors.joining("\n      "));
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  %s
                </Relationships>
                """.formatted(relationships);
    }

    private static String nativeOmmlDocumentXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
                  <w:body>
                    <w:p>
                      <m:oMath>
                        <m:r><m:t>x</m:t></m:r>
                      </m:oMath>
                    </w:p>
                    %s
                  </w:body>
                </w:document>
                """.formatted(sectionXml());
    }

    private static String oleObjectDocumentXml(MathObjectRef object) {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                            xmlns:o="urn:schemas-microsoft-com:office:office"
                            xmlns:v="urn:schemas-microsoft-com:vml"
                            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
                  <w:body>
                    <w:p>
                      %s
                    </w:p>
                    %s
                  </w:body>
                </w:document>
                """.formatted(objectRunXml(object), sectionXml());
    }

    private static String inlineObjectDocumentXml(String prefixXml, List<String> segments) {
        String joined = segments.stream().collect(Collectors.joining("\n      "));
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                            xmlns:o="urn:schemas-microsoft-com:office:office"
                            xmlns:v="urn:schemas-microsoft-com:vml"
                            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
                  <w:body>
                    <w:p>
                      %s
                      %s
                    </w:p>
                    %s
                  </w:body>
                </w:document>
                """.formatted(prefixXml, joined, sectionXml());
    }

    private static String nativeOmmlAndMultiObjectDocumentXml(List<MathObjectRef> objects) {
        return inlineObjectDocumentXml(
                "<m:oMath><m:r><m:t>z</m:t></m:r></m:oMath>",
                List.of(textRunXml("mix "), objectRunXml(objects.get(0)), textRunXml(" + "), objectRunXml(objects.get(1)))
        );
    }

    private static String sectionXml() {
        return """
                    <w:sectPr>
                      <w:pgSz w:w="12240" w:h="15840"/>
                      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
                    </w:sectPr>
                """;
    }

    private static String textRunXml(String text) {
        if (text == null || text.isEmpty()) {
            return "";
        }
        return "<w:r><w:t xml:space=\"preserve\">" + escapeXml(text) + "</w:t></w:r>";
    }

    private static String objectRunXml(MathObjectRef object) {
        return """
                <w:r>
                  <w:object>
                    <v:shape id="_x0000_i1025" type="#_x0000_t75" o:ole="">
                      <v:imagedata r:id="%s" o:title=""/>
                    </v:shape>
                    <o:OLEObject Type="Embed" ProgID="Equation.DSMT4" ShapeID="_x0000_i1025" DrawAspect="Content" ObjectID="_1" r:id="%s"/>
                  </w:object>
                </w:r>
                """.formatted(object.previewRelId(), object.oleRelId());
    }

    private static String unsafeMixedRunXml(MathObjectRef object) {
        return """
                <w:r>
                  <w:object>
                    <v:shape id="_x0000_i1025" type="#_x0000_t75" o:ole="">
                      <v:imagedata r:id="%s" o:title=""/>
                    </v:shape>
                    <o:OLEObject Type="Embed" ProgID="Equation.DSMT4" ShapeID="_x0000_i1025" DrawAspect="Content" ObjectID="_1" r:id="%s"/>
                  </w:object>
                  <w:drawing/>
                </w:r>
                """.formatted(object.previewRelId(), object.oleRelId());
    }

    private static String standaloneDrawingRunXml() {
        return """
                <w:r>
                  <w:rPr><w:noProof/></w:rPr>
                  <w:drawing>
                    <wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
                      <wp:extent cx="3076575" cy="238125"/>
                      <wp:docPr id="10008" name="Picture 10008"/>
                      <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                        <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"/>
                      </a:graphic>
                    </wp:inline>
                  </w:drawing>
                </w:r>
                """;
    }

    private static String drawingAndTextRunXml(String text) {
        return """
                <w:r>
                  <w:rPr><w:noProof/></w:rPr>
                  <w:drawing>
                    <wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
                      <wp:extent cx="3076575" cy="238125"/>
                      <wp:docPr id="10008" name="Picture 10008"/>
                      <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                        <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"/>
                      </a:graphic>
                    </wp:inline>
                  </w:drawing>
                  <w:t xml:space="preserve">%s</w:t>
                </w:r>
                """.formatted(escapeXml(text));
    }

    private static String pageBreakRunXml(MathObjectRef object) {
        return """
                <w:r>
                  <w:object>
                    <v:shape id="_x0000_i1025" type="#_x0000_t75" o:ole="">
                      <v:imagedata r:id="%s" o:title=""/>
                    </v:shape>
                    <o:OLEObject Type="Embed" ProgID="Equation.DSMT4" ShapeID="_x0000_i1025" DrawAspect="Content" ObjectID="_1" r:id="%s"/>
                  </w:object>
                  <w:lastRenderedPageBreak/>
                </w:r>
                """.formatted(object.previewRelId(), object.oleRelId());
    }

    private static String pageBreakAndTextRunXml(MathObjectRef object, String trailingText) {
        return """
                <w:r>
                  <w:object>
                    <v:shape id="_x0000_i1025" type="#_x0000_t75" o:ole="">
                      <v:imagedata r:id="%s" o:title=""/>
                    </v:shape>
                    <o:OLEObject Type="Embed" ProgID="Equation.DSMT4" ShapeID="_x0000_i1025" DrawAspect="Content" ObjectID="_1" r:id="%s"/>
                  </w:object>
                  <w:lastRenderedPageBreak/>
                  <w:t xml:space="preserve">%s</w:t>
                </w:r>
                """.formatted(object.previewRelId(), object.oleRelId(), escapeXml(trailingText));
    }

    private static String escapeXml(String text) {
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private static void assertContainsInOrder(String haystack, List<String> needles) {
        int from = 0;
        for (String needle : needles) {
            int index = haystack.indexOf(needle, from);
            assertTrue(index >= 0, "Expected to find <" + needle + "> after offset " + from);
            from = index + needle.length();
        }
    }

    private static MathObjectRef mathObjectRef(int index, String mathml) {
        return new MathObjectRef(
                index,
                "rIdOle" + index,
                "rIdPreview" + index,
                "/word/embeddings/oleObject" + index + ".bin",
                "/word/media/image" + index + ".wmf",
                mathml
        );
    }

    private static String wmfMathml(String left, String operator, String right) {
        return """
                <math xmlns="http://www.w3.org/1998/Math/MathML">
                  <mi>%s</mi><mo>%s</mo><mn>%s</mn>
                </math>
                """.formatted(left, operator, right);
    }

    private record PatchRunResult(DocxMathPatchMain.PatchSummary summary, String xml) {
    }

    private record MathObjectRef(
            int index,
            String oleRelId,
            String previewRelId,
            String olePartName,
            String previewPartName,
            String mathml
    ) {
        private String oleTarget() {
            return olePartName.substring("/word/".length());
        }

        private String previewTarget() {
            return previewPartName.substring("/word/".length());
        }
    }
}
