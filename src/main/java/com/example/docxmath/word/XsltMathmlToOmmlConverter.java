package com.example.docxmath.word;

import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.SaxonApiException;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XdmDestination;
import net.sf.saxon.s9api.XdmNode;
import net.sf.saxon.s9api.Xslt30Transformer;
import net.sf.saxon.s9api.XsltCompiler;
import net.sf.saxon.s9api.XsltExecutable;

import javax.xml.transform.stream.StreamSource;
import java.io.StringReader;
import java.io.StringWriter;

public final class XsltMathmlToOmmlConverter implements MathmlToOmmlConverter {
    private final Processor processor;
    private final XsltExecutable executable;

    public XsltMathmlToOmmlConverter() {
        try {
            this.processor = new Processor(false);
            XsltCompiler compiler = processor.newXsltCompiler();
            try (var xsltStream = XsltMathmlToOmmlConverter.class.getResourceAsStream("/mml2omml.xsl")) {
                if (xsltStream == null) {
                    throw new IllegalStateException("Missing resource: /mml2omml.xsl");
                }
                this.executable = compiler.compile(new StreamSource(xsltStream));
            }
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to initialize MathML->OMML transformer", ex);
        }
    }

    @Override
    public String convert(String normalizedMathml) {
        if (normalizedMathml == null || normalizedMathml.isBlank()) {
            return null;
        }
        try {
            XdmNode source = processor.newDocumentBuilder().build(new StreamSource(new StringReader(normalizedMathml)));
            Xslt30Transformer transformer = executable.load30();
            XdmDestination destination = new XdmDestination();
            transformer.applyTemplates(source, destination);

            StringWriter out = new StringWriter();
            Serializer serializer = processor.newSerializer(out);
            serializer.setOutputProperty(Serializer.Property.OMIT_XML_DECLARATION, "yes");
            serializer.setOutputProperty(Serializer.Property.INDENT, "no");
            serializer.serializeXdmValue(destination.getXdmNode());
            return out.toString().trim();
        } catch (SaxonApiException ex) {
            throw new IllegalStateException("Failed to convert MathML to OMML", ex);
        }
    }
}
