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
    pass


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

    # TODO: clean and document
    def __apply_safe_reduction(
        self,
        config: configuration.Configuration,
        row: int,
        col: int,
        error_on_fail: bool = False
    ) -> list[tuple[int, int, int]]:
        """
        Attempt to safely reduce the color of a tower at a specific position to 0, if possible.

        This method tries to "reduce" the color of a tower (change its color to 0)
        at the specified (row, col) position. If the reduction is not possible, the method may either
        return an empty list or raise an exception, depending on the `error_on_fail` flag.

        Args:
            config (Configuration): The current tower configuration -- will be modified!
            row (int): The row index of the tower to reduce.
            col (int): The column index of the tower to reduce.
            error_on_fail (bool): If True, raises an Exception when reduction fails.
                                If False, returns an empty list on failure.

        Returns:
            list of tuples: A list of (row, col, color) tuples representing the moves required to achieve the reduction.
                            If reduction is not possible and `error_on_fail` is False, returns an empty list.

        Raises:
            Exception: If reduction is not possible and `error_on_fail` is True, an Exception is raised.

        Notes:
            - The method tries to promote adjacent towers with color 0 to the necessary color to enable the reduction.
            - If promotion is not possible, the reduction fails.
            - The algorithm recursively reduces any promoted towers after the initial reduction.
            - Promotion is only carried out if this recursive reduction is guaranteed to work
        """
        def irreducible():
            if error_on_fail:
                raise Exception("reduce() failed while error_on_fail=True")
            return []

        color = config.towers[row][col]
        assert color <= 3, "This function does not support reduction for colors > 3"

        if color == 0:
            return irreducible()  # no further reduction possible

        if not config.has_neighbor(row, col, 0):
            return irreducible()  # no neighbors with color 0 so the reduction fails

        # Try to find the colors needed from neighbors to make the reduction possible.
        # If necessary, towers with color 0 are promoted to the necessary color.

        moves = []       # track moves performed
        promotions = []  # track necessary promotions for the reduction
        promotion_colors = []

        neighbors = self.city.neighbors(row, col)
        nb_zero = sum(config.towers[p][q] == 0 for p, q in neighbors)
        nb_promotions_available = nb_zero - 1  # -1 to keep one 0 tower for reduction

        for color_needed in reversed(range(1, color)):  # reverse loop to handle difficult promotions first

            if config.has_neighbor(row, col, color_needed):
                continue  # neigbor with color_needed is readily available

            # attempt to make the reduction possible by promoting a 0 to color_needed
            if nb_promotions_available == 0:
                return irreducible()

            # tower number can safely be increased, as it can be decreased again immediately after
            def safely_promotable(p, q):

                assert color_needed in [1, 2]  # 0 does not need promotion, color > 3 (color_needed > 2) not supported

                if config.towers[p][q] != 0:
                    return False  # only 0 towers can be promoted

                if (p, q) in promotions:
                    return False  # already used

                if color_needed == 1:
                    # after reducing (row, col) to 0, the 0 tower can be used to reduce (p, q) from 1 back to 0
                    return True

                # color_needed == 2
                # if (p, q) has another neighbor (v, w) that is 0 or 1, then after reducing (row, col) to 0:
                # (row, col, 0) and (v, w, 0/1) can together reduce (p, q, 2) back to 0
                neighbor_neighbors = [
                    neighbor_neighbor
                    for neighbor_neighbor in self.city.neighbors(p, q)
                    if neighbor_neighbor != (row, col)
                ]
                for v, w in neighbor_neighbors:
                    if config.towers[v][w] in [0, 1]:
                        return True

                return False

            promoted = False
            for p, q in neighbors:
                if safely_promotable(p, q):
                    promotions += [(p, q)]
                    promotion_colors += [color_needed]
                    promoted = True
                    break

            if not promoted:
                return irreducible()  # necessary promotion failed

            nb_promotions_available -= 1

        for promotion, promotion_color in zip(promotions, promotion_colors):
            p, q = promotion
            config.towers[p][q] = promotion_color
            moves = [(p, q, 0)] + moves
        config.towers[row][col] = 0
        moves = [(row, col, color)] + moves
        for promotion, promotion_color in zip(promotions, promotion_colors):
            p, q = promotion
            moves = self.__apply_safe_reduction(config, p, q, error_on_fail=True) + moves

        return moves

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
