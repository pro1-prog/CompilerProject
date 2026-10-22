// Range types: the compiler PROVES every assignment is in range.
let marks: int[0..100] = 85;
let bonus: int[0..10] = 5;
let total: int[0..110] = marks + bonus;   // range of marks+bonus is [0..110] -> proven safe
print total;

let passed: bool = total >= 40;
print passed;
