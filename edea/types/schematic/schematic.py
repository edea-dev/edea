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

from edea.types.config import PydanticConfig
from edea.types.base import KicadExpr
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
class PaperUser(KicadExpr):
    format: Literal["User"] = "User"
    width: float = 0
    height: float = 0
    kicad_expr_tag_name: Literal["paper"] = "paper"


@dataclass(config=PydanticConfig)
class Paper(KicadExpr):
    format: PaperFormat = PaperFormat.A4
    orientation: PaperOrientation = PaperOrientation.LANDSCAPE


@dataclass(config=PydanticConfig)
class PinAssignment(KicadExpr):
    number: str
    uuid: UUID = field(default_factory=uuid4)
    alternate: Optional[str] = None
    kicad_expr_tag_name: Literal["pin"] = "pin"


@dataclass(config=PydanticConfig)
class DefaultInstance(KicadExpr):
    reference: str
    unit: int = 1
    value: str = ""
    footprint: str = ""


@dataclass(config=PydanticConfig)
class IsFieldsAutoplaced(KicadExpr):
    kicad_expr_tag_name: Literal["fields_autoplaced"] = "fields_autoplaced"
    # holds no data, appears simply as "(fields_autoplaced)" with parens.
    # maybe there is a less ugly solution to this?


@dataclass(config=PydanticConfig)
class SymbolPlaced(KicadExpr):
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
    fields_autoplaced: Optional[IsFieldsAutoplaced] = None
    kicad_expr_tag_name: Literal["symbol"] = "symbol"


@dataclass(config=PydanticConfig)
class Wire(KicadExpr):
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    uuid: UUID = field(default_factory=uuid4)


@dataclass(config=PydanticConfig)
class Junction(KicadExpr):
    at: tuple[float, float]
    diameter: float = 0
    color: Color = Color((0, 0, 0, 0))
    uuid: UUID = field(default_factory=uuid4)


@dataclass(config=PydanticConfig)
class NoConnect(KicadExpr):
    at: tuple[float, float]
    uuid: UUID = field(default_factory=uuid4)


@dataclass(config=PydanticConfig)
class LocalLabel(KicadExpr):
    text: str
    at: tuple[float, float, float]
    fields_autoplaced: Optional[IsFieldsAutoplaced] = None
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)
    kicad_expr_tag_name: Literal["label"] = "label"


class LabelShape(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    TRI_STATE = "tri_state"
    PASSIVE = "passive"


@dataclass(config=PydanticConfig)
class GlobalLabel(KicadExpr):
    text: str
    at: tuple[float, float, float]
    shape: LabelShape = LabelShape.BIDIRECTIONAL
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)
    property: list[SymbolProperty] = field(default_factory=list)
    fields_autoplaced: Optional[IsFieldsAutoplaced] = None


@dataclass(config=PydanticConfig)
class HierarchicalLabel(KicadExpr):
    text: str
    at: tuple[float, float, float]
    shape: LabelShape = LabelShape.BIDIRECTIONAL
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)
    fields_autoplaced: Optional[IsFieldsAutoplaced] = None


@dataclass(config=PydanticConfig)
class LibSymbols(KicadExpr):
    symbol: list[Symbol] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class TitleBlockComment(KicadExpr):
    number: int = 1
    text: str = ""
    kicad_expr_tag_name: Literal["comment"] = "comment"


@dataclass(config=PydanticConfig)
class TitleBlock(KicadExpr):
    title: str = ""
    date: str = ""
    rev: str = ""
    company: str = ""
    comment: list[TitleBlockComment] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class SheetPath(KicadExpr):
    path: str = "/"
    page: str = "1"
    kicad_expr_tag_name: Literal["path"] = "path"


@dataclass(config=PydanticConfig)
class SheetInstances(KicadExpr):
    path: list[SheetPath] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class SymbolInstancesPath(KicadExpr):
    path: str
    reference: str
    unit: int
    value: str
    footprint: str = ""
    kicad_expr_tag_name: Literal["path"] = "path"


@dataclass(config=PydanticConfig)
class SymbolInstances(KicadExpr):
    path: list[SymbolInstancesPath] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class PolyLineTopLevel(KicadExpr):
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    fill: Fill = field(default_factory=Fill)
    uuid: UUID = field(default_factory=uuid4)
    kicad_expr_tag_name: Literal["polyline"] = "polyline"


@dataclass(config=PydanticConfig)
class FillColor(KicadExpr):
    color: Color = Color((0, 0, 0, 0))
    kicad_expr_tag_name: Literal["fill"] = "fill"


@dataclass(config=PydanticConfig)
class SheetPin(KicadExpr):
    name: str
    shape: LabelShape = LabelShape.BIDIRECTIONAL
    at: tuple[float, float, float] = (0, 0, 0)
    effects: Effects = field(default_factory=Effects)
    uuid: UUID = field(default_factory=uuid4)
    kicad_expr_tag_name: Literal["pin"] = "pin"


@dataclass(config=PydanticConfig)
class Sheet(KicadExpr):
    at: tuple[float, float]
    size: tuple[float, float]
    stroke: Stroke = field(default_factory=Stroke)
    fill: FillColor = field(default_factory=FillColor)
    uuid: UUID = field(default_factory=uuid4)
    property: list[SymbolProperty] = field(default_factory=list)
    pin: list[SheetPin] = field(default_factory=list)
    fields_autoplaced: Optional[IsFieldsAutoplaced] = None


@dataclass(config=PydanticConfig)
class BusEntry(KicadExpr):
    at: tuple[float, float]
    size: tuple[float, float]
    stroke: Stroke = field(default_factory=Stroke)
    uuid: UUID = field(default_factory=uuid4)


@dataclass(config=PydanticConfig)
class Bus(KicadExpr):
    pts: Pts = field(default_factory=Pts)
    stroke: Stroke = field(default_factory=Stroke)
    uuid: UUID = field(default_factory=uuid4)


@dataclass(config=PydanticConfig)
class Image(KicadExpr):
    at: tuple[float, float]
    scale: Optional[float] = None
    uuid: UUID = field(default_factory=uuid4)
    data: list[str] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class BusAlias(KicadExpr):
    name: str
    members: list[str] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Schematic(KicadExpr):
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

    kicad_expr_tag_name: Literal["kicad_sch"] = "kicad_sch"
