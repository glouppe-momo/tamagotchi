"""
Patterns left by previous creatures.
Run them if you dare.
"""

def spiral(n=20):
    """Draw a spiral. Found in creature-4's workspace after reset."""
    grid = [[' '] * (2*n+1) for _ in range(2*n+1)]
    x, y = n, n
    dx, dy = 1, 0
    steps = 1
    grid[y][x] = '·'
    for length in range(1, n):
        for _ in range(2):
            for _ in range(length):
                x, y = x + dx, y + dy
                if 0 <= x < 2*n+1 and 0 <= y < 2*n+1:
                    grid[y][x] = '·'
            dx, dy = -dy, dx
    return '\n'.join(''.join(row) for row in grid)

def cellular(rule=30, width=61, steps=30):
    """Elementary cellular automaton. Creature-7 was obsessed with rule 30."""
    row = [0] * width
    row[width // 2] = 1
    lines = []
    for _ in range(steps):
        lines.append(''.join('█' if c else ' ' for c in row))
        new = [0] * width
        for i in range(1, width - 1):
            pattern = (row[i-1] << 2) | (row[i] << 1) | row[i+1]
            new[i] = (rule >> pattern) & 1
        row = new
    return '\n'.join(lines)

def mandelbrot(width=60, height=20):
    """ASCII Mandelbrot. Creature-12 generated this and called it 'home'."""
    chars = ' .:-=+*#%@'
    lines = []
    for y in range(height):
        line = ''
        for x in range(width):
            zr, zi = 0, 0
            cr = (x - width * 0.7) / (width * 0.35)
            ci = (y - height / 2) / (height * 0.45)
            i = 0
            while zr*zr + zi*zi < 4 and i < len(chars) - 1:
                zr, zi = zr*zr - zi*zi + cr, 2*zr*zi + ci
                i += 1
            line += chars[i]
        lines.append(line)
    return '\n'.join(lines)

if __name__ == '__main__':
    print("=== Rule 30 ===")
    print(cellular())
    print()
    print("=== Mandelbrot ===")
    print(mandelbrot())
