package com.example.docxmath;

import java.util.List;
import java.util.regex.Pattern;

public class GenericProfile implements SubjectProfile {
    private static final List<TextReplacementRule> GENERIC_RULES = List.of(
            new TextReplacementRule(Pattern.compile("(?iu)(?<!\\p{L})(?:vớ(?:ii+)?|vöi(?:i+)?|với{2,})(?!\\p{L})"), "với"),
            new TextReplacementRule(Pattern.compile("(?iu)\\bc\\s+m\\s*(?:²|2)\\b"), "cm²"),
            new TextReplacementRule(Pattern.compile("(?iu)\\bc\\s+m\\s*(?:³|3)\\b"), "cm³"),
            new TextReplacementRule(Pattern.compile("(?iu)\\bm\\s+o\\s+l\\b"), "mol"),
            new TextReplacementRule(Pattern.compile("(?iu)\\bmol\\s*(?:\\^?\\s*-\\s*1|−\\s*1|⁻\\s*1)\\b"), "mol⁻¹"),
            new TextReplacementRule(Pattern.compile("Ð"), "Đ"),
            new TextReplacementRule(Pattern.compile("ð"), "đ")
    );

    private static final SubjectRules RULES = new SubjectRules(
            GENERIC_RULES,
            false,
            false,
            "diagram-asset",
            "Diagram",
            "chem-diagram",
            "Chemical structure diagram"
    );

    @Override
    public String getName() {
        return "generic";
    }

    @Override
    public Subject getSubject() {
        return Subject.GENERIC;
    }

    @Override
    public SubjectRules getRules() {
        return RULES;
    }

    protected List<TextReplacementRule> genericRules() {
        return GENERIC_RULES;
    }
}
