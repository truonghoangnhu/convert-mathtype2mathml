import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/transpect/mathml_content.py'
# Same vectors as MathmlContentVectorTest.java, so the Java and Python gates cannot drift apart.
VECTORS = ROOT / 'fixtures/mathml_content/visible_content_vectors.json'


def load_helper():
    spec = importlib.util.spec_from_file_location('mathml_content', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MathmlContentTest(unittest.TestCase):
    def test_invisible_nonspacing_controls_alone_are_not_formulas(self):
        module = load_helper()
        # These Mn characters are invisible by themselves. Do not reject all Mn:
        # ordinary accents and selectors beside a visible base must stay usable.
        controls = [0x034F, 0x180B, 0x180D, 0x180F, 0xFE00, 0xFE0F, 0xE0100, 0xE01EF]
        for cp in controls:
            with self.subTest(cp=hex(cp)):
                char = chr(cp)
                self.assertFalse(module.is_visible_char(char))
                self.assertFalse(module.is_usable_math_text(f'<math><mi>{char}</mi></math>'))
                self.assertTrue(module.is_usable_math_text(f'<math><mi>x{char}</mi></math>'))
        self.assertTrue(module.is_visible_char('\u0300'))

    def test_manifest_candidate_requires_visible_presentation_content(self):
        module = load_helper()
        cases = [
            ('<math/>', False),
            ('<math><mrow><mspace/></mrow></math>', False),
            ('<math><annotation>x</annotation></math>', False),
            ('<math><mphantom><mi>x</mi></mphantom></math>', False),
            ('<math xmlns="urn:wrong"><mi>x</mi></math>', False),
            ('<math><mi>x</math>', False),
            ('<math><mi></mi></math>', False),
            ('<math><mo>→</mo></math>', True),
            ('<m:math xmlns:m="http://www.w3.org/1998/Math/MathML"><m:mi>x</m:mi></m:math>', True),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'eq.mathml'
            self.assertFalse(module.is_usable_math(path))
            for xml, expected in cases:
                with self.subTest(xml=xml):
                    path.write_text(xml, encoding='utf-8')
                    self.assertEqual(expected, module.is_usable_math(path))

    def test_code_points_match_shared_vectors(self):
        module = load_helper()
        vectors = json.loads(VECTORS.read_text(encoding='utf-8'))['code_points']
        self.assertGreater(len(vectors), 20)
        for vector in vectors:
            char = chr(int(vector['cp'][2:], 16))
            with self.subTest(cp=vector['cp'], note=vector['note']):
                self.assertEqual(vector['visible'], module.is_visible_char(char))
                xml = '<math><mi>&#x%x;</mi></math>' % ord(char)
                self.assertEqual(vector['visible'], module.is_usable_math_text(xml))

    def test_mathml_documents_match_shared_vectors(self):
        module = load_helper()
        vectors = json.loads(VECTORS.read_text(encoding='utf-8'))['mathml']
        self.assertGreater(len(vectors), 10)
        for vector in vectors:
            with self.subTest(xml=vector['xml'], note=vector['note']):
                self.assertEqual(vector['usable'], module.is_usable_math_text(vector['xml']))
