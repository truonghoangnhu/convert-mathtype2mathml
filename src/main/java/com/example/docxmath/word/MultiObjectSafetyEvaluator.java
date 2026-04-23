package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import java.util.ArrayList;
import java.util.IdentityHashMap;
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

        Map<Node, ResolvedMathOccurrence> byObjectNode = new IdentityHashMap<>();
        for (ResolvedMathOccurrence resolvedOccurrence : resolvedOccurrences) {
            byObjectNode.put(resolvedOccurrence.occurrence().sourceNode(), resolvedOccurrence);
        }

        List<ParagraphSegment> segments = new ArrayList<>();
        Node paragraphNode = paragraph.getCTP().getDomNode();
        NodeList children = paragraphNode.getChildNodes();
        int objectSegments = 0;
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() != Node.ELEMENT_NODE) {
                continue;
            }
            String localName = child.getLocalName();
            if (isPreservedParagraphNode(localName)) {
                segments.add(ParagraphSegment.text(child));
                continue;
            }
            if (!"r".equals(localName)) {
                return MultiObjectPatchPlan.skip(
                        paragraph,
                        MultiObjectPatchPlan.SkipReason.UNSUPPORTED_PARAGRAPH_STRUCTURE,
                        SkipClassification.of(
                                PatchSkipReason.UNSUPPORTED_PARAGRAPH_CHILD,
                                "unsupported paragraph child <" + localName + ">"
                        )
                );
            }

            RunScanResult runScanResult = scanRun(child);
            if (runScanResult.skipReason() != null) {
                return MultiObjectPatchPlan.skip(paragraph, runScanResult.skipReason(), runScanResult.classification());
            }
            if (runScanResult.objectNode() == null) {
                segments.add(ParagraphSegment.text(child));
                continue;
            }

            ResolvedMathOccurrence resolvedOccurrence = byObjectNode.remove(runScanResult.objectNode());
            if (resolvedOccurrence == null) {
                return MultiObjectPatchPlan.skip(
                        paragraph,
                        MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                        SkipClassification.of(
                                PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                                "detector could not map object run to a resolved occurrence"
                        )
                );
            }

            segments.add(ParagraphSegment.object(child, resolvedOccurrence.occurrence(), resolvedOccurrence.ommlXml()));
            objectSegments++;
        }

        if (!byObjectNode.isEmpty()) {
            return MultiObjectPatchPlan.skip(
                    paragraph,
                    MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(
                            PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                            "not all resolved objects could be mapped back into paragraph order"
                    )
            );
        }
        if (objectSegments != resolvedOccurrences.size()) {
            return MultiObjectPatchPlan.skip(
                    paragraph,
                    MultiObjectPatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(
                            PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                            "paragraph object sequence is incomplete after safety scan"
                    )
            );
        }
        return MultiObjectPatchPlan.safe(paragraph, segments);
    }

    private static boolean isPreservedParagraphNode(String localName) {
        return "pPr".equals(localName)
                || "bookmarkStart".equals(localName)
                || "bookmarkEnd".equals(localName)
                || "proofErr".equals(localName)
                || "lastRenderedPageBreak".equals(localName);
    }

    private static RunScanResult scanRun(Node runNode) {
        Node objectNode = null;
        boolean sawBenignDrawingOnlyArtifact = false;
        NodeList children = runNode.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() != Node.ELEMENT_NODE) {
                continue;
            }
            String localName = child.getLocalName();
            if ("rPr".equals(localName)) {
                continue;
            }
            if ("drawing".equals(localName)) {
                if (objectNode != null) {
                    return RunScanResult.skip(
                            MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                            SkipClassification.of(PatchSkipReason.DRAWING_IN_RUN, "run contains drawing")
                    );
                }
                if (isBenignStandaloneDrawingRun(runNode)) {
                    sawBenignDrawingOnlyArtifact = true;
                    continue;
                }
                return RunScanResult.skip(
                        MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                        SkipClassification.of(PatchSkipReason.DRAWING_IN_RUN, "run contains drawing")
                );
            }
            if (isIgnorableRunArtifact(localName)) {
                continue;
            }
            if ("object".equals(localName)) {
                if (sawBenignDrawingOnlyArtifact) {
                    return RunScanResult.skip(
                            MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                            SkipClassification.of(PatchSkipReason.DRAWING_IN_RUN, "run mixes drawing with object content")
                    );
                }
                if (objectNode != null) {
                    return RunScanResult.skip(
                            MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                            SkipClassification.of(
                                    PatchSkipReason.MULTIPLE_OBJECTS_IN_SINGLE_RUN,
                                    "run contains multiple object elements"
                            )
                    );
                }
                objectNode = child;
                continue;
            }
            if (objectNode != null) {
                return RunScanResult.skip(
                        MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                        classifyMixedRunElement(localName)
                );
            }
            if (sawBenignDrawingOnlyArtifact) {
                return RunScanResult.skip(
                        MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                        SkipClassification.of(PatchSkipReason.DRAWING_IN_RUN, "run mixes drawing with text content")
                );
            }
            if (!isSafeTextNode(localName)) {
                return RunScanResult.skip(
                        MultiObjectPatchPlan.SkipReason.UNSAFE_RUN_STRUCTURE,
                        classifyUnsupportedRunElement(localName)
                );
            }
        }
        return new RunScanResult(objectNode, null, null);
    }

    private static boolean isBenignStandaloneDrawingRun(Node runNode) {
        NodeList children = runNode.getChildNodes();
        boolean sawDrawing = false;
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() != Node.ELEMENT_NODE) {
                continue;
            }
            String localName = child.getLocalName();
            if ("rPr".equals(localName) || isIgnorableRunArtifact(localName)) {
                continue;
            }
            if ("drawing".equals(localName)) {
                sawDrawing = true;
                continue;
            }
            return false;
        }
        return sawDrawing;
    }

    private static boolean isIgnorableRunArtifact(String localName) {
        return "lastRenderedPageBreak".equals(localName);
    }

    private static SkipClassification classifyMixedRunElement(String localName) {
        if (isSafeTextNode(localName)) {
            return SkipClassification.of(
                    PatchSkipReason.MIXED_OBJECT_AND_TEXT_IN_RUN,
                    "run mixes object content with text element <" + localName + ">"
            );
        }
        if ("drawing".equals(localName)) {
            return SkipClassification.of(PatchSkipReason.DRAWING_IN_RUN, "run contains drawing");
        }
        if ("lastRenderedPageBreak".equals(localName)) {
            return SkipClassification.of(
                    PatchSkipReason.LAST_RENDERED_PAGE_BREAK_IN_RUN,
                    "run contains lastRenderedPageBreak"
            );
        }
        return SkipClassification.of(
                PatchSkipReason.OTHER_UNSAFE_MODEL,
                "run mixes object content with <" + localName + ">"
        );
    }

    private static SkipClassification classifyUnsupportedRunElement(String localName) {
        if ("drawing".equals(localName)) {
            return SkipClassification.of(PatchSkipReason.DRAWING_IN_RUN, "run contains drawing");
        }
        if ("lastRenderedPageBreak".equals(localName)) {
            return SkipClassification.of(
                    PatchSkipReason.LAST_RENDERED_PAGE_BREAK_IN_RUN,
                    "run contains lastRenderedPageBreak"
            );
        }
        return SkipClassification.of(
                PatchSkipReason.OTHER_UNSAFE_MODEL,
                "run contains unsupported element <" + localName + ">"
        );
    }

    private static boolean isSafeTextNode(String localName) {
        return Objects.equals(localName, "t")
                || Objects.equals(localName, "tab")
                || Objects.equals(localName, "br")
                || Objects.equals(localName, "cr");
    }

    private record RunScanResult(
            Node objectNode,
            MultiObjectPatchPlan.SkipReason skipReason,
            SkipClassification classification
    ) {
        private static RunScanResult skip(
                MultiObjectPatchPlan.SkipReason skipReason,
                SkipClassification classification
        ) {
            return new RunScanResult(null, skipReason, classification);
        }
    }
}
