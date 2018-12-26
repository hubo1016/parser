"""
Parse parser definitions
e.g.

tuple := expression ["," expression]*
"""
from __future__ import unicode_literals, print_function
from .parser import *
import re
import unicodedata

try:
    unichr
except Exception:
    unichr = chr

identifier = Token("([A-Za-z_][A-Za-z_0-9]*)", mapper=lambda m,t: (t, m.group(1)), name="identifier")

_default_escape_strs = {'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}

def default_escaped_mapper(s):
    if s[0] in ('u', 'U', 'x'):
        return unichr(int(s[1:], 16))
    elif s[0] >= '0' and s[0] <= '7':
        return unichr(int(s[1:], 8))
    elif s[0] in ('\r', '\n'):
        return ''
    elif s[0] == 'N':
        return unicodedata.lookup(s[2:-1])
    else:
        return _default_escape_strs.get(s, s)

def string_type(delimiter, name = 'str',
                escaped_regexp=r'[uU][a-fA-F0-9]{4}|x[a-fA-F0-9]{2}|[0-7]{1,3}|N\{[^\}\r\n\'\"]+\}|\r?\n|\r|[^\r\nuUxN0-7]',
                escaped_mapper=default_escaped_mapper):
    normal_string = Token('[^\\\\' + re.escape(delimiter) + ']+',
                        name="normalstr", mapper=lambda m,t: m.group(0))
    escaped_string = Token(r'\\(?:' + escaped_regexp + ')', name="escapedstr",
                        mapper=lambda m,t: escaped_mapper(m.group(0)[1:]))
    string_close = Switch()
    string_close.bind(Sequence(normal_string, string_close, flattern=True),
                      Sequence(escaped_string, string_close, flattern=True),
                      placeholder(delimiter, True))
    return Sequence(placeholder(delimiter, True), string_close, name=name,
                    mapper=lambda m,t: (t, ''.join(m)))

string = Switch(string_type(r'"', name='str'), string_type(r"'", name='str'),
                Sequence(placeholder('r', True), Switch(string_type(r'"', name='str',
                                                                escaped_regexp=r'\r?\n|\r|.',
                                                                escaped_mapper=lambda s: s),
                                                        string_type(r"'", name='str',
                                                                escaped_regexp=r'\r?\n|\r|.',
                                                                escaped_mapper=lambda s: s)),
                            mapper=lambda m,t: t[1]))

regexp = Switch(string_type(r'/', name='regexp'), string_type(r"~", name='regexp'),
                Sequence(placeholder('r', True), Switch(string_type(r'/', name='str',
                                                                    escaped_regexp=r'\r?\n|\r|.',
                                                                    escaped_mapper=lambda s: s),
                                                        string_type(r"~", name='str',
                                                                    escaped_regexp=r'\r?\n|\r|.',
                                                                    escaped_mapper=lambda s: s)),
                            mapper=lambda m,t: t[1]))

expression = Sequence(name="switch")

multi_mark = Switch(Token(r'[\*\+]', mapper=lambda m,t: (t, m.group(0)), name="multi"), allow_nomatch=True)

brackets_expression = Sequence(placeholder('(', True),
                                escaped_optional_space,
                                expression,
                                placeholder(')', True),
                                name="brackets")

square_brackets_expression = Sequence(placeholder('[', True),
                                escaped_optional_space,
                                expression,
                                placeholder(']', True),
                                name="brackets")

expression_part = Sequence(Switch(string, regexp, identifier, brackets_expression, square_brackets_expression),
                            multi_mark, escaped_optional_space, name="part")

expression_sequence_flattern = Sequence()

expression_sequence_flattern.bind(expression_part, Switch(expression_sequence_flattern, allow_nomatch=True),
                                    flattern=True)

expression_sequence = Sequence(expression_sequence_flattern, name="sequence")

expression_flattern = Sequence()

expression_flattern.bind(expression_sequence, Switch(Sequence(placeholder('|', True),
                                                     escaped_optional_space,
                                                     expression_sequence, flattern=True),
                         allow_nomatch=True),
                         flattern=True)

expression.bind(expression_flattern)

rule = Sequence(escaped_optional_space,
                identifier,
                escaped_optional_space,
                placeholder("::=", True),
                escaped_optional_space,
                expression,
                newline,
                name="rule")

document_flattern = Sequence()

document_flattern.bind(Sequence(Switch(rule, newline), escaped_optional_space, flattern=True), Switch(document_flattern, allow_nomatch=True), flattern=True)

document = Sequence(escaped_optional_space, document_flattern, name='document')

if __name__ == '__main__':
    import sys
    from pprint import pprint
    with open(sys.argv[1], 'r') as f:
        try:
            pprint(document.fullparse(f.read()))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            sys.exit(1)
