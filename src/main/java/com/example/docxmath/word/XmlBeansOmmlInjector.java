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
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import org.xml.sax.InputSource;

public final class XmlBeansOmmlInjector implements OmmlInjector {
    private static final String MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";
    private static final String WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
    // Source run properties that Word applies to an equation run. Bold/italic/position are
    // left out: math style comes from the MathML, and w:position only aligned the OLE picture.
    // Listed in CT_RPr schema order, which the merge below keeps.
    private static final List<String> CARRIED_RUN_PROPERTIES = List.of("color", "sz", "szCs", "highlight", "u");
    private static final List<String> RUN_PROPERTY_ORDER = List.of(
            "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
            "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
            "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
            "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath");

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

            List<ParagraphSegment> objectSegments = new ArrayList<>(patchPlan.objectSegments());
            objectSegments.sort(Comparator.comparing(ParagraphSegment::paragraphChild, XmlBeansOmmlInjector::compareDocumentOrderDesc));

            for (ParagraphSegment segment : objectSegments) {
                Node targetObject = resolveTargetObjectNode(segment.paragraphChild());
                if (targetObject == null) {
                    restoreParagraph(paragraphNode, snapshotXml);
                    return false;
                }
                Node targetParent = targetObject.getParentNode();
                if (targetParent == null || !"r".equals(targetParent.getLocalName()) || targetParent.getParentNode() != paragraphNode) {
                    restoreParagraph(paragraphNode, snapshotXml);
                    return false;
                }
                Node importedMath = ownerDocument.importNode(parseOmmlRoot(segment.ommlXml()), true);
                Node inlineMath = buildInlineMath(ownerDocument, importedMath);
                replaceObjectRun(paragraphNode, targetParent, targetObject, inlineMath);
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
        Node objectNode = findFirstDescendantByLocalName(paragraphNode, "object");
        if (objectNode != null) {
            carryRunFormatting(objectNode.getParentNode(), mathPara);
        }

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
        Node paragraphNode = paragraph.getCTP().getDomNode();
        Document ownerDocument = paragraphNode.getOwnerDocument();
        String snapshotXml = serializeNode(paragraphNode);

        Node targetObject = resolveTargetObjectNode(occurrence.sourceNode());
        if (targetObject == null) {
            if (occurrence.runIndex() < 0 || occurrence.runIndex() >= paragraph.getRuns().size()) {
                return false;
            }
            targetObject = findFirstDescendantByLocalName(
                    paragraph.getRuns().get(occurrence.runIndex()).getCTR().getDomNode(),
                    "object"
            );
            if (targetObject == null) {
                return false;
            }
        }

        Node targetParent = targetObject.getParentNode();
        if (targetParent == null || !"r".equals(targetParent.getLocalName()) || targetParent.getParentNode() != paragraphNode) {
            return false;
        }

        Node importedMath = ownerDocument.importNode(parseOmmlRoot(ommlXml), true);
        Node inlineMath = buildInlineMath(ownerDocument, importedMath);
        try {
            replaceObjectRun(paragraphNode, targetParent, targetObject, inlineMath);
            return true;
        } catch (Exception ex) {
            restoreParagraph(paragraphNode, snapshotXml);
            return false;
        }
    }

    // Inline oMath belongs to w:p, not w:r. Split a mixed object run at the
    // object so drawings, page-break markers, text and run properties survive.
    private static void replaceObjectRun(Node paragraph, Node run, Node object, Node math) {
        carryRunFormatting(run, math);
        Node before = run.cloneNode(false);
        Node after = run.cloneNode(false);
        List<Node> children = new ArrayList<>();
        for (Node child = run.getFirstChild(); child != null; child = child.getNextSibling()) children.add(child);
        boolean passedObject = false;
        boolean hasBefore = false;
        boolean hasAfter = false;
        for (Node child : children) {
            if ("rPr".equals(child.getLocalName())) {
                before.appendChild(child.cloneNode(true));
                after.appendChild(child.cloneNode(true));
            } else if (child == object) {
                passedObject = true;
            } else if (passedObject) {
                after.appendChild(child);
                hasAfter = true;
            } else {
                before.appendChild(child);
                hasBefore = true;
            }
        }
        if (hasBefore) paragraph.insertBefore(before, run);
        paragraph.insertBefore(math, run);
        if (hasAfter) paragraph.insertBefore(after, run);
        paragraph.removeChild(run);
    }

    // Equation runs do not inherit the size/colour of neighbouring runs, so the formatting of the
    // run that held the OLE object is copied onto every m:r, keeping anything the transform set.
    private static void carryRunFormatting(Node sourceRun, Node math) {
        if (sourceRun == null || math == null) {
            return;
        }
        List<Node> carried = new ArrayList<>();
        for (Node child = sourceRun.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (!"rPr".equals(child.getLocalName()) || !WORD_NS.equals(child.getNamespaceURI())) {
                continue;
            }
            for (Node prop = child.getFirstChild(); prop != null; prop = prop.getNextSibling()) {
                if (WORD_NS.equals(prop.getNamespaceURI()) && CARRIED_RUN_PROPERTIES.contains(prop.getLocalName())) {
                    carried.add(prop);
                }
            }
        }
        if (carried.isEmpty()) {
            return;
        }
        List<Node> mathRuns = new ArrayList<>();
        collectMathRuns(math, mathRuns);
        for (Node mathRun : mathRuns) {
            Node runProperties = ensureWordRunProperties(mathRun);
            for (Node prop : carried) {
                if (!hasChildNamed(runProperties, prop.getLocalName())) {
                    insertInSchemaOrder(runProperties, prop.cloneNode(true));
                }
            }
        }
    }

    private static void collectMathRuns(Node node, List<Node> out) {
        for (Node child = node.getFirstChild(); child != null; child = child.getNextSibling()) {
            if ("r".equals(child.getLocalName()) && MATH_NS.equals(child.getNamespaceURI())) {
                out.add(child);
            } else {
                collectMathRuns(child, out);
            }
        }
    }

    // CT_R order is m:rPr, then w:rPr, then content.
    private static Node ensureWordRunProperties(Node mathRun) {
        Node insertBefore = null;
        for (Node child = mathRun.getFirstChild(); child != null; child = child.getNextSibling()) {
            if ("rPr".equals(child.getLocalName()) && WORD_NS.equals(child.getNamespaceURI())) {
                return child;
            }
            if (insertBefore == null && !("rPr".equals(child.getLocalName()) && MATH_NS.equals(child.getNamespaceURI()))
                    && child.getNodeType() == Node.ELEMENT_NODE) {
                insertBefore = child;
            }
        }
        Node created = mathRun.getOwnerDocument().createElementNS(WORD_NS, "w:rPr");
        mathRun.insertBefore(created, insertBefore);
        return created;
    }

    private static boolean hasChildNamed(Node parent, String localName) {
        for (Node child = parent.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (localName.equals(child.getLocalName())) {
                return true;
            }
        }
        return false;
    }

    private static void insertInSchemaOrder(Node runProperties, Node property) {
        int rank = RUN_PROPERTY_ORDER.indexOf(property.getLocalName());
        for (Node child = runProperties.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child.getNodeType() == Node.ELEMENT_NODE && RUN_PROPERTY_ORDER.indexOf(child.getLocalName()) > rank) {
                runProperties.insertBefore(property, child);
                return;
            }
        }
        runProperties.appendChild(property);
    }

    private static Node resolveTargetObjectNode(Node candidate) {
        if (candidate == null) {
            return null;
        }
        if ("object".equals(candidate.getLocalName())) {
            return candidate;
        }
        return findFirstDescendantByLocalName(candidate, "object");
    }

    private static int compareDocumentOrderDesc(Node left, Node right) {
        if (left == null && right == null) {
            return 0;
        }
        if (left == null) {
            return 1;
        }
        if (right == null) {
            return -1;
        }
        short position = left.compareDocumentPosition(right);
        if ((position & Node.DOCUMENT_POSITION_PRECEDING) != 0) {
            return -1;
        }
        if ((position & Node.DOCUMENT_POSITION_FOLLOWING) != 0) {
            return 1;
        }
        return 0;
    }

    private static Node findFirstDescendantByLocalName(Node node, String localName) {
        if (node == null) {
            return null;
        }
        if (localName.equals(node.getLocalName())) {
            return node;
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node found = findFirstDescendantByLocalName(children.item(i), localName);
            if (found != null) {
                return found;
            }
        }
        return null;
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
