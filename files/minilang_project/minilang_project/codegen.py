"""Phase 4 - Intermediate code generation (three-address code) + optimiser."""
import copy
from collections import Counter
from ast_nodes import *

ARITH_OPS = {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=", "neg", "not"}


class Instr:
    def __init__(self, op, dest=None, a=None, b=None, x=None):
        self.op, self.dest, self.a, self.b, self.x = op, dest, a, b, x

    def __str__(self):
        o = self.op
        flag = f"   ; checks: {','.join(sorted(self.x))}" if o in ARITH_OPS and self.x else ""
        if o == "label": return f"{self.a}:"
        if o == "jmp":   return f"    goto {self.a}"
        if o == "jz":    return f"    ifFalse {self.a} goto {self.b}"
        if o == "jnz":   return f"    if {self.a} goto {self.b}"
        if o == "copy":  return f"    {self.dest} = {self.a}"
        if o == "neg":   return f"    {self.dest} = -{self.a}{flag}"
        if o == "not":   return f"    {self.dest} = !{self.a}"
        if o == "guard": return f"    guard {self.a} in [{self.b[0]}..{self.b[1]}]"
        if o == "read":  return f"    read {self.dest}  ; must be in [{self.b[0]}..{self.b[1]}]"
        if o == "print": return f"    print {self.a}"
        return f"    {self.dest} = {self.a} {o} {self.b}{flag}"


class CodeGen:
    def __init__(self):
        self.code, self.tmp, self.lab, self.folded = [], 0, 0, 0

    def t(self): self.tmp += 1; return f"$t{self.tmp}"
    def l(self): self.lab += 1; return f"L{self.lab}"
    def emit(self, *a, **k): self.code.append(Instr(*a, **k))

    def generate(self, prog):
        self.block(prog.body)
        return self.code

    def block(self, b):
        for s in b.stmts: getattr(self, "s_" + type(s).__name__)(s)

    # ---- statements ----
    def assign(self, n, value):
        self.emit("copy", dest=n.sym.uid, a=self.gx(value))
        if n.guard: self.emit("guard", a=n.sym.uid, b=n.sym.type.interval, x=n.name)

    def s_Let(self, n): self.assign(n, n.init)
    def s_Assign(self, n): self.assign(n, n.value)
    def s_Block(self, n): self.block(n)
    def s_Print(self, n): self.emit("print", a=self.gx(n.value), x="bool" if n.value.ty.is_bool else "int")
    def s_Read(self, n): self.emit("read", dest=n.sym.uid, b=n.sym.type.interval, x=n.name)

    def s_If(self, n):
        if n.static is True: return self.block(n.then)
        if n.static is False: return self.block(n.orelse) if n.orelse else None
        c, Lelse = self.gx(n.cond), self.l()
        self.emit("jz", a=c, b=Lelse)
        self.block(n.then)
        if n.orelse:
            Lend = self.l()
            self.emit("jmp", a=Lend); self.emit("label", a=Lelse)
            self.block(n.orelse); self.emit("label", a=Lend)
        else:
            self.emit("label", a=Lelse)

    def s_While(self, n):
        if n.cond.bv is False: return
        Ls, Le = self.l(), self.l()
        self.emit("label", a=Ls)
        self.emit("jz", a=self.gx(n.cond), b=Le)
        self.block(n.body)
        self.emit("jmp", a=Ls); self.emit("label", a=Le)

    def s_For(self, n):
        v, hv = n.sym.uid, self.t()
        lo, hi = self.gx(n.lo), self.gx(n.hi)       # bounds are evaluated ONCE
        self.emit("copy", dest=v, a=lo); self.emit("copy", dest=hv, a=hi)
        Ls, Le, c = self.l(), self.l(), self.t()
        self.emit("label", a=Ls)
        self.emit("<", dest=c, a=v, b=hv); self.emit("jz", a=c, b=Le)
        self.block(n.body)
        self.emit("+", dest=v, a=v, b=1, x=set())
        self.emit("jmp", a=Ls); self.emit("label", a=Le)

    # ---- expressions: returns an operand (name or immediate int) ----
    def gx(self, n):
        if n.ty.is_int and n.iv[0] == n.iv[1]:           # range analysis proves a constant
            if not isinstance(n, Num): self.folded += 1
            return n.iv[0]
        if n.ty.is_bool and n.bv is not None:
            if not isinstance(n, BoolLit): self.folded += 1
            return int(n.bv)
        if isinstance(n, BoolLit): return int(n.value)
        if isinstance(n, Var): return n.sym.uid
        if isinstance(n, Unary):
            a, t = self.gx(n.operand), self.t()
            self.emit("neg" if n.op == "-" else "not", dest=t, a=a, x=getattr(n, "flags", None))
            return t
        if n.op in ("&&", "||"):                          # short-circuit evaluation
            res, Lend = self.t(), self.l()
            self.emit("copy", dest=res, a=self.gx(n.left))
            self.emit("jz" if n.op == "&&" else "jnz", a=res, b=Lend)
            self.emit("copy", dest=res, a=self.gx(n.right))
            self.emit("label", a=Lend)
            return res
        a, b, t = self.gx(n.left), self.gx(n.right), self.t()
        self.emit(n.op, dest=t, a=a, b=b, x=getattr(n, "flags", None))
        return t


def optimize(code):
    """Peephole optimiser: temp-copy fusion, constant jumps, redundant jumps/labels."""
    code = copy.deepcopy(code)
    for _ in range(3):
        uses = Counter(o for i in code for o in (i.a, i.b) if isinstance(o, str))
        out, i = [], 0
        while i < len(code):
            ins = code[i]
            nxt = code[i + 1] if i + 1 < len(code) else None
            if (ins.op in ARITH_OPS and isinstance(ins.dest, str) and ins.dest.startswith("$t")
                    and nxt and nxt.op == "copy" and nxt.a == ins.dest and uses[ins.dest] == 1):
                ins.dest = nxt.dest; out.append(ins); i += 2; continue
            if ins.op == "jz" and isinstance(ins.a, int):          # constant condition
                if ins.a == 0: out.append(Instr("jmp", a=ins.b))
                i += 1; continue
            if ins.op == "jmp" and nxt and nxt.op == "label" and nxt.a == ins.a:
                i += 1; continue
            out.append(ins); i += 1
        refs = {i.a for i in out if i.op == "jmp"} | {i.b for i in out if i.op in ("jz", "jnz")}
        code = [i for i in out if not (i.op == "label" and i.a not in refs)]
    return code
