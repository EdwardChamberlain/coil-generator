import math
from dataclasses import dataclass

import matplotlib.axes
import matplotlib.patches
import matplotlib.path
import matplotlib.pyplot

ARC_DIRECTION_ALIASES = {
    "clockwise": "clockwise",
    "cw": "clockwise",
    "counterclockwise": "counterclockwise",
    "counter-clockwise": "counterclockwise",
    "counter_clockwise": "counterclockwise",
    "ccw": "counterclockwise",
}


@dataclass
class LineSegment:
    start_position: tuple
    end_position: tuple

    @property
    def length(self):
        return math.sqrt((self.end_position[0] - self.start_position[0]) ** 2 +
                         (self.end_position[1] - self.start_position[1]) ** 2)

    def plot(self, line_width: float, axis: matplotlib.axes.Axes | None = None) -> matplotlib.patches.PathPatch:
        if axis is None:
            axis = matplotlib.pyplot.gca()

        line_path = matplotlib.path.Path(
            vertices=[self.start_position, self.end_position],
            codes=[matplotlib.path.Path.MOVETO, matplotlib.path.Path.LINETO],
        )
        line_patch = matplotlib.patches.PathPatch(
            line_path,
            fill=False,
            edgecolor="black",
            linewidth=line_width,
            capstyle="round",
            joinstyle="round",
        )
        axis.add_patch(line_patch)
        return line_patch


@dataclass
class ArcSegment:
    center: tuple
    radius: float
    start_angle: float  # in degrees
    end_angle: float  # in degrees
    direction: str = "counterclockwise"

    def __post_init__(self):
        normalized_direction = ARC_DIRECTION_ALIASES.get(self.direction.lower())
        if normalized_direction is None:
            raise ValueError("direction must be 'clockwise' or 'counterclockwise'.")
        self.direction = normalized_direction

    @property
    def length(self):
        return math.radians(self._sweep_angle()) * self.radius

    def plot(self, line_width: float, axis: matplotlib.axes.Axes | None = None) -> matplotlib.patches.Arc:
        if axis is None:
            axis = matplotlib.pyplot.gca()

        theta1, theta2 = self._matplotlib_angle_limits()
        arc_patch = matplotlib.patches.Arc(
            xy=self.center,
            width=2 * self.radius,
            height=2 * self.radius,
            angle=0,
            theta1=theta1,
            theta2=theta2,
            linewidth=line_width,
            color="black",
            capstyle="round",
        )
        axis.add_patch(arc_patch)
        return arc_patch

    def _sweep_angle(self):
        if self.direction == "clockwise":
            return (self.start_angle - self.end_angle) % 360
        return (self.end_angle - self.start_angle) % 360

    def _matplotlib_angle_limits(self):
        sweep_angle = self._sweep_angle()
        if self.direction == "clockwise":
            return self.end_angle, self.end_angle + sweep_angle
        return self.start_angle, self.start_angle + sweep_angle


class Coil:
    def __init__(self, outer_radius, inner_radius, number_of_coils=9):
        self.radius_outer = outer_radius  # mm
        self.radius_inner = inner_radius  # mm
        self.number_of_coils = number_of_coils

        self.angular_width = 360 / self.number_of_coils  # DEG
        self.geometry = []

    def print(self):
        print(f"Outer Radius: {self.radius_outer} mm")
        print(f"Inner Radius: {self.radius_inner} mm")
        print(f"Number of Coils: {self.number_of_coils}")
        print(f"Angular Width per Coil: {self.angular_width} degrees")

    def _add_geometry(self, geometry):
        self.geometry.append(geometry)

    @staticmethod
    def polar_to_cartesian(radius, angle_degrees):
        angle_radians = math.radians(angle_degrees)
        x = radius * math.cos(angle_radians)
        y = radius * math.sin(angle_radians)
        return (x, y)

    @staticmethod
    def arclength_to_angle(radius, arc_length):
        return math.degrees(arc_length / radius)

    def build_coil(self):
        SPACING = 0.5
        for i in range(10):
            j = max((i - 1), 0)
            outer_radius = self.radius_outer - i * SPACING
            inner_radius = self.radius_inner + i * SPACING
            next_outer_radius = self.radius_outer - (i + 1) * SPACING
            outer_start_angle = -self.angular_width / 2 + self.arclength_to_angle(outer_radius, SPACING) * j
            outer_end_angle = self.angular_width / 2 - self.arclength_to_angle(outer_radius, SPACING) * i
            inner_start_angle = self.angular_width / 2 - self.arclength_to_angle(inner_radius, SPACING) * i
            inner_end_angle = -self.angular_width / 2 + self.arclength_to_angle(inner_radius, SPACING) * i
            next_outer_end_angle = -self.angular_width / 2 + self.arclength_to_angle(next_outer_radius, SPACING) * i
            self._add_geometry(
                ArcSegment(
                    center=(0, 0),
                    radius=outer_radius,
                    start_angle=outer_start_angle,
                    end_angle=outer_end_angle,
                    direction="counterclockwise",
                )
            )
            self._add_geometry(
                LineSegment(
                    start_position=self.polar_to_cartesian(outer_radius, outer_end_angle),
                    end_position=self.polar_to_cartesian(inner_radius, inner_start_angle),
                )
            )
            self._add_geometry(
                ArcSegment(
                    center=(0, 0),
                    radius=inner_radius,
                    start_angle=inner_start_angle,
                    end_angle=inner_end_angle,
                    direction="clockwise",
                )
            )
            self._add_geometry(
                LineSegment(
                    start_position=self.polar_to_cartesian(inner_radius, inner_end_angle),
                    end_position=self.polar_to_cartesian(next_outer_radius, next_outer_end_angle),
                )
            )

    def plot(self, line_width: float = 1.0):
        figure, axis = matplotlib.pyplot.subplots()
        for geometry in self.geometry:
            geometry.plot(line_width=line_width, axis=axis)
        axis.set_aspect("equal", adjustable="box")
        axis.autoscale_view()
        return figure, axis


if __name__ == "__main__":
    coil = Coil(outer_radius=20, inner_radius=10, number_of_coils=9)
    coil.print()
    coil.build_coil()
    coil.plot(line_width=1.0)
    matplotlib.pyplot.show()
