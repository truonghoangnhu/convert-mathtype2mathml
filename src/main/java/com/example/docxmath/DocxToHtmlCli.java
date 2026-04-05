package com.example.docxmath;

import org.apache.poi.openxml4j.util.ZipSecureFile;

import java.nio.file.Path;

public final class DocxToHtmlCli {
    private DocxToHtmlCli() {
    }

    public static void main(String[] args) throws Exception {
        configureZipSafetyLimitsForLargeDocx();

        if (args.length < 2) {
            usageAndExit(1);
        }

        Path input = Path.of(args[0]).toAbsolutePath().normalize();
        Path output = Path.of(args[1]).toAbsolutePath().normalize();
        boolean includeMathJax = true;
        Path mathmlManifest = null;
        Subject subject = null;

        for (int i = 2; i < args.length; i++) {
            String arg = args[i];
            if ("--native-mathml-only".equals(arg)) {
                includeMathJax = false;
            } else if ("--mathml-manifest".equals(arg)) {
                if (i + 1 >= args.length) {
                    System.err.println("Missing value after --mathml-manifest");
                    usageAndExit(2);
                }
                mathmlManifest = Path.of(args[++i]).toAbsolutePath().normalize();
            } else if ("--subject".equals(arg)) {
                if (i + 1 >= args.length) {
                    System.err.println("Missing value after --subject");
                    usageAndExit(2);
                }
                try {
                    subject = Subject.fromCliValue(args[++i]);
                } catch (IllegalArgumentException ex) {
                    System.err.println(ex.getMessage());
                    usageAndExit(2);
                }
            } else {
                System.err.println("Unknown option: " + arg);
                usageAndExit(2);
            }
        }

        MathmlSidecarRegistry registry = mathmlManifest == null
                ? MathmlSidecarRegistry.empty()
                : MathmlSidecarRegistry.load(mathmlManifest);
        Subject effectiveSubject = subject == null ? SubjectDetector.detect(input) : subject;

        DocxToHtmlConverter converter = new DocxToHtmlConverter(includeMathJax, registry, effectiveSubject);
        DocxToHtmlConverter.ConversionSummary summary = converter.convert(input, output);

        System.out.println("Input:  " + input);
        System.out.println("Output: " + output);
        System.out.println("Subject: " + effectiveSubject.cliName());
        if (mathmlManifest != null) {
            System.out.println("MathML manifest: " + mathmlManifest);
        }
        System.out.println("OMML equations converted: " + summary.ommlEquations());
        System.out.println("Transpect sidecar equations used: " + summary.sidecarMathmlEquations());
        System.out.println("OLE fallback images used: " + summary.olePreviewImages());
        System.out.println("  OLE equation previews: " + summary.oleEquationPreviews());
        System.out.println("  OLE diagram/chemical previews: " + summary.oleDiagramPreviews());
        System.out.println("  OLE generic previews: " + summary.oleIllustrationPreviews());
        System.out.println("EMF/WMF previews encountered: " + summary.emfWmfPreviewImages());
        System.out.println("Unresolved Visio previews: " + summary.unresolvedVisioPreviews());
        System.out.println("Text normalizations applied: " + summary.normalizedTextFixes());
        System.out.println("Chemistry inline fixes applied: " + summary.chemistryInlineFixes());
        System.out.println("Chemistry arrow/symbol fixes applied: " + summary.chemistryArrowSymbolFixes());
        System.out.println("Chemistry unit fixes applied: " + summary.chemistryUnitFixes());
        System.out.println("Physics unit fixes applied: " + summary.physicsUnitFixes());
        System.out.println("Physics text fixes applied: " + summary.physicsTextFixes());
        System.out.println("Mixed math/text cleanup fixes applied: " + summary.mixedMathTextCleanupFixes());
        System.out.println("Math glyph/text fixes applied: " + summary.mathGlyphCleanupFixes());
        System.out.println("Empty paragraphs removed: " + summary.emptyParagraphRemovedCount());
        System.out.println("Table-adjacent empty paragraph cleanups: " + summary.tableAdjacentEmptyParagraphCleanupCount());
        System.out.println("Table-cell empty paragraphs removed: " + summary.tableCellEmptyParagraphRemovedCount());
        System.out.println("Math-block flow cleanups: " + summary.mathBlockFlowCleanupCount());
        System.out.println("Suppressed blank standalone images: " + summary.suppressedBlankStandaloneImageCount());
        System.out.println("Suppressed nonessential standalone context images: " + summary.suppressedNonessentialStandaloneImageCount());
        System.out.println("Restored context images kept: " + summary.restoredContextImageCount());
        System.out.println("EMF/WMF previews rasterized to PNG: " + summary.rasterizedMetafilePreviews());
        System.out.println("EMF/WMF raster-cache hits: " + summary.rasterizedMetafileCacheHits());
        System.out.println("Unsupported OLE placeholders: " + summary.olePlaceholders());
        long converterTotalMillis = summary.docxLoadMillis()
                + summary.bodyRenderMillis()
                + summary.essayPolicyMillis()
                + summary.htmlBuildMillis()
                + summary.publishSanitizeMillis()
                + summary.htmlWriteMillis();
        System.out.println("Conversion timings (ms):");
        System.out.println("  DOCX load: " + summary.docxLoadMillis());
        System.out.println("  Body render: " + summary.bodyRenderMillis());
        System.out.println("  OMML handling: " + summary.ommlHandlingMillis());
        System.out.println("  MathType sidecar handling: " + summary.mathTypeHandlingMillis());
        System.out.println("  Image/diagram rendering: " + summary.imageRenderingMillis());
        System.out.println("  HTML cleanup: " + summary.htmlCleanupMillis());
        System.out.println("  Essay figure policy: " + summary.essayPolicyMillis());
        System.out.println("  HTML build: " + summary.htmlBuildMillis());
        System.out.println("  Publish sanitize: " + summary.publishSanitizeMillis());
        System.out.println("  HTML write: " + summary.htmlWriteMillis());
        System.out.println("  Converter total: " + converterTotalMillis);
    }

    private static void usageAndExit(int code) {
        System.err.println("Usage: java -jar docx-html-math.jar <input.docx> <output.html> [--native-mathml-only] [--mathml-manifest manifest.tsv] [--subject generic|physics|chemistry|math|biology]");
        System.exit(code);
    }

    private static void configureZipSafetyLimitsForLargeDocx() {
        String configured = System.getProperty("docxmath.poi.maxFileCount", "").trim();
        long limit = 200_000L;
        if (!configured.isEmpty()) {
            try {
                limit = Long.parseLong(configured);
            } catch (NumberFormatException ignored) {
                // keep default if custom value is invalid
            }
        }
        ZipSecureFile.setMaxFileCount(limit);
    }
}
