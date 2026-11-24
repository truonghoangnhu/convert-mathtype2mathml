#!/usr/bin/env bash
# One-argument Word/OMML conversion, usable in a checkout or extracted delivery ZIP.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo "Cần Python 3.9+ để chạy script này." >&2
  exit 2
fi
exec python3 - "$SCRIPT_DIR" "$@" <<'PY'
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

scripts = Path(sys.argv[1])
root = scripts.parent.parent
parser = argparse.ArgumentParser(
    prog='convert_docx_to_omml.sh',
    description='Chuyển DOCX có MathType sang OMML cho Word; giữ nguyên file gốc.')
parser.add_argument('docx', help='Đường dẫn file DOCX (đặt trong dấu nháy nếu có khoảng trắng)')
args = parser.parse_args(sys.argv[2:])
work = None


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check_docx(path):
    try:
        with zipfile.ZipFile(path) as doc:
            required = {'[Content_Types].xml', '_rels/.rels', 'word/document.xml'}
            if not required.issubset(doc.namelist()):
                raise ValueError('thiếu thành phần DOCX bắt buộc')
            document = ET.fromstring(doc.read('word/document.xml'))
            if document.tag != '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document':
                raise ValueError('document.xml không phải tài liệu Word được hỗ trợ')
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError('File không phải DOCX hợp lệ: ' + str(path)) from exc


def dependency(variable, default, directory=False):
    path = Path(os.environ.get(variable) or default).expanduser().resolve()
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError('Thiếu thành phần ' + variable + ': ' + str(path)
                         + '\nXem cách cài transpect/JAR trong ' + str(root / 'docs/dsmt4_delivery_guide.md'))
    return path


try:
    if sys.version_info < (3, 9):
        raise ValueError('Cần Python 3.9 trở lên.')
    source = Path(args.docx).expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() != '.docx':
        raise ValueError('Đầu vào phải là một file .docx.')
    check_docx(source)
    jar_default = root / 'lib/docx-html-math.jar'
    if not jar_default.is_file():
        jar_default = root / 'target/docx-html-math-1.0.0-jar-with-dependencies.jar'
    jar = dependency('DOCX_MATH_JAR', jar_default)
    runtime = root / 'tools/calabash'
    mathtype = dependency('MT_DIR', runtime / 'extensions/transpect/mathtype-extension', directory=True)
    calabash = dependency('XMLCALABASH_JAR', runtime / 'distro/xmlcalabash-1.4.1-100.jar')
    saxon = dependency('SAXON_HE_JAR', runtime / 'distro/lib/Saxon-HE-10.8.jar')
    generator = scripts / 'generate_sidecars.sh'
    if not generator.is_file():
        raise ValueError('Thiếu generate_sidecars.sh cạnh script chạy nhanh.')
    java = shutil.which('java')
    if java is None:
        raise ValueError('Cần cài Java 17 trở lên (không cần Maven khi dùng release).')
    version = subprocess.run([java, '-version'], capture_output=True, text=True, check=True)
    match = re.search(r'version\s+"([0-9]+)(?:\.([0-9]+))?', version.stdout + version.stderr)
    major = int(match.group(2) if match and match.group(1) == '1' else match.group(1)) if match else 0
    if major < 17:
        raise ValueError('Cần Java 17 trở lên; hãy kiểm tra java -version.')
    original_hash = digest(source)
    work = Path(tempfile.mkdtemp(prefix=source.stem[:80] + '-omml-work-', dir=source.parent))
    snapshot = work / 'input.docx'
    shutil.copy2(source, snapshot)
    if digest(snapshot) != original_hash:
        raise ValueError('File nguồn thay đổi trong lúc sao chép; chưa xuất kết quả.')
    staged = work / 'result.docx'
    log_path = work / 'conversion.log'
    with log_path.open('w', encoding='utf-8') as log:
        print('[1/2] Đang tạo sidecar MathML...', flush=True)
        subprocess.run(['bash', str(generator), str(snapshot), str(work / 'sidecars'),
                        str(mathtype), str(calabash), str(saxon)], stdout=log, stderr=subprocess.STDOUT, check=True)
        if not (work / 'sidecars/manifest.tsv').is_file():
            raise ValueError('Không có manifest sidecar; chưa xuất kết quả.')
        print('[2/2] Đang tạo DOCX OMML cho Word...', flush=True)
        subprocess.run([java, '-jar', str(jar), '--patch-docx', str(snapshot), str(staged),
                        '--mathml-manifest', str(work / 'sidecars/manifest.tsv'), '--patch-log-level', 'summary'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    check_docx(staged)
    if digest(source) != original_hash:
        raise ValueError('File nguồn đã thay đổi trong lúc chạy; chưa xuất kết quả cạnh file nguồn.')
    # Exclusive creation never follows or replaces an existing file/symlink. Works on
    # local macOS volumes and external filesystems that do not support hard links.
    index = 1
    while True:
        ending = '' if index == 1 else '-' + str(index)
        output = source.with_name(source.stem + '-omml' + ending + '.docx')
        try:
            stream = output.open('xb')
        except FileExistsError:
            index += 1
            continue
        try:
            with stream, staged.open('rb') as data:
                shutil.copyfileobj(data, stream)
        except BaseException:
            output.unlink()
            raise
        break
    print('Đã tạo: ' + str(output))
    print('Sidecar và nhật ký: ' + str(work))
    print('File gốc được giữ nguyên. Xem conversion.log để biết các công thức giữ OLE.')
except (OSError, ValueError, subprocess.CalledProcessError) as exc:
    print('Không hoàn tất chuyển đổi: ' + str(exc), file=sys.stderr)
    if work is not None:
        print('Dữ liệu kiểm tra/nhật ký: ' + str(work), file=sys.stderr)
    sys.exit(1)
PY
