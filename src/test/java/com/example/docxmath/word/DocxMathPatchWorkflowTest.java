package com.example.docxmath.word;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class DocxMathPatchWorkflowTest {
    @Test
    void leavesNativeOmmlUntouched() throws Exception {
        Path tempDir = Files.createTempDirectory("docx-patch-native");
        Path input = tempDir.resolve("native.docx");
        Path output = tempDir.resolve("native-out.docx");
        writeMinimalDocx(input, nativeOmmlDocumentXml());

        DocxMathPatchMain.PatchSummary summary =
                new DocxMathPatchMain(ManifestMathSidecarRepository.empty()).patch(input, output);

        String xml = readDocumentXml(output);
        assertEquals(1, summary.totalOccurrences());
        assertEquals(1, summary.nativeOmmlUntouched());
        assertEquals(0, summary.patchedBlocks());
        assertTrue(xml.contains("<m:oMath>"));
        assertFalse(xml.contains("<w:object"));
    }

    @Test
    void patchesStandaloneOleObjectWhenManifestMatches() throws Exception {
        Path tempDir = Files.createTempDirectory("docx-patch-ole");
        Path input = tempDir.resolve("ole.docx");
        Path output = tempDir.resolve("ole-out.docx");
        writeMinimalDocx(input, oleObjectDocumentXml());

        Path manifestDir = tempDir.resolve("sidecars");
        Files.createDirectories(manifestDir.resolve("mathml"));
        Files.writeString(
                manifestDir.resolve("manifest.tsv"),
                "/word/embeddings/oleObject1.bin\tmathml/eq1.mathml\n",
                StandardCharsets.UTF_8
        );
        Files.writeString(
                manifestDir.resolve("mathml/eq1.mathml"),
                "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi><mo>+</mo><mn>1</mn></math>",
                StandardCharsets.UTF_8
        );

        DocxMathPatchMain.PatchSummary summary = new DocxMathPatchMain(
                ManifestMathSidecarRepository.load(manifestDir.resolve("manifest.tsv"))
        ).patch(input, output);

        String xml = readDocumentXml(output);
        assertEquals(1, summary.patchedBlocks());
        assertEquals(0, summary.unresolved());
        assertTrue(xml.contains("oMathPara"));
        assertTrue(xml.contains("x+1"));
        assertFalse(xml.contains("<w:object"));
    }

    @Test
    void keepsOleObjectWhenManifestIsUnresolved() throws Exception {
        Path tempDir = Files.createTempDirectory("docx-patch-unresolved");
        Path input = tempDir.resolve("ole.docx");
        Path output = tempDir.resolve("ole-out.docx");
        writeMinimalDocx(input, oleObjectDocumentXml());

        DocxMathPatchMain.PatchSummary summary =
                new DocxMathPatchMain(ManifestMathSidecarRepository.empty()).patch(input, output);

        String xml = readDocumentXml(output);
        assertEquals(1, summary.unresolved());
        assertEquals(0, summary.patchedBlocks());
        assertTrue(xml.contains("<w:object"));
    }

    private static void writeMinimalDocx(Path path, String documentXml) throws IOException {
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(path))) {
            put(zip, "[Content_Types].xml", contentTypesXml());
            put(zip, "_rels/.rels", packageRelationshipsXml());
            put(zip, "word/document.xml", documentXml);
            put(zip, "word/_rels/document.xml.rels", documentRelationshipsXml());
            put(zip, "word/embeddings/oleObject1.bin", "dummy");
            put(zip, "word/media/image1.wmf", "dummy");
        }
    }

    private static void put(ZipOutputStream zip, String entryName, String text) throws IOException {
        zip.putNextEntry(new ZipEntry(entryName));
        zip.write(text.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }

    private static String readDocumentXml(Path docx) throws IOException {
        try (var zip = new java.util.zip.ZipFile(docx.toFile())) {
            return new String(zip.getInputStream(zip.getEntry("word/document.xml")).readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static String contentTypesXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                  <Default Extension="xml" ContentType="application/xml"/>
                  <Default Extension="bin" ContentType="application/vnd.openxmlformats-officedocument.oleObject"/>
                  <Default Extension="wmf" ContentType="image/x-wmf"/>
                  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                </Types>
                """;
    }

    private static String packageRelationshipsXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                </Relationships>
                """;
    }

    private static String documentRelationshipsXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rIdOle" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" Target="embeddings/oleObject1.bin"/>
                  <Relationship Id="rIdPreview" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.wmf"/>
                </Relationships>
                """;
    }

    private static String nativeOmmlDocumentXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
                  <w:body>
                    <w:p>
                      <m:oMath>
                        <m:r><m:t>x</m:t></m:r>
                      </m:oMath>
                    </w:p>
                    <w:sectPr>
                      <w:pgSz w:w="12240" w:h="15840"/>
                      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
                    </w:sectPr>
                  </w:body>
                </w:document>
                """;
    }

    private static String oleObjectDocumentXml() {
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                            xmlns:o="urn:schemas-microsoft-com:office:office"
                            xmlns:v="urn:schemas-microsoft-com:vml"
                            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
                  <w:body>
                    <w:p>
                      <w:r>
                        <w:object>
                          <v:shape id="_x0000_i1025" type="#_x0000_t75" o:ole="">
                            <v:imagedata r:id="rIdPreview" o:title=""/>
                          </v:shape>
                          <o:OLEObject Type="Embed" ProgID="Equation.DSMT4" ShapeID="_x0000_i1025" DrawAspect="Content" ObjectID="_1" r:id="rIdOle"/>
                        </w:object>
                      </w:r>
                    </w:p>
                    <w:sectPr>
                      <w:pgSz w:w="12240" w:h="15840"/>
                      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
                    </w:sectPr>
                  </w:body>
                </w:document>
                """;
    }
}
