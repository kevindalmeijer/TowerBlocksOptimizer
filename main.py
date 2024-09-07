import city
import solver
import cp_optimizer
import visualizer
import pprint

my_city = city.City(5, 5, scores=[205, 966, 2677, 5738])
my_solver = solver.Solver(my_city)

settings = {
    'print_log': True,
}
optimizer = cp_optimizer.CPOptimizer(my_city, settings)

solution, info = my_solver.solve(optimizer)
pprint.pprint(info)
print(
    f"Solution with total score {info['total_score']} (optimal={info['optimal']}) " +
    f"obtained in {len(info['moves'])} moves:"
)
print(solution)

viz = visualizer.Visualizer(my_city)
viz.set_animation(info["moves"])
viz.save_animation(f"{my_city.n}x{my_city.m}_animated.gif")
viz.show()
