"""Shared usable-content gate for sidecar caches and manifests.

This establishes visible presentation content, not semantic equivalence.
"""
from pathlib import Path
import unicodedata
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/1998/Math/MathML'
TOKENS = {'mi', 'mn', 'mo', 'mtext', 'ms'}
HIDDEN = {'annotation', 'annotation-xml', 'mphantom', 'mspace', 'none', 'mprescripts'}
# Controls, format characters (U+2061, U+2062, U+200B, U+00AD ...) and separators show nothing
# by themselves. Same rule as MathmlContent.isVisibleCodePoint; shared vectors live in
# fixtures/mathml_content/visible_content_vectors.json.
INVISIBLE_CATEGORIES = {'Cc', 'Cf', 'Zs', 'Zl', 'Zp'}
KNOWN_ARTIFACT = ''


def is_visible_char(char):
    # CGJ and variation selectors are invisible Mn, not Cf. These ranges match Java
    # independently of the runtime Unicode version; ordinary combining accents stay.
    cp = ord(char)
    if (cp == 0x034F or 0x180B <= cp <= 0x180D or cp == 0x180F
            or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF):
        return False
    return char != KNOWN_ARTIFACT and not char.isspace() and unicodedata.category(char) not in INVISIBLE_CATEGORIES


def _name(element, require_namespace=False):
    if element.tag.startswith('{'):
        namespace, name = element.tag[1:].split('}', 1)
        return name if namespace == NS else None
    return None if require_namespace else element.tag


def _token_text(element, require_namespace):
    if not require_namespace:
        return ''.join(element.itertext())
    # A namespaced token cannot obtain visible content from a foreign subtree.
    # Tails belong to the MathML parent, so keep them even after foreign children.
    name = _name(element, True)
    if name is None or name in HIDDEN:
        return ''
    return (element.text or '') + ''.join(
        _token_text(child, True) + (child.tail or '') for child in element)


def _contains_token(element, require_namespace=False):
    name = _name(element, require_namespace)
    if name is None or name in HIDDEN:
        return False
    if name in TOKENS:
        return any(is_visible_char(char) for char in _token_text(element, require_namespace))
    children = list(element)
    if name == 'semantics':
        return bool(children) and _contains_token(children[0], require_namespace)
    return any(_contains_token(child, require_namespace) for child in children)


def is_usable_math_text(text: str, require_namespace=False) -> bool:
    try:
        if '<!DOCTYPE' in text.upper():
            return False
        root = ET.fromstring(text)
        return _name(root, require_namespace) == 'math' and _contains_token(root, require_namespace)
    except ET.ParseError:
        return False


def is_usable_math(path: Path) -> bool:
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return False
    return is_usable_math_text(text)
