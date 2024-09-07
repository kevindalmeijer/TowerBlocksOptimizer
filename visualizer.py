import city
import configuration
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class Visualizer:
    """
    Class to visualize tower configurations.
    """

    def __init__(self, city: city.City) -> None:
        """
        Initialize the Visualizer object with a plot that represents an empty grid.

        Args:
            city (city.City): City that is visualized.
        """
        self.city = city

        self.fig, self.ax = plt.subplots()
        self.rectangles = {
            (i, j):
                plt.Rectangle(
                    (j, -i), 1, -1,
                    fc='white',
                    ec='black',
                    linewidth=1
                )
            for i in range(city.n)
            for j in range(city.m)
        }
        for i in range(city.n):
            for j in range(city.m):
                self.ax.add_patch(self.rectangles[i, j])

        plt.axis('scaled')
        plt.axis('off')

    def show(self) -> None:
        """
        Show the plot on screen.
        """
        plt.show()

    def set_configuration(self, config: configuration.Configuration) -> None:
        """
        Update the plot to reflect the provided configuration.

        Args:
            config (configuration.Configuration): Tower configuration to be visualized.
        """
        for i, j in self.rectangles:
            color = config.towers[i][j]
            color_code = self.city.color_codes[color]
            self.rectangles[i, j].set_fc(color_code)

    def set_animation(self, moves: list[tuple[int, int, int]], start_empty=False) -> None:
        """
        Update the plot to reflect the provided set of moves.

        Args:
            moves (list[tuple[int, int, int]]): List of moves (row, col, color) to apply.
            start_empty (bool, optional): Start from an empty plot (all white) if True.
                If False, use the default starting point of all 0-towers.
        """
        if start_empty:
            # Add moves to populate from white to 0-towers
            moves = [(i, j, 0) for i in range(self.city.n) for j in range(self.city.m)] + moves

        def update(frame):
            if frame == 0:
                if start_empty:
                    # Reset to white
                    self.__reset_configuration()
                else:
                    # Reset to all 0-towers
                    config = configuration.Configuration(self.city)
                    self.set_configuration(config)
                return
            index = frame - 1
            row, col, color = moves[index]
            color_code = self.city.color_codes[color]
            self.rectangles[row, col].set_facecolor(color_code)
            return

        self.animation = animation.FuncAnimation(
            self.fig,
            update,
            frames=len(moves) + 1,
            repeat=True
        )

    def __reset_configuration(self) -> None:
        """
        Reset to an empty plot (all white)
        """
        for i, j in self.rectangles:
            self.rectangles[i, j].set_fc('white')
