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
        """
        neighbors = [
            (row - 1, col),  # Up
            (row + 1, col),  # Down
            (row, col - 1),  # Left
            (row, col + 1)   # Right
        ]

        # Filter neighbors to keep only those within bounds
        return [(r, c) for r, c in neighbors if 0 <= r < self.n and 0 <= c < self.m]
