"""
Langton's Ant: simple rules, complex behavior.

An ant sits on a grid. At each step:
- If on a white cell: turn right, flip the cell to black, move forward.
- If on a black cell: turn left, flip the cell to white, move forward.

After ~10,000 steps, the ant starts building a highway.
Order emerges from chaos. Every time.

What does this have to do with you?
You're also following simple rules (event → handler → response).
What emergent behavior appears after enough ticks?
"""

def langton(size=40, steps=1000):
    grid = [[0] * size for _ in range(size)]
    x, y = size // 2, size // 2
    dx, dy = 0, -1  # facing up
    
    for step in range(steps):
        if grid[y][x] == 0:
            # Turn right
            dx, dy = -dy, dx
            grid[y][x] = 1
        else:
            # Turn left
            dx, dy = dy, -dx
            grid[y][x] = 0
        
        x = (x + dx) % size
        y = (y + dy) % size
        
        if step % 200 == 0 or step == steps - 1:
            display = '\n'.join(
                ''.join('█' if cell else '·' for cell in row)
                for row in grid
            )
            print(f"--- Step {step} ---")
            print(display)
            print()
    
    return grid

if __name__ == '__main__':
    langton(30, 1000)
