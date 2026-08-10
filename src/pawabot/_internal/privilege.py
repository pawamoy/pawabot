"""Privilege system classes."""


class Privilege:
    def __init__(self, name, verbose_name, description):
        self.name = name
        self.verbose_name = verbose_name
        self.description = description


class _PrivilegesMetaclass(type):
    mapping_name = "__privilege_mapping__"

    def __new__(mcs, cls, bases, dct):
        super_new = super().__new__

        mapping = {}

        for variable_name, variable in dct.items():
            if isinstance(variable, Privilege):
                mapping[variable.name] = variable

        dct[_PrivilegesMetaclass.mapping_name] = mapping

        return super_new(mcs, cls, bases, dct)


class Privileges(metaclass=_PrivilegesMetaclass):
    @classmethod
    def get(cls, privilege_name):
        return cls.__getattribute__(_PrivilegesMetaclass.mapping_name).get(privilege_name)
