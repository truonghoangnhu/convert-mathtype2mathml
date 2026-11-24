#!/usr/bin/env python3
"""Assemble the scoped DSMT4 delivery from a clean, built checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='2026.11.24')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'out/releases')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.version):
        parser.error('version must be a filename-safe identifier')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT):
        parser.error('commit tracked working-tree changes before packaging')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    jar = ROOT / 'target/docx-html-math-1.0.0-jar-with-dependencies.jar'
    if not jar.is_file():
        parser.error('missing built JAR; run mvn package first')
    name = 'dsmt4-migration-' + args.version
    out = args.out_dir.resolve()
    zip_path = out / (name + '.zip')
    jar_path = out / (name + '.jar')
    sums_path = out / (name + '-SHA256SUMS')
    if any(p.exists() for p in (zip_path, jar_path, sums_path)):
        parser.error('output exists; choose a new output directory')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [p for p in tracked if p and (p.startswith(('docs/', 'scripts/transpect/',
             'fixtures/dsmt4/chemistry-arrows/', 'samples/')) or p in ('README.md', 'LICENSE_transpect_docx2hub.txt'))]
    payload = {p: (ROOT / p).read_bytes() for p in paths}
    payload['lib/docx-html-math.jar'] = jar.read_bytes()
    payload['START_HERE.md'] = (
        '# DSMT4 migration delivery\n\n'
        'Read [the delivery guide](docs/dsmt4_delivery_guide.md) for checksum verification, '
        'examples, external-runtime installation and the scoped acceptance results.\n\n'
        'Run the guide commands from this extracted top-level folder.\n'
    ).encode()
    payload['BUILD_INFO.json'] = (json.dumps({
        'version': args.version, 'source_commit': revision,
        'jar_sha256': hashlib.sha256(payload['lib/docx-html-math.jar']).hexdigest(),
        'external_runtime_bundled': False,
        'acceptance_snapshot': 'docs/acceptance/dsmt4-2026-11-24/',
    }, indent=2) + '\n').encode()
    payload['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + path + '\n'
                                    for path, data in sorted(payload.items())).encode()
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name + '/' + path, date_time=(2026, 11, 24, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 if path.endswith('.sh') else 0o100644) << 16
            archive.writestr(entry, data)
    with jar_path.open('xb') as stream:
        stream.write(payload['lib/docx-html-math.jar'])
    with sums_path.open('x') as stream:
        for path in (zip_path, jar_path):
            stream.write(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n')
    print(json.dumps({'zip': str(zip_path), 'jar': str(jar_path), 'checksums': str(sums_path),
                      'source_commit': revision}, indent=2))


if __name__ == '__main__':
    main()
