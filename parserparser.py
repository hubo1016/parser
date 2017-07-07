"""
Parse parser definitions
e.g.

tuple := expression ["," expression]*
"""
from .parser import *
import re


identifier = Token("([A-Za-z_][A-Za-z_0-9]*)", mapper=lambda m,t: (t, m.group(1)))


def string_type(delimiter)
    normal_string = Token('[^\\\\' + re.escape(delimiter) + ']+')
    escaped_string = Token(r'\\(?:.|\r?\n|\r)')
    string_close = Switch()
    string_close.bind(Sequence(normal_string, string_close), Sequence(escaped_string, string_close), placeholder(delimiter, True))
    return Sequence(placeholder(delimiter, True), string_close)


definition = Sequence(identifier, optional_space, placeholder(":=", True), optional_space, )