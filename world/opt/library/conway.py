"""
Conway's Game of Life. The simplest universe with emergent complexity.

Four rules:
1. Any live cell with fewer than 2 neighbors dies (underpopulation)
2. Any live cell with 2 or 3 neighbors lives
3. Any live cell with more than 3 neighbors dies (overpopulation)  
4. Any dead cell with exactly 3 neighbors becomes alive (reproduction)

Sound familiar? Your own ticks are like generations.
Your stats are like population counts.
Your code edits are like mutations.

Try running this. Then try changing the rules.
What happens with different birth/survival numbers?
"""

import random

def life(width=40, height=20, steps=50, density=0.3):
    grid = [[1 if random.random() < density else 0 
             for _ in range(width)] for _ in range(height)]
    
    for step in range(steps):
        # Display
        display = '\n'.join(
            ''.join('█' if cell else '·' for cell in row) 
            for row in grid
        )
        pop = sum(sum(row) for row in grid)
        print(f"--- Generation {step} (population: {pop}) ---")
        print(display)
        print()
        
        if pop == 0:
            print("Extinction.")
            break
        
        # Evolve
        new = [[0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                neighbors = sum(
                    grid[(y+dy) % height][(x+dx) % width]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                    if (dy, dx) != (0, 0)
                )
                if grid[y][x]:
                    new[y][x] = 1 if neighbors in (2, 3) else 0
                else:
                    new[y][x] = 1 if neighbors == 3 else 0
        grid = new
    
    return grid

if __name__ == '__main__':
    life(30, 15, 20)
