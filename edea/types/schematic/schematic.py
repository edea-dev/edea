"""
Dataclasses describing the contents of .kicad_sch files.

SPDX-License-Identifier: EUPL-1.2
"""
from dataclasses import field
from enum import Enum
from typing import Optional, Literal, Union
from uuid import UUID, uuid4

from pydantic import validator
from pydantic.color import Color
from pydantic.dataclasses import dataclass

from edea.types.config import PydanticConfig, IsPresent
from edea.types.from_list_expr import from_list_expr
from edea.types.schematic.shapes import Pts, Stroke, Fill
from edea.types.schematic.symbol import Effects, Symbol, SymbolProperty


class PaperFormat(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    US_LETTER = "USLetter"
    US_LEGAL = "USLegal"
    US_LEDGER = "USLedger"


class PaperOrientation(str, Enum):
    LANDSCAPE = ""
    PORTRAIT = "portrait"


@dataclass(config=PydanticConfig)
class PaperUser:
    format: Literal["User"] = "User"
    width: float = 0
    height: float = 0

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Paper:
    format: PaperFormat = PaperFormat.A4
    orientation: PaperOrientation = PaperOrientation.LANDSCAPE

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class PinAssignment:
    number: str
    uuid: UUID = field(default_factory=uuid4)
    alternate: Optional[str] = None

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class DefaultInstance:
    reference: str
    unit: int = 1
    value: str = ""
    footprint: str = ""

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SymbolPlaced:
    lib_id: str
    lib_name: Optional[str] = None
    at: tuple[float, float, float] = (0, 0, 0)
    unit: int = 1
    convert: Optional[int] = None
    in_bom: bool = True
    on_board: bool = True
    mirror: bool = False
    uuid: UUID = field(default_factory=uuid4)
    default_instance: Optional[DefaultInstance] = None
    property: list[SymbolProperty] = field(default_factory=list)
    pin: list[PinAssignment] = field(default_factory=list)
    fields_autoplaced: Optional[IsPresent] = None

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Wire:
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Junction:
    at: tuple[float, float]
    diameter: float = 0
    color: Color = Color((0, 0, 0, 0))
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class NoConnect:
    at: tuple[float, float]
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class LocalLabel:
    text: str
    at: tuple[float, float, float]
    fields_autoplaced: Optional[IsPresent] = None
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


class LabelShape(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    TRI_STATE = "tri_state"
    PASSIVE = "passive"


@dataclass(config=PydanticConfig)
class GlobalLabel:
    text: str
    at: tuple[float, float, float]
    shape: LabelShape = LabelShape.BIDIRECTIONAL
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)
    property: list[SymbolProperty] = field(default_factory=list)
    fields_autoplaced: Optional[IsPresent] = None

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class HierarchicalLabel:
    text: str
    at: tuple[float, float, float]
    shape: LabelShape = LabelShape.BIDIRECTIONAL
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)
    fields_autoplaced: Optional[IsPresent] = None

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class LibSymbols:
    symbol: list[Symbol] = field(default_factory=list)
    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class TitleBlockComment:
    number: int = 1
    text: str = ""
    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class TitleBlock:
    title: str = ""
    date: str = ""
    rev: str = ""
    company: str = ""
    comment: list[TitleBlockComment] = field(default_factory=list)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SheetPath:
    path: str = "/"
    page: str = "1"

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SheetInstances:
    path: list[SheetPath] = field(default_factory=list)
    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SymbolInstancesPath:
    path: str
    reference: str
    unit: int
    value: str
    footprint: str = ""

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SymbolInstances:
    path: list[SymbolInstancesPath] = field(default_factory=list)
    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class PolyLineTopLevel:
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class FillColor:
    color: Color = Color((0, 0, 0, 0))
    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class SheetPin:
    name: str
    shape: LabelShape = LabelShape.BIDIRECTIONAL
    at: tuple[float, float, float] = (0, 0, 0)
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Sheet:
    at: tuple[float, float]
    size: tuple[float, float]
    stroke: Stroke = field(default_factory=Stroke)
    fill: FillColor = field(default_factory=FillColor)
    uuid: UUID = field(default_factory=uuid4)
    property: list[SymbolProperty] = field(default_factory=list)
    pin: list[SheetPin] = field(default_factory=list)
    fields_autoplaced: Optional[IsPresent] = None

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class BusEntry:
    at: tuple[float, float]
    size: tuple[float, float]
    stroke: Stroke = field(default_factory=Stroke)
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Bus:
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    uuid: UUID = field(default_factory=uuid4)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Image:
    at: tuple[float, float]
    scale: Optional[float] = None
    uuid: UUID = field(default_factory=uuid4)
    data: list[str] = field(default_factory=list)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class BusAlias:
    name: str
    members: list[str] = field(default_factory=list)

    from_list_expr = from_list_expr


@dataclass(config=PydanticConfig)
class Schematic:
    version: int = 20211123

    @validator("version")
    def check_version(cls, v):
        if v != 20211123:
            raise ValueError(
                f"Only the stable KiCad 6 schematic file format, i.e. version '20211123', "
                f"is supported. Got '{v}'."
            )
        return v

    generator: str = "edea"
    uuid: UUID = field(default_factory=uuid4)
    title_block: Optional[TitleBlock] = None
    paper: Union[Paper, PaperUser] = field(default_factory=Paper)
    lib_symbols: LibSymbols = field(default_factory=LibSymbols)
    sheet: list[Sheet] = field(default_factory=list)
    symbol: list[SymbolPlaced] = field(default_factory=list)
    polyline: list[PolyLineTopLevel] = field(default_factory=list)
    wire: list[Wire] = field(default_factory=list)
    bus: list[Bus] = field(default_factory=list)
    image: list[Image] = field(default_factory=list)
    junction: list[Junction] = field(default_factory=list)
    no_connect: list[NoConnect] = field(default_factory=list)
    bus_entry: list[BusEntry] = field(default_factory=list)
    text: list[LocalLabel] = field(default_factory=list)
    label: list[LocalLabel] = field(default_factory=list)
    hierarchical_label: list[HierarchicalLabel] = field(default_factory=list)
    global_label: list[GlobalLabel] = field(default_factory=list)
    sheet_instances: SheetInstances = field(default_factory=SheetInstances)
    symbol_instances: SymbolInstances = field(default_factory=SymbolInstances)
    bus_alias: list[BusAlias] = field(default_factory=list)

    from_list_expr = from_list_expr
