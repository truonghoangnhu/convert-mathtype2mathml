package com.example.docxmath;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertTrue;

final class DocxToHtmlMalformedRelationshipRegressionTest {

    @Test
    void continuesConversionWhenRelationshipTargetPartNameIsInvalid() throws Exception {
        Path tempDir = Files.createTempDirectory("docx-html-malformed-rel-test");
        Path input = tempDir.resolve("input-malformed-rel.docx");
        Path output = tempDir.resolve("output.html");
        writeMalformedRelationshipDocx(input);

        DocxToHtmlConverter converter =
                new DocxToHtmlConverter(false, MathmlSidecarRegistry.empty(), Subject.CHEMISTRY, OutputMode.PUBLISH);

        PrintStream originalErr = System.err;
        ByteArrayOutputStream errBuffer = new ByteArrayOutputStream();
        try (PrintStream captureErr = new PrintStream(errBuffer, true, StandardCharsets.UTF_8)) {
            System.setErr(captureErr);
            converter.convert(input, output);
        } finally {
            System.setErr(originalErr);
        }

        assertTrue(Files.exists(output), "conversion should still produce HTML output");
        String html = Files.readString(output, StandardCharsets.UTF_8);
        assertTrue(html.contains("Prefix"), "expected text before malformed object should remain");
        assertTrue(html.contains("Suffix"), "expected text after malformed object should remain");

        String stderr = errBuffer.toString(StandardCharsets.UTF_8);
        assertTrue(stderr.contains("skipping malformed relationship"), "expected malformed relationship warning");
        assertTrue(stderr.contains("relId=rIdBad"), "expected warning to include relId context");
        assertTrue(stderr.contains("Conversion continues"), "expected warning to confirm conversion continues");
    }

    private static void writeMalformedRelationshipDocx(Path docxPath) throws IOException {
        Files.createDirectories(docxPath.toAbsolutePath().normalize().getParent());
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(docxPath))) {
            writeZipEntry(
                    zip,
                    "[Content_Types].xml",
                    """
                            <?xml version="1.0" encoding="UTF-8"?>
                            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                              <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                              <Default Extension="xml" ContentType="application/xml"/>
                              <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                            </Types>
                            """
            );
            writeZipEntry(
                    zip,
                    "_rels/.rels",
                    """
                            <?xml version="1.0" encoding="UTF-8"?>
                            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                            </Relationships>
                            """
            );
            writeZipEntry(
                    zip,
                    "word/_rels/document.xml.rels",
                    """
                            <?xml version="1.0" encoding="UTF-8"?>
                            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                              <Relationship Id="rIdBad" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="NULL"/>
                            </Relationships>
                            """
            );
            writeZipEntry(
                    zip,
                    "word/document.xml",
                    """
                            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                                        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                              <w:body>
                                <w:p>
                                  <w:r><w:t>Prefix </w:t></w:r>
                                  <w:r>
                                    <w:drawing>
                                      <a:blip r:embed="rIdBad"/>
                                    </w:drawing>
                                  </w:r>
                                  <w:r><w:t> Suffix</w:t></w:r>
                                </w:p>
                              </w:body>
                            </w:document>
                            """
            );
        }
    }

    private static void writeZipEntry(ZipOutputStream zip, String name, String value) throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        zip.write(value.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }
}
