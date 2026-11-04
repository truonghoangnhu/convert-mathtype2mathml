"""Shared usable-content gate for sidecar caches and manifests.

This establishes visible presentation content, not semantic equivalence.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/1998/Math/MathML'
TOKENS = {'mi', 'mn', 'mo', 'mtext', 'ms'}
HIDDEN = {'annotation', 'annotation-xml', 'mphantom', 'mspace', 'none', 'mprescripts'}


def _name(element):
    if element.tag.startswith('{'):
        namespace, name = element.tag[1:].split('}', 1)
        return name if namespace == NS else None
    return element.tag


def _contains_token(element):
    name = _name(element)
    if name is None or name in HIDDEN:
        return False
    if name in TOKENS:
        return bool(''.join(element.itertext()).replace('\uef0a', '').strip())
    children = list(element)
    if name == 'semantics':
        return bool(children) and _contains_token(children[0])
    return any(_contains_token(child) for child in children)


def is_usable_math(path: Path) -> bool:
    try:
        text = path.read_text(encoding='utf-8')
        if '<!DOCTYPE' in text.upper():
            return False
        root = ET.fromstring(text)
        return _name(root) == 'math' and _contains_token(root)
    except (OSError, UnicodeError, ET.ParseError):
        return False
