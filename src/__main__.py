import argparse

from edea import schematic, from_str

parser = argparse.argumentparser(description='parse, render and merge kicad projects')
parser.add_argument('projects', metavar='path', type=str, nargs='+',
                    help='kicad project folders')
parser.add_argument('--meta', help='extract metadata and output to stdout')
parser.add_argument('--merge', help='extract metadata and output to stdout')

args = parser.parse_args()

# pro = project("example-module/example-module.kicad_sch")
# pro = project("/home/elen/automated/upcu/mk1/mk1.kicad_sch")
# before = time.time()
# pro.parse()
# after = time.time()
# print(f"took {after - before}s to parse")

# pro.metadata()
# pro.as_sheet()

# pro.box()

sch1 = schematic.empty()
sub_sch: schematic

with open("example-module/example-module.kicad_sch", encoding="utf-8") as f:
    sch = from_str(f.read())
    sub_sch = schematic(sch, "example_sub", "example-module/example-module.kicad_sch")

sch1.append(sub_sch, "sub schematic 1")
sch1.append(sub_sch, "sub schematic 2")

with open("top.kicad_sch", "w", encoding="utf-8") as f:
    f.write(str(sch1.as_expr()))

# todo(ln): add a pin to the sub
