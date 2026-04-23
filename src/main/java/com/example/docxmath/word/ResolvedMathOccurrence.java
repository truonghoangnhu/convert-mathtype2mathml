package com.example.docxmath.word;

record ResolvedMathOccurrence(
        MathOccurrence occurrence,
        String resolvedPartName,
        String ommlXml
) {
}
