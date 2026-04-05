package com.example.docxmath;

public final class SubjectProfileFactory {
    private SubjectProfileFactory() {
    }

    public static SubjectProfile create(Subject subject) {
        if (subject == null) {
            return new GenericProfile();
        }
        return switch (subject) {
            case PHYSICS -> new PhysicsProfile();
            case CHEMISTRY -> new ChemistryProfile();
            case MATH -> new MathProfile();
            case BIOLOGY -> new BiologyProfile();
            case GENERIC -> new GenericProfile();
        };
    }
}
