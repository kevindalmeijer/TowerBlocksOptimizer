import solver
import configuration
from ortools.sat.python import cp_model
import warnings
import itertools as it


class YellowCPOptimizer:
    """
    Optimizer based on constraint-programming solver CP-SAT.
    As opposed to CPOptimizer, only maximizes the number of
    3-towers/yellow towers. That is, city.scores = [0, 0, 0, 1].
    """

    def __init__(self, solver: solver.Solver, settings: dict = {}) -> None:
        """
        Initialize the YellowCPOptimizer object and check the settings provided by the user.

        Args:
            solver (solver.Solver): Solver for which the optimizer is called.
            settings (dict): Dictionary of user-provided parameters and values.
                See __check_user_settings() for details.

        Raises:
            ValueError: If city.nb_colors != 4 or city.scores != [0, 0, 0, 1].
        """
        self.solver = solver
        self.city = solver.city

        if self.city.nb_colors != 4:
            raise ValueError(f"Number of colors {self.city.nb_colors} must be equal to 4.")
        if self.city.scores != [0, 0, 0, 1]:
            raise ValueError(f"Scores {self.city.scores} must be equal to [0, 0, 0, 1].")

        self.settings = settings
        self.__check_user_settings()

        self.max_distance = self.city.n * self.city.m - 1  # TODO: can this be lowered?
        self.__build_model()

    def __check_user_settings(self) -> None:
        """
        Check the settings provided by the user and give a warning for parameters that are not recognized.
        """
        parameters = [
            "time_limit",               # time limit in seconds (default: no limit)
            "print_log",                # print the CP-SAT log (default: False)
            "prioritize_feasibility",   # generates more feasible solutions but may slow optimality (default: True)
            "suboptimality_cuts",       # add cuts that remove suboptimal solutions (default: False)
        ]
        for parameter in self.settings:
            if parameter not in parameters:
                warnings.warn(f"'{parameter}' is not a recognized parameter and will be ignored.", UserWarning)

        if "prioritize_feasibility" not in self.settings:
            self.settings["prioritize_feasibility"] = True
        if "suboptimality_cuts" not in self.settings:
            self.settings["suboptimality_cuts"] = False

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
        info["optimal"] = (status == 4)  # CP-SAT reports optimality

        return solution, info

    def get_solution_towers(self) -> list[list[int]]:
        """
        Get the tower placements found by the solver as a double array.

        Returns:
            list: Best found tower placements as a double array.
        """
        solution = [
            [
                3 if self.cp_solver.Value(self.z[i, j]) == 1 else 0
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

        self.model = cp_model.CpModel()
        self.cp_solver = cp_model.CpSolver()

        self.__set_solver_settings()
        self.d, self.v, self.z = self.__define_variables(self.model, n, m)
        self.__add_objective()
        self.__add_constraints(self.model, self.d, self.v, self.z, n, m)
        self.__add_redundant_constraints(self.model, self.d, self.v, self.z, n, m)

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
    ) -> tuple[dict, dict, dict]:
        """
        Define variables and basic constraints for the optimization model.

        Args:
            model (cp_model.CpModel): CP-SAT model.
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m

        Returns:
            tuple(dict, dict, dict): dictionaries for variables d, v, z
        """

        # Variable z[i, j] == 1 indicates a 3-tower at location (i, j),
        # while z[i, j] == 0 indicates a 0-tower.
        z = {
            (i, j):
                model.NewBoolVar(f"z_{i}_{j}")
            for i in range(n)
            for j in range(m)
        }

        # For all 0-towers, d[i ,j] indicates the minimum number of steps
        # to go from (0, 0) to (i, j) while visiting only 0-towers
        # and moving like a chess king (i.e., using city.extended_neighbors).
        d = {
            (i, j):
                model.NewIntVar(0, self.max_distance, f"d{i}_{j}")
            for i in range(n)
            for j in range(m)
        }

        # To calculate the minimum distance defined above, each 0-tower
        # will point to an extended neighbor with a lower distance.
        # Variable v[i, j, p, q] == 1 if (i, j) points to predecessor (p, q)
        # or 0 otherwise.
        v = {
            (i, j, p, q):
                model.NewBoolVar(f"v{i}_{j}_{p}_{q}")
                for i in range(n)
                for j in range(m)
                if (i, j) != (0, 0)
                for p, q in self.city.extended_neighbors(i, j)
        }

        return d, v, z

    def __add_objective(self) -> None:
        """
        Add the objective to the optimization model.
        """
        self.model.Maximize(
            sum(
                self.city.scores[3] * self.z[i, j]
                for i in range(self.city.n)
                for j in range(self.city.m)
            )
        )

    def __add_constraints(
        self,
        model: cp_model.CpModel,
        d: dict,
        v: dict,
        z: dict,
        n: int,
        m: int,
    ) -> None:
        """
        Add necessary constraints to the optimization model.

        Args:
            model (cp_model.CpModel): CP-SAT model.
            d (dict): shorthand for self.d
            v (dict): shorthand for self.v
            z (dict): shorthand for self.z
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
        """

        # Forbid 3-towers when the number of neighbors is insufficient (corners)
        for i in range(n):
            for j in range(m):
                if len(self.city.neighbors(i, j)) < 3:
                    model.Add(z[i, j] == 0)

        # Forbid 3-towers next to eachother when the number of neighbors in insufficient (edges)
        def three_neighbors(row: int, col: int) -> bool:
            return len(self.city.neighbors(row, col)) == 3

        non_corner_edge_pairs = set()
        for i in range(n):
            for j in range(m):
                if three_neighbors(i, j):
                    for p, q in self.city.neighbors(i, j):
                        if three_neighbors(p, q):
                            pair = tuple(sorted([(i, j), (p, q)]))
                            non_corner_edge_pairs.add(pair)

        for neighbor1, neighbor2 in non_corner_edge_pairs:
            i, j = neighbor1
            p, q = neighbor2
            model.Add(z[i, j] + z[p, q] <= 1)

        # Forbid 2x2 squares of 3-towers by forcing at least one 0-tower
        for i in range(1, n-2):
            for j in range(1, m-2):
                model.AddAtLeastOne(
                    z[p, q].Not()
                    for p in [i, i + 1]
                    for q in [j, j + 1]
                )

        # Tower is either a 3-tower, or it has to select one predecessor
        for i in range(n):
            for j in range(m):
                if (i, j) != (0, 0):
                    model.AddExactlyOne(
                        it.chain(
                            (v[i, j, p, q] for p, q in self.city.extended_neighbors(i, j)),
                            (z[i, j],)
                        )
                    )

        # Predecessor must be a 0-tower
        for i in range(n):
            for j in range(m):
                if (i, j) != (0, 0):
                    for p, q in self.city.extended_neighbors(i, j):
                        model.Add(
                            v[i, j, p, q] == 0
                        ).OnlyEnforceIf(z[p, q])

        # Calculate distances
        for i in range(n):
            for j in range(m):
                if (i, j) != (0, 0):
                    for p, q in self.city.extended_neighbors(i, j):
                        if self.settings["prioritize_feasibility"]:
                            model.Add(
                                d[i, j] >= d[p, q] + 1
                            ).OnlyEnforceIf(v[i, j, p, q])
                        else:
                            model.Add(
                                d[i, j] == d[p, q] + 1
                            ).OnlyEnforceIf(v[i, j, p, q])

    def __add_redundant_constraints(
        self,
        model: cp_model.CpModel,
        d: dict,
        v: dict,
        z: dict,
        n: int,
        m: int,
    ) -> None:
        """
        Add redundant constraints to speed up the solver.

        Args:
            model (cp_model.CpModel): CP-SAT model.
            d (dict): shorthand for self.d
            v (dict): shorthand for self.v
            z (dict): shorthand for self.z
            n (int): shorthand for self.city.n
            m (int): shorthand for self.city.m
        """
        pass

        # Distance at (0, 0) is zero
        model.Add(d[0, 0] == 0)

        # Only 0-towers have distance values
        for i in range(n):
            for j in range(m):
                if (i, j) != (0, 0):
                    model.Add(
                        d[i, j] == 0
                    ).OnlyEnforceIf(z[i, j])

        # Each row has at least one 0-tower
        for i in range(n):
            model.AddAtLeastOne(
                z[i, j].Not()
                for j in range(m)
            )

        # Each column has at least one 0-tower
        for j in range(m):
            model.AddAtLeastOne(
                z[i, j].Not()
                for i in range(n)
            )

        # It is suboptimal for a 0-towers to have three 0-tower neighbors (suboptimality cut)
        if self.settings["suboptimality_cuts"]:
            for i in range(n):
                for j in range(m):
                    model.Add(
                        sum(
                            z[p, q]
                            for p, q in self.city.neighbors(i, j)
                        ) >= 2
                    ).OnlyEnforceIf(z[i, j].Not())
