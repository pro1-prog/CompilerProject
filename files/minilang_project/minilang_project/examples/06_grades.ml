// Grade calculator: loops, else-if, nested ranges, refinement inside branches.
let sum: int[0..500] = 0;
for i in 0..5 {
    let m: int[0..100] = 0;
    read m;
    sum = sum + m;                 // sum may exceed 500 in theory -> guard, but it is cheap
}
let avg: int[0..100] = sum / 5;
print avg;
if (avg >= 90) { print 1; }
else if (avg >= 75) { print 2; }
else if (avg >= 40) { print 3; }
else { print 0; }
