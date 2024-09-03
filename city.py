class City:

    def __init__(self, n, m, points=[1, 2, 3, 4]):
        """
        Initialize the City object.

        Args:
            n (int): Number of rows in the grid.
            m (int): Number of columns in the grid.
        """
        self.n = n
        self.m = m
        self.points = points

        self.nb_colors = 4
        self.colors = ["Blue", "Red", "Green", "Yellow"]
        self.colors_short = [color[0:1] for color in self.colors]

    def neighbors(self, row, col):
        """
        Create a list of neighboring cells for a given cell, filtering out-of-bounds neighbors.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.

        Returns:
            list of tuples: A list of (row, col) tuples representing valid neighboring cells.
        """
        neighbors = [
            (row - 1, col),  # Up
            (row + 1, col),  # Down
            (row, col - 1),  # Left
            (row, col + 1)   # Right
        ]

        # Filter neighbors to keep only those within bounds
        return [(r, c) for r, c in neighbors if 0 <= r < self.n and 0 <= c < self.m]
