// Factorial with automatic overflow detection (C would silently wrap around).
let n: int[1..20] = 1;
read n;
let f: int = 1;
for i in 1..n + 1 {
    f = f * i;           // overflow check inserted by compiler
}
print f;
