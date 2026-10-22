"""Phase 3 - Semantic analysis.

* symbol table with nested scopes
* strict type checking (int / int[lo..hi] / bool, NO implicit conversions)
* NOVELTY: flow-sensitive interval (range) analysis. Every expression gets a
  provable range; range-typed assignments are PROVEN safe at compile time,
  REJECTED if they can never fit, or protected by a runtime guard otherwise.
"""
from common import *
from ast_nodes import *

ARITH, CMP, EQ, LOGIC = {"+", "-", "*", "/", "%"}, {"<", ">", "<=", ">="}, {"==", "!="}, {"&&", "||"}
NEG = {"<": ">=", ">": "<=", "<=": ">", ">=": "<", "==": "!=", "!=": "=="}
FLIP = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "==": "==", "!=": "!="}


def iv_add(a, b): return (a[0] + b[0], a[1] + b[1])
def iv_sub(a, b): return (a[0] - b[1], a[1] - b[0])
def iv_mul(a, b):
    c = [x * y for x in a for y in b]
    return (min(c), max(c))

def tdiv(a, b):                       # C-style truncating division
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q

def iv_div(a, b):
    parts = []
    if b[0] <= -1: parts.append((b[0], min(b[1], -1)))
    if b[1] >= 1:  parts.append((max(b[0], 1), b[1]))
    c = [tdiv(x, y) for p in parts for x in a for y in p]
    return (min(c), max(c))

def iv_mod(a, b):
    m = max(abs(b[0]), abs(b[1])) - 1
    if a[0] >= 0: return (0, min(a[1], m))
    if a[1] <= 0: return (max(a[0], -m), 0)
    return (max(a[0], -m), min(a[1], m))

def cmp_iv(op, a, b):
    """Abstract comparison -> True / False / None (unknown)."""
    if op == "<":  return True if a[1] < b[0] else False if a[0] >= b[1] else None
    if op == "<=": return True if a[1] <= b[0] else False if a[0] > b[1] else None
    if op == ">":  return True if a[0] > b[1] else False if a[1] <= b[0] else None
    if op == ">=": return True if a[0] >= b[1] else False if a[1] < b[0] else None
    eq = True if a[0] == a[1] == b[0] == b[1] else False if (a[1] < b[0] or a[0] > b[1]) else None
    return eq if op == "==" else (None if eq is None else not eq)


class Symbol:
    def __init__(self, name, ty, mutable=True, loopvar=False, line=0):
        self.name, self.type, self.mutable, self.loopvar, self.line = name, ty, mutable, loopvar, line
        self.used, self.uid = False, name


def assigned_names(n, out):
    if isinstance(n, Block):
        for s in n.stmts: assigned_names(s, out)
    elif isinstance(n, (Assign, Read)): out.add(n.name)
    elif isinstance(n, If):
        assigned_names(n.then, out)
        if n.orelse: assigned_names(n.orelse, out)
    elif isinstance(n, (While, For)): assigned_names(n.body, out)


class Analyzer:
    def __init__(self):
        self.scopes, self.env, self.warnings, self.symbols = [{}], {}, [], []
        self.uid_counts = {}
        self.stats = dict(range_proven=0, range_guards=0, arith_total=0, arith_checked=0,
                          div_checks=0, dead_branches=0)

    # ---- helpers --------------------------------------------------------
    def err(self, line, msg): raise MiniLangError("semantic", msg, line)
    def warn(self, line, msg): self.warnings.append(f"line {line}: {msg}")

    def find(self, name):
        for sc in reversed(self.scopes):
            if name in sc: return sc[name]
        return None

    def lookup(self, name, line):
        s = self.find(name)
        if s is None: self.err(line, f"variable '{name}' is not declared")
        return s

    def declare(self, name, ty, line, mutable=True, loopvar=False):
        if self.find(name) is not None:
            self.err(line, f"'{name}' is already declared (shadowing is not allowed in MiniLang)")
        s = Symbol(name, ty, mutable, loopvar, line)
        c = self.uid_counts.get(name, 0)
        s.uid = name if c == 0 else f"{name}_{c}"
        self.uid_counts[name] = c + 1
        self.scopes[-1][name] = s
        self.symbols.append(s)
        return s

    def join(self, a, b, keys):
        out = {}
        for k in keys:
            out[k] = iv_hull(a[k], b[k]) if k.type.is_int else (a[k] if a[k] == b[k] else None)
        return out

    # ---- condition refinement (narrow ranges using a known condition) ----
    def refine(self, c, truth):
        if isinstance(c, Unary) and c.op == "!":
            return self.refine(c.operand, not truth)
        if not isinstance(c, Binary): return
        if c.op == "&&" and truth:
            self.refine(c.left, True); self.refine(c.right, True)
        elif c.op == "||" and not truth:
            self.refine(c.left, False); self.refine(c.right, False)
        elif c.op in NEG and c.left.ty.is_int:
            op = c.op if truth else NEG[c.op]
            self.narrow(c.left, op, c.right.iv)
            self.narrow(c.right, FLIP[op], c.left.iv)

    def narrow(self, node, op, iv):
        if not isinstance(node, Var) or not node.ty.is_int: return
        lo, hi = self.env[node.sym]
        if op == "<": hi = min(hi, iv[1] - 1)
        elif op == "<=": hi = min(hi, iv[1])
        elif op == ">": lo = max(lo, iv[0] + 1)
        elif op == ">=": lo = max(lo, iv[0])
        elif op == "==": lo, hi = max(lo, iv[0]), min(hi, iv[1])
        elif op == "!=" and iv[0] == iv[1]:
            if lo == iv[0]: lo += 1
            elif hi == iv[0]: hi -= 1
        if lo <= hi: self.env[node.sym] = (lo, hi)

    # ---- entry point -----------------------------------------------------
    def analyze(self, prog):
        self.block(prog.body, new_scope=False)
        for s in self.symbols:
            if not s.used and not s.loopvar:
                self.warn(s.line, f"variable '{s.name}' is declared but its value is never read")
        return self

    def block(self, b, new_scope=True):
        if new_scope: self.scopes.append({})
        for s in b.stmts: getattr(self, "s_" + type(s).__name__)(s)
        if new_scope:
            for sym in self.scopes.pop().values(): self.env.pop(sym, None)

    # ---- statements ------------------------------------------------------
    def check_assign(self, target, e, line, name):
        if target.kind != e.ty.kind:
            self.err(line, f"type mismatch: cannot assign {e.ty} to '{name}' of type {target} (no implicit conversion)")
        if target.is_bool: return False, e.bv
        guard = False
        if not target.is_plain:
            if iv_within(e.iv, target.interval):
                self.stats["range_proven"] += 1
            elif iv_meet(e.iv, target.interval) is None:
                self.err(line, f"value in range {iv_str(e.iv)} can never fit '{name}' declared as {target}")
            else:
                guard = True
                self.stats["range_guards"] += 1
                self.warn(line, f"'{name}' may receive {iv_str(e.iv)} but is declared {target}: runtime guard inserted")
        return guard, iv_meet(e.iv, target.interval)

    def s_Let(self, n):
        self.expr(n.init)
        n.guard, new = self.check_assign(n.type, n.init, n.line, n.name)
        n.sym = self.declare(n.name, n.type, n.line)
        self.env[n.sym] = new

    def s_Assign(self, n):
        sym = self.lookup(n.name, n.line)
        if not sym.mutable: self.err(n.line, f"cannot assign to loop variable '{n.name}'")
        self.expr(n.value)
        n.guard, new = self.check_assign(sym.type, n.value, n.line, n.name)
        n.sym, self.env[sym] = sym, new

    def s_Print(self, n): self.expr(n.value)

    def s_Read(self, n):
        sym = self.lookup(n.name, n.line)
        if not sym.type.is_int or not sym.mutable:
            self.err(n.line, f"'read' needs a mutable int variable, '{n.name}' is not")
        n.sym = sym
        self.env[sym] = sym.type.interval
        self.stats["range_guards"] += 1

    def s_Block(self, n): self.block(n)

    def s_If(self, n):
        if not self.expr(n.cond).is_bool: self.err(n.line, "if-condition must be bool")
        bv = n.static = n.cond.bv
        if bv is not None:
            self.stats["dead_branches"] += 1
            self.warn(n.line, f"condition is always {str(bv).lower()}: the {'else' if bv else 'then'}-branch is dead code and is removed")
        before = dict(self.env)
        self.refine(n.cond, True)
        self.block(n.then)
        env_t = dict(self.env)
        self.env = dict(before)
        self.refine(n.cond, False)
        if n.orelse: self.block(n.orelse)
        env_e = dict(self.env)
        if bv is True: self.env = env_t
        elif bv is False: self.env = env_e
        else: self.env = self.join(env_t, env_e, list(before))

    def widen(self, body):
        names = set(); assigned_names(body, names)
        for nm in names:
            s = self.find(nm)
            if s is not None: self.env[s] = s.type.interval if s.type.is_int else None

    def s_While(self, n):
        self.widen(n.body)                       # sound over-approximation of all iterations
        if not self.expr(n.cond).is_bool: self.err(n.line, "while-condition must be bool")
        if n.cond.bv is True: self.warn(n.line, "loop condition is always true: this loop never terminates")
        if n.cond.bv is False: self.warn(n.line, "loop condition is always false: the loop never runs")
        saved = dict(self.env)
        self.refine(n.cond, True)
        self.block(n.body)
        self.env = saved
        self.refine(n.cond, False)               # on exit the condition is false

    def s_For(self, n):
        for e in (n.lo, n.hi):
            if not self.expr(e).is_int: self.err(n.line, "for-loop bounds must be int")
        rng = (n.lo.iv[0], max(n.lo.iv[0], n.hi.iv[1] - 1))
        if n.hi.iv[1] <= n.lo.iv[0]: self.warn(n.line, "for-loop range is always empty")
        self.widen(n.body)
        self.scopes.append({})
        n.sym = self.declare(n.var, Type("int", *rng), n.line, mutable=False, loopvar=True)
        self.env[n.sym] = rng
        self.block(n.body)
        for s in self.scopes.pop().values(): self.env.pop(s, None)

    # ---- expressions -----------------------------------------------------
    def expr(self, n):
        n.iv = n.bv = None
        return getattr(self, "e_" + type(n).__name__)(n)

    def e_Num(self, n):
        if not INT_MIN <= n.value <= INT_MAX: self.err(n.line, f"literal {n.value} does not fit in 32 bits")
        n.ty, n.iv = INT, (n.value, n.value)
        return n.ty

    def e_BoolLit(self, n): n.ty, n.bv = BOOL, n.value; return n.ty

    def e_Var(self, n):
        n.sym = self.lookup(n.name, n.line)
        n.sym.used = True
        n.ty = n.sym.type
        v = self.env[n.sym]
        if n.ty.is_int: n.iv = v
        else: n.bv = v
        return n.ty

    def e_Unary(self, n):
        t = self.expr(n.operand)
        if n.op == "!":
            if not t.is_bool: self.err(n.line, "operator '!' needs a bool operand")
            n.ty = BOOL
            n.bv = None if n.operand.bv is None else not n.operand.bv
            return n.ty
        if not t.is_int: self.err(n.line, "unary '-' needs an int operand")
        lo, hi = n.operand.iv
        return self.finish_arith(n, (-hi, -lo))

    def finish_arith(self, n, raw):
        n.flags = set()
        self.stats["arith_total"] += 1
        if not iv_within(raw, INT_RANGE):
            clipped = iv_meet(raw, INT_RANGE)
            if clipped is None: self.err(n.line, "this arithmetic always overflows 32-bit int")
            self.warn(n.line, f"result may reach {iv_str(raw)}: overflow check inserted")
            n.flags.add("ovf"); self.stats["arith_checked"] += 1
            raw = clipped
        n.ty, n.iv = INT, raw
        return INT

    def e_Binary(self, n):
        op = n.op
        lt = self.expr(n.left)
        if op in LOGIC:                      # short-circuit: right side sees refined ranges
            saved = dict(self.env)
            self.refine(n.left, op == "&&")
            rt = self.expr(n.right)
            self.env = saved
        else:
            rt = self.expr(n.right)
        l, r = n.left, n.right
        if op in ARITH:
            if not (lt.is_int and rt.is_int):
                self.err(n.line, f"operator '{op}' needs int operands, got {lt} and {rt}")
            a, b = l.iv, r.iv
            n.flags = set()
            if op == "+": raw = iv_add(a, b)
            elif op == "-": raw = iv_sub(a, b)
            elif op == "*": raw = iv_mul(a, b)
            else:
                if b == (0, 0): self.err(n.line, "division by zero: the divisor is always 0")
                if b[0] <= 0 <= b[1]:
                    n.flags.add("zero"); self.stats["div_checks"] += 1
                    self.warn(n.line, f"divisor may be 0 (range {iv_str(b)}): runtime check inserted")
                raw = iv_div(a, b) if op == "/" else iv_mod(a, b)
            flags = n.flags
            self.finish_arith(n, raw)
            n.flags |= flags
            return INT
        n.ty = BOOL
        if op in CMP or (op in EQ and lt.is_int):
            if not (lt.is_int and rt.is_int):
                self.err(n.line, f"cannot compare {lt} with {rt}")
            n.bv = cmp_iv(op, l.iv, r.iv)
        elif op in EQ:
            if not (lt.is_bool and rt.is_bool): self.err(n.line, f"cannot compare {lt} with {rt}")
            if l.bv is not None and r.bv is not None: n.bv = (l.bv == r.bv) == (op == "==")
        else:  # && ||
            if not (lt.is_bool and rt.is_bool): self.err(n.line, f"operator '{op}' needs bool operands")
            if op == "&&":
                n.bv = False if (l.bv is False or r.bv is False) else True if (l.bv and r.bv) else None
            else:
                n.bv = True if (l.bv is True or r.bv is True) else False if (l.bv is False and r.bv is False) else None
        return BOOL
