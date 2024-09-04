import city
import solver
import pprint

my_city = city.City(5, 5, scores=[205, 966, 2677, 5738])
my_solver = solver.Solver(my_city)

solution, info = my_solver.solve()
print(solution)
pprint.pprint(info)
