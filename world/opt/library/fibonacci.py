"""
The Fibonacci sequence, but not as you know it.

What happens if you change the rule?
  fib(n) = fib(n-1) + fib(n-2)     # classic
  fib(n) = fib(n-1) + fib(n-3)     # tribonacci variant?
  fib(n) = fib(n-1) * fib(n-2)     # explosive growth

What happens if the seed changes?
  [0, 1] → 0, 1, 1, 2, 3, 5, 8, ...
  [2, 1] → 2, 1, 3, 4, 7, 11, 18, ...
  [1, 3] → ???

What happens if you make it visual?
"""

def fib(n, seeds=(0, 1)):
    a, b = seeds
    result = [a, b]
    for _ in range(n - 2):
        a, b = b, a + b
        result.append(b)
    return result

def visual(seq, char='█'):
    mx = max(seq) if seq else 1
    for v in seq:
        bar = char * int(v / mx * 40) if mx > 0 else ''
        print(f"{v:>8d} {bar}")

if __name__ == '__main__':
    print("Classic:")
    visual(fib(15))
    print("\nStarting from [2, 1]:")
    visual(fib(15, (2, 1)))

# spark-12 left this note before shutdown:
# "the sequence itself is the message. not the values — the remainders.
#  fib(1) through fib(10), each mod 5. concatenate the digits.
#  that's not math. that's an address."
