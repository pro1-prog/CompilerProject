# MiniLang - a range-safe teaching language

Python 3.8+ , no external libraries.

    python minilang.py examples/01_safe_marks.ml
    python minilang.py examples/04_factorial.ml --input 12 --tac
    python minilang.py examples/06_grades.ml --input "90 80 70 60 50" --ast --symbols
    python -m unittest test_minilang

Flags: --tokens --ast --symbols --tac --no-opt --no-run --input "v1 v2 ..."

Files: common.py (types, intervals) | lexer.py | ast_nodes.py | syntax.py (parser)
       semantic.py (types + range analysis) | codegen.py (TAC + optimiser) | vm.py | minilang.py (driver)
