import city
import configuration
from ortools.sat.python import cp_model
import itertools as it


class ConstraintProgrammingOptimizer:
    """
    Optimizer based on constraint-programming solver CP-SAT.
    """

    def __init__(self, city: city.City) -> None:
        self.city = city

    def run(self) -> tuple[configuration.Configuration, dict]:
        
        height = self.city.n
        width = self.city.m
        nb_colors = self.city.nb_colors
        nb_periods = height * width
        weights = self.city.scores        
        
        neighbors = tuple(
            tuple(
                tuple(
                    {*{(k,j) for k in [i-1, i+1] if k >= 0 and k < height},
                    *{(i,k) for k in [j-1, j+1] if k >= 0 and k < width}}
                )
                for j in range(width)
            )
            for i in range(height)
        )
        
        def get_solution(solver: cp_model.CpSolver):
            solution = [
                [
                    sum(
                        solver.Value(x[i, j, k, 0]) * k
                        for k in range(nb_colors)
                    )
                    for j in range(width)
                ]
                for i in range(height)
            ]
            return solution

        def get_solutions(solver: cp_model.CpSolver):
            solution = [
                [
                    [
                        sum(
                            solver.Value(x[i, j, k, t]) * k
                            for k in range(nb_colors)
                        )
                        for j in range(width)
                    ]
                    for i in range(height)
                ]
                for t in range(nb_periods)
            ]
            return solution
        
        ### CP MODEL ###

        model = cp_model.CpModel()
        solver = cp_model.CpSolver()

        x = {
            (i, j, k, t): model.NewBoolVar("x_{}_{}_{}_{}".format(i, j, k, t))
            for i in range(height)
            for j in range(width)
            for k in range(nb_colors)
            for t in range(nb_periods)
        }

        solver.parameters.log_search_progress = True
        # solver.parameters.max_time_in_seconds = 60

        # Select one color per cell
        for i in range(height):
            for j in range(width):
                for t in range(nb_periods):
                    model.AddExactlyOne(
                        x[i, j, k, t] for k in range(nb_colors)
                    )

        # End at all color zero
        for i in range(height):
            for j in range(width):
                model.Add(x[i, j, 0, nb_periods-1] == True)

        # Objective
        model.Maximize(
            sum(
                weights[k] * x[i, j, k, 0]
                for i in range(height)
                for j in range(width)
                for k in range(nb_colors)
            )
        )

        for i in range(height):
            for j in range(width):
                for t1, t2 in zip(range(nb_periods), range(1, nb_periods)):

                    for k in range(nb_colors):
                        
                        # 1
                        if k == 0:
                            model.Add(x[i, j, 0, t2] >= x[i, j, 0, t1])
                        else:
                            model.Add(x[i, j, 0, t2] + x[i, j, k, t2] >= x[i, j, k, t1])
                        
                        # 2
                        if k != 0:    
                            model.Add(x[i, j, k, t2] >= x[i, j, k, t1] - sum(x[p, q, 0, t1] for p, q in neighbors[i][j]))
                    
                        # 3
                        if k >= 2:
                            nb_neighbors = len(neighbors[i][j])
                            subset_size = nb_neighbors + 1 - k
                            if subset_size < 0:
                                continue  # weird edge case with 1 neighbor
                            for subset in it.combinations(neighbors[i][j], subset_size):
                                for l in range(k, nb_colors):
                                    model.Add(
                                        x[i, j, l, t2] >= sum(
                                            x[p, q, m, t1]
                                            for m in range(k, nb_colors)
                                            for p, q in subset
                                        ) - subset_size + x[i, j, l, t1]
                                    )

                    # 4
                    nb_neighbors = len(neighbors[i][j])
                    if nb_neighbors >= 3:
                        subset_size = nb_neighbors - 1
                        for subset in it.combinations(neighbors[i][j], subset_size):
                            model.Add(
                                x[i, j, 3, t2] >= sum(
                                    x[p, q, k, t1]
                                    for k in [1, 3]
                                    for p, q in subset
                                ) - subset_size + x[i, j, 3, t1]
                            )

        # for i in range(height):
        #     for j in range(width):
        #         for t1, t2 in zip(range(nb_periods), range(1, nb_periods)):
                    
        #             for k in range(1, nb_colors):
                        
        #                 permutation_size = k
        #                 for permutation in it.permutations(neighbors[i][j], permutation_size):
                            
        #                     model.Add(
        #                         x[i, j, 0, t2] >= sum(
        #                             x[permutation[r][0], permutation[r][1], l, t1]
        #                             for r in range(permutation_size)
        #                             for l in set([0, r])
        #                         ) - permutation_size + x[i, j, k, t1]
        #                     )       

        status = solver.Solve(model)
        
        info = dict()
        info["optimal"] = True if status == 4 else False
            
        solutions = get_solutions(solver)
        solution = configuration.Configuration(self.city)
        solution.towers = solutions[0]
        
        return solution, info
