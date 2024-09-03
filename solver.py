import configuration
import copy


class Solver:
    def __init__(self, city):
        """
        Initialize the Solver object with a reference to a City.

        Args:
            city (City): The City object that contains the grid, neighbor, and point information.
        """
        self.city = city
        self.status = dict()

    def solve(self):
        """
        Solve the optimization problem and return a final configuration and status.

        Returns:
            - Configuration: An instance of Configuration with the final tower placement.
            - dict: Status information about the solve.
        """
        solution = configuration.Configuration(self.city)
        self.status["optimal"] = False
        if not self.is_implementable(solution):
            raise Exception("Could not prove the solution is implementable.")
        return solution, self.status

    def get_moves(self, config: configuration.Configuration):
        """
        Given a configuration, return a list of moves (row, col, color) to achieve that configuration,
        or raise an error if such list can be found. There is no guarantee that this list is of minimal length.
        TODO: Guarantee that a list can be found if it exists;
            currently not the case for [[0, 3, 0], [3, 0, 3], [0, 3, 0]]

        Args:
            config (Configuration): The final tower configuration.

        Returns:
            list of tuples: A list of (row, col, color) tuples representing the moves.

        Raises:
            Exception: If a path to the configuration cannot be found.
        """
        current_config = copy.deepcopy(config)
        moves = []

        # Work back in time to reduce the towers and record the corresponding moves
        change_made = True
        while change_made:
            change_made = False
            for row in range(self.city.n):
                for col in range(self.city.m):
                    new_moves = self.__safe_reduce(current_config, row, col)
                    if len(new_moves) > 0:
                        change_made = True
                        moves = new_moves + moves

        if not self.moves_valid(moves, config):
            raise Exception(
                "Could not find list of moves for the given configuration: " +
                "Either the configuration is infeasible, or the get_moves() algorithm is not sufficiently strong."
            )  # TODO

        return moves

    def moves_valid(self, moves, goal):

        config = configuration.Configuration(city=self.city)

        for move in moves:
            try:
                config.place_tower(*move, verify=True)
            except Exception:
                return False

        if config.towers != goal.towers:
            return False

        return True

    def is_implementable(self, config: configuration.Configuration):
        try:
            self.get_moves(config)
            return True
        except Exception:
            return False

    def __safe_reduce(self, config: configuration.Configuration, row, col, error_on_fail=False):
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
                    # perform promotion
                    config.towers[p][q] = color_needed
                    moves = [(p, q, 0)] + moves
                    promotions += [(p, q)]
                    promoted = True
                    break

            if not promoted:
                return irreducible()  # necessary promotion failed

            nb_promotions_available -= 1

        # reduce (row, col) to 0 and then reduce the promotions that were made
        config.towers[row][col] = 0
        moves = [(row, col, color)] + moves
        for p, q in promotions:
            moves = self.__safe_reduce(config, p, q, error_on_fail=True) + moves

        return moves
