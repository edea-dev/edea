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
from edea.types.from_list_expr import from_list_expr


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
class Stroke:
    width: float = 0.1524
    type: StrokeType = StrokeType.DEFAULT
    color: Color = Color((0, 0, 0, 1))

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Fill:
    type: FillType = FillType.NONE
    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class XY:
    x: float
    y: float

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Pts:
    xy: list[XY] = field(default_factory=list)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class PolyLine:
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Bezier:
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Rectangle:
    start: tuple[float, float]
    end: tuple[float, float]
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Circle:
    center: tuple[float, float]
    radius: float
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Radius:
    at: tuple[float, float]
    length: float
    angles: tuple[float, float]

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Arc:
    start: tuple[float, float]
    end: tuple[float, float]
    mid: Optional[tuple[float, float]] = None
    radius: Optional[Radius] = None
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)

    from_list_expr = from_list_expr
