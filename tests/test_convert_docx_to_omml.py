"""Exercise the one-argument macOS wrapper; conversion internals have their own tests."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/transpect/convert_docx_to_omml.sh'


class QuickOmmlTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='quick OMML tiếng Việt ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scripts = self.root / 'scripts/transpect'
        self.scripts.mkdir(parents=True)
        self.cli = self.scripts / SCRIPT.name
        if SCRIPT.exists():
            shutil.copyfile(SCRIPT, self.cli)
        self.source = self.root / 'Đề thi có khoảng trắng.DOCX'
        with zipfile.ZipFile(self.source, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types/>')
            z.writestr('_rels/.rels', '<Relationships/>')
            z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
        self.original = self.source.read_bytes()
        self.jar = self.root / 'target/docx-html-math-1.0.0-jar-with-dependencies.jar'
        self.jar.parent.mkdir()
        self.jar.write_bytes(b'test boundary: fake java does not read this jar')
        runtime = self.root / 'tools/calabash'
        (runtime / 'extensions/transpect/mathtype-extension').mkdir(parents=True)
        (runtime / 'distro/lib').mkdir(parents=True)
        (runtime / 'distro/xmlcalabash-1.4.1-100.jar').touch()
        (runtime / 'distro/lib/Saxon-HE-10.8.jar').touch()
        # Only replace heavyweight external conversion, retaining real filesystem effects.
        generator = self.scripts / 'generate_sidecars.sh'
        generator.write_text('''#!/usr/bin/env bash
set -e
if [ "${FAIL_STAGE:-}" = sidecar ]; then echo decoder-failed >&2; exit 7; fi
mkdir -p "$2"
printf 'part\\tformula.mathml\\n' > "$2/manifest.tsv"
''')
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        java = bin_dir / 'java'
        java.write_text('''#!/usr/bin/env bash
if [ "$1" = -version ]; then echo "openjdk version \\\"${TEST_JAVA_VERSION:-17}.0.1\\\"" >&2; exit 0; fi
if [ "${FAIL_STAGE:-}" = java ]; then echo patch-failed >&2; exit 8; fi
cp "$4" "$5"
''')
        java.chmod(0o755)
        self.env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'])
        for name in ('DOCX_MATH_JAR', 'MT_DIR', 'XMLCALABASH_JAR', 'SAXON_HE_JAR'):
            self.env.pop(name, None)
        self.cwd = self.root / 'unrelated working directory'
        self.cwd.mkdir()

    def run_cli(self, *args, **env):
        return subprocess.run(['bash', str(self.cli), *map(str, args)], cwd=self.cwd,
                              env=dict(self.env, **env), text=True, capture_output=True)

    def test_one_argument_handles_spaces_unicode_and_both_jar_layouts(self):
        for layout in ('repository', 'release'):
            with self.subTest(layout=layout):
                if layout == 'release':
                    lib = self.root / 'lib'
                    lib.mkdir()
                    shutil.move(self.jar, lib / 'docx-html-math.jar')
                result = self.run_cli(self.source)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                name = 'Đề thi có khoảng trắng-omml' + ('' if layout == 'repository' else '-2') + '.docx'
                self.assertEqual(self.original, (self.root / name).read_bytes())
                self.assertEqual(self.original, self.source.read_bytes())
                work = list(self.root.glob('*-omml-work-*'))
                self.assertTrue(any((p / 'sidecars/manifest.tsv').is_file() for p in work))
                self.assertTrue(all((p / 'conversion.log').is_file() for p in work))

    def test_existing_output_symlink_never_overwrites_original(self):
        output = self.root / 'Đề thi có khoảng trắng-omml.docx'
        output.symlink_to(self.source)
        result = self.run_cli(self.source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(output.is_symlink())
        self.assertEqual(self.original, self.source.read_bytes())
        self.assertEqual(self.original, (self.root / 'Đề thi có khoảng trắng-omml-2.docx').read_bytes())

    def test_missing_runtime_leaves_source_and_directory_untouched(self):
        shutil.rmtree(self.root / 'tools')
        result = self.run_cli(self.source)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('transpect', result.stderr)
        self.assertEqual([], list(self.root.glob('*-omml*')))
        self.assertEqual(self.original, self.source.read_bytes())

    def test_bad_input_or_argument_count_is_rejected(self):
        bad = self.root / 'fake.docx'
        bad.write_text('not a DOCX package')
        for args in [(), (self.source, self.source), (bad,), (self.root / 'absent.docx',)]:
            with self.subTest(args=args):
                self.assertNotEqual(0, self.run_cli(*args).returncode)
        self.assertEqual([], list(self.root.glob('*-omml*')))
        self.assertEqual(self.original, self.source.read_bytes())

    def test_failure_at_either_conversion_stage_publishes_no_docx(self):
        for stage in ('sidecar', 'java'):
            with self.subTest(stage=stage):
                result = self.run_cli(self.source, FAIL_STAGE=stage)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], list(self.root.glob('*-omml.docx')))
                self.assertEqual(self.original, self.source.read_bytes())
                logs = [p.read_text() for p in self.root.glob('*-omml-work-*/conversion.log')]
                self.assertTrue(any('failed' in log for log in logs))

    def test_old_java_is_rejected_before_creating_work_files(self):
        result = self.run_cli(self.source, TEST_JAVA_VERSION='1.8')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('17', result.stderr)
        self.assertEqual([], list(self.root.glob('*-omml*')))
