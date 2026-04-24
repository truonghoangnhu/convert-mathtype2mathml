package com.example.docxmath;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.example.docxmath.word.DocxMathPatchMain;
import com.example.docxmath.word.ManifestMathSidecarRepository;
import com.example.docxmath.word.PatchSkipReason;
import org.apache.poi.openxml4j.util.ZipSecureFile;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashMap;
import java.util.Map;

public final class DocxToHtmlCli {
    private static final ObjectMapper JSON = new ObjectMapper();

    private DocxToHtmlCli() {
    }

    public static void main(String[] args) throws Exception {
        configureZipSafetyLimitsForLargeDocx();

        if (args.length > 0 && "review-server".equals(args[0])) {
            ReviewServerCli.run(sliceArgs(args, 1));
            return;
        }
        if (args.length > 0 && "--patch-docx".equals(args[0])) {
            runPatchDocx(sliceArgs(args, 1));
            return;
        }

        if (args.length < 2) {
            usageAndExit(1);
        }

        Path input = Path.of(args[0]).toAbsolutePath().normalize();
        Path output = Path.of(args[1]).toAbsolutePath().normalize();
        boolean includeMathJax = true;
        Path mathmlManifest = null;
        Subject subject = null;
        OutputMode outputMode = OutputMode.PUBLISH;

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
            } else if ("--output-mode".equals(arg)) {
                if (i + 1 >= args.length) {
                    System.err.println("Missing value after --output-mode");
                    usageAndExit(2);
                }
                try {
                    outputMode = OutputMode.fromCliValue(args[++i]);
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

        DocxToHtmlConverter converter = new DocxToHtmlConverter(includeMathJax, registry, effectiveSubject, outputMode);
        DocxToHtmlConverter.ConversionSummary summary = converter.convert(input, output);

        System.out.println("Input:  " + input);
        System.out.println("Output: " + output);
        System.out.println("Subject: " + effectiveSubject.cliName());
        System.out.println("Output mode: " + outputMode.cliName());
        if (mathmlManifest != null) {
            System.out.println("MathML manifest: " + mathmlManifest);
        }
        System.out.println("OMML equations converted: " + summary.ommlEquations());
        System.out.println("Transpect sidecar equations used: " + summary.sidecarMathmlEquations());
        System.out.println("DSMT4 total: " + summary.dsmt4Total());
        System.out.println("  DSMT4 sidecar resolved: " + summary.dsmt4SidecarResolved());
        System.out.println("  DSMT4 unresolved: " + summary.dsmt4Unresolved());
        System.out.println("  DSMT4 manifest missing: " + summary.dsmt4ManifestMissing());
        System.out.println("  DSMT4 manifest mismatch: " + summary.dsmt4ManifestMismatch());
        System.out.println("  DSMT4 fallback placeholders: " + summary.dsmt4FallbackPlaceholderCount());
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
        System.err.println(
                "Usage: java -jar docx-html-math.jar <input.docx> <output.html> "
                        + "[--native-mathml-only] [--mathml-manifest manifest.tsv] "
                        + "[--subject generic|physics|chemistry|math|biology|english|literature] "
                        + "[--output-mode internal|publish]\n"
                        + "   or: java -jar docx-html-math.jar --patch-docx <input.docx> <output.docx> "
                        + "[--mathml-manifest manifest.tsv] [--patch-log-level summary|warnings] "
                        + "[--patch-summary-jsonl summary.jsonl] [--patch-summary-jsonl-stdout]\n"
                        + "   or: java -jar docx-html-math.jar review-server --review-root <dir> "
                        + "[or --root <dir>] "
                        + "[--host 127.0.0.1] [--port 8080]"
        );
        System.exit(code);
    }

    private static String[] sliceArgs(String[] args, int fromIndex) {
        if (fromIndex >= args.length) {
            return new String[0];
        }
        String[] sliced = new String[args.length - fromIndex];
        System.arraycopy(args, fromIndex, sliced, 0, sliced.length);
        return sliced;
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

    private static void runPatchDocx(String[] args) throws Exception {
        if (args.length < 2) {
            usageAndExit(1);
        }
        Path input = Path.of(args[0]).toAbsolutePath().normalize();
        Path output = Path.of(args[1]).toAbsolutePath().normalize();
        Path outputParent = output.getParent();
        if (outputParent != null) {
            Files.createDirectories(outputParent);
        }
        Path mathmlManifest = null;
        Path patchSummaryJsonl = null;
        boolean patchSummaryJsonlStdout = false;
        DocxMathPatchMain.LogLevel patchLogLevel = DocxMathPatchMain.LogLevel.WARNINGS;

        for (int i = 2; i < args.length; i++) {
            String arg = args[i];
            if ("--mathml-manifest".equals(arg)) {
                if (i + 1 >= args.length) {
                    System.err.println("Missing value after --mathml-manifest");
                    usageAndExit(2);
                }
                mathmlManifest = Path.of(args[++i]).toAbsolutePath().normalize();
            } else if ("--patch-log-level".equals(arg)) {
                if (i + 1 >= args.length) {
                    System.err.println("Missing value after --patch-log-level");
                    usageAndExit(2);
                }
                String value = args[++i].trim().toLowerCase();
                if ("summary".equals(value)) {
                    patchLogLevel = DocxMathPatchMain.LogLevel.SUMMARY;
                } else if ("warnings".equals(value)) {
                    patchLogLevel = DocxMathPatchMain.LogLevel.WARNINGS;
                } else {
                    System.err.println("Unsupported value for --patch-log-level: " + value);
                    usageAndExit(2);
                }
            } else if ("--patch-summary-jsonl".equals(arg)) {
                if (i + 1 >= args.length) {
                    System.err.println("Missing value after --patch-summary-jsonl");
                    usageAndExit(2);
                }
                patchSummaryJsonl = Path.of(args[++i]).toAbsolutePath().normalize();
            } else if ("--patch-summary-jsonl-stdout".equals(arg)) {
                patchSummaryJsonlStdout = true;
            } else {
                System.err.println("Unknown option for --patch-docx: " + arg);
                usageAndExit(2);
            }
        }
        if ((patchSummaryJsonl != null || patchSummaryJsonlStdout)
                && patchLogLevel != DocxMathPatchMain.LogLevel.SUMMARY) {
            patchLogLevel = DocxMathPatchMain.LogLevel.SUMMARY;
        }

        ManifestMathSidecarRepository repository = mathmlManifest == null
                ? ManifestMathSidecarRepository.empty()
                : ManifestMathSidecarRepository.load(mathmlManifest);
        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(repository, patchLogLevel).patch(input, output);
        if (patchSummaryJsonl != null) {
            appendPatchSummaryJsonlRecord(patchSummaryJsonl, input, output, mathmlManifest, summary);
        }
        System.out.print(renderPatchSummaryOutput(input, output, mathmlManifest, summary, patchSummaryJsonlStdout));
    }

    static String buildPatchSummaryJsonRecord(
            Path input,
            Path output,
            Path mathmlManifest,
            DocxMathPatchMain.PatchSummary summary
    ) throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("patch_mode", "docx_to_docx_native_omml");
        payload.put("input", input == null ? "" : input.toString());
        payload.put("output", output == null ? "" : output.toString());
        if (mathmlManifest != null) {
            payload.put("mathml_manifest", mathmlManifest.toString());
        }
        payload.put("scanned", summary.totalOccurrences());
        payload.put("block", summary.patchedBlocks());
        payload.put("inline", summary.patchedInline());
        payload.put("native", summary.nativeOmmlUntouched());
        payload.put("unresolved", summary.unresolved());
        payload.put("skipped_unsafe_inline", summary.skippedUnsafeInlineObjects());
        payload.put("skipped_multi", summary.skippedMultiObjectParagraphs());
        payload.put("skipped_unknown", summary.skippedUnknownOrAmbiguous());
        payload.put("multi_patched", summary.multiObjectPatchedParagraphs());
        payload.put("multi_skipped_unsafe", summary.multiObjectSkippedUnsafeParagraphs());
        payload.put("multi_skipped_ambiguous", summary.multiObjectSkippedAmbiguousParagraphs());
        if (!summary.ommlPreservationToken().isEmpty()) {
            payload.put("omml_preservation", summary.ommlPreservationToken());
        }
        payload.put("omml_before", formatOmmlSnapshot(summary.structureBeforePatch()));
        payload.put("omml_after", formatOmmlSnapshot(summary.structureAfterPatch()));
        if (!summary.ommlDriftWarningToken().isEmpty()) {
            payload.put("omml_drift_warning", summary.ommlDriftWarningToken());
        }
        if (!summary.ommlDriftClass().isEmpty()) {
            payload.put("omml_drift_class", summary.ommlDriftClass());
        }
        if (!summary.ommlDriftPair().isEmpty()) {
            payload.put("omml_drift_pair", summary.ommlDriftPair());
        }
        if (!summary.ommlDriftBundle().isEmpty()) {
            payload.put("omml_drift_bundle", summary.ommlDriftBundle());
        }
        return JSON.writeValueAsString(payload);
    }

    private static String formatOmmlSnapshot(DocxMathPatchMain.OmmlStructureSnapshot snapshot) {
        if (snapshot == null) {
            return "";
        }
        return "eq:" + snapshot.equationCount()
                + ",inline:" + snapshot.inlineEquationCount()
                + ",block:" + snapshot.blockEquationCount()
                + ",shape:" + snapshot.shapeSummary();
    }

    private static void appendPatchSummaryJsonlRecord(
            Path summaryPath,
            Path input,
            Path output,
            Path mathmlManifest,
            DocxMathPatchMain.PatchSummary summary
    ) throws Exception {
        Files.createDirectories(summaryPath.toAbsolutePath().normalize().getParent());
        String record = buildPatchSummaryJsonRecord(input, output, mathmlManifest, summary) + System.lineSeparator();
        Files.writeString(
                summaryPath,
                record,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND
        );
    }

    static String renderPatchSummaryOutput(
            Path input,
            Path output,
            Path mathmlManifest,
            DocxMathPatchMain.PatchSummary summary,
            boolean patchSummaryJsonlStdout
    ) throws Exception {
        if (patchSummaryJsonlStdout) {
            return buildPatchSummaryJsonRecord(input, output, mathmlManifest, summary) + System.lineSeparator();
        }

        String ommlDriftWarning = summary.ommlDriftWarningToken();
        String ommlDriftClass = summary.ommlDriftClass();
        String ommlDriftPair = summary.ommlDriftPair();
        String ommlDriftBundle = summary.ommlDriftBundle();
        StringBuilder rendered = new StringBuilder();
        rendered.append("Input:  ").append(input).append(System.lineSeparator());
        rendered.append("Output: ").append(output).append(System.lineSeparator());
        if (mathmlManifest != null) {
            rendered.append("MathML manifest: ").append(mathmlManifest).append(System.lineSeparator());
        }
        rendered.append("Patch mode: DOCX -> DOCX (native OMML)").append(System.lineSeparator());
        rendered.append("Patch summary: ")
                .append("scanned=").append(summary.totalOccurrences())
                .append(" block=").append(summary.patchedBlocks())
                .append(" inline=").append(summary.patchedInline())
                .append(" native=").append(summary.nativeOmmlUntouched())
                .append(" unresolved=").append(summary.unresolved())
                .append(" skipped_unsafe_inline=").append(summary.skippedUnsafeInlineObjects())
                .append(" skipped_multi=").append(summary.skippedMultiObjectParagraphs())
                .append(" skipped_unknown=").append(summary.skippedUnknownOrAmbiguous())
                .append(" multi_patched=").append(summary.multiObjectPatchedParagraphs())
                .append(" multi_skipped_unsafe=").append(summary.multiObjectSkippedUnsafeParagraphs())
                .append(" multi_skipped_ambiguous=").append(summary.multiObjectSkippedAmbiguousParagraphs())
                .append(" omml_preservation=").append(summary.ommlPreservationToken())
                .append(" omml_before=").append(formatOmmlSnapshot(summary.structureBeforePatch()))
                .append(" omml_after=").append(formatOmmlSnapshot(summary.structureAfterPatch()));
        if (!ommlDriftWarning.isEmpty()) {
            rendered.append(" omml_drift_warning=").append(ommlDriftWarning);
        }
        if (!ommlDriftClass.isEmpty()) {
            rendered.append(" omml_drift_class=").append(ommlDriftClass);
        }
        if (!ommlDriftPair.isEmpty()) {
            rendered.append(" omml_drift_pair=").append(ommlDriftPair);
        }
        if (!ommlDriftBundle.isEmpty()) {
            rendered.append(" omml_drift_bundle=").append(ommlDriftBundle);
        }
        rendered.append(System.lineSeparator());
        rendered.append("Skip breakdown:").append(System.lineSeparator());
        for (PatchSkipReason reason : PatchSkipReason.values()) {
            rendered.append("- ").append(reason.name()).append("=").append(summary.skipBreakdownCount(reason))
                    .append(System.lineSeparator());
        }
        return rendered.toString();
    }
}
