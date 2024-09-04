import city
import solver
import cp_optimizer
import pprint

my_city = city.City(5, 5, scores=[205, 966, 2677, 5738])
my_solver = solver.Solver(my_city)
my_optimizer = cp_optimizer.ConstraintProgrammingOptimizer(my_city)

solution, info = my_solver.solve(my_optimizer)
pprint.pprint(info)
print(
    f"Solution with total score {info['total_score']} (optimal={info['optimal']})" +
    f"obtained in {len(info["moves"])} moves:"
)
print(solution)
