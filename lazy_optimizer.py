import solver
import configuration
import gurobipy as gp
from gurobipy import GRB
import warnings
import copy


class LazyOptimizer:
    """
    Optimizer based on lazy constraint generation with Mixed Integer Programming solver Gurobi.
    Requires a Gurobi license to run.
    """

    def __init__(self, solver: solver.Solver, settings: dict = {}) -> None:
        """
        Initialize the LazyOptimizer object and check the settings provided by the user.

        Args:
            solver (solver.Solver): Solver for which the optimizer is called.
            settings (dict): Dictionary of user-provided parameters and values.
                See __check_user_settings() for details.
        """
        self.solver = solver
        self.city = solver.city
        self.settings = settings
        self.__check_user_settings()
        self.__build_model()

    def __check_user_settings(self) -> None:
        """
        Check the settings provided by the user and give a warning for parameters that are not recognized.
        """
        parameters = [
            "time_limit",   # time limit in seconds (default: no limit)
            "print_log",    # print the Gurobi log (default: False)
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
        self.model.optimize(self.callback)
        status = self.model.status

        solution = configuration.Configuration(self.city)
        solution.towers = self.get_solution_towers()

        info = dict()

        # Solution is optimal if...
        info["optimal"] = (status == GRB.Status.OPTIMAL)  # ...Gurobi reports optimality

        return solution, info

    def get_solution_towers(self, in_callback: bool = False) -> list[list[int]]:
        """
        Get the tower placements found by the solver as a double array.

        Args:
            in_callback (bool): If called from a Gurobi callback. Defaults to False.

        Returns:
            list: Best found tower placements as a double array.
        """
        solution = [
            [
                sum(
                    round(
                        self.y[i, j, k].x if not in_callback
                        else self.model.cbGetSolution(self.y[i, j, k])
                    ) * k
                    for k in range(self.city.nb_colors)
                )
                for j in range(self.city.m)
            ]
            for i in range(self.city.n)
        ]
        return solution

    def __build_model(self) -> None:
        """
        Build the mixed integer programming model.
        """
        n = self.city.n
        m = self.city.m
        nb_colors = self.city.nb_colors

        self.env = gp.Env()
        self.model = gp.Model(env=self.env)

        self.__set_solver_settings()
        self.y = self.__define_variables(self.model, n, m, nb_colors)
        self.callback = self.__get_callback()
        self.__add_valid_inequalities(self.model, self.y, n, m, nb_colors)

    def __set_solver_settings(self) -> None:
        """
        Set solver settings based on the settings provided at initialization.
        """
        self.model.Params.LazyConstraints = 1  # required to use lazy constraints

        if "time_limit" in self.settings:
            self.model.setParam(GRB.Param.TimeLimit, self.settings['time_limit'])
        if "print_log" in self.settings:
            if not self.settings["print_log"]:
                self.model.setParam(GRB.Param.OutputFlag, 0)

    def __define_variables(
        self,
        model: gp.Model,
        n: int,
        m: int,
        nb_colors: int,
    ) -> tuple[dict, dict]:
        """
        Define variables and basic constraints for the optimization model.

        Args:
            model (gp.Model): Gurobi model.
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
            nb_colors (int): shorthand for self.city.nb_colors

        Returns:
            dict: variables y.
        """

        # Variables y represent the final configuration
        y = {
            (i, j, k):
                model.addVar(
                    vtype=GRB.BINARY,
                    name=f"y_{i}_{j}_{k}",
                    obj=self.city.scores[k]
                )
            for i in range(n)
            for j in range(m)
            for k in range(nb_colors)
        }
        model.setAttr("ModelSense", -1)  # maximize score

        # Assign one color to each tower
        for i in range(n):
            for j in range(m):
                model.addConstr(gp.quicksum(y[i, j, k] for k in range(nb_colors)) == 1)

        return y

    def __get_callback(self):
        """
        Prepare a callback to be used by Gurobi for lazy constraint generation.

        Returns:
            Callback: callback object.
        """
        class Callback:

            def __init__(self, optimizer: LazyOptimizer) -> None:
                """
                Initialize the callback with a reference to the containing class.

                Args:
                    optimizer (LazyOptimizer): reference to the containing class.
                """
                self.optimizer = optimizer

            def __call__(self, model: gp.Model, where: int) -> None:
                """
                Callback entry point: find a conflict if one exists, and add
                a lazy constraint to prevent it.

                Args:
                    model (gp.Model): the calling model.
                    where (int): indicator where the callback is called from.
                """
                if where == GRB.Callback.MIPSOL:  # integer solution found

                    optimizer = self.optimizer
                    solver = optimizer.solver
                    city = optimizer.city

                    # Extract current solution
                    config = configuration.Configuration(city)
                    config.towers = optimizer.get_solution_towers(in_callback=True)

                    # Find conflict opportunistically (fast but not guaranteed)
                    conflict = optimizer.get_opportunistic_minimal_conflict(config)

                    # If no conflict is found, try again rigorously (slow but guaranteed)
                    if conflict.all_zero():
                        conflict, _moves = solver.get_reduced_configuration(config)
                        if conflict.all_zero():
                            return  # no conflict found

                    # Strengthen conflict by replacing 3-towers by 2-towers where possible
                    optimizer.strengthen_conflict(conflict)

                    # Add a cut to forbid the conflict
                    lhs = gp.quicksum(
                        optimizer.y[i, j, color]
                        for i in range(city.n)
                        for j in range(city.m)
                        if conflict.towers[i][j] != 0
                        for color in {conflict.towers[i][j], 3}  # Add color 3 to the lhs...
                        # ...this is allowed because changing a tower to 3 never resolves the conflict.
                        # It is mandatory when strengthen_conflict() is used to ensure the current solution is cut off.
                        if color < city.nb_colors
                    )
                    rhs = conflict.nb_nonzero() - 1
                    model.cbLazy(lhs <= rhs)

        return Callback(self)

    def get_opportunistic_minimal_conflict(self, config: configuration.Configuration) -> configuration.Configuration:
        """
        Get a minimal conflict by reducing towers opportunistically (see __apply_opportunistic_reduction()).
        A conflict is a configuration in which the non-0 tower positions cannot be reached with valid moves.
        This function either returns:
        - a configuration with only 0-towers: no conflict could be found opportunistically,
            but a conflict may still exist; or
        - a conflict that is minimal in the sense that changing any non-zero tower to zero would allow an
            opportunistic reduction to the all-0 configuration (i.e., would remove the conflict). The conflict
            is guaranteed to be smallest locally (minimal) but is not guaranteed to be the smallest globally (minimum).

        Maintains a last_conflict, which is guaranteed to be an opportunistic conflict (i.e., it cannot be fully
        reduced by opportunistic reductions), and a current_config, which may or may not contain a conflict.
        At every step, one of the non-zero towers in the current_config is changed to zero, and it is checked
        if the opportunistic conflict remains. If so, last_conflict is updated, else current_config is reset
        to the last_conflict.

        Every tower is only considered once: either it can be changed to zero without removing the conflict,
        and last_conflict is updated, or changing the tower removes the conflict. And if it removes the conflict
        now, it will also remove the conflict after more towers have been reduced. Hence, towers do not
        need to be reconsidered. Towers can be considered in any order, but the current implementation considers
        lower colors first, as this seems to lead to smaller conflicts made of high-colored towers.

        Args:
            config (configuration.Configuration): The configuration to start from -- will not be modified.

        Returns:
            configuration.Configuration: The opportunistic minimal conflict,
                or the all-0 configuration if no conflict was found.
        """

        # Prepare last_conflict and current_config
        current_config = copy.deepcopy(config)
        self.__apply_opportunistic_reductions(current_config)
        if current_config.all_zero():
            return current_config  # current_config does not contain an opportunistic conflict
        last_conflict = copy.deepcopy(current_config)  # guaranteed to contain an opportunistic conflict

        # Consider the towers in order of color
        for color in range(1, self.city.nb_colors):
            for row in range(self.city.n):
                for col in range(self.city.m):

                    if last_conflict.towers[row][col] != color:
                        continue

                    # See if the conflict remains after changing (row, col) to 0
                    current_config.place_tower(row, col, 0)
                    self.__apply_opportunistic_reductions(current_config)

                    if current_config.all_zero():
                        # No opportunistic conflict: reset to last_conflict
                        current_config = copy.deepcopy(last_conflict)
                    else:
                        # An opportunistic conflict remains: update last_conflict
                        last_conflict = copy.deepcopy(current_config)

        return last_conflict

    def __apply_opportunistic_reductions(self, config: configuration.Configuration) -> None:
        """
        Apply as many opportunistic reductions to the given configuration as possible (modifying the input).

        Args:
            config (configuration.Configuration): The configuration to start from -- will be modified!
        """
        change_made = True
        while change_made:
            change_made = False
            for row in range(self.city.n):
                for col in range(self.city.m):
                    modified = self.__apply_opportunistic_reduction(config, row, col)
                    if modified:
                        change_made = True
        return

    def __apply_opportunistic_reduction(self, config: configuration.Configuration, row: int, col: int) -> bool:
        """
        Opportunistically reduce the color of the tower at position (row, col) to zero.
        If the reduction is successful, config is updated to the reduced configuration, and the value True is returned.
        If no opport reduction is possible, the value False is returned.

        An opportunistic reduction looks at whether the number of 0-towers is sufficient for the necessary promotions,
        but it is not verified whether these promotions are safe (compare to Solver.__apply_safe_reduction()).

        Args:
            config (configuration.Configuration): The configuration to start from -- will be modified!
            row (int): The row index of the tower to be reduced.
            col (int): The column index of the tower to be reduced.

        Returns:
            bool: True if config was modified, False otherwise.
        """
        color = config.towers[row][col]
        if color == 0:
            return False  # tower is already color 0

        neighbor_counts = config.neighbor_counts(row, col)
        nb_promotions_needed = sum(
            neighbor_count == 0  # neighbor is missing, so a promotion is needed
            for neighbor_count in neighbor_counts[1:color]
        )
        nb_promotions_available = neighbor_counts[0] - 1  # -1 to maintain at least one neighbor with color 0

        if nb_promotions_needed <= nb_promotions_available:
            config.place_tower(row, col, 0)
            return True
        else:
            return False

    def strengthen_conflict(self, conflict: configuration.Configuration) -> None:
        """
        Strenghtens a conflict by replacing 3-towers with 2-towers in a way that maintains an opportunistic
        conflict (see get_opportunistic_minimal_conflict()). A conflict is a configuration in which the
        non-0 tower positions cannot be reached with valid moves. If the conflict cannot be strengthened
        (or fails to be an opportunistic conflict), the input is not modified.

        Note:
            Cutting off a strengthened conflict requires special attention, see the comments in Callback.__call__().

        Args:
            conflict (configuration.Configuration): The conflict to start from -- will be modified!
                The all-zero configuration is a valid input and will not be modified.
        """
        for row in range(self.city.n):
            for col in range(self.city.m):

                if conflict.towers[row][col] != 3:
                    continue

                # Check if the conflict remains after changing (row, col) to 2
                next_conflict = copy.deepcopy(conflict)
                next_conflict.place_tower(row, col, 2)
                self.__apply_opportunistic_reductions(next_conflict)

                if not next_conflict.all_zero():
                    # An opportunistic conflict remains: make the same change to conflict
                    conflict.place_tower(row, col, 2)

        return

    def __add_valid_inequalities(
        self,
        model: gp.Model,
        y: dict,
        n: int,
        m: int,
        nb_colors: int,
    ) -> None:
        """
        Add valid inequalities to speed up the solver.

        Args:
            model (gp.Model): Gurobi model.
            y (dict): shorthand for self.y
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
            nb_colors (int): shorthand for self.city.nb_colors
        """

        # If towers of color k score less than 0-towers, then 0-towers are preferred
        for k in range(1, nb_colors):
            if self.city.scores[k] <= self.city.scores[0]:
                for i in range(n):
                    for j in range(m):
                        model.addConstr(y[i, j, k] == 0)

        # Remove colors that have an insufficient number of neighbors to ever be reduced
        for i in range(n):
            for j in range(m):
                for k in range(nb_colors):
                    if k > len(self.city.neighbors(i, j)):
                        model.addConstr(y[i, j, k] == 0)

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
            for neighbor1, neighbor2 in three_neighbor_pairs:
                i, j = neighbor1
                p, q = neighbor2
                model.addConstr(y[i, j, 3] + y[p, q, 3] <= 1)

        # Forbid 2x2 squares of 3-towers
        if nb_colors >= 4:
            for i in range(1, n-2):
                for j in range(1, m-2):
                    model.addConstr(
                        gp.quicksum(
                            y[i + delta_i, j + delta_j, 3]
                            for delta_i in [0, 1]
                            for delta_j in [0, 1]
                        ) <= 3
                    )

        # At least one 0-tower
        model.addConstr(
            gp.quicksum(
                y[i, j, 0]
                for i in range(n)
                for j in range(m)
            ) >= 1
        )
