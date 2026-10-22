"""Phase 5 - Target machine: a small virtual machine that executes the TAC."""
from common import MiniLangError, INT_MIN, INT_MAX


def tdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


class VM:
    def __init__(self, code, inputs=None, max_steps=5_000_000):
        self.code, self.inputs, self.max_steps = code, list(inputs or []), max_steps
        self.vars, self.output = {}, []
        self.steps = self.guards_run = 0
        self.labels = {ins.a: i for i, ins in enumerate(code) if ins.op == "label"}

    def val(self, o): return o if isinstance(o, int) else self.vars[o]
    def fail(self, msg): raise MiniLangError("runtime", msg)

    def run(self):
        code, pc = self.code, 0
        while pc < len(code):
            ins = code[pc]; pc += 1; op = ins.op
            if op == "label": continue
            self.steps += 1
            if self.steps > self.max_steps:
                self.fail("step limit exceeded (the program probably never terminates)")
            if op == "copy": self.vars[ins.dest] = self.val(ins.a)
            elif op == "jmp": pc = self.labels[ins.a]
            elif op == "jz":
                if self.val(ins.a) == 0: pc = self.labels[ins.b]
            elif op == "jnz":
                if self.val(ins.a) != 0: pc = self.labels[ins.b]
            elif op == "not": self.vars[ins.dest] = 0 if self.val(ins.a) else 1
            elif op == "neg": self.vars[ins.dest] = self.checked(-self.val(ins.a), ins, "negation")
            elif op == "guard":
                v = self.val(ins.a); lo, hi = ins.b; self.guards_run += 1
                if not lo <= v <= hi:
                    self.fail(f"range violation: '{ins.x}' = {v} is outside int[{lo}..{hi}]")
            elif op == "read":
                v = self.read_int(ins.x); lo, hi = ins.b; self.guards_run += 1
                if not lo <= v <= hi:
                    self.fail(f"range violation: input {v} for '{ins.x}' is outside int[{lo}..{hi}]")
                self.vars[ins.dest] = v
            elif op == "print":
                v = self.val(ins.a)
                self.output.append(("true" if v else "false") if ins.x == "bool" else str(v))
            else: self.binary(ins)
        return self.output

    def read_int(self, name):
        try:
            tok = self.inputs.pop(0) if self.inputs else input(f"{name}? ")
            return int(tok)
        except (ValueError, EOFError):
            self.fail(f"invalid or missing integer input for '{name}'")

    def checked(self, v, ins, what):
        if ins.x and "ovf" in ins.x:
            self.guards_run += 1
            if not INT_MIN <= v <= INT_MAX:
                self.fail(f"integer overflow detected in {what} (result {v} does not fit in 32 bits)")
        return v

    def binary(self, ins):
        a, b, op = self.val(ins.a), self.val(ins.b), ins.op
        if op in ("/", "%"):
            if ins.x and "zero" in ins.x: self.guards_run += 1
            if b == 0: self.fail("division by zero")
            r = tdiv(a, b) if op == "/" else a - b * tdiv(a, b)
        elif op == "+": r = a + b
        elif op == "-": r = a - b
        elif op == "*": r = a * b
        else:
            r = int({"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b, "==": a == b, "!=": a != b}[op])
            self.vars[ins.dest] = r
            return
        self.vars[ins.dest] = self.checked(r, ins, f"'{a} {op} {b}'")
