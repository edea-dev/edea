"""
Test schematic merging with a few example projects

SPDX-License-Identifier: EUPL-1.2
"""

from edea.edea import Schematic
from edea.parser import from_str
from tests.util import get_path_to_test_project

test_projects = {"3v3ldo": {}, "MP2451": {}, "STM32F072CBU6": {}}


class TestSchematicMerge:
    def test_basic_merge(self):
        target_schematic = Schematic.empty()

        for proj_name, context in test_projects.items():
            path = get_path_to_test_project(proj_name)

            with open(path) as f:
                sch = Schematic(from_str(f.read()), proj_name, f"{proj_name}.kicad_sch")
                target_schematic.append({proj_name: sch})

        assert str(target_schematic.as_expr()) != ""
