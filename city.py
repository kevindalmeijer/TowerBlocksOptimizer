class City:
    """
    Class that models the properties of a city, including grid size and allowed tower colors.
    """

    def __init__(self, rows: int, cols: int, scores: list = [1, 2, 3, 4]) -> None:
        """
        Initialize the City object.

        Args:
            rows (int): Number of rows in the grid.
            cols (int): Number of columns in the grid.
            scores (list): List of scores for each of the four tower colors.
        """
        self.n = rows
        self.m = cols
        if len(scores) != 4:
            raise Exception(f"Provided len(scores)={len(scores)} but len(scores)=4 expected.")
        self.scores = scores

        self.nb_colors = 4
        self.colors = ["Blue", "Red", "Green", "Yellow"]
        self.colors_short = list(str(i) for i in range(4))
        self.color_codes = ['#0075B5', 'red', 'green', 'yellow']

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
