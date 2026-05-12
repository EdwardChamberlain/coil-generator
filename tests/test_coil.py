import math
import xml.etree.ElementTree

import pytest

import wedge_generator


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
