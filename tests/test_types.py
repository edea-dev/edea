from edea.types.parser import from_str
from edea.types.schematic import Schematic


class TestTypes:
    def test_schematic(self):
        with open(
            "tests/kicad_projects/ferret/control.kicad_sch", encoding="utf-8"
        ) as f:
            sch = from_str(f.read())

        assert isinstance(sch, Schematic)
