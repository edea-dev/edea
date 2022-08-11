"""
KiCad file format parser

SPDX-License-Identifier: EUPL-1.2
"""
from __future__ import annotations

import re
from collections import UserList
from dataclasses import dataclass
from math import tau, cos, sin
from typing import Tuple, Union, Dict
from uuid import uuid4, UUID
from _operator import methodcaller

import numpy as np

from .bbox import BoundingBox

Symbol = str
Number = (int, float)
Atom = (Symbol, Number)

# types which have children with absolute coordinates
to_be_moved = ["footprint", "gr_text", "gr_poly", "gr_line", "gr_arc", "via", "segment", "dimension", "gr_circle",
               "gr_curve", "arc", "polygon", "filled_polygon"]  # pts is handled separately
skip_move = ["primitives"]

# types which should be moved if their parent is in the set of "to_be_moved"
movable_types = ["at", "xy", "start", "end", "center", "mid"]

drawable_types = ["pin", "polyline", "rectangle"]
lib_symbols = {}
TOKENIZE_EXPR = re.compile(r'("[^"\\]*(?:\\.[^"\\]*)*"|\(|\)|"|[^\s()"]+)')


@dataclass
class Expr(UserList):
    """Expr lisp-y kicad expressions"""
    __slots__ = ("name", "data", "_more_than_once", "_known_attrs")

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
        return f"\n({self.name} {sub})"

    def apply(self, cls, func) -> list | None:
        """
        call func on all objects in data recursively which match the type

        to call an instance method, just use e.g. v.apply(Pad, methodcaller("move_xy", x, y))
        """
        vals = []
        ret = None

        if isinstance(self, cls):
            ret = func(self)
            if ret is not None:
                vals.append(ret)

        if len(self.data) > 0:
            for item in self.data:
                if isinstance(item, Expr):
                    ret = item.apply(cls, func)
                    if ret is not None:
                        vals.append(ret)

        if len(vals) == 0:
            return None
        return vals

    def parsed(self):
        """subclasses can parse additional stuff out of data now"""
        # TODO: currently modifying the object and accessing fields again is not handled
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
class Pts(Movable):
    """Movable is an object with a position"""

    def move_xy(self, x: float, y: float) -> None:
        """move_xy adds the position offset x and y to the object"""
        for point in self.data:
            if point.name == "xy":
                point.data[0] += x
                point.data[1] += y


@dataclass(init=False)
class Pad(Expr):
    """Pad"""

    def corners(self):
        """Returns a numpy array containing every corner [x,y]
        """
        if len(self.at) > 2:
            angle = self.at.data[2] / tau
        else:
            angle = 0
        origin = self.at.data[0:2]  # in this case we explicitly need to access the data list because of the range op
        # otherwise it would return a list of Expr

        if self[2] in ["rect", "roundrect", "oval", "custom"]:
            # TODO optimize this, this is called quite often

            points = np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]], dtype=np.float64)
            if self[2] == "oval":
                points = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=np.float64)
            w = self.size.data[0] / 2
            h = self.size.data[1] / 2
            angle_cos = cos(angle)
            angle_sin = sin(angle)
            for i, _ in enumerate(points):
                points[i] = origin + points[i] * [(w * angle_cos + h * angle_sin), (h * angle_cos + w * angle_sin)]

        elif self[2] == "circle":
            points = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=np.float64)
            radius = self.size.data[0] / 2
            for i, _ in enumerate(points):
                points[i] = origin + points[i] * [radius, radius]
        else:
            raise NotImplementedError(f"pad shape {self[2]} is not implemented")

        return points


@dataclass(init=False)
class FPLine(Expr):
    """FPLine"""

    def corners(self):
        """ corners returns start and end of the FPLine
        """
        points = np.array([[self.start[0], self.start[1]], [self.end[0], self.end[1]]],
                          dtype=np.float64)
        return points


@dataclass(init=False)
class Polygon(Expr):
    """Polygon
    TODO: Zone polygons are with absolute positions, are there other types?
    """

    def bounding_box(self) -> BoundingBox:
        """ bounding_box of the polygon
        """
        return BoundingBox(self.corners())

    def corners(self) -> np.array:
        """ corners returns the min and max points of a polygon
        """
        x_points = []
        y_points = []

        for point in self.pts:
            if point.name != "xy":
                raise NotImplementedError(f"the following polygon format isn't implemented yet: {point}")
            x_points.append(point[0])
            y_points.append(point[1])

        npx = np.array(x_points)
        npy = np.array(y_points)

        max_x = np.amax(npx)
        min_x = np.amin(npx)
        max_y = np.amax(npy)
        min_y = np.amin(npy)

        return np.array([[min_x, min_y], [min_x, max_y], [max_x, max_y], [max_x, min_y], ], dtype=np.float64)


@dataclass(init=False)
class Footprint(Expr):
    """Footprint"""

    def bounding_box(self) -> BoundingBox:
        """return the BoundingBox"""
        box = BoundingBox([])
        if hasattr(self, "pad"):
            # check if it's a single pad only
            if isinstance(self.pad, list):
                _ = [box.envelop(pad.corners()) for pad in self.pad]
            else:
                box.envelop(self.pad.corners())

            if len(self.at.data) > 2:
                box.rotate(self.at.data[2])
            box.translate(self.at.data[0:2])

        if hasattr(self, "fp_line"):
            # check if it's a single line only
            if isinstance(self.fp_line, list):
                _ = [box.envelop(pad.corners()) for pad in self.pad]
            else:
                box.envelop(self.fp_line.corners())

            if len(self.at.data) > 2:
                box.rotate(self.at.data[2])
            box.translate(self.at.data[0:2])

        # TODO(ln): implement other types too, though pads and lines should work well enough

        return box

    def prepend_path(self, path: str):
        """ prepend_path prepends the uuid path to the current one
        """
        # path is always in the format of /<uuid>[/<uuid>]
        sub = self.path.data[0].strip('"')
        self.path.data[0] = f"\"/{path}{sub}\""


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
                # rounding is necessary because otherwise you get 
                # numbers ending with .9999999999 due to floating point precision :/
                frag += f"{round(point.data[0] + position[0], 3)},{round(point.data[1] + position[1], 3)} "
            return f'{frag}" {self.parse_visual()}/>'
        elif self.name == "rectangle":
            x_start = self.start[0]
            y_start = self.start[1]
            x_end = self.end[0]
            y_end = self.end[1]
            return (
                f'<rect x="{round(x_start + position[0], 3)}" y="{round(y_start + position[1], 3)}" '
                f'width="{round(x_end - x_start, 3)}" height="{round(y_end - y_start, 3)}" {self.parse_visual()}/>'   
            )
        else:
            raise NotImplementedError(self.name)

    def parse_visual(self):
        """parse fill/stroke, if present"""
        attrs = ""
        if hasattr(self, 'stroke'):
            color, opacity = parse_color(self.stroke.color)
            attrs += f'stroke="rgb({color})" stroke-opacity="{opacity}" stroke-width="{self.stroke.width[0]}" '
            
            match self.stroke.type[0]:
                case ("default"|"solid"):
                    pass
                case "dot":
                    attrs += 'stroke-dasharray="1" '
                case "dash":
                    attrs += 'stroke-dasharray="3 1" '
                case "dash_dot":
                    attrs += 'stroke-dasharray="3 1 1 1" '
                case "dash_dot_dot":
                    attrs += 'stroke-dasharray="3 1 1 1 1 1" '
        if hasattr(self, 'fill'):
            match self.fill.type[0]:
                case "none":
                    attrs += 'fill="none" '
                case "background":
                    # TODO: figure out how to access theme background
                    pass
                case "outline":
                    color, opacity = parse_color(self.stroke.color)
                    attrs += f'fill="rgb({color})" fill-opacity="{opacity}" '
        return attrs
        

def parse_color(color: list):
        """converts `r g b a` to a tuple of `(r,g,b)` and `alpha`"""
        return (f"{color[0]},{color[1]},{color[2]}", color[3])
    

@dataclass(init=False)
class TStamp(Expr):
    """
    TStamp UUIDv4 identifiers which replace the pcbnew v5 timestamp base ones
    """

    def randomize(self):
        """randomize the tstamp UUID
        """
        # parse the old uuid first to catch edgecases
        _ = UUID(self.data[0])
        # generate a new random UUIDv4
        self.data[0] = str(uuid4())


@dataclass(init=False)
class Net(Expr):

    def rename(self, numbers: Dict[int, int], names: Dict[str, str]):
        """ rename and/or re-number a net

        A net type is either net_name with only the name (net_name "abcd"), net with only the number (net 42)
        of net with number and name (net 42 "abcd")
        """
        name_offset = 0
        if self.name == "net_name":
            net_name = self.data[0]
            net_number = None
        elif self.name == "net" and len(self.data) == 1:
            net_name = None
            net_number = self.data[0]
        else:
            name_offset = 1
            net_name = self.data[1]
            net_number = self.data[0]

        if net_name in names:
            self.data[name_offset] = names[net_name]
        if net_number in numbers:
            self.data[0] = numbers[net_number]


def from_str(program: str) -> Expr:
    """Parse KiCAD s-expr from a string"""
    tokens = TOKENIZE_EXPR.findall(program)
    _, expr = from_tokens(tokens, 0, "", "")
    return expr


def from_tokens(tokens: list, index: int, parent: str, grand_parent: str) -> Tuple[int, Union[Expr, int, float, str]]:
    """Read an expression from a sequence of tokens."""
    if len(tokens) == index:
        raise SyntaxError("unexpected EOF")
    token = tokens[index]
    index += 1

    if token == "(":
        expr: Expr
        typ = tokens[index]
        index += 1

        # TODO: handle more types here
        if typ in drawable_types:
            expr = Drawable(typ)
        elif typ == "pad":
            expr = Pad(typ)
        elif typ == "footprint":
            expr = Footprint(typ)
        elif typ == "fp_line":
            expr = FPLine(typ)
        elif typ in ["polygon", "filled_polygon"]:
            expr = Polygon(typ)
        elif typ == "pts" and parent in to_be_moved and grand_parent not in skip_move:
            expr = Pts(typ)
        elif typ in movable_types and parent in to_be_moved:
            expr = Movable(typ)
        elif typ == "tstamp":
            expr = TStamp(typ)
        else:
            expr = Expr(typ)

        while tokens[index] != ")":
            index, sub_expr = from_tokens(tokens, index, expr.name, parent)
            expr.append(sub_expr)
        index += 1  # remove ')'

        expr.parsed()

        return (index, expr)

    if token == ")":
        raise SyntaxError("unexpected )")

    # Numbers become numbers, every other token is a symbol
    try:
        return (index, int(token))
    except ValueError:
        try:
            return (index, float(token))
        except ValueError:
            return (index, Symbol(token))
