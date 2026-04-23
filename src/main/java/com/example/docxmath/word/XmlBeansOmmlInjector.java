package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.StringReader;
import java.io.StringWriter;

import org.xml.sax.InputSource;

public final class XmlBeansOmmlInjector implements OmmlInjector {
    private static final String MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";

    @Override
    public boolean inject(MathOccurrence occurrence, String ommlXml) {
        if (occurrence == null || ommlXml == null || ommlXml.isBlank()) {
            return false;
        }
        try {
            return occurrence.blockCandidate()
                    ? injectBlock(occurrence, ommlXml)
                    : injectInline(occurrence, ommlXml);
        } catch (Exception ex) {
            return false;
        }
    }

    @Override
    public boolean inject(MultiObjectPatchPlan patchPlan) {
        if (patchPlan == null || !patchPlan.safe() || patchPlan.objectSegments().isEmpty()) {
            return false;
        }
        Node paragraphNode = null;
        String snapshotXml = null;
        try {
            XWPFParagraph paragraph = patchPlan.paragraph();
            paragraphNode = paragraph.getCTP().getDomNode();
            Document ownerDocument = paragraphNode.getOwnerDocument();
            snapshotXml = serializeNode(paragraphNode);
            for (ParagraphSegment segment : patchPlan.objectSegments()) {
                Node targetRun = segment.paragraphChild();
                if (targetRun == null || targetRun.getParentNode() != paragraphNode) {
                    restoreParagraph(paragraphNode, snapshotXml);
                    return false;
                }
                Node importedMath = ownerDocument.importNode(parseOmmlRoot(segment.ommlXml()), true);
                Node inlineMath = buildInlineMath(ownerDocument, importedMath);
                Node nextSibling = targetRun.getNextSibling();
                paragraphNode.insertBefore(inlineMath, nextSibling);
                paragraphNode.removeChild(targetRun);
            }
            return true;
        } catch (Exception ex) {
            if (paragraphNode != null && snapshotXml != null) {
                try {
                    restoreParagraph(paragraphNode, snapshotXml);
                } catch (Exception ignored) {
                    // Keep the original failure path if rollback itself fails.
                }
            }
            return false;
        }
    }

    private boolean injectBlock(MathOccurrence occurrence, String ommlXml) throws Exception {
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
    }

    private boolean injectInline(MathOccurrence occurrence, String ommlXml) throws Exception {
        XWPFParagraph paragraph = occurrence.paragraph();
        if (occurrence.runIndex() < 0 || occurrence.runIndex() >= paragraph.getRuns().size()) {
            return false;
        }

        Node paragraphNode = paragraph.getCTP().getDomNode();
        Document ownerDocument = paragraphNode.getOwnerDocument();
        String snapshotXml = serializeNode(paragraphNode);
        Node targetRun = paragraph.getRuns().get(occurrence.runIndex()).getCTR().getDomNode();
        Node importedMath = ownerDocument.importNode(parseOmmlRoot(ommlXml), true);
        Node inlineMath = buildInlineMath(ownerDocument, importedMath);
        Node nextSibling = targetRun.getNextSibling();
        try {
            paragraphNode.insertBefore(inlineMath, nextSibling);
            paragraphNode.removeChild(targetRun);
            return true;
        } catch (Exception ex) {
            restoreParagraph(paragraphNode, snapshotXml);
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

    private static Node buildInlineMath(Document ownerDocument, Node importedMath) {
        String localName = importedMath.getLocalName();
        if ("oMath".equals(localName)) {
            return importedMath;
        }
        if ("oMathPara".equals(localName)) {
            NodeList children = importedMath.getChildNodes();
            for (int i = 0; i < children.getLength(); i++) {
                Node child = children.item(i);
                if ("oMath".equals(child.getLocalName())) {
                    return child;
                }
            }
        }

        Node math = ownerDocument.createElementNS(MATH_NS, "m:oMath");
        NodeList children = importedMath.getChildNodes();
        while (children.getLength() > 0) {
            math.appendChild(children.item(0));
        }
        return math;
    }

    private static String serializeNode(Node node) throws Exception {
        TransformerFactory transformerFactory = TransformerFactory.newInstance();
        transformerFactory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        Transformer transformer = transformerFactory.newTransformer();
        transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
        transformer.setOutputProperty(OutputKeys.INDENT, "no");
        StringWriter out = new StringWriter();
        transformer.transform(new DOMSource(node), new StreamResult(out));
        return out.toString();
    }

    private static void restoreParagraph(Node paragraphNode, String snapshotXml) throws Exception {
        Document ownerDocument = paragraphNode.getOwnerDocument();
        Node restored = ownerDocument.importNode(parseOmmlRoot(snapshotXml), true);
        Node parent = paragraphNode.getParentNode();
        parent.replaceChild(restored, paragraphNode);
    }
}
