package com.example.docxmath;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

final class ReviewWorkspace {
    static final String REVIEW_MANIFEST_FILENAME = "review_override_manifest.json";
    static final String FINAL_EXAM_BUNDLE_FILENAME = "final_exam_bundle.json";
    static final String FINAL_QUESTION_BANK_ITEMS_FILENAME = "final_question_bank_items.json";
    static final String REVIEW_AUDIT_FILENAME = "review_audit.json";

    private static final Set<String> REQUIRED_TRIGGER_CODES = Set.of(
            "canonical_answer_missing",
            "unresolved_reconciliation",
            "answer_source_conflict",
            "summary_vs_local_conflict",
            "summary_vs_solution_conflict",
            "local_vs_solution_conflict",
            "short_answer_value_conflict",
            "boolean_subanswer_conflict",
            "rubric_source_conflict"
    );

    private static final Set<String> SECONDARY_TRIGGER_CODES = Set.of(
            "missing_rubric_source",
            "document_family_ambiguous",
            "summary_mapping_invalid",
            "low_parse_confidence"
    );

    private static final Set<String> APPROVED_REVIEW_STATUSES = Set.of(
            "reviewed_fixed",
            "reviewed_confirmed",
            "auto_accepted"
    );

    private static final Set<String> BLOCKING_REVIEW_STATUSES = Set.of(
            "needs_review",
            "skipped",
            "rejected_from_import"
    );

    private final Path root;
    private final ObjectMapper mapper;
    private final Map<Path, Object> bundleLocks = new ConcurrentHashMap<>();

    private ReviewWorkspace(Path root) {
        this.root = root.toAbsolutePath().normalize();
        this.mapper = new ObjectMapper();
        this.mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        this.mapper.enable(SerializationFeature.INDENT_OUTPUT);
    }

    static ReviewWorkspace open(Path root) {
        return new ReviewWorkspace(root);
    }

    Path root() {
        return root;
    }

    ObjectMapper mapper() {
        return mapper;
    }

    List<Map<String, Object>> bundleSummaries() throws IOException {
        List<Map<String, Object>> summaries = new ArrayList<>();
        for (BundleData bundle : discoverBundles()) {
            summaries.add(bundle.summaryMap());
        }
        summaries.sort(Comparator.comparing(m -> string(m.get("bundle_id"))));
        return summaries;
    }

    Map<String, Object> openSession(String bundleId) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            Map<String, Object> open = new LinkedHashMap<>();
            open.put("bundle", bundle.summaryMap());
            open.put("parser_summary", bundle.parserSummaryMap());
            open.put("queue_summary", bundle.queueSummary(false, false, Collections.emptyMap()));
            open.put("override_manifest", bundle.reviewManifestAsMap());
            return open;
        }
    }

    Map<String, Object> queue(String bundleId, boolean includeSecondary, boolean includeReviewed, Map<String, String> filters) throws IOException {
        return queue(bundleId, includeSecondary, includeReviewed, false, filters);
    }

    Map<String, Object> queue(String bundleId, boolean includeSecondary, boolean includeReviewed, boolean includeAll, Map<String, String> filters) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            return bundle.queueSummary(includeSecondary, includeReviewed, includeAll, filters);
        }
    }

    Map<String, Object> questionDetail(String bundleId, String questionId) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            return bundle.questionDetail(questionId);
        }
    }

    Map<String, Object> sourceHtml(String bundleId) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            return bundle.sourceHtmlPayload();
        }
    }

    Map<String, Object> saveQuestion(String bundleId, String questionId, JsonNode request) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            ObjectNode manifest = bundle.reviewManifest.deepCopy();
            bundle.ensureReviewManifestDefaults(manifest);

            ObjectNode payload = request instanceof ObjectNode ? (ObjectNode) request : mapper.createObjectNode();
            String reviewer = optText(payload, "reviewed_by", optText(payload, "reviewer"));
            if (reviewer.isBlank()) {
                reviewer = optText(manifest, "reviewer", "user");
            }
            String reviewStatus = optText(payload, "review_status", optText(payload, "status", "needs_review"));
            String reviewNote = optText(payload, "review_note", optText(payload, "note", ""));
            JsonNode editsNode = payload.get("edits");
            ObjectNode edits = editsNode instanceof ObjectNode ? ((ObjectNode) editsNode).deepCopy() : mapper.createObjectNode();

            Map<String, Object> question = bundle.questionItem(questionId);
            Map<String, Object> parserQuestion = bundle.parserQuestion(questionId);
            if (question.isEmpty()) {
                throw new IOException("Question not found: " + questionId);
            }

            ObjectNode entry = mapper.createObjectNode();
            entry.put("question_id", questionId);
            entry.put("status", reviewStatus);
            entry.put("review_note", reviewNote);
            entry.put("reviewer", reviewer);
            entry.put("reviewed_by", reviewer);
            entry.put("reviewed_at", Instant.now().toString());
            entry.set("edits", edits);
            entry.set("source_evidence", mapper.valueToTree(buildSourceEvidence(question, parserQuestion, bundle)));

            ArrayNode overrides = manifest.withArray("question_overrides");
            int existingIndex = -1;
            for (int i = 0; i < overrides.size(); i++) {
                JsonNode existing = overrides.get(i);
                if (questionId.equals(string(existing.get("question_id")))) {
                    existingIndex = i;
                    break;
                }
            }
            if (existingIndex >= 0) {
                overrides.set(existingIndex, entry);
            } else {
                overrides.add(entry);
            }
            manifest.put("reviewer", reviewer);
            manifest.put("updated_at", Instant.now().toString());
            updateManifestSummary(manifest, bundle, overrides);
            bundle.writeReviewManifest(manifest);
            bundle.replaceReviewManifest(manifest);

            Map<String, Object> response = new LinkedHashMap<>();
            response.put("saved_override", toMap(entry));
            response.put("override_manifest", toMap(manifest));
            response.put("queue_summary", bundle.queueSummary(false, false, Collections.emptyMap()));
            return response;
        }
    }

    Map<String, Object> batchSaveQuestions(String bundleId, JsonNode request) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            bundle.refreshReviewManifest();
            ObjectNode payload = request instanceof ObjectNode ? (ObjectNode) request : mapper.createObjectNode();
            String reviewStatus = optText(payload, "review_status", optText(payload, "status", ""));
            if (!"reviewed_confirmed".equals(reviewStatus) && !"skipped".equals(reviewStatus)) {
                throw new IOException("Unsupported batch review status: " + reviewStatus);
            }
            String reviewer = optText(payload, "reviewed_by", optText(payload, "reviewer"));
            if (reviewer.isBlank()) {
                reviewer = optText(bundle.reviewManifest, "reviewer", "user");
            }
            String reviewNote = optText(payload, "review_note", optText(payload, "note", ""));

            List<String> requestedIds = new ArrayList<>();
            JsonNode idsNode = payload.get("question_ids");
            if (idsNode != null && idsNode.isArray()) {
                for (JsonNode idNode : idsNode) {
                    String questionId = string(idNode);
                    if (!questionId.isBlank() && !requestedIds.contains(questionId)) {
                        requestedIds.add(questionId);
                    }
                }
            }
            if (requestedIds.isEmpty()) {
                Map<String, Object> blocked = new LinkedHashMap<>();
                blocked.put("allowed", false);
                blocked.put("status", "blocked");
                blocked.put("bundle_id", bundle.bundleId());
                blocked.put("blockers", List.of(Map.of(
                        "code", "empty_batch_selection",
                        "message", "no question_ids were selected"
                )));
                blocked.put("applied_count", 0);
                blocked.put("blocked_count", 0);
                blocked.put("queue_summary", bundle.queueSummary(false, false, Collections.emptyMap()));
                blocked.put("artifacts", Map.of());
                return blocked;
            }

            List<Map<String, Object>> queueItems = bundle.queueItems(true, true, true, Collections.emptyMap());
            Map<String, Map<String, Object>> queueById = new LinkedHashMap<>();
            for (Map<String, Object> item : queueItems) {
                queueById.put(string(item.get("question_id")), item);
            }

            List<Map<String, Object>> blockers = new ArrayList<>();
            List<String> safeQuestionIds = new ArrayList<>();
            for (String questionId : requestedIds) {
                Map<String, Object> item = queueById.get(questionId);
                if (item == null) {
                    blockers.add(Map.of(
                            "question_id", questionId,
                            "code", "question_not_found",
                            "message", "question not found in current bundle"
                    ));
                    continue;
                }
                String currentStatus = string(item.get("review_status"));
                boolean required = Boolean.TRUE.equals(item.get("required"));
                boolean secondary = Boolean.TRUE.equals(item.get("secondary"));
                boolean finalized = "reviewed_fixed".equals(currentStatus)
                        || "reviewed_confirmed".equals(currentStatus)
                        || "skipped".equals(currentStatus)
                        || "rejected_from_import".equals(currentStatus);
                if (finalized) {
                    blockers.add(Map.of(
                            "question_id", questionId,
                            "code", "already_finalized",
                            "message", "question already has a terminal review status"
                    ));
                    continue;
                }
                if ("reviewed_confirmed".equals(reviewStatus)) {
                    if (required || secondary) {
                        blockers.add(Map.of(
                                "question_id", questionId,
                                "code", "not_safe_for_batch_confirm",
                                "message", "question still carries required or secondary review issues"
                        ));
                        continue;
                    }
                } else if ("skipped".equals(reviewStatus)) {
                    if (!(required || secondary)) {
                        blockers.add(Map.of(
                                "question_id", questionId,
                                "code", "not_safe_for_batch_skip",
                                "message", "question does not currently require bulk skip handling"
                        ));
                        continue;
                    }
                }
                safeQuestionIds.add(questionId);
            }

            List<Map<String, Object>> applied = new ArrayList<>();
            for (String questionId : safeQuestionIds) {
                ObjectNode single = mapper.createObjectNode();
                single.put("review_status", reviewStatus);
                single.put("review_note", reviewNote);
                single.put("reviewed_by", reviewer);
                single.put("reviewer", reviewer);
                single.set("edits", mapper.createObjectNode());
                Map<String, Object> saved = saveQuestion(bundleId, questionId, single);
                applied.add(saved);
            }

            bundle.refreshReviewManifest();

            Map<String, Object> response = new LinkedHashMap<>();
            response.put("allowed", !applied.isEmpty());
            response.put("status", blockers.isEmpty() ? "batch_completed" : (applied.isEmpty() ? "blocked" : "batch_partial"));
            response.put("bundle_id", bundle.bundleId());
            response.put("review_status", reviewStatus);
            response.put("reviewed_by", reviewer);
            response.put("review_note", reviewNote);
            response.put("question_ids", requestedIds);
            response.put("applied_count", applied.size());
            response.put("blocked_count", blockers.size());
            response.put("applied_question_ids", safeQuestionIds);
            response.put("blockers", blockers);
            response.put("override_manifest", bundle.reviewManifestAsMap());
            response.put("queue_summary", bundle.queueSummary(false, false, Collections.emptyMap()));
            return response;
        }
    }

    Map<String, Object> getOverrideManifest(String bundleId) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            return bundle.reviewManifestAsMap();
        }
    }

    Map<String, Object> finalizeBundle(String bundleId) throws IOException {
        return finalizeBundle(bundleId, mapper.createObjectNode());
    }

    Map<String, Object> finalizeBundle(String bundleId, JsonNode request) throws IOException {
        BundleData bundle = requireBundle(bundleId);
        synchronized (bundleLock(bundle)) {
            bundle.refreshReviewManifest();
            Map<String, Object> queueSummary = bundle.queueSummary(false, false, Collections.emptyMap());
            ObjectNode payload = request instanceof ObjectNode ? (ObjectNode) request : mapper.createObjectNode();
            ObjectNode manifest = bundle.reviewManifest.deepCopy();
            bundle.ensureReviewManifestDefaults(manifest);
            String finalizer = optText(payload, "finalized_by", optText(payload, "reviewed_by", optText(payload, "reviewer", optText(manifest, "finalized_by", optText(manifest, "reviewer", "user")))));
            if (finalizer.isBlank()) {
                finalizer = "user";
            }
            String finalizeNote = optText(payload, "finalize_note", optText(payload, "note", ""));
            String finalizedAt = Instant.now().toString();
            manifest.put("finalized_by", finalizer);
            manifest.put("finalized_at", finalizedAt);
            manifest.put("finalize_note", finalizeNote);
            if (bundle.questionCount() == 0) {
                Map<String, Object> blocked = new LinkedHashMap<>();
                blocked.put("allowed", false);
                blocked.put("status", "blocked");
                blocked.put("bundle_id", bundle.bundleId());
                blocked.put("blockers", List.of(Map.of(
                        "code", "zero_question_bundle",
                        "message", "bundle contains no questions"
                )));
                blocked.put("queue_summary", queueSummary);
                blocked.put("artifacts", Map.of());
                return blocked;
            }
            int pending = intValue(queueSummary.get("required_pending_count"));
            List<Map<String, Object>> pendingItems = bundle.queueItems(false, false, Collections.emptyMap()).stream()
                    .filter(item -> BLOCKING_REVIEW_STATUSES.contains(string(item.get("review_status"))))
                    .collect(Collectors.toList());
            if (pending > 0) {
                Map<String, Object> blocked = new LinkedHashMap<>();
                blocked.put("allowed", false);
                blocked.put("status", "blocked");
                blocked.put("bundle_id", bundle.bundleId());
                blocked.put("blockers", pendingItems);
                blocked.put("queue_summary", queueSummary);
                blocked.put("artifacts", Map.of());
                return blocked;
            }

            ObjectNode finalQuestionBank = bundle.questionBankItems.deepCopy();
            ObjectNode finalExamBundle = bundle.examBundle.deepCopy();
            ArrayNode items = finalQuestionBank.withArray("items");

            Map<String, ObjectNode> overridesByQuestion = bundle.reviewOverridesByQuestionId(manifest);
            List<Map<String, Object>> auditRecords = new ArrayList<>();
            int overridesApplied = 0;
            int fixedCount = 0;
            int confirmedCount = 0;

            for (int i = 0; i < items.size(); i++) {
                JsonNode node = items.get(i);
                if (!(node instanceof ObjectNode itemNode)) {
                    continue;
                }
                String questionId = string(itemNode.get("item_id"));
                ObjectNode override = overridesByQuestion.get(questionId);
                if (override == null) {
                    continue;
                }

                String reviewStatus = string(override.get("status"), "needs_review");
                if (reviewStatus.equals("reviewed_fixed")) {
                    fixedCount++;
                } else if (reviewStatus.equals("reviewed_confirmed")) {
                    confirmedCount++;
                }
                Map<String, Object> audit = applyOverride(itemNode, override);
                if (audit != null) {
                    overridesApplied++;
                    auditRecords.add(audit);
                }
            }

            updateManifestSummary(manifest, bundle, manifest.withArray("question_overrides"));
            bundle.writeReviewManifest(manifest);
            bundle.replaceReviewManifest(manifest);

            Map<String, Object> finalSummary = summarizeFinalItems(finalQuestionBank);
            updateFinalExamBundle(finalExamBundle, finalSummary, bundle);

            Path finalExamPath = bundle.bundleDir.resolve(FINAL_EXAM_BUNDLE_FILENAME);
            Path finalItemsPath = bundle.bundleDir.resolve(FINAL_QUESTION_BANK_ITEMS_FILENAME);
            Path auditPath = bundle.bundleDir.resolve(REVIEW_AUDIT_FILENAME);
            writeJson(finalExamPath, finalExamBundle);
            writeJson(finalItemsPath, finalQuestionBank);
            writeJson(auditPath, buildAuditRecord(bundle, manifest, finalSummary, auditRecords, overridesApplied, fixedCount, confirmedCount));

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("allowed", true);
            result.put("status", "finalized");
            result.put("bundle_id", bundle.bundleId());
            result.put("finalized_at", finalizedAt);
            result.put("finalized_by", finalizer);
            result.put("finalize_note", finalizeNote);
            result.put("reviewed_by", bundle.reviewedByList());
            result.put("reviewed_by_count", bundle.reviewedByList().size());
            result.put("review_ownership_status", bundle.reviewOwnershipStatus());
            result.put("queue_summary", queueSummary);
            Map<String, Object> artifacts = new LinkedHashMap<>();
            artifacts.put("final_exam_bundle", finalExamPath.toString());
            artifacts.put("final_question_bank_items", finalItemsPath.toString());
            artifacts.put("review_audit", auditPath.toString());
            artifacts.put("review_override_manifest", bundle.reviewManifestPath().toString());
            result.put("artifacts", artifacts);
            result.put("summary", finalSummary);
            return result;
        }
    }

    List<BundleData> discoverBundles() throws IOException {
        if (!Files.exists(root)) {
            return List.of();
        }
        if (isBundleDir(root)) {
            return List.of(loadBundle(root));
        }
        List<BundleData> bundles = new ArrayList<>();
        try (var stream = Files.list(root)) {
            for (Path child : stream.filter(Files::isDirectory).sorted().collect(Collectors.toList())) {
                if (isBundleDir(child)) {
                    bundles.add(loadBundle(child));
                }
            }
        }
        bundles.sort(Comparator.comparing(BundleData::bundleId));
        return bundles;
    }

    private BundleData requireBundle(String bundleId) throws IOException {
        for (BundleData bundle : discoverBundles()) {
            if (bundle.bundleId().equals(bundleId) || bundle.bundleDir.getFileName().toString().equals(bundleId)) {
                return bundle;
            }
        }
        throw new IOException("Bundle not found: " + bundleId + " under " + root);
    }

    private BundleData loadBundle(Path bundleDir) throws IOException {
        return new BundleData(bundleDir);
    }

    private Object bundleLock(BundleData bundle) {
        return bundleLocks.computeIfAbsent(bundle.bundleDir, ignored -> new Object());
    }

    private boolean isBundleDir(Path dir) {
        return Files.exists(dir.resolve("manifest.json")) && Files.exists(dir.resolve("question_bank_items.json"));
    }

    private Map<String, Object> buildSourceEvidence(Map<String, Object> question, Map<String, Object> parserQuestion, BundleData bundle) {
        Map<String, Object> evidence = new LinkedHashMap<>();
        evidence.put("question_id", string(question.get("item_id")));
        evidence.put("question_type", string(question.get("question_type")));
        evidence.put("document_family", string(question.get("document_family")));
        evidence.put("parse_confidence", number(question.get("parse_confidence")));
        evidence.put("source_location", question.get("source_location"));
        evidence.put("parser_warning_codes", question.get("parser_warning_codes"));
        evidence.put("qa_flags", question.get("qa_flags"));
        evidence.put("answer_key", question.get("answer_key"));
        evidence.put("reconciliation", question.get("reconciliation"));
        evidence.put("answer_sources", question.get("answer_sources"));
        evidence.put("answer_summary_entry", bundle.answerSummaryEntryForQuestionNumber(intValue(question.get("question_number"))));
        evidence.put("rubric", question.get("rubric"));
        evidence.put("rubric_detection", question.get("rubric_detection"));
        evidence.put("prompt_preview", question.get("prompt_preview"));
        if (parserQuestion != null && !parserQuestion.isEmpty()) {
            evidence.put("parser_question", parserQuestion);
        }
        evidence.put("bundle_path", bundle.bundleDir.toString());
        return evidence;
    }

    private void updateManifestSummary(ObjectNode manifest, BundleData bundle, ArrayNode overrides) {
        int reviewedFixed = 0;
        int reviewedConfirmed = 0;
        int pending = 0;
        int skipped = 0;
        int rejected = 0;
        Set<String> reviewers = new TreeSet<>();
        for (JsonNode node : overrides) {
            String status = string(node.get("status"));
            String reviewer = string(node.get("reviewed_by"), string(node.get("reviewer")));
            if (!reviewer.isBlank()) {
                reviewers.add(reviewer);
            }
            if (status.equals("reviewed_fixed")) {
                reviewedFixed++;
            } else if (status.equals("reviewed_confirmed")) {
                reviewedConfirmed++;
            } else if (status.equals("skipped")) {
                skipped++;
            } else if (status.equals("rejected_from_import")) {
                rejected++;
            } else {
                pending++;
            }
        }
        ObjectNode summary = manifest.withObject("summary");
        summary.put("question_override_count", overrides.size());
        summary.put("reviewed_fixed_count", reviewedFixed);
        summary.put("reviewed_confirmed_count", reviewedConfirmed);
        summary.put("pending_count", pending);
        summary.put("skipped_count", skipped);
        summary.put("rejected_count", rejected);
        summary.put("bundle_question_count", bundle.questionCount());
        ArrayNode reviewedBy = mapper.createArrayNode();
        for (String reviewer : reviewers) {
            reviewedBy.add(reviewer);
        }
        summary.set("reviewed_by", reviewedBy);
        summary.put("reviewed_by_count", reviewers.size());
        summary.put("review_ownership_status", reviewers.isEmpty() ? "unassigned" : reviewers.size() == 1 ? "single_reviewer" : "multi_reviewer");
        summary.put("primary_reviewer", reviewers.size() == 1 ? reviewers.iterator().next() : "");
        summary.put("finalized_by", string(manifest.get("finalized_by")));
        summary.put("finalized_at", string(manifest.get("finalized_at")));
        summary.put("finalize_note", string(manifest.get("finalize_note")));
    }

    private Map<String, Object> applyOverride(ObjectNode itemNode, ObjectNode override) throws JsonProcessingException {
        ObjectNode edits = override.has("edits") && override.get("edits") instanceof ObjectNode ? (ObjectNode) override.get("edits") : mapper.createObjectNode();
        boolean changed = false;
        List<Map<String, Object>> auditEdits = new ArrayList<>();

        if (edits.has("question_type")) {
            itemNode.put("question_type", string(edits.get("question_type")));
            changed = true;
            auditEdits.add(Map.of("field", "question_type", "value", string(edits.get("question_type"))));
        }

        if (edits.has("answer_key")) {
            JsonNode answerKey = edits.get("answer_key");
            itemNode.set("answer_key", answerKey.deepCopy());
            changed = true;
            auditEdits.add(Map.of("field", "answer_key", "value", toMap(answerKey)));
            appendManualOverrideSource(itemNode, answerKey, override);
            adjustReconciliationForAnswerOverride(itemNode, string(override.get("status"), "reviewed_fixed"), answerKey);
        }

        if (edits.has("accepted_answers")) {
            ArrayNode accepted = edits.get("accepted_answers") instanceof ArrayNode
                    ? ((ArrayNode) edits.get("accepted_answers")).deepCopy()
                    : mapper.createArrayNode();
            ObjectNode answerKey = ensureAnswerKeyObject(itemNode, "short_answer");
            answerKey.set("accepted_answers", accepted);
            itemNode.set("answer_key", answerKey);
            changed = true;
            auditEdits.add(Map.of("field", "accepted_answers", "value", toListOfMaps(accepted)));
            appendManualOverrideSource(itemNode, answerKey, override);
            adjustReconciliationForAnswerOverride(itemNode, string(override.get("status"), "reviewed_fixed"), answerKey);
        }

        if (edits.has("boolean_subanswers")) {
            JsonNode subanswers = edits.get("boolean_subanswers");
            ObjectNode answerKey = ensureAnswerKeyObject(itemNode, "boolean_group");
            answerKey.set("subanswers", subanswers.deepCopy());
            itemNode.set("answer_key", answerKey);
            changed = true;
            auditEdits.add(Map.of("field", "boolean_subanswers", "value", toMap(subanswers)));
            appendManualOverrideSource(itemNode, answerKey, override);
            adjustReconciliationForAnswerOverride(itemNode, string(override.get("status"), "reviewed_fixed"), answerKey);
        }

        if (edits.has("rubric")) {
            JsonNode rubric = edits.get("rubric");
            itemNode.set("rubric", rubric.deepCopy());
            ObjectNode answerKey = ensureAnswerKeyObject(itemNode, "rubric");
            itemNode.set("answer_key", answerKey);
            changed = true;
            auditEdits.add(Map.of("field", "rubric", "value", toMap(rubric)));
            appendManualOverrideSource(itemNode, answerKey, override);
            adjustReconciliationForAnswerOverride(itemNode, string(override.get("status"), "reviewed_fixed"), answerKey);
        }

        if (edits.has("solution")) {
            auditEdits.add(Map.of("field", "solution", "value", toMap(edits.get("solution"))));
            changed = true;
        }

        if (!changed) {
            return Map.of(
                    "question_id", string(itemNode.get("item_id")),
                    "applied", false,
                    "review_status", string(override.get("status")),
                    "note", "override contained no supported edits"
            );
        }

        Map<String, Object> audit = new LinkedHashMap<>();
        audit.put("question_id", string(itemNode.get("item_id")));
        audit.put("applied", true);
        audit.put("review_status", string(override.get("status")));
        audit.put("review_note", string(override.get("review_note")));
        audit.put("reviewed_at", string(override.get("reviewed_at")));
        audit.put("reviewer", string(override.get("reviewer")));
        audit.put("reviewed_by", string(override.get("reviewed_by"), string(override.get("reviewer"))));
        audit.put("edits", auditEdits);
        audit.put("final_answer_key", toMap(itemNode.get("answer_key")));
        audit.put("final_reconciliation", toMap(itemNode.get("reconciliation")));
        audit.put("source_evidence", toMap(override.get("source_evidence")));
        return audit;
    }

    private void adjustReconciliationForAnswerOverride(ObjectNode itemNode, String reviewStatus, JsonNode answerKey) {
        ObjectNode reconciliation = itemNode.has("reconciliation") && itemNode.get("reconciliation") instanceof ObjectNode
                ? (ObjectNode) itemNode.get("reconciliation")
                : mapper.createObjectNode();
        String mode = string(answerKey.get("mode"));
        if (!mode.isBlank() && !mode.equals("none")) {
            reconciliation.put("status", "resolved");
            reconciliation.put("chosen_source", "manual_override");
            ArrayNode notes = reconciliation.withArray("notes");
            boolean hasNote = false;
            for (JsonNode note : notes) {
                if (string(note).contains("manual override applied")) {
                    hasNote = true;
                    break;
                }
            }
            if (!hasNote) {
                notes.add("manual override applied");
            }
            itemNode.set("reconciliation", reconciliation);
        } else if ("reviewed_confirmed".equals(reviewStatus)) {
            reconciliation.put("chosen_source", string(reconciliation.get("chosen_source")));
            itemNode.set("reconciliation", reconciliation);
        }
    }

    private void appendManualOverrideSource(ObjectNode itemNode, JsonNode answerKey, ObjectNode override) {
        if (answerKey == null || answerKey.isNull()) {
            return;
        }
        ArrayNode answerSources = itemNode.has("answer_sources") && itemNode.get("answer_sources") instanceof ArrayNode
                ? (ArrayNode) itemNode.get("answer_sources")
                : mapper.createArrayNode();
        for (JsonNode node : answerSources) {
            if ("manual_override".equals(string(node.get("source")))) {
                itemNode.set("answer_sources", answerSources);
                return;
            }
        }
        ObjectNode source = mapper.createObjectNode();
        source.put("source", "manual_override");
        source.put("confidence", 1.0);
        ObjectNode details = mapper.createObjectNode();
        details.put("mode", string(answerKey.get("mode")));
        details.put("review_override_status", string(override.get("status")));
        details.put("reviewed_at", string(override.get("reviewed_at")));
        source.set("details", details);
        answerSources.add(source);
        itemNode.set("answer_sources", answerSources);
    }

    private ObjectNode ensureAnswerKeyObject(ObjectNode itemNode, String mode) {
        ObjectNode answerKey = itemNode.has("answer_key") && itemNode.get("answer_key") instanceof ObjectNode
                ? (ObjectNode) itemNode.get("answer_key")
                : mapper.createObjectNode();
        answerKey.put("mode", mode);
        return answerKey;
    }

    private Map<String, Object> summarizeFinalItems(ObjectNode finalQuestionBank) throws JsonProcessingException {
        ArrayNode items = finalQuestionBank.withArray("items");
        int missing = 0;
        int unresolved = 0;
        int conflict = 0;
        int reviewedFixed = 0;
        int reviewedConfirmed = 0;
        int autoAccepted = 0;
        for (JsonNode node : items) {
            String mode = string(node.path("answer_key").path("mode"));
            String status = string(node.path("reconciliation").path("status"));
            if ("none".equals(mode) || "blocked".equals(status)) {
                missing++;
            }
            if ("conflict".equals(status) || "needs_review".equals(status) || "blocked".equals(status)) {
                unresolved++;
            }
            if ("conflict".equals(status)) {
                conflict++;
            }
            String reviewStatus = string(node.path("review_status"));
            if (reviewStatus.isBlank()) {
                continue;
            }
            if (reviewStatus.equals("reviewed_fixed")) {
                reviewedFixed++;
            } else if (reviewStatus.equals("reviewed_confirmed")) {
                reviewedConfirmed++;
            } else if (reviewStatus.equals("auto_accepted")) {
                autoAccepted++;
            }
        }
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("question_count", items.size());
        summary.put("canonical_answer_missing_count", missing);
        summary.put("unresolved_reconciliation_count", unresolved);
        summary.put("answer_conflict_count", conflict);
        summary.put("reviewed_fixed_count", reviewedFixed);
        summary.put("reviewed_confirmed_count", reviewedConfirmed);
        summary.put("auto_accepted_count", autoAccepted);
        summary.put("publish_verdict", unresolved > 0 ? "needs_review" : "safe_to_publish");
        return summary;
    }

    private void updateFinalExamBundle(ObjectNode finalExamBundle, Map<String, Object> finalSummary, BundleData bundle) {
        ObjectNode summary = finalExamBundle.withObject("summary");
        summary.put("canonical_answer_missing_count", intValue(finalSummary.get("canonical_answer_missing_count")));
        summary.put("unresolved_object_count", intValue(finalSummary.get("unresolved_reconciliation_count")));
        summary.put("answer_conflict_count", intValue(finalSummary.get("answer_conflict_count")));
        summary.put("parser_question_count", intValue(finalSummary.get("question_count")));
        summary.put("publish_verdict", string(finalSummary.get("publish_verdict")));
        summary.put("document_family", bundle.documentFamily());
        summary.put("document_family_confidence", bundle.documentFamilyConfidence());
        summary.set("document_family_priority_path", mapper.valueToTree(bundle.documentFamilyPriorityPath()));
        summary.set("reviewed_by", mapper.valueToTree(bundle.reviewedByList()));
        summary.put("reviewed_by_count", bundle.reviewedByList().size());
        summary.put("review_ownership_status", bundle.reviewOwnershipStatus());
        summary.put("primary_reviewer", bundle.primaryReviewer());
        summary.put("finalized_by", bundle.finalizedBy());
        summary.put("finalized_at", bundle.finalizedAt());
        summary.put("finalize_note", bundle.finalizeNote());
        finalExamBundle.put("question_item_count", intValue(finalSummary.get("question_count")));

        // Review/finalize can fix answers/rubrics, but the original parser answer_qa_summary
        // reflects pre-review findings. Import readiness is based on final artifacts, so
        // we must reconcile these hard counts with the post-review question_bank_items state.
        ObjectNode answerQa = finalExamBundle.withObject("answer_qa_summary");
        int canonicalMissing = intValue(finalSummary.get("canonical_answer_missing_count"));
        int unresolved = intValue(finalSummary.get("unresolved_reconciliation_count"));
        int conflict = intValue(finalSummary.get("answer_conflict_count"));
        answerQa.put("canonical_answer_missing_count", canonicalMissing);
        answerQa.put("unresolved_reconciliation_count", unresolved);
        answerQa.put("conflict_count", conflict);
        // Conservative: treat hard answer failures as blockers for readiness, but avoid double-counting
        // in downstream readiness logic that already checks canonical_missing/unresolved/conflict.
        answerQa.put("blocker_count", canonicalMissing + conflict);
        if (!answerQa.has("issue_count")) {
            answerQa.put("issue_count", canonicalMissing + unresolved + conflict);
        }
    }

    private Map<String, Object> buildAuditRecord(BundleData bundle, ObjectNode manifest, Map<String, Object> finalSummary, List<Map<String, Object>> auditRecords, int overridesApplied, int fixedCount, int confirmedCount) {
        Map<String, Object> audit = new LinkedHashMap<>();
        audit.put("schema_version", "review_audit.v1");
        audit.put("artifact_type", "review_audit");
        audit.put("bundle_id", bundle.bundleId());
        audit.put("bundle_path", bundle.bundleDir.toString());
        audit.put("reviewed_at", Instant.now().toString());
        audit.put("overrides_applied", overridesApplied);
        audit.put("reviewed_fixed_count", fixedCount);
        audit.put("reviewed_confirmed_count", confirmedCount);
        audit.put("reviewed_by", bundle.reviewedByList());
        audit.put("reviewed_by_count", bundle.reviewedByList().size());
        audit.put("review_ownership_status", bundle.reviewOwnershipStatus());
        audit.put("finalized_by", bundle.finalizedBy());
        audit.put("finalized_at", bundle.finalizedAt());
        audit.put("finalize_note", bundle.finalizeNote());
        audit.put("summary", finalSummary);
        audit.put("review_override_manifest", toMap(manifest));
        audit.put("records", auditRecords);
        return audit;
    }

    private void writeJson(Path path, JsonNode node) throws IOException {
        Files.createDirectories(path.getParent());
        mapper.writeValue(path.toFile(), node);
    }

    private void writeJson(Path path, Object value) throws IOException {
        Files.createDirectories(path.getParent());
        mapper.writeValue(path.toFile(), value);
    }

    private Map<String, Object> toMap(JsonNode node) {
        if (node == null || node.isNull()) {
            return Map.of();
        }
        return mapper.convertValue(node, new TypeReference<Map<String, Object>>() {
        });
    }

    private List<Map<String, Object>> toListOfMaps(JsonNode node) {
        if (node == null || !node.isArray()) {
            return List.of();
        }
        return mapper.convertValue(node, new TypeReference<List<Map<String, Object>>>() {
        });
    }

    private String string(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String string(JsonNode node) {
        return node == null || node.isNull() ? "" : node.asText("");
    }

    private String string(JsonNode node, String defaultValue) {
        String value = string(node);
        return value.isBlank() ? defaultValue : value;
    }

    private int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(string(value));
        } catch (NumberFormatException ex) {
            return 0;
        }
    }

    private double number(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        try {
            return Double.parseDouble(string(value));
        } catch (NumberFormatException ex) {
            return 0.0;
        }
    }

    private String optText(JsonNode node, String field) {
        return optText(node, field, "");
    }

    private String optText(JsonNode node, String field, String defaultValue) {
        if (node == null) {
            return defaultValue;
        }
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? defaultValue : value.asText(defaultValue);
    }

    private static final class BundleData {
        private final Path bundleDir;
        private final ObjectNode manifest;
        private final ObjectNode examBundle;
        private final ObjectNode questionBankItems;
        private final ObjectNode parserReport;
        private final ObjectNode qa;
        private ObjectNode reviewManifest;
        private final ObjectMapper mapper;
        private final Map<String, Map<String, Object>> questionItemsById;
        private final Map<String, Map<String, Object>> parserQuestionsById;
        private final Map<Integer, Map<String, Object>> answerSummaryEntriesByQuestionNumber;

        private BundleData(Path bundleDir) throws IOException {
            this.bundleDir = bundleDir.toAbsolutePath().normalize();
            this.mapper = new ObjectMapper();
            this.mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
            this.mapper.enable(SerializationFeature.INDENT_OUTPUT);
            this.manifest = readObjectNode(bundleDir.resolve("manifest.json"));
            this.examBundle = readObjectNode(bundleDir.resolve("exam_bundle.json"));
            this.questionBankItems = readObjectNode(bundleDir.resolve("question_bank_items.json"));
            this.parserReport = readObjectNode(bundleDir.resolve("parser_report.json"));
            this.qa = readObjectNode(bundleDir.resolve("qa.json"));
            this.reviewManifest = loadReviewManifest();
            this.questionItemsById = indexQuestionItems();
            this.parserQuestionsById = indexParserQuestions();
            this.answerSummaryEntriesByQuestionNumber = indexAnswerSummaryEntries();
        }

        private ObjectNode readObjectNode(Path path) throws IOException {
            if (!Files.exists(path)) {
                return mapper.createObjectNode();
            }
            JsonNode node = mapper.readTree(path.toFile());
            return node instanceof ObjectNode ? (ObjectNode) node : mapper.createObjectNode();
        }

        private ObjectNode loadReviewManifest() throws IOException {
            Path path = reviewManifestPath();
            ObjectNode manifest = Files.exists(path) ? readObjectNode(path) : mapper.createObjectNode();
            ensureReviewManifestDefaults(manifest);
            return manifest;
        }

        private void refreshReviewManifest() throws IOException {
            this.reviewManifest = loadReviewManifest();
        }

        private void replaceReviewManifest(ObjectNode manifest) {
            this.reviewManifest = manifest;
        }

        private Map<String, Map<String, Object>> indexQuestionItems() {
            Map<String, Map<String, Object>> map = new LinkedHashMap<>();
            for (JsonNode item : array(questionBankItems.get("items"))) {
                Map<String, Object> m = mapper.convertValue(item, new TypeReference<Map<String, Object>>() {
                });
                map.put(string(m.get("item_id")), m);
            }
            return map;
        }

        private Map<String, Map<String, Object>> indexParserQuestions() {
            Map<String, Map<String, Object>> map = new LinkedHashMap<>();
            for (JsonNode item : array(parserReport.get("questions"))) {
                Map<String, Object> m = mapper.convertValue(item, new TypeReference<Map<String, Object>>() {
                });
                map.put(string(m.get("item_id")), m);
            }
            return map;
        }

        private Map<Integer, Map<String, Object>> indexAnswerSummaryEntries() {
            Map<Integer, Map<String, Object>> map = new LinkedHashMap<>();
            for (JsonNode item : array(examBundle.path("answer_summary").path("entries"))) {
                Map<String, Object> m = mapper.convertValue(item, new TypeReference<Map<String, Object>>() {
                });
                map.put(intValue(m.get("question_number")), m);
            }
            return map;
        }

        private ArrayNode array(JsonNode node) {
            if (node instanceof ArrayNode array) {
                return array;
            }
            return mapper.createArrayNode();
        }

        String bundleId() {
            String id = string(manifest.get("bundle_id"));
            return id.isBlank() ? bundleDir.getFileName().toString() : id;
        }

        String subject() {
            String subject = string(manifest.get("subject"));
            if (!subject.isBlank()) {
                return subject;
            }
            subject = string(questionBankItems.get("subject"));
            return subject.isBlank() ? "generic" : subject;
        }

        String displayTitle() {
            String title = string(qa.get("title"));
            if (!title.isBlank()) {
                return title;
            }
            String docx = string(manifest.path("source").path("docx_path"));
            if (!docx.isBlank()) {
                return Path.of(docx).getFileName().toString();
            }
            return bundleId();
        }

        int questionCount() {
            return intValue(questionBankItems.get("item_count"), questionItemsById.size());
        }

        double documentFamilyConfidence() {
            return number(questionBankItems.path("items").isArray() ? parserReport.path("summary").path("document_family_confidence") : parserReport.path("summary").path("document_family_confidence"));
        }

        List<String> documentFamilyPriorityPath() {
            JsonNode node = parserReport.path("summary").path("source_priority_path");
            if (!node.isArray()) {
                node = parserReport.path("summary").path("document_family_priority_path");
            }
            List<String> result = new ArrayList<>();
            for (JsonNode value : array(node)) {
                result.add(string(value));
            }
            return result;
        }

        String documentFamily() {
            String family = string(parserReport.path("summary").path("document_family"));
            return family.isBlank() ? string(questionBankItems.path("document_family"), "unknown") : family;
        }

        Map<String, Object> parserSummaryMap() {
            return mapper.convertValue(parserReport.path("summary"), new TypeReference<Map<String, Object>>() {
            });
        }

        Map<String, Object> reviewManifestAsMap() {
            return mapper.convertValue(reviewManifest, new TypeReference<Map<String, Object>>() {
            });
        }

        List<String> reviewedByList() {
            Set<String> reviewers = new TreeSet<>();
            JsonNode summary = reviewManifest.path("summary");
            JsonNode reviewedBy = summary.path("reviewed_by");
            if (reviewedBy.isArray()) {
                for (JsonNode value : reviewedBy) {
                    String reviewer = string(value);
                    if (!reviewer.isBlank()) {
                        reviewers.add(reviewer);
                    }
                }
            }
            if (reviewers.isEmpty()) {
                for (JsonNode override : array(reviewManifest.path("question_overrides"))) {
                    String reviewer = string(override.get("reviewed_by"), string(override.get("reviewer")));
                    if (!reviewer.isBlank()) {
                        reviewers.add(reviewer);
                    }
                }
            }
            return new ArrayList<>(reviewers);
        }

        String reviewOwnershipStatus() {
            String status = string(reviewManifest.path("summary").path("review_ownership_status"));
            if (!status.isBlank()) {
                return status;
            }
            int count = reviewedByList().size();
            if (count <= 0) {
                return "unassigned";
            }
            if (count == 1) {
                return "single_reviewer";
            }
            return "multi_reviewer";
        }

        String primaryReviewer() {
            String primary = string(reviewManifest.path("summary").path("primary_reviewer"));
            if (!primary.isBlank()) {
                return primary;
            }
            List<String> reviewers = reviewedByList();
            return reviewers.size() == 1 ? reviewers.get(0) : "";
        }

        String finalizedBy() {
            String finalizedBy = string(reviewManifest.path("finalized_by"));
            if (!finalizedBy.isBlank()) {
                return finalizedBy;
            }
            return string(reviewManifest.path("summary").path("finalized_by"));
        }

        String finalizedAt() {
            String finalizedAt = string(reviewManifest.path("finalized_at"));
            if (!finalizedAt.isBlank()) {
                return finalizedAt;
            }
            return string(reviewManifest.path("summary").path("finalized_at"));
        }

        String finalizeNote() {
            String note = string(reviewManifest.path("finalize_note"));
            if (!note.isBlank()) {
                return note;
            }
            return string(reviewManifest.path("summary").path("finalize_note"));
        }

        Map<String, Object> answerSummaryEntryForQuestionNumber(int questionNumber) {
            return answerSummaryEntriesByQuestionNumber.getOrDefault(questionNumber, Map.of());
        }

        Map<String, Object> questionItem(String questionId) {
            return questionItemsById.getOrDefault(questionId, Map.of());
        }

        Map<String, Object> parserQuestion(String questionId) {
            return parserQuestionsById.getOrDefault(questionId, Map.of());
        }

        void writeReviewManifest(ObjectNode manifest) throws IOException {
            Files.createDirectories(reviewManifestPath().getParent());
            mapper.writeValue(reviewManifestPath().toFile(), manifest);
            this.reviewManifest = manifest;
        }

        Path reviewManifestPath() {
            return bundleDir.resolve(REVIEW_MANIFEST_FILENAME);
        }

        Path finalExamBundlePath() {
            return bundleDir.resolve(FINAL_EXAM_BUNDLE_FILENAME);
        }

        Path finalQuestionBankItemsPath() {
            return bundleDir.resolve(FINAL_QUESTION_BANK_ITEMS_FILENAME);
        }

        Path sourceHtmlPath() {
            String htmlPath = string(manifest.path("source").path("html_path"));
            if (!htmlPath.isBlank()) {
                return Path.of(htmlPath).toAbsolutePath().normalize();
            }
            String stem = bundleDir.getFileName().toString();
            Path candidate = bundleDir.resolveSibling(stem + "-transpect.html");
            return Files.exists(candidate) ? candidate : candidate;
        }

        Map<String, Object> sourceHtmlPayload() throws IOException {
            Path htmlPath = sourceHtmlPath();
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("bundle_id", bundleId());
            payload.put("display_title", displayTitle());
            payload.put("source_html_path", htmlPath.toString());
            payload.put("source_docx_path", string(manifest.path("source").path("docx_path")));
            payload.put("html_available", Files.exists(htmlPath));
            if (Files.exists(htmlPath)) {
                payload.put("html_content", Files.readString(htmlPath, StandardCharsets.UTF_8));
            } else {
                payload.put("html_content", "<html><body><p><em>Khong tim thay source HTML.</em></p></body></html>");
            }
            return payload;
        }

        Map<String, Object> summaryMap(ReviewWorkspace workspace) throws IOException {
            Map<String, Object> queueSummary = queueSummary(false, false, Collections.emptyMap());
            int zeroQuestionPenalty = questionCount() == 0 ? 1 : 0;
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("bundle_id", bundleId());
        summary.put("display_title", displayTitle());
        summary.put("subject", subject());
        summary.put("bundle_path", bundleDir.toString());
        summary.put("question_count", questionCount());
        summary.put("review_item_count", queueSummary.get("required_pending_count"));
        summary.put("secondary_item_count", queueSummary.get("secondary_pending_count"));
        summary.put("reviewed_count", queueSummary.get("reviewed_count"));
        summary.put("reviewed_fixed_count", queueSummary.get("reviewed_fixed_count"));
        summary.put("reviewed_confirmed_count", queueSummary.get("reviewed_confirmed_count"));
        summary.put("reviewed_by", reviewedByList());
        summary.put("reviewed_by_count", reviewedByList().size());
        summary.put("review_ownership_status", reviewOwnershipStatus());
        summary.put("primary_reviewer", primaryReviewer());
        summary.put("finalized_by", finalizedBy());
        summary.put("finalized_at", finalizedAt());
        summary.put("finalize_note", finalizeNote());
        summary.put("blocker_count", intValue(queueSummary.get("required_pending_count")) + zeroQuestionPenalty);
        summary.put("unresolved_count", intValue(queueSummary.get("required_pending_count")) + zeroQuestionPenalty);
        summary.put("conflict_count", queueSummary.get("conflict_count"));
        summary.put("status_summary", queueSummary.get("status_summary"));
        summary.put("finalized", Files.exists(finalExamBundlePath()) && Files.exists(finalQuestionBankItemsPath()));
            summary.put("issue_codes", queueSummary.get("bundle_issue_codes"));
            summary.put("parser_summary", parserSummaryMap());
            return summary;
        }

        Map<String, Object> summaryMap() throws IOException {
            return summaryMap(null);
        }

        Map<String, Object> queueSummary(boolean includeSecondary, boolean includeReviewed, Map<String, String> filters) throws IOException {
            return queueSummary(includeSecondary, includeReviewed, false, filters);
        }

        Map<String, Object> queueSummary(boolean includeSecondary, boolean includeReviewed, boolean includeAll, Map<String, String> filters) throws IOException {
            List<Map<String, Object>> items = queueItems(includeSecondary, includeReviewed, includeAll, filters);
        int requiredPending = 0;
        int secondaryPending = 0;
        int reviewed = 0;
        int reviewedFixed = 0;
        int reviewedConfirmed = 0;
        int conflict = 0;
        Set<String> issueCodes = new TreeSet<>();
        for (Map<String, Object> item : items) {
            if (Boolean.TRUE.equals(item.get("required")) && isPendingReviewStatus(string(item.get("review_status")))) {
                requiredPending++;
            }
                if (Boolean.TRUE.equals(item.get("secondary")) && isPendingReviewStatus(string(item.get("review_status")))) {
                    secondaryPending++;
            }
            if (APPROVED_REVIEW_STATUSES.contains(string(item.get("review_status")))) {
                reviewed++;
            }
            String reviewStatus = string(item.get("review_status"));
            if ("reviewed_fixed".equals(reviewStatus)) {
                reviewedFixed++;
            } else if ("reviewed_confirmed".equals(reviewStatus)) {
                reviewedConfirmed++;
            }
            if (item.get("issue_codes") instanceof List<?> list) {
                for (Object value : list) {
                    issueCodes.add(string(value));
                    if (string(value).contains("conflict")) {
                        conflict++;
                        }
                    }
                }
            }
            if (questionCount() == 0) {
                issueCodes.add("zero_question_bundle");
            }
            Map<String, Object> summary = new LinkedHashMap<>();
            summary.put("bundle_id", bundleId());
            summary.put("display_title", displayTitle());
            summary.put("subject", subject());
            summary.put("question_count", questionCount());
            summary.put("total_item_count", items.size());
            summary.put("required_pending_count", requiredPending);
            summary.put("secondary_pending_count", secondaryPending);
            summary.put("reviewed_count", reviewed);
            summary.put("reviewed_fixed_count", reviewedFixed);
            summary.put("reviewed_confirmed_count", reviewedConfirmed);
            summary.put("reviewed_by", reviewedByList());
            summary.put("reviewed_by_count", reviewedByList().size());
            summary.put("review_ownership_status", reviewOwnershipStatus());
            summary.put("primary_reviewer", primaryReviewer());
            summary.put("finalized_by", finalizedBy());
            summary.put("finalized_at", finalizedAt());
            summary.put("finalize_note", finalizeNote());
            summary.put("conflict_count", conflict);
            summary.put("bundle_issue_codes", new ArrayList<>(issueCodes));
            summary.put("status_summary", deriveStatusSummary(questionCount(), requiredPending, reviewed));
            summary.put("finalized", Files.exists(finalExamBundlePath()) && Files.exists(finalQuestionBankItemsPath()));
            summary.put("include_secondary", includeSecondary);
            summary.put("include_reviewed", includeReviewed);
            summary.put("include_all", includeAll);
            summary.put("filters", filters);
            summary.put("items", items);
            return summary;
        }

        List<Map<String, Object>> queueItems(boolean includeSecondary, boolean includeReviewed, Map<String, String> filters) throws IOException {
            return queueItems(includeSecondary, includeReviewed, false, filters);
        }

        List<Map<String, Object>> queueItems(boolean includeSecondary, boolean includeReviewed, boolean includeAll, Map<String, String> filters) throws IOException {
            List<Map<String, Object>> items = new ArrayList<>();
            Map<String, ObjectNode> overrides = reviewOverridesByQuestionId(reviewManifest);
            String filter = filters.getOrDefault("filter", "all");
            String reviewStatusFilter = filters.getOrDefault("reviewStatus", "");
            String questionType = filters.getOrDefault("questionType", "");
            String family = filters.getOrDefault("family", "");
            String search = filters.getOrDefault("q", "");
            boolean showReviewed = includeReviewed || includeAll || "all".equalsIgnoreCase(filters.getOrDefault("status", ""));

            for (Map<String, Object> item : questionItemsById.values()) {
                String questionId = string(item.get("item_id"));
                Map<String, Object> parserItem = parserQuestionsById.getOrDefault(questionId, Map.of());
                ObjectNode override = overrides.get(questionId);
                List<String> issueCodes = deriveIssueCodes(item, parserItem, bundleIssueCodes());
                boolean required = hasAny(issueCodes, REQUIRED_TRIGGER_CODES) || parserNeedsReview(parserItem) || parserConflict(parserItem);
                boolean secondary = hasAny(issueCodes, SECONDARY_TRIGGER_CODES);
                String reviewStatus = override != null ? string(override.get("status"), "needs_review") : (required ? "needs_review" : "auto_accepted");
                boolean approved = APPROVED_REVIEW_STATUSES.contains(reviewStatus);
                if (!includeAll) {
                    if (approved && !showReviewed) {
                        continue;
                    }
                    if (!required && !(includeSecondary && secondary)) {
                        continue;
                    }
                }
                if (!matchesFilter(item, issueCodes, filter, questionType, family, search)) {
                    continue;
                }
                if (reviewStatusFilter != null && !reviewStatusFilter.isBlank() && !reviewStatusFilter.equalsIgnoreCase("all") && !reviewStatusFilter.equalsIgnoreCase(reviewStatus)) {
                    continue;
                }
                Map<String, Object> queueItem = new LinkedHashMap<>();
                queueItem.put("question_id", questionId);
                queueItem.put("question_number", intValue(item.get("question_number")));
                queueItem.put("display_label", "Câu " + intValue(item.get("question_number")));
                queueItem.put("question_type", string(item.get("question_type")));
                queueItem.put("document_family", string(item.get("document_family")));
                queueItem.put("document_family_confidence", number(item.get("document_family_confidence")));
                queueItem.put("parse_confidence", number(item.get("parse_confidence")));
                queueItem.put("parser_status", parserStatus(parserItem));
                queueItem.put("chosen_source", parserChosenSource(parserItem));
                queueItem.put("review_status", reviewStatus);
                queueItem.put("review_note", override == null ? "" : string(override.get("review_note")));
                queueItem.put("reviewed_at", override == null ? "" : string(override.get("reviewed_at")));
                queueItem.put("reviewer", override == null ? "" : string(override.get("reviewer")));
                queueItem.put("reviewed_by", override == null ? "" : string(override.get("reviewed_by"), string(override.get("reviewer"))));
                queueItem.put("required", required);
                queueItem.put("secondary", secondary);
                queueItem.put("problematic", required || secondary);
                queueItem.put("issue_codes", issueCodes);
                queueItem.put("parser_warning_codes", listOfStrings(item.get("parser_warning_codes")));
                queueItem.put("qa_flags", listOfStrings(item.get("qa_flags")));
                queueItem.put("asset_count", intValue(item.get("asset_count")));
                queueItem.put("math_fragment_count", intValue(item.get("math_fragment_count")));
                queueItem.put("has_math", intValue(item.get("math_fragment_count")) > 0);
                queueItem.put("has_image", intValue(item.get("asset_count")) > 0);
                queueItem.put("asset_roles", listOfStrings(item.get("asset_roles")));
                queueItem.put("prompt_preview", string(item.get("prompt_preview")));
                queueItem.put("source_line", intValue(itemToMap(item).getOrDefault("source_location", Map.of()) instanceof Map<?, ?> sl ? ((Map<?, ?>) sl).get("line") : 0));
                queueItem.put("answer_key_mode", string(itemToMap(item).getOrDefault("answer_key", Map.of()) instanceof Map<?, ?> ak ? ((Map<?, ?>) ak).get("mode") : ""));
                queueItem.put("answer_key_preview", answerKeyPreview(itemToMap(item).get("answer_key")));
                queueItem.put("answer_sources", item.get("answer_sources"));
                items.add(queueItem);
            }
            items.sort(Comparator.comparingInt(m -> intValue(m.get("question_number"))));
            return items;
        }

        Map<String, Object> questionDetail(String questionId) throws IOException {
            Map<String, Object> item = questionItemsById.get(questionId);
            if (item == null) {
                return Map.of("error", "question not found", "question_id", questionId);
            }
            Map<String, Object> parserItem = parserQuestionsById.getOrDefault(questionId, Map.of());
            ObjectNode override = reviewOverridesByQuestionId(reviewManifest).get(questionId);
            int questionNumber = intValue(item.get("question_number"));
            Map<String, Object> answerSummaryEntry = answerSummaryEntriesByQuestionNumber.getOrDefault(questionNumber, Map.of());
            Map<String, Object> detail = new LinkedHashMap<>();
            detail.put("bundle_id", bundleId());
            detail.put("bundle_title", displayTitle());
            detail.put("question_id", questionId);
            detail.put("display_label", "Câu " + questionNumber);
            detail.put("question_number", questionNumber);
            detail.put("question_type", string(item.get("question_type")));
            detail.put("document_family", string(item.get("document_family")));
            detail.put("document_family_confidence", number(item.get("document_family_confidence")));
            detail.put("parse_confidence", number(item.get("parse_confidence")));
            detail.put("asset_count", intValue(item.get("asset_count")));
            detail.put("math_fragment_count", intValue(item.get("math_fragment_count")));
            detail.put("asset_roles", listOfStrings(item.get("asset_roles")));
            detail.put("prompt_preview", string(item.get("prompt_preview")));
            detail.put("source_line", intValue(itemToMap(item).getOrDefault("source_location", Map.of()) instanceof Map<?, ?> sl ? ((Map<?, ?>) sl).get("line") : 0));
            detail.put("source_html_excerpt", sourceHtmlExcerpt(questionNumber, detailLine(item, parserItem), questionId));
            detail.put("answer_html_excerpt", answerHtmlExcerpt(questionNumber, detailLine(item, parserItem), item, parserItem));
            detail.put("rubric_html_excerpt", rubricHtmlExcerpt(questionNumber, detailLine(item, parserItem), item, parserItem));
            detail.put("question_item", item);
            detail.put("parser_question", parserItem);
            detail.put("answer_summary_entry", answerSummaryEntry);
            detail.put("answer_detection", item.get("answer_detection"));
            detail.put("answer_sources", item.get("answer_sources"));
            detail.put("reconciliation", item.get("reconciliation"));
            detail.put("rubric_detection", item.get("rubric_detection"));
            detail.put("qa_flags", item.get("qa_flags"));
            detail.put("parser_warning_codes", item.get("parser_warning_codes"));
            detail.put("issue_codes", deriveIssueCodes(item, parserItem, bundleIssueCodes()));
            detail.put("override_entry", override == null ? Map.of() : toMap(override));
            detail.put("review_status", override == null ? "" : string(override.get("status"), "needs_review"));
            detail.put("review_note", override == null ? "" : string(override.get("review_note")));
            detail.put("reviewer", override == null ? "" : string(override.get("reviewer")));
            detail.put("reviewed_by", override == null ? "" : string(override.get("reviewed_by"), string(override.get("reviewer"))));
            detail.put("reviewed_at", override == null ? "" : string(override.get("reviewed_at")));
            detail.put("reviewed_by_all", reviewedByList());
            detail.put("reviewed_by_count", reviewedByList().size());
            detail.put("review_ownership_status", reviewOwnershipStatus());
            detail.put("primary_reviewer", primaryReviewer());
            detail.put("finalized_by", finalizedBy());
            detail.put("finalized_at", finalizedAt());
            detail.put("finalize_note", finalizeNote());
            detail.put("review_manifest", reviewManifestAsMap());
            detail.put("prev_question_id", adjacentQuestionId(questionNumber, -1));
            detail.put("next_question_id", adjacentQuestionId(questionNumber, +1));
            detail.put("source_html_path", sourceHtmlPath().toString());
            return detail;
        }

        private int detailLine(Map<String, Object> item, Map<String, Object> parserItem) {
            Object sourceLocation = item.get("source_location");
            if (sourceLocation instanceof Map<?, ?> map) {
                return intValue(map.get("line"));
            }
            if (parserItem != null) {
                Object parserSourceLocation = parserItem.get("source_location");
                if (parserSourceLocation instanceof Map<?, ?> map) {
                    return intValue(map.get("line"));
                }
            }
            return 0;
        }

        private String adjacentQuestionId(int questionNumber, int delta) {
            int target = questionNumber + delta;
            for (Map<String, Object> item : questionItemsById.values()) {
                if (intValue(item.get("question_number")) == target) {
                    return string(item.get("item_id"));
                }
            }
            return "";
        }

        private String sourceHtmlExcerpt(int questionNumber, int line, String questionId) throws IOException {
            Path htmlPath = sourceHtmlPath();
            if (!Files.exists(htmlPath)) {
                return "<p><em>Source HTML not available.</em></p>";
            }
            List<String> lines = Files.readAllLines(htmlPath, StandardCharsets.UTF_8);
            if (lines.isEmpty()) {
                return "<p><em>Source HTML empty.</em></p>";
            }
            int idx = clampIndex(line > 0 ? line - 1 : 0, lines.size());
            int start = Math.max(0, idx - 1);
            int end = Math.min(lines.size(), idx + 2);
            String snippet = String.join("\n", lines.subList(start, end));
            if (snippet.isBlank()) {
                snippet = lines.get(idx);
            }
            return snippet;
        }

        private String answerHtmlExcerpt(int questionNumber, int line, Map<String, Object> item, Map<String, Object> parserItem) throws IOException {
            String anchor = string(itemToMap(item).getOrDefault("answer_detection", Map.of()) instanceof Map<?, ?> ad ? ((Map<?, ?>) ad).get("anchored_solution_anchor") : "");
            if (anchor.isBlank() && parserItem != null) {
                Object parserAnswerDetection = parserItem.get("answer_detection");
                if (parserAnswerDetection instanceof Map<?, ?> ad) {
                    anchor = string(ad.get("anchored_solution_anchor"));
                }
            }
            return excerptForNeedle(line, anchor, Set.of("ĐÁP ÁN", "ĐÁP SỐ", "HƯỚNG DẪN GIẢI", "Câu " + questionNumber));
        }

        private String rubricHtmlExcerpt(int questionNumber, int line, Map<String, Object> item, Map<String, Object> parserItem) throws IOException {
            String anchor = string(itemToMap(item).getOrDefault("answer_detection", Map.of()) instanceof Map<?, ?> ad ? ((Map<?, ?>) ad).get("anchored_rubric_anchor") : "");
            if (anchor.isBlank() && parserItem != null) {
                Object parserAnswerDetection = parserItem.get("answer_detection");
                if (parserAnswerDetection instanceof Map<?, ?> ad) {
                    anchor = string(ad.get("anchored_rubric_anchor"));
                }
            }
            return excerptForNeedle(line, anchor, Set.of("HƯỚNG DẪN CHẤM", "ĐÁP ÁN", "Câu " + questionNumber));
        }

        private String excerptForNeedle(int baseLine, String anchor, Set<String> fallbackNeedles) throws IOException {
            Path htmlPath = sourceHtmlPath();
            if (!Files.exists(htmlPath)) {
                return "";
            }
            List<String> lines = Files.readAllLines(htmlPath, StandardCharsets.UTF_8);
            if (lines.isEmpty()) {
                return "";
            }
            int startIndex = clampIndex(baseLine > 0 ? baseLine - 1 : 0, lines.size());
            if (!anchor.isBlank()) {
                for (int i = startIndex; i < lines.size(); i++) {
                    if (lines.get(i).contains(anchor)) {
                        return lines.get(i);
                    }
                }
            }
            for (String needle : fallbackNeedles) {
                for (int i = startIndex; i < lines.size(); i++) {
                    if (lines.get(i).contains(needle)) {
                        return lines.get(i);
                    }
                }
            }
            int end = Math.min(lines.size(), startIndex + 1);
            return String.join("\n", lines.subList(startIndex, end));
        }

        private int clampIndex(int index, int size) {
            if (size <= 0) {
                return 0;
            }
            return Math.max(0, Math.min(index, size - 1));
        }

        private Map<String, Object> itemToMap(Map<String, Object> item) {
            return item == null ? Map.of() : item;
        }

        private List<String> bundleIssueCodes() {
            List<String> codes = new ArrayList<>();
            JsonNode issueCode = parserReport.path("summary").path("issue_code");
            if (!issueCode.isMissingNode() && !issueCode.asText("").isBlank()) {
                codes.add(issueCode.asText());
            }
            JsonNode warnings = parserReport.path("warnings");
            if (warnings.isArray()) {
                for (JsonNode warning : warnings) {
                    // Only treat bundle-level warnings (no question_id) as bundle issues.
                    // Per-question warnings are already surfaced via parser_question.warning_codes and
                    // question_bank_item.parser_warning_codes; adding them here would incorrectly
                    // mark every item as required for review.
                    String qid = string(warning.path("question_id"));
                    if (!qid.isBlank()) {
                        continue;
                    }
                    String code = string(warning.path("code"));
                    if (!code.isBlank()) {
                        codes.add(code);
                    }
                }
            }
            return codes;
        }

        private List<String> listOfStrings(Object value) {
            if (value instanceof List<?> list) {
                List<String> result = new ArrayList<>(list.size());
                for (Object item : list) {
                    result.add(string(item));
                }
                return result;
            }
            if (value instanceof JsonNode node && node.isArray()) {
                List<String> result = new ArrayList<>();
                for (JsonNode item : node) {
                    result.add(string(item));
                }
                return result;
            }
            return List.of();
        }

        private int intValue(JsonNode node, int defaultValue) {
            if (node == null || node.isNull()) {
                return defaultValue;
            }
            if (node.isNumber()) {
                return node.intValue();
            }
            try {
                return Integer.parseInt(node.asText());
            } catch (Exception ex) {
                return defaultValue;
            }
        }

        private boolean parserNeedsReview(Map<String, Object> parserItem) {
            String status = reconciliationStatus(parserItem);
            return "needs_review".equals(status);
        }

        private boolean parserConflict(Map<String, Object> parserItem) {
            return "conflict".equals(reconciliationStatus(parserItem));
        }

        private String reconciliationStatus(Map<String, Object> parserItem) {
            Object reconciliation = parserItem.get("reconciliation");
            if (reconciliation instanceof Map<?, ?> map) {
                return string(map.get("status"));
            }
            return "";
        }

        private String parserStatus(Map<String, Object> parserItem) {
            return reconciliationStatus(parserItem);
        }

        private String parserChosenSource(Map<String, Object> parserItem) {
            Object reconciliation = parserItem.get("reconciliation");
            if (reconciliation instanceof Map<?, ?> map) {
                return string(map.get("chosen_source"));
            }
            return "";
        }

        private List<String> deriveIssueCodes(Map<String, Object> item, Map<String, Object> parserItem, List<String> bundleIssues) {
            Set<String> codes = new TreeSet<>();
            codes.addAll(listOfStrings(item.get("qa_flags")));
            codes.addAll(listOfStrings(item.get("parser_warning_codes")));
            codes.addAll(bundleIssues);
            String status = reconciliationStatus(parserItem);
            if (status.equals("blocked")) {
                codes.add("canonical_answer_missing");
            } else if (status.equals("conflict")) {
                codes.add("answer_source_conflict");
                codes.add("unresolved_reconciliation");
            } else if (status.equals("needs_review")) {
                codes.add("unresolved_reconciliation");
            }
            String questionType = string(item.get("question_type"));
            String answerKeyMode = string(itemToMap(item).getOrDefault("answer_key", Map.of()) instanceof Map<?, ?> ak ? ((Map<?, ?>) ak).get("mode") : "");
            if ("essay".equals(questionType) && answerKeyMode.equals("none")) {
                codes.add("missing_rubric_source");
            }
            double parseConfidence = number(item.get("parse_confidence"));
            if (parseConfidence > 0.0 && parseConfidence < 0.6) {
                codes.add("low_parse_confidence");
            }
            if (status.isBlank() && answerKeyMode.equals("none")) {
                codes.add("canonical_answer_missing");
            }
            if (item.get("answer_detection") instanceof Map<?, ?> detection) {
                if (string(detection.get("document_family")).equals("unknown")) {
                    codes.add("document_family_ambiguous");
                }
            }
            if (item.get("reconciliation") instanceof Map<?, ?> reconciliation) {
                String notes = string(reconciliation.get("notes"));
                if (notes.contains("conflict")) {
                    codes.add("answer_source_conflict");
                }
            }
            return new ArrayList<>(codes);
        }

        private boolean hasAny(List<String> values, Set<String> candidates) {
            for (String value : values) {
                if (candidates.contains(value)) {
                    return true;
                }
            }
            return false;
        }

        private boolean matchesFilter(Map<String, Object> item, List<String> issueCodes, String filter, String questionTypeFilter, String familyFilter, String search) {
            if (questionTypeFilter != null && !questionTypeFilter.isBlank() && !string(item.get("question_type")).equalsIgnoreCase(questionTypeFilter)) {
                return false;
            }
            if (familyFilter != null && !familyFilter.isBlank() && !string(item.get("document_family")).equalsIgnoreCase(familyFilter)) {
                return false;
            }
            if (search != null && !search.isBlank()) {
                String text = (string(item.get("prompt_preview")) + " " + string(item.get("item_id")) + " " + string(item.get("question_number"))).toLowerCase(Locale.ROOT);
                if (!text.contains(search.toLowerCase(Locale.ROOT))) {
                    return false;
                }
            }
            if (filter == null || filter.isBlank() || filter.equalsIgnoreCase("all")) {
                return true;
            }
            String normalizedFilter = filter.toLowerCase(Locale.ROOT);
            return switch (normalizedFilter) {
                case "missing-answer" -> issueCodes.contains("canonical_answer_missing");
                case "unresolved" -> issueCodes.contains("unresolved_reconciliation") || issueCodes.contains("canonical_answer_missing");
                case "conflict" -> issueCodes.contains("answer_source_conflict") || issueCodes.contains("summary_vs_local_conflict") || issueCodes.contains("summary_vs_solution_conflict") || issueCodes.contains("local_vs_solution_conflict");
                case "missing-rubric" -> issueCodes.contains("missing_rubric_source") || issueCodes.contains("rubric_source_conflict");
                case "low-confidence" -> issueCodes.contains("low_parse_confidence");
                case "with-math" -> intValue(item.get("math_fragment_count")) > 0;
                case "with-image" -> intValue(item.get("asset_count")) > 0;
                default -> true;
            };
        }

        private String answerKeyPreview(Object value) {
            if (!(value instanceof Map<?, ?> map)) {
                return "";
            }
            String mode = string(map.get("mode"));
            if (mode.equals("single_choice")) {
                return string(map.get("value"));
            }
            if (mode.equals("boolean_group")) {
                return string(map.get("subanswers"));
            }
            if (mode.equals("short_answer")) {
                Object accepted = map.get("accepted_answers");
                if (accepted instanceof List<?> list && !list.isEmpty()) {
                    Object first = list.get(0);
                    if (first instanceof Map<?, ?> firstMap) {
                        return string(firstMap.get("normalized"), string(firstMap.get("raw")));
                    }
                    return string(first);
                }
            }
            return mode;
        }

        private ObjectNode ensureReviewManifestDefaults(ObjectNode manifest) {
            if (!manifest.has("schema_version")) {
                manifest.put("schema_version", "review_override.v1");
            }
            if (!manifest.has("artifact_type")) {
                manifest.put("artifact_type", "review_override_manifest");
            }
            if (!manifest.has("bundle_id")) {
                manifest.put("bundle_id", bundleId());
            }
            if (!manifest.has("bundle_path")) {
                manifest.put("bundle_path", bundleDir.toString());
            }
            if (!manifest.has("reviewer")) {
                manifest.put("reviewer", "user");
            }
            if (!manifest.has("created_at")) {
                manifest.put("created_at", Instant.now().toString());
            }
            if (!manifest.has("updated_at")) {
                manifest.put("updated_at", Instant.now().toString());
            }
            if (!(manifest.get("question_overrides") instanceof ArrayNode)) {
                manifest.set("question_overrides", mapper.createArrayNode());
            }
            if (!(manifest.get("summary") instanceof ObjectNode)) {
                manifest.set("summary", mapper.createObjectNode());
            }
            return manifest;
        }

        private Map<String, ObjectNode> reviewOverridesByQuestionId(ObjectNode manifest) {
            Map<String, ObjectNode> map = new LinkedHashMap<>();
            if (!(manifest.get("question_overrides") instanceof ArrayNode overrides)) {
                return map;
            }
            for (JsonNode node : overrides) {
                String questionId = string(node.get("question_id"));
                if (!questionId.isBlank() && node instanceof ObjectNode objectNode) {
                    map.put(questionId, objectNode);
                }
            }
            return map;
        }

        private boolean isPendingReviewStatus(String status) {
            return BLOCKING_REVIEW_STATUSES.contains(status) || status.isBlank();
        }

        private String deriveStatusSummary(int questionCount, int requiredPending, int reviewed) {
            if (questionCount <= 0) {
                return "blocked";
            }
            if (Files.exists(finalExamBundlePath()) && Files.exists(finalQuestionBankItemsPath())) {
                return "finalized";
            }
            if (requiredPending > 0) {
                return "needs_review";
            }
            if (reviewed > 0) {
                return "ready_to_finalize";
            }
            return "ready_to_review";
        }

        private Map<String, Object> toMap(ObjectNode node) {
            return mapper.convertValue(node, new TypeReference<Map<String, Object>>() {
            });
        }

        private int intValue(Object value) {
            if (value instanceof Number number) {
                return number.intValue();
            }
            try {
                return Integer.parseInt(string(value));
            } catch (Exception ex) {
                return 0;
            }
        }

        private double number(Object value) {
            if (value instanceof Number number) {
                return number.doubleValue();
            }
            try {
                return Double.parseDouble(string(value));
            } catch (Exception ex) {
                return 0.0;
            }
        }

        private String string(Object value) {
            if (value == null) {
                return "";
            }
            if (value instanceof JsonNode node) {
                return node.isNull() ? "" : node.asText("");
            }
            return String.valueOf(value);
        }

        private String string(Object value, String defaultValue) {
            String text = string(value);
            return text.isBlank() ? defaultValue : text;
        }
    }
}
