package com.example.docxmath;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public final class MathProfile extends GenericProfile {
    private static final List<TextReplacementRule> MATH_RULES = buildRules();

    private static List<TextReplacementRule> buildRules() {
        List<TextReplacementRule> rules = new ArrayList<>();
        rules.addAll(new GenericProfile().genericRules());
        rules.add(new TextReplacementRule(Pattern.compile("\uf0b7"), "•"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)môt\\s+tả"), "mô tả"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)két\\s+quả"), "kết quả"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)kết\\s+quá"), "kết quả"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)Ta\\s+đó"), "Ta có"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)tí\\s+lệ"), "tỉ lệ"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)Ta\\s+cẩn\\s+tính"), "Ta cần tính"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)đô\\s+thị(?=\\s+của\\s+hàm\\s+số)"), "đồ thị"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)đứng\\s*có"), "đứng có"));
        return List.copyOf(rules);
    }

    private static final SubjectRules RULES = new SubjectRules(
            MATH_RULES,
            false,
            false,
            "diagram-asset",
            "Diagram",
            "chem-diagram",
            "Chemical structure diagram"
    );

    @Override
    public String getName() {
        return "math";
    }

    @Override
    public Subject getSubject() {
        return Subject.MATH;
    }

    @Override
    public SubjectRules getRules() {
        return RULES;
    }
}
