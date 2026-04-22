package com.example.docxmath;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class ChemistryCleanupRegressionTest {
    private final DocxToHtmlConverter publishChemistryConverter =
            new DocxToHtmlConverter(false, MathmlSidecarRegistry.empty(), Subject.CHEMISTRY, OutputMode.PUBLISH);

    @Test
    void normalizesLegacyReactionArrowsInVisibleChemistryText() throws Exception {
        assertEquals(
                "C(s) + H<sub>2</sub>O(g)<span class=\"chem-inline\" data-chem-fixed=\"1\" data-chem-arrow-fixed=\"1\">⇌</span>CO(g) + H<sub>2</sub>(g)",
                normalizeInlineHtml("C(s) + H<sub>2</sub>O(g) ⇌ CO(g) + H<sub>2</sub>(g)")
        );
        assertEquals(
                "<span class=\"chem-inline\" data-chem-fixed=\"1\">CH<sub>4</sub></span><span class=\"chem-inline\" data-chem-fixed=\"1\" data-chem-arrow-fixed=\"1\">→</span>2<span class=\"chem-inline\" data-chem-fixed=\"1\">H<sub>2</sub></span> + C",
                normalizeInlineHtml("CH4 ⟶ 2H2 + C")
        );
    }

    @Test
    void normalizesReversibleArrowWhenInputIsPlainTextChunk() throws Exception {
        String normalized = normalizeVisible("NH3 + H2O ⇌ NH4+ + OH-");
        assertTrue(normalized.contains("data-chem-arrow-fixed=\"1\">⇌</span>"));
        assertTrue(normalized.contains("NH<sub>3</sub>"));
        assertTrue(normalized.contains("NH<sub>4</sub><sup>+</sup>"));
        assertTrue(normalized.contains("OH<sup>-</sup>"));
    }

    private String normalizeVisible(String raw) throws Exception {
        Method method = DocxToHtmlConverter.class.getDeclaredMethod("normalizeVisibleTextChunk", String.class);
        method.setAccessible(true);
        return (String) method.invoke(publishChemistryConverter, raw);
    }

    private String normalizeInlineHtml(String raw) throws Exception {
        Method method = DocxToHtmlConverter.class.getDeclaredMethod("normalizeInlineHtmlSegment", String.class);
        method.setAccessible(true);
        return (String) method.invoke(publishChemistryConverter, raw);
    }
}
