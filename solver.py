import configuration
import city
import copy


class InfeasibleConfigurationError(Exception):
    """
    Error for configurations that cannot be constructed with valid moves.
    """
    def __init__(self, config, conflict):
        super().__init__(f"Configuration\n{config}\nincludes the minimal conflict\n{conflict}.")


class SafeReductionError(Exception):
    """
    Error that indicates that a reduction that was flagged as safe could not safely be performed.
    """
    def __init__(self, config, row, col):
        super().__init__(f"Failed to safely reduce ({row}, {col}) in configuration\n{config}.")


class Solver:
    """
    Class to calculate high-scoring configurations and the corresponding moves to construct them.
    """

    def __init__(self, city: city.City) -> None:
        """
        Initialize the Solver object with a reference to a City.

        Args:
            city (City): The City object that contains the grid, color, and scoring information.
        """
        self.city = city
        self.info = dict()

    def solve(self) -> tuple[configuration.Configuration, dict]:
        """
        Solve an optimization problem to obtain a high-scoring configuration.

        Returns:
            Configuration: Final tower configuration resulting from the optimization.
            dict: Dictionary with information about the solve.

        Raises:
            InfeasibleConfigurationError: If no valid moves can be found to construct
            the generated solution configuration.
        """
        solution = configuration.Configuration(self.city)
        self.info["optimal"] = False

        # TODO: improve zero solution

        self.info["moves"] = self.get_moves(solution)  # raises error if impossible
        self.info["total_score"] = solution.get_total_score()
        return solution, self.info

    def get_moves(self, config: configuration.Configuration) -> tuple[int, int, int]:
        """
        Generate a list of moves (row, col, color) that turn the zero configuration
        into the provided configuration, or throw an error with a minimal conflict.
        This method is exhaustive and should find a list of moves if one exists,
        although there are no guarantees on the length of the list.

        Args:
            config (configuration.Configuration): The target configuration.

        Raises:
            InfeasibleConfigurationError: If the configuration cannot be attained.

        Returns:
            tuple: List of moves (row, col, color).
        """
        reduced_config, moves = self.__get_reduced_configuration(config)
        if not self.valid_sequence(reduced_config, moves, config):
            raise Exception("get_moves() generated an invalid sequence of moves.")  # this should never happen

        if not reduced_config.all_zero():
            raise InfeasibleConfigurationError(config, reduced_config)

        return moves

    def valid_sequence(
        self,
        start_config: configuration.Configuration,
        moves: list[tuple[int, int, int]],
        end_config: configuration.Configuration
    ) -> bool:
        """
        Test if the sequence of moves allows the start configuration to turn into the end configuration.

        Args:
            start_config (configuration.Configuration): Start configuration.
            moves (list[tuple[int, int, int]]): List of moves (row, col, color).
            end_config (configuration.Configuration): End configuration.

        Returns:
            bool: True if all moves are valid and provide a path from start to end, False otherwise.
        """
        config = copy.deepcopy(start_config)
        for move in moves:
            try:
                config.place_tower(*move, verify=True)  # apply moves with verification
            except configuration.PlacementError:
                return False  # invalid tower placement
        return config.towers == end_config.towers  # test if end_config has been reached

    def __apply_safe_reductions(self, config: configuration.Configuration) -> list[tuple[int, int, int]]:
        """
        Apply as many safe reductions to the given configuration as possible
        (modifying the input) and return the moves that correspond to this reduction.

        Args:
            config (configuration.Configuration): The configuration to start from -- will be modified!

        Returns:
            list: List of moves to move from the modified configuration to the original configuration.
        """
        moves = []
        change_made = True
        while change_made:
            change_made = False
            for row in range(self.city.n):
                for col in range(self.city.m):
                    new_moves = self.__apply_safe_reduction(config, row, col)
                    if len(new_moves) > 0:
                        change_made = True
                        moves = new_moves + moves
        return moves

    def __apply_safe_reduction(
        self,
        config: configuration.Configuration,
        row: int,
        col: int,
        error_on_fail: bool = False
    ) -> list[tuple[int, int, int]]:
        """
        Attempt to safely reduce the color of the tower at position (row, col) to zero.
        If the reduction is successful, config is updated to the reduced configuration and a
        list of corresponding moves from the reduced configuration to the original configuration is returned.
        If no safe reduction is possible, either an empty list of moves is returned (default),
        or an error is thrown (if error_on_fail is set).

        A reduction is safe if:
        1. Tower (row, col) neighbors all towers that would be needed to build this tower now.
            - Example: (row, col) has color 2 and has neighbors of 0 and 1. In this case, we can
            reduce (row, col) to color 0 and return a single valid move (row, col, 2).
        2. Towers of color 0 neighboring (row, col) can be promoted to colors such that rule 1 applies.
        In this case it is critical that the promotions can be undone after the reduction of (row, col).
            - Example (1-promotion): (row, col) has color 2 and has two neighbors of 0 and no neighbors of 1.
            Going back in time, one of the 0s (p, q) can be promoted to a 1. This corresponds to a forward
            move (p, q, 0). Going further back in time, (row, col) can now be reduced with move (row, col, 2).
            Finally, the promotion has to be undone. This is always possible (i.e., the reduction is safe),
            as (row, col) serves as the necessary 0 neighbor for (p, q). Following rule 1, (p, q) is
            reduced to 0 with move (p, q, 1). The overall result is that config now has a 0 tower at (row, col)
            and the corresponding moves [(p, q, 1), (row, col, 2), (p, q, 0)]] are returned.
            - Example (2-promotion): to guarantee safety, promotions to color 2 at cell (p, q) are only
            performed if (p, q) has a neighbor (v, w) != (row, col) with color 0 or 1. For example,
            lets say (row, col) has color 3 and has two neighbors of 0, one neighbor of 1, and no neighbors of 2.
            One of the 0-neighbors has its own neighbor (v, w) different from (row, col) with color 1.
            Going back in time, we can now safely promote (p, w) to 2, then reduce (row, col) to 0,
            and then use rule 1 to reduce (p, w) to 0 based on its necessary neighbors with color 0 (row, col)
            and color 1 (v, w).
            - Example (nested promotion): in the example above, if (v, w) had been color 0 instead, then
            (p, q) could still be reduced back from color 2 to color 0 by applying rule 2 (1-promotion) on
            the two 0-neighbors (row, col) and (v, w).

        Args:
            config (configuration.Configuration): The configuration to start from -- will be modified!
            row (int): The row index of the tower to be reduced.
            col (int): The column index of the tower to be reduced.
            error_on_fail (bool, optional): If True, throw an error when the reduction fails.
                The default behavior (error_on_fail=False) is to return an empty list of moves.

        Returns:
            list: List of moves (p, q, color) from the reduced configuration to the original configuration.

        Raises:
            SafeReductionError: If reduction is not possible and error_on_fail is True.
        """
        def reduction_fail():
            if error_on_fail:
                raise SafeReductionError(config, row, col)
            return []

        color = config.towers[row][col]
        if color == 0:
            return reduction_fail()  # tower is already color 0
        if not config.has_neighbor(row, col, 0):
            return reduction_fail()  # no neighbors with color 0

        nb_zero_neighbors = sum(config.towers[p][q] == 0 for p, q in self.city.neighbors(row, col))
        nb_promotions_available = nb_zero_neighbors - 1  # -1 to maintain at least one neighbor with color 0

        # The reduction additionally requires neighbors with colors in range [1, color).
        # For each needed color, check if it is available or propose a promotion.
        promotions = []
        used_neighbors = []
        for color_needed in reversed(range(1, color)):  # reverse loop to handle more restrictive promotions first
            if config.has_neighbor(row, col, color_needed):
                continue  # no promotion necessary
            if nb_promotions_available == 0:
                return reduction_fail()  # no more 0-towers available for promotion
            promotion_added = False
            for p, q in self.city.neighbors(row, col):
                if (p, q) in used_neighbors:
                    continue  # already used
                if self.__safely_promotable(config, row, col, p, q, color_needed):
                    promotions += [(p, q, color_needed)]
                    used_neighbors += [(p, q)]
                    promotion_added = True
                    break
            if not promotion_added:
                return reduction_fail()  # failed to find a safely promotable neighbor
            nb_promotions_available -= 1

        # Perform pending promotions
        moves = []
        for p, q, promotion_color in promotions:
            config.towers[p][q] = promotion_color
            moves = [(p, q, 0)] + moves

        # Reduce target tower
        config.towers[row][col] = 0
        moves = [(row, col, color)] + moves

        # Undo the promotions with recursive reductions that are guaranteed to safe by design
        for p, q, _promotion_color in promotions:
            moves = self.__apply_safe_reduction(config, p, q, error_on_fail=True) + moves  # fail on error

        return moves

    def __safely_promotable(
        self,
        config: configuration.Configuration,
        reduce_row: int,
        reduce_col: int,
        promote_row: int,
        promote_col: int,
        promote_color: int,
    ) -> bool:
        """
        Test whether neighbor (promote_row, promote_col) in config can safely be promoted to promote_color,
        for the sake of reducing (reduce_row, reduce_col).

        Args:
            config (configuration.Configuration): The current configuration.
            reduce_row (int): The row index of the tower to be reduced.
            reduce_col (int): The column index of the tower to be reduced.
            promote_row (int): The row index of the tower to be promoted.
            promote_col (int): The column index of the tower to be promoted.
            promote_color (int): The color of the tower to be promoted.
            free_neighbors (list): Free neighbors that can be used to undo the promotion.

        Returns:
            bool: True if (row, col) is safely promotable, False otherwise.
        """

        if (promote_row, promote_col) not in self.city.neighbors(reduce_row, reduce_col):
            raise Exception(
                f"Promotion tower ({promote_row}, {promote_col}) is not a neighbor of " +
                f"reduction tower ({reduce_row}, {reduce_col})."
            )
        if promote_color not in [1, 2]:
            raise Exception("Only promotion colors 1 and 2 are supported by safely_promotable().")

        if config.towers[promote_row][promote_col] != 0:
            return False  # only 0 towers can be promoted
        if promote_color == 1:
            return True  # 1-promotion is always safe: see __apply_safe_reduction()
        elif promote_color == 2:
            # 2-promotion requires an extra 0/1 neighbor: see __apply_safe_reduction()
            for v, w in self.city.neighbors(promote_row, promote_col):
                if (v, w) == (reduce_row, reduce_col):
                    continue
                if config.towers[v][w] in [0, 1]:
                    return True

        return False

    # TODO: clean and document
    def __get_reduced_configuration(self, config: configuration.Configuration):
        """
        Given a configuration, return a list of moves (row, col, color) to achieve that configuration,
        or raise an error if such list can be found. There is no guarantee that this list is of minimal length.
        TODO: Guarantee that a list can be found if it exists;
            currently not the case for [[0, 3, 0], [3, 0, 3], [0, 3, 0]]

        Args:
            config (Configuration): The final tower configuration

        Returns:
            list of tuples: A list of (row, col, color) tuples representing the moves.
            #TODO moves + reduced

        Raises:
            Exception: If a path to the configuration cannot be found.
            #TODO error if fails
        """
        current_config = copy.deepcopy(config)
        moves = self.__apply_safe_reductions(current_config)
        minimal_config = current_config
        minimal_config_moves = moves

        # If safe reductions are insufficient to reduce all towers,
        # recursively call get_moves() for each 2-promotion that enables a 3-reduction
        if not current_config.all_zero():

            def get_two_promotion_eligible_neighbors(row, col):

                color = current_config.towers[row][col]
                if color != 3:
                    return []

                neighbors = self.city.neighbors(row, col)
                nb_zero = sum(current_config.towers[p][q] == 0 for p, q in neighbors)
                nb_one = sum(current_config.towers[p][q] == 1 for p, q in neighbors)

                if not ((nb_zero >= 2 and nb_one >= 1) or nb_zero >= 3):
                    return []

                return [(p, q) for p, q in neighbors if current_config.towers[p][q] == 0]

            possible_promotions = set()
            for row in range(self.city.n):
                for col in range(self.city.m):
                    possible_promotions.update(get_two_promotion_eligible_neighbors(row, col))

            for row, col in possible_promotions:
                trial_config = copy.deepcopy(current_config)
                trial_config.place_tower(row, col, 2)
                reduced_trial_config, new_moves = self.__get_reduced_configuration(trial_config)
                trial_moves = new_moves + [(row, col, 0)] + moves

                if reduced_trial_config < minimal_config:
                    minimal_config = reduced_trial_config
                    minimal_config_moves = trial_moves

                if reduced_trial_config.all_zero():
                    current_config = reduced_trial_config
                    moves = trial_moves
                    break

            if not current_config.all_zero():
                current_config = minimal_config
                moves = minimal_config_moves

        return current_config, moves
