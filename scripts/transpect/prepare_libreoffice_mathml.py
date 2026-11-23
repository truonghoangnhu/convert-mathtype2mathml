#!/usr/bin/env python3
"""Prepare a separate MathML candidate for LibreOffice Math, never for Word.

Bounded W/L/T/G/C/I/B/D/A/V compatibility rules measured on LibreOffice 26.8.0.3.
G groups explicitly unseparated ()/|| fence arguments. C completes only the
demonstrated +/2+/3+ exponents on a single ASCII-letter mi base. I handles comma-decimal
[a;b) intervals; B handles a leading |mi_sub_mi| followed by equals. D makes
only the delimiters of an explicit msup('(', '°'), mi C, mo ')' sequence literal,
retaining the original script base and degree position.
A supplies left alignment for unstyled, flat three-row assignment systems using
a generated StarMath annotation alongside the unchanged presentation MathML.
Only integer/ASCII-letter terms and +/minus are accepted; annotation is authoritative
in the measured importer, so unverified shapes and grammar never receive it.
Preparation
does not validate formula equivalence, application rendering, or DOCX roundtrips.
The mfenced expansion (F) investigated in scratch is deliberately not included.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

try:
    from .mathml_content import NS, is_usable_math_text
except ImportError:  # Direct script invocation, alongside mathml_content.py.
    from mathml_content import NS, is_usable_math_text

ET.register_namespace('', NS)
META = {'semantics', 'annotation', 'annotation-xml'}
LEAD = frozenset('<>≤≥=→')
TRAIL = frozenset('=>→')
SUSPECT = frozenset('<>=≤≥≠≈≡∼≃≅∝∈∉⊂⊃⊆⊇→←↔⇒⇐⇔⇌⇄⩽⩾≪≫')
CONTAINERS = {'math', 'mrow', 'msqrt', 'mstyle', 'mtd', 'menclose',
              'mpadded', 'mphantom', 'merror'}


def _is_math(el, name=None):
    return isinstance(el.tag, str) and el.tag.startswith('{' + NS + '}') and (
        name is None or el.tag == '{' + NS + '}' + name)


def _local(el):
    return el.tag.split('}', 1)[-1]


def _row():
    return ET.Element('{' + NS + '}mrow')


def _aligned_assignment_command(root):
    """Return a command only for the whole, measured flat assignment-system shape."""
    if root.attrib or len(root) != 1:
        return None
    fence = root[0]
    if (not _is_math(fence, 'mfenced') or len(fence) != 1
            or fence.attrib != {'open': '{', 'close': '', 'separators': ''}):
        return None
    table = fence[0]
    if (not _is_math(table, 'mtable') or table.attrib != {'columnalign': 'left'}
            or len(table) != 3):
        return None
    for el in root.iter():
        if ((len(el) and (el.text or '').strip(' \t\r\n'))
                or (el.tail or '').strip(' \t\r\n')):
            return None
    rows = []
    for row in table:
        if not _is_math(row, 'mtr') or row.attrib or len(row) != 1:
            return None
        cell = row[0]
        if not _is_math(cell, 'mtd') or cell.attrib or len(cell) < 3:
            return None
        tokens = []
        for leaf in cell:
            if leaf.attrib or len(leaf):
                return None
            kind, text = _local(leaf), leaf.text or ''
            if not ((kind == 'mi' and re.fullmatch(r'[A-Za-z]', text))
                    or (kind == 'mn' and re.fullmatch(r'[0-9]+', text))
                    or (kind == 'mo' and text in {'=', '+', '-', '−'})):
                return None
            tokens.append((kind, text))
        if tokens[0][0] != 'mi' or tokens[1] != ('mo', '='):
            return None
        # RHS = optional initial minus, term, (binary plus/minus, term)*.
        # term = integer with at most one following letter, or one letter.
        # In particular, adjacent numbers/letters, chained relations, incomplete
        # operators and arbitrary StarMath commands are never synthesized.
        i = 2
        if tokens[i] in {('mo', '-'), ('mo', '−')}:
            i += 1
        while True:
            if i >= len(tokens) or tokens[i][0] not in {'mi', 'mn'}:
                return None
            number = tokens[i][0] == 'mn'
            i += 1
            if number and i < len(tokens) and tokens[i][0] == 'mi':
                i += 1
            if i == len(tokens):
                break
            if tokens[i] not in {('mo', '+'), ('mo', '-'), ('mo', '−')}:
                return None
            i += 1
        rows.append('alignl { ' + ' '.join(t.replace('−', '-') for _, t in tokens) + ' }')
    return 'left lbrace matrix{ ' + ' ## '.join(rows) + ' } right none'


def _vector_integer_triple_command(root):
    """Only a whole unstyled vector assignment to three signed integer coordinates."""
    def leaf(el, tag, text=None):
        return (_is_math(el, tag) and not el.attrib and not len(el)
                and (text is None or el.text == text))
    if root.attrib or len(root) != 1:
        return None
    row = root[0]
    if not _is_math(row, 'mrow') or row.attrib or len(row) != 3:
        return None
    if any((len(n) and (n.text or '').strip(' \t\r\n'))
           or (n.tail or '').strip(' \t\r\n') for n in root.iter()):
        return None
    vector, equals, fence = row
    if (not _is_math(vector, 'mover') or vector.attrib != {'accent': 'true'} or len(vector) != 2
            or not leaf(vector[0], 'mi') or not re.fullmatch('[A-Za-z]', vector[0].text or '')
            or not leaf(vector[1], 'mo', '→') or not leaf(equals, 'mo', '=')
            or not _is_math(fence, 'mfenced')
            or fence.attrib != {'open': '(', 'close': ')', 'separators': ''} or len(fence) != 1):
        return None
    coords = fence[0]
    if not _is_math(coords, 'mrow') or coords.attrib:
        return None
    tokens = list(coords)
    result, i = [], 0
    for axis in range(3):
        if i < len(tokens) and leaf(tokens[i], 'mo') and tokens[i].text in {'-', '−'}:
            result.append('-'); i += 1
        if (i >= len(tokens) or not leaf(tokens[i], 'mn')
                or not re.fullmatch('0|[1-9][0-9]*', tokens[i].text or '')):
            return None
        result.append(tokens[i].text); i += 1
        if axis < 2:
            if i >= len(tokens) or not leaf(tokens[i], 'mo', ';'):
                return None
            result.append(';'); i += 1
    if i != len(tokens):
        return None
    return 'vec ' + vector[0].text + ' = left ( ' + ' '.join(result) + ' right )'


def _adapt(root):
    changes, untested = [], []

    def note(rule, path, reason):
        untested.append({'rule': rule, 'path': path, 'reason': reason})

    def operator(el):
        return ''.join(el.itertext()).strip() if _is_math(el, 'mo') else None

    def leaf(el, name, text=None):
        return (_is_math(el, name) and not el.attrib and len(el) == 0
                and (text is None or el.text == text))

    def xml_space(text):
        return not (text or '').strip(' \t\r\n')

    def empty_row(el):
        return leaf(el, 'mrow') and xml_space(el.text)

    def plain_letter(el):
        return leaf(el, 'mi') and re.fullmatch(r'[A-Za-z]', el.text or '') is not None

    def positive_exponent(el, path):
        # Literal +, 2+, 3+ exponents; this does not identify chemical ions.
        if (len(el) != 2 or el.attrib or not plain_letter(el[0])
                or not xml_space(el.text) or any(not xml_space(k.tail) for k in el)):
            return False
        exp = el[1]
        if leaf(exp, 'mo', '+'):
            row = _row()
            el.remove(exp)
            row.extend([exp, _row()])
            el.append(row)
            changes.append({'rule': 'C', 'path': path, 'exponent': '+', 'shape': 'wrapped'})
            return True
        if not _is_math(exp, 'mrow') or exp.attrib or not xml_space(exp.text):
            return False
        kids = list(exp)
        if kids and empty_row(kids[-1]):
            kids = kids[:-1]
            already = True
        else:
            already = False
        supported = ((len(kids) == 1 and leaf(kids[0], 'mo', '+'))
                     or (len(kids) == 2 and leaf(kids[0], 'mn')
                         and kids[0].text in {'2', '3'} and leaf(kids[1], 'mo', '+')))
        if not supported or any(not xml_space(k.tail) for k in exp):
            return False
        if not already:
            exp.append(_row())
            changes.append({'rule': 'C', 'path': path,
                            'exponent': ''.join(k.text or '' for k in kids), 'shape': 'appended'})
        return True

    def celsius_delimiters(el, path, verified_context):
        if el.attrib or not xml_space(el.text) or any(not xml_space(k.tail) for k in el):
            return
        kids = list(el)
        matches = []
        for i in range(len(kids) - 2):
            sup, unit, closing = kids[i:i + 3]
            if (not _is_math(sup, 'msup') or sup.attrib or len(sup) != 2
                    or not xml_space(sup.text) or any(not xml_space(k.tail) for k in sup)
                    or not leaf(sup[0], 'mo', '(') or not leaf(sup[1], 'mo', '°')
                    or not leaf(unit, 'mi', 'C') or not leaf(closing, 'mo', ')')):
                continue
            matches.append((i, sup, closing))
        if not matches:
            return
        if not verified_context or len(matches) != 1:
            note('D', path, 'nested/styled/combined or multiple-unit context outside demonstrated scope')
            return
        i, sup, closing = matches[0]
        depth = 0
        for j, child in enumerate(kids):
            if j == i and depth:
                note('D', path, 'unit nested inside other bare parentheses is unprobed')
                return
            if i <= j <= i + 2:
                continue
            simple_token = any(leaf(child, kind) for kind in ('mi', 'mo', 'mn'))
            plain_space = (_is_math(child, 'mspace') and len(child) == 0
                           and not (set(child.attrib) - {'width'}) and xml_space(child.text))
            if not (simple_token or plain_space):
                note('D', path, 'non-flat or styled sibling context is unprobed')
                return
            if _is_math(child, 'mo'):
                if child.text in {'[', ']', '{', '}', '|'}:
                    note('D', path, 'other fence context is unprobed')
                    return
                if child.text == '(':
                    depth += 1
                elif child.text == ')':
                    depth -= 1
                    if depth < 0:
                        break
        if depth:
            note('D', path, 'other bare parentheses are unbalanced')
            return
        # Retain the script base/degree; quote only its adjacent delimiter pair.
        sup[0].tag = '{' + NS + '}mtext'
        closing.tag = '{' + NS + '}mtext'
        changes.append({'rule': 'D', 'path': f'{path}/msup[{i}]',
                        'close_path': f'{path}/mtext[{i + 2}]',
                        'unit': '°C', 'shape': 'literal_script_delimiters'})

    def explicit_fences(el, path):
        if el.attrib or not xml_space(el.text) or any(not xml_space(k.tail) for k in el):
            return
        kids = list(el)
        if (len(kids) == 5 and leaf(kids[0], 'mo', '[') and leaf(kids[4], 'mo', ')')
                and leaf(kids[2], 'mo', ';')
                and all(leaf(kids[i], 'mn') and re.fullmatch(r'[0-9]+,[0-9]+', kids[i].text or '')
                        for i in (1, 3))):
            fence = ET.Element('{' + NS + '}mfenced', open='[', close=')', separators='')
            inner = _row()
            inner.text = kids[0].tail
            for child in kids:
                el.remove(child)
            inner.extend(kids[1:4])
            fence.append(inner)
            fence.tail = kids[4].tail
            el.append(fence)
            changes.append({'rule': 'I', 'path': path, 'open': '[', 'close': ')'})
        elif (len(kids) >= 5 and leaf(kids[0], 'mo', '|') and leaf(kids[2], 'mo', '|')
              and leaf(kids[3], 'mo', '=') and _is_math(kids[1], 'msub')
              and not kids[1].attrib and xml_space(kids[1].text) and len(kids[1]) == 2
              and all(plain_letter(k) and xml_space(k.tail) for k in kids[1])):
            fence = ET.Element('{' + NS + '}mfenced', open='|', close='|', separators='')
            fence.text = kids[0].tail
            for child in kids[:3]:
                el.remove(child)
            fence.append(kids[1])
            fence.tail = kids[2].tail
            el.insert(0, fence)
            changes.append({'rule': 'B', 'path': path, 'open': '|', 'close': '|'})

    kids = list(root)
    if len(kids) > 1:
        if any(not _is_math(k) or _local(k) in META for k in kids):
            note('W', 'math', 'foreign namespace or semantics/annotation child')
        else:
            wrapper = _row()
            wrapper.text, root.text = root.text, None
            for child in kids:
                root.remove(child)
                wrapper.append(child)
            root.append(wrapper)
            changes.append({'rule': 'W', 'path': 'math', 'children': len(kids)})

    def visit(el, path, inside_fence=False):
        if not _is_math(el):
            note('*', path, 'foreign or namespace-free subtree preserved, not entered')
            return
        name = _local(el)
        if name in META:
            note('*', path, 'semantics/annotation not entered')
            return
        if name in {'mtable', 'mtr', 'mtd'} and any(
                value in {'left', 'right'} for value in el.get('columnalign', '').split()):
            note('table_alignment', path,
                 'noncentered column alignment is preserved in MathML; '
                 'LibreOffice Math layout is not certified (left-alignment probe failed)')
        if name == 'msup' and positive_exponent(el, path):
            # The verified exponent is complete. Do not reinterpret its literal
            # charge sign as an operator-only relation sequence, including on rerun.
            return
        if name == 'mrow':
            if inside_fence:
                if len(el) and operator(el[0]) in {'[', '|'}:
                    note('I/B', path, 'nested fence context outside demonstrated scope')
            else:
                explicit_fences(el, path)
        if name == 'mfenced' and len(el) > 1:
            # With no separators, MathML treats the arguments as one sequence.
            # LO otherwise repeats the close fence between the arguments. Keep
            # the mfenced envelope: expanding bars into mo tokens loses them.
            fences = (el.get('open', '('), el.get('close', ')'))
            if (el.get('separators') == '' and fences in {('(', ')'), ('|', '|')}
                    and not (set(el.attrib) - {'open', 'close', 'separators'})
                    and not (el.text or '').strip(' \t\r\n')
                    and all(not (k.tail or '').strip(' \t\r\n') for k in el)):
                child_count = len(el)
                wrapper = _row()
                wrapper.text, el.text = el.text, None
                for child in list(el):
                    el.remove(child)
                    wrapper.append(child)
                el.append(wrapper)
                changes.append({'rule': 'G', 'path': path, 'open': fences[0], 'close': fences[1],
                                'children': child_count})
            else:
                note('G', path, 'fence/separator/attributes outside demonstrated grouping scope')
        kids = list(el)
        nonempty = [k for k in kids if not (
            _is_math(k, 'mrow') and len(k) == 0 and not (k.text or '').strip())]
        if name in CONTAINERS and nonempty:
            if name == 'mrow' and inside_fence:
                # G must not expand the demonstrated L/T context within fences. This also
                # applies on a second preparation of the already grouped XML.
                if operator(nonempty[0]) in SUSPECT or operator(nonempty[-1]) in SUSPECT:
                    note('L/T', path, 'fenced argument row outside demonstrated relation scope')
            elif any(not _is_math(k) for k in kids):
                if any(operator(k) in SUSPECT for k in kids):
                    note('L/T', path, 'foreign namespace sibling')
            elif all(_local(k) == 'mo' for k in nonempty):
                if any(operator(k) in SUSPECT or operator(k) in {'+', '-', '−', '±', '∓'} for k in nonempty):
                    note('operator_only', path, 'no demonstrated operand; no L/T repair')
            else:
                first, last = nonempty[0], nonempty[-1]
                if operator(first) in SUSPECT and kids[0] is first:
                    if operator(first) in LEAD and name in {'mrow', 'msqrt'}:
                        el.insert(0, _row())
                        changes.append({'rule': 'L', 'path': path, 'op': operator(first)})
                    else:
                        note('L', path, 'relation/container outside demonstrated scope')
                if operator(last) in SUSPECT and list(el)[-1] is last:
                    if operator(last) in TRAIL and name == 'mrow':
                        el.append(_row())
                        changes.append({'rule': 'T', 'path': path, 'op': operator(last)})
                    else:
                        note('T', path, 'relation/container outside demonstrated scope')
        for i, child in enumerate(list(el)):
            visit(child, f'{path}/{_local(child)}[{i}]', inside_fence or name == 'mfenced')

    visit(root, 'math')
    # Resolve D after every structural rule so its audit paths name the final
    # candidate tree. Only W+D in one flat unstyled top-level row was probed.
    def finish_degree(el, path):
        if _is_math(el, 'mrow'):
            verified = (len(root) == 1 and el is root[0] and not root.attrib
                        and all(c['rule'] == 'W' for c in changes))
            celsius_delimiters(el, path, verified)
        for i, child in enumerate(list(el)):
            finish_degree(child, f'{path}/{_local(child)}[{i}]')

    finish_degree(root, 'math')
    return changes, untested


def prepare(xml):
    """Return (candidate or None, JSON-compatible preparation report)."""
    report = {'status': 'unsupported', 'target': 'libreoffice_math_mathml_import',
              'path_space': 'candidate_tree',
              'application_acceptance': 'not_run', 'changes': [], 'untested': [],
              'limitations': ['Not for normalized MathML/OMML used by Word.',
                              'Writer DOCX leading relations and system-row alignment can fail.',
                              'Content, editability, placement and application reopening need review.']}
    if '<!DOCTYPE' in xml.upper():
        raise ValueError('DOCTYPE is not allowed')
    root = ET.fromstring(xml)
    if not _is_math(root, 'math'):
        report['reason'] = 'LibreOffice Math requires a namespaced MathML math root'
        return None, report
    if not is_usable_math_text(xml, require_namespace=True):
        report['reason'] = 'no visible presentation content; source retained'
        return None, report
    # ElementTree reserialization can lose xmlns="" resets or namespace bindings
    # used only in QName-valued metadata. Do not adapt any branch of mixed input:
    # preserving such subtrees requires preserving the original XML serialization.
    if any(not _is_math(el) or _local(el) in META for el in root.iter()):
        report.update(status='needs_review', untested=[{
            'rule': '*', 'path': 'math',
            'reason': 'mixed namespace or metadata input kept byte-identical; no W/L/T/G/C/I/B/D/A/V applied'}])
        return xml, report
    command = _aligned_assignment_command(root)
    if command is not None:
        semantics = ET.Element('{' + NS + '}semantics')
        presentation = root[0]
        root.remove(presentation)
        semantics.append(presentation)
        ET.SubElement(semantics, '{' + NS + '}annotation',
                      {'encoding': 'StarMath 5.0'}).text = command
        root.append(semantics)
        report.update(status='needs_review', changes=[{
            'rule': 'A', 'path': 'math', 'shape': 'three_flat_assignment_rows',
            'rows': 3, 'annotation_encoding': 'StarMath 5.0', 'command': command,
            'annotation_priority_measured_on': 'LibreOffice 26.8.0.3'}])
        return ET.tostring(root, encoding='unicode'), report
    changes, untested = _adapt(root)
    vector_command = _vector_integer_triple_command(root)
    if vector_command is not None:
        semantics = ET.Element('{' + NS + '}semantics')
        presentation = root[0]
        root.remove(presentation)
        semantics.append(presentation)
        ET.SubElement(semantics, '{' + NS + '}annotation',
                      {'encoding': 'StarMath 5.0'}).text = vector_command
        root.append(semantics)
        changes.append({'rule': 'V', 'path': 'math', 'command': vector_command,
                        'annotation_encoding': 'StarMath 5.0',
                        'annotation_priority_measured_on': 'LibreOffice 26.8.0.3',
                        'scope': 'whole unstyled single-letter vector and three integer coordinates'})
    report.update(status='needs_review', changes=changes, untested=untested)
    # Leave untouched input byte-identical whenever no rule applies.
    return (ET.tostring(root, encoding='unicode') if changes else xml), report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='New LibreOffice-only MathML file; never overwritten')
    args = parser.parse_args(argv)
    try:
        if args.source.resolve() == args.output.resolve():
            raise ValueError('source and output must be different files')
        if args.output.exists():
            raise FileExistsError('output already exists; choose a new path')
        source = args.source.read_bytes()
        candidate, report = prepare(source.decode('utf-8'))
        report.update(source=str(args.source), source_sha256=hashlib.sha256(source).hexdigest())
        if candidate is None:
            print(json.dumps(report, ensure_ascii=False))
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(candidate)
        report.update(output=str(args.output), output_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError, ET.ParseError) as exc:
        print(json.dumps({'status': 'failed', 'reason': str(exc), 'application_acceptance': 'not_run'}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
