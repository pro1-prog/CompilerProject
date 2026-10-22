// The compiler warns about loops that can never terminate.
let i: int[0..10] = 0;
while (true) {
    i = i + 1;
}
