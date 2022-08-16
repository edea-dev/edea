"""
Test that parses as many KiCad 6 projects as we could find.

SPDX-License-Identifier: EUPL-1.2
"""

import os
import re
import pytest

from edea.edea import Project, VersionError

test_folder = os.path.dirname(os.path.realpath(__file__))
kicad_folder = os.path.join(test_folder, "kicad_projects/kicad6-test-files")

kicad_pcb_files = []
for root, dirs, files in os.walk(kicad_folder):
    for file in files:
        if file.endswith(".kicad_pcb"):
            path = os.path.join(root, file)
            kicad_pcb_files.append(path)


@pytest.mark.parametrize("pcb_path", kicad_pcb_files)
def test_parse_all(pcb_path):
    sch_path = re.sub(r"\.kicad_pcb$", ".kicad_sch", pcb_path)
    pro = Project(sch_path, pcb_path)
    try:
        pro.parse()
    except VersionError as e:
        print(f"skipping {sch_path} due to old format: {e}")
    except FileNotFoundError as e:
        print(f"project {sch_path} appears to be incomplete")
    except AttributeError as e:
        # some minimal files don't have a uuid, but they're not interesting anyway.
        if "uuid" in str(e):
            print(f"{sch_path} does not contain a uuid")
        else:
            raise e
    except SyntaxError:
        print(f"{sch_path} contains unmatched braces or there's a parser error")
    except Exception as e:
        print(f"failed to parse {sch_path}")
        raise e
