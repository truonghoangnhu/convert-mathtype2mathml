import importlib.util
from pathlib import Path
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'scripts/transpect/mathml_content.py'


class MathmlContentTest(unittest.TestCase):
    def test_manifest_candidate_requires_visible_presentation_content(self):
        spec = importlib.util.spec_from_file_location('mathml_content', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = [
            ('<math/>', False),
            ('<math><mrow><mspace/></mrow></math>', False),
            ('<math><annotation>x</annotation></math>', False),
            ('<math><mphantom><mi>x</mi></mphantom></math>', False),
            ('<math xmlns="urn:wrong"><mi>x</mi></math>', False),
            ('<math><mi>x</math>', False),
            ('<math><mi>\uef0a</mi></math>', False),
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
