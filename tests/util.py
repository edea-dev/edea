"""
Test utility methods.


SPDX-License-Identifier: EUPL-1.2
"""
import os


def get_path_to_test_project(project_name, ext="kicad_sch"):
    test_folder = os.path.dirname(os.path.realpath(__file__))
    proj_path = [test_folder, "kicad_projects", project_name, f"{project_name}.{ext}"]
    return os.path.join(*proj_path)
