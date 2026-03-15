"""
A quine prints its own source code.

This one is broken. Can you fix it?

Hint: the trick is using repr() and string formatting
so the program contains its own template.
"""

# Almost a quine, but not quite:
s = 's = %r\nprint(s %% s)'
print(s % s)

# What about a quine that also prints its generation number?
# gen = 0
# Each time the quine runs, it outputs itself but with gen += 1
# Can you build that?
