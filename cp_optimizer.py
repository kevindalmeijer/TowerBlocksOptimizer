import solver
import configuration
from ortools.sat.python import cp_model
import itertools as it
import warnings


class CPOptimizer:
    """
    Optimizer based on constraint-programming solver CP-SAT.
    """

    def __init__(self, solver: solver.Solver, settings: dict = {}) -> None:
        """
        Initialize the CPOptimizer object and check the settings provided by the user.

        Args:
            solver (solver.Solver): Solver for which the optimizer is called.
            settings (dict): Dictionary of user-provided parameters and values.
                See __check_user_settings() for details.
        """
        self.city = solver.city
        self.settings = settings
        self.__check_user_settings()

        n = self.city.n
        m = self.city.m
        self.nb_periods = min(n * m, settings["depth_limit"]) if "depth_limit" in self.settings else n * m

        self.__build_model()

    def __check_user_settings(self) -> None:
        """
        Check the settings provided by the user and give a warning for parameters that are not recognized.
        """
        parameters = [
            "time_limit",   # time limit in seconds (default: no limit)
            "depth_limit",  # maximum number of periods used by the model (default: city.n * city.m)
            "print_log",    # print the CP-SAT log (default: False)
        ]
        for parameter in self.settings:
            if parameter not in parameters:
                warnings.warn(f"'{parameter}' is not a recognized parameter and will be ignored.", UserWarning)

    def run(self) -> tuple[configuration.Configuration, dict]:
        """
        Run the optimization model.

        Returns:
            tuple(configuration.Configuration, dict): Best configuration that was found and
            a dictionary with information about the solve.
        """
        status = self.cp_solver.Solve(self.model)

        solution = configuration.Configuration(self.city)
        solution.towers = self.get_solution_towers()

        info = dict()

        # Solution is optimal if...
        info["optimal"] = (status == 4)  # ...CP-SAT reports optimality, and...
        required_depth = self.city.n * self.city.m  # ...the depth used is sufficient.
        if self.settings.get("depth_limit", required_depth) < required_depth:
            info["optimal"] = False

        return solution, info

    def get_solution_towers(self) -> list[list[int]]:
        """
        Get the tower placements found by the solver as a double array.

        Returns:
            list: Best found tower placements as a double array.
        """
        solution = [
            [
                sum(
                    self.cp_solver.Value(self.y[i, j, k]) * k
                    for k in range(self.city.nb_colors)
                )
                for j in range(self.city.m)
            ]
            for i in range(self.city.n)
        ]
        return solution

    def __build_model(self) -> None:
        """
        Build the constraint programming model.
        """
        n = self.city.n
        m = self.city.m
        nb_colors = self.city.nb_colors
        nb_periods = self.nb_periods

        self.model = cp_model.CpModel()
        self.cp_solver = cp_model.CpSolver()

        self.__set_solver_settings()
        self.x, self.y = self.__define_variables(self.model, n, m, nb_colors, nb_periods)
        self.__add_objective()
        self.__add_constraints(self.model, self.x, n, m, nb_colors, nb_periods)
        self.__add_redundant_constraints(self.model, self.x, self.y, n, m, nb_colors, nb_periods)

    def __set_solver_settings(self) -> None:
        """
        Set solver settings based on the settings provided at initialization.
        """
        if "time_limit" in self.settings:
            self.cp_solver.parameters.max_time_in_seconds = self.settings['time_limit']
        if "print_log" in self.settings:
            self.cp_solver.parameters.log_search_progress = self.settings["print_log"]

    def __define_variables(
        self,
        model: cp_model.CpModel,
        n: int,
        m: int,
        nb_colors: int,
        nb_periods: int
    ) -> tuple[dict, dict]:
        """
        Define variables and basic constraints for the optimization model.

        Args:
            model (cp_model.CpModel): CP-SAT model.
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
            nb_colors (int): shorthand for self.city.nb_colors
            nb_periods (int): shorthand for self.nb_periods

        Returns:
            tuple(dict, dict): variables x and variables y.
        """

        # Variables y represent the final configuration
        y = {
            (i, j, k):
                model.NewBoolVar(f"y_{i}_{j}_{k}")
            for i in range(n)
            for j in range(m)
            for k in range(nb_colors)
        }

        # Assign one color to each tower
        for i in range(n):
            for j in range(m):
                model.AddExactlyOne(y[i, j, k] for k in range(nb_colors))

        # Variables x represent the configuration in different periods
        # from period 0 to nb_periods-1 (which matches y).
        x = {
            (i, j, k, t):
                model.NewBoolVar(f"x_{i}_{j}_{k}_{t}")
            for i in range(n)
            for j in range(m)
            for k in range(nb_colors)
            for t in range(nb_periods)
        }

        # Assign one color to each tower in each period
        for i in range(n):
            for j in range(m):
                for t in range(nb_periods):
                    model.AddExactlyOne(x[i, j, k, t] for k in range(nb_colors))

        # x is zero in the first period...
        for i in range(n):
            for j in range(m):
                model.Add(x[i, j, 0, 0] == 1)

        # ...and matches y in the final period
        for i in range(n):
            for j in range(m):
                for k in range(nb_colors):
                    model.Add(x[i, j, k, nb_periods - 1] == y[i, j, k])

        return x, y

    def __add_objective(self) -> None:
        """
        Add the objective to the optimization model.
        """
        self.model.Maximize(
            sum(
                self.city.scores[k] * self.y[i, j, k]
                for i in range(self.city.n)
                for j in range(self.city.m)
                for k in range(self.city.nb_colors)
            )
        )

    def __add_constraints(
        self,
        model: cp_model.CpModel,
        x: dict,
        n: int,
        m: int,
        nb_colors: int,
        nb_periods: int
    ) -> None:
        """
        Add necessary constraints to the optimization model.

        Args:
            model (cp_model.CpModel): CP-SAT model.
            x (dict): shorthand for self.x
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
            nb_colors (int): shorthand for self.city.nb_colors
            nb_periods (int): shorthand for self.nb_periods
        """

        # Going back in time, maintain 0-towers
        for i in range(n):
            for j in range(m):
                for s, t in zip(range(nb_periods), range(1, nb_periods)):
                    model.Add(
                        x[i, j, 0, s] >= x[i, j, 0, t]
                    )

        # Going back in time, maintain towers or reduce to 0
        for i in range(n):
            for j in range(m):
                for s, t in zip(range(nb_periods), range(1, nb_periods)):
                    for k in range(1, nb_colors):
                        model.Add(
                            x[i, j, 0, s] + x[i, j, k, s] >= x[i, j, k, t]
                        )

        # Going back in time, maintain towers that don't have 0-neighbors
        for i in range(n):
            for j in range(m):
                for s, t in zip(range(nb_periods), range(1, nb_periods)):
                    for k in range(1, nb_colors):
                        model.Add(
                            x[i, j, k, s] >= x[i, j, k, t] - sum(
                                x[p, q, 0, t] for p, q in self.city.neighbors(i, j)
                            )
                        )

        # Going back in time, maintain a-towers if for any threshold (k-1) < a
        # there are too many towers b >= k that do not contribute to its reduction.
        # Example for a tower of color 3 (a=3) with four neighbors using threshold 1 (k=2):
        #   Maintain this 3-tower if three or more of its neighbors have color >= 2.
        #   To reduce the 3-tower, it needs at least one neighbor of color 0,
        #   so if three neighbors have color >= 2, then no 1-tower is available for the reduction.
        for i in range(n):
            for j in range(m):
                neighbors = self.city.neighbors(i, j)
                for s, t in zip(range(nb_periods), range(1, nb_periods)):
                    for k in range(2, nb_colors):
                        subset_size = len(neighbors) + 1 - k
                        if subset_size < 0:
                            continue  # handle edge case when len(neighbors) = 1
                        for subset in it.combinations(neighbors, subset_size):
                            for a in range(k, nb_colors):
                                model.Add(
                                    x[i, j, a, s] >= x[i, j, a, t] + sum(
                                        x[p, q, b, t]
                                        for b in range(k, nb_colors)
                                        for p, q in subset
                                    ) - subset_size
                                )

        # Correction to forbid neighbors 0/1/1 to reduce 3-towers,
        # which is not captured by the threshold rule above.
        if nb_colors >= 4:
            for i in range(n):
                for j in range(m):
                    neighbors = self.city.neighbors(i, j)
                    if len(neighbors) < 3:
                        continue
                    subset_size = len(neighbors) - 1
                    for s, t in zip(range(nb_periods), range(1, nb_periods)):
                        for subset in it.combinations(neighbors, subset_size):
                            model.Add(
                                x[i, j, 3, s] >= x[i, j, 3, t] + sum(
                                    x[p, q, k, t]
                                    for k in [1, 3]
                                    for p, q in subset
                                ) - subset_size
                            )

    def __add_redundant_constraints(
        self,
        model: cp_model.CpModel,
        x: dict,
        y: dict,
        n: int,
        m: int,
        nb_colors: int,
        nb_periods: int
    ) -> None:
        """
        Add redundant constraints to speed up the solver.

        Args:
            model (cp_model.CpModel): CP-SAT model.
            x (dict): shorthand for self.x
            y (dict): shorthand for self.y
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
            nb_colors (int): shorthand for self.city.nb_colors
            nb_periods (int): shorthand for self.nb_periods
        """

        # If towers of color k score less than 0-towers, then 0-towers are preferred
        for k in range(1, nb_colors):
            if self.city.scores[k] <= self.city.scores[0]:
                for i in range(n):
                    for j in range(m):
                        for t in range(nb_periods):
                            model.Add(x[i, j, k, t] == 0)

        # Remove colors that have an insufficient number of neighbors to ever be reduced
        for i in range(n):
            for j in range(m):
                for k in range(nb_colors):
                    if k > len(self.city.neighbors(i, j)):
                        for t in range(nb_periods):
                            model.Add(x[i, j, k, t] == 0)

        # Forbid two neighbors with three neighbors each to both take on color 3
        if nb_colors >= 4:
            three_neighbor_pairs = set()
            for i in range(n):
                for j in range(m):
                    neighbors = self.city.neighbors(i, j)
                    if len(neighbors) == 3:
                        for p, q in neighbors:
                            if len(self.city.neighbors(p, q)) == 3:
                                pair = tuple(sorted([(i, j), (p, q)]))
                                three_neighbor_pairs.add(pair)
            for t in range(nb_periods):
                for neighbor1, neighbor2 in three_neighbor_pairs:
                    i, j = neighbor1
                    p, q = neighbor2
                    model.Add(x[i, j, 3, t] + x[p, q, 3, t] <= 1)

        # Forbid 2x2 squares of 3-towers
        if nb_colors >= 4:
            for t in range(nb_periods):
                for i in range(1, n-2):
                    for j in range(1, m-2):
                        model.Add(
                            sum(
                                x[i + delta_i, j + delta_j, 3, t]
                                for delta_i in [0, 1]
                                for delta_j in [0, 1]
                            ) <= 3
                        )

        # At least one 0-tower
        for t in range(nb_periods):
            model.Add(
                sum(
                    x[i, j, 0, t]
                    for i in range(n)
                    for j in range(m)
                ) >= 1
            )
