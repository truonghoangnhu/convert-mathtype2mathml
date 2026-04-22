package com.example.docxmath.word;

import org.apache.poi.openxml4j.opc.PackagePart;
import org.apache.poi.openxml4j.opc.PackageRelationship;
import org.apache.poi.openxml4j.exceptions.OpenXML4JException;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

public final class PoiMathSourceDetector implements MathSourceDetector {
    @Override
    public List<MathOccurrence> detect(XWPFDocument document, XWPFParagraph paragraph) {
        List<MathOccurrence> results = new ArrayList<>();
        Node paragraphNode = paragraph.getCTP().getDomNode();
        if (containsMathNode(paragraphNode)) {
            results.add(new MathOccurrence(
                    MathOccurrence.SourceType.NATIVE_OMML,
                    document,
                    paragraph,
                    paragraphNode,
                    null,
                    null,
                    null,
                    null,
                    false
            ));
            return results;
        }
        for (XWPFRun run : paragraph.getRuns()) {
            Node runNode = run.getCTR().getDomNode();
            Element objectElement = findFirstDescendant(runNode, "object");
            if (objectElement == null) {
                continue;
            }

            Element oleObject = findFirstDescendant(objectElement, "OLEObject");
            Element imageData = findFirstDescendant(objectElement, "imagedata");

            String oleRelId = attrByLocalName(oleObject, "id");
            String previewRelId = attrByLocalName(imageData, "id");
            String olePartName = resolveRelatedPartName(document, oleRelId);
            String previewPartName = resolveRelatedPartName(document, previewRelId);
            String oleExt = extensionOf(olePartName);
            String previewExt = extensionOf(previewPartName);

            MathOccurrence.SourceType sourceType = MathOccurrence.SourceType.UNKNOWN;
            if (".bin".equals(oleExt)) {
                sourceType = MathOccurrence.SourceType.OLE_BIN;
            } else if (".wmf".equals(previewExt) || ".emf".equals(previewExt)) {
                sourceType = MathOccurrence.SourceType.WMF_PREVIEW;
            }

            results.add(new MathOccurrence(
                    sourceType,
                    document,
                    paragraph,
                    objectElement,
                    oleRelId,
                    previewRelId,
                    olePartName,
                    previewPartName,
                    isBlockEquationCandidate(paragraph)
            ));
        }
        return results;
    }

    static boolean isBlockEquationCandidate(XWPFParagraph paragraph) {
        String text = Objects.toString(paragraph.getText(), "");
        String compactText = text.replaceAll("\\s+", "").trim();
        int objectCount = 0;
        for (XWPFRun run : paragraph.getRuns()) {
            if (findFirstDescendant(run.getCTR().getDomNode(), "object") != null) {
                objectCount++;
            }
        }
        if (objectCount != 1) {
            return false;
        }
        if (compactText.isEmpty()) {
            return true;
        }
        return compactText.length() <= 12;
    }

    private static boolean containsMathNode(Node node) {
        return findFirstDescendant(node, "oMath") != null || findFirstDescendant(node, "oMathPara") != null;
    }

    private static String resolveRelatedPartName(XWPFDocument document, String relId) {
        if (relId == null || relId.isBlank()) {
            return null;
        }
        try {
            PackageRelationship relationship = document.getPackagePart().getRelationship(relId);
            if (relationship == null) {
                return null;
            }
            PackagePart part = document.getPackagePart().getRelatedPart(relationship);
            return part == null ? null : part.getPartName().getName();
        } catch (OpenXML4JException ex) {
            return null;
        }
    }

    private static String extensionOf(String partName) {
        String normalized = Objects.toString(partName, "").toLowerCase(Locale.ROOT);
        int dot = normalized.lastIndexOf('.');
        return dot >= 0 ? normalized.substring(dot) : "";
    }

    static Element findFirstDescendant(Node node, String localName) {
        if (node == null) {
            return null;
        }
        if (node instanceof Element element && localName.equals(element.getLocalName())) {
            return element;
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Element found = findFirstDescendant(children.item(i), localName);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    static String attrByLocalName(Element element, String localName) {
        if (element == null || localName == null) {
            return null;
        }
        for (int i = 0; i < element.getAttributes().getLength(); i++) {
            Node attr = element.getAttributes().item(i);
            if (localName.equals(attr.getLocalName())) {
                return attr.getNodeValue();
            }
        }
        return null;
    }
}
