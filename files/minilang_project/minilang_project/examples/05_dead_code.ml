// Range analysis folds constants and removes provably dead branches.
let x: int[0..9] = 7;
let y: int = x * 2 + 1;        // folded: y is exactly 15
if (y > 100) {                 // always false -> dead
    print 999;
} else {
    print y;
}
