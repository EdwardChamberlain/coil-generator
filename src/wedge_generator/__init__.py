"""Tools for generating wedge coil PCB traces."""

import wedge_generator.coil

ArcSegment = wedge_generator.coil.ArcSegment
Coil = wedge_generator.coil.Coil
CoilPoint = wedge_generator.coil.CoilPoint
CoilStatistics = wedge_generator.coil.CoilStatistics
LineSegment = wedge_generator.coil.LineSegment
WedgeCoil = wedge_generator.coil.WedgeCoil

__all__ = [
    "ArcSegment",
    "Coil",
    "CoilPoint",
    "CoilStatistics",
    "LineSegment",
    "WedgeCoil",
]
