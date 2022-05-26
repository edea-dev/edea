"""
it's a kicad parser! it's edea! it's the kicad parser and edea tooling!

This contains a KiCAD parser with a minimalistic approach that should hopefully be easy to use. There's a lot of code
manipulating kicad data structures, so it's hopefully not too hard to pick up what it's doing.

SPDX-License-Identifier: EUPL-1.2
"""
from __future__ import annotations

import os
from itertools import filterfalse, groupby
from operator import methodcaller
from typing import Dict
from uuid import uuid4

import numpy as np

from .bbox import BoundingBox
from .parser import Expr, from_str, Pad


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

    def to_sheet(self, sheet_name: str, file_name: str, pos_x=20.0, pos_y=20.0) -> (BoundingBox, Expr):
        """ to_sheet extracts all hierarchical labels and generates a new sheet object from them
        """

        if hasattr(self._sch, "hierarchical_label"):
            labels = self._sch.hierarchical_label
            len_longest_label = len(max(labels.keys(), key=len))
        else:
            len_longest_label = 0
            labels = {}

        # width of the hierarchical sheet, length of the longest pin name or min 4 chars wide plus one spacing on each
        # side.
        lbl_space = max(len_longest_label, 4) + 2

        width = lbl_space * 1.27
        height = (len(labels) + 1) * 2.54

        # build a bounding box so that the next sheet can be placed properly
        box = BoundingBox(np.array([[pos_x, pos_y], [pos_x + height, pos_y + width]]))

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

        return (box, sheet)

    @staticmethod
    def empty() -> Schematic:
        """empty_schematic returns a minimal KiCad schematic
        """
        sch = Expr("kicad_sch", Expr("version", 20211123), Expr("generator", "edea"), Expr("uuid", uuid4()),
                   Expr("paper", "A4"), Expr("lib_symbols"),
                   Expr("sheet_instances", Expr("path", '"/"', Expr("page", '"1"'))))
        return Schematic(sch, "", "")

    def append(self, schematics: Dict[str, Schematic]):
        """
        here's the problem: append needs the filename of the other schematic, but also a name which it should reference
        this schematic by. i think we should take the file name from the file and make the name an optional parameter.
        """
        last_x = 20.0  # where to place the first sheet
        last_y = 20.0
        max_height = 0.0

        for name, schematic in schematics.items():
            max_page: str
            # find the max page number
            box, sheet = schematic.to_sheet(name, schematic.file_name, pos_x=last_x, pos_y=last_y)

            last_x += box.width + 20.0  # update where the next sheet should go
            max_height = max(max_height, box.height)

            # wrap to next row if there's too many sheets
            if last_x > 270.0:
                last_x = 20.0
                last_y += max_height + 20.0

            for instance in self._sch.sheet_instances:
                max_page = instance.page[0]

            new_page = int(max_page[1:-1]) + 1

            # append sheet and create a new instance
            self._sch.append(sheet)
            self._sch.sheet_instances.append(
                Expr("path", f'"/{sheet.uuid}"', Expr("page", f'"{new_page}"')),
            )


class PCB:
    """ PCB
    Representation of a kicad PCB
    """
    _pcb: Expr
    file_name: str
    name: str

    def __init__(self, pcb: Expr, name: str, file_name: str):
        self._pcb = pcb
        self.name = name
        self.file_name = file_name

    def as_expr(self) -> Expr:
        """ return the schematic as an Expr """
        return self._pcb

    def bounding_box(self):
        all_corners = self._pcb.apply(Pad, methodcaller("corners"))
        print(all_corners)


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
