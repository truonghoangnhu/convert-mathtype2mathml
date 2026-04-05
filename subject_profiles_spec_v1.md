# SPEC KỸ THUẬT — SUBJECT PROFILES V1

## 0. Mục tiêu

Chuẩn hóa pipeline convert `DOCX -> HTML` theo cấu trúc:

- **Global Core**
- **Subject Profile**
- **QA + Acceptance**

Trong pha này, triển khai 2 profile đầu tiên:

- **PhysicsProfile**
- **ChemistryProfile**

Phải đảm bảo:

- không làm giảm chất lượng convert công thức hiện tại
- không để rule của Hóa ảnh hưởng sang Lý
- không áp dụng rewrite chuyên ngành ở `generic/core`
- mọi thay đổi đều có QA đo trước/sau

---

# 1. Cấu trúc module đề xuất

## 1.1. Package/module layout

```text
pipeline/
  core/
    classifier/
    extract/
    html/
    math/
    images/
    qa/
    normalize/
  subjects/
    generic/
    physics/
    chemistry/
  model/
  config/
```

## 1.2. Các interface chính

```java
interface SubjectProfile {
    String getName();
    SubjectRules getRules();
    void preprocess(DocumentContext ctx);
    void postprocess(DocumentContext ctx);
    void contributeQa(QaReport report, DocumentContext ctx);
}
```

```java
interface ObjectClassifier {
    ObjectKind classify(EmbeddedObjectRef ref, SurroundingContext ctx);
}
```

```java
interface NormalizationRule {
    boolean applies(DocumentContext ctx, HtmlNodeRef node);
    void apply(DocumentContext ctx, HtmlNodeRef node);
}
```

```java
interface EquationHandler {
    EquationResult convert(EquationSource source, ConversionContext ctx);
}
```

---

# 2. Model dữ liệu chuẩn

## 2.1. Subject enum

```java
enum Subject {
    GENERIC,
    MATH,
    PHYSICS,
    CHEMISTRY,
    BIOLOGY
}
```

## 2.2. ObjectKind enum

```java
enum ObjectKind {
    EQUATION,
    DIAGRAM,
    CHART,
    CHEMICAL_DIAGRAM,
    GENERIC_IMAGE,
    UNKNOWN_PREVIEW
}
```

## 2.3. Embedded object model

```java
class EmbeddedObjectRef {
    String id;
    String progId;
    String sourcePath;
    String extension;
    String altText;
    String mimeType;
    byte[] data;
}
```

## 2.4. Context model

```java
class DocumentContext {
    Subject subject;
    Path sourceDocx;
    HtmlDocument html;
    List<EmbeddedObjectRef> objects;
    List<EquationRef> equations;
    QaReport qa;
    Map<String, Object> attributes;
}
```

## 2.5. QA model

```java
class QaReport {
    int totalMathMlFormulaCount;
    int totalPreviewCount;
    int equationDsmt4PreviewCount;
    int visioPreviewCount;
    int chemDrawPreviewCount;
    int emfCount;
    int wmfCount;
    int textFixCount;
    int chemistryInlineFixCount;
    List<UnresolvedObject> unresolvedObjects;
    Map<String, ExamQaSummary> examSummaries;
}
```

---

# 3. Global Core — những gì subject profile được phép dựa vào

Subject profile **không được tự làm lại** các việc sau. Chúng phải được cung cấp từ core:

## 3.1. Core classification
Classifier phải dựa trên:
- `progId`
- extension
- alt text
- surrounding paragraph/table context
- tên asset
- metadata của pipeline hiện tại

### Rule tối thiểu

```text
Equation.DSMT4            -> EQUATION
Visio.Drawing.15          -> DIAGRAM or CHART
ChemDraw*.Document.*      -> CHEMICAL_DIAGRAM
.emf / .wmf + graph-like context -> DIAGRAM or CHART
.png/.jpg fallback assets -> GENERIC_IMAGE unless linked to equation metadata
unknown OLE preview       -> UNKNOWN_PREVIEW
```

## 3.2. Core equation branch
Phải giữ nguyên hướng hiện tại:
- MathType/WMF/BIN/OMML -> MathML
- render bằng MathJax
- không degrade về ảnh nếu convert được

## 3.3. Core diagram/image branch
- diagram/chart không đi vào equation handler
- render web-safe:
  - ưu tiên SVG
  - fallback PNG

## 3.4. Core HTML cleanup
Dùng chung cho mọi môn:
- không để ảnh dính vào text sau
- block math không nằm trong câu inline
- giảm DOM thừa
- sửa alt/class sai kiểu “equation preview” khi object thực ra là diagram

---

# 4. PhysicsProfile — spec chi tiết

## 4.1. Mục tiêu
Dành cho:
- cơ học
- nhiệt học
- điện, quang, hạt nhân
- các đề có công thức + đồ thị + sơ đồ

Mục tiêu cụ thể:
- giữ nguyên chất lượng MathML hiện tại
- coi `Visio/EMF/WMF` đúng là **diagram/chart**, không phải equation
- không “hóa học hóa” chỉ số vật lý
- cleanup text corruption còn sót

## 4.2. Không được làm
PhysicsProfile **không được**:
- chuyển `v₀`, `x₁`, `U₀`, `I₀`, `p₁`, `T₂` sang logic chemical token
- biến mọi Unicode sub/sup thành `<sub>/<sup>` theo kiểu Hóa
- sửa notation vật lý nếu chưa chắc

## 4.3. Physics object rules

### Equation
Áp cho:
- Equation.DSMT4
- OMML
- WMF/BIN đã classify là equation

Hành động:
- đi qua core equation handler
- nếu còn preview fallback thì log QA

### Diagram / Chart
Áp cho:
- Visio.Drawing.15
- EMF/WMF đồ thị, sơ đồ mạch, p–T, đồ thị dao động, sơ đồ thí nghiệm

Hành động:
- convert sang SVG hoặc PNG
- đổi class HTML thành:
  - `physics-diagram`
  - `physics-chart`
- alt phải phản ánh loại object, ví dụ:
  - `Physics diagram`
  - `Physics chart`
không dùng:
  - `Embedded equation preview`

## 4.4. Physics text normalization rules
Chỉ áp cho `subject=physics`.

### Rule dictionary ban đầu
```text
điện trờ   -> điện trở
thừi điềm  -> thời điểm
kết quà    -> kết quả
khối lương -> khối lượng
phóng xạ̣  -> phóng xạ
nhiệ̣t     -> nhiệt
Mpa        -> MPa
c m²       -> cm²
```

### Unit cleanup
Chuẩn hóa:
- `kW.h`, `kWh` theo quy ước bạn chọn
- `cm²`, `m²`, `m³`
- `MPa`, `kPa`, `V`, `A`, `mA`
- `mol⁻¹` nếu xuất hiện trong Vật lý-Hóa liên ngành

### Physics inline notation rules
Chỉ cleanup spacing nhẹ:
- `v 0` -> `v₀` hoặc giữ nguyên tùy nguồn
- `x 1`, `T 2` chỉ sửa khi pattern chắc chắn
- không tự động semantic hóa bằng `<sub>/<sup>` trừ khi chắc chắn là chỉ số vật lý hiển thị hỏng

Khuyến nghị:
- ưu tiên giữ MathML nếu đã là MathML
- với plain text vật lý, chỉ sửa những case OCR/corruption rõ ràng

## 4.5. Physics acceptance criteria
- giữ nguyên số lượng MathML hiện có hoặc tăng
- preview count giảm
- `Equation.DSMT4` preview còn lại phải giảm về 0 nếu làm được
- `Visio.Drawing.15` không còn bị mô tả như equation preview
- Đề 1 và Đề 2 phải giảm lỗi nhiều nhất

---

# 5. ChemistryProfile — spec chi tiết

## 5.1. Mục tiêu
Dành cho:
- công thức hóa học
- ion
- số oxi hóa
- nồng độ
- cấu trúc hữu cơ
- đối tượng ChemDraw
- lời giải có biểu thức hóa học ngắn inline

Mục tiêu cụ thể:
- công thức hóa học ngắn inline phải hiển thị tự nhiên
- ChemDraw không còn nằm dưới dạng OLE preview thô
- MathType/Equation fallback còn sót phải được xử lý tiếp
- cleanup text corruption đặc thù Hóa

## 5.2. Nhánh riêng: chemical inline notation
Đây là phần quan trọng nhất của ChemistryProfile.

### Input patterns cần nhận diện
Các token hóa học ngắn trong text thường:

- phân tử:
  - `H2O`, `CO2`, `NH3`, `CH3COOH`
  - `H₂O`, `CO₂`, `NH₃`, `CH₃COOH`

- ion:
  - `Na+`, `Ca2+`, `SO4^2-`, `Al3+`
  - `Na⁺`, `Ca²⁺`, `SO₄²⁻`, `Al³⁺`

- nồng độ/đơn vị:
  - `mol.L-1`, `mol·L^-1`, `mol·L⁻¹`

- đồng vị:
  - `235U`, `14C`, `²³⁵U`, `¹⁴C`

- số oxi hóa:
  - `Fe3+`, `MnO4-`, `SO4^2-`

### Mục tiêu hiển thị
Không được để những token này:
- bị flatten như text thường
- bị đẩy lên một hàng thiếu tự nhiên
- bị vỡ baseline trong paragraph/table

### Chiến lược chuyển đổi
**Không ép tất cả sang MathML.**

Với token ngắn inline, ưu tiên semantic HTML:
- `H2O` -> `H<sub>2</sub>O`
- `SO4^2-` -> `SO<sub>4</sub><sup>2−</sup>`
- `Al3+` -> `Al<sup>3+</sup>`
- `mol·L^-1` -> `mol·L<sup>−1</sup>`

### Khi nào không nên rewrite
Không rewrite nếu:
- token đang nằm trong MathML đúng
- token nằm trong code/preformatted
- pattern không chắc là hóa học
- token có thể là notation của môn khác

## 5.3. Regex/pattern guideline cho ChemistryProfile

### Molecule with trailing digits
```regex
([A-Z][a-z]?)(\d+)
```

### Ion charge suffix
```regex
([A-Z][a-z]?(?:[A-Z][a-z]?\d*)*)(\^?\d*[+-])
```

### Sulfate-like group
```regex
([A-Z][a-z]?)(\d+)([A-Z][a-z]?)(\d+)(\^?\d*[+-])?
```

### Unit pattern
```regex
mol[·.]L(?:\^-?\d+|[⁻−]\d+)
```

Lưu ý:
- đây chỉ là gợi ý khởi đầu
- Codex phải implement detector an toàn hơn bằng tokenizer/context, không dùng regex mù toàn tài liệu

## 5.4. HTML output cho chemistry inline tokens
Tạo wrapper:
```html
<span class="chem-inline">H<sub>2</sub>SO<sub>4</sub></span>
```

hoặc:
```html
<span class="chem-inline">SO<sub>4</sub><sup>2−</sup></span>
```

### CSS bắt buộc
```css
.chem-inline sub,
.chem-inline sup {
  font-size: 0.75em;
  line-height: 0;
}
```

Có thể thêm:
```css
.chem-inline sup { vertical-align: super; }
.chem-inline sub { vertical-align: sub; }
```

Mục đích:
- chữ không bị phình hàng quá mức
- chỉ số trên/dưới nhìn tự nhiên

## 5.5. ChemDraw branch
Áp cho:
- `ChemDraw_x64.Document.6.0`
- `ChemDraw.Document.6.0`

### Hành động
- classify là `CHEMICAL_DIAGRAM`
- convert/render sang SVG nếu được
- fallback PNG
- HTML class:
  - `chem-diagram`
- alt:
  - `Chemical structure diagram`
  - `Chemical reaction scheme`

Không để alt như:
- `Embedded object preview (...)`

## 5.6. Chemistry text normalization rules
Chỉ áp cho `subject=chemistry`.

### Rule dictionary ban đầu
```text
Trọng giai đoạn    -> Trong giai đoạn
T lag              -> T là
Có 2 tố thí nghiệm -> Có 2 thí nghiệm
Ñaët               -> Đặt
taán               -> tấn
thế nhom           -> thế nhóm
```

### Symbol cleanup
Chuẩn hóa:
- mũi tên phản ứng
- dấu cộng ion
- dấu trừ điện tích
- đơn vị `mol·L⁻¹`
- số oxi hóa
- spacing quanh công thức inline

### Numeric corruption detection
Flag QA nếu thấy các biểu thức bất thường kiểu:
- `211,8*0 = 8472`
- `M = 29` trong ngữ cảnh đáng ra 290
- số bị mất chữ số sau normalize

Những case này:
- **không tự sửa bừa**
- đưa vào `qa.suspectedNumericCorruption`

## 5.7. Chemistry acceptance criteria
- giảm preview ChemDraw
- giảm preview Equation.DSMT4
- công thức hóa học inline nhìn tự nhiên
- không còn flatten Unicode sub/sup ở các chỗ phổ biến
- không làm hỏng câu văn thường
- không dùng chemistry rules ngoài `subject=chemistry`

---

# 6. Dispatcher spec

## 6.1. Subject selection
Pipeline nhận tham số:

```text
subject=generic|physics|chemistry|math|biology
```

## 6.2. Dispatch logic
```java
SubjectProfile profile = SubjectProfileFactory.create(subject);

core.extract(docx);
core.classify(objects);
core.convertEquations();
core.renderDiagrams();
profile.preprocess(ctx);
core.cleanupHtml();
profile.postprocess(ctx);
core.runQa();
profile.contributeQa(report, ctx);
```

---

# 7. QA spec cho 2 profile này

## 7.1. Physics QA fields
```json
{
  "subject": "physics",
  "mathml_formula_count": 0,
  "preview_count": 0,
  "equation_dsmt4_preview_count": 0,
  "visio_preview_count": 0,
  "emf_count": 0,
  "wmf_count": 0,
  "text_fix_count": 0,
  "remaining_corruption_hits": [],
  "per_exam": {}
}
```

## 7.2. Chemistry QA fields
```json
{
  "subject": "chemistry",
  "mathml_formula_count": 0,
  "preview_count": 0,
  "equation_dsmt4_preview_count": 0,
  "chemdraw_preview_count": 0,
  "chemical_inline_fix_count": 0,
  "text_fix_count": 0,
  "suspected_numeric_corruption": [],
  "remaining_corruption_hits": [],
  "per_exam": {}
}
```

## 7.3. QA Markdown summary
Bắt buộc có:
- tổng quan
- improvements before/after
- unresolved list
- publish verdict

---

# 8. Quy tắc tìm package mới

Nếu cần thêm package mới để triển khai 2 profile này, Codex phải tìm theo thứ tự:

1. **upstream repo / stack đang dùng**
   - transpect
   - Apache POI
   - dependency hiện có

2. **registry chính thức**
   - Maven Central
   - npm
   - PyPI

3. **GitHub repo còn maintain**
   - có release
   - có issue activity
   - docs rõ

4. **community fork**
   - chỉ khi upstream không đủ

5. **last resort**
   - package cũ, ít maintain, workaround tạm

Ngoài ra:
- ưu tiên open source
- ưu tiên tương thích với nhánh hiện tại
- không thêm package làm đổi generation của pipeline nếu chưa có lý do mạnh

---

# 9. Deliverables Codex phải trả về

## 9.1. Code
- `SubjectProfile` abstraction
- `PhysicsProfile`
- `ChemistryProfile`
- branch `chemical inline notation`
- improved classifier for `Visio` / `ChemDraw` / `Equation.DSMT4`

## 9.2. Reports
- QA JSON
- QA Markdown
- before/after diff summary

## 9.3. Demo runs
Ít nhất:
- 1 file Physics
- 1 file Chemistry

---

# 10. Phán quyết triển khai

Nên làm theo thứ tự này:

### Phase 1
- refactor khung `SubjectProfile`
- implement `PhysicsProfile`
- giữ `ChemistryProfile` skeleton

### Phase 2
- implement `ChemistryInlineNotationRule`
- thêm `ChemDrawPostProcessor`
- thêm QA fields chemistry

### Phase 3
- thêm cache improvements
- thêm `MathTypeBatchConverter`
- thêm unresolved object report

### Phase 4
- tinh chỉnh dictionary và heuristics
- benchmark trước/sau

---

# PSEUDO-CODE SPEC — IMPLEMENTATION LAYER

## 1. Factory và entrypoint

### 1.1. `SubjectProfileFactory`

```java
public final class SubjectProfileFactory {
    public static SubjectProfile create(Subject subject) {
        return switch (subject) {
            case PHYSICS -> new PhysicsProfile();
            case CHEMISTRY -> new ChemistryProfile();
            case MATH -> new MathProfile();
            case BIOLOGY -> new BiologyProfile();
            case GENERIC -> new GenericProfile();
        };
    }
}
```

### 1.2. `ConversionPipelineRunner`

```java
public final class ConversionPipelineRunner {
    private final CoreExtractor extractor;
    private final CoreClassifier classifier;
    private final EquationPipeline equationPipeline;
    private final DiagramPipeline diagramPipeline;
    private final HtmlAssembler htmlAssembler;
    private final HtmlCleanupPipeline htmlCleanupPipeline;
    private final QaCollector qaCollector;

    public ConversionResult run(Path docxPath, Subject subject, ConversionConfig config) {
        SubjectProfile profile = SubjectProfileFactory.create(subject);

        DocumentContext ctx = new DocumentContext(docxPath, subject, config);

        extractor.extract(ctx);
        classifier.classifyAll(ctx);

        profile.preprocess(ctx);

        equationPipeline.process(ctx);
        diagramPipeline.process(ctx);

        htmlAssembler.assemble(ctx);
        htmlCleanupPipeline.cleanup(ctx);

        profile.postprocess(ctx);

        qaCollector.collect(ctx);
        profile.contributeQa(ctx.getQaReport(), ctx);

        return new ConversionResult(ctx.getHtml(), ctx.getQaReport());
    }
}
```

## 2. Core classifier

```java
public final class CoreClassifier {
    private final List<ObjectClassifierRule> rules;

    public void classifyAll(DocumentContext ctx) {
        for (EmbeddedObjectRef ref : ctx.getObjects()) {
            ClassifiedObject classified = classify(ref, ctx);
            ctx.addClassifiedObject(classified);
        }
    }

    private ClassifiedObject classify(EmbeddedObjectRef ref, DocumentContext ctx) {
        for (ObjectClassifierRule rule : rules) {
            if (rule.matches(ref, ctx)) {
                return rule.classify(ref, ctx);
            }
        }
        return ClassifiedObject.unknown(ref);
    }
}
```

```java
public interface ObjectClassifierRule {
    boolean matches(EmbeddedObjectRef ref, DocumentContext ctx);
    ClassifiedObject classify(EmbeddedObjectRef ref, DocumentContext ctx);
}
```

## 3. Equation pipeline

```java
public final class EquationPipeline {
    private final EquationSourceResolver sourceResolver;
    private final EquationHandler ommlHandler;
    private final EquationHandler mathTypeHandler;
    private final EquationHtmlEmitter htmlEmitter;

    public void process(DocumentContext ctx) {
        for (ClassifiedObject obj : ctx.getClassifiedObjects()) {
            if (obj.kind() != ObjectKind.EQUATION) continue;

            EquationSource source = sourceResolver.resolve(obj, ctx);
            EquationResult result = switch (source.type()) {
                case OMML -> ommlHandler.convert(source, ctx.getConversionContext());
                case MATHTYPE_WMF, MATHTYPE_BIN, MATHTYPE_OLE -> mathTypeHandler.convert(source, ctx.getConversionContext());
                default -> EquationResult.unresolved(source);
            };

            ctx.addEquationResult(result);
            htmlEmitter.register(result, ctx);
        }
    }
}
```

```java
public final class MathTypeEquationHandler implements EquationHandler {
    private final MathMlSidecarCache cache;
    private final MathTypeBatchConverter batchConverter;

    public EquationResult convert(EquationSource source, ConversionContext ctx) {
        String hash = source.contentHash();

        if (cache.hasValidMathMl(hash)) {
            return EquationResult.fromMathMl(cache.load(hash), source, true);
        }

        MathMlResult converted = batchConverter.convert(source, ctx);
        if (converted.isSuccess()) {
            cache.store(hash, converted.getMathMl());
            return EquationResult.fromMathMl(converted.getMathMl(), source, false);
        }

        return EquationResult.previewFallback(source);
    }
}
```

## 4. Diagram pipeline

```java
public final class DiagramPipeline {
    private final DiagramRenderer renderer;
    private final DiagramHtmlEmitter emitter;

    public void process(DocumentContext ctx) {
        for (ClassifiedObject obj : ctx.getClassifiedObjects()) {
            if (obj.kind() != ObjectKind.DIAGRAM &&
                obj.kind() != ObjectKind.CHART &&
                obj.kind() != ObjectKind.CHEMICAL_DIAGRAM &&
                obj.kind() != ObjectKind.GENERIC_IMAGE) {
                continue;
            }

            DiagramRenderResult result = renderer.render(obj, ctx);
            ctx.addDiagramResult(result);
            emitter.register(result, ctx);
        }
    }
}
```

## 5. HTML cleanup

```java
public final class HtmlCleanupPipeline {
    private final List<HtmlCleanupRule> rules;

    public void cleanup(DocumentContext ctx) {
        for (HtmlCleanupRule rule : rules) {
            rule.apply(ctx);
        }
    }
}
```

Các rule bắt buộc:
- `SeparateImageFromFollowingTextRule`
- `InlineDisplayMathBoundaryRule`
- `MisleadingPreviewAltCleanupRule`
- `InvalidParagraphStructureRule`

## 6. `PhysicsProfile`

```java
public final class PhysicsProfile implements SubjectProfile {
    private final List<NormalizationRule> normalizationRules = List.of(
        new PhysicsTextDictionaryRule(),
        new PhysicsUnitCleanupRule(),
        new PhysicsSafeInlineIndexRule()
    );

    @Override
    public String getName() { return "physics"; }

    @Override
    public SubjectRules getRules() {
        return SubjectRules.physics();
    }

    @Override
    public void preprocess(DocumentContext ctx) {}

    @Override
    public void postprocess(DocumentContext ctx) {
        for (NormalizationRule rule : normalizationRules) {
            HtmlWalker.walk(ctx.getHtml(), node -> {
                if (rule.applies(ctx, node)) {
                    rule.apply(ctx, node);
                }
            });
        }
    }

    @Override
    public void contributeQa(QaReport report, DocumentContext ctx) {
        report.setSubject("physics");
    }
}
```

## 7. `ChemistryProfile`

```java
public final class ChemistryProfile implements SubjectProfile {
    private final List<NormalizationRule> normalizationRules = List.of(
        new ChemistryTextDictionaryRule(),
        new ChemistryInlineNotationRule(),
        new ChemistryUnitNormalizationRule(),
        new ChemistrySuspiciousNumericRule()
    );

    @Override
    public String getName() { return "chemistry"; }

    @Override
    public SubjectRules getRules() {
        return SubjectRules.chemistry();
    }

    @Override
    public void preprocess(DocumentContext ctx) {}

    @Override
    public void postprocess(DocumentContext ctx) {
        for (NormalizationRule rule : normalizationRules) {
            HtmlWalker.walk(ctx.getHtml(), node -> {
                if (rule.applies(ctx, node)) {
                    rule.apply(ctx, node);
                }
            });
        }
    }

    @Override
    public void contributeQa(QaReport report, DocumentContext ctx) {
        report.setSubject("chemistry");
    }
}
```

## 8. `ChemistryInlineNotationRule`

```java
public final class ChemistryInlineNotationRule implements NormalizationRule {
    private final ChemistryTokenDetector detector = new ChemistryTokenDetector();
    private final ChemistryHtmlFormatter formatter = new ChemistryHtmlFormatter();

    public boolean applies(DocumentContext ctx, HtmlNodeRef node) {
        return node.isTextNode() && !node.isInsideMath() && !node.isInsideCodeLike();
    }

    public void apply(DocumentContext ctx, HtmlNodeRef node) {
        List<ChemToken> tokens = detector.detect(node.getText());
        if (tokens.isEmpty()) return;

        HtmlFragment fragment = formatter.format(node.getText(), tokens);
        node.replaceWith(fragment);

        ctx.getQaReport().incrementChemistryInlineFixCount(tokens.size());
    }
}
```

## 9. `QaCollector`

```java
public final class QaCollector {
    public void collect(DocumentContext ctx) {
        QaReport qa = ctx.getQaReport();

        qa.setTotalMathMlFormulaCount(countMathMl(ctx));
        qa.setTotalPreviewCount(countPreviews(ctx));
        qa.setEquationDsmt4PreviewCount(countByProgId(ctx, "Equation.DSMT4"));
        qa.setVisioPreviewCount(countByProgId(ctx, "Visio.Drawing.15"));
        qa.setChemDrawPreviewCount(countChemDraw(ctx));
        qa.setEmfCount(countByExtension(ctx, ".emf"));
        qa.setWmfCount(countByExtension(ctx, ".wmf"));

        qa.setExamSummaries(buildPerExamSummaries(ctx));
        qa.setUnresolvedObjects(findUnresolvedObjects(ctx));
    }
}
```

## 10. `MathMlSidecarCache`

```java
public final class MathMlSidecarCache {
    private final Path cacheDir;

    public boolean hasValidMathMl(String hash) {
        Path p = cacheDir.resolve(hash + ".mml");
        return Files.exists(p) && isValidMathMl(p);
    }

    public String load(String hash) {
        return Files.readString(cacheDir.resolve(hash + ".mml"));
    }

    public void store(String hash, String mathMl) {
        Files.writeString(cacheDir.resolve(hash + ".mml"), mathMl);
    }
}
```

## 11. CSS bắt buộc

```css
.chem-inline sub,
.chem-inline sup {
  font-size: 0.75em;
  line-height: 0;
}

.chem-inline sup { vertical-align: super; }
.chem-inline sub { vertical-align: sub; }

.physics-diagram,
.physics-chart,
.chem-diagram {
  max-width: 100%;
  height: auto;
  display: block;
}

.math-inline {
  display: inline;
}

.math-block {
  display: block;
  margin: 0.5em 0;
}
```

## 12. Quy tắc tìm package mới

Nếu Codex cần thêm package mới để triển khai spec này, phải tìm theo thứ tự:

1. **upstream repo / stack đang dùng**
   - transpect
   - Apache POI
   - dependency hiện có

2. **registry chính thức**
   - Maven Central
   - npm
   - PyPI

3. **GitHub maintained repo**
   - có docs, release, issue activity

4. **community fork**

5. **last resort**

## 13. Acceptance checklist cho Codex

### Physics
- giữ nguyên chất lượng MathML hiện có
- preview còn lại giảm hoặc sạch hơn
- diagram không còn alt/class sai kiểu equation
- text corruption giảm

### Chemistry
- chemical inline notation hiển thị tự nhiên
- ChemDraw preview giảm
- Equation.DSMT4 preview giảm
- text corruption giảm
- không chemistry hóa các môn khác
