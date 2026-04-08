package com.example.docxmath;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public final class ChemistryProfile extends GenericProfile {
    private static final List<TextReplacementRule> CHEMISTRY_RULES = buildRules();

    private static List<TextReplacementRule> buildRules() {
        List<TextReplacementRule> rules = new ArrayList<>();
        rules.addAll(new GenericProfile().genericRules());
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)trọng\\s+giai\\s+đoạn"), "Trong giai đoạn"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)\\bT\\s+lag\\b"), "T là"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)có\\s+2\\s+tố\\s+thí\\s+nghiệm"), "Có 2 thí nghiệm"));
        rules.add(new TextReplacementRule(Pattern.compile("Ñaët"), "Đặt"));
        rules.add(new TextReplacementRule(Pattern.compile("taán"), "tấn"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)thế\\s+nhom"), "thế nhóm"));
        rules.add(new TextReplacementRule(Pattern.compile("phaûn"), "phản"));
        rules.add(new TextReplacementRule(Pattern.compile("öùng"), "ứng"));
        rules.add(new TextReplacementRule(Pattern.compile("taïo"), "tạo"));
        rules.add(new TextReplacementRule(Pattern.compile("thaønh"), "thành"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)\\bM\\s*=\\s*29\\b(?=\\s*nên)"), "M = 290"));
        rules.add(new TextReplacementRule(Pattern.compile("(?iu)211\\s*,\\s*8\\s*[x*×]\\s*0\\s*=\\s*8472"), "211,8*40 = 8472"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0ae"), "→"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0e0"), "→"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0de"), "⇒"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0f0"), "⇒"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0ad"), "↑"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0af"), "↓"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0b7"), "•"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0d7"), "·"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf02d"), "−"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0b4"), "×"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf044"), "Δ"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf0b0"), "°"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf061"), "α"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf062"), "β"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf065"), "ε"));
        rules.add(new TextReplacementRule(Pattern.compile("\uf073"), "σ"));
        return List.copyOf(rules);
    }

    private static final SubjectRules RULES = new SubjectRules(
            CHEMISTRY_RULES,
            true,
            true,
            "diagram-asset",
            "Diagram",
            "chem-diagram",
            "Chemical structure diagram"
    );

    @Override
    public String getName() {
        return "chemistry";
    }

    @Override
    public Subject getSubject() {
        return Subject.CHEMISTRY;
    }

    @Override
    public SubjectRules getRules() {
        return RULES;
    }
}
