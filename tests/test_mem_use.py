from __future__ import print_function

import gc
import sys
from time import time

from edea.parser import from_str
from tests.test_metadata import get_path_to_test_project

test_projects = {
    "ferret": {
        "parse_time": 2.0, # gitlab ci runner is really slow
        "total_mem": 38.5
    }
}

# https://stackoverflow.com/a/53705610
def get_obj_size(obj):
    marked = {id(obj)}
    obj_q = [obj]
    sz = 0

    while obj_q:
        sz += sum(map(sys.getsizeof, obj_q))

        # Lookup all the object referred to by the object in obj_q.
        # See: https://docs.python.org/3.7/library/gc.html#gc.get_referents
        all_refr = ((id(o), o) for o in gc.get_referents(*obj_q))

        # Filter object that are already marked.
        # Using dict notation will prevent repeated objects.
        new_refr = {o_id: o for o_id, o in all_refr if o_id not in marked and not isinstance(o, type)}

        # The new obj_q will be the ones that were not marked,
        # and we will update marked with their ids so we will
        # not traverse them again.
        obj_q = new_refr.values()
        marked.update(new_refr.keys())

    return sz


class TestMetadata:
    def test_mem_use(self):
        for proj_name, context in test_projects.items():
            with open(get_path_to_test_project(proj_name, "kicad_pcb")) as f:
                s = f.read()
                before = time()
                pcb = from_str(s)
                after = time()

            parse_time = after - before

            total_mem = float(get_obj_size(pcb)) / (1024 * 1024)

            print(f"parsing took {parse_time:.2f}s with {total_mem:.2f}MiB of memory")
            # locally it takes 0.34s and 38MiB to parse the test file
            assert parse_time < context["parse_time"]
            assert total_mem < context["total_mem"]
