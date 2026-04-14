#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 5 ] || [ "$#" -gt 6 ]; then
  echo "Usage: $0 <input.docx> <out-dir> <mathtype-extension-dir> <xmlcalabash-jar> <saxon-he-jar> [transpect-config.xml]" >&2
  exit 1
fi

abs_path() {
  python3 - <<'PY' "$1"
import os
import sys
print(os.path.abspath(sys.argv[1]))
PY
}

now_ms() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

ms_to_sec() {
  python3 - <<'PY' "$1" "$2"
import sys
start = int(sys.argv[1])
end = int(sys.argv[2])
print(f"{(end - start) / 1000.0:.3f}")
PY
}

INPUT_DOCX=$(abs_path "$1")
OUT_DIR=$(abs_path "$2")
MATHTYPE_DIR=$(abs_path "$3")
XMLCALABASH_JAR=$(abs_path "$4")
SAXON_JAR=$(abs_path "$5")

TRANSPECT_CONFIG=""
if [ "$#" -eq 6 ]; then
  TRANSPECT_CONFIG=$(abs_path "$6")
elif [ -f "$(dirname "$MATHTYPE_DIR")/transpect-config.xml" ]; then
  TRANSPECT_CONFIG=$(abs_path "$(dirname "$MATHTYPE_DIR")/transpect-config.xml")
fi

DEFAULT_CACHE_BASE="$OUT_DIR/.cache/docx-html-math/transpect-sidecars"
CACHE_DIR=$(abs_path "${DOCX_MATH_CACHE_DIR:-$DEFAULT_CACHE_BASE}")

rm -rf "$OUT_DIR/unzipped" "$OUT_DIR/mathml" "$OUT_DIR/stage" "$OUT_DIR/tmp"
mkdir -p \
  "$OUT_DIR/unzipped" \
  "$OUT_DIR/mathml/wmf" \
  "$OUT_DIR/mathml/bin" \
  "$OUT_DIR/stage/wmf-src" \
  "$OUT_DIR/stage/wmf-needed-src" \
  "$OUT_DIR/stage/bin-src" \
  "$OUT_DIR/stage/bin-needed-src" \
  "$OUT_DIR/stage/bin-convert-src" \
  "$CACHE_DIR/wmf" \
  "$CACHE_DIR/bin" \
  "$OUT_DIR/tmp"
rm -f "$OUT_DIR/manifest.tsv" "$OUT_DIR/timings.tsv"
echo "[INFO] Persistent cache dir: $CACHE_DIR"

JRUBY_JAR=$(find "$MATHTYPE_DIR/lib" -maxdepth 1 -type f -name 'jruby-complete-*.jar' | sort | tail -n 1)
if [ -z "$JRUBY_JAR" ]; then
  echo "Could not find jruby-complete-*.jar in $MATHTYPE_DIR/lib" >&2
  exit 1
fi

RUBY_OLE_DIR=$(find "$MATHTYPE_DIR/ruby" -maxdepth 1 -type d -name 'ruby-ole-*' | sort | tail -n 1)
NOKOGIRI_DIR=$(find "$MATHTYPE_DIR/ruby" -maxdepth 1 -type d -name 'nokogiri-*-java' | sort | tail -n 1)
BINDATA_DIR=$(find "$MATHTYPE_DIR/ruby" -maxdepth 1 -type d -name 'bindata-*' | sort | tail -n 1)
MATHTYPE_RUBY_DIR=$(find "$MATHTYPE_DIR/ruby" -maxdepth 1 -type d -name 'mathtype-*' | sort | tail -n 1)

for required_dir in "$RUBY_OLE_DIR" "$NOKOGIRI_DIR" "$BINDATA_DIR" "$MATHTYPE_RUBY_DIR"; do
  if [ -z "$required_dir" ]; then
    echo "Could not locate one or more bundled Ruby dependency directories under $MATHTYPE_DIR/ruby" >&2
    exit 1
  fi
done

CALABASH_DISTRO_DIR=$(dirname "$XMLCALABASH_JAR")
CALABASH_LIB_CP=""
if [ -d "$CALABASH_DISTRO_DIR/lib" ]; then
  while IFS= read -r jar; do
    if [ -z "$CALABASH_LIB_CP" ]; then
      CALABASH_LIB_CP="$jar"
    else
      CALABASH_LIB_CP="$CALABASH_LIB_CP:$jar"
    fi
  done < <(find "$CALABASH_DISTRO_DIR/lib" -maxdepth 1 -type f -name '*.jar' | sort)
fi

MATHTYPE_CP="$XMLCALABASH_JAR"
if [ -n "$CALABASH_LIB_CP" ]; then
  MATHTYPE_CP="$MATHTYPE_CP:$CALABASH_LIB_CP"
fi
MATHTYPE_CP="$MATHTYPE_CP:$SAXON_JAR:$MATHTYPE_DIR:$JRUBY_JAR:$MATHTYPE_DIR/ruby/stdlib:$RUBY_OLE_DIR/lib:$NOKOGIRI_DIR/lib:$BINDATA_DIR/lib:$MATHTYPE_RUBY_DIR/lib"

IMPORT_URI=$(python3 - <<'PY' "$MATHTYPE_DIR/xpl/mathtype2mml-declaration-internal.xpl"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve().as_uri())
PY
)

BATCH_XPL="$OUT_DIR/tmp/mathtype-batch-files.xpl"
cat > "$BATCH_XPL" <<'XPL'
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc" xmlns:tr="http://transpect.io" xmlns:c="http://www.w3.org/ns/xproc-step" version="1.0" name="main">
  <p:import href="__IMPORT_URI__"/>
  <p:option name="source-dir" required="true"/>
  <p:option name="source-dir-uri" required="true"/>
  <p:option name="target-dir-uri" required="true"/>
  <p:option name="include-filter" select="'.*'"/>
  <p:option name="mml-ext" select="'.mathml'"/>

  <p:directory-list name="list">
    <p:with-option name="path" select="$source-dir"/>
    <p:with-option name="include-filter" select="$include-filter"/>
  </p:directory-list>

  <p:for-each name="each-file">
    <p:iteration-source select="/c:directory/c:file">
      <p:pipe port="result" step="list"/>
    </p:iteration-source>
    <p:variable name="name" select="/*/@name"/>
    <p:variable name="href" select="resolve-uri($name, $source-dir-uri)"/>
    <p:variable name="store-path" select="concat($target-dir-uri, $name, $mml-ext)"/>
    <p:try>
      <p:group>
        <tr:mathtype2mml-internal>
          <p:with-option name="href" select="$href"/>
        </tr:mathtype2mml-internal>
        <p:store>
          <p:with-option name="href" select="$store-path"/>
        </p:store>
      </p:group>
      <p:catch>
        <p:identity>
          <p:input port="source">
            <p:inline><math xmlns="http://www.w3.org/1998/Math/MathML"/></p:inline>
          </p:input>
        </p:identity>
        <p:store>
          <p:with-option name="href" select="$store-path"/>
        </p:store>
      </p:catch>
    </p:try>
  </p:for-each>
</p:declare-step>
XPL
python3 - <<'PY' "$BATCH_XPL" "$IMPORT_URI"
from pathlib import Path
import sys
path = Path(sys.argv[1])
import_uri = sys.argv[2]
path.write_text(path.read_text(encoding='utf-8').replace('__IMPORT_URI__', import_uri), encoding='utf-8')
PY

SINGLE_XPL="$OUT_DIR/tmp/mathtype-single-file.xpl"
cat > "$SINGLE_XPL" <<'XPL'
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc" xmlns:tr="http://transpect.io" version="1.0" name="main">
  <p:import href="__IMPORT_URI__"/>
  <p:output port="result" primary="true"/>
  <p:option name="href" required="true"/>
  <tr:mathtype2mml-internal>
    <p:with-option name="href" select="$href"/>
  </tr:mathtype2mml-internal>
</p:declare-step>
XPL
python3 - <<'PY' "$SINGLE_XPL" "$IMPORT_URI"
from pathlib import Path
import sys
path = Path(sys.argv[1])
import_uri = sys.argv[2]
path.write_text(path.read_text(encoding='utf-8').replace('__IMPORT_URI__', import_uri), encoding='utf-8')
PY

run_batch() {
  local source_dir="$1"
  local target_dir="$2"
  local include_filter="$3"
  local phase_name="$4"
  local file_count
  file_count=$(find "$source_dir" -maxdepth 1 -type f | wc -l | tr -d '[:space:]')

  if [ "$file_count" = "0" ]; then
    echo "[INFO] No files to convert for phase '$phase_name'"
    return 0
  fi
  echo "[INFO] Files queued for phase '$phase_name': $file_count"

  local source_uri
  local target_uri
  local before_count
  source_uri=$(python3 - <<'PY' "$source_dir"
from pathlib import Path
import sys
uri = Path(sys.argv[1]).resolve().as_uri()
if not uri.endswith('/'):
    uri += '/'
print(uri)
PY
)
  target_uri=$(python3 - <<'PY' "$target_dir"
from pathlib import Path
import sys
uri = Path(sys.argv[1]).resolve().as_uri()
if not uri.endswith('/'):
    uri += '/'
print(uri)
PY
)
  echo "[INFO] $phase_name source-dir: $source_dir"
  echo "[INFO] $phase_name source-dir-uri: $source_uri"
  echo "[INFO] $phase_name target-dir-uri: $target_uri"
  before_count=$(find "$target_dir" -maxdepth 1 -type f -name '*.mathml' | wc -l | tr -d '[:space:]')

  local -a calabash_cmd=(java -cp "$MATHTYPE_CP" com.xmlcalabash.drivers.Main)
  if [ -n "$TRANSPECT_CONFIG" ]; then
    calabash_cmd+=( -c "$TRANSPECT_CONFIG" )
  fi
  calabash_cmd+=( "$BATCH_XPL" "source-dir=$source_dir" "source-dir-uri=$source_uri" "target-dir-uri=$target_uri" "include-filter=$include_filter" )

  "${calabash_cmd[@]}" > "$OUT_DIR/tmp/${phase_name}.xml" 2> "$OUT_DIR/tmp/${phase_name}.log"
  local output_count
  local new_count
  output_count=$(find "$target_dir" -maxdepth 1 -type f -name '*.mathml' | wc -l | tr -d '[:space:]')
  new_count=$((output_count - before_count))
  if [ "$new_count" -lt 0 ]; then
    new_count=0
  fi
  echo "[INFO] Files newly written for phase '$phase_name': $new_count (total in target: $output_count)"
}

run_single_file() {
  local source_file="$1"
  local output_file="$2"
  local phase_name="$3"

  if [ ! -f "$source_file" ]; then
    return 1
  fi

  local file_uri
  file_uri=$(python3 - <<'PY' "$source_file"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve().as_uri())
PY
)

  local -a calabash_cmd=(java -cp "$MATHTYPE_CP" com.xmlcalabash.drivers.Main)
  if [ -n "$TRANSPECT_CONFIG" ]; then
    calabash_cmd+=( -c "$TRANSPECT_CONFIG" )
  fi
  calabash_cmd+=( "$SINGLE_XPL" "href=$file_uri" )

  "${calabash_cmd[@]}" > "$output_file" 2> "${output_file}.${phase_name}.log"
}

t_extract_start=$(now_ms)
unzip -o "$INPUT_DOCX" -d "$OUT_DIR/unzipped" >/dev/null
t_extract_end=$(now_ms)

t_scan_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/unzipped" "$OUT_DIR/tmp/refs.json" "$OUT_DIR/stage/wmf-src" "$OUT_DIR/stage/bin-src"
import hashlib
import json
import posixpath
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

unzipped_dir = Path(sys.argv[1])
refs_json = Path(sys.argv[2])
wmf_stage = Path(sys.argv[3])
bin_stage = Path(sys.argv[4])

ns = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'v': 'urn:schemas-microsoft-com:vml',
    'o': 'urn:schemas-microsoft-com:office:office',
}

rid_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def normalize_part(path: str | None) -> str | None:
    if not path:
        return None
    p = path.replace('\\', '/').strip()
    if not p:
        return None
    if p.startswith('/'):
        normalized = posixpath.normpath(p)
    else:
        normalized = posixpath.normpath('/word/' + p)
    if not normalized.startswith('/'):
        normalized = '/' + normalized
    return normalized

def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def classify_prog_id(prog_id: str | None) -> str:
    normalized = (prog_id or '').strip().lower()
    if any(tok in normalized for tok in ('equation', 'mathtype', 'dsmt', 'mtef')):
        return 'equation'
    if any(tok in normalized for tok in ('chemdraw', 'chemsketch', 'chemwindow', 'acd.')):
        return 'chemical-diagram'
    if any(tok in normalized for tok in ('visio', 'diagram', 'graph', 'chart')):
        return 'diagram'
    return 'illustration'

relationships_file = unzipped_dir / 'word/_rels/document.xml.rels'
document_file = unzipped_dir / 'word/document.xml'

if not relationships_file.exists() or not document_file.exists():
    payload = {
        'referenced_wmf_parts': [],
        'referenced_bin_parts': [],
        'object_pairs': [],
        'wmf_part_to_hash': {},
        'bin_part_to_hash': {},
        'wmf_hash_to_file': {},
        'bin_hash_to_file': {},
    }
    refs_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')
    print("Referenced WMF parts: 0")
    print("Referenced BIN parts: 0")
    print("Unique WMF payloads (sha256): 0")
    print("Unique BIN payloads (sha256): 0")
    raise SystemExit(0)

rels_root = ET.parse(relationships_file).getroot()
rid_to_target = {
    rel.attrib.get('Id'): normalize_part(rel.attrib.get('Target'))
    for rel in rels_root
    if rel.attrib.get('Id')
}

doc_root = ET.parse(document_file).getroot()

def resolve_rid(rid: str | None) -> str | None:
    return normalize_part(rid_to_target.get(rid)) if rid else None

referenced_wmf = set()
referenced_bin = set()
object_pairs = []

for obj in doc_root.findall('.//w:object', ns):
    ole_el = obj.find('.//o:OLEObject', ns)
    preview_el = obj.find('.//v:imagedata', ns)
    prog_id = None
    if ole_el is not None:
        prog_id = ole_el.attrib.get('ProgID') or ole_el.attrib.get('progId')
    ole_part = resolve_rid(ole_el.attrib.get(rid_ns + 'id') if ole_el is not None else None)
    wmf_part = resolve_rid(preview_el.attrib.get(rid_ns + 'id') if preview_el is not None else None)

    if wmf_part and wmf_part.lower().endswith('.wmf'):
        referenced_wmf.add(wmf_part)
    if ole_part and ole_part.lower().endswith('.bin'):
        referenced_bin.add(ole_part)

    object_pairs.append({
        'prog_id': prog_id,
        'object_kind': classify_prog_id(prog_id),
        'preview_part': wmf_part,
        'ole_part': ole_part,
        'wmf': wmf_part if wmf_part and wmf_part.lower().endswith('.wmf') else None,
        'bin': ole_part if ole_part and ole_part.lower().endswith('.bin') else None,
    })

for blip in doc_root.findall('.//a:blip', ns):
    rid = blip.attrib.get(rid_ns + 'embed')
    part = resolve_rid(rid)
    if part and part.lower().endswith('.wmf'):
        referenced_wmf.add(part)

for image_data in doc_root.findall('.//v:imagedata', ns):
    rid = image_data.attrib.get(rid_ns + 'id')
    part = resolve_rid(rid)
    if part and part.lower().endswith('.wmf'):
        referenced_wmf.add(part)

for ole in doc_root.findall('.//o:OLEObject', ns):
    rid = ole.attrib.get(rid_ns + 'id')
    part = resolve_rid(rid)
    if part and part.lower().endswith('.bin'):
        referenced_bin.add(part)

wmf_part_to_hash = {}
bin_part_to_hash = {}
wmf_hash_to_file = {}
bin_hash_to_file = {}

for part in sorted(referenced_wmf):
    source = unzipped_dir / part.lstrip('/')
    if not source.exists():
        continue
    digest = file_hash(source)
    stage_name = f"{digest}.wmf"
    staged = wmf_stage / stage_name
    if not staged.exists():
        shutil.copy2(source, staged)
    wmf_part_to_hash[part] = digest
    wmf_hash_to_file[digest] = stage_name

for part in sorted(referenced_bin):
    source = unzipped_dir / part.lstrip('/')
    if not source.exists():
        continue
    digest = file_hash(source)
    stage_name = f"{digest}.bin"
    staged = bin_stage / stage_name
    if not staged.exists():
        shutil.copy2(source, staged)
    bin_part_to_hash[part] = digest
    bin_hash_to_file[digest] = stage_name

payload = {
    'referenced_wmf_parts': sorted(wmf_part_to_hash.keys()),
    'referenced_bin_parts': sorted(bin_part_to_hash.keys()),
    'object_pairs': object_pairs,
    'wmf_part_to_hash': wmf_part_to_hash,
    'bin_part_to_hash': bin_part_to_hash,
    'wmf_hash_to_file': wmf_hash_to_file,
    'bin_hash_to_file': bin_hash_to_file,
}
refs_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')

print(f"Referenced WMF parts: {len(payload['referenced_wmf_parts'])}")
print(f"Referenced BIN parts: {len(payload['referenced_bin_parts'])}")
print(f"Unique WMF payloads (sha256): {len(wmf_hash_to_file)}")
print(f"Unique BIN payloads (sha256): {len(bin_hash_to_file)}")
PY
t_scan_end=$(now_ms)

t_wmf_prepare_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/refs.json" "$CACHE_DIR/wmf" "$OUT_DIR/mathml/wmf" "$OUT_DIR/stage/wmf-src" "$OUT_DIR/stage/wmf-needed-src"
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

refs_path = Path(sys.argv[1])
cache_dir = Path(sys.argv[2])
wmf_math_dir = Path(sys.argv[3])
wmf_stage_dir = Path(sys.argv[4])
wmf_needed_dir = Path(sys.argv[5])
refs = json.loads(refs_path.read_text(encoding='utf-8'))

for stale in wmf_needed_dir.glob('*'):
    if stale.is_file():
        stale.unlink()

suppressed_preview_parts = {
    pair.get('preview_part')
    for pair in refs.get('object_pairs', [])
    if pair.get('preview_part') and pair.get('object_kind') not in {'equation', '', None}
}

def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

cache_hits = 0
cache_misses = 0
cache_failed_hits = 0
scheduled_hashes = set()
for part, digest in sorted(refs.get('wmf_part_to_hash', {}).items()):
    if part in suppressed_preview_parts or digest in scheduled_hashes:
        continue
    staged_file = wmf_stage_dir / f"{digest}.wmf"
    target_mathml = wmf_math_dir / f"{digest}.wmf.mathml"
    cached_mathml = cache_dir / f"{digest}.wmf.mathml"
    failed_marker = cache_dir / f"{digest}.wmf.failed"
    if is_usable_math(cached_mathml):
        if target_mathml != cached_mathml:
            shutil.copy2(cached_mathml, target_mathml)
        cache_hits += 1
        scheduled_hashes.add(digest)
        continue
    if failed_marker.exists():
        cache_failed_hits += 1
        scheduled_hashes.add(digest)
        continue
    if staged_file.exists():
        needed_file = wmf_needed_dir / staged_file.name
        if needed_file != staged_file:
            shutil.copy2(staged_file, needed_file)
        cache_misses += 1
        scheduled_hashes.add(digest)

print(f"WMF cache hits: {cache_hits}")
print(f"WMF known-failed cache hits: {cache_failed_hits}")
print(f"WMF cache misses queued for convert: {cache_misses}")
print(f"WMF preview parts suppressed from math conversion: {len(suppressed_preview_parts)}")
PY
t_wmf_prepare_end=$(now_ms)

t_wmf_batch_start=$(now_ms)
run_batch "$OUT_DIR/stage/wmf-needed-src" "$OUT_DIR/mathml/wmf" '.*\.wmf' 'wmf-batch'
t_wmf_batch_end=$(now_ms)

t_wmf_cache_write_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/refs.json" "$OUT_DIR/mathml/wmf" "$CACHE_DIR/wmf"
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

refs_path = Path(sys.argv[1])
wmf_math_dir = Path(sys.argv[2])
cache_dir = Path(sys.argv[3])
refs = json.loads(refs_path.read_text(encoding='utf-8'))

def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

written = 0
failed = 0
recovered = 0
for digest in sorted(refs.get('wmf_hash_to_file', {}).keys()):
    source = wmf_math_dir / f"{digest}.wmf.mathml"
    target = cache_dir / f"{digest}.wmf.mathml"
    failed_marker = cache_dir / f"{digest}.wmf.failed"
    if not is_usable_math(source):
        if source.exists():
            failed_marker.write_text("failed\n", encoding='utf-8')
            failed += 1
        continue
    if failed_marker.exists():
        failed_marker.unlink()
        recovered += 1
    if target.exists() and is_usable_math(target):
        continue
    shutil.copy2(source, target)
    written += 1

print(f"WMF cache writes: {written}")
print(f"WMF cache failure markers set: {failed}")
print(f"WMF cache failure markers cleared: {recovered}")
PY
t_wmf_cache_write_end=$(now_ms)

t_bin_select_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/refs.json" "$OUT_DIR/mathml/wmf" "$OUT_DIR/stage/bin-src" "$OUT_DIR/stage/bin-needed-src" "$OUT_DIR/tmp/state.json"
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

refs_path = Path(sys.argv[1])
wmf_math_dir = Path(sys.argv[2])
bin_stage_dir = Path(sys.argv[3])
bin_needed_dir = Path(sys.argv[4])
state_path = Path(sys.argv[5])

refs = json.loads(refs_path.read_text(encoding='utf-8'))

for stale in bin_needed_dir.glob('*'):
    if stale.is_file():
        stale.unlink()

def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

wmf_usable_parts = set()
for part, digest in refs['wmf_part_to_hash'].items():
    candidate = wmf_math_dir / f"{digest}.wmf.mathml"
    if is_usable_math(candidate):
        wmf_usable_parts.add(part)

suppressed_preview_parts = {
    pair.get('preview_part')
    for pair in refs.get('object_pairs', [])
    if pair.get('preview_part') and pair.get('object_kind') not in {'equation', '', None}
}
wmf_usable_parts.difference_update(suppressed_preview_parts)

paired_bins = set()
bins_needed = set()
for pair in refs['object_pairs']:
    bin_part = pair.get('bin')
    wmf_part = pair.get('wmf')
    object_kind = pair.get('object_kind')
    if not bin_part:
        continue
    paired_bins.add(bin_part)
    if object_kind not in {'equation', '', None}:
        continue
    if wmf_part and wmf_part in wmf_usable_parts:
        continue
    bins_needed.add(bin_part)

for standalone_bin in refs['referenced_bin_parts']:
    if standalone_bin not in paired_bins:
        bins_needed.add(standalone_bin)

needed_hashes = set()
for bin_part in sorted(bins_needed):
    digest = refs['bin_part_to_hash'].get(bin_part)
    stage_file = refs['bin_hash_to_file'].get(digest)
    if not digest or not stage_file:
        continue
    if digest in needed_hashes:
        continue
    source = bin_stage_dir / stage_file
    target = bin_needed_dir / stage_file
    if source.exists() and not target.exists():
        shutil.copy2(source, target)
    needed_hashes.add(digest)

state = dict(refs)
state['wmf_usable_parts'] = sorted(wmf_usable_parts)
state['bins_needed'] = sorted(bins_needed)
state['bin_needed_hashes'] = sorted(needed_hashes)
state['suppressed_non_equation_preview_parts'] = sorted(suppressed_preview_parts)
state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding='utf-8')

print(f"WMF parts with usable MathML: {len(wmf_usable_parts)}")
print(f"BIN parts required after WMF pass: {len(bins_needed)}")
print(f"Unique BIN payloads required: {len(needed_hashes)}")
print(f"Non-equation preview parts suppressed: {len(suppressed_preview_parts)}")
PY
t_bin_select_end=$(now_ms)

t_bin_cache_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/state.json" "$CACHE_DIR/bin" "$OUT_DIR/mathml/bin" "$OUT_DIR/stage/bin-needed-src" "$OUT_DIR/stage/bin-convert-src"
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

state_path = Path(sys.argv[1])
cache_dir = Path(sys.argv[2])
bin_math_dir = Path(sys.argv[3])
bin_needed_dir = Path(sys.argv[4])
bin_convert_dir = Path(sys.argv[5])
state = json.loads(state_path.read_text(encoding='utf-8'))

for stale in bin_convert_dir.glob('*'):
    if stale.is_file():
        stale.unlink()

def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

cache_hits = 0
cache_misses = 0
cache_failed_hits = 0
for digest in state.get('bin_needed_hashes', []):
    source_bin = bin_needed_dir / f"{digest}.bin"
    target_mathml = bin_math_dir / f"{digest}.bin.mathml"
    cached_mathml = cache_dir / f"{digest}.bin.mathml"
    failed_marker = cache_dir / f"{digest}.bin.failed"
    if is_usable_math(cached_mathml):
        if target_mathml != cached_mathml:
            shutil.copy2(cached_mathml, target_mathml)
        cache_hits += 1
        continue
    if failed_marker.exists():
        cache_failed_hits += 1
        continue
    if source_bin.exists():
        shutil.copy2(source_bin, bin_convert_dir / source_bin.name)
        cache_misses += 1

print(f"BIN cache hits: {cache_hits}")
print(f"BIN known-failed cache hits: {cache_failed_hits}")
print(f"BIN cache misses queued for convert: {cache_misses}")
PY
t_bin_cache_end=$(now_ms)

t_bin_convert_start=$(now_ms)
run_batch "$OUT_DIR/stage/bin-convert-src" "$OUT_DIR/mathml/bin" '.*\.bin' 'bin-batch'
t_bin_convert_end=$(now_ms)

t_bin_fallback_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/state.json" "$OUT_DIR/mathml/bin" "$OUT_DIR/tmp/bin-fallback-hashes.txt"
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

state_path = Path(sys.argv[1])
bin_math_dir = Path(sys.argv[2])
fallback_file = Path(sys.argv[3])
state = json.loads(state_path.read_text(encoding='utf-8'))

def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

fallback_hashes = []
for digest in state.get('bin_needed_hashes', []):
    candidate = bin_math_dir / f"{digest}.bin.mathml"
    if not is_usable_math(candidate):
        fallback_hashes.append(digest)

fallback_file.write_text("\n".join(fallback_hashes), encoding='utf-8')
print(f"BIN hashes requiring single-file fallback: {len(fallback_hashes)}")
PY

while IFS= read -r digest; do
  [ -z "$digest" ] && continue
  source_bin="$OUT_DIR/stage/bin-needed-src/$digest.bin"
  target_mathml="$OUT_DIR/mathml/bin/$digest.bin.mathml"
  run_single_file "$source_bin" "$target_mathml" "single-bin-fallback" || true
done < "$OUT_DIR/tmp/bin-fallback-hashes.txt"
t_bin_fallback_end=$(now_ms)

t_bin_cache_write_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/state.json" "$OUT_DIR/mathml/bin" "$CACHE_DIR/bin"
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

state_path = Path(sys.argv[1])
bin_math_dir = Path(sys.argv[2])
cache_dir = Path(sys.argv[3])
state = json.loads(state_path.read_text(encoding='utf-8'))

def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

written = 0
failed = 0
recovered = 0
for digest in state.get('bin_needed_hashes', []):
    source = bin_math_dir / f"{digest}.bin.mathml"
    target = cache_dir / f"{digest}.bin.mathml"
    failed_marker = cache_dir / f"{digest}.bin.failed"
    if not is_usable_math(source):
        if source.exists():
            failed_marker.write_text("failed\n", encoding='utf-8')
            failed += 1
        continue
    if failed_marker.exists():
        failed_marker.unlink()
        recovered += 1
    if target.exists() and is_usable_math(target):
        continue
    shutil.copy2(source, target)
    written += 1

print(f"BIN cache writes: {written}")
print(f"BIN cache failure markers set: {failed}")
print(f"BIN cache failure markers cleared: {recovered}")
PY
t_bin_cache_write_end=$(now_ms)

t_manifest_start=$(now_ms)
python3 - <<'PY' "$OUT_DIR/tmp/state.json" "$OUT_DIR/mathml/wmf" "$OUT_DIR/mathml/bin" "$OUT_DIR/manifest.tsv"
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

state_path = Path(sys.argv[1])
wmf_math_dir = Path(sys.argv[2])
bin_math_dir = Path(sys.argv[3])
manifest_path = Path(sys.argv[4])

state = json.loads(state_path.read_text(encoding='utf-8'))


def is_usable_math(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding='utf-8', errors='ignore').strip()
    if '<math' not in text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    if root.tag.split('}')[-1] != 'math':
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return True
    if (root.text or '').strip():
        return True
    return False

manifest_entries = []
wmf_success = 0
for part in sorted(state['wmf_usable_parts']):
    digest = state['wmf_part_to_hash'].get(part)
    if not digest:
        continue
    rel_path = f"mathml/wmf/{digest}.wmf.mathml"
    abs_path = manifest_path.parent / rel_path
    if is_usable_math(abs_path):
        manifest_entries.append((part, rel_path))
        wmf_success += 1

bin_success = 0
for part in sorted(state['bins_needed']):
    digest = state['bin_part_to_hash'].get(part)
    if not digest:
        continue
    rel_path = f"mathml/bin/{digest}.bin.mathml"
    abs_path = manifest_path.parent / rel_path
    if is_usable_math(abs_path):
        manifest_entries.append((part, rel_path))
        bin_success += 1

manifest_entries.sort(key=lambda pair: pair[0])
with manifest_path.open('w', encoding='utf-8') as out:
    for part, rel in manifest_entries:
        out.write(f"{part}\t{rel}\n")

print(f"Manifest entries: {len(manifest_entries)}")
print(f"Manifest WMF entries: {wmf_success}")
print(f"Manifest BIN entries: {bin_success}")
PY
t_manifest_end=$(now_ms)

t_report_start=$(now_ms)
python3 - <<'PY' "$INPUT_DOCX" "$OUT_DIR/tmp/state.json" "$OUT_DIR/manifest.tsv" "$OUT_DIR/manifest.lineage-report.json"
import hashlib
import json
import sys
from pathlib import Path

input_docx = Path(sys.argv[1]).resolve()
state_path = Path(sys.argv[2])
manifest_path = Path(sys.argv[3])
report_path = Path(sys.argv[4])

state = json.loads(state_path.read_text(encoding='utf-8'))
manifest_entries = []
if manifest_path.exists():
    for raw in manifest_path.read_text(encoding='utf-8').splitlines():
        if "\t" not in raw:
            continue
        part, rel = raw.split("\t", 1)
        manifest_entries.append({"part": part, "rel_path": rel})

manifest_parts = {entry["part"] for entry in manifest_entries}
dsmt4_pairs = [pair for pair in state.get("object_pairs", []) if pair.get("prog_id") == "Equation.DSMT4"]
dsmt4_total = len(dsmt4_pairs)
dsmt4_manifest_mapped = sum(
    1 for pair in dsmt4_pairs
    if pair.get("preview_part") in manifest_parts or pair.get("ole_part") in manifest_parts
)
dsmt4_unresolved = dsmt4_total - dsmt4_manifest_mapped

report = {
    "input_docx": str(input_docx),
    "input_docx_sha256": hashlib.sha256(input_docx.read_bytes()).hexdigest(),
    "manifest_path": str(manifest_path.resolve()),
    "manifest_entry_count": len(manifest_entries),
    "wmf_manifest_entries": sum(1 for entry in manifest_entries if entry["part"].lower().endswith(".wmf")),
    "bin_manifest_entries": sum(1 for entry in manifest_entries if entry["part"].lower().endswith(".bin")),
    "dsmt4_total": dsmt4_total,
    "dsmt4_manifest_mapped": dsmt4_manifest_mapped,
    "dsmt4_unresolved_after_generation": dsmt4_unresolved,
    "dsmt4_unresolved_pairs": [
        {
            "preview_part": pair.get("preview_part"),
            "ole_part": pair.get("ole_part"),
        }
        for pair in dsmt4_pairs
        if pair.get("preview_part") not in manifest_parts and pair.get("ole_part") not in manifest_parts
    ],
}
report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding='utf-8')
print(f"Manifest lineage report: {report_path}")
print(f"DSMT4 total: {dsmt4_total}")
print(f"DSMT4 manifest mapped: {dsmt4_manifest_mapped}")
print(f"DSMT4 unresolved after generation: {dsmt4_unresolved}")
PY
t_report_end=$(now_ms)

extract_sec=$(ms_to_sec "$t_extract_start" "$t_extract_end")
scan_sec=$(ms_to_sec "$t_scan_start" "$t_scan_end")
wmf_cache_read_sec=$(ms_to_sec "$t_wmf_prepare_start" "$t_wmf_prepare_end")
wmf_batch_sec=$(ms_to_sec "$t_wmf_batch_start" "$t_wmf_batch_end")
wmf_cache_write_sec=$(ms_to_sec "$t_wmf_cache_write_start" "$t_wmf_cache_write_end")
bin_select_sec=$(ms_to_sec "$t_bin_select_start" "$t_bin_select_end")
bin_cache_read_sec=$(ms_to_sec "$t_bin_cache_start" "$t_bin_cache_end")
bin_convert_sec=$(ms_to_sec "$t_bin_convert_start" "$t_bin_convert_end")
bin_fallback_sec=$(ms_to_sec "$t_bin_fallback_start" "$t_bin_fallback_end")
bin_cache_write_sec=$(ms_to_sec "$t_bin_cache_write_start" "$t_bin_cache_write_end")
manifest_sec=$(ms_to_sec "$t_manifest_start" "$t_manifest_end")
report_sec=$(ms_to_sec "$t_report_start" "$t_report_end")

wmf_sec=$(python3 - <<'PY' "$wmf_cache_read_sec" "$wmf_batch_sec" "$wmf_cache_write_sec"
import sys
vals = [float(v) for v in sys.argv[1:]]
print(f"{sum(vals):.3f}")
PY
)

bin_fallback_total_sec=$(python3 - <<'PY' "$bin_select_sec" "$bin_cache_read_sec" "$bin_convert_sec" "$bin_fallback_sec" "$bin_cache_write_sec"
import sys
vals = [float(v) for v in sys.argv[1:]]
print(f"{sum(vals):.3f}")
PY
)

printf "phase\tseconds\n" > "$OUT_DIR/timings.tsv"
printf "extract\t%s\n" "$extract_sec" >> "$OUT_DIR/timings.tsv"
printf "reference-scan-and-staging\t%s\n" "$scan_sec" >> "$OUT_DIR/timings.tsv"
printf "wmf-cache-read\t%s\n" "$wmf_cache_read_sec" >> "$OUT_DIR/timings.tsv"
printf "wmf-batch-convert\t%s\n" "$wmf_batch_sec" >> "$OUT_DIR/timings.tsv"
printf "wmf-cache-write\t%s\n" "$wmf_cache_write_sec" >> "$OUT_DIR/timings.tsv"
printf "bin-selection\t%s\n" "$bin_select_sec" >> "$OUT_DIR/timings.tsv"
printf "bin-cache-read\t%s\n" "$bin_cache_read_sec" >> "$OUT_DIR/timings.tsv"
printf "bin-batch-convert\t%s\n" "$bin_convert_sec" >> "$OUT_DIR/timings.tsv"
printf "bin-single-fallback\t%s\n" "$bin_fallback_sec" >> "$OUT_DIR/timings.tsv"
printf "bin-cache-write\t%s\n" "$bin_cache_write_sec" >> "$OUT_DIR/timings.tsv"
printf "manifest-write\t%s\n" "$manifest_sec" >> "$OUT_DIR/timings.tsv"
printf "manifest-lineage-report\t%s\n" "$report_sec" >> "$OUT_DIR/timings.tsv"
printf "reference-scan\t%s\n" "$scan_sec" >> "$OUT_DIR/timings.tsv"
printf "wmf-convert\t%s\n" "$wmf_sec" >> "$OUT_DIR/timings.tsv"
printf "bin-fallback\t%s\n" "$bin_fallback_total_sec" >> "$OUT_DIR/timings.tsv"

equation_total=$(python3 - <<'PY' "$wmf_sec" "$bin_fallback_total_sec"
import sys
vals = [float(v) for v in sys.argv[1:]]
print(f"{sum(vals):.3f}")
PY
)
printf "equation-conversion-total\t%s\n" "$equation_total" >> "$OUT_DIR/timings.tsv"

echo "Manifest written to: $OUT_DIR/manifest.tsv"
echo "Timings written to:  $OUT_DIR/timings.tsv"
cat "$OUT_DIR/timings.tsv"
