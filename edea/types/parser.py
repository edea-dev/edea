"""
Methods for turning strings and lists into EDeA dataclasses.

SPDX-License-Identifier: EUPL-1.2
"""
import re
from edea.types.base import KicadExpr

# we need to import this for get_all_subclasses to work
import edea.types.schematic
from edea.util import get_all_subclasses

all_classes = get_all_subclasses(KicadExpr)


def from_list(expr: list[str | list]) -> KicadExpr:
    """
    Turn an s-expression list into an EDeA dataclass.
    """
    errors = []
    result = None
    tag_name = expr[0]
    # pass the rest of the list to the first class where the tag name matches
    # and it doesn't throw an error
    for cls in all_classes:
        if tag_name == cls.kicad_expr_tag_name:
            try:
                result = cls.from_list(expr[1:])
            except Exception as e:
                errors.append(e)
            else:
                break
    if result is None:
        if len(errors) >= 1:
            raise errors[0]
        else:
            raise ValueError(f"Unknown KiCad expression starting with '{expr[0]}'")
    return result


def _tokens_to_list(tokens: list, index: int = 0):
    if len(tokens) == index:
        raise SyntaxError("unexpected EOF")
    token = tokens[index]
    index += 1

    if token == "(":
        typ = tokens[index]
        index += 1

        expr = [typ]
        while tokens[index] != ")":
            index, sub_expr = _tokens_to_list(tokens, index)
            expr.append(sub_expr)

        # remove ')'
        index += 1

        return (index, expr)

    if token == ")":
        raise SyntaxError("unexpected )")

    if token.startswith('"') and token.endswith('"'):
        token = token.strip('"')
    return (index, token)


_TOKENIZE_EXPR = re.compile(r'("[^"\\]*(?:\\.[^"\\]*)*"|\(|\)|"|[^\s()"]+)')


def from_str_to_list(text) -> list:
    tokens = _TOKENIZE_EXPR.findall(text)
    _, expr = _tokens_to_list(tokens, 0)
    return expr


def from_str(text) -> KicadExpr:
    """
    Turn a string containing KiCad s-expressions into an EDeA dataclass.
    """
    expr = from_str_to_list(text)
    return from_list(expr)
