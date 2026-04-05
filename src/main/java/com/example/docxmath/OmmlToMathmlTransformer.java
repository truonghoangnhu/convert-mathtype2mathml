package com.example.docxmath;

import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.QName;
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

/**
 * Converts Word OMML fragments into MathML using the open-source XSLT shipped as a project resource.
 */
public final class OmmlToMathmlTransformer {
    private static final QName OMML2MML_MODE = new QName("omml2mml");

    private final Processor processor;
    private final XsltExecutable executable;

    public OmmlToMathmlTransformer() {
        try {
            this.processor = new Processor(false);
            XsltCompiler compiler = processor.newXsltCompiler();
            try (var xsltStream = OmmlToMathmlTransformer.class.getResourceAsStream("/omml2mml.xsl")) {
                if (xsltStream == null) {
                    throw new IllegalStateException("Missing resource: /omml2mml.xsl");
                }
                this.executable = compiler.compile(new StreamSource(xsltStream));
            }
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to initialize OMML->MathML transformer", ex);
        }
    }

    public String transformOmmlToMathml(String ommlXml) throws SaxonApiException {
        XdmNode source = processor.newDocumentBuilder().build(new StreamSource(new StringReader(ommlXml)));
        Xslt30Transformer transformer = executable.load30();
        transformer.setInitialMode(OMML2MML_MODE);

        XdmDestination destination = new XdmDestination();
        transformer.applyTemplates(source, destination);

        StringWriter out = new StringWriter();
        Serializer serializer = processor.newSerializer(out);
        serializer.setOutputProperty(Serializer.Property.OMIT_XML_DECLARATION, "yes");
        serializer.setOutputProperty(Serializer.Property.INDENT, "no");
        serializer.serializeXdmValue(destination.getXdmNode());
        return out.toString().trim();
    }
}
