package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFParagraph;

import java.util.List;

public record MultiObjectPatchPlan(
        boolean safe,
        XWPFParagraph paragraph,
        List<ParagraphSegment> segments,
        SkipReason skipReason,
        SkipClassification classification
) {
    public static MultiObjectPatchPlan safe(XWPFParagraph paragraph, List<ParagraphSegment> segments) {
        return new MultiObjectPatchPlan(true, paragraph, List.copyOf(segments), null, null);
    }

    public static MultiObjectPatchPlan skip(
            XWPFParagraph paragraph,
            SkipReason skipReason,
            SkipClassification classification
    ) {
        return new MultiObjectPatchPlan(false, paragraph, List.of(), skipReason, classification);
    }

    public List<ParagraphSegment> objectSegments() {
        return segments.stream().filter(segment -> segment.type() == ParagraphSegment.Type.OBJECT).toList();
    }

    public enum SkipCategory {
        UNSAFE,
        AMBIGUOUS
    }

    public enum SkipReason {
        NATIVE_OMML_PRESENT(SkipCategory.UNSAFE),
        UNRESOLVED_MANIFEST(SkipCategory.UNSAFE),
        OMML_CONVERSION_FAILED(SkipCategory.UNSAFE),
        XML_MUTATION_FAILED(SkipCategory.UNSAFE),
        UNSAFE_RUN_STRUCTURE(SkipCategory.UNSAFE),
        UNKNOWN_SOURCE(SkipCategory.AMBIGUOUS),
        AMBIGUOUS_RUN_SPAN(SkipCategory.AMBIGUOUS),
        UNSUPPORTED_PARAGRAPH_STRUCTURE(SkipCategory.AMBIGUOUS);

        private final SkipCategory category;

        SkipReason(SkipCategory category) {
            this.category = category;
        }

        public SkipCategory category() {
            return category;
        }
    }
}
