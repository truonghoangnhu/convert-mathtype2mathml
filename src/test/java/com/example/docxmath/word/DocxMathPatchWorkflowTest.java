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
    void retainsOriginalPackageForMixedTextWithUnsafeLetterlikeSymbols() throws Exception {
        for (String token : List.of("xℝ", "khối ℓ", "ℤ kg", "tập ℕ", "z ∈ ℂ", "tập ℚ", "𝐯 = 2", "ℝ\u00a0")) {
            var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mtext>"
                    + token + "</mtext></math>");
            Path dir = Files.createTempDirectory("mixed-letterlike");
            Path source = dir.resolve("source.docx");
            Path output = dir.resolve("output.docx");
            writeMinimalDocx(source, oleObjectDocumentXml(object), List.of(object));
            var summary = new DocxMathPatchMain(ManifestMathSidecarRepository.load(
                    writeManifest(dir, List.of(object)))).patch(source, output);
            assertEquals(0, summary.patchedBlocks() + summary.patchedInline(), token);
            assertEquals(1, summary.unresolved(), token);
            assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.OMML_CONVERSION_FAILED), token);
            assertEquals(java.util.Map.of("normal_text_symbol_requires_review", 1), summary.conversionDiagnostics(), token);
            assertArrayEquals(Files.readAllBytes(source), Files.readAllBytes(output), token);
        }
    }

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
        assertEquationTexts(result.xml, List.of("x+1"));
        assertFalse(result.xml.contains("<w:object"));
    }

    @Test
    void preservesOriginalPackageWhenSidecarHasNoUsableFormula() throws Exception {
        for (String mathml : List.of(
                "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"/>",
                "<math><mrow><mspace width=\"1em\"/></mrow></math>",
                "<math><semantics><mrow/><annotation encoding=\"text/plain\">x</annotation></semantics></math>",
                "<math xmlns=\"urn:wrong\"><mi>x</mi></math>",
                "<math><mi>broken</math>",
                "<math><mi>&#x2061;</mi></math>",
                "<math><mrow><mtext>&#x200B;</mtext><mo>&#x2062;</mo><mi>&#xAD;</mi></mrow></math>")) {
            Path temp = Files.createTempDirectory("dsmt4-no-content");
            Path input = temp.resolve("input.docx");
            Path output = temp.resolve("output.docx");
            MathObjectRef object = mathObjectRef(1, mathml);
            writeMinimalDocx(input, oleObjectDocumentXml(object), List.of(object));
            var summary = new DocxMathPatchMain(
                    ManifestMathSidecarRepository.load(writeManifest(temp, List.of(object))))
                    .patch(input, output);
            assertEquals(0, summary.patchedBlocks(), mathml);
            assertEquals(0, summary.patchedInline(), mathml);
            assertEquals(1, summary.unresolved(), mathml);
            assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output), mathml);
        }
    }

    // The gate only rejects formulas made of nothing visible; it does not strip invisible operators.
    @Test
    void keepsInvisibleOperatorsBesideVisibleTokens() throws Exception {
        var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">"
                + "<mi>f</mi><mo>&#x2061;</mo><mi>x</mi><mo>&#x2062;</mo><mi>y</mi></math>");
        var result = runPatch(oleObjectDocumentXml(object), List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedBlocks());
        var text = new StringBuilder();
        var ts = parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "t");
        for (int i = 0; i < ts.getLength(); i++) text.append(ts.item(i).getTextContent());
        // U+2061 survives. U+2062 (and U+200B) are removed by mml2omml.xsl's own OutputText
        // template (Microsoft's stylesheet), not by the content gate; recorded as a known limit.
        assertEquals("f⁡xy", text.toString());
    }

    @Test
    void preservesOleWhenOmmlConversionThrows() throws Exception {
        Path temp = Files.createTempDirectory("dsmt4-conversion-failed");
        Path input = temp.resolve("input.docx");
        Path output = temp.resolve("output.docx");
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        writeMinimalDocx(input, oleObjectDocumentXml(object), List.of(object));
        var patcher = new DocxMathPatchMain(
                ManifestMathSidecarRepository.load(writeManifest(temp, List.of(object))),
                new BasicMathmlNormalizer(),
                mathml -> { throw new IllegalStateException("decoder output cannot be transformed"); },
                new XmlBeansOmmlInjector(), new DocxWalker(new PoiMathSourceDetector()),
                new InlineSafetyEvaluator(), new MultiObjectSafetyEvaluator(), DocxMathPatchMain.LogLevel.WARNINGS);
        var summary = patcher.patch(input, output);
        assertEquals(0, summary.patchedBlocks());
        assertEquals(1, summary.unresolved());
        assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.OMML_CONVERSION_FAILED));
        assertEquals(java.util.Map.of("conversion_exception", 1), summary.conversionDiagnostics());
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
        Path nativeInput = temp.resolve("native.docx");
        writeMinimalDocx(nativeInput, nativeOmmlDocumentXml(), List.of());
        var next = patcher.patch(nativeInput, temp.resolve("native-output.docx"));
        assertTrue(next.conversionDiagnostics().isEmpty());
        assertEquals(java.util.Map.of("conversion_exception", 1), summary.conversionDiagnostics());
    }

    @Test
    void normalizesNamespaceFreeMathmlIntoEditableOmmlRuns() throws Exception {
        MathObjectRef object = mathObjectRef(1, "<math><mi>x</mi></math>");
        PatchRunResult result = runPatch(oleObjectDocumentXml(object), List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedBlocks());
        var factory = javax.xml.parsers.DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        var document = factory.newDocumentBuilder().parse(new org.xml.sax.InputSource(new java.io.StringReader(result.xml)));
        var runs = document.getElementsByTagNameNS("http://schemas.openxmlformats.org/officeDocument/2006/math", "t");
        assertEquals(1, runs.getLength());
        assertEquals("x", runs.item(0).getTextContent());
    }

    @Test
    void retainsOriginalWhenTransformReturnsEmptyOrBareTextOmml() throws Exception {
        for (String omml : List.of(
                "<m:oMath xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\"/>",
                "<m:oMath xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\">x</m:oMath>")) {
            Path temp = Files.createTempDirectory("dsmt4-empty-omml");
            Path input = temp.resolve("input.docx");
            Path output = temp.resolve("output.docx");
            MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
            writeMinimalDocx(input, oleObjectDocumentXml(object), List.of(object));
            var patcher = new DocxMathPatchMain(
                    ManifestMathSidecarRepository.load(writeManifest(temp, List.of(object))),
                    new BasicMathmlNormalizer(), mathml -> omml,
                    new XmlBeansOmmlInjector(), new DocxWalker(new PoiMathSourceDetector()),
                    new InlineSafetyEvaluator(), new MultiObjectSafetyEvaluator(), DocxMathPatchMain.LogLevel.WARNINGS);
            var summary = patcher.patch(input, output);
            assertEquals(0, summary.patchedBlocks());
            assertEquals(1, summary.unresolved());
            assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
        }
    }

    @Test
    void retainsSourceWhenRealDegreeOrNuclidePatternProducesAnEmptyScriptBase() throws Exception {
        for (String mathml : List.of(
                "<math><mtext>0</mtext><msup><mspace width=\"0.08em\"/><mtext>o</mtext></msup><mtext>C?</mtext></math>",
                "<math><msubsup><mrow/><mn>94</mn><mn>238</mn></msubsup><mtext>Pu</mtext></math>")) {
            var object = mathObjectRef(1, mathml);
            String source = oleObjectDocumentXml(object);
            var result = runPatch(source, List.of(object), List.of(object));
            assertEquals(0, result.summary.patchedBlocks() + result.summary.patchedInline());
            assertEquals(1, result.summary.unresolved());
            assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.OMML_CONVERSION_FAILED));
            assertEquals(signature(equationParagraph(source)), signature(equationParagraph(result.xml)));
        }
    }

    @Test
    void retainsSourceWhenScriptBaseContainsOnlyEmptyOrInvisibleTokens() throws Exception {
        for (String base : List.of("<mi/>", "<mrow><mi/></mrow>", "<mtext> </mtext>",
                "<mi>&#x2062;</mi>", "<mspace width=\"1em\"/>")) {
            var object = mathObjectRef(1, "<math><msup>" + base + "<mn>2</mn></msup><mo>+</mo><mi>y</mi></math>");
            Path temp = Files.createTempDirectory("dsmt4-invisible-script-base");
            Path input = temp.resolve("input.docx");
            Path output = temp.resolve("output.docx");
            writeMinimalDocx(input, oleObjectDocumentXml(object), List.of(object));
            var summary = new DocxMathPatchMain(
                    ManifestMathSidecarRepository.load(writeManifest(temp, List.of(object)))).patch(input, output);
            assertEquals(0, summary.patchedBlocks() + summary.patchedInline(), base);
            assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.OMML_CONVERSION_FAILED), base);
            assertEquals(java.util.Map.of("missing_script_base", 1), summary.conversionDiagnostics(), base);
            assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output), base);
        }
    }

    @Test
    void retainsWholeMultiObjectParagraphWhenOneScriptBaseIsIncomplete() throws Exception {
        var good = mathObjectRef(1, wmfMathml("x", "+", "1"));
        var bad = mathObjectRef(2, "<math><msubsup><mrow/><mn>94</mn><mn>238</mn></msubsup><mi>Pu</mi></math>");
        String source = inlineObjectDocumentXml("", List.of(textRunXml("A "), objectRunXml(good), textRunXml(" B "), objectRunXml(bad)));
        var result = runPatch(source, List.of(good, bad), List.of(good, bad));
        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.unresolved(), "only the failed conversion counts as unresolved");
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(signature(equationParagraph(source)), signature(equationParagraph(result.xml)));
    }

    @Test
    void retainsLabeledArrowContentFromRealChemistryMtefSidecars() throws Exception {
        var first = mathObjectRef(1, Files.readString(Path.of("fixtures/dsmt4/chemistry-arrows/arrow-1.mathml")));
        var second = mathObjectRef(2, Files.readString(Path.of("fixtures/dsmt4/chemistry-arrows/arrow-2.mathml")));
        var result = runPatch(inlineObjectDocumentXml("", List.of(
                textRunXml("CH₃CH(NH₂)COOH "), objectRunXml(first),
                textRunXml(" X "), objectRunXml(second), textRunXml(" Y."))),
                List.of(first, second), List.of(first, second));
        assertEquals(2, result.summary.patchedInline());
        assertOmmlIsParagraphChild(result.xml, 2);
        var factory = javax.xml.parsers.DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        var doc = factory.newDocumentBuilder().parse(new org.xml.sax.InputSource(new java.io.StringReader(result.xml)));
        var xpath = javax.xml.xpath.XPathFactory.newInstance().newXPath();
        // Literal expected labels come from the source preview, including its commas.
        String base = "//*[local-name()='oMath']/*[local-name()='box']/*[local-name()='e']";
        // The arrow is Word's stretching group character over the upper label, with the lower
        // label hanging beneath; a bare "→" run with labels around it renders as a short arrow.
        String arrow1 = "(" + base + ")[1]/*[local-name()='limLow']/*[local-name()='e']/*[local-name()='d']/*[local-name()='e']/*[local-name()='groupChr']";
        assertEquals("→", xpath.evaluate(arrow1 + "/*[local-name()='groupChrPr']/*[local-name()='chr']/@*[local-name()='val']", doc));
        // The two TeX "\\ " gaps in the source (mspace 0.16em) must survive as spaces: "CH3OH, HCl khan".
        assertEquals("CH3OH,\u2006HCl\u2006khan", xpath.evaluate(arrow1 + "/*[local-name()='e']", doc));
        assertEquals(",−H2O,", xpath.evaluate("(" + base + ")[1]/*[local-name()='limLow']/*[local-name()='lim']", doc));
        // The lower label is the wider one here, so the arrow is grouped over it and the upper label sits above.
        String arrow2 = "(" + base + ")[2]/*[local-name()='limUpp']/*[local-name()='e']/*[local-name()='d']/*[local-name()='e']/*[local-name()='groupChr']";
        assertEquals("→", xpath.evaluate(arrow2 + "/*[local-name()='groupChrPr']/*[local-name()='chr']/@*[local-name()='val']", doc));
        assertEquals(",−NH4Cl,", xpath.evaluate(arrow2 + "/*[local-name()='e']", doc));
        assertEquals("NH3", xpath.evaluate("(" + base + ")[2]/*[local-name()='limUpp']/*[local-name()='lim']", doc));
    }

    private static final String SOURCE_RUN_PROPERTIES =
            "<w:rPr><w:b/><w:color w:val=\"0000CC\"/><w:position w:val=\"-4\"/><w:sz w:val=\"28\"/>"
                    + "<w:szCs w:val=\"28\"/><w:highlight w:val=\"yellow\"/><w:u w:val=\"single\"/></w:rPr>";

    @Test
    void carriesExplicitHiddenStateOntoInlineAndBlockEquationRuns() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        for (String value : List.of("", " w:val=\"0\"", " w:val=\"false\"")) {
            String properties = "<w:rPr><w:vanish" + value + "/></w:rPr>";
            for (boolean block : List.of(false, true)) {
                var runs = block ? List.of(formattedObjectRunXml(object, properties))
                        : List.of(textRunXml("Cho "), formattedObjectRunXml(object, properties), textRunXml(" xong"));
                var result = runPatch(inlineObjectDocumentXml(block ? CENTRED_PARAGRAPH : "", runs),
                        List.of(object), List.of(object));
                assertEquals(block ? 1 : 0, result.summary.patchedBlocks());
                assertEquals(block ? 0 : 1, result.summary.patchedInline());
                var mathRuns = parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "r");
                assertTrue(mathRuns.getLength() > 0);
                for (int i = 0; i < mathRuns.getLength(); i++) {
                    var hidden = ((org.w3c.dom.Element) mathRuns.item(i)).getElementsByTagNameNS(WORD_NS, "vanish");
                    assertEquals(1, hidden.getLength(), "every equation run must retain explicit hidden state");
                    assertEquals(value.isEmpty() ? "" : value.contains("false") ? "false" : "0",
                            ((org.w3c.dom.Element) hidden.item(0)).getAttributeNS(WORD_NS, "val"));
                }
            }
        }
    }

    @Test
    void preservesHiddenMixedRunWithoutHidingNeighbouringEquation() throws Exception {
        var hidden = mathObjectRef(1, wmfMathml("x", "+", "1"));
        var visible = mathObjectRef(2, wmfMathml("y", "+", "2"));
        var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Cho "),
                mixedObjectRunXml(hidden).replace(SPLIT_RUN_PROPERTIES, "<w:rPr><w:vanish/></w:rPr>"),
                textRunXml(" và "), objectRunXml(visible))), List.of(hidden, visible), List.of(hidden, visible));
        assertEquals(2, result.summary.patchedInline());
        var equations = parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "oMath");
        assertEquals(2, equations.getLength());
        var hiddenRuns = ((org.w3c.dom.Element) equations.item(0)).getElementsByTagNameNS(OMML_NS, "r");
        assertTrue(hiddenRuns.getLength() > 0);
        assertEquals(hiddenRuns.getLength(), ((org.w3c.dom.Element) equations.item(0))
                .getElementsByTagNameNS(WORD_NS, "vanish").getLength());
        assertEquals(0, ((org.w3c.dom.Element) equations.item(1)).getElementsByTagNameNS(WORD_NS, "vanish").getLength());
        var textRuns = parseNamespaceAware(result.xml).getElementsByTagNameNS(WORD_NS, "r");
        int splitTextRuns = 0;
        for (int i = 0; i < textRuns.getLength(); i++) {
            var run = (org.w3c.dom.Element) textRuns.item(i);
            var texts = run.getElementsByTagNameNS(WORD_NS, "t");
            if (texts.getLength() == 1 && (texts.item(0).getTextContent().equals("pre ")
                    || texts.item(0).getTextContent().equals(" post"))) {
                splitTextRuns++;
                assertEquals(1, run.getElementsByTagNameNS(WORD_NS, "vanish").getLength());
            }
        }
        assertEquals(2, splitTextRuns, "both text fragments of the hidden source run survive");
    }

    @Test
    void carriesSourceRunSizeAndColourOntoEveryInlineEquationRun() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        var result = runPatch(inlineObjectDocumentXml("", List.of(
                textRunXml("Cho "), formattedObjectRunXml(object, SOURCE_RUN_PROPERTIES), textRunXml(" xong"))),
                List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedInline());
        assertMathRunsCarry(result.xml, 1, "28", "0000CC");
    }

    @Test
    void carriesSourceRunFormattingOntoBlockEquationRuns() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        var result = runPatch(inlineObjectDocumentXml(CENTRED_PARAGRAPH, List.of(formattedObjectRunXml(object, SOURCE_RUN_PROPERTIES))),
                List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedBlocks());
        assertMathRunsCarry(result.xml, 1, "28", "0000CC");
    }

    @Test
    void givesStandaloneLeftEquationExplicitMathJustificationForWord() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        var result = runPatch(inlineObjectDocumentXml("<w:pPr><w:jc w:val=\"left\"/></w:pPr>",
                List.of(objectRunXml(object))), List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedBlocks());
        var doc = parseNamespaceAware(result.xml);
        var jc = (org.w3c.dom.Element) doc.getElementsByTagNameNS(OMML_NS, "jc").item(0);
        assertTrue(jc != null);
        assertEquals("left", jc.getAttributeNS(OMML_NS, "val"));
    }

    @Test
    void retainsStandaloneObjectWhenIndentPlacementNeedsApplicationReview() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        String source = inlineObjectDocumentXml("<w:pPr><w:ind w:firstLine=\"283\"/><w:jc w:val=\"center\"/></w:pPr>",
                List.of(objectRunXml(object)));
        var result = runPatch(source, List.of(object), List.of(object));
        assertEquals(0, result.summary.patchedBlocks() + result.summary.patchedInline());
        assertEquals(1, result.summary.skippedUnknownOrAmbiguous());
        assertEquals(signature(equationParagraph(source)), signature(equationParagraph(result.xml)));
    }

    @Test
    void retainsLoneObjectWithProofingMarkersOrEmptyTextInsteadOfCentringItInWord() throws Exception {
        // Actual Word opening: proofErr and w:t="" leave a lone inline oMath,
        // which Word centres even though the source OLE is laid out at the left.
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        for (var runs : List.of(
                List.of("<w:proofErr w:type=\"spellStart\"/>", objectRunXml(object),
                        "<w:proofErr w:type=\"spellEnd\"/>"),
                List.of("<w:r><w:t/></w:r>", objectRunXml(object)),
                List.of(objectRunXml(object), "<w:r><w:t></w:t></w:r>"))) {
            String source = inlineObjectDocumentXml("<w:pPr><w:jc w:val=\"left\"/></w:pPr>", runs);
            var result = runPatch(source, List.of(object), List.of(object));
            assertEquals(0, result.summary.patchedBlocks() + result.summary.patchedInline());
            assertEquals(1, result.summary.skippedUnknownOrAmbiguous());
            assertEquals(signature(equationParagraph(source)), signature(equationParagraph(result.xml)));
        }
    }

    @Test
    void proofingMarkersArePreservedAcrossSeparatedAndUnseparatedInlineBoundaries() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        for (String text : List.of("A.", " ")) {
            String source = inlineObjectDocumentXml("<w:pPr><w:jc w:val=\"left\"/></w:pPr>",
                    List.of("<w:proofErr w:type=\"spellStart\"/>", objectRunXml(object),
                            "<w:proofErr w:type=\"spellEnd\"/>", textRunXml(text)));
            var result = runPatch(source, List.of(object), List.of(object));
            if (text.equals("A.")) {
                assertEquals(0, result.summary.patchedInline());
                assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
                assertEquals(source, result.xml);
                continue;
            }
            assertEquals(1, result.summary.patchedInline());
            assertEquals(0, result.summary.patchedBlocks());
            var paragraph = equationParagraph(result.xml);
            var texts = paragraph.getElementsByTagNameNS(WORD_NS, "t");
            assertEquals(1, texts.getLength());
            assertEquals(text, texts.item(0).getTextContent());
            assertEquals(2, paragraph.getElementsByTagNameNS(WORD_NS, "proofErr").getLength());
        }
    }

    // Word centres a lone oMath too. Use explicit math alignment for known plain layouts;
    // preserve the object when indentation, numbering or bidi makes placement uncertain.
    @Test
    void usesExplicitAlignmentOrRetainsObjectWhenStandalonePlacementIsUncertain() throws Exception {
        for (String paragraphProperties : List.of(
                "",
                "<w:pPr><w:jc w:val=\"left\"/></w:pPr>",
                "<w:pPr><w:jc w:val=\"both\"/></w:pPr>",
                "<w:pPr><w:jc w:val=\"right\"/></w:pPr>",
                "<w:pPr><w:ind w:firstLine=\"283\"/><w:jc w:val=\"center\"/></w:pPr>",
                "<w:pPr><w:numPr><w:ilvl w:val=\"0\"/><w:numId w:val=\"3\"/></w:numPr><w:jc w:val=\"center\"/></w:pPr>",
                "<w:pPr><w:bidi/><w:jc w:val=\"center\"/></w:pPr>")) {
            var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
            String documentXml = inlineObjectDocumentXml(paragraphProperties, List.of(objectRunXml(object)));
            var result = runPatch(documentXml, List.of(object), List.of(object));
            boolean uncertain = paragraphProperties.contains("w:ind") || paragraphProperties.contains("w:numPr")
                    || paragraphProperties.contains("w:bidi");
            assertEquals(uncertain ? 0 : 1, result.summary.patchedBlocks(), paragraphProperties);
            assertEquals(0, result.summary.patchedInline(), paragraphProperties);
            if (uncertain) {
                assertEquals(1, result.summary.skippedUnknownOrAmbiguous(), paragraphProperties);
                assertEquals(signature(equationParagraph(documentXml)), signature(equationParagraph(result.xml)));
            } else {
                var jc = (org.w3c.dom.Element) parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "jc").item(0);
                assertEquals(paragraphProperties.contains("right") ? "right" : "left", jc.getAttributeNS(OMML_NS, "val"));
            }
            assertEquals(paragraphPropertiesSignature(documentXml), paragraphPropertiesSignature(result.xml), paragraphProperties);
        }
    }

    @Test
    void keepsCentredObjectParagraphAsExplicitlyCentredDisplayEquation() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        // Bookmarks around the object stay on their side of the equation.
        String documentXml = inlineObjectDocumentXml(
                CENTRED_PARAGRAPH + "<w:bookmarkStart w:id=\"0\" w:name=\"eq\"/>",
                List.of("<w:r><w:rPr><w:sz w:val=\"24\"/></w:rPr></w:r>", objectRunXml(object), "<w:bookmarkEnd w:id=\"0\"/>"));
        var result = runPatch(documentXml, List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedBlocks());
        assertEquals(List.of("pPr", "bookmarkStart", "oMathPara", "bookmarkEnd"), paragraphChildNames(result.xml));
        assertEquals(paragraphPropertiesSignature(documentXml), paragraphPropertiesSignature(result.xml));
        var doc = parseNamespaceAware(result.xml);
        var jc = (org.w3c.dom.Element) doc.getElementsByTagNameNS(OMML_NS, "jc").item(0);
        assertEquals("oMathParaPr", jc.getParentNode().getLocalName());
        // Explicit, so a document-level m:defJc other than centre cannot move it.
        assertEquals("centerGroup", jc.getAttributeNS(OMML_NS, "val"));
    }

    @Test
    void resolvesInheritedAlignmentFromStylesAndDocumentDefaults() throws Exception {
        String centredBase = "<w:style w:type=\"paragraph\" w:styleId=\"Centred\"><w:pPr><w:jc w:val=\"center\"/></w:pPr></w:style>";
        String equation = "<w:style w:type=\"paragraph\" w:styleId=\"Eq\"><w:basedOn w:val=\"Centred\"/></w:style>";
        String indented = "<w:style w:type=\"paragraph\" w:styleId=\"Indented\"><w:basedOn w:val=\"Centred\"/><w:pPr><w:ind w:left=\"720\"/></w:pPr></w:style>";
        String numbered = "<w:style w:type=\"paragraph\" w:styleId=\"Numbered\"><w:basedOn w:val=\"Centred\"/><w:pPr><w:numPr><w:numId w:val=\"4\"/></w:numPr></w:pPr></w:style>";
        String leftNormal = "<w:style w:type=\"paragraph\" w:default=\"1\" w:styleId=\"Normal\"><w:pPr><w:jc w:val=\"left\"/></w:pPr></w:style>";
        String centredNormal = "<w:style w:type=\"paragraph\" w:default=\"1\" w:styleId=\"Normal\"><w:pPr><w:jc w:val=\"center\"/></w:pPr></w:style>";
        String centredDefaults = "<w:pPr><w:jc w:val=\"center\"/></w:pPr>";
        record Case(String paragraphProperties, String styles, int blocks) { }
        for (Case c : List.of(
                new Case("<w:pPr><w:pStyle w:val=\"Eq\"/></w:pPr>", stylesXml("", centredBase, equation, leftNormal), 1),
                new Case("", stylesXml("", centredBase, centredNormal), 1),
                new Case("", stylesXml(centredDefaults), 1),
                new Case("", stylesXml(centredDefaults, leftNormal), 1),
                new Case("<w:pPr><w:pStyle w:val=\"Indented\"/></w:pPr>", stylesXml("", centredBase, indented), 0),
                new Case("<w:pPr><w:pStyle w:val=\"Numbered\"/></w:pPr>", stylesXml("", centredBase, numbered), 0),
                // numId 0 explicitly removes the style's numbering.
                new Case("<w:pPr><w:pStyle w:val=\"Numbered\"/><w:numPr><w:numId w:val=\"0\"/></w:numPr></w:pPr>",
                        stylesXml("", centredBase, numbered), 1),
                new Case("<w:pPr><w:pStyle w:val=\"Eq\"/><w:jc w:val=\"left\"/></w:pPr>", stylesXml("", centredBase, equation), 1))) {
            var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
            var result = runPatch(inlineObjectDocumentXml(c.paragraphProperties(), List.of(objectRunXml(object))),
                    c.styles(), List.of(object), List.of(object));
            assertEquals(c.blocks(), result.summary.patchedBlocks(), c.toString());
            assertEquals(0, result.summary.patchedInline(), c.toString());
            assertEquals(1 - c.blocks(), result.summary.skippedUnknownOrAmbiguous(), c.toString());
        }
    }

    @Test
    void resolvesAlignmentOfObjectParagraphsInTableCells() throws Exception {
        String centredTable = "<w:style w:type=\"table\" w:styleId=\"CentredGrid\"><w:pPr><w:jc w:val=\"center\"/></w:pPr></w:style>";
        String conditionalTable = "<w:style w:type=\"table\" w:styleId=\"HeaderGrid\"><w:pPr><w:jc w:val=\"center\"/></w:pPr>"
                + "<w:tblStylePr w:type=\"firstRow\"><w:pPr><w:jc w:val=\"left\"/></w:pPr></w:tblStylePr></w:style>";
        record Case(String tableProperties, String paragraphProperties, String styles, int blocks) { }
        for (Case c : List.of(
                new Case("", CENTRED_PARAGRAPH, null, 1),
                new Case("", "", null, 1),
                new Case("<w:tblStyle w:val=\"CentredGrid\"/>", "", stylesXml("", centredTable), 1),
                // Conditional table formatting depends on the cell's row/column: not decided here.
                new Case("<w:tblStyle w:val=\"HeaderGrid\"/>", "", stylesXml("", conditionalTable), 0))) {
            var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
            String documentXml = tableObjectDocumentXml(c.tableProperties(), c.paragraphProperties(), List.of(objectRunXml(object)));
            var result = runPatch(documentXml, c.styles(), List.of(object), List.of(object));
            assertEquals(c.blocks(), result.summary.patchedBlocks(), c.toString());
            assertEquals(0, result.summary.patchedInline(), c.toString());
            assertEquals(1 - c.blocks(), result.summary.skippedUnknownOrAmbiguous(), c.toString());
            assertEquals(paragraphPropertiesSignature(documentXml), paragraphPropertiesSignature(result.xml), c.toString());
        }
    }

    private static final String SPLIT_RUN_PROPERTIES = "<w:rPr><w:color w:val=\"0000CC\"/><w:sz w:val=\"28\"/></w:rPr>";

    // One run holding text, the object, a rendered page break, more text, a break and a drawing.
    private static String mixedObjectRunXml(MathObjectRef object) {
        return objectRunXml(object)
                .replaceFirst("<w:r>", java.util.regex.Matcher.quoteReplacement(
                        "<w:r>" + SPLIT_RUN_PROPERTIES + "<w:t xml:space=\"preserve\">pre </w:t>"))
                .replace("</w:object>", "</w:object><w:lastRenderedPageBreak/><w:t xml:space=\"preserve\"> post</w:t><w:br/><w:drawing/>");
    }

    // The multi-object path accepts mixed object runs and splits them at the object.
    @Test
    void splitsMixedObjectRunAroundEquationInMultiObjectParagraph() throws Exception {
        var first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        var result = runPatch(inlineObjectDocumentXml("", List.of(
                        textRunXml("A "), mixedObjectRunXml(first), textRunXml(" B "), objectRunXml(second))),
                List.of(first, second), List.of(first, second));
        assertEquals(2, result.summary.patchedInline());
        assertEquals(List.of(
                "r{}[t'A ']",
                "r{color=0000CC,sz=28}[t'pre ']",
                "math'a+1'",
                "r{color=0000CC,sz=28}[lastRenderedPageBreak,t' post',br,drawing]",
                "r{}[t' B ']",
                "math'b-2'"), paragraphSequence(equationParagraph(result.xml)));
    }

    // The single-object path keeps its stricter run check: a mixed object run is left as OLE.
    @Test
    void retainsMixedObjectRunUnchangedOnSingleObjectPath() throws Exception {
        var object = mathObjectRef(1, wmfMathml("a", "+", "1"));
        Path temp = Files.createTempDirectory("docx-patch-single-mixed");
        Path input = temp.resolve("input.docx");
        Path output = temp.resolve("output.docx");
        writeMinimalDocx(input, inlineObjectDocumentXml("", List.of(textRunXml("A "), mixedObjectRunXml(object))), List.of(object));
        var summary = new DocxMathPatchMain(ManifestMathSidecarRepository.load(writeManifest(temp, List.of(object))))
                .patch(input, output);
        assertEquals(0, summary.patchedInline());
        assertEquals(1, summary.skippedUnknownOrAmbiguous());
        assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.OTHER_UNSAFE_MODEL));
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
    }

    // Object 3 and the mixed object 2 are replaced (in reverse order) before object 1, inside a
    // hyperlink, fails the placement check. The paragraph must come out exactly as it went in.
    @Test
    void leavesParagraphIntactWhenMultiObjectPatchFailsPartWay() throws Exception {
        var first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        var third = mathObjectRef(3, wmfMathml("c", "+", "3"));
        var fourth = mathObjectRef(4, wmfMathml("d", "+", "4"));
        var objects = List.of(first, second, third, fourth);
        String documentXml = twoParagraphDocumentXml(
                List.of(textRunXml("Cho "), "<w:hyperlink w:anchor=\"eq\">" + objectRunXml(first) + "</w:hyperlink>",
                        mixedObjectRunXml(second), drawingAndTextRunXml(" helper "), objectRunXml(third)),
                List.of(textRunXml("Sau "), objectRunXml(fourth)));
        var result = runPatch(documentXml, objects, objects);

        assertEquals(1, result.summary.patchedInline());
        assertEquals(3, result.summary.unresolved());
        assertEquals(1, result.summary.skippedMultiObjectParagraphs());
        assertEquals(1, result.summary.multiObjectSkippedUnsafeParagraphs());
        assertEquals(0, result.summary.multiObjectPatchedParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.XML_MUTATION_ROLLBACK));
        var source = bodyParagraphs(documentXml);
        var patched = bodyParagraphs(result.xml);
        assertEquals(signature(source.get(0)), signature(patched.get(0)));
        assertEquals(List.of(
                "r{}[t'Cho ']", "hyperlink", "r{color=0000CC,sz=28}[t'pre ',object,lastRenderedPageBreak,t' post',br,drawing]",
                "r{noProof}[drawing,t' helper ']", "r{}[object]"), paragraphSequence(patched.get(0)));
        assertEquals(List.of("r{}[t'Sau ']", "math'd+4'"), paragraphSequence(patched.get(1)));
    }

    // A failure after the first replacement on any path (multi, inline, block) leaves the live
    // paragraph untouched; the next paragraph still patches and the document is rewritten.
    @Test
    void leavesParagraphIntactWhenReplacementFailsAfterStarting() throws Exception {
        var a = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var b = mathObjectRef(2, wmfMathml("b", "-", "2"));
        var tail = mathObjectRef(3, wmfMathml("d", "+", "4"));
        List<List<String>> firstParagraphs = List.of(
                List.of(textRunXml("A "), mixedObjectRunXml(a), textRunXml(" B "), objectRunXml(b)),
                List.of(textRunXml("A "), formattedObjectRunXml(a, SPLIT_RUN_PROPERTIES), textRunXml(" B")),
                List.of(CENTRED_PARAGRAPH, formattedObjectRunXml(a, SPLIT_RUN_PROPERTIES)));
        for (List<String> firstParagraph : firstParagraphs) {
            var objects = firstParagraph.stream().anyMatch(run -> run.contains(b.oleRelId()))
                    ? List.of(a, b, tail) : List.of(a, tail);
            String documentXml = twoParagraphDocumentXml(firstParagraph, List.of(textRunXml("Sau "), objectRunXml(tail)));
            Path temp = Files.createTempDirectory("docx-patch-fault");
            Path input = temp.resolve("input.docx");
            Path output = temp.resolve("output.docx");
            writeMinimalDocx(input, documentXml, objects);
            var calls = new java.util.concurrent.atomic.AtomicInteger();
            var injector = new XmlBeansOmmlInjector(replaced -> {
                if (calls.incrementAndGet() == 1) throw new IllegalStateException("injected failure after a replacement");
            });
            var summary = new DocxMathPatchMain(
                    ManifestMathSidecarRepository.load(writeManifest(temp, objects)),
                    new BasicMathmlNormalizer(), new XsltMathmlToOmmlConverter(), injector,
                    new DocxWalker(new PoiMathSourceDetector()), new InlineSafetyEvaluator(),
                    new MultiObjectSafetyEvaluator(), DocxMathPatchMain.LogLevel.SUMMARY).patch(input, output);

            String label = firstParagraph.toString();
            assertEquals(0, summary.patchedBlocks(), label);
            assertEquals(1, summary.patchedInline(), label);
            assertEquals(objects.size() - 1, summary.unresolved(), label);
            assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.XML_MUTATION_ROLLBACK), label);
            var source = bodyParagraphs(documentXml);
            var patched = bodyParagraphs(readDocumentXml(output));
            assertEquals(signature(source.get(0)), signature(patched.get(0)), label);
            assertEquals(List.of("r{}[t'Sau ']", "math'd+4'"), paragraphSequence(patched.get(1)), label);
        }
    }

    // The live XWPFParagraph stays attached and readable after a failed attempt, and a later
    // attempt on the same paragraph still works.
    @Test
    void keepsXwpfParagraphUsableAfterFailedMultiObjectPatch() throws Exception {
        var a = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var b = mathObjectRef(2, wmfMathml("b", "-", "2"));
        Path temp = Files.createTempDirectory("docx-patch-xwpf");
        Path input = temp.resolve("input.docx");
        writeMinimalDocx(input, inlineObjectDocumentXml("", List.of(
                textRunXml("A "), mixedObjectRunXml(a), textRunXml(" B "), objectRunXml(b))), List.of(a, b));
        try (var in = Files.newInputStream(input);
             var document = new org.apache.poi.xwpf.usermodel.XWPFDocument(in)) {
            var paragraph = document.getParagraphs().get(0);
            var body = paragraph.getCTP().getDomNode().getParentNode();
            String textBefore = paragraph.getText();
            String before = signature(paragraph.getCTP().getDomNode());
            var resolved = new DocxWalker(new PoiMathSourceDetector()).collect(document).stream()
                    .map(occurrence -> new ResolvedMathOccurrence(occurrence, occurrence.previewPartName(),
                            new XsltMathmlToOmmlConverter().convert(new BasicMathmlNormalizer().normalize(
                                    occurrence.oleRelationshipId().equals(a.oleRelId()) ? a.mathml() : b.mathml()))))
                    .toList();
            var plan = new MultiObjectSafetyEvaluator().plan(resolved);
            assertTrue(plan.safe());
            var liveNode = paragraph.getCTP().getDomNode();
            // Objects are replaced right to left, so the valid right-hand OMML goes in before the
            // malformed left-hand one fails.
            var malformedLeft = MultiObjectPatchPlan.safe(paragraph, List.of(
                    ParagraphSegment.object(plan.objectSegments().get(0).paragraphChild(), null, "<bad"),
                    plan.objectSegments().get(1)));

            for (var failing : List.of(
                    (java.util.function.Supplier<Boolean>) () -> new XmlBeansOmmlInjector(
                            replaced -> { throw new IllegalStateException("injected"); }).inject(plan),
                    () -> new XmlBeansOmmlInjector().inject(malformedLeft))) {
                assertFalse(failing.get());
                assertTrue(paragraph.getCTP().getDomNode() == liveNode, "XWPFParagraph lost its CTP node");
                assertTrue(liveNode.getParentNode() == body, "paragraph detached from body");
                assertTrue(document.getParagraphs().get(0) == paragraph);
                for (var segment : plan.objectSegments()) {
                    assertTrue(isDescendant(segment.paragraphChild(), liveNode), "plan object detached");
                }
                assertEquals(before, signature(liveNode));
                assertEquals(textBefore, paragraph.getText());
                assertTrue(paragraph.getCTP().xmlText().contains("w:object"));
                assertEquals(4, paragraph.getRuns().size());
            }

            // A failed attempt does not stop a later one on the same paragraph and plan.
            assertTrue(new XmlBeansOmmlInjector().inject(plan));
            assertTrue(liveNode.getParentNode() == body, "paragraph detached from body");
            assertEquals(2, ((org.w3c.dom.Element) liveNode).getElementsByTagNameNS(OMML_NS, "oMath").getLength());
            assertTrue(paragraph.getCTP().xmlText().contains("oMath"));

            var saved = new java.io.ByteArrayOutputStream();
            document.write(saved);
            try (var reopened = new org.apache.poi.xwpf.usermodel.XWPFDocument(new java.io.ByteArrayInputStream(saved.toByteArray()))) {
                var reopenedParagraph = (org.w3c.dom.Element) reopened.getParagraphs().get(0).getCTP().getDomNode();
                assertEquals(List.of("r{}[t'A ']", "r{color=0000CC,sz=28}[t'pre ']", "math'a+1'",
                        "r{color=0000CC,sz=28}[lastRenderedPageBreak,t' post',br,drawing]", "r{}[t' B ']", "math'b-2'"),
                        paragraphSequence(reopenedParagraph));
                assertEquals(0, reopenedParagraph.getElementsByTagNameNS(WORD_NS, "object").getLength());
            }
        }
    }

    // On success the runs that were not replaced stay the same live XWPFRun objects, and the
    // paragraph's run list and text follow the new content (split text included).
    @Test
    void keepsLiveRunsAndTextAfterSuccessfulPatch() throws Exception {
        var a = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var b = mathObjectRef(2, wmfMathml("b", "-", "2"));
        record Case(String documentXml, List<MathObjectRef> objects, String textAfter, int runsAfter) { }
        for (Case c : List.of(
                new Case(inlineObjectDocumentXml("", List.of(textRunXml("A "), mixedObjectRunXml(a), textRunXml(" B "), objectRunXml(b))),
                        List.of(a, b), "A pre  post\n B ", 4),
                new Case(inlineObjectDocumentXml("", List.of(textRunXml("A "), objectRunXml(a), textRunXml(" B"))),
                        List.of(a), "A  B", 2),
                new Case(inlineObjectDocumentXml(CENTRED_PARAGRAPH, List.of("<w:r><w:rPr><w:sz w:val=\"24\"/></w:rPr></w:r>", objectRunXml(a))),
                        List.of(a), "", 0))) {
            Path temp = Files.createTempDirectory("docx-patch-live-runs");
            Path input = temp.resolve("input.docx");
            writeMinimalDocx(input, c.documentXml(), c.objects());
            try (var in = Files.newInputStream(input);
                 var document = new org.apache.poi.xwpf.usermodel.XWPFDocument(in)) {
                var paragraph = document.getParagraphs().get(0);
                var liveNode = paragraph.getCTP().getDomNode();
                paragraph.getText();
                // Runs with text and no object; the block path drops rPr-only runs by design.
                var textRuns = paragraph.getRuns().stream()
                        .filter(run -> PoiMathSourceDetector.findDescendants(run.getCTR().getDomNode(), "object").isEmpty()
                                && !run.text().isEmpty())
                        .toList();
                var summary = new DocxMathPatchMain(ManifestMathSidecarRepository.load(writeManifest(temp, c.objects())))
                        .patch(document);
                assertEquals(c.objects().size(), summary.patchedBlocks() + summary.patchedInline(), c.toString());

                assertTrue(paragraph.getCTP().getDomNode() == liveNode, "XWPFParagraph lost its CTP node");
                assertEquals(c.textAfter(), paragraph.getText(), c.toString());
                assertEquals(c.runsAfter(), paragraph.getRuns().size(), c.toString());
                for (var run : textRuns) {
                    assertTrue(paragraph.getRuns().contains(run), "untouched run left the paragraph");
                    run.text();
                }
                for (var run : paragraph.getRuns()) {
                    assertTrue(isDescendant(run.getCTR().getDomNode(), liveNode), "run list holds a node outside the paragraph");
                }
                var saved = new java.io.ByteArrayOutputStream();
                document.write(saved);
                try (var reopened = new org.apache.poi.xwpf.usermodel.XWPFDocument(new java.io.ByteArrayInputStream(saved.toByteArray()))) {
                    var reopenedParagraph = reopened.getParagraphs().get(0);
                    assertEquals(c.textAfter(), reopenedParagraph.getText(), c.toString());
                    assertEquals(paragraphSequence((org.w3c.dom.Element) liveNode),
                            paragraphSequence((org.w3c.dom.Element) reopenedParagraph.getCTP().getDomNode()), c.toString());
                }
            }
        }
    }

    // After a failed attempt, saving and reopening gives back the untouched objects.
    @Test
    void savesUntouchedParagraphAfterFailedMultiObjectPatch() throws Exception {
        var a = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var b = mathObjectRef(2, wmfMathml("b", "-", "2"));
        Path temp = Files.createTempDirectory("docx-patch-xwpf-save");
        Path input = temp.resolve("input.docx");
        String documentXml = inlineObjectDocumentXml("", List.of(
                textRunXml("A "), mixedObjectRunXml(a), textRunXml(" B "), objectRunXml(b)));
        writeMinimalDocx(input, documentXml, List.of(a, b));
        try (var in = Files.newInputStream(input);
             var document = new org.apache.poi.xwpf.usermodel.XWPFDocument(in)) {
            var paragraph = document.getParagraphs().get(0);
            var objects = PoiMathSourceDetector.findDescendants(paragraph.getCTP().getDomNode(), "object");
            String omml = new XsltMathmlToOmmlConverter().convert(new BasicMathmlNormalizer().normalize(a.mathml()));
            assertFalse(new XmlBeansOmmlInjector().inject(MultiObjectPatchPlan.safe(paragraph, List.of(
                    ParagraphSegment.object(objects.get(0), null, "<bad"), ParagraphSegment.object(objects.get(1), null, omml)))));
            var saved = new java.io.ByteArrayOutputStream();
            document.write(saved);
            try (var reopened = new org.apache.poi.xwpf.usermodel.XWPFDocument(new java.io.ByteArrayInputStream(saved.toByteArray()))) {
                assertEquals(signature(bodyParagraphs(documentXml).get(0)),
                        signature(reopened.getParagraphs().get(0).getCTP().getDomNode()));
            }
        }
    }

    private static boolean isDescendant(org.w3c.dom.Node node, org.w3c.dom.Node ancestor) {
        for (var n = node; n != null; n = n.getParentNode()) {
            if (n == ancestor) return true;
        }
        return false;
    }

    // The walker covers body paragraphs and table cells only. Objects in content controls and in a
    // header are reported by container, never patched, and left exactly as they were.
    @Test
    void reportsObjectsOutsideWalkedParagraphsAndLeavesThemUnchanged() throws Exception {
        var body = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var blockSdt = mathObjectRef(2, wmfMathml("b", "+", "2"));
        var inlineSdt = mathObjectRef(3, wmfMathml("c", "+", "3"));
        var header = mathObjectRef(4, wmfMathml("d", "+", "4"));
        var objects = List.of(body, blockSdt, inlineSdt, header);
        String documentXml = inlineObjectDocumentXml("", List.of(textRunXml("Cho "), objectRunXml(body)))
                .replace("</w:p>", "</w:p>"
                        + "<w:sdt><w:sdtPr><w:alias w:val=\"eq\"/></w:sdtPr><w:sdtContent><w:p>"
                        + objectRunXml(blockSdt) + "</w:p></w:sdtContent></w:sdt>"
                        + "<w:p>" + textRunXml("Trong ") + "<w:sdt><w:sdtContent>" + objectRunXml(inlineSdt)
                        + "</w:sdtContent></w:sdt></w:p>");
        String headerXml = """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                       xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:v="urn:schemas-microsoft-com:vml">
                  <w:p>%s</w:p>
                </w:hdr>
                """.formatted(objectRunXml(header));
        Path temp = Files.createTempDirectory("docx-patch-unscanned");
        Path input = temp.resolve("input.docx");
        Path output = temp.resolve("output.docx");
        writeMinimalDocx(input, documentXml, objects, null, headerXml);
        var summary = new DocxMathPatchMain(ManifestMathSidecarRepository.load(writeManifest(temp, objects)))
                .patch(input, output);

        assertEquals(1, summary.patchedInline());
        assertEquals(1, summary.totalOccurrences());
        var inventory = summary.objectInventory();
        assertEquals(4, inventory.discovered());
        assertEquals(1, inventory.scanned());
        assertEquals(3, inventory.unscanned());
        assertEquals(java.util.Map.of("sdt", 2, "part:header", 1), inventory.unscannedByContainer());
        assertEquals(inventory.discovered(), inventory.scanned() + inventory.unscanned());

        String patched = readDocumentXml(output);
        var sourceSdts = parseNamespaceAware(documentXml).getElementsByTagNameNS(WORD_NS, "sdt");
        var patchedSdts = parseNamespaceAware(patched).getElementsByTagNameNS(WORD_NS, "sdt");
        assertEquals(2, patchedSdts.getLength());
        for (int i = 0; i < 2; i++) {
            assertEquals(signature(sourceSdts.item(i)), signature(patchedSdts.item(i)));
        }
        // POI re-serializes every XML part it loaded, so compare the header's XML, not its bytes.
        try (var in = new java.util.zip.ZipFile(input.toFile()); var out = new java.util.zip.ZipFile(output.toFile())) {
            var sourceHeader = new String(in.getInputStream(in.getEntry("word/header1.xml")).readAllBytes(), StandardCharsets.UTF_8);
            var patchedHeader = new String(out.getInputStream(out.getEntry("word/header1.xml")).readAllBytes(), StandardCharsets.UTF_8);
            assertEquals(signature(parseNamespaceAware(sourceHeader.strip()).getDocumentElement()),
                    signature(parseNamespaceAware(patchedHeader.strip()).getDocumentElement()));
        }
    }

    private static String twoParagraphDocumentXml(List<String> first, List<String> second) {
        return inlineObjectDocumentXml("", first)
                .replace("</w:p>", "</w:p><w:p>" + String.join("", second) + "</w:p>");
    }

    private static List<org.w3c.dom.Element> bodyParagraphs(String xml) throws Exception {
        var body = (org.w3c.dom.Element) parseNamespaceAware(xml).getElementsByTagNameNS(WORD_NS, "body").item(0);
        var paragraphs = new java.util.ArrayList<org.w3c.dom.Element>();
        for (var c = body.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (c instanceof org.w3c.dom.Element e && "p".equals(e.getLocalName())) paragraphs.add(e);
        }
        return paragraphs;
    }

    // getTextContent is DOM level 3, which the live XMLBeans DOM does not implement.
    private static String textOf(org.w3c.dom.Node node) {
        if (node.getNodeType() == org.w3c.dom.Node.TEXT_NODE) return node.getNodeValue();
        var text = new StringBuilder();
        for (var c = node.getFirstChild(); c != null; c = c.getNextSibling()) text.append(textOf(c));
        return text.toString();
    }

    // Paragraph children in order: runs as r{run properties}[content], equations as math'text'.
    private static List<String> paragraphSequence(org.w3c.dom.Element paragraph) {
        var sequence = new java.util.ArrayList<String>();
        for (var c = paragraph.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (!(c instanceof org.w3c.dom.Element e)) continue;
            if ("oMath".equals(e.getLocalName())) {
                var text = new StringBuilder();
                var ts = e.getElementsByTagNameNS(OMML_NS, "t");
                for (int i = 0; i < ts.getLength(); i++) text.append(textOf(ts.item(i)));
                sequence.add("math'" + text + "'");
            } else if ("r".equals(e.getLocalName())) {
                var properties = new java.util.ArrayList<String>();
                var content = new java.util.ArrayList<String>();
                for (var k = e.getFirstChild(); k != null; k = k.getNextSibling()) {
                    if (!(k instanceof org.w3c.dom.Element child)) continue;
                    if ("rPr".equals(child.getLocalName())) {
                        for (var p = child.getFirstChild(); p != null; p = p.getNextSibling()) {
                            if (p instanceof org.w3c.dom.Element prop) {
                                // XMLBeans DOM returns null, JAXP "" for a missing attribute.
                                String value = java.util.Objects.toString(prop.getAttributeNS(WORD_NS, "val"), "");
                                properties.add(prop.getLocalName() + (value.isEmpty() ? "" : "=" + value));
                            }
                        }
                    } else if ("t".equals(child.getLocalName())) {
                        content.add("t'" + textOf(child) + "'");
                    } else {
                        content.add(child.getLocalName());
                    }
                }
                sequence.add("r{" + String.join(",", properties) + "}[" + String.join(",", content) + "]");
            } else {
                sequence.add(e.getLocalName());
            }
        }
        return sequence;
    }

    // Children of the first body paragraph that holds math or an object (element names only).
    private static List<String> paragraphChildNames(String xml) throws Exception {
        var names = new java.util.ArrayList<String>();
        for (var c = equationParagraph(xml).getFirstChild(); c != null; c = c.getNextSibling()) {
            if (c.getNodeType() == org.w3c.dom.Node.ELEMENT_NODE) names.add(c.getLocalName());
        }
        return names;
    }

    private static org.w3c.dom.Element equationParagraph(String xml) throws Exception {
        var paragraphs = parseNamespaceAware(xml).getElementsByTagNameNS(WORD_NS, "p");
        for (int i = 0; i < paragraphs.getLength(); i++) {
            var p = (org.w3c.dom.Element) paragraphs.item(i);
            if (p.getElementsByTagNameNS(OMML_NS, "oMath").getLength() > 0
                    || p.getElementsByTagNameNS(WORD_NS, "object").getLength() > 0) {
                return p;
            }
        }
        throw new AssertionError("no paragraph with math or object");
    }

    private static String paragraphPropertiesSignature(String xml) throws Exception {
        for (var c = equationParagraph(xml).getFirstChild(); c != null; c = c.getNextSibling()) {
            if ("pPr".equals(c.getLocalName())) return signature(c);
        }
        return "";
    }

    // Namespace, name, sorted attributes (without namespace declarations) and non-blank text, recursively.
    private static String signature(org.w3c.dom.Node node) {
        if (node.getNodeType() == org.w3c.dom.Node.TEXT_NODE) {
            return node.getNodeValue().isBlank() ? "" : "'" + node.getNodeValue() + "'";
        }
        if (node.getNodeType() != org.w3c.dom.Node.ELEMENT_NODE) return "";
        var attributes = new java.util.TreeMap<String, String>();
        var map = node.getAttributes();
        for (int i = 0; i < map.getLength(); i++) {
            var a = map.item(i);
            if ("http://www.w3.org/2000/xmlns/".equals(a.getNamespaceURI())) continue;
            // XMLBeans DOM reports "" where a JAXP parser reports null for no namespace.
            attributes.put("{" + java.util.Objects.toString(a.getNamespaceURI(), "") + "}" + a.getLocalName(), a.getNodeValue());
        }
        var out = new StringBuilder("{" + node.getNamespaceURI() + "}" + node.getLocalName() + attributes + "[");
        for (var c = node.getFirstChild(); c != null; c = c.getNextSibling()) out.append(signature(c));
        return out.append("]").toString();
    }

    @Test
    void carriesEachObjectsOwnFormattingInMultiObjectParagraph() throws Exception {
        var first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var second = mathObjectRef(2, wmfMathml("b", "+", "2"));
        var result = runPatch(inlineObjectDocumentXml("", List.of(
                formattedObjectRunXml(first, "<w:rPr><w:sz w:val=\"20\"/></w:rPr>"), textRunXml(" và "),
                formattedObjectRunXml(second, "<w:rPr><w:sz w:val=\"30\"/></w:rPr>"))),
                List.of(first, second), List.of(first, second));
        assertEquals(2, result.summary.patchedInline());
        var equations = parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "oMath");
        assertEquals(2, equations.getLength());
        assertEquals("20", singleSize(equations.item(0)));
        assertEquals("30", singleSize(equations.item(1)));
    }

    private static final String OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";
    private static final String WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

    private static org.w3c.dom.Document parseNamespaceAware(String xml) throws Exception {
        var factory = javax.xml.parsers.DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        return factory.newDocumentBuilder().parse(new org.xml.sax.InputSource(new java.io.StringReader(xml)));
    }

    private static String singleSize(org.w3c.dom.Node equation) {
        var sizes = new java.util.TreeSet<String>();
        var runs = ((org.w3c.dom.Element) equation).getElementsByTagNameNS(OMML_NS, "r");
        for (int i = 0; i < runs.getLength(); i++) {
            var sz = ((org.w3c.dom.Element) runs.item(i)).getElementsByTagNameNS(WORD_NS, "sz");
            assertEquals(1, sz.getLength(), "every m:r needs the source size");
            sizes.add(((org.w3c.dom.Element) sz.item(0)).getAttributeNS(WORD_NS, "val"));
        }
        assertEquals(1, sizes.size());
        return sizes.first();
    }

    private static void assertMathRunsCarry(String xml, int equations, String size, String colour) throws Exception {
        var doc = parseNamespaceAware(xml);
        assertEquals(equations, doc.getElementsByTagNameNS(OMML_NS, "oMath").getLength());
        var runs = doc.getElementsByTagNameNS(OMML_NS, "r");
        assertTrue(runs.getLength() > 0);
        for (int i = 0; i < runs.getLength(); i++) {
            var props = (org.w3c.dom.Element) ((org.w3c.dom.Element) runs.item(i)).getElementsByTagNameNS(WORD_NS, "rPr").item(0);
            assertTrue(props != null, "m:r lost w:rPr");
            var names = new java.util.ArrayList<String>();
            for (var c = props.getFirstChild(); c != null; c = c.getNextSibling()) {
                if (c.getNodeType() == org.w3c.dom.Node.ELEMENT_NODE) names.add(c.getLocalName());
            }
            // Schema order, no bold/position leaking from the OLE picture run.
            assertEquals(List.of("rFonts", "color", "sz", "szCs", "highlight", "u"), names);
            assertEquals(size, ((org.w3c.dom.Element) props.getElementsByTagNameNS(WORD_NS, "sz").item(0)).getAttributeNS(WORD_NS, "val"));
            assertEquals(colour, ((org.w3c.dom.Element) props.getElementsByTagNameNS(WORD_NS, "color").item(0)).getAttributeNS(WORD_NS, "val"));
        }
    }

    private static String formattedObjectRunXml(MathObjectRef object, String runPropertiesXml) {
        return objectRunXml(object).replaceFirst("<w:r>", "<w:r>" + java.util.regex.Matcher.quoteReplacement(runPropertiesXml));
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
        assertOmmlIsParagraphChild(result.xml, 1);
        assertFalse(result.xml.contains("<w:object"));
    }

    @Test
    void preservesShortUnitsAndAnswerLabelsBesideSingleEquation() throws Exception {
        for (String label : List.of("Suy ra:", " (gam)", " kJ/mol.", "[A] ", ".", " ")) {
            var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
            for (boolean before : List.of(true, false)) {
                var runs = before ? List.of(textRunXml(label), objectRunXml(object))
                        : List.of(objectRunXml(object), textRunXml(label));
                String source = inlineObjectDocumentXml("", runs);
                var result = runPatch(source, List.of(object), List.of(object));
                if (!before && label.equals("Suy ra:")) {
                    assertEquals(0, result.summary.patchedInline());
                    assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
                    assertEquals(source, result.xml);
                    continue;
                }
                assertEquals(0, result.summary.patchedBlocks(), label);
                assertEquals(1, result.summary.patchedInline(), label);
                // The paragraph's own w:t values, in order around the equation (not a substring of
                // the package XML, which always contains "." and " ").
                var expected = before ? List.of("r{}[t'" + label + "']", "math'x+1'") : List.of("math'x+1'", "r{}[t'" + label + "']");
                assertEquals(expected, paragraphSequence(equationParagraph(result.xml)), label);
                assertOmmlIsParagraphChild(result.xml, 1);
            }
        }
    }

    @Test
    void preservesNumberedListParagraphByUsingInlinePatchForShortListLabel() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        numberedParagraphPrefixXml("7", "0"),
                        List.of(textRunXml("A. "), objectRunXml(object))
                ),
                List.of(object),
                List.of(object)
        );

        assertEquals(0, result.summary.patchedBlocks());
        assertEquals(1, result.summary.patchedInline());
        assertTrue(result.xml.contains("<w:numPr>"));
        assertTrue(result.xml.contains("A. "));
        assertTrue(result.xml.contains("oMath"));
        assertFalse(result.xml.contains("<w:object"));
    }

    @Test
    void preservesIndentedListLikeParagraphByUsingInlinePatchForShortLabel() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        indentedParagraphPrefixXml("720"),
                        List.of(textRunXml("a) "), objectRunXml(object))
                ),
                List.of(object),
                List.of(object)
        );

        assertEquals(0, result.summary.patchedBlocks());
        assertEquals(1, result.summary.patchedInline());
        assertTrue(result.xml.contains("<w:ind w:left=\"720\""));
        assertTrue(result.xml.contains("a) "));
        assertTrue(result.xml.contains("oMath"));
        assertFalse(result.xml.contains("<w:object"));
    }

    @Test
    void stripsKnownPrivateUseGlyphArtifactsFromPatchedOmml() throws Exception {
        MathObjectRef object = mathObjectRef(
                1,
                """
                <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline">
                  <mrow>
                    <mn>2</mn>
                    <mtext></mtext>
                    <mi>x</mi>
                    <mo>−</mo>
                    <mn>1</mn>
                  </mrow>
                </math>
                """
        );
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(textRunXml("f(x)="), objectRunXml(object), textRunXml(", với x>0."))
                ),
                List.of(object),
                List.of(object)
        );

        assertEquals(0, result.summary.patchedBlocks());
        assertEquals(1, result.summary.patchedInline());
        assertTrue(result.xml.contains("f(x)="));
        assertTrue(result.xml.contains(", với x>0."));
        assertTrue(result.xml.contains("−") || result.xml.contains("-"));
        assertFalse(result.xml.contains(""));
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
        assertOmmlIsParagraphChild(result.xml, 2);
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertFalse(result.xml.contains("<w:object"));
        assertContainsInOrder(result.xml, List.of("Alpha ", "a+1", " and ", "b-2", " omega"), List.of("a+1", "b-2"));
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
        assertContainsInOrder(result.xml, List.of("Before ", "a+1", ", ", "b+2", ", ", "c+3", " after"), List.of("a+1", "b+2", "c+3"));
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
        assertContainsInOrder(result.xml, List.of("s+1", " start ", "m+2", " end ", "e+3"), List.of("s+1", "m+2", "e+3"));
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
    void copiesInputBytesWhenSingleInlineObjectSharesParagraphWithNativeOmml() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("a", "+", "1"));
        Path tempDir = Files.createTempDirectory("docx-patch-native-single-copy");
        Path input = tempDir.resolve("input.docx");
        Path output = tempDir.resolve("output.docx");
        writeMinimalDocx(
                input,
                inlineObjectDocumentXml(
                        "<m:oMath><m:r><m:t>z</m:t></m:r></m:oMath>",
                        List.of(textRunXml(" mix "), objectRunXml(object))
                ),
                List.of(object)
        );

        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(
                ManifestMathSidecarRepository.load(writeManifest(tempDir, List.of()))
        ).patch(input, output);

        assertEquals(1, summary.nativeOmmlUntouched());
        assertEquals(0, summary.patchedBlocks());
        assertEquals(0, summary.patchedInline());
        assertEquals(0, summary.unresolved());
        assertEquals(1, summary.skippedUnsafeInlineObjects());
        assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.NATIVE_OMML_PRESENT));
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
    }

    @Test
    void copiesInputBytesWhenSingleBlockObjectSkipsEarlyWithNativeOmmlPresent() throws Exception {
        MathObjectRef object = mathObjectRef(1, wmfMathml("a", "+", "1"));
        Path tempDir = Files.createTempDirectory("docx-patch-native-single-block-copy");
        Path input = tempDir.resolve("input.docx");
        Path output = tempDir.resolve("output.docx");
        writeMinimalDocx(
                input,
                inlineObjectDocumentXml(
                        "<m:oMath><m:r><m:t>z</m:t></m:r></m:oMath>",
                        List.of(objectRunXml(object))
                ),
                List.of(object)
        );

        MathSourceDetector detector = (document, paragraph) -> new PoiMathSourceDetector().detect(document, paragraph).stream()
                .map(occurrence -> occurrence.sourceType() == MathOccurrence.SourceType.NATIVE_OMML
                        ? occurrence
                        : new MathOccurrence(
                                occurrence.sourceType(),
                                occurrence.document(),
                                occurrence.paragraph(),
                                occurrence.sourceNode(),
                                occurrence.runIndex(),
                                occurrence.oleRelationshipId(),
                                occurrence.previewRelationshipId(),
                                occurrence.olePartName(),
                                occurrence.previewPartName(),
                                true,
                                occurrence.paragraphHasNativeOmml(),
                                occurrence.paragraphObjectCount()
                        ))
                .toList();

        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(
                partName -> {
                    throw new AssertionError("sidecar lookup should not run for native-OMML single-block no-op");
                },
                rawMathml -> {
                    throw new AssertionError("mathml normalizer should not run for native-OMML single-block no-op");
                },
                normalizedMathml -> {
                    throw new AssertionError("mathml-to-omml should not run for native-OMML single-block no-op");
                },
                new OmmlInjector() {
                    @Override
                    public boolean inject(MathOccurrence occurrence, String ommlXml) {
                        throw new AssertionError("single-occurrence injector should not run for native-OMML single-block no-op");
                    }

                    @Override
                    public boolean inject(MultiObjectPatchPlan patchPlan) {
                        throw new AssertionError("multi-object injector should not run for native-OMML single-block no-op");
                    }
                },
                new DocxWalker(detector),
                new InlineSafetyEvaluator(),
                new MultiObjectSafetyEvaluator(),
                DocxMathPatchMain.LogLevel.SUMMARY
        ).patch(input, output);

        assertEquals(1, summary.nativeOmmlUntouched());
        assertEquals(0, summary.patchedBlocks());
        assertEquals(0, summary.patchedInline());
        assertEquals(0, summary.unresolved());
        assertEquals(0, summary.skippedUnsafeInlineObjects());
        assertEquals(1, summary.skipBreakdownCount(PatchSkipReason.NATIVE_OMML_PRESENT));
        assertArrayEquals(Files.readAllBytes(input), Files.readAllBytes(output));
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
    void patchesMultiObjectParagraphWithDrawingInsideObjectRun() throws Exception {
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

        assertEquals(2, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertFalse(result.xml.contains("<w:object"));
        assertTrue(result.xml.contains("<w:drawing/>"));
        assertContainsInOrder(result.xml, List.of("A ", "a+1", " B ", "b-2"), List.of("a+1", "b-2"));
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
        assertContainsInOrder(result.xml, List.of(" C.", " D.", " Cl - Cl ", "a+1", " ", "b-2"), List.of("a+1", "b-2"));
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
        assertContainsInOrder(result.xml, List.of("A ", "a+1", " B ", "b-2"), List.of("a+1", "b-2"));
    }

    @Test
    void patchesLastRenderedPageBreakCaseWhenRunMixesObjectAndText() throws Exception {
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

        assertEquals(2, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertTrue(result.xml.contains("<w:lastRenderedPageBreak/>"));
        assertContainsInOrder(result.xml, List.of("A ", "a+1", " inline ", "b-2"), List.of("a+1", "b-2"));
    }

    @Test
    void patchesDrawingCaseWhenRunStillMixesDrawingAndText() throws Exception {
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

        assertEquals(2, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertContainsInOrder(result.xml, List.of("A ", " helper ", "a+1", "b-2"), List.of("a+1", "b-2"));
    }

    @Test
    void patchesParagraphWithEightInlineObjectsAndPreservesSurroundingText() throws Exception {
        MathObjectRef first = mathObjectRef(1, wmfMathml("x", "+", "1"));
        MathObjectRef second = mathObjectRef(2, wmfMathml("x", "+", "2"));
        MathObjectRef third = mathObjectRef(3, wmfMathml("x", "+", "3"));
        MathObjectRef fourth = mathObjectRef(4, wmfMathml("x", "+", "4"));
        MathObjectRef fifth = mathObjectRef(5, wmfMathml("x", "+", "5"));
        MathObjectRef sixth = mathObjectRef(6, wmfMathml("x", "+", "6"));
        MathObjectRef seventh = mathObjectRef(7, wmfMathml("x", "+", "7"));
        MathObjectRef eighth = mathObjectRef(8, wmfMathml("x", "+", "8"));
        List<MathObjectRef> objects = List.of(first, second, third, fourth, fifth, sixth, seventh, eighth);
        PatchRunResult result = runPatch(
                inlineObjectDocumentXml(
                        "",
                        List.of(
                                textRunXml("Câu 2. ... trên hệ tọa độ "),
                                objectRunXml(first),
                                textRunXml(" ... Trong đó "),
                                objectRunXml(second),
                                textRunXml(" "),
                                objectRunXml(third),
                                textRunXml(" ... Gọi "),
                                objectRunXml(fourth),
                                textRunXml(", "),
                                objectRunXml(fifth),
                                textRunXml(", "),
                                objectRunXml(sixth),
                                textRunXml(" ... Ta có "),
                                objectRunXml(seventh),
                                textRunXml(". Giá trị của tổng "),
                                objectRunXml(eighth),
                                textRunXml(" ...")
                        )
                ),
                objects,
                objects
        );

        assertEquals(8, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectPatchedParagraphs());
        assertEquals(0, result.summary.skippedMultiObjectParagraphs());
        assertFalse(result.xml.contains("<w:object"));
        assertContainsInOrder(result.xml, List.of("Câu 2. ... trên hệ tọa độ ", "x+1", "Trong đó ", "x+2", "x+3", "Gọi ", "x+4", "x+5", "x+6", "Ta có ", "x+7", "Giá trị của tổng ", "x+8"), List.of("x+1", "x+2", "x+3", "x+4", "x+5", "x+6", "x+7", "x+8"));
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

    private static void assertOmmlIsParagraphChild(String xml, int count) throws Exception {
        var factory = javax.xml.parsers.DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        var doc = factory.newDocumentBuilder().parse(new org.xml.sax.InputSource(new java.io.StringReader(xml)));
        var equations = doc.getElementsByTagNameNS("http://schemas.openxmlformats.org/officeDocument/2006/math", "oMath");
        assertEquals(count, equations.getLength());
        for (int i = 0; i < equations.getLength(); i++) {
            var parent = equations.item(i).getParentNode();
            assertEquals("p", parent.getLocalName(), "inline OMML must be a paragraph child, not nested in w:r");
            assertEquals("http://schemas.openxmlformats.org/wordprocessingml/2006/main", parent.getNamespaceURI());
        }
    }

    @Test
    void retainsInlineObjectWhenFollowingWordHasNoExplicitSeparator() throws Exception {
        var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>p</mi><mn>,</mn></math>");
        for (String following : List.of("khối lượng", "theo", "𝑥")) {
            String source = inlineObjectDocumentXml("", List.of(
                    textRunXml("Áp suất "), objectRunXml(object), textRunXml(following)));
            var result = runPatch(source, List.of(object), List.of(object));
            assertEquals(0, result.summary.patchedInline(), following);
            assertEquals(1, result.summary.skippedUnsafeInlineObjects(), following);
            assertEquals(0, result.summary.unresolved(), following);
            assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW), following);
            assertEquals(source, result.xml, "no guessed space or formula/prose mutation");
        }
    }

    @Test
    void retainsWholeMultiObjectParagraphAtUnseparatedWordBoundary() throws Exception {
        var first = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>p</mi></math>");
        var second = mathObjectRef(2, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>V</mi></math>");
        String source = inlineObjectDocumentXml("", List.of(textRunXml("Áp suất "), objectRunXml(first),
                "<w:bookmarkStart w:id=\"7\" w:name=\"boundary\"/>", "<w:r><w:rPr/></w:r>",
                "<w:proofErr w:type=\"spellStart\"/>", "<w:r><w:t/></w:r>",
                "<w:bookmarkEnd w:id=\"7\"/>", textRunXml("theo "), objectRunXml(second), textRunXml(" .")));
        var result = runPatch(source, List.of(first, second), List.of(first, second));
        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.multiObjectSkippedUnsafeParagraphs());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
        assertEquals(0, result.summary.unresolved());
        assertEquals(source, result.xml, "all objects and boundary markup remain intact");
    }

    @Test
    void retainsMixedRunWhenLetterFollowsObjectBeforeNextRun() throws Exception {
        var first = mathObjectRef(1, wmfMathml("p", "+", "1"));
        var second = mathObjectRef(2, wmfMathml("V", "+", "2"));
        String source = inlineObjectDocumentXml("", List.of(
                mixedObjectRunXml(first).replace(" post", "khối"), textRunXml(" và "), objectRunXml(second)));
        var result = runPatch(source, List.of(first, second), List.of(first, second));
        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
        assertEquals(1, result.summary.multiObjectSkippedUnsafeParagraphs());
        assertEquals(source, result.xml);
    }

    @Test
    void renderedPageBreakIsNotAnExplicitSeparatorBeforeFollowingLetter() throws Exception {
        var object = mathObjectRef(1, wmfMathml("p", "+", "1"));
        String source = inlineObjectDocumentXml("", List.of(textRunXml("Áp suất "), objectRunXml(object),
                "<w:r><w:lastRenderedPageBreak/><w:t>theo</w:t></w:r>"));
        var result = runPatch(source, List.of(object), List.of(object));
        assertEquals(0, result.summary.patchedInline());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
        assertEquals(source, result.xml);
    }

    @Test
    void nativeAndMissingSidecarKeepPriorityOverInlineBoundaryRetention() throws Exception {
        var first = mathObjectRef(1, wmfMathml("p", "+", "1"));
        var second = mathObjectRef(2, wmfMathml("V", "+", "2"));
        for (boolean multi : List.of(false, true)) {
            var objects = multi ? List.of(first, second) : List.of(first);
            var runs = new java.util.ArrayList<>(List.of(textRunXml("Áp suất "), objectRunXml(first), textRunXml("khối")));
            if (multi) runs.add(objectRunXml(second));
            String missingSource = inlineObjectDocumentXml("", runs);
            var missing = runPatch(missingSource, objects, List.of());
            assertEquals(1, missing.summary.unresolved());
            assertEquals(1, missing.summary.skipBreakdownCount(PatchSkipReason.UNRESOLVED_MANIFEST));
            assertEquals(0, missing.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
            assertEquals(missingSource, missing.xml);
            String nativeSource = inlineObjectDocumentXml("<m:oMath><m:r><m:t>z</m:t></m:r></m:oMath>", runs);
            var nativeResult = runPatch(nativeSource, objects, List.of());
            assertEquals(1, nativeResult.summary.skipBreakdownCount(PatchSkipReason.NATIVE_OMML_PRESENT));
            assertEquals(0, nativeResult.summary.unresolved());
            assertEquals(0, nativeResult.summary.skipBreakdownCount(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW));
            assertEquals(nativeSource, nativeResult.xml);
        }
    }

    @Test
    void explicitSeparatorOrNonLetterDoesNotTriggerInlineBoundaryRetention() throws Exception {
        var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>p</mi></math>");
        for (String following : List.of(textRunXml(" khối"), textRunXml("\u00a0khối"),
                textRunXml(", khối"), "<w:r><w:tab/><w:t>khối</w:t></w:r>",
                "<w:r><w:br/><w:t>khối</w:t></w:r>")) {
            var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Áp suất "),
                    objectRunXml(object), following)), List.of(object), List.of(object));
            assertEquals(1, result.summary.patchedInline(), following);
            assertEquals(0, result.summary.skippedUnsafeInlineObjects(), following);
            assertEquals(0, result.summary.unresolved(), following);
        }
    }

    @Test
    void conversionFailureKeepsPriorityOverUnseparatedWordBoundary() throws Exception {
        var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>\u2061</mi></math>");
        String source = inlineObjectDocumentXml("", List.of(textRunXml("Áp suất "),
                objectRunXml(object), textRunXml("khối")));
        var result = runPatch(source, List.of(object), List.of(object));
        assertEquals(1, result.summary.unresolved());
        assertEquals(1, result.summary.skipBreakdownCount(PatchSkipReason.OMML_CONVERSION_FAILED));
        assertEquals(0, result.summary.skippedUnsafeInlineObjects());
        assertEquals(source, result.xml);
    }

    @Test
    void keepsNewLegacyInlineRelationsInsideOneUnbreakableMathGroup() throws Exception {
        var samples = List.of(
                "<mi>A</mi><mi>B</mi><mo>=</mo><mi>C</mi><mi>D</mi><mo>=</mo><mn>16</mn><mi>c</mi><mi>m</mi>",
                "<mover accent=\"true\"><mi>u</mi><mo>→</mo></mover><mo>=</mo><mfenced open=\"(\" close=\")\" separators=\"\"><mn>5</mn><mo>;</mo><mn>2</mn><mo>;</mo><mo>−</mo><mn>3</mn></mfenced>",
                "<mi>B</mi><mo>=</mo><mn>0,400</mn>");
        var expected = List.of("AB=CD=16cm", "u=5;2;−3", "B=0,400");
        for (int i = 0; i < samples.size(); i++) {
            var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">" + samples.get(i) + "</math>");
            var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Biết "),
                    objectRunXml(object), textRunXml(", tiếp tục."))), List.of(object), List.of(object));
            assertEquals(1, result.summary.patchedInline());
            var doc = parseNamespaceAware(result.xml);
            var xp = javax.xml.xpath.XPathFactory.newInstance().newXPath();
            String root = "//*[local-name()='oMath']";
            assertEquals("on", xp.evaluate(root + "/*[local-name()='box']/*[local-name()='boxPr']/*[local-name()='noBreak']/@*[local-name()='val']", doc));
            assertEquals("1", xp.evaluate("count(" + root + "/*)", doc));
            assertEquals("boxPr", xp.evaluate("local-name(" + root + "/*[local-name()='box']/*[1])", doc));
            assertEquals("e", xp.evaluate("local-name(" + root + "/*[local-name()='box']/*[2])", doc));
            assertEquals("2", xp.evaluate("count(" + root + "/*[local-name()='box']/*)", doc));
            assertEquals(1, ((org.w3c.dom.Element) doc.getElementsByTagNameNS(OMML_NS, "oMath").item(0)).getElementsByTagNameNS(OMML_NS, "box").getLength());
            assertEquals(expected.get(i), xp.evaluate(root + "/*[local-name()='box']/*[local-name()='e']", doc));
            if (i == 1) {
                String expression = root + "/*[local-name()='box']/*[local-name()='e']";
                assertEquals("1", xp.evaluate("count(" + expression + "/*[local-name()='acc'])", doc));
                // Word uses the combining right-arrow accent U+20D7 for this MathML mover.
                assertEquals("\u20d7", xp.evaluate(expression + "/*[local-name()='acc']/*[local-name()='accPr']/*[local-name()='chr']/@*[local-name()='val']", doc));
                assertEquals("1", xp.evaluate("count(" + expression + "/*[local-name()='d'])", doc));
                // Missing begChr/endChr means Word's default parentheses, not an empty fence.
                String delimiter = expression + "/*[local-name()='d']/*[local-name()='dPr']";
                assertEquals("0", xp.evaluate("count(" + delimiter + "/*[local-name()='begChr'][not(@*[local-name()='val']='(')])", doc));
                assertEquals("0", xp.evaluate("count(" + delimiter + "/*[local-name()='endChr'][not(@*[local-name()='val']=')')])", doc));
            }
            assertEquals(0, doc.getElementsByTagNameNS(WORD_NS, "object").getLength());
        }
    }

    @Test
    void groupsLeadingTemperatureComparisonWithoutAddingAnOperandOrCharacter() throws Exception {
        String content = "<mo>&gt;</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext>";
        var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">" + content + "</math>");
        var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Điều kiện ("),
                objectRunXml(object), textRunXml(") tiếp tục."))), List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedInline());
        var doc = parseNamespaceAware(result.xml);
        var xp = javax.xml.xpath.XPathFactory.newInstance().newXPath();
        String e = "//*[local-name()='oMath']/*[local-name()='box']/*[local-name()='e']";
        String d = e + "/*[1]";
        assertEquals("d", xp.evaluate("local-name(" + d + ")", doc));
        assertEquals("1", xp.evaluate("count(" + d + "/*[local-name()='dPr']/*[local-name()='begChr'][@*[local-name()='val']=''])", doc));
        assertEquals("1", xp.evaluate("count(" + d + "/*[local-name()='dPr']/*[local-name()='endChr'][@*[local-name()='val']=''])", doc));
        assertEquals(">", xp.evaluate(d + "/*[local-name()='e']", doc));
        assertEquals("1", xp.evaluate("count(" + d + "/*[local-name()='e']/*[local-name()='r'])", doc));
        assertEquals(">150°C", xp.evaluate(e, doc));
        assertEquals("0", xp.evaluate("count(" + e + "//*[local-name()='e'][not(*)])", doc));
        assertEquals("sSup", xp.evaluate("local-name(" + e + "/*[2])", doc));
        assertEquals("C", xp.evaluate(e + "/*[3]", doc));
        var block = runPatch(oleObjectDocumentXml(object), List.of(object), List.of(object));
        assertEquals(1, block.summary.patchedBlocks());
        assertEquals(0, parseNamespaceAware(block.xml).getElementsByTagNameNS(OMML_NS, "d").getLength());
    }

    @Test
    void doesNotExtendTemperatureGroupingToOtherRelationsOrUnverifiedShapes() throws Exception {
        for (String content : List.of(
                "<mo>&gt;</mo>", "<mo>&gt;</mo><mn>150</mn>",
                "<mi>x</mi><mo>&gt;</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext>",
                "<mo>&lt;</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext>",
                "<mo>−</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext>",
                "<mtext>&gt;</mtext><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext>",
                "<mo>&gt;</mo><msup><mi>x</mi><mo>°</mo></msup><mtext>C</mtext>",
                "<mo>&gt;</mo><msup><mn>150</mn><mo>2</mo></msup><mtext>C</mtext>",
                "<mo>&gt;</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>F</mtext>")) {
            var object = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">" + content + "</math>");
            var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Biết ("),
                    objectRunXml(object), textRunXml(")."))), List.of(object), List.of(object));
            assertEquals(1, result.summary.patchedInline(), content);
            assertEquals(0, parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "d").getLength(), content);
        }
    }

    @Test
    void temperatureGroupingCarriesColorAndSizeInMultiObjectParagraph() throws Exception {
        var first = mathObjectRef(1, "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mo>&gt;</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext></math>");
        var second = mathObjectRef(2, wmfMathml("x", "+", "1"));
        String formatted = objectRunXml(first).replace("<w:r>",
                "<w:r><w:rPr><w:color w:val=\"123456\"/><w:sz w:val=\"28\"/></w:rPr>");
        var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Cho ("), formatted,
                textRunXml(") và "), objectRunXml(second), textRunXml("."))),
                List.of(first, second), List.of(first, second));
        assertEquals(2, result.summary.patchedInline());
        var doc = parseNamespaceAware(result.xml);
        var xp = javax.xml.xpath.XPathFactory.newInstance().newXPath();
        String run = "//*[local-name()='d']/*[local-name()='e']/*[local-name()='r']";
        assertEquals("1", xp.evaluate("count(//*[local-name()='d'])", doc));
        assertEquals(">", xp.evaluate(run + "/*[local-name()='t']", doc));
        assertEquals("123456", xp.evaluate(run + "/*[local-name()='rPr']/*[local-name()='color']/@*[local-name()='val']", doc));
        assertEquals("28", xp.evaluate(run + "/*[local-name()='rPr']/*[local-name()='sz']/@*[local-name()='val']", doc));
    }

    @Test
    void temperatureGroupingRejectsSpacedOperatorText() throws Exception {
        var object = mathObjectRef(1, wmfMathml("x", "+", "1"));
        Path path = Files.createTempDirectory("spaced-temperature").resolve("input.docx");
        writeMinimalDocx(path, inlineObjectDocumentXml("", List.of(textRunXml("Cho "), objectRunXml(object))), List.of(object));
        try (var in = Files.newInputStream(path); var document = new org.apache.poi.xwpf.usermodel.XWPFDocument(in)) {
            var occurrence = new DocxWalker(new PoiMathSourceDetector()).collect(document).get(0);
            String omml = "<m:oMath xmlns:m=\"" + OMML_NS + "\"><m:r><m:t xml:space=\"preserve\"> &gt; </m:t></m:r><m:sSup><m:e><m:r><m:t>150</m:t></m:r></m:e><m:sup><m:r><m:t>°</m:t></m:r></m:sup></m:sSup><m:r><m:t>C</m:t></m:r></m:oMath>";
            assertTrue(new XmlBeansOmmlInjector().inject(occurrence, omml));
            var parsed = parseNamespaceAware(occurrence.paragraph().getCTP().xmlText());
            assertEquals(0, parsed.getElementsByTagNameNS(OMML_NS, "d").getLength());
            assertEquals(" > ", parsed.getElementsByTagNameNS(OMML_NS, "t").item(0).getTextContent());
        }
    }

    @Test
    void multiObjectParagraphKeepsEachLegacyEquationInItsOwnUnbreakableGroup() throws Exception {
        var first = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var second = mathObjectRef(2, wmfMathml("b", "-", "2"));
        var result = runPatch(inlineObjectDocumentXml("", List.of(textRunXml("Biết "), objectRunXml(first),
                textRunXml(" và "), objectRunXml(second), textRunXml(" ."))), List.of(first, second), List.of(first, second));
        var doc = parseNamespaceAware(result.xml);
        assertEquals(2, result.summary.patchedInline());
        assertEquals(2, doc.getElementsByTagNameNS(OMML_NS, "box").getLength());
        assertEquals(2, doc.getElementsByTagNameNS(OMML_NS, "noBreak").getLength());
        for (int i = 0; i < 2; i++) {
            var equation = doc.getElementsByTagNameNS(OMML_NS, "oMath").item(i);
            var xp = javax.xml.xpath.XPathFactory.newInstance().newXPath();
            assertEquals("1", xp.evaluate("count(*)", equation));
            assertEquals("1", xp.evaluate("count(*[local-name()='box']/*[local-name()='boxPr']/*[local-name()='noBreak'])", equation));
        }
        assertEquals(List.of("r{}[t'Biết ']", "math'a+1'", "r{}[t' và ']", "math'b-2'", "r{}[t' .']"),
                paragraphSequence(equationParagraph(result.xml)));
    }

    @Test
    void displayConversionDoesNotReceiveAnInlineNoBreakWrapper() throws Exception {
        var object = mathObjectRef(1, wmfMathml("a", "+", "1"));
        var result = runPatch(oleObjectDocumentXml(object), List.of(object), List.of(object));
        assertEquals(1, result.summary.patchedBlocks());
        assertEquals(0, parseNamespaceAware(result.xml).getElementsByTagNameNS(OMML_NS, "box").getLength());
    }

    @Test
    void rejectsUnverifiedInlineOmmlRootsWithoutMutatingOriginalParagraph() throws Exception {
        String m = "xmlns:m=\"" + OMML_NS + "\"";
        var invalidRoots = List.of(
                "<m:oMathPara " + m + "><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath><m:oMath><m:r><m:t>y</m:t></m:r></m:oMath></m:oMathPara>",
                "<m:r " + m + "><m:t>x</m:t></m:r>",
                "<x:oMath xmlns:x=\"urn:foreign\"><x:r><x:t>x</x:t></x:r></x:oMath>",
                "<m:oMathPara " + m + "><w:r xmlns:w=\"" + WORD_NS + "\"/><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></m:oMathPara>",
                "<m:oMathPara " + m + "><![CDATA[lost text]]><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></m:oMathPara>",
                "<m:oMathPara " + m + "><m:oMathParaPr/></m:oMathPara>");
        for (String omml : invalidRoots) {
            for (boolean multi : List.of(false, true)) {
                var a = mathObjectRef(1, wmfMathml("a", "+", "1"));
                var b = mathObjectRef(2, wmfMathml("b", "+", "2"));
                var objects = multi ? List.of(a, b) : List.of(a);
                var runs = new java.util.ArrayList<>(List.of(textRunXml("Cho "), objectRunXml(a), textRunXml(" .")));
                if (multi) runs.add(objectRunXml(b));
                Path file = Files.createTempDirectory("inline-root-rejection").resolve("input.docx");
                writeMinimalDocx(file, inlineObjectDocumentXml("", runs), objects);
                try (var in = Files.newInputStream(file); var doc = new org.apache.poi.xwpf.usermodel.XWPFDocument(in)) {
                    var occurrences = new DocxWalker(new PoiMathSourceDetector()).collect(doc);
                    var paragraph = occurrences.get(0).paragraph();
                    String before = paragraph.getCTP().xmlText();
                    var injector = new XmlBeansOmmlInjector();
                    if (multi) {
                        var segments = List.of(ParagraphSegment.object(occurrences.get(0).sourceNode(), occurrences.get(0), omml),
                                ParagraphSegment.object(occurrences.get(1).sourceNode(), occurrences.get(1), "<m:oMath " + m + "><m:r><m:t>z</m:t></m:r></m:oMath>"));
                        assertFalse(injector.inject(MultiObjectPatchPlan.safe(paragraph, segments)), omml);
                    } else {
                        assertFalse(injector.inject(occurrences.get(0), omml), omml);
                    }
                    assertEquals(before, paragraph.getCTP().xmlText(), "root rejection preserves live paragraph");
                    assertEquals(objects.size(), new DocxWalker(new PoiMathSourceDetector()).collect(doc).size());
                }
            }
        }
    }

    @Test
    void singleEquationMathParagraphRootRetainsAllItsMathContentInline() throws Exception {
        var object = mathObjectRef(1, wmfMathml("a", "+", "1"));
        Path file = Files.createTempDirectory("inline-paragraph-root").resolve("input.docx");
        writeMinimalDocx(file, inlineObjectDocumentXml("", List.of(textRunXml("Cho "), objectRunXml(object))), List.of(object));
        try (var in = Files.newInputStream(file); var doc = new org.apache.poi.xwpf.usermodel.XWPFDocument(in)) {
            var occurrence = new DocxWalker(new PoiMathSourceDetector()).collect(doc).get(0);
            assertTrue(new XmlBeansOmmlInjector().inject(occurrence,
                    "<m:oMathPara xmlns:m=\"" + OMML_NS + "\"><m:oMathParaPr/><m:oMath><m:r><m:t>x+1</m:t></m:r></m:oMath></m:oMathPara>"));
            var parsed = parseNamespaceAware(occurrence.paragraph().getCTP().xmlText());
            assertEquals(0, parsed.getElementsByTagNameNS(OMML_NS, "oMathPara").getLength());
            assertEquals(0, parsed.getElementsByTagNameNS(OMML_NS, "oMathParaPr").getLength());
            var math = parsed.getElementsByTagNameNS(OMML_NS, "oMath").item(0);
            // CTP.xmlText serializes paragraph contents in an xml-fragment root.
            // A direct child of that root is a direct child of the live paragraph.
            org.junit.jupiter.api.Assertions.assertSame(parsed.getDocumentElement(), math.getParentNode());
            var xp = javax.xml.xpath.XPathFactory.newInstance().newXPath();
            assertEquals("on", xp.evaluate("//*[local-name()='oMath']/*[local-name()='box']/*[local-name()='boxPr']/*[local-name()='noBreak']/@*[local-name()='val']", parsed));
            assertEquals("Cho ", xp.evaluate("//*[local-name()='oMath']/preceding-sibling::*[local-name()='r'][1]/*[local-name()='t']", parsed));
            assertEquals(1, parsed.getElementsByTagNameNS(OMML_NS, "box").getLength());
            assertEquals("x+1", parsed.getElementsByTagNameNS(OMML_NS, "e").item(0).getTextContent());
            assertEquals(0, parsed.getElementsByTagNameNS(WORD_NS, "object").getLength());
        }
    }

    private PatchRunResult runPatch(
            String documentXml,
            List<MathObjectRef> documentObjects,
            List<MathObjectRef> manifestObjects
    ) throws Exception {
        return runPatch(documentXml, null, documentObjects, manifestObjects);
    }

    private PatchRunResult runPatch(
            String documentXml,
            String stylesXml,
            List<MathObjectRef> documentObjects,
            List<MathObjectRef> manifestObjects
    ) throws Exception {
        Path tempDir = Files.createTempDirectory("docx-patch-workflow");
        Path input = tempDir.resolve("input.docx");
        Path output = tempDir.resolve("output.docx");
        writeMinimalDocx(input, documentXml, documentObjects, stylesXml, null);
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
        writeMinimalDocx(path, documentXml, objects, null, null);
    }

    private static void writeMinimalDocx(
            Path path, String documentXml, List<MathObjectRef> objects, String stylesXml, String headerXml
    ) throws IOException {
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(path))) {
            String extraTypes = (stylesXml == null ? "" : "<Override PartName=\"/word/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml\"/>")
                    + (headerXml == null ? "" : "<Override PartName=\"/word/header1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml\"/>");
            String extraRelationships = (stylesXml == null ? "" : "<Relationship Id=\"rIdStyles\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>")
                    + (headerXml == null ? "" : "<Relationship Id=\"rIdHeader1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/header\" Target=\"header1.xml\"/>");
            put(zip, "[Content_Types].xml", contentTypesXml().replace("</Types>", extraTypes + "</Types>"));
            put(zip, "_rels/.rels", packageRelationshipsXml());
            put(zip, "word/document.xml", documentXml);
            put(zip, "word/_rels/document.xml.rels",
                    documentRelationshipsXml(objects).replace("</Relationships>", extraRelationships + "</Relationships>"));
            if (stylesXml != null) {
                put(zip, "word/styles.xml", stylesXml);
            }
            if (headerXml != null) {
                put(zip, "word/header1.xml", headerXml);
            }
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
                      %s
                    </w:p>
                    %s
                  </w:body>
                </w:document>
                """.formatted(CENTRED_PARAGRAPH, objectRunXml(object), sectionXml());
    }

    // A MathType display equation paragraph: centred and holding only the object.
    private static final String CENTRED_PARAGRAPH = "<w:pPr><w:jc w:val=\"center\"/></w:pPr>";

    private static String tableObjectDocumentXml(String tablePropertiesXml, String paragraphPropertiesXml, List<String> runs) {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                            xmlns:o="urn:schemas-microsoft-com:office:office"
                            xmlns:v="urn:schemas-microsoft-com:vml"
                            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
                  <w:body>
                    <w:tbl>
                      <w:tblPr>%s</w:tblPr>
                      <w:tblGrid><w:gridCol w:w="4000"/></w:tblGrid>
                      <w:tr><w:tc><w:tcPr><w:tcW w:w="4000" w:type="dxa"/></w:tcPr>
                        <w:p>%s%s</w:p>
                      </w:tc></w:tr>
                    </w:tbl>
                    <w:p/>
                    %s
                  </w:body>
                </w:document>
                """.formatted(tablePropertiesXml, paragraphPropertiesXml, String.join("", runs), sectionXml());
    }

    private static String stylesXml(String docDefaultParagraphPropertiesXml, String... styles) {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:docDefaults><w:pPrDefault>%s</w:pPrDefault></w:docDefaults>
                  %s
                </w:styles>
                """.formatted(docDefaultParagraphPropertiesXml, String.join("\n", styles));
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

    private static String numberedParagraphPrefixXml(String numId, String ilvl) {
        return """
                <w:pPr>
                  <w:numPr>
                    <w:ilvl w:val="%s"/>
                    <w:numId w:val="%s"/>
                  </w:numPr>
                </w:pPr>
                """.formatted(escapeXml(ilvl), escapeXml(numId));
    }

    private static String indentedParagraphPrefixXml(String left) {
        return """
                <w:pPr>
                  <w:ind w:left="%s"/>
                </w:pPr>
                """.formatted(escapeXml(left));
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

    private static String assertionFixture(String body) {
        return "<w:document xmlns:w='" + WORD_NS + "' xmlns:m='" + OMML_NS + "'><w:body><w:p>" + body + "</w:p></w:body></w:document>";
    }

    @Test void rejectsFormulaLeakingIntoProse() throws Exception {
        String xml=assertionFixture("<m:oMath><m:r><m:t>a+</m:t></m:r></m:oMath><w:r><w:t>1</w:t></w:r>");
        org.junit.jupiter.api.Assertions.assertThrows(AssertionError.class, () -> assertContainsInOrder(xml, List.of("a+1"), List.of("a+1")));
    }
    @Test void rejectsFormulaSplitAcrossTwoEquations() throws Exception {
        String xml=assertionFixture("<m:oMath><m:r><m:t>a+</m:t></m:r></m:oMath><m:oMath><m:r><m:t>1</m:t></m:r></m:oMath>");
        org.junit.jupiter.api.Assertions.assertThrows(AssertionError.class, () -> assertContainsInOrder(xml, List.of("a+1"), List.of("a+1")));
    }
    @Test void rejectsProseMasqueradingAsEquation() throws Exception {
        String xml=assertionFixture("<w:r><w:t>a+1</w:t></w:r>");
        org.junit.jupiter.api.Assertions.assertThrows(AssertionError.class, () -> assertContainsInOrder(xml, List.of("a+1"), List.of("a+1")));
    }
    @Test void acceptsSplitMathRunsWithinOneEquation() throws Exception {
        String xml=assertionFixture("<m:oMath><m:r><m:t>a</m:t></m:r><m:r><m:t>+</m:t></m:r><m:r><m:t>1</m:t></m:r></m:oMath>");
        assertContainsInOrder(xml, List.of("a+1"), List.of("a+1"));
    }
    private static void assertEquationTexts(String xml, List<String> expected) throws Exception {
        var equations = parseNamespaceAware(xml).getElementsByTagNameNS(OMML_NS, "oMath");
        var actual = new java.util.ArrayList<String>();
        for (int i = 0; i < equations.getLength(); i++) {
            var equation = (org.w3c.dom.Element) equations.item(i);
            assertEquals(0, equation.getElementsByTagNameNS(WORD_NS, "t").getLength(), "prose inside equation");
            var texts = equation.getElementsByTagNameNS(OMML_NS, "t");
            var text = new StringBuilder();
            for (int j = 0; j < texts.getLength(); j++) text.append(texts.item(j).getTextContent());
            actual.add(text.toString());
        }
        assertEquals(expected, actual, "complete payload per oMath, in document order");
    }

    private static void assertContainsInOrder(String xml, List<String> needles, List<String> equations) throws Exception {
        assertEquationTexts(xml, equations);
        assertVisibleTextInOrder(xml, needles);
    }

    private static String visibleText(String xml) throws Exception {
        var nodes = parseNamespaceAware(xml).getElementsByTagNameNS("*", "t");
        var out = new StringBuilder();
        for (int i = 0; i < nodes.getLength(); i++) {
            var node = nodes.item(i);
            if (WORD_NS.equals(node.getNamespaceURI()) || OMML_NS.equals(node.getNamespaceURI()))
                out.append(node.getTextContent());
        }
        return out.toString();
    }

    private static void assertVisibleTextInOrder(String haystack, List<String> needles) throws Exception {
        // Compare visible prose/math tokens, independent of valid math-run boundaries.
        haystack = visibleText(haystack);
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
