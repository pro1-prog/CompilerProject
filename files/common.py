"""Shared definitions: errors, types, interval helpers."""
INT_MIN, INT_MAX = -2**31, 2**31 - 1
INT_RANGE = (INT_MIN, INT_MAX)


class MiniLangError(Exception):
    def __init__(self, phase, msg, line=None):
        loc = f" at line {line}" if line else ""
        super().__init__(f"[{phase} error{loc}] {msg}")
        self.phase, self.msg, self.line = phase, msg, line


class Type:
    """int, int[lo..hi] (range type) or bool."""
    def __init__(self, kind, lo=None, hi=None):
        self.kind, self.lo, self.hi = kind, lo, hi

    @property
    def is_int(self): return self.kind == "int"
    @property
    def is_bool(self): return self.kind == "bool"
    @property
    def is_plain(self): return self.is_int and (self.lo, self.hi) == INT_RANGE
    @property
    def interval(self): return (self.lo, self.hi)

    def __str__(self):
        if self.is_bool: return "bool"
        return "int" if self.is_plain else f"int[{self.lo}..{self.hi}]"
    __repr__ = __str__


INT = Type("int", INT_MIN, INT_MAX)
BOOL = Type("bool")


# ---- interval arithmetic helpers -------------------------------------------
def iv_hull(a, b): return (min(a[0], b[0]), max(a[1], b[1]))
def iv_meet(a, b):
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo <= hi else None
def iv_within(a, b): return b[0] <= a[0] and a[1] <= b[1]
def iv_str(a): return f"[{a[0]}..{a[1]}]" if a[0] != a[1] else f"[{a[0]}]"
