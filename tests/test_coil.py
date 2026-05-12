import math
import xml.etree.ElementTree

import matplotlib
import pytest

import wedge_generator

matplotlib.use("Agg")


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
    path = root.find("svg:path", namespace)

    assert root.attrib["width"].endswith("mm")
    assert "viewBox" in root.attrib
    assert path is not None
    assert path.attrib["d"].startswith("M ")
    assert float(path.attrib["stroke-width"]) == pytest.approx(0.5)


def test_plot_returns_figure_and_axis() -> None:
    coil = wedge_generator.Coil(track_width=0.5)
    coil.add_line((0.0, 0.0), (5.0, 0.0))

    figure, axis = coil.plot(show=False)

    assert figure is axis.figure
    assert len(axis.patches) == 1


def test_wedge_coil_builds_from_scratch_algorithm() -> None:
    coil = wedge_generator.WedgeCoil(
        inner_diameter=20.0,
        outer_diameter=40.0,
        coil_count=9,
        minimum_track_width=1.0,
        minimum_track_gap=0.5,
        packing_factor=1.0,
    )

    assert coil.statistics.turn_count == 4
    assert coil.statistics.angular_width_degrees == pytest.approx(40.0)
    assert len(coil.segments) == 15
    assert isinstance(coil.segments[0], wedge_generator.ArcSegment)
    assert isinstance(coil.segments[1], wedge_generator.LineSegment)
    assert coil.segments[0].direction == "counterclockwise"
    assert coil.segments[2].direction == "clockwise"
    assert coil.total_track_length > 0.0


def test_wedge_coil_packing_factor_controls_turn_count() -> None:
    sparse_coil = wedge_generator.WedgeCoil(20.0, 40.0, 9, 1.0, 0.5, 0.0)
    dense_coil = wedge_generator.WedgeCoil(20.0, 40.0, 9, 1.0, 0.5, 1.0)

    assert sparse_coil.statistics.turn_count == 1
    assert dense_coil.statistics.turn_count > sparse_coil.statistics.turn_count


def test_wedge_coil_motor_plot_uses_segment_patches() -> None:
    coil = wedge_generator.WedgeCoil(20.0, 40.0, 9, 1.0, 0.5, 0.0)

    figure, axis = coil.plot_motor(show=False)

    assert figure is axis.figure
    assert len(axis.patches) == len(coil.segments) * coil.coil_count
