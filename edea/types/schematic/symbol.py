"""
Dataclasses describing the symbols found in "lib_symbols" of .kicad_sch files.

SPDX-License-Identifier: EUPL-1.2
"""

from dataclasses import field
from enum import Enum
from typing import Optional
from pydantic import validator, root_validator
from pydantic.dataclasses import dataclass

from edea.types.config import PydanticConfig, IsPresent
from edea.types.schematic.shapes import PolyLine, Rectangle, Circle, Arc, Bezier
from edea.types.from_list_expr import from_list_expr


class JustifyHoriz(str, Enum):
    LEFT = "left"
    CENTER = ""
    RIGHT = "right"


class JustifyVert(str, Enum):
    TOP = "top"
    CENTER = ""
    BOTTOM = "bottom"


@dataclass(config=PydanticConfig)
class Justify:
    horizontal: JustifyHoriz = JustifyHoriz.CENTER
    vertical: JustifyVert = JustifyVert.CENTER
    mirror: bool = False

    # allow for e.g. (justify bottom) on its own
    @root_validator(pre=True)
    def allow_vertical_as_first_arg(cls, values):
        h = values.get("horizontal")
        if (h not in list(JustifyHoriz)) and (h in list(JustifyVert)):
            values["vertical"] = h
            values["horizontal"] = JustifyHoriz.CENTER
        return values

    from_list_expr = from_list_expr


class PinElectricalType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    TRI_STATE = "tri_state"
    PASSIVE = "passive"
    FREE = "free"
    UNSPECIFIED = "unspecified"
    POWER_IN = "power_in"
    POWER_OUT = "power_out"
    OPEN_COLLECTOR = "open_collector"
    OPEN_EMITTER = "open_emitter"
    NO_CONNECT = "no_connect"


class PinGraphicStyle(str, Enum):
    LINE = "line"
    INVERTED = "inverted"
    CLOCK = "clock"
    INVERTED_CLOCK = "inverted_clock"
    INPUT_LOW = "input_low"
    CLOCK_LOW = "clock_low"
    OUTPUT_LOW = "output_low"
    EDGE_CLOCK_HIGH = "edge_clock_high"
    NON_LOGIC = "non_logic"


@dataclass(config=PydanticConfig)
class Font:
    size: tuple[float, float] = (1.27, 1.27)
    thickness: Optional[float] = None
    italic: bool = False
    bold: bool = False

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Effects:
    font: Font = field(default_factory=Font)
    justify: Justify = field(default_factory=Justify)
    hide: bool = False

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class TextItem:
    text: str = ""
    effects: Effects = field(default_factory=Effects)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SymbolProperty:
    key: str = ""
    value: str = ""
    id: int = 0
    at: tuple[float, float, float] = (0, 0, 0)
    effects: Effects = field(default_factory=Effects)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class PinAlternate:
    name: str
    electrical_type: PinElectricalType = PinElectricalType.UNSPECIFIED
    graphic_style: PinGraphicStyle = PinGraphicStyle.LINE

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Pin:
    electrical_type: PinElectricalType = PinElectricalType.UNSPECIFIED
    graphic_style: PinGraphicStyle = PinGraphicStyle.LINE
    at: tuple[float, float, float] = (0, 0, 0)
    length: float = 0
    hide: bool = False
    name: TextItem = field(default_factory=TextItem)
    number: TextItem = field(default_factory=TextItem)
    alternate: list[PinAlternate] = field(default_factory=list)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class PinNameSettings:
    offset: Optional[float] = None
    hide: bool = False

    @validator("hide", pre=True)
    def accept_hide_string(s):
        if s == "hide":
            return True
        return s

    # allow for (pin_names hide) on its own
    @root_validator(pre=True)
    def allow_just_hide(cls, values):
        if values.get("offset") == "hide":
            values["offset"] = None
            values["hide"] = True
        return values

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class PinNumberSettings:
    hide: bool = False

    @validator("hide", pre=True)
    def accept_hide_string(s):
        if s == "hide":
            return True
        return s

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SymbolGraphicText:
    text: str
    at: tuple[float, float, float]
    effects: Effects = field(default_factory=Effects)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Symbol:
    name: str
    property: list[SymbolProperty] = field(default_factory=list)
    pin_names: PinNameSettings = field(default_factory=PinNameSettings)
    pin_numbers: PinNumberSettings = field(default_factory=PinNumberSettings)
    in_bom: bool = True
    on_board: bool = True
    power: Optional[IsPresent] = None
    pin: list[Pin] = field(default_factory=list)
    # Symbol is in quotes here to allow for a recursive type
    symbol: list["Symbol"] = field(default_factory=list)
    polyline: list[PolyLine] = field(default_factory=list)
    bezier: list[Bezier] = field(default_factory=list)
    text: list[SymbolGraphicText] = field(default_factory=list)
    rectangle: list[Rectangle] = field(default_factory=list)
    circle: list[Circle] = field(default_factory=list)
    arc: list[Arc] = field(default_factory=list)

    from_list_expr = from_list_expr
