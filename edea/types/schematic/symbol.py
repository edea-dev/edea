"""
Dataclasses describing the symbols found in "lib_symbols" of .kicad_sch files.

SPDX-License-Identifier: EUPL-1.2
"""

from dataclasses import field
from enum import Enum
from typing import Literal, Optional

from pydantic import root_validator, validator
from pydantic.dataclasses import dataclass

from edea.types.base import KicadExpr
from edea.types.config import PydanticConfig
from edea.types.schematic.shapes import Arc, Bezier, Circle, PolyLine, Rectangle


class JustifyHoriz(str, Enum):
    LEFT = "left"
    CENTER = ""
    RIGHT = "right"


class JustifyVert(str, Enum):
    TOP = "top"
    CENTER = ""
    BOTTOM = "bottom"


@dataclass(config=PydanticConfig)
class Justify(KicadExpr):
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
class Font(KicadExpr):
    size: tuple[float, float] = (1.27, 1.27)
    thickness: Optional[float] = None
    italic: bool = False
    bold: bool = False


@dataclass(config=PydanticConfig)
class Effects(KicadExpr):
    font: Font = field(default_factory=Font)
    justify: Justify = field(default_factory=Justify)
    hide: bool = False


@dataclass(config=PydanticConfig)
class PinNumber(KicadExpr):
    text: str = ""
    effects: Effects = field(default_factory=Effects)
    kicad_expr_tag_name: Literal["number"] = "number"


@dataclass(config=PydanticConfig)
class PinName(KicadExpr):
    text: str = ""
    effects: Effects = field(default_factory=Effects)
    kicad_expr_tag_name: Literal["name"] = "name"


@dataclass(config=PydanticConfig)
class SymbolProperty(KicadExpr):
    key: str = ""
    value: str = ""
    id: int = 0
    at: tuple[float, float, float] = (0, 0, 0)
    effects: Effects = field(default_factory=Effects)
    kicad_expr_tag_name: Literal["property"] = "property"


@dataclass(config=PydanticConfig)
class PinAlternate(KicadExpr):
    name: str
    electrical_type: PinElectricalType = PinElectricalType.UNSPECIFIED
    graphic_style: PinGraphicStyle = PinGraphicStyle.LINE
    kicad_expr_tag_name: Literal["alternate"] = "alternate"


@dataclass(config=PydanticConfig)
class Pin(KicadExpr):
    electrical_type: PinElectricalType = PinElectricalType.UNSPECIFIED
    graphic_style: PinGraphicStyle = PinGraphicStyle.LINE
    at: tuple[float, float, float] = (0, 0, 0)
    length: float = 0
    hide: bool = False
    name: PinName = field(default_factory=PinName)
    number: PinNumber = field(default_factory=PinNumber)
    alternate: list[PinAlternate] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class PinNameSettings(KicadExpr):
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

    kicad_expr_tag_name: Literal["pin_names"] = "pin_names"


@dataclass(config=PydanticConfig)
class PinNumberSettings(KicadExpr):
    hide: bool = False

    @validator("hide", pre=True)
    def accept_hide_string(s):
        if s == "hide":
            return True
        return s

    kicad_expr_tag_name: Literal["pin_numbers"] = "pin_numbers"


@dataclass(config=PydanticConfig)
class SymbolGraphicText(KicadExpr):
    text: str
    at: tuple[float, float, float]
    effects: Effects = field(default_factory=Effects)
    kicad_expr_tag_name: Literal["text"] = "text"


@dataclass(config=PydanticConfig)
class IsPower(KicadExpr):
    kicad_expr_tag_name: Literal["power"] = "power"
    # holds no data, appears simply as "(power)" with parens.
    # maybe there is a less ugly solution to this?


@dataclass(config=PydanticConfig)
class Symbol(KicadExpr):
    name: str
    property: list[SymbolProperty] = field(default_factory=list)
    pin_names: PinNameSettings = field(default_factory=PinNameSettings)
    pin_numbers: PinNumberSettings = field(default_factory=PinNumberSettings)
    in_bom: bool = True
    on_board: bool = True
    power: Optional[IsPower] = None
    pin: list[Pin] = field(default_factory=list)
    # Symbol is in quotes here to allow for a recursive type
    symbol: list["Symbol"] = field(default_factory=list)
    polyline: list[PolyLine] = field(default_factory=list)
    bezier: list[Bezier] = field(default_factory=list)
    text: list[SymbolGraphicText] = field(default_factory=list)
    rectangle: list[Rectangle] = field(default_factory=list)
    circle: list[Circle] = field(default_factory=list)
    arc: list[Arc] = field(default_factory=list)
