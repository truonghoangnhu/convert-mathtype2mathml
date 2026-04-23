package com.example.docxmath.word;

public record SkipClassification(
        PatchSkipReason reason,
        String detail
) {
    public static SkipClassification of(PatchSkipReason reason, String detail) {
        return new SkipClassification(reason, detail);
    }

    public String detailOrReason() {
        if (detail == null || detail.isBlank()) {
            return reason.name();
        }
        return detail;
    }
}
