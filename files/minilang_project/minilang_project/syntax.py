"""Phase 2 - Syntax analysis: recursive-descent (LL(1)) parser -> AST."""
from common import MiniLangError, Type, BOOL, INT_MIN, INT_MAX
from lexer import tokenize
from ast_nodes import *


class Parser:
    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    @property
    def cur(self): return self.t[self.i]

    def match(self, *kinds):
        if self.cur.kind in kinds:
            tok = self.cur
            self.i += 1
            return tok
        return None

    def expect(self, kind):
        tok = self.cur
        if tok.kind != kind:
            raise MiniLangError("syntax", f"expected '{kind}' but found '{tok.value}'", tok.line)
        self.i += 1
        return tok

    # program -> stmt* EOF
    def parse_program(self):
        stmts = []
        while self.cur.kind != "EOF":
            stmts.append(self.stmt())
        return Program(1, Block(1, stmts))

    def block(self):
        line = self.expect("{").line
        stmts = []
        while self.cur.kind not in ("}", "EOF"):
            stmts.append(self.stmt())
        self.expect("}")
        return Block(line, stmts)

    def stmt(self):
        k, line = self.cur.kind, self.cur.line
        if k == "let":
            self.i += 1
            name = self.expect("ID").value
            self.expect(":")
            ty = self.type()
            self.expect("=")        # initialisation is MANDATORY
            init = self.expr()
            self.expect(";")
            return Let(line, name, ty, init)
        if k == "print":
            self.i += 1
            e = self.expr(); self.expect(";")
            return Print(line, e)
        if k == "read":
            self.i += 1
            name = self.expect("ID").value; self.expect(";")
            return Read(line, name)
        if k == "if":
            return self.if_stmt()
        if k == "while":
            self.i += 1
            self.expect("("); c = self.expr(); self.expect(")")
            return While(line, c, self.block())
        if k == "for":
            self.i += 1
            v = self.expect("ID").value
            self.expect("in")
            lo = self.expr(); self.expect(".."); hi = self.expr()
            return For(line, v, lo, hi, self.block())
        if k == "{":
            return self.block()
        if k == "ID":
            name = self.cur.value
            self.i += 1
            self.expect("=")
            e = self.expr(); self.expect(";")
            return Assign(line, name, e)
        raise MiniLangError("syntax", f"unexpected token '{self.cur.value}'", line)

    def if_stmt(self):
        line = self.expect("if").line
        self.expect("("); c = self.expr(); self.expect(")")
        then = self.block()
        orelse = None
        if self.match("else"):
            if self.cur.kind == "if":          # else-if chain
                nested = self.if_stmt()
                orelse = Block(nested.line, [nested])
            else:
                orelse = self.block()
        return If(line, c, then, orelse)

    def sint(self):
        neg = bool(self.match("-"))
        v = int(self.expect("NUM").value)
        return -v if neg else v

    def type(self):
        tok = self.cur
        if self.match("bool"):
            return BOOL
        self.expect("int")
        if self.match("["):
            lo = self.sint(); self.expect(".."); hi = self.sint(); self.expect("]")
            if lo > hi:
                raise MiniLangError("syntax", f"empty range [{lo}..{hi}]: lower bound exceeds upper bound", tok.line)
            if lo < INT_MIN or hi > INT_MAX:
                raise MiniLangError("syntax", "range bounds must fit in 32 bits", tok.line)
            return Type("int", lo, hi)
        return Type("int", INT_MIN, INT_MAX)

    # ---- expressions (precedence climbing, lowest -> highest) -----------
    def _binary(self, sub, ops):
        left = sub()
        while self.cur.kind in ops:
            op = self.cur
            self.i += 1
            left = Binary(op.line, op.kind, left, sub())
        return left

    def expr(self):   return self._binary(self.and_, ("||",))
    def and_(self):   return self._binary(self.eq, ("&&",))
    def eq(self):     return self._binary(self.rel, ("==", "!="))
    def rel(self):    return self._binary(self.add, ("<", ">", "<=", ">="))
    def add(self):    return self._binary(self.mul, ("+", "-"))
    def mul(self):    return self._binary(self.unary, ("*", "/", "%"))

    def unary(self):
        if self.cur.kind in ("-", "!"):
            op = self.cur
            self.i += 1
            return Unary(op.line, op.kind, self.unary())
        return self.primary()

    def primary(self):
        tok = self.cur
        if self.match("NUM"):  return Num(tok.line, int(tok.value))
        if self.match("true"): return BoolLit(tok.line, True)
        if self.match("false"): return BoolLit(tok.line, False)
        if self.match("ID"):   return Var(tok.line, tok.value)
        if self.match("("):
            e = self.expr(); self.expect(")")
            return e
        raise MiniLangError("syntax", f"expected an expression but found '{tok.value}'", tok.line)


def parse(src):
    return Parser(tokenize(src)).parse_program()
