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
        boolean paragraphHasNativeOmml = containsMathNode(paragraphNode);
        int paragraphObjectCount = countObjects(paragraph);
        if (paragraphHasNativeOmml) {
            results.add(new MathOccurrence(
                    MathOccurrence.SourceType.NATIVE_OMML,
                    document,
                    paragraph,
                    paragraphNode,
                    -1,
                    null,
                    null,
                    null,
                    null,
                    false,
                    true,
                    paragraphObjectCount
            ));
        }
        List<XWPFRun> runs = paragraph.getRuns();
        for (int runIndex = 0; runIndex < runs.size(); runIndex++) {
            XWPFRun run = runs.get(runIndex);
            Node runNode = run.getCTR().getDomNode();
            List<Element> objectElements = findDescendants(runNode, "object");
            for (Element objectElement : objectElements) {
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
                        runIndex,
                        oleRelId,
                        previewRelId,
                        olePartName,
                        previewPartName,
                        isBlockEquationCandidate(paragraph, paragraphHasNativeOmml, paragraphObjectCount, runIndex),
                        paragraphHasNativeOmml,
                        paragraphObjectCount
                ));
            }
        }
        return results;
    }

    static boolean isBlockEquationCandidate(
            XWPFParagraph paragraph,
            boolean paragraphHasNativeOmml,
            int paragraphObjectCount,
            int objectRunIndex
    ) {
        if (paragraphHasNativeOmml) {
            return false;
        }
        if (paragraphObjectCount != 1) return false;
        // A short answer marker or unit is still document content. A block
        // replacement owns the whole paragraph, so only object-only runs qualify.
        Node paragraphNode = paragraph.getCTP().getDomNode();
        for (Node child = paragraphNode.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child.getNodeType() != Node.ELEMENT_NODE) continue;
            String name = child.getLocalName();
            if ("pPr".equals(name) || "bookmarkStart".equals(name) || "bookmarkEnd".equals(name)) continue;
            if (!"r".equals(name)) return false;
            for (Node runChild = child.getFirstChild(); runChild != null; runChild = runChild.getNextSibling()) {
                if (runChild.getNodeType() != Node.ELEMENT_NODE) continue;
                String runName = runChild.getLocalName();
                if (!"rPr".equals(runName) && !"object".equals(runName)) return false;
            }
        }
        return true;
    }

    private static int countObjects(XWPFParagraph paragraph) {
        int objectCount = 0;
        for (XWPFRun run : paragraph.getRuns()) {
            objectCount += findDescendants(run.getCTR().getDomNode(), "object").size();
        }
        return objectCount;
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

    static List<Element> findDescendants(Node node, String localName) {
        List<Element> results = new ArrayList<>();
        collectDescendants(node, localName, results);
        return results;
    }

    private static void collectDescendants(Node node, String localName, List<Element> results) {
        if (node == null) {
            return;
        }
        if (node instanceof Element element && localName.equals(element.getLocalName())) {
            results.add(element);
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            collectDescendants(children.item(i), localName, results);
        }
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
