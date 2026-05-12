"""Simple coil geometry primitives."""

from __future__ import annotations

import dataclasses
import math
import pathlib
import typing

if typing.TYPE_CHECKING:
    import matplotlib.axes
    import matplotlib.figure
    import matplotlib.patches

ARC_DIRECTION_ALIASES = {
    "clockwise": "clockwise",
    "cw": "clockwise",
    "counterclockwise": "counterclockwise",
    "counter-clockwise": "counterclockwise",
    "counter_clockwise": "counterclockwise",
    "ccw": "counterclockwise",
}


@dataclasses.dataclass(frozen=True, slots=True)
class CoilPoint:
    """A two-dimensional point in millimetres."""

    x: float
    y: float


PointInput = CoilPoint | tuple[float, float]


@dataclasses.dataclass(frozen=True, slots=True)
class LineSegment:
    """A straight coil segment."""

    start_point: CoilPoint
    end_point: CoilPoint

    @property
    def length(self) -> float:
        """Segment length in millimetres."""

        return math.dist((self.start_point.x, self.start_point.y), (self.end_point.x, self.end_point.y))

    def plot(self, line_width: float, axis: matplotlib.axes.Axes | None = None) -> matplotlib.patches.Polygon:
        """Draw the segment on a matplotlib axis.

        :param line_width: Rendered line width.
        :param axis: Optional existing matplotlib axis.
        """

        import matplotlib.patches
        import matplotlib.pyplot

        if axis is None:
            axis = matplotlib.pyplot.gca()

        length = self.length
        if length <= 0.0:
            raise ValueError("Cannot plot a zero-length line segment.")

        perpendicular_x = -((self.end_point.y - self.start_point.y) / length) * (line_width / 2.0)
        perpendicular_y = ((self.end_point.x - self.start_point.x) / length) * (line_width / 2.0)
        vertices = [
            (self.start_point.x + perpendicular_x, self.start_point.y + perpendicular_y),
            (self.end_point.x + perpendicular_x, self.end_point.y + perpendicular_y),
            (self.end_point.x - perpendicular_x, self.end_point.y - perpendicular_y),
            (self.start_point.x - perpendicular_x, self.start_point.y - perpendicular_y),
        ]
        line_patch = matplotlib.patches.Polygon(
            vertices,
            closed=True,
            facecolor="black",
            edgecolor="black",
            linewidth=0.0,
        )
        axis.add_patch(line_patch)
        return line_patch


@dataclasses.dataclass(frozen=True, slots=True)
class ArcSegment:
    """A circular coil arc."""

    start_point: CoilPoint
    end_point: CoilPoint
    center_point: CoilPoint
    direction: str
    radius: float

    def __post_init__(self) -> None:
        normalized_direction = ARC_DIRECTION_ALIASES.get(self.direction.lower())
        if normalized_direction is None:
            raise ValueError("direction must be 'clockwise' or 'counterclockwise'.")
        object.__setattr__(self, "direction", normalized_direction)

    @property
    def length(self) -> float:
        """Segment length in millimetres."""

        return math.radians(self.sweep_angle_degrees) * self.radius

    @property
    def start_angle_degrees(self) -> float:
        """Start angle relative to the arc centre."""

        return math.degrees(math.atan2(self.start_point.y - self.center_point.y, self.start_point.x - self.center_point.x))

    @property
    def end_angle_degrees(self) -> float:
        """End angle relative to the arc centre."""

        return math.degrees(math.atan2(self.end_point.y - self.center_point.y, self.end_point.x - self.center_point.x))

    @property
    def sweep_angle_degrees(self) -> float:
        """Positive sweep angle in the configured direction."""

        if self.direction == "clockwise":
            return (self.start_angle_degrees - self.end_angle_degrees) % 360.0
        return (self.end_angle_degrees - self.start_angle_degrees) % 360.0

    @property
    def signed_angle_radians(self) -> float:
        """Signed sweep angle in radians."""

        angle_radians = math.radians(self.sweep_angle_degrees)
        if self.direction == "clockwise":
            return -angle_radians
        return angle_radians

    def plot(self, line_width: float, axis: matplotlib.axes.Axes | None = None) -> matplotlib.patches.Wedge:
        """Draw the arc on a matplotlib axis.

        :param line_width: Rendered line width.
        :param axis: Optional existing matplotlib axis.
        """

        import matplotlib.patches
        import matplotlib.pyplot

        if axis is None:
            axis = matplotlib.pyplot.gca()

        theta1, theta2 = self._matplotlib_angle_limits()
        arc_patch = matplotlib.patches.Wedge(
            center=(self.center_point.x, self.center_point.y),
            r=self.radius + (line_width / 2.0),
            theta1=theta1,
            theta2=theta2,
            width=line_width,
            facecolor="black",
            edgecolor="black",
            linewidth=0.0,
        )
        axis.add_patch(arc_patch)
        return arc_patch

    def _matplotlib_angle_limits(self) -> tuple[float, float]:
        if self.direction == "clockwise":
            return self.end_angle_degrees, self.end_angle_degrees + self.sweep_angle_degrees
        return self.start_angle_degrees, self.start_angle_degrees + self.sweep_angle_degrees


@dataclasses.dataclass(frozen=True, slots=True)
class CoilStatistics:
    """Computed statistics for a constructed coil."""

    total_track_length: float
    track_width: float
    segment_count: int
    start_point: CoilPoint | None
    end_point: CoilPoint | None
    turn_count: int | None = None
    angular_width_degrees: float | None = None


class Coil:
    """A manually constructed PCB coil path.

    :param track_width: Track width in millimetres.
    """

    def __init__(self, track_width: float = 1.0) -> None:
        if track_width <= 0.0:
            raise ValueError("track_width must be greater than 0.")

        self.track_width = float(track_width)
        self._segments: list[LineSegment | ArcSegment] = []

    @property
    def segments(self) -> tuple[LineSegment | ArcSegment, ...]:
        """The coil segments in construction order."""

        return tuple(self._segments)

    @property
    def total_track_length(self) -> float:
        """Total track centreline length in millimetres."""

        return sum(segment.length for segment in self._segments)

    @property
    def statistics(self) -> CoilStatistics:
        """Computed statistics for the constructed coil."""

        path_points = self.path_points
        start_point = path_points[0] if path_points else None
        end_point = path_points[-1] if path_points else None
        return CoilStatistics(
            total_track_length=self.total_track_length,
            track_width=self.track_width,
            segment_count=len(self._segments),
            start_point=start_point,
            end_point=end_point,
        )

    @property
    def path_points(self) -> tuple[CoilPoint, ...]:
        """Sampled path points suitable for plotting and SVG export."""

        points: list[CoilPoint] = []
        for segment in self._segments:
            if isinstance(segment, LineSegment):
                if not points or points[-1] != segment.start_point:
                    points.append(segment.start_point)
                points.append(segment.end_point)
            else:
                points.extend(self._sample_arc_segment(segment, include_start=not points))
        return tuple(points)

    def build_coil(self) -> None:
        """Construct the coil geometry.

        Override or edit this method to add line and arc segments.
        """

        pass

    def add_line(self, start_point: PointInput, end_point: PointInput) -> None:
        """Add a straight segment.

        :param start_point: Segment start point.
        :param end_point: Segment end point.
        """

        coerced_start_point = self._coerce_point(start_point)
        coerced_end_point = self._coerce_point(end_point)
        self._segments.append(LineSegment(start_point=coerced_start_point, end_point=coerced_end_point))

    def add_arc(
        self,
        start_point: PointInput,
        end_point: PointInput,
        center_point: PointInput,
        clockwise: bool | None = None,
        direction: str | None = None,
    ) -> None:
        """Add a circular arc segment.

        :param start_point: Arc start point.
        :param end_point: Arc end point.
        :param center_point: Arc centre point.
        :param clockwise: Optional compatibility direction flag.
        :param direction: Optional explicit direction, ``clockwise`` or ``counterclockwise``.
        """

        coerced_start_point = self._coerce_point(start_point)
        coerced_end_point = self._coerce_point(end_point)
        coerced_center_point = self._coerce_point(center_point)
        radius = self._distance(coerced_start_point, coerced_center_point)
        end_radius = self._distance(coerced_end_point, coerced_center_point)

        if radius <= 0.0:
            raise ValueError("Arc radius must be greater than 0.")
        if not math.isclose(radius, end_radius, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Arc start and end points must be the same distance from the center point.")

        arc_direction = self._normalize_arc_direction(coerced_start_point, coerced_end_point, coerced_center_point, clockwise, direction)
        self._segments.append(
            ArcSegment(
                start_point=coerced_start_point,
                end_point=coerced_end_point,
                center_point=coerced_center_point,
                direction=arc_direction,
                radius=radius,
            )
        )

    def export_svg(self, file_path: str | pathlib.Path = "coil.svg") -> pathlib.Path:
        """Write an SVG rendering of the coil and return the written path.

        :param file_path: Destination path for the SVG file.
        """

        output_path = pathlib.Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._build_svg(), encoding="utf-8")
        return output_path

    def plot(
        self,
        axis: matplotlib.axes.Axes | None = None,
        show: bool = True,
    ) -> tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        """Render the coil using matplotlib.

        :param axis: Optional existing matplotlib axis.
        :param show: Show the plot before returning when true.
        """

        figure, selected_axis = self._resolve_axis(axis)
        for segment in self._segments:
            segment.plot(line_width=self.track_width, axis=selected_axis)
        points = self.path_points
        if points:
            selected_axis.scatter([points[0].x], [points[0].y], color="tab:green", s=24, zorder=3)
            selected_axis.scatter([points[-1].x], [points[-1].y], color="tab:red", s=24, zorder=3)
        self._style_axis(selected_axis)
        if show:
            import matplotlib.pyplot

            matplotlib.pyplot.show()
        return figure, selected_axis

    def _build_svg(self) -> str:
        points = self.path_points
        drawing_limit = self._drawing_limit(points)
        size = 2.0 * drawing_limit
        view_box_values = (
            self._format_number(-drawing_limit),
            self._format_number(-drawing_limit),
            self._format_number(size),
            self._format_number(size),
        )
        path_data = self._build_svg_path_data(points)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self._format_number(size)}mm" height="{self._format_number(size)}mm" '
            f'viewBox="{" ".join(view_box_values)}">\n'
            f'  <path d="{path_data}" fill="none" stroke="black" stroke-width="{self._format_number(self.track_width)}" '
            'stroke-linecap="butt" stroke-linejoin="round"/>\n'
            "</svg>\n"
        )

    def _build_svg_path_data(self, points: tuple[CoilPoint, ...]) -> str:
        if not points:
            return ""
        commands = [f"M {self._format_number(points[0].x)} {self._format_number(-points[0].y)}"]
        commands.extend(
            f"L {self._format_number(point.x)} {self._format_number(-point.y)}"
            for point in points[1:]
        )
        return " ".join(commands)

    def _sample_arc_segment(self, segment: ArcSegment, include_start: bool) -> list[CoilPoint]:
        start_angle = math.radians(segment.start_angle_degrees)
        angle_radians = segment.signed_angle_radians
        step_count = max(2, int(math.ceil(abs(angle_radians) / math.radians(3.0))))
        start_index = 0 if include_start else 1
        return [
            CoilPoint(
                x=segment.center_point.x + (segment.radius * math.cos(start_angle + ((angle_radians * index) / step_count))),
                y=segment.center_point.y + (segment.radius * math.sin(start_angle + ((angle_radians * index) / step_count))),
            )
            for index in range(start_index, step_count + 1)
        ]

    def _style_axis(self, axis: matplotlib.axes.Axes) -> None:
        points = self.path_points
        drawing_limit = self._drawing_limit(points)
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlim(-drawing_limit, drawing_limit)
        axis.set_ylim(-drawing_limit, drawing_limit)
        axis.set_xlabel("x (mm)")
        axis.set_ylabel("y (mm)")

    def _resolve_axis(self, axis: matplotlib.axes.Axes | None) -> tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        if axis is not None:
            return axis.figure, axis
        import matplotlib.pyplot

        figure, created_axis = matplotlib.pyplot.subplots()
        return figure, created_axis

    def _drawing_limit(self, points: tuple[CoilPoint, ...]) -> float:
        if not points:
            return max(1.0, self.track_width)
        maximum_coordinate = max(max(abs(point.x), abs(point.y)) for point in points)
        return maximum_coordinate + self.track_width

    @staticmethod
    def _normalize_arc_direction(
        start_point: CoilPoint,
        end_point: CoilPoint,
        center_point: CoilPoint,
        clockwise: bool | None,
        direction: str | None,
    ) -> str:
        if direction is not None and clockwise is not None:
            raise ValueError("Use either direction or clockwise, not both.")
        if direction is not None:
            normalized_direction = ARC_DIRECTION_ALIASES.get(direction.lower())
            if normalized_direction is None:
                raise ValueError("direction must be 'clockwise' or 'counterclockwise'.")
            return normalized_direction
        if clockwise is True:
            return "clockwise"
        if clockwise is False:
            return "counterclockwise"

        start_x = start_point.x - center_point.x
        start_y = start_point.y - center_point.y
        end_x = end_point.x - center_point.x
        end_y = end_point.y - center_point.y
        cross_product = (start_x * end_y) - (start_y * end_x)
        if cross_product < 0.0:
            return "clockwise"
        return "counterclockwise"

    @staticmethod
    def _coerce_point(point: PointInput) -> CoilPoint:
        if isinstance(point, CoilPoint):
            return point
        return CoilPoint(x=float(point[0]), y=float(point[1]))

    @staticmethod
    def _distance(start_point: CoilPoint, end_point: CoilPoint) -> float:
        return math.dist((start_point.x, start_point.y), (end_point.x, end_point.y))

    @staticmethod
    def _format_number(value: float) -> str:
        return f"{value:.6f}".rstrip("0").rstrip(".")


class WedgeCoil(Coil):
    """Generate a wedge spiral coil using the proven polar construction.

    :param inner_diameter: Inner coil diameter in millimetres.
    :param outer_diameter: Outer coil diameter in millimetres.
    :param coil_count: Number of coils around the full motor.
    :param minimum_track_width: Minimum allowed track width in millimetres.
    :param minimum_track_gap: Minimum edge gap between neighbouring tracks.
    :param packing_factor: Value from 0 to 1 selecting one thick turn through to maximum thin turns.
    :param center_angle_degrees: Centre angle of the wedge.
    """

    def __init__(
        self,
        inner_diameter: float,
        outer_diameter: float,
        coil_count: int,
        minimum_track_width: float,
        minimum_track_gap: float,
        packing_factor: float,
        center_angle_degrees: float = 0.0,
    ) -> None:
        self.inner_diameter = float(inner_diameter)
        self.outer_diameter = float(outer_diameter)
        self.coil_count = coil_count
        self.minimum_track_width = float(minimum_track_width)
        self.minimum_track_gap = float(minimum_track_gap)
        self.packing_factor = float(packing_factor)
        self.center_angle_degrees = float(center_angle_degrees)
        self.inner_radius = self.inner_diameter / 2.0
        self.outer_radius = self.outer_diameter / 2.0
        self.angular_width_degrees = 360.0 / self.coil_count

        self._validate_inputs()
        self.maximum_turn_count = self._maximum_turn_count_for_width(self.minimum_track_width)
        if self.maximum_turn_count < 1:
            raise ValueError("The requested dimensions cannot fit one coil turn.")
        self.turn_count = self._calculate_turn_count()
        generated_track_width = self._calculate_track_width()
        self.centerline_spacing = generated_track_width + self.minimum_track_gap
        self.side_clearance = (generated_track_width / 2.0) + (self.minimum_track_gap / 2.0)

        super().__init__(track_width=generated_track_width)
        self.build_coil()

    @property
    def statistics(self) -> CoilStatistics:
        """Computed statistics for the generated wedge coil."""

        statistics = super().statistics
        return CoilStatistics(
            total_track_length=statistics.total_track_length,
            track_width=statistics.track_width,
            segment_count=statistics.segment_count,
            start_point=statistics.start_point,
            end_point=statistics.end_point,
            turn_count=self.turn_count,
            angular_width_degrees=self.angular_width_degrees,
        )

    def build_coil(self) -> None:
        """Build the wedge coil geometry."""

        self._segments.clear()
        for turn_index in range(self.turn_count):
            self._add_turn(turn_index)

    def plot_motor(
        self,
        axis: matplotlib.axes.Axes | None = None,
        show: bool = True,
    ) -> tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        """Render this wedge coil around a full motor."""

        figure, selected_axis = self._resolve_axis(axis)
        original_segments = tuple(self._segments)
        for coil_index in range(self.coil_count):
            rotation_degrees = coil_index * self.angular_width_degrees
            for segment in original_segments:
                self._rotate_segment(segment, rotation_degrees).plot(line_width=self.track_width, axis=selected_axis)
        self._style_axis(selected_axis)
        if show:
            import matplotlib.pyplot

            matplotlib.pyplot.show()
        return figure, selected_axis

    def _add_turn(self, turn_index: int) -> None:
        outer_radius = self._outer_centerline_radius(turn_index, self.track_width)
        inner_radius = self._inner_centerline_radius(turn_index, self.track_width)
        next_outer_radius = self._outer_centerline_radius(turn_index + 1, self.track_width)

        outer_start_angle = self._minimum_angle_for_radius(outer_radius, max(turn_index - 1, 0))
        outer_end_angle = self._maximum_angle_for_radius(outer_radius, turn_index)
        inner_start_angle = self._maximum_angle_for_radius(inner_radius, turn_index)
        inner_end_angle = self._minimum_angle_for_radius(inner_radius, turn_index)
        next_outer_end_angle = self._minimum_angle_for_radius(next_outer_radius, turn_index)

        self.add_arc(
            start_point=self.polar_to_cartesian(outer_radius, outer_start_angle),
            end_point=self.polar_to_cartesian(outer_radius, outer_end_angle),
            center_point=(0.0, 0.0),
            direction="counterclockwise",
        )
        self.add_line(
            start_point=self.polar_to_cartesian(outer_radius, outer_end_angle),
            end_point=self.polar_to_cartesian(inner_radius, inner_start_angle),
        )
        self.add_arc(
            start_point=self.polar_to_cartesian(inner_radius, inner_start_angle),
            end_point=self.polar_to_cartesian(inner_radius, inner_end_angle),
            center_point=(0.0, 0.0),
            direction="clockwise",
        )
        if turn_index < self.turn_count - 1:
            self.add_line(
                start_point=self.polar_to_cartesian(inner_radius, inner_end_angle),
                end_point=self.polar_to_cartesian(next_outer_radius, next_outer_end_angle),
            )

    def _validate_inputs(self) -> None:
        if self.inner_diameter <= 0.0:
            raise ValueError("inner_diameter must be greater than 0.")
        if self.outer_diameter <= self.inner_diameter:
            raise ValueError("outer_diameter must be greater than inner_diameter.")
        if isinstance(self.coil_count, bool) or not isinstance(self.coil_count, int) or self.coil_count < 1:
            raise ValueError("coil_count must be an integer greater than or equal to 1.")
        if self.minimum_track_width <= 0.0:
            raise ValueError("minimum_track_width must be greater than 0.")
        if self.minimum_track_gap < 0.0:
            raise ValueError("minimum_track_gap must be greater than or equal to 0.")
        if not 0.0 <= self.packing_factor <= 1.0:
            raise ValueError("packing_factor must be between 0 and 1 inclusive.")

    def _calculate_turn_count(self) -> int:
        interpolated_turn_count = 1.0 + (self.packing_factor * (self.maximum_turn_count - 1))
        return int(math.floor(interpolated_turn_count + 0.5))

    def _calculate_track_width(self) -> float:
        maximum_track_width = self._maximum_track_width_for_turn_count(self.turn_count)
        return self.minimum_track_width + ((1.0 - self.packing_factor) * (maximum_track_width - self.minimum_track_width))

    def _maximum_track_width_for_turn_count(self, turn_count: int) -> float:
        radial_width = self.outer_radius - self.inner_radius
        low = self.minimum_track_width
        high = radial_width
        for _ in range(80):
            midpoint = (low + high) / 2.0
            if self._turn_count_fits(turn_count, midpoint):
                low = midpoint
            else:
                high = midpoint
        return low

    def _maximum_turn_count_for_width(self, track_width: float) -> int:
        radial_width = self.outer_radius - self.inner_radius
        centerline_spacing = track_width + self.minimum_track_gap
        maximum_radial_turn_count = max(0, int(math.floor((radial_width - track_width) / (2.0 * centerline_spacing))) + 1)
        turn_count = 0
        for candidate_turn_count in range(1, maximum_radial_turn_count + 1):
            if self._turn_count_fits(candidate_turn_count, track_width):
                turn_count = candidate_turn_count
        return turn_count

    def _turn_count_fits(self, turn_count: int, track_width: float) -> bool:
        if turn_count < 1 or track_width < self.minimum_track_width:
            return False
        for turn_index in range(turn_count):
            outer_radius = self._outer_centerline_radius(turn_index, track_width)
            inner_radius = self._inner_centerline_radius(turn_index, track_width)
            if outer_radius - inner_radius < (track_width + self.minimum_track_gap):
                return False
            outer_start_angle = self._minimum_angle_for_radius(outer_radius, max(turn_index - 1, 0), track_width)
            outer_end_angle = self._maximum_angle_for_radius(outer_radius, turn_index, track_width)
            inner_start_angle = self._maximum_angle_for_radius(inner_radius, turn_index, track_width)
            inner_end_angle = self._minimum_angle_for_radius(inner_radius, turn_index, track_width)
            if outer_start_angle >= outer_end_angle:
                return False
            if inner_end_angle >= inner_start_angle:
                return False
        return True

    def _outer_centerline_radius(self, turn_index: int, track_width: float) -> float:
        centerline_spacing = track_width + self.minimum_track_gap
        return self.outer_radius - (track_width / 2.0) - (turn_index * centerline_spacing)

    def _inner_centerline_radius(self, turn_index: int, track_width: float) -> float:
        centerline_spacing = track_width + self.minimum_track_gap
        return self.inner_radius + (track_width / 2.0) + (turn_index * centerline_spacing)

    def _minimum_angle_for_radius(self, radius: float, spacing_count: int, track_width: float | None = None) -> float:
        angular_offset = self.arclength_to_angle(radius, self._side_offset(spacing_count, track_width))
        return self.center_angle_degrees - (self.angular_width_degrees / 2.0) + angular_offset

    def _maximum_angle_for_radius(self, radius: float, spacing_count: int, track_width: float | None = None) -> float:
        angular_offset = self.arclength_to_angle(radius, self._side_offset(spacing_count, track_width))
        return self.center_angle_degrees + (self.angular_width_degrees / 2.0) - angular_offset

    def _side_offset(self, spacing_count: int, track_width: float | None = None) -> float:
        selected_track_width = self.track_width if track_width is None else track_width
        centerline_spacing = selected_track_width + self.minimum_track_gap
        return (selected_track_width / 2.0) + (self.minimum_track_gap / 2.0) + (centerline_spacing * spacing_count)

    @staticmethod
    def polar_to_cartesian(radius: float, angle_degrees: float) -> CoilPoint:
        """Convert a polar coordinate to a point."""

        angle_radians = math.radians(angle_degrees)
        return CoilPoint(
            x=radius * math.cos(angle_radians),
            y=radius * math.sin(angle_radians),
        )

    @staticmethod
    def arclength_to_angle(radius: float, arc_length: float) -> float:
        """Convert arc length to degrees at the given radius."""

        return math.degrees(arc_length / radius)

    @staticmethod
    def _rotate_segment(segment: LineSegment | ArcSegment, rotation_degrees: float) -> LineSegment | ArcSegment:
        if isinstance(segment, LineSegment):
            return LineSegment(
                start_point=WedgeCoil._rotate_point(segment.start_point, rotation_degrees),
                end_point=WedgeCoil._rotate_point(segment.end_point, rotation_degrees),
            )
        return ArcSegment(
            start_point=WedgeCoil._rotate_point(segment.start_point, rotation_degrees),
            end_point=WedgeCoil._rotate_point(segment.end_point, rotation_degrees),
            center_point=WedgeCoil._rotate_point(segment.center_point, rotation_degrees),
            direction=segment.direction,
            radius=segment.radius,
        )

    @staticmethod
    def _rotate_point(point: CoilPoint, rotation_degrees: float) -> CoilPoint:
        angle_radians = math.radians(rotation_degrees)
        cosine_value = math.cos(angle_radians)
        sine_value = math.sin(angle_radians)
        return CoilPoint(
            x=(point.x * cosine_value) - (point.y * sine_value),
            y=(point.x * sine_value) + (point.y * cosine_value),
        )
