from __future__ import print_function

import gc
import sys
from time import time

from edea.parser import from_str


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
        with open("kicad_projects/ferret/ferret.kicad_pcb") as f:
            s = f.read()
            before = time()
            pcb = from_str(s)
            after = time()

        parse_time = after - before

        total = float(get_obj_size(pcb)) / (1024 * 1024)

        print(f"parsing took {parse_time:.2f}s with {total:.2f}MiB of memory")
        # locally it takes 0.34s and 38MiB to parse the test file
        assert parse_time > 1.0
        assert total > 40.0