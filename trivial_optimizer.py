import city
import configuration


class TrivialOptimizer:
    """
    Trivial optimizer that returns a configuration with only towers of color 0.
    """

    def __init__(self, city: city.City) -> None:
        self.city = city

    def run(self) -> tuple[configuration.Configuration, dict]:
        solution = configuration.Configuration(self.city)
        info = {
            "optimal": False
        }
        return solution, info
