"""
SVG Rendering tests

SPDX-License-Identifier: EUPL-1.2
"""

from edea.parser import from_str
from edea.edea import Schematic


class TestRendering:
    def test_draw_rect(self):
        expr = from_str("(rectangle (start -5.08 5.08) (end 5.08 -1.905))")

        # kicad flips the y axis inside symbols, we undo this when we draw
        # rects. rects are only ever inside symbols, never on the top level in
        # schematics
        assert (
            expr.draw((0, 0))
            == '<rect x="-5.08" y="-5.08" width="10.16" height="6.985" />'
        )

    def test_draw_rect_stroke(self):
        expr = from_str(
            "(rectangle (start -5.08 5.08) (end 5.08 -1.905) (stroke (width 0.254) (type default) (color 120 85 0 0.5)) (fill (type background))))"
        )

        assert (
            expr.draw((20, 10))
            == '<rect stroke="rgb(120,85,0)" stroke-opacity="0.5" stroke-width="0.254" fill="none" x="14.92" y="4.92" width="10.16" height="6.985" />'
        )
    def test_draw_polyline(self):
        expr = from_str(
            "(polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.3048) (type default) (color 0 0 0 0)) (fill (type none)))"
        )

        assert (
            expr.draw((0, 0))
            == '<polyline stroke="rgb(0,0,0)" stroke-opacity="1" stroke-width="0.3048" fill="none" points="-1.524,0.508 1.524,0.508" />'
        )
    def test_draw_polyline_outline(self):
        expr = from_str(
            "(polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.3048) (type default) (color 0 50 0 0.2)) (fill (type outline)))"
        )

        assert (
            expr.draw((12, 0))
            == '<polyline stroke="rgb(0,50,0)" stroke-opacity="0.2" stroke-width="0.3048" fill="rgb(0,50,0)" fill-opacity="0.2" points="10.476,0.508 13.524,0.508" />'
        )
    # def test_draw_pin(self):

    def test_draw_symbol(self):
        with open(
            "tests/kicad_projects/ferret/control.kicad_sch", encoding="utf-8"
        ) as f:
            sch = Schematic(from_str(f.read()), "3v3ldo", "")

        lines = sch.draw()
        with open("test_schematic.svg", "w", encoding="utf-8") as f:
            f.write("\n".join([l for l in lines if l is not None]))
