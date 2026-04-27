package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;

import java.util.List;

public interface MathSourceDetector {
    List<MathOccurrence> detect(XWPFDocument document, XWPFParagraph paragraph);
}
