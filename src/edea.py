"""
it's a kicad parser! it's edea! it's the kicad parser and edea tooling!

This contains a KiCAD parser with a minimalistic approach that should hopefully be easy to use. There's a lot of code
manipulating kicad data structures, so it's hopefully not too hard to pick up what it's doing.

SPDX-License-Identifier: EUPL-1.2
"""
from __future__ import annotations

import os
import re
from collections import UserList
from dataclasses import dataclass
from itertools import filterfalse, groupby
from math import sin, cos, tau
from operator import methodcaller
from typing import Tuple, Union
from uuid import uuid4

import numpy as np

Symbol = str
Number = (int, float)
Atom = (Symbol, Number)

to_be_moved = ["module", "gr_text", "gr_poly", "gr_line", "gr_arc", "via", "segment", "dimension", "gr_circle",
               "gr_curve", "arc", ]

movable_types = ["at", "xy", "start", "end", "center"]
drawable_types = ["pin", "polyline", "rectangle"]

lib_symbols = {}

TOKENIZE_EXPR = re.compile(r'("[^"]*"|\(|\)|"|[^\s()"]+)')


class BoundingBox:
    """
    BoundingBox for computing the upright 2D bounding box for a set of
    2D coordinates in a (n,2) numpy array.
    You can access the bbox using the
    (min_x, max_x, min_y, max_y) members.
    """
    def __init__(self, points):
        self.max_y = None
        self.min_y = None
        self.max_x = None
        self.min_x = None
        self._valid = None
        self.reset()
        self.envelop(points)

    @staticmethod
    def rot(point, angle):
        """rotate the point at xy by an angle"""
        point_x, point_y = point
        angle_sin, angle_cos = sin(angle), cos(angle)
        x_out = point_x * angle_cos + point_y * angle_sin
        y_out = point_y * angle_cos + point_x * angle_sin
        return [x_out, y_out]

    def envelop(self, points):
        """
        Envelop the existing bounding box with new points
        This might need optimization, we're doing some unnecessary
        math for the sake of programmatic simplicity
        """
        if points is None or len(points) == 0:
            return
        if len(points.shape) != 2 or points.shape[1] != 2:
            raise ValueError(
                f"Points must be a (n,2), array but it has shape {points.shape}"
            )
        if self._valid:
            extended = np.concatenate((points, self.corners))
        else:
            extended = points
        self._valid = True
        self.min_x, self.min_y = np.min(extended, axis=0)
        self.max_x, self.max_y = np.max(extended, axis=0)

    def translate(self, coords):
        """
        move the bounding box by [x y]
        this is used for coordinate system transformation
        """
        if self._valid:
            self.min_x += coords[0]
            self.max_x += coords[0]
            self.min_y += coords[1]
            self.max_y += coords[1]

    def reset(self):
        """reset the BoundingBox"""
        self.min_x, self.min_y = float("inf") * np.array([1, 1], dtype=np.float64)
        self.max_x, self.max_y = float("inf") * np.array([-1, -1], dtype=np.float64)
        self._valid = False

    def rotate(self, angle):
        """
        rotate the box around the origin. angle is in degrees
        """
        if self._valid:
            corners = self.corners
            rotated = np.zeros((4, 2), dtype=np.float64)
            angle = angle / tau
            angle_sin, angle_cos = sin(angle), cos(angle)
            for i in enumerate(corners):
                x_out = corners[i][0] * angle_cos + corners[i][1] * angle_sin
                y_out = corners[i][1] * angle_cos + corners[i][0] * angle_sin
                rotated[i] = [x_out, y_out]
            self.reset()
            self.envelop(rotated)

    @property
    def corners(self):
        """
        If the bounding box is empty, this returns None.
        Returns all four corners of this rectangle in a [4][2] float64 array
        """
        if self._valid:
            return np.array(
                [
                    [self.min_x, self.min_y],
                    [self.min_x, self.max_y],
                    [self.max_x, self.max_y],
                    [self.max_x, self.min_y],
                ],
                dtype=np.float64,
            )
        return None  # np.array([[]])

    @property
    def valid(self):
        """returns True if the BoundBox has been calculated yet"""
        return self._valid

    @property
    def width(self):
        """X-axis extent of the bounding box"""
        if self._valid:
            return self.max_x - self.min_x

        return 0

    @property
    def height(self):
        """Y-axis extent of the bounding box"""
        if self._valid:
            return self.max_y - self.min_y

        return 0

    @property
    def area(self):
        """width * height"""
        return self.width * self.height

    @property
    def center(self):
        """(x,y) center point of the bounding box"""
        if self._valid:
            return self.min_x + self.width / 2, self.min_y + self.height / 2

        return False  # I don't want to return 0,0

    def __repr__(self):
        if not self._valid:
            return "boundingbox empty"

        val = f"boundingbox([{self.min_x:03.2f}x, {self.min_y:03.2f}y] -> [{self.max_x:03.2f}x, {self.max_y:03.2f}y])"
        return val




@dataclass
class Expr(UserList):
    """Expr lisp-y kicad expressions"""
    name: str
    data: list

    _more_than_once: set
    _known_attrs: set

    def __init__(self, typ: str, *args) -> None:
        """ __init__ builds a new pin with typ as the type
        passing additional arguments will append them to the list and Expr.parsed() will be called afterwards
        to update the internals.
        """
        super().__init__()
        self.name = typ
        self._known_attrs = set()
        self._more_than_once = set()

        # optionally initialize with anything thrown at init
        if len(args) > 0:
            self.extend(args)
            self.parsed()

    def __str__(self) -> str:
        sub = " ".join(map(methodcaller("__str__"), self.data))
        return f"({self.name} {sub})"

    def apply(self, cls, func) -> None:
        """
        call func on all objects in data recursively which match the type

        to call an instance method, just use e.g. v.apply(Pad, methodcaller("move_xy", x, y))
        """
        if isinstance(self, cls):
            func(self)

        if len(self.data) > 0:
            for item in self.data:
                if isinstance(item, Expr):
                    item.apply(cls, func)

    def parsed(self):
        """subclasses can parse additional stuff out of data now"""
        for item in self.data:
            if not isinstance(item, Expr):
                continue

            if item.name in self._known_attrs:
                if item.name not in self._more_than_once:
                    self._more_than_once.add(item.name)
            else:
                self._known_attrs.add(item.name)

    def __getattr__(self, name) -> list | dict | str:
        """
        make items from data callable via the attribute syntax
        this allows us to work with sub-expressions just like one would intuitively expect it
        combined with the index operator we can do things like: effects.font.size[0]
        this is much less verbose and conveys intent instantly.
        """
        if name not in self._known_attrs:
            raise AttributeError(f"no attribute {name} in {self.name}")

        if name not in self._more_than_once:
            for item in self.data:
                if isinstance(item, str):
                    if item == name:
                        return item
                elif item.name == name:
                    return item

        dict_items = {}
        items = []
        skip = False

        # use data[0] as dict key in case there's no duplicates
        # this allows us to access e.g. properties by their key
        for item in self.data:
            if item.name == name:
                if not skip:
                    if isinstance(item[0], Expr) or item[0] in dict_items:
                        skip = True
                    else:
                        dict_items[item[0].strip('"')] = item
                items.append(item)

        if not skip:
            return dict_items
        return items

    def __eq__(self, other) -> bool:
        """Overrides the default implementation"""
        if len(self.data) != 1:
            raise NotImplementedError

        if other is True or other is False:
            return self[0] == "yes" and other
        if isinstance(other, Number):
            return self[0] == other.number

        return False

    def startswith(self, prefix):
        """startswith implements prefix comparison for single element lists"""
        if len(self.data) != 1:
            raise NotImplementedError

        return self[0].startswith(prefix)


@dataclass(init=False)
class Movable(Expr):
    """Movable is an object with a position"""

    def move_xy(self, x: float, y: float) -> None:
        """move_xy adds the position offset x and y to the object"""
        self.data[0] += x
        self.data[1] += y


@dataclass(init=False)
class Pad(Movable):
    """Pad"""

    @property
    def corners(self):
        """Returns a numpy array containing every corner [x,y]
        """
        if len(self.at) > 2:
            angle = self.at[2] / tau
        else:
            angle = 0
        origin = self.at[0:2]

        if self.name in ["rect", "roundrect", "oval", "custom"]:
            # TODO optimize this, this is called quite often

            points = np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]], dtype=np.float64)
            if self[2] == "oval":
                points = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=np.float64)
            w = self.size[0] / 2
            h = self.size[1] / 2
            angle_cos = cos(angle)
            angle_sin = sin(angle)
            for i in enumerate(points):
                points[i] = origin + points[i] * [(w * angle_cos + h * angle_sin), (h * angle_cos + w * angle_sin)]

        elif self[2] == "circle":
            points = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=np.float64)
            radius = self.size[0] / 2
            for i in enumerate(points):
                points[i] = origin + points[i] * [radius, radius]
        else:
            raise NotImplementedError(f"pad shape {self[2]} is not implemented")

        return points


@dataclass(init=False)
class Module(Movable):
    """Module"""

    @property
    def bounding_box(self) -> BoundingBox:
        """return the BoundingBox"""
        if not hasattr(self, "pad"):
            box = BoundingBox([])
        else:
            box = BoundingBox(self.pad[0].corners)

        if len(self.pad) > 1:
            for i in range(1, len(self.pad)):
                box.envelop(self.pad[i].corners)

        if len(self.at) > 2:
            box.rotate(self.at[2])
        box.translate(self.at[0:2])
        return box


@dataclass(init=False)
class Drawable(Movable):
    """
    Drawable is an object which can be converted to an SVG
    pin: line with text
    polyline: symbols drawn with line(s), e.g. the ground symbol
    rectangle: usually ic symbols
    """

    def draw(self, position: Tuple[float, float]):
        """draw the shape with the given offset"""
        if self.name == "pin":
            # raise NotImplementedError(self.name)
            pass
        elif self.name == "polyline":
            frag = '<polyline points="'
            for point in self.data[0]:
                frag += f"{point.data[0]},{point.data[1]} "
            # TODO: stroke and fill
            print(f'{frag}" />')
        elif self.name == "rectangle":
            x_start = self.start[0]
            y_start = self.start[1]
            x_end = self.end[0]
            y_end = self.end[1]
            print(
                f'<rect x="{x_start + position[0]}" y="{y_start + position[1]}" width="{x_start - x_end}" height="{y_start - y_end}" />')
        else:
            raise NotImplementedError(self.name)


def from_str(program: str) -> Expr:
    """Parse KiCAD s-expr from a string"""
    tokens = TOKENIZE_EXPR.findall(program)
    return from_tokens(tokens, "")


def from_tokens(tokens: list, parent: str) -> Union[Expr, int, float, str]:
    """Read an expression from a sequence of tokens."""
    if len(tokens) == 0:
        raise SyntaxError("unexpected EOF")
    token = tokens.pop(0)

    if token == "(":
        expr: Expr
        typ = tokens.pop(0)

        # TODO: handle more types here
        if typ in movable_types and parent in to_be_moved:
            expr = Movable(typ)
        elif typ in drawable_types:
            expr = Drawable(typ)
        else:
            expr = Expr(typ)

        while tokens[0] != ")":
            expr.append(from_tokens(tokens, expr.name))
        tokens.pop(0)  # remove ')'

        expr.parsed()

        return expr

    if token == ")":
        raise SyntaxError("unexpected )")

    # Numbers become numbers, every other token is a symbol
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)


class Schematic:
    """ Schematic
    Representation of a kicad schematic
    """
    _sch: Expr
    file_name: str
    name: str

    def __init__(self, sch: Expr, name: str, file_name: str):
        self._sch = sch
        self.name = name
        self.file_name = file_name

    def as_expr(self) -> Expr:
        """ return the schematic as an Expr """
        return self._sch

    def to_sheet(self, sheet_name: str, file_name: str, pos_x=20.0, pos_y=20.0) -> Expr:
        """ to_sheet extracts all hierarchical labels and generates a new sheet object from them
        """

        if hasattr(self._sch, "hierarchical_label"):
            labels = self._sch.hierarchical_label
            len_longest_label =len(max(labels.keys(), key=len))
        else:
            len_longest_label = 0
            labels = {}

        # width of the hierarchical sheet, length of longest pin name or min 5 chars wide

        lbl_space = max(len_longest_label, 4) + 1
        width = lbl_space * 1.27
        height = (len(labels) + 1) * 2.54

        sheet = Expr("sheet", Expr("at", pos_x, pos_y), Expr("size", width, height),
                     Expr("fields_autoplaced"), from_str("(stroke (width 0) (type solid) (color 0 0 0 0))"),
                     from_str("(fill (color 0 0 0 0.0000))"), Expr("uuid", uuid4()),
                     Expr("property", '"Sheet name"', f'"{sheet_name}"', Expr("id", 0), Expr("at", pos_x, pos_y, 0),
                          from_str("(effects (font (size 1.27 1.27)) (justify left bottom))")),
                     Expr("property", '"Sheet file"', f'"{file_name}"', Expr("id", 1),
                          Expr("at", pos_x, pos_y + height + 2.54, 0),
                          from_str("(effects (font (size 1.27 1.27)) (justify left bottom))")))
        i = 0
        for label in labels.values():
            # build a new pin, (at x y angle)
            i += 1
            sheet.append(Expr("pin", label[0], label.shape[0], Expr("at", pos_x, pos_y + i * 2.54, 0),
                              from_str("(effects (font (size 1.27 1.27)) (justify right))"), Expr("uuid", uuid4())))

        return sheet

    @staticmethod
    def empty() -> Schematic:
        """empty_schematic returns a minimal KiCad schematic
        """
        sch = Expr("kicad_sch", Expr("version", 20211123), Expr("generator", "edea"), Expr("uuid", uuid4()),
                   Expr("paper", "A4"), Expr("lib_symbols"),
                   Expr("sheet_instances", Expr("path", '"/"', Expr("page", '"1"'))))
        return Schematic(sch, "", "")

    def append(self, schematic: Schematic, name=""):
        """
        here's the problem: append needs the filename of the other schematic, but also a name which it should reference
        this schematic by. i think we should take the file name from the file and make the name an optional parameter.
        """
        max_page: str
        # find the max page number
        sheet = schematic.to_sheet(name if name != "" else schematic.name, schematic.file_name)
        for instance in self._sch.sheet_instances:
            max_page = instance.page[0]

        new_page = int(max_page[1:-1]) + 1

        # append sheet and create a new instance
        self._sch.append(sheet)
        self._sch.sheet_instances.append(
            Expr("path", f'"/{sheet.uuid}"', Expr("page", f'"{new_page}"')),
        )


class Project:
    """KiCAD project
    nya
    """

    schematics = {}
    fn_to_uuid = {}
    symbol_instances = {}
    top: str
    sheets: int  # sheets is the amount of schematics including all instances of sub-schematics

    def __init__(self, file_name) -> None:
        self.file_name = file_name

    def parse(self):
        """parse the base schematic"""
        with open(self.file_name, encoding="utf-8") as sch_file:
            sch = from_str(sch_file.read())

        # loop through symbol instances and extract a tree for uuid to reference
        if hasattr(sch, "symbol_instances"):
            for path in sch.symbol_instances:
                reference = path[1][0][1:-1]

                # skip virtual items, e.g. GND symbols
                if reference[0] == "#":
                    continue

                symbol_id = list(filter(None, path[0][1:-1].split("/")))[-1]

                if symbol_id in self.symbol_instances:
                    self.symbol_instances[symbol_id].append(reference)
                else:
                    self.symbol_instances[symbol_id] = [reference]

        self.top = sch.uuid[0]
        self._parse_sheet(sch, self.file_name)

    def _parse_sheet(self, sch: Expr, file_name: str):
        """recursively parse schematic sub-sheets"""
        uuid = sch.uuid[0]
        self.schematics[uuid] = Schematic(sch, "", file_name)
        self.fn_to_uuid[os.path.basename(file_name)] = uuid

        dir_name = os.path.dirname(self.file_name)

        if not hasattr(sch, "sheet"):
            return

        for sheet in sch.sheet:
            prop = sheet.property
            sheet_file = prop["Sheet file"][1].strip('"')
            if os.path.basename(sheet_file) not in self.fn_to_uuid:
                with open(os.path.join(dir_name, sheet_file), encoding="utf-8") as sch_file:
                    print(f"reading {sheet_file}")
                    sub = from_str(sch_file.read())

                self._parse_sheet(sub, sheet_file)

    @staticmethod
    def _key_unique_part(sym: Expr) -> str:
        """key function to group by footprint and value or mpn"""
        props = sym.property
        if hasattr(props, "MPN"):
            return props["MPN"][1]
        if hasattr(props, "LCSC"):
            return props["LCSC"][1]

        return props["Value"][1] + props["Footprint"][1]

    def metadata(self) -> dict:
        """parse metadata from the schematic"""
        self.sheets = 0
        parts = []
        top = self.schematics[self.top].as_expr()

        parts += self._get_parts(top, f"/{top.uuid}")

        groups = []  # parts with the same footprint and value
        unique_keys = []  # part keys, footprint + value or MPN if set
        for k, g in groupby(parts, key=Project._key_unique_part):
            groups.append(list(g))  # Store group iterator as a list
            unique_keys.append(k)

        bom_parts = {}

        for sym in parts:
            # expand the properties and add list of instances
            properties = {}
            for prop in sym.property:
                properties[prop] = sym.property[prop][1][1:-1]

            properties["Reference"] = self.symbol_instances[sym.uuid[0]]

            bom_parts[sym.uuid[0]] = properties

        bom = {"count_part": len(parts), "count_unique": len(unique_keys), "parts": bom_parts, "sheets": self.sheets, }

        return bom

    def _get_parts(self, sch, path) -> list:
        self.sheets += 1

        # don't trust the linter, it's telling lies here
        parts = list(
            filterfalse(lambda sym: sym.property["Reference"][1].startswith('"#') or sym.in_bom is False, sch.symbol, ))

        # recurse sub-schematics
        if hasattr(sch, "sheet"):
            for sheet in sch.sheet:
                prop = sheet.property
                sheet_fn = prop["Sheet file"][1].strip('"')
                sch = self.schematics[self.fn_to_uuid[sheet_fn]].as_expr()
                parts += self._get_parts(sch, f"{path}/{sch.uuid}")

        return parts
