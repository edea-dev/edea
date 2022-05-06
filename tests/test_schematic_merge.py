"""
Test schematic merging with a few example projects

SPDX-License-Identifier: EUPL-1.2
"""

import os

from src.edea import Schematic, from_str

test_projects = {
    "3v3ldo": {},
    "MP2451": {},
    "STM32F072CBU6": {}
}


def get_path_to_test_project(project_name):
    proj_path = ["kicad_projects", project_name, f"{project_name}.kicad_sch"]
    test_folder_name = "tests"

    if not os.getcwd().endswith(test_folder_name):
        proj_path.insert(0, test_folder_name)
    return os.path.join(*proj_path)


class TestSchematicMerge:
    def test_basic_merge(self):
        target_schematic = Schematic.empty()

        for proj_name, context in test_projects.items():
            path = get_path_to_test_project(proj_name)

            with open(path) as f:
                sch = Schematic(from_str(f.read()), proj_name, f"{proj_name}.kicad_sch")
                target_schematic.append(sch)

        assert str(target_schematic.as_expr()) != ""
