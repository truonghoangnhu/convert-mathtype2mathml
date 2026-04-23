package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class DocxMathPatchMain {
    public enum LogLevel {
        SUMMARY,
        WARNINGS
    }

    private final MathSidecarRepository sidecarRepository;
    private final MathmlNormalizer mathmlNormalizer;
    private final MathmlToOmmlConverter mathmlToOmmlConverter;
    private final OmmlInjector ommlInjector;
    private final DocxWalker walker;
    private final InlineSafetyEvaluator inlineSafetyEvaluator;
    private final MultiObjectSafetyEvaluator multiObjectSafetyEvaluator;
    private final LogLevel logLevel;

    public DocxMathPatchMain(MathSidecarRepository sidecarRepository) {
        this(sidecarRepository, LogLevel.WARNINGS);
    }

    public DocxMathPatchMain(MathSidecarRepository sidecarRepository, LogLevel logLevel) {
        this(
                sidecarRepository,
                new BasicMathmlNormalizer(),
                new XsltMathmlToOmmlConverter(),
                new XmlBeansOmmlInjector(),
                new DocxWalker(new PoiMathSourceDetector()),
                new InlineSafetyEvaluator(),
                new MultiObjectSafetyEvaluator(),
                logLevel
        );
    }

    DocxMathPatchMain(
            MathSidecarRepository sidecarRepository,
            MathmlNormalizer mathmlNormalizer,
            MathmlToOmmlConverter mathmlToOmmlConverter,
            OmmlInjector ommlInjector,
            DocxWalker walker,
            InlineSafetyEvaluator inlineSafetyEvaluator,
            MultiObjectSafetyEvaluator multiObjectSafetyEvaluator,
            LogLevel logLevel
    ) {
        this.sidecarRepository = sidecarRepository;
        this.mathmlNormalizer = mathmlNormalizer;
        this.mathmlToOmmlConverter = mathmlToOmmlConverter;
        this.ommlInjector = ommlInjector;
        this.walker = walker;
        this.inlineSafetyEvaluator = inlineSafetyEvaluator;
        this.multiObjectSafetyEvaluator = multiObjectSafetyEvaluator;
        this.logLevel = logLevel == null ? LogLevel.WARNINGS : logLevel;
    }

    public PatchSummary patch(Path inputDocx, Path outputDocx) throws IOException {
        Files.createDirectories(outputDocx.toAbsolutePath().normalize().getParent());
        try (InputStream in = Files.newInputStream(inputDocx);
             XWPFDocument document = new XWPFDocument(in)) {
            PatchSummary summary = patch(document);
            try (OutputStream out = Files.newOutputStream(outputDocx)) {
                document.write(out);
            }
            return summary;
        }
    }

    PatchSummary patch(XWPFDocument document) throws IOException {
        int totalOccurrences = 0;
        int nativeOmmlUntouched = 0;
        int patchedBlocks = 0;
        int patchedInline = 0;
        int unresolved = 0;
        int skippedUnsafeInlineObjects = 0;
        int skippedMultiObjectParagraphs = 0;
        int multiObjectPatchedParagraphs = 0;
        int multiObjectSkippedUnsafeParagraphs = 0;
        int multiObjectSkippedAmbiguousParagraphs = 0;
        int skippedUnknownOrAmbiguous = 0;
        EnumMap<PatchSkipReason, Integer> skipBreakdown = zeroedSkipBreakdown();

        List<MathOccurrence> occurrences = walker.collect(document);
        totalOccurrences = occurrences.size();
        for (ParagraphBatch paragraphBatch : groupByParagraph(occurrences)) {
            List<MathOccurrence> paragraphOccurrences = paragraphBatch.occurrences();
            for (MathOccurrence occurrence : paragraphOccurrences) {
                if (occurrence.sourceType() == MathOccurrence.SourceType.NATIVE_OMML) {
                    nativeOmmlUntouched++;
                }
            }

            List<MathOccurrence> objectOccurrences = paragraphOccurrences.stream()
                    .filter(occurrence -> occurrence.sourceType() != MathOccurrence.SourceType.NATIVE_OMML)
                    .toList();
            if (objectOccurrences.isEmpty()) {
                continue;
            }

            if (objectOccurrences.size() > 1) {
                MultiParagraphOutcome outcome = patchMultiObjectParagraph(objectOccurrences);
                patchedInline += outcome.patchedInlineObjects();
                unresolved += outcome.unresolvedOccurrences();
                if (outcome.skippedParagraph()) {
                    skippedMultiObjectParagraphs++;
                    incrementSkipBreakdown(skipBreakdown, outcome.classification());
                    if (outcome.skipReason() != null) {
                        if (outcome.skipReason().category() == MultiObjectPatchPlan.SkipCategory.UNSAFE) {
                            multiObjectSkippedUnsafeParagraphs++;
                        } else {
                            multiObjectSkippedAmbiguousParagraphs++;
                        }
                    }
                }
                if (outcome.patchedParagraph()) {
                    multiObjectPatchedParagraphs++;
                }
                continue;
            }

            SingleOccurrenceOutcome outcome = patchSingleOccurrence(objectOccurrences.get(0));
            patchedBlocks += outcome.patchedBlocks();
            patchedInline += outcome.patchedInline();
            unresolved += outcome.unresolved();
            skippedUnsafeInlineObjects += outcome.skippedUnsafeInlineObjects();
            skippedUnknownOrAmbiguous += outcome.skippedUnknownOrAmbiguous();
            incrementSkipBreakdown(skipBreakdown, outcome.classification());
        }

        return new PatchSummary(
                totalOccurrences,
                patchedBlocks,
                patchedInline,
                nativeOmmlUntouched,
                unresolved,
                skippedUnsafeInlineObjects,
                skippedMultiObjectParagraphs,
                skippedUnknownOrAmbiguous,
                multiObjectPatchedParagraphs,
                multiObjectSkippedUnsafeParagraphs,
                multiObjectSkippedAmbiguousParagraphs,
                buildBreakdownEntries(skipBreakdown)
        );
    }

    private SingleOccurrenceOutcome patchSingleOccurrence(MathOccurrence occurrence) throws IOException {
        if (occurrence.sourceType() == MathOccurrence.SourceType.UNKNOWN) {
            warn("Skipped math object: detector classified occurrence as UNKNOWN");
            return SingleOccurrenceOutcome.skippedUnknown(
                    SkipClassification.of(PatchSkipReason.UNKNOWN_SOURCE_KIND, "detector classified occurrence as UNKNOWN")
            );
        }

        ResolutionResult resolution = resolveOccurrence(occurrence);
        if (resolution.resolvedOccurrence() == null) {
            return SingleOccurrenceOutcome.unresolvedOutcome(resolution.classification());
        }
        ResolvedMathOccurrence resolvedOccurrence = resolution.resolvedOccurrence();

        if (occurrence.blockCandidate()) {
            if (!ommlInjector.inject(occurrence, resolvedOccurrence.ommlXml())) {
                warn("Failed to inject block OMML for " + resolvedOccurrence.resolvedPartName());
                return SingleOccurrenceOutcome.unresolvedOutcome(
                        SkipClassification.of(PatchSkipReason.XML_MUTATION_ROLLBACK, "failed to inject block OMML")
                );
            }
            return SingleOccurrenceOutcome.blockPatched();
        }

        InlinePatchPlan inlinePlan = inlineSafetyEvaluator.plan(occurrence);
        if (!inlinePlan.safe()) {
            warn("Skipped inline math object: " + describeClassification(inlinePlan.classification()));
            return switch (inlinePlan.skipReason()) {
                case NATIVE_OMML_PRESENT -> SingleOccurrenceOutcome.skippedUnsafeInline(inlinePlan.classification());
                case UNKNOWN_SOURCE, AMBIGUOUS_RUN_SPAN -> SingleOccurrenceOutcome.skippedUnknown(inlinePlan.classification());
                case MULTI_OBJECT_PARAGRAPH -> SingleOccurrenceOutcome.skippedUnknown(inlinePlan.classification());
            };
        }

        if (!ommlInjector.inject(occurrence, resolvedOccurrence.ommlXml())) {
            warn("Failed to inject inline OMML for " + resolvedOccurrence.resolvedPartName());
            return SingleOccurrenceOutcome.unresolvedOutcome(
                    SkipClassification.of(PatchSkipReason.XML_MUTATION_ROLLBACK, "failed to inject inline OMML")
            );
        }
        return SingleOccurrenceOutcome.inlinePatched();
    }

    private MultiParagraphOutcome patchMultiObjectParagraph(List<MathOccurrence> occurrences) throws IOException {
        if (occurrences.stream().anyMatch(MathOccurrence::paragraphHasNativeOmml)) {
            warn("Skipped multi-object paragraph: native OMML already present in paragraph");
            return MultiParagraphOutcome.skipped(
                    MultiObjectPatchPlan.SkipReason.NATIVE_OMML_PRESENT,
                    SkipClassification.of(PatchSkipReason.NATIVE_OMML_PRESENT, "native OMML already present in paragraph")
            );
        }

        List<ResolvedMathOccurrence> resolvedOccurrences = new ArrayList<>();
        for (MathOccurrence occurrence : occurrences) {
            if (occurrence.sourceType() == MathOccurrence.SourceType.UNKNOWN) {
                warn("Skipped multi-object paragraph: at least one object has unknown source type");
                return MultiParagraphOutcome.skipped(
                        MultiObjectPatchPlan.SkipReason.UNKNOWN_SOURCE,
                        SkipClassification.of(PatchSkipReason.UNKNOWN_SOURCE_KIND, "at least one object has unknown source type")
                );
            }
            ResolutionResult resolution = resolveOccurrence(occurrence);
            if (resolution.resolvedOccurrence() == null) {
                warn("Skipped multi-object paragraph: at least one object could not be resolved from manifest");
                return MultiParagraphOutcome.skippedWithUnresolved(
                        MultiObjectPatchPlan.SkipReason.UNRESOLVED_MANIFEST,
                        resolution.classification(),
                        1
                );
            }
            resolvedOccurrences.add(resolution.resolvedOccurrence());
        }

        MultiObjectPatchPlan plan = multiObjectSafetyEvaluator.plan(resolvedOccurrences);
        if (!plan.safe()) {
            warn("Skipped multi-object paragraph: " + describeClassification(plan.classification()));
            return MultiParagraphOutcome.skipped(plan.skipReason(), plan.classification());
        }

        if (!ommlInjector.inject(plan)) {
            warn("Skipped multi-object paragraph: XML mutation failed while applying tier 3A patch plan");
            return MultiParagraphOutcome.skippedWithUnresolved(
                    MultiObjectPatchPlan.SkipReason.XML_MUTATION_FAILED,
                    SkipClassification.of(
                            PatchSkipReason.XML_MUTATION_ROLLBACK,
                            "XML mutation failed while applying tier 3A patch plan"
                    ),
                    occurrences.size()
            );
        }
        return MultiParagraphOutcome.patched(occurrences.size());
    }

    private ResolutionResult resolveOccurrence(MathOccurrence occurrence) throws IOException {
        List<String> candidatePartNames = candidatePartNames(occurrence);
        String resolvedPartName = null;
        String mathml = null;
        for (String partName : candidatePartNames) {
            if (partName == null || partName.isBlank()) {
                continue;
            }
            mathml = sidecarRepository.readMathml(partName);
            if (mathml != null && !mathml.isBlank()) {
                resolvedPartName = partName;
                break;
            }
        }
        if (resolvedPartName == null) {
            warn("Unresolved math object: no manifest match for "
                    + String.join(" | ", candidatePartNames.stream().filter(s -> s != null && !s.isBlank()).toList()));
            return ResolutionResult.failure(
                    SkipClassification.of(PatchSkipReason.UNRESOLVED_MANIFEST, "no manifest match for occurrence")
            );
        }

        String normalizedMathml = mathmlNormalizer.normalize(mathml);
        String ommlXml = mathmlToOmmlConverter.convert(normalizedMathml);
        if (ommlXml == null || ommlXml.isBlank()) {
            warn("Failed to convert OMML for " + resolvedPartName);
            return ResolutionResult.failure(
                    SkipClassification.of(PatchSkipReason.OMML_CONVERSION_FAILED, "failed to convert OMML for " + resolvedPartName)
            );
        }
        return ResolutionResult.success(new ResolvedMathOccurrence(occurrence, resolvedPartName, ommlXml));
    }

    private static List<String> candidatePartNames(MathOccurrence occurrence) {
        if (occurrence.sourceType() == MathOccurrence.SourceType.OLE_BIN) {
            return List.of(occurrence.olePartName(), occurrence.previewPartName());
        }
        if (occurrence.sourceType() == MathOccurrence.SourceType.WMF_PREVIEW) {
            return List.of(occurrence.previewPartName(), occurrence.olePartName());
        }
        return List.of(occurrence.olePartName(), occurrence.previewPartName());
    }

    private void warn(String message) {
        if (logLevel != LogLevel.WARNINGS) {
            return;
        }
        System.err.println("[docx-omml-patch] " + message);
    }

    private static String describeClassification(SkipClassification classification) {
        if (classification == null) {
            return PatchSkipReason.OTHER_UNSAFE_MODEL.name();
        }
        return classification.detailOrReason();
    }

    private static List<ParagraphBatch> groupByParagraph(List<MathOccurrence> occurrences) {
        Map<String, ParagraphBatchBuilder> batches = new LinkedHashMap<>();
        for (MathOccurrence occurrence : occurrences) {
            String key = Integer.toHexString(System.identityHashCode(occurrence.paragraph().getCTP().getDomNode()));
            batches.computeIfAbsent(key, ignored -> new ParagraphBatchBuilder(occurrence.paragraph()))
                    .occurrences()
                    .add(occurrence);
        }
        return batches.values().stream()
                .map(builder -> new ParagraphBatch(builder.paragraph(), List.copyOf(builder.occurrences())))
                .toList();
    }

    public record PatchSummary(
            int totalOccurrences,
            int patchedBlocks,
            int patchedInline,
            int nativeOmmlUntouched,
            int unresolved,
            int skippedUnsafeInlineObjects,
            int skippedMultiObjectParagraphs,
            int skippedUnknownOrAmbiguous,
            int multiObjectPatchedParagraphs,
            int multiObjectSkippedUnsafeParagraphs,
            int multiObjectSkippedAmbiguousParagraphs,
            List<SkipBreakdownEntry> skipBreakdown
    ) {
        public int skipBreakdownCount(PatchSkipReason reason) {
            return skipBreakdown.stream()
                    .filter(entry -> entry.reason() == reason)
                    .mapToInt(SkipBreakdownEntry::count)
                    .findFirst()
                    .orElse(0);
        }
    }

    public record SkipBreakdownEntry(PatchSkipReason reason, int count) {
    }

    private record ParagraphBatch(XWPFParagraph paragraph, List<MathOccurrence> occurrences) {
    }

    private record ParagraphBatchBuilder(XWPFParagraph paragraph, List<MathOccurrence> occurrences) {
        private ParagraphBatchBuilder(XWPFParagraph paragraph) {
            this(paragraph, new ArrayList<>());
        }
    }

    private record SingleOccurrenceOutcome(
            int patchedBlocks,
            int patchedInline,
            int unresolved,
            int skippedUnsafeInlineObjects,
            int skippedUnknownOrAmbiguous,
            SkipClassification classification
    ) {
        private static SingleOccurrenceOutcome blockPatched() {
            return new SingleOccurrenceOutcome(1, 0, 0, 0, 0, null);
        }

        private static SingleOccurrenceOutcome inlinePatched() {
            return new SingleOccurrenceOutcome(0, 1, 0, 0, 0, null);
        }

        private static SingleOccurrenceOutcome unresolvedOutcome(SkipClassification classification) {
            return new SingleOccurrenceOutcome(0, 0, 1, 0, 0, classification);
        }

        private static SingleOccurrenceOutcome skippedUnsafeInline(SkipClassification classification) {
            return new SingleOccurrenceOutcome(0, 0, 0, 1, 0, classification);
        }

        private static SingleOccurrenceOutcome skippedUnknown(SkipClassification classification) {
            return new SingleOccurrenceOutcome(0, 0, 0, 0, 1, classification);
        }
    }

    private record MultiParagraphOutcome(
            boolean patchedParagraph,
            int patchedInlineObjects,
            boolean skippedParagraph,
            MultiObjectPatchPlan.SkipReason skipReason,
            SkipClassification classification,
            int unresolvedOccurrences
    ) {
        private static MultiParagraphOutcome patched(int patchedInlineObjects) {
            return new MultiParagraphOutcome(true, patchedInlineObjects, false, null, null, 0);
        }

        private static MultiParagraphOutcome skipped(
                MultiObjectPatchPlan.SkipReason skipReason,
                SkipClassification classification
        ) {
            return new MultiParagraphOutcome(false, 0, true, skipReason, classification, 0);
        }

        private static MultiParagraphOutcome skippedWithUnresolved(
                MultiObjectPatchPlan.SkipReason skipReason,
                SkipClassification classification,
                int unresolvedOccurrences
        ) {
            return new MultiParagraphOutcome(false, 0, true, skipReason, classification, unresolvedOccurrences);
        }
    }

    private record ResolutionResult(
            ResolvedMathOccurrence resolvedOccurrence,
            SkipClassification classification
    ) {
        private static ResolutionResult success(ResolvedMathOccurrence resolvedOccurrence) {
            return new ResolutionResult(resolvedOccurrence, null);
        }

        private static ResolutionResult failure(SkipClassification classification) {
            return new ResolutionResult(null, classification);
        }
    }

    private static EnumMap<PatchSkipReason, Integer> zeroedSkipBreakdown() {
        EnumMap<PatchSkipReason, Integer> breakdown = new EnumMap<>(PatchSkipReason.class);
        for (PatchSkipReason reason : PatchSkipReason.values()) {
            breakdown.put(reason, 0);
        }
        return breakdown;
    }

    private static void incrementSkipBreakdown(
            EnumMap<PatchSkipReason, Integer> breakdown,
            SkipClassification classification
    ) {
        if (breakdown == null || classification == null || classification.reason() == null) {
            return;
        }
        breakdown.merge(classification.reason(), 1, Integer::sum);
    }

    private static List<SkipBreakdownEntry> buildBreakdownEntries(EnumMap<PatchSkipReason, Integer> breakdown) {
        List<SkipBreakdownEntry> entries = new ArrayList<>();
        for (PatchSkipReason reason : PatchSkipReason.values()) {
            entries.add(new SkipBreakdownEntry(reason, breakdown.getOrDefault(reason, 0)));
        }
        return List.copyOf(entries);
    }
}
