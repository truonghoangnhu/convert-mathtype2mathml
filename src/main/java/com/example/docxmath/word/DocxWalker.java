package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.IBody;
import org.apache.poi.xwpf.usermodel.IBodyElement;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;

import java.util.ArrayList;
import java.util.List;

public final class DocxWalker {
    private final MathSourceDetector detector;

    public DocxWalker(MathSourceDetector detector) {
        this.detector = detector;
    }

    public List<MathOccurrence> collect(XWPFDocument document) {
        return collectFromBody(document, document);
    }

    private List<MathOccurrence> collectFromBody(XWPFDocument document, IBody body) {
        List<MathOccurrence> results = new ArrayList<>();
        for (IBodyElement element : body.getBodyElements()) {
            switch (element.getElementType()) {
                case PARAGRAPH -> results.addAll(detector.detect(document, (XWPFParagraph) element));
                case TABLE -> results.addAll(collectFromTable(document, (XWPFTable) element));
                default -> {
                }
            }
        }
        return results;
    }

    private List<MathOccurrence> collectFromTable(XWPFDocument document, XWPFTable table) {
        List<MathOccurrence> results = new ArrayList<>();
        for (XWPFTableRow row : table.getRows()) {
            for (XWPFTableCell cell : row.getTableCells()) {
                results.addAll(collectFromBody(document, cell));
            }
        }
        return results;
    }
}
