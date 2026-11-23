package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.IntConsumer;

import org.xml.sax.InputSource;

public final class XmlBeansOmmlInjector implements OmmlInjector {
    private static final String MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";
    private static final String WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
    // Source run properties that Word applies to an equation run. Bold/italic/position are
    // left out: math style comes from the MathML, and w:position only aligned the OLE picture.
    // Listed in CT_RPr schema order, which the merge below keeps.
    private static final List<String> CARRIED_RUN_PROPERTIES = List.of("vanish", "color", "sz", "szCs", "highlight", "u");
    private static final List<String> RUN_PROPERTY_ORDER = List.of(
            "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
            "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
            "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
            "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath");

    private final IntConsumer afterReplacement;

    public XmlBeansOmmlInjector() {
        this(replaced -> { });
    }

    // Test seam: runs after each object replacement on the working copy of a paragraph.
    XmlBeansOmmlInjector(IntConsumer afterReplacement) {
        this.afterReplacement = afterReplacement;
    }

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
        try {
            Node paragraphNode = patchPlan.paragraph().getCTP().getDomNode();
            Document ownerDocument = paragraphNode.getOwnerDocument();
            List<ParagraphSegment> objectSegments = new ArrayList<>(patchPlan.objectSegments());
            objectSegments.sort(Comparator.comparing(ParagraphSegment::paragraphChild, XmlBeansOmmlInjector::compareDocumentOrderDesc));
            List<Node> targets = new ArrayList<>();
            for (ParagraphSegment segment : objectSegments) {
                Node targetObject = resolveTargetObjectNode(segment.paragraphChild());
                if (targetObject == null) {
                    return false;
                }
                targets.add(targetObject);
            }
            return editParagraph(patchPlan.paragraph(), targets, (working, workingTargets) -> {
                for (int i = 0; i < workingTargets.size(); i++) {
                    Node targetObject = workingTargets.get(i);
                    Node targetParent = targetObject.getParentNode();
                    if (!isRunOf(targetParent, working)) {
                        return false;
                    }
                    Node importedMath = ownerDocument.importNode(parseOmmlRoot(objectSegments.get(i).ommlXml()), true);
                    replaceObjectRun(working, targetParent, targetObject, buildInlineMath(ownerDocument, importedMath));
                    afterReplacement.accept(i + 1);
                }
                return true;
            });
        } catch (Exception ex) {
            return false;
        }
    }

    private boolean injectBlock(MathOccurrence occurrence, String ommlXml) throws Exception {
        Node paragraphNode = occurrence.paragraph().getCTP().getDomNode();
        Document ownerDocument = paragraphNode.getOwnerDocument();
        Node targetObject = resolveTargetObjectNode(occurrence.sourceNode());
        if (targetObject == null) {
            return false;
        }
        Node mathPara = buildMathPara(ownerDocument, ownerDocument.importNode(parseOmmlRoot(ommlXml), true));
        String justification = DisplayEquationPlacement.justification(occurrence.paragraph());
        if (justification == null) return false;
        ensureJustification(ownerDocument, mathPara, justification);
        return editParagraph(occurrence.paragraph(), List.of(targetObject), (working, workingTargets) -> {
            Node run = workingTargets.get(0).getParentNode();
            if (!isRunOf(run, working)) {
                return false;
            }
            carryRunFormatting(run, mathPara);
            // The equation takes the object's place. The other runs hold only run properties (see
            // PoiMathSourceDetector.isBlockEquationCandidate); bookmarks keep their side of it.
            working.insertBefore(mathPara, run);
            List<Node> children = new ArrayList<>();
            for (Node child = working.getFirstChild(); child != null; child = child.getNextSibling()) children.add(child);
            for (Node child : children) {
                String localName = child.getLocalName();
                if (child != mathPara && !"pPr".equals(localName)
                        && !"bookmarkStart".equals(localName) && !"bookmarkEnd".equals(localName)) {
                    working.removeChild(child);
                }
            }
            afterReplacement.accept(1);
            return true;
        });
    }

    private boolean injectInline(MathOccurrence occurrence, String ommlXml) throws Exception {
        XWPFParagraph paragraph = occurrence.paragraph();
        Node paragraphNode = paragraph.getCTP().getDomNode();
        Document ownerDocument = paragraphNode.getOwnerDocument();

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

        if (!isRunOf(targetObject.getParentNode(), paragraphNode)) {
            return false;
        }

        Node inlineMath = buildInlineMath(ownerDocument, ownerDocument.importNode(parseOmmlRoot(ommlXml), true));
        return editParagraph(paragraph, List.of(targetObject), (working, workingTargets) -> {
            Node object = workingTargets.get(0);
            replaceObjectRun(working, object.getParentNode(), object, inlineMath);
            afterReplacement.accept(1);
            return true;
        });
    }

    @FunctionalInterface
    private interface ParagraphEdit {
        boolean apply(Node workingParagraph, List<Node> workingTargets) throws Exception;
    }

    // Edits run on a deep copy of the paragraph, so any failure while editing leaves the live
    // paragraph, and every XWPF object bound to it, untouched. Edits only add, replace or remove
    // whole paragraph children, never change a kept child in place.
    //
    // On success only the difference reaches the live paragraph: kept children stay the same
    // nodes, so their XWPFRun objects stay live. Replaced runs leave XWPFParagraph's run lists
    // through removeRun, and new runs (the parts of a split object run) enter them through
    // insertNewRun at the same position, so getRuns()/getText() keep working. The XWPFRun of a
    // replaced object run is disconnected afterwards; nothing in the patcher reads it again.
    private static boolean editParagraph(XWPFParagraph paragraph, List<Node> targets, ParagraphEdit edit) throws Exception {
        Node paragraphNode = paragraph.getCTP().getDomNode();
        Node working = paragraphNode.cloneNode(true);
        // Only elements are matched: XMLBeans does not keep DOM text-node objects stable, and the
        // whitespace between paragraph children carries no content.
        Map<Node, Node> liveByCopy = new IdentityHashMap<>();
        for (Node live = firstElement(paragraphNode), copy = firstElement(working);
             live != null && copy != null; live = nextElement(live), copy = nextElement(copy)) {
            liveByCopy.put(copy, live);
        }
        List<Node> workingTargets = new ArrayList<>();
        for (Node target : targets) {
            Node mapped = counterpart(paragraphNode, working, target);
            if (mapped == null) {
                return false;
            }
            workingTargets.add(mapped);
        }
        if (!edit.apply(working, workingTargets)) {
            return false;
        }

        List<Node> result = new ArrayList<>();
        Set<Node> kept = Collections.newSetFromMap(new IdentityHashMap<>());
        for (Node copy = firstElement(working); copy != null; copy = nextElement(copy)) {
            Node live = liveByCopy.get(copy);
            result.add(live != null ? live : copy);
            if (live != null) kept.add(live);
        }
        // Kept children keep their order, so walk the live paragraph once: new nodes go in front of
        // the live child that is current (the run they replace), dropped children go when passed.
        // These are plain insert/remove steps after all parsing and checks; they are not undone if
        // the XML store itself fails here.
        Node cursor = firstElement(paragraphNode);
        for (Node node : result) {
            if (kept.contains(node)) {
                while (cursor != node) {
                    if (cursor == null) throw new IllegalStateException("kept paragraph child out of order");
                    Node next = nextElement(cursor);
                    removeLiveChild(paragraph, cursor);
                    cursor = next;
                }
                cursor = nextElement(cursor);
            } else {
                insertLiveChild(paragraph, node, cursor);
            }
        }
        while (cursor != null) {
            Node next = nextElement(cursor);
            removeLiveChild(paragraph, cursor);
            cursor = next;
        }
        return true;
    }

    private static Node firstElement(Node parent) {
        Node child = parent.getFirstChild();
        return child == null || child.getNodeType() == Node.ELEMENT_NODE ? child : nextElement(child);
    }

    private static Node nextElement(Node node) {
        Node next = node.getNextSibling();
        while (next != null && next.getNodeType() != Node.ELEMENT_NODE) next = next.getNextSibling();
        return next;
    }

    private static void removeLiveChild(XWPFParagraph paragraph, Node child) {
        int run = runPosition(paragraph, child);
        if (run >= 0) {
            paragraph.removeRun(run);
        } else {
            paragraphNode(paragraph).removeChild(child);
        }
    }

    private static void insertLiveChild(XWPFParagraph paragraph, Node child, Node before) {
        int run = before == null ? -1 : runPosition(paragraph, before);
        if (run < 0 || !"r".equals(child.getLocalName()) || !WORD_NS.equals(child.getNamespaceURI())) {
            paragraphNode(paragraph).insertBefore(child, before);
            return;
        }
        // A new run: let XWPFParagraph create it in front of the run it replaces, then fill it.
        Node created = paragraph.insertNewRun(run).getCTR().getDomNode();
        while (child.getFirstChild() != null) created.appendChild(child.getFirstChild());
        for (int i = 0; i < child.getAttributes().getLength(); i++) {
            ((org.w3c.dom.Element) created).setAttributeNodeNS(
                    (org.w3c.dom.Attr) child.getAttributes().item(i).cloneNode(true));
        }
    }

    private static int runPosition(XWPFParagraph paragraph, Node node) {
        List<XWPFRun> runs = paragraph.getRuns();
        for (int i = 0; i < runs.size(); i++) {
            if (runs.get(i).getCTR().getDomNode() == node) return i;
        }
        return -1;
    }

    private static Node paragraphNode(XWPFParagraph paragraph) {
        return paragraph.getCTP().getDomNode();
    }

    // The node at the same child-index path in a deep copy of root.
    private static Node counterpart(Node root, Node copy, Node target) {
        Deque<Integer> path = new ArrayDeque<>();
        for (Node node = target; node != root; node = node.getParentNode()) {
            if (node == null) {
                return null;
            }
            int index = 0;
            for (Node sibling = node.getPreviousSibling(); sibling != null; sibling = sibling.getPreviousSibling()) index++;
            path.push(index);
        }
        Node mapped = copy;
        for (int index : path) {
            mapped = mapped == null ? null : mapped.getChildNodes().item(index);
        }
        if (mapped == null || !Objects.equals(mapped.getNamespaceURI(), target.getNamespaceURI())
                || !Objects.equals(mapped.getLocalName(), target.getLocalName())) {
            return null;
        }
        return mapped;
    }

    private static boolean isRunOf(Node run, Node paragraph) {
        return run != null && "r".equals(run.getLocalName()) && WORD_NS.equals(run.getNamespaceURI())
                && run.getParentNode() == paragraph;
    }

    // State source placement on the equation itself; a lone inline oMath is centred by Word.
    private static void ensureJustification(Document ownerDocument, Node mathPara, String justification) {
        Node properties = null;
        for (Node child = mathPara.getFirstChild(); child != null; child = child.getNextSibling()) {
            if ("oMathParaPr".equals(child.getLocalName()) && MATH_NS.equals(child.getNamespaceURI())) properties = child;
        }
        if (properties == null) {
            properties = ownerDocument.createElementNS(MATH_NS, "m:oMathParaPr");
            mathPara.insertBefore(properties, mathPara.getFirstChild());
        }
        for (Node child = properties.getFirstChild(); child != null; child = child.getNextSibling()) {
            if ("jc".equals(child.getLocalName()) && MATH_NS.equals(child.getNamespaceURI())) {
                ((org.w3c.dom.Element) child).setAttributeNS(MATH_NS, "m:val", justification);
                return;
            }
        }
        org.w3c.dom.Element jc = ownerDocument.createElementNS(MATH_NS, "m:jc");
        jc.setAttributeNS(MATH_NS, "m:val", justification);
        properties.appendChild(jc);
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
            // Whitespace between run children is not run content and must not create empty runs.
            boolean content = child.getNodeType() == Node.ELEMENT_NODE;
            if ("rPr".equals(child.getLocalName())) {
                before.appendChild(child.cloneNode(true));
                after.appendChild(child.cloneNode(true));
            } else if (child == object) {
                passedObject = true;
            } else if (passedObject) {
                after.appendChild(child);
                hasAfter |= content;
            } else {
                before.appendChild(child);
                hasBefore |= content;
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
        if (!MATH_NS.equals(importedMath.getNamespaceURI())) {
            throw new IllegalArgumentException("inline OMML root must use the math namespace");
        }
        String localName = importedMath.getLocalName();
        if ("oMath".equals(localName)) {
            return keepInlineObjectTogether(ownerDocument, importedMath);
        }
        if ("oMathPara".equals(localName)) {
            NodeList children = importedMath.getChildNodes();
            Node equation = null;
            for (int i = 0; i < children.getLength(); i++) {
                Node child = children.item(i);
                if (child.getNodeType() != Node.ELEMENT_NODE) {
                    if ((child.getNodeType() == Node.TEXT_NODE || child.getNodeType() == Node.CDATA_SECTION_NODE)
                            && !child.getNodeValue().isBlank()) {
                        throw new IllegalArgumentException("unexpected text in inline OMML paragraph");
                    }
                    continue;
                }
                if (MATH_NS.equals(child.getNamespaceURI()) && "oMathParaPr".equals(child.getLocalName())) continue;
                if (!MATH_NS.equals(child.getNamespaceURI()) || !"oMath".equals(child.getLocalName()) || equation != null) {
                    throw new IllegalArgumentException("inline OMML paragraph requires exactly one equation");
                }
                equation = child;
            }
            if (equation == null) throw new IllegalArgumentException("inline OMML paragraph is missing an equation");
            return keepInlineObjectTogether(ownerDocument, equation);
        }
        // Fragments such as m:r or m:f are not verified input roots. Flattening them would
        // lose their wrapper and silently produce invalid math; leave the OLE intact instead.
        throw new IllegalArgumentException("unverified inline OMML root: " + localName);
    }

    // An inline OLE object occupies one unbreakable position in its source paragraph.
    // Preserve that boundary in editable math; Word otherwise wraps at relation operators,
    // including across page boundaries. Native OMML and display equations do not use this path.
    private static Node keepInlineObjectTogether(Document ownerDocument, Node math) {
        groupLeadingTemperatureComparison(ownerDocument, math);
        Node box = ownerDocument.createElementNS(MATH_NS, "m:box");
        Node properties = ownerDocument.createElementNS(MATH_NS, "m:boxPr");
        org.w3c.dom.Element noBreak = ownerDocument.createElementNS(MATH_NS, "m:noBreak");
        noBreak.setAttributeNS(MATH_NS, "m:val", "on");
        properties.appendChild(noBreak);
        box.appendChild(properties);
        Node expression = ownerDocument.createElementNS(MATH_NS, "m:e");
        while (math.getFirstChild() != null) expression.appendChild(math.getFirstChild());
        box.appendChild(expression);
        math.appendChild(box);
        return math;
    }

    // Writer's installed OMML importer treats a bare leading > as a binary relation
    // with a missing operand, then drops it when saving DOCX. A delimiter with empty
    // visible characters groups the existing operator without adding an operand.
    // Only the measured >number-degree-C shape is covered, not arbitrary relations.
    private static void groupLeadingTemperatureComparison(Document document, Node math) {
        List<Node> parts = elementChildren(math);
        if (parts.size() != 3 || !">".equals(mathRunText(parts.get(0)))
                || !isMathElement(parts.get(1), "sSup") || !"C".equals(mathRunText(parts.get(2)))) return;
        Node operator = parts.get(0);
        for (Node child : elementChildren(operator)) {
            if (isMathElement(child, "rPr")) {
                for (Node property : elementChildren(child)) {
                    if (isMathElement(property, "nor") || isMathElement(property, "lit")) return;
                }
            }
        }
        Node base = null;
        Node superscript = null;
        for (Node child : elementChildren(parts.get(1))) {
            if (isMathElement(child, "e") && base == null) base = child;
            else if (isMathElement(child, "sup") && superscript == null) superscript = child;
            else if (!isMathElement(child, "sSupPr")) return;
        }
        if (base == null || superscript == null) return;
        List<Node> baseParts = elementChildren(base);
        List<Node> supParts = elementChildren(superscript);
        if (baseParts.size() != 1 || supParts.size() != 1) return;
        String number = mathRunText(baseParts.get(0));
        if (number == null || !number.matches("[0-9]+") || !"°".equals(mathRunText(supParts.get(0)))) return;

        Node delimiter = document.createElementNS(MATH_NS, "m:d");
        Node properties = document.createElementNS(MATH_NS, "m:dPr");
        for (String name : List.of("begChr", "endChr")) {
            org.w3c.dom.Element character = document.createElementNS(MATH_NS, "m:" + name);
            character.setAttributeNS(MATH_NS, "m:val", "");
            properties.appendChild(character);
        }
        delimiter.appendChild(properties);
        Node expression = document.createElementNS(MATH_NS, "m:e");
        math.replaceChild(delimiter, operator);
        expression.appendChild(operator);
        delimiter.appendChild(expression);
    }

    private static boolean isMathElement(Node node, String name) {
        return MATH_NS.equals(node.getNamespaceURI()) && name.equals(node.getLocalName());
    }

    private static List<Node> elementChildren(Node node) {
        List<Node> children = new ArrayList<>();
        for (Node child = node.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child.getNodeType() == Node.ELEMENT_NODE) children.add(child);
        }
        return children;
    }

    private static String mathRunText(Node node) {
        if (!isMathElement(node, "r")) return null;
        String text = null;
        for (Node child : elementChildren(node)) {
            if (isMathElement(child, "t") && text == null) {
                StringBuilder value = new StringBuilder();
                // XMLBeans' live DOM does not implement DOM Level 3 getTextContent().
                for (Node leaf = child.getFirstChild(); leaf != null; leaf = leaf.getNextSibling()) {
                    if (leaf.getNodeType() != Node.TEXT_NODE && leaf.getNodeType() != Node.CDATA_SECTION_NODE) return null;
                    value.append(leaf.getNodeValue());
                }
                text = value.toString();
            }
            else if (!isMathElement(child, "rPr")
                    && !(WORD_NS.equals(child.getNamespaceURI()) && "rPr".equals(child.getLocalName()))) return null;
        }
        return text;
    }
}
