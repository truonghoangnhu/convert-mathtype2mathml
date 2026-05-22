package com.example.docxmath;

import com.example.docxmath.word.BasicMathmlNormalizer;
import com.example.docxmath.word.XsltMathmlToOmmlConverter;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.ByteArrayOutputStream;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class LatexToOmmlCli {
    private static final String MATHML_NS = "http://www.w3.org/1998/Math/MathML";
    private static final String OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math";
    private static final Pattern MATH_ELEMENT_PATTERN = Pattern.compile("(?is)<math\\b.*?</math>");

    private LatexToOmmlCli() {
    }

    public static void main(String[] args) {
        try {
            String latex = new String(System.in.readAllBytes(), StandardCharsets.UTF_8).trim();
            if (latex.isBlank()) {
                throw new IllegalArgumentException("No LaTeX received on stdin");
            }
            boolean display = "1".equals(System.getenv().getOrDefault("DOCX_MATH_DISPLAY", "0").trim());
            String mathml = latexToMathml(latex, display);
            String normalizedMathml = new BasicMathmlNormalizer().normalize(stripPandocSemantics(mathml));
            String omml = new XsltMathmlToOmmlConverter().convert(normalizedMathml);
            String output = validateAndPrefixOmml(omml, display);
            System.out.print(output);
        } catch (Exception ex) {
            System.err.println("LaTeX to OMML conversion failed: " + ex.getMessage());
            System.exit(1);
        }
    }

    static String latexToMathml(String latex, boolean display) throws Exception {
        String pandoc = System.getenv().getOrDefault("PANDOC_CMD", "pandoc").trim();
        if (pandoc.isBlank()) {
            throw new IllegalArgumentException("PANDOC_CMD is empty");
        }

        String source = (display ? "\\[" : "\\(") + latex + (display ? "\\]" : "\\)") + "\n";
        List<String> command = splitCommand(pandoc);
        command.add("-f");
        command.add("latex");
        command.add("-t");
        command.add("html");
        command.add("--mathml");

        Process process = new ProcessBuilder(command).start();
        try (var stdin = process.getOutputStream()) {
            stdin.write(source.getBytes(StandardCharsets.UTF_8));
        }

        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        ByteArrayOutputStream stderr = new ByteArrayOutputStream();
        process.getInputStream().transferTo(stdout);
        process.getErrorStream().transferTo(stderr);
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            String diagnostic = stderr.toString(StandardCharsets.UTF_8).trim();
            throw new IllegalStateException("pandoc exited " + exitCode + (diagnostic.isBlank() ? "" : ": " + diagnostic));
        }

        String html = stdout.toString(StandardCharsets.UTF_8);
        Matcher matcher = MATH_ELEMENT_PATTERN.matcher(html);
        if (!matcher.find()) {
            throw new IllegalStateException("pandoc output did not contain a MathML <math> element");
        }
        return matcher.group(0).trim();
    }

    private static List<String> splitCommand(String command) {
        List<String> out = new ArrayList<>();
        Matcher matcher = Pattern.compile("\"([^\"]*)\"|'([^']*)'|\\S+").matcher(command);
        while (matcher.find()) {
            String doubleQuoted = matcher.group(1);
            String singleQuoted = matcher.group(2);
            out.add(doubleQuoted != null ? doubleQuoted : singleQuoted != null ? singleQuoted : matcher.group());
        }
        if (out.isEmpty()) {
            out.add(command);
        }
        return out;
    }

    static String stripPandocSemantics(String mathml) throws Exception {
        Document document = parseXml(mathml);
        NodeList semanticsNodes = document.getElementsByTagNameNS(MATHML_NS, "semantics");
        for (int i = semanticsNodes.getLength() - 1; i >= 0; i--) {
            Element semantics = (Element) semanticsNodes.item(i);
            Element replacement = firstMathElementChild(semantics);
            if (replacement == null) {
                continue;
            }
            Node imported = document.importNode(replacement, true);
            semantics.getParentNode().replaceChild(imported, semantics);
        }
        return serializeXml(document);
    }

    private static Element firstMathElementChild(Element parent) {
        NodeList children = parent.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE && MATHML_NS.equals(child.getNamespaceURI())) {
                return (Element) child;
            }
        }
        return null;
    }

    static String validateAndPrefixOmml(String omml, boolean display) throws Exception {
        Document document = parseXml(omml);
        Element root = document.getDocumentElement();
        if (root == null || !OMML_NS.equals(root.getNamespaceURI()) || !"oMath".equals(root.getLocalName())) {
            throw new IllegalStateException("MathML->OMML converter did not return m:oMath");
        }
        prefixOmmlElements(document, root);
        root.setAttributeNS(XMLConstants.XMLNS_ATTRIBUTE_NS_URI, "xmlns:m", OMML_NS);
        String prefixed = serializeXml(document);
        if (!display) {
            return prefixed;
        }
        String wrapped = "<m:oMathPara xmlns:m=\"" + OMML_NS + "\">" + prefixed + "</m:oMathPara>";
        validateOmmlRoot(wrapped);
        return wrapped;
    }

    private static void prefixOmmlElements(Document document, Node node) {
        if (node.getNodeType() == Node.ELEMENT_NODE && OMML_NS.equals(node.getNamespaceURI())) {
            document.renameNode(node, OMML_NS, "m:" + node.getLocalName());
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            prefixOmmlElements(document, children.item(i));
        }
    }

    private static void validateOmmlRoot(String omml) throws Exception {
        Document document = parseXml(omml);
        Element root = document.getDocumentElement();
        String localName = root == null ? "" : root.getLocalName();
        if (root == null || !OMML_NS.equals(root.getNamespaceURI()) || !List.of("oMath", "oMathPara").contains(localName)) {
            throw new IllegalStateException(
                    "OMML root must be m:oMath or m:oMathPara, got "
                            + (localName == null ? "" : localName).toLowerCase(Locale.ROOT)
            );
        }
    }

    private static Document parseXml(String xml) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        return factory.newDocumentBuilder().parse(new InputSource(new StringReader(xml == null ? "" : xml.trim())));
    }

    private static String serializeXml(Document document) throws Exception {
        TransformerFactory factory = TransformerFactory.newInstance();
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        Transformer transformer = factory.newTransformer();
        transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
        transformer.setOutputProperty(OutputKeys.INDENT, "no");
        StringWriter out = new StringWriter();
        transformer.transform(new DOMSource(document), new StreamResult(out));
        return out.toString().trim();
    }
}
