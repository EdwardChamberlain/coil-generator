"""Basic wedge coil generation demo."""

import pathlib

import wedge_generator


def main() -> None:
    """Generate wedge coil SVG files."""

    output_directory = pathlib.Path("demo_output")
    output_directory.mkdir(exist_ok=True)

    coil = wedge_generator.WedgeCoil(
        inner_diameter=40.0,
        outer_diameter=60.0,
        motor_coil_count=9,
        minimum_track_width=0.1,
        minimum_track_gap=0.1,
        packing_factor=0.1,
    )

    svg_path = coil.export_svg(output_directory / "wedge_coil.svg")
    motor_svg_path = coil.export_motor_svg(output_directory / "wedge_motor.svg")

    statistics = coil.statistics
    print(f"Turn count: {statistics.turn_count}")
    print(f"Track width: {statistics.track_width:.3f} mm")
    print(f"Total track length: {statistics.total_track_length:.3f} mm")
    print(f"SVG: {svg_path}")
    print(f"Motor SVG: {motor_svg_path}")


if __name__ == "__main__":
    main()
