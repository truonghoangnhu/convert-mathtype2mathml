package com.example.docxmath;

public enum Subject {
    GENERIC("generic"),
    MATH("math"),
    PHYSICS("physics"),
    CHEMISTRY("chemistry"),
    BIOLOGY("biology");

    private final String cliName;

    Subject(String cliName) {
        this.cliName = cliName;
    }

    public String cliName() {
        return cliName;
    }

    public static Subject fromCliValue(String value) {
        if (value == null || value.isBlank()) {
            return GENERIC;
        }
        String normalized = value.trim().toLowerCase();
        for (Subject subject : values()) {
            if (subject.cliName.equals(normalized)) {
                return subject;
            }
        }
        throw new IllegalArgumentException("Unsupported subject: " + value);
    }
}
