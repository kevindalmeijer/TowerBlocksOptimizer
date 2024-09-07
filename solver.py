import configuration
import city
import copy
import warnings
import trivial_optimizer


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

    def solve(self, optimizer=None) -> tuple[configuration.Configuration, dict]:
        """
        Solve an optimization problem to obtain a high-scoring configuration.

        Args:
            optimizer: instance of an optimization class that has a function run()
                that returns a solution and info about the solve; see TrivialOptimizer as an example.

        Returns:
            Configuration: Final tower configuration resulting from the optimization.
            dict: Dictionary with information about the solve.

        Raises:
            InfeasibleConfigurationError: If no valid moves can be found to construct
            the generated solution configuration.
        """
        if optimizer is None:
            warnings.warn("No optimizer provided: using trivial optimizer by default.", UserWarning)
            optimizer = trivial_optimizer.TrivialOptimizer(self.city)

        solution, info = optimizer.run()
        self.info.update(info)
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
        for p, q, _ in promotions:
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

    def __get_reduced_configuration(
        self,
        config: configuration.Configuration
    ) -> tuple[configuration.Configuration, list[tuple[int, int, int]]]:
        """
        Generates a reduced configuration and a list of moves (row, col, color) such that:
        - applying the list of moves to the reduced configuration results in the original configuration,
        - the reduced configuration cannot be reduced further.

        The reduction is performed by first applying safe reductions (see __apply_safe_reductions()) and
        then performing depth-first search on potentially unsafe reductions.
        The original config is not modified during this process.

        Args:
            config (configuration.Configuration): The configuration to be reduced -- will not be modified.

        Returns:
            configuration.Configuration: The reduced configuration, which is either all zeros if config
                can be constructed with valid moves, or represent a minimal (but not necessarily minimum) conflict.
        """
        current_config = copy.deepcopy(config)  # config at current node of the search tree
        current_moves = []                      # ...and corresponding moves from current_config to config

        current_moves = self.__apply_safe_reductions(current_config) + current_moves
        if current_config.all_zero():
            return current_config, current_moves  # safe reductions were sufficient to obtain the all-zero configuration

        minimal_config = current_config         # minimal config encountered during the search
        minimal_moves = current_moves           # ...and corresponding moves from minimal_config to config

        search_list = self.__get_useful_two_promotions(current_config)
        for promotion in search_list:

            next_config = copy.deepcopy(current_config)     # create new node in the search tree
            next_config.place_tower(*promotion, 2)          # apply promotion to the node
            next_to_current_move = [(*promotion, 0)]        # record move to undo the promotion

            # create a reduced next configuration and corresponding moves through a recursive call
            reduced_next_config, reduced_next_to_next_moves = self.__get_reduced_configuration(next_config)
            reduced_next_moves = reduced_next_to_next_moves + next_to_current_move + current_moves

            if reduced_next_config.all_zero():
                return reduced_next_config, reduced_next_moves

            if reduced_next_config < minimal_config:
                minimal_config = reduced_next_config
                minimal_moves = reduced_next_moves

        return minimal_config, minimal_moves

    def __get_useful_two_promotions(self, config: configuration.Configuration) -> set[tuple[int, int]]:
        """
        Return the set of all useful 2-promotions (row, col). A 2-promotion is said to be useful if
        promoting (row, col) from 0 to 2 enables the safe reduction of a neighboring tower of color 3,
        where this was previously impossible.

        Args:
            config (configuration.Configuration): The tower configuration.

        Returns:
            set: Set of useful 2-promotions (row, col).
        """

        # Loop over 3-towers for which safe reduction is enabled by promoting a neighboring 0 to 2.
        # For these 3-towers, flag all the 0 neighbors as useful promotions.

        useful_two_promotions = set()  # avoid duplicates when promotions are useful to multiple neighbors

        for row in range(self.city.n):
            for col in range(self.city.m):
                if config.towers[row][col] != 3:
                    continue  # only interested in 3-towers
                counts = config.neighbor_counts(row, col)
                if counts[2] > 0:
                    continue  # 2-tower is already available
                if counts[0] < 2:
                    continue  # need at least two 0-neighbors; one for the reduction and one to promote to 2
                if counts[1] >= 1 or counts[0] >= 3:
                    # need at least one 1-tower (0/0/1) or three 0-towers (0/0/0)
                    useful_two_promotions.update(
                        (p, q) for p, q in self.city.neighbors(row, col)
                        if config.towers[p][q] == 0  # flag 0-neighbors
                    )

        return useful_two_promotions
