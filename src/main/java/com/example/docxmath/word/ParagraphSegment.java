package com.example.docxmath.word;

import org.w3c.dom.Node;

public record ParagraphSegment(
        Type type,
        Node paragraphChild,
        MathOccurrence occurrence,
        String ommlXml
) {
    public static ParagraphSegment text(Node paragraphChild) {
        return new ParagraphSegment(Type.TEXT, paragraphChild, null, null);
    }

    public static ParagraphSegment object(Node paragraphChild, MathOccurrence occurrence, String ommlXml) {
        return new ParagraphSegment(Type.OBJECT, paragraphChild, occurrence, ommlXml);
    }

    public enum Type {
        TEXT,
        OBJECT
    }
}
