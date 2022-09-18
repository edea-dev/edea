"""
Provides the generic class method from_list_expr that interprets an
s-expression list into one of our dataclasses.

SPDX-License-Identifier: EUPL-1.2
"""
from typing import get_origin, TypeVar, Type, Union
from pydantic import ValidationError
from pydantic.color import Color


def get_args(expr: list[list | str]) -> tuple[list[str], dict]:
    """
    Turn an s-expression list into something resembling python args and
    keyword args.
    e.g. for `["name", ["property", "foo"], ["pin", 1], ["pin", 2]]` it returns
    `(["name"], {"property": [["foo"]], "pin": [[1], [2]]})`
    """
    args = []
    index = 0
    for arg in expr:
        # once we hit a list we start treating it as kwargs
        if isinstance(arg, list):
            break
        index += 1
        args.append(arg)

    kwarg_list = []
    for kwarg in expr[index:]:
        if isinstance(kwarg, list):
            kw = kwarg[0]
            kwarg_list.append((kw, kwarg[1:]))
        else:
            # treat positional args after keyword args as booleans
            # e.g. instance of 'hide' becomes hide=True
            kwarg_list.append((kwarg, [True]))

    # Turn a list of kwargs into a kwarg dict collecting duplicates
    # into lists.
    # e.g. `[("pin", [1]), ("pin", [2])]` becomes `{"pin": [[1], [2]]}`
    kwargs = {}
    for kw, arg in kwarg_list:
        if kw in kwargs:
            kwargs[kw].append(arg)
        else:
            kwargs[kw] = [arg]

    return (args, kwargs)


T = TypeVar("T")


def _from_list_expr(cls: Type[T], expr: list[list | str]) -> T:
    """Turn an s-expression list into an edea dataclass."""
    # TODO validate first item in expr
    parsed_args, parsed_kwargs = get_args(expr[1:])
    fields = cls.__pydantic_model__.__fields__

    # this is a bit hacky. we instantiate a schematic with just the version
    # because we want to validate the file format version before anything else.
    # what's a better way to do this? maybe make from_list_expr lazy?
    if expr[0] == "kicad_sch" and "version" in parsed_kwargs:
        cls(version=parsed_kwargs["version"][0][0])

    kwargs = {}
    for kw in parsed_kwargs:
        field_type = fields[kw].type_
        field_type_outer = get_origin(fields[kw].outer_type_)
        exp = parsed_kwargs[kw]

        # if it's one of our pydantic dataclasses it will have a from_list_expr
        if hasattr(field_type, "from_list_expr"):
            # if our type says it's a list we give it the args as a list
            if field_type_outer is list:
                kwargs[kw] = [field_type.from_list_expr([kw] + e) for e in exp]
            else:
                if len(exp) != 1:
                    raise SyntaxError(
                        f"Expecting only one item but got {len(exp)}: {exp}"
                    )
                kwargs[kw] = field_type.from_list_expr([kw] + exp[0])
        else:
            if len(exp) != 1:
                raise SyntaxError(f"Expecting only one item but got {len(exp)}: {exp}")
            # if it's not one of our dataclasses most often we just want to pass
            # the first and only item to `field_type` but sometimes we want to
            # make a tuple or something similar from the list of args
            # e.g. `["start", 1.0, 1.0]` -> `{"start": tuple([1.0, 1.0])}`
            if field_type_outer is tuple:
                kwargs[kw] = tuple(exp[0])
            elif field_type_outer is list:
                kwargs[kw] = list(exp[0])
            elif field_type is Color:
                kwargs[kw] = Color(exp[0])

            # union types are tried till we find one that doesn't produce a validation error
            # XXX this does not yet support unions that include `tuple`, `list` or `Color`
            elif field_type_outer is Union:
                errors = []
                for sub_field in fields[kw].sub_fields:
                    try:
                        # would be nice to not repeat logic from above here
                        if hasattr(sub_field.type_, "from_list_expr"):
                            kwargs[kw] = sub_field.type_.from_list_expr([kw] + exp[0])
                        else:
                            kwargs[kw] = sub_field.type_(*exp[0])
                    except (ValidationError, TypeError) as e:
                        errors.append(e)
                    else:
                        break
                if kw not in kwargs:
                    raise errors[0]

            else:
                # we do actually support multiple args by using `*exp[0]` but
                # do we gain anything by allowing it?
                if len(exp[0]) != 1:
                    raise SyntaxError(
                        f"Expecting only one item but got {len(exp[0])}: {exp[0]}"
                    )
                kwargs[kw] = field_type(*exp[0])

    return cls(*parsed_args, **kwargs)


from_list_expr = classmethod(_from_list_expr)
