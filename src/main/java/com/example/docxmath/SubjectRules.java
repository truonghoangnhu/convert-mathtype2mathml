package com.example.docxmath;

import java.util.List;

public record SubjectRules(
        List<TextReplacementRule> textReplacementRules,
        boolean chemistryInlineNormalizationEnabled,
        boolean chemistryHtmlScriptNormalizationEnabled,
        String diagramCssClass,
        String diagramAltText,
        String chemicalDiagramCssClass,
        String chemicalDiagramAltText
) {
    public SubjectRules {
        textReplacementRules = List.copyOf(textReplacementRules);
    }
}
