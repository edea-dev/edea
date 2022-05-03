import argparse
import os
import pathlib
from time import time
import json

from edea import Schematic, Project
from edea import from_str

parser = argparse.ArgumentParser(description='Tool to parse, render, and merge KiCad projects.')
pgroup = parser.add_mutually_exclusive_group()
pgroup.add_argument('--extract-meta', help='Extract metadata from KiCad project and output to stdout or to json file.',
                    action='store_true')
pgroup.add_argument('--merge', action='store_true', help='Merge the listed KiCad projects into a single project ('
                                                         'specify target directory with the output argument).')
parser.add_argument('--output', type=str, nargs='?', default=False,
                    help="Specify output directory for merge, or output file for metadata extraction.")
parser.add_argument('projects', type=str, nargs='+',
                    help='Path(s) to KiCad Project directory used as input.')

args = parser.parse_args()

# pro = project("example-module/example-module.kicad_sch")
# pro = project("/home/elen/automated/upcu/mk1/mk1.kicad_sch")
# before = time.time()
# pro.parse()
# after = time.time()
# print(f"took {after - before}s to parse")

# pro.metadata()
# pro.as_sheet()

    print(json.dumps(metadata))

else:
    # not a metadata dump operation
    sch1 = Schematic.empty()
    sub_sch: Schematic

    with open("example-module/example-module.kicad_sch", encoding="utf-8") as f:
        sch = from_str(f.read())
        sub_sch = Schematic(sch, "example_sub", "example-module/example-module.kicad_sch")

    sch1.append(sub_sch, "sub schematic 1")
    sch1.append(sub_sch, "sub schematic 2")

    with open("top.kicad_sch", "w", encoding="utf-8") as f:
        f.write(str(sch1.as_expr()))

    # todo(ln): add a pin to the sub
