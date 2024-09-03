import city
import configuration
import solver

my_city = city.City(5, 5)

config = configuration.Configuration(my_city)
config.towers = [
    [2, 3, 2, 3, 0],
    [3, 1, 3, 2, 3],
    [2, 3, 3, 3, 1],
    [3, 2, 3, 1, 3],
    [1, 3, 1, 3, 2]
]

my_solver = solver.Solver(my_city)
moves = my_solver.get_moves(config)

config = configuration.Configuration(my_city)
print(config)
for move in moves:
    config.place_tower(*move)
    print()
    print(config)

print()
print(f"number of moves: {len(moves)}")
