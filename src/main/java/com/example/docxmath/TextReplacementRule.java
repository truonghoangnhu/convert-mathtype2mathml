package com.example.docxmath;

import java.util.regex.Pattern;

public record TextReplacementRule(Pattern pattern, String replacement) {
}
