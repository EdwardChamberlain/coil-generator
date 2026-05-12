# Wedge Coils Generator

Generate PCB motor wedge coils, or build custom coil paths from simple line and arc primitives.

```python
import wedge_generator

coil = wedge_generator.WedgeCoil(
    inner_diameter=20.0,
    outer_diameter=60.0,
    coil_count=9,
    minimum_track_width=0.1,
    minimum_track_gap=0.1,
    packing_factor=1.0,
)

coil.export_svg()
coil.plot()
coil.plot_motor()
print(coil.total_track_length)
```

Run the basic demo with:

```bash
python examples/basic_demo.py
```

It writes an SVG and plot images to `demo_output/`.
