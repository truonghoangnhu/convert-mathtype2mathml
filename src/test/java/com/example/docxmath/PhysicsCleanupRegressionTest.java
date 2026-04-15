package com.example.docxmath;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class PhysicsCleanupRegressionTest {
    private final DocxToHtmlConverter publishPhysicsConverter =
            new DocxToHtmlConverter(false, MathmlSidecarRegistry.empty(), Subject.PHYSICS, OutputMode.PUBLISH);

    @Test
    void normalizesMalformedIsotopeNotation() throws Exception {
        String tc = normalizeMathml("<math><msup><mrow/><mn>99</mn></msup><mn>43</mn><mtext>Tc</mtext></math>");
        String u = normalizeMathml("<math><msup><mrow/><mn>235</mn></msup><mn>92</mn><mtext>U</mtext></math>");
        String he = normalizeMathml("<math><msup><mrow/><mn>4</mn></msup><mn>2</mn><mtext>He</mtext></math>");
        String si = normalizeMathml("<math><msubsup><mrow/><mn>14</mn><mn>27</mn></msubsup><mtext>Si</mtext></math>");
        String pb = normalizeMathml("<math><msubsup><mn> </mn><mn>82</mn><mn>206</mn></msubsup><mtext>Pb</mtext></math>");
        String generic = normalizeMathml("<math><msubsup><mrow/><mi>Z</mi><mi>A</mi></msubsup><mi>X</mi></math>");

        assertTrue(tc.contains("<msubsup><mrow/><mn>43</mn><mn>99</mn></msubsup><mtext>Tc</mtext>"));
        assertTrue(u.contains("<msubsup><mrow/><mn>92</mn><mn>235</mn></msubsup><mtext>U</mtext>"));
        assertTrue(he.contains("<msubsup><mrow/><mn>2</mn><mn>4</mn></msubsup><mtext>He</mtext>"));
        assertTrue(si.contains("<msubsup><mrow/><mn>14</mn><mn>27</mn></msubsup><mtext>Si</mtext>"));
        assertTrue(pb.contains("<msubsup><mrow/><mn>82</mn><mn>206</mn></msubsup><mtext>Pb</mtext>"));
        assertTrue(generic.contains("<msubsup><mrow/><mi>Z</mi><mi>A</mi></msubsup><mi>X</mi>"));
    }

    @Test
    void normalizesPhysicsUnitsAndTemperature() throws Exception {
        assertTrue(normalizeMathml("<math><mn>0,42</mn><mi>μ</mi><mi>m</mi></math>").contains("<mtext>μm</mtext>"));
        assertTrue(normalizeMathml("<math><mn>100</mn><mi>μ</mi><mi>F</mi></math>").contains("<mtext>μF</mtext>"));
        assertTrue(normalizeMathml("<math><mn>12,</mn><mi mathvariant=\"normal\">Ω</mi></math>").contains("<mn>12</mn><mspace width=\"0.33em\"/><mi mathvariant=\"normal\">Ω</mi>"));
        assertTrue(normalizeMathml("<math><mn>12,0,</mn><mi mathvariant=\"normal\">Ω</mi></math>").contains("<mn>12,0</mn><mspace width=\"0.33em\"/><mi mathvariant=\"normal\">Ω</mi>"));
        assertTrue(normalizeMathml("<math><msup><mn>27</mn><mo>°</mo></msup><mtext>C</mtext></math>").contains("<mn>27</mn><mspace width=\"0.33em\"/><mtext>°C</mtext>"));
        assertTrue(normalizeMathml("<math><msup><mn>67</mn><mo>°</mo></msup><mtext>C</mtext></math>").contains("<mn>67</mn><mspace width=\"0.33em\"/><mtext>°C</mtext>"));
        assertTrue(normalizeMathml("<math><mn>33,8,</mn><mtext>psi</mtext></math>").contains("<mn>33,8</mn><mspace width=\"0.33em\"/><mtext>psi</mtext>"));
        assertTrue(normalizeMathml("<math><mn>4167,</mn><mtext>MW</mtext></math>").contains("<mn>4167</mn><mspace width=\"0.33em\"/><mtext>MW</mtext>"));
        assertTrue(normalizeMathml("<math><mn>2,2,</mn><mtext>T</mtext></math>").contains("<mn>2,2</mn><mspace width=\"0.33em\"/><mtext>T</mtext>"));
        assertTrue(normalizeMathml("<math><mn>1,7,</mn><mtext>N</mtext></math>").contains("<mn>1,7</mn><mspace width=\"0.33em\"/><mtext>N</mtext>"));
        assertTrue(normalizeMathml("<math><mtext>J/(kg.K)</mtext></math>").contains("J/(kg.K)"));
    }

    @Test
    void preservesOrdinaryDegreeNotationWithoutCelsiusPromotion() throws Exception {
        String normalized = normalizeMathml("<math><msup><mn>45</mn><mo>°</mo></msup></math>");
        assertTrue(normalized.contains("<msup><mn>45</mn><mo>°</mo></msup>"));
        assertFalse(normalized.contains("°C"));
    }

    @Test
    void cleansSplitFunctionTokensWithoutTouchingGoodMath() throws Exception {
        String split = normalizeMathml("<math><mi>c</mi><mtext>os</mtext><mo>(</mo><mi>φ</mi><mo>)</mo></math>");
        String alreadyGood = normalizeMathml("<math><mi>cos</mi><mi>φ</mi></math>");
        String splitWithoutParen = normalizeMathml("<math><mi>c</mi><mtext>os</mtext><mi>φ</mi></math>");

        assertTrue(split.contains("<mi>cos</mi><mo>(</mo><mi>φ</mi>"));
        assertTrue(splitWithoutParen.contains("<mi>cos</mi><mi>φ</mi>"));
        assertTrue(alreadyGood.contains("<mi>cos</mi><mi>φ</mi>"));
    }

    @Test
    void normalizesLeadingArtifactsAndPhysicsGlyphs() throws Exception {
        assertEquals("Câu hỏi vật lí", normalizeVisible("   Câu hỏi vật lí"));
        assertEquals("Nhiệt độ", normalizeVisible("» Nhiệt độ"));
        assertEquals("• Nhiệt độ", normalizeVisible("• Nhiệt độ"));
        assertEquals("cosφ = 0,8, Ω, ∠ABC, π, ω, ≈", normalizeVisible("cos = 0,8, , ABC, , , "));
        assertEquals("λm", normalizeVisible("m"));
        assertEquals("μF", normalizeVisible("F"));
        assertEquals("27 °C", normalizeInlineHtml("27<sup>0</sup>C"));
        assertTrue(
                normalizeInlineHtml("<span class=\"math-inline mathml\"><math><msup><mn>27</mn><mo>°</mo></msup></math></span> C")
                        .contains("<mn>27</mn><mspace width=\"0.33em\"/><mtext>°C</mtext>")
        );
    }

    @Test
    void hidesUnresolvedEquationPlaceholdersInPublishOutput() throws Exception {
        String placeholder = buildUnsupportedEquationPlaceholder(true);
        assertTrue(placeholder.contains("unsupported-equation"));
        assertTrue(placeholder.contains("qa-hidden"));
        assertTrue(placeholder.contains("data-unresolved-reason=\"dsmt4-manifest-missing\""));
        assertTrue(placeholder.contains("data-placeholder-label=\"Unresolved OLE equation: Equation.DSMT4\""));
        assertFalse(placeholder.contains("[Unresolved OLE equation: Equation.DSMT4]"));
    }

    private String normalizeMathml(String raw) throws Exception {
        Method method = DocxToHtmlConverter.class.getDeclaredMethod("normalizeMathmlFragment", String.class);
        method.setAccessible(true);
        return (String) method.invoke(publishPhysicsConverter, raw);
    }

    private String normalizeVisible(String raw) throws Exception {
        Method method = DocxToHtmlConverter.class.getDeclaredMethod("normalizeVisibleTextChunk", String.class);
        method.setAccessible(true);
        return (String) method.invoke(publishPhysicsConverter, raw);
    }

    private String normalizeInlineHtml(String raw) throws Exception {
        Method method = DocxToHtmlConverter.class.getDeclaredMethod("normalizeInlineHtmlSegment", String.class);
        method.setAccessible(true);
        return (String) method.invoke(publishPhysicsConverter, raw);
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static String buildUnsupportedEquationPlaceholder(boolean qaHidden) throws Exception {
        Class<?> oleKindClass = Class.forName("com.example.docxmath.DocxToHtmlConverter$OleKind");
        Enum oleKind = Enum.valueOf((Class<Enum>) oleKindClass.asSubclass(Enum.class), "DSMT4_EQUATION");
        Method method = DocxToHtmlConverter.class.getDeclaredMethod(
                "buildUnsupportedOlePlaceholder",
                String.class,
                oleKindClass,
                String.class,
                boolean.class,
                String.class,
                String.class,
                String.class,
                String.class,
                String.class,
                boolean.class
        );
        method.setAccessible(true);
        return (String) method.invoke(
                null,
                "Unresolved OLE equation: Equation.DSMT4",
                oleKind,
                "Equation.DSMT4",
                false,
                "sidecar-first",
                "ole:.bin,preview:.wmf",
                "ole:/word/embeddings/oleObject1.bin,preview:/word/media/image1.wmf",
                "ole-equation-dsmt4",
                "dsmt4-manifest-missing",
                qaHidden
        );
    }
}
