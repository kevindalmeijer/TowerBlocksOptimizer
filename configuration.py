import city


class PlacementError(Exception):
    """
    Error for invalid tower placements.
    """
    def __init__(self, config, row, col, color):
        super().__init__(f"Placement (row={row}, col={col}, color={color}) is invalid for configuration:\n{config}")


class Configuration:
    """
    Class that holds a configuration of towers for a given city.
    """

    def __init__(self, city: city.City) -> None:
        """
        Initialize a Configuration. All towers are initialized at zero.

        Args:
            city (city.City): City that defines the grid for this configuration.
        """
        self.city = city
        self.towers = [[0 for _ in range(city.m)] for _ in range(city.n)]

    def __lt__(self, other: 'Configuration') -> bool:
        """
        Overload the < operator to compare two configurations.
        A configuration is strictly smaller if all tower colors are smaller or equal,
        and at least one tower color is strictly smaller.

        Args:
            other (Configuration): The other configuration to compare against.

        Returns:
            bool: True if self < other according to the definition above.
        """
        if self.towers == other.towers:
            return False
        for tower_row_self, tower_row_other in zip(self.towers, other.towers):
            for tower_self, tower_other in zip(tower_row_self, tower_row_other):
                if tower_self > tower_other:
                    return False
        return True

    def __str__(self) -> str:
        """
        Return a string representation of the configuration using the short names defined by the city
        """
        color_map = self.city.colors_short
        return "\n".join([" ".join([color_map[cell] for cell in row]) for row in self.towers])

    def place_tower(self, row: int, col: int, color: int, verify: bool = False) -> None:
        """
        Place a tower on the grid.

        Args:
            row (int): The row index where the tower should be placed.
            col (int): The column index where the tower should be placed.
            color (int): The color of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).
            verify (bool): If True, raise a PlacementError if the placement is invalid.

        Raises:
            ValueError: If the row or column index is out of bounds, or if the color is invalid.
            PlacementError: If verify=True and the placement is invalid.
        """
        self.__check_bounds(row, col, color)
        if verify and not self.__valid_placement(row, col, color):
            raise PlacementError(self, row, col, color)
        self.towers[row][col] = color

    def has_neighbor(self, row: int, col: int, color: int) -> bool:
        """
        Check if a cell has a neighbor with a specific color.

        Args:
            row (int): The row index where the tower should be placed.
            col (int): The column index where the tower should be placed.
            color (int): The color of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).

        Returns:
            bool: True if there is a neighbor with the specified color, False otherwise.

        Raises:
            ValueError: If the row or column index is out of bounds, or if the color is invalid.
        """
        neighbors = self.city.neighbors(row, col)
        for p, q in neighbors:
            if self.towers[p][q] == color:
                return True
        return False

    def all_zero(self) -> bool:
        """
        Check if all towers in the grid have color zero.

        Returns:
            bool: True if all towers are zero, False otherwise.
        """
        return all(tower == 0 for tower_row in self.towers for tower in tower_row)

    def __check_bounds(self, row: int, col: int, color: int) -> None:
        """
        Check if the given placement is within the bounds of the grid and if the color is valid.

        Args:
            row (int): The row index where the tower should be placed.
            col (int): The column index where the tower should be placed.
            color (int): The color of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).

        Raises:
            ValueError: If the row or column index is out of bounds, or if the color is invalid.
        """
        if not (0 <= row < self.city.n):
            raise ValueError(f"Row index {row} is out of bounds. Must be between 0 and {self.city.n - 1}.")

        if not (0 <= col < self.city.m):
            raise ValueError(f"Column index {col} is out of bounds. Must be between 0 and {self.city.m - 1}.")

        if not (0 <= color < self.city.nb_colors):
            raise ValueError(f"Color index {color} is invalid. Must be between 0 and {self.city.nb_colors - 1}.")

    def __valid_placement(self, row: int, col: int, color: int) -> bool:
        """
        Check if the current tower placement is valid according to the rules.

        Args:
            row (int): The row index where the tower should be placed.
            col (int): The column index where the tower should be placed.
            color (int): The color of the tower (0 for blue, 1 for red, 2 for green, 3 for yellow).

        Returns:
            bool: True if the placement is valid, False otherwise.

        Raises:
            ValueError: If the row or column index is out of bounds, or if the color is invalid.
        """
        self.__check_bounds(row, col, color)
        return all(self.has_neighbor(row, col, k) for k in range(color))
