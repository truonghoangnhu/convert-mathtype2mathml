package com.example.docxmath.word;

import java.io.IOException;

public interface MathSidecarRepository {
    String readMathml(String partName) throws IOException;
}
