import curses


# The docstring contains \\\\ to show a \\ when interpreted
class DisplayStr:
    """A Class to allow (basic) formatting of strings
     inside a curses display.

    DisplayStrs are created from strings with embedded format specifiers
     of the form `...[formatchars:text to format]...`
    Valid formatchars are available in DisplayStr.FORMAT_CODES
    All '[' and ']' should be escaped with a \\ - note that two backslashes
     are needed to create a literal backslash that DisplayStr will interpret
     as a single backslash.
    There is no need to escape ':' - the first ':' after an unescaped '['
     signifies the ending formatchars and all other ':'s are treated as text
    Example: "You [s:MUST] escape \\\\[ and \\\\] (but : is fine)"
     creates the string "You MUST escape [ and ] (but : is fine)"
     with 'MUST' displayed in curses.A_STANDOUT
    """

    FORMAT_CODES = {
        "u": curses.A_UNDERLINE,
        "s": curses.A_STANDOUT,
        "f": curses.A_BLINK  # f for flash, and to not conflict with bold
        # Bold doesn't look good in light mode
        #  - figure out why and fix before adding it
        #'b': curses.A_BOLD
    }

    def __init__(self, content: str):
        self._orig_str = content
        self.segments = DisplayStr._parse_content(content)
        self._display_chars = "".join(seg[0] for seg in self.segments)

    def __repr__(self):
        return self._orig_str

    def __str__(self):
        return self._display_chars

    def __len__(self):
        return len(self._display_chars)

    @staticmethod
    def _from_other(other):
        otherstr = str(other)
        if isinstance(other, DisplayStr):
            otherstr = other._orig_str
        othersegs = DisplayStr._parse_content(otherstr)
        otherdisp = "".join(seg[0] for seg in othersegs)
        return otherstr, othersegs, otherdisp

    def __add__(self, other):
        otherstr, othersegs, otherdisp = DisplayStr._from_other(other)

        ret = DisplayStr("")
        ret._orig_str = self._orig_str + otherstr
        ret.segments = self.segments + othersegs
        ret._display_chars = self._display_chars + otherdisp
        return ret

    def __radd__(self, other):
        otherstr, othersegs, otherdisp = DisplayStr._from_other(other)

        ret = DisplayStr("")
        ret._orig_str = otherstr + self._orig_str
        ret.segments = othersegs + self.segments
        ret._display_chars = otherdisp + self._display_chars
        return ret

    def __iadd__(self, other):
        otherstr, othersegs, otherdisp = DisplayStr._from_other(other)

        self._orig_str += otherstr
        self.segments += othersegs
        self._display_chars += otherdisp
        return self

    def __mul__(self, other):
        ret = DisplayStr("")
        ret._orig_str = self._orig_str * other
        ret.segments = self.segments * other
        ret._display_chars = self._display_chars * other
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        self._orig_str *= other
        self.segments *= other
        self._display_chars *= other

    def __contains__(self, item):
        return item in self._display_chars

    def _check_range(self, idx, allow_len=False):
        if idx < 0:
            idx = len(self) + idx
        if idx < 0 or idx > len(self) or (not allow_len and idx == len(self)):
            raise IndexError
        return idx

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            if start is None:
                start = 0
            if stop is None:
                stop = len(self)
            if step is None:
                step = 1
        elif isinstance(key, int):
            start, stop, step = key, key + 1, 1
        else:
            raise TypeError(f"Invalid key for DStr[key]: {type(key)}")

        start = self._check_range(start)
        stop = self._check_range(stop, allow_len=True)
        if stop < start:
            raise IndexError("DStrs do not support reverse slicing")
        if step < 0:
            raise IndexError("DStrs do not support reverse slicing")

        newsegs = [([], curses.A_NORMAL)]

        try:
            i = -1
            iterator = DisplayStr.Iterator(self)
            while i < start:
                iterator.step()
                i += 1

            while i < stop:
                seg = self.segments[iterator.segidx]
                c = seg[0][iterator.charinsegidx]
                if seg[1] != newsegs[-1][1]:
                    newsegs.append(([c], seg[1]))
                else:
                    newsegs[-1][0].append(c)

                for _ in range(step):
                    iterator.step()
                    i += 1
        except StopIteration:
            pass

        if not newsegs[0][0]:
            del newsegs[0]

        newsegs = [("".join(seg[0]), seg[1]) for seg in newsegs]
        disp = "".join(seg[0] for seg in newsegs)

        ret = DisplayStr("")
        ret._orig_str = f"<sliced DStr (no creation string): {disp}>"
        ret.segments = newsegs
        ret._display_chars = disp

        return ret

    class Iterator:
        def __init__(self, dstr):
            self.dstr = dstr
            self.segidx = 0
            self.charinsegidx = -1
            self.done = not (dstr.segments and dstr.segments[0][0])

        def __iter__(self):
            return self

        def step(self):
            if self.done:
                raise StopIteration
            self.charinsegidx += 1
            while self.charinsegidx >= len(self.dstr.segments[self.segidx][0]):
                self.segidx += 1
                if self.segidx >= len(self.dstr.segments):
                    self.done = True
                    raise StopIteration
                self.charinsegidx = 0

        def curr(self):
            seg = self.dstr.segments[self.segidx]
            char = seg[self.charinsegidx]
            ret = DisplayStr("")
            ret._orig_str = f"<DStr from iterating {repr(self.dstr)}>"
            ret.segments = [(char, seg[1])]
            ret._display_chars = char
            return ret

        def __next__(self):
            self.step()
            return self.curr()

    def __iter__(self):
        return DisplayStr.Iterator(self)

    @staticmethod
    def _parse_content(content: str):
        if not content:
            return []

        segments = [([], curses.A_NORMAL)]

        S_TEXT = 0
        S_FORMATTERS = 1
        S_ESCAPE = 2
        state = S_TEXT

        format_stack = [curses.A_NORMAL]
        formatter_chars = []

        for c in content:
            if state == S_TEXT:
                if c == "\\":
                    state = S_ESCAPE
                elif c == "[":
                    formatter_chars = []
                    state = S_FORMATTERS
                elif c == "]":
                    format_stack.pop()
                    segments.append(([], format_stack[-1]))
                else:
                    segments[-1][0].append(c)
            elif state == S_FORMATTERS:
                if c == ":":
                    formatter = format_stack[-1]
                    for fchar in formatter_chars:
                        if fchar in DisplayStr.FORMAT_CODES:
                            formatter |= DisplayStr.FORMAT_CODES[fchar]
                    segments.append(([], formatter))
                    format_stack.append(formatter)
                    state = S_TEXT
                else:
                    formatter_chars.append(c)
            elif state == S_ESCAPE:
                segments[-1][0].append(c)

        return [("".join(seg[0]), seg[1]) for seg in segments]
