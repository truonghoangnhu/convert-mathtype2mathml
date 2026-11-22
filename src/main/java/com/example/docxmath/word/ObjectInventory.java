package com.example.docxmath.word;

import org.apache.poi.openxml4j.exceptions.InvalidFormatException;
import org.apache.poi.openxml4j.opc.PackagePart;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.xml.sax.helpers.DefaultHandler;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.InputStream;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Every embedded {@code w:object} in the package, against the ones the walker handed to the patcher.
 *
 * <p>The walker covers body paragraphs and table cells. Objects in content controls ({@code w:sdt}),
 * text boxes, alternate content, other containers, or other parts (headers, footers, notes,
 * comments) are not scanned, so they are never patched and stay unchanged. They are counted here
 * by container so that discovered = scanned + unscanned reconciles instead of dropping them
 * silently. Being discovered does not make an object patchable.
 */
public record ObjectInventory(int discovered, int scanned, Map<String, Integer> unscannedByContainer) {
    private static final String WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
    private static final String MARKUP_COMPATIBILITY_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006";
    private static final String WORDPROCESSING_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.";

    public ObjectInventory {
        unscannedByContainer = Collections.unmodifiableMap(new TreeMap<>(unscannedByContainer));
    }

    public int unscanned() {
        return unscannedByContainer.values().stream().mapToInt(Integer::intValue).sum();
    }

    /** Container counts as "sdt:2,textbox:1"; empty when every object was scanned. */
    public String unscannedContainersToken() {
        StringBuilder token = new StringBuilder();
        unscannedByContainer.forEach((container, count) ->
                token.append(token.isEmpty() ? "" : ",").append(container).append(':').append(count));
        return token.toString();
    }

    static ObjectInventory of(XWPFDocument document, List<MathOccurrence> occurrences) {
        Set<Node> handed = Collections.newSetFromMap(new IdentityHashMap<>());
        for (MathOccurrence occurrence : occurrences) {
            if (occurrence.sourceType() != MathOccurrence.SourceType.NATIVE_OMML && occurrence.sourceNode() != null) {
                handed.add(occurrence.sourceNode());
            }
        }
        Map<String, Integer> unscanned = new TreeMap<>();
        int discovered = 0;
        int scanned = 0;
        for (Element object : PoiMathSourceDetector.findDescendants(document.getDocument().getDomNode(), "object")) {
            if (!WORD_NS.equals(object.getNamespaceURI())) continue;
            discovered++;
            if (handed.contains(object)) {
                scanned++;
            } else {
                unscanned.merge(container(object), 1, Integer::sum);
            }
        }
        List<PackagePart> parts;
        try {
            parts = document.getPackage().getParts();
        } catch (InvalidFormatException ex) {
            unscanned.merge("package:unreadable", 0, Integer::sum);
            parts = List.of();
        }
        for (PackagePart part : parts) {
            String type = part.getContentType();
            if (part == document.getPackagePart() || !type.startsWith(WORDPROCESSING_TYPE) || !type.endsWith("+xml")) {
                continue;
            }
            String kind = "part:" + type.substring(WORDPROCESSING_TYPE.length(), type.length() - "+xml".length());
            int count = countObjects(part);
            if (count < 0) {
                // Not countable: say so rather than report zero objects for it.
                unscanned.merge(kind + ":unreadable", 0, Integer::sum);
            } else if (count > 0) {
                discovered += count;
                unscanned.merge(kind, count, Integer::sum);
            }
        }
        return new ObjectInventory(discovered, scanned, unscanned);
    }

    // The nearest container the walker does not enter, or the element that holds the object's run.
    private static String container(Element object) {
        Node holder = null;
        for (Node node = object.getParentNode(); node != null; node = node.getParentNode()) {
            String name = node.getLocalName();
            if (MARKUP_COMPATIBILITY_NS.equals(node.getNamespaceURI()) && "AlternateContent".equals(name)) {
                return "alternate_content";
            }
            if (!WORD_NS.equals(node.getNamespaceURI())) continue;
            switch (name) {
                case "sdt": return "sdt";
                case "txbxContent": return "textbox";
                case "ins", "del", "moveFrom", "moveTo": return "tracked_change";
                case "customXml": return "custom_xml";
                case "smartTag": return "smart_tag";
                case "fldSimple": return "field";
                case "body": return "other:" + (holder == null ? "unknown" : holder.getLocalName());
                default: if ("r".equals(name) && holder == null) holder = node.getParentNode();
            }
        }
        return "other:detached";
    }

    private static int countObjects(PackagePart part) {
        try (InputStream in = part.getInputStream()) {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            var builder = factory.newDocumentBuilder();
            builder.setErrorHandler(new DefaultHandler());
            return builder.parse(in).getElementsByTagNameNS(WORD_NS, "object").getLength();
        } catch (Exception ex) {
            return -1;
        }
    }
}
