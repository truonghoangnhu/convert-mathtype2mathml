package com.example.docxmath.word;

import org.w3c.dom.Node;

/** Detects the observed OLE-to-prose boundary whose visual gap is absent from document text.
 * No space is inferred from a picture's viewport or from a formula's characters.
 */
final class InlineBoundarySafety {
    private static final String WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

    private InlineBoundarySafety() { }

    static boolean followedByUnseparatedLetter(Node object) {
        Node run = object == null ? null : object.getParentNode();
        if (!isWord(run, "r") || !isWord(run.getParentNode(), "p")) return false;
        // Multi-object paragraphs can split a mixed run at the object itself.
        NextContent insideRun = nextContent(object.getNextSibling());
        if (insideRun != NextContent.NONE) return insideRun == NextContent.LETTER;
        for (Node next = run.getNextSibling(); next != null; next = next.getNextSibling()) {
            if (next.getNodeType() != Node.ELEMENT_NODE) continue;
            if (isWord(next, "bookmarkStart") || isWord(next, "bookmarkEnd") || isWord(next, "proofErr")) continue;
            if (!isWord(next, "r")) return false;
            NextContent content = nextContent(next.getFirstChild());
            if (content != NextContent.NONE) return content == NextContent.LETTER;
        }
        return false;
    }

    private enum NextContent { NONE, LETTER, OTHER }

    private static NextContent nextContent(Node first) {
        for (Node child = first; child != null; child = child.getNextSibling()) {
            if (child.getNodeType() != Node.ELEMENT_NODE || isWord(child, "rPr")
                    || isWord(child, "lastRenderedPageBreak")) continue;
            // Unlike lastRenderedPageBreak, a real tab or break separates the text.
            if (!isWord(child, "t")) return NextContent.OTHER;
            StringBuilder text = new StringBuilder();
            for (Node part = child.getFirstChild(); part != null; part = part.getNextSibling()) {
                if (part.getNodeType() == Node.TEXT_NODE) text.append(part.getNodeValue());
            }
            if (!text.isEmpty()) return Character.isLetter(text.codePointAt(0)) ? NextContent.LETTER : NextContent.OTHER;
        }
        return NextContent.NONE;
    }

    static SkipClassification classification() {
        return SkipClassification.of(PatchSkipReason.INLINE_SPACING_REQUIRES_REVIEW,
                "needs_review: inline object is followed by a letter without an explicit separator; original retained");
    }

    private static boolean isWord(Node node, String name) {
        return node != null && WORD_NS.equals(node.getNamespaceURI()) && name.equals(node.getLocalName());
    }
}
