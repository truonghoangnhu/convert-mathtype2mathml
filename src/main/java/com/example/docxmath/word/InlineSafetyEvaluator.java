package com.example.docxmath.word;

import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public final class InlineSafetyEvaluator {
    public InlinePatchPlan plan(MathOccurrence occurrence) {
        if (occurrence == null) {
            return InlinePatchPlan.skip(
                    null,
                    InlinePatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(
                            PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                            "inline occurrence is missing required run context"
                    )
            );
        }
        if (occurrence.sourceType() == MathOccurrence.SourceType.UNKNOWN) {
            return InlinePatchPlan.skip(
                    occurrence,
                    InlinePatchPlan.SkipReason.UNKNOWN_SOURCE,
                    SkipClassification.of(PatchSkipReason.UNKNOWN_SOURCE_KIND, "source type is unknown")
            );
        }
        if (occurrence.paragraphHasNativeOmml()) {
            return InlinePatchPlan.skip(
                    occurrence,
                    InlinePatchPlan.SkipReason.NATIVE_OMML_PRESENT,
                    SkipClassification.of(PatchSkipReason.NATIVE_OMML_PRESENT, "native OMML already present in paragraph")
            );
        }
        if (occurrence.paragraphObjectCount() != 1) {
            return InlinePatchPlan.skip(
                    occurrence,
                    InlinePatchPlan.SkipReason.MULTI_OBJECT_PARAGRAPH,
                    SkipClassification.of(
                            PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE,
                            "single-inline planner requires exactly one object candidate in paragraph"
                    )
            );
        }
        if (occurrence.runIndex() < 0 || occurrence.runIndex() >= occurrence.paragraph().getRuns().size()) {
            return InlinePatchPlan.skip(
                    occurrence,
                    InlinePatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE, "run span is outside paragraph bounds")
            );
        }

        Node runNode = occurrence.paragraph().getRuns().get(occurrence.runIndex()).getCTR().getDomNode();
        int objectChildren = 0;
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
            if ("object".equals(localName)) {
                objectChildren++;
                continue;
            }
            return InlinePatchPlan.skip(
                    occurrence,
                    InlinePatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(
                            PatchSkipReason.OTHER_UNSAFE_MODEL,
                            "run contains unsupported inline child <" + localName + ">"
                    )
            );
        }
        if (objectChildren != 1) {
            return InlinePatchPlan.skip(
                    occurrence,
                    InlinePatchPlan.SkipReason.AMBIGUOUS_RUN_SPAN,
                    SkipClassification.of(PatchSkipReason.AMBIGUOUS_SEGMENT_SEQUENCE, "inline run must contain exactly one object")
            );
        }
        return InlinePatchPlan.safe(occurrence);
    }
}
