package com.example.docxmath;

import java.nio.file.Path;
import java.text.Normalizer;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public final class SubjectDetector {
    private SubjectDetector() {
    }

    public static Subject detect(Path path) {
        if (path == null || path.getFileName() == null) {
            return Subject.GENERIC;
        }
        return detect(path.getFileName().toString());
    }

    public static Subject detect(String rawName) {
        if (rawName == null || rawName.isBlank()) {
            return Subject.GENERIC;
        }
        String ascii = Normalizer.normalize(rawName, Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "")
                .toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9]+", " ")
                .trim();
        Set<String> tokens = new HashSet<>(Arrays.asList(ascii.split("\\s+")));
        if (tokens.contains("hoa") || tokens.contains("chem") || tokens.contains("chemistry")) {
            return Subject.CHEMISTRY;
        }
        if (tokens.contains("ly") || (tokens.contains("vat") && tokens.contains("ly")) || tokens.contains("phys") || tokens.contains("physics")) {
            return Subject.PHYSICS;
        }
        if (tokens.contains("toan") || tokens.contains("math")) {
            return Subject.MATH;
        }
        if (tokens.contains("sinh") || tokens.contains("bio") || tokens.contains("biology")) {
            return Subject.BIOLOGY;
        }
        if ((tokens.contains("tieng") && tokens.contains("anh")) || tokens.contains("english") || tokens.contains("eng")) {
            return Subject.ENGLISH;
        }
        if (tokens.contains("van") || tokens.contains("literature") || tokens.contains("literary") || tokens.contains("nguvan")
                || (tokens.contains("ngu") && tokens.contains("van"))) {
            return Subject.LITERATURE;
        }
        return Subject.GENERIC;
    }
}
