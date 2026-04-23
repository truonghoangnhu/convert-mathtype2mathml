package com.example.docxmath.word;

public record InlinePatchPlan(
        boolean safe,
        MathOccurrence occurrence,
        SkipReason skipReason,
        SkipClassification classification
) {
    public static InlinePatchPlan safe(MathOccurrence occurrence) {
        return new InlinePatchPlan(true, occurrence, null, null);
    }

    public static InlinePatchPlan skip(
            MathOccurrence occurrence,
            SkipReason skipReason,
            SkipClassification classification
    ) {
        return new InlinePatchPlan(false, occurrence, skipReason, classification);
    }

    public enum SkipReason {
        NATIVE_OMML_PRESENT,
        MULTI_OBJECT_PARAGRAPH,
        UNKNOWN_SOURCE,
        AMBIGUOUS_RUN_SPAN
    }
}
