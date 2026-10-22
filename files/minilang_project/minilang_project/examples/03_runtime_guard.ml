// Unknown input -> compiler inserts a runtime guard instead of trusting the user.
let age: int[0..120] = 0;
read age;
let years_left: int[0..120] = 100 - age;   // range [-20..100]: guard inserted for the negative side
print years_left;
