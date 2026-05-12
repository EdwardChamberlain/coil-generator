"""Basic wedge coil generation demo."""

import os
import pathlib

import wedge_generator

DEMO_IMAGE_DPI = 1000


def main() -> None:
    """Generate a wedge coil SVG and plot images."""

    output_directory = pathlib.Path("demo_output")
    matplotlib_cache_directory = output_directory / "matplotlib-cache"
    output_directory.mkdir(exist_ok=True)
    matplotlib_cache_directory.mkdir(exist_ok=True)

    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache_directory))
    os.environ.setdefault("XDG_CACHE_HOME", str(matplotlib_cache_directory))

    coil = wedge_generator.WedgeCoil(
        inner_diameter=40.0,
        outer_diameter=60.0,
        coil_count=9,
        minimum_track_width=0.1,
        minimum_track_gap=0.1,
        packing_factor=0.1,
    )

    svg_path = coil.export_svg(output_directory / "wedge_coil.svg")
    single_figure, _single_axis = coil.plot(show=False)
    motor_figure, _motor_axis = coil.plot_motor(show=False)

    single_plot_path = output_directory / "wedge_coil.png"
    motor_plot_path = output_directory / "wedge_motor.png"
    single_figure.savefig(single_plot_path, dpi=DEMO_IMAGE_DPI, bbox_inches="tight")
    motor_figure.savefig(motor_plot_path, dpi=DEMO_IMAGE_DPI, bbox_inches="tight")

    statistics = coil.statistics
    print(f"Turn count: {statistics.turn_count}")
    print(f"Track width: {statistics.track_width:.3f} mm")
    print(f"Total track length: {statistics.total_track_length:.3f} mm")
    print(f"SVG: {svg_path}")
    print(f"Single coil plot: {single_plot_path}")
    print(f"Motor plot: {motor_plot_path}")


if __name__ == "__main__":
    main()
