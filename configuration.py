class Configuration:

    def __init__(self, city):
        """
        Initialize the Configuration object.

        Args:
            n (int): Number of rows in the grid.
            m (int): Number of columns in the grid.
        """
        self.city = city
        self.towers = [[0 for _ in range(city.m)] for _ in range(city.n)]

    def place_tower(self, row, col, color, verify=False):
        """
        Place a tower on the grid.

        Args:
            row (int): The row index where the tower should be placed.
            col (int): The column index where the tower should be placed.
            color (int): The color of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).
        """
        self.__check_bounds(row, col, color)
        if verify and not self.__valid_placement(row, col, color):
            raise Exception(f"Placement (row={row}, col={col}, color={color}) invalid")
        self.towers[row][col] = color

    def __check_bounds(self, row, col, color):
        """
        Check if the given placement is within the bounds of the grid and if the color is valid.

        Args:
            row (int): The row index where the tower is being placed.
            col (int): The column index where the tower is being placed.
            color (int): The color index of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).

        Raises:
            ValueError: If the row or column index is out of bounds, or if the color is invalid.
        """
        if not (0 <= row < self.city.n):
            raise ValueError(f"Row index {row} is out of bounds. Must be between 0 and {self.city.n - 1}.")

        if not (0 <= col < self.city.m):
            raise ValueError(f"Column index {col} is out of bounds. Must be between 0 and {self.city.m - 1}.")

        if not (0 <= color < self.city.nb_colors):
            raise ValueError(f"Color index {color} is invalid. Must be between 0 and {self.city.nb_colors - 1}.")

    def __valid_placement(self, row, col, color):
        """
        Verify if the current placement of towers is valid according to the rules.

        Args:
            row (int): The row index where the tower should be placed.
            col (int): The column index where the tower should be placed.
            color (int): The color of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).

        Returns:
            bool: True if the placement is valid, False otherwise.
        """

        if color == 0:
            pass  # Blue tower has no requirements
        elif color == 1:
            if not all(self.has_neighbor(row, col, k) for k in range(1)):
                return False
        elif color == 2:
            if not all(self.has_neighbor(row, col, k) for k in range(2)):
                return False
        elif color == 3:
            if not all(self.has_neighbor(row, col, k) for k in range(3)):
                return False
        else:
            raise ValueError(f"No rules defined for color {color}")

        return True

    def has_neighbor(self, row, col, color):
        """
        Check if a cell has a neighbor with a specific color.

        Args:
            row (int): Row index of the cell.
            col (int): Column index of the cell.
            color (int): Color to check for (0 for blue, 1 for red, 2 for green, 3 for yellow).

        Returns:
            bool: True if there is a neighbor with the specified color, False otherwise.
        """
        neighbors = self.city.neighbors(row, col)
        for r, c in neighbors:
            if self.towers[r][c] == color:
                return True
        return False

    def __str__(self):
        """
        Return a string representation of the grid configuration.
        """
        color_map = self.city.colors_short
        return "\n".join([" ".join([color_map[cell] for cell in row]) for row in self.towers])
