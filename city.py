class City:
    """
    Class that models the properties of a city, including grid size and allowed tower colors.
    """

    def __init__(self, rows: int, cols: int, nb_colors: int = 4, scores: list = [1, 2, 3, 4]) -> None:
        """
        Initialize the City object.

        Args:
            rows (int): Number of rows in the grid.
            cols (int): Number of columns in the grid.
            nb_colors (int): Number of different tower colors [0, nb_colors).
            scores (list): List of scores for each of the four tower colors.

        Raises:
            ValueError: If nb_colors is invalid or not enough scores are provided.
        """
        if nb_colors < 1 or nb_colors > 4:
            raise ValueError(f"Number of colors {nb_colors} is out of bounds. Must be between 1 and 4.")
        if len(scores) < nb_colors:
            raise ValueError(f"Number of scores {len(scores)} is out of bounds. Must be at least nbcolors={nb_colors}.")

        self.n = rows
        self.m = cols
        self.nb_colors = nb_colors

        self.scores = scores[0:nb_colors]
        self.colors = ["Blue", "Red", "Green", "Yellow"][0:nb_colors]
        self.colors_short = list(str(i) for i in range(nb_colors))
        self.color_codes = ['#0075B5', 'red', 'green', 'yellow'][0:nb_colors]

    def neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """
        Create a list of neighbors to a given cell, filtering out-of-bounds neighbors.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.

        Returns:
            list: A list of (row, col) tuples representing valid neighboring cells.
            For the 1x1 grid the list is empty.

        Raises:
            ValueError: If row or col is out of bounds.
        """
        if row < 0 or row >= self.n:
            raise ValueError(f"Row index {row} is out of bounds. Must be between 0 and {self.n - 1}.")
        if col < 0 or col >= self.m:
            raise ValueError(f"Col index {col} is out of bounds. Must be between 0 and {self.m - 1}.")

        neighbors = []
        if row > 0:
            neighbors.append((row - 1, col))  # Up
        if row < self.n - 1:
            neighbors.append((row + 1, col))  # Down
        if col > 0:
            neighbors.append((row, col - 1))  # Left
        if col < self.m - 1:
            neighbors.append((row, col + 1))  # Right
        return neighbors

    def extended_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """
        Create a list of extended neighbors to a given cell, filtering out-of-bounds neighbors.
        Extended neighbors are those that can be reached by a chess king in a single step.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.

        Returns:
            list: A list of (row, col) tuples representing valid neighboring cells.
            For the 1x1 grid the list is empty.

        Raises:
            ValueError: If row or col is out of bounds.
        """
        if row < 0 or row >= self.n:
            raise ValueError(f"Row index {row} is out of bounds. Must be between 0 and {self.n - 1}.")
        if col < 0 or col >= self.m:
            raise ValueError(f"Col index {col} is out of bounds. Must be between 0 and {self.m - 1}.")

        neighbors = [
            (i, j)
            for i in range(row - 1, row + 2)
            for j in range(col - 1, col + 2)
            if i >= 0 and i < self.n and j >= 0 and j < self.m and (i, j) != (row, col)
        ]
        return neighbors
