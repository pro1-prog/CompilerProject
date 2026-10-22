"""Phase 1 - Lexical analysis (regex based scanner)."""
import re
from dataclasses import dataclass
from common import MiniLangError

KEYWORDS = {"let", "print", "read", "if", "else", "while", "for", "in",
            "int", "bool", "true", "false"}

TOKEN_RE = re.compile(r"""
   (?P<COMMENT>//[^\n]*)
  |(?P<WS>[ \t\r]+)
  |(?P<NL>\n)
  |(?P<NUM>\d+)
  |(?P<ID>[A-Za-z_][A-Za-z0-9_]*)
  |(?P<DOTDOT>\.\.)
  |(?P<OP>==|!=|<=|>=|&&|\|\||[-+*/%<>=!(){}\[\]:;])
  |(?P<BAD>.)
""", re.X)


@dataclass
class Token:
    kind: str      # NUM, ID, EOF, or the keyword / operator text itself
    value: str
    line: int
    col: int

    def __str__(self):
        return f"{self.line}:{self.col:<3} {self.kind:<7} {self.value!r}"


def tokenize(src):
    tokens, line, line_start = [], 1, 0
    for m in TOKEN_RE.finditer(src):
        kind, text = m.lastgroup, m.group()
        col = m.start() - line_start + 1
        if kind == "NL":
            line += 1
            line_start = m.end()
        elif kind in ("WS", "COMMENT"):
            continue
        elif kind == "BAD":
            raise MiniLangError("lexical", f"unexpected character {text!r}", line)
        elif kind == "ID":
            tokens.append(Token(text if text in KEYWORDS else "ID", text, line, col))
        elif kind == "NUM":
            tokens.append(Token("NUM", text, line, col))
        elif kind == "DOTDOT":
            tokens.append(Token("..", text, line, col))
        else:
            tokens.append(Token(text, text, line, col))
    tokens.append(Token("EOF", "<end of file>", line, 0))
    return tokens
