import math
import xml.etree.ElementTree

import pytest

import wedge_generator

TEST_TOLERANCE = 1e-8


def _point_radius(point: wedge_generator.CoilPoint) -> float:
    return math.hypot(point.x, point.y)


def _point_angle_degrees(point: wedge_generator.CoilPoint) -> float:
    return math.degrees(math.atan2(point.y, point.x))


def test_add_line_updates_segments_and_total_length() -> None:
    coil = wedge_generator.Coil(track_width=0.5)

    coil.add_line((0.0, 0.0), (3.0, 4.0))

    assert len(coil.segments) == 1
    assert coil.total_track_length == pytest.approx(5.0)
    assert coil.statistics.track_width == pytest.approx(0.5)
    assert coil.statistics.segment_count == 1


def test_add_arc_updates_segments_and_total_length() -> None:
    coil = wedge_generator.Coil(track_width=0.5)

    coil.add_arc((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))

    assert len(coil.segments) == 1
    assert coil.total_track_length == pytest.approx(math.pi / 2.0)


def test_add_arc_can_force_direction() -> None:
    clockwise_coil = wedge_generator.Coil(track_width=0.5)
    counter_clockwise_coil = wedge_generator.Coil(track_width=0.5)

    clockwise_coil.add_arc((1.0, 0.0), (0.0, 1.0), (0.0, 0.0), clockwise=True)
    counter_clockwise_coil.add_arc((1.0, 0.0), (0.0, 1.0), (0.0, 0.0), clockwise=False)

    assert clockwise_coil.total_track_length == pytest.approx((3.0 * math.pi) / 2.0)
    assert counter_clockwise_coil.total_track_length == pytest.approx(math.pi / 2.0)


def test_path_points_preserve_construction_order() -> None:
    coil = wedge_generator.Coil(track_width=0.5)

    coil.add_line((0.0, 0.0), (1.0, 0.0))
    coil.add_arc((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))

    assert coil.path_points[0] == wedge_generator.CoilPoint(0.0, 0.0)
    assert coil.path_points[-1].x == pytest.approx(0.0)
    assert coil.path_points[-1].y == pytest.approx(1.0)


def test_invalid_arc_radius_raises_clear_error() -> None:
    coil = wedge_generator.Coil(track_width=0.5)

    with pytest.raises(ValueError, match="same distance"):
        coil.add_arc((1.0, 0.0), (0.0, 2.0), (0.0, 0.0))


def test_build_coil_is_available_as_stub() -> None:
    coil = wedge_generator.Coil(track_width=0.5)

    coil.build_coil()

    assert coil.segments == ()
    assert coil.total_track_length == pytest.approx(0.0)


def test_export_svg_writes_valid_svg_file(tmp_path) -> None:
    coil = wedge_generator.Coil(track_width=0.5)
    coil.add_line((0.0, 0.0), (5.0, 0.0))
    output_path = coil.export_svg(tmp_path / "coil.svg")

    assert output_path.exists()
    root = xml.etree.ElementTree.fromstring(output_path.read_text(encoding="utf-8"))
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    background = root.find("svg:rect", namespace)
    path = root.find("svg:path", namespace)

    assert root.attrib["width"].endswith("mm")
    assert "viewBox" in root.attrib
    assert background is not None
    assert background.attrib["fill"] == "white"
    assert path is not None
    assert path.attrib["d"].startswith("M ")
    assert float(path.attrib["stroke-width"]) == pytest.approx(0.5)


def test_public_api_exports_expected_classes() -> None:
    from wedge_generator import ArcSegment
    from wedge_generator import Coil
    from wedge_generator import CoilPoint
    from wedge_generator import CoilStatistics
    from wedge_generator import LineSegment
    from wedge_generator import WedgeCoil

    assert wedge_generator.__all__ == [
        "ArcSegment",
        "Coil",
        "CoilPoint",
        "CoilStatistics",
        "LineSegment",
        "WedgeCoil",
    ]
    assert ArcSegment is wedge_generator.ArcSegment
    assert Coil is wedge_generator.Coil
    assert CoilPoint is wedge_generator.CoilPoint
    assert CoilStatistics is wedge_generator.CoilStatistics
    assert LineSegment is wedge_generator.LineSegment
    assert WedgeCoil is wedge_generator.WedgeCoil
    assert WedgeCoil(20.0, 40.0, motor_coil_count=9, minimum_track_width=1.0, minimum_track_gap=0.5, packing_factor=1.0)


def test_wedge_coil_builds_from_scratch_algorithm() -> None:
    coil = wedge_generator.WedgeCoil(
        inner_diameter=20.0,
        outer_diameter=40.0,
        motor_coil_count=9,
        minimum_track_width=1.0,
        minimum_track_gap=0.5,
        packing_factor=1.0,
    )

    assert coil.statistics.turn_count == 3
    assert coil.statistics.angular_width_degrees == pytest.approx(40.0)
    assert len(coil.segments) == 11
    assert isinstance(coil.segments[0], wedge_generator.ArcSegment)
    assert isinstance(coil.segments[1], wedge_generator.LineSegment)
    assert coil.segments[0].direction == "counterclockwise"
    assert coil.segments[2].direction == "clockwise"
    assert coil.total_track_length > 0.0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"inner_diameter": 0.0}, "inner_diameter"),
        ({"outer_diameter": 20.0}, "outer_diameter"),
        ({"motor_coil_count": 0}, "motor_coil_count"),
        ({"motor_coil_count": True}, "motor_coil_count"),
        ({"minimum_track_width": 0.0}, "minimum_track_width"),
        ({"minimum_track_gap": -0.1}, "minimum_track_gap"),
        ({"packing_factor": -0.1}, "packing_factor"),
        ({"packing_factor": 1.1}, "packing_factor"),
        ({"outer_diameter": 20.1, "minimum_track_width": 1.0, "minimum_track_gap": 1.0}, "cannot fit one coil turn"),
    ],
)
def test_wedge_coil_rejects_invalid_inputs(overrides, message) -> None:
    arguments = {
        "inner_diameter": 20.0,
        "outer_diameter": 60.0,
        "motor_coil_count": 9,
        "minimum_track_width": 0.1,
        "minimum_track_gap": 0.1,
        "packing_factor": 0.5,
    }
    arguments.update(overrides)

    with pytest.raises(ValueError, match=message):
        wedge_generator.WedgeCoil(**arguments)


def test_wedge_coil_leaves_half_gap_at_each_angular_side() -> None:
    coil = wedge_generator.WedgeCoil(
        inner_diameter=20.0,
        outer_diameter=40.0,
        motor_coil_count=9,
        minimum_track_width=1.0,
        minimum_track_gap=0.5,
        packing_factor=0.0,
    )
    outer_arc = coil.segments[0]
    expected_side_clearance = (coil.statistics.track_width / 2.0) + (coil.minimum_track_gap / 2.0)
    expected_side_clearance_angle = wedge_generator.WedgeCoil.arclength_to_angle(outer_arc.radius, expected_side_clearance)

    assert outer_arc.start_angle_degrees == pytest.approx(-20.0 + expected_side_clearance_angle)
    assert outer_arc.end_angle_degrees == pytest.approx(20.0 - expected_side_clearance_angle)


def test_wedge_coil_packing_factor_controls_turn_count() -> None:
    sparse_coil = wedge_generator.WedgeCoil(20.0, 60.0, 9, 0.1, 0.1, 0.0)
    dense_coil = wedge_generator.WedgeCoil(20.0, 60.0, 9, 0.1, 0.1, 1.0)

    assert sparse_coil.statistics.turn_count == 1
    assert sparse_coil.statistics.track_width > dense_coil.statistics.track_width
    assert dense_coil.statistics.turn_count > sparse_coil.statistics.turn_count
    assert dense_coil.statistics.track_width == pytest.approx(0.1)


def test_wedge_coil_packing_factor_is_monotonic() -> None:
    packing_factors = [0.0, 0.25, 0.5, 0.75, 1.0]
    coils = [
        wedge_generator.WedgeCoil(20.0, 60.0, 9, 0.1, 0.1, packing_factor)
        for packing_factor in packing_factors
    ]
    turn_counts = [coil.statistics.turn_count for coil in coils]
    track_widths = [coil.statistics.track_width for coil in coils]

    assert turn_counts == sorted(turn_counts)
    assert track_widths == sorted(track_widths, reverse=True)
    assert turn_counts[0] == 1
    assert track_widths[-1] == pytest.approx(0.1)


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "inner_diameter": 20.0,
            "outer_diameter": 60.0,
            "motor_coil_count": 9,
            "minimum_track_width": 0.1,
            "minimum_track_gap": 0.1,
            "packing_factor": 1.0,
            "center_angle_degrees": 25.0,
        },
        {
            "inner_diameter": 20.0,
            "outer_diameter": 50.0,
            "motor_coil_count": 12,
            "minimum_track_width": 0.2,
            "minimum_track_gap": 0.15,
            "packing_factor": 0.5,
            "center_angle_degrees": 30.0,
        },
        {
            "inner_diameter": 40.0,
            "outer_diameter": 80.0,
            "motor_coil_count": 9,
            "minimum_track_width": 0.1,
            "minimum_track_gap": 0.1,
            "packing_factor": 0.25,
            "center_angle_degrees": 15.0,
        },
    ],
)
def test_wedge_coil_geometry_stays_inside_edge_aware_bounds(arguments) -> None:
    coil = wedge_generator.WedgeCoil(**arguments)
    minimum_centerline_radius = coil.inner_radius + (coil.statistics.track_width / 2.0)
    maximum_centerline_radius = coil.outer_radius - (coil.statistics.track_width / 2.0)
    minimum_angle = coil.center_angle_degrees - (coil.angular_width_degrees / 2.0)
    maximum_angle = coil.center_angle_degrees + (coil.angular_width_degrees / 2.0)
    minimum_side_clearance = (coil.statistics.track_width / 2.0) + (coil.minimum_track_gap / 2.0)

    for point in coil.path_points:
        radius = _point_radius(point)
        angle_degrees = _point_angle_degrees(point)
        left_clearance = math.radians(angle_degrees - minimum_angle) * radius
        right_clearance = math.radians(maximum_angle - angle_degrees) * radius

        assert radius >= minimum_centerline_radius - TEST_TOLERANCE
        assert radius <= maximum_centerline_radius + TEST_TOLERANCE
        assert minimum_angle <= angle_degrees <= maximum_angle
        assert left_clearance >= minimum_side_clearance - TEST_TOLERANCE
        assert right_clearance >= minimum_side_clearance - TEST_TOLERANCE


@pytest.mark.parametrize(
    "coil",
    [
        wedge_generator.WedgeCoil(20.0, 60.0, 9, 0.1, 0.1, 1.0),
        wedge_generator.WedgeCoil(20.0, 50.0, 12, 0.2, 0.15, 0.5),
    ],
)
def test_wedge_coil_radial_track_gaps_are_edge_to_edge(coil) -> None:
    outer_arcs = [
        coil.segments[index]
        for index in range(0, len(coil.segments), 4)
    ]
    inner_arcs = [
        coil.segments[index]
        for index in range(2, len(coil.segments), 4)
    ]
    outer_edge_gaps = [
        outer_arcs[index].radius - outer_arcs[index + 1].radius - coil.statistics.track_width
        for index in range(len(outer_arcs) - 1)
    ]
    inner_edge_gaps = [
        inner_arcs[index + 1].radius - inner_arcs[index].radius - coil.statistics.track_width
        for index in range(len(inner_arcs) - 1)
    ]

    assert outer_edge_gaps
    assert inner_edge_gaps
    assert min(outer_edge_gaps) >= coil.minimum_track_gap - TEST_TOLERANCE
    assert min(inner_edge_gaps) >= coil.minimum_track_gap - TEST_TOLERANCE


def test_wedge_coil_track_gap_is_edge_to_edge() -> None:
    coil = wedge_generator.WedgeCoil(20.0, 60.0, 9, 0.1, 0.1, 1.0)
    outer_arcs = [
        coil.segments[index]
        for index in range(0, len(coil.segments), 4)
    ]
    edge_gaps = [
        outer_arcs[index].radius - outer_arcs[index + 1].radius - coil.statistics.track_width
        for index in range(len(outer_arcs) - 1)
    ]

    assert edge_gaps
    assert min(edge_gaps) == pytest.approx(0.1)


def test_wedge_coil_adjacent_motor_coils_have_full_edge_gap() -> None:
    coil = wedge_generator.WedgeCoil(20.0, 60.0, 9, 0.1, 0.1, 1.0)
    outer_arc = coil.segments[0]
    next_coil_start_angle = outer_arc.start_angle_degrees + coil.angular_width_degrees
    centerline_arc_gap = math.radians(next_coil_start_angle - outer_arc.end_angle_degrees) * outer_arc.radius
    edge_arc_gap = centerline_arc_gap - coil.statistics.track_width

    assert edge_arc_gap == pytest.approx(coil.minimum_track_gap)


def test_wedge_coil_export_motor_svg_writes_all_coils(tmp_path) -> None:
    coil = wedge_generator.WedgeCoil(20.0, 40.0, 9, 1.0, 0.5, 0.0)
    output_path = coil.export_motor_svg(tmp_path / "motor.svg")

    root = xml.etree.ElementTree.fromstring(output_path.read_text(encoding="utf-8"))
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    background = root.find("svg:rect", namespace)
    paths = root.findall("svg:path", namespace)

    assert output_path.exists()
    assert root.attrib["width"].endswith("mm")
    assert "viewBox" in root.attrib
    assert background is not None
    assert background.attrib["fill"] == "white"
    assert len(paths) == coil.motor_coil_count
    assert all(path.attrib["d"].startswith("M ") for path in paths)
    assert all(float(path.attrib["stroke-width"]) == pytest.approx(coil.statistics.track_width) for path in paths)
