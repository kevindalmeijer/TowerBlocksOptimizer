import city
import solver
import cp_optimizer
import lazy_optimizer
import visualizer
import pprint

height = 5
width = 5
scores = [205, 966, 2677, 5738]

method = 0
settings = {
    'print_log': True,
    # 'time_limit': 60,
    # 'depth_limit': 5,
}

my_city = city.City(height, width, scores=scores)
my_solver = solver.Solver(my_city)

if method == 0:
    optimizer = cp_optimizer.CPOptimizer(my_solver, settings)
elif method == 1:
    optimizer = lazy_optimizer.LazyOptimizer(my_solver, settings)  # requires Gurobi license
else:
    raise ValueError(f"Method {method} not recognized.")

solution, info = my_solver.solve(optimizer)
pprint.pprint(info)
print(
    f"Solution with total score {info['total_score']} (optimal={info['optimal']}) " +
    f"obtained in {len(info['moves'])} moves:"
)
print(solution)

viz = visualizer.Visualizer(my_city)
viz.set_configuration(solution)
viz.save_plot(f"{my_city.n}x{my_city.m}.png")

viz = visualizer.Visualizer(my_city)
viz.set_animation(info["moves"])
viz.save_animation(f"{my_city.n}x{my_city.m}_animated.gif")
viz.show()
