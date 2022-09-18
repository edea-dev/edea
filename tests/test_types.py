from edea.parser import from_str_to_list
from edea.types.schematic import Schematic

class TestTypes:
    def test_schematic(self):
        with open(
            "tests/kicad_projects/ferret/control.kicad_sch", encoding="utf-8"
        ) as f:
            l = from_str_to_list(f.read())

        sch = Schematic.from_list_expr(l)

        from pprint import pprint
        pprint(sch)

        assert(sch is not None)


