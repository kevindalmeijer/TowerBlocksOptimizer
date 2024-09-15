import solver
import configuration
import gurobipy as gp
from gurobipy import GRB
import warnings


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
                """
                self.optimizer = optimizer

            def __call__(self, model: gp.Model, where: int):
                """
                Callback entry point.

                Args:
                    model (gp.Model): the calling model.
                    where (int): indicator where the callback is called from.
                """
                if where == GRB.Callback.MIPSOL:

                    optimizer = self.optimizer
                    solver = optimizer.solver
                    city = optimizer.city

                    # extract current solution
                    solution = optimizer.get_solution_towers(in_callback=True)
                    config = configuration.Configuration(self.optimizer.city)
                    config.towers = solution

                    # find a conflict and add a cut to forbid it
                    conflict, _moves = solver.get_reduced_configuration(config)
                    if not conflict.all_zero():
                        lhs = gp.quicksum(
                            optimizer.y[i, j, conflict.towers[i][j]]
                            for i in range(city.n)
                            for j in range(city.m)
                            if conflict.towers[i][j] != 0
                        )
                        rhs = lhs.size() - 1
                        model.cbLazy(lhs <= rhs)

        return Callback(self)

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
