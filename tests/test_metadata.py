"""
Metadata extraction tests

This takes ferret, a fairly complex project and verifies some basic facts about it.

SPDX-License-Identifier: EUPL-1.2
"""

from time import time
from tests.util import get_path_to_test_project

from edea.edea import Project

test_projects = {
    "ferret": {
        "count_part": 134,
        "count_unique": 115,
        "copper_layers": 4
    }
}


class TestMetadata:
    def test_metadata_extraction_all_projects(self):
        for proj_name, context in test_projects.items():
            path = get_path_to_test_project(proj_name, "")
            pro = Project(path + "kicad_sch", path + "kicad_pcb")
            before = time()
            pro.parse()
            after = time()

            metadata = pro.metadata()
            metadata["parse_time"] = after - before

            for meta_key, expected_value in context.items():
                assert metadata[meta_key] == expected_value
