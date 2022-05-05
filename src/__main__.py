import argparse
import json
import os
from time import time

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
    elif os.path.isdir(project_path):
        path_lead, project_name = os.path.split(os.path.normpath(project_path))
        root_schematic = os.path.join(project_path, project_name + '.kicad_sch')
    else:
        raise Exception("Please provide a KiCad project directory or project file")

    pro = Project(root_schematic)
    before = time()
    pro.parse()
    after = time()

    metadata = pro.metadata()
    metadata["parse_time"] = after - before

    print(json.dumps(metadata))

else:
    # not a metadata dump operation
    files = {}
    target_schematic = Schematic.empty()

    for path in args.projects:
        # TODO: sort this mess out
        if path.endswith('.kicad_pro'):
            path_lead, _ = os.path.splitext(path)
            project_name = os.path.basename(path_lead)
            project_path = os.path.dirname(path)
        elif os.path.isdir(path):
            _, project_name = os.path.split(os.path.normpath(path))
            project_path = path
        else:
            raise Exception("please specify a path to a KiCad project or the .kicad_pro file")

        if project_path not in files:
            files[project_path] = [{"project_name": project_name, "name": project_name}]
        else:
            # check if the first instance was already renamed
            if "renamed" not in files[project_path][0]:
                files[project_path][0]["name"] = f"{project_name} 1"
                files[project_path][0]["renamed"] = True

            # append another instance of the project
            files[project_path].append(
                {"project_name": project_name, "name": f"{project_name} {len(files[project_path]) + 1}"},
            )

    # now iterate all the (renamed) instances of the projects
    for project_path, obj in files.items():
        for instance in obj:
            root_schematic = os.path.join(project_path, instance["project_name"] + '.kicad_sch')

            with open(root_schematic, encoding="utf-8") as f:
                sch = Schematic(from_str(f.read()), instance["project_name"], f"{instance['project_name']}.kicad_sch")
                target_schematic.append(sch)

            # TODO: merge PCB too

    # dump the resulting schematic
    with open("top.kicad_sch", "w", encoding="utf-8") as f:
        f.write(str(target_schematic.as_expr()))

    # todo(ln): add a pin to the sub
