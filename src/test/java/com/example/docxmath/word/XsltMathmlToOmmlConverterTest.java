package com.example.docxmath.word;

import org.junit.jupiter.api.Test;
import org.w3c.dom.Element;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class XsltMathmlToOmmlConverterTest {
    private static final String OMML = "http://schemas.openxmlformats.org/officeDocument/2006/math";

    private static Element convert(String mathml) throws Exception {
        String omml = new XsltMathmlToOmmlConverter().convert(mathml);
        var factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        return factory.newDocumentBuilder().parse(new InputSource(new StringReader(omml))).getDocumentElement();
    }

    private static String text(Element omml) {
        var texts = omml.getElementsByTagNameNS(OMML, "t");
        var out = new StringBuilder();
        for (int i = 0; i < texts.getLength(); i++) out.append(texts.item(i).getTextContent());
        return out.toString();
    }

    @Test
    void keepsExplicitSpacesAndDropsMathTypeAutomaticThinSpace() throws Exception {
        Element omml = convert("<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>a</mi><mspace width=\"0.08em\"/>"
                + "<mi>b</mi><mspace width=\"0.16em\"/><mi>c</mi><mspace width=\"0.33em\"/><mi>d</mi>"
                + "<mspace width=\"1em\"/><mi>e</mi></math>");
        assertEquals("ab c d e", text(omml));
    }

    @Test
    void spaceBetweenNumberAndUnitSurvives() throws Exception {
        Element omml = convert("<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>I</mi><mo>=</mo><mn>10,0</mn>"
                + "<mspace width=\"0.33em\"/><mi mathvariant=\"normal\">A</mi></math>");
        assertTrue(text(omml).contains("10,0 A"), text(omml));
    }

    @Test
    void spaceRunIsNormalTextAndNeverCountsAsFormulaContent() throws Exception {
        Element omml = convert("<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi><mspace width=\"1em\"/></math>");
        var spaceRuns = omml.getElementsByTagNameNS(OMML, "nor");
        assertEquals(1, spaceRuns.getLength());
        // A formula made only of spaces is still rejected by the content gate.
        assertEquals(false, MathmlContentProbe.onlySpacesAccepted());
    }

    @Test
    void unknownOrMissingWidthAddsNothingAndDoesNotFail() throws Exception {
        Element omml = convert("<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi><mspace/>"
                + "<mspace width=\"auto\"/><mspace width=\"thinmathspace\"/><mi>y</mi></math>");
        assertEquals("xy", text(omml));
    }

    private static final class MathmlContentProbe {
        static boolean onlySpacesAccepted() {
            return com.example.docxmath.MathmlContent.hasOmmlRunContent(
                    "<m:oMath xmlns:m=\"" + OMML + "\"><m:r><m:t xml:space=\"preserve\"> </m:t></m:r></m:oMath>");
        }
    }

    private static final String MML = "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">";

    private static org.w3c.dom.NodeList all(Element omml, String name) {
        return omml.getElementsByTagNameNS(OMML, name);
    }

    @Test
    void prescriptArgumentsFollowSchemaOrderAndKeepTheirBase() throws Exception {
        // CT_SPre is sub, sup, e (unlike sSubSup, whose base comes first).
        // Writer loses C when the old converter emits e, sub, sup for real Lý #8.
        for (String post : new String[]{"", "<mn>2</mn><mn>3</mn>",
                "<mn>2</mn><none/>", "<none/><mn>3</mn>"}) {
            Element omml = convert(MML + "<mmultiscripts><mi>C</mi>" + post
                    + "<mprescripts/><mn>6</mn><mn>14</mn></mmultiscripts></math>");
            Element pre = (Element) all(omml, "sPre").item(0);
            var names = new java.util.ArrayList<String>();
            for (var c = pre.getFirstChild(); c != null; c = c.getNextSibling()) {
                if (c instanceof Element) names.add(c.getLocalName());
            }
            assertEquals(java.util.List.of("sub", "sup", "e"), names);
            assertEquals("6", pre.getElementsByTagNameNS(OMML, "sub").item(0).getTextContent());
            assertEquals("14", pre.getElementsByTagNameNS(OMML, "sup").item(0).getTextContent());
            assertTrue(pre.getLastChild().getTextContent().contains("C"), "base C must survive");
        }
    }

    @Test
    void separatorFreeFencedExpressionHasOneEditableArgument() throws Exception {
        // Real Toan_TQB_HN_Lx #54: separate delimiter arguments broke Writer's import
        // of the nested f(x), adding the literal text "left" after save/reopen.
        Element omml = convert(MML + "<mfenced open=\"(\" close=\")\" separators=\"\">"
                + "<mn>2</mn><mi>f</mi><mfenced separators=\"\"><mi>x</mi></mfenced>"
                + "<mo>−</mo><mn>1</mn></mfenced></math>");
        var outer = all(omml, "d").item(0);
        int arguments = 0;
        for (var c = outer.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (OMML.equals(c.getNamespaceURI()) && "e".equals(c.getLocalName())) arguments++;
        }
        assertEquals(1, arguments);
        assertEquals("2fx−1", text(omml));
        assertEquals(2, all(omml, "d").getLength(), "nested f(x) delimiter remains editable");
    }

    @Test
    void visibleAndDefaultFencedSeparatorsKeepSeparateArguments() throws Exception {
        for (String separators : new String[]{"", " separators=\";\""}) {
            Element omml = convert(MML + "<mfenced" + separators + "><mi>x</mi><mi>y</mi></mfenced></math>");
            assertEquals(2, all(omml, "e").getLength());
        }
    }

    @Test
    void chemistryArrowWithEmptyOverLabelHasNoPlaceholderArgument() throws Exception {
        // Real Hoa_Ha_Noi_L1 #66/#67: mover(arrow, empty mrow) is an ordinary arrow.
        Element omml = convert(MML + "<mi>Li</mi><mover><mo>→</mo><mrow/></mover><mi>C</mi></math>");
        assertEquals("Li→C", text(omml));
        assertEquals(0, all(omml, "limUpp").getLength());
        assertEquals(0, all(omml, "groupChr").getLength());
    }

    @Test
    void arrowWithBothLabelsIsAStretchingGroupCharWithLowerLabelBeneath() throws Exception {
        Element omml = convert(MML + "<munderover><mo>\u2192</mo><mrow><mi>b</mi></mrow><mrow><mi>a</mi></mrow></munderover></math>");
        Element limLow = (Element) all(omml, "limLow").item(0);
        Element group = (Element) limLow.getElementsByTagNameNS(OMML, "groupChr").item(0);
        assertEquals("\u2192", ((Element) group.getElementsByTagNameNS(OMML, "chr").item(0)).getAttributeNS(OMML, "val"));
        assertEquals("a", ((Element) group.getElementsByTagNameNS(OMML, "e").item(0)).getTextContent());
        assertEquals("b", ((Element) limLow.getElementsByTagNameNS(OMML, "lim").item(0)).getTextContent());
        assertEquals(0, all(omml, "limUpp").getLength());
    }

    @Test
    void twoLabelArrowGroupCharIsWrappedInInvisibleDelimiterForWriter() throws Exception {
        for (String body : new String[] {
                "<munderover><mo>\u2192</mo><mi>b</mi><mi>a</mi></munderover>",
                "<munderover><mo>\u2192</mo><mrow><mi>b</mi><mi>c</mi></mrow><mi>a</mi></munderover>"}) {
            Element omml = convert(MML + body + "</math>");
            Element group = (Element) all(omml, "groupChr").item(0);
            Element delimiter = (Element) group.getParentNode().getParentNode();
            assertEquals("d", delimiter.getLocalName());
            Element props = (Element) delimiter.getElementsByTagNameNS(OMML, "dPr").item(0);
            assertEquals("", ((Element) props.getElementsByTagNameNS(OMML, "begChr").item(0)).getAttributeNS(OMML, "val"));
            assertEquals("", ((Element) props.getElementsByTagNameNS(OMML, "endChr").item(0)).getAttributeNS(OMML, "val"));
        }
    }

    @Test
    void arrowIsGroupedOverTheWiderLabelSoItSpansBoth() throws Exception {
        Element omml = convert(MML + "<munderover><mo>\u2192</mo><mrow><mi>b</mi><mi>c</mi><mi>d</mi></mrow><mrow><mi>a</mi></mrow></munderover></math>");
        Element limUpp = (Element) all(omml, "limUpp").item(0);
        Element group = (Element) limUpp.getElementsByTagNameNS(OMML, "groupChr").item(0);
        assertEquals("bcd", ((Element) group.getElementsByTagNameNS(OMML, "e").item(0)).getTextContent());
        assertEquals("a", ((Element) limUpp.getElementsByTagNameNS(OMML, "lim").item(0)).getTextContent());
        assertEquals(0, all(omml, "limLow").getLength());
    }

    @Test
    void arrowWithOnlyOneLabelStillStretchesOverOrUnderIt() throws Exception {
        Element over = convert(MML + "<mover><mo>\u2192</mo><mi>t</mi></mover></math>");
        Element g = (Element) all(over, "groupChr").item(0);
        assertEquals("bot", ((Element) g.getElementsByTagNameNS(OMML, "vertJc").item(0)).getAttributeNS(OMML, "val"));
        assertEquals(0, g.getElementsByTagNameNS(OMML, "pos").getLength());
        assertEquals(0, all(over, "limUpp").getLength());
        Element under = convert(MML + "<munder><mo>\u2192</mo><mi>t</mi></munder></math>");
        Element u = (Element) all(under, "groupChr").item(0);
        assertEquals("top", ((Element) u.getElementsByTagNameNS(OMML, "pos").item(0)).getAttributeNS(OMML, "val"));
        assertEquals("top", ((Element) u.getElementsByTagNameNS(OMML, "vertJc").item(0)).getAttributeNS(OMML, "val"));
    }

    private static Element runContaining(Element omml, String text) {
        var runs = omml.getElementsByTagNameNS(OMML, "r");
        for (int i = 0; i < runs.getLength(); i++) {
            Element run = (Element) runs.item(i);
            var t = run.getElementsByTagNameNS(OMML, "t");
            if (t.getLength() > 0 && t.item(0).getTextContent().equals(text)) return run;
        }
        throw new AssertionError("no run with text " + text);
    }

    @Test
    void letterlikeSymbolTextIsAMathRunSoWordKeepsItOnSave() throws Exception {
        // Real Toan_TQB_HN_Lx #78 (a ∈ ℝ) and TN-THPT-2026 #17/#20 (ℓ) are mtext. Word 16.114 saves
        // ℝ/ℓ/ℤ/ℕ inside an m:nor run as plain R/l/Z/N, but keeps them (as m:scr) in a math run.
        for (String ch : new String[] {"ℝ", "ℓ", "ℤ", "ℕ"}) {
            Element omml = convert(MML + "<mi>a</mi><mo>∈</mo><mtext>" + ch + "</mtext></math>");
            Element run = runContaining(omml, ch);
            assertEquals(0, run.getElementsByTagNameNS(OMML, "nor").getLength(), ch);
            Element sty = (Element) run.getElementsByTagNameNS(OMML, "sty").item(0);
            assertEquals("p", sty == null ? null : sty.getAttributeNS(OMML, "val"), ch);
        }
    }

    @Test
    void adjacentNormalTextAndLetterlikeTokensKeepSeparateRunKinds() throws Exception {
        for (String ch : new String[]{"ℝ", "ℤ", "ℕ", "ℓ"}) {
            Element omml = convert(MML + "<mtext>x</mtext><mtext>" + ch
                    + "</mtext><mtext>kg</mtext></math>");
            assertEquals("x" + ch + "kg", text(omml));
            assertEquals(3, all(omml, "r").getLength());
            assertEquals(1, all(runContaining(omml, "x"), "nor").getLength());
            assertEquals(0, all(runContaining(omml, ch), "nor").getLength());
            assertEquals(1, all(runContaining(omml, "kg"), "nor").getLength());
        }
    }

    @Test
    void unverifiedSymbolsAreNotSilentlyPromotedToUprightMath() throws Exception {
        for (String ch : new String[]{"℃", "№", "™", "℅", "𝑥", "ℂ"}) {
            Element omml = convert(MML + "<mtext>" + ch + "</mtext></math>");
            assertEquals(ch, text(omml));
            assertEquals(1, all(runContaining(omml, ch), "nor").getLength(), ch);
        }
    }

    @Test
    void ordinaryTextAndMixedTextKeepNormalTextRuns() throws Exception {
        Element unit = convert(MML + "<mn>3</mn><mtext>km</mtext></math>");
        assertEquals(1, runContaining(unit, "km").getElementsByTagNameNS(OMML, "nor").getLength());
        Element mixed = convert(MML + "<mtext>xℝ</mtext></math>");
        assertEquals(1, runContaining(mixed, "xℝ").getElementsByTagNameNS(OMML, "nor").getLength());
    }

    @Test
    void arrowWithoutLabelsAndNonArrowBasesKeepTheGenericRule() throws Exception {
        assertEquals(0, all(convert(MML + "<mover><mo>\u21CC</mo><mrow/></mover></math>"), "groupChr").getLength());
        assertEquals(0, all(convert(MML + "<mover><mo>=</mo><mi>x</mi></mover></math>"), "groupChr").getLength());
        assertEquals(0, all(convert(MML + "<mover><mi>x</mi><mo>\u2192</mo></mover></math>"), "groupChr").getLength());
    }
}
