import solver
import configuration


class TrivialOptimizer:
    """
    Trivial optimizer that returns a configuration with only towers of color 0.
    """

    def __init__(self, solver: solver.Solver) -> None:
        self.solver = solver
        self.city = solver.city

    def run(self) -> tuple[configuration.Configuration, dict]:
        solution = configuration.Configuration(self.city)
        info = {
            "optimal": False
        }
        return solution, info
