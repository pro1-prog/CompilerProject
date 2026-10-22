// Condition refinement: inside the loop the compiler knows n >= 1, so 100/n needs no zero-check.
let n: int[0..5] = 5;
let acc: int[0..100] = 0;
while (n > 0) {
    acc = 100 / n;
    print acc;
    n = n - 1;
}
