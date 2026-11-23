package com.example.docxmath;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

// Same vectors as tests/test_mathml_content.py, so the Java and Python gates cannot drift apart.
final class MathmlContentVectorTest {
    private static final Path VECTORS = Path.of("fixtures/mathml_content/visible_content_vectors.json");
    private static final String MATHML_NS = "http://www.w3.org/1998/Math/MathML";
    private static final String OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";

    @Test
    void normalTextSymbolReviewGateCoversSharedScopeAndOnOffValues() {
        for (String symbol : new String[]{"ℝ", "ℓ", "ℂ", "ℚ", "ⅆ", "ℋ", "𝐯", "𝑥"}) {
            for (String val : new String[]{"", "1", "on", "true", "0", "false", "off"}) {
                String prop = val.isEmpty() ? "<m:nor/>" : "<m:nor m:val=\"" + val + "\"/>";
                String xml = "<m:oMath xmlns:m=\"" + OMML_NS + "\"><m:r><m:rPr>" + prop
                        + "</m:rPr><m:t>x " + symbol + "</m:t></m:r></m:oMath>";
                assertEquals(java.util.Set.of("0", "false", "off").contains(val),
                        MathmlContent.hasOmmlRunContent(xml), symbol + "/" + val);
            }
        }
        assertTrue(MathmlContent.hasOmmlRunContent("<m:oMath xmlns:m=\"" + OMML_NS
                + "\"><m:r><m:rPr><m:nor/></m:rPr><m:t>20 km</m:t></m:r></m:oMath>"));
    }

    @Test
    void ommlDiagnosticsDistinguishReviewFromEmptyAndMissingBase() {
        String start = "<m:oMath xmlns:m=\"" + OMML_NS + "\">";
        assertEquals("normal_text_symbol_requires_review", MathmlContent.ommlRejectionReason(start
                + "<m:r><m:rPr><m:nor/></m:rPr><m:t>xℂ</m:t></m:r></m:oMath>"));
        assertEquals("empty_math_content", MathmlContent.ommlRejectionReason(start + "</m:oMath>"));
        assertEquals("missing_script_base", MathmlContent.ommlRejectionReason(start
                + "<m:sSup><m:e/><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:oMath>"));
        assertEquals(null, MathmlContent.ommlRejectionReason(start
                + "<m:r><m:t>x</m:t></m:r></m:oMath>"));
    }

    @Test
    void invisibleNonspacingControlsAloneAreNotFormulas() {
        for (int cp : new int[]{0x034F, 0x180B, 0x180D, 0x180F, 0xFE00, 0xFE0F, 0xE0100, 0xE01EF}) {
            String label = Integer.toHexString(cp);
            String token = "&#x" + label + ";";
            assertEquals(false, MathmlContent.isVisibleCodePoint(cp), label);
            assertEquals(false, MathmlContent.hasFormula("<math><mi>" + token + "</mi></math>"), label);
            assertEquals(false, MathmlContent.hasOmmlRunContent("<m:oMath xmlns:m=\"" + OMML_NS
                    + "\"><m:r><m:t>" + token + "</m:t></m:r></m:oMath>"), label);
            assertTrue(MathmlContent.hasFormula("<math><mi>x" + token + "</mi></math>"), label);
            assertTrue(MathmlContent.hasOmmlRunContent("<m:oMath xmlns:m=\"" + OMML_NS
                    + "\"><m:r><m:t>x" + token + "</m:t></m:r></m:oMath>"), label);
        }
        assertTrue(MathmlContent.isVisibleCodePoint(0x0300), "ordinary combining accent");
    }

    @Test
    void codePointsMatchSharedVectorsInMathmlAndOmmlGates() throws Exception {
        JsonNode codePoints = new ObjectMapper().readTree(VECTORS.toFile()).get("code_points");
        assertTrue(codePoints.size() > 20);
        for (JsonNode vector : codePoints) {
            int codePoint = Integer.parseInt(vector.get("cp").asText().substring(2), 16);
            boolean visible = vector.get("visible").asBoolean();
            String label = vector.get("cp").asText() + " " + vector.get("note").asText();
            assertEquals(visible, MathmlContent.isVisibleCodePoint(codePoint), label);
            String character = "&#x" + Integer.toHexString(codePoint) + ";";
            assertEquals(visible, MathmlContent.hasFormula(
                    "<math xmlns=\"" + MATHML_NS + "\"><mi>" + character + "</mi></math>"), label);
            assertEquals(visible, MathmlContent.hasOmmlRunContent(
                    "<m:oMath xmlns:m=\"" + OMML_NS + "\"><m:r><m:t>" + character + "</m:t></m:r></m:oMath>"), label);
        }
    }

    @Test
    void mathmlDocumentsMatchSharedVectors() throws Exception {
        JsonNode documents = new ObjectMapper().readTree(VECTORS.toFile()).get("mathml");
        assertTrue(documents.size() > 10);
        for (JsonNode vector : documents) {
            String xml = vector.get("xml").asText();
            assertEquals(vector.get("usable").asBoolean(), MathmlContent.hasFormula(xml),
                    xml + " " + vector.get("note").asText());
        }
    }

    @Test
    void rejectsMissingScriptBasesEvenWhenOtherRunsContainVisibleText() {
        for (String script : new String[]{"sSup", "sSub", "sSubSup", "sPre"}) {
            String xml = "<m:oMath xmlns:m=\"" + OMML_NS + "\"><m:" + script
                    + "><m:e><m:argPr/></m:e><m:sub><m:r><m:t>94</m:t></m:r></m:sub>"
                    + "<m:sup><m:r><m:t>238</m:t></m:r></m:sup></m:" + script
                    + "><m:r><m:t>Pu</m:t></m:r></m:oMath>";
            assertEquals(false, MathmlContent.hasOmmlRunContent(xml), script);
        }
    }

    @Test
    void rejectsScriptBasesWithEmptyOrInvisibleRunsThroughWrappers() {
        for (String script : new String[]{"sSup", "sSub", "sSubSup", "sPre"}) {
            for (String token : new String[]{"", " ", "&#x2062;", "&#xFE0F;", "&#xEF0A;"}) {
                String base = "<m:e><m:box><m:e><m:r><m:t>" + token + "</m:t></m:r></m:e></m:box></m:e>";
                String sub = "<m:sub><m:r><m:t>6</m:t></m:r></m:sub>";
                String sup = "<m:sup><m:r><m:t>14</m:t></m:r></m:sup>";
                String arguments = switch (script) {
                    case "sSup" -> base + sup;
                    case "sSub" -> base + sub;
                    case "sPre" -> sub + sup + base;
                    default -> base + sub + sup;
                };
                String xml = "<m:oMath xmlns:m=\"" + OMML_NS + "\"><m:" + script + ">" + arguments + "</m:" + script
                        + "><m:r><m:t>C</m:t></m:r></m:oMath>";
                assertEquals("missing_script_base", MathmlContent.ommlRejectionReason(xml), script + ": " + token);
            }
        }
    }

    @Test
    void acceptsVisibleScriptBasesInsideBoxesAndStructuralBasesWithoutText() {
        for (String base : new String[]{
                "<m:box><m:boxPr><m:noBreak/></m:boxPr><m:e><m:r><m:t>x&#xFE0F;</m:t></m:r></m:e></m:box>",
                "<m:d><m:dPr><m:begChr m:val=\"(\"/><m:endChr m:val=\")\"/></m:dPr><m:e/></m:d>",
                "<m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>2</m:t></m:r></m:den></m:f>"}) {
            String xml = "<m:oMath xmlns:m=\"" + OMML_NS + "\"><m:sSup><m:e>" + base
                    + "</m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:oMath>";
            assertTrue(MathmlContent.hasOmmlRunContent(xml), base);
        }
    }

    @Test
    void acceptsCompletePrescriptsAndOptionalEmptyNaryLimits() {
        assertTrue(MathmlContent.hasOmmlRunContent("<m:oMath xmlns:m=\"" + OMML_NS
                + "\"><m:sPre><m:sub><m:r><m:t>6</m:t></m:r></m:sub>"
                + "<m:sup><m:r><m:t>14</m:t></m:r></m:sup>"
                + "<m:e><m:r><m:t>C</m:t></m:r></m:e></m:sPre></m:oMath>"));
        assertTrue(MathmlContent.hasOmmlRunContent("<m:oMath xmlns:m=\"" + OMML_NS
                + "\"><m:nary><m:sub/><m:sup/><m:e><m:r><m:t>x</m:t></m:r></m:e></m:nary></m:oMath>"));
    }
}
