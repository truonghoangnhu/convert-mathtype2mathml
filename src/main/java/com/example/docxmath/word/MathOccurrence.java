package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.w3c.dom.Node;

public record MathOccurrence(
        SourceType sourceType,
        XWPFDocument document,
        XWPFParagraph paragraph,
        Node sourceNode,
        String oleRelationshipId,
        String previewRelationshipId,
        String olePartName,
        String previewPartName,
        boolean blockCandidate
) {
    public enum SourceType {
        NATIVE_OMML,
        OLE_BIN,
        WMF_PREVIEW,
        UNKNOWN
    }
}
