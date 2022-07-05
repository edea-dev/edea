"""
Metadata extraction tests

This takes ferret, a fairly complex project and verifies some basic facts about it.

SPDX-License-Identifier: EUPL-1.2
"""

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
