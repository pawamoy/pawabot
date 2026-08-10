# Copyright (c) 2020, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

from typing import Any


class Privilege:
    def __init__(self, name: str, verbose_name: str, description: str) -> None:
        self.name = name
        self.verbose_name = verbose_name
        self.description = description


class _PrivilegesMetaclass(type):
    mapping_name = "__privilege_mapping__"

    def __new__(mcs: type, cls: str, bases: tuple, dct: dict[str, Any]) -> type:
        super_new = super().__new__  # ty:ignore

        mapping = {}

        for variable in dct.values():
            if isinstance(variable, Privilege):
                mapping[variable.name] = variable

        dct[_PrivilegesMetaclass.mapping_name] = mapping

        return super_new(mcs, cls, bases, dct)


class Privileges(metaclass=_PrivilegesMetaclass):
    @classmethod
    def get(cls, privilege_name: str) -> Privilege | None:
        return cls.__getattribute__(_PrivilegesMetaclass.mapping_name).get(privilege_name)  # ty:ignore
