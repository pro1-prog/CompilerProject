#!/usr/bin/env python3
"""MiniLang compiler driver.

usage: python minilang.py program.ml [--tokens] [--ast] [--symbols] [--tac] [--no-opt]
                                     [--no-run] [--input "5 7 9"]
"""
import argparse, sys
from common import MiniLangError, iv_str
from lexer import tokenize
from syntax import Parser
from ast_nodes import dump
from semantic import Analyzer
from codegen import CodeGen, optimize
from vm import VM

BANNER = "MiniLang compiler  -  range-safe language with compile-time interval analysis"


def compile_source(src):
    tokens = tokenize(src)
    tree = Parser(tokens).parse_program()
    an = Analyzer().analyze(tree)
    cg = CodeGen()
    raw = cg.generate(tree)
    return tokens, tree, an, cg, raw, optimize(raw)


def safety_report(an, cg, raw, opt):
    s = an.stats
    rows = [
        ("Range-typed assignments proven safe (no runtime cost)", s["range_proven"]),
        ("Runtime range guards inserted", s["range_guards"]),
        ("Arithmetic ops proven overflow-free", s["arith_total"] - s["arith_checked"]),
        ("Overflow checks inserted", s["arith_checked"]),
        ("Division/modulo zero-checks inserted", s["div_checks"]),
        ("Dead branches removed", s["dead_branches"]),
        ("Expressions folded to constants by range analysis", cg.folded),
        ("TAC instructions (before -> after optimisation)", f"{len(raw)} -> {len(opt)}"),
    ]
    out = ["", "=== Safety & optimisation report ==="]
    out += [f"  {k:<56}{v}" for k, v in rows]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=BANNER)
    ap.add_argument("file")
    ap.add_argument("--tokens", action="store_true", help="show token stream")
    ap.add_argument("--ast", action="store_true", help="show annotated AST")
    ap.add_argument("--symbols", action="store_true", help="show symbol table")
    ap.add_argument("--tac", action="store_true", help="show three-address code")
    ap.add_argument("--no-opt", action="store_true", help="run unoptimised TAC")
    ap.add_argument("--no-run", action="store_true", help="compile only")
    ap.add_argument("--input", default="", help="space separated values for 'read'")
    a = ap.parse_args()

    src = open(a.file, encoding="utf-8").read()
    try:
        tokens, tree, an, cg, raw, opt = compile_source(src)
    except MiniLangError as e:
        print(e); sys.exit(1)

    print(BANNER)
    if a.tokens:
        print("\n--- Tokens ---"); print("\n".join(map(str, tokens)))
    if a.ast:
        print("\n--- Annotated AST ---"); print(dump(tree), end="")
    if a.symbols:
        print("\n--- Symbol table ---")
        print(f"  {'name':<12}{'type':<14}{'kind':<10}line")
        for s in an.symbols:
            print(f"  {s.name:<12}{str(s.type):<14}{'loop var' if s.loopvar else 'variable':<10}{s.line}")
    if a.tac:
        print("\n--- Three-address code" + (" (unoptimised)" if a.no_opt else " (optimised)") + " ---")
        print("\n".join(map(str, raw if a.no_opt else opt)))
    for w in an.warnings:
        print("warning:", w)
    print(safety_report(an, cg, raw, opt))
    if a.no_run: return
    print("\n--- Program output ---")
    vm = VM(raw if a.no_opt else opt, a.input.split())
    try:
        vm.run()
    except MiniLangError as e:
        print("\n".join(vm.output)); print(e); sys.exit(2)
    print("\n".join(vm.output))
    print(f"\n[{vm.steps} VM steps, {vm.guards_run} runtime checks executed]")


if __name__ == "__main__":
    main()
