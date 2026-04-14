package com.example.docxmath;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ReviewServerCli {
    private ReviewServerCli() {
    }

    public static void main(String[] args) throws Exception {
        run(args);
    }

    public static void run(String[] args) throws Exception {
        Config config = Config.parse(args);
        ReviewWorkspace workspace = ReviewWorkspace.open(config.reviewRoot);
        HttpServer server = HttpServer.create(new InetSocketAddress(config.host, config.port), 0);
        server.createContext("/", new ReviewHandler(workspace, config));
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();

        int actualPort = server.getAddress().getPort();
        System.out.println("Review server running at http://" + config.host + ":" + actualPort);
        System.out.println("Review root: " + config.reviewRoot.toAbsolutePath().normalize());
        System.out.println("Operator Python: " + config.pythonExecutable);
        System.out.println("Bundle list: /review/bundles");
        System.out.println("API root: /api/review");
    }

    private record Config(Path reviewRoot, String host, int port, Path questionBankDb, String questionBankDbUrl, String pythonExecutable) {
        static Config parse(String[] args) {
            Path reviewRoot = null;
            String host = "127.0.0.1";
            int port = 8080;
            Path questionBankDb = null;
            String questionBankDbUrl = null;
            String pythonExecutable = envOrDefault("QB_OPERATOR_PYTHON",
                    envOrDefault("QUESTION_BANK_PYTHON",
                            envOrDefault("PYTHON", "python3")));

            for (int i = 0; i < args.length; i++) {
                String arg = args[i];
                if ("--review-root".equals(arg) || "--root".equals(arg)) {
                    if (i + 1 >= args.length) {
                        throw new IllegalArgumentException("Missing value after " + arg);
                    }
                    reviewRoot = Path.of(args[++i]).toAbsolutePath().normalize();
                } else if ("--host".equals(arg)) {
                    if (i + 1 >= args.length) {
                        throw new IllegalArgumentException("Missing value after --host");
                    }
                    host = args[++i];
                } else if ("--port".equals(arg)) {
                    if (i + 1 >= args.length) {
                        throw new IllegalArgumentException("Missing value after --port");
                    }
                    port = Integer.parseInt(args[++i]);
                } else if ("--question-bank-db".equals(arg)) {
                    if (i + 1 >= args.length) {
                        throw new IllegalArgumentException("Missing value after --question-bank-db");
                    }
                    questionBankDb = Path.of(args[++i]).toAbsolutePath().normalize();
                } else if ("--question-bank-db-url".equals(arg)) {
                    if (i + 1 >= args.length) {
                        throw new IllegalArgumentException("Missing value after --question-bank-db-url");
                    }
                    questionBankDbUrl = args[++i];
                } else if ("--python-executable".equals(arg)) {
                    if (i + 1 >= args.length) {
                        throw new IllegalArgumentException("Missing value after --python-executable");
                    }
                    pythonExecutable = args[++i].trim();
                    if (pythonExecutable.isBlank()) {
                        throw new IllegalArgumentException(
                                "--python-executable requires a non-blank value; set QB_OPERATOR_PYTHON or omit this option"
                        );
                    }
                } else if (!arg.startsWith("--") && reviewRoot == null) {
                    reviewRoot = Path.of(arg).toAbsolutePath().normalize();
                } else {
                    throw new IllegalArgumentException("Unknown option: " + arg);
                }
            }

            if (reviewRoot == null) {
                throw new IllegalArgumentException("Missing required --review-root <dir> (or --root <dir>)");
            }
            return new Config(reviewRoot, host, port, questionBankDb, questionBankDbUrl, pythonExecutable);
        }

        private static String envOrDefault(String key, String defaultValue) {
            String value = System.getenv(key);
            if (value == null || value.isBlank()) {
                return defaultValue;
            }
            return value.trim();
        }
    }

    private static final class ReviewHandler implements HttpHandler {
        private final ReviewWorkspace workspace;
        private final Config config;
        private final Path repoRoot;
        private final ObjectMapper mapper = new ObjectMapper();
        private final ExecutorService jobExecutor = Executors.newCachedThreadPool();

        private ReviewHandler(ReviewWorkspace workspace, Config config) {
            this.workspace = workspace;
            this.config = config;
            this.repoRoot = Path.of("").toAbsolutePath().normalize();
        }

        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                String method = exchange.getRequestMethod().toUpperCase(Locale.ROOT);
                URI uri = exchange.getRequestURI();
                String path = uri.getPath();
                if (path == null || path.isBlank() || "/".equals(path)) {
                    redirect(exchange, "/review/bundles");
                    return;
                }
                if (path.startsWith("/review/")) {
                    handlePage(exchange, method, path);
                    return;
                }
                if (path.startsWith("/operator/")) {
                    handleOperatorPage(exchange, method, path);
                    return;
                }
                if (path.startsWith("/api/review/")) {
                    handleApi(exchange, method, path, uri.getRawQuery());
                    return;
                }
                if (path.startsWith("/api/operator/")) {
                    handleOperatorApi(exchange, method, path, uri.getRawQuery());
                    return;
                }
                if ("/review".equals(path)) {
                    redirect(exchange, "/review/bundles");
                    return;
                }
                if ("/operator".equals(path)) {
                    redirect(exchange, "/operator/dashboard");
                    return;
                }
                notFound(exchange, "Unknown path: " + path);
            } catch (Exception ex) {
                sendJson(exchange, 500, Map.of(
                        "error", "internal_server_error",
                        "message", ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage()
                ));
            } finally {
                exchange.close();
            }
        }

        private void handlePage(HttpExchange exchange, String method, String path) throws Exception {
            if (!"GET".equals(method)) {
                notFound(exchange, "Page routes are GET-only");
                return;
            }
            List<String> segments = splitPath(path);
            if (segments.size() == 2 && "review".equals(segments.get(0)) && "bundles".equals(segments.get(1))) {
                sendHtml(exchange, 200, ReviewHtml.bundleListPage());
                return;
            }
            if (segments.size() == 3 && "review".equals(segments.get(0)) && "bundle".equals(segments.get(1))) {
                sendHtml(exchange, 200, ReviewHtml.queuePage(segments.get(2)));
                return;
            }
            if (segments.size() == 4
                    && "review".equals(segments.get(0))
                    && "bundle".equals(segments.get(1))
                    && "full".equals(segments.get(3))) {
                sendHtml(exchange, 200, ReviewHtml.fullBundlePage(segments.get(2)));
                return;
            }
            if (segments.size() == 5
                    && "review".equals(segments.get(0))
                    && "bundle".equals(segments.get(1))
                    && "question".equals(segments.get(3))) {
                sendHtml(exchange, 200, ReviewHtml.questionDetailPage(segments.get(2), segments.get(4)));
                return;
            }
            notFound(exchange, "Unknown review page: " + path);
        }

        private void handleOperatorPage(HttpExchange exchange, String method, String path) throws Exception {
            if (!"GET".equals(method)) {
                notFound(exchange, "Operator page routes are GET-only");
                return;
            }
            List<String> segments = splitPath(path);
            if (segments.size() == 2 && "operator".equals(segments.get(0)) && "dashboard".equals(segments.get(1))) {
                sendHtml(exchange, 200, ReviewHtml.operatorDashboardPage());
                return;
            }
            notFound(exchange, "Unknown operator page: " + path);
        }

        private void handleApi(HttpExchange exchange, String method, String path, String rawQuery) throws Exception {
            List<String> segments = splitPath(path);
            if (segments.size() == 3 && "api".equals(segments.get(0)) && "review".equals(segments.get(1)) && "bundles".equals(segments.get(2))) {
                if (!"GET".equals(method)) {
                    notFound(exchange, "bundles API is GET-only");
                    return;
                }
                sendJson(exchange, 200, Map.of(
                        "root", workspace.root().toString(),
                        "bundles", workspace.bundleSummaries()
                ));
                return;
            }

            if (segments.size() == 4 && "api".equals(segments.get(0)) && "review".equals(segments.get(1)) && "session".equals(segments.get(2)) && "open".equals(segments.get(3))) {
                if (!"POST".equals(method)) {
                    notFound(exchange, "open API is POST-only");
                    return;
                }
                ObjectNode payload = readObjectBody(exchange);
                String requestedBundleId = text(payload, "bundle_id", "");
                String requestedBundlePath = text(payload, "bundle_path", "");
                if (!requestedBundlePath.isBlank()) {
                    requestedBundleId = Path.of(requestedBundlePath).getFileName().toString();
                }
                if (requestedBundleId.isBlank()) {
                    throw new IllegalArgumentException("Missing bundle_id or bundle_path");
                }
                sendJson(exchange, 200, workspace.openSession(requestedBundleId));
                return;
            }

            if (segments.size() >= 4 && "api".equals(segments.get(0)) && "review".equals(segments.get(1)) && "session".equals(segments.get(2))) {
                String bundleId = segments.get(3);
                if (segments.size() == 5 && "queue".equals(segments.get(4)) && "GET".equals(method)) {
                    Map<String, String> filters = queryParams(rawQuery);
                    boolean includeSecondary = booleanQuery(filters, "includeSecondary", false);
                    boolean includeReviewed = booleanQuery(filters, "includeReviewed", false);
                    boolean includeAll = booleanQuery(filters, "includeAll", false);
                    sendJson(exchange, 200, workspace.queue(bundleId, includeSecondary, includeReviewed, includeAll, filters));
                    return;
                }
                if (segments.size() == 5 && "source-html".equals(segments.get(4)) && "GET".equals(method)) {
                    sendJson(exchange, 200, workspace.sourceHtml(bundleId));
                    return;
                }
                if (segments.size() == 6 && "question".equals(segments.get(4)) && "GET".equals(method)) {
                    sendJson(exchange, 200, workspace.questionDetail(bundleId, segments.get(5)));
                    return;
                }
                if (segments.size() == 7 && "question".equals(segments.get(4)) && "save".equals(segments.get(6)) && "POST".equals(method)) {
                    ObjectNode payload = readObjectBody(exchange);
                    sendJson(exchange, 200, workspace.saveQuestion(bundleId, segments.get(5), payload));
                    return;
                }
                if (segments.size() == 6 && "batch".equals(segments.get(4)) && "save".equals(segments.get(5)) && "POST".equals(method)) {
                    ObjectNode payload = readObjectBody(exchange);
                    sendJson(exchange, 200, workspace.batchSaveQuestions(bundleId, payload));
                    return;
                }
                if (segments.size() == 5 && "override-manifest".equals(segments.get(4)) && "GET".equals(method)) {
                    sendJson(exchange, 200, workspace.getOverrideManifest(bundleId));
                    return;
                }
                if (segments.size() == 5 && "finalize".equals(segments.get(4)) && "POST".equals(method)) {
                    ObjectNode payload = readObjectBody(exchange);
                    sendJson(exchange, 200, workspace.finalizeBundle(bundleId, payload));
                    return;
                }
            }

            notFound(exchange, "Unknown API route: " + path);
        }

        private void handleOperatorApi(HttpExchange exchange, String method, String path, String rawQuery) throws Exception {
            List<String> segments = splitPath(path);
            if (segments.size() == 3 && "api".equals(segments.get(0)) && "operator".equals(segments.get(1)) && "jobs".equals(segments.get(2))) {
                if (!"GET".equals(method)) {
                    notFound(exchange, "jobs API is GET-only");
                    return;
                }
                sendJson(exchange, 200, Map.of(
                        "root", workspace.root().toString(),
                        "jobs", listOperatorJobs()
                ));
                return;
            }
            if (segments.size() == 3 && "api".equals(segments.get(0)) && "operator".equals(segments.get(1)) && "bundles".equals(segments.get(2))) {
                if (!"GET".equals(method)) {
                    notFound(exchange, "bundles API is GET-only");
                    return;
                }
                sendJson(exchange, 200, Map.of(
                        "root", workspace.root().toString(),
                        "bundles", listOperatorBundles()
                ));
                return;
            }
            if (segments.size() == 3 && "api".equals(segments.get(0)) && "operator".equals(segments.get(1)) && "upload".equals(segments.get(2))) {
                if (!"POST".equals(method)) {
                    notFound(exchange, "upload API is POST-only");
                    return;
                }
                ObjectNode payload = readObjectBody(exchange);
                sendJson(exchange, 200, startUploadJob(payload));
                return;
            }
            if (segments.size() == 4 && "api".equals(segments.get(0)) && "operator".equals(segments.get(1)) && "import".equals(segments.get(2))) {
                if (!"POST".equals(method)) {
                    notFound(exchange, "import API is POST-only");
                    return;
                }
                ObjectNode payload = readObjectBody(exchange);
                try {
                    sendJson(exchange, 200, startImportJob(segments.get(3), payload));
                } catch (OperatorImportRefusal refusal) {
                    sendJson(exchange, 409, Map.of(
                            "error_code", "import_not_allowed",
                            "bundle_id", refusal.bundleId,
                            "readiness_state", refusal.readinessState,
                            "reason", refusal.getMessage()
                    ));
                } catch (OperatorRuntimeRefusal refusal) {
                    sendJson(exchange, refusal.statusCode, Map.of(
                            "error_code", refusal.errorCode,
                            "reason", refusal.getMessage(),
                            "python_executable", config.pythonExecutable,
                            "details", refusal.details
                    ));
                }
                return;
            }
            if (segments.size() == 4 && "api".equals(segments.get(0)) && "operator".equals(segments.get(1)) && "export".equals(segments.get(2))) {
                if (!"POST".equals(method)) {
                    notFound(exchange, "export API is POST-only");
                    return;
                }
                ObjectNode payload = readObjectBody(exchange);
                try {
                    sendJson(exchange, 200, startExportJob(segments.get(3), payload));
                } catch (OperatorRuntimeRefusal refusal) {
                    sendJson(exchange, refusal.statusCode, Map.of(
                            "error_code", refusal.errorCode,
                            "reason", refusal.getMessage(),
                            "python_executable", config.pythonExecutable,
                            "details", refusal.details
                    ));
                }
                return;
            }
            notFound(exchange, "Unknown operator API route: " + path);
        }

        private Path operatorJobsDir() {
            return workspace.root().resolve(".operator").resolve("jobs");
        }

        private Path operatorJobDir(String jobId) {
            return operatorJobsDir().resolve(jobId);
        }

        private Path operatorJobFile(String jobId) {
            return operatorJobDir(jobId).resolve("job.json");
        }

        private void writeJob(Map<String, Object> job) throws IOException {
            String jobId = String.valueOf(job.get("job_id"));
            Path jobFile = operatorJobFile(jobId);
            Files.createDirectories(jobFile.getParent());
            mapper.writeValue(jobFile.toFile(), job);
        }

        private Map<String, Object> readJob(Path jobFile) throws IOException {
            JsonNode node = mapper.readTree(jobFile.toFile());
            return jsonObjectOrEmpty(node);
        }

        private List<Map<String, Object>> listOperatorJobs() throws IOException {
            Path jobsDir = operatorJobsDir();
            if (!Files.exists(jobsDir)) {
                return List.of();
            }
            List<Map<String, Object>> jobs = new ArrayList<>();
            try (var stream = Files.list(jobsDir)) {
                for (Path child : stream.filter(Files::isDirectory).sorted().toList()) {
                    Path jobFile = child.resolve("job.json");
                    if (!Files.exists(jobFile)) {
                        continue;
                    }
                    jobs.add(readJob(jobFile));
                }
            }
            jobs.sort(Comparator.comparing((Map<String, Object> job) -> String.valueOf(job.getOrDefault("updated_at", job.getOrDefault("created_at", "")))).reversed());
            return jobs;
        }

        private List<Map<String, Object>> listOperatorBundles() throws IOException {
            List<Map<String, Object>> bundles = new ArrayList<>();
            for (Map<String, Object> bundle : workspace.bundleSummaries()) {
                Map<String, Object> item = new LinkedHashMap<>(bundle);
                boolean finalized = Boolean.TRUE.equals(bundle.get("finalized"));
                int questionCount = 0;
                try {
                    questionCount = Integer.parseInt(String.valueOf(bundle.getOrDefault("question_count", 0)));
                } catch (Exception ignored) {
                }
                Map<String, Object> readiness = readBundleImportReadiness(Path.of(String.valueOf(bundle.getOrDefault("bundle_path", ""))), finalized, questionCount);
                String readinessState = String.valueOf(readiness.getOrDefault("import_readiness_state", ""));
                String readinessReason = String.valueOf(readiness.getOrDefault("import_readiness_reason", ""));
                String operatorState;
                if (questionCount <= 0) {
                    operatorState = "failed";
                } else if (!finalized) {
                    int blockerCount = 0;
                    try {
                        blockerCount = Integer.parseInt(String.valueOf(bundle.getOrDefault("blocker_count", 0)));
                    } catch (Exception ignored) {
                    }
                    operatorState = blockerCount > 0 ? "needs_review" : "uploaded";
                } else if ("approved_importable".equals(readinessState)) {
                    operatorState = "import_ready";
                } else {
                    operatorState = "import_blocked";
                }
                item.put("operator_state", operatorState);
                item.put("import_ready", "import_ready".equals(operatorState));
                item.put("import_blocked", "import_blocked".equals(operatorState));
                item.put("import_readiness_state", readinessState);
                item.put("import_readiness_reason", readinessReason);
                item.put("import_readiness_evidence", readiness.getOrDefault("import_readiness_evidence", Map.of()));
                item.put("review_bundle_link", "/review/bundle/" + bundle.getOrDefault("bundle_id", ""));
                item.put("review_bundle_full_link", "/review/bundle/" + bundle.getOrDefault("bundle_id", "") + "/full");
                bundles.add(item);
            }
            bundles.sort(Comparator.comparing(m -> String.valueOf(m.getOrDefault("bundle_id", ""))));
            return bundles;
        }

        private Map<String, Object> readBundleImportReadiness(Path bundlePath, boolean finalized, int questionCount) {
            Map<String, Object> out = new LinkedHashMap<>();
            // Import readiness is defined for finalized (approved-artifact) bundles. For non-finalized
            // bundles we still surface a clear operator-facing reason so the import button is honest.
            if (questionCount <= 0) {
                out.put("import_readiness_state", "blocked_import");
                out.put("import_readiness_reason", "question_count is 0");
                out.put("import_readiness_evidence", Map.of("question_count", questionCount));
                return out;
            }
            if (!finalized) {
                out.put("import_readiness_state", "blocked_import");
                out.put("import_readiness_reason", "bundle is not finalized");
                out.put("import_readiness_evidence", Map.of("finalized", false));
                return out;
            }
            if (bundlePath == null || bundlePath.toString().isBlank() || !Files.exists(bundlePath)) {
                out.put("import_readiness_state", "blocked_import");
                out.put("import_readiness_reason", "bundle path not found");
                out.put("import_readiness_evidence", Map.of("bundle_path", String.valueOf(bundlePath)));
                return out;
            }
            Path validationPath = bundlePath.resolve("question_bank_import_validation.json");
            Path summaryPath = bundlePath.resolve("question_bank_import_summary.json");
            Map<String, Object> validation = Map.of();
            if (Files.exists(validationPath)) {
                try {
                    validation = readJsonMap(validationPath);
                } catch (Exception ignored) {
                }
            } else if (Files.exists(summaryPath)) {
                try {
                    validation = readJsonMap(summaryPath);
                } catch (Exception ignored) {
                }
            }
            if (validation.isEmpty()) {
                out.put("import_readiness_state", "blocked_import");
                out.put("import_readiness_reason", "missing question_bank_import_validation.json");
                out.put("import_readiness_evidence", Map.of(
                        "expected_validation_path", validationPath.toString(),
                        "expected_summary_path", summaryPath.toString()
                ));
                return out;
            }
            Map<String, Object> readiness = coerceJsonObject(validation.get("import_readiness"));
            String stateRaw = String.valueOf(readiness.getOrDefault("state", ""));
            String state;
            if ("approved_importable".equals(stateRaw)) {
                state = "approved_importable";
            } else if ("draft_importable".equals(stateRaw)) {
                state = "draft_importable";
            } else {
                // Anything else is treated as blocked for operator clarity.
                state = "blocked_import";
            }
            String reason = String.valueOf(readiness.getOrDefault("reason", ""));
            Map<String, Object> evidence = coerceJsonObject(readiness.get("evidence"));
            out.put("import_readiness_state", state);
            out.put("import_readiness_reason", reason.isBlank() ? "no reason provided" : reason);
            out.put("import_readiness_evidence", evidence);
            return out;
        }

        private Map<String, Object> coerceJsonObject(Object value) {
            if (!(value instanceof Map<?, ?>)) {
                return Map.of();
            }
            Map<String, Object> out = new LinkedHashMap<>();
            Map<?, ?> src = (Map<?, ?>) value;
            for (Map.Entry<?, ?> entry : src.entrySet()) {
                String key = String.valueOf(entry.getKey());
                out.put(key, entry.getValue());
            }
            return out;
        }

        private Map<String, Object> startUploadJob(ObjectNode payload) throws IOException {
            String fileName = text(payload, "filename", "");
            String contentBase64 = text(payload, "content_base64", "");
            String uploadLabel = text(payload, "upload_label", "");
            if (fileName.isBlank() || contentBase64.isBlank()) {
                throw new IOException("missing filename or content_base64");
            }
            String jobId = "upload_" + Instant.now().toString().replace(":", "").replace("-", "") + "_" + UUID.randomUUID().toString().substring(0, 8);
            Path inputDir = Path.of(System.getProperty("java.io.tmpdir"), "transpect_operator_uploads", jobId, "input");
            Files.createDirectories(inputDir);
            Path sourceDocx = inputDir.resolve(Path.of(fileName).getFileName().toString());
            Files.write(sourceDocx, Base64.getDecoder().decode(contentBase64));
            Map<String, Object> job = new LinkedHashMap<>();
            job.put("schema_version", "operator_job.v1");
            job.put("job_type", "exam_intake");
            job.put("job_id", jobId);
            job.put("status", "uploaded");
            job.put("created_at", Instant.now().toString());
            job.put("updated_at", Instant.now().toString());
            job.put("source_filename", fileName);
            job.put("upload_label", uploadLabel);
            job.put("source_docx_path", sourceDocx.toString());
            job.put("review_root", workspace.root().toString());
            job.put("bundle_id", "");
            job.put("bundle_path", "");
            job.put("review_link", "");
            job.put("batch_summary_json", "");
            job.put("message", "uploaded; processing queued");
            writeJob(job);
            jobExecutor.submit(() -> processUploadJob(jobId, sourceDocx));
            return job;
        }

        private void processUploadJob(String jobId, Path sourceDocx) {
            try {
                updateJobStatus(jobId, "processing", "running DOCX -> contracts pipeline", Map.of());
                Path jobDir = operatorJobDir(jobId);
                Path batchOutputRoot = jobDir.resolve("batch_output");
                Files.createDirectories(batchOutputRoot);
                List<String> command = new ArrayList<>();
                command.add("python3");
                command.add("scripts/batch/run_subject_batch.py");
                command.add("--input-docx");
                command.add(sourceDocx.toString());
                command.add("--output-root");
                command.add(batchOutputRoot.toString());
                command.add("--batch-name");
                command.add(jobId);
                command.add("--skip-build");
                ProcessResult result = runProcess(command, repoRoot);
                Path batchDir = batchOutputRoot.resolve(jobId);
                Path summaryJson = batchDir.resolve("batch-summary.json");
                if (result.exitCode != 0 || !Files.exists(summaryJson)) {
                    updateJobStatus(jobId, "failed", "batch conversion failed", Map.of(
                            "exit_code", result.exitCode,
                            "stdout", result.stdout,
                            "stderr", result.stderr
                    ));
                    return;
                }
                Map<String, Object> summary = readJobSummary(summaryJson);
                String bundleId = "";
                Path bundlePath = null;
                List<Path> contractDirs = listDirectories(batchDir.resolve("contracts"));
                if (!contractDirs.isEmpty()) {
                    Path sourceBundleDir = contractDirs.get(0);
                    Map<String, Object> manifest = readJsonMap(sourceBundleDir.resolve("manifest.json"));
                    bundleId = String.valueOf(manifest.getOrDefault("bundle_id", sourceBundleDir.getFileName().toString()));
                    bundlePath = workspace.root().resolve(bundleId);
                    copyDirectory(sourceBundleDir, bundlePath);
                }
                updateJobStatus(jobId, "contracts_ready", "contracts generated", Map.of(
                        "batch_dir", batchDir.toString(),
                        "batch_summary_json", summaryJson.toString(),
                        "bundle_id", bundleId,
                        "bundle_path", bundlePath == null ? "" : bundlePath.toString(),
                        "review_link", bundleId.isBlank() ? "" : "/review/bundle/" + bundleId,
                        "review_link_full", bundleId.isBlank() ? "" : "/review/bundle/" + bundleId + "/full",
                        "publish_verdict", String.valueOf(summary.getOrDefault("publish_verdict", "needs_review"))
                ));
            } catch (Exception ex) {
                try {
                    updateJobStatus(jobId, "failed", "processing failed: " + ex.getMessage(), Map.of());
                } catch (IOException ignored) {
                }
            }
        }

        private Map<String, Object> startImportJob(String bundleId, ObjectNode payload) throws IOException, OperatorImportRefusal, OperatorRuntimeRefusal {
            if ((config.questionBankDbUrl == null || config.questionBankDbUrl.isBlank()) && config.questionBankDb == null) {
                throw new IOException("question_bank DB is not configured for import triggers");
            }
            Map<String, Object> bundle = findOperatorBundle(bundleId);
            String bundlePathText = String.valueOf(bundle.getOrDefault("bundle_path", ""));
            if (bundlePathText.isBlank()) {
                bundlePathText = workspace.root().resolve(bundleId).toString();
            }
            Path bundlePath = Path.of(bundlePathText);
            if (!Files.exists(bundlePath)) {
                throw new IOException("bundle not found: " + bundleId);
            }
            // Preflight the same readiness the approved-only importer enforces, but surface it early
            // so operators see a clear reason before pressing import.
            int questionCount = 0;
            try {
                questionCount = Integer.parseInt(String.valueOf(bundle.getOrDefault("question_count", 0)));
            } catch (Exception ignored) {
            }
            boolean finalized = Boolean.TRUE.equals(bundle.get("finalized"));
            Map<String, Object> readiness = readBundleImportReadiness(bundlePath, finalized, questionCount);
            String readinessState = String.valueOf(readiness.getOrDefault("import_readiness_state", ""));
            if (!"approved_importable".equals(readinessState)) {
                throw new OperatorImportRefusal(
                        bundleId,
                        readinessState,
                        String.valueOf(readiness.getOrDefault("import_readiness_reason", "bundle is not approved-importable"))
                );
            }
            ensureOperatorPythonRuntime("approved import");
            String jobId = "import_" + Instant.now().toString().replace(":", "").replace("-", "") + "_" + UUID.randomUUID().toString().substring(0, 8);
            Path jobDir = operatorJobDir(jobId);
            Files.createDirectories(jobDir);
            Map<String, Object> job = new LinkedHashMap<>();
            job.put("schema_version", "operator_job.v1");
            job.put("job_type", "approved_import");
            job.put("job_id", jobId);
            job.put("bundle_id", bundleId);
            job.put("bundle_path", bundlePath.toString());
            job.put("status", "uploaded");
            job.put("created_at", Instant.now().toString());
            job.put("updated_at", Instant.now().toString());
            job.put("message", "import queued");
            writeJob(job);
            jobExecutor.submit(() -> processImportJob(jobId, bundlePath, payload));
            return job;
        }

        private static final class OperatorImportRefusal extends Exception {
            private final String bundleId;
            private final String readinessState;

            private OperatorImportRefusal(String bundleId, String readinessState, String message) {
                super(message);
                this.bundleId = bundleId;
                this.readinessState = readinessState;
            }
        }

        private static final class OperatorRuntimeRefusal extends Exception {
            private final String errorCode;
            private final int statusCode;
            private final Map<String, Object> details;

            private OperatorRuntimeRefusal(String errorCode, int statusCode, String message, Map<String, Object> details) {
                super(message);
                this.errorCode = errorCode;
                this.statusCode = statusCode;
                this.details = details;
            }
        }

        private void processImportJob(String jobId, Path bundlePath, ObjectNode payload) {
            try {
                updateJobStatus(jobId, "processing", "running approved-artifact import", Map.of());
                Path jobDir = operatorJobDir(jobId);
                Path reportJson = jobDir.resolve("import_report.json");
                Path summaryJson = jobDir.resolve("import_summary.json");
                Path summaryMd = jobDir.resolve("import_summary.md");
                List<String> command = new ArrayList<>();
                command.add(config.pythonExecutable);
                command.add("scripts/question_bank_import.py");
                command.add("--bundle-dir");
                command.add(bundlePath.toString());
                command.add("--mode");
                command.add("approved-only");
                if (config.questionBankDbUrl != null && !config.questionBankDbUrl.isBlank()) {
                    command.add("--db-url");
                    command.add(config.questionBankDbUrl);
                } else if (config.questionBankDb != null) {
                    command.add("--db");
                    command.add(config.questionBankDb.toString());
                }
                command.add("--report-json");
                command.add(reportJson.toString());
                command.add("--summary-json");
                command.add(summaryJson.toString());
                command.add("--summary-md");
                command.add(summaryMd.toString());
                ProcessResult result = runProcess(command, repoRoot);
                if (result.exitCode != 0) {
                    updateJobStatus(jobId, "failed", "import failed", Map.of(
                            "exit_code", result.exitCode,
                            "stdout", result.stdout,
                            "stderr", result.stderr,
                            "report_json", reportJson.toString(),
                            "summary_json", summaryJson.toString(),
                            "summary_md", summaryMd.toString()
                    ));
                    return;
                }
                updateJobStatus(jobId, "completed", "bundle imported", Map.of(
                        "report_json", reportJson.toString(),
                        "summary_json", summaryJson.toString(),
                        "summary_md", summaryMd.toString()
                ));
            } catch (Exception ex) {
                try {
                    updateJobStatus(jobId, "failed", "import failed: " + ex.getMessage(), Map.of());
                } catch (IOException ignored) {
                }
            }
        }

        private Map<String, Object> startExportJob(String assemblyId, ObjectNode payload) throws IOException, OperatorRuntimeRefusal {
            if ((config.questionBankDbUrl == null || config.questionBankDbUrl.isBlank()) && config.questionBankDb == null) {
                throw new IOException("question_bank DB is not configured for export triggers");
            }
            if (assemblyId.isBlank()) {
                throw new IOException("missing assembly_id");
            }
            String mode = text(payload, "mode", "teacher");
            String exportLabel = text(payload, "export_label", "");
            if (!"student".equals(mode) && !"teacher".equals(mode)) {
                throw new IOException("invalid export mode: " + mode);
            }
            ensureOperatorPythonRuntime("DOCX export");
            String jobId = "export_" + Instant.now().toString().replace(":", "").replace("-", "") + "_" + UUID.randomUUID().toString().substring(0, 8);
            Path jobDir = operatorJobDir(jobId);
            Files.createDirectories(jobDir);
            Map<String, Object> job = new LinkedHashMap<>();
            job.put("schema_version", "operator_job.v1");
            job.put("job_type", "assembly_export");
            job.put("job_id", jobId);
            job.put("assembly_id", assemblyId);
            job.put("export_mode", mode);
            job.put("export_label", exportLabel);
            job.put("status", "uploaded");
            job.put("created_at", Instant.now().toString());
            job.put("updated_at", Instant.now().toString());
            job.put("message", "export queued");
            writeJob(job);
            jobExecutor.submit(() -> processExportJob(jobId, assemblyId, mode));
            return job;
        }

        private void processExportJob(String jobId, String assemblyId, String mode) {
            try {
                updateJobStatus(jobId, "processing", "running DOCX export", Map.of());
                Path jobDir = operatorJobDir(jobId);
                Path outputDocx = jobDir.resolve("assembled_" + mode + ".docx");
                Path exportReport = jobDir.resolve("assembled_" + mode + "_export_report.json");
                List<String> command = new ArrayList<>();
                command.add(config.pythonExecutable);
                command.add("scripts/question_bank_export_assembled_docx.py");
                if (config.questionBankDbUrl != null && !config.questionBankDbUrl.isBlank()) {
                    command.add("--db-url");
                    command.add(config.questionBankDbUrl);
                } else if (config.questionBankDb != null) {
                    command.add("--db");
                    command.add(config.questionBankDb.toString());
                }
                command.add("--assembly-id");
                command.add(assemblyId);
                command.add("--mode");
                command.add(mode);
                command.add("--output-docx");
                command.add(outputDocx.toString());
                command.add("--report");
                command.add(exportReport.toString());
                ProcessResult result = runProcess(command, repoRoot);
                if (result.exitCode != 0) {
                    updateJobStatus(jobId, "failed", "export failed", Map.of(
                            "exit_code", result.exitCode,
                            "stdout", result.stdout,
                            "stderr", result.stderr,
                            "docx_path", outputDocx.toString(),
                            "export_report_path", exportReport.toString()
                    ));
                    return;
                }
                Path acceptanceJson = jobDir.resolve("assembled_" + mode + "_acceptance.json");
                Path acceptanceMd = jobDir.resolve("assembled_" + mode + "_acceptance.md");
                List<String> verifyCommand = new ArrayList<>();
                verifyCommand.add(config.pythonExecutable);
                verifyCommand.add("scripts/question_bank_verify_assembled_docx_export.py");
                verifyCommand.add("--artifact");
                verifyCommand.add(readExportReportInputArtifact(exportReport));
                verifyCommand.add("--export-report");
                verifyCommand.add(exportReport.toString());
                verifyCommand.add("--docx");
                verifyCommand.add(outputDocx.toString());
                verifyCommand.add("--output-json");
                verifyCommand.add(acceptanceJson.toString());
                verifyCommand.add("--output-md");
                verifyCommand.add(acceptanceMd.toString());
                ProcessResult verifyResult = runProcess(verifyCommand, repoRoot);
                if (verifyResult.exitCode != 0) {
                    updateJobStatus(jobId, "failed", "export verification failed", Map.of(
                            "verify_exit_code", verifyResult.exitCode,
                            "verify_stdout", verifyResult.stdout,
                            "verify_stderr", verifyResult.stderr,
                            "docx_path", outputDocx.toString(),
                            "export_report_path", exportReport.toString(),
                            "acceptance_json_path", acceptanceJson.toString(),
                            "acceptance_md_path", acceptanceMd.toString()
                    ));
                    return;
                }
                updateJobStatus(jobId, "completed", "DOCX export complete", Map.of(
                        "docx_path", outputDocx.toString(),
                        "export_report_path", exportReport.toString(),
                        "acceptance_json_path", acceptanceJson.toString(),
                        "acceptance_md_path", acceptanceMd.toString()
                ));
            } catch (Exception ex) {
                try {
                    updateJobStatus(jobId, "failed", "export failed: " + ex.getMessage(), Map.of());
                } catch (IOException ignored) {
                }
            }
        }

        private void updateJobStatus(String jobId, String status, String message, Map<String, Object> extra) throws IOException {
            Path jobFile = operatorJobFile(jobId);
            if (!Files.exists(jobFile)) {
                return;
            }
            Map<String, Object> job = readJob(jobFile);
            job.put("status", status);
            job.put("message", message);
            job.put("updated_at", Instant.now().toString());
            if (extra != null) {
                job.putAll(extra);
            }
            writeJob(job);
        }

        private List<Path> listDirectories(Path parent) throws IOException {
            if (!Files.exists(parent)) {
                return List.of();
            }
            List<Path> result = new ArrayList<>();
            try (var stream = Files.list(parent)) {
                for (Path child : stream.filter(Files::isDirectory).sorted().toList()) {
                    result.add(child);
                }
            }
            return result;
        }

        private Map<String, Object> readJobSummary(Path summaryJson) throws IOException {
            JsonNode node = mapper.readTree(summaryJson.toFile());
            return jsonObjectOrEmpty(node);
        }

        private Map<String, Object> readJsonMap(Path path) throws IOException {
            if (!Files.exists(path)) {
                return Map.of();
            }
            JsonNode node = mapper.readTree(path.toFile());
            return jsonObjectOrEmpty(node);
        }

        private Map<String, Object> jsonObjectOrEmpty(JsonNode node) {
            if (node == null || node.isNull()) {
                return Map.of();
            }
            return mapper.convertValue(node, new TypeReference<Map<String, Object>>() { });
        }

        private void ensureOperatorPythonRuntime(String purpose) throws IOException, OperatorRuntimeRefusal {
            String python = config.pythonExecutable == null ? "" : config.pythonExecutable.trim();
            if (python.isBlank()) {
                throw new OperatorRuntimeRefusal(
                        "operator_python_runtime_missing",
                        503,
                        "operator Python executable is not configured",
                        Map.of("purpose", purpose)
                );
            }
            List<String> command = List.of(python, "-c", "import psycopg");
            ProcessResult result = runProcess(command, repoRoot);
            if (result.exitCode != 0) {
                throw new OperatorRuntimeRefusal(
                        "operator_python_runtime_missing_psycopg",
                        503,
                        "operator Python runtime cannot import psycopg; set QB_OPERATOR_PYTHON to a Python environment with psycopg installed",
                        Map.of(
                                "purpose", purpose,
                                "python_executable", python,
                                "stdout", result.stdout,
                                "stderr", result.stderr
                        )
                );
            }
        }

        private Map<String, Object> findOperatorBundle(String bundleId) throws IOException {
            for (Map<String, Object> bundle : listOperatorBundles()) {
                String bundleIdValue = String.valueOf(bundle.get("bundle_id"));
                String bundlePath = String.valueOf(bundle.get("bundle_path"));
                String bundleDirName = bundlePath.isBlank() ? "" : Path.of(bundlePath).getFileName().toString();
                if (bundleId.equals(bundleIdValue) || bundleId.equals(bundleDirName) || bundleId.equals(bundlePath)) {
                    return bundle;
                }
            }
            return Map.of();
        }

        private ProcessResult runProcess(List<String> command, Path cwd) throws IOException {
            ProcessBuilder builder = new ProcessBuilder(command);
            builder.directory(cwd.toFile());
            builder.redirectErrorStream(true);
            Process process = builder.start();
            byte[] bytes = process.getInputStream().readAllBytes();
            int exit;
            try {
                exit = process.waitFor();
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                process.destroyForcibly();
                throw new IOException("process execution interrupted: " + String.join(" ", command), ex);
            }
            String output = new String(bytes, StandardCharsets.UTF_8);
            return new ProcessResult(exit, output, "");
        }

        private String readExportReportInputArtifact(Path exportReport) throws IOException {
            Map<String, Object> report = readJobSummary(exportReport);
            String inputPath = String.valueOf(report.getOrDefault("input_assembly_artifact_path", ""));
            if (inputPath.isBlank()) {
                throw new IOException("export report missing input_assembly_artifact_path");
            }
            return inputPath;
        }

        private void copyDirectory(Path source, Path target) throws IOException {
            if (Files.exists(target)) {
                deleteDirectory(target);
            }
            Files.createDirectories(target);
            try (var stream = Files.walk(source)) {
                stream.forEach(path -> {
                    try {
                        Path relative = source.relativize(path);
                        Path dest = target.resolve(relative.toString());
                        if (Files.isDirectory(path)) {
                            Files.createDirectories(dest);
                        } else {
                            Files.createDirectories(dest.getParent());
                            Files.copy(path, dest, StandardCopyOption.REPLACE_EXISTING);
                        }
                    } catch (IOException ex) {
                        throw new RuntimeException(ex);
                    }
                });
            } catch (RuntimeException ex) {
                if (ex.getCause() instanceof IOException io) {
                    throw io;
                }
                throw ex;
            }
        }

        private void deleteDirectory(Path path) throws IOException {
            if (!Files.exists(path)) {
                return;
            }
            try (var stream = Files.walk(path)) {
                stream.sorted(Comparator.reverseOrder()).forEach(p -> {
                    try {
                        Files.deleteIfExists(p);
                    } catch (IOException ex) {
                        throw new RuntimeException(ex);
                    }
                });
            } catch (RuntimeException ex) {
                if (ex.getCause() instanceof IOException io) {
                    throw io;
                }
                throw ex;
            }
        }

        private ObjectNode readObjectBody(HttpExchange exchange) throws IOException {
            try (InputStream inputStream = exchange.getRequestBody()) {
                byte[] bytes = inputStream.readAllBytes();
                if (bytes.length == 0) {
                    return workspace.mapper().createObjectNode();
                }
                JsonNode node = mapper.readTree(bytes);
                return node instanceof ObjectNode objectNode ? objectNode : workspace.mapper().createObjectNode();
            }
        }

        private String text(ObjectNode node, String field, String defaultValue) {
            if (node == null || !node.has(field) || node.get(field).isNull()) {
                return defaultValue;
            }
            return node.get(field).asText(defaultValue);
        }

        private record ProcessResult(int exitCode, String stdout, String stderr) {
        }

        private Map<String, String> queryParams(String rawQuery) {
            Map<String, String> params = new LinkedHashMap<>();
            if (rawQuery == null || rawQuery.isBlank()) {
                return params;
            }
            for (String part : rawQuery.split("&")) {
                if (part.isBlank()) {
                    continue;
                }
                int idx = part.indexOf('=');
                String key = idx >= 0 ? part.substring(0, idx) : part;
                String value = idx >= 0 ? part.substring(idx + 1) : "";
                params.put(urlDecode(key), urlDecode(value));
            }
            return params;
        }

        private boolean booleanQuery(Map<String, String> params, String key, boolean defaultValue) {
            String value = params.get(key);
            if (value == null || value.isBlank()) {
                return defaultValue;
            }
            return switch (value.toLowerCase(Locale.ROOT)) {
                case "1", "true", "yes", "on" -> true;
                case "0", "false", "no", "off" -> false;
                default -> defaultValue;
            };
        }

        private List<String> splitPath(String path) {
            String normalized = path == null ? "" : path.trim();
            if (normalized.startsWith("/")) {
                normalized = normalized.substring(1);
            }
            if (normalized.endsWith("/")) {
                normalized = normalized.substring(0, normalized.length() - 1);
            }
            if (normalized.isBlank()) {
                return List.of();
            }
            String[] parts = normalized.split("/");
            List<String> segments = new ArrayList<>(parts.length);
            for (String part : parts) {
                segments.add(urlDecode(part));
            }
            return segments;
        }

        private String urlDecode(String text) {
            return URLDecoder.decode(text, StandardCharsets.UTF_8);
        }

        private void redirect(HttpExchange exchange, String location) throws IOException {
            exchange.getResponseHeaders().set("Location", location);
            exchange.sendResponseHeaders(302, -1);
        }

        private void sendHtml(HttpExchange exchange, int status, String html) throws IOException {
            byte[] bytes = html.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
        }

        private void sendJson(HttpExchange exchange, int status, Object payload) throws IOException {
            byte[] bytes = mapper.writerWithDefaultPrettyPrinter().writeValueAsBytes(payload);
            exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
        }

        private void notFound(HttpExchange exchange, String message) throws IOException {
            sendJson(exchange, 404, Map.of(
                    "error", "not_found",
                    "message", message,
                    "timestamp", Instant.now().toString()
            ));
        }
    }
}
