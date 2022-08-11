"""
Metadata extraction tests

This takes ferret, a fairly complex project and verifies some basic facts about it.

SPDX-License-Identifier: EUPL-1.2
"""
from uuid import uuid4

from edea.edea import PCB
from edea.parser import from_str
from tests.test_metadata import get_path_to_test_project

test_projects = {
    "ferret": {
        "count_part": 134,
        "count_unique": 115,
        "area": 2500.0
    }
}


class TestPCB:
    def test_boundingbox(self):
        for proj_name, context in test_projects.items():
            fn = get_path_to_test_project(proj_name, "kicad_pcb")
            with open(fn) as f:
                s = f.read()
            pcb = PCB(from_str(s), proj_name, fn)

            bb = pcb.bounding_box()

            assert bb.area == context["area"]

    def test_merge_pcb(self):
        fn = get_path_to_test_project("3v3ldo", "kicad_pcb")
        with open(fn) as f:
            s = f.read()
        pcb = PCB(from_str(s), "3v3ldo", fn)
        pcb2 = PCB(from_str(s), "3v3ldo", fn)
        pcb3 = PCB(from_str(s), "3v3ldo", fn)

        pcb.append([(str(uuid4()), pcb2), (str(uuid4()), pcb3)])

        # with open("3v3ldo_merged.kicad_pcb", "w") as f:
        #     f.write(str(pcb.as_expr()))
