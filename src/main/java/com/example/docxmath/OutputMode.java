package com.example.docxmath;

public enum OutputMode {
    INTERNAL("internal"),
    PUBLISH("publish");

    private final String cliName;

    OutputMode(String cliName) {
        this.cliName = cliName;
    }

    public String cliName() {
        return cliName;
    }

    public static OutputMode fromCliValue(String value) {
        if (value == null || value.isBlank()) {
            return PUBLISH;
        }
        String normalized = value.trim().toLowerCase();
        for (OutputMode mode : values()) {
            if (mode.cliName.equals(normalized)) {
                return mode;
            }
        }
        throw new IllegalArgumentException("Unsupported output mode: " + value);
    }
}
