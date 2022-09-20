"""
Dataclasses describing the graphic items found in .kicad_sch files.

SPDX-License-Identifier: EUPL-1.2
"""
from dataclasses import field
from enum import Enum
from typing import Optional

from pydantic.color import Color
from pydantic.dataclasses import dataclass

from edea.types.config import PydanticConfig
from edea.types.base import KicadExpr


class FillType(str, Enum):
    NONE = "none"
    OUTLINE = "outline"
    BACKGROUND = "background"


class StrokeType(str, Enum):
    DEFAULT = "default"
    DASH = "dash"
    DASH_DOT = "dash_dot"
    DASH_DOT_DOT = "dash_dot_dot"
    DOT = "dot"
    SOLID = "solid"


@dataclass(config=PydanticConfig)
class Stroke(KicadExpr):
    width: float = 0.1524
    type: StrokeType = StrokeType.DEFAULT
    color: Color = Color((0, 0, 0, 1))


@dataclass(config=PydanticConfig)
class Fill(KicadExpr):
    type: FillType = FillType.NONE


@dataclass(config=PydanticConfig)
class XY(KicadExpr):
    x: float
    y: float


@dataclass(config=PydanticConfig)
class Pts(KicadExpr):
    xy: list[XY] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class PolyLine(KicadExpr):
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)


@dataclass(config=PydanticConfig)
class Bezier(KicadExpr):
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)


@dataclass(config=PydanticConfig)
class Rectangle(KicadExpr):
    start: tuple[float, float]
    end: tuple[float, float]
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)


@dataclass(config=PydanticConfig)
class Circle(KicadExpr):
    center: tuple[float, float]
    radius: float
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)


@dataclass(config=PydanticConfig)
class Radius(KicadExpr):
    at: tuple[float, float]
    length: float
    angles: tuple[float, float]


@dataclass(config=PydanticConfig)
class Arc(KicadExpr):
    start: tuple[float, float]
    end: tuple[float, float]
    mid: Optional[tuple[float, float]] = None
    radius: Optional[Radius] = None
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)
