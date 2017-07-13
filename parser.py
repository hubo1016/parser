"""
Basic Parser structures
"""
import re
import reprlib

class ParserException(Exception):
    def __init__(self, message, source, position):
        super().__init__(self, message)
        self.source = source
        self.position = position


class ParserNotMatchException(ParserException):
    pass


class ParserFatalException(ParserException):
    pass


class Structure(object):
    def bind(self, *args, **kwargs):
        raise NotImplementedError
        
    def __init__(self, *args, name = None, forcebind = False, **kwargs):
        self.name = name
        if args or kwargs or forcebind:
            self.bind(*args, **kwargs)
    
    def _base_repr(self, inner):
        return '<' + type(self).__name__ + ' ' + inner + '>'
    
    def __repr__(self):
        return self._base_repr(repr(self.name) if self.name is not None else '')
    
    def parse(self, source, start, end):
        """
        Return (parsed, next_start) when the input string can be parsed into
        this structure, where parsed is the returning object, and next_start
        is the starting position of the next . Raises a ParserException if it cannot.
        """
        raise NotImplementedError

    def fullparse(self, source, start, end):
        """
        Return (parsed, next_start) when the input string can be fully parsed
        into this structure without remaining data. next_start should be the same
        as end.
        """
        parsed, next_start = self.parse(source, start, end)
        if next_start != end:
            raise ParserFatalException("extra unparsed data", source, end)
        return (parsed, next_start)


def _safecall(mapper, *args, **kwargs):
    try:
        return mapper(*args, **kwargs)
    except ParserException:
        raise
    except Exception as exc:
        raise ParserFatalException(str(exc), source, start)


class Token(Structure):
    """
    Regular expression match
    """
    def bind(self, pattern, mapper=lambda m,t: (t, m.groups()), flags=0, escape=False):
        """
        :param pattern: regular expression to match
        
        :param mapper: a function mapper(match, type) -> return_obj to generate the returning object,
                       where match is the match object and type is the current token type (i.e. self)
        
        :param name: a name to mark this type
        
        :param flags: regular expression flags
        """
        if self.name is None:
            self.name = pattern
        if escape:
            pattern = re.escape(pattern)
        self._pattern = re.compile(pattern, flags)
        self._mapper = mapper
    
    def parse(self, source, start, end):
        m = self._pattern.match(source, start, end)
        if not m:
            raise ParserNotMatchException("cannot match " + repr(self), source, start)
        return (_safecall(self._mapper, m, self), m.end())


def placeholder(pattern, escape=False):
    return Token(pattern, mapper=lambda m,t: None, escape=escape)


space = placeholder(r"[ \t]+")
optional_space = placeholder(r"[ \t]*")
space_newline = placeholder(r"[ \t\n\r]+")
optional_space_newline = placeholder(r"[ \t\n\r]*")
newline = placeholder(r"\r\n?|\n")
escaped_optional_space = placeholder(r"[ \t]*(?:\\(?:\r\n?|\n)[ \t]*)*")

class Sequence(Structure):
    """
    A sequence of other structures
    """
    def bind(self, *args, mapper=lambda m,t: (t,m), flattern=False):
        """
        :param args: one or more structures
        
        :param mapper: mapper(tuple, type) where tuple is a tuple of parsed objects and type is
                       current structure (self)
        
        :param flattern: if True, sequence result will be flattern into the parent if it is
                         embedded into another sequence
        """
        if not args:
            raise ValueError("At lease one structure should be specified")
        self._seqs = args
        self._mapper = mapper
        self._flattern = flattern
        
    def parse(self, source, start, end):
        next_pos = start
        return_obj = []
        for structure in self._seqs:
            obj, next_pos = structure.parse(source, start, end)
            if obj is not None:
                return_obj.append(obj)
        return (_safecall(self._mapper, self.flattern(return_obj), self), next_pos)

    def fullparse(self, source, start, end):
        next_pos = start
        return_obj = []
        for structure in self._seqs[-1]:
            obj, next_pos = structure.parse(source, start, end)
            if obj is not None:
                return_obj.append(obj)
        obj, next_pos = self._seqs[-1].fullparse(source, start, end)
        if obj is not None:
            return_obj.append(obj)
        return (_safecall(self._mapper, self.flattern(return_obj), self), next_pos)

    @reprlib.recursive_repr()
    def __repr__(self):
        if self.name is None:
            return self._base_repr(reprlib.repr(self._seqs))
        else:
            return super().__repr__()

    def flattern(self, value):
        result = []
        for v in value:
            if isinstance(v, tuple) and isinstance(v[0], Sequence) and v[0]._flattern:
                result.extend(v[1])
            else:
                result.append(v)
        return tuple(result)


class Switch(Structure):
    """
    Match any of the given structures
    """
    def bind(self, *args, mapper=lambda o,m,t: o, allow_nomatch = False):
        """
        :param args: one or more structures
        
        :param mapper: mapper(obj, match_structure, type) where tuple is a tuple of parsed objects,
                       match_structure is the matched structure, and type is
                       current structure (self)
        
        :param allow_nomatch: return None when not matched instead of raises Exception
        """
        self._switches = args
        self._mapper = mapper
        self._allow_nomatch = allow_nomatch

    def add(self, structure):
        if structure not in self._switches:
            self._switches.append(structure)

    def remove(self, structure):
        self._switches.remove(structure)

    def parse(self, source, start, end):
        for s in self._switches:
            try:
                obj, next_start = s.parse(source, start, end)
            except ParserNotMatchException:
                pass
            else:
                break
        else:
            if self._allow_nomatch:
                return (None, start)
            else:
                raise ParserNotMatchException("No valid match for " repr(self), source, start, end)
        return (_safecall(self._mapper, obj, s, self), next_start)

    def fullparse(self, source, start, end):
        for s in self._switches:
            try:
                obj, next_start = s.fullparse(source, start, end)
            except ParserNotMatchException:
                pass
            else:
                break
        else:
            if self._allow_nomatch:
                if start == end:
                    return (None, start)
                else:
                    raise ParserNotMatchException("No valid full match for " repr(self), source, start, end)
            raise ParserNotMatchException("No valid full match for " repr(self), source, start, end)
        return (_safecall(self._mapper, obj, s, self), next_start)

    @reprlib.recursive_repr()
    def __repr__(self):
        if self.name is None:
            return self._base_repr(reprlib.repr(self._switches))
        else:
            return super().__repr__()
