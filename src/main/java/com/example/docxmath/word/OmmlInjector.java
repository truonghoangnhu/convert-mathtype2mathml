package com.example.docxmath.word;

public interface OmmlInjector {
    boolean inject(MathOccurrence occurrence, String ommlXml);
}
