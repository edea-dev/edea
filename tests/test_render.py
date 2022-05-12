"""
SVG Rendering tests

SPDX-License-Identifier: EUPL-1.2
"""

from edea.parser import from_str

class TestRendering:
    def test_draw_rect(self):
        expr = from_str("(rectangle (start -5.08 -5.08) (end 5.08 1.905))")
        
        assert expr.draw((0,0)) == '<rect x="-5.08" y="-5.08" width="10.16" height="6.985" />'
        
    def test_draw_rect_stroke(self):
        expr = from_str("(rectangle (start -5.08 -5.08) (end 5.08 1.905) (stroke (width 0.254) (type default) (color 120 85 0 0.5)) (fill (type background))))")
        
        assert expr.draw((20,10)) == '<rect x="14.92" y="4.92" width="10.16" height="6.985" stroke="rgb(120,85,0)" stroke-opacity="0.5" stroke-width="0.254" />'
        
    def test_draw_polyline(self):
        expr = from_str("(polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.3048) (type default) (color 0 0 0 0)) (fill (type none)))")
        
        assert expr.draw((0,0)) == '<polyline points="-1.524,0.508 1.524,0.508 " stroke="rgb(0,0,0)" stroke-opacity="0" stroke-width="0.3048" fill="none" />'
        
    def test_draw_polyline_outline(self):
        expr = from_str("(polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.3048) (type default) (color 0 50 0 0.2)) (fill (type outline)))")
        
        assert expr.draw((12,0)) == '<polyline points="10.476,0.508 13.524,0.508 " stroke="rgb(0,50,0)" stroke-opacity="0.2" stroke-width="0.3048" fill="rgb(0,50,0)" fill-opacity="0.2" />'

    # def test_draw_pin(self):