"""
KiCad file format parser

SPDX-License-Identifier: EUPL-1.2
"""
from __future__ import annotations

import re
from copy import deepcopy, copy
from _operator import methodcaller
from collections import UserDict, UserList
from dataclasses import dataclass
from math import acos, cos, degrees, radians, sin, tau
from typing import Dict, Tuple, Union
from uuid import UUID, uuid4

import numpy as np

from .bbox import BoundingBox

Symbol = str
Number = (int, float)
Atom = (Symbol, Number)

# types which have children with absolute coordinates
to_be_moved = [
    "footprint",
    "gr_text",
    "gr_poly",
    "gr_line",
    "gr_arc",
    "via",
    "segment",
    "dimension",
    "gr_circle",
    "gr_curve",
    "arc",
    "polygon",
    "filled_polygon",
]  # pts is handled separately
skip_move = ["primitives"]

# types which should be moved if their parent is in the set of "to_be_moved"
movable_types = ["at", "xy", "start", "end", "center", "mid"]

drawable_types = [
    "pin",
    "polyline",
    "rectangle",
    "wire",
    "property",
    "hierarchical_label",
    "junction",
    "text",
    "label",
]
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
        """__init__ builds a new pin with typ as the type
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
            return UserList.__getattribute__(self, name)

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
            return self.name == other
            # raise NotImplementedError

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

    def __copy__(self):
        c = type(self)(typ=self.name)
        for name in self.__slots__:
            value = copy(getattr(self, name))
            setattr(c, name, value)
        return c

    def __deepcopy__(self, memo):
        c = type(self)(typ=self.name)
        memo[id(self)] = c
        for name in self.__slots__:
            value = deepcopy(getattr(self, name))
            setattr(c, name, value)
        return c



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
        """Returns a numpy array containing every corner [x,y]"""
        if len(self.at) > 2:
            angle = self.at.data[2] / tau
        else:
            angle = 0
        origin = self.at.data[
                 0:2
                 ]  # in this case we explicitly need to access the data list because of the range op
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
                points[i] = origin + points[i] * [
                    (w * angle_cos + h * angle_sin),
                    (h * angle_cos + w * angle_sin),
                ]

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
        """corners returns start and end of the FPLine"""
        points = np.array(
            [[self.start[0], self.start[1]], [self.end[0], self.end[1]]],
            dtype=np.float64,
        )
        return points

    def bounding_box(self) -> BoundingBox:
        """bounding_box of the fp_line"""
        return BoundingBox(self.corners())


@dataclass(init=False)
class Polygon(Expr):
    """Polygon
    TODO: Zone polygons are with absolute positions, are there other types?
    """

    def bounding_box(self) -> BoundingBox:
        """bounding_box of the polygon"""
        return BoundingBox(self.corners())

    def corners(self) -> np.array:
        """corners returns the min and max points of a polygon"""
        x_points = []
        y_points = []

        for point in self.pts:
            if point.name != "xy":
                raise NotImplementedError(
                    f"the following polygon format isn't implemented yet: {point}"
                )
            x_points.append(point[0])
            y_points.append(point[1])

        npx = np.array(x_points)
        npy = np.array(y_points)

        max_x = np.amax(npx)
        min_x = np.amin(npx)
        max_y = np.amax(npy)
        min_y = np.amin(npy)

        return np.array(
            [
                [min_x, min_y],
                [min_x, max_y],
                [max_x, max_y],
                [max_x, min_y],
            ],
            dtype=np.float64,
        )


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
        """prepend_path prepends the uuid path to the current one"""
        # path is always in the format of /<uuid>[/<uuid>]
        sub = self.path.data[0].strip('"')
        self.path.data[0] = f'"/{path}{sub}"'


@dataclass()
class Elem(UserDict):
    """SVG Element"""

    def __init__(self, typ: str, inner=None) -> None:
        """__init__"""
        super().__init__()
        self.typ = typ
        self.inner = inner

    def append(self, key: str, value: str):
        """creates and/or appends value to the given key"""
        if key in self.data:
            self.data[key].append(value)
        else:
            self.data[key] = [value]

    def to_string(self) -> str:
        """build a string representation of the current svg element"""
        attrs = []
        for key, values in self.data.items():
            joined_vals = " ".join(values)
            attrs.append(f'{key}="{joined_vals}"')
        all_attrs = " ".join(attrs)
        if self.inner is None or self.inner == "":
            return f"<{self.typ} {all_attrs} />"

        return f"<{self.typ} {all_attrs}>{self.inner}</{self.typ}>"


@dataclass(init=False)
class Drawable(Movable):
    """
    Drawable is an object which can be converted to an SVG
    pin: line with text
    polyline: symbols drawn with line(s), e.g. the ground symbol
    rectangle: usually ic symbols
    """

    svg_precision = 4

    def draw(self, position: Tuple[float, float] | Tuple[float, float, float]):
        """draw the shape with the given offset"""
        node = Elem(self.name)
        self.parse_visual(node, position)

        # if len(position) == 3 and position[2] != 0:
        #    attrs.append(f'transform="rotate({position[2]})"')

        if self.name == "pin":
            # raise NotImplementedError(self.name)
            return None
        elif self.name == "polyline":
            for point in self.data[0]:
                # rounding is necessary because otherwise you get
                # numbers ending with .9999999999 due to floating point precision :/
                x = round(position[0] + point.data[0], self.svg_precision)
                y = round(position[1] + point.data[1], self.svg_precision)
                node.append("points", f"{x},{y}")
        elif self.name == "rectangle":
            node.typ = "rect"
            xc, yc = [self.start[0], self.end[0]], [self.start[1], self.end[1]]
            width = max(xc) - min(xc)
            height = max(yc) - min(yc)
            x_mid = (self.start[0] + self.end[0]) / 2
            # y_mid = (self.start[1] + self.end[1]) / 2
            svgx = min(position[0] + self.start[0], position[0] + self.end[0])
            # kicad flips the y-axis when going from symbol to schematic for
            # some reason, hence we are subtracting here
            svgy = min(position[1] - self.start[1], position[1] - self.end[1])

            node.append("x", f"{round(svgx, self.svg_precision)}")
            node.append("y", f"{round(svgy, self.svg_precision)}")
            node.append("width", f"{round(width, self.svg_precision)}")
            node.append("height", f"{round(height, self.svg_precision)}")
        elif self.name == "wire":
            node.typ = "polyline"
            for point in self.data[0]:
                node.append(
                    "points",
                    f"{point.data[0]},{point.data[1]}",
                )
        elif self.name in ["property", "hierarchical_label", "text", "label"]:
            node.typ = "text"
            has_effects = hasattr(self, "effects")

            # check if it's hidden
            if has_effects and "hide" in self.effects:
                return None

            text = self.data[0].strip('"')
            if self.name == "property":
                text = self.data[1].strip(
                    '"'
                )  # property is key, value and we only display the value

            anchor = "middle"

            x_mid = self.at[0]

            font_size = 1.27  # default font size
            if has_effects and hasattr(self.effects, "font"):
                if hasattr(self.effects.font, "size"):
                    font_size = self.effects.font.size[0]
                if hasattr(self.effects, "justify"):
                    if self.effects.justify[0] == "left":
                        anchor = "start"
                        # x_mid -= len(text)/2 * font_size
                    elif self.effects.justify[0] == "middle":
                        anchor = "center"
                    elif self.effects.justify[0] == "right":
                        anchor = "end"
                        x_mid += len(text) / 2 * font_size

            node.append("text-anchor", anchor)

            y = self.at[1]
            if self.name in ["property", "hierarchical_label"]:
                y += font_size / 2

            if len(position) > 0 and position[0] != 0 and position[1] != 0:
                x_mid = position[0] + x_mid
                y = position[1] - y

            node.append("font-family", "monospace")

            node.append("x", f"{x_mid}")
            node.append("y", f"{y}")

            node.append("font-size", f"{font_size}px")
            node.inner = text
        elif self.name == "junction":
            return f'<circle cx="{self.at[0]}" cy="{self.at[1]}" r="0.5" fill="green" stroke="green" stroke-width="0" />'
        else:
            raise NotImplementedError(self.name)

        return node.to_string()

    def parse_visual(self, node: Elem, at) -> None:
        """parse fill/stroke, if present"""
        attrs = []
        if hasattr(self, "stroke"):
            color, opacity = parse_color(self.stroke.color)

            # in kicad 0 usually means default
            if opacity == 0:
                opacity = 1

            stroke_width = self.stroke.width[0]
            if stroke_width == 0:
                stroke_width = 0.1524  # kicad default stroke width

            node.append("stroke", f"rgb({color})")
            node.append("stroke-opacity", f"{opacity}")
            node.append("stroke-width", f"{stroke_width}")

            match self.stroke.type[0]:
                case ("default" | "solid"):
                    pass
                case "dot":
                    node.append("stroke-dasharray", "1")
                case "dash":
                    node.append("stroke-dasharray", "3 1")
                case "dash_dot":
                    node.append("stroke-dasharray", "3 1 1 1")
                case "dash_dot_dot":
                    node.append("stroke-dasharray", "3 1 1 1 1 1")

        if hasattr(self, "fill"):
            match self.fill.type[0]:
                case "none":
                    node.append("fill", "none")
                case "background":
                    # TODO: figure out how to access theme background
                    node.append("fill", "none")
                case "outline":
                    color, opacity = parse_color(self.stroke.color)
                    node.append("fill", f"rgb({color})")
                    node.append("fill-opacity", f"{opacity}")

        if hasattr(self, "at") and len(self.at) > 2 and self.at[2] != 0:
            angle = self.at[2]

            # TODO: if type is label and angle 180, don't rotate but anchor at end of text instead of start

            if len(at) == 3:
                angle += at[2]

            angle = angle % 360

            x = self.at[0]
            y = self.at[1]
            vector_length = np.sqrt(x ** 2 + y ** 2)
            if vector_length > 0:
                original_angle = degrees(acos(x / vector_length))
            else:
                original_angle = 0
            offset_y = vector_length * sin(radians(original_angle - angle))
            offset_x = vector_length * cos(radians(original_angle - angle))
            self.at = (offset_x, offset_y, angle)
            node.append("transform", f"rotate({angle})")


def parse_color(color: list):
    """converts `r g b a` to a tuple of `(r,g,b)` and `alpha`"""
    return (f"{color[0]},{color[1]},{color[2]}", color[3])


@dataclass(init=False)
class TStamp(Expr):
    """
    TStamp UUIDv4 identifiers which replace the pcbnew v5 timestamp base ones
    """

    def randomize(self):
        """randomize the tstamp UUID"""
        # parse the old uuid first to catch edgecases
        _ = UUID(self.data[0])
        # generate a new random UUIDv4
        self.data[0] = str(uuid4())


@dataclass(init=False)
class Net(Expr):
    """Schematic/PCB net"""

    def rename(self, numbers: Dict[int, int], names: Dict[str, str]):
        """rename and/or re-number a net

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


def from_tokens(
        tokens: list, index: int, parent: str, grand_parent: str
) -> Tuple[int, Union[Expr, int, float, str]]:
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
