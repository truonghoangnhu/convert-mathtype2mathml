package com.example.docxmath;

public final class BiologyProfile extends GenericProfile {
    @Override
    public String getName() {
        return "biology";
    }

    @Override
    public Subject getSubject() {
        return Subject.BIOLOGY;
    }
}
