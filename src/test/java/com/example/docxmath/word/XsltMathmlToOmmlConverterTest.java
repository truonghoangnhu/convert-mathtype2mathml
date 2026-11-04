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

    @Test
    void arrowWithoutLabelsAndNonArrowBasesKeepTheGenericRule() throws Exception {
        assertEquals(0, all(convert(MML + "<mover><mo>\u21CC</mo><mrow/></mover></math>"), "groupChr").getLength());
        assertEquals(0, all(convert(MML + "<mover><mo>=</mo><mi>x</mi></mover></math>"), "groupChr").getLength());
        assertEquals(0, all(convert(MML + "<mover><mi>x</mi><mo>\u2192</mo></mover></math>"), "groupChr").getLength());
    }
}
