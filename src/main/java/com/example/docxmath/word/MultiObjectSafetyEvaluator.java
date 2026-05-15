package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.w3c.dom.Node;

import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public final class MultiObjectSafetyEvaluator {
    public MultiObjectPatchPlan plan(List<ResolvedMathOccurrence> resolvedOccurrences) {
        if (resolvedOccurrences == null || resolvedOccurrences.size() < 2) {
            return MultiObjectPatchPlan.skip(
                    null,
                    MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(
                            PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                            "paragraph does not contain a deterministic multi-object sequence"
                    )
            );
        }

        XWPFParagraph paragraph = resolvedOccurrences.get(0).occurrence().paragraph();
        if (resolvedOccurrences.stream().anyMatch(entry -> entry.occurrence().paragraphHasNativeOmml())) {
            return MultiObjectPatchPlan.skip(
                    paragraph,
                    MultiObjectPatchPlan.SkipReason.NATIVE_OMML_PRESENT,
                    SkipClassification.of(PatchSkipReason.NATIVE_OMML_PRESENT, "native OMML already present in paragraph")
            );
        }
        if (resolvedOccurrences.stream().anyMatch(entry -> entry.occurrence().sourceType() == MathOccurrence.SourceType.UNKNOWN)) {
            return MultiObjectPatchPlan.skip(
                    paragraph,
                    MultiObjectPatchPlan.SkipReason.UNKNOWN_SOURCE,
                    SkipClassification.of(PatchSkipReason.UNKNOWN_SOURCE_KIND, "at least one object has unknown source type")
            );
        }

        Map<String, ResolvedMathOccurrence> byEmbeddingRelationshipId = new LinkedHashMap<>();
        Map<String, ResolvedMathOccurrence> byPreviewRelationshipId = new LinkedHashMap<>();
        for (ResolvedMathOccurrence resolvedOccurrence : resolvedOccurrences) {
            MathOccurrence occurrence = resolvedOccurrence.occurrence();
            String embeddingRelationshipId = normalized(occurrence.oleRelationshipId());
            if (!embeddingRelationshipId.isEmpty()) {
                if (byEmbeddingRelationshipId.containsKey(embeddingRelationshipId)) {
                    return MultiObjectPatchPlan.skip(
                            paragraph,
                            MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                            SkipClassification.of(
                                    PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                                    "duplicate embedding relationship id " + embeddingRelationshipId + " in paragraph"
                            )
                    );
                }
                byEmbeddingRelationshipId.put(embeddingRelationshipId, resolvedOccurrence);
            }
            String previewRelationshipId = normalized(occurrence.previewRelationshipId());
            if (!previewRelationshipId.isEmpty()) {
                if (byPreviewRelationshipId.containsKey(previewRelationshipId)) {
                    return MultiObjectPatchPlan.skip(
                            paragraph,
                            MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                            SkipClassification.of(
                                    PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                                    "duplicate preview relationship id " + previewRelationshipId + " in paragraph"
                            )
                    );
                }
                byPreviewRelationshipId.put(previewRelationshipId, resolvedOccurrence);
            }
        }

        List<ParagraphSegment> segments = new ArrayList<>();
        Node paragraphNode = paragraph.getCTP().getDomNode();
        Map<ResolvedMathOccurrence, Boolean> matched = new IdentityHashMap<>();
        List<org.w3c.dom.Element> objectNodes = PoiMathSourceDetector.findDescendants(paragraphNode, "object");
        for (Node objectNode : objectNodes) {
            ResolvedMathOccurrence resolvedOccurrence = matchOccurrenceByRelationshipId(
                    objectNode,
                    byEmbeddingRelationshipId,
                    byPreviewRelationshipId
            );
            if (resolvedOccurrence == null) {
                continue;
            }
            matched.put(resolvedOccurrence, true);
            segments.add(ParagraphSegment.object(objectNode, resolvedOccurrence.occurrence(), resolvedOccurrence.ommlXml()));
        }

        if (matched.size() != resolvedOccurrences.size()) {
            return MultiObjectPatchPlan.skip(
                    paragraph,
                    MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(
                            PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                            "not all resolved objects could be mapped by relationship id"
                    )
            );
        }
        return MultiObjectPatchPlan.safe(paragraph, segments);
    }

    private static ResolvedMathOccurrence matchOccurrenceByRelationshipId(
            Node objectNode,
            Map<String, ResolvedMathOccurrence> byEmbeddingRelationshipId,
            Map<String, ResolvedMathOccurrence> byPreviewRelationshipId
    ) {
        String embeddingRelationshipId = normalized(
                PoiMathSourceDetector.attrByLocalName(
                        PoiMathSourceDetector.findFirstDescendant(objectNode, "OLEObject"),
                        "id"
                )
        );
        if (!embeddingRelationshipId.isEmpty()) {
            ResolvedMathOccurrence match = byEmbeddingRelationshipId.remove(embeddingRelationshipId);
            if (match != null) {
                byPreviewRelationshipId.remove(normalized(match.occurrence().previewRelationshipId()));
                return match;
            }
        }

        String previewRelationshipId = normalized(
                PoiMathSourceDetector.attrByLocalName(
                        PoiMathSourceDetector.findFirstDescendant(objectNode, "imagedata"),
                        "id"
                )
        );
        if (!previewRelationshipId.isEmpty()) {
            ResolvedMathOccurrence match = byPreviewRelationshipId.remove(previewRelationshipId);
            if (match != null) {
                byEmbeddingRelationshipId.remove(normalized(match.occurrence().oleRelationshipId()));
                return match;
            }
        }

        return null;
    }

    private static String normalized(String value) {
        return Objects.toString(value, "").trim();
    }
}
