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
from typing import Dict, List, Tuple
from uuid import uuid4

import numpy as np

from .bbox import BoundingBox
from .parser import (Drawable, Expr, Footprint, FPLine, Movable, Polygon,
                     TStamp, from_str)

# top level types to copy over to the new PCB
copy_parts = ["footprint", "zone", "via", "segment", "arc", "gr_text", "gr_line", "gr_poly", "gr_arc", "gr_circle",
              "gr_curve", "dimension"]


class VersionError(Exception):
    """ VersionError
    Source file was produced with a KiCad version before 6.0
    """


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

    def draw(self) -> list:
        """draw the whole schematic"""
        svg_header = """<svg version="2.0" width="297mm" height="210mm" xmlns="http://www.w3.org/2000/svg">"""
        lines = []
        lines.append(svg_header)

        for sym in self._sch.symbol:
            sym_name = sym.lib_id[0].strip('"')

            lines.append(f"<!--drawing {sym_name} -->")

            for expr in self._sch.lib_symbols.symbol[sym_name]:
                # loop the inner symbol once more
                if isinstance(expr, Expr) and expr.name == "symbol":
                    # loop the inner symbol
                    for e in expr:
                        if isinstance(e, Drawable):
                            lines.append(e.draw(sym.at))
                elif isinstance(expr, Drawable) and expr.name not in [
                    "property"]:  # draw instances which aren't symbols
                    lines.append(expr.draw(sym.at))

            for expr in sym:
                if isinstance(expr, Drawable):
                    lines.append(expr.draw((0, 0, sym.at[2])))

        lines.append("<!--drawing wires -->")
        for wire in self._sch.wire:
            lines.append(wire.draw(()))

        lines.append("<!--drawing junk -->")
        for j in self._sch.junction:
            lines.append(j.draw(()))

        lines.append("<!--drawing text -->")
        for t in self._sch:
            if t.name == "text":
                lines.append(t.draw(()))

        lines.append("<!--drawing labels -->")
        for t in self._sch:
            if t.name == "label":
                lines.append(t.draw(()))

        lines.append('</svg>')
        return lines


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

    def bounding_box(self) -> BoundingBox:
        """ bounding_box calculates and returns the BoundingBox of a PCB
        """
        flatten = lambda l: sum(map(flatten, l), []) if isinstance(l, list) else [l]

        footprints = flatten(
            self._pcb.apply(Footprint, methodcaller("bounding_box")))  # return value is a list of single element lists
        polygons = flatten(self._pcb.apply(Polygon, methodcaller("bounding_box")))
        fp_line = flatten(self._pcb.apply(FPLine, methodcaller("bounding_box")))

        all_boxes = []
        all_boxes.extend(footprints)
        all_boxes.extend(polygons)
        all_boxes.extend(fp_line)

        outer = BoundingBox([])

        # add bounding boxes together
        for box in all_boxes:
            if box is not None:
                outer.envelop(box.corners)

        return outer

    def move(self, x: float, y: float):
        """ move a pcb with relative coordinates
        """
        self._pcb.apply(Movable, methodcaller("move_xy", x, y))

    def append(self, pcbs: List[Tuple[str, PCB]]):
        """
        append merges one or more PCBs into the current one. it also takes a UUID per PCB
        which is prepended to the path of symbols/footprints
        """
        # step 1: get nets, merge and rename them

        # TODO: actually do it

        # step 2: arrange pcbs
        # move initial pcb to origin coordinates
        target_box = self.bounding_box()
        self.move(-target_box.min_x, -target_box.min_y)

        # step 3: merge
        for path_uuid, pcb in pcbs:
            target_box = self.bounding_box()
            pcb_box = pcb.bounding_box()

            # move the new PCB 20 units to the right of the previous one
            pcb.move(-pcb_box.min_x + target_box.max_x + 20.0, -pcb_box.min_y)

            # TODO: arrange the PCBs within rows and columns, but for this we would need to calculate all placements
            #       beforehand.

            expr = pcb.as_expr()

            # prepend paths and randomize "tstamp" values
            expr.apply(Footprint, methodcaller("prepend_path", path_uuid))
            expr.apply(TStamp, methodcaller("randomize"))

            for part in copy_parts:
                if hasattr(expr, part):
                    print(f"getting {part}")
                    sub_expr = expr.__getattr__(part)

                    # if it's a single occurrence we can just append it, otherwise extend the parent
                    if isinstance(sub_expr, list):
                        self._pcb.data.extend(sub_expr)
                    elif isinstance(sub_expr, dict):
                        self._pcb.extend(sub_expr.values())
                    else:
                        self._pcb.data.extend(sub_expr)

        # refresh known attributes, etc
        self._pcb.parsed()


class Project:
    """KiCAD project
    nya
    """

    schematics = {}
    fn_to_uuid = {}
    symbol_instances = {}
    top: str
    sheets: int  # sheets is the amount of schematics including all instances of sub-schematics
    pcb: PCB

    def __init__(self, sch_file_name: str, pcb_file_name: str) -> None:
        self.sch_file_name = sch_file_name
        self.pcb_file_name = pcb_file_name

    def parse(self):
        """parse the base schematic and PCB file"""
        with open(self.sch_file_name, encoding="utf-8") as sch_file:
            sch = from_str(sch_file.read())

        if sch.version[0] < 20211123:
            raise VersionError("kicad file format versions pre-6.0.0 are unsupported")

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
        self._parse_sheet(sch, self.sch_file_name)

        # parse the PCB
        with open(self.pcb_file_name, encoding="utf-8") as pcb_file:
            self.pcb = PCB(from_str(pcb_file.read()), "", self.pcb_file_name)

    def _parse_sheet(self, sch: Expr, file_name: str):
        """recursively parse schematic sub-sheets"""
        uuid = sch.uuid[0]
        self.schematics[uuid] = Schematic(sch, "", file_name)
        self.fn_to_uuid[os.path.basename(file_name)] = uuid

        dir_name = os.path.dirname(self.sch_file_name)

        if not hasattr(sch, "sheet"):
            return

        sheets = sch.sheet

        # check if it's a single sheet or multiple
        if sheets[0].name != "sheet":
            sheets = [sheets]

        for sheet in sheets:
            try:
                prop = sheet.property
            except AttributeError as e:
                print(str(sheet))
                raise e

            if "Sheet file" in prop:
                sheet_file_key = "Sheet file"
            elif "Sheetfile" in prop:
                sheet_file_key = "Sheetfile"
            elif "Fichier de feuille" in prop:
                sheet_file_key = "Fichier de feuille"
            else:
                raise ValueError("unknown property key for sheet file")

            sheet_file = prop[sheet_file_key][1].strip('"')
            if os.path.basename(sheet_file) not in self.fn_to_uuid:
                with open(os.path.join(dir_name, sheet_file), encoding="utf-8") as sch_file:
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

        box = self.pcb.bounding_box()

        copper_layers = 0
        for layer in self.pcb.as_expr().layers:
            if layer[0].endswith('.Cu"'):
                copper_layers += 1

        bom = {"count_part": len(parts), "count_unique": len(unique_keys), "parts": bom_parts, "sheets": self.sheets,
               "area": box.area, "width": box.width, "height": box.height, "copper_layers": copper_layers}

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
