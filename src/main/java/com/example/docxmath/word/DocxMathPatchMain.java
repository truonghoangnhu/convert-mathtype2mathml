package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFDocument;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public final class DocxMathPatchMain {
    private final MathSidecarRepository sidecarRepository;
    private final MathmlNormalizer mathmlNormalizer;
    private final MathmlToOmmlConverter mathmlToOmmlConverter;
    private final OmmlInjector ommlInjector;
    private final DocxWalker walker;

    public DocxMathPatchMain(MathSidecarRepository sidecarRepository) {
        this(
                sidecarRepository,
                new BasicMathmlNormalizer(),
                new XsltMathmlToOmmlConverter(),
                new XmlBeansOmmlInjector(),
                new DocxWalker(new PoiMathSourceDetector())
        );
    }

    DocxMathPatchMain(
            MathSidecarRepository sidecarRepository,
            MathmlNormalizer mathmlNormalizer,
            MathmlToOmmlConverter mathmlToOmmlConverter,
            OmmlInjector ommlInjector,
            DocxWalker walker
    ) {
        this.sidecarRepository = sidecarRepository;
        this.mathmlNormalizer = mathmlNormalizer;
        this.mathmlToOmmlConverter = mathmlToOmmlConverter;
        this.ommlInjector = ommlInjector;
        this.walker = walker;
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
        int unresolved = 0;
        int skippedInline = 0;

        List<MathOccurrence> occurrences = walker.collect(document);
        for (MathOccurrence occurrence : occurrences) {
            totalOccurrences++;
            if (occurrence.sourceType() == MathOccurrence.SourceType.NATIVE_OMML) {
                nativeOmmlUntouched++;
                continue;
            }
            if (!occurrence.blockCandidate()) {
                skippedInline++;
                continue;
            }

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
                unresolved++;
                warn("Unresolved math object: no manifest match for "
                        + String.join(" | ", candidatePartNames.stream().filter(s -> s != null && !s.isBlank()).toList()));
                continue;
            }

            String normalizedMathml = mathmlNormalizer.normalize(mathml);
            String ommlXml = mathmlToOmmlConverter.convert(normalizedMathml);
            if (ommlXml == null || ommlXml.isBlank() || !ommlInjector.inject(occurrence, ommlXml)) {
                unresolved++;
                warn("Failed to inject OMML for " + resolvedPartName);
                continue;
            }
            patchedBlocks++;
        }

        return new PatchSummary(totalOccurrences, patchedBlocks, nativeOmmlUntouched, unresolved, skippedInline);
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

    private static void warn(String message) {
        System.err.println("[docx-omml-patch] " + message);
    }

    public record PatchSummary(
            int totalOccurrences,
            int patchedBlocks,
            int nativeOmmlUntouched,
            int unresolved,
            int skippedInline
    ) {
    }
}
