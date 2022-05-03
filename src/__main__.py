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

# what we need: schematic and pcb file, ideally find from kicad project file
# we don't need to parse project json to get top level file names; the project name is always (?) the filename
# of the top level schematic

if args.extract_meta:
    # parse the top-level schematic (and sub-schematics) plus the PCB file
    # and output metadata about it
    if len(args.projects) != 1:
        raise Exception(f"need exactly one KiCad Project, found {len(args.projects)}")

    project_path = args.projects[0]
    if project_path.endswith('.kicad_pro'):
        path, _ = os.path.splitext(project_path)
        root_schematic = path + ".kicad_sch"
    else:
        if os.path.isdir(project_path):
            path_lead, project_name = os.path.split(os.path.normpath(project_path))
            root_schematic = os.path.join(project_path, project_name + '.kicad_sch')
    pro = Project(root_schematic)
    before = time()
    pro.parse()
    after = time()

    metadata = pro.metadata()
    metadata["parse_time"] = after - before

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
