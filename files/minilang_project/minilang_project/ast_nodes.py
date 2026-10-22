"""Abstract Syntax Tree node definitions."""
from dataclasses import dataclass, fields
from common import Type, iv_str


@dataclass(eq=False)
class Node: line: int
@dataclass(eq=False)
class Num(Node): value: int
@dataclass(eq=False)
class BoolLit(Node): value: bool
@dataclass(eq=False)
class Var(Node): name: str
@dataclass(eq=False)
class Unary(Node): op: str; operand: Node
@dataclass(eq=False)
class Binary(Node): op: str; left: Node; right: Node
@dataclass(eq=False)
class Let(Node): name: str; type: Type; init: Node
@dataclass(eq=False)
class Assign(Node): name: str; value: Node
@dataclass(eq=False)
class Print(Node): value: Node
@dataclass(eq=False)
class Read(Node): name: str
@dataclass(eq=False)
class Block(Node): stmts: list
@dataclass(eq=False)
class If(Node): cond: Node; then: Block; orelse: object
@dataclass(eq=False)
class While(Node): cond: Node; body: Block
@dataclass(eq=False)
class For(Node): var: str; lo: Node; hi: Node; body: Block
@dataclass(eq=False)
class Program(Node): body: Block


def dump(n, ind=0):
    """Pretty-print the AST (with inferred ranges once semantic analysis ran)."""
    pad = "  " * ind
    if isinstance(n, list):
        return "".join(dump(x, ind) for x in n)
    simple, kids = [], []
    for f in fields(n):
        if f.name == "line":
            continue
        v = getattr(n, f.name)
        if isinstance(v, (Node, list)):
            kids.append(v)
        elif v is not None:
            simple.append(f"{f.name}={v}")
    note = ""
    iv, bv = getattr(n, "iv", None), getattr(n, "bv", None)
    if iv is not None:
        note = f"   <range {iv_str(iv)}>"
    elif bv is not None:
        note = f"   <always {bv}>"
    out = f"{pad}{type(n).__name__}({', '.join(simple)}){note}\n"
    for k in kids:
        out += dump(k, ind + 1)
    return out
