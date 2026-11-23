"""Exercise the public preparation command; successful preparation is not acceptance."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/transpect/prepare_libreoffice_mathml.py'
NS = 'http://www.w3.org/1998/Math/MathML'


class LibreOfficeMathmlPreparationTest(unittest.TestCase):
    @staticmethod
    def assignment_system(first='<mn>2</mn><mo>+</mo><mn>5</mn><mi>t</mi>',
                          table_attrs='columnalign="left"', rows=3):
        bodies = [f'<mi>x</mi><mo>=</mo>{first}',
                  '<mi>y</mi><mo>=</mo><mn>2</mn><mo>+</mo><mn>2</mn><mi>t</mi>',
                  '<mi>z</mi><mo>=</mo><mo>−</mo><mn>1</mn><mo>−</mo><mn>3</mn><mi>t</mi>']
        bodies = (bodies + [bodies[0]])[:rows]
        return (f'<math xmlns="{NS}"><mfenced open="{{" close="" separators="">'
                f'<mtable {table_attrs}>' + ''.join(f'<mtr><mtd>{b}</mtd></mtr>' for b in bodies)
                + '</mtable></mfenced></math>')

    def test_aligns_verified_assignment_rows_with_matching_annotation_and_presentation(self):
        xml = self.assignment_system()
        output, report = self.prepare(xml)
        self.assertEqual(['A'], [c['rule'] for c in report['changes']])
        self.assertEqual('needs_review', report['status'])
        self.assertEqual('not_run', report['application_acceptance'])
        root = ET.fromstring(output)
        self.assertEqual(f'{{{NS}}}semantics', root[0].tag)
        self.assertEqual(ET.tostring(ET.fromstring(xml)[0]), ET.tostring(root[0][0]))
        self.assertEqual({'encoding': 'StarMath 5.0'}, root[0][1].attrib)
        self.assertEqual('left lbrace matrix{ alignl { x = 2 + 5 t } ## alignl { y = 2 + 2 t } ## alignl { z = - 1 - 3 t } } right none', root[0][1].text)
        again, second = self.prepare(output)
        self.assertEqual(output, again)
        self.assertEqual([], second['changes'])

    def test_assignment_annotation_rejects_ambiguous_or_incomplete_expression_grammar(self):
        for rhs in [
            '<mo>=</mo><mn>1</mn>', '<mn>1</mn><mo>+</mo>',
            '<mn>1</mn><mo>+</mo><mo>−</mo><mn>2</mn>',
            '<mn>2</mn><mn>5</mn>', '<mi>t</mi><mi>q</mi>',
            '<mn>2</mn><mo>=</mo><mn>3</mn>', '<mo>+</mo><mn>1</mn>',
            '<mn>2</mn><mi>t</mi><mi>q</mi>', '<mi>x</mi><mn>2</mn>',
            '<mo>−</mo><mo>−</mo><mn>1</mn>', '<mn>2,5</mn>',
            '<mi>alignl</mi>', '<mi>α</mi>', '<mn>1</mn><mo>×</mo><mi>t</mi>',
        ]:
            with self.subTest(rhs=rhs):
                out, report = self.prepare(self.assignment_system(rhs))
                self.assertNotIn('A', [c['rule'] for c in report['changes']])
                self.assertIsNone(ET.fromstring(out).find(f'.//{{{NS}}}annotation'))

    def test_assignment_annotation_rejects_unverified_shape_style_and_mixed_text(self):
        raw = self.assignment_system()
        cases = [self.assignment_system(table_attrs=a) for a in ['', 'columnalign="center"',
                 'columnalign="right"', 'columnalign="left" class="x"']]
        empty, empty_report = self.prepare(self.assignment_system(rows=0), expected=2)
        self.assertIsNone(empty)
        self.assertEqual('unsupported', empty_report['status'])
        cases += [self.assignment_system(rows=n) for n in [1, 2, 4]]
        cases += [raw.replace('<math ', '<math display="block" ', 1),
                  raw.replace('open="{"', 'open="("'), raw.replace('close=""', 'close="}"'),
                  raw.replace('separators=""', 'separators=","'),
                  raw.replace('<mtr>', '<mtr columnalign="left">', 1),
                  raw.replace('<mtd>', '<mtd style="x">', 1),
                  raw.replace('<mi>x</mi>', '<mi mathvariant="bold">x</mi>', 1),
                  raw.replace('<mi>x</mi>', '<msub><mi>x</mi><mn>1</mn></msub>', 1),
                  raw.replace('<mtd>', '<mtd>\u00a0', 1),
                  raw.replace('</mn>', '</mn>unhandled', 1),
                  raw.replace('<mfenced', '<mtable columnalign="left"><mtr><mtd><mfenced', 1)
                     .replace('</mfenced>', '</mfenced></mtd></mtr></mtable>'),
                  raw.replace('<mi>x</mi>', '<x:mi xmlns:x="urn:foreign">x</x:mi>', 1)]
        for xml in cases:
            with self.subTest(xml=xml):
                out, report = self.prepare(xml)
                self.assertNotIn('A', [c['rule'] for c in report['changes']])
                self.assertIsNone(ET.fromstring(out).find(f'.//{{{NS}}}annotation'))

    def test_assignment_annotation_accepts_only_unambiguous_integer_and_letter_terms(self):
        for rhs, command_rhs in [('<mn>12</mn>', '12'), ('<mi>t</mi>', 't'),
                    ('<mo>−</mo><mi>t</mi>', '- t'),
                    ('<mn>2</mn><mi>t</mi><mo>+</mo><mn>1</mn>', '2 t + 1'),
                    ('<mo>-</mo><mn>3</mn><mi>t</mi><mo>−</mo><mn>4</mn>', '- 3 t - 4')]:
            with self.subTest(rhs=rhs):
                output, report = self.prepare(self.assignment_system(rhs))
                self.assertEqual(['A'], [c['rule'] for c in report['changes']])
                expected = ('left lbrace matrix{ alignl { x = ' + command_rhs
                            + ' } ## alignl { y = 2 + 2 t } ## alignl { z = - 1 - 3 t } } right none')
                self.assertEqual(expected, ET.fromstring(output)[0][1].text)
                self.assertEqual(expected, report['changes'][0]['command'])

    def test_assignment_annotation_rejects_unverified_left_hand_side(self):
        for lhs in ['<mn>1</mn><mo>=</mo>', '<mi>x</mi><mi>y</mi><mo>=</mo>',
                    '<mi>x</mi><mo>+</mo>', '<mi>x</mi><mo> = </mo>']:
            with self.subTest(lhs=lhs):
                xml = self.assignment_system().replace('<mi>x</mi><mo>=</mo>', lhs, 1)
                out, report = self.prepare(xml)
                self.assertNotIn('A', [c['rule'] for c in report['changes']])
                self.assertIsNone(ET.fromstring(out).find(f'.//{{{NS}}}annotation'))

    def test_vector_integer_triple_keeps_accent_via_bounded_annotation(self):
        xml = f'<math xmlns="{NS}"><mover accent="true"><mi>u</mi><mo>→</mo></mover><mo>=</mo><mfenced open="(" close=")" separators=""><mn>5</mn><mo>;</mo><mn>2</mn><mo>;</mo><mo>−</mo><mn>3</mn></mfenced></math>'
        out, report = self.prepare(xml)
        self.assertIn('V', [c['rule'] for c in report['changes']])
        root = ET.fromstring(out)
        self.assertEqual('vec u = left ( 5 ; 2 ; - 3 right )', root.find(f'.//{{{NS}}}annotation').text)
        self.assertEqual('→', root.find(f'.//{{{NS}}}mover')[1].text)
        again, second = self.prepare(out)
        self.assertEqual(out, again)
        self.assertEqual([], second['changes'])

    def test_vector_annotation_rejects_unverified_tuple_or_accent_shapes(self):
        raw = f'<math xmlns="{NS}"><mover accent="true"><mi>u</mi><mo>→</mo></mover><mo>=</mo><mfenced open="(" close=")" separators=""><mn>5</mn><mo>;</mo><mn>2</mn><mo>;</mo><mn>3</mn></mfenced></math>'
        for xml in [raw.replace('accent="true"','accent="false"'), raw.replace('<mi>u</mi>','<mi>AB</mi>'),
                    raw.replace('→','←'),raw.replace('<mn>5</mn>','<mn>2,5</mn>'),
                    raw.replace('<mn>5</mn>','<mi>x</mi>'),raw.replace('<mn>3</mn>','<mn>3</mn><mo>;</mo><mn>4</mn>'),
                    raw.replace('<mn>5</mn>','<mn mathvariant="bold">5</mn>'),raw.replace('open="("','open="["'),
                    raw.replace('<math ', '<math display="block" ', 1),
                    raw.replace('<mi>u</mi>', '<mi mathvariant="bold">u</mi>'),
                    raw.replace('<mo>→</mo>', '<mo stretchy="false">→</mo>'),
                    raw.replace('accent="true"', 'accent="true" class="x"'),
                    raw.replace('<mn>5</mn>', '<mo>+</mo><mn>5</mn>'),
                    raw.replace('<mn>5</mn>', '<mo>−</mo><mo>−</mo><mn>5</mn>'),
                    raw.replace('<mo>;</mo><mn>3</mn>', ''),
                    raw.replace('separators=""', 'separators=","'),
                    raw.replace('<mn>5</mn>', '\u00a0<mn>5</mn>'),
                    raw.replace('<mover ', '<mstyle><mover ').replace('</mover>', '</mover></mstyle>')]:
            with self.subTest(xml=xml):
                out, r = self.prepare(xml)
                self.assertNotIn('V', [c['rule'] for c in r['changes']])
                self.assertIsNone(ET.fromstring(out).find(f'.//{{{NS}}}annotation'))

    def test_vector_annotation_preserves_complete_prepared_presentation(self):
        xml = f'<math xmlns="{NS}"><mrow><mover accent="true"><mi>u</mi><mo>→</mo></mover><mo>=</mo><mfenced open="(" close=")" separators=""><mrow><mn>91</mn><mo>;</mo><mn>75</mn><mo>;</mo><mn>0</mn></mrow></mfenced></mrow></math>'
        out, report = self.prepare(xml)
        self.assertEqual(['V'], [c['rule'] for c in report['changes']])
        self.assertEqual(ET.tostring(ET.fromstring(xml)[0]), ET.tostring(ET.fromstring(out)[0][0]))
        self.assertEqual('LibreOffice 26.8.0.3', report['changes'][0]['annotation_priority_measured_on'])

    def prepare(self, xml, expected=0, destination_text=None, same_path=False):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'source.mathml'
            dst = src if same_path else Path(tmp) / 'lo.mathml'
            src.write_text(xml, encoding='utf-8')
            if destination_text is not None and not same_path:
                dst.write_text(destination_text, encoding='utf-8')
            proc = subprocess.run([sys.executable, str(CLI), str(src), str(dst)],
                                  capture_output=True, text=True)
            self.assertEqual(expected, proc.returncode, proc.stderr + proc.stdout)
            self.assertTrue(proc.stdout.strip().startswith('{'), proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(xml, src.read_text(encoding='utf-8'), 'source changed')
            output = dst.read_text(encoding='utf-8') if dst.exists() else None
            return output, result

    def test_prepares_leading_relation_without_changing_tokens(self):
        xml = f'<math xmlns="{NS}"><mo>&gt;</mo><msup><mn>150</mn><mo>°</mo></msup><mtext>C</mtext></math>'
        output, result = self.prepare(xml)
        self.assertEqual('needs_review', result['status'])
        self.assertEqual(['W', 'L'], [c['rule'] for c in result['changes']])
        self.assertEqual('not_run', result['application_acceptance'])
        self.assertEqual('>150°C', ''.join(ET.fromstring(output).itertext()))
        row = ET.fromstring(output)[0]
        self.assertEqual(f'{{{NS}}}mrow', row[0].tag)
        self.assertEqual(0, len(row[0]))

    def test_scoped_leading_relations_and_trailing_arrow(self):
        for op in ['&lt;', '&gt;', '≤', '≥', '=', '→']:
            with self.subTest(op=op):
                _, r = self.prepare(f'<math xmlns="{NS}"><mo>{op}</mo><mn>1</mn></math>')
                self.assertEqual(['W', 'L'], [c['rule'] for c in r['changes']])
        _, r = self.prepare(f'<math xmlns="{NS}"><mi>NaOH</mi><mo>→</mo></math>')
        self.assertEqual(['W', 'T'], [c['rule'] for c in r['changes']])

    def test_annotations_foreign_content_and_single_argument_fences_remain_unchanged(self):
        for body in [
            '<semantics><mrow><mo>&gt;</mo><mn>1</mn></mrow><annotation encoding="StarMath 5.0">x</annotation></semantics>',
            '<annotation-xml><mfenced separators=""><mi>x</mi></mfenced></annotation-xml><mi>y</mi>',
            '<mrow><x:mo xmlns:x="urn:foreign">&gt;</x:mo><mn>1</mn></mrow>',
            '<mfenced open="(" close=")" separators=""><mi>x</mi></mfenced>',
            '<mrow><mi>x</mi><mo>=</mo><mn>1</mn></mrow>',
            '<mrow><mo>−</mo><mi>x</mi></mrow>',
        ]:
            with self.subTest(body=body):
                xml = f'<math xmlns="{NS}">{body}</math>'
                out, r = self.prepare(xml)
                self.assertEqual(xml, out)
                self.assertEqual([], r['changes'])

    def test_groups_explicitly_unseparated_fence_arguments_without_expanding_fences(self):
        for attrs in ['open="(" close=")"', 'open="|" close="|"', '']:
            with self.subTest(attrs=attrs):
                xml = f'<math xmlns="{NS}"><mfenced {attrs} separators=""><mi>x</mi><mo>+</mo><mn>2</mn></mfenced></math>'
                out, report = self.prepare(xml)
                self.assertEqual(['G'], [c['rule'] for c in report['changes']])
                fence = ET.fromstring(out)[0]
                self.assertEqual(f'{{{NS}}}mfenced', fence.tag)
                self.assertEqual(ET.fromstring(xml)[0].attrib, fence.attrib)
                self.assertEqual(1, len(fence))
                self.assertEqual(f'{{{NS}}}mrow', fence[0].tag)
                self.assertEqual(['x', '+', '2'], [c.text for c in fence[0]])
                again, second = self.prepare(out)
                self.assertEqual(out, again)
                self.assertEqual([], second['changes'])
                self.assertEqual('needs_review', report['status'])

    def test_fence_groups_do_not_cascade_unprobed_leading_or_trailing_relation_repairs(self):
        for body in ['<mo>=</mo><mn>1</mn>', '<mi>x</mi><mo>→</mo>']:
            raw = f'<math xmlns="{NS}"><mfenced separators="">{body}</mfenced></math>'
            out, report = self.prepare(raw)
            self.assertEqual(['G'], [c['rule'] for c in report['changes']])
            self.assertEqual(2, len(ET.fromstring(out)[0][0]))
            self.assertTrue(report['untested'])
            again, second = self.prepare(out)
            self.assertEqual(out, again)
            self.assertEqual([], second['changes'])

    def test_fence_grouping_preserves_xml_whitespace_and_does_not_treat_nbsp_as_ignorable(self):
        raw = f'<math xmlns="{NS}"><mfenced separators="">\n  <mi>x</mi>\n  <mi>y</mi>\n</mfenced></math>'
        out, report = self.prepare(raw)
        self.assertEqual('\n  x\n  y\n', ''.join(ET.fromstring(out)[0].itertext()))
        self.assertEqual(2, report['changes'][0].get('children'))
        for gap in ['\u00a0', '\u2003']:
            mixed = f'<math xmlns="{NS}"><mfenced separators="">{gap}<mi>x</mi><mi>y</mi></mfenced></math>'
            out, report = self.prepare(mixed)
            self.assertEqual(mixed, out)
            self.assertEqual([], report['changes'])

    def test_groups_nested_fences_but_preserves_nonempty_separators_and_unprobed_attributes(self):
        xml = f'<math xmlns="{NS}"><mfenced separators=""><mn>2</mn><mi>f</mi><mfenced separators=""><mi>x</mi></mfenced><mo>−</mo><mn>1</mn></mfenced></math>'
        out, _ = self.prepare(xml)
        outer = ET.fromstring(out)[0]
        self.assertEqual(1, len(outer))
        self.assertEqual('2fx−1', ''.join(outer.itertext()))
        self.assertEqual(f'{{{NS}}}mfenced', outer[0][2].tag)
        for attrs in ['separators=","', '', 'separators=" "', 'separators="" open="[" close=")"',
                      'separators="" open="(" close=""', 'separators="" class="custom"']:
            with self.subTest(attrs=attrs):
                raw = f'<math xmlns="{NS}"><mfenced {attrs}><mi>x</mi><mi>y</mi></mfenced></math>'
                candidate, report = self.prepare(raw)
                self.assertEqual(raw, candidate)
                self.assertEqual([], report['changes'])
                self.assertTrue(report['untested'])

    def test_does_not_group_fences_inside_metadata_or_mixed_namespaces(self):
        fence = '<mfenced separators=""><mi>x</mi><mo>+</mo><mn>2</mn></mfenced>'
        for body in [f'<semantics>{fence}<annotation>text</annotation></semantics>',
                     f'<mrow>{fence}<mi xmlns="">y</mi></mrow>']:
            raw = f'<math xmlns="{NS}">{body}</math>'
            candidate, report = self.prepare(raw)
            self.assertEqual(raw, candidate)
            self.assertEqual([], report['changes'])
            self.assertTrue(report['untested'])

    def test_prepares_demonstrated_positive_charge_exponents_only(self):
        for exponent in ['<mo>+</mo>', '<mrow><mn>2</mn><mo>+</mo></mrow>',
                         '<mrow><mn>3</mn><mo>+</mo></mrow>']:
            raw = f'<math xmlns="{NS}"><msup><mi>X</mi>{exponent}</msup></math>'
            out, report = self.prepare(raw)
            self.assertEqual(['C'], [c['rule'] for c in report['changes']])
            sup = ET.fromstring(out)[0]
            self.assertEqual('X', sup[0].text)
            self.assertEqual(f'{{{NS}}}mrow', sup[1].tag)
            self.assertEqual(f'{{{NS}}}mrow', sup[1][-1].tag)
            self.assertEqual(0, len(sup[1][-1]))
            self.assertEqual('X'+''.join(ET.fromstring(raw)[0][1].itertext()), ''.join(sup.itertext()))
            again, second = self.prepare(out)
            self.assertEqual(out, again)
            self.assertEqual([], second['changes'])
            self.assertEqual([], second['untested'])
        for exponent in ['<mo>−</mo>', '<mrow><mn>4</mn><mo>+</mo></mrow>',
                         '<mrow><mi>n</mi><mo>+</mo></mrow>', '<mrow><mn>2</mn><mo>+</mo><mn>1</mn></mrow>']:
            raw = f'<math xmlns="{NS}"><msup><mi>X</mi>{exponent}</msup></math>'
            out, report = self.prepare(raw)
            self.assertEqual(raw, out)
            self.assertEqual([], report['changes'])

    def test_fence_grouping_does_not_cascade_interval_or_bar_repairs_in_fenced_context(self):
        interval = '<mo>[</mo><mn>2,7</mn><mo>;</mo><mn>3,0</mn><mo>)</mo>'
        bars = '<mo>|</mo><msub><mi>e</mi><mi>c</mi></msub><mo>|</mo><mo>=</mo><mi>B</mi>'
        for body in [interval, bars, f'<mrow>{interval}</mrow><mi>x</mi>']:
            with self.subTest(body=body):
                raw = f'<math xmlns="{NS}"><mfenced separators="">{body}</mfenced></math>'
                out, report = self.prepare(raw)
                self.assertEqual(['G'], [c['rule'] for c in report['changes']])
                self.assertTrue(report['untested'])
                again, second = self.prepare(out)
                self.assertEqual(out, again)
                self.assertEqual([], second['changes'])

    def test_charge_and_bar_rules_do_not_promote_empty_invisible_or_unprobed_bases(self):
        for token in ['', '\u200b', 'Ca', 'α']:
            with self.subTest(token=token):
                charge = f'<math xmlns="{NS}"><msup><mi>{token}</mi><mo>+</mo></msup></math>'
                bars = f'<math xmlns="{NS}"><mrow><mo>|</mo><msub><mi>{token}</mi><mi>c</mi></msub><mo>|</mo><mo>=</mo><mi>B</mi></mrow></math>'
                for raw in [charge, bars]:
                    out, report = self.prepare(raw)
                    self.assertEqual(raw, out)
                    self.assertEqual([], report['changes'])

    def test_prepares_exact_comma_decimal_half_open_interval_without_changing_endpoints(self):
        raw = f'<math xmlns="{NS}"><mrow><mo>[</mo><mn>2,7</mn><mo>;</mo><mn>3,0</mn><mo>)</mo></mrow></math>'
        out, report = self.prepare(raw)
        self.assertEqual(['I'], [c['rule'] for c in report['changes']])
        fence = ET.fromstring(out)[0][0]
        self.assertEqual(f'{{{NS}}}mfenced', fence.tag)
        self.assertEqual({'open': '[', 'close': ')', 'separators': ''}, fence.attrib)
        self.assertEqual(['2,7', ';', '3,0'], [c.text for c in fence[0]])
        again, report = self.prepare(out)
        self.assertEqual(out, again)
        self.assertEqual([], report['changes'])

    def test_prepares_bare_absolute_value_of_a_simple_subscript_before_equals(self):
        raw = f'<math xmlns="{NS}"><mrow><mo>|</mo><msub><mi>e</mi><mi>c</mi></msub><mo>|</mo><mo>=</mo><mi>B</mi><mtext>ℓ</mtext><mi>v</mi></mrow></math>'
        out, report = self.prepare(raw)
        self.assertEqual(['B'], [c['rule'] for c in report['changes']])
        row = ET.fromstring(out)[0]
        self.assertEqual({'open': '|', 'close': '|', 'separators': ''}, row[0].attrib)
        self.assertEqual(f'{{{NS}}}msub', row[0][0].tag)
        self.assertEqual('ec', ''.join(row[0][0].itertext()))
        self.assertEqual(['=', 'B', 'ℓ', 'v'], [c.text for c in row[1:]])
        again, report = self.prepare(out)
        self.assertEqual(out, again)
        self.assertEqual([], report['changes'])

    def test_interval_and_bar_repairs_do_not_cross_unprobed_structure_or_metadata(self):
        interval = '<mo>[</mo><mn>2,7</mn><mo>;</mo><mn>3,0</mn><mo>)</mo>'
        bars = '<mo>|</mo><msub><mi>e</mi><mi>c</mi></msub><mo>|</mo><mo>=</mo><mi>B</mi>'
        attributed_bars = bars.replace('<mo>|</mo>', '<mo stretchy="false">|</mo>', 1)
        for body in [f'<mrow class="custom">{interval}</mrow>',
                     f'<mrow>{interval.replace("2,7", "−2,7")}</mrow>',
                     f'<mrow>{attributed_bars}</mrow>',
                     f'<semantics><mrow>{interval}</mrow></semantics>',
                     f'<mrow>{bars}<mi xmlns="">x</mi></mrow>']:
            raw = f'<math xmlns="{NS}">{body}</math>'
            out, report = self.prepare(raw)
            self.assertEqual(raw, out)
            self.assertEqual([], report['changes'])

    def test_scoped_exponent_interval_and_bar_attribute_and_shape_boundaries(self):
        intervals = '<mo>[</mo><mn>2,7</mn><mo>;</mo><mn>3,0</mn><mo>)</mo>'
        bars = '<mo>|</mo><msub><mi>e</mi><mi>c</mi></msub><mo>|</mo><mo>=</mo><mi>B</mi>'
        cases = [
            ('C', '<msup><mi mathvariant="normal">H</mi><mo>+</mo></msup>'),
            ('C', '<msup displaystyle="true"><mi>H</mi><mo>+</mo></msup>'),
            ('I', '<mrow>'+intervals.replace('<mo>;</mo>', '<mo>,</mo>')+'</mrow>'),
            ('I', '<mrow>'+intervals.replace('2,7', '2').replace('3,0', '3')+'</mrow>'),
            ('I', '<mrow>'+intervals.replace('<mo>;</mo>', '')+'</mrow>'),
            ('I', '<mrow>'+intervals+'<mi>x</mi></mrow>'),
            ('B', '<mrow>'+bars.replace('<mi>B</mi>', '')+'</mrow>'),
            ('B', '<mrow>'+bars.replace('<mi>c</mi>', '<mn>1</mn>')+'</mrow>'),
            ('B', '<mrow><mi>x</mi>'+bars+'</mrow>'),
        ]
        for forbidden, body in cases:
            with self.subTest(body=body):
                _, report = self.prepare(f'<math xmlns="{NS}">{body}</math>')
                self.assertNotIn(forbidden, [c['rule'] for c in report['changes']])
        raw = f'<math xmlns="{NS}"><msup>\n <mi>H</mi>\n <mo>+</mo>\n</msup></math>'
        out, report = self.prepare(raw)
        self.assertEqual(['C'], [c['rule'] for c in report['changes']])
        self.assertEqual('\n H\n +\n', ''.join(ET.fromstring(out).itertext()))
        self.assertEqual('wrapped', report['changes'][0]['shape'])
        self.assertEqual('+', report['changes'][0]['exponent'])
        self.assertEqual('candidate_tree', report['path_space'])

    def test_celsius_script_delimiters_remain_literal_without_moving_the_degree(self):
        unit = '<msup><mo>(</mo><mo>°</mo></msup><mi>C</mi><mo>)</mo>'
        body = '<mi>T</mi><mo>(</mo><mi>K</mi><mo>)</mo><mo>=</mo><mi>t</mi><mspace width="0.33em"/>'+unit+'<mo>+</mo><mn>273</mn>'
        raw = f'<math xmlns="{NS}"><mrow>{body}</mrow></math>'
        out, report = self.prepare(raw)
        self.assertEqual(['D'], [c['rule'] for c in report['changes']])
        row = ET.fromstring(out)[0]
        self.assertEqual('T(K)=t(°C)+273', ''.join(row.itertext()))
        self.assertEqual(12, len(row))
        self.assertEqual(f'{{{NS}}}msup', row[7].tag)
        self.assertEqual(f'{{{NS}}}mtext', row[7][0].tag)
        self.assertEqual('(', row[7][0].text)
        self.assertEqual(f'{{{NS}}}mo', row[7][1].tag)
        self.assertEqual('°', row[7][1].text)
        self.assertEqual(f'{{{NS}}}mi', row[8].tag)
        self.assertEqual('C', row[8].text)
        self.assertEqual(f'{{{NS}}}mtext', row[9].tag)
        self.assertEqual(')', row[9].text)
        self.assertEqual(f'{{{NS}}}mo', row[1].tag, 'ordinary T(K) delimiters changed')
        self.assertEqual('0.33em', row[6].get('width'))
        again, second = self.prepare(out)
        self.assertEqual(out, again)
        self.assertEqual([], second['changes'])
        self.assertEqual('needs_review', report['status'])
        self.assertEqual('not_run', report['application_acceptance'])

    def test_celsius_script_rule_does_not_cross_unprobed_shapes_or_boundaries(self):
        unit = '<msup><mo>(</mo><mo>°</mo></msup><mi>C</mi><mo>)</mo>'
        cases = [unit.replace('<mi>C</mi>', '<mi>F</mi>'),
                 unit.replace('<mo>°</mo>', '<mo>′</mo>'),
                 unit.replace('<msup>', '<msup displaystyle="true">'),
                 unit.replace('<mo>(</mo>', '<mo stretchy="false">(</mo>'),
                 unit.replace('<mi>C</mi>', '<mi mathvariant="normal">C</mi>'),
                 unit.replace('<mo>)</mo>', ''),
                 unit.replace('</msup><mi>', '</msup>\u00a0<mi>')]
        for body in cases:
            with self.subTest(body=body):
                raw = f'<math xmlns="{NS}"><mrow><mi>t</mi>{body}</mrow></math>'
                out, report = self.prepare(raw)
                self.assertEqual(raw, out)
                self.assertEqual([], report['changes'])
        for wrapped in [f'<mfenced separators=""><mrow>{unit}</mrow></mfenced>',
                        f'<semantics><mrow>{unit}</mrow></semantics>',
                        f'<mrow>{unit}<mi xmlns="">x</mi></mrow>']:
            raw = f'<math xmlns="{NS}">{wrapped}</math>'
            out, report = self.prepare(raw)
            self.assertEqual(raw, out)
            self.assertEqual([], report['changes'])

    def test_celsius_script_rule_preserves_pretty_print_whitespace(self):
        body = '<msup>\n <mo>(</mo>\n <mo>°</mo>\n</msup>\n<mi>C</mi>\n<mo>)</mo>\n'
        raw = f'<math xmlns="{NS}"><mrow>\n{body}</mrow></math>'
        out, report = self.prepare(raw)
        self.assertEqual(['D'], [c['rule'] for c in report['changes']])
        self.assertEqual(''.join(ET.fromstring(raw).itertext()), ''.join(ET.fromstring(out).itertext()))
        self.assertEqual('math/mrow[0]/msup[0]', report['changes'][0]['path'])

    def test_celsius_rule_defers_nested_styled_and_multiple_unit_contexts(self):
        unit = '<msup><mo>(</mo><mo>°</mo></msup><mi>C</mi><mo>)</mo>'
        contexts = [f'<mfrac><mrow>{unit}</mrow><mn>1</mn></mfrac>',
                    f'<msub><mi>x</mi><mrow>{unit}</mrow></msub>',
                    f'<msqrt><mrow>{unit}</mrow></msqrt>',
                    f'<mtable><mtr><mtd><mrow>{unit}</mrow></mtd></mtr></mtable>',
                    f'<mstyle scriptlevel="1"><mrow>{unit}</mrow></mstyle>',
                    f'<mrow>{unit}{unit}</mrow>']
        for body in contexts:
            with self.subTest(body=body):
                raw = f'<math xmlns="{NS}">{body}</math>'
                out, report = self.prepare(raw)
                self.assertEqual(raw, out)
                self.assertTrue(any(n['rule'] == 'D' for n in report['untested']))
        raw = f'<math xmlns="{NS}" display="block"><mrow>{unit}</mrow></math>'
        out, report = self.prepare(raw)
        self.assertEqual(raw, out)
        self.assertTrue(any(n['rule'] == 'D' for n in report['untested']))

    def test_celsius_rule_defers_unbalanced_and_nested_bare_parentheses(self):
        unit = '<msup><mo>(</mo><mo>°</mo></msup><mi>C</mi><mo>)</mo>'
        for body in [unit+'<mo>)</mo>', '<mo>(</mo>'+unit,
                     '<mo>(</mo><mi>t</mi>'+unit+'<mo>)</mo>',
                     '<mo>[</mo>'+unit+'<mo>]</mo>']:
            with self.subTest(body=body):
                raw = f'<math xmlns="{NS}"><mrow>{body}</mrow></math>'
                out, report = self.prepare(raw)
                self.assertEqual(raw, out)
                self.assertTrue(any(n['rule'] == 'D' for n in report['untested']))

    def test_celsius_rule_defers_unprobed_combinations_and_reports_final_candidate_paths(self):
        unit = '<msup><mo>(</mo><mo>°</mo></msup><mi>C</mi><mo>)</mo>'
        bars = '<mo>|</mo><msub><mi>a</mi><mi>b</mi></msub><mo>|</mo><mo>=</mo><mi>t</mi>'
        for prefix, allowed in [('<mo>=</mo>', ['L']), (bars, ['B'])]:
            raw = f'<math xmlns="{NS}"><mrow>{prefix}{unit}</mrow></math>'
            out, report = self.prepare(raw)
            self.assertEqual(allowed, [c['rule'] for c in report['changes']])
            self.assertTrue(any(n['rule'] == 'D' for n in report['untested']))
            self.assertTrue(ET.fromstring(out).findall('.//{'+NS+'}msup/{'+NS+'}mo'))
        raw = f'<math xmlns="{NS}">{unit}</math>'
        out, report = self.prepare(raw)
        self.assertEqual(['W', 'D'], [c['rule'] for c in report['changes']])
        self.assertEqual('math/mrow[0]/msup[0]', report['changes'][1]['path'])
        self.assertEqual('math/mrow[0]/mtext[2]', report['changes'][1]['close_path'])

    def test_reports_noncentered_table_alignment_without_changing_formula_or_rows(self):
        for element in ['mtable', 'mtr', 'mtd']:
            attrs = {name: (' columnalign="left"' if name == element else '') for name in ['mtable', 'mtr', 'mtd']}
            body = '<mtable'+attrs['mtable']+'><mtr'+attrs['mtr']+'><mtd'+attrs['mtd']+'><mi>x</mi></mtd></mtr></mtable>'
            raw = f'<math xmlns="{NS}">{body}</math>'
            with self.subTest(element=element):
                out, report = self.prepare(raw)
                self.assertEqual(raw, out)
                self.assertEqual([], report['changes'])
                self.assertTrue(any(n['rule'] == 'table_alignment' for n in report['untested']))
                self.assertEqual('needs_review', report['status'])
                self.assertEqual('not_run', report['application_acceptance'])
        raw = f'<math xmlns="{NS}"><mtable columnalign="center"><mtr><mtd><mi>x</mi></mtd></mtr></mtable></math>'
        _, report = self.prepare(raw)
        self.assertEqual([], report['untested'])

    def test_operator_only_and_unprobed_relations_are_not_repaired(self):
        for body in ['<mrow><mo>&gt;</mo><mo>=</mo></mrow>',
                     '<mrow><mo>≠</mo><mn>1</mn></mrow>',
                     '<mstyle><mo>&gt;</mo><mn>1</mn></mstyle>']:
            with self.subTest(body=body):
                xml = f'<math xmlns="{NS}">{body}</math>'
                out, r = self.prepare(xml)
                self.assertEqual(xml, out)
                self.assertTrue(r['untested'])

    def test_unsupported_input_creates_no_candidate(self):
        for xml in ['<math><mi>x</mi></math>', '<math xmlns="urn:foreign"><mi>x</mi></math>',
                    f'<math xmlns="{NS}"/>', f'<math xmlns="{NS}"><mi>\ufe0f</mi></math>',
                    f'<math xmlns="{NS}"><mi xmlns="">x</mi></math>',
                    f'<math xmlns="{NS}"><mi><x:text xmlns:x="urn:foreign">x</x:text></mi></math>',
                    f'<math xmlns="{NS}"><annotation>x</annotation></math>']:
            with self.subTest(xml=xml):
                out, r = self.prepare(xml, expected=2)
                self.assertIsNone(out)
                self.assertEqual('unsupported', r['status'])

    def test_foreign_content_is_preserved_and_reported_beside_visible_mathml(self):
        xml = f'<math xmlns="{NS}"><mi>y</mi><mi xmlns="">x</mi></math>'
        out, r = self.prepare(xml)
        self.assertEqual(xml, out)
        self.assertTrue(r['untested'])

    def test_mixed_namespaces_and_metadata_are_not_reserialized_when_a_rule_could_fire(self):
        for suffix in [
            '<mi xmlns="">x</mi>',
            '<annotation-xml xmlns:custom="urn:custom" encoding="custom:format">x</annotation-xml>',
        ]:
            xml = f'<math xmlns="{NS}"><mrow><mo>&gt;</mo><mn>1</mn></mrow>{suffix}</math>'
            with self.subTest(suffix=suffix):
                out, r = self.prepare(xml)
                self.assertEqual(xml, out, 'mixed namespace/metadata must stay byte-identical')
                self.assertEqual([el.tag for el in ET.fromstring(xml).iter()],
                                 [el.tag for el in ET.fromstring(out).iter()])
                self.assertEqual([], r['changes'])
                self.assertTrue(r['untested'])

    def test_invalid_xml_is_failed_without_output(self):
        for xml in ['<math><mi>x</math>', '<!DOCTYPE math [<!ENTITY x "y">]><math><mi>&x;</mi></math>']:
            out, r = self.prepare(xml, expected=1)
            self.assertIsNone(out)
            self.assertEqual('failed', r['status'])

    def test_source_and_existing_outputs_are_preserved(self):
        xml = f'<math xmlns="{NS}"><mi>x</mi></math>'
        out, r = self.prepare(xml, expected=1, destination_text='keep old output')
        self.assertEqual('keep old output', out)
        self.assertEqual('failed', r['status'])
        out, r = self.prepare(xml, expected=1, same_path=True)
        self.assertEqual(xml, out)
        self.assertEqual('failed', r['status'])
