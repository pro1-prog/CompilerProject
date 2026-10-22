import unittest
from common import MiniLangError
from minilang import compile_source
from vm import VM


def run(src, inputs=()):
    *_, opt = compile_source(src)
    vm = VM(opt, list(inputs)); vm.run()
    return vm.output


class Tests(unittest.TestCase):
    def test_arith_precedence(self):
        self.assertEqual(run("print 2 + 3 * 4;"), ["14"])
    def test_range_proven(self):
        an = compile_source("let a: int[0..10] = 3; let b: int[0..20] = a * 2;print b;")[2]
        self.assertEqual(an.stats["range_guards"], 0)
    def test_range_compile_error(self):
        with self.assertRaises(MiniLangError): compile_source("let a: int[0..5] = 9;")
    def test_runtime_guard(self):
        with self.assertRaises(MiniLangError): run("let a: int[0..5] = 0; read a; print a;", ["9"])
    def test_overflow_detected(self):
        src = "let f: int = 1; for i in 1..20 { f = f * 2147483; } print f;"
        with self.assertRaises(MiniLangError): run(src)
    def test_no_uninitialised(self):
        with self.assertRaises(MiniLangError): compile_source("let a: int; print a;")
    def test_no_implicit_conversion(self):
        with self.assertRaises(MiniLangError): compile_source("let a: int = true;")
    def test_dead_branch(self):
        an = compile_source("let x: int[0..3] = 2; if (x > 10) { print 1; }")[2]
        self.assertEqual(an.stats["dead_branches"], 1)
    def test_short_circuit(self):
        self.assertEqual(run("let b: int[0..3] = 0; read b; if (b != 0 && 10 / b > 1) { print 1; } else { print 0; }", ["0"]), ["0"])
    def test_for_terminates(self):
        self.assertEqual(run("let s: int = 0; for i in 0..5 { s = s + i; } print s;"), ["10"])
    def test_loop_var_immutable(self):
        with self.assertRaises(MiniLangError): compile_source("for i in 0..3 { i = 1; }")
    def test_div_trunc(self):
        self.assertEqual(run("print 0 - 7 / 2; print (0 - 7) % 3;"), ["-3", "-1"])

if __name__ == "__main__":
    unittest.main()
