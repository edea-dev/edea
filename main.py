"""
Blub
"""
import os
import re
import time
from collections import UserList
from dataclasses import dataclass
from itertools import filterfalse, groupby
from operator import methodcaller
from typing import OrderedDict, Tuple, Union
from uuid import uuid4

Symbol = str
Number = (int, float)
Atom = (Symbol, Number)

to_be_moved = [
    "module",
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
]

movable_types = ["at", "xy", "start", "end", "center"]
drawable_types = ["pin", "polyline", "rectangle"]

lib_symbols = {}

TOKENIZE_EXPR = re.compile("""("[^"]*"|\(|\)|"|[^\s()"]+)""")


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

    def __getattr__(self, name) -> list | OrderedDict:
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
                if type(item) is str:
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

    def __eq__(self, other):
        """Overrides the default implementation"""
        if len(self.data) != 1:
            raise NotImplementedError  # return super.__eq__(self, other)

        if other is True or other is False:
            return self[0] == "yes" and other
        if isinstance(other, Number):
            return self[0] == other.number

        print(f"type: {type(other)}")

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
        "move_xy adds the position offset x and y to the object"
        self.data[0] += x
        self.data[1] += y


@dataclass(init=False)
class Drawable(Movable):
    """
    Drawable is an object which can be converted to a SVG
    pin: line with text
    polyline: symbols drawn with line(s), e.g. the ground symbol
    rectangle: usually ic symbols
    """

    def draw(self, at: Tuple[float, float]):
        """draw the shape with the given offset"""
        if self.name == "pin":
            # raise NotImplementedError(self.name)
            pass
        elif self.name == "polyline":
            s = '<polyline points="'
            for pt in self.data[0]:
                s += f"{pt.data[0]},{pt.data[1]} "
            # TODO: stroke and fill
            print(f'{s}" />')
        elif self.name == "rectangle":
            x_start = self.start[0]
            y_start = self.start[1]
            x_end = self.end[0]
            y_end = self.end[1]
            print(
                f'<rect x="{x_start + at[0]}" y="{y_start + at[1]}" width="{x_start - x_end}" height="{y_start - y_end}" />'
            )
        else:
            raise NotImplementedError(self.name)


def tokenize(chars: str) -> list[str]:
    """Convert a string of characters into a list of tokens."""
    return TOKENIZE_EXPR.findall(chars)


def from_str(program: str) -> Expr:
    """Parse KiCAD s-expr from a string"""
    return read_from_tokens(tokenize(program), "")


def read_from_tokens(tokens: list, parent: str) -> Union[Expr, int, float, str]:
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
            expr.append(read_from_tokens(tokens, expr.name))
        tokens.pop(0)  # remove ')'

        expr.parsed()

        return expr

    if token == ")":
        raise SyntaxError("unexpected )")

    return atom(token)


def atom(token: str) -> Atom:
    """Numbers become numbers; every other token is a symbol."""
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)


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
        with open(self.file_name, encoding="utf-8") as f:
            sch = from_str(f.read())

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
        self.schematics[uuid] = sch
        self.fn_to_uuid[os.path.basename(file_name)] = uuid

        dir_name = os.path.dirname(self.file_name)

        if not hasattr(sch, "sheet"):
            return

        for sheet in sch.sheet:
            prop = sheet.property
            sheet_file = prop["Sheet file"][1].strip('"')
            if os.path.basename(sheet_file) not in self.fn_to_uuid:
                with open(os.path.join(dir_name, sheet_file), encoding="utf-8") as f:
                    print(f"reading {sheet_file}")
                    sub = from_str(f.read())

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
        top = self.schematics[self.top]

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

        bom = {
            "count_part": len(parts),
            "count_unique": len(unique_keys),
            "parts": bom_parts,
            "sheets": self.sheets,
        }

        # print(json.dumps(bom, indent=4, sort_keys=True))

    def _get_parts(self, sch, path) -> list:
        self.sheets += 1

        parts = list(
            filterfalse(
                lambda sym: sym.property["Reference"][1].startswith('"#')
                            or sym.in_bom == False,
                sch.symbol,
            )
        )

        # recurse sub-schematics
        if hasattr(sch, "sheet"):
            for sheet in sch.sheet:
                prop = sheet.property
                sheet_fn = prop["Sheet file"][1].strip('"')
                sch = self.schematics[self.fn_to_uuid[sheet_fn]]
                parts += self._get_parts(sch, f"{path}/{sch.uuid}")

        return parts

    def as_sheet(self) -> Expr:
        """ as_sheet extracts all hierarchical labels and generates a new sheet object from them
        """

        labels = self.schematics[self.top].hierarchical_label
        lbl_space = len(max(labels.keys(), key=len))

        y = 0.0
        x = 0.0

        sheet = Expr("sheet",
                     Expr("at", x, y),
                     Expr("size", lbl_space * 1.27, (len(labels) + 2) * 1.27),
                     Expr("fields_autoplaced"),
                     from_str("(stroke (width 0) (type solid) (color 0 0 0 0))"),
                     from_str("(fill (color 0 0 0 0.0000))"),
                     Expr("uuid", uuid4()),
                     Expr("property", '"Sheet name"', "TODO", Expr("id", 0),
                          Expr("at", 0.0, 0.0, 0),
                          from_str("(effects (font (size 1.27 1.27)) (justify left bottom))")),
                     Expr("property", '"Sheet file"', self.file_name, Expr("id", 1), Expr("at", 0.0, 0.0, 0),
                          from_str("(effects (font (size 1.27 1.27)) (justify left bottom))"))
                     )
        n = 0
        for label in labels.values():
            # build a new pin, (at x y angle)
            n += 1
            sheet += Expr("pin", label[0], label.shape[0], Expr("at", x, y + n * 1.27, 0),
                          from_str("(effects (font (size 1.27 1.27)) (justify left))"),
                          Expr("uuid", uuid4()))

        return sheet


pro = Project("example-module/example-module.kicad_sch")
before = time.time()
pro.parse()
after = time.time()
print(f"took {after - before}s to parse")

pro.metadata()
pro.as_sheet()

# pro.box()
