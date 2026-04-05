package com.example.docxmath;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public final class PhysicsProfile extends GenericProfile {
    private static final List<TextReplacementRule> PHYSICS_RULES = buildRules();

    private static List<TextReplacementRule> buildRules() {
        List<TextReplacementRule> rules = new ArrayList<>();
        rules.addAll(new GenericProfile().genericRules());
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)điện\\s+trờ"), "điện trở"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)thừi\\s+điềm"), "thời điểm"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)kết\\s+quà"), "kết quả"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)khối\\s+lương"), "khối lượng"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)phóng\\s*xạ̣"), "phóng xạ"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)nhiệ̣t"), "nhiệt"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)cần\\s+thiết\\s+đề(?=\\s|$|[\\p{Punct}])"), "cần thiết để"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)được\\s+sử\\s+dụng\\s+đề\\s+xác\\s+định"), "được sử dụng để xác định"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)đồ\\s+dài"), "độ dài"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)thế\\s+tích"), "thể tích"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)biến\\s+đối"), "biến đổi"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)truờng"), "trường"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)chuyền\\s+thành\\s+nhiệt"), "chuyển thành nhiệt"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)\\bmo\\s+l\\s*(?:\\^?\\s*-\\s*1|−\\s*1|⁻\\s*1)\\b"), "mol⁻¹"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)\\bmo\\s+l\\b"), "mol"));
        rules.add(new TextReplacementRule(Pattern.compile("\\bMpa\\b"), "MPa"));
        return List.copyOf(rules);
    }

    private static final SubjectRules RULES = new SubjectRules(
            PHYSICS_RULES,
            false,
            false,
            "physics-diagram",
            "Physics diagram",
            "chem-diagram",
            "Chemical structure diagram"
    );

    @Override
    public String getName() {
        return "physics";
    }

    @Override
    public Subject getSubject() {
        return Subject.PHYSICS;
    }

    @Override
    public SubjectRules getRules() {
        return RULES;
    }
}
