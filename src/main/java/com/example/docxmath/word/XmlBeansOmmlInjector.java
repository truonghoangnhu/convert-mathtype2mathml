package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;

import org.xml.sax.InputSource;

public final class XmlBeansOmmlInjector implements OmmlInjector {
    private static final String MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";

    @Override
    public boolean inject(MathOccurrence occurrence, String ommlXml) {
        if (occurrence == null || ommlXml == null || ommlXml.isBlank() || !occurrence.blockCandidate()) {
            return false;
        }
        try {
            XWPFParagraph paragraph = occurrence.paragraph();
            Node paragraphNode = paragraph.getCTP().getDomNode();
            Document ownerDocument = paragraphNode.getOwnerDocument();
            Node importedMath = ownerDocument.importNode(parseOmmlRoot(ommlXml), true);
            Node mathPara = buildMathPara(ownerDocument, importedMath);

            for (int i = paragraphNode.getChildNodes().getLength() - 1; i >= 0; i--) {
                Node child = paragraphNode.getChildNodes().item(i);
                String localName = child.getLocalName();
                if ("pPr".equals(localName) || "bookmarkStart".equals(localName) || "bookmarkEnd".equals(localName)) {
                    continue;
                }
                paragraphNode.removeChild(child);
            }
            paragraphNode.appendChild(mathPara);
            return true;
        } catch (Exception ex) {
            return false;
        }
    }

    private static Node parseOmmlRoot(String ommlXml) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        Document document = factory.newDocumentBuilder().parse(new InputSource(new StringReader(ommlXml)));
        return document.getDocumentElement();
    }

    private static Node buildMathPara(Document ownerDocument, Node importedMath) {
        String localName = importedMath.getLocalName();
        if ("oMathPara".equals(localName)) {
            return importedMath;
        }

        Node mathPara = ownerDocument.createElementNS(MATH_NS, "m:oMathPara");
        if ("oMath".equals(localName)) {
            mathPara.appendChild(importedMath);
            return mathPara;
        }

        Node math = ownerDocument.createElementNS(MATH_NS, "m:oMath");
        NodeList children = importedMath.getChildNodes();
        while (children.getLength() > 0) {
            math.appendChild(children.item(0));
        }
        mathPara.appendChild(math);
        return mathPara;
    }
}
