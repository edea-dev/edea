"""
KiCad file format parser

SPDX-License-Identifier: EUPL-1.2
"""
from __future__ import annotations

import re
from _operator import methodcaller
from collections import UserList
from dataclasses import dataclass
from math import tau, cos, sin
from typing import Tuple, Union

import numpy as np

from .bbox import BoundingBox

Symbol = str
Number = (int, float)
Atom = (Symbol, Number)
to_be_moved = ["module", "gr_text", "gr_poly", "gr_line", "gr_arc", "via", "segment", "dimension", "gr_circle",
               "gr_curve", "arc", ]
movable_types = ["at", "xy", "start", "end", "center"]
drawable_types = ["pin", "polyline", "rectangle"]
lib_symbols = {}
TOKENIZE_EXPR = re.compile(r'("[^"]*"|\(|\)|"|[^\s()"]+)')


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
