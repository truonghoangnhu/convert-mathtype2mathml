package com.example.docxmath.word;
import org.junit.jupiter.api.Test;
import org.w3c.dom.*;
import javax.xml.parsers.DocumentBuilderFactory;
import org.xml.sax.InputSource;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class OperatorBoundaryReviewTest {
  static final String M="http://schemas.openxmlformats.org/officeDocument/2006/math";
  static Element convert(String s)throws Exception {
    String o=new XsltMathmlToOmmlConverter().convert(new BasicMathmlNormalizer().normalize(s));
    var f=DocumentBuilderFactory.newInstance();f.setNamespaceAware(true);
    return f.newDocumentBuilder().parse(new InputSource(new StringReader(o))).getDocumentElement();
  }
  static List<Element> runs(Element e){var a=new ArrayList<Element>();var n=e.getElementsByTagNameNS(M,"r");for(int i=0;i<n.getLength();i++)a.add((Element)n.item(i));return a;}
  static String text(Element e){var n=e.getElementsByTagNameNS(M,"t");var s=new StringBuilder();for(int i=0;i<n.getLength();i++)s.append(n.item(i).getTextContent());return s.toString();}
  static String math(String s){return "<math xmlns='http://www.w3.org/1998/Math/MathML'>"+s+"</math>";}
  @Test void realPriceKeepsRelationAndAdditionRuns()throws Exception {
    String s;try(var in=getClass().getResourceAsStream("/review/real-price.mathml")){s=new String(in.readAllBytes(),StandardCharsets.UTF_8);}
    var o=convert(s);assertEquals("p=7+0,25(6)=8,5",text(o));
    assertEquals(2,runs(o).stream().filter(r->text(r).equals("=")).count());
    assertEquals(1,runs(o).stream().filter(r->text(r).equals("+")).count());
    for(var r:runs(o))if(Set.of("=","+").contains(text(r))){assertEquals(0,r.getElementsByTagNameNS(M,"nor").getLength());assertEquals(0,r.getElementsByTagNameNS(M,"lit").getLength());}
  }
  @Test void literalEqualsStaysNormalText()throws Exception {
    var o=convert(math("<mi>x</mi><mo>=</mo><mn>1</mn><mtext>=</mtext>"));
    var equal=runs(o).stream().filter(r->text(r).equals("=")).toList();assertEquals(2,equal.size());
    assertEquals(0,equal.get(0).getElementsByTagNameNS(M,"nor").getLength());
    assertEquals(1,equal.get(1).getElementsByTagNameNS(M,"nor").getLength());
  }
  @Test void consecutiveOperatorsAreNotCollectedTogether()throws Exception {
    var o=convert(math("<mi>x</mi><mo>=</mo><mo>−</mo><mn>2</mn>"));
    assertEquals(List.of("x","=","−","2"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void identifierGroupingRemainsAvailable()throws Exception {
    var o=convert(math("<mi>s</mi><mi>i</mi><mi>n</mi><mo>+</mo><mn>1</mn>"));
    assertEquals(List.of("sin","+","1"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void leadingAndTrailingOperatorsKeepOwnRuns()throws Exception {
    var o=convert(math("<mo>−</mo><mi>x</mi><mo>!</mo>"));
    assertEquals(List.of("−","x","!"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void multicharacterOperatorNotSplitInternally()throws Exception {
    var o=convert(math("<mi>x</mi><mo>&lt;=</mo><mn>2</mn>"));
    assertEquals(List.of("x","<=","2"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void invisibleOperatorPolicyIsExplicit()throws Exception {
    var o=convert(math("<mi>f</mi><mo>\u2061</mo><mi>x</mi><mo>\u2062</mo><mn>2</mn>"));
    assertEquals("f\u2061x2",text(o)); // Existing OutputText policy removes U+2062, not U+2061.
    assertTrue(runs(o).stream().anyMatch(r -> text(r).equals("\u2061")));
  }
  @Test void stringLiteralIsNotPromotedToOperator()throws Exception {
    var o=convert(math("<ms>=</ms><mo>+</mo><mn>1</mn>"));
    assertEquals(1,runs(o).stream().filter(r -> text(r).equals("+")).count());
    assertTrue(text(o).contains("="));
    assertEquals(0,runs(o).stream().filter(r -> text(r).equals("=")).count());
  }
  @Test void glyphOperatorDoesNotSwallowFollowingTokens()throws Exception {
    var o=convert(math("<mi>x</mi><mo><mglyph alt='+'/></mo><mn>2</mn>"));
    assertTrue(text(o).startsWith("x"));assertTrue(text(o).endsWith("2"));
    assertEquals(1,runs(o).stream().filter(r -> text(r).equals("2")).count());
  }

  static List<String> firstSuperscriptRuns(Element o) {
    var s=(Element)o.getElementsByTagNameNS(M,"sup").item(0);
    return runs(s).stream().map(OperatorBoundaryReviewTest::text).toList();
  }
  @Test void realIonChargesKeepNumericPostfixTogetherForWriter()throws Exception {
    String s;try(var in=getClass().getResourceAsStream("/review/real-ions.mathml")){s=new String(in.readAllBytes(),StandardCharsets.UTF_8);}
    var o=convert(s);assertEquals("Mg2+,Cu2+,Zn2+,Ag+",text(o));
    var supers=o.getElementsByTagNameNS(M,"sup");assertEquals(4,supers.getLength());
    for(int i=0;i<3;i++)assertEquals(List.of("2+"),runs((Element)supers.item(i)).stream().map(OperatorBoundaryReviewTest::text).toList());
    assertEquals(List.of("+"),runs((Element)supers.item(3)).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void integerChargeSignsInSuperscriptRemainPostfix()throws Exception {
    for(String sign:List.of("+","-","−")) {
      var o=convert(math("<msup><mi>X</mi><mrow><mn>12</mn><mo>"+sign+"</mo></mrow></msup>"));
      assertEquals(List.of("12"+sign),firstSuperscriptRuns(o));
    }
  }
  @Test void numericChargeInSubSuperscriptRemainsPostfix()throws Exception {
    var o=convert(math("<msubsup><mi>Fe</mi><mn>1</mn><mrow><mn>3</mn><mo>+</mo></mrow></msubsup>"));
    assertEquals(List.of("3+"),firstSuperscriptRuns(o));
  }
  @Test void superscriptInfixExpressionStillSeparatesOperators()throws Exception {
    var o=convert(math("<msup><mi>x</mi><mrow><mn>2</mn><mo>+</mo><mn>1</mn></mrow></msup>"));
    assertEquals(List.of("2","+","1"),firstSuperscriptRuns(o));
  }
  @Test void numberFollowedByPlusOutsideSuperscriptStillSeparates()throws Exception {
    var o=convert(math("<mrow><mn>2</mn><mo>+</mo></mrow>"));
    assertEquals(List.of("2","+"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void subscriptIsNotTreatedAsChargeSuperscript()throws Exception {
    var o=convert(math("<msub><mi>x</mi><mrow><mn>2</mn><mo>+</mo></mrow></msub>"));
    var sub=(Element)o.getElementsByTagNameNS(M,"sub").item(0);
    assertEquals(List.of("2","+"),runs(sub).stream().map(OperatorBoundaryReviewTest::text).toList());
  }

  @Test void realLeadingNumericFragmentsKeepEqualsWithNumberForWriter()throws Exception {
    var expected=List.of("=31,35","=4,101,000","=24");
    for(int i=1;i<=3;i++) {
      String source;try(var in=getClass().getResourceAsStream("/review/real-leading-"+i+".mathml")){source=new String(in.readAllBytes(),StandardCharsets.UTF_8);}
      var o=convert(source);assertEquals(expected.get(i-1),text(o));
      assertEquals(List.of(expected.get(i-1)),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList(),"Writer ignores literal flags on a standalone equals run");
      assertEquals(0,o.getElementsByTagNameNS(M,"nor").getLength());assertEquals(0,o.getElementsByTagNameNS(M,"lit").getLength());
    }
  }
  @Test void transparentRootWrappersAllowTwoTokenNumericContinuation()throws Exception {
    var o=convert(math("<mstyle><mrow><mo>=</mo><mn>24</mn></mrow></mstyle>"));
    assertEquals(List.of("=24"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void laterNestedNumericRelationDoesNotBecomeContinuation()throws Exception {
    var o=convert(math("<mi>x</mi><mrow><mo>=</mo><mn>24</mn></mrow>"));
    assertEquals(List.of("x","=","24"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void relationInsideStructuralArgumentIsNotRootFragment()throws Exception {
    var o=convert(math("<mfrac><mrow><mo>=</mo><mn>24</mn></mrow><mn>2</mn></mfrac>"));
    assertEquals(List.of("=","24","2"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void generalLeadingExpressionKeepsOperatorSeparation()throws Exception {
    var o=convert(math("<mo>=</mo><mi>a</mi><mo>+</mo><mn>1</mn><mo>=</mo><mn>2</mn>"));
    assertEquals(List.of("=","a","+","1","=","2"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }

  @Test void realSymbolicChargeFixturesKeepPostfixPlusForWriter()throws Exception {
    for(int i=1;i<=2;i++) {
      String source;try(var in=getClass().getResourceAsStream("/review/real-symbolic-charge-"+i+".mathml")){source=new String(in.readAllBytes(),StandardCharsets.UTF_8);}
      var o=convert(source);assertEquals("Mn+",text(o));
      assertEquals(List.of("n+"),firstSuperscriptRuns(o));
      assertEquals(0,o.getElementsByTagNameNS(M,"nor").getLength());assertEquals(0,o.getElementsByTagNameNS(M,"lit").getLength());
    }
  }
  @Test void singleLetterSymbolicChargesRemainPostfix()throws Exception {
    for(String symbol:List.of("n","q","α"))for(String sign:List.of("+","-","−")) {
      var o=convert(math("<msup><mi>M</mi><mrow><mi>"+symbol+"</mi><mo>"+sign+"</mo></mrow></msup>"));
      assertEquals(List.of(symbol+sign),firstSuperscriptRuns(o));
    }
  }
  @Test void symbolicChargeInSubSuperscriptRemainsPostfix()throws Exception {
    var o=convert(math("<msubsup><mi>M</mi><mn>1</mn><mrow><mi>n</mi><mo>+</mo></mrow></msubsup>"));
    assertEquals(List.of("n+"),firstSuperscriptRuns(o));
  }
  @Test void symbolicInfixExponentStillSeparatesPlus()throws Exception {
    var o=convert(math("<msup><mi>x</mi><mrow><mi>n</mi><mo>+</mo><mn>1</mn></mrow></msup>"));
    assertEquals(List.of("n","+","1"),firstSuperscriptRuns(o));
  }
  @Test void symbolicSubscriptDoesNotBecomeCharge()throws Exception {
    var o=convert(math("<msub><mi>x</mi><mrow><mi>n</mi><mo>+</mo></mrow></msub>"));
    var sub=(Element)o.getElementsByTagNameNS(M,"sub").item(0);
    assertEquals(List.of("n","+"),runs(sub).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void multiLetterIdentifierDoesNotBecomeCharge()throws Exception {
    var o=convert(math("<msup><mi>x</mi><mrow><mi>sin</mi><mo>+</mo></mrow></msup>"));
    assertEquals(List.of("sin","+"),firstSuperscriptRuns(o));
  }
  @Test void symbolicPostfixOutsideSuperscriptStillSeparates()throws Exception {
    var o=convert(math("<mrow><mi>n</mi><mo>+</mo></mrow>"));
    assertEquals(List.of("n","+"),runs(o).stream().map(OperatorBoundaryReviewTest::text).toList());
  }
  @Test void symbolicChargeDoesNotOverrideFontBoundary()throws Exception {
    var o=convert(math("<msup><mi>M</mi><mrow><mi mathvariant='bold'>n</mi><mo>+</mo></mrow></msup>"));
    assertEquals(List.of("n","+"),firstSuperscriptRuns(o));
  }
}
